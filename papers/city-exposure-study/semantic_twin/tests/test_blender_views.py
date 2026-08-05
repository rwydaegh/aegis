from __future__ import annotations

import json
import pathlib
import subprocess
import textwrap

import pytest

from semantic_twin.viz.blender.views import (
    PANORAMA_VIEW_KEY,
    RAW_SCENE_NAME,
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
    ]
    assert len({view.key for view in specs}) == len(specs)
    assert next(view for view in specs if view.key == "ranked_paths").frame_range_property == "animation_path_frames"
    assert next(view for view in specs if view.key == "nee_explainer").frame_range_property == "animation_nee_frames"
    panorama = next(view for view in specs if view.key == PANORAMA_VIEW_KEY)
    assert panorama.camera == "cam_evidence"
    assert panorama.layers[0].show == ("twin",)
    assert next(view for view in specs if view.key == "exposure_overview").camera == "cam_walk"
    nee = next(view for view in specs if view.key == "nee_explainer")
    assert nee.layers[0].show == ("twin", "body", "nee_animation")


def test_collection_exclusions_are_explicit_and_reject_unknown_keys() -> None:
    available = ("twin", "walk", "body", "rays", "cameras")
    layer = prepared_view_specs()[0].layers[0]
    assert excluded_collection_keys(layer, available) == ("body", "rays", "cameras")
    with pytest.raises(KeyError, match="unknown collections"):
        excluded_collection_keys(type(layer)("broken", ("twin", "missing")), available)


BLENDER = pathlib.Path.home() / "blender-4.5" / "blender"


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
            for name in ("cam_overview", "cam_body", "cam_lobe", "cam_rays", "cam_evidence"):
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
            made = build_prepared_scenes(raw, groups)
            for scene in bpy.data.scenes:
                scene.render.resolution_x = 32
                scene.render.resolution_y = 32
                scene.render.resolution_percentage = 100
            bpy.ops.wm.save_as_mainfile(filepath={str(blend)!r})
            bpy.ops.wm.open_mainfile(filepath={str(blend)!r})

            raw = bpy.data.scenes[RAW_SCENE_NAME]
            made = {{spec.key: bpy.data.scenes[spec.name] for spec in prepared_view_specs()}}
            groups = {{key: bpy.data.collections[key] for key in keys}}
            walk_camera = bpy.data.objects["cam_walk"]
            animated = bpy.data.objects["prepared frame probe"]
            rendered = render_prepared_scenes(
                made,
                {str(renders)!r},
                only=("exposure_overview", "nee_explainer"),
            )
            rendered_scene = bpy.context.scene.name
            rendered_frame = bpy.context.scene.frame_current
            animated_visible = not animated.hide_render
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
    assert "displayed city mesh reaches 110 m" in measured["readme"]
    assert "support out to 250 m" in measured["readme"]
    assert "not mapped transmitters" in measured["readme"]
    assert len(measured["rendered"]) == 2
    assert all(pathlib.Path(path).is_file() for path in measured["rendered"])
    assert measured["rendered_scene"] == "05 VIEW - NEE explainer"
    assert measured["rendered_frame"] == 4
    assert measured["animated_visible"]
    assert len(measured["views"]) == 8
    for view in measured["views"].values():
        assert view["shared"]
        assert not view["global_hide_render"]
        assert view["layers"] == view["layers_expected"]
    assert measured["views"]["ranked_paths"]["frame_range"] == [1, 3]
    assert measured["views"]["nee_explainer"]["frame_range"] == [4, 5]
