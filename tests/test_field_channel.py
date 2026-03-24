"""Tests for the field channel and serialization edge cases.

Covers:
- compute_field_channel() basic correctness, element accumulation, phase
- DosimetryResult.to_dict()/to_json() with complex arrays
- level1_aggregate directivity weighting paths
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from aegis.coherent.field_channel import (
    _accumulate_by_element_numpy,
    compute_field_channel,
)
from aegis.result import DosimetryResult

# ---------------------------------------------------------------------------
# compute_field_channel tests
# ---------------------------------------------------------------------------


class TestFieldChannel:
    def _make_inputs(self, M=4, N=3, n_elements=2, freq_hz=28e9):
        rng = np.random.default_rng(42)
        centroids = rng.standard_normal((M, 3))
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        psi = rng.standard_normal((N, 3)) + 1j * rng.standard_normal((N, 3))
        element_index = rng.integers(0, n_elements, size=N).astype(np.intp)
        return centroids, k_hat, psi, element_index, freq_hz, n_elements

    def test_output_shape(self):
        M, N, n_el = 10, 5, 3
        c, k, psi, ei, f, ne = self._make_inputs(M, N, n_el)
        G = compute_field_channel(c, k, psi, ei, f, ne)
        assert G.shape == (M, 3, n_el)
        assert np.iscomplexobj(G)

    def test_single_element_single_path(self):
        """With one path and one element, G should be psi * phase."""
        centroids = np.array([[0.0, 0.0, 0.0]])
        k_hat = np.array([[0.0, 0.0, -1.0]])
        psi = np.array([[1.0 + 0j, 0.0, 0.0]])
        ei = np.array([0], dtype=np.intp)
        freq_hz = 28e9

        G = compute_field_channel(centroids, k_hat, psi, ei, freq_hz, 1)
        # At origin, phase_arg = -k0 * (0.0) = 0, so phase = 1
        # G = psi * 1 = psi
        np.testing.assert_allclose(G[0, :, 0], psi[0], atol=1e-12)

    def test_phase_at_nonzero_position(self):
        """Verify phase is correct at a non-origin centroid."""
        from aegis.constants import C_0

        freq_hz = 28e9
        k0 = 2 * np.pi * freq_hz / C_0
        r = np.array([[0.0, 0.0, 0.1]])  # 10cm along z
        k_hat = np.array([[0.0, 0.0, -1.0]])
        psi = np.array([[1.0 + 0j, 0.0, 0.0]])
        ei = np.array([0], dtype=np.intp)

        G = compute_field_channel(r, k_hat, psi, ei, freq_hz, 1)

        # Expected phase: exp(-i * k0 * k_hat . r) = exp(-i * k0 * (0*0 + 0*0 + (-1)*0.1))
        expected_phase = np.exp(1j * (-k0) * (k_hat[0] @ r[0]))
        expected_G = psi[0] * expected_phase
        np.testing.assert_allclose(G[0, :, 0], expected_G, rtol=1e-10)

    def test_element_accumulation(self):
        """Two paths from same element should sum their contributions."""
        centroids = np.array([[0.0, 0.0, 0.0]])
        k_hat = np.array([[0.0, 0.0, -1.0], [0.0, 0.0, -1.0]])
        psi = np.array([[1 + 0j, 0, 0], [0, 1 + 0j, 0]])
        ei = np.array([0, 0], dtype=np.intp)

        G = compute_field_channel(centroids, k_hat, psi, ei, 28e9, 1)
        # At origin, both phases are 1.0, so G = psi[0] + psi[1]
        expected = psi[0] + psi[1]
        np.testing.assert_allclose(G[0, :, 0], expected, atol=1e-12)

    def test_separate_elements_independent(self):
        """Paths from different elements should go to different columns."""
        centroids = np.array([[0.0, 0.0, 0.0]])
        k_hat = np.array([[0.0, 0.0, -1.0], [0.0, 0.0, -1.0]])
        psi = np.array([[1 + 0j, 0, 0], [0, 1 + 0j, 0]])
        ei = np.array([0, 1], dtype=np.intp)

        G = compute_field_channel(centroids, k_hat, psi, ei, 28e9, 2)
        np.testing.assert_allclose(G[0, :, 0], psi[0], atol=1e-12)
        np.testing.assert_allclose(G[0, :, 1], psi[1], atol=1e-12)

    def test_multiple_centroids(self):
        """G should have different phases at different positions."""
        centroids = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 0.01]])
        k_hat = np.array([[0.0, 0.0, -1.0]])
        psi = np.array([[1 + 0j, 0, 0]])
        ei = np.array([0], dtype=np.intp)

        G = compute_field_channel(centroids, k_hat, psi, ei, 28e9, 1)
        # Different centroids should yield different phases
        assert not np.allclose(G[0, :, 0], G[1, :, 0])

    def test_accumulate_numpy_empty_element(self):
        """Element with no paths should give zero."""
        weighted = np.ones((2, 3, 3), dtype=complex)
        element_index = np.array([0, 0, 0], dtype=np.intp)
        G = _accumulate_by_element_numpy(weighted, element_index, 2, 2)
        # Element 1 has no paths
        np.testing.assert_array_equal(G[:, :, 1], 0.0)

    def test_field_is_linear_in_psi(self):
        """Scaling psi by alpha should scale G by alpha."""
        args = self._make_inputs()
        G1 = compute_field_channel(*args)
        c, k, psi, ei, f, ne = args
        alpha = 2.5 + 1j * 0.3
        G2 = compute_field_channel(c, k, psi * alpha, ei, f, ne)
        np.testing.assert_allclose(G2, G1 * alpha, rtol=1e-10)


# ---------------------------------------------------------------------------
# DosimetryResult serialization with complex arrays
# ---------------------------------------------------------------------------


class TestComplexSerialization:
    def test_to_dict_complex_Q(self):
        """to_dict should serialize complex Q as real/imag dict."""
        Q = np.array([[1 + 2j, 3 + 4j], [5 + 6j, 7 + 8j]])
        result = DosimetryResult(
            sab=np.array([1.0, 2.0]),
            p_abs=0.01,
            fidelity_level=7,
            Q=Q,
        )
        d = result.to_dict()
        assert "Q" in d
        assert "real" in d["Q"]
        assert "imag" in d["Q"]
        np.testing.assert_allclose(d["Q"]["real"], Q.real.tolist())
        np.testing.assert_allclose(d["Q"]["imag"], Q.imag.tolist())

    def test_to_json_with_complex(self):
        """to_json should not crash with complex arrays."""
        Q = np.array([[1 + 2j, 3 + 4j], [5 + 6j, 7 + 8j]])
        eigenvalues = np.array([10.0 + 0j, 5.0 + 0j])
        x_star = np.array([0.5 + 0.5j, 0.3 - 0.2j])
        result = DosimetryResult(
            sab=np.array([1.0]),
            p_abs=0.01,
            fidelity_level=8,
            Q=Q,
            eigenvalues=eigenvalues,
            x_star=x_star,
        )
        j = result.to_json()
        parsed = json.loads(j)
        assert "Q" in parsed
        assert "eigenvalues" in parsed
        assert "x_star" in parsed

    def test_to_dict_real_arrays_unchanged(self):
        """Real arrays should still be plain lists, not real/imag dicts."""
        result = DosimetryResult(
            sab=np.array([1.0, 2.0]),
            p_abs=0.01,
            fidelity_level=2,
            sab_averaged=np.array([0.9, 1.8]),
        )
        d = result.to_dict()
        assert isinstance(d["sab"], list)
        assert isinstance(d["sab"][0], float)

    def test_to_dict_omits_none(self):
        result = DosimetryResult(
            sab=np.array([1.0]),
            p_abs=0.01,
            fidelity_level=2,
        )
        d = result.to_dict()
        assert "Q" not in d
        assert "x_star" not in d
        assert "sar_wb" not in d


# ---------------------------------------------------------------------------
# level1_aggregate directivity paths
# ---------------------------------------------------------------------------


class TestLevel1Directivity:
    def test_default_no_directivity(self):
        """Without directivity, level 1 should use D=1 for all paths."""
        from aegis.kernels.level1_aggregate import level1_aggregate

        A_ab = 0.01
        total_area = 0.5
        k_hat = np.array([[0, 0, -1.0], [1, 0, 0.0]])
        power = np.array([1.0, 2.0])
        T0 = 0.5
        n_tri = 10

        sab, p_abs = level1_aggregate(total_area, A_ab, k_hat, power, T0, n_tri)
        # With D=1 for all: p_abs = T0 * (A_ab/4) * sum(power * 1)
        expected_p_abs = T0 * (A_ab / 4) * np.sum(power)
        np.testing.assert_allclose(p_abs, expected_p_abs, rtol=1e-10)

    def test_uniform_sab(self):
        """Level 1 produces uniform S_ab across all triangles."""
        from aegis.kernels.level1_aggregate import level1_aggregate

        n_tri = 20
        sab, _ = level1_aggregate(
            total_area=0.5,
            A_ab=0.01,
            k_hat=np.array([[0, 0, -1.0]]),
            power=np.array([1.0]),
            T0=0.5,
            n_triangles=n_tri,
        )
        assert sab.shape == (n_tri,)
        # All values should be identical
        np.testing.assert_allclose(sab, sab[0])

    def test_scales_with_power(self):
        """Doubling power should double S_ab."""
        from aegis.kernels.level1_aggregate import level1_aggregate

        args = dict(
            total_area=0.5,
            A_ab=0.01,
            k_hat=np.array([[0, 0, -1.0]]),
            T0=0.5,
            n_triangles=10,
        )
        sab1, _ = level1_aggregate(power=np.array([1.0]), **args)
        sab2, _ = level1_aggregate(power=np.array([2.0]), **args)
        np.testing.assert_allclose(sab2, 2 * sab1, rtol=1e-10)

    def test_zero_power_gives_zero(self):
        from aegis.kernels.level1_aggregate import level1_aggregate

        sab, p_abs = level1_aggregate(
            total_area=0.5,
            A_ab=0.01,
            k_hat=np.array([[0, 0, -1.0]]),
            power=np.array([0.0]),
            T0=0.5,
            n_triangles=5,
        )
        np.testing.assert_allclose(sab, 0.0)
        assert p_abs == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Spatial kernel validation
# ---------------------------------------------------------------------------


class TestSpatialKernelValidation:
    def test_polarisation_requires_fresnel(self):
        """polarisation=True with fresnel=False should raise ValueError."""
        from aegis.kernels.spatial import spatial_kernel

        normals = np.array([[0, 0, 1.0]])
        k_hat = np.array([[0, 0, -1.0]])
        power = np.array([1.0])

        with pytest.raises(ValueError, match="polarisation.*requires.*fresnel"):
            spatial_kernel(
                normals,
                k_hat,
                power,
                n_tilde=4 + 3j,
                T0=0.5,
                freq_hz=28e9,
                fresnel=False,
                polarisation=True,
            )

    def test_polarisation_with_fresnel_works(self):
        """polarisation=True with fresnel=True should succeed."""
        from aegis.kernels.spatial import spatial_kernel

        normals = np.array([[0, 0, 1.0]])
        k_hat = np.array([[0, 0, -1.0]])
        power = np.array([1.0])

        sab = spatial_kernel(
            normals,
            k_hat,
            power,
            n_tilde=4 + 3j,
            T0=0.5,
            freq_hz=28e9,
            fresnel=True,
            polarisation=True,
            q=0.5,
        )
        assert sab.shape == (1,)
        assert float(sab[0]) >= 0
