from __future__ import annotations

import time
from dataclasses import fields
from pathlib import Path

import numpy as np
import pytest

from semantic_twin.exposure import coupler as coupler_module
from semantic_twin.exposure import BodyCoupler, BodyExposure
from semantic_twin.transport import DirectionalMeasure
from semantic_twin.transport.next_event import NextEventField
from semantic_twin.illumination import fibonacci_sphere


def _real_level_two_coupler(*, level2_backend: str = "numpy") -> BodyCoupler:
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
    coupler.body_anterior_axis = np.array([0.0, -1.0, 0.0], dtype=np.float64)
    coupler._body_frame_error = None
    coupler.level2_backend = level2_backend
    coupler.level2_algorithm = (
        coupler_module.LEVEL2_NUMPY_ALGORITHM if level2_backend == "numpy" else coupler_module.LEVEL2_DEVICE_ALGORITHM
    )
    coupler.level2_direction_block_size = (
        None if level2_backend == "numpy" else coupler_module.LEVEL2_DEVICE_CHUNK_CELLS
    )
    coupler._level2_device_normals = None
    if level2_backend != "numpy":
        coupler._prepare_level2_device()
    return coupler


def _boundary_measure(seed: int = 912) -> DirectionalMeasure:
    rng = np.random.default_rng(seed)
    directions = rng.normal(size=(516, 3))
    directions /= np.linalg.norm(directions, axis=1, keepdims=True)
    atom_mass = rng.uniform(0.0, 0.01, size=3)
    diffuse_mass = rng.uniform(0.0, 0.01, size=513)
    diffuse_mass[[5, 211, 510]] = 0.0
    return DirectionalMeasure(directions[:3], atom_mass, directions[3:], diffuse_mass)


def _assert_exposure_close(actual: BodyExposure, expected: BodyExposure) -> None:
    for field in fields(BodyExposure):
        assert getattr(actual, field.name) == pytest.approx(
            getattr(expected, field.name),
            rel=2.0e-13,
            abs=2.0e-15,
        ), field.name


def test_llvm_level_two_matches_numpy_for_atoms_diffuse_yaw_and_fixed_chunk_boundary() -> None:
    numpy_coupler = _real_level_two_coupler()
    llvm_coupler = _real_level_two_coupler(level2_backend="llvm")
    measure = _boundary_measure()

    expected, expected_sab = numpy_coupler.couple_measure_with_sab(
        measure,
        0.83,
        chunk_cells=512,
        body_yaw_deg=37.0,
    )
    actual, actual_sab = llvm_coupler.couple_measure_with_sab(
        measure,
        0.83,
        chunk_cells=512,
        body_yaw_deg=37.0,
    )

    assert np.count_nonzero(measure.diffuse_mass) + np.count_nonzero(measure.atom_mass) == 513
    _assert_exposure_close(actual, expected)
    np.testing.assert_allclose(actual_sab, expected_sab, rtol=2.0e-13, atol=2.0e-15)


def test_llvm_level_two_zero_measure_is_exactly_zero() -> None:
    coupler = _real_level_two_coupler(level2_backend="llvm")
    exposure, sab = coupler.couple_measure_with_sab(DirectionalMeasure.empty(), 0.83)
    assert exposure == BodyExposure(0.83, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    np.testing.assert_array_equal(sab, np.zeros(coupler.body.n_triangles, dtype=np.float64))


def test_device_level_two_requires_the_sealed_512_direction_block() -> None:
    coupler = _real_level_two_coupler(level2_backend="llvm")
    with pytest.raises(ValueError, match="requires chunk_cells=512"):
        coupler.couple_measure_with_sab(_boundary_measure(), 0.83, chunk_cells=511)


def test_llvm_level_two_is_bit_deterministic_and_reuses_compiled_kernel() -> None:
    dr = pytest.importorskip("drjit")
    coupler = _real_level_two_coupler(level2_backend="llvm")
    measure = _boundary_measure()
    with dr.scoped_set_flag(dr.JitFlag.KernelHistory, True):
        first_exposure, first_sab = coupler.couple_measure_with_sab(measure, 0.83, body_yaw_deg=37.0)
        first_history = dr.kernel_history()
        second_exposure, second_sab = coupler.couple_measure_with_sab(measure, 0.83, body_yaw_deg=37.0)
        second_history = dr.kernel_history()

    assert first_exposure == second_exposure
    np.testing.assert_array_equal(first_sab, second_sab)
    first_hashes = {entry["hash"] for entry in first_history if "hash" in entry}
    reused = [entry for entry in second_history if entry.get("hash") in first_hashes]
    assert reused
    assert all(entry["cache_hit"] for entry in reused)


def test_requested_cuda_body_backend_never_falls_back(monkeypatch) -> None:
    dr = pytest.importorskip("drjit")
    original = dr.has_backend
    monkeypatch.setattr(
        dr,
        "has_backend",
        lambda backend: False if backend == dr.JitBackend.CUDA else original(backend),
    )
    with pytest.raises(RuntimeError, match="CUDA body coupling was requested"):
        coupler_module._drjit_level2_types("cuda")


@pytest.mark.slow
def test_duke_cuda_level_two_parity_determinism_and_timing(record_property) -> None:
    dr = pytest.importorskip("drjit")
    if not dr.has_backend(dr.JitBackend.CUDA):
        pytest.skip("Dr.Jit CUDA backend is unavailable")
    phantom = Path(__file__).resolve().parents[4] / "data" / "duke.stl"
    if not phantom.is_file():
        pytest.skip("Duke phantom is unavailable")
    numpy_coupler = BodyCoupler(str(phantom), 15.0e9, body_mass_kg=72.4)
    cuda_coupler = BodyCoupler(str(phantom), 15.0e9, body_mass_kg=72.4, level2_backend="cuda")
    measure = _boundary_measure()

    cuda_coupler.couple_measure_with_sab(measure, 0.83, body_yaw_deg=37.0)
    cpu_start = time.perf_counter()
    expected, expected_sab = numpy_coupler.couple_measure_with_sab(measure, 0.83, body_yaw_deg=37.0)
    cpu_seconds = time.perf_counter() - cpu_start
    with dr.scoped_set_flag(dr.JitFlag.KernelHistory, True):
        cuda_start = time.perf_counter()
        actual, actual_sab = cuda_coupler.couple_measure_with_sab(measure, 0.83, body_yaw_deg=37.0)
        cuda_seconds = time.perf_counter() - cuda_start
        first_history = dr.kernel_history()
        repeated, repeated_sab = cuda_coupler.couple_measure_with_sab(measure, 0.83, body_yaw_deg=37.0)
        second_history = dr.kernel_history()

    absolute_error = np.abs(actual_sab - expected_sab)
    relative_error = absolute_error / np.maximum(np.abs(expected_sab), np.finfo(np.float64).tiny)
    first_hashes = {entry["hash"] for entry in first_history if "hash" in entry}
    reused = [entry for entry in second_history if entry.get("hash") in first_hashes]
    record_property("cpu_seconds", cpu_seconds)
    record_property("cuda_seconds", cuda_seconds)
    record_property("cpu_cuda_ratio", cpu_seconds / cuda_seconds)
    record_property("max_abs_sab_error", float(np.max(absolute_error)))
    record_property("max_rel_sab_error", float(np.max(relative_error)))
    record_property("reused_kernel_count", len(reused))
    assert actual_sab.shape == (56_024,)
    _assert_exposure_close(actual, expected)
    np.testing.assert_allclose(actual_sab, expected_sab, rtol=2.0e-13, atol=2.0e-15)
    assert repeated == actual
    np.testing.assert_array_equal(repeated_sab, actual_sab)
    assert reused
    assert all(entry["cache_hit"] for entry in reused)
    assert cpu_seconds > 0.0
    assert cuda_seconds > 0.0


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
