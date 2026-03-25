"""Tests for multi-user MIMO precoders."""

from __future__ import annotations

import numpy as np
from numpy.testing import assert_allclose

from aegis.precoder import Precoder


class TestMRT:
    """Tests for MRT (maximum ratio transmission) precoder."""

    def test_single_user_matches_existing(self):
        """K=1 MRT matches Precoder.mrt from aegis.precoder."""
        rng = np.random.default_rng(42)
        h = rng.standard_normal(8) + 1j * rng.standard_normal(8)
        P = 2.0

        from aegis.mimo.precoders import mrt

        W = mrt(h.reshape(1, -1), P=P)
        x_old = Precoder.mrt(h, P=P).x

        # Directions should match (up to global phase)
        ratio = W[:, 0] / x_old
        assert_allclose(np.abs(ratio), np.abs(ratio[0]) * np.ones(8), atol=1e-12)

    def test_per_column_power(self):
        """Each column power = P/K."""
        rng = np.random.default_rng(43)
        K, M = 3, 8
        H = rng.standard_normal((K, M)) + 1j * rng.standard_normal((K, M))
        P = 5.0

        from aegis.mimo.precoders import mrt

        W = mrt(H, P=P)
        for k in range(K):
            col_power = float(np.real(np.vdot(W[:, k], W[:, k])))
            assert_allclose(col_power, P / K, atol=1e-12)

    def test_total_power(self):
        """||W||_F^2 = P."""
        rng = np.random.default_rng(44)
        K, M = 4, 16
        H = rng.standard_normal((K, M)) + 1j * rng.standard_normal((K, M))
        P = 3.0

        from aegis.mimo.precoders import mrt

        W = mrt(H, P=P)
        frob_sq = float(np.real(np.trace(W.conj().T @ W)))
        assert_allclose(frob_sq, P, atol=1e-12)

    def test_conjugate_direction(self):
        """Each column proportional to conj(h_k)."""
        rng = np.random.default_rng(45)
        K, M = 2, 8
        H = rng.standard_normal((K, M)) + 1j * rng.standard_normal((K, M))

        from aegis.mimo.precoders import mrt

        W = mrt(H, P=1.0)
        for k in range(K):
            h_conj = H[k].conj()
            # W[:, k] should be proportional to h_conj
            ratio = W[:, k] / h_conj
            assert_allclose(
                ratio,
                ratio[0] * np.ones(M),
                atol=1e-12,
            )

    def test_output_shape(self):
        """Output shape is (M, K) complex."""
        rng = np.random.default_rng(46)
        K, M = 3, 12
        H = rng.standard_normal((K, M)) + 1j * rng.standard_normal((K, M))

        from aegis.mimo.precoders import mrt

        W = mrt(H)
        assert W.shape == (M, K)
        assert np.iscomplexobj(W)
