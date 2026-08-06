from __future__ import annotations

from dataclasses import fields

import numpy as np
import pytest

from semantic_twin.exposure import BodyCoupler, BodyExposure
from semantic_twin.transport import DirectionalMeasure
from semantic_twin.transport.next_event import NextEventField
from semantic_twin.illumination import fibonacci_sphere


def _real_level_two_coupler() -> BodyCoupler:
    pytest.importorskip("aegis")
    from aegis.engine import DosimetryEngine
    from aegis.geometry.mesh import BodyMesh
    from aegis.tissue import TissueModel

    corners = np.array(
        [
            [0.0, 0.0, 0.0],
            [2.0, 0.0, 0.0],
            [2.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 3.0],
            [2.0, 0.0, 3.0],
            [2.0, 1.0, 3.0],
            [0.0, 1.0, 3.0],
        ],
        dtype=np.float64,
    )
    quads = ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))
    triangles = np.asarray(
        [[corners[a], corners[b], corners[c]] for a, b, c, _d in quads]
        + [[corners[a], corners[c], corners[d]] for a, _b, c, d in quads]
    )
    body = BodyMesh.from_arrays(triangles, name="couple-many-box")
    tissue = TissueModel.from_database("Skin", 15.0e9)
    coupler = BodyCoupler.__new__(BodyCoupler)
    coupler.body = body
    coupler.tissue = tissue
    coupler.engine = DosimetryEngine(tissue)
    coupler.level = 2
    coupler.body_mass_kg = 70.0
    coupler.frequency_hz = 15.0e9
    return coupler


def test_couple_many_forced_chunks_match_normal_level_two_coupling() -> None:
    coupler = _real_level_two_coupler()
    cells = 37
    chunk_cells = 7
    grid = fibonacci_sphere(cells)
    solid_angle = 4.0 * np.pi / cells
    rng = np.random.default_rng(481)
    spectra = np.stack(
        (
            np.full(cells, 1.0 / (4.0 * np.pi)),
            np.abs(rng.normal(size=cells)),
            np.eye(cells, dtype=np.float64)[11] / solid_angle,
        )
    )
    reference_s0 = 0.73

    expected = tuple(coupler.couple(grid, rho, solid_angle, reference_s0) for rho in spectra)
    actual = coupler.couple_many(
        grid,
        spectra,
        solid_angle,
        reference_s0,
        chunk_cells=chunk_cells,
    )
    retained, sab = coupler.couple_many_with_sab(
        grid,
        spectra,
        solid_angle,
        reference_s0,
        chunk_cells=chunk_cells,
    )

    assert chunk_cells < cells
    assert len(actual) == len(expected)
    assert sab.shape == (len(spectra), coupler.body.n_triangles)
    for index, (chunked, normal) in enumerate(zip(actual, expected, strict=True)):
        for field in fields(BodyExposure):
            assert getattr(chunked, field.name) == pytest.approx(
                getattr(normal, field.name),
                rel=2.0e-14,
                abs=1.0e-15,
            ), field.name
        assert retained[index] == chunked
        assert np.max(sab[index]) == chunked.peak_sab_w_m2
        assert np.sum(sab[index] * coupler.body.areas) == chunked.absorbed_power_w
        assert np.sum(sab[index] * coupler.body.areas) / coupler.body.total_area == chunked.mean_sab_w_m2

    weights = np.asarray([0.2, 0.3, 0.5])
    _mean_exposure, mean_sab = coupler.couple_many_with_sab(
        grid,
        np.sum(weights[:, None] * spectra, axis=0, keepdims=True),
        solid_angle,
        reference_s0,
        chunk_cells=chunk_cells,
    )
    assert mean_sab[0] == pytest.approx(np.sum(weights[:, None] * sab, axis=0), rel=2.0e-14, abs=1.0e-15)


def test_couple_measure_matches_explicit_combined_propagation_paths() -> None:
    coupler = _real_level_two_coupler()
    measure = DirectionalMeasure(
        atom_k_hat=np.array([[1.0, 0.0, 0.0], [0.0, 0.0, -1.0]]),
        atom_mass=np.array([0.2, 0.1]),
        diffuse_k_hat=np.array([[0.0, 1.0, 0.0]]),
        diffuse_mass=np.array([0.3]),
    )
    reference_s0 = 0.73
    actual = coupler.couple_measure(measure, reference_s0)

    from aegis.paths import PropagationPaths

    directions = np.concatenate((measure.atom_k_hat, measure.diffuse_k_hat))
    powers = np.concatenate((measure.atom_mass, measure.diffuse_mass)) * reference_s0
    expected_result = coupler.engine.compute(
        coupler.body,
        PropagationPaths.from_powers(directions, powers),
        level=coupler.level,
        body_mass=coupler.body_mass_kg,
    )
    expected_sab = np.asarray(expected_result.sab, dtype=np.float64)
    chunked, chunked_sab = coupler.couple_measure_with_sab(measure, reference_s0, chunk_cells=1)
    assert actual.reference_s0_w_m2 == reference_s0
    assert actual.arriving_power_density_w_m2 == pytest.approx(np.sum(powers))
    assert actual.susceptibility == pytest.approx(measure.total_transfer)
    assert actual.peak_sab_w_m2 == pytest.approx(np.max(expected_sab))
    assert actual.absorbed_power_w == pytest.approx(expected_result.p_abs)
    assert actual.mean_sab_w_m2 == pytest.approx(expected_result.p_abs / coupler.body.total_area)
    np.testing.assert_allclose(chunked_sab, expected_sab, rtol=2.0e-14, atol=1.0e-15)
    assert chunked == actual


def test_measure_chunking_and_mixed_additivity_match_explicit_sab() -> None:
    coupler = _real_level_two_coupler()
    atom_dirs = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, -1.0]])
    diffuse_dirs = np.array([[0.0, 1.0, 0.0], [-1.0, 0.0, 0.0]])
    atom = DirectionalMeasure(atom_dirs, np.array([0.2, 0.1]), np.empty((0, 3)), np.empty(0))
    diffuse = DirectionalMeasure(np.empty((0, 3)), np.empty(0), diffuse_dirs, np.array([0.3, 0.4]))
    mixed = DirectionalMeasure(atom_dirs, np.array([0.2, 0.1]), diffuse_dirs, np.array([0.3, 0.4]))
    reference_s0 = 0.73
    atom_exposure, atom_sab = coupler.couple_measure_with_sab(atom, reference_s0, chunk_cells=1)
    diffuse_exposure, diffuse_sab = coupler.couple_measure_with_sab(diffuse, reference_s0, chunk_cells=1)
    mixed_exposure, mixed_sab = coupler.couple_measure_with_sab(mixed, reference_s0, chunk_cells=1)
    np.testing.assert_allclose(mixed_sab, atom_sab + diffuse_sab, rtol=2.0e-14, atol=1.0e-15)
    assert mixed_exposure.absorbed_power_w == pytest.approx(
        atom_exposure.absorbed_power_w + diffuse_exposure.absorbed_power_w,
        rel=2.0e-14,
        abs=1.0e-15,
    )

    repeated = DirectionalMeasure(
        np.tile(atom_dirs, (4, 1)),
        np.tile([0.2, 0.1], 4) / 4.0,
        np.tile(diffuse_dirs, (4, 1)),
        np.tile([0.3, 0.4], 4) / 4.0,
    )
    repeated_exposure, repeated_sab = coupler.couple_measure_with_sab(repeated, reference_s0, chunk_cells=2)
    assert repeated_exposure.arriving_power_density_w_m2 == pytest.approx(mixed_exposure.arriving_power_density_w_m2)
    assert repeated_exposure.susceptibility == pytest.approx(mixed_exposure.susceptibility)
    assert repeated_exposure.absorbed_power_w == pytest.approx(mixed_exposure.absorbed_power_w)
    assert repeated_exposure.peak_sab_w_m2 == pytest.approx(mixed_exposure.peak_sab_w_m2)
    np.testing.assert_allclose(repeated_sab, mixed_sab, rtol=2.0e-14, atol=1.0e-15)


def test_nonempty_measure_with_zero_reference_s0_is_all_zero() -> None:
    coupler = _real_level_two_coupler()
    measure = DirectionalMeasure(
        np.array([[1.0, 0.0, 0.0]]),
        np.array([1.0]),
        np.empty((0, 3)),
        np.empty(0),
    )
    exposure, sab = coupler.couple_measure_with_sab(measure, 0.0)
    assert exposure == BodyExposure(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    assert np.all(sab == 0.0)


def test_atom_only_measure_is_independent_of_diagnostic_grid() -> None:
    coupler = _real_level_two_coupler()
    kwargs = dict(
        direct_k_hat=np.array([[1.0, 0.0, 0.0], [0.0, 0.0, -1.0]]),
        direct_atom_mass=np.array([0.2, 0.1]),
    )
    coarse = NextEventField(
        local_grid=np.array([[1.0, 0.0, 0.0]]),
        solid_angle=4.0 * np.pi,
        direct_mass=np.array([0.3]),
        bounced_mass=np.array([0.0]),
        **kwargs,
    )
    fine = NextEventField(
        local_grid=np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]),
        solid_angle=4.0 * np.pi / 3.0,
        direct_mass=np.zeros(3),
        bounced_mass=np.zeros(3),
        **kwargs,
    )
    assert coupler.couple_measure(coarse.directional_measure(1.0), 0.73) == coupler.couple_measure(
        fine.directional_measure(1.0), 0.73
    )


@pytest.mark.parametrize("reference_s0", [-1.0, np.nan, np.inf])
def test_couple_measure_rejects_invalid_reference_s0(reference_s0: float) -> None:
    coupler = _real_level_two_coupler()
    with pytest.raises(ValueError, match="reference_s0_w_m2"):
        coupler.couple_measure(DirectionalMeasure.empty(), reference_s0)
