"""What the walking path has to get right before it can move a standpoint.

Nothing here reaches the network. The one function that does is passed a stub,
because a test that needs an API key is a test that stops running.
"""

from __future__ import annotations

import json
import pathlib

import numpy as np
import pytest

from semantic_twin.geo import EnuFrame, ecef_to_llh, llh_to_ecef
from semantic_twin.propagation.street import (
    cached_walking_route,
    decode_polyline,
    polyline_enu,
    request_key,
    site_anchor,
)

#: Google's own documented example of the encoded polyline format.
GOOGLE_EXAMPLE = "_p~iF~ps|U_ulLnnqC_mqNvxq`@"


def test_the_documented_example_decodes_to_its_documented_points():
    assert decode_polyline(GOOGLE_EXAMPLE) == [(38.5, -120.2), (40.7, -120.95), (43.252, -126.453)]


def test_an_empty_polyline_decodes_to_nothing():
    assert decode_polyline("") == []


# --- the frame the path has to land in ---------------------------------------


def test_a_point_survives_the_round_trip_through_latitude_and_longitude():
    """The walk knows metres and the routing service knows degrees."""
    frame = EnuFrame(50.84673, 4.35247)
    for point in ([0.0, 0.0, 0.0], [123.4, -56.7, 12.3], [-250.0, 250.0, 0.0]):
        latitude, longitude, height = frame.to_llh(point)
        assert frame.to_enu(latitude, longitude, height) == pytest.approx(point, abs=1.0e-6)


def test_the_inverse_agrees_with_the_forward_conversion_at_altitude():
    for latitude, longitude, height in ((0.0, 0.0, 0.0), (51.05, 3.72, 137.0), (-33.9, 151.2, -12.0)):
        back = ecef_to_llh(llh_to_ecef(latitude, longitude, height))
        assert back[0] == pytest.approx(latitude, abs=1.0e-9)
        assert back[1] == pytest.approx(longitude, abs=1.0e-9)
        assert back[2] == pytest.approx(height, abs=1.0e-4)


def test_a_path_lands_where_the_anchor_says_it_should():
    """A route through the anchor itself passes through the scene origin."""
    anchor = (50.84673, 4.35247)
    route = {"polyline_llh": [(anchor[0], anchor[1]), (anchor[0] + 0.001, anchor[1])]}
    line = polyline_enu(route, anchor)
    assert line[0] == pytest.approx([0.0, 0.0], abs=1.0e-6)
    # A thousandth of a degree of latitude is about 111 m north and no east.
    assert line[1][0] == pytest.approx(0.0, abs=1.0e-3)
    assert line[1][1] == pytest.approx(111.2, abs=0.5)


# --- paying for the route once ------------------------------------------------


def test_the_same_waypoints_are_never_bought_twice(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch):
    """The cache is the whole reason this is safe to leave on by default."""
    calls = []

    def stub(waypoints, **kwargs):
        calls.append(list(waypoints))
        return {
            "distance_m": 100.0,
            "duration": "90s",
            "waypoint_order": None,
            "polyline_llh": [[50.0, 4.0], [50.001, 4.0]],
            "waypoints_llh": [list(p) for p in waypoints],
            "optimised": False,
            "source": "stub",
        }

    monkeypatch.setattr("semantic_twin.propagation.street.fetch_walking_route", stub)
    points = [(50.0, 4.0), (50.001, 4.0)]

    first = cached_walking_route("nowhere", points, root=tmp_path)
    second = cached_walking_route("nowhere", points, root=tmp_path)

    assert len(calls) == 1
    assert first["polyline_llh"] == second["polyline_llh"]
    assert (tmp_path / "data" / "street_routes").is_dir()


def test_a_different_waypoint_set_buys_a_new_route(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch):
    calls = []

    def stub(waypoints, **kwargs):
        calls.append(list(waypoints))
        return {"distance_m": 1.0, "polyline_llh": [(50.0, 4.0)], "source": "stub"}

    monkeypatch.setattr("semantic_twin.propagation.street.fetch_walking_route", stub)
    cached_walking_route("nowhere", [(50.0, 4.0), (50.001, 4.0)], root=tmp_path)
    cached_walking_route("nowhere", [(50.0, 4.0), (50.002, 4.0)], root=tmp_path)
    assert len(calls) == 2


def test_the_cache_name_ignores_a_rounding_difference_and_not_a_real_one():
    """Seven decimals of a degree is a centimetre, which is below any camera."""
    base = [(50.8467300, 4.3524700), (50.8465580, 4.3517429)]
    same = [(50.84673000000001, 4.35247), (50.8465580, 4.3517429)]
    moved = [(50.8467400, 4.3524700), (50.8465580, 4.3517429)]
    assert request_key(base, True) == request_key(same, True)
    assert request_key(base, True) != request_key(moved, True)
    assert request_key(base, True) != request_key(base, False)


# --- the anchor ---------------------------------------------------------------


def test_the_anchor_comes_off_the_mesh_manifest(tmp_path: pathlib.Path):
    directory = tmp_path / "data" / "geometry" / "somewhere"
    directory.mkdir(parents=True)
    (directory / "inhouse_leaf_250m_f64.json").write_text(
        json.dumps({"anchor": {"lat_deg": 12.5, "lon_deg": -7.25, "height_m": 0.0}})
    )
    assert site_anchor("somewhere", tmp_path) == (12.5, -7.25)


def test_a_site_with_no_manifest_says_so_rather_than_guessing(tmp_path: pathlib.Path):
    with pytest.raises(FileNotFoundError):
        site_anchor("somewhere", tmp_path)


# --- picking A and B ----------------------------------------------------------


def test_a_and_b_are_the_two_cameras_furthest_apart():
    from semantic_twin.propagation.route import span_endpoints

    cameras = np.array([[0.0, 0.0, 2.5], [10.0, 0.0, 2.5], [0.0, 60.0, 2.5], [3.0, 3.0, 2.5]])
    assert set(span_endpoints(cameras)) == {1, 2}


def test_height_does_not_decide_which_cameras_are_furthest_apart():
    """The walk is a plan, so a camera on a hill is not further away for it."""
    from semantic_twin.propagation.route import span_endpoints

    # The third camera is 200 m up but only halfway along, so in plan it is the
    # nearest of the three to everything and cannot be an endpoint.
    flat = np.array([[0.0, 0.0, 2.0], [30.0, 0.0, 2.0], [15.0, 0.0, 200.0]])
    assert set(span_endpoints(flat)) == {0, 1}


def test_distance_to_the_path_is_measured_to_the_line_and_not_to_its_corners():
    """A camera beside the middle of a long straight is close to the walk."""
    from semantic_twin.propagation.route import gap_to_path

    line = np.array([[0.0, 0.0], [100.0, 0.0]])
    points = np.array([[50.0, 4.0, 1.7], [50.0, -4.0, 1.7], [-10.0, 0.0, 1.7], [130.0, 0.0, 1.7]])
    assert gap_to_path(points, line) == pytest.approx([4.0, 4.0, 10.0, 30.0])


# --- what the path is for -----------------------------------------------------


def test_a_coarse_path_still_carries_a_stride():
    """Nineteen points over 267 m is enough, because the stride resamples it."""
    from semantic_twin.propagation.route import densify

    coarse = np.array([[0.0, 0.0], [44.5, 0.0]])
    dense = densify([coarse], stride_m=6.0)
    assert len(dense) == 8
    assert np.linalg.norm(np.diff(dense, axis=0), axis=1) == pytest.approx(6.0)
