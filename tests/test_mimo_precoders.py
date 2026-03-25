"""Tests for multi-user MIMO precoders.

Covers: MRT, ZF, MMSE, ZF+exposure-scaling, PrecoderMatrix,
and property-based invariants from design doc section H2.
"""

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.extra.numpy import arrays

from aegis.mimo.precoders import PrecoderMatrix, mmse, mrt, zf, zf_exposure_scaled

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def random_channel_matrix(K, M, rng=None):
    """Create a random (K, M) complex channel matrix."""
    if rng is None:
        rng = np.random.default_rng(42)
    return (rng.standard_normal((K, M)) + 1j * rng.standard_normal((K, M))) / np.sqrt(2)


def random_psd_matrix(M, rng=None):
    """Create a random (M, M) Hermitian PSD matrix."""
    if rng is None:
        rng = np.random.default_rng(42)
    A = (rng.standard_normal((M, M)) + 1j * rng.standard_normal((M, M))) / np.sqrt(2)
    return A.conj().T @ A


# ---------------------------------------------------------------------------
# PrecoderMatrix dataclass
# ---------------------------------------------------------------------------


class TestPrecoderMatrix:
    def test_basic_construction(self):
        W = np.eye(4, 2, dtype=complex)
        pm = PrecoderMatrix(W=W, method="test")
        assert pm.n_elements == 4
        assert pm.n_users == 2
        assert pm.method == "test"

    def test_rejects_1d(self):
        with pytest.raises(ValueError, match="2D"):
            PrecoderMatrix(W=np.ones(4, dtype=complex))

    def test_total_power(self):
        W = np.eye(4, 2, dtype=complex) * np.sqrt(0.5)
        pm = PrecoderMatrix(W=W, method="test")
        assert pm.total_power == pytest.approx(1.0)

    def test_per_user_power(self):
        W = np.zeros((4, 2), dtype=complex)
        W[0, 0] = 2.0
        W[1, 1] = 3.0
        pm = PrecoderMatrix(W=W)
        pup = pm.per_user_power()
        assert pup[0] == pytest.approx(4.0)
        assert pup[1] == pytest.approx(9.0)

    def test_column(self):
        W = np.eye(4, 2, dtype=complex)
        pm = PrecoderMatrix(W=W)
        np.testing.assert_array_equal(pm.column(0), W[:, 0])

    def test_repr(self):
        W = np.eye(4, 2, dtype=complex)
        pm = PrecoderMatrix(W=W, method="test")
        r = repr(pm)
        assert "test" in r
        assert "M=4" in r
        assert "K=2" in r


# ---------------------------------------------------------------------------
# MRT precoder
# ---------------------------------------------------------------------------


class TestMRT:
    def test_power_normalization(self):
        H = random_channel_matrix(3, 8)
        P = 2.5
        pm = mrt(H, P)
        assert pm.total_power == pytest.approx(P, rel=1e-10)

    def test_equal_per_user_power(self):
        H = random_channel_matrix(4, 16)
        P = 4.0
        pm = mrt(H, P)
        pup = pm.per_user_power()
        np.testing.assert_allclose(pup, P / 4, rtol=1e-10)

    def test_single_user_matches_existing_precoder(self):
        """K=1 MRT should match the existing Precoder.mrt."""
        from aegis.precoder import Precoder

        h = np.array([1 + 2j, 3 - 1j, 0.5j, 2.0], dtype=complex)
        P = 1.0

        old = Precoder.mrt(h, P)
        new = mrt(h[np.newaxis, :], P)

        np.testing.assert_allclose(np.abs(new.column(0)), np.abs(old.x), rtol=1e-10)
        assert new.total_power == pytest.approx(P, rel=1e-10)

    def test_method_name(self):
        H = random_channel_matrix(2, 4)
        pm = mrt(H)
        assert pm.method == "mrt"

    def test_zero_channel(self):
        """Zero channel should not crash."""
        H = np.zeros((2, 4), dtype=complex)
        pm = mrt(H, 1.0)
        assert pm.total_power == pytest.approx(1.0, rel=1e-10)

    def test_1d_input(self):
        """Single user passed as 1D vector."""
        h = np.array([1 + 0j, 0, 0, 0])
        pm = mrt(h, 1.0)
        assert pm.n_users == 1
        assert pm.total_power == pytest.approx(1.0)

    def test_conjugate_direction(self):
        """MRT column should be proportional to h_k^*."""
        h = np.array([1 + 2j, 3 - 1j], dtype=complex)
        pm = mrt(h[np.newaxis, :], 1.0)
        w = pm.column(0)
        # w should be proportional to h.conj()
        ratio = w / h.conj()
        np.testing.assert_allclose(ratio[0], ratio[1], rtol=1e-10)


# ---------------------------------------------------------------------------
# ZF precoder
# ---------------------------------------------------------------------------


class TestZF:
    def test_zero_interference(self):
        """H @ W should be (scaled) identity."""
        H = random_channel_matrix(3, 8)
        P = 1.0
        pm = zf(H, P)

        HW = H @ pm.W  # (K, K)
        # Should be proportional to I
        diag = np.diag(HW)
        off_diag = HW - np.diag(diag)
        np.testing.assert_allclose(np.abs(off_diag), 0, atol=1e-10)

    def test_power_normalization(self):
        H = random_channel_matrix(2, 8)
        P = 3.0
        pm = zf(H, P)
        assert pm.total_power == pytest.approx(P, rel=1e-10)

    def test_fallback_underdetermined(self):
        """M < K should fall back to MRT with warning."""
        H = random_channel_matrix(8, 4)
        with pytest.warns(match="falling back to MRT"):
            pm = zf(H, 1.0)
        assert "fallback" in pm.method

    def test_single_user_equals_mrt(self):
        """K=1 ZF reduces to MRT (pseudoinverse of 1xM row = normalized conjugate)."""
        h = np.array([1 + 2j, 3 - 1j, 0.5j, 2.0], dtype=complex)
        P = 1.0

        pm_zf = zf(h[np.newaxis, :], P)
        pm_mrt = mrt(h[np.newaxis, :], P)

        # Should be numerically equivalent (up to global phase)
        np.testing.assert_allclose(
            np.abs(pm_zf.column(0)),
            np.abs(pm_mrt.column(0)),
            rtol=1e-10,
        )

    def test_method_name(self):
        H = random_channel_matrix(2, 4)
        pm = zf(H)
        assert pm.method == "zf"


# ---------------------------------------------------------------------------
# MMSE precoder
# ---------------------------------------------------------------------------


class TestMMSE:
    def test_power_normalization(self):
        H = random_channel_matrix(3, 8)
        P = 2.0
        pm = mmse(H, P)
        assert pm.total_power == pytest.approx(P, rel=1e-10)

    def test_reduces_to_zf_high_snr(self):
        """At very high SNR, MMSE approaches ZF."""
        H = random_channel_matrix(2, 8, rng=np.random.default_rng(99))
        P = 1.0

        pm_mmse = mmse(H, P, snr_db=80)

        # At high SNR, MMSE interference should be very low
        HW = H @ pm_mmse.W
        off_diag = HW - np.diag(np.diag(HW))
        assert np.max(np.abs(off_diag)) < 1e-5

    def test_better_conditioned_than_zf(self):
        """MMSE should handle correlated channels better than ZF."""
        # Two users with moderately correlated channels (not singular)
        h1 = np.array([1, 0.5, 0.1, 0], dtype=complex)
        h2 = np.array([1, 0.5, 0.1, 0.001], dtype=complex)
        H = np.stack([h1, h2])

        import warnings as w

        with w.catch_warnings():
            w.simplefilter("ignore")
            pm_zf = zf(H, 1.0)
            pm_mmse = mmse(H, 1.0, snr_db=20)

        # If ZF fell back to MRT, the test premise doesn't apply
        if "fallback" in pm_zf.method:
            return

        # MMSE per-user power should be less extreme
        zf_ratio = max(pm_zf.per_user_power()) / (min(pm_zf.per_user_power()) + 1e-30)
        mmse_ratio = max(pm_mmse.per_user_power()) / (min(pm_mmse.per_user_power()) + 1e-30)
        assert mmse_ratio < zf_ratio

    def test_explicit_alpha(self):
        H = random_channel_matrix(2, 4)
        pm = mmse(H, 1.0, alpha=0.1)
        assert pm.total_power == pytest.approx(1.0, rel=1e-10)

    def test_method_name(self):
        H = random_channel_matrix(2, 4)
        pm = mmse(H)
        assert pm.method == "mmse"


# ---------------------------------------------------------------------------
# ZF + exposure scaling
# ---------------------------------------------------------------------------


class TestZFExposureScaled:
    def test_exposure_constraint_satisfied(self):
        """All per-body exposure should be <= P_abs_max."""
        rng = np.random.default_rng(42)
        K, M = 2, 8
        H = random_channel_matrix(K, M, rng)
        Qs = [random_psd_matrix(M, np.random.default_rng(i)) for i in range(K)]
        P_abs_max = 0.01

        pm = zf_exposure_scaled(H, Qs, P=1.0, P_abs_max=P_abs_max)

        for u in range(K):
            p_abs = float(np.real(np.trace(pm.W.conj().T @ Qs[u] @ pm.W)))
            assert p_abs <= P_abs_max * 1.01  # 1% tolerance for floating point

    def test_no_scaling_needed(self):
        """If exposure is already low, power should be preserved."""
        rng = np.random.default_rng(42)
        K, M = 2, 8
        H = random_channel_matrix(K, M, rng)
        # Very small Q matrices -> exposure will be tiny
        Qs = [random_psd_matrix(M, np.random.default_rng(i)) * 1e-10 for i in range(K)]

        pm = zf_exposure_scaled(H, Qs, P=1.0, P_abs_max=1.0)
        # Power should be close to ZF power (1.0)
        assert pm.total_power == pytest.approx(1.0, rel=0.01)

    def test_wrong_number_of_Qs(self):
        H = random_channel_matrix(2, 4)
        Qs = [random_psd_matrix(4)]
        with pytest.raises(ValueError, match="Need 2"):
            zf_exposure_scaled(H, Qs)

    def test_method_name(self):
        rng = np.random.default_rng(42)
        K, M = 2, 8
        H = random_channel_matrix(K, M, rng)
        Qs = [random_psd_matrix(M, np.random.default_rng(i)) for i in range(K)]
        pm = zf_exposure_scaled(H, Qs)
        assert pm.method == "zf_exposure_scaled"


# ---------------------------------------------------------------------------
# Property-based tests (Hypothesis)
# ---------------------------------------------------------------------------


@st.composite
def channel_matrix_strategy(draw, max_K=4, max_M=8):
    K = draw(st.integers(1, max_K))
    M = draw(st.integers(K, max_M))  # M >= K for ZF feasibility
    real = draw(arrays(np.float64, (K, M), elements=st.floats(-10, 10)))
    imag = draw(arrays(np.float64, (K, M), elements=st.floats(-10, 10)))
    return real + 1j * imag


class TestPrecoderProperties:
    @given(H=channel_matrix_strategy())
    @settings(max_examples=30, deadline=2000)
    def test_mrt_power_is_P(self, H):
        """MRT total power equals P for any channel matrix."""
        P = 2.0
        pm = mrt(H, P)
        assert pm.total_power == pytest.approx(P, rel=1e-8)

    @given(H=channel_matrix_strategy())
    @settings(max_examples=30, deadline=2000)
    def test_mrt_nonneg_per_user_power(self, H):
        """Per-user power is always non-negative."""
        pm = mrt(H, 1.0)
        assert np.all(pm.per_user_power() >= -1e-15)

    @given(H=channel_matrix_strategy())
    @settings(max_examples=20, deadline=5000)
    def test_zf_interference_nulling(self, H):
        """H @ W_zf should have near-zero off-diagonal entries."""
        from hypothesis import assume

        K, M = H.shape
        assume(M >= K)
        # Skip near-zero or degenerate channels
        assume(np.all(np.isfinite(H)))
        assume(np.linalg.norm(H) > 1e-10)

        import warnings as w

        with w.catch_warnings():
            w.simplefilter("ignore")
            pm = zf(H, 1.0)

        if "fallback" in pm.method:
            return

        HW = H @ pm.W
        off_diag = HW - np.diag(np.diag(HW))
        diag_scale = np.max(np.abs(np.diag(HW))) + 1e-30
        assert np.max(np.abs(off_diag)) / diag_scale < 1e-6

    @given(H=channel_matrix_strategy())
    @settings(max_examples=20, deadline=5000)
    def test_mmse_power_is_P(self, H):
        """MMSE total power equals P."""
        P = 1.5
        pm = mmse(H, P)
        assert pm.total_power == pytest.approx(P, rel=1e-8)


# ---------------------------------------------------------------------------
# Golden test: 2-user ZF with known geometry
# ---------------------------------------------------------------------------


class TestGoldenTwoUserZF:
    """Deterministic 2-user ZF test with known channels and expected outputs."""

    def setup_method(self):
        """Set up a deterministic 2-user scenario."""
        # Two orthogonal channel vectors (ideal for ZF)
        self.h1 = np.array([1, 0, 0, 0], dtype=complex)
        self.h2 = np.array([0, 1, 0, 0], dtype=complex)
        self.H = np.stack([self.h1, self.h2])
        self.P = 1.0

    def test_zf_orthogonal_channels(self):
        """With orthogonal channels, ZF = MRT (no interference to null)."""
        pm = zf(self.H, self.P)

        # H @ W should be diagonal
        HW = self.H @ pm.W
        np.testing.assert_allclose(HW[0, 1], 0, atol=1e-12)
        np.testing.assert_allclose(HW[1, 0], 0, atol=1e-12)

        # Each column should point along h_k^*
        # w_0 should be proportional to [1, 0, 0, 0]
        assert np.abs(pm.column(0)[0]) > 0.4  # most power in element 0
        assert np.abs(pm.column(0)[1]) < 1e-10
        assert np.abs(pm.column(1)[1]) > 0.4
        assert np.abs(pm.column(1)[0]) < 1e-10

    def test_zf_power(self):
        pm = zf(self.H, self.P)
        assert pm.total_power == pytest.approx(self.P, rel=1e-10)

    def test_exposure_additivity(self):
        """P_abs = trace(W^H Q W) should equal sum_k w_k^H Q w_k."""
        rng = np.random.default_rng(42)
        M = 4
        Q = random_psd_matrix(M, rng)
        pm = zf(self.H, self.P)

        # Method 1: trace
        p_abs_trace = float(np.real(np.trace(pm.W.conj().T @ Q @ pm.W)))

        # Method 2: per-column sum
        p_abs_sum = sum(float(np.real(pm.column(k).conj() @ Q @ pm.column(k))) for k in range(2))

        np.testing.assert_allclose(p_abs_trace, p_abs_sum, rtol=1e-10)

    def test_golden_values(self):
        """Verify specific numerical outputs for reproducibility."""
        pm = zf(self.H, self.P)

        # With orthogonal unit channels, ZF pseudoinverse = H^H
        # After Frobenius normalization: ||W||_F = 1
        expected_frob = np.sqrt(self.P)
        assert np.sqrt(pm.total_power) == pytest.approx(expected_frob, rel=1e-10)

        # Per-user power should be equal for symmetric channels
        pup = pm.per_user_power()
        np.testing.assert_allclose(pup[0], pup[1], rtol=1e-10)
