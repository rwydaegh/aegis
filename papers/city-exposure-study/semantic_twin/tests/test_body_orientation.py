from __future__ import annotations

from dataclasses import fields
from pathlib import Path

import numpy as np
import pytest

from semantic_twin.exposure import (
    BodyCoupler,
    BodyExposure,
    DirectionalMeasure,
    UniformYawBodyExposure,
    describe,
    uniform_z_yaw_mean_incidence,
)


def _dense_mean_incidence(normals: np.ndarray, arrival_k_hat: np.ndarray, samples: int = 4096) -> np.ndarray:
    theta = np.arange(samples, dtype=np.float64) * (2.0 * np.pi / samples)
    c = np.cos(theta)
    s = np.sin(theta)
    rotated = np.empty((samples, normals.shape[0], 3), dtype=np.float64)
    rotated[:, :, 0] = c[:, None] * normals[None, :, 0] - s[:, None] * normals[None, :, 1]
    rotated[:, :, 1] = s[:, None] * normals[None, :, 0] + c[:, None] * normals[None, :, 1]
    rotated[:, :, 2] = normals[None, :, 2]
    return np.mean(np.maximum(np.einsum("tnc,mc->tnm", rotated, -arrival_k_hat), 0.0), axis=0)


def _random_unit(rng: np.random.Generator, shape: tuple[int, ...]) -> np.ndarray:
    vectors = rng.normal(size=shape)
    return vectors / np.linalg.norm(vectors, axis=-1, keepdims=True)


@pytest.mark.parametrize("seed", [3, 41, 199])
def test_uniform_z_yaw_closed_form_matches_dense_quadrature(seed: int) -> None:
    rng = np.random.default_rng(seed)
    normals = _random_unit(rng, (11, 3))
    arrival = _random_unit(rng, (7, 3))
    actual = uniform_z_yaw_mean_incidence(normals, arrival, chunk_directions=2, chunk_normals=3)
    expected = _dense_mean_incidence(normals, arrival)
    np.testing.assert_allclose(actual, expected, rtol=3.0e-7, atol=3.0e-8)


def test_uniform_z_yaw_closed_form_boundary_cases() -> None:
    normals = np.array(
        [
            [0.0, 0.0, 1.0],
            [0.0, 0.0, -1.0],
            [1.0, 0.0, 0.0],
            [0.6, 0.0, 0.8],
            [0.6, 0.0, -0.8],
        ]
    )
    arrival = np.array(
        [
            [0.0, 0.0, -1.0],
            [0.0, 0.0, 1.0],
            [1.0, 0.0, 0.0],
            [-0.6, 0.0, -0.8],
            [-0.6, 0.0, 0.8],
        ]
    )
    actual = uniform_z_yaw_mean_incidence(normals, arrival)
    expected = _dense_mean_incidence(normals, arrival)
    np.testing.assert_allclose(actual, expected, rtol=3.0e-7, atol=3.0e-8)
    assert actual[0, 0] == pytest.approx(1.0)
    assert actual[1, 0] == pytest.approx(0.0)
    assert actual[2, 2] == pytest.approx(1.0 / np.pi)


def test_uniform_z_yaw_two_axis_chunking_matches_wide_block() -> None:
    rng = np.random.default_rng(214)
    normals = _random_unit(rng, (13, 3))
    arrival = _random_unit(rng, (17, 3))
    blocked = uniform_z_yaw_mean_incidence(normals, arrival, chunk_directions=2, chunk_normals=3)
    wide = uniform_z_yaw_mean_incidence(normals, arrival, chunk_directions=64, chunk_normals=64)
    np.testing.assert_allclose(blocked, wide, rtol=2.0e-14, atol=2.0e-15)


def test_common_z_rotation_invariance_and_fixed_body_yaw_sensitivity() -> None:
    rng = np.random.default_rng(87)
    normals = _random_unit(rng, (8, 3))
    arrival = _random_unit(rng, (9, 3))
    angle = 0.73
    rotation = np.array([[np.cos(angle), -np.sin(angle), 0.0], [np.sin(angle), np.cos(angle), 0.0], [0.0, 0.0, 1.0]])
    common = uniform_z_yaw_mean_incidence(normals, arrival)
    rotated = uniform_z_yaw_mean_incidence(normals @ rotation.T, arrival @ rotation.T)
    np.testing.assert_allclose(common, rotated, rtol=2.0e-14, atol=2.0e-15)
    fixed = np.maximum(normals @ (-arrival).T, 0.0)
    fixed_rotated_body = np.maximum((normals @ rotation.T) @ (-arrival).T, 0.0)
    assert not np.allclose(fixed, fixed_rotated_body)


def test_orientation_helper_rejects_malformed_inputs() -> None:
    good = np.array([[1.0, 0.0, 0.0]])
    with pytest.raises(ValueError, match="normals"):
        uniform_z_yaw_mean_incidence(np.zeros((1, 2)), good)
    with pytest.raises(ValueError, match="arrival_k_hat"):
        uniform_z_yaw_mean_incidence(good, np.array([[2.0, 0.0, 0.0]]))
    with pytest.raises(ValueError, match="finite"):
        uniform_z_yaw_mean_incidence(good, np.array([[np.nan, 0.0, 0.0]]))
    with pytest.raises(ValueError, match="chunk_directions"):
        uniform_z_yaw_mean_incidence(good, good, chunk_directions=0)
    with pytest.raises(ValueError, match="chunk_directions"):
        uniform_z_yaw_mean_incidence(good, good, chunk_directions=1.5)
    with pytest.raises(ValueError, match="chunk_directions"):
        uniform_z_yaw_mean_incidence(good, good, chunk_directions=True)
    with pytest.raises(ValueError, match="chunk_normals"):
        uniform_z_yaw_mean_incidence(good, good, chunk_normals=0)
    with pytest.raises(ValueError, match="chunk_normals"):
        uniform_z_yaw_mean_incidence(good, good, chunk_normals=1.5)
    with pytest.raises(ValueError, match="chunk_normals"):
        uniform_z_yaw_mean_incidence(good, good, chunk_normals=True)


def _asymmetric_coupler() -> BodyCoupler:
    pytest.importorskip("aegis")
    from aegis.engine import DosimetryEngine
    from aegis.geometry.mesh import BodyMesh
    from aegis.tissue import TissueModel

    normals = np.array(
        [
            [0.0, 0.0, 1.0],
            [0.6, 0.0, 0.8],
            [-0.2, 0.9, 0.4],
            [0.7, -0.4, 0.59],
            [-0.8, -0.3, 0.52],
        ],
        dtype=np.float64,
    )
    normals /= np.linalg.norm(normals, axis=1, keepdims=True)
    areas = np.array([0.7, 1.3, 0.9, 1.7, 0.45], dtype=np.float64)
    triangles = []
    for index, normal in enumerate(normals):
        reference = np.array([0.0, 0.0, 1.0]) if abs(normal[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
        edge_a = np.cross(normal, reference)
        edge_a /= np.linalg.norm(edge_a)
        edge_b = np.cross(normal, edge_a)
        origin = np.array([3.0 * index, 0.0, 0.0])
        triangles.append(
            np.stack(
                [origin, origin + edge_a * np.sqrt(2.0 * areas[index]), origin + edge_b * np.sqrt(2.0 * areas[index])],
                axis=0,
            )
        )
    body = BodyMesh.from_arrays(np.asarray(triangles), normals=normals, name="yaw-asymmetric")
    tissue = TissueModel.from_database("Skin", 15.0e9)
    coupler = BodyCoupler.__new__(BodyCoupler)
    coupler.body = body
    coupler.tissue = tissue
    coupler.engine = DosimetryEngine(tissue)
    coupler.level = 2
    coupler.body_mass_kg = 70.0
    coupler.frequency_hz = 15.0e9
    # This synthetic mesh is intentionally asymmetric but not anatomically
    # shaped, so provide the same native anterior sign that the real Virtual
    # Family phantoms receive from ``detect_body_frame``.
    coupler.body_anterior_axis = np.array([0.0, -1.0, 0.0])
    return coupler


def _rotate_body(coupler: BodyCoupler, angle: float) -> None:
    from aegis.geometry.mesh import BodyMesh

    c = np.cos(angle)
    s = np.sin(angle)
    rotation = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
    body = coupler.body
    coupler.body = BodyMesh.from_arrays(body.vertices @ rotation.T, normals=body.normals @ rotation.T, name=body.name)


def _mixed_measure() -> DirectionalMeasure:
    atom_k_hat = np.array([[0.4, -0.3, 0.8660254037844386], [-0.7, 0.2, 0.6855654600401044]])
    diffuse_k_hat = np.array([[0.2, 0.9, -0.3872983346207417], [-0.5, -0.6, -0.6204836822995429]])
    atom_k_hat /= np.linalg.norm(atom_k_hat, axis=1, keepdims=True)
    diffuse_k_hat /= np.linalg.norm(diffuse_k_hat, axis=1, keepdims=True)
    return DirectionalMeasure(
        atom_k_hat=atom_k_hat,
        atom_mass=np.array([0.35, 0.17]),
        diffuse_k_hat=diffuse_k_hat,
        diffuse_mass=np.array([0.22, 0.11]),
    )


def _rotate_measure_xy(measure: DirectionalMeasure, angle: float) -> DirectionalMeasure:
    """Rotate arrival directions by a known inverse body-frame yaw."""
    cosine, sine = np.cos(angle), np.sin(angle)

    def rotate(values: np.ndarray) -> np.ndarray:
        answer = np.array(values, copy=True)
        answer[:, 0] = cosine * values[:, 0] - sine * values[:, 1]
        answer[:, 1] = sine * values[:, 0] + cosine * values[:, 1]
        return answer

    return DirectionalMeasure(
        atom_k_hat=rotate(measure.atom_k_hat),
        atom_mass=measure.atom_mass,
        diffuse_k_hat=rotate(measure.diffuse_k_hat),
        diffuse_mass=measure.diffuse_mass,
    )


def test_fixed_yaw_uses_detected_minus_y_anterior_and_matches_manual_inverse_rotation() -> None:
    coupler = _asymmetric_coupler()
    measure = _mixed_measure()
    # The shipped phantoms' native anterior is -Y. At ENU yaw zero (north),
    # the body therefore has a 180-degree world-to-native rotation.
    actual, actual_sab = coupler.couple_measure_with_sab(measure, 0.83, body_yaw_deg=0.0)
    manually_rotated = _rotate_measure_xy(measure, np.pi)
    expected, expected_sab = coupler.couple_measure_with_sab(manually_rotated, 0.83)
    for field in fields(BodyExposure):
        assert getattr(actual, field.name) == pytest.approx(getattr(expected, field.name), rel=1.0e-14, abs=1.0e-15)
    np.testing.assert_allclose(actual_sab, expected_sab, rtol=1.0e-14, atol=1.0e-15)

    native_facing, _ = coupler.couple_measure_with_sab(measure, 0.83, body_yaw_deg=180.0)
    direct, _ = coupler.couple_measure_with_sab(measure, 0.83)
    for field in fields(BodyExposure):
        assert getattr(native_facing, field.name) == pytest.approx(getattr(direct, field.name))
    assert actual.absorbed_power_w != pytest.approx(native_facing.absorbed_power_w)


def test_fixed_yaw_matches_coupling_to_a_physically_rotated_asymmetric_body() -> None:
    measure = _mixed_measure()
    coupler = _asymmetric_coupler()
    actual, actual_sab = coupler.couple_measure_with_sab(measure, 0.83, body_yaw_deg=90.0)

    physically_rotated = _asymmetric_coupler()
    _rotate_body(physically_rotated, np.pi / 2.0)
    expected, expected_sab = physically_rotated.couple_measure_with_sab(measure, 0.83)
    for field in fields(BodyExposure):
        assert getattr(actual, field.name) == pytest.approx(getattr(expected, field.name), rel=1.0e-14, abs=1.0e-15)
    np.testing.assert_allclose(actual_sab, expected_sab, rtol=1.0e-14, atol=1.0e-15)


def test_route_reversal_changes_asymmetric_exposure_with_the_declared_180_degree_yaw_shift() -> None:
    from semantic_twin.walk import route_body_yaw_deg

    points = np.array([[0.0, 0.0, 1.5], [5.0, 0.0, 1.5], [10.0, 0.0, 1.5]])
    forward, _ = route_body_yaw_deg(points)
    reverse, _ = route_body_yaw_deg(points[::-1])
    np.testing.assert_array_equal(forward, np.full(3, 90.0))
    np.testing.assert_array_equal(reverse, np.full(3, 270.0))

    coupler = _asymmetric_coupler()
    measure = _mixed_measure()
    forward_exposure = coupler.couple_measure(measure, 0.83, body_yaw_deg=float(forward[1]))
    reverse_exposure = coupler.couple_measure(measure, 0.83, body_yaw_deg=float(reverse[1]))
    assert reverse_exposure.absorbed_power_w != pytest.approx(forward_exposure.absorbed_power_w)


def test_couple_many_fixed_yaw_matches_each_spectrum_loop() -> None:
    coupler = _asymmetric_coupler()
    grid = np.array(
        [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [-1.0, 0.0, 0.0]],
        dtype=np.float64,
    )
    spectra = np.array([[0.2, 0.4, 0.1], [0.7, 0.1, 0.3]], dtype=np.float64)
    expected = tuple(coupler.couple(grid, spectrum, 0.5, 0.83, body_yaw_deg=270.0) for spectrum in spectra)
    actual = coupler.couple_many(grid, spectra, 0.5, 0.83, chunk_cells=1, body_yaw_deg=270.0)
    for batched, single in zip(actual, expected, strict=True):
        for field in fields(BodyExposure):
            assert getattr(batched, field.name) == pytest.approx(getattr(single, field.name))


def test_fixed_yaw_grid_and_directional_measure_paths_have_the_same_incidence() -> None:
    coupler = _asymmetric_coupler()
    grid = np.array(
        [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [-1.0, 0.0, 0.0]],
        dtype=np.float64,
    )
    rho = np.array([0.2, 0.4, 0.1], dtype=np.float64)
    solid_angle = 0.5
    reference = 0.83
    grid_exposure = coupler.couple(grid, rho, solid_angle, reference, body_yaw_deg=270.0)
    measure = DirectionalMeasure(
        atom_k_hat=-grid,
        atom_mass=rho * solid_angle,
        diffuse_k_hat=np.empty((0, 3)),
        diffuse_mass=np.empty(0),
    )
    measure_exposure = coupler.couple_measure(measure, reference, body_yaw_deg=270.0)
    for field in fields(BodyExposure):
        assert getattr(grid_exposure, field.name) == pytest.approx(getattr(measure_exposure, field.name))


def test_body_description_seals_the_frame_sign_and_route_yaw_convention() -> None:
    metadata = describe(_asymmetric_coupler())
    assert metadata["body_anterior_axis"] == [0.0, -1.0, 0.0]
    assert "route yaw is ENU azimuth" in metadata["body_orientation_convention"]


@pytest.mark.slow
@pytest.mark.parametrize("phantom", ["duke", "eartha", "ella", "thelonious"])
def test_virtual_family_phantoms_all_detect_minus_y_anterior(phantom: str) -> None:
    pytest.importorskip("aegis")
    from aegis.geometry.mesh import BodyMesh
    from aegis.nearfield.scenarios import detect_body_frame

    path = Path("/home/user/aegis/data") / f"{phantom}.stl"
    if not path.exists():
        pytest.skip("phantom mesh not available")
    frame = detect_body_frame(BodyMesh.load(str(path)))
    np.testing.assert_array_equal(frame.anterior, np.array([0.0, -1.0, 0.0]))


def test_mixed_measure_matches_dense_rigid_yaw_level_two_average() -> None:
    coupler = _asymmetric_coupler()
    measure = _mixed_measure()
    reference = 0.83
    actual, mean_sab = coupler.couple_measure_uniform_yaw_with_sab(
        measure,
        reference,
        chunk_directions=1,
        chunk_normals=2,
    )
    wide_actual, wide_sab = coupler.couple_measure_uniform_yaw_with_sab(
        measure,
        reference,
        chunk_directions=128,
        chunk_normals=4096,
    )
    assert wide_actual == actual
    np.testing.assert_allclose(wide_sab, mean_sab, rtol=2.0e-14, atol=2.0e-15)
    original_body = coupler.body
    dense_sab = np.zeros_like(mean_sab)
    dense_exposures = []
    samples = 256
    for angle in np.arange(samples) * (2.0 * np.pi / samples):
        coupler.body = original_body
        _rotate_body(coupler, float(angle))
        exposure, sab = coupler.couple_measure_with_sab(measure, reference, chunk_cells=1)
        dense_exposures.append(exposure)
        dense_sab += sab
    coupler.body = original_body
    dense_sab /= samples
    np.testing.assert_allclose(mean_sab, dense_sab, rtol=2.0e-5, atol=2.0e-7)
    assert actual.yaw_mean_absorbed_power_w == pytest.approx(
        np.mean([item.absorbed_power_w for item in dense_exposures]), rel=2.0e-5
    )
    assert actual.yaw_mean_area_mean_sab_w_m2 == pytest.approx(
        np.mean([item.mean_sab_w_m2 for item in dense_exposures]), rel=2.0e-5
    )


def test_area_mean_and_absorbed_power_commute_with_yaw_average() -> None:
    coupler = _asymmetric_coupler()
    result, sab = coupler.couple_measure_uniform_yaw_with_sab(_mixed_measure(), 0.83)
    expected_absorbed = float(np.sum(sab * coupler.body.areas))
    assert result.yaw_mean_absorbed_power_w == pytest.approx(expected_absorbed)
    assert result.yaw_mean_area_mean_sab_w_m2 == pytest.approx(expected_absorbed / coupler.body.total_area)
    assert result.peak_of_yaw_mean_sab_w_m2 == pytest.approx(np.max(sab))


def test_atom_and_diffuse_representation_parity_for_uniform_yaw() -> None:
    coupler = _asymmetric_coupler()
    measure = _mixed_measure()
    atom_only = DirectionalMeasure(
        atom_k_hat=np.concatenate((measure.atom_k_hat, measure.diffuse_k_hat)),
        atom_mass=np.concatenate((measure.atom_mass, measure.diffuse_mass)),
        diffuse_k_hat=np.empty((0, 3)),
        diffuse_mass=np.empty(0),
    )
    diffuse_only = DirectionalMeasure(
        atom_k_hat=np.empty((0, 3)),
        atom_mass=np.empty(0),
        diffuse_k_hat=np.concatenate((measure.atom_k_hat, measure.diffuse_k_hat)),
        diffuse_mass=np.concatenate((measure.atom_mass, measure.diffuse_mass)),
    )
    atom_result, atom_sab = coupler.couple_measure_uniform_yaw_with_sab(atom_only, 0.83)
    diffuse_result, diffuse_sab = coupler.couple_measure_uniform_yaw_with_sab(diffuse_only, 0.83)
    assert atom_result == diffuse_result
    np.testing.assert_allclose(atom_sab, diffuse_sab, rtol=2.0e-14, atol=2.0e-15)


def test_uniform_endpoint_does_not_mutate_body_or_change_fixed_yaw_result() -> None:
    coupler = _asymmetric_coupler()
    measure = _mixed_measure()
    before_body = coupler.body
    before_exposure, before_sab = coupler.couple_measure_with_sab(measure, 0.83, chunk_cells=1)
    _uniform = coupler.couple_measure_uniform_yaw(measure, 0.83, chunk_directions=1)
    after_exposure, after_sab = coupler.couple_measure_with_sab(measure, 0.83, chunk_cells=1)
    assert coupler.body is before_body
    assert after_exposure == before_exposure
    np.testing.assert_array_equal(after_sab, before_sab)


def test_uniform_result_is_invariant_to_body_only_yaw_shift() -> None:
    coupler = _asymmetric_coupler()
    measure = _mixed_measure()
    unshifted = coupler.couple_measure_uniform_yaw(measure, 0.83)
    original_body = coupler.body
    _rotate_body(coupler, 0.37)
    shifted = coupler.couple_measure_uniform_yaw(measure, 0.83)
    coupler.body = original_body
    assert shifted == unshifted


def test_peak_of_yaw_mean_is_not_mean_of_per_yaw_peaks() -> None:
    normals = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    arrival = np.array([[1.0, 0.0, 0.0]])
    mean_field = uniform_z_yaw_mean_incidence(normals, arrival).ravel()
    theta = np.arange(4096) * (2.0 * np.pi / 4096)
    per_yaw = np.maximum(np.stack((np.cos(theta), np.sin(theta)), axis=1), 0.0)
    assert np.max(mean_field) < np.mean(np.max(per_yaw, axis=1))


def test_uniform_yaw_endpoint_has_explicit_empty_zero_and_missing_mass_behavior() -> None:
    coupler = _asymmetric_coupler()
    empty = coupler.couple_measure_uniform_yaw(DirectionalMeasure.empty(), 0.83)
    assert empty == UniformYawBodyExposure(0.83, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    zero, zero_sab = coupler.couple_measure_uniform_yaw_with_sab(_mixed_measure(), 0.0)
    assert zero.reference_s0_w_m2 == 0.0
    assert zero.arriving_power_density_w_m2 == 0.0
    assert zero.susceptibility == 0.0
    assert zero.yaw_mean_absorbed_power_w == 0.0
    assert zero.yaw_mean_sar_wb_w_kg == 0.0
    assert np.all(zero_sab == 0.0)
    coupler.body_mass_kg = None
    nonzero = coupler.couple_measure_uniform_yaw(_mixed_measure(), 0.83)
    assert np.isnan(nonzero.yaw_mean_sar_wb_w_kg)
    assert [field.name for field in fields(UniformYawBodyExposure)] == [
        "reference_s0_w_m2",
        "arriving_power_density_w_m2",
        "susceptibility",
        "peak_of_yaw_mean_sab_w_m2",
        "yaw_mean_area_mean_sab_w_m2",
        "yaw_mean_absorbed_power_w",
        "yaw_mean_sar_wb_w_kg",
    ]


@pytest.mark.parametrize("reference", [-1.0, np.nan, np.inf])
def test_uniform_yaw_endpoint_rejects_invalid_reference(reference: float) -> None:
    coupler = _asymmetric_coupler()
    with pytest.raises(ValueError, match="reference_s0_w_m2"):
        coupler.couple_measure_uniform_yaw(DirectionalMeasure.empty(), reference)


@pytest.mark.parametrize("chunk", [0, -1, 1.5, True])
def test_uniform_yaw_endpoint_rejects_invalid_direction_chunk(chunk: object) -> None:
    coupler = _asymmetric_coupler()
    with pytest.raises(ValueError, match="chunk_directions"):
        coupler.couple_measure_uniform_yaw(DirectionalMeasure.empty(), 1.0, chunk_directions=chunk)  # type: ignore[arg-type]


@pytest.mark.parametrize("chunk", [0, -1, 1.5, True])
def test_uniform_yaw_endpoint_rejects_invalid_normal_chunk(chunk: object) -> None:
    coupler = _asymmetric_coupler()
    with pytest.raises(ValueError, match="chunk_normals"):
        coupler.couple_measure_uniform_yaw(DirectionalMeasure.empty(), 1.0, chunk_normals=chunk)  # type: ignore[arg-type]


def test_uniform_yaw_endpoint_is_level_two_only() -> None:
    coupler = _asymmetric_coupler()
    coupler.level = 3
    with pytest.raises(ValueError, match="level 2"):
        coupler.couple_measure_uniform_yaw(DirectionalMeasure.empty(), 1.0)
