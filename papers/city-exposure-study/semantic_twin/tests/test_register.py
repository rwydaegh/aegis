from __future__ import annotations

import numpy as np
import pytest
from semantic_twin.vision.conflict import sky_conflict
from semantic_twin.vision.register import (
    SkylineFit,
    SkylineSettings,
    candidate_vertices,
    ensemble_covariance,
    fit_pose,
    mesh_skyline,
    observed_skyline,
    profile_intervals,
    seed_study,
    signed_skyline_residual,
    skyline_cost,
)
from semantic_twin.pano_geometry import panorama_to_world_matrix


def _ring(radius: float, height: float, camera_z: float, *, n: int = 4096) -> np.ndarray:
    """A cylindrical wall of the given height, seen from a camera on the axis."""
    angle = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    return np.stack([radius * np.sin(angle), radius * np.cos(angle), np.full(n, camera_z + height)], axis=1)


def _skyline_town(*, n: int = 8192) -> np.ndarray:
    """A ring of buildings whose roofline varies with azimuth, so yaw is observable."""
    angle = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    radius = 28.0 + 12.0 * np.sin(3.0 * angle) ** 2
    height = 11.0 + 7.0 * np.sin(2.0 * angle) + 3.0 * np.cos(5.0 * angle)
    return np.stack([radius * np.sin(angle), radius * np.cos(angle), height], axis=1)


def _observed_from_model(vertices: np.ndarray, n_bins: int, yaw_deg: float, percentile: float = 90.0) -> np.ndarray:
    model = mesh_skyline(vertices, np.zeros(3), n_bins, 8.0, smoothing_percentile=percentile)
    azimuth = (np.arange(n_bins) / n_bins - 0.5) * 2.0 * np.pi
    world = np.stack([np.sin(azimuth) * np.cos(model), np.cos(azimuth) * np.cos(model), np.sin(model)], axis=1)
    return world @ panorama_to_world_matrix(yaw_deg)


def test_mesh_skyline_recovers_a_uniform_wall_elevation() -> None:
    vertices = _ring(30.0, 12.0, 0.0)
    skyline = mesh_skyline(vertices, np.zeros(3), 256, 8.0)
    assert np.degrees(skyline).min() == pytest.approx(np.degrees(np.arctan2(12.0, 30.0)), abs=1e-6)
    assert np.degrees(skyline).max() == pytest.approx(np.degrees(np.arctan2(12.0, 30.0)), abs=1e-6)


def test_median_smoothing_removes_a_peak_that_an_upper_quantile_keeps() -> None:
    """The shipped median filter is the source of the mesh-skyline low bias."""
    vertices = _ring(30.0, 12.0, 0.0)
    # A balustrade or chimney is several azimuth bins wide. A single-bin spike is
    # rejected by both filters, which is the behaviour the next test pins down.
    offsets = np.linspace(-0.5, 0.5, 9)
    peak = np.stack([offsets, np.full(9, 30.0), np.full(9, 20.0)], axis=1)
    with_peak = np.vstack([vertices, peak])
    median = mesh_skyline(with_peak, np.zeros(3), 256, 8.0, smoothing_percentile=50.0)
    upper = mesh_skyline(with_peak, np.zeros(3), 256, 8.0, smoothing_percentile=90.0)
    flat = np.arctan2(12.0, 30.0)
    assert median.max() == pytest.approx(flat, abs=1e-6)
    assert upper.max() > flat + np.radians(3.0)
    assert np.all(upper >= median - 1e-12)


def test_upper_quantile_still_rejects_an_isolated_spike() -> None:
    vertices = _ring(30.0, 12.0, 0.0)
    spike = np.array([[0.1, 30.0, 200.0]])
    upper = mesh_skyline(np.vstack([vertices, spike]), np.zeros(3), 256, 8.0, smoothing_percentile=90.0)
    assert upper.max() < np.radians(30.0)


def test_candidate_pruning_over_the_search_box_keeps_more_than_one_point() -> None:
    """Pruning at the start position alone discards geometry the optimiser needs."""
    rng = np.random.default_rng(0xA11)
    angle = rng.uniform(0.0, 2.0 * np.pi, 20000)
    radius = rng.uniform(9.0, 60.0, 20000)
    vertices = np.stack([radius * np.sin(angle), radius * np.cos(angle), rng.uniform(-2.0, 18.0, 20000)], axis=1)
    single = candidate_vertices(vertices, np.zeros(3), 256, 8.0)
    box = candidate_vertices(vertices, np.zeros(3), 256, 8.0, search_box_m=((-4.0, 4.0), (-4.0, 4.0), (-3.0, 3.0)))
    assert len(box) > len(single)


def test_observed_skyline_drops_columns_with_no_sky_rather_than_inventing_one() -> None:
    entity = np.zeros((64, 256), dtype=np.int32)
    entity[:20, :128] = 1  # sky over half the panorama only
    without_sky = observed_skyline(entity, sky_id=1, n_bins=64, structural_ids={0})
    everywhere = observed_skyline(entity, sky_id=1, n_bins=64, structural_ids=None)
    assert len(without_sky) < 64
    assert len(everywhere) < 64


def test_skyline_bias_parameter_shifts_the_model_not_the_observation() -> None:
    vertices = _ring(30.0, 12.0, 0.0)
    elevation = np.arctan2(12.0, 30.0)
    azimuth = np.linspace(-np.pi, np.pi, 512, endpoint=False)
    observed = np.stack(
        [np.sin(azimuth) * np.cos(elevation), np.cos(azimuth) * np.cos(elevation), np.full(512, np.sin(elevation))],
        axis=1,
    )
    settings = SkylineSettings(n_bins=256)
    kwargs = {
        "vertices": vertices,
        "local_skyline": observed,
        "position": np.zeros(3),
        "heading_deg": 0.0,
        "pitch_prior_deg": 0.0,
        "roll_prior_deg": 0.0,
        "settings": settings,
    }
    exact = skyline_cost(np.zeros(6), **kwargs)
    biased = skyline_cost(np.r_[np.zeros(6), 1.0], **kwargs)
    assert exact < 1e-6
    assert biased == pytest.approx(np.radians(1.0), rel=0.01)


def test_signed_residual_is_positive_when_the_mesh_skyline_sits_low() -> None:
    vertices = _ring(30.0, 12.0, 0.0)
    elevation = np.arctan2(14.0, 30.0)
    azimuth = np.linspace(-np.pi, np.pi, 512, endpoint=False)
    observed = np.stack(
        [np.sin(azimuth) * np.cos(elevation), np.cos(azimuth) * np.cos(elevation), np.full(512, np.sin(elevation))],
        axis=1,
    )
    signed = signed_skyline_residual(
        np.zeros(6),
        vertices=vertices,
        local_skyline=observed,
        position=np.zeros(3),
        heading_deg=0.0,
        pitch_prior_deg=0.0,
        roll_prior_deg=0.0,
        settings=SkylineSettings(n_bins=256),
    )
    assert np.median(signed) > 0.0


def test_camera_altitude_and_mesh_skyline_bias_are_degenerate() -> None:
    """Sinking the camera and raising the roofline are the same edit to the model.

    This is why widening the dz bound cannot on its own make the altitude
    trustworthy, and why the bias term is a diagnostic rather than a parameter.
    """
    radius, height = 30.0, 12.0
    vertices = _ring(radius, height, 0.0)
    settings = SkylineSettings(n_bins=256)
    sink = 1.0
    lowered = mesh_skyline(vertices - np.array([0.0, 0.0, -sink]), np.zeros(3), 256, 8.0)
    reference = mesh_skyline(vertices, np.zeros(3), 256, 8.0)
    predicted = np.degrees(np.arctan2(height + sink, radius) - np.arctan2(height, radius))
    assert np.degrees(lowered - reference).mean() == pytest.approx(predicted, rel=1e-6)
    assert predicted == pytest.approx(np.degrees(sink / radius), rel=0.15)
    assert settings.n_bins == 256


def test_fit_pose_recovers_a_known_yaw_offset() -> None:
    vertices = _skyline_town()
    truth_yaw = 4.0
    fit = fit_pose(
        vertices,
        _observed_from_model(vertices, 256, truth_yaw),
        np.zeros(3),
        0.0,
        0.0,
        0.0,
        settings=SkylineSettings(n_bins=256, smoothing_percentile=90.0),
        maxiter=300,
        dz_bounds=(-2.0, 2.0),
        translation_bound_m=1.0,
        yaw_bound_deg=10.0,
        orientation_bound_deg=2.0,
    )
    assert fit.params[3] == pytest.approx(truth_yaw, abs=0.3)
    assert fit.residual_deg < 0.2
    assert fit.converged


def test_seed_study_reports_a_covariance_over_independent_seeds() -> None:
    vertices = _skyline_town(n=2048)
    ensemble = seed_study(
        vertices,
        _observed_from_model(vertices, 128, 0.0),
        np.zeros(3),
        0.0,
        0.0,
        0.0,
        seeds=(1, 2, 3),
        settings=SkylineSettings(n_bins=128, smoothing_percentile=90.0),
        maxiter=60,
        dz_bounds=(-1.0, 1.0),
        translation_bound_m=1.0,
        yaw_bound_deg=5.0,
        orientation_bound_deg=1.0,
    )
    assert ensemble.covariance.shape == (7, 7)
    assert np.all(np.diag(ensemble.covariance) >= 0.0)
    assert ensemble.best.cost == min(fit.cost for fit in ensemble.fits)
    document = ensemble.as_dict()
    assert document["n_seeds"] == 3
    assert len(document["standard_deviation"]) == 7


def test_profile_finds_horizontal_position_the_least_constrained_axis() -> None:
    """A skyline pins orientation far better than it pins where the camera stands."""
    vertices = _skyline_town(n=2048)
    intervals = profile_intervals(
        np.zeros(6),
        [(-1.0, 1.0), (-1.0, 1.0), (-2.0, 2.0), (-4.0, 4.0), (-2.0, 2.0), (-2.0, 2.0)],
        tolerance_deg=0.5,
        steps=9,
        vertices=vertices,
        local_skyline=_observed_from_model(vertices, 128, 0.0),
        position=np.zeros(3),
        heading_deg=0.0,
        pitch_prior_deg=0.0,
        roll_prior_deg=0.0,
        settings=SkylineSettings(n_bins=128, smoothing_percentile=90.0),
    )
    assert intervals["_tolerance_deg"]["reference_residual_deg"] < 0.01
    assert intervals["dx_m"]["half_width"] > intervals["pitch_delta_deg"]["half_width"]
    assert intervals["dx_m"]["reached_bound"]
    assert set(intervals["yaw_deg"]) == {"best", "low", "high", "half_width", "reached_bound"}


def test_ensemble_covariance_of_a_single_fit_is_zero() -> None:
    fit = SkylineFit(np.zeros(6), 0.0, 0.0, 0.0, 1, 1, 1, True, (-1.0, 1.0))
    assert np.allclose(ensemble_covariance([fit]), 0.0)


def test_settings_reject_an_even_smoothing_window() -> None:
    with pytest.raises(ValueError, match="odd"):
        SkylineSettings(smoothing_size=10)


def test_sky_conflict_separates_a_correct_pose_from_a_sunken_one() -> None:
    """A camera below the pavement makes every ray hit, which no fit can hide."""
    pytest.importorskip("trimesh")
    pytest.importorskip("embreex")
    angle = np.linspace(0.0, 2.0 * np.pi, 96, endpoint=False)
    radius, height = 30.0, 12.0
    lower = np.stack([radius * np.sin(angle), radius * np.cos(angle), np.zeros(96)], axis=1)
    upper = lower + np.array([0.0, 0.0, height])
    vertices = np.vstack([lower, upper])
    faces = []
    for index in range(96):
        nxt = (index + 1) % 96
        faces.append([index, nxt, 96 + index])
        faces.append([nxt, 96 + nxt, 96 + index])
    faces = np.array(faces, dtype=np.int64)

    entity = np.zeros((256, 512), dtype=np.int32)
    elevation = np.degrees(np.arctan2(height - 2.0, radius))
    boundary = int((0.5 - elevation / 180.0) * 256)
    entity[:boundary, :] = 1  # sky above the wall top
    entity[boundary:, :] = 2  # wall below it

    camera = np.array([0.0, 0.0, 2.0])
    good = sky_conflict(vertices, faces, entity, 1, {2}, camera, heading_deg=0.0, pitch_deg=0.0, roll_deg=0.0)
    sunk = sky_conflict(
        vertices,
        faces,
        entity,
        1,
        {2},
        camera - np.array([0.0, 0.0, 6.0]),
        heading_deg=0.0,
        pitch_deg=0.0,
        roll_deg=0.0,
    )
    assert good.sky_with_mesh < 0.05
    assert sunk.sky_with_mesh > good.sky_with_mesh
    assert sunk.disagreement > good.disagreement
