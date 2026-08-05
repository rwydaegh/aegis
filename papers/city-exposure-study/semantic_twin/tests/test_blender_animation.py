"""The readable path and NEE animation added to propagation blends."""

from __future__ import annotations

import json
import pathlib
import subprocess
import textwrap

import numpy as np
import pytest

from semantic_twin.illumination import fibonacci_sphere, nearest_cell
from semantic_twin.viz.blender.animation import rank_rooftop_visual_paths


BLENDER = pathlib.Path.home() / "blender-4.5" / "blender"


def animation_payload() -> dict[str, np.ndarray]:
    """Five records with cell normalisation, a bounce and two exclusions."""
    grid = fibonacci_sphere(8)
    origin = np.zeros(3)
    exit_direction = np.array([np.cos(np.radians(10.0)), 0.0, np.sin(np.radians(10.0))])
    direct_cell = int(nearest_cell(exit_direction[None, :], grid)[0])
    bounced_cell = (direct_cell + 3) % grid.shape[0]
    paths = [
        np.array([origin, 200.0 * exit_direction]),
        np.array([origin, 4.0 * grid[bounced_cell], 4.0 * grid[bounced_cell] + 200.0 * exit_direction]),
        np.array([origin, [111.0, 0.0, 1.0], [211.0, 0.0, 20.0]]),
        np.array([origin, grid[3], grid[3]]),
        np.array([origin, 200.0 * exit_direction]),
    ]
    power = [
        np.array([1.0, 1.0]),
        np.array([1.0, 0.6, 0.6]),
        np.array([1.0, 0.9, 0.9]),
        np.array([1.0, 0.8, 0.8]),
        np.array([1.0, 1.0]),
    ]
    payload = {
        "path_vertices": np.concatenate(paths),
        "path_offsets": np.concatenate([[0], np.cumsum([len(path) for path in paths])]),
        "path_throughput": np.concatenate(power),
        "path_exit_direction": np.tile(exit_direction, (len(paths), 1)),
        "path_termination": np.array([0, 0, 0, 1, 0]),
        "path_bounces": np.array([0, 1, 1, 1, 0]),
        "local_grid": grid,
    }
    bounce = paths[1][1]
    payload.update(
        {
            "nee_paths": np.array([1]),
            "nee_path_index": np.array([1, 1]),
            "nee_vertex_index": np.array([0, 1]),
            "nee_origin_m": np.array([origin, bounce]),
            "nee_site_m": np.array([[20.0, 4.0, 12.0], [22.0, -3.0, 14.0]]),
            "nee_weight": np.array([0.02, 0.03]),
            "nee_blocked": np.array([False, True]),
        }
    )
    return payload


def test_rooftop_visual_ranking_uses_cell_normalised_escape_contribution() -> None:
    payload = animation_payload()
    ranked = rank_rooftop_visual_paths(payload, ("sky", "roulette", "truncated"), count=4, drawn_radius_m=110.0)

    assert ranked.path_index.tolist() == [1, 0, 4]
    assert ranked.bounces.tolist() == [1, 0, 0]
    assert ranked.departure_cell_count.tolist() == [1, 3, 3]
    assert ranked.paths_left_out_beyond_drawn_support.tolist() == [2]
    assert np.all(np.diff(ranked.score) <= 0.0)
    assert ranked.score[0] > ranked.score[1], "cell normalisation makes the bounced path the strongest sample"


@pytest.mark.skipif(not BLENDER.is_file(), reason="Blender is not installed at the default location")
def test_animation_keeps_one_poly_path_visible_per_frame_after_reopen(tmp_path: pathlib.Path) -> None:
    study = pathlib.Path(__file__).resolve().parents[1]
    payload_path = tmp_path / "animation_payload.npz"
    np.savez(payload_path, **animation_payload())
    blend = tmp_path / "animation.blend"
    report = tmp_path / "animation.json"
    script = tmp_path / "animation_probe.py"
    script.write_text(
        textwrap.dedent(
            f"""
            import json
            import pathlib
            import sys

            import bpy
            import numpy as np

            sys.path.insert(0, {str(study)!r})
            from semantic_twin.viz.blender import animation, scene

            payload = np.load({str(payload_path)!r})
            scene.reset_scene()
            scene.add_camera("cam_rays", (0.0, -10.0, 8.0), (0.0, 0.0, 0.0), scene.collection("cameras"))
            summary = animation.build_path_animation(
                payload,
                ("sky", "roulette", "truncated"),
                path_collection=scene.collection("path_animation"),
                nee_collection=scene.collection("nee_animation"),
                dense_ray_collection=scene.collection("rays"),
                dense_bounce_collection=scene.collection("bounces"),
                drawn_radius_m=110.0,
                ranked_count=3,
                nee_count=1,
            )
            bpy.ops.wm.save_as_mainfile(filepath={str(blend)!r}, compress=True)
            bpy.ops.wm.open_mainfile(filepath={str(blend)!r})
            group = bpy.data.collections["16 ranked path animation"]
            nee_group = bpy.data.collections["17 NEE explanation animation"]
            visible = []
            labels = []
            curve_types = []
            interpolation = []
            for frame in range(1, 4):
                bpy.context.scene.frame_set(frame)
                live = {{
                    int(obj["visual_trace_path_index"])
                    for obj in group.objects
                    if not obj.hide_viewport and "visual_trace_path_index" in obj
                }}
                visible.append(sorted(live))
                labels.append([obj["label_text"] for obj in group.objects if not obj.hide_viewport and "label_text" in obj])
            bpy.context.scene.frame_set(4)
            nee_visible = sorted({{
                int(obj["visual_trace_path_index"])
                for obj in nee_group.objects
                if not obj.hide_viewport and "visual_trace_path_index" in obj
            }})
            nee_labels = [
                obj["label_text"] for obj in nee_group.objects if not obj.hide_viewport and "label_text" in obj
            ]
            for obj in group.objects:
                if obj.type == "CURVES":
                    curve_types.extend(item.value for item in obj.data.attributes["curve_type"].data)
                for curve in obj.animation_data.action.fcurves:
                    interpolation.extend(point.interpolation for point in curve.keyframe_points)
            pathlib.Path({str(report)!r}).write_text(json.dumps({{
                "summary": summary,
                "visible": visible,
                "labels": labels,
                "nee_visible": nee_visible,
                "nee_labels": nee_labels,
                "curve_types": curve_types,
                "interpolation": interpolation,
                "fps": bpy.context.scene.render.fps,
                "dense_preserved": (
                    not bpy.data.collections["09 ray paths by fate"].hide_viewport
                    and bpy.data.collections["09 ray paths by fate"].get("role", "").startswith("static dense overview")
                ),
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
    assert "Traceback" not in result.stdout + result.stderr, result.stdout[-4000:] + result.stderr[-4000:]
    assert report.is_file(), result.stdout[-4000:] + result.stderr[-4000:]
    measured = json.loads(report.read_text())
    assert measured["summary"]["strongest_path_index"] == 1
    assert measured["visible"] == [[1], [0], [4]]
    assert "not a production MPC" in measured["labels"][0][0]
    assert "RANK 01" in measured["labels"][0][0]
    assert measured["nee_visible"] == [1]
    assert "post-bounce origin" in measured["nee_labels"][0]
    assert "no dose value" in measured["nee_labels"][0]
    assert set(measured["curve_types"]) == {1}
    assert set(measured["interpolation"]) == {"CONSTANT"}
    assert measured["fps"] == 1
    assert measured["dense_preserved"]
