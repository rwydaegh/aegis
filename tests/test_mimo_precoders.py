"""Tests for multi-user MIMO precoders."""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st
from numpy.testing import assert_allclose

from aegis.mimo.precoders import compute_precoder, mmse, mrt, zf, zf_exposure
from aegis.precoder import Precoder


class TestMRT:
    """Tests for MRT (maximum ratio transmission) precoder."""

    def test_single_user_matches_existing(self):
        """K=1 MRT matches Precoder.mrt from aegis.precoder."""
        rng = np.random.default_rng(42)
        h = rng.standard_normal(8) + 1j * rng.standard_normal(8)
        P = 2.0

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

        W = mrt(H, P=P)
        frob_sq = float(np.real(np.trace(W.conj().T @ W)))
        assert_allclose(frob_sq, P, atol=1e-12)

    def test_conjugate_direction(self):
        """Each column proportional to conj(h_k)."""
        rng = np.random.default_rng(45)
        K, M = 2, 8
        H = rng.standard_normal((K, M)) + 1j * rng.standard_normal((K, M))

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

        W = zf(H, P=P)
        frob_sq = float(np.real(np.trace(W.conj().T @ W)))
        assert_allclose(frob_sq, P, atol=1e-10)

    def test_single_user_direction_matches_mrt(self):
        """K=1 direction matches MRT."""
        rng = np.random.default_rng(52)
        M = 8
        h = rng.standard_normal(M) + 1j * rng.standard_normal(M)
        H = h.reshape(1, -1)

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

        W = zf(H)
        assert W.shape == (M, K)
        assert np.iscomplexobj(W)

    def test_requires_M_ge_K(self):
        """Raises ValueError when M < K."""
        rng = np.random.default_rng(54)
        K, M = 8, 4  # M < K
        H = rng.standard_normal((K, M)) + 1j * rng.standard_normal((K, M))

        with pytest.raises(ValueError, match="M_ant.*must be >= K"):
            zf(H)


class TestMMSE:
    """Tests for MMSE (regularized zero-forcing) precoder."""

    def test_approaches_zf_at_low_noise(self):
        """alpha -> 0 recovers ZF (atol 1e-6)."""
        rng = np.random.default_rng(60)
        K, M = 3, 8
        H = rng.standard_normal((K, M)) + 1j * rng.standard_normal((K, M))
        P = 2.0

        W_zf = zf(H, P=P)
        W_mmse = mmse(H, P=P, noise_power=1e-12)
        assert_allclose(W_mmse, W_zf, atol=1e-6)

    def test_total_power(self):
        """||W||_F^2 = P."""
        rng = np.random.default_rng(61)
        K, M = 4, 16
        H = rng.standard_normal((K, M)) + 1j * rng.standard_normal((K, M))
        P = 3.0

        W = mmse(H, P=P, noise_power=0.1)
        frob_sq = float(np.real(np.trace(W.conj().T @ W)))
        assert_allclose(frob_sq, P, atol=1e-10)

    def test_better_conditioned_than_zf(self):
        """Near-singular H: MMSE column norms more balanced than ZF."""
        rng = np.random.default_rng(62)
        M = 8
        # Create near-singular H by making rows nearly dependent
        h0 = rng.standard_normal(M) + 1j * rng.standard_normal(M)
        H = np.stack(
            [
                h0,
                h0 + 1e-4 * (rng.standard_normal(M) + 1j * rng.standard_normal(M)),
                rng.standard_normal(M) + 1j * rng.standard_normal(M),
            ]
        )

        W_zf = zf(H, P=1.0)
        W_mmse = mmse(H, P=1.0, noise_power=0.1)

        norms_zf = np.linalg.norm(W_zf, axis=0)
        norms_mmse = np.linalg.norm(W_mmse, axis=0)

        # MMSE should have more balanced column norms (lower ratio max/min)
        ratio_zf = norms_zf.max() / max(norms_zf.min(), 1e-30)
        ratio_mmse = norms_mmse.max() / max(norms_mmse.min(), 1e-30)
        assert ratio_mmse < ratio_zf

    def test_output_shape(self):
        """Output shape is (M, K) complex."""
        rng = np.random.default_rng(63)
        K, M = 3, 12
        H = rng.standard_normal((K, M)) + 1j * rng.standard_normal((K, M))

        W = mmse(H)
        assert W.shape == (M, K)
        assert np.iscomplexobj(W)

    def test_works_with_M_equal_K(self):
        """M=K works with regularization."""
        rng = np.random.default_rng(64)
        K = M = 4
        H = rng.standard_normal((K, M)) + 1j * rng.standard_normal((K, M))

        W = mmse(H, P=1.0, noise_power=0.01)
        assert W.shape == (M, K)
        frob_sq = float(np.real(np.trace(W.conj().T @ W)))
        assert_allclose(frob_sq, 1.0, atol=1e-10)


class TestZFExposure:
    """Tests for ZF+exposure-scaling precoder."""

    def _make_scenario(self, rng, K=2, M=8):
        """Build H, Q_list, and return them."""
        H = rng.standard_normal((K, M)) + 1j * rng.standard_normal((K, M))
        # Build positive semidefinite Q matrices (one per user)
        Q_list = []
        for _ in range(K):
            A = rng.standard_normal((M, M)) + 1j * rng.standard_normal((M, M))
            Q_list.append(A.conj().T @ A / M)
        return H, Q_list

    def test_exposure_constraints_satisfied(self):
        """trace(W^H Q_u W) <= P_abs_max for all u."""
        rng = np.random.default_rng(70)
        H, Q_list = self._make_scenario(rng, K=3, M=8)
        P_abs_max = 0.05

        W = zf_exposure(H, Q_list, P_abs_max=P_abs_max, P=1.0)
        for Q_u in Q_list:
            absorbed = float(np.real(np.trace(W.conj().T @ Q_u @ W)))
            assert absorbed <= P_abs_max + 1e-10

    def test_directions_match_zf(self):
        """Column directions match ZF."""
        rng = np.random.default_rng(71)
        H, Q_list = self._make_scenario(rng, K=2, M=8)
        P_abs_max = 100.0  # loose constraint

        W_zfe = zf_exposure(H, Q_list, P_abs_max=P_abs_max, P=1.0)
        W_zf = zf(H, P=1.0)

        for k in range(H.shape[0]):
            d_zfe = W_zfe[:, k] / np.linalg.norm(W_zfe[:, k])
            d_zf = W_zf[:, k] / np.linalg.norm(W_zf[:, k])
            # Inner product magnitude should be ~1
            assert_allclose(np.abs(np.vdot(d_zfe, d_zf)), 1.0, atol=1e-10)

    def test_total_power_does_not_exceed_budget(self):
        """||W||_F^2 <= P."""
        rng = np.random.default_rng(72)
        H, Q_list = self._make_scenario(rng, K=3, M=8)
        P = 2.0
        P_abs_max = 0.01

        W = zf_exposure(H, Q_list, P_abs_max=P_abs_max, P=P)
        frob_sq = float(np.real(np.trace(W.conj().T @ W)))
        assert frob_sq <= P + 1e-10

    def test_loose_constraint_recovers_zf(self):
        """P_abs_max=1e6 recovers ZF exactly."""
        rng = np.random.default_rng(73)
        H, Q_list = self._make_scenario(rng, K=2, M=8)
        P = 1.0

        W_zfe = zf_exposure(H, Q_list, P_abs_max=1e6, P=P)
        W_zf = zf(H, P=P)
        assert_allclose(W_zfe, W_zf, atol=1e-10)

    def test_output_shape(self):
        """Output shape is (M, K) complex."""
        rng = np.random.default_rng(74)
        H, Q_list = self._make_scenario(rng, K=4, M=16)

        W = zf_exposure(H, Q_list, P_abs_max=1.0, P=1.0)
        assert W.shape == (16, 4)
        assert np.iscomplexobj(W)


class TestComputePrecoder:
    """Tests for the compute_precoder dispatcher."""

    def test_dispatch_mrt(self):
        rng = np.random.default_rng(80)
        K, M = 2, 8
        H = rng.standard_normal((K, M)) + 1j * rng.standard_normal((K, M))

        W = compute_precoder(H, precoder_type="mrt", P=1.0)
        W_ref = mrt(H, P=1.0)
        assert_allclose(W, W_ref)

    def test_dispatch_zf(self):
        rng = np.random.default_rng(81)
        K, M = 2, 8
        H = rng.standard_normal((K, M)) + 1j * rng.standard_normal((K, M))

        W = compute_precoder(H, precoder_type="zf", P=2.0)
        W_ref = zf(H, P=2.0)
        assert_allclose(W, W_ref)

    def test_dispatch_mmse(self):
        rng = np.random.default_rng(82)
        K, M = 3, 8
        H = rng.standard_normal((K, M)) + 1j * rng.standard_normal((K, M))

        W = compute_precoder(H, precoder_type="mmse", P=1.0, noise_power=0.05)
        W_ref = mmse(H, P=1.0, noise_power=0.05)
        assert_allclose(W, W_ref)

    def test_dispatch_zf_exposure(self):
        rng = np.random.default_rng(83)
        K, M = 2, 8
        H = rng.standard_normal((K, M)) + 1j * rng.standard_normal((K, M))
        Q_list = []
        for _ in range(K):
            A = rng.standard_normal((M, M)) + 1j * rng.standard_normal((M, M))
            Q_list.append(A.conj().T @ A / M)

        W = compute_precoder(
            H,
            precoder_type="zf_exposure",
            P=1.0,
            Q_list=Q_list,
            P_abs_max=0.1,
        )
        W_ref = zf_exposure(H, Q_list, P_abs_max=0.1, P=1.0)
        assert_allclose(W, W_ref)

    def test_unknown_type_raises(self):
        rng = np.random.default_rng(84)
        H = rng.standard_normal((2, 8)) + 1j * rng.standard_normal((2, 8))

        with pytest.raises(ValueError, match="Unknown precoder type"):
            compute_precoder(H, precoder_type="banana")

    def test_zf_exposure_missing_args(self):
        H = np.eye(2, dtype=complex)
        with pytest.raises(ValueError, match="zf_exposure requires"):
            compute_precoder(H, precoder_type="zf_exposure")


def _random_H(K, M, seed):
    rng = np.random.default_rng(seed)
    return rng.standard_normal((K, M)) + 1j * rng.standard_normal((K, M))


def _random_Q(M, seed):
    rng = np.random.default_rng(seed)
    A = rng.standard_normal((M, M)) + 1j * rng.standard_normal((M, M))
    Q = A.conj().T @ A
    return Q / max(np.linalg.norm(Q), 1e-10)


class TestPrecoderInvariants:
    """Property tests for precoder invariants (Hypothesis)."""

    @given(
        K=st.integers(min_value=1, max_value=4),
        M=st.integers(min_value=4, max_value=16),
        P=st.floats(min_value=0.1, max_value=10.0),
        seed=st.integers(min_value=0, max_value=2**31),
    )
    @settings(max_examples=50, deadline=5000)
    def test_mrt_total_power(self, K, M, P, seed):
        assume(M >= K)
        H = _random_H(K, M, seed)
        W = mrt(H, P=P)
        total = float(np.real(np.trace(W.conj().T @ W)))
        np.testing.assert_allclose(total, P, rtol=1e-10)

    @given(
        K=st.integers(min_value=1, max_value=4),
        M=st.integers(min_value=4, max_value=16),
        P=st.floats(min_value=0.1, max_value=10.0),
        seed=st.integers(min_value=0, max_value=2**31),
    )
    @settings(max_examples=50, deadline=5000)
    def test_zf_zero_interference(self, K, M, P, seed):
        assume(M >= K)
        H = _random_H(K, M, seed)
        W = zf(H, P=P)
        HW = H @ W
        off_diag = HW - np.diag(np.diag(HW))
        np.testing.assert_allclose(np.abs(off_diag), 0, atol=1e-8)

    @given(
        K=st.integers(min_value=1, max_value=4),
        M=st.integers(min_value=4, max_value=16),
        P=st.floats(min_value=0.1, max_value=10.0),
        seed=st.integers(min_value=0, max_value=2**31),
    )
    @settings(max_examples=50, deadline=5000)
    def test_zf_total_power(self, K, M, P, seed):
        assume(M >= K)
        H = _random_H(K, M, seed)
        W = zf(H, P=P)
        total = float(np.real(np.trace(W.conj().T @ W)))
        np.testing.assert_allclose(total, P, rtol=1e-10)

    @given(
        K=st.integers(min_value=1, max_value=4),
        M=st.integers(min_value=4, max_value=16),
        seed=st.integers(min_value=0, max_value=2**31),
    )
    @settings(max_examples=50, deadline=5000)
    def test_exposure_constraint_satisfaction(self, K, M, seed):
        assume(M >= K)
        H = _random_H(K, M, seed)
        Q_list = [_random_Q(M, seed + i) for i in range(K)]
        P_abs_max = 0.05
        W = zf_exposure(H, Q_list, P_abs_max=P_abs_max, P=1.0)
        for Q_u in Q_list:
            p_abs = float(np.real(np.trace(W.conj().T @ Q_u @ W)))
            assert p_abs <= P_abs_max + 1e-8, f"P_abs={p_abs} > P_abs_max={P_abs_max}"

    @given(
        K=st.integers(min_value=1, max_value=4),
        M=st.integers(min_value=4, max_value=16),
        seed=st.integers(min_value=0, max_value=2**31),
    )
    @settings(max_examples=50, deadline=5000)
    def test_sab_nonnegative(self, K, M, seed):
        assume(M >= K)
        rng = np.random.default_rng(seed)
        H = _random_H(K, M, seed)
        W = zf(H, P=1.0)
        n_tri = 20
        G_tilde = rng.standard_normal((n_tri, 3, M)) + 1j * rng.standard_normal((n_tri, 3, M))
        G_tilde *= 0.01
        from aegis.mimo.compute import compute_multistream_sab

        sab = compute_multistream_sab(G_tilde, W)
        assert np.all(sab >= -1e-15)
