"""Archived predecessor of the packaged propagation Blender workflow.

This is a review scene, not a promoted RT scene.  It deliberately keeps
unregistered image semantics on evidence boards rather than painting them onto
the support mesh.  Candidate camera poses and the dynamic SAM 3D Body mesh are
separate collections so uncertainty stays visible in Blender's outliner.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys

import bpy
from mathutils import Vector

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from semantic_twin.viz.blender.alignment import look_at, setup_scene  # noqa: E402
from semantic_twin.vision.bodies import DynamicBodyArtifact  # noqa: E402


def arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh", type=pathlib.Path, required=True)
    parser.add_argument("--views-root", type=pathlib.Path, required=True)
    parser.add_argument("--reference-blend", type=pathlib.Path)
    parser.add_argument("--google-pano", type=pathlib.Path)
    parser.add_argument("--smooth-blend", type=pathlib.Path)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--size", type=int, default=1600)
    return parser.parse_args(argv)


def collection(name: str) -> bpy.types.Collection:
    result = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(result)
    return result


def move_to_collection(obj: bpy.types.Object, target: bpy.types.Collection) -> bpy.types.Object:
    for current in tuple(obj.users_collection):
        current.objects.unlink(obj)
    target.objects.link(obj)
    return obj


def colour_material(name: str, rgba: tuple[float, float, float, float], *, emission: float = 0.0) -> bpy.types.Material:
    result = bpy.data.materials.new(name)
    result.diffuse_color = rgba
    result.use_nodes = True
    node = result.node_tree.nodes.get("Principled BSDF")
    assert node is not None
    node.inputs["Base Color"].default_value = rgba
    node.inputs["Roughness"].default_value = 0.65
    node.inputs["Metallic"].default_value = 0.08
    node.inputs["Emission Color"].default_value = rgba
    node.inputs["Emission Strength"].default_value = emission
    return result


def image_material(name: str, image_path: pathlib.Path) -> bpy.types.Material:
    image = bpy.data.images.load(str(image_path.resolve()), check_existing=True)
    result = bpy.data.materials.new(name)
    result.use_nodes = True
    nodes = result.node_tree.nodes
    links = result.node_tree.links
    nodes.clear()
    image_node = nodes.new("ShaderNodeTexImage")
    image_node.image = image
    emission = nodes.new("ShaderNodeEmission")
    output = nodes.new("ShaderNodeOutputMaterial")
    links.new(image_node.outputs["Color"], emission.inputs["Color"])
    links.new(emission.outputs["Emission"], output.inputs["Surface"])
    return result


def add_text(
    text: str,
    location: Vector,
    target: bpy.types.Collection,
    *,
    size: float,
    material: bpy.types.Material,
) -> bpy.types.Object:
    bpy.ops.object.text_add(location=location, rotation=(math.pi / 2.0, 0.0, 0.0))
    result = bpy.context.object
    result.name = text
    result.data.body = text
    result.data.align_x = "CENTER"
    result.data.size = size
    result.data.extrude = 0.012
    result.data.materials.append(material)
    return move_to_collection(result, target)


def add_evidence_board(
    *,
    image_path: pathlib.Path,
    title: str,
    location: Vector,
    width: float,
    target: bpy.types.Collection,
    label_material: bpy.types.Material,
) -> bpy.types.Object:
    image = bpy.data.images.load(str(image_path.resolve()), check_existing=True)
    ratio = image.size[1] / image.size[0]
    bpy.ops.mesh.primitive_plane_add(size=2.0, location=location, rotation=(math.pi / 2.0, 0.0, 0.0))
    board = bpy.context.object
    board.name = title
    board.scale = (width / 2.0, width * ratio / 2.0, 1.0)
    board.data.materials.append(image_material(title, image_path))
    move_to_collection(board, target)
    add_text(
        title,
        location + Vector((0.0, -0.04, width * ratio * 0.5 + 0.55)),
        target,
        size=0.72,
        material=label_material,
    )
    return board


def add_direction_marker(
    *,
    name: str,
    position: Vector,
    heading_deg: float,
    colour: tuple[float, float, float, float],
    target: bpy.types.Collection,
    score_deg: float | None = None,
) -> bpy.types.Object:
    surface = colour_material(name, colour, emission=0.25)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=0.72, location=position)
    marker = bpy.context.object
    marker.name = name
    marker.data.materials.append(surface)
    marker["heading_deg"] = heading_deg
    if score_deg is not None:
        marker["skyline_residual_deg"] = score_deg
    move_to_collection(marker, target)

    direction = Vector((math.sin(math.radians(heading_deg)), math.cos(math.radians(heading_deg)), 0.0))
    bpy.ops.mesh.primitive_cone_add(
        vertices=20, radius1=0.48, radius2=0.05, depth=4.0, location=position + direction * 2.2
    )
    arrow = bpy.context.object
    arrow.name = f"{name} viewing direction"
    arrow.rotation_mode = "QUATERNION"
    arrow.rotation_quaternion = Vector((0.0, 0.0, 1.0)).rotation_difference(direction)
    arrow.data.materials.append(surface)
    move_to_collection(arrow, target)
    return marker


def add_body(artifact_path: pathlib.Path, target: bpy.types.Collection) -> bpy.types.Object:
    artifact = DynamicBodyArtifact.load(artifact_path)
    mesh = bpy.data.meshes.new(f"{artifact.body_id} SAM 3D Body mesh")
    mesh.from_pydata(artifact.vertices_enu_m.tolist(), [], artifact.faces.tolist())
    mesh.update()
    result = bpy.data.objects.new(f"{artifact.body_id} dynamic SAM 3D Body (floor unresolved)", mesh)
    target.objects.link(result)
    body_surface = colour_material("Dynamic human, not static semantics", (0.98, 0.06, 0.55, 1.0), emission=0.12)
    mesh.materials.append(body_surface)
    result["source_view_id"] = artifact.source_view_id
    result["placement_provenance"] = artifact.placement_provenance
    result["floor_status"] = "unresolved: camera-transform only, do not use as static geometry"
    result["reconstruction_std_m"] = artifact.uncertainty.reconstruction_std_m
    result["camera_pose_std_m"] = artifact.uncertainty.camera_pose_std_m
    return result


def pose(path: pathlib.Path) -> dict:
    return json.loads(path.read_text())


def add_pose_set(
    image_root: pathlib.Path, evidence_root: pathlib.Path, index: int, candidates: bpy.types.Collection
) -> None:
    label = f"v{index}"
    thumbnail = pose(evidence_root / "alignment" / "pose_aligned.json")
    high_res = pose(evidence_root / "alignment_hires" / "pose_aligned.json")
    initial = pose(image_root / "pose_initial.json")
    add_direction_marker(
        name=f"{label} retained skyline candidate | thumbnail | {thumbnail['skyline_score_mean_deg']:.2f} deg",
        position=Vector(thumbnail["position_enu_m"]),
        heading_deg=float(thumbnail["heading_deg"]),
        colour=(0.10, 0.95, 0.46, 1.0),
        target=candidates,
        score_deg=float(thumbnail["skyline_score_mean_deg"]),
    )
    add_direction_marker(
        name=f"{label} unpromoted high-res candidate | {high_res['skyline_score_mean_deg']:.2f} deg",
        position=Vector(high_res["position_enu_m"]),
        heading_deg=float(high_res["heading_deg"]),
        colour=(1.0, 0.20, 0.09, 1.0),
        target=candidates,
        score_deg=float(high_res["skyline_score_mean_deg"]),
    )
    add_direction_marker(
        name=f"{label} Mapillary metadata prior",
        position=Vector(initial["position_enu_m"]),
        heading_deg=float(initial["heading_deg"]),
        colour=(0.50, 0.55, 0.68, 1.0),
        target=candidates,
    )


def main() -> None:
    args = arguments()
    args.out.mkdir(parents=True, exist_ok=True)
    if args.reference_blend is not None:
        bpy.ops.wm.open_mainfile(filepath=str(args.reference_blend.resolve()))
        scene = bpy.context.scene
        scene.render.engine = "BLENDER_EEVEE_NEXT"
        scene.render.resolution_x = args.size
        scene.render.resolution_y = args.size
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = "PNG"
        scene.render.image_settings.color_mode = "RGBA"
    else:
        scene = setup_scene(args.size)
    scene.render.film_transparent = False
    scene.world.color = (0.006, 0.010, 0.022)
    scene["status"] = "Evidence review only. No camera candidate has been promoted to RT-ready registration."
    scene["coordinate_system"] = "ENU metres: X east, Y north, Z up"

    mesh_collection = collection("00 Support mesh | geometric reference")
    legacy_collection = collection("10 Legacy SAM3 decal reference | pre-Mapillary")
    candidate_collection = collection("20 Cameras | candidates only")
    evidence_collection = collection("30 Mapillary evidence | unprojected")
    google_collection = collection("31 Existing Google pano | visual reference only")
    dynamic_collection = collection("40 Dynamic clutter | SAM 3D Body | floor unresolved")
    smooth_collection = collection("50 Experimental smooth projection | Mapillary | not registered")
    annotation_collection = collection("90 Review annotations")

    support = bpy.data.objects.get("Inhouse photogrammetry reference")
    for existing in tuple(bpy.data.objects):
        if existing != support:
            move_to_collection(existing, legacy_collection)
    if support is None:
        bpy.ops.wm.ply_import(filepath=str(args.mesh.resolve()))
        support = bpy.context.object
    support.name = "Inhouse photogrammetry support mesh | no new imagery analysis"
    move_to_collection(support, mesh_collection)
    support.data.materials.clear()
    support.data.materials.append(colour_material("Support mesh clay", (0.035, 0.18, 0.32, 1.0), emission=0.03))
    support["role"] = "first-hit geometric support only"

    corners = [support.matrix_world @ Vector(corner) for corner in support.bound_box]
    centre = sum(corners, Vector()) / len(corners)
    extent = max((corner - centre).length for corner in corners)

    roots = sorted(args.views_root.glob("view_*"))[:2]
    if len(roots) != 2:
        raise RuntimeError("expected the two retained Mapillary view directories")
    output_views_root = ROOT / "outputs" / args.views_root.name
    for index, view_root in enumerate(roots):
        add_pose_set(view_root, output_views_root / view_root.name, index, candidate_collection)

    panel_specs = (
        (roots[0] / "panorama_original.jpg", "v0 Mapillary panorama | 5760 x 2880", -31.0),
        (
            output_views_root / roots[0].name / "sam3_fused" / "panorama_layered_overlay.png",
            "v0 SAM3 layered evidence | not projected",
            -10.5,
        ),
        (roots[1] / "panorama_original.jpg", "v1 Mapillary panorama | 5760 x 2880", 10.5),
        (
            output_views_root / roots[1].name / "sam3_fused" / "panorama_layered_overlay.png",
            "v1 SAM3 layered evidence | not projected",
            31.0,
        ),
    )
    label_surface = colour_material("Evidence board labels", (0.9, 0.95, 1.0, 1.0), emission=0.5)
    board_y = centre.y - extent * 0.72
    board_z = centre.z + extent * 0.22
    for image_path, title, x_offset in panel_specs:
        resolved = image_path.resolve()
        if resolved.exists():
            add_evidence_board(
                image_path=resolved,
                title=title,
                location=Vector((centre.x + x_offset, board_y, board_z)),
                width=18.5,
                target=evidence_collection,
                label_material=label_surface,
            )

    if args.google_pano is not None and args.google_pano.exists():
        add_evidence_board(
            image_path=args.google_pano,
            title="Existing Google Street View pano | visual reference only",
            location=Vector((centre.x, board_y, board_z + 17.5)),
            width=24.0,
            target=google_collection,
            label_material=label_surface,
        )

    body_path = output_views_root / roots[0].name / "sam3_body" / "person_h00_045_061" / "dynamic_body_enu.npz"
    if body_path.exists():
        add_body(body_path, dynamic_collection)

    if args.smooth_blend is not None and args.smooth_blend.exists():
        with bpy.data.libraries.load(str(args.smooth_blend.resolve()), link=False) as (source, destination):
            destination.objects = [name for name in source.objects if name.startswith("Pixel semantic projection")]
        for object in destination.objects:
            if object is None:
                continue
            smooth_collection.objects.link(object)
            object.hide_render = True
            object["method"] = "edge-aware smoothed support depth with bounded deviation"
            object["status"] = "experimental Mapillary single-view prototype, pose not registered"

    add_text(
        "Semantic twin evidence review\nGreen = retained thumbnail pose candidate\nRed = high-res skyline candidate, not promoted\nPink = dynamic SAM 3D Body, floor unresolved",
        Vector((centre.x, board_y - 0.1, board_z + 12.0)),
        annotation_collection,
        size=0.78,
        material=label_surface,
    )

    bpy.ops.object.light_add(type="SUN", location=centre + Vector((0.0, 0.0, extent * 1.5)))
    bpy.context.object.data.energy = 2.0
    bpy.context.object.rotation_euler = (math.radians(32.0), math.radians(-20.0), math.radians(25.0))
    bpy.ops.object.light_add(type="AREA", location=Vector((centre.x, board_y - 8.0, board_z + 12.0)))
    bpy.context.object.data.energy = 1100.0
    bpy.context.object.data.shape = "RECTANGLE"
    bpy.context.object.data.size = 55.0
    bpy.context.object.data.size_y = 16.0
    bpy.context.object.rotation_euler = (math.radians(90.0), 0.0, 0.0)

    camera_data = bpy.data.cameras.new("Semantic twin review camera")
    camera = bpy.data.objects.new("Semantic twin review camera", camera_data)
    bpy.context.collection.objects.link(camera)
    camera.location = centre + Vector((extent * 0.95, -extent * 1.20, extent * 0.82))
    camera.data.lens = 43.0
    camera.data.clip_end = max(2000.0, extent * 8.0)
    look_at(camera, centre + Vector((0.0, -extent * 0.15, extent * 0.05)))
    scene.camera = camera
    scene.render.filepath = str(args.out / "semantic_twin_progress_overview.png")
    bpy.ops.render.render(write_still=True)

    evidence_camera_data = bpy.data.cameras.new("Mapillary evidence-board camera")
    evidence_camera = bpy.data.objects.new("Mapillary evidence-board camera", evidence_camera_data)
    bpy.context.collection.objects.link(evidence_camera)
    evidence_camera.location = Vector((centre.x, board_y - 95.0, board_z + 3.0))
    evidence_camera.data.lens = 40.0
    evidence_camera.data.clip_end = max(2000.0, extent * 8.0)
    look_at(evidence_camera, Vector((centre.x, board_y, board_z + 3.5)))
    scene.camera = evidence_camera
    scene.render.filepath = str(args.out / "semantic_twin_evidence_boards.png")
    bpy.ops.render.render(write_still=True)
    scene.camera = camera

    scene["source_mesh"] = str(args.mesh.resolve())
    scene["mapillary_views"] = [path.name for path in roots]
    scene["dynamic_body"] = str(body_path) if body_path.exists() else "not available"
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str((args.out / "semantic_twin_progress.blend").resolve()))
    (args.out / "README.txt").write_text(
        "This Blender file is an evidence review scene, not a calibrated RT scene.\n"
        "Open collection 10 for camera candidates, 20 for unprojected image semantics,\n"
        "and 30 for the transient SAM 3D Body mesh.\n"
    )


if __name__ == "__main__":
    main()
