"""The readable path and NEE animation added to propagation blends."""

from __future__ import annotations

import json
import pathlib
import subprocess
import textwrap

import numpy as np
import pytest

from semantic_twin.illumination import fibonacci_sphere, nearest_cell
from semantic_twin.viz.blender.animation import (
    ANIMATION_CAMERA_NAME,
    _arrowhead_geometry,
    nee_candidate_chain_points,
    rank_rooftop_visual_paths,
)

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
            "nee_path_index": np.array([1, 1, 1]),
            "nee_vertex_index": np.array([0, 1, 1]),
            "nee_origin_m": np.array([origin, bounce, bounce]),
            "nee_site_m": np.array([[20.0, 4.0, 12.0], [21.0, 3.0, 13.0], [22.0, -3.0, 14.0]]),
            "nee_weight": np.array([0.02, 0.04, 0.03]),
            "nee_blocked": np.array([False, False, True]),
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


def test_rooftop_visual_ranking_accepts_zero_and_rejects_negative_counts() -> None:
    payload = animation_payload()
    ranked = rank_rooftop_visual_paths(
        payload,
        ("sky", "roulette", "truncated"),
        count=0,
        drawn_radius_m=110.0,
    )

    assert ranked.path_index.shape == (0,)
    assert ranked.score.shape == (0,)
    assert ranked.positive_sky_paths == 4
    with pytest.raises(ValueError, match="non-negative"):
        rank_rooftop_visual_paths(
            payload,
            ("sky", "roulette", "truncated"),
            count=-1,
            drawn_radius_m=110.0,
        )


def test_nee_candidate_chain_uses_only_reverse_prefix_to_receiver() -> None:
    payload = animation_payload()
    source = payload["nee_site_m"][2]
    chain = nee_candidate_chain_points(
        payload,
        path_index=1,
        vertex_index=1,
        site=source,
        recorded_origin=payload["nee_origin_m"][2],
    )

    start = payload["path_offsets"][1]
    assert np.allclose(chain, np.vstack([source, payload["path_vertices"][start + 1], [0.0, 0.0, 0.0]]))
    assert not np.any(np.all(np.isclose(chain, payload["path_vertices"][start + 2]), axis=1))


def test_nee_candidate_chain_rejects_mismatched_recorded_origin() -> None:
    payload = animation_payload()
    with pytest.raises(ValueError, match="does not match"):
        nee_candidate_chain_points(
            payload,
            path_index=1,
            vertex_index=1,
            site=payload["nee_site_m"][1],
            recorded_origin=np.array([99.0, 99.0, 99.0]),
        )


def test_nee_candidate_chain_omits_later_reflections_from_the_sbr_suffix() -> None:
    receiver = np.array([0.0, 0.0, 1.7])
    selected = np.array([4.0, 0.0, 2.0])
    unused_bounce = np.array([8.0, 3.0, 4.0])
    unused_escape_proxy = np.array([30.0, 9.0, 14.0])
    payload = {
        "path_vertices": np.vstack([receiver, selected, unused_bounce, unused_escape_proxy]),
        "path_offsets": np.array([0, 4]),
    }
    source = np.array([12.0, -4.0, 18.0])

    chain = nee_candidate_chain_points(
        payload,
        path_index=0,
        vertex_index=1,
        site=source,
        recorded_origin=selected,
    )

    assert np.allclose(chain, np.vstack([source, selected, receiver]))
    assert not np.any(np.all(np.isclose(chain, unused_bounce), axis=1))
    assert not np.any(np.all(np.isclose(chain, unused_escape_proxy), axis=1))


def test_escape_arrowhead_points_in_the_requested_direction() -> None:
    tip = np.array([2.0, 3.0, 4.0])
    direction = np.array([-1.0, 0.0, 0.0])
    vertices, faces = _arrowhead_geometry(tip, direction, length_m=0.9, radius_m=0.3)

    assert np.allclose(vertices[0], tip)
    assert np.all(vertices[1:, 0] > tip[0])
    assert vertices.shape == (5, 3)
    assert faces.shape == (6, 3)


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
            from bpy_extras.object_utils import world_to_camera_view
            from mathutils import Vector

            sys.path.insert(0, {str(study)!r})
            from semantic_twin.viz.blender import animation, scene

            stored = np.load({str(payload_path)!r})
            payload = {{key: stored[key] for key in stored.files}}
            original_exit_direction = payload["path_exit_direction"].copy()
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
                nee_count=2,
            )
            bpy.ops.wm.save_as_mainfile(filepath={str(blend)!r}, compress=True)
            bpy.ops.wm.open_mainfile(filepath={str(blend)!r})
            group = bpy.data.collections["16 ranked path animation"]
            nee_group = bpy.data.collections["17 NEE explanation animation"]
            visible = []
            labels = []
            arrow_counts = []
            ranked_curve_points = []
            camera_bounds = []
            curve_types = []
            interpolation = []
            for frame in range(1, 4):
                bpy.context.scene.frame_set(frame)
                curves = [obj for obj in group.objects if not obj.hide_viewport and obj.type == "CURVES"]
                live = {{
                    int(obj["visual_trace_path_index"])
                    for obj in group.objects
                    if not obj.hide_viewport and "visual_trace_path_index" in obj
                }}
                visible.append(sorted(live))
                labels.append([obj["label_text"] for obj in group.objects if not obj.hide_viewport and "label_text" in obj])
                arrow_counts.append(sum(
                    obj.get("candidate_part") == "incoming travel direction arrow"
                    for obj in group.objects
                    if not obj.hide_viewport
                ))
                ranked_curve_points.append([len(obj.data.attributes["position"].data) for obj in curves])
                projected = [
                    world_to_camera_view(
                        bpy.context.scene,
                        bpy.data.objects[{ANIMATION_CAMERA_NAME!r}],
                        obj.matrix_world @ Vector(point.vector),
                    )
                    for obj in curves
                    for point in obj.data.attributes["position"].data
                ]
                camera_bounds.append({{
                    "x": [min(point.x for point in projected), max(point.x for point in projected)],
                    "y": [min(point.y for point in projected), max(point.y for point in projected)],
                    "z_min": min(point.z for point in projected),
                }})
            nee_frames = []
            for frame in (4, 5):
                bpy.context.scene.frame_set(frame)
                live = [obj for obj in nee_group.objects if not obj.hide_viewport]
                source_links = [obj for obj in live if obj.get("candidate_part", "").startswith("sampled source")]
                prefixes = [obj for obj in live if obj.get("candidate_part", "").startswith("selected scattering")]
                def coordinates(obj):
                    return [list(item.vector) for item in obj.data.attributes["position"].data]
                nee_frames.append({{
                    "paths": sorted({{
                        int(obj["visual_trace_path_index"])
                        for obj in live
                        if "visual_trace_path_index" in obj
                    }}),
                    "records": sorted({{
                        int(obj["nee_record_index"])
                        for obj in live
                        if "nee_record_index" in obj
                    }}),
                    "states": sorted({{
                        obj["connection_state"] for obj in live if "connection_state" in obj
                    }}),
                    "labels": [obj["label_text"] for obj in live if "label_text" in obj],
                    "source_links": [coordinates(obj) for obj in source_links],
                    "prefixes": [coordinates(obj) for obj in prefixes],
                    "unused_suffix": [obj["unused_sbr_suffix_drawn"] for obj in live if "unused_sbr_suffix_drawn" in obj],
                }})
            for obj in group.objects:
                if obj.type == "CURVES":
                    curve_types.extend(item.value for item in obj.data.attributes["curve_type"].data)
                for curve in obj.animation_data.action.fcurves:
                    interpolation.extend(point.interpolation for point in curve.keyframe_points)
            pathlib.Path({str(report)!r}).write_text(json.dumps({{
                "summary": summary,
                "visible": visible,
                "labels": labels,
                "arrow_counts": arrow_counts,
                "ranked_curve_points": ranked_curve_points,
                "camera_bounds": camera_bounds,
                "nee_frames": nee_frames,
                "curve_types": curve_types,
                "interpolation": interpolation,
                "camera_interpolation": sorted({{
                    point.interpolation
                    for curve in bpy.data.objects[{ANIMATION_CAMERA_NAME!r}].animation_data.action.fcurves
                    for point in curve.keyframe_points
                }}),
                "static_camera_unchanged": (
                    list(bpy.data.objects["cam_rays"].location) == [0.0, -10.0, 8.0]
                    and bpy.data.objects["cam_rays"].animation_data is None
                    and bpy.data.objects["cam_rays"].data.clip_end == 8000.0
                ),
                "animation_camera_is_private": (
                    bpy.data.objects[{ANIMATION_CAMERA_NAME!r}].data
                    is not bpy.data.objects["cam_rays"].data
                ),
                "input_directions_unchanged": np.array_equal(
                    payload["path_exit_direction"], original_exit_direction
                ),
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
        check=False,
        text=True,
        timeout=90,
    )
    assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-4000:]
    assert "Traceback" not in result.stdout + result.stderr, result.stdout[-4000:] + result.stderr[-4000:]
    assert report.is_file(), result.stdout[-4000:] + result.stderr[-4000:]
    measured = json.loads(report.read_text())
    assert measured["summary"]["strongest_path_index"] == 1
    assert measured["visible"] == [[1], [0], [4]]
    assert measured["ranked_curve_points"] == [[2, 2], [2], [2]]
    for bounds in measured["camera_bounds"]:
        assert 0.0 < bounds["x"][0] <= bounds["x"][1] < 1.0
        assert 0.0 < bounds["y"][0] <= bounds["y"][1] < 1.0
        assert bounds["z_min"] > 0.0
    assert "not a production MPC" in measured["labels"][0][0]
    assert "VISUAL-RETRACE RANK 01" in measured["labels"][0][0]
    assert measured["arrow_counts"] == [1, 1, 1]
    assert [item["paths"] for item in measured["nee_frames"]] == [[1], [1]]
    assert [item["records"] for item in measured["nee_frames"]] == [[1], [2]]
    assert [item["states"] for item in measured["nee_frames"]] == [["clear"], ["blocked"]]
    assert all("one connected candidate" in item["labels"][0] for item in measured["nee_frames"])
    assert all("no dose value" in item["labels"][0] for item in measured["nee_frames"])
    for item in measured["nee_frames"]:
        assert len(item["source_links"]) == 1
        assert len(item["prefixes"]) == 1
        assert np.allclose(item["source_links"][0][-1], item["prefixes"][0][0])
        assert np.allclose(item["prefixes"][0][-1], [0.0, 0.0, 0.0])
        assert set(item["unused_suffix"]) == {False}
    assert set(measured["curve_types"]) == {1}
    assert set(measured["interpolation"]) == {"CONSTANT"}
    assert measured["camera_interpolation"] == ["CONSTANT"]
    assert measured["static_camera_unchanged"]
    assert measured["animation_camera_is_private"]
    assert measured["input_directions_unchanged"]
    assert measured["fps"] == 1
    assert measured["dense_preserved"]


@pytest.mark.skipif(not BLENDER.is_file(), reason="Blender is not installed at the default location")
def test_zero_animation_counts_remain_empty_after_reopen(tmp_path: pathlib.Path) -> None:
    study = pathlib.Path(__file__).resolve().parents[1]
    payload_path = tmp_path / "animation_payload.npz"
    np.savez(payload_path, **animation_payload())
    blend = tmp_path / "zero_animation.blend"
    report = tmp_path / "zero_animation.json"
    script = tmp_path / "zero_animation_probe.py"
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
            negative_errors = {{}}
            for label, ranked_count, nee_count in (("ranked", -1, 0), ("nee", 0, -1)):
                try:
                    animation.build_path_animation(
                        payload,
                        ("sky", "roulette", "truncated"),
                        path_collection=scene.collection("path_animation"),
                        nee_collection=scene.collection("nee_animation"),
                        dense_ray_collection=scene.collection("rays"),
                        dense_bounce_collection=scene.collection("bounces"),
                        drawn_radius_m=110.0,
                        ranked_count=ranked_count,
                        nee_count=nee_count,
                    )
                except ValueError as error:
                    negative_errors[label] = str(error)
            summary = animation.build_path_animation(
                payload,
                ("sky", "roulette", "truncated"),
                path_collection=scene.collection("path_animation"),
                nee_collection=scene.collection("nee_animation"),
                dense_ray_collection=scene.collection("rays"),
                dense_bounce_collection=scene.collection("bounces"),
                drawn_radius_m=110.0,
                ranked_count=0,
                nee_count=0,
            )
            bpy.ops.wm.save_as_mainfile(filepath={str(blend)!r}, compress=True)
            bpy.ops.wm.open_mainfile(filepath={str(blend)!r})
            pathlib.Path({str(report)!r}).write_text(json.dumps({{
                "summary": summary,
                "negative_errors": negative_errors,
                "path_objects": len(bpy.data.collections["16 ranked path animation"].objects),
                "nee_objects": len(bpy.data.collections["17 NEE explanation animation"].objects),
                "animation_camera_exists": {ANIMATION_CAMERA_NAME!r} in bpy.data.objects,
                "static_camera_action": bpy.data.objects["cam_rays"].animation_data is not None,
                "path_range_exists": "animation_path_frames" in bpy.context.scene,
                "nee_range_exists": "animation_nee_frames" in bpy.context.scene,
                "frame_range": [bpy.context.scene.frame_start, bpy.context.scene.frame_end],
            }}))
            """
        )
    )
    result = subprocess.run(
        [str(BLENDER), "--background", "--factory-startup", "--python", str(script)],
        capture_output=True,
        check=False,
        text=True,
        timeout=90,
    )
    assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-4000:]
    assert "Traceback" not in result.stdout + result.stderr, result.stdout[-4000:] + result.stderr[-4000:]
    measured = json.loads(report.read_text())
    assert measured["summary"] == {
        "ranked_path_frames": 0,
        "nee_frames": 0,
        "frame_range": [1, 1],
        "strongest_path_index": None,
        "strongest_path_bounces": None,
        "strongest_score": None,
    }
    assert "non-negative" in measured["negative_errors"]["ranked"]
    assert "non-negative" in measured["negative_errors"]["nee"]
    assert measured["path_objects"] == 0
    assert measured["nee_objects"] == 0
    assert not measured["animation_camera_exists"]
    assert not measured["static_camera_action"]
    assert not measured["path_range_exists"]
    assert not measured["nee_range_exists"]
    assert measured["frame_range"] == [1, 1]
