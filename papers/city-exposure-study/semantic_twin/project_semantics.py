"""Label the support mesh from one panorama and export it as a Sionna RT scene.

This is the only writer of ``scene.xml`` in the repository. It takes the
photogrammetry triangles as they come, samples the panorama once per face
centroid, groups the faces by RF material, and emits one PLY per material plus
the XML that binds each to an ITU radio material. Everything downstream that
wants a traceable scene comes out of here.

The per-face sampling is coarse on purpose: a face gets exactly one label, so
semantic boundaries land on the photogrammetry triangulation rather than on the
image. ``archive/scripts/project_pixel_semantics.py`` and the fishnet package are the
boundary-faithful paths. Neither of them exports a scene yet, which is why this
module stays.

Run in Blender so its BVH settles visibility::

    ~/blender-4.5/blender -b -P project_semantics.py -- \
      --mesh data/geometry/korenmarkt/inhouse_leaf_130m.ply \
      --semantics data/panoramas/korenmarkt/semantics/panorama_semantics.npz \
      --semantics-json data/panoramas/korenmarkt/semantics/semantics.json \
      --pose data/panoramas/korenmarkt/alignment/pose_aligned.json \
      --out outputs/korenmarkt_mesh

Only surface classes paint the source mesh. People, vehicles, bollards and other
object detections are counted as unmodelled observations instead of incorrectly
painting the background triangle hit by their camera ray.

Geometry that no panorama ray ever reached is not given an RF material. It
carries the explicit :data:`UNOBSERVED_MATERIAL` sentinel, is excluded from
``scene.xml``, and is counted separately in the manifest.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from semantic_twin.blender_mesh import mesh_arrays  # noqa: E402
from semantic_twin.export import compact, scene_xml, write_ply  # noqa: E402
from semantic_twin.pano_geometry import panorama_to_world_matrix  # noqa: E402
from semantic_twin.vision.vocabulary import is_object  # noqa: E402

# Material id 0 is the real ``unknown`` class, which a segmenter can genuinely
# assign to an observed surface. Never-observed geometry therefore needs its own
# out-of-band value so a consumer can tell "seen, unclassified" from "not seen".
UNOBSERVED_MATERIAL = int(np.iinfo(np.uint16).max)

RF_TO_ITU = {
    "unknown": "concrete",
    "unknown_building": "concrete",
    "unknown_wall": "concrete",
    "unknown_furniture": "wood",
    "asphalt": "medium_dry_ground",
    "road_paint": "concrete",
    "concrete": "concrete",
    "soil": "medium_dry_ground",
    "snow": "wet_ground",
    "vegetation": "wood",
    "water": "wet_ground",
    "metal": "metal",
    "vehicle_composite": "metal",
    "human_tissue": "concrete",
    "animal_tissue": "concrete",
}


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh", type=pathlib.Path, required=True)
    parser.add_argument("--semantics", type=pathlib.Path, required=True)
    parser.add_argument("--semantics-json", type=pathlib.Path, required=True)
    parser.add_argument("--pose", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--min-confidence", type=float, default=0.35)
    return parser.parse_args(argv)


def sample_panorama(
    directions: np.ndarray,
    rotation: np.ndarray,
    entity: np.ndarray,
    material: np.ndarray,
    confidence: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    local = directions @ rotation
    local /= np.linalg.norm(local, axis=1, keepdims=True)
    yaw = np.arctan2(local[:, 0], local[:, 1])
    pitch = np.arcsin(np.clip(local[:, 2], -1.0, 1.0))
    u = (yaw / (2.0 * np.pi) + 0.5) % 1.0
    v = np.clip(0.5 - pitch / np.pi, 0.0, 1.0 - np.finfo(float).eps)
    x = np.floor(u * entity.shape[1]).astype(int)
    y = np.floor(v * entity.shape[0]).astype(int)
    return entity[y, x], material[y, x], confidence[y, x]


def assign_materials(face_material: np.ndarray, visible: np.ndarray) -> np.ndarray:
    """Return per-face material ids with an explicit never-observed sentinel."""
    assigned = np.full(len(visible), UNOBSERVED_MATERIAL, dtype=np.uint16)
    assigned[visible] = np.asarray(face_material)[visible]
    return assigned


def material_groups(assigned_material: np.ndarray, material_names: dict[int, str]) -> dict[str, np.ndarray]:
    """Group observed faces by material name, leaving unobserved faces out."""
    groups: dict[str, np.ndarray] = {}
    for material_id in np.unique(assigned_material):
        if int(material_id) == UNOBSERVED_MATERIAL:
            continue
        name = material_names.get(int(material_id), "unknown")
        selection = assigned_material == material_id
        groups[name] = selection if name not in groups else groups[name] | selection
    return groups


def visible_faces(
    vertices: np.ndarray,
    faces: np.ndarray,
    camera: np.ndarray,
    candidates: np.ndarray,
) -> np.ndarray:
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree

    vectors = [Vector(v) for v in vertices]
    bvh = BVHTree.FromPolygons(vectors, faces.tolist(), all_triangles=True)
    centroids = vertices[faces].mean(axis=1)
    visible = np.zeros(len(faces), dtype=bool)
    origin = Vector(camera)
    indices = np.flatnonzero(candidates)
    for done, face_id in enumerate(indices, 1):
        delta = centroids[face_id] - camera
        distance = float(np.linalg.norm(delta))
        if distance <= 1e-6:
            continue
        _location, _normal, hit_id, _distance = bvh.ray_cast(origin, Vector(delta / distance), distance + 0.05)
        visible[face_id] = hit_id == int(face_id)
        if done % 50000 == 0:
            print(f"[project] visibility {done}/{len(indices)}", flush=True)
    return visible


def main() -> None:
    import bpy

    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "meshes").mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.ply_import(filepath=str(args.mesh.resolve()))
    obj = bpy.context.object
    vertices, faces = mesh_arrays(obj)
    centroids = vertices[faces].mean(axis=1)

    semantic = np.load(args.semantics)
    entity = semantic["entity"]
    material = semantic["material_hint"]
    confidence = semantic["confidence"]
    document = json.loads(args.semantics_json.read_text())
    entity_names = {int(k): v for k, v in document["entity_id2label"].items()}
    material_names = {int(k): v for k, v in document["material_id2label"].items()}
    pose = json.loads(args.pose.read_text())
    camera = np.asarray(pose["position_enu_m"], dtype=float)
    rotation = panorama_to_world_matrix(
        float(pose["heading_deg"]),
        pitch_deg=float(pose.get("pitch_correction_deg", 0.0)),
        roll_deg=float(pose.get("roll_correction_deg", 0.0)),
    )

    directions = centroids - camera
    distance = np.linalg.norm(directions, axis=1)
    directions /= np.maximum(distance[:, None], 1e-8)
    face_entity, face_material, face_confidence = sample_panorama(directions, rotation, entity, material, confidence)
    object_ids = {class_id for class_id, name in entity_names.items() if is_object(name)}
    object_mask = np.isin(face_entity, list(object_ids))
    sky_ids = {class_id for class_id, name in entity_names.items() if name.casefold() == "sky"}
    sky_mask = np.isin(face_entity, list(sky_ids))
    candidates = (~object_mask) & (~sky_mask) & (face_confidence >= args.min_confidence)
    visible = visible_faces(vertices, faces, camera, candidates)

    assigned_material = assign_materials(face_material, visible)
    groups = material_groups(assigned_material, material_names)
    shapes = []
    counts = {}
    for name, selection in groups.items():
        itu = RF_TO_ITU.get(name, "concrete")
        mesh_id = f"semantic_{name}".replace(" ", "_")
        compact_vertices, compact_faces = compact(vertices, faces[selection])
        relative = f"meshes/{mesh_id}.ply"
        write_ply(args.out / relative, compact_vertices, compact_faces)
        shapes.append((mesh_id, relative, itu))
        counts[name] = int(selection.sum())

    comments = [
        "Street View semantic projection onto the Inhouse photogrammetry mesh.",
        "Only first-visible surface triangles receive panorama labels.",
        "Object classes are not painted onto background geometry.",
        "Faces no panorama ray reached are omitted entirely and carry no ITU material.",
        "ITU materials are provisional mappings from material hints, not calibrated values.",
    ]
    (args.out / "scene.xml").write_text(scene_xml(shapes, comments=comments))
    np.savez_compressed(
        args.out / "face_semantics.npz",
        entity=face_entity,
        material_hint=face_material,
        confidence=face_confidence,
        visible=visible,
        assigned_material=assigned_material,
    )
    object_pixels = {
        entity_names[class_id]: int((entity == class_id).sum())
        for class_id in sorted(object_ids)
        if np.any(entity == class_id)
    }
    manifest = {
        "source_mesh": str(args.mesh),
        "source_faces": len(faces),
        "camera_enu_m": camera.tolist(),
        "observed_faces": int(visible.sum()),
        "unobserved_faces": int((~visible).sum()),
        "exported_faces": int(sum(counts.values())),
        "unobserved_material_id": UNOBSERVED_MATERIAL,
        "observed_face_groups": counts,
        "unmodelled_object_pixel_counts": object_pixels,
        "object_policy": "retain as observations; never paint their background hit",
        "unobserved_policy": "no RF material, no PLY, no scene.xml shape",
        "material_policy": "provisional RF hints mapped to nearest installed ITU material",
    }
    (args.out / "projection_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"[project] {visible.sum()}/{len(faces)} first-visible faces labelled, {(~visible).sum()} left unobserved")
    print(f"[project] -> {args.out / 'scene.xml'}")


if __name__ == "__main__":
    main()
