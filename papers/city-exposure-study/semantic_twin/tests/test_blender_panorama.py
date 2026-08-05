from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import textwrap

import numpy as np
import pytest
from PIL import Image

from semantic_twin.pano_geometry import panorama_to_world_matrix
from semantic_twin.viz.blender.panorama import PanoramaAsset, camera_matrix, select_panorama_asset


BLENDER = pathlib.Path.home() / "blender-4.5" / "blender"


def sample_asset(image: pathlib.Path, pose: pathlib.Path) -> PanoramaAsset:
    return PanoramaAsset(
        capture="walk_05_1084407470281938",
        provider="Mapillary",
        image_id="1084407470281938",
        image_path=image,
        image_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),
        width=64,
        height=32,
        pose_path=pose,
        position_enu_m=(-6.4, -14.9, 52.4),
        heading_deg=192.0,
        pitch_deg=-20.0,
        roll_deg=11.0,
        skyline_residual_deg=1.083,
        sky_with_mesh_hit_fraction=0.0049,
        registration_verdict="usable",
        captured_at="2025-04-28",
    )


def test_select_panorama_asset_uses_manifest_pose_and_keeps_image_external(tmp_path: pathlib.Path) -> None:
    capture = tmp_path / "data" / "panoramas" / "korenmarkt_walk" / "walk_05_1084407470281938"
    pose_path = capture / "alignment" / "pose_aligned.json"
    pose_path.parent.mkdir(parents=True)
    pose_path.write_text(
        json.dumps(
            {
                "position_enu_m": [-6.4, -14.9, 52.4],
                "heading_deg": 192.0,
                "pitch_correction_deg": -20.0,
                "roll_correction_deg": 11.0,
            }
        )
    )
    (capture / "metadata.json").write_text(json.dumps({"id": "1084407470281938", "captured_at": 1745856743000}))
    image_path = capture / "panorama_original.jpg"
    Image.new("RGB", (64, 32), (20, 30, 40)).save(image_path)
    manifest = {
        "hero": {"point_enu_m": [-6.4, -4.9, 52.4]},
        "evidence": {
            "camera": {"position_enu_m": [3.6, -14.9, 52.4]},
            "registration": {
                "poses": [
                    {
                        "capture": "walk_05_1084407470281938",
                        "pose_file": str(pose_path.relative_to(tmp_path)),
                        "skyline_residual_deg": 1.083,
                        "sky_with_mesh_hit_fraction": 0.0049,
                        "verdict": "usable",
                    }
                ]
            },
        },
    }

    asset = select_panorama_asset(manifest, tmp_path)

    assert asset.image_path == image_path.resolve()
    assert asset.image_id == "1084407470281938"
    assert asset.provider == "Mapillary"
    assert (asset.width, asset.height) == (64, 32)
    assert asset.image_sha256 == hashlib.sha256(image_path.read_bytes()).hexdigest()
    assert asset.captured_at == "2025-04-28T16:12:23+00:00"
    assert asset.semantic_evidence_origin_distance_m == pytest.approx(10.0)
    assert asset.hero_trace_origin_distance_m == pytest.approx(10.0)


def test_panorama_camera_matrix_maps_blender_axes_to_registered_panorama(tmp_path: pathlib.Path) -> None:
    image = tmp_path / "pano.jpg"
    Image.new("RGB", (64, 32)).save(image)
    pose = tmp_path / "pose.json"
    pose.write_text("{}")
    asset = sample_asset(image, pose)
    matrix = camera_matrix(asset)
    rotation = panorama_to_world_matrix(
        asset.heading_deg,
        pitch_deg=asset.pitch_deg,
        roll_deg=asset.roll_deg,
    )

    assert np.allclose(matrix[:3, 0], rotation[:, 0])
    assert np.allclose(matrix[:3, 1], rotation[:, 2])
    assert np.allclose(-matrix[:3, 2], rotation[:, 1])
    assert np.allclose(matrix[:3, 3], asset.position_enu_m)
    assert np.allclose(matrix[:3, :3].T @ matrix[:3, :3], np.eye(3), atol=1e-12)
    assert np.linalg.det(matrix[:3, :3]) == pytest.approx(1.0)


@pytest.mark.skipif(not BLENDER.is_file(), reason="Blender is not installed at the default location")
def test_registered_panorama_scene_stays_linked_and_survives_reopen(tmp_path: pathlib.Path) -> None:
    study = pathlib.Path(__file__).resolve().parents[1]
    image = tmp_path / "panorama_original.jpg"
    pixels = np.zeros((32, 64, 3), dtype=np.uint8)
    pixels[:, :16] = (220, 30, 30)
    pixels[:, 16:32] = (30, 220, 30)
    pixels[:, 32:48] = (30, 30, 220)
    pixels[:, 48:] = (220, 220, 30)
    Image.fromarray(pixels).save(image, quality=100, subsampling=0)
    pose = tmp_path / "pose.json"
    pose.write_text("{}")
    blend = tmp_path / "panorama.blend"
    render = tmp_path / "panorama_half_size.png"
    report = tmp_path / "report.json"
    script = tmp_path / "probe.py"
    script.write_text(
        textwrap.dedent(
            f"""
            import json
            import pathlib
            import sys

            import bpy

            sys.path.insert(0, {str(study)!r})
            from semantic_twin.viz.blender.panorama import PanoramaAsset, configure_panorama_scene

            bpy.ops.wm.read_factory_settings(use_empty=True)
            scene = bpy.context.scene
            support = bpy.data.collections.new("01 city mesh")
            scene.collection.children.link(support)
            bpy.ops.mesh.primitive_cube_add()
            cube = bpy.context.object
            for group in list(cube.users_collection):
                group.objects.unlink(cube)
            support.objects.link(cube)
            asset = PanoramaAsset(
                capture="walk_05_1084407470281938",
                provider="Mapillary",
                image_id="1084407470281938",
                image_path=pathlib.Path({str(image)!r}),
                image_sha256="abc123",
                width=64,
                height=32,
                pose_path=pathlib.Path({str(pose)!r}),
                position_enu_m=(-6.4, -14.9, 52.4),
                heading_deg=192.0,
                pitch_deg=-20.0,
                roll_deg=11.0,
                skyline_residual_deg=1.083,
                sky_with_mesh_hit_fraction=0.0049,
                registration_verdict="usable",
                captured_at="2025-04-28",
            )
            configure_panorama_scene(scene, asset, blend_path=pathlib.Path({str(blend)!r}))
            bpy.ops.wm.save_as_mainfile(filepath={str(blend)!r}, compress=True)
            bpy.ops.wm.open_mainfile(filepath={str(blend)!r})
            scene = bpy.context.scene
            scene.render.resolution_percentage = 50
            scene.cycles.samples = 1
            scene.render.filepath = {str(render)!r}
            bpy.ops.render.render(write_still=True)
            camera = scene.camera
            image = bpy.data.images["Linked panorama | Mapillary | 1084407470281938"]
            layer = scene.view_layers[0].layer_collection.children["01 city mesh"]
            nodes = scene.node_tree.nodes
            scale = nodes["Fit panorama to render percentage"]
            support_overlay = bpy.data.collections[scene["panorama_support_overlay_collection"]]
            pathlib.Path({str(report)!r}).write_text(json.dumps({{
                "camera_type": camera.data.type,
                "panorama_type": camera.data.panorama_type,
                "longitude": [camera.data.longitude_min, camera.data.longitude_max],
                "latitude": [camera.data.latitude_min, camera.data.latitude_max],
                "resolution": [scene.render.resolution_x, scene.render.resolution_y],
                "engine": scene.render.engine,
                "transparent": scene.render.film_transparent,
                "packed": image.packed_file is not None,
                "linked_path": image.filepath,
                "holdout": layer.holdout,
                "nodes": sorted(node.bl_idname for node in nodes),
                "scale_space": scale.space,
                "scale_frame_method": scale.frame_method,
                "support_overlay_objects": len(support_overlay.objects),
                "support_overlay_scale": scene["panorama_support_overlay_scale_about_camera"],
                "support_overlay_opacity": scene["panorama_support_overlay_opacity"],
                "image_id": camera["panorama_image_id"],
                "projection": camera["panorama_projection"],
            }}))
            """
        )
    )
    result = subprocess.run(
        [str(BLENDER), "--background", "--factory-startup", "--python", str(script)],
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-4000:]
    assert report.is_file(), result.stdout[-4000:] + result.stderr[-4000:]
    measured = json.loads(report.read_text())
    assert measured["camera_type"] == "PANO"
    assert measured["panorama_type"] == "EQUIRECTANGULAR"
    assert measured["longitude"] == pytest.approx([-np.pi, np.pi])
    assert measured["latitude"] == pytest.approx([-np.pi / 2.0, np.pi / 2.0])
    assert measured["resolution"] == [64, 32]
    assert measured["engine"] == "CYCLES"
    assert measured["transparent"]
    assert not measured["packed"]
    assert measured["linked_path"].startswith("//")
    assert measured["holdout"]
    assert measured["nodes"] == [
        "CompositorNodeAlphaOver",
        "CompositorNodeComposite",
        "CompositorNodeImage",
        "CompositorNodeRLayers",
        "CompositorNodeScale",
    ]
    assert measured["scale_space"] == "RENDER_SIZE"
    assert measured["scale_frame_method"] == "STRETCH"
    assert measured["support_overlay_objects"] == 1
    assert measured["support_overlay_scale"] == pytest.approx(0.99999)
    assert measured["support_overlay_opacity"] == pytest.approx(0.08)
    assert measured["image_id"] == "1084407470281938"
    assert measured["projection"].startswith("equirectangular")
    rendered = np.asarray(Image.open(render).convert("RGB"))
    assert rendered.shape == (16, 32, 3)
    samples = rendered[2, [2, 10, 18, 26]]
    assert np.argmax(samples[:3], axis=1).tolist() == [0, 1, 2]
    assert min(samples[3, 0], samples[3, 1]) > 120
    assert samples[3, 2] < 80, "the last yellow quarter proves the full image was scaled, not centre-cropped"


@pytest.mark.skipif(not BLENDER.is_file(), reason="Blender is not installed at the default location")
def test_cycles_projection_and_support_holdout_are_visible_in_rendered_pixels(tmp_path: pathlib.Path) -> None:
    study = pathlib.Path(__file__).resolve().parents[1]
    source = tmp_path / "black_panorama.jpg"
    Image.new("RGB", (360, 180), (0, 0, 0)).save(source)
    pose = tmp_path / "pose.json"
    pose.write_text("{}")
    convention_render = tmp_path / "convention.png"
    occlusion_render = tmp_path / "occlusion.png"
    script = tmp_path / "projection_probe.py"
    script.write_text(
        textwrap.dedent(
            f"""
            import pathlib
            import sys

            import bpy

            sys.path.insert(0, {str(study)!r})
            from semantic_twin.viz.blender.panorama import PanoramaAsset, configure_panorama_scene

            def material(name, colour):
                made = bpy.data.materials.new(name)
                made.use_nodes = True
                tree = made.node_tree
                tree.nodes.clear()
                emission = tree.nodes.new("ShaderNodeEmission")
                emission.inputs["Color"].default_value = (*colour, 1.0)
                emission.inputs["Strength"].default_value = 5.0
                output = tree.nodes.new("ShaderNodeOutputMaterial")
                tree.links.new(emission.outputs[0], output.inputs["Surface"])
                return made

            def asset():
                return PanoramaAsset(
                    capture="walk_05_1084407470281938",
                    provider="Mapillary",
                    image_id="1084407470281938",
                    image_path=pathlib.Path({str(source)!r}),
                    image_sha256="probe",
                    width=360,
                    height=180,
                    pose_path=pathlib.Path({str(pose)!r}),
                    position_enu_m=(0.0, 0.0, 0.0),
                    heading_deg=0.0,
                    pitch_deg=0.0,
                    roll_deg=0.0,
                    skyline_residual_deg=0.0,
                    sky_with_mesh_hit_fraction=0.0,
                    registration_verdict="usable",
                    captured_at="probe",
                )

            def sphere(name, location, colour, radius=0.7):
                bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=radius, location=location)
                obj = bpy.context.object
                obj.name = name
                obj.data.materials.append(material(name, colour))

            bpy.ops.wm.read_factory_settings(use_empty=True)
            scene = bpy.context.scene
            support = bpy.data.collections.new("01 city mesh")
            scene.collection.children.link(support)
            bpy.ops.mesh.primitive_cube_add(size=0.2, location=(-50.0, -50.0, -50.0))
            far_support = bpy.context.object
            for group in list(far_support.users_collection):
                group.objects.unlink(far_support)
            support.objects.link(far_support)
            configure_panorama_scene(scene, asset(), blend_path=pathlib.Path({str(tmp_path / "probe.blend")!r}))
            sphere("forward red", (0.0, 10.0, 0.0), (1.0, 0.0, 0.0))
            sphere("right green", (10.0, 0.0, 0.0), (0.0, 1.0, 0.0))
            sphere("up blue", (0.0, 0.0, 10.0), (0.0, 0.0, 1.0))
            scene.cycles.samples = 1
            scene.cycles.use_denoising = False
            scene.render.filepath = {str(convention_render)!r}
            bpy.ops.render.render(write_still=True)

            bpy.ops.wm.read_factory_settings(use_empty=True)
            scene = bpy.context.scene
            support = bpy.data.collections.new("01 city mesh")
            scene.collection.children.link(support)
            mesh = bpy.data.meshes.new("support plane")
            mesh.from_pydata(
                [(-2.0, 5.0, -2.0), (2.0, 5.0, -2.0), (2.0, 5.0, 2.0), (-2.0, 5.0, 2.0)],
                [],
                [(0, 1, 2, 3)],
            )
            plane = bpy.data.objects.new("support plane", mesh)
            support.objects.link(plane)
            configure_panorama_scene(scene, asset(), blend_path=pathlib.Path({str(tmp_path / "probe.blend")!r}))
            sphere("behind red", (0.0, 10.0, 0.0), (1.0, 0.0, 0.0), radius=0.35)
            sphere("front green", (1.0, 3.0, 0.0), (0.0, 1.0, 0.0), radius=0.35)
            scene.cycles.samples = 1
            scene.cycles.use_denoising = False
            scene.render.filepath = {str(occlusion_render)!r}
            bpy.ops.render.render(write_still=True)
            """
        )
    )
    result = subprocess.run(
        [str(BLENDER), "--background", "--factory-startup", "--python", str(script)],
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-4000:]
    assert convention_render.is_file(), result.stdout[-4000:] + result.stderr[-4000:]
    assert occlusion_render.is_file(), result.stdout[-4000:] + result.stderr[-4000:]

    convention = np.asarray(Image.open(convention_render).convert("RGB"), dtype=np.int16)
    red = (convention[:, :, 0] > convention[:, :, 1] + 80) & (convention[:, :, 0] > 100)
    green = (
        (convention[:, :, 1] > convention[:, :, 0] + 80)
        & (convention[:, :, 1] > convention[:, :, 2] + 80)
        & (convention[:, :, 1] > 100)
    )
    blue = (convention[:, :, 2] > convention[:, :, 0] + 80) & (convention[:, :, 2] > 100)
    red_y, red_x = np.nonzero(red)
    green_y, green_x = np.nonzero(green)
    blue_y, _ = np.nonzero(blue)
    assert (red_x.mean(), red_y.mean()) == pytest.approx((179.5, 89.5), abs=1.0)
    assert (green_x.mean(), green_y.mean()) == pytest.approx((269.5, 89.5), abs=1.0)
    assert blue_y.mean() < 4.0

    occlusion = np.asarray(Image.open(occlusion_render).convert("RGB"), dtype=np.int16)
    red = (occlusion[:, :, 0] > occlusion[:, :, 1] + 80) & (occlusion[:, :, 0] > 100)
    green = (
        (occlusion[:, :, 1] > occlusion[:, :, 0] + 80)
        & (occlusion[:, :, 1] > occlusion[:, :, 2] + 80)
        & (occlusion[:, :, 1] > 100)
    )
    assert not red.any(), "the support holdout must hide a marker behind it"
    green_y, green_x = np.nonzero(green)
    assert green_x.size > 0, "a marker in front of the support must remain visible"
    assert (green_x.mean(), green_y.mean()) == pytest.approx((197.9, 89.5), abs=2.0)
