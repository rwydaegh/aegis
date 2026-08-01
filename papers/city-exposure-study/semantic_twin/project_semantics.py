"""Project panorama semantics onto the first visible photogrammetry triangles.

Run in Blender so its BVH settles visibility::

    ~/blender-4.5/blender -b -P project_semantics.py -- \
      --mesh ../hybrid_twin/scenes/photo/meshes/photogrammetry.ply \
      --semantics data/panoramas/korenmarkt/semantics/panorama_semantics.npz \
      --semantics-json data/panoramas/korenmarkt/semantics/semantics.json \
      --pose data/panoramas/korenmarkt/alignment/pose_aligned.json \
      --out outputs/korenmarkt_mesh

Only surface classes paint the source mesh. People, vehicles, bollards and other
object detections are counted as unmodelled observations instead of incorrectly
painting the background triangle hit by their camera ray.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from semantic_twin.export import compact, scene_xml, write_ply  # noqa: E402

OBJECT_WORDS = {
    "person",
    "rider",
    "bicyclist",
    "motorcyclist",
    "animal",
    "bird",
    "car",
    "truck",
    "bus",
    "vehicle",
    "motorcycle",
    "bicycle",
    "boat",
    "caravan",
    "trailer",
    "bollard",
    "bench",
    "trash can",
    "traffic light",
    "traffic sign",
    "street light",
    "pole",
    "fire hydrant",
    "bike rack",
}

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


def panorama_rotation(heading_deg: float, pitch_deg: float, roll_deg: float) -> np.ndarray:
    def axis_angle(axis, angle_deg):
        axis = np.asarray(axis, dtype=float)
        axis /= np.linalg.norm(axis)
        x, y, z = axis
        angle = math.radians(angle_deg)
        c, s, c1 = math.cos(angle), math.sin(angle), 1.0 - math.cos(angle)
        return np.array(
            [
                [c + x * x * c1, x * y * c1 - z * s, x * z * c1 + y * s],
                [y * x * c1 + z * s, c + y * y * c1, y * z * c1 - x * s],
                [z * x * c1 - y * s, z * y * c1 + x * s, c + z * z * c1],
            ]
        )

    heading = math.radians(heading_deg)
    right = np.array([math.cos(heading), -math.sin(heading), 0.0])
    forward = np.array([math.sin(heading), math.cos(heading), 0.0])
    up = np.array([0.0, 0.0, 1.0])
    base = np.column_stack([right, forward, up])
    return base @ axis_angle((0, 1, 0), roll_deg) @ axis_angle((1, 0, 0), pitch_deg)


def mesh_arrays(obj) -> tuple[np.ndarray, np.ndarray]:
    mesh = obj.data
    mesh.calc_loop_triangles()
    vertices = np.empty(len(mesh.vertices) * 3, dtype=np.float64)
    mesh.vertices.foreach_get("co", vertices)
    vertices = vertices.reshape(-1, 3)
    matrix = np.array(obj.matrix_world)
    vertices = vertices @ matrix[:3, :3].T + matrix[:3, 3]
    faces = np.empty(len(mesh.loop_triangles) * 3, dtype=np.int64)
    mesh.loop_triangles.foreach_get("vertices", faces)
    return vertices, faces.reshape(-1, 3)


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


def is_object(label: str) -> bool:
    text = label.casefold()
    return any(word in text for word in OBJECT_WORDS)


def visible_faces(
    vertices: np.ndarray,
    faces: np.ndarray,
    camera: np.ndarray,
    candidates: np.ndarray,
) -> np.ndarray:
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
    rotation = panorama_rotation(
        float(pose["heading_deg"]),
        float(pose.get("pitch_correction_deg", 0.0)),
        float(pose.get("roll_correction_deg", 0.0)),
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

    assigned_material = np.zeros(len(faces), dtype=np.uint16)
    assigned_material[visible] = face_material[visible]
    groups: dict[str, np.ndarray] = {}
    shapes = []
    counts = {}
    for material_id in np.unique(assigned_material):
        name = material_names.get(int(material_id), "unknown")
        selection = assigned_material == material_id
        if not np.any(selection):
            continue
        itu = RF_TO_ITU.get(name, "concrete")
        mesh_id = f"semantic_{name}".replace(" ", "_")
        compact_vertices, compact_faces = compact(vertices, faces[selection])
        relative = f"meshes/{mesh_id}.ply"
        write_ply(args.out / relative, compact_vertices, compact_faces)
        shapes.append((mesh_id, relative, itu))
        counts[name] = int(selection.sum())
        groups[name] = selection

    comments = [
        "Street View semantic projection onto the Inhouse photogrammetry mesh.",
        "Only first-visible surface triangles receive panorama labels.",
        "Object classes are not painted onto background geometry.",
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
        "visible_labelled_faces": int(visible.sum()),
        "hidden_or_unresolved_faces": int((~visible).sum()),
        "face_groups": counts,
        "unmodelled_object_pixel_counts": object_pixels,
        "object_policy": "retain as observations; never paint their background hit",
        "material_policy": "provisional RF hints mapped to nearest installed ITU material",
    }
    (args.out / "projection_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"[project] {visible.sum()}/{len(faces)} first-visible faces labelled")
    print(f"[project] -> {args.out / 'scene.xml'}")


if __name__ == "__main__":
    main()
