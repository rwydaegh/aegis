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


def test_select_panorama_asset_includes_explicitly_admitted_companions_and_records_missing(
    tmp_path: pathlib.Path,
) -> None:
    def capture_files(name: str, image_id: str, position: list[float]) -> pathlib.Path:
        folder = tmp_path / "data" / "panoramas" / name
        pose_path = folder / "alignment" / "pose_aligned.json"
        pose_path.parent.mkdir(parents=True)
        pose_path.write_text(
            json.dumps(
                {
                    "position_enu_m": position,
                    "heading_deg": 12.0,
                    "pitch_correction_deg": -2.0,
                    "roll_correction_deg": 1.0,
                    "pose_uncertainty": {
                        "parameter_names": ["dx_m", "dy_m"],
                        "standard_deviation": [0.1, 0.2],
                    },
                }
            )
        )
        (folder / "metadata.json").write_text(json.dumps({"id": image_id, "captured_at": 1_700_000_000_000}))
        Image.new("RGB", (64, 32), (20, 30, 40)).save(folder / "panorama_original.jpg")
        return pose_path

    hero_pose = capture_files("hero", "hero-id", [0.0, 0.0, 2.0])
    companion_pose = capture_files("companion", "companion-id", [4.0, 1.0, 2.0])
    missing_pose = tmp_path / "data" / "panoramas" / "missing" / "alignment" / "pose_aligned.json"
    manifest = {
        "surface_atlas": {"admitted_captures": ["hero", "companion", "missing", "without_registration"]},
        "evidence": {
            "registration": {
                "poses": [
                    {
                        "capture": "hero",
                        "pose_file": str(hero_pose.relative_to(tmp_path)),
                        "skyline_residual_deg": 1.0,
                        "sky_with_mesh_hit_fraction": 0.01,
                        "position_sigma_m": 0.15,
                        "verdict": "usable",
                    },
                    {
                        "capture": "companion",
                        "pose_file": str(companion_pose.relative_to(tmp_path)),
                        "skyline_residual_deg": 3.2,
                        "sky_with_mesh_hit_fraction": 0.04,
                        "position_sigma_m": 0.35,
                        "verdict": "suspect",
                    },
                    {
                        "capture": "missing",
                        "pose_file": str(missing_pose.relative_to(tmp_path)),
                        "skyline_residual_deg": 2.0,
                        "sky_with_mesh_hit_fraction": 0.02,
                        "verdict": "usable",
                    },
                ]
            }
        },
    }

    asset = select_panorama_asset(manifest, tmp_path, capture="hero")

    assert [item.capture for item in asset.acquisition_assets] == ["hero", "companion"]
    assert asset.unavailable_admitted_captures == ("without_registration", "missing")
    assert asset.companion_assets[0].registration_verdict == "suspect"
    assert asset.companion_assets[0].position_sigma_m == pytest.approx(0.35)
    assert json.loads(asset.pose_uncertainty_json)["standard_deviation"] == [0.1, 0.2]


def test_select_panorama_asset_reads_production_cameras_from_surface_atlas_manifest(
    tmp_path: pathlib.Path,
) -> None:
    def camera_files(name: str, position: list[float], residual: float) -> tuple[pathlib.Path, pathlib.Path]:
        folder = tmp_path / "data" / "panoramas" / name
        pose_path = folder / "alignment" / "pose_aligned.json"
        pose_path.parent.mkdir(parents=True)
        pose_path.write_text(
            json.dumps(
                {
                    "position_enu_m": position,
                    "heading_deg": 20.0,
                    "pitch_correction_deg": -3.0,
                    "roll_correction_deg": 2.0,
                    "skyline_score_mean_deg": residual,
                    "sky_conflict": {"sky_with_mesh_hit_fraction": 0.03},
                }
            )
        )
        (folder / "metadata.json").write_text(json.dumps({"id": f"{name}-id", "captured_at": 0}))
        panorama = folder / "panorama_original.jpg"
        Image.new("RGB", (64, 32), (20, 30, 40)).save(panorama)
        return pose_path, panorama

    hero_pose, hero_panorama = camera_files("hero", [0.0, 0.0, 2.0], 1.1)
    companion_pose, companion_panorama = camera_files("companion", [3.0, 0.0, 2.0], 2.4)
    atlas_path = tmp_path / "outputs" / "surface_atlas.json"
    atlas_path.parent.mkdir()
    atlas_path.write_text(
        json.dumps(
            {
                "cameras": [
                    {
                        "camera_id": "hero",
                        "folder": str(hero_pose.parent.parent.relative_to(tmp_path)),
                        "pose": str(hero_pose.relative_to(tmp_path)),
                        "panorama": str(hero_panorama.relative_to(tmp_path)),
                        "position_enu_m": [0.0, 0.0, 2.0],
                        "heading_deg": 20.0,
                        "pitch_correction_deg": -3.0,
                        "roll_correction_deg": 2.0,
                    },
                    {
                        "camera_id": "companion",
                        "folder": str(companion_pose.parent.parent.relative_to(tmp_path)),
                        "pose": str(companion_pose.relative_to(tmp_path)),
                        "panorama": str(companion_panorama.relative_to(tmp_path)),
                        "position_enu_m": [3.0, 0.0, 2.0],
                        "heading_deg": 20.0,
                        "pitch_correction_deg": -3.0,
                        "roll_correction_deg": 2.0,
                    },
                ]
            }
        )
    )
    manifest = {
        "surface_atlas": {"manifest": str(atlas_path.relative_to(tmp_path))},
        "evidence": {
            "registration": {
                "poses": [
                    {
                        "capture": "hero",
                        "pose_file": str(hero_pose.relative_to(tmp_path)),
                        "skyline_residual_deg": 1.1,
                        "sky_with_mesh_hit_fraction": 0.01,
                        "verdict": "usable",
                    }
                ]
            }
        },
    }

    asset = select_panorama_asset(manifest, tmp_path, capture="hero")

    assert [item.capture for item in asset.acquisition_assets] == ["hero", "companion"]
    assert asset.companion_assets[0].registration_verdict == "admitted by surface atlas"
    assert asset.companion_assets[0].skyline_residual_deg == pytest.approx(2.4)
    assert asset.companion_assets[0].sky_with_mesh_hit_fraction == pytest.approx(0.03)
    assert asset.companion_assets[0].image_path == companion_panorama.resolve()
    assert asset.atlas_panorama_verification == "surface atlas panorama provenance unavailable"


def test_surface_atlas_pose_values_do_not_require_optional_pose_corrections(tmp_path: pathlib.Path) -> None:
    folder = tmp_path / "capture"
    pose = folder / "alignment" / "pose_aligned.json"
    pose.parent.mkdir(parents=True)
    pose.write_text(json.dumps({"position_enu_m": [1.0, 2.0, 3.0]}))
    (folder / "metadata.json").write_text(json.dumps({"id": "image-id"}))
    panorama = folder / "panorama_original.jpg"
    Image.new("RGB", (64, 32)).save(panorama)
    manifest = {
        "surface_atlas": {
            "camera_ids": ["hero"],
            "cameras": [
                {
                    "camera_id": "hero",
                    "folder": str(folder.relative_to(tmp_path)),
                    "pose": str(pose.relative_to(tmp_path)),
                    "panorama": str(panorama.relative_to(tmp_path)),
                    "position_enu_m": [1.0, 2.0, 3.0],
                    "heading_deg": 30.0,
                    "pitch_correction_deg": -4.0,
                    "roll_correction_deg": 2.0,
                }
            ],
        }
    }

    asset = select_panorama_asset(manifest, tmp_path, capture="hero")

    assert (asset.heading_deg, asset.pitch_deg, asset.roll_deg) == pytest.approx((30.0, -4.0, 2.0))


def test_surface_atlas_panorama_sha_is_verified(tmp_path: pathlib.Path) -> None:
    folder = tmp_path / "capture"
    pose = folder / "alignment" / "pose_aligned.json"
    pose.parent.mkdir(parents=True)
    pose.write_text(json.dumps({"position_enu_m": [0.0, 0.0, 0.0], "heading_deg": 0.0}))
    (folder / "metadata.json").write_text(json.dumps({"id": "image-id"}))
    panorama = folder / "panorama_original.jpg"
    Image.new("RGB", (64, 32), (10, 20, 30)).save(panorama)
    digest = hashlib.sha256(panorama.read_bytes()).hexdigest()

    def manifest(expected: str) -> dict[str, object]:
        return {
            "surface_atlas": {
                "camera_ids": ["hero"],
                "cameras": [
                    {
                        "camera_id": "hero",
                        "folder": str(folder.relative_to(tmp_path)),
                        "pose": str(pose.relative_to(tmp_path)),
                        "panorama": str(panorama.relative_to(tmp_path)),
                        "position_enu_m": [0.0, 0.0, 0.0],
                        "heading_deg": 0.0,
                        "input_files": {"panorama": {"present": True, "sha256": expected}},
                    }
                ],
            }
        }

    asset = select_panorama_asset(manifest(digest), tmp_path, capture="hero")
    assert asset.atlas_panorama_sha256 == digest
    assert asset.atlas_panorama_verification == "verified against surface atlas panorama SHA-256"

    with pytest.raises(ValueError, match="does not match"):
        select_panorama_asset(manifest("0" * 64), tmp_path, capture="hero")


@pytest.mark.parametrize(
    ("camera_ids", "camera_records", "match"),
    [
        (["hero", "extra"], [{"camera_id": "hero"}], "same length"),
        (["other"], [{"camera_id": "hero"}], "do not match"),
        (["hero", "hero"], [{"camera_id": "hero"}, {"camera_id": "hero"}], "duplicate id"),
    ],
)
def test_surface_atlas_rejects_inconsistent_or_duplicate_camera_records(
    tmp_path: pathlib.Path,
    camera_ids: list[str],
    camera_records: list[dict[str, str]],
    match: str,
) -> None:
    manifest = {"surface_atlas": {"camera_ids": camera_ids, "cameras": camera_records}}
    with pytest.raises(ValueError, match=match):
        select_panorama_asset(manifest, tmp_path, capture="hero")


def test_unavailable_companion_records_keep_the_omission_reason(tmp_path: pathlib.Path) -> None:
    folder = tmp_path / "hero"
    pose = folder / "alignment" / "pose_aligned.json"
    pose.parent.mkdir(parents=True)
    pose.write_text(json.dumps({"position_enu_m": [0.0, 0.0, 0.0], "heading_deg": 0.0}))
    (folder / "metadata.json").write_text(json.dumps({"id": "hero-id"}))
    Image.new("RGB", (64, 32)).save(folder / "panorama_original.jpg")
    manifest = {
        "surface_atlas": {"admitted_captures": ["hero", "missing"]},
        "evidence": {
            "registration": {
                "poses": [
                    {"capture": "hero", "pose_file": str(pose.relative_to(tmp_path)), "verdict": "usable"},
                    {
                        "capture": "missing",
                        "pose_file": "missing/alignment/pose_aligned.json",
                        "verdict": "usable",
                    },
                ]
            }
        },
    }

    asset = select_panorama_asset(manifest, tmp_path, capture="hero")
    omissions = json.loads(asset.omitted_admitted_captures_json)

    assert asset.unavailable_admitted_captures == ("missing",)
    assert omissions[0]["capture"] == "missing"
    assert omissions[0]["status"] == "omitted"
    assert "FileNotFoundError" in omissions[0]["reason"]


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
    source_digest = hashlib.sha256(image.read_bytes()).hexdigest()
    companion_image = tmp_path / "panorama_companion.jpg"
    Image.new("RGB", (64, 32), (12, 210, 180)).save(companion_image, quality=100, subsampling=0)
    companion_digest = hashlib.sha256(companion_image.read_bytes()).hexdigest()
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
            from dataclasses import replace

            import bpy
            from mathutils import Vector

            sys.path.insert(0, {str(study)!r})
            from semantic_twin.viz.blender.panorama import PanoramaAsset, configure_panorama_scene
            from semantic_twin.viz.blender.views import _render_prepared_layer

            bpy.ops.wm.read_factory_settings(use_empty=True)
            scene = bpy.context.scene
            support = bpy.data.collections.new("01 city mesh")
            scene.collection.children.link(support)
            bpy.ops.mesh.primitive_cube_add()
            cube = bpy.context.object
            cube.location = (-6.4, -14.9, 52.4)
            cube.scale = (4.0, 4.0, 4.0)
            for group in list(cube.users_collection):
                group.objects.unlink(cube)
            support.objects.link(cube)
            scene.view_layers.new("Panorama capture poses")
            scene.view_layers.new("Exposure standpoints")
            asset = PanoramaAsset(
                capture="walk_05_1084407470281938",
                provider="Mapillary",
                image_id="1084407470281938",
                image_path=pathlib.Path({str(image)!r}),
                image_sha256={source_digest!r},
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
                atlas_panorama_sha256={source_digest!r},
                atlas_panorama_verification="verified against surface atlas panorama SHA-256",
            )
            asset = replace(
                asset,
                companion_assets=(
                    replace(
                        asset,
                        capture="walk_06_1419513849204492",
                        image_id="1419513849204492",
                        image_path=pathlib.Path({str(companion_image)!r}),
                        image_sha256={companion_digest!r},
                        atlas_panorama_sha256={companion_digest!r},
                        position_enu_m=(-0.5, 25.4, 52.0),
                    ),
                ),
            )
            duplicate_rejected = False
            try:
                configure_panorama_scene(
                    scene,
                    replace(asset, companion_assets=(replace(asset, image_id="duplicate"),)),
                    blend_path=pathlib.Path({str(blend)!r}),
                )
            except ValueError as error:
                duplicate_rejected = "unique non-empty capture ids" in str(error)
            configure_panorama_scene(scene, asset, blend_path=pathlib.Path({str(blend)!r}))

            def display_sphere(name, location, radius, colour):
                bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=radius, location=location)
                obj = bpy.context.object
                obj.name = name
                material = bpy.data.materials.new(name)
                material.use_nodes = True
                tree = material.node_tree
                tree.nodes.clear()
                emission = tree.nodes.new("ShaderNodeEmission")
                emission.inputs["Color"].default_value = (*colour, 1.0)
                emission.inputs["Strength"].default_value = 5.0
                output = tree.nodes.new("ShaderNodeOutputMaterial")
                tree.links.new(emission.outputs[0], output.inputs["Surface"])
                obj.data.materials.append(material)

            display_sphere("local camera marker shell", asset.position_enu_m, 0.9, (0.0, 1.0, 0.0))
            distant = scene.camera.matrix_world @ Vector((0.0, 0.0, -3.2))
            display_sphere("distant registered glyph", distant, 0.6, (1.0, 0.0, 1.0))
            bpy.ops.wm.save_as_mainfile(filepath={str(blend)!r}, compress=True)
            bpy.ops.wm.open_mainfile(filepath={str(blend)!r})
            scene = bpy.context.scene
            scene.render.resolution_percentage = 50
            scene.cycles.samples = 1
            compositor_layers_during_render = []
            def record_compositor_layer(_scene, _depsgraph=None):
                node_name = scene["panorama_compositor_render_layer_node"]
                compositor_layers_during_render.append(scene.node_tree.nodes[node_name].layer)
            bpy.app.handlers.render_pre.append(record_compositor_layer)
            for layer_name, path in (
                ("Panorama capture poses", pathlib.Path({str(tmp_path / "capture_poses.png")!r})),
                ("Exposure standpoints", pathlib.Path({str(tmp_path / "exposure_standpoints.png")!r})),
            ):
                _render_prepared_layer(scene, scene.view_layers[layer_name], path)
            bpy.app.handlers.render_pre.remove(record_compositor_layer)
            compositor_layer_after_render = scene.node_tree.nodes[scene["panorama_compositor_render_layer_node"]].layer
            scene.render.filepath = {str(render)!r}
            bpy.ops.render.render(write_still=True)
            camera = scene.camera
            image = bpy.data.images["Linked panorama | Mapillary | 1084407470281938"]
            layer = scene.view_layers[0].layer_collection.children["01 city mesh"]
            nodes = scene.node_tree.nodes
            scale = nodes["Fit panorama to render percentage"]
            support_overlay = bpy.data.collections[scene["panorama_support_overlay_collection"]]
            acquisition = bpy.data.collections[scene["panorama_acquisition_collection"]]
            pano_backgrounds = []
            for obj in acquisition.objects:
                if obj.type != "CAMERA" or obj.data.type != "PANO":
                    continue
                pano_backgrounds.append({{
                    "capture": obj["capture"],
                    "show": obj.data.show_background_images,
                    "count": len(obj.data.background_images),
                    "fit": obj.data.background_images[0].frame_method,
                    "path": obj.data.background_images[0].image.filepath,
                    "packed": obj.data.background_images[0].image.packed_file is not None,
                    "sha256": obj["source_image_sha256"],
                }})
            normal = next(obj for obj in acquisition.objects if obj.get("view_role") == "normal camera view with linked panorama crop")
            image_plane = next(obj for obj in acquisition.objects if obj.get("role") == "projection-aligned rectilinear panorama image plane")
            background = normal.data.background_images[0]
            pathlib.Path({str(report)!r}).write_text(json.dumps({{
                "camera_type": camera.data.type,
                "panorama_type": camera.data.panorama_type,
                "camera_clip_start_m": camera.data.clip_start,
                "display_clip_start_m": camera["panorama_display_clip_start_m"],
                "scene_display_clip_start_m": scene["panorama_display_clip_start_m"],
                "display_clip_rule": scene["panorama_display_clip_rule"],
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
                "support_overlay_marker": support_overlay["panorama_overlay_collection"],
                "support_overlay_scale": scene["panorama_support_overlay_scale_about_camera"],
                "support_overlay_opacity": scene["panorama_support_overlay_opacity"],
                "support_holdout_layers": json.loads(scene["panorama_support_holdout_view_layers_json"]),
                "support_holdout_values": {{
                    layer.name: layer.layer_collection.children["01 city mesh"].holdout
                    for layer in scene.view_layers
                }},
                "image_id": camera["panorama_image_id"],
                "projection": camera["panorama_projection"],
                "acquisition_count": acquisition["capture_count"],
                "acquisition_marker": acquisition["panorama_overlay_collection"],
                "acquisition_separate_from": acquisition["separate_from"],
                "acquisition_camera_types": sorted(obj.data.type for obj in acquisition.objects if obj.type == "CAMERA"),
                "panorama_camera_backgrounds": sorted(pano_backgrounds, key=lambda row: row["capture"]),
                "active_pose_role": camera["pose_role"],
                "normal_fov_deg": normal["rectilinear_fov_deg"],
                "normal_sensor_fit": normal.data.sensor_fit,
                "normal_background_fit": background.frame_method,
                "normal_background_path": background.image.filepath,
                "normal_crop_path": normal["rectilinear_crop_path"],
                "normal_crop_packed": background.image.packed_file is not None,
                "image_plane_capture": image_plane["capture"],
                "image_plane_camera": image_plane["projection_camera"],
                "image_plane_distance_m": image_plane["distance_from_camera_m"],
                "image_plane_hidden_in_render": image_plane.hide_render,
                "image_plane_material_image": image_plane.data.materials[0].node_tree.nodes.get("Image Texture").image.filepath,
                "compositor_layer": nodes[scene["panorama_compositor_render_layer_node"]].layer,
                "compositor_layer_property": scene["panorama_compositor_view_layer"],
                "duplicate_rejected": duplicate_rejected,
                "atlas_image_verification": camera["panorama_surface_atlas_image_verification"],
                "compositor_layers_during_render": compositor_layers_during_render,
                "compositor_layer_after_render": compositor_layer_after_render,
            }}))
            """
        )
    )
    result = subprocess.run(
        [str(BLENDER), "--background", "--factory-startup", "--python", str(script)],
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-4000:]
    assert report.is_file(), result.stdout[-4000:] + result.stderr[-4000:]
    measured = json.loads(report.read_text())
    assert measured["camera_type"] == "PANO"
    assert measured["panorama_type"] == "EQUIRECTANGULAR"
    assert measured["camera_clip_start_m"] == pytest.approx(2.0)
    assert measured["display_clip_start_m"] == pytest.approx(2.0)
    assert measured["scene_display_clip_start_m"] == pytest.approx(2.0)
    assert "display geometry within 2 m" in measured["display_clip_rule"]
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
    assert measured["support_overlay_marker"]
    assert measured["support_overlay_scale"] == pytest.approx(0.99999)
    assert measured["support_overlay_opacity"] == pytest.approx(0.08)
    assert measured["support_holdout_layers"] == ["ViewLayer", "Panorama capture poses", "Exposure standpoints"]
    assert measured["support_holdout_values"] == {
        "ViewLayer": True,
        "Panorama capture poses": True,
        "Exposure standpoints": True,
    }
    assert measured["image_id"] == "1084407470281938"
    assert measured["projection"].startswith("equirectangular")
    assert measured["acquisition_count"] == 2
    assert measured["acquisition_marker"]
    assert measured["acquisition_separate_from"].startswith("walk exposure standpoints")
    assert measured["acquisition_camera_types"] == ["PANO", "PANO", "PERSP", "PERSP"]
    assert measured["panorama_camera_backgrounds"] == [
        {
            "capture": "walk_05_1084407470281938",
            "show": True,
            "count": 1,
            "fit": "FIT",
            "path": "//panorama_original.jpg",
            "packed": False,
            "sha256": source_digest,
        },
        {
            "capture": "walk_06_1419513849204492",
            "show": True,
            "count": 1,
            "fit": "FIT",
            "path": "//panorama_companion.jpg",
            "packed": False,
            "sha256": companion_digest,
        },
    ]
    assert measured["active_pose_role"] == "registered panorama acquisition pose"
    assert measured["normal_fov_deg"] == pytest.approx(90.0)
    assert measured["normal_sensor_fit"] == "VERTICAL"
    assert measured["normal_background_fit"] == "FIT"
    assert measured["normal_background_path"].startswith("//")
    assert pathlib.Path(measured["normal_crop_path"]).is_file()
    assert not measured["normal_crop_packed"]
    assert measured["image_plane_capture"] == "walk_05_1084407470281938"
    assert measured["image_plane_camera"].startswith("Acquisition normal view")
    assert measured["image_plane_distance_m"] == pytest.approx(1.0)
    assert measured["image_plane_hidden_in_render"]
    assert measured["image_plane_material_image"].startswith("//")
    assert measured["compositor_layer"] == "ViewLayer"
    assert measured["compositor_layer_property"] == "ViewLayer"
    assert measured["duplicate_rejected"]
    assert measured["atlas_image_verification"] == "verified against surface atlas panorama SHA-256"
    assert measured["compositor_layers_during_render"] == ["Panorama capture poses", "Exposure standpoints"]
    assert measured["compositor_layer_after_render"] == "ViewLayer"
    for prepared_render in (tmp_path / "capture_poses.png", tmp_path / "exposure_standpoints.png"):
        prepared = np.asarray(Image.open(prepared_render).convert("RGB"), dtype=np.int16)
        assert prepared.std(axis=(0, 1)).max() > 50, "the linked photograph must remain visible"
        green = (prepared[:, :, 1] > prepared[:, :, 0] + 80) & (prepared[:, :, 1] > prepared[:, :, 2] + 80)
        assert green.mean() < 0.4, "the local camera marker must not fill the prepared panorama"
        magenta = (prepared[:, :, 0] > prepared[:, :, 1] + 80) & (prepared[:, :, 2] > prepared[:, :, 1] + 80)
        assert magenta.any(), "display geometry beyond the 2 m clip must remain visible"
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
            sphere("self marker green", (0.0, 0.0, 0.0), (0.0, 1.0, 0.0), radius=0.9)
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
        check=False,
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
    assert not green[20, 20], "the 0.9 m camera marker must be removed by the 2 m display clip"

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
