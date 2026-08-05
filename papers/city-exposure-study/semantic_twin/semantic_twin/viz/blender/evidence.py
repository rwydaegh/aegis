"""The image evidence layers. Every one of these is skipped when the payload lacks it.

These are the layers that make the file a semantic twin rather than a textured
mesh: what the segmenter said, how sure it was, what the cutter refused and why,
what the depth gate threw out, where the panoramas stood and who was standing in
front of them. A site with no panorama builds none of them and opens exactly as
fast as it did before.

They are optional in a specific way that is worth naming. The test is whether the
arrays are in the payload, not whether a flag was passed, so a site acquires the
layer the moment its data exists and nothing has to be told.
"""

from __future__ import annotations

import json
from typing import Any

import bpy
import numpy as np

from .payload import has, octahedra, unit_sphere
from .scene import (
    assign,
    attach_face_colour,
    attach_point_colour,
    attach_values,
    build_mesh,
    emissive_material,
    layered,
    point_cloud,
    scalar_layers,
)
from .style import categorical_colours, colour_ramp, log_ramp

#: Which fishnet columns become colour layers, and the range each is shaded on. A
#: fixed range where the quantity has one, so two taxonomies and two sites are
#: comparable, and a measured range where it does not.
FISHNET_LAYERS: dict[str, tuple[float, float] | None] = {
    "confidence": (0.0, 1.0),
    "top_probability": (0.0, 1.0),
    # Clipped at half a bit rather than at the maximum. Five sixths of the faces
    # sit at exactly zero, so a range set by the tail leaves the whole surface in
    # the dark end of the ramp and the mixed faces, which are the point of the
    # layer, invisible. The exact value is on the same object.
    "entropy_bits": (0.0, 0.5),
    "visible_fraction": (0.0, 1.0),
    "range_m": None,
}

#: Colours for the mesh against monocular depth verdict, matching the order in
#: ``compare_mesh_depth.DECISIONS``. Kept in that order rather than looked up so
#: the blend does not need the module.
DECISION_TINT = np.array(
    [
        [0.35, 0.35, 0.35],  # no mesh
        [0.08, 0.75, 0.35],  # agree
        [0.96, 0.75, 0.12],  # uncertain
        [0.92, 0.20, 0.16],  # something stands in front of the mesh
        [0.51, 0.22, 0.75],  # the mesh is implausibly in front
        [0.14, 0.59, 0.96],  # person or vehicle, handled by the body layer
        [0.55, 0.55, 0.55],  # depth evidence withheld, the mesh decides alone
    ]
)

#: Colour per rejection reason code, indexed from one as the reasons are.
REFUSAL_TINT: dict[str, tuple[float, float, float]] = {
    "occluded_by_support_mesh": (0.30, 0.34, 0.55),
    "transient_object": (0.14, 0.59, 0.96),
    "clutter_in_front": (0.92, 0.20, 0.16),
    "mesh_or_pose_conflict": (0.51, 0.22, 0.75),
    "not_support_surface": (0.62, 0.58, 0.30),
    "below_minimum_area": (0.40, 0.40, 0.40),
}

#: Verdict colours for a registered pose, in the order of the exporter's codes.
VERDICT_TINT = np.array([[0.10, 0.80, 0.40], [0.98, 0.72, 0.15], [0.95, 0.18, 0.18]])

#: Manifest evidence records represented by each Blender collection. The
#: collection names stay stable across sites, including sites where a source
#: artifact was missing at export time.
COLLECTION_LAYERS: dict[str, tuple[str, ...]] = {
    "semantics": ("fishnet_vistas", "fishnet_sam3"),
    "evidence": ("support_evidence",),
    "refused": ("rejected",),
    "depth": ("depth_mesh", "depth_monocular"),
    "panoramas": ("registration",),
    "bodies": ("bodies",),
}


def annotate_collection_status(groups: dict[str, Any], manifest: dict) -> None:
    """Put an explicit build result on every optional evidence collection."""
    statuses = manifest.get("evidence", {}).get("layer_status", {})
    for key, layer_names in COLLECTION_LAYERS.items():
        group = groups[key]
        records = {name: statuses[name] for name in layer_names if name in statuses}
        populated = len(group.objects) > 0
        incomplete = any(record.get("status") != "built" for record in records.values())
        if populated and incomplete:
            group["status"] = "built_partial"
        elif populated:
            group["status"] = "built"
        else:
            group["status"] = "empty"
        group["layers"] = json.dumps(records, default=str)
        reasons = [str(record["reason"]) for record in records.values() if record.get("reason")]
        if reasons:
            group["reason"] = "; ".join(reasons)
        elif not populated:
            group["reason"] = "payload contains no drawable arrays for this evidence collection"


def build_fishnet(payload: Any, manifest: dict, taxonomy: str, into: Any) -> dict[str, int] | None:
    """One surface set per taxonomy, carrying what the segmenter said about each face.

    The class layer is a lookup and is drawn from a palette, not a ramp. Every other
    layer is a measured scalar and is drawn on inferno over a stated range, which is
    on the object. The face count is the cutter's own, so this is the surface the
    propagation stage would bind materials to, not a redrawing of it.
    """
    key = f"fishnet_{taxonomy}"
    if not has(payload, f"{key}_vertices"):
        return None
    record = manifest.get("evidence", {}).get(key, {})
    obj = build_mesh(f"fishnet_{taxonomy}", payload[f"{key}_vertices"], payload[f"{key}_faces"], into)
    classes = payload[f"{key}_class"]
    attach_face_colour(obj, "class", categorical_colours(classes, payload[f"{key}_class_rgb"]))
    attach_values(obj, "value_class", classes, "FACE")
    columns = {name: payload[f"{key}_{name}"] for name in FISHNET_LAYERS if f"{key}_{name}" in payload.files}
    ranges = {
        name: span for name, span in FISHNET_LAYERS.items() if span is not None and f"{key}_{name}" in payload.files
    }
    scalar_layers(obj, columns, "FACE", ranges=ranges)
    for extra in ("area_m2", "solid_angle_sr", "pixel_support", "view"):
        if f"{key}_{extra}" in payload.files:
            attach_values(obj, f"value_{extra}", payload[f"{key}_{extra}"], "FACE")
    assign(obj, emissive_material(f"fishnet_{taxonomy}", "class"))
    obj["taxonomy"] = taxonomy
    obj["class_names"] = record.get("class_names", [])
    obj["views"] = record.get("views", [])
    obj["cut_by"] = "semantic_twin/fishnet.py, projected support triangles cut at semantic island boundaries"
    layered(obj, ("class", *columns), "class")
    return {"faces": int(payload[f"{key}_faces"].shape[0])}


def build_support_evidence(payload: Any, manifest: dict, into: Any) -> dict[str, float] | None:
    """Every support triangle a view considered, clean pixels against withheld ones.

    Four withholding channels rather than one total, because they do not mean the
    same thing. A transient pixel is deferred to the body layer and will come back
    as a person. A clutter pixel is geometry the tiles never captured and is simply
    gone. Reading them as one number is what this layer exists to stop.
    """
    if not has(payload, "support_evidence_vertices"):
        return None
    record = manifest.get("evidence", {}).get("support_evidence", {})
    obj = build_mesh("support_evidence", payload["support_evidence_vertices"], payload["support_evidence_faces"], into)
    attach_face_colour(
        obj, "class", categorical_colours(payload["support_evidence_class"], payload["support_evidence_class_rgb"])
    )
    attach_values(obj, "value_class", payload["support_evidence_class"], "FACE")
    scalar_layers(
        obj, {"confidence": payload["support_evidence_confidence"]}, "FACE", ranges={"confidence": (0.0, 1.0)}
    )
    withheld = np.zeros(payload["support_evidence_class"].size)
    counted = ("clean", "transient", "clutter", "occluded", "other")
    for name in counted:
        values = payload[f"support_evidence_{name}_px"]
        attach_values(obj, f"value_{name}_px", values, "FACE")
        rgba, low, high = log_ramp(values)
        attach_face_colour(obj, f"{name}_px", rgba)
        obj[f"{name}_px_log10_range"] = [low, high]
        if name != "clean":
            withheld += values
    total = withheld + payload["support_evidence_clean_px"]
    fraction = np.divide(withheld, total, out=np.zeros(total.size), where=total > 0.0)
    scalar_layers(obj, {"withheld_fraction": fraction}, "FACE", ranges={"withheld_fraction": (0.0, 1.0)})
    assign(obj, emissive_material("support_evidence", "class"))
    obj["grouping"] = json.dumps(record.get("grouping", {}))
    obj["reading"] = "clean_px is what was painted, the other four are what was refused and why"
    layered(obj, ("class", "confidence", *(f"{name}_px" for name in counted), "withheld_fraction"), "class")
    return {"triangles": int(payload["support_evidence_faces"].shape[0])}


def build_refused(payload: Any, manifest: dict, into: Any) -> dict[str, int] | None:
    """The candidate surface the cutter refused, one object per reason.

    Separate objects rather than one object with a reason layer, because the
    question a reader has is what a single reason removed, and that is answered by
    switching an object off. The transient set and the clutter set are the two that
    matter: one comes back as a body and the other never comes back.
    """
    if not has(payload, "rejected_vertices"):
        return None
    record = manifest.get("evidence", {}).get("rejected", {})
    names = record.get("reason_names", [])
    reasons = payload["rejected_reason"]
    faces = payload["rejected_faces"]
    vertices = payload["rejected_vertices"]
    areas = payload["rejected_image_area_px"]
    counts: dict[str, int] = {}
    for code in np.unique(reasons):
        label = names[int(code) - 1] if 0 < int(code) <= len(names) else f"reason_{int(code)}"
        keep = np.flatnonzero(reasons == code)
        kept = faces[keep]
        used, remapped = np.unique(kept, return_inverse=True)
        obj = build_mesh(f"refused_{label}", vertices[used], remapped.reshape(kept.shape), into)
        rgba, low, high = log_ramp(areas[keep])
        attach_face_colour(obj, "image_area_px", rgba)
        attach_values(obj, "value_image_area_px", areas[keep], "FACE")
        tint = REFUSAL_TINT.get(label, (0.5, 0.5, 0.5))
        attach_face_colour(obj, "reason", np.tile((*tint, 1.0), (kept.shape[0], 1)))
        assign(obj, emissive_material(f"refused_{label}", "reason"))
        obj["reason"] = label
        obj["image_area_px_total"] = float(areas[keep].sum())
        obj["image_area_px_log10_range"] = [low, high]
        layered(obj, ("reason", "image_area_px"), "reason")
        counts[label] = int(kept.shape[0])
    return counts


def build_depth(payload: Any, manifest: dict, into: Any, *, radius: float) -> dict[str, int] | None:
    """Two clouds: the first hit the twin uses, and the depth the gate refused.

    They are deliberately in the same collection and the same units. The point of
    drawing the refused one is that the refusal stops being a line in a manifest: at
    a fitted scale of 0.41 the whole square sits at four tenths of its range, inside
    the mesh, and no reader needs the plausibility band explained after seeing it.
    """
    made: dict[str, int] = {}
    camera = payload["evidence_camera"].astype(np.float64) if "evidence_camera" in payload.files else None
    for kind, tint_channel in (("mesh", "decision"), ("monocular", "decision")):
        key = f"depth_{kind}"
        if not has(payload, f"{key}_points"):
            continue
        points = payload[f"{key}_points"].astype(np.float64)
        material = emissive_material(f"{key}_cloud", "decision")
        obj = point_cloud(f"depth_{kind}", points, into, radius=radius, material=material)
        attach_point_colour(obj, "decision", categorical_colours(payload[f"{key}_decision"], DECISION_TINT))
        attach_values(obj, "value_decision", payload[f"{key}_decision"].astype(np.int32), "POINT")
        columns: dict[str, np.ndarray] = {}
        if camera is not None:
            columns["range_m"] = np.linalg.norm(points - camera, axis=1)
        if f"{key}_z_score" in payload.files:
            columns["z_score"] = np.clip(payload[f"{key}_z_score"], -6.0, 6.0)
        if f"{key}_mesh_range_m" in payload.files and camera is not None:
            columns["mesh_minus_this_m"] = payload[f"{key}_mesh_range_m"] - columns["range_m"]
        scalar_layers(obj, columns, "POINT", ranges={"z_score": (-6.0, 6.0)})
        attach_values(obj, "value_view", payload[f"{key}_view"].astype(np.int32), "POINT")
        record = manifest.get("evidence", {}).get(key, {})
        obj["meaning"] = record.get("meaning", "")
        obj["decisions"] = json.dumps(
            record.get("decisions") or manifest.get("evidence", {}).get("depth_mesh", {}).get("decisions")
        )
        obj["stride_px"] = record.get("stride_px")
        if record.get("scale_plausibility") is not None:
            obj["scale_plausibility"] = json.dumps(record["scale_plausibility"].get("problems", []))
        layered(obj, (tint_channel, *columns), tint_channel)
        made[kind] = int(points.shape[0])
    return made or None


def build_panoramas(payload: Any, manifest: dict, into: Any, *, sigma_scale: float) -> int | None:
    """Every registered pose, as a camera you can look through, a marker and an ellipsoid.

    The camera is a real Blender camera at the solved rotation, so the view it saw is
    reproducible from inside the blend. The marker carries the verdict the sky
    conflict audit reached, which at Korenmarkt is three cameras standing inside the
    geometry out of thirteen, and no residual would have said so. The ellipsoid is
    the position block of the seed study covariance at one sigma, scaled by
    ``sigma_scale`` because one sigma here is a few centimetres and a few centimetres
    in a two hundred metre scene is nothing. The scale is on every ellipsoid as a
    property, so nobody reads it as a metre.
    """
    # Imported here rather than at module level: mathutils ships inside Blender and
    # is absent from the venv, and the pure geometry in this package is tested
    # outside Blender.
    import mathutils

    if "pano_position" not in payload.files:
        return None
    positions = payload["pano_position"].astype(np.float64)
    rotations = payload["pano_rotation"].astype(np.float64)
    sigmas = payload["pano_sigma_vectors"].astype(np.float64)
    verdict = payload["pano_verdict"]
    records = manifest.get("evidence", {}).get("registration", {}).get("poses", [])
    markers, faces = octahedra(positions, 0.9)
    marker = build_mesh("pano_markers", markers, faces, into)
    attach_face_colour(marker, "verdict", np.repeat(categorical_colours(verdict, VERDICT_TINT), 8, axis=0))
    attach_face_colour(
        marker, "sky_conflict", np.repeat(colour_ramp(payload["pano_sky_conflict"], 0.0, 1.0), 8, axis=0)
    )
    attach_face_colour(
        marker, "skyline_residual_deg", np.repeat(colour_ramp(payload["pano_residual_deg"], 0.0, 8.0), 8, axis=0)
    )
    assign(marker, emissive_material("pano_markers", "verdict"))
    marker["reading"] = manifest.get("evidence", {}).get("registration", {}).get("reading", "")
    marker["captures"] = [record.get("capture", "") for record in records]
    layered(marker, ("verdict", "sky_conflict", "skyline_residual_deg"), "verdict")

    sphere, sphere_faces = unit_sphere()
    blobs = [position + sigma_scale * (sphere @ sigmas[index].T) for index, position in enumerate(positions)]
    ellipsoid = build_mesh(
        "pano_uncertainty",
        np.concatenate(blobs),
        np.concatenate([sphere_faces + index * sphere.shape[0] for index in range(len(blobs))]),
        into,
    )
    attach_face_colour(
        ellipsoid, "verdict", np.repeat(categorical_colours(verdict, VERDICT_TINT), sphere_faces.shape[0], axis=0)
    )
    assign(ellipsoid, emissive_material("pano_uncertainty", "verdict"))
    ellipsoid["sigma_multiple_drawn"] = sigma_scale
    ellipsoid["reading"] = f"one sigma of the pose position, drawn {sigma_scale:g} times life size"
    layered(ellipsoid, ("verdict",), "verdict")

    for index, record in enumerate(records):
        rotation = rotations[index]
        # The pose rotation takes panorama-local right, forward and up to world. A
        # Blender camera looks down its own -Z with +Y up, so its columns are right,
        # up and backwards, which is the pose's columns with the last two swapped and
        # the new last one negated.
        basis = np.column_stack([rotation[:, 0], rotation[:, 2], -rotation[:, 1]])
        data = bpy.data.cameras.new(f"pano_{index:02d}")
        data.lens = 18.0
        data.clip_end = 400.0
        obj = bpy.data.objects.new(f"pano_{index:02d}", data)
        into.objects.link(obj)
        placed = np.eye(4)
        placed[:3, :3] = basis
        placed[:3, 3] = positions[index]
        obj.matrix_world = mathutils.Matrix([[float(value) for value in row] for row in placed])
        for field in ("capture", "skyline_residual_deg", "sky_with_mesh_hit_fraction", "position_sigma_m", "verdict"):
            if record.get(field) is not None:
                obj[field] = record[field]
    return int(positions.shape[0])


def build_bodies(payload: Any, manifest: dict, into: Any) -> int | None:
    """The SMPL-X bystanders, already in scene ENU, one object each.

    These are the people the transient mask cut out of the static surface. The
    fishnet leaves a hole where they stood and this layer is what fills it, which is
    the whole reason the occlusion budget separates deferred from absent. They have
    never been in a blend before and they carry no exposure, so the tint is flat and
    the numbers are properties.
    """
    if "body_layer_vertices" not in payload.files:
        return None
    vertices = payload["body_layer_vertices"].astype(np.float64)
    faces = payload["body_layer_faces"]
    records = manifest.get("evidence", {}).get("bodies", {}).get("records", [])
    material = emissive_material("bystander", None, (0.20, 0.62, 0.95))
    for index in range(vertices.shape[0]):
        record = records[index] if index < len(records) else {}
        obj = build_mesh(record.get("body_id", f"bystander_{index:02d}"), vertices[index], faces, into)
        assign(obj, material)
        for field in ("view", "stature_m", "placed_range_m", "range_source", "placement_provenance"):
            if record.get(field) is not None:
                obj[field] = record[field]
        if record.get("uncertainty"):
            obj["uncertainty"] = json.dumps(record["uncertainty"])
        obj["layer"] = "transient, never baked into the static semantic atlas"
    return int(vertices.shape[0])


def build_all(
    payload: Any, manifest: dict, collection: Any, *, point_radius_m: float, pose_sigma_scale: float
) -> dict[str, object]:
    """Every evidence layer the payload carries, keyed by what it is.

    Returns only the layers that were built. A site with no panorama gets an empty
    mapping rather than a mapping full of None, so the manifest line the blend
    carries reads as a list of what is in the file.
    """
    built: dict[str, object] = {}
    groups = {key: collection(key) for key in COLLECTION_LAYERS}
    semantics = groups["semantics"]
    for taxonomy in ("vistas", "sam3"):
        made = build_fishnet(payload, manifest, taxonomy, semantics)
        if made is not None:
            built[f"fishnet_{taxonomy}"] = made
    for key, value in (
        ("support_evidence", build_support_evidence(payload, manifest, groups["evidence"])),
        ("refused", build_refused(payload, manifest, groups["refused"])),
        ("depth", build_depth(payload, manifest, groups["depth"], radius=point_radius_m)),
        ("panoramas", build_panoramas(payload, manifest, groups["panoramas"], sigma_scale=pose_sigma_scale)),
        ("bodies", build_bodies(payload, manifest, groups["bodies"])),
    ):
        if value is not None:
            built[key] = value
    annotate_collection_status(groups, manifest)
    return built
