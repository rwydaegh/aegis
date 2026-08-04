"""Cut matched facade crops from the panorama and from the Google tile texture.

Both crops of a pair share a viewpoint, a field of view and a pixel grid, so the
only thing that differs between them is where the pixels came from: a Street View
capture taken from the square, or the photogrammetric texture the 3D Tiles leaves
carry. That is the controlled comparison the material question needs, and it is
the reason the crops are cut here rather than lifted from either source's own
framing.

Each crop also records the support mesh faces it looks at, their incidence and
their range, so a per crop material answer can be bound back onto the tracer's
own triangles without a second registration step.

    python3 build_facade_crops.py --out outputs/material_vlm
"""

from __future__ import annotations

import argparse
import json
import pathlib
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
from PIL import Image

from semantic_twin.pano_geometry import PerspectiveView, inference_views, perspective_directions
from semantic_twin.propagation.geometry import MitsubaGeometry
from semantic_twin.materials import classify_faces

ROOT = pathlib.Path(__file__).resolve().parent
MESH = ROOT / "data" / "geometry" / "korenmarkt" / "inhouse_leaf_130m_f64.ply"
MESH_MANIFEST = MESH.with_suffix(".json")
TILES = ROOT / "data" / "tiles" / "korenmarkt"
PANORAMA_DIR = ROOT / "data" / "panoramas" / "korenmarkt"
VIEWS = PANORAMA_DIR / "semantics" / "views"
POSE = PANORAMA_DIR / "alignment" / "pose_aligned.json"
SEMANTICS = PANORAMA_DIR / "semantics" / "semantics.json"
GROUND_DATUM_M = 50.83747424667166


@dataclass(frozen=True)
class Crop:
    crop_id: str
    view: str
    row: int
    column: int
    size: int
    building_fraction: float
    wall_group: str
    faces: int
    face_area_m2: float
    range_median_m: float
    incidence_median_deg: float
    normal_enu: tuple[float, float, float]
    plane_offset_m: float
    centroid_enu: tuple[float, float, float]
    patch: str
    texture_pixel_fraction: float
    texture_gsd_m: float

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def sub_view_directions(view: PerspectiveView, row: int, column: int, size: int, full: int) -> np.ndarray:
    """World-local directions for one square window inside a rectilinear view.

    The window is cut from the same direction grid the segmenter saw, so a crop's
    pixels and its Vistas labels index the same rays by construction.
    """
    grid = perspective_directions(view, full, full)
    return grid[row : row + size, column : column + size]


def building_windows(
    labels: np.ndarray,
    building_id: int,
    *,
    size: int,
    stride: int,
    minimum_fraction: float,
) -> list[tuple[int, int, float]]:
    mask = (labels == building_id).astype(np.float64)
    integral = np.pad(mask, ((1, 0), (1, 0))).cumsum(axis=0).cumsum(axis=1)
    out: list[tuple[int, int, float]] = []
    for row in range(0, labels.shape[0] - size + 1, stride):
        for column in range(0, labels.shape[1] - size + 1, stride):
            total = (
                integral[row + size, column + size]
                - integral[row, column + size]
                - integral[row + size, column]
                + integral[row, column]
            )
            fraction = float(total) / (size * size)
            if fraction >= minimum_fraction:
                out.append((row, column, fraction))
    return sorted(out, key=lambda item: -item[2])


def spread_pick(
    candidates: list[tuple[int, int, float]], *, limit: int, separation: int
) -> list[tuple[int, int, float]]:
    """Greedy pick of the best windows that are not on top of each other."""
    picked: list[tuple[int, int, float]] = []
    for row, column, fraction in candidates:
        if all(max(abs(row - r), abs(column - c)) >= separation for r, c, _ in picked):
            picked.append((row, column, fraction))
        if len(picked) >= limit:
            break
    return picked


def load_tile_surface(crop_radius_m: float) -> Any:
    from semantic_twin.vision.tiles import read_tile_surface

    matrix = np.array(json.loads(MESH_MANIFEST.read_text())["alignment"]["ecef_to_local_enu_matrix"], dtype=np.float64)
    return read_tile_surface(TILES, matrix, crop_radius_m=crop_radius_m)


def barycentric(triangles: np.ndarray, points: np.ndarray) -> np.ndarray:
    """Barycentric coordinates of points inside their own triangles."""
    a, b, c = triangles[:, 0], triangles[:, 1], triangles[:, 2]
    v0, v1, v2 = b - a, c - a, points - a
    d00 = np.einsum("ij,ij->i", v0, v0)
    d01 = np.einsum("ij,ij->i", v0, v1)
    d11 = np.einsum("ij,ij->i", v1, v1)
    d20 = np.einsum("ij,ij->i", v2, v0)
    d21 = np.einsum("ij,ij->i", v2, v1)
    denominator = np.where(np.abs(d00 * d11 - d01 * d01) < 1e-30, 1e-30, d00 * d11 - d01 * d01)
    v = (d11 * d20 - d01 * d21) / denominator
    w = (d00 * d21 - d01 * d20) / denominator
    return np.column_stack([1.0 - v - w, v, w])


def render_texture(
    origin: np.ndarray,
    directions: np.ndarray,
    geometry: MitsubaGeometry,
    surface: Any,
    tile_triangle: np.ndarray,
    matched: np.ndarray,
) -> tuple[np.ndarray, float, float]:
    """Sample the tile atlas along the same rays the panorama crop uses.

    Pixels whose face has no matched tile triangle, or whose ray misses, are left
    black and counted, because a texture crop that is half missing is a different
    object from one that is complete and the model should not be asked to judge
    it as though it were.
    """
    shape = directions.shape[:2]
    flat = directions.reshape(-1, 3)
    origins = np.broadcast_to(origin, flat.shape)
    hit, distance, _normal, face = geometry.intersect(origins, flat)
    image = np.zeros((*shape, 3), dtype=np.uint8)
    usable = hit & matched[np.clip(face, 0, matched.size - 1)]
    if not usable.any():
        return image, 0.0, float("nan")
    index = face[usable]
    point = origins[usable] + distance[usable, None] * flat[usable]
    triangle = surface.triangles[tile_triangle[index]]
    weights = np.clip(barycentric(triangle, point), 0.0, 1.0)
    weights /= np.maximum(weights.sum(axis=1, keepdims=True), 1e-30)
    uv = np.einsum("ij,ijk->ik", weights, surface.uv[tile_triangle[index]])
    patch = surface.patch[tile_triangle[index]]
    colours = np.zeros((usable.sum(), 3), dtype=np.uint8)
    texel_area = np.zeros(usable.sum())
    for patch_id in np.unique(patch):
        rows = patch == patch_id
        atlas = surface.patches[int(patch_id)]
        height, width = atlas.shape[0], atlas.shape[1]
        x = np.clip((uv[rows, 0] * width).astype(np.int64), 0, width - 1)
        y = np.clip((uv[rows, 1] * height).astype(np.int64), 0, height - 1)
        colours[rows] = atlas[y, x, :3]
        texel_area[rows] = 1.0 / max(height * width, 1)
    flat_image = image.reshape(-1, 3)
    flat_image[usable] = colours
    # Ground sample distance of the texture at this crop, from the texel density
    # of the triangles the crop actually landed on rather than a scene average.
    area = 0.5 * np.linalg.norm(np.cross(triangle[:, 1] - triangle[:, 0], triangle[:, 2] - triangle[:, 0]), axis=1)
    texels = np.array([surface.patches[int(p)].shape[0] * surface.patches[int(p)].shape[1] for p in patch])
    uv_area = _uv_area(surface.uv[tile_triangle[index]]) * texels
    density = uv_area / np.maximum(area, 1e-12)
    gsd = float(np.median(1.0 / np.sqrt(np.maximum(density, 1e-12))))
    return flat_image.reshape(*shape, 3), float(usable.mean()), gsd


def _uv_area(uv: np.ndarray) -> np.ndarray:
    a, b, c = uv[:, 0], uv[:, 1], uv[:, 2]
    return 0.5 * np.abs((b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (c[:, 0] - a[:, 0]) * (b[:, 1] - a[:, 1]))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=pathlib.Path, default=ROOT / "outputs" / "material_vlm")
    parser.add_argument("--size", type=int, default=384)
    parser.add_argument("--stride", type=int, default=128)
    parser.add_argument("--min-building-fraction", type=float, default=0.9)
    parser.add_argument("--per-view", type=int, default=4)
    parser.add_argument("--per-wall", type=int, default=5)
    parser.add_argument("--per-patch", type=int, default=2)
    parser.add_argument("--patch-separation-m", type=float, default=6.0)
    parser.add_argument("--crop-radius-m", type=float, default=130.0)
    parser.add_argument("--max-range-m", type=float, default=90.0)
    args = parser.parse_args()

    out = args.out
    (out / "crops").mkdir(parents=True, exist_ok=True)

    document = json.loads(SEMANTICS.read_text())
    labels_by_name = {int(k): v for k, v in document["entity_id2label"].items()}
    building_id = next(k for k, v in labels_by_name.items() if v == "Building")

    pose = json.loads(POSE.read_text())
    from semantic_twin.pano_geometry import panorama_to_world_matrix

    rotation = panorama_to_world_matrix(
        float(pose["heading_deg"]),
        pitch_deg=float(pose.get("pitch_correction_deg", 0.0)),
        roll_deg=float(pose.get("roll_correction_deg", 0.0)),
    )
    camera = np.asarray(pose["position_enu_m"], dtype=np.float64)

    geometry = MitsubaGeometry(MESH)
    areas = geometry.face_areas()
    face_class = classify_faces(geometry.vertices, geometry.faces, GROUND_DATUM_M)

    surface = load_tile_surface(args.crop_radius_m)
    from semantic_twin.vision.tiles import match_support_faces

    match = match_support_faces(geometry.vertices[geometry.faces], surface)
    print(f"tile match {match.report['matched_fraction']:.4f}, residual {match.report['median_residual_m']:.2e} m")

    views = {view.name: view for view in inference_views()}
    candidates: list[dict[str, Any]] = []

    for name in sorted(views):
        if not name.startswith("h+00") and not name.startswith("h+45"):
            continue
        labels_path = VIEWS / f"{name}_labels.npy"
        image_path = VIEWS / f"{name}.jpg"
        if not labels_path.exists() or not image_path.exists():
            continue
        labels = np.load(labels_path)
        picked = spread_pick(
            building_windows(
                labels,
                building_id,
                size=args.size,
                stride=args.stride,
                minimum_fraction=args.min_building_fraction,
            ),
            limit=args.per_view,
            separation=args.size,
        )
        for row, column, fraction in picked:
            local = sub_view_directions(views[name], row, column, args.size, labels.shape[0])
            directions = local @ rotation.T
            flat = directions.reshape(-1, 3)
            hit, distance, normal, face = geometry.intersect(np.broadcast_to(camera, flat.shape), flat)
            good = hit & (distance < args.max_range_m) & (face_class[np.clip(face, 0, face_class.size - 1)] == 1)
            if good.mean() < 0.6:
                continue
            points = np.broadcast_to(camera, flat.shape)[good] + distance[good, None] * flat[good]
            mean_normal = normal[good].mean(axis=0)
            mean_normal /= max(np.linalg.norm(mean_normal), 1e-12)
            candidates.append(
                {
                    "crop_id": f"{name}_r{row:04d}_c{column:04d}",
                    "view": name,
                    "row": row,
                    "column": column,
                    "fraction": fraction,
                    "directions": directions,
                    "faces": np.unique(face[good]),
                    "normal": mean_normal,
                    "offset": float(np.median(points @ mean_normal)),
                    "centroid": points.mean(axis=0),
                    "range_m": float(np.median(distance[good])),
                    "incidence_deg": float(
                        np.median(
                            np.degrees(
                                np.arccos(np.clip(np.abs(np.einsum("ij,ij->i", flat[good], normal[good])), 0.0, 1.0))
                            )
                        )
                    ),
                    "image_path": image_path,
                }
            )

    # Selection. Crops are capped per physical patch and per wall so that one
    # long facade seen from four overlapping views does not become half the
    # sample. Two crops per patch is deliberate rather than one: a second look at
    # the same square metre from a different view is the only cross view repeat
    # available, and the calibration harness has nothing to score without it.
    candidates.sort(key=lambda item: -item["fraction"])
    walls: list[tuple[np.ndarray, float]] = []
    patches: list[np.ndarray] = []
    patch_count: dict[int, int] = {}
    wall_count: dict[str, int] = {}
    records: list[Crop] = []
    images: dict[str, np.ndarray] = {}

    patch_wall: dict[int, str] = {}
    for item in candidates:
        # The patch is the primary grouping, because it is the one the
        # calibration harness needs: two crops in a patch are two looks at the
        # same square metres. The wall is derived from the patch rather than
        # clustered independently, so a patch can never straddle two walls.
        patch = None
        for index, centre in enumerate(patches):
            if float(np.linalg.norm(centre - item["centroid"])) < args.patch_separation_m:
                patch = index
                break
        if patch is None:
            patches.append(item["centroid"])
            patch = len(patches) - 1
        if patch in patch_wall:
            wall_name = patch_wall[patch]
        else:
            group = None
            for index, (wall_normal, wall_offset) in enumerate(walls):
                if float(wall_normal @ item["normal"]) > 0.94 and abs(wall_offset - item["offset"]) < 4.0:
                    group = index
                    break
            if group is None:
                walls.append((item["normal"], item["offset"]))
                group = len(walls) - 1
            wall_name = f"wall_{group:02d}"
            patch_wall[patch] = wall_name
        if wall_count.get(wall_name, 0) >= args.per_wall:
            continue
        if patch_count.get(patch, 0) >= args.per_patch:
            continue
        patch_count[patch] = patch_count.get(patch, 0) + 1
        wall_count[wall_name] = wall_count.get(wall_name, 0) + 1

        crop_id = item["crop_id"]
        if item["view"] not in images:
            with Image.open(item["image_path"]) as source:
                images[item["view"]] = np.asarray(source.convert("RGB"))
        rgb = images[item["view"]]
        row, column = item["row"], item["column"]
        Image.fromarray(rgb[row : row + args.size, column : column + args.size]).save(
            out / "crops" / f"{crop_id}_panorama.png"
        )
        texture_crop, covered, gsd = render_texture(
            camera, item["directions"], geometry, surface, match.tile_triangle, match.matched
        )
        Image.fromarray(texture_crop).save(out / "crops" / f"{crop_id}_texture.png")
        np.save(out / "crops" / f"{crop_id}_faces.npy", item["faces"])
        records.append(
            Crop(
                crop_id=crop_id,
                view=item["view"],
                row=row,
                column=column,
                size=args.size,
                building_fraction=item["fraction"],
                wall_group=wall_name,
                faces=int(item["faces"].size),
                face_area_m2=float(areas[item["faces"]].sum()),
                range_median_m=item["range_m"],
                incidence_median_deg=item["incidence_deg"],
                normal_enu=tuple(float(x) for x in item["normal"]),
                plane_offset_m=item["offset"],
                centroid_enu=tuple(float(x) for x in item["centroid"]),
                patch=f"patch_{patch:02d}",
                texture_pixel_fraction=covered,
                texture_gsd_m=gsd,
            )
        )
        print(
            f"{crop_id}  {wall_name}  patch_{patch:02d}  {item['faces'].size} faces  "
            f"{item['range_m']:.1f} m  {item['incidence_deg']:.0f} deg  texture {covered:.2f}"
        )

    manifest = {
        "generator": "build_facade_crops.py",
        "mesh": str(MESH),
        "tiles": str(TILES),
        "panorama_pose": str(POSE),
        "tile_match": match.report,
        "crop_size_px": args.size,
        "min_building_fraction": args.min_building_fraction,
        "max_range_m": args.max_range_m,
        "walls": len(walls),
        "crops": [record.as_dict() for record in records],
    }
    (out / "crops.json").write_text(json.dumps(manifest, indent=2))
    print(f"\n{len(records)} crops over {len(walls)} walls -> {out / 'crops.json'}")


if __name__ == "__main__":
    main()
