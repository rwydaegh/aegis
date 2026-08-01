"""Render first-hit projected semantic triangles from the recovered camera."""

from __future__ import annotations

import argparse
import colorsys
import json
import math
import pathlib
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from render_blender_alignment import camera_matrix, material, panorama_rotation, setup_scene


PREFERRED_COLOURS = {
    "building": (0.03, 0.64, 0.95, 1.0),
    "vegetation": (0.08, 0.82, 0.25, 1.0),
    "pedestrian area": (0.98, 0.65, 0.18, 1.0),
    "road": (0.46, 0.50, 0.56, 1.0),
    "on rails": (0.96, 0.86, 0.10, 1.0),
    "fence": (1.0, 0.30, 0.08, 1.0),
    "billboard": (0.96, 0.08, 0.65, 1.0),
    "rail track": (0.70, 0.24, 0.92, 1.0),
    "terrain": (0.55, 0.30, 0.10, 1.0),
}


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh", type=pathlib.Path, required=True)
    parser.add_argument("--face-semantics", type=pathlib.Path, required=True)
    parser.add_argument("--semantics-json", type=pathlib.Path, required=True)
    parser.add_argument("--pose", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--size", type=int, default=1024)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def mesh_arrays(obj: bpy.types.Object) -> tuple[np.ndarray, np.ndarray]:
    mesh = obj.data
    vertices = np.empty(len(mesh.vertices) * 3, dtype=np.float64)
    mesh.vertices.foreach_get("co", vertices)
    vertices = vertices.reshape(-1, 3)
    faces = np.empty(len(mesh.polygons) * 3, dtype=np.int64)
    mesh.polygons.foreach_get("vertices", faces)
    return vertices, faces.reshape(-1, 3)


def fallback_colour(class_id: int) -> tuple[float, float, float, float]:
    rgb = colorsys.hsv_to_rgb((class_id * 0.61803398875) % 1.0, 0.72, 0.95)
    return (*rgb, 1.0)


def main() -> None:
    args = arguments()
    args.out.mkdir(parents=True, exist_ok=True)
    scene = setup_scene(args.size)
    pose = json.loads(args.pose.read_text())
    labels = json.loads(args.semantics_json.read_text())["entity_id2label"]
    labels = {int(class_id): name for class_id, name in labels.items()}
    projection = np.load(args.face_semantics)
    visible = projection["visible"]
    entity = projection["entity"]

    bpy.ops.wm.ply_import(filepath=str(args.mesh.resolve()))
    source = bpy.context.object
    vertices, faces = mesh_arrays(source)
    if len(faces) != len(visible):
        raise RuntimeError(f"mesh has {len(faces)} faces but projection has {len(visible)}")
    source.hide_render = True

    visible_faces = faces[visible]
    visible_entity = entity[visible]
    used, inverse = np.unique(visible_faces, return_inverse=True)
    compact_vertices = vertices[used]
    compact_faces = inverse.reshape(-1, 3)
    projected_data = bpy.data.meshes.new("Projected Street View semantics")
    projected_data.from_pydata(compact_vertices.tolist(), [], compact_faces.tolist())
    projected_data.update()
    projected = bpy.data.objects.new("Projected Street View semantics", projected_data)
    bpy.context.collection.objects.link(projected)

    legend = []
    class_to_slot = {}
    for class_id in sorted(np.unique(visible_entity)):
        name = labels.get(int(class_id), f"class {class_id}")
        colour = PREFERRED_COLOURS.get(name.casefold(), fallback_colour(int(class_id)))
        class_to_slot[int(class_id)] = len(projected.data.materials)
        projected.data.materials.append(material(f"Projected {name}", colour, emission=0.18))
        legend.append({"id": int(class_id), "name": name, "rgb": [round(255 * value) for value in colour[:3]]})
    for polygon, class_id in zip(projected.data.polygons, visible_entity, strict=True):
        polygon.material_index = class_to_slot[int(class_id)]

    location = Vector(pose["position_enu_m"])
    rotation = panorama_rotation(
        float(pose["heading_deg"]),
        float(pose["pitch_correction_deg"]),
        float(pose["roll_correction_deg"]),
    )
    bpy.ops.object.light_add(type="SUN", location=location + Vector((0.0, 0.0, 100.0)))
    bpy.context.object.data.energy = 1.5
    bpy.context.object.rotation_euler = (math.radians(30.0), math.radians(-20.0), math.radians(35.0))
    camera_data = bpy.data.cameras.new("Recovered Street View camera")
    camera_data.angle = math.radians(90.0)
    camera_data.lens = 18.0
    camera = bpy.data.objects.new("Recovered Street View camera", camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera
    for yaw in (0, 90, 180, 270):
        camera.matrix_world = camera_matrix(location, rotation, yaw)
        scene.render.filepath = str(args.out / f"projected_yaw_{yaw:03d}.png")
        bpy.ops.render.render(write_still=True)

    manifest = {
        "source_mesh": str(args.mesh),
        "face_semantics": str(args.face_semantics),
        "visible_projected_triangles": int(visible.sum()),
        "legend": legend,
    }
    (args.out / "projected_render_manifest.json").write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
