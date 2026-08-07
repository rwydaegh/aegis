"""Route-aligned body yaw is ordered walk metadata, not panorama metadata."""

from __future__ import annotations

import numpy as np
import pytest

from semantic_twin.walk import (
    BODY_YAW_CONVENTION,
    BODY_YAW_FALLBACK,
    GRID,
    PANORAMA_LINKS,
    Walk,
    body_yaw_array_hash,
    orient_route_walk,
    route_body_yaw_deg,
)
from semantic_twin.walk.site import _keep_near_the_street
from semantic_twin.exposure.reuse import _valid_route_rows
from semantic_twin.runconfig import RunConfig


def _route(points: np.ndarray) -> Walk:
    return Walk(
        points=np.asarray(points, dtype=float),
        ground_z_m=np.zeros(len(points)),
        step_m=np.zeros(len(points)),
        provenance={},
        kind=PANORAMA_LINKS,
        site="test",
    )


def test_route_yaw_uses_centered_tangents_and_enu_azimuth() -> None:
    points = np.array([[0.0, 0.0, 1.5], [1.0, 1.0, 1.5], [3.0, 1.0, 1.5]])
    yaw, fallback_count = route_body_yaw_deg(points)

    assert yaw == pytest.approx([45.0, 71.5650511771, 90.0])
    assert fallback_count == 0


def test_corner_and_uneven_straight_spacing_keep_the_expected_headings() -> None:
    corner, fallback_count = route_body_yaw_deg(np.array([[0.0, 0.0, 1.5], [10.0, 0.0, 1.5], [10.0, 10.0, 1.5]]))
    uneven, uneven_fallback_count = route_body_yaw_deg(
        np.array([[0.0, 0.0, 1.5], [0.0, 3.0, 1.5], [0.0, 40.0, 1.5], [0.0, 100.0, 1.5]])
    )

    assert corner == pytest.approx([90.0, 45.0, 0.0])
    assert fallback_count == 0
    assert uneven == pytest.approx([0.0, 0.0, 0.0, 0.0])
    assert uneven_fallback_count == 0


def test_reversing_a_route_reverses_every_defined_yaw() -> None:
    points = np.array([[0.0, 0.0, 1.5], [1.0, 1.0, 1.5], [3.0, 1.0, 1.5]])
    forward, _ = route_body_yaw_deg(points)
    reverse, _ = route_body_yaw_deg(points[::-1])

    assert reverse == pytest.approx((forward[::-1] + 180.0) % 360.0)


def test_zero_motion_fallback_is_deterministic_and_recorded() -> None:
    walk = orient_route_walk(_route([[0.0, 0.0, 1.5], [0.0, 0.0, 1.5], [2.0, 0.0, 1.5]]))

    assert walk.body_yaw_deg == pytest.approx([90.0, 90.0, 90.0])
    assert walk.provenance["body_yaw_fallback_count"] == 1
    assert walk.provenance["body_yaw_deg"] == [90.0, 90.0, 90.0]
    assert len(walk.provenance["body_yaw_hash"]) == 64
    assert len(walk.provenance["body_yaw_route_order_hash"]) == 64
    with pytest.raises(ValueError):
        walk.body_yaw_deg[0] = 0.0


def test_all_identical_points_use_the_declared_fallback_for_every_point() -> None:
    points = np.tile(np.array([[2.0, -3.0, 1.5]]), (4, 1))
    yaw, fallback_count = route_body_yaw_deg(points)

    assert yaw == pytest.approx([0.0, 0.0, 0.0, 0.0])
    assert fallback_count == len(points)


def test_provenance_hashes_and_convention_are_stable() -> None:
    first = orient_route_walk(_route([[0.0, 0.0, 1.5], [0.0, 2.0, 1.5], [2.0, 2.0, 1.5]]))
    second = orient_route_walk(_route([[0.0, 0.0, 1.5], [0.0, 2.0, 1.5], [2.0, 2.0, 1.5]]))

    assert first.provenance == second.provenance
    assert first.provenance["body_yaw_convention"] == BODY_YAW_CONVENTION
    assert first.provenance["body_yaw_fallback"] == BODY_YAW_FALLBACK
    assert first.provenance["body_yaw_array_hash"] == body_yaw_array_hash(first.body_yaw_deg)


def test_filtering_discards_provisional_yaw_before_final_orientation() -> None:
    base = orient_route_walk(_route([[0.0, 0.0, 1.5], [10.0, 0.0, 1.5], [20.0, 0.0, 1.5]]))
    filtered = _keep_near_the_street(
        base,
        dict(base.provenance),
        {"polyline_enu": [[0.0, 0.0], [10.0, 0.0]]},
        site="test",
        stride_m=0.0,
    )

    assert filtered.body_yaw_deg is None
    assert "body_yaw_deg" not in filtered.provenance
    final = orient_route_walk(filtered)
    assert final.body_yaw_deg == pytest.approx([90.0, 90.0])
    assert len(final.provenance["body_yaw_deg"]) == len(final.points)


def test_grid_walks_remain_backward_compatible_and_unoriented() -> None:
    grid = Walk(
        points=np.zeros((1, 3)),
        ground_z_m=np.zeros(1),
        step_m=np.zeros(1),
        provenance={},
        kind=GRID,
    )

    assert grid.body_yaw_deg is None
    with pytest.raises(ValueError, match="only applies to route walks"):
        orient_route_walk(grid)


def test_walk_rejects_malformed_yaw_alignment() -> None:
    with pytest.raises(ValueError, match="does not match points"):
        Walk(
            points=np.zeros((2, 3)),
            ground_z_m=np.zeros(2),
            step_m=np.zeros(2),
            provenance={},
            kind=PANORAMA_LINKS,
            body_yaw_deg=np.zeros(1),
        )


def test_walk_rejects_unsealed_provenance_yaw() -> None:
    with pytest.raises(ValueError, match="requires the sealed"):
        Walk(
            points=np.zeros((1, 3)),
            ground_z_m=np.zeros(1),
            step_m=np.zeros(1),
            provenance={"body_yaw_deg": [0.0]},
            kind=PANORAMA_LINKS,
        )


def test_route_reuse_rejects_a_manifest_without_frozen_yaw() -> None:
    config = RunConfig(site="test", law="band", models=("rooftop",), estimator="escape", walk="route")
    manifest = {
        "walk": {
            "route_geometry": "registered_road_v1",
            "candidates_after_clearance": 1,
            "point_kind": ["camera_registered"],
        }
    }
    rows = [{"index": 0, "point_kind": "camera_registered"}]

    assert not _valid_route_rows(manifest, config, rows)
