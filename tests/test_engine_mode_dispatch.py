"""Tests for mode-based engine API: bound, aggregate, coherent, ecbf.

The existing test_engine_modes.py covers mode="spatial" thoroughly but
does not test the other four modes. This file fills that gap and also
tests compute_sab for coherent levels (7-8), which had zero coverage.
"""

import numpy as np
import pytest
from conftest import make_flat_mesh, make_icosahedron

from aegis.engine import DosimetryEngine, coherent_sinc
from aegis.geometry.projected_area import compute_projected_area, fibonacci_sphere
from aegis.paths import PropagationPaths
from aegis.precoder import Precoder
from aegis.tissue.dielectric import SKIN_28GHZ

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine():
    return DosimetryEngine(SKIN_28GHZ)


@pytest.fixture
def ico_mesh():
    return make_icosahedron()


@pytest.fixture
def flat_mesh():
    return make_flat_mesh(50)


@pytest.fixture
def multi_path():
    rng = np.random.default_rng(77)
    N = 15
    k_hat = rng.standard_normal((N, 3))
    k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
    power = rng.uniform(0.5, 3.0, size=N)
    return PropagationPaths.from_powers(k_hat, power)


@pytest.fixture
def single_path_down():
    return PropagationPaths.from_powers(
        k_hat=np.array([[0.0, 0.0, -1.0]]),
        power=np.array([1.0]),
    )


@pytest.fixture
def coherent_paths():
    """Multi-path coherent data with psi and element_index."""
    rng = np.random.default_rng(42)
    N, M_ant = 8, 4
    k_hat = rng.standard_normal((N, 3))
    k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
    psi = rng.standard_normal((N, 3)) + 1j * rng.standard_normal((N, 3))
    for i in range(N):
        psi[i] -= np.dot(psi[i], k_hat[i]) * k_hat[i]
    element_index = rng.integers(0, M_ant, size=N)
    return PropagationPaths(
        k_hat=k_hat,
        psi=psi,
        element_index=element_index,
        delay=np.zeros(N),
        is_los=np.ones(N, dtype=bool),
    ), M_ant


# ---------------------------------------------------------------------------
# mode="bound" (level 0)
# ---------------------------------------------------------------------------


class TestModeBound:
    def test_bound_matches_level0(self, engine, ico_mesh, multi_path):
        """mode='bound' must produce the same result as level=0."""
        dirs = fibonacci_sphere(100)
        A_perp = compute_projected_area(ico_mesh.normals, ico_mesh.areas, dirs)
        A_ab = float(np.mean(A_perp))
        D_max = float(np.max(A_perp) / np.mean(A_perp)) if np.mean(A_perp) > 0 else 1.0

        r_mode = engine.compute(ico_mesh, multi_path, mode="bound", A_ab=A_ab, D_max=D_max)
        r_level = engine.compute(ico_mesh, multi_path, level=0, A_ab=A_ab, D_max=D_max)
        np.testing.assert_allclose(r_mode.sab, r_level.sab, rtol=1e-12)
        assert r_mode.p_abs == pytest.approx(r_level.p_abs, rel=1e-12)

    def test_bound_fidelity_level_is_zero(self, engine, ico_mesh, multi_path):
        dirs = fibonacci_sphere(100)
        A_perp = compute_projected_area(ico_mesh.normals, ico_mesh.areas, dirs)
        A_ab = float(np.mean(A_perp))
        D_max = float(np.max(A_perp) / np.mean(A_perp)) if np.mean(A_perp) > 0 else 1.0

        r = engine.compute(ico_mesh, multi_path, mode="bound", A_ab=A_ab, D_max=D_max)
        assert r.fidelity_level == 0
        assert r.mode == "bound"

    def test_bound_sab_non_negative(self, engine, ico_mesh, multi_path):
        dirs = fibonacci_sphere(100)
        A_perp = compute_projected_area(ico_mesh.normals, ico_mesh.areas, dirs)
        A_ab = float(np.mean(A_perp))
        D_max = float(np.max(A_perp) / np.mean(A_perp)) if np.mean(A_perp) > 0 else 1.0

        r = engine.compute(ico_mesh, multi_path, mode="bound", A_ab=A_ab, D_max=D_max)
        assert np.all(r.sab >= 0)


# ---------------------------------------------------------------------------
# mode="aggregate" (level 1)
# ---------------------------------------------------------------------------


class TestModeAggregate:
    def test_aggregate_matches_level1(self, engine, ico_mesh, multi_path):
        """mode='aggregate' must produce the same result as level=1."""
        dirs = fibonacci_sphere(100)
        A_perp = compute_projected_area(ico_mesh.normals, ico_mesh.areas, dirs)
        A_ab = float(np.mean(A_perp))

        r_mode = engine.compute(ico_mesh, multi_path, mode="aggregate", A_ab=A_ab)
        r_level = engine.compute(ico_mesh, multi_path, level=1, A_ab=A_ab)
        np.testing.assert_allclose(r_mode.sab, r_level.sab, rtol=1e-12)

    def test_aggregate_fidelity_level_is_one(self, engine, ico_mesh, multi_path):
        dirs = fibonacci_sphere(100)
        A_perp = compute_projected_area(ico_mesh.normals, ico_mesh.areas, dirs)
        A_ab = float(np.mean(A_perp))

        r = engine.compute(ico_mesh, multi_path, mode="aggregate", A_ab=A_ab)
        assert r.fidelity_level == 1
        assert r.mode == "aggregate"

    def test_aggregate_sab_non_negative(self, engine, ico_mesh, multi_path):
        dirs = fibonacci_sphere(100)
        A_perp = compute_projected_area(ico_mesh.normals, ico_mesh.areas, dirs)
        A_ab = float(np.mean(A_perp))

        r = engine.compute(ico_mesh, multi_path, mode="aggregate", A_ab=A_ab)
        assert np.all(r.sab >= 0)


# ---------------------------------------------------------------------------
# mode="coherent" (level 7)
# ---------------------------------------------------------------------------


class TestModeCoherent:
    def test_coherent_matches_level7(self, engine, ico_mesh, coherent_paths):
        """mode='coherent' must produce the same result as level=7."""
        paths, M_ant = coherent_paths
        x = np.ones(M_ant, dtype=complex)
        precoder = Precoder(x=x)

        r_mode = engine.compute(ico_mesh, paths, mode="coherent", precoder=precoder)
        r_level = engine.compute(ico_mesh, paths, level=7, precoder=precoder)
        np.testing.assert_allclose(r_mode.sab, r_level.sab, rtol=1e-12)
        assert r_mode.p_abs == pytest.approx(r_level.p_abs, rel=1e-12)

    def test_coherent_fidelity_level_is_seven(self, engine, ico_mesh, coherent_paths):
        paths, M_ant = coherent_paths
        precoder = Precoder(x=np.ones(M_ant, dtype=complex))
        r = engine.compute(ico_mesh, paths, mode="coherent", precoder=precoder)
        assert r.fidelity_level == 7
        assert r.mode == "coherent"

    def test_coherent_has_Q_and_eigenvalues(self, engine, ico_mesh, coherent_paths):
        paths, M_ant = coherent_paths
        precoder = Precoder(x=np.ones(M_ant, dtype=complex))
        r = engine.compute(ico_mesh, paths, mode="coherent", precoder=precoder)
        assert r.Q is not None
        assert r.Q.shape == (M_ant, M_ant)
        assert r.eigenvalues is not None

    def test_coherent_sab_non_negative(self, engine, ico_mesh, coherent_paths):
        paths, M_ant = coherent_paths
        precoder = Precoder(x=np.ones(M_ant, dtype=complex))
        r = engine.compute(ico_mesh, paths, mode="coherent", precoder=precoder)
        assert np.all(r.sab >= 0)

    def test_coherent_requires_precoder(self, engine, ico_mesh, coherent_paths):
        paths, _ = coherent_paths
        with pytest.raises(ValueError, match="precoder"):
            engine.compute(ico_mesh, paths, mode="coherent")

    def test_coherent_with_h_computes_rho(self, engine, ico_mesh, coherent_paths):
        paths, M_ant = coherent_paths
        rng = np.random.default_rng(55)
        h = rng.standard_normal(M_ant) + 1j * rng.standard_normal(M_ant)
        precoder = Precoder(x=np.ones(M_ant, dtype=complex))
        r = engine.compute(ico_mesh, paths, mode="coherent", precoder=precoder, h=h)
        assert r.rho is not None
        assert 0.0 <= r.rho <= 1.0 + 1e-10

    def test_coherent_freq_override_changes_output(self, engine, ico_mesh, coherent_paths):
        """freq_hz override must change coherent SAB and S_inc."""
        paths, M_ant = coherent_paths
        precoder = Precoder(x=np.ones(M_ant, dtype=complex))

        low = engine.compute(
            ico_mesh,
            paths,
            mode="coherent",
            precoder=precoder,
            freq_hz=28e9,
            spatial_averaging=False,
        )
        high = engine.compute(
            ico_mesh,
            paths,
            mode="coherent",
            precoder=precoder,
            freq_hz=60e9,
            spatial_averaging=False,
        )

        assert not np.allclose(low.sab, high.sab, rtol=1e-6, atol=1e-12)
        assert low.sinc is not None
        assert high.sinc is not None
        assert not np.allclose(low.sinc, high.sinc, rtol=1e-6, atol=1e-12)


# ---------------------------------------------------------------------------
# mode="ecbf" (level 8)
# ---------------------------------------------------------------------------


class TestModeEcbf:
    def test_ecbf_matches_level8(self, engine, ico_mesh, coherent_paths):
        """mode='ecbf' must produce the same result as level=8."""
        paths, M_ant = coherent_paths
        rng = np.random.default_rng(66)
        h = rng.standard_normal(M_ant) + 1j * rng.standard_normal(M_ant)

        r_mode = engine.compute(ico_mesh, paths, mode="ecbf", h=h)
        r_level = engine.compute(ico_mesh, paths, level=8, h=h)
        np.testing.assert_allclose(r_mode.sab, r_level.sab, rtol=1e-12)
        assert r_mode.p_abs == pytest.approx(r_level.p_abs, rel=1e-12)

    def test_ecbf_fidelity_level_is_eight(self, engine, ico_mesh, coherent_paths):
        paths, M_ant = coherent_paths
        rng = np.random.default_rng(66)
        h = rng.standard_normal(M_ant) + 1j * rng.standard_normal(M_ant)
        r = engine.compute(ico_mesh, paths, mode="ecbf", h=h)
        assert r.fidelity_level == 8
        assert r.mode == "ecbf"

    def test_ecbf_requires_h(self, engine, ico_mesh, coherent_paths):
        paths, _ = coherent_paths
        with pytest.raises(ValueError, match="h"):
            engine.compute(ico_mesh, paths, mode="ecbf")

    def test_ecbf_returns_x_star_and_rho(self, engine, ico_mesh, coherent_paths):
        paths, M_ant = coherent_paths
        rng = np.random.default_rng(66)
        h = rng.standard_normal(M_ant) + 1j * rng.standard_normal(M_ant)
        r = engine.compute(ico_mesh, paths, mode="ecbf", h=h)
        assert r.x_star is not None
        assert r.x_star.shape == (M_ant,)
        assert r.rho is not None
        assert 0.0 <= r.rho <= 1.0 + 1e-10

    def test_ecbf_sab_non_negative(self, engine, ico_mesh, coherent_paths):
        paths, M_ant = coherent_paths
        rng = np.random.default_rng(66)
        h = rng.standard_normal(M_ant) + 1j * rng.standard_normal(M_ant)
        r = engine.compute(ico_mesh, paths, mode="ecbf", h=h)
        assert np.all(r.sab >= 0)


# ---------------------------------------------------------------------------
# Unknown mode
# ---------------------------------------------------------------------------


class TestModeInvalid:
    def test_unknown_mode_raises(self, engine, ico_mesh, multi_path):
        with pytest.raises(ValueError, match="Unknown mode"):
            engine.compute(ico_mesh, multi_path, mode="fantasy")

    def test_compute_sab_unknown_mode_raises(self, engine, ico_mesh, multi_path):
        with pytest.raises(ValueError, match="Unknown mode"):
            engine.compute_sab(ico_mesh, multi_path, mode="fantasy")


# ---------------------------------------------------------------------------
# compute_sab for coherent levels (7-8) -- previously untested
# ---------------------------------------------------------------------------


class TestComputeSabCoherent:
    def test_compute_sab_level7(self, engine, ico_mesh, coherent_paths):
        """compute_sab at level 7 returns raw array matching compute().sab."""
        paths, M_ant = coherent_paths
        x = np.ones(M_ant, dtype=complex)
        precoder = Precoder(x=x)

        sab_raw = engine.compute_sab(ico_mesh, paths, level=7, precoder=precoder)
        result = engine.compute(ico_mesh, paths, level=7, precoder=precoder)

        # compute_sab returns the backend's native array type (JAX or NumPy)
        sab_np = np.asarray(sab_raw)
        assert sab_np.shape == (ico_mesh.n_triangles,)
        np.testing.assert_allclose(sab_np, result.sab, rtol=1e-12)

    def test_compute_sab_level7_precoder_x(self, engine, ico_mesh, coherent_paths):
        """compute_sab at level 7 accepts precoder_x directly."""
        paths, M_ant = coherent_paths
        x = np.ones(M_ant, dtype=complex)
        sab = engine.compute_sab(ico_mesh, paths, level=7, precoder_x=x)
        assert np.asarray(sab).shape == (ico_mesh.n_triangles,)
        assert np.all(sab >= 0)

    def test_compute_sab_level7_requires_precoder(self, engine, ico_mesh, coherent_paths):
        """Level 7 without precoder must raise."""
        paths, _ = coherent_paths
        with pytest.raises(ValueError, match="precoder"):
            engine.compute_sab(ico_mesh, paths, level=7)

    def test_compute_sab_level8(self, engine, ico_mesh, coherent_paths):
        """compute_sab at level 8 returns raw array matching compute().sab."""
        paths, M_ant = coherent_paths
        rng = np.random.default_rng(88)
        h = rng.standard_normal(M_ant) + 1j * rng.standard_normal(M_ant)
        precoder = Precoder(x=np.ones(M_ant, dtype=complex))

        sab_raw = engine.compute_sab(ico_mesh, paths, level=8, precoder=precoder, h=h)

        # compute_sab returns the backend's native array type (JAX or NumPy)
        sab_np = np.asarray(sab_raw)
        assert sab_np.shape == (ico_mesh.n_triangles,)
        assert np.all(sab_np >= 0)

    def test_compute_sab_level8_requires_h(self, engine, ico_mesh, coherent_paths):
        """Level 8 without h must raise."""
        paths, M_ant = coherent_paths
        precoder = Precoder(x=np.ones(M_ant, dtype=complex))
        with pytest.raises(ValueError, match="h"):
            engine.compute_sab(ico_mesh, paths, level=8, precoder=precoder)

    def test_compute_sab_mode_spatial_matches_level(self, engine, ico_mesh, multi_path):
        """compute_sab with mode='spatial' matches mode-less level 3."""
        sab_mode = engine.compute_sab(ico_mesh, multi_path, mode="spatial")
        sab_level = engine.compute_sab(ico_mesh, multi_path, level=3)
        np.testing.assert_allclose(sab_mode, sab_level, rtol=1e-12)


# ---------------------------------------------------------------------------
# coherent_sinc physics invariants
# ---------------------------------------------------------------------------


class TestCoherentSinc:
    def test_sinc_non_negative(self):
        """Incident power density must be non-negative."""
        rng = np.random.default_rng(11)
        M, N, M_ant = 10, 5, 3
        centroids = rng.standard_normal((M, 3))
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        psi = rng.standard_normal((N, 3)) + 1j * rng.standard_normal((N, 3))
        element_index = rng.integers(0, M_ant, size=N)
        x = rng.standard_normal(M_ant) + 1j * rng.standard_normal(M_ant)

        sinc = coherent_sinc(centroids, k_hat, psi, element_index, x, 28e9)
        assert np.all(sinc >= 0)
        assert sinc.shape == (M,)

    def test_sinc_zero_precoder(self):
        """Zero precoder should give zero incident power density."""
        centroids = np.array([[0.0, 0.0, 0.0]])
        k_hat = np.array([[0.0, 0.0, -1.0]])
        psi = np.array([[1.0 + 0j, 0.0, 0.0]])
        element_index = np.array([0])
        x = np.array([0.0 + 0j])

        sinc = coherent_sinc(centroids, k_hat, psi, element_index, x, 28e9)
        assert sinc[0] == pytest.approx(0.0, abs=1e-30)

    def test_sinc_multi_stream_non_negative(self):
        """Multi-stream (2D x) incident power density must be non-negative."""
        rng = np.random.default_rng(22)
        M, N, M_ant, K = 10, 5, 4, 2
        centroids = rng.standard_normal((M, 3))
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        psi = rng.standard_normal((N, 3)) + 1j * rng.standard_normal((N, 3))
        element_index = rng.integers(0, M_ant, size=N)
        W = rng.standard_normal((M_ant, K)) + 1j * rng.standard_normal((M_ant, K))

        sinc = coherent_sinc(centroids, k_hat, psi, element_index, W, 28e9)
        assert np.all(sinc >= 0)
        assert sinc.shape == (M,)

    def test_sinc_scales_with_precoder_power(self):
        """Doubling the precoder should quadruple the power density."""
        rng = np.random.default_rng(33)
        M, N = 5, 3
        centroids = rng.standard_normal((M, 3))
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        psi = rng.standard_normal((N, 3)) + 1j * rng.standard_normal((N, 3))
        element_index = np.zeros(N, dtype=np.intp)
        x = rng.standard_normal(1) + 1j * rng.standard_normal(1)

        sinc_1x = coherent_sinc(centroids, k_hat, psi, element_index, x, 28e9)
        sinc_2x = coherent_sinc(centroids, k_hat, psi, element_index, 2 * x, 28e9)
        np.testing.assert_allclose(sinc_2x, 4 * sinc_1x, rtol=1e-12)

    def test_single_stream_matches_multi_stream_k1(self):
        """1D precoder and 2D precoder with K=1 must give the same result."""
        rng = np.random.default_rng(44)
        M, N, M_ant = 8, 4, 3
        centroids = rng.standard_normal((M, 3))
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        psi = rng.standard_normal((N, 3)) + 1j * rng.standard_normal((N, 3))
        element_index = rng.integers(0, M_ant, size=N)
        x = rng.standard_normal(M_ant) + 1j * rng.standard_normal(M_ant)

        sinc_1d = coherent_sinc(centroids, k_hat, psi, element_index, x, 28e9)
        sinc_2d = coherent_sinc(centroids, k_hat, psi, element_index, x.reshape(-1, 1), 28e9)
        np.testing.assert_allclose(sinc_1d, sinc_2d, rtol=1e-12)


# ---------------------------------------------------------------------------
# Mode corrections metadata
# ---------------------------------------------------------------------------


class TestModeCorrectionsMetadata:
    def test_spatial_records_fresnel_by_default(self, engine, ico_mesh, multi_path):
        r = engine.compute(ico_mesh, multi_path, mode="spatial")
        assert "fresnel" in r.corrections

    def test_spatial_no_fresnel_no_correction(self, engine, ico_mesh, multi_path):
        r = engine.compute(ico_mesh, multi_path, mode="spatial", fresnel=False)
        assert "fresnel" not in r.corrections

    def test_spatial_all_corrections(self, engine, ico_mesh, multi_path):
        H = np.full(ico_mesh.n_triangles, 5.0)
        r = engine.compute(
            ico_mesh,
            multi_path,
            mode="spatial",
            fresnel=True,
            polarisation=True,
            q=0.3,
            curvature=True,
            diffraction=True,
            curvature_H=H,
        )
        assert "fresnel" in r.corrections
        assert "polarisation" in r.corrections
        assert "curvature" in r.corrections
        assert "diffraction" in r.corrections

    def test_bound_no_corrections(self, engine, ico_mesh, multi_path):
        """Non-spatial modes should have empty corrections."""
        dirs = fibonacci_sphere(100)
        A_perp = compute_projected_area(ico_mesh.normals, ico_mesh.areas, dirs)
        A_ab = float(np.mean(A_perp))
        D_max = max(float(np.max(A_perp) / np.mean(A_perp)), 1.0)
        r = engine.compute(ico_mesh, multi_path, mode="bound", A_ab=A_ab, D_max=D_max)
        assert r.corrections == ()


# ---------------------------------------------------------------------------
# compute_with_timings for mode-based API
# ---------------------------------------------------------------------------


class TestComputeWithTimingsModes:
    def test_bound_mode_with_timings(self, engine, ico_mesh, multi_path):
        dirs = fibonacci_sphere(100)
        A_perp = compute_projected_area(ico_mesh.normals, ico_mesh.areas, dirs)
        A_ab = float(np.mean(A_perp))
        D_max = max(float(np.max(A_perp) / np.mean(A_perp)), 1.0)

        result, timings = engine.compute_with_timings(ico_mesh, multi_path, mode="bound", A_ab=A_ab, D_max=D_max)
        assert isinstance(result.sab, np.ndarray)
        assert isinstance(timings, dict)

    def test_coherent_mode_with_timings(self, engine, ico_mesh, coherent_paths):
        paths, M_ant = coherent_paths
        precoder = Precoder(x=np.ones(M_ant, dtype=complex))
        result, timings = engine.compute_with_timings(ico_mesh, paths, mode="coherent", precoder=precoder)
        assert result.Q is not None
        assert isinstance(timings, dict)
