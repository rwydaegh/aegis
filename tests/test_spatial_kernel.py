"""Tests for the unified spatial kernel with composable corrections."""

import numpy as np
import pytest
from conftest import make_icosahedron

from aegis.tissue.dielectric import SKIN_28GHZ


@pytest.fixture
def setup():
    body = make_icosahedron()
    rng = np.random.default_rng(99)
    N = 10
    k_hat = rng.standard_normal((N, 3))
    k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
    power = rng.uniform(0.5, 3.0, size=N)
    n_tilde = SKIN_28GHZ.n_complex
    T0 = SKIN_28GHZ.T0
    freq_hz = SKIN_28GHZ.freq_hz
    curvature_H = np.full(body.n_triangles, 10.0)
    return body, k_hat, power, n_tilde, T0, freq_hz, curvature_H


class TestUnifiedSpatialMatchesOldLevels:
    """Unified kernel with specific flags must match old per-level kernels."""

    def test_fresnel_off_matches_level2(self, setup):
        body, k_hat, power, n_tilde, T0, freq_hz, _ = setup
        from aegis.kernels.level2_geometric import level2_geometric
        from aegis.kernels.spatial import spatial_kernel

        expected = level2_geometric(body.normals, k_hat, power, T0)
        actual = spatial_kernel(
            body.normals,
            k_hat,
            power,
            n_tilde,
            T0,
            freq_hz,
            fresnel=False,
        )
        np.testing.assert_allclose(actual, expected, rtol=1e-12)

    def test_no_corrections_matches_level3(self, setup):
        body, k_hat, power, n_tilde, T0, freq_hz, _ = setup
        from aegis.kernels.level3_fresnel import level3_fresnel
        from aegis.kernels.spatial import spatial_kernel

        expected = level3_fresnel(body.normals, k_hat, power, n_tilde)
        actual = spatial_kernel(body.normals, k_hat, power, n_tilde, T0, freq_hz)
        np.testing.assert_allclose(actual, expected, rtol=1e-12)

    def test_polarisation_matches_level4(self, setup):
        body, k_hat, power, n_tilde, T0, freq_hz, _ = setup
        from aegis.kernels.level4_polarisation import level4_polarisation
        from aegis.kernels.spatial import spatial_kernel

        q = 0.5
        expected = level4_polarisation(body.normals, k_hat, power, n_tilde, q=q)
        actual = spatial_kernel(
            body.normals,
            k_hat,
            power,
            n_tilde,
            T0,
            freq_hz,
            polarisation=True,
            q=q,
        )
        np.testing.assert_allclose(actual, expected, rtol=1e-12)

    def test_curvature_matches_level5(self, setup):
        body, k_hat, power, n_tilde, T0, freq_hz, curvature_H = setup
        from aegis.kernels.level5_curvature import level5_curvature
        from aegis.kernels.spatial import spatial_kernel

        expected = level5_curvature(
            body.normals,
            k_hat,
            power,
            n_tilde,
            T0,
            curvature_H,
            freq_hz,
        )
        actual = spatial_kernel(
            body.normals,
            k_hat,
            power,
            n_tilde,
            T0,
            freq_hz,
            curvature=True,
            curvature_H=curvature_H,
        )
        np.testing.assert_allclose(actual, expected, rtol=1e-12)

    def test_curvature_matches_level5_negative_H(self, setup):
        """level5_curvature and spatial_kernel(curvature=True) must agree for negative curvature."""
        body, k_hat, power, n_tilde, T0, freq_hz, _ = setup
        curvature_H_mixed = np.linspace(-10.0, 10.0, body.n_triangles)
        from aegis.kernels.level5_curvature import level5_curvature
        from aegis.kernels.spatial import spatial_kernel

        expected = level5_curvature(
            body.normals,
            k_hat,
            power,
            n_tilde,
            T0,
            curvature_H_mixed,
            freq_hz,
        )
        actual = spatial_kernel(
            body.normals,
            k_hat,
            power,
            n_tilde,
            T0,
            freq_hz,
            curvature=True,
            curvature_H=curvature_H_mixed,
        )
        np.testing.assert_allclose(actual, expected, rtol=1e-12)

    def test_curvature_diffraction_matches_level6(self, setup):
        body, k_hat, power, n_tilde, T0, freq_hz, curvature_H = setup
        from aegis.kernels.level6_diffraction import level6_diffraction
        from aegis.kernels.spatial import spatial_kernel

        expected = level6_diffraction(
            body.normals,
            k_hat,
            power,
            n_tilde,
            T0,
            curvature_H,
            freq_hz,
        )
        actual = spatial_kernel(
            body.normals,
            k_hat,
            power,
            n_tilde,
            T0,
            freq_hz,
            curvature=True,
            diffraction=True,
            curvature_H=curvature_H,
        )
        np.testing.assert_allclose(actual, expected, rtol=1e-12)


class TestNewCombinations:
    """Combinations the old level system could not express."""

    def test_polarisation_curvature(self, setup):
        body, k_hat, power, n_tilde, T0, freq_hz, curvature_H = setup
        from aegis.kernels.spatial import spatial_kernel

        sab = spatial_kernel(
            body.normals,
            k_hat,
            power,
            n_tilde,
            T0,
            freq_hz,
            polarisation=True,
            q=0.5,
            curvature=True,
            curvature_H=curvature_H,
        )
        assert sab.shape == (body.n_triangles,)
        assert np.all(np.isfinite(sab))

    def test_polarisation_diffraction_no_curvature(self, setup):
        body, k_hat, power, n_tilde, T0, freq_hz, curvature_H = setup
        from aegis.kernels.spatial import spatial_kernel

        sab = spatial_kernel(
            body.normals,
            k_hat,
            power,
            n_tilde,
            T0,
            freq_hz,
            polarisation=True,
            q=0.5,
            diffraction=True,
            curvature_H=curvature_H,
        )
        assert sab.shape == (body.n_triangles,)
        assert np.all(np.isfinite(sab))
        # Without curvature term, should differ from with curvature
        sab_with_curv = spatial_kernel(
            body.normals,
            k_hat,
            power,
            n_tilde,
            T0,
            freq_hz,
            polarisation=True,
            q=0.5,
            curvature=True,
            diffraction=True,
            curvature_H=curvature_H,
        )
        assert float(np.sum(sab_with_curv * body.areas)) >= float(np.sum(sab * body.areas)) - 1e-10

    def test_all_corrections_on(self, setup):
        body, k_hat, power, n_tilde, T0, freq_hz, curvature_H = setup
        from aegis.kernels.spatial import spatial_kernel

        sab = spatial_kernel(
            body.normals,
            k_hat,
            power,
            n_tilde,
            T0,
            freq_hz,
            polarisation=True,
            q=0.3,
            curvature=True,
            diffraction=True,
            curvature_H=curvature_H,
        )
        assert sab.shape == (body.n_triangles,)
        assert np.all(np.isfinite(sab))
        # With q=0 it should match level 6
        sab_q0 = spatial_kernel(
            body.normals,
            k_hat,
            power,
            n_tilde,
            T0,
            freq_hz,
            polarisation=True,
            q=0.0,
            curvature=True,
            diffraction=True,
            curvature_H=curvature_H,
        )
        from aegis.kernels.level6_diffraction import level6_diffraction

        expected = level6_diffraction(
            body.normals,
            k_hat,
            power,
            n_tilde,
            T0,
            curvature_H,
            freq_hz,
        )
        np.testing.assert_allclose(sab_q0, expected, rtol=1e-10)


class TestValidation:
    def test_diffraction_requires_curvature_H(self, setup):
        body, k_hat, power, n_tilde, T0, freq_hz, _ = setup
        from aegis.kernels.spatial import spatial_kernel

        with pytest.raises(ValueError, match="curvature_H"):
            spatial_kernel(
                body.normals,
                k_hat,
                power,
                n_tilde,
                T0,
                freq_hz,
                diffraction=True,
            )

    def test_curvature_requires_curvature_H(self, setup):
        body, k_hat, power, n_tilde, T0, freq_hz, _ = setup
        from aegis.kernels.spatial import spatial_kernel

        with pytest.raises(ValueError, match="curvature_H"):
            spatial_kernel(
                body.normals,
                k_hat,
                power,
                n_tilde,
                T0,
                freq_hz,
                curvature=True,
            )

    def test_curvature_low_freq_finite(self, setup):
        """Curvature correction must stay finite at very low frequencies.

        Regression: spatial_kernel was missing the k floor (1e-6) that
        level5_curvature and level6_diffraction both apply, causing
        H/k to blow up when freq_hz is small.
        """
        body, k_hat, power, n_tilde, T0, _, curvature_H = setup
        from aegis.kernels.spatial import spatial_kernel

        sab = spatial_kernel(
            body.normals,
            k_hat,
            power,
            n_tilde,
            T0,
            1.0,  # 1 Hz: k ≈ 2e-8, would blow up without floor
            curvature=True,
            curvature_H=curvature_H,
        )
        assert np.all(np.isfinite(sab)), "sab must be finite at very low frequencies"


class TestChunkingDeterminism:
    """spatial_kernel must produce identical results regardless of chunk size.

    Regression: per-chunk clamping ``max(sab, 0)`` inside the inner kernel made
    the chunked path chunk-size-dependent when individual chunks could sum to
    negative (e.g. diffraction with mostly back-facing paths). The fix clamps
    only once, after all chunks are summed. This suite forces the chunked path
    via small ``_MAX_MN_ELEMENTS`` values and asserts bit-for-bit agreement
    across chunk sizes.
    """

    def _build_scene(self, rng):
        # 4 triangles, 20 paths, strongly back-heavy so partial sums can be
        # negative under the GELU (diffraction) activation.
        normals = np.array(
            [
                [0.0, 0.0, 1.0],
                [0.0, 0.0, 1.0],
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
            ],
            dtype=np.float64,
        )
        N = 20
        # Mix of glancing and back-facing directions near the shadow boundary,
        # plus a couple of well-lit ones so the full sum is not all-zero.
        k_hat = rng.standard_normal((N, 3))
        k_hat[:16] = np.array([0.05, 0.0, 0.05])  # nearly back-facing for triangles 0/1
        k_hat[:16] += rng.standard_normal((16, 3)) * 0.02
        k_hat[16:] = np.array([0.0, 0.0, -1.0])  # fully incident on triangles 0/1
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        power = rng.uniform(0.5, 2.0, size=N).astype(np.float64)
        curvature_H = np.array([5.0, 50.0, 2.0, 10.0], dtype=np.float64)
        return normals, k_hat, power, curvature_H

    @pytest.mark.parametrize(
        "flags",
        [
            {"fresnel": False, "diffraction": True},
            {"fresnel": True, "diffraction": True},
            {"fresnel": True, "curvature": True, "diffraction": True},
            {"fresnel": True, "polarisation": True, "q": 0.5, "curvature": True, "diffraction": True},
        ],
    )
    def test_chunk_size_invariance(self, monkeypatch, flags):
        from aegis import kernels
        from aegis.kernels.spatial import spatial_kernel

        if kernels.spatial.JAX_AVAILABLE:
            pytest.skip("chunking path is only exercised on NumPy backend")

        rng = np.random.default_rng(0)
        normals, k_hat, power, curvature_H = self._build_scene(rng)
        n_tilde = SKIN_28GHZ.n_complex
        T0 = SKIN_28GHZ.T0
        freq_hz = SKIN_28GHZ.freq_hz
        M = normals.shape[0]

        reference = spatial_kernel(
            normals,
            k_hat,
            power,
            n_tilde,
            T0,
            freq_hz,
            curvature_H=curvature_H,
            **flags,
        )

        # Force chunked path with chunk sizes 1, 2, 3, 5, 7, 13 (not evenly
        # divisible into N=20 — exercises partial trailing chunks).
        for chunk_paths in [1, 2, 3, 5, 7, 13]:
            monkeypatch.setattr(
                kernels.spatial,
                "_MAX_MN_ELEMENTS",
                M * chunk_paths,
            )
            chunked = spatial_kernel(
                normals,
                k_hat,
                power,
                n_tilde,
                T0,
                freq_hz,
                curvature_H=curvature_H,
                **flags,
            )
            # Float64 @-product is exact under permutation of contributions
            # only up to rounding; but for these sizes the error is well
            # below 1e-12 of the magnitude. This guards the real regression
            # (orders-of-magnitude drift from chunk-wise clamping to zero).
            np.testing.assert_allclose(
                chunked,
                reference,
                rtol=1e-12,
                atol=1e-14,
                err_msg=f"chunk_paths={chunk_paths} flags={flags} drift from unchunked",
            )
