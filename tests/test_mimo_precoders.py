"""Tests for multi-user MIMO precoders."""

from __future__ import annotations

import numpy as np
import pytest
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


class TestZF:
    """Tests for ZF (zero-forcing) precoder."""

    def test_zero_interference(self):
        """H @ W is diagonal (off-diag < 1e-10)."""
        rng = np.random.default_rng(50)
        K, M = 3, 8
        H = rng.standard_normal((K, M)) + 1j * rng.standard_normal((K, M))

        from aegis.mimo.precoders import zf

        W = zf(H, P=1.0)
        HW = H @ W
        # Off-diagonal elements should be near zero
        off_diag = HW - np.diag(np.diag(HW))
        assert np.all(np.abs(off_diag) < 1e-10)

    def test_total_power(self):
        """||W||_F^2 = P."""
        rng = np.random.default_rng(51)
        K, M = 2, 8
        H = rng.standard_normal((K, M)) + 1j * rng.standard_normal((K, M))
        P = 4.0

        from aegis.mimo.precoders import zf

        W = zf(H, P=P)
        frob_sq = float(np.real(np.trace(W.conj().T @ W)))
        assert_allclose(frob_sq, P, atol=1e-10)

    def test_single_user_direction_matches_mrt(self):
        """K=1 direction matches MRT."""
        rng = np.random.default_rng(52)
        M = 8
        h = rng.standard_normal(M) + 1j * rng.standard_normal(M)
        H = h.reshape(1, -1)

        from aegis.mimo.precoders import mrt, zf

        W_zf = zf(H, P=1.0)
        W_mrt = mrt(H, P=1.0)
        # Directions should match
        d_zf = W_zf[:, 0] / np.linalg.norm(W_zf[:, 0])
        d_mrt = W_mrt[:, 0] / np.linalg.norm(W_mrt[:, 0])
        # Up to global phase
        assert_allclose(np.abs(np.vdot(d_zf, d_mrt)), 1.0, atol=1e-10)

    def test_output_shape(self):
        """Output shape is (M, K) complex."""
        rng = np.random.default_rng(53)
        K, M = 4, 16
        H = rng.standard_normal((K, M)) + 1j * rng.standard_normal((K, M))

        from aegis.mimo.precoders import zf

        W = zf(H)
        assert W.shape == (M, K)
        assert np.iscomplexobj(W)

    def test_requires_M_ge_K(self):
        """Raises ValueError when M < K."""
        rng = np.random.default_rng(54)
        K, M = 8, 4  # M < K
        H = rng.standard_normal((K, M)) + 1j * rng.standard_normal((K, M))

        from aegis.mimo.precoders import zf

        with pytest.raises(ValueError, match="M_ant.*must be >= K"):
            zf(H)
