"""Render photogrammetry from the recovered Street View camera in Blender.

Run from ``semantic_twin``::

    ~/blender-4.5/blender --background --python render_blender_alignment.py -- \
      --mesh data/geometry/korenmarkt/inhouse_leaf_130m.ply \
      --pose data/panoramas/korenmarkt/alignment/pose_aligned.json \
      --out data/panoramas/korenmarkt/alignment/blender
"""

from __future__ import annotations

import json
import math
import pathlib
import sys
from typing import Any

import bpy
from mathutils import Matrix, Vector

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from semantic_twin.pano_geometry import panorama_to_world_matrix, view_basis  # noqa: E402


def panorama_rotation(heading_deg: float, pitch_deg: float, roll_deg: float) -> Matrix:
    """Panorama-local to world ENU rotation as a ``mathutils.Matrix``.

    The rotation itself is defined once in
    :func:`semantic_twin.pano_geometry.panorama_to_world_matrix`. This wrapper
    exists only so Blender code can multiply it against a ``Vector``.
    """
    rotation = panorama_to_world_matrix(heading_deg, pitch_deg=pitch_deg, roll_deg=roll_deg)
    return Matrix([[float(value) for value in row] for row in rotation])


def local_view_basis(yaw_deg: float, pitch_deg: float = 0.0) -> tuple[Vector, Vector, Vector]:
    """Panorama-local view axes as ``mathutils`` vectors.

    Same axes as :func:`semantic_twin.pano_geometry.view_basis`, which is where
    the convention is defined.
    """
    right, forward, up = view_basis(yaw_deg, pitch_deg)
    return Vector(right), Vector(forward), Vector(up)


def camera_matrix(location: Vector, panorama: Matrix, yaw_deg: float, pitch_deg: float = 0.0) -> Matrix:
    local_right, local_forward, local_up = local_view_basis(yaw_deg, pitch_deg)
    right = panorama @ local_right
    forward = panorama @ local_forward
    up = panorama @ local_up
    rotation = Matrix((right, up, -forward)).transposed().to_4x4()
    rotation.translation = location
    return rotation


def material(name: str, colour: tuple[float, float, float, float], *, emission: float = 0.0) -> bpy.types.Material:
    result = bpy.data.materials.new(name)
    result.diffuse_color = colour
    result.use_nodes = True
    shader = result.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = colour
    shader.inputs["Roughness"].default_value = 0.72
    shader.inputs["Metallic"].default_value = 0.05
    if emission:
        shader.inputs["Emission Color"].default_value = colour
        shader.inputs["Emission Strength"].default_value = emission
    return result


def cylinder_between(start: Vector, end: Vector, radius: float, surface: bpy.types.Material) -> None:
    delta = end - start
    midpoint = (start + end) * 0.5
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=radius, depth=delta.length, location=midpoint)
    cylinder = bpy.context.object
    cylinder.rotation_mode = "QUATERNION"
    cylinder.rotation_quaternion = Vector((0.0, 0.0, 1.0)).rotation_difference(delta.normalized())
    cylinder.data.materials.append(surface)


def look_at(camera: bpy.types.Object, target: Vector) -> None:
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def setup_scene(size: int) -> bpy.types.Scene:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.eevee.taa_render_samples = 4
    scene.eevee.taa_samples = 4
    scene.render.resolution_x = size
    scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True
    scene.render.image_settings.color_depth = "8"
    scene.render.fps = 1
    scene.world = bpy.data.worlds.new("Alignment world")
    scene.world.color = (0.025, 0.025, 0.025)
    scene.view_settings.look = "AgX - Medium High Contrast"
    return scene


def render_alignment(args: Any) -> None:
    args.out.mkdir(parents=True, exist_ok=True)
    pose = json.loads(args.pose.read_text())
    location = Vector(pose["position_enu_m"])
    panorama = panorama_rotation(
        float(pose["heading_deg"]),
        float(pose["pitch_correction_deg"]),
        float(pose["roll_correction_deg"]),
    )
    scene = setup_scene(args.size)

    bpy.ops.wm.ply_import(filepath=str(args.mesh.resolve()))
    mesh = bpy.context.object
    mesh.name = "Photogrammetry"
    clay = material("Photogrammetry clay", (0.035, 0.32, 0.64, 1.0))
    mesh.data.materials.append(clay)

    bpy.ops.object.light_add(type="SUN", location=location + Vector((0.0, 0.0, 100.0)))
    sun = bpy.context.object
    sun.rotation_euler = (math.radians(28.0), math.radians(-18.0), math.radians(35.0))
    sun.data.energy = 2.0
    sun.data.angle = math.radians(20.0)

    camera_data = bpy.data.cameras.new("Recovered Street View camera")
    camera_data.type = "PERSP"
    camera_data.angle = math.radians(90.0)
    camera_data.lens = 18.0
    camera_data.clip_start = 0.05
    camera_data.clip_end = 2000.0
    camera = bpy.data.objects.new("Recovered Street View camera", camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera

    for yaw in args.yaws:
        camera.matrix_world = camera_matrix(location, panorama, yaw)
        scene.render.film_transparent = True
        scene.render.filepath = str(args.out / f"mesh_yaw_{int(round(yaw)) % 360:03d}.png")
        bpy.ops.render.render(write_still=True)

    red = material("Camera marker", (1.0, 0.035, 0.02, 1.0), emission=0.2)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1.5, location=location)
    bpy.context.object.data.materials.append(red)
    for yaw in args.yaws:
        _, local_forward, _ = local_view_basis(yaw)
        direction = panorama @ local_forward
        cylinder_between(location, location + direction * 22.0, 0.22, red)

    corners = [mesh.matrix_world @ Vector(corner) for corner in mesh.bound_box]
    centre = sum(corners, Vector()) / len(corners)
    extent = max((corner - centre).length for corner in corners)
    overview_data = bpy.data.cameras.new("Overview camera")
    overview = bpy.data.objects.new("Overview camera", overview_data)
    bpy.context.collection.objects.link(overview)
    overview.location = location + Vector((extent * 0.72, -extent * 0.72, extent * 0.58))
    overview_data.lens = 52.0
    overview_data.clip_end = extent * 5.0
    look_at(overview, location + Vector((0.0, 0.0, -5.0)))
    scene.camera = overview
    scene.render.film_transparent = False
    scene.world.color = (0.018, 0.023, 0.035)
    scene.render.filepath = str(args.out / "camera_overview.png")
    bpy.ops.render.render(write_still=True)

    manifest = {
        "mesh": str(args.mesh),
        "pose": str(args.pose),
        "position_enu_m": list(location),
        "heading_deg": pose["heading_deg"],
        "pitch_deg": pose["pitch_correction_deg"],
        "roll_deg": pose["roll_correction_deg"],
        "horizontal_yaws_deg": args.yaws,
        "render_engine": scene.render.engine,
    }
    (args.out / "render_manifest.json").write_text(json.dumps(manifest, indent=2))
