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
from semantic_twin.viz.blender import panorama as panorama_module
from semantic_twin.viz.blender.panorama import (
    PANORAMA_PREVIEW_RESOLUTION_PERCENT,
    PANORAMA_PREVIEW_SAMPLES,
    PANORAMA_PUBLICATION_RESOLUTION_PERCENT,
    PANORAMA_PUBLICATION_SAMPLES,
    PanoramaAsset,
    camera_matrix,
    default_panorama_capture,
    select_panorama_asset,
)

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


def test_recorded_panorama_paths_relocate_with_the_checkout(tmp_path: pathlib.Path) -> None:
    local = tmp_path / "data" / "panoramas" / "prague" / "capture" / "panorama_z5.jpg"
    local.parent.mkdir(parents=True)
    local.write_bytes(b"image")

    resolved = panorama_module._path_from_record(
        {
            "panorama": "/home/worker/aegis/papers/city-exposure-study/semantic_twin/data/panoramas/"
            "prague/capture/panorama_z5.jpg"
        },
        tmp_path,
        "panorama",
    )

    assert resolved == local


def test_default_panorama_capture_is_the_admitted_camera_nearest_the_hero(tmp_path: pathlib.Path) -> None:
    manifest = {
        "site": "prague_staromestske",
        "hero": {"point_enu_m": [10.0, 0.0, 2.0]},
        "surface_atlas": {
            "camera_ids": ["far", "near"],
            "cameras": [
                {"camera_id": "far", "position_enu_m": [-20.0, 0.0, 2.0]},
                {"camera_id": "near", "position_enu_m": [9.0, 0.0, 2.0]},
            ],
        },
    }

    assert default_panorama_capture(manifest, tmp_path) == "near"


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
            saved_preview_settings = {{
                "resolution_percentage": scene.render.resolution_percentage,
                "samples": scene.cycles.samples,
                "denoising": scene.cycles.use_denoising,
                "use_compositing": scene.render.use_compositing,
                "source_width_px": scene["panorama_source_width_px"],
                "source_height_px": scene["panorama_source_height_px"],
                "source_resolution": json.loads(scene["panorama_source_resolution_json"]),
                "preview_percentage_property": scene["panorama_preview_resolution_percentage"],
                "preview_samples_property": scene["panorama_preview_samples"],
                "preview_denoising_property": scene["panorama_preview_denoising"],
                "publication_percentage": scene["panorama_publication_resolution_percentage"],
                "publication_samples": scene["panorama_publication_samples"],
                "instructions": scene["panorama_render_instructions"],
            }}
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
                "saved_preview_settings": saved_preview_settings,
                "denoising_during_final_render": scene.cycles.use_denoising,
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
    assert measured["saved_preview_settings"] == {  # nosec B101
        "resolution_percentage": PANORAMA_PREVIEW_RESOLUTION_PERCENT,
        "samples": PANORAMA_PREVIEW_SAMPLES,
        "denoising": True,
        "use_compositing": True,
        "source_width_px": 64,
        "source_height_px": 32,
        "source_resolution": [64, 32],
        "preview_percentage_property": PANORAMA_PREVIEW_RESOLUTION_PERCENT,
        "preview_samples_property": PANORAMA_PREVIEW_SAMPLES,
        "preview_denoising_property": True,
        "publication_percentage": PANORAMA_PUBLICATION_RESOLUTION_PERCENT,
        "publication_samples": PANORAMA_PUBLICATION_SAMPLES,
        "instructions": (
            "F12 renders a fast 5% preview at 16 samples with denoising. For a publication render, keep "
            "Resolution X/Y at the linked source dimensions, set Percentage to 100, and set Render Max Samples "
            "to 96."
        ),
    }
    assert measured["denoising_during_final_render"]  # nosec B101
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
def test_each_admitted_capture_has_a_saved_render_ready_scene(tmp_path: pathlib.Path) -> None:
    study = pathlib.Path(__file__).resolve().parents[1]
    hero_image = tmp_path / "hero_64x32.png"
    companion_image = tmp_path / "companion_80x40.png"
    Image.new("RGB", (64, 32), (210, 25, 20)).save(hero_image)
    Image.new("RGB", (80, 40), (15, 190, 215)).save(companion_image)
    hero_digest = hashlib.sha256(hero_image.read_bytes()).hexdigest()
    companion_digest = hashlib.sha256(companion_image.read_bytes()).hexdigest()
    pose = tmp_path / "pose.json"
    pose.write_text("{}")
    blend = tmp_path / "capture_scenes.blend"
    report = tmp_path / "capture_scenes.json"
    script = tmp_path / "capture_scenes_probe.py"
    script.write_text(
        textwrap.dedent(
            f"""
            import hashlib
            import json
            import pathlib
            import sys
            from dataclasses import replace

            import bpy
            import numpy as np
            from mathutils import Matrix, Vector

            sys.path.insert(0, {str(study)!r})
            from semantic_twin.viz.blender.panorama import (
                PanoramaAsset,
                SUPPORT_OVERLAY_SCALE,
                camera_matrix,
                configure_panorama_scene,
                finalize_panorama_render_cameras,
                prepared_capture_scene_hooks,
            )

            bpy.ops.wm.read_factory_settings(use_empty=True)
            hero_scene = bpy.context.scene
            hero_scene.name = "07 VIEW - panorama registration"
            hero_scene.view_layers[0].name = "Registered photograph"
            support = bpy.data.collections.new("01 city mesh")
            hero_scene.collection.children.link(support)
            mesh = bpy.data.meshes.new("shared city support")
            mesh.from_pydata(
                [(99.0, 99.0, 99.0), (100.0, 99.0, 99.0), (99.0, 100.0, 99.0)],
                [],
                [(0, 1, 2)],
            )
            city = bpy.data.objects.new("city support", mesh)
            support.objects.link(city)
            for name in ("Panorama capture poses", "Exposure standpoints"):
                hero_scene.view_layers.new(name)

            hero = PanoramaAsset(
                capture="hero_capture",
                provider="Mapillary",
                image_id="hero-image",
                image_path=pathlib.Path({str(hero_image)!r}),
                image_sha256={hero_digest!r},
                width=64,
                height=32,
                pose_path=pathlib.Path({str(pose)!r}),
                position_enu_m=(0.0, 0.0, 2.0),
                heading_deg=0.0,
                pitch_deg=0.0,
                roll_deg=0.0,
                skyline_residual_deg=1.0,
                sky_with_mesh_hit_fraction=0.01,
                registration_verdict="usable",
                captured_at="2025-01-01",
                atlas_panorama_sha256={hero_digest!r},
            )
            companion = replace(
                hero,
                capture="companion_capture",
                image_id="companion-image",
                image_path=pathlib.Path({str(companion_image)!r}),
                image_sha256={companion_digest!r},
                atlas_panorama_sha256={companion_digest!r},
                width=80,
                height=40,
                position_enu_m=(10.0, 0.0, 3.0),
                heading_deg=90.0,
                captured_at="2025-01-02",
            )
            hero = replace(hero, companion_assets=(companion,))
            hooks = prepared_capture_scene_hooks(hero, blend_path=pathlib.Path({str(blend)!r}))
            assert len(hooks) == 1

            companion_scene = bpy.data.scenes.new(hooks[0].name)
            companion_scene.view_layers[0].name = "Registered photograph"
            companion_scene.collection.children.link(support)
            for name in ("Panorama capture poses", "Exposure standpoints"):
                companion_scene.view_layers.new(name)

            handler_counts_before = {{
                "frame_change_pre": len(bpy.app.handlers.frame_change_pre),
                "frame_change_post": len(bpy.app.handlers.frame_change_post),
                "render_pre": len(bpy.app.handlers.render_pre),
            }}
            configure_panorama_scene(hero_scene, hero, blend_path=pathlib.Path({str(blend)!r}))
            hooks[0].configure(companion_scene)
            for scene, active_asset in ((hero_scene, hero), (companion_scene, companion)):
                acquisition_name = scene["panorama_acquisition_collection"]
                scene.view_layers[0].layer_collection.children[acquisition_name].exclude = True
                bpy.context.window.scene = scene
                bpy.context.view_layer.update()
                marker_position = Vector(
                    (camera_matrix(active_asset) @ np.array((0.0, 0.0, -5.0, 1.0)))[:3]
                )
                bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=0.55, location=marker_position)
                marker = bpy.context.object
                marker.name = f"camera projection probe | {{scene['panorama_capture']}}"
                marker_material = bpy.data.materials.new(marker.name)
                marker_material.use_nodes = True
                marker_nodes = marker_material.node_tree.nodes
                marker_nodes.clear()
                marker_emission = marker_nodes.new("ShaderNodeEmission")
                marker_emission.inputs["Color"].default_value = (1.0, 0.0, 1.0, 1.0)
                marker_emission.inputs["Strength"].default_value = 5.0
                marker_output = marker_nodes.new("ShaderNodeOutputMaterial")
                marker_material.node_tree.links.new(marker_emission.outputs[0], marker_output.inputs["Surface"])
                marker.data.materials.append(marker_material)
            handler_counts_after = {{
                "frame_change_pre": len(bpy.app.handlers.frame_change_pre),
                "frame_change_post": len(bpy.app.handlers.frame_change_post),
                "render_pre": len(bpy.app.handlers.render_pre),
            }}

            neutral_scene = bpy.data.scenes.new("01 VIEW - neutral default")
            finalize_panorama_render_cameras(
                (hero_scene, companion_scene),
                cold_open_anchor=neutral_scene,
            )
            bpy.context.window.scene = neutral_scene
            bpy.ops.wm.save_as_mainfile(filepath={str(blend)!r}, compress=True)
            bpy.ops.wm.open_mainfile(filepath={str(blend)!r})
            city = bpy.data.objects["city support"]

            rows = []
            render_paths = []
            for scene_name in ("07 VIEW - panorama registration", hooks[0].name):
                scene = bpy.data.scenes[scene_name]
                bpy.context.window.scene = scene
                bpy.context.view_layer.update()
                saved_preview = {{
                    "resolution_percentage": scene.render.resolution_percentage,
                    "samples": scene.cycles.samples,
                    "denoising": scene.cycles.use_denoising,
                    "source_resolution": json.loads(scene["panorama_source_resolution_json"]),
                    "publication_percentage": scene["panorama_publication_resolution_percentage"],
                    "publication_samples": scene["panorama_publication_samples"],
                }}
                scene.render.resolution_percentage = 100
                scene.cycles.samples = 1
                scene.cycles.use_denoising = False
                render_path = pathlib.Path({str(tmp_path)!r}) / f"{{scene['panorama_capture']}}.png"
                scene.render.filepath = str(render_path)
                bpy.ops.render.render(write_still=True)
                render_paths.append(render_path)

                camera = scene.camera
                evaluated_camera = camera.evaluated_get(bpy.context.evaluated_depsgraph_get())
                source = scene.node_tree.nodes["Linked source panorama"].image
                overlay_collection = bpy.data.collections[scene["panorama_support_overlay_collection"]]
                overlay = next(obj for obj in overlay_collection.objects if obj.type == "MESH")
                centre = Vector(json.loads(scene["panorama_support_overlay_centre_enu_m_json"]))
                display = Matrix.Translation(centre) @ Matrix.Diagonal(
                    (SUPPORT_OVERLAY_SCALE, SUPPORT_OVERLAY_SCALE, SUPPORT_OVERLAY_SCALE, 1.0)
                ) @ Matrix.Translation(-centre)
                expected_overlay = display @ city.matrix_world
                acquisition = bpy.data.collections[scene["panorama_acquisition_collection"]]
                normal = next(obj for obj in acquisition.objects if obj.get("view_role") == "normal camera view with linked panorama crop")
                drivers = []
                for datablock in (scene, camera, camera.data, normal, normal.data, overlay):
                    animation = getattr(datablock, "animation_data", None)
                    drivers.extend([] if animation is None else animation.drivers)
                rows.append({{
                    "scene": scene.name,
                    "capture": scene["panorama_capture"],
                    "camera_capture": camera["capture"],
                    "camera_position": list(evaluated_camera.matrix_world.translation),
                    "camera_basis_position": list(camera.matrix_basis.translation),
                    "camera_original_world_position": list(camera.matrix_world.translation),
                    "camera_root_linked": camera.name in scene.collection.objects,
                    "camera_preload_linked": camera.name in bpy.data.collections[
                        scene["panorama_render_camera_collection"]
                    ].objects,
                    "view_layer_use": {{layer.name: layer.use for layer in scene.view_layers}},
                    "source_path": source.filepath,
                    "source_sha256": camera["panorama_image_sha256"],
                    "resolution": [scene.render.resolution_x, scene.render.resolution_y],
                    "saved_preview": saved_preview,
                    "overlay_centre": list(centre),
                    "overlay_matrix_error": max(
                        abs(overlay.matrix_world[row][column] - expected_overlay[row][column])
                        for row in range(4) for column in range(4)
                    ),
                    "overlay_mesh": overlay.data.name,
                    "overlay_mesh_shared": overlay.data["panorama_display_mesh_shared_between_capture_scenes"],
                    "nearest_capture": scene["panorama_marker_capture"],
                    "nearest_distance_m": scene["panorama_marker_distance_m"],
                    "admitted_count": scene["panorama_admitted_capture_count"],
                    "scene_count": scene["panorama_capture_scene_count"],
                    "scene_captures": json.loads(scene["panorama_capture_scene_captures_json"]),
                    "active_camera_count": acquisition["capture_count"],
                    "normal_capture": normal["capture"],
                    "driver_count": len(drivers),
                }})

            pathlib.Path({str(report)!r}).write_text(json.dumps({{
                "rows": rows,
                "handler_counts_before": handler_counts_before,
                "handler_counts_after": handler_counts_after,
                "render_paths": [str(path) for path in render_paths],
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
    assert measured["handler_counts_after"] == measured["handler_counts_before"]
    hero, companion = measured["rows"]
    assert [hero["capture"], companion["capture"]] == ["hero_capture", "companion_capture"]
    assert hero["camera_capture"] == hero["normal_capture"] == "hero_capture"
    assert companion["camera_capture"] == companion["normal_capture"] == "companion_capture"
    assert hero["camera_position"] == pytest.approx([0.0, 0.0, 2.0])
    assert companion["camera_position"] == pytest.approx([10.0, 0.0, 3.0])
    assert hero["camera_basis_position"] == pytest.approx(hero["camera_position"])
    assert companion["camera_basis_position"] == pytest.approx(companion["camera_position"])
    assert not hero["camera_root_linked"] and not companion["camera_root_linked"]
    assert hero["camera_preload_linked"] and companion["camera_preload_linked"]
    expected_layer_use = {
        "Registered photograph": True,
        "Panorama capture poses": False,
        "Exposure standpoints": False,
    }
    assert hero["view_layer_use"] == companion["view_layer_use"] == expected_layer_use
    assert pathlib.Path(hero["source_path"]).name == hero_image.name
    assert pathlib.Path(companion["source_path"]).name == companion_image.name
    assert hero["source_sha256"] == hero_digest
    assert companion["source_sha256"] == companion_digest
    assert hero["resolution"] == [64, 32]
    assert companion["resolution"] == [80, 40]
    assert hero["saved_preview"] == {  # nosec B101
        "resolution_percentage": PANORAMA_PREVIEW_RESOLUTION_PERCENT,
        "samples": PANORAMA_PREVIEW_SAMPLES,
        "denoising": True,
        "source_resolution": [64, 32],
        "publication_percentage": PANORAMA_PUBLICATION_RESOLUTION_PERCENT,
        "publication_samples": PANORAMA_PUBLICATION_SAMPLES,
    }
    assert companion["saved_preview"] == {  # nosec B101
        **hero["saved_preview"],
        "source_resolution": [80, 40],
    }
    assert hero["overlay_centre"] == pytest.approx(hero["camera_position"])
    assert companion["overlay_centre"] == pytest.approx(companion["camera_position"])
    assert hero["overlay_matrix_error"] < 1e-9
    assert companion["overlay_matrix_error"] < 1e-9
    assert hero["overlay_mesh"] == companion["overlay_mesh"]
    assert hero["overlay_mesh_shared"] and companion["overlay_mesh_shared"]
    assert hero["nearest_capture"] == "companion_capture"
    assert companion["nearest_capture"] == "hero_capture"
    assert hero["nearest_distance_m"] == pytest.approx(np.sqrt(101.0))
    assert companion["nearest_distance_m"] == pytest.approx(np.sqrt(101.0))
    assert hero["admitted_count"] == hero["scene_count"] == 2
    assert companion["admitted_count"] == companion["scene_count"] == 2
    assert hero["scene_captures"] == ["hero_capture", "companion_capture"]
    assert companion["scene_captures"] == ["companion_capture", "hero_capture"]
    assert hero["active_camera_count"] == 2
    assert companion["active_camera_count"] == 1
    assert hero["driver_count"] == companion["driver_count"] == 0

    hero_render = np.asarray(Image.open(measured["render_paths"][0]).convert("RGB"))
    companion_render = np.asarray(Image.open(measured["render_paths"][1]).convert("RGB"))
    assert hero_render.shape == (32, 64, 3)
    assert companion_render.shape == (40, 80, 3)
    assert hero_render[:, :, 0].mean() > hero_render[:, :, 2].mean() + 100
    assert companion_render[:, :, 2].mean() > companion_render[:, :, 0].mean() + 100
    for rendered in (hero_render, companion_render):
        centre = rendered[rendered.shape[0] // 2, rendered.shape[1] // 2]
        assert centre[0] > 150 and centre[2] > 150 and centre[1] < 100


@pytest.mark.skipif(not BLENDER.is_file(), reason="Blender is not installed at the default location")
def test_saved_panorama_cameras_have_correct_raw_transform_on_cold_open(tmp_path: pathlib.Path) -> None:
    study = pathlib.Path(__file__).resolve().parents[1]
    hero_image = tmp_path / "cold_hero.png"
    companion_image = tmp_path / "cold_companion.png"
    Image.new("RGB", (64, 32), (210, 25, 20)).save(hero_image)
    Image.new("RGB", (80, 40), (15, 190, 215)).save(companion_image)
    hero_digest = hashlib.sha256(hero_image.read_bytes()).hexdigest()
    companion_digest = hashlib.sha256(companion_image.read_bytes()).hexdigest()
    pose = tmp_path / "pose.json"
    pose.write_text("{}")
    blend = tmp_path / "cold_capture_scenes.blend"
    build_script = tmp_path / "build_cold_capture_scenes.py"
    inspect_script = tmp_path / "inspect_cold_capture_scenes.py"
    report = tmp_path / "cold_capture_scenes.json"
    build_script.write_text(
        textwrap.dedent(
            f"""
            import json
            import pathlib
            import sys
            from dataclasses import replace

            import bpy

            sys.path.insert(0, {str(study)!r})
            from semantic_twin.viz.blender.panorama import (
                PanoramaAsset,
                camera_matrix,
                configure_panorama_scene,
                finalize_panorama_render_cameras,
                prepared_capture_scene_hooks,
            )

            bpy.ops.wm.read_factory_settings(use_empty=True)
            hero_scene = bpy.context.scene
            hero_scene.name = "07 VIEW - panorama registration"
            hero_scene.view_layers[0].name = "Registered photograph"
            support = bpy.data.collections.new("01 city mesh")
            hero_scene.collection.children.link(support)
            mesh = bpy.data.meshes.new("cold support")
            mesh.from_pydata(
                [(99.0, 99.0, 99.0), (100.0, 99.0, 99.0), (99.0, 100.0, 99.0)],
                [],
                [(0, 1, 2)],
            )
            support.objects.link(bpy.data.objects.new("cold support", mesh))
            for name in ("Panorama capture poses", "Exposure standpoints"):
                hero_scene.view_layers.new(name)

            hero = PanoramaAsset(
                capture="cold_hero",
                provider="Mapillary",
                image_id="cold-hero-image",
                image_path=pathlib.Path({str(hero_image)!r}),
                image_sha256={hero_digest!r},
                width=64,
                height=32,
                pose_path=pathlib.Path({str(pose)!r}),
                position_enu_m=(1.25, -4.5, 2.75),
                heading_deg=12.0,
                pitch_deg=-1.5,
                roll_deg=0.5,
                skyline_residual_deg=1.0,
                sky_with_mesh_hit_fraction=0.01,
                registration_verdict="usable",
                captured_at="2025-01-01",
                atlas_panorama_sha256={hero_digest!r},
            )
            companion = replace(
                hero,
                capture="cold_companion",
                image_id="cold-companion-image",
                image_path=pathlib.Path({str(companion_image)!r}),
                image_sha256={companion_digest!r},
                atlas_panorama_sha256={companion_digest!r},
                width=80,
                height=40,
                position_enu_m=(11.0, 2.5, 3.25),
                heading_deg=97.0,
                captured_at="2025-01-02",
            )
            hero = replace(hero, companion_assets=(companion,))
            hook = prepared_capture_scene_hooks(hero, blend_path=pathlib.Path({str(blend)!r}))[0]
            companion_scene = bpy.data.scenes.new(hook.name)
            companion_scene.view_layers[0].name = "Registered photograph"
            companion_scene.collection.children.link(support)
            for name in ("Panorama capture poses", "Exposure standpoints"):
                companion_scene.view_layers.new(name)

            configure_panorama_scene(hero_scene, hero, blend_path=pathlib.Path({str(blend)!r}))
            hook.configure(companion_scene)
            hero_scene["_test_expected_camera_matrix_json"] = json.dumps(camera_matrix(hero).tolist())
            companion_scene["_test_expected_camera_matrix_json"] = json.dumps(camera_matrix(companion).tolist())
            neutral = bpy.data.scenes.new("01 VIEW - neutral cold-open default")
            bpy.data.scenes.new("08 VIEW - ordinary scene without panorama cameras")
            finalize_panorama_render_cameras(
                (hero_scene, companion_scene),
                cold_open_anchor=neutral,
            )
            bpy.context.window.scene = neutral
            bpy.ops.wm.save_as_mainfile(filepath={str(blend)!r}, compress=True)
            """
        )
    )
    inspect_script.write_text(
        textwrap.dedent(
            f"""
            import json
            import pathlib

            import bpy

            default_scene = bpy.context.scene.name
            scenes = sorted(
                (item for item in bpy.data.scenes if item.get("panorama_capture")),
                key=lambda item: item.name,
            )
            raw_by_scene = {{
                scene.name: [list(row) for row in scene.camera.matrix_world]
                for scene in scenes
            }}
            rows = []
            for scene in scenes:
                camera = scene.camera
                rows.append({{
                    "scene": scene.name,
                    "capture": scene["panorama_capture"],
                    "raw": raw_by_scene[scene.name],
                    "expected": json.loads(scene["_test_expected_camera_matrix_json"]),
                    "camera": camera.name,
                }})
            for scene, row in zip(scenes, rows, strict=True):
                camera = scene.camera
                preload = bpy.data.collections[scene["panorama_render_camera_collection"]]
                row.update({{
                    "camera_collections": [item.name for item in camera.users_collection],
                    "preload": preload.name,
                    "preload_linked_scenes": sorted(
                        item.name for item in bpy.data.scenes if preload.name in item.collection.children
                    ),
                    "preload_visible_in_target_layer": not scene.view_layers[0].layer_collection.children[
                        preload.name
                    ].exclude,
                    "camera_hide_select": camera.hide_select,
                    "camera_display_size": camera.data.display_size,
                    "layer_use": {{item.name: item.use for item in scene.view_layers}},
                    "basis": [list(values) for values in camera.matrix_basis],
                }})
            depsgraph = bpy.context.evaluated_depsgraph_get()
            for row in rows:
                camera = bpy.data.objects[row["camera"]]
                row["evaluated"] = [list(values) for values in camera.evaluated_get(depsgraph).matrix_world]
            pathlib.Path({str(report)!r}).write_text(json.dumps({{
                "default_scene": default_scene,
                "rows": rows,
            }}))
            """
        )
    )

    built = subprocess.run(
        [
            str(BLENDER),
            "--background",
            "--factory-startup",
            "--python-exit-code",
            "1",
            "--python",
            str(build_script),
        ],
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    assert built.returncode == 0, built.stdout[-4000:] + built.stderr[-4000:]
    assert blend.is_file(), built.stdout[-4000:] + built.stderr[-4000:]
    inspected = subprocess.run(
        [
            str(BLENDER),
            "--background",
            str(blend),
            "--python-exit-code",
            "1",
            "--python",
            str(inspect_script),
        ],
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    assert inspected.returncode == 0, inspected.stdout[-4000:] + inspected.stderr[-4000:]
    measured = json.loads(report.read_text())
    assert measured["default_scene"] == "01 VIEW - neutral cold-open default"
    assert [row["capture"] for row in measured["rows"]] == ["cold_companion", "cold_hero"]
    expected_layer_use = {
        "Registered photograph": True,
        "Panorama capture poses": False,
        "Exposure standpoints": False,
    }
    expected_linked_scenes = [
        "01 VIEW - neutral cold-open default",
        "07 PANO 02 - cold_companion",
        "07 VIEW - panorama registration",
    ]
    for row in measured["rows"]:
        assert np.asarray(row["raw"]) == pytest.approx(np.asarray(row["expected"]), abs=2e-6)
        assert np.asarray(row["basis"]) == pytest.approx(np.asarray(row["expected"]), abs=2e-6)
        assert np.asarray(row["evaluated"]) == pytest.approx(np.asarray(row["expected"]), abs=2e-6)
        assert row["camera_collections"] == [row["preload"]]
        assert row["preload_linked_scenes"] == expected_linked_scenes
        assert row["preload_visible_in_target_layer"]
        assert row["camera_hide_select"]
        assert row["camera_display_size"] == pytest.approx(0.15)
        assert row["layer_use"] == expected_layer_use


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
            scene.render.resolution_percentage = 100
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
            scene.render.resolution_percentage = 100
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
