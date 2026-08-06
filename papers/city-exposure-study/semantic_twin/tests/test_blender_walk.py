"""The Blender walk keeps its measured QA layer and adds a readable route."""

from __future__ import annotations

import json
import pathlib
import subprocess
import textwrap

import numpy as np
import pytest


BLENDER = pathlib.Path.home() / "blender-4.5" / "blender"


@pytest.mark.skipif(not BLENDER.is_file(), reason="Blender is not installed at the default location")
def test_walk_draws_registered_route_over_exact_susceptibility_markers(tmp_path: pathlib.Path) -> None:
    study = pathlib.Path(__file__).resolve().parents[1]
    report = tmp_path / "walk.json"
    script = tmp_path / "walk_probe.py"
    script.write_text(
        textwrap.dedent(
            f"""
            import json
            import pathlib
            import sys

            import bpy
            import numpy as np

            sys.path.insert(0, {str(study)!r})
            from semantic_twin.viz.blender.estimator import build_walk

            bpy.ops.wm.read_factory_settings(use_empty=True)
            collection = bpy.data.collections.new("walk")
            bpy.context.scene.collection.children.link(collection)
            points = np.column_stack([
                np.arange(13, dtype=np.float64),
                np.linspace(0.0, 3.0, 13),
                np.full(13, 52.4),
            ])
            chi = np.linspace(0.1, 0.7, 13)
            kinds = [
                "camera_registered", "stride_interpolated", "stride_interpolated",
                "camera_registered", "stride_interpolated", "stride_interpolated",
                "camera_registered", "stride_interpolated", "stride_interpolated",
                "camera_registered", "stride_interpolated", "stride_interpolated",
                "camera_registered",
            ]
            measured_range = build_walk(
                {{
                    "walk_points": points,
                    "walk_chi_rooftop": chi,
                    "hero_index": np.array(6),
                }},
                collection,
                "rooftop",
                {{"point_kind": kinds}},
                hero_index=6,
            )
            standpoints = bpy.data.objects["walk_standpoints"]
            route = bpy.data.objects["walk_route"]
            camera = bpy.data.objects["walk_camera_registered_points"]
            stride = bpy.data.objects["walk_stride_interpolated_points"]
            exact_db = [item.value for item in standpoints.data.attributes["value_chi_db"].data]
            route_points = [list(item.vector) for item in route.data.attributes["position"].data]
            pathlib.Path({str(report)!r}).write_text(json.dumps({{
                "objects": sorted(obj.name for obj in collection.objects),
                "standpoint_faces": len(standpoints.data.polygons),
                "exact_db": exact_db,
                "colour_quantity": standpoints["colour_quantity"],
                "route_type": route.type,
                "route_curve_types": [item.value for item in route.data.attributes["curve_type"].data],
                "route_points": route_points,
                "route_segments": route["segments"],
                "camera_count": camera["points"],
                "camera_indices": list(camera["walk_indices"]),
                "stride_count": stride["points"],
                "stride_indices": list(stride["walk_indices"]),
                "start_index": bpy.data.objects["walk_start_marker"]["walk_index"],
                "hero_index": bpy.data.objects["walk_hero_marker"]["walk_index"],
                "end_index": bpy.data.objects["walk_end_marker"]["walk_index"],
                "range": list(measured_range),
            }}))
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

    measured = json.loads(report.read_text())
    expected_db = 10.0 * np.log10(np.linspace(0.1, 0.7, 13))
    assert measured["standpoint_faces"] == 13 * 8
    assert np.allclose(np.asarray(measured["exact_db"]).reshape(13, 8), expected_db[:, None])
    assert measured["colour_quantity"] == ("10 log10(max(dimensionless rooftop susceptibility chi, 1e-12)), in dB")
    assert measured["route_type"] == "CURVES"
    assert measured["route_curve_types"] == [1]
    assert np.allclose(
        measured["route_points"], np.column_stack([np.arange(13), np.linspace(0, 3, 13), np.full(13, 52.4)])
    )
    assert measured["route_segments"] == 12
    assert measured["camera_count"] == 5
    assert measured["camera_indices"] == [0, 3, 6, 9, 12]
    assert measured["stride_count"] == 8
    assert measured["stride_indices"] == [1, 2, 4, 5, 7, 8, 10, 11]
    assert (measured["start_index"], measured["hero_index"], measured["end_index"]) == (0, 6, 12)
    assert measured["range"] == pytest.approx([float(expected_db.min()), float(expected_db.max())])
    assert {
        "walk_standpoints",
        "walk_route",
        "walk_camera_registered_points",
        "walk_stride_interpolated_points",
        "walk_start_marker",
        "walk_hero_marker",
        "walk_end_marker",
    }.issubset(measured["objects"])
