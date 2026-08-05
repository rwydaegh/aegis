from __future__ import annotations

import json
import pathlib
import subprocess
import textwrap

import pytest

from semantic_twin.viz.blender.views import (
    PANORAMA_VIEW_KEY,
    RAW_SCENE_NAME,
    available_view_specs,
    excluded_collection_keys,
    prepared_view_specs,
)


def test_prepared_views_keep_each_question_small_and_separate() -> None:
    specs = prepared_view_specs()
    assert [view.name for view in specs] == [
        "01 VIEW - exposure overview",
        "02 VIEW - body exposure at hero",
        "03 VIEW - arrival angular shape",
        "04 VIEW - ranked recorded paths",
        "05 VIEW - NEE explainer",
        "06 VIEW - material binding",
        "07 VIEW - panorama registration",
        "08 VIEW - evidence audit",
        "09 VIEW - full traced support",
        "10 VIEW - all-camera fused surface",
    ]
    assert len({view.key for view in specs}) == len(specs)
    assert next(view for view in specs if view.key == "ranked_paths").frame_range_property == "animation_path_frames"
    assert next(view for view in specs if view.key == "nee_explainer").frame_range_property == "animation_nee_frames"
    panorama = next(view for view in specs if view.key == PANORAMA_VIEW_KEY)
    assert panorama.camera == "cam_evidence"
    assert panorama.layers[0].show == ("twin",)
    assert panorama.layers[1].show == ("twin", "panoramas", "cameras")
    assert panorama.layers[2].show == ("twin", "walk")
    assert next(view for view in specs if view.key == "exposure_overview").camera == "cam_walk"
    assert next(view for view in specs if view.key == "ranked_paths").camera == "cam_path_animation"
    nee = next(view for view in specs if view.key == "nee_explainer")
    assert nee.camera == "cam_path_animation"
    assert nee.layers[0].show == ("twin", "body", "nee_animation")
    full = next(view for view in specs if view.key == "full_support")
    assert full.camera == "cam_full_support"
    assert full.layers[0].show == ("twin", "outer_support", "support_extent", "walk")
    fused = next(view for view in specs if view.key == "fused_surface")
    assert fused.requires_objects == ("fused_semantics",)


def test_all_camera_view_exists_only_when_the_fused_surface_has_geometry() -> None:
    class Group:
        def __init__(self, objects):
            self.objects = objects

    keys = {key for spec in prepared_view_specs() for layer in spec.layers for key in layer.show}
    empty = {key: Group([]) for key in keys}
    assert "fused_surface" not in {spec.key for spec in available_view_specs(empty)}

    empty["fused_semantics"] = Group([object()])
    assert "fused_surface" in {spec.key for spec in available_view_specs(empty)}


def test_collection_exclusions_are_explicit_and_reject_unknown_keys() -> None:
    available = ("twin", "walk", "body", "rays", "cameras")
    layer = prepared_view_specs()[0].layers[0]
    assert excluded_collection_keys(layer, available) == ("body", "rays", "cameras")
    with pytest.raises(KeyError, match="unknown collections"):
        excluded_collection_keys(type(layer)("broken", ("twin", "missing")), available)


BLENDER = pathlib.Path.home() / "blender-4.5" / "blender"


@pytest.mark.skipif(not BLENDER.is_file(), reason="Blender is not installed at the default location")
def test_prepared_animation_frames_use_the_target_scene_and_frame(tmp_path: pathlib.Path) -> None:
    study = pathlib.Path(__file__).resolve().parents[1]
    report = tmp_path / "animation.json"
    renders = tmp_path / "animation"
    script = tmp_path / "animation_probe.py"
    script.write_text(
        textwrap.dedent(
            f"""
            import hashlib
            import json
            import pathlib
            import sys

            import bpy

            sys.path.insert(0, {str(study)!r})
            from semantic_twin.viz.blender.views import render_prepared_frames

            bpy.ops.wm.read_factory_settings(use_empty=True)
            decoy = bpy.context.scene
            decoy.name = "decoy scene"
            decoy.frame_set(11)

            target = bpy.data.scenes.new("prepared animation")
            target.render.engine = "BLENDER_EEVEE_NEXT"
            target.render.resolution_x = 48
            target.render.resolution_y = 48
            target.render.resolution_percentage = 100
            target.render.image_settings.file_format = "PNG"
            target.render.filepath = "/tmp/original-prepared-path"
            target.frame_start = 1
            target.frame_end = 2
            target.world = bpy.data.worlds.new("animation world")
            target.world.color = (0.0, 0.0, 0.0)
            prior_layer = target.view_layers.new("prior audit layer")

            camera_data = bpy.data.cameras.new("animation camera")
            camera_data.type = "ORTHO"
            camera_data.ortho_scale = 4.0
            camera = bpy.data.objects.new("animation camera", camera_data)
            camera.location = (0.0, 0.0, 10.0)
            target.collection.objects.link(camera)
            target.camera = camera

            def emission(name, colour):
                material = bpy.data.materials.new(name)
                material.use_nodes = True
                nodes = material.node_tree.nodes
                nodes.clear()
                output = nodes.new("ShaderNodeOutputMaterial")
                shader = nodes.new("ShaderNodeEmission")
                shader.inputs["Color"].default_value = (*colour, 1.0)
                shader.inputs["Strength"].default_value = 2.0
                material.node_tree.links.new(shader.outputs["Emission"], output.inputs["Surface"])
                return material

            def animated_panel(name, x, material, visible_frame):
                mesh = bpy.data.meshes.new(name + " mesh")
                mesh.from_pydata(
                    [(x - 0.7, -0.7, 0.0), (x + 0.7, -0.7, 0.0),
                     (x + 0.7, 0.7, 0.0), (x - 0.7, 0.7, 0.0)],
                    [],
                    [(0, 1, 2, 3)],
                )
                obj = bpy.data.objects.new(name, mesh)
                obj.data.materials.append(material)
                target.collection.objects.link(obj)
                for frame in (1, 2):
                    obj.hide_render = frame != visible_frame
                    obj.keyframe_insert(data_path="hide_render", frame=frame)
                for curve in obj.animation_data.action.fcurves:
                    for point in curve.keyframe_points:
                        point.interpolation = "CONSTANT"
                return obj

            ranked = animated_panel("ranked full chain", -0.8, emission("ranked red", (1.0, 0.0, 0.0)), 1)
            nee = animated_panel("NEE full chain", 0.8, emission("NEE green", (0.0, 1.0, 0.0)), 2)
            target.frame_set(2)
            bpy.context.window.scene = decoy

            written = render_prepared_frames(
                {{"ranked_paths": target}},
                {str(renders)!r},
                "ranked_paths",
                frames=(1, 2),
                resolution_scale=0.5,
            )

            channels = []
            hashes = []
            for filename in written:
                path = pathlib.Path(filename)
                hashes.append(hashlib.sha256(path.read_bytes()).hexdigest())
                image = bpy.data.images.load(str(path), check_existing=False)
                pixels = list(image.pixels)
                channels.append([sum(pixels[index::4]) for index in range(3)])
                bpy.data.images.remove(image)

            first_restore = [bpy.context.scene.name, bpy.context.scene.frame_current]
            bpy.context.window.scene = target
            bpy.context.window.view_layer = prior_layer
            target.frame_set(2)
            render_prepared_frames(
                {{"ranked_paths": target}},
                {str(tmp_path / "same-scene")!r},
                "ranked_paths",
                frames=(1,),
                layer_name=target.view_layers[0].name,
            )
            same_scene_restore = [
                bpy.context.scene.name,
                bpy.context.view_layer.name,
                bpy.context.scene.frame_current,
            ]

            pathlib.Path({str(report)!r}).write_text(json.dumps({{
                "written": written,
                "hashes": hashes,
                "channels": channels,
                "first_restore": first_restore,
                "same_scene_restore": same_scene_restore,
                "target_frame": target.frame_current,
                "target_filepath": target.render.filepath,
                "target_resolution": [target.render.resolution_x, target.render.resolution_y],
                "ranked_visible": not ranked.hide_render,
                "nee_visible": not nee.hide_render,
            }}))
            """
        )
    )
    result = subprocess.run(
        [str(BLENDER), "--background", "--factory-startup", "--python", str(script)],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-3000:]
    assert report.exists(), result.stdout[-3000:] + result.stderr[-3000:]
    measured = json.loads(report.read_text())
    assert [pathlib.Path(path).name for path in measured["written"]] == [
        "ranked_paths_frame_0001.png",
        "ranked_paths_frame_0002.png",
    ]
    assert all(pathlib.Path(path).is_file() for path in measured["written"])
    assert measured["hashes"][0] != measured["hashes"][1]
    assert measured["channels"][0][0] > measured["channels"][0][1] * 2.0
    assert measured["channels"][1][1] > measured["channels"][1][0] * 1.5
    assert measured["first_restore"] == ["decoy scene", 11]
    assert measured["same_scene_restore"] == ["prepared animation", "prior audit layer", 2]
    assert measured["target_frame"] == 2
    assert measured["target_filepath"] == "/tmp/original-prepared-path"
    assert measured["target_resolution"] == [48, 48]
    assert not measured["ranked_visible"]
    assert measured["nee_visible"]


@pytest.mark.skipif(not BLENDER.is_file(), reason="Blender is not installed at the default location")
def test_full_support_and_fused_atlas_are_exact_separate_layers(tmp_path: pathlib.Path) -> None:
    study = pathlib.Path(__file__).resolve().parents[1]
    report = tmp_path / "support.json"
    script = tmp_path / "support_probe.py"
    script.write_text(
        textwrap.dedent(
            f"""
            import json
            import pathlib
            import sys

            import bpy
            import numpy as np

            sys.path.insert(0, {str(study)!r})
            from semantic_twin.viz.blender import scene

            scene.reset_scene()
            vertices = np.array([
                [-0.2, -0.2, 0.0], [0.2, -0.2, 0.0], [0.0, 0.2, 0.0],
                [1.8, -0.2, 0.0], [2.2, -0.2, 0.0], [2.0, 0.2, 0.0],
            ])
            faces = np.array([[0, 1, 2], [3, 4, 5]])
            inner = scene.build_mesh(
                "support_mesh",
                vertices[:3],
                np.array([[0, 1, 2]]),
                scene.collection("twin"),
            )
            payload = {{
                "support_full_vertices": vertices,
                "support_full_faces": faces,
                "support_full_face_class": np.array([2, 5]),
                "support_full_face_index": np.array([40, 41]),
                "atlas_vertices": vertices[:3] + np.array([0.0, 0.0, 0.01]),
                "atlas_faces": np.array([[0, 1, 2]]),
                "atlas_entity": np.array([7]),
                "atlas_material": np.array([2]),
                "atlas_confidence": np.array([0.8]),
                "atlas_camera_count": np.array([4]),
                "atlas_observation_count": np.array([12]),
                "atlas_material_probabilities": np.array([[0.1, 0.7, 0.2]]),
            }}
            manifest = {{
                "site": "fixture",
                "frequency_hz": 15.0e9,
                "drawn_radius_m": 1.0,
                "traced_crop_radius_m": 3.0,
                "hero": {{"sky_fraction": 0.5, "susceptibility": {{"rooftop": 0.25}}}},
                "surface_atlas": {{
                    "content_sha256": "a" * 64,
                    "mesh_sha256": "b" * 64,
                    "vocabularies": {{
                        "entity": [f"entity {{index}}" for index in range(8)],
                        "material": ["unknown", "brick", "glass"],
                    }},
                }},
            }}
            support = scene.build_support_display(
                payload,
                manifest,
                inner,
                scene.collection("outer_support"),
                scene.collection("support_extent"),
                ground_z_m=0.0,
            )
            atlas = scene.build_fused_semantic_surface(
                payload,
                manifest,
                scene.collection("fused_semantics"),
            )
            camera = scene.build_full_support_camera(
                np.array([0.0, 0.0, 1.5]),
                3.0,
                scene.collection("cameras"),
            )
            empty_outer = scene.collection("outer_empty")
            empty_inner = scene.build_mesh(
                "support_mesh_without_outer_annulus",
                vertices[:3],
                np.array([[0, 1, 2]]),
                scene.collection("inner_empty"),
            )
            empty_support = scene.build_support_display(
                {{
                    "support_full_vertices": vertices[:3],
                    "support_full_faces": np.array([[0, 1, 2]]),
                    "support_full_face_class": np.array([2]),
                }},
                {{"drawn_radius_m": 1.0, "traced_crop_radius_m": 1.0}},
                empty_inner,
                empty_outer,
                scene.collection("extent_empty"),
                ground_z_m=0.0,
            )
            original_outer = scene.BUILT["outer_support"]
            scene.BUILT["outer_support"] = empty_outer
            scene.stamp_scene(
                manifest,
                rays={{}},
                legs={{}},
                connections={{}},
                layers={{}},
                root=pathlib.Path({str(study)!r}),
            )
            stamped_reading_note = bpy.context.scene["reading_note"]
            stamped_atlas_provenance = json.loads(bpy.context.scene["surface_atlas_provenance"])
            stamped_entity_vocabulary = json.loads(bpy.context.scene["surface_atlas_entity_vocabulary"])
            stamped_material_vocabulary = json.loads(bpy.context.scene["surface_atlas_material_vocabulary"])
            scene.BUILT["outer_support"] = original_outer
            outer = bpy.data.objects["support_mesh_outer"]
            fused = bpy.data.objects["all_camera_fused_surface_atlas"]
            result = {{
                "support": support,
                "atlas": atlas,
                "outer_faces": len(outer.data.polygons),
                "outer_source_face": int(outer.data.attributes["source_face_index"].data[0].value),
                "outer_class": int(outer.data.attributes["surface_class_id"].data[0].value),
                "rings": len(scene.BUILT["support_extent"].objects),
                "fused_faces": len(fused.data.polygons),
                "fused_layers": list(fused["colour_layers"]),
                "material_probability_channels": fused["material_probability_channels"],
                "material_probability_attributes": list(fused["material_probability_attributes"]),
                "material_probability_names": json.loads(fused["material_probability_names"]),
                "fused_role": fused["surface_role"],
                "transport_role": fused["transport_role"],
                "changes_transport": fused["changes_transport"],
                "atlas_drives_transport": fused["atlas_drives_supported_hit_transport"],
                "display_winner_changes_transport": fused["display_winner_changes_transport"],
                "is_transport_geometry": fused["is_transport_geometry"],
                "entity_vocabulary": json.loads(fused["entity_vocabulary"]),
                "material_vocabulary": json.loads(fused["material_vocabulary"]),
                "entity_legend": json.loads(fused["entity_colour_legend"]),
                "material_legend": json.loads(fused["material_colour_legend"]),
                "provenance": json.loads(fused["canonical_surface_atlas_provenance"]),
                "camera": camera.name,
                "camera_type": camera.data.type,
                "camera_scale": camera.data.ortho_scale,
                "camera_subject": camera["framing_subject"],
                "empty_support": empty_support,
                "empty_outer_status": empty_outer["status"],
                "empty_outer_reason": empty_outer["reason"],
                "empty_outer_objects": len(empty_outer.objects),
                "stamped_reading_note": stamped_reading_note,
                "stamped_atlas_provenance": stamped_atlas_provenance,
                "stamped_entity_vocabulary": stamped_entity_vocabulary,
                "stamped_material_vocabulary": stamped_material_vocabulary,
                "collections": {{
                    key: scene.collection(key)["description"]
                    for key in ("twin", "outer_support", "fused_semantics", "semantics", "panoramas", "walk", "arrival")
                }},
            }}
            pathlib.Path({str(report)!r}).write_text(json.dumps(result))
            """
        )
    )
    result = subprocess.run(
        [str(BLENDER), "--background", "--factory-startup", "--python", str(script)],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-3000:]
    measured = json.loads(report.read_text())
    assert measured["support"]["outer_faces"] == 1
    assert measured["outer_faces"] == 1
    assert measured["outer_source_face"] == 41
    assert measured["outer_class"] == 5
    assert measured["rings"] == 2
    assert measured["atlas"] == {"status": "built", "faces": 1}
    assert measured["fused_faces"] == 1
    assert {
        "material_posterior_winner",
        "entity_posterior_winner",
        "confidence",
        "camera_count",
    }.issubset(measured["fused_layers"])
    assert measured["material_probability_channels"] == 3
    assert measured["material_probability_attributes"] == [
        "material_probability_00",
        "material_probability_01",
        "material_probability_02",
    ]
    assert measured["material_probability_names"]["material_probability_02"] == "glass"
    assert measured["fused_role"] == "display audit of joint all-camera entity and material atlas"
    assert "ray-hit positions" in measured["transport_role"]
    assert measured["changes_transport"]
    assert measured["atlas_drives_transport"]
    assert not measured["display_winner_changes_transport"]
    assert not measured["is_transport_geometry"]
    assert measured["entity_vocabulary"][7] == "entity 7"
    assert measured["material_vocabulary"] == ["unknown", "brick", "glass"]
    assert len({tuple(item["rgba"]) for item in measured["entity_legend"]}) == 8
    assert len({tuple(item["rgba"]) for item in measured["material_legend"]}) == 3
    assert measured["provenance"]["content_sha256"] == "a" * 64
    assert measured["camera"] == "cam_full_support"
    assert measured["camera_type"] == "ORTHO"
    assert measured["camera_scale"] == pytest.approx(7.65)
    assert "full traced support" in measured["camera_subject"]
    assert "whole-face geometric fallback" in measured["collections"]["twin"]
    assert "Legacy single-panorama" in measured["collections"]["semantics"]
    assert "source-image locations" in measured["collections"]["panoramas"]
    assert "receiver position" in measured["collections"]["walk"]
    assert "Source-bearing angular power" in measured["collections"]["arrival"]
    assert "k_hat = -local_grid" in measured["collections"]["arrival"]
    assert measured["empty_support"]["outer_faces"] == 0
    assert measured["empty_support"]["full_faces"] == 1
    assert measured["empty_outer_status"] == "empty"
    assert measured["empty_outer_objects"] == 0
    assert measured["empty_outer_reason"] == "the exact full support has no faces outside the close-view radius"
    assert "outer annulus is empty" in measured["stamped_reading_note"]
    assert "legacy payload" not in measured["stamped_reading_note"]
    assert measured["stamped_atlas_provenance"]["content_sha256"] == "a" * 64
    assert measured["stamped_entity_vocabulary"][7] == "entity 7"
    assert measured["stamped_material_vocabulary"] == ["unknown", "brick", "glass"]


@pytest.mark.skipif(not BLENDER.is_file(), reason="Blender is not installed at the default location")
def test_prepared_scenes_share_collections_and_exclude_per_view_layer(tmp_path: pathlib.Path) -> None:
    study = pathlib.Path(__file__).resolve().parents[1]
    report = tmp_path / "views.json"
    blend = tmp_path / "views.blend"
    renders = tmp_path / "renders"
    script = tmp_path / "views_probe.py"
    script.write_text(
        textwrap.dedent(
            f"""
            import json
            import pathlib
            import sys

            import bpy
            import numpy as np

            sys.path.insert(0, {str(study)!r})
            from semantic_twin.viz.blender.scene import build_walk_camera
            from semantic_twin.viz.blender.views import (
                RAW_SCENE_NAME,
                activate_raw_scene,
                build_prepared_scenes,
                prepared_view_specs,
                render_prepared_scenes,
            )

            bpy.ops.wm.read_factory_settings(use_empty=True)
            raw = bpy.context.scene
            keys = []
            for spec in prepared_view_specs():
                for layer in spec.layers:
                    for key in layer.show:
                        if key not in keys:
                            keys.append(key)
            groups = {{}}
            for key in keys:
                group = bpy.data.collections.new(key)
                raw.collection.children.link(group)
                groups[key] = group
            animated = bpy.data.objects.new("prepared frame probe", None)
            groups["nee_animation"].objects.link(animated)
            for frame, hidden in ((1, True), (4, False), (6, True)):
                animated.hide_render = hidden
                animated.hide_viewport = hidden
                animated.keyframe_insert(data_path="hide_render", frame=frame)
                animated.keyframe_insert(data_path="hide_viewport", frame=frame)
            for curve in animated.animation_data.action.fcurves:
                for point in curve.keyframe_points:
                    point.interpolation = "CONSTANT"
            for name in (
                "cam_overview",
                "cam_body",
                "cam_lobe",
                "cam_rays",
                "cam_path_animation",
                "cam_evidence",
                "cam_full_support",
            ):
                camera = bpy.data.objects.new(name, bpy.data.cameras.new(name))
                groups["cameras"].objects.link(camera)
            twin_mesh = bpy.data.meshes.new("empty support")
            twin_mesh.from_pydata([], [], [])
            twin = bpy.data.objects.new("empty support", twin_mesh)
            raw.collection.objects.link(twin)
            walk_points = np.array([
                [-2.0, -24.0, 1.5],
                [0.0, 0.0, 1.5],
                [2.0, 24.0, 1.5],
            ])
            walk_camera = build_walk_camera(twin, walk_points, groups["cameras"], aspect=16.0 / 9.0)
            raw["animation_path_frames"] = [1, 3]
            raw["animation_nee_frames"] = [4, 5]
            raw.frame_start = 1
            raw.frame_end = 5
            raw.render.resolution_x = 32
            raw.render.resolution_y = 32
            raw.render.resolution_percentage = 100
            def panorama_hook(prepared_scene):
                overlay = bpy.data.collections.new("panorama hook overlay")
                overlay["panorama_overlay_collection"] = True
                overlay["panorama_overlay_role"] = "support registration overlay"
                prepared_scene.collection.children.link(overlay)
                acquisition = bpy.data.collections.new("panorama hook acquisitions")
                acquisition["panorama_overlay_collection"] = True
                acquisition["panorama_overlay_role"] = "registered acquisition cameras and projection planes"
                prepared_scene.collection.children.link(acquisition)

            made = build_prepared_scenes(raw, groups, panorama_hook=panorama_hook)
            bpy.ops.wm.save_as_mainfile(filepath={str(blend)!r})
            bpy.ops.wm.open_mainfile(filepath={str(blend)!r})

            raw = bpy.data.scenes[RAW_SCENE_NAME]
            made = {{
                spec.key: bpy.data.scenes[spec.name]
                for spec in prepared_view_specs()
                if spec.name in bpy.data.scenes
            }}
            groups = {{key: bpy.data.collections[key] for key in keys}}
            walk_camera = bpy.data.objects["cam_walk"]
            animated = bpy.data.objects["prepared frame probe"]
            rendered = render_prepared_scenes(
                made,
                {str(renders)!r},
                only=("exposure_overview", "nee_explainer"),
                resolution_scale=0.5,
            )
            rendered_scene = bpy.context.scene.name
            rendered_frame = bpy.context.scene.frame_current
            animated_visible = not animated.hide_render
            first_resolution = [made["exposure_overview"].render.resolution_x, made["exposure_overview"].render.resolution_y]
            render_prepared_scenes(
                made,
                {str(renders)!r},
                only=("exposure_overview",),
                resolution_scale=0.5,
            )
            second_resolution = [made["exposure_overview"].render.resolution_x, made["exposure_overview"].render.resolution_y]
            raw.view_layers[0].layer_collection.children[groups["twin"].name].exclude = True
            activate_raw_scene(raw, clear_root_exclusions=True)

            result = {{
                "raw": raw.name,
                "raw_root_excluded": any(
                    child.exclude for child in raw.view_layers[0].layer_collection.children
                ),
                "walk_camera": {{
                    "name": walk_camera.name,
                    "type": walk_camera.data.type,
                    "scale": walk_camera.data.ortho_scale,
                    "span": walk_camera["walk_route_span_m"],
                    "subject": walk_camera["framing_subject"],
                }},
                "readme": bpy.data.texts["README_START_HERE"].as_string(),
                "rendered": rendered,
                "rendered_scene": rendered_scene,
                "rendered_frame": rendered_frame,
                "animated_visible": animated_visible,
                "first_resolution": first_resolution,
                "second_resolution": second_resolution,
                "panorama_overlay_excluded": {{
                    layer.name: layer.layer_collection.children["panorama hook overlay"].exclude
                    for layer in made["panorama_registration"].view_layers
                }},
                "panorama_acquisition_excluded": {{
                    layer.name: layer.layer_collection.children["panorama hook acquisitions"].exclude
                    for layer in made["panorama_registration"].view_layers
                }},
                "views": {{}},
            }}
            for key, scene in made.items():
                layers = {{}}
                for layer in scene.view_layers:
                    layers[layer.name] = sorted(
                        name for name, group in groups.items()
                        if layer.layer_collection.children[group.name].exclude
                    )
                layers_expected = {{
                    layer.name: sorted(set(groups).difference(layer.show))
                    for layer in next(spec for spec in prepared_view_specs() if spec.key == key).layers
                }}
                result["views"][key] = {{
                    "name": scene.name,
                    "camera": scene.camera.name,
                    "frame_range": [scene.frame_start, scene.frame_end],
                    "layers": layers,
                    "layers_expected": layers_expected,
                    "shared": all(scene.collection.children[group.name] == group for group in groups.values()),
                    "global_hide_render": any(group.hide_render for group in groups.values()),
                }}
            pathlib.Path({str(report)!r}).write_text(json.dumps(result))
            """
        )
    )
    result = subprocess.run(
        [str(BLENDER), "--background", "--factory-startup", "--python", str(script)],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-3000:]
    assert report.exists(), result.stdout[-3000:] + result.stderr[-3000:]
    measured = json.loads(report.read_text())
    assert measured["raw"] == RAW_SCENE_NAME
    assert not measured["raw_root_excluded"]
    assert measured["walk_camera"]["name"] == "cam_walk"
    assert measured["walk_camera"]["type"] == "ORTHO"
    assert 30.0 < measured["walk_camera"]["scale"] < 40.0
    assert 48.0 < measured["walk_camera"]["span"] < 49.0
    assert measured["walk_camera"]["subject"] == "exact walk_points bounds"
    assert "200,000-ray GPU escape transport" in measured["readme"]
    assert "separate 1,200-ray visual retrace" in measured["readme"]
    assert "exact inner support" in measured["readme"]
    assert "exact muted outer support" in measured["readme"]
    assert "reference markers, not propagation surfaces" in measured["readme"]
    assert "not mapped transmitters" in measured["readme"]
    assert len(measured["rendered"]) == 2
    assert all(pathlib.Path(path).is_file() for path in measured["rendered"])
    assert measured["rendered_scene"] == "05 VIEW - NEE explainer"
    assert measured["rendered_frame"] == 4
    assert measured["animated_visible"]
    assert measured["first_resolution"] == [16, 16]
    assert measured["second_resolution"] == [16, 16]
    assert measured["panorama_overlay_excluded"] == {
        "Registered photograph": False,
        "Panorama capture poses": True,
        "Exposure standpoints": True,
    }
    assert measured["panorama_acquisition_excluded"] == {
        "Registered photograph": True,
        "Panorama capture poses": False,
        "Exposure standpoints": True,
    }
    assert len(measured["views"]) == 9
    for view in measured["views"].values():
        assert view["shared"]
        assert not view["global_hide_render"]
        assert view["layers"] == view["layers_expected"]
    assert measured["views"]["ranked_paths"]["frame_range"] == [1, 3]
    assert measured["views"]["nee_explainer"]["frame_range"] == [4, 5]
