"""Build and render the showcase views of the semantic twin, procedurally.

Nothing here is a hand-authored scene. Every run reads the shipped artifacts of
one site, assembles the layers, derives the camera framing from the data, drives
headless Blender, and burns the legends into the images. The same code path runs
Milan and Korenmarkt, and the only per-site input is a block in
``config/showcase.json``.

    python render_showcase.py --site korenmarkt
    python render_showcase.py --site milan_duomo --render-host blgpu
    python render_showcase.py --site korenmarkt --draft          # fast preview
    python render_showcase.py --site korenmarkt --stage annotate # relabel only

Stages, in order, all of which can be run alone with ``--stage``:

``payload``   read the artifacts and write ``payload.npz`` plus its sidecar
``render``    run ``showcase_blender.py`` and write the raw PNGs
``annotate``  compose legends, titles and the reference photograph into them

Determinism. Cycles runs with a fixed seed, no animated seed and no motion blur,
every camera is derived from the artifacts rather than from a saved viewport,
and no material carries random jitter. The same artifacts and the same render
device give the same pixels.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import shutil
import subprocess
import sys
from typing import Any

import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from semantic_twin.materials import SurfaceRoughnessLibrary  # noqa: E402
from semantic_twin.showcase import (  # noqa: E402
    MATERIAL_COLOURS,
    REJECTION_COLOURS,
    VISIBILITY_COLOURS,
    VISIBILITY_STATES,
    Layer,
    Pose,
    box,
    class_colour,
    classify_visibility,
    compact_faces,
    crop_specs,
    ellipsoid,
    face_channel_majority,
    legend_entry,
    lift_towards,
    load_fishnet,
    load_rejected,
    ramp,
    read_ply,
    reprojection_residual_px,
    rejection_reason_names,
    triangle_area,
    unweld_duplicates,
    uniform,
    write_payload,
)

SENSOR_WIDTH_MM = 36.0

# Above this, the pose file and the shipped surface set did not come from the
# same solve, and the render cannot be laid over the source photograph.
CROP_REGISTRATION_TOLERANCE_PX = 2.0

# A rendered pixel of a categorical layer has to be its legend colour to within
# this much on each channel. Two levels out of 255 covers PNG quantisation and
# nothing else.
PALETTE_TOLERANCE = 2.0 / 255.0
DEFAULT_BLENDER = pathlib.Path.home() / "blender-4.5" / "blender"


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--site", required=True)
    parser.add_argument("--config", type=pathlib.Path, default=SCRIPT_DIR / "config" / "showcase.json")
    parser.add_argument("--out", type=pathlib.Path, help="Output directory, defaults to outputs/showcase_<site>")
    parser.add_argument("--stage", nargs="*", choices=["payload", "render", "annotate"], default=None)
    parser.add_argument("--views", nargs="*", help="Restrict rendering and annotation to these views")
    parser.add_argument("--blender", type=pathlib.Path, default=DEFAULT_BLENDER)
    parser.add_argument("--render-host", help="ssh host with a GPU, for example blgpu")
    parser.add_argument("--remote-root", default="~/showcase")
    parser.add_argument("--device", default="GPU", choices=["GPU", "CPU"])
    parser.add_argument("--draft", action="store_true", help="Low samples and half resolution")
    parser.add_argument("--samples", type=int)
    parser.add_argument("--resolution-scale", type=float, default=1.0)
    parser.add_argument("--blend", action="store_true", help="Also save the assembled .blend")
    parser.add_argument("--skip-tiles", action="store_true", help="Leave the textured leaves out, for fast iteration")
    return parser.parse_args()


def lens_for_fov(fov_deg: float) -> float:
    return (SENSOR_WIDTH_MM / 2.0) / math.tan(math.radians(fov_deg) / 2.0)


def orbit(anchor: np.ndarray, radius: float, azimuth_deg: float, elevation_deg: float) -> np.ndarray:
    azimuth = math.radians(azimuth_deg)
    elevation = math.radians(elevation_deg)
    return anchor + radius * np.array(
        [
            math.sin(azimuth) * math.cos(elevation),
            math.cos(azimuth) * math.cos(elevation),
            math.sin(elevation),
        ]
    )


def concept_roughness(config_dir: pathlib.Path) -> tuple[SurfaceRoughnessLibrary, dict[str, float]]:
    """RMS height in metres for every concept prompt the roughness library claims."""
    library = SurfaceRoughnessLibrary.load(config_dir / "surface_roughness.json")
    table: dict[str, float] = {}
    for entry in library.classes.values():
        for concept in entry.concepts:
            table.setdefault(concept, entry.rms_height_m)
    return library, table


def build_layers(site: dict[str, Any], paths: dict[str, pathlib.Path]) -> tuple[list[Layer], dict[str, Any]]:
    """Turn every shipped artifact of one site into renderable triangle soups."""
    report: dict[str, Any] = {}
    pose = Pose.load(paths["pose"])
    views = site["crops"]

    support_vertices, support_faces = read_ply(paths["support_mesh"])
    support_area = triangle_area(support_vertices, support_faces)
    report["support"] = {
        "mesh": str(paths["support_mesh"]),
        "vertices": int(len(support_vertices)),
        "faces": int(len(support_faces)),
        "area_m2": float(support_area.sum()),
    }

    texture_index = None
    texture_material = None
    texture_concentration = None
    if paths.get("texture_evidence") is not None and paths["texture_evidence"].is_file():
        with np.load(paths["texture_evidence"]) as data:
            texture_index = np.asarray(data["face_index"], dtype=np.int64)
            probability = np.asarray(data["material_probability"], dtype=np.float64)
            labels = [str(name) for name in data["material_labels"]]
            texture_concentration = np.asarray(data["concentration"], dtype=np.float64)
        texture_material = [labels[index] for index in probability.argmax(axis=1)]
        report["texture_evidence"] = {
            "source": str(paths["texture_evidence"]),
            "faces": int(len(texture_index)),
            "face_fraction": float(len(texture_index) / len(support_faces)),
        }

    intersector = trimesh.Trimesh(vertices=support_vertices, faces=support_faces, process=False).ray
    state, visibility_report = classify_visibility(support_vertices, support_faces, pose, texture_index, intersector)
    report["visibility"] = visibility_report

    support_channels: dict[str, np.ndarray] = {
        "support_plain": uniform((0.52, 0.52, 0.52, 1.0), len(support_faces)),
        "support_dark": uniform((0.10, 0.10, 0.12, 1.0), len(support_faces)),
        "visibility": np.stack([VISIBILITY_COLOURS[VISIBILITY_STATES[value]] for value in state]).astype(np.float32),
    }
    support_legends: dict[str, list[dict[str, Any]]] = {
        "support_dark": [
            legend_entry(
                "support geometry with no surface element over it",
                (0.10, 0.10, 0.12, 1.0),
                "the panorama saw nothing there, or the cutter refused it",
            )
        ],
        "visibility": [
            legend_entry(
                "seen by the panorama",
                VISIBILITY_COLOURS["panorama"],
                f"{visibility_report['panorama_face_fraction']:.1%} of faces",
            ),
            legend_entry(
                "tile texture only",
                VISIBILITY_COLOURS["texture"],
                f"{visibility_report['texture_face_fraction']:.1%} of faces",
            ),
            legend_entry(
                "no image evidence",
                VISIBILITY_COLOURS["unseen"],
                f"{visibility_report['unseen_face_fraction']:.1%} of faces",
            ),
        ],
    }
    if texture_index is not None:
        material_colours = np.tile(np.array([0.10, 0.10, 0.12, 1.0], dtype=np.float32), (len(support_faces), 1))
        for face, name in zip(texture_index, texture_material, strict=True):
            material_colours[face] = MATERIAL_COLOURS.get(name, MATERIAL_COLOURS["unknown"])
        support_channels["texture_material"] = material_colours
        concentration_colours = np.tile(np.array([0.10, 0.10, 0.12, 1.0], dtype=np.float32), (len(support_faces), 1))
        concentration_colours[texture_index] = ramp(np.log10(np.maximum(texture_concentration, 1e-3)), -1.0, 2.0)
        support_channels["texture_concentration"] = concentration_colours
        present = sorted({name for name in texture_material})
        support_legends["texture_material"] = [
            legend_entry(name, MATERIAL_COLOURS.get(name, MATERIAL_COLOURS["unknown"])) for name in present
        ]
        support_legends["texture_concentration"] = [
            legend_entry("0.1", ramp(np.array([-1.0]), -1.0, 2.0)[0]),
            legend_entry("10", ramp(np.array([1.0]), -1.0, 2.0)[0]),
            legend_entry("100 pseudo-counts", ramp(np.array([2.0]), -1.0, 2.0)[0]),
        ]

    layers = [
        Layer(
            name="support",
            vertices=support_vertices,
            faces=support_faces,
            channels=support_channels,
            legends=support_legends,
            scalars={"visibility_state": state.astype(np.float32)},
        )
    ]

    fishnet = load_fishnet(paths["fishnet"], views)
    entity_names = {
        int(key): value for key, value in json.loads(paths["semantics_json"].read_text())["entity_id2label"].items()
    }
    sphere = dict(np.load(paths["panorama_semantics"]))
    material_names = {
        int(key): value
        for key, value in json.loads(paths["semantics_json"].read_text())["rf_material_id2label"].items()
    }
    concept_names = {
        int(key): value for key, value in json.loads(paths["semantics_json"].read_text())["concept_id2label"].items()
    }

    centroids = fishnet["vertices"][fishnet["faces"]].mean(axis=1)
    specs = crop_specs(paths["fishnet"] / "fishnet_manifest.json", views, site["crop_yaws"])
    sampled = face_channel_majority(
        paths["fishnet"],
        views,
        specs,
        sphere,
        ("rf_material", "material_concept"),
        {"rf_material": len(material_names), "material_concept": len(concept_names)},
    )
    face_material = np.array([material_names.get(int(value), "unknown") for value in sampled["rf_material"]])
    face_concept = np.array([concept_names.get(int(value), "") for value in sampled["material_concept"]])
    _library, roughness_table = concept_roughness(paths["config_dir"])
    face_rms = np.array([roughness_table.get(name, np.nan) for name in face_concept])

    class_colours = np.stack(
        [class_colour(value, entity_names.get(int(value), str(value))) for value in fishnet["face_class"]]
    ).astype(np.float32)
    material_colours = np.stack(
        [MATERIAL_COLOURS.get(name, MATERIAL_COLOURS["unknown"]) for name in face_material]
    ).astype(np.float32)
    roughness_colours = ramp(np.log10(np.where(np.isfinite(face_rms), face_rms, 1e-6)), -6.0, -2.5)
    roughness_colours[~np.isfinite(face_rms)] = (0.16, 0.16, 0.18, 1.0)

    lift = float(site.get("fishnet_lift_m", 0.25))
    fishnet_vertices = lift_towards(fishnet["vertices"], fishnet["faces"], pose.position, lift)

    class_counts: dict[str, float] = {}
    class_ids: dict[str, int] = {}
    for value, area in zip(fishnet["face_class"], fishnet["face_area_m2"], strict=True):
        name = entity_names.get(int(value), str(value))
        class_counts[name] = class_counts.get(name, 0.0) + float(area)
        class_ids[name] = int(value)
    ordered_classes = sorted(class_counts, key=lambda name: -class_counts[name])
    material_area: dict[str, float] = {}
    for name, area in zip(face_material, fishnet["face_area_m2"], strict=True):
        material_area[name] = material_area.get(name, 0.0) + float(area)
    ordered_materials = sorted(material_area, key=lambda name: -material_area[name])

    report["fishnet"] = {
        "directory": str(paths["fishnet"]),
        "crops": views,
        "faces": int(len(fishnet["faces"])),
        "area_m2": float(fishnet["face_area_m2"].sum()),
        "solid_angle_sr": float(fishnet["face_solid_angle_sr"].sum()),
        "mean_confidence": float(fishnet["face_confidence"].mean()),
        "lift_towards_camera_m": lift,
        "class_area_m2": {name: class_counts[name] for name in ordered_classes},
        "material_area_m2": {name: material_area[name] for name in ordered_materials},
        "concept_backed_faces": int(np.isfinite(face_rms).sum()),
    }

    layers.append(
        Layer(
            name="fishnet",
            vertices=fishnet_vertices,
            faces=fishnet["faces"],
            channels={
                "fishnet_class": class_colours,
                "fishnet_material": material_colours,
                "fishnet_confidence": ramp(fishnet["face_confidence"], 0.3, 1.0),
                "fishnet_roughness": roughness_colours,
                "fishnet_visible_fraction": ramp(fishnet["face_visible_fraction"], 0.5, 1.0),
            },
            legends={
                "fishnet_class": [
                    legend_entry(name, class_colour(class_ids[name], name), f"{class_counts[name]:,.0f} m2")
                    for name in ordered_classes[:10]
                ],
                "fishnet_material": [
                    legend_entry(
                        name, MATERIAL_COLOURS.get(name, MATERIAL_COLOURS["unknown"]), f"{material_area[name]:,.0f} m2"
                    )
                    for name in ordered_materials[:10]
                ],
                "fishnet_confidence": [
                    legend_entry("0.30", ramp(np.array([0.3]), 0.3, 1.0)[0]),
                    legend_entry("0.65", ramp(np.array([0.65]), 0.3, 1.0)[0]),
                    legend_entry("1.00", ramp(np.array([1.0]), 0.3, 1.0)[0]),
                ],
                "fishnet_roughness": [
                    legend_entry("1 um", ramp(np.array([-6.0]), -6.0, -2.5)[0]),
                    legend_entry("60 um", ramp(np.array([-4.2]), -6.0, -2.5)[0]),
                    legend_entry("3 mm RMS", ramp(np.array([-2.5]), -6.0, -2.5)[0]),
                    legend_entry("no concept claim", (0.16, 0.16, 0.18, 1.0)),
                ],
                "fishnet_visible_fraction": [
                    legend_entry("0.5", ramp(np.array([0.5]), 0.5, 1.0)[0]),
                    legend_entry("1.0 of its own cell", ramp(np.array([1.0]), 0.5, 1.0)[0]),
                ],
            },
        )
    )

    fixed_class = np.array([entity_names.get(int(value), str(value)) for value in fishnet["face_class"]])
    report["fishnet"]["building_faces"] = int((fixed_class == "Building").sum())
    report["facade"] = facade_frame(fishnet, fixed_class, pose)

    # The exploded stack has to be one patch, not the whole surface set. Four
    # copies of a 130 m scene lifted apart still interpenetrate, and the reader
    # sees four overlapping cities rather than four layers of one wall.
    patch_radius = float(site.get("framing", {}).get("stack_patch_radius_m", 22.0))
    centre = np.asarray(report["facade"]["centre_enu_m"])
    inside = np.linalg.norm(fishnet["vertices"][fishnet["faces"]].mean(axis=1) - centre, axis=1) <= patch_radius
    patch_faces, patch_map = compact_faces(fishnet_vertices, fishnet["faces"][inside])
    report["facade"]["stack_patch_radius_m"] = patch_radius
    report["facade"]["stack_patch_faces"] = int(inside.sum())
    layers.append(
        Layer(
            name="fishnet_patch",
            vertices=fishnet_vertices[patch_map],
            faces=patch_faces,
            channels={
                "patch_plain": uniform((0.55, 0.55, 0.58, 1.0), int(inside.sum())),
                "patch_class": class_colours[inside],
                "patch_material": material_colours[inside],
                "patch_roughness": roughness_colours[inside],
            },
            legends={"patch_roughness": []},
        )
    )

    rejected = load_rejected(paths["fishnet"], views)
    source_vertices, source_faces = read_ply(paths["fishnet_source_mesh"])
    reason_names = rejection_reason_names()
    keep = (rejected["source_triangle"] >= 0) & (rejected["source_triangle"] < len(source_faces))
    reject_faces = source_faces[rejected["source_triangle"][keep]]
    reasons = rejected["reason"][keep]
    # The source vertex table is kept whole so neighbouring rejected triangles
    # still share edges. ``lift_towards`` moves only the vertices they use.
    reject_vertices = lift_towards(source_vertices, reject_faces, pose.position, lift)
    reject_colours = np.stack(
        [REJECTION_COLOURS.get(reason_names.get(int(value), ""), (0.7, 0.7, 0.7, 1.0)) for value in reasons]
    ).astype(np.float32)
    reason_area: dict[str, float] = {}
    for value, area in zip(reasons, rejected["image_area_px"][keep], strict=True):
        name = reason_names.get(int(value), "unknown")
        reason_area[name] = reason_area.get(name, 0.0) + float(area)
    ordered_reasons = sorted(reason_area, key=lambda name: -reason_area[name])
    total_reject_area = sum(reason_area.values()) or 1.0
    report["rejected"] = {
        "candidates": int(len(reasons)),
        "image_area_px_by_reason": {name: reason_area[name] for name in ordered_reasons},
    }
    layers.append(
        Layer(
            name="rejected",
            vertices=reject_vertices,
            faces=reject_faces,
            channels={"rejected_reason": reject_colours},
            legends={
                "rejected_reason": [
                    legend_entry(
                        name.replace("_", " "),
                        REJECTION_COLOURS.get(name, (0.7, 0.7, 0.7, 1.0)),
                        f"{reason_area[name] / total_reject_area:.0%} of rejected image area",
                    )
                    for name in ordered_reasons
                ]
            },
        )
    )

    body_dir = paths.get("bodies")
    if body_dir is not None and body_dir.is_dir():
        manifest = json.loads((body_dir / "dynamic_bodies_manifest.json").read_text())
        parts_v: list[np.ndarray] = []
        parts_f: list[np.ndarray] = []
        offset = 0
        for record in sorted(manifest["bodies"], key=lambda entry: entry["body_id"]):
            path = body_dir / f"{record['body_id']}.npz"
            if not path.is_file():
                continue
            with np.load(path) as data:
                parts_v.append(np.asarray(data["vertices_enu_m"], dtype=np.float64))
                parts_f.append(np.asarray(data["faces"], dtype=np.int64) + offset)
                offset += len(data["vertices_enu_m"])
        if parts_v:
            body_vertices = np.vstack(parts_v)
            body_faces = np.vstack(parts_f)
            layers.append(
                Layer(
                    name="bodies",
                    vertices=body_vertices,
                    faces=body_faces,
                    channels={"body_flat": uniform((0.62, 0.95, 0.20, 1.0), len(body_faces))},
                    legends={
                        "body_flat": [
                            legend_entry(
                                f"{len(parts_v)} SMPL-X pedestrians",
                                (0.62, 0.95, 0.20, 1.0),
                                "reconstructed, not painted onto the wall",
                            )
                        ]
                    },
                )
            )
            report["bodies"] = {
                "count": len(parts_v),
                "stature_m": [float(record["stature_m"]) for record in manifest["bodies"]],
                "placed_range_m": [float(record["placed_range_m"]) for record in manifest["bodies"]],
            }

    marker_vertices, marker_faces = box(pose.position, np.array([0.55, 0.55, 0.55]))
    layers.append(
        Layer(
            name="camera_marker",
            vertices=marker_vertices,
            faces=marker_faces,
            channels={"camera_flat": uniform((1.0, 0.95, 0.25, 1.0), len(marker_faces))},
            legends={
                "camera_flat": [
                    legend_entry(
                        "registered panorama camera",
                        (1.0, 0.95, 0.25, 1.0),
                        f"{pose.height_above_ground_m:.2f} m above ground, {pose.residual_deg:.3f} deg residual",
                    )
                ]
            },
        )
    )

    shell = ellipsoid(pose.position, pose.covariance_xyz, sigma=float(site.get("covariance_sigma", 3.0)))
    sigma = np.sqrt(np.diag(pose.covariance_xyz))
    shell.channels["covariance_flat"] = uniform((0.20, 0.95, 0.85, 1.0), len(shell.faces))
    shell.legends["covariance_flat"] = [
        legend_entry(
            "3 sigma pose covariance",
            (0.20, 0.95, 0.85, 1.0),
            f"{sigma[0] * 100:.0f}, {sigma[1] * 100:.0f}, {sigma[2] * 100:.0f} cm east north up",
        )
    ]
    layers.append(shell)
    pose_document = json.loads(paths["pose"].read_text())
    report["pose"] = {
        "position_enu_m": pose.position.tolist(),
        "heading_deg": pose.heading_deg,
        "pitch_correction_deg": float(pose_document.get("pitch_correction_deg", 0.0)),
        "roll_correction_deg": float(pose_document.get("roll_correction_deg", 0.0)),
        "skyline_residual_deg": pose.residual_deg,
        "height_above_ground_m": pose.height_above_ground_m,
        "sigma_enu_m": sigma.tolist(),
    }

    unwelded = {layer.name: unweld_duplicates(layer) for layer in layers}
    report["unwelded_duplicate_faces"] = {name: count for name, count in unwelded.items() if count}
    report["crop_registration"] = reprojection_residual_px(paths["fishnet"], views, specs, pose)
    if report["crop_registration"]["median_px"] > CROP_REGISTRATION_TOLERANCE_PX:
        print(
            f"[driver] WARNING: the pose file reprojects the shipped surface set "
            f"{report['crop_registration']['median_px']:.1f} px from where the cutter recorded it. "
            "The facade views will say so rather than claim a registration they do not have.",
            flush=True,
        )
    report["material_reference"] = sphere_material_split(sphere, entity_names, material_names)
    report["extent"] = {
        "p90_range_m": float(np.percentile(np.linalg.norm(centroids - pose.position, axis=1), 90)),
        "ground_z_m": float(pose.position[2] - pose.height_above_ground_m),
    }
    return layers, report


def sphere_material_split(
    sphere: dict[str, np.ndarray], entity_names: dict[int, str], material_names: dict[int, str]
) -> dict[str, float]:
    """Material shares over the whole panorama sphere, weighted by solid angle.

    The fishnet legend is weighted by metric surface area over four horizontal
    crops, which loads distant and grazing surfaces heavily. This is the other
    natural weighting of the same evidence and it is not the same number, so
    both are carried and neither is presented as the site's material split.
    """
    entity = np.asarray(sphere["entity"])
    material = np.asarray(sphere["rf_material"])
    wall = [key for key, value in entity_names.items() if value in ("Building", "Wall")]
    selection = np.isin(entity, wall)
    rows = np.arange(entity.shape[0])
    weight = np.repeat(np.cos((rows + 0.5) / entity.shape[0] * np.pi - np.pi / 2.0), entity.shape[1])
    weight = weight.reshape(entity.shape)[selection]
    values = material[selection]
    totals: dict[str, float] = {}
    for code in np.unique(values):
        totals[material_names.get(int(code), "unknown")] = float(weight[values == code].sum())
    scale = sum(totals.values()) or 1.0
    return {name: share / scale for name, share in sorted(totals.items(), key=lambda item: -item[1])}


def facade_frame(fishnet: dict[str, np.ndarray], class_names: np.ndarray, pose: Pose) -> dict[str, Any]:
    """Pick the facade patch the render should close in on.

    The choice is made from the data rather than by hand: the crop that carries
    the most building area, and inside it the area-weighted centroid and normal
    of the faces whose normal faces the camera. That rule transfers to any site.
    """
    building = class_names == "Building"
    if not building.any():
        building = np.ones(len(class_names), dtype=bool)
    best_view = int(np.bincount(fishnet["view"][building], weights=fishnet["face_area_m2"][building]).argmax())
    selection = building & (fishnet["view"] == best_view)
    centroids = fishnet["vertices"][fishnet["faces"]].mean(axis=1)[selection]
    areas = fishnet["face_area_m2"][selection]
    corners = fishnet["vertices"][fishnet["faces"][selection]]
    normals = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
    towards = pose.position - centroids
    normals *= np.sign(np.sum(normals * towards, axis=1))[:, None]
    upright = np.abs(normals[:, 2]) < 0.6
    if upright.sum() > 8:
        centroids, areas, normals = centroids[upright], areas[upright], normals[upright]
    centre = (centroids * areas[:, None]).sum(axis=0) / areas.sum()
    normal = (normals * areas[:, None]).sum(axis=0)
    normal /= np.linalg.norm(normal)
    return {
        "crop_index": best_view,
        "centre_enu_m": centre.tolist(),
        "normal_enu": normal.tolist(),
        "area_m2": float(areas.sum()),
        "faces": int(len(areas)),
    }


def registration_caption(report: dict[str, Any], right_panel: str) -> str:
    """Say whether the two panels are registered to each other, or only alike."""
    residual = float(report["crop_registration"]["median_px"])
    if residual <= CROP_REGISTRATION_TOLERANCE_PX:
        return (
            f"Left, the source crop. Right, {right_panel}. Same camera, same 90 degree field of view, "
            f"registered to {residual:.2f} px"
        )
    return (
        f"Left, the source crop. Right, {right_panel}. The camera is the pose currently on disk, which "
        f"reprojects the shipped surface set {residual:.0f} px from where the cutter recorded it, so read "
        "these as the same view rather than as an overlay"
    )


def crop_basis(pose_report: dict[str, Any], crop_yaw_deg: float) -> np.ndarray:
    """Blender camera basis that reproduces one panorama crop exactly.

    ``view_basis`` gives the crop's right, forward and up in the panorama frame
    and ``panorama_to_world_matrix`` carries them into ENU, roll included.
    Blender looks down its own minus Z with plus Y up, so the columns are right,
    up and minus forward. Deriving the roll rather than dropping it is the
    difference between a render that overlays the photograph and one that is
    merely pointed the same way.
    """
    from semantic_twin.pano_geometry import panorama_to_world_matrix, view_basis

    right, forward, up = view_basis(crop_yaw_deg, 0.0)
    rotation = panorama_to_world_matrix(
        float(pose_report["heading_deg"]),
        pitch_deg=float(pose_report.get("pitch_correction_deg", 0.0)),
        roll_deg=float(pose_report.get("roll_correction_deg", 0.0)),
    )
    return np.column_stack([rotation @ right, rotation @ up, rotation @ -forward])


def build_views(site: dict[str, Any], report: dict[str, Any], paths: dict[str, pathlib.Path]) -> list[dict[str, Any]]:
    """Derive every camera from the artifacts, not from a saved viewport."""
    framing = site.get("framing", {})
    pose_position = np.asarray(report["pose"]["position_enu_m"])
    ground = float(report["extent"]["ground_z_m"])
    radius = float(framing.get("orbit_scale", 2.1)) * float(report["extent"]["p90_range_m"])
    anchor = np.array([pose_position[0], pose_position[1], ground + float(framing.get("anchor_height_m", 10.0))])
    orbit_position = orbit(
        anchor, radius, float(framing.get("azimuth_deg", 215.0)), float(framing.get("elevation_deg", 26.0))
    )
    orbit_camera = {"position": orbit_position.tolist(), "target": anchor.tolist(), "lens_mm": lens_for_fov(48.0)}

    centre = np.asarray(report["facade"]["centre_enu_m"])
    normal = np.asarray(report["facade"]["normal_enu"])

    # The facade views reproduce the crop the fishnet was cut in, exactly. The
    # camera sits at the registered pose with the crop's own basis and field of
    # view, so the render and the photograph beside it are the same projection
    # and a reader can compare them pixel for pixel rather than by eye.
    crop_index = int(report["facade"]["crop_index"])
    crop_camera = {
        "position": pose_position.tolist(),
        "basis": crop_basis(report["pose"], float(site["crop_yaws"][crop_index])).tolist(),
        "lens_mm": lens_for_fov(90.0),
    }

    stack_gap = float(framing.get("stack_gap_m", 16.0))
    yaw = math.radians(float(framing.get("stack_yaw_offset_deg", 38.0)))
    swing = np.array(
        [
            normal[0] * math.cos(yaw) - normal[1] * math.sin(yaw),
            normal[0] * math.sin(yaw) + normal[1] * math.cos(yaw),
            0.0,
        ]
    )
    swing /= np.linalg.norm(swing)
    stack_target = centre + np.array([0.0, 0.0, 1.5 * stack_gap])
    stack_camera = {
        "position": (stack_target + swing * float(framing.get("stack_distance_m", 150.0))).tolist(),
        "target": stack_target.tolist(),
        "lens_mm": lens_for_fov(float(framing.get("stack_fov_deg", 42.0))),
    }

    wide = [1920, 1200]
    square = [1440, 1440]
    portrait = [1150, 1500]
    visibility = report["visibility"]
    photo = paths["views_dir"] / f"{site['crops'][int(report['facade']['crop_index'])]}.jpg"

    return [
        {
            "name": "establishing",
            "title": f"{site['title']}, assembled from the shipped artifacts",
            "subtitle": (
                "Photorealistic 3D Tiles leaves placed in double precision, the registered panorama camera, "
                "and the pedestrians the segmenter refused to paint onto the walls"
            ),
            "camera": orbit_camera,
            "resolution": wide,
            "samples": 512,
            "view_transform": "AgX",
            "lighting": "photographic",
            "layers": [
                {"layer": "tiles"},
                {"layer": "bodies", "channel": "body_flat"},
                {"layer": "camera_marker", "channel": "camera_flat"},
                {"layer": "pose_covariance", "channel": "covariance_flat"},
            ],
            "legend": [
                ("bodies", "body_flat"),
                ("camera_marker", "camera_flat"),
                ("pose_covariance", "covariance_flat"),
            ],
            "notes": [
                f"support mesh {report['support']['faces']:,} triangles from {site['tile_count']} leaf tiles",
                f"panorama pose residual {report['pose']['skyline_residual_deg']:.3f} deg",
            ],
        },
        {
            "name": "semantics",
            "title": "Fishnet surface set, coloured by entity class",
            "subtitle": (
                "Support triangles projected into the four panorama crops, cut against the semantic island "
                "boundaries there, and mapped back onto their own planes"
            ),
            "camera": orbit_camera,
            "resolution": wide,
            "samples": 384,
            "layers": [
                {"layer": "support", "channel": "support_dark"},
                {"layer": "fishnet", "channel": "fishnet_class"},
                {"layer": "camera_marker", "channel": "camera_flat"},
            ],
            "legend": [("fishnet", "fishnet_class"), ("support", "support_dark")],
            "notes": [
                f"{report['fishnet']['faces']:,} surface elements over {report['fishnet']['area_m2']:,.0f} m2",
                f"mean class confidence {report['fishnet']['mean_confidence']:.2f}",
            ],
        },
        {
            "name": "visibility",
            "title": "What the panorama actually sees",
            "subtitle": (
                "Only the orange band is directly observed. Everything blue takes its material from the tile "
                "texture, and everything dark is asserted by the photogrammetry with no image evidence at all"
            ),
            "camera": orbit_camera,
            "resolution": wide,
            "samples": 384,
            "layers": [
                {"layer": "support", "channel": "visibility"},
                {"layer": "camera_marker", "channel": "camera_flat"},
            ],
            "legend": [("support", "visibility")],
            "notes": [
                f"{visibility['panorama_faces']:,} of {visibility['faces']:,} support triangles are a first hit "
                f"from the capture point inside the {visibility['crop_half_elevation_deg']:.0f} degree crop band",
                f"by area that is {visibility['panorama_area_fraction']:.1%} seen, "
                f"{visibility['texture_area_fraction']:.1%} texture only, "
                f"{visibility['unseen_area_fraction']:.1%} unobserved",
            ],
        },
        {
            "name": "visibility_from_camera",
            "title": "The same classification, from the capture point",
            "subtitle": (
                "A 90 degree crop taken from the registered camera position. The observed set fills the frame "
                "here and is a thin shell everywhere else"
            ),
            "camera": crop_camera,
            "resolution": square,
            "samples": 384,
            "layers": [{"layer": "support", "channel": "visibility"}],
            "legend": [("support", "visibility")],
            "notes": [
                "one panorama constrains one shell of one street",
                f"{visibility['in_crop_band_faces']:,} triangles lie inside the crop band at all",
            ],
        },
        {
            "name": "facade_class",
            "title": "Resolved facade, against the photograph it came from",
            "subtitle": registration_caption(report, "the entity classes the cutter carried onto the surface"),
            "camera": crop_camera,
            "resolution": square,
            "samples": 512,
            "photo": str(photo),
            "layers": [
                {"layer": "support", "channel": "support_dark"},
                {"layer": "fishnet", "channel": "fishnet_class"},
            ],
            "legend": [("fishnet", "fishnet_class"), ("support", "support_dark")],
            "notes": [
                f"crop {site['crops'][int(report['facade']['crop_index'])]}, "
                f"{report['facade']['faces']:,} building faces over {report['facade']['area_m2']:,.0f} m2"
            ],
        },
        {
            "name": "facade_material",
            "title": "The same facade, as radio materials",
            "subtitle": registration_caption(
                report,
                "the ITU-facing material of the panorama ray that observed each surface element, one row of "
                "Recommendation ITU-R P.2040-4 per colour",
            ),
            "camera": crop_camera,
            "resolution": square,
            "samples": 512,
            "photo": str(photo),
            "layers": [
                {"layer": "support", "channel": "support_dark"},
                {"layer": "fishnet", "channel": "fishnet_material"},
            ],
            "legend": [("fishnet", "fishnet_material"), ("support", "support_dark")],
            "notes": [
                "material is a separate axis from entity class, with its own posterior",
                f"{report['fishnet']['concept_backed_faces']:,} of {report['fishnet']['faces']:,} faces carry a "
                "concept claim that reaches a roughness class",
                "the legend weights by metric surface area over the four horizontal crops. Over the whole "
                "sphere, weighted by solid angle on building pixels, the same evidence reads "
                + ", ".join(f"{name} {share:.0%}" for name, share in list(report["material_reference"].items())[:4]),
            ],
        },
        {
            "name": "stack",
            "title": "One patch of facade, four layers deep",
            "subtitle": "Geometry, entity class, radio material and RMS surface height, in that order upward",
            "camera": stack_camera,
            "resolution": portrait,
            "samples": 384,
            "layers": [{"layer": "fishnet_patch", "channel": "patch_plain"}],
            "stack": [
                {"layer": "fishnet_patch", "channel": "patch_class", "dz_m": stack_gap},
                {"layer": "fishnet_patch", "channel": "patch_material", "dz_m": 2 * stack_gap},
                {"layer": "fishnet_patch", "channel": "patch_roughness", "dz_m": 3 * stack_gap},
            ],
            # All three upper sheets, not just the top one. A legend that names
            # one of four sheets leaves two thirds of the colour in the figure
            # undecodable, which is the same failure as a wrong swatch.
            "legend": [
                ("fishnet", "fishnet_class"),
                ("fishnet", "fishnet_material"),
                ("fishnet", "fishnet_roughness"),
            ],
            "stack_labels": [
                "1. support geometry, Photorealistic 3D Tiles leaves",
                "2. entity class, cut at the semantic island boundaries",
                "3. radio material, one ITU-R P.2040-4 row per colour",
                "4. RMS surface height, from the concept the segmenter admitted",
            ],
            "notes": [
                "the three upper sheets are the same triangles, carrying three independent posteriors",
                f"one patch, {report['facade']['stack_patch_faces']:,} surface elements within "
                f"{report['facade']['stack_patch_radius_m']:.0f} m of the facade centre",
            ],
        },
        {
            "name": "blockage",
            "title": "What was refused, and why",
            "subtitle": (
                "Candidate surface elements the cutter rejected. A moving object leaves a hole in the static "
                "surface rather than being painted onto the wall behind it"
            ),
            "camera": orbit_camera,
            "resolution": wide,
            "samples": 384,
            "layers": [
                {"layer": "support", "channel": "support_dark"},
                {"layer": "rejected", "channel": "rejected_reason"},
                {"layer": "bodies", "channel": "body_flat"},
                {"layer": "camera_marker", "channel": "camera_flat"},
            ],
            "legend": [("rejected", "rejected_reason"), ("bodies", "body_flat"), ("support", "support_dark")],
            "notes": [
                f"{report['rejected']['candidates']:,} rejected candidates across the four crops",
            ],
        },
    ]


def resolve_paths(site: dict[str, Any]) -> dict[str, pathlib.Path]:
    def resolve(value: str | None) -> pathlib.Path | None:
        if value is None:
            return None
        path = pathlib.Path(value).expanduser()
        return path if path.is_absolute() else (SCRIPT_DIR / path)

    paths = {
        "support_mesh": resolve(site["support_mesh"]),
        "fishnet": resolve(site["fishnet"]),
        "fishnet_source_mesh": resolve(site["fishnet_source_mesh"]),
        "pose": resolve(site["pose"]),
        "semantics_json": resolve(site["semantics_json"]),
        "panorama_semantics": resolve(site["panorama_semantics"]),
        "views_dir": resolve(site["views_dir"]),
        "texture_evidence": resolve(site.get("texture_evidence")),
        "bodies": resolve(site.get("bodies")),
        "tiles": resolve(site.get("tiles")),
        "config_dir": SCRIPT_DIR / "config",
    }
    required = ("support_mesh", "fishnet", "fishnet_source_mesh", "pose", "semantics_json", "panorama_semantics")
    missing = [name for name in required if paths[name] is None or not paths[name].exists()]
    if missing:
        detail = ", ".join(f"{name} -> {paths[name]}" for name in missing)
        raise SystemExit(f"Missing required artifacts for this site: {detail}")
    return paths


def run_blender_local(args: argparse.Namespace, out: pathlib.Path, payload: pathlib.Path) -> None:
    command = [
        str(args.blender),
        "--background",
        "--python",
        str(SCRIPT_DIR / "showcase_blender.py"),
        "--",
        "--payload",
        str(payload),
        "--out",
        str(out / "raw"),
        "--device",
        args.device,
        "--resolution-scale",
        str(args.resolution_scale),
    ]
    if args.blend:
        command += ["--blend", str(out / f"{args.site}.blend")]
    if args.views:
        command += ["--views", *args.views]
    if args.samples:
        command += ["--samples", str(args.samples)]
    if args.skip_tiles:
        command += ["--skip-tiles"]
    print("[driver] " + " ".join(command), flush=True)
    subprocess.run(command, check=True)


def run_blender_remote(
    args: argparse.Namespace, out: pathlib.Path, payload: pathlib.Path, tiles: pathlib.Path | None
) -> None:
    """Push the payload to a GPU host, render there, and pull the images back."""
    home = subprocess.run(
        ["ssh", args.render_host, "echo $HOME"], check=True, capture_output=True, text=True
    ).stdout.strip()
    root = f"{args.remote_root}/{args.site}".replace("~", home)
    subprocess.run(["ssh", args.render_host, f"mkdir -p {root}/payload {root}/raw {root}/code"], check=True)
    subprocess.run(
        [
            "rsync",
            "-a",
            "--delete",
            str(SCRIPT_DIR / "semantic_twin") + "/",
            f"{args.render_host}:{root}/code/semantic_twin/",
        ],
        check=True,
    )
    subprocess.run(
        ["rsync", "-a", str(SCRIPT_DIR / "showcase_blender.py"), f"{args.render_host}:{root}/code/"], check=True
    )
    subprocess.run(
        ["rsync", "-a", str(payload), str(payload.with_suffix(".json")), f"{args.render_host}:{root}/payload/"],
        check=True,
    )
    remote_payload = f"{root}/payload/{payload.name}"
    remote_tiles = None
    if tiles is not None:
        remote_tiles = f"{root}/tiles"
        subprocess.run(["rsync", "-a", str(tiles) + "/", f"{args.render_host}:{remote_tiles}/"], check=True)
        sidecar = json.loads(payload.with_suffix(".json").read_text())
        if sidecar.get("tiles") is not None:
            sidecar["tiles"]["directory"] = remote_tiles
            patched = payload.with_suffix(".remote.json")
            patched.write_text(json.dumps(sidecar, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            subprocess.run(
                ["rsync", "-a", str(patched), f"{args.render_host}:{root}/payload/{payload.stem}.json"], check=True
            )

    remote = [
        "LD_LIBRARY_PATH=$HOME/blender-4.5/lib",
        "$HOME/blender-4.5/blender",
        "--background",
        "--python",
        f"{root}/code/showcase_blender.py",
        "--",
        "--payload",
        remote_payload,
        "--out",
        f"{root}/raw",
        "--device",
        args.device,
        "--resolution-scale",
        str(args.resolution_scale),
    ]
    if args.views:
        remote += ["--views", *args.views]
    if args.samples:
        remote += ["--samples", str(args.samples)]
    if args.blend:
        remote += ["--blend", f"{root}/{args.site}.blend"]
    if args.skip_tiles:
        remote += ["--skip-tiles"]
    print(f"[driver] remote render on {args.render_host}", flush=True)
    subprocess.run(["ssh", args.render_host, " ".join(remote)], check=True)
    (out / "raw").mkdir(parents=True, exist_ok=True)
    subprocess.run(["rsync", "-a", f"{args.render_host}:{root}/raw/", str(out / "raw") + "/"], check=True)
    if args.blend:
        subprocess.run(["rsync", "-a", f"{args.render_host}:{root}/{args.site}.blend", str(out)], check=True)


def verify_palette(view: dict[str, Any], sidecar: dict[str, Any], source: pathlib.Path) -> dict[str, Any]:
    """Check that the rendered pixels really are the legend colours.

    The failure this catches is not hypothetical. A colour attribute handed to
    Blender as a display value, or a categorical layer lit like a photograph,
    both put something on the screen that is close to the swatch and wrong, and
    the render still looks fine. Counting how many pixels land within a couple
    of levels of each declared colour turns that into a number.
    """
    entries = [
        entry for key in view.get("legend", []) for entry in sidecar["legend_index"].get(f"{key[0]}:{key[1]}", [])
    ]
    if not entries or view.get("lighting", "flat") != "flat":
        return {"checked": False, "reason": "no categorical legend, or the view is lit like a photograph"}
    pixels = np.asarray(Image.open(source).convert("RGB"), dtype=np.float64) / 255.0
    flat = pixels.reshape(-1, 3)
    swatches = np.array([entry["colour"][:3] for entry in entries])
    distance = np.abs(flat[:, None, :] - swatches[None, :, :]).max(axis=2)
    nearest = distance.argmin(axis=1)
    within = distance.min(axis=1) <= PALETTE_TOLERANCE
    counts = {}
    for index, entry in enumerate(entries):
        counts[entry["label"]] = int(np.count_nonzero(within & (nearest == index)))
    return {
        "checked": True,
        "partial_legend": bool(view.get("stack")),
        "tolerance": PALETTE_TOLERANCE,
        "matched_fraction": float(within.mean()),
        "pixels_by_legend_entry": counts,
        "note": (
            "Fraction of image pixels within the tolerance of some legend swatch. The remainder is the "
            "background, the antialiased edges between classes, and any layer the legend does not name."
        ),
    }


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    for base in ("/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/TTF"):
        candidate = pathlib.Path(base) / name
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default(size)


def to_rgb(colour: list[float]) -> tuple[int, int, int]:
    return tuple(int(round(255 * min(1.0, max(0.0, float(value))))) for value in colour[:3])


def annotate(view: dict[str, Any], sidecar: dict[str, Any], source: pathlib.Path, target: pathlib.Path) -> None:
    """Burn the title, the legend and the key numbers into one render."""
    image = Image.open(source).convert("RGB")
    photo_path = view.get("photo")
    if photo_path and pathlib.Path(photo_path).is_file():
        photo = Image.open(photo_path).convert("RGB")
        photo = photo.resize((image.width, image.height), Image.LANCZOS)
        panel = Image.new("RGB", (image.width * 2 + 12, image.height), (12, 12, 14))
        panel.paste(photo, (0, 0))
        panel.paste(image, (image.width + 12, 0))
        image = panel

    # Every size is a fraction of the image width, so a half resolution draft
    # and a full render carry the same layout rather than the same pixel counts.
    scale = image.width / 1920.0
    margin = int(round(34 * scale))
    title_face = font(max(12, int(round(34 * scale))), bold=True)
    body_face = font(max(10, int(round(20 * scale))))
    label_face = font(max(10, int(round(20 * scale))), bold=True)
    note_face = font(max(9, int(round(18 * scale))))
    stamp_face = font(max(8, int(round(15 * scale))))
    text_width = image.width - 2 * margin

    legends = [
        entry for key in view.get("legend", []) for entry in sidecar["legend_index"].get(f"{key[0]}:{key[1]}", [])
    ]
    notes = view.get("notes", [])
    labels = view.get("stack_labels", [])

    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    subtitle = wrap(probe, view["subtitle"], body_face, text_width)
    note_lines = [line for note in notes for line in wrap(probe, note, note_face, text_width)]
    label_lines = [line for label in labels for line in wrap(probe, label, label_face, text_width)]

    title_step = int(round(44 * scale))
    body_step = int(round(27 * scale))
    row_step = int(round(31 * scale))
    header = title_step + body_step * len(subtitle) + int(round(30 * scale))
    footer = (
        int(round(24 * scale))
        + row_step * (len(legends) + len(label_lines))
        + body_step * len(note_lines)
        + int(round(46 * scale))
    )
    canvas = Image.new("RGB", (image.width, image.height + header + footer), (14, 14, 17))
    canvas.paste(image, (0, header))
    draw = ImageDraw.Draw(canvas)

    y = int(round(20 * scale))
    draw.text((margin, y), view["title"], font=title_face, fill=(244, 244, 246))
    y += title_step
    for line in subtitle:
        draw.text((margin, y), line, font=body_face, fill=(168, 172, 180))
        y += body_step
    draw.line([(0, header - 1), (canvas.width, header - 1)], fill=(40, 40, 46), width=2)

    y = image.height + header + int(round(22 * scale))
    swatch = int(round(26 * scale))
    # The value column starts past the widest label, so a long legend entry
    # cannot run into its own number.
    label_width = max((probe.textlength(entry["label"], font=label_face) for entry in legends), default=0.0)
    value_column = min(
        margin + swatch + int(round(28 * scale)) + int(label_width),
        image.width - int(round(360 * scale)),
    )
    for entry in legends:
        draw.rectangle(
            [margin, y + 3, margin + swatch, y + 3 + swatch * 3 // 4],
            fill=to_rgb(entry["colour"]),
            outline=(70, 70, 78),
        )
        draw.text((margin + swatch + int(round(14 * scale)), y), entry["label"], font=label_face, fill=(232, 234, 238))
        if entry.get("value"):
            draw.text((value_column, y + 1), entry["value"], font=note_face, fill=(150, 154, 162))
        y += row_step
    for line in label_lines:
        draw.text((margin, y), line, font=label_face, fill=(210, 214, 220))
        y += row_step
    y += int(round(8 * scale))
    for line in note_lines:
        draw.text((margin, y), line, font=note_face, fill=(140, 144, 152))
        y += body_step

    stamp = f"{sidecar['site']}  |  {sidecar['generator']}  |  seed {sidecar['render']['seed']}"
    draw.text((margin, canvas.height - int(round(28 * scale))), stamp, font=stamp_face, fill=(96, 100, 108))
    target.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(target)
    print(f"[annotate] {target}", flush=True)


def wrap(draw: ImageDraw.ImageDraw, text: str, face: ImageFont.FreeTypeFont, width: float) -> list[str]:
    """Greedy wrap measured in pixels, so a half-resolution draft still fits."""
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=face) > width and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def main() -> None:
    args = arguments()
    document = json.loads(args.config.read_text())
    if args.site not in document["sites"]:
        raise SystemExit(f"Unknown site {args.site}. Known: {', '.join(sorted(document['sites']))}")
    site = {**document["defaults"], **document["sites"][args.site]}
    out = args.out or (SCRIPT_DIR / "outputs" / f"showcase_{args.site}")
    out.mkdir(parents=True, exist_ok=True)
    payload = out / "payload.npz"
    stages = args.stage or ["payload", "render", "annotate"]
    if args.draft:
        args.resolution_scale = min(args.resolution_scale, 0.5)
        args.samples = args.samples or 48

    paths = resolve_paths(site)
    if "payload" in stages:
        layers, report = build_layers(site, paths)
        views = build_views(site, report, paths)
        legend_index = {
            f"{layer.name}:{channel}": entries for layer in layers for channel, entries in layer.legends.items()
        }
        tiles = None
        if paths["tiles"] is not None and (paths["tiles"] / "manifest.json").is_file():
            tiles = {"directory": str(paths["tiles"]), "crop_radius_m": float(site["crop_radius_m"])}
        elif paths["tiles"] is not None:
            print(f"[driver] tile cache {paths['tiles']} is absent, the textured layer will be skipped", flush=True)
        metadata = {
            "generator": "semantic_twin/render_showcase.py",
            "site": site["title"],
            "site_key": args.site,
            "artifacts": {key: str(value) for key, value in paths.items() if value is not None},
            "report": report,
            "views": views,
            "legend_index": legend_index,
            "tiles": tiles,
            "render": document["render"],
        }
        write_payload(payload, layers, metadata)
        print(f"[driver] payload {payload} ({payload.stat().st_size / 1e6:.1f} MB)", flush=True)

    if "render" in stages:
        if args.render_host:
            run_blender_remote(args, out, payload, paths["tiles"])
        else:
            run_blender_local(args, out, payload)

    if "annotate" in stages:
        sidecar = json.loads(payload.with_suffix(".json").read_text())
        final = out / "figures"
        final.mkdir(parents=True, exist_ok=True)
        for view in sidecar["views"]:
            if args.views and view["name"] not in args.views:
                continue
            source = out / "raw" / f"{view['name']}.png"
            if not source.is_file():
                print(f"[annotate] {source} is absent, skipped", flush=True)
                continue
            annotate(view, sidecar, source, final / f"{view['name']}.png")
        checks = {}
        for view in sidecar["views"]:
            if args.views and view["name"] not in args.views:
                continue
            raw = out / "raw" / f"{view['name']}.png"
            if not raw.is_file():
                continue
            checks[view["name"]] = verify_palette(view, sidecar, raw)
            report = checks[view["name"]]
            if report["checked"]:
                empty = [name for name, count in report["pixels_by_legend_entry"].items() if count == 0]
                print(
                    f"[verify] {view['name']}: {report['matched_fraction']:.1%} of pixels are a legend colour"
                    + (f", absent from the image: {', '.join(empty)}" if empty else ""),
                    flush=True,
                )
                if report["matched_fraction"] < 0.05 and not view.get("stack"):
                    print(
                        f"[verify] WARNING: {view['name']} barely matches its own legend. "
                        "The colour pipeline is wrong, not the framing.",
                        flush=True,
                    )
        sidecar["report"]["palette_check"] = checks
        summary = out / "showcase_manifest.json"
        summary.write_text(json.dumps(sidecar["report"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"[driver] {summary}", flush=True)


if __name__ == "__main__":
    if shutil.which("rsync") is None:
        print("[driver] rsync is not on PATH, remote rendering will fail", file=sys.stderr)
    main()
