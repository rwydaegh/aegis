"""Tests for walk selection and the independence weighting that guards fusion."""

from __future__ import annotations

import math

import numpy as np
import pytest

from semantic_twin import walk
from semantic_twin.geo import EnuFrame

FRAME = EnuFrame(51.055, 3.722, 0.0)


def image(
    identifier: str, east: float, north: float, *, sequence: str = "seq", pano: bool = True, rotation=(0.1, 2.0, -2.2)
):
    latitude = 51.055 + north / 111320.0
    longitude = 3.722 + east / (111320.0 * math.cos(math.radians(51.055)))
    record = {
        "id": identifier,
        "computed_geometry": {"type": "Point", "coordinates": [longitude, latitude]},
        "is_pano": pano,
        "sequence": sequence,
        "quality_score": 0.9,
        "captured_at": 1740994813000,
        "width": 5760,
        "height": 2880,
    }
    if rotation is not None:
        record["computed_rotation"] = list(rotation)
    return record


def stations(points, sequence="seq"):
    images = [image(str(index), east, north, sequence=sequence) for index, (east, north) in enumerate(points)]
    return walk.stations_from_images(images, FRAME, target_lat=51.055, target_lon=3.722)


def test_stations_are_placed_in_the_local_frame():
    result = stations([(10.0, 0.0), (0.0, -20.0)])
    assert len(result) == 2
    assert result[0].easting_m == pytest.approx(10.0, abs=0.05)
    assert result[0].northing_m == pytest.approx(0.0, abs=0.05)
    assert result[1].range_m == pytest.approx(20.0, abs=0.05)


def test_radius_and_panorama_filters_are_applied():
    images = [image("near", 5.0, 0.0), image("far", 500.0, 0.0), image("flat", 6.0, 0.0, pano=False)]
    result = walk.stations_from_images(images, FRAME, target_lat=51.055, target_lon=3.722, radius_m=60.0)
    assert [station.image_id for station in result] == ["near"]


def test_measured_gravity_is_mandatory_by_default():
    """A capture with no computed_rotation would have to be assumed level."""
    images = [image("tilted", 5.0, 0.0), image("unknown", 6.0, 0.0, rotation=None)]
    strict = walk.stations_from_images(images, FRAME, target_lat=51.055, target_lon=3.722)
    lenient = walk.stations_from_images(images, FRAME, target_lat=51.055, target_lon=3.722, require_rotation=False)
    assert [station.image_id for station in strict] == ["tilted"]
    assert len(lenient) == 2
    assert not [s for s in lenient if s.image_id == "unknown"][0].has_computed_rotation


def test_select_walk_thins_by_separation_and_prefers_the_near_field():
    result = walk.select_walk(stations([(2.0, 0.0), (3.0, 0.0), (30.0, 0.0)]), count=5, separation_m=8.0)
    assert [station.image_id for station in result] == ["0", "2"]


def test_select_walk_caps_a_single_dense_drive():
    """One drive must not fill the walk and leave nothing to cross-validate against."""
    dense = stations([(5.0, 0.0), (15.0, 0.0), (25.0, 0.0)], sequence="a")
    other = stations([(-5.0, 0.0), (-15.0, 0.0)], sequence="b")
    result = walk.select_walk(dense + other, count=4, separation_m=8.0, per_sequence_cap=2)
    counts = {station.sequence_id for station in result}
    assert counts == {"a", "b"}
    assert sum(station.sequence_id == "a" for station in result) == 2


def test_spread_reports_extent_and_baselines():
    report = walk.spread(stations([(0.0, 0.0), (30.0, 0.0), (0.0, 40.0)]))
    assert report["n_stations"] == 3
    assert report["extent_east_m"] == pytest.approx(30.0, abs=0.1)
    assert report["extent_north_m"] == pytest.approx(40.0, abs=0.1)
    assert report["baseline_m"]["max"] == pytest.approx(50.0, abs=0.2)
    assert report["convex_hull_area_m2"] == pytest.approx(600.0, rel=0.02)


def test_spread_of_an_empty_walk_is_not_an_error():
    assert walk.spread([]) == {"n_stations": 0}


def test_parallax_is_the_angle_at_the_surface_not_the_baseline():
    """The same baseline is a large parallax up close and a small one far away."""
    pair = stations([(-5.0, 0.0), (5.0, 0.0)])
    near = walk.parallax_angles_deg(pair, np.array([[0.0, -5.0]]))
    far = walk.parallax_angles_deg(pair, np.array([[0.0, -100.0]]))
    assert near[0, 0, 1] == pytest.approx(90.0, abs=0.5)
    assert far[0, 0, 1] < 6.0
    # arccos is flat at 1, so a station's parallax with itself is zero only to
    # the square root of machine precision.
    assert np.allclose(np.diagonal(near[0]), 0.0, atol=1e-4)


def test_two_co_located_cameras_count_as_one_observation():
    """The double-counting guard: zero parallax must halve each weight."""
    parallax = np.zeros((1, 2, 2))
    visible = np.ones((1, 2), dtype=bool)
    weight = walk.parallax_independence(parallax, visible)
    assert weight[0].tolist() == pytest.approx([0.5, 0.5])
    assert walk.effective_looks(weight)[0] == pytest.approx(1.0)


def test_widely_separated_cameras_keep_their_full_weight():
    parallax = np.array([[[0.0, 90.0], [90.0, 0.0]]], dtype=float)
    weight = walk.parallax_independence(parallax, np.ones((1, 2), dtype=bool))
    assert weight[0].tolist() == pytest.approx([1.0, 1.0], abs=1e-6)
    assert walk.effective_looks(weight)[0] == pytest.approx(2.0, abs=1e-6)


def test_effective_looks_never_exceed_the_raw_count():
    rng = np.random.default_rng(11)
    points = rng.uniform(-40.0, 40.0, size=(9, 2))
    surfaces = rng.uniform(-60.0, 60.0, size=(50, 2))
    walk_stations = stations([tuple(point) for point in points])
    parallax = walk.parallax_angles_deg(walk_stations, surfaces)
    visible = rng.random((50, len(walk_stations))) > 0.4
    weight = walk.parallax_independence(parallax, visible)
    looks = walk.effective_looks(weight)
    raw = visible.sum(axis=1)
    assert np.all(looks <= raw + 1e-9)
    assert np.all(looks[raw > 0] >= 1.0 - 1e-9)
    assert np.all(weight[~visible] == 0.0)


def test_unseen_surfaces_carry_no_weight_and_no_looks():
    parallax = np.zeros((1, 3, 3))
    visible = np.array([[False, False, False]])
    weight = walk.parallax_independence(parallax, visible)
    assert weight.sum() == 0.0
    assert walk.effective_looks(weight)[0] == 0.0


def test_independence_weights_are_a_valid_evidence_quality_factor():
    """They have to be usable as-is by ObservationQuality, which demands [0, 1]."""
    from semantic_twin.evidence import ObservationQuality

    pair = stations([(-2.0, 0.0), (2.0, 0.0), (40.0, 40.0)])
    parallax = walk.parallax_angles_deg(pair, np.array([[0.0, -30.0]]))
    weight = walk.parallax_independence(parallax, np.ones((1, 3), dtype=bool))[0]
    ones = np.ones(3)
    quality = ObservationQuality(ones, ones, ones, ones, ones, weight)
    assert np.all((quality.combined() >= 0.0) & (quality.combined() <= 1.0))
    assert quality.combined()[0] < quality.combined()[2]


def test_invalid_shapes_are_rejected():
    with pytest.raises(ValueError):
        walk.parallax_angles_deg(stations([(0.0, 0.0)]), np.zeros((2, 3)))
    with pytest.raises(ValueError):
        walk.parallax_independence(np.zeros((1, 2, 3)), np.ones((1, 2), dtype=bool))
    with pytest.raises(ValueError):
        walk.parallax_independence(np.zeros((1, 2, 2)), np.ones((1, 3), dtype=bool))
    with pytest.raises(ValueError):
        walk.parallax_independence(np.zeros((1, 2, 2)), np.ones((1, 2), dtype=bool), decorrelation_deg=0.0)
    with pytest.raises(ValueError):
        walk.select_walk([], count=0)


def test_seed_cells_must_respect_the_graph_bbox_limit():
    with pytest.raises(ValueError):
        walk.seed_sequences("token", latitude=51.055, longitude=3.722, half_width_m=100000.0, cells=1)


def test_coverage_curve_is_monotone_and_ends_at_the_union():
    from build_walk_twin import coverage_curve

    seen = np.array([[True, False, False], [True, True, False], [False, False, True]])
    area = np.array([1.0, 1.0, 2.0])
    curve = coverage_curve(seen, area, [0, 1, 2])
    assert [entry["faces"] for entry in curve] == [1, 2, 3]
    assert curve[-1]["face_fraction"] == 1.0
    assert curve[-1]["area_fraction"] == 1.0
    assert all(curve[i]["faces"] <= curve[i + 1]["faces"] for i in range(len(curve) - 1))


def test_saturation_curve_is_order_averaged_and_ends_at_the_union():
    from build_walk_twin import saturation_curves

    seen = np.array([[True, False, False], [False, True, False], [False, False, True]])
    area = np.ones(3)
    result = saturation_curves(seen, area, permutations=8)
    assert result["mean_face_fraction"][-1] == pytest.approx(1.0)
    assert result["mean_faces"][0] == pytest.approx(1.0)
    # Every order reaches the same union, so the spread must close at the end.
    assert result["face_fraction_p10"][-1] == pytest.approx(result["face_fraction_p90"][-1])


def test_marginal_gain_decays_when_stations_are_redundant():
    """A saturating set must show a falling marginal, an expanding one must not."""
    from build_walk_twin import saturation_curves

    faces = 400
    redundant = np.zeros((6, faces), dtype=bool)
    redundant[:, :200] = True
    redundant[np.arange(6), 200 + np.arange(6)] = True
    disjoint = np.zeros((6, faces), dtype=bool)
    for index in range(6):
        disjoint[index, index * 50 : (index + 1) * 50] = True

    area = np.ones(faces)
    slowing = saturation_curves(redundant, area, permutations=12)["marginal_faces_per_panorama"]
    steady = saturation_curves(disjoint, area, permutations=12)["marginal_faces_per_panorama"]
    assert slowing[-1] < 0.05 * slowing[0]
    assert steady[-1] == pytest.approx(steady[1])


def test_random_order_never_beats_the_union():
    from build_walk_twin import saturation_curves

    rng = np.random.default_rng(5)
    seen = rng.random((7, 300)) > 0.7
    result = saturation_curves(seen, np.ones(300), permutations=10)
    union = seen.any(axis=0).mean()
    assert result["mean_face_fraction"][-1] == pytest.approx(union)
    assert all(a <= b + 1e-9 for a, b in zip(result["mean_faces"], result["mean_faces"][1:]))
