"""Edge case tests for the coherent MIMO dosimetry module.

Covers boundary conditions, degenerate inputs, and invariants across:
- ECBF solver (solve_ecbf)
- Exposure operator (compute_exposure_operator, eigendecompose_Q, compute_rho)
- Precoder dataclass
- Field channel (compute_field_channel)
"""

from __future__ import annotations

import numpy as np
import pytest

from aegis.coherent.ecbf import solve_ecbf
from aegis.coherent.exposure_operator import (
    compute_exposure_operator,
    compute_rho,
    eigendecompose_Q,
)
from aegis.coherent.field_channel import compute_field_channel
from aegis.precoder import Precoder
from tests.conftest import NUMERICAL_FLOOR

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _random_hermitian_psd(M_ant, rng, scale=1.0):
    """Build a random Hermitian PSD matrix of size M_ant."""
    A = rng.standard_normal((M_ant, M_ant)) + 1j * rng.standard_normal((M_ant, M_ant))
    Q = A @ A.conj().T * scale
    Q = (Q + Q.conj().T) / 2  # enforce exact symmetry
    return Q


def _random_channel(M_ant, rng):
    """Build a random normalised complex channel vector."""
    h = rng.standard_normal(M_ant) + 1j * rng.standard_normal(M_ant)
    return h


@pytest.fixture
def rng():
    return np.random.default_rng(12345)


@pytest.fixture
def simple_Q(rng):
    """4x4 Hermitian PSD exposure operator."""
    return _random_hermitian_psd(4, rng, scale=0.1)


@pytest.fixture
def simple_h(rng):
    """4-element complex channel vector."""
    return _random_channel(4, rng)


# ---------------------------------------------------------------------------
# ECBF solver edge cases
# ---------------------------------------------------------------------------


class TestEcbfEdgeCases:
    # --- Input validation ---

    def test_p_zero_raises(self, simple_h, simple_Q):
        with pytest.raises(ValueError, match="P must be positive"):
            solve_ecbf(simple_h, simple_Q, P_abs_max=0.1, P=0.0)

    def test_p_negative_raises(self, simple_h, simple_Q):
        with pytest.raises(ValueError, match="P must be positive"):
            solve_ecbf(simple_h, simple_Q, P_abs_max=0.1, P=-1.0)

    def test_p_abs_max_zero_raises(self, simple_h, simple_Q):
        with pytest.raises(ValueError, match="P_abs_max must be positive"):
            solve_ecbf(simple_h, simple_Q, P_abs_max=0.0, P=1.0)

    def test_p_abs_max_negative_raises(self, simple_h, simple_Q):
        with pytest.raises(ValueError, match="P_abs_max must be positive"):
            solve_ecbf(simple_h, simple_Q, P_abs_max=-0.5, P=1.0)

    def test_h_2d_raises(self, simple_Q):
        h_2d = np.ones((2, 4), dtype=complex)
        with pytest.raises(ValueError, match="1D"):
            solve_ecbf(h_2d, simple_Q, P_abs_max=0.1, P=1.0)

    def test_Q_non_square_raises(self, simple_h):
        Q_rect = np.eye(4, 5, dtype=complex)
        with pytest.raises(ValueError, match="square"):
            solve_ecbf(simple_h, Q_rect, P_abs_max=0.1, P=1.0)

    def test_h_Q_dimension_mismatch_raises(self, simple_Q):
        h_wrong = np.ones(6, dtype=complex)  # Q is 4x4
        with pytest.raises(ValueError, match="[Dd]imension"):
            solve_ecbf(h_wrong, simple_Q, P_abs_max=0.1, P=1.0)

    # --- Degenerate inputs ---

    def test_zero_h_returns_valid_precoder(self, simple_Q):
        """Zero channel vector should not crash; must return a unit-power vector."""
        h_zero = np.zeros(4, dtype=complex)
        x = solve_ecbf(h_zero, simple_Q, P_abs_max=1e3, P=1.0)
        power = float(np.real(np.vdot(x, x)))
        assert power == pytest.approx(1.0, rel=1e-6)
        assert x.shape == (4,)

    def test_mrt_satisfies_constraint_returns_mrt(self, rng):
        """When MRT already meets P_abs_max, ECBF returns MRT."""
        M_ant = 4
        # Q very small so MRT absorption is tiny
        Q = np.eye(M_ant, dtype=complex) * 1e-6
        h = _random_channel(M_ant, rng)
        P = 1.0
        # MRT absorption = P * h^H Q h / ||h||^2 ~ P * 1e-6
        x_mrt = np.sqrt(P) * h.conj() / np.linalg.norm(h)
        p_abs_mrt = float(np.real(x_mrt.conj() @ Q @ x_mrt))

        P_abs_max = p_abs_mrt * 10.0  # generous limit
        x_star = solve_ecbf(h, Q, P_abs_max=P_abs_max, P=P)

        # Should be parallel to MRT
        x_star_n = x_star / np.linalg.norm(x_star)
        x_mrt_n = x_mrt / np.linalg.norm(x_mrt)
        alignment = abs(np.vdot(x_star_n, x_mrt_n))
        assert alignment > 0.999

    def test_single_element_trivial(self):
        """M_ant=1: trivial problem, x = sqrt(P)."""
        h = np.array([1.0 + 0.5j])
        Q = np.array([[0.01 + 0j]])
        x = solve_ecbf(h, Q, P_abs_max=1.0, P=2.0)
        assert x.shape == (1,)
        power = float(np.real(np.vdot(x, x)))
        assert power == pytest.approx(2.0, rel=1e-6)

    def test_infeasible_constraint_warns_and_returns_vector(self, rng):
        """When P*lambda_min > P_abs_max the solver warns and returns min-absorption direction."""
        M_ant = 4
        # Build Q with well-separated eigenvalues, all large
        eigvals = np.array([10.0, 8.0, 6.0, 5.0])
        V = np.linalg.qr(rng.standard_normal((M_ant, M_ant)) + 1j * rng.standard_normal((M_ant, M_ant)))[0]
        Q = (V * eigvals[None, :]) @ V.conj().T
        Q = (Q + Q.conj().T) / 2

        h = _random_channel(M_ant, rng)
        P = 1.0
        # lambda_min = 5.0, P*lambda_min = 5.0 > P_abs_max = 0.1
        P_abs_max = 0.1

        with pytest.warns(UserWarning, match="infeasible"):
            x = solve_ecbf(h, Q, P_abs_max=P_abs_max, P=P)

        # Must still return a valid power-normalised vector
        power = float(np.real(np.vdot(x, x)))
        assert power == pytest.approx(P, rel=1e-5)
        assert x.shape == (M_ant,)


# ---------------------------------------------------------------------------
# Exposure operator edge cases
# ---------------------------------------------------------------------------


class TestExposureOperatorEdgeCases:
    # --- Hermitian and PSD ---

    def test_hermitian_small(self):
        """Q is Hermitian for a small 2-triangle, 2-antenna problem."""
        rng = np.random.default_rng(7)
        G = rng.standard_normal((2, 3, 2)) + 1j * rng.standard_normal((2, 3, 2))
        areas = np.array([0.01, 0.02])
        Q = compute_exposure_operator(G, areas)
        np.testing.assert_allclose(Q, Q.conj().T, atol=1e-12)

    def test_psd_small(self):
        """All eigenvalues >= 0 for a small problem."""
        rng = np.random.default_rng(8)
        G = rng.standard_normal((3, 3, 3)) + 1j * rng.standard_normal((3, 3, 3))
        areas = np.array([0.01, 0.02, 0.03])
        Q = compute_exposure_operator(G, areas)
        eigenvalues = np.linalg.eigvalsh(Q)
        assert np.all(eigenvalues >= NUMERICAL_FLOOR)

    def test_hermitian_rank1_G(self):
        """With rank-1 G at each triangle, Q is still Hermitian PSD."""
        M_tri, M_ant = 4, 3
        rng = np.random.default_rng(99)
        # G_tilde[m] = a_m * b_m^T, so it has rank 1
        a = rng.standard_normal((M_tri, 3)) + 1j * rng.standard_normal((M_tri, 3))
        b = rng.standard_normal((M_tri, M_ant)) + 1j * rng.standard_normal((M_tri, M_ant))
        G = a[:, :, None] * b[:, None, :]  # (M_tri, 3, M_ant)
        areas = np.ones(M_tri) * 0.01
        Q = compute_exposure_operator(G, areas)
        # Hermitian
        np.testing.assert_allclose(Q, Q.conj().T, atol=1e-12)
        # PSD
        assert np.all(np.linalg.eigvalsh(Q) >= NUMERICAL_FLOOR)

    # --- eigendecompose_Q ---

    def test_eigenvalues_descending(self):
        """eigendecompose_Q returns eigenvalues in descending order."""
        rng = np.random.default_rng(11)
        G = rng.standard_normal((10, 3, 5)) + 1j * rng.standard_normal((10, 3, 5))
        areas = np.ones(10) * 0.01
        Q = compute_exposure_operator(G, areas)
        eigenvalues, _ = eigendecompose_Q(Q)
        assert np.all(np.diff(eigenvalues) <= 1e-12), "Eigenvalues not in descending order"

    def test_eigenvalues_non_negative_after_clamp(self):
        """eigendecompose_Q clamps near-zero negatives to 0."""
        # Construct a nearly-singular PSD matrix that can have tiny negative eigenvalues
        rng = np.random.default_rng(22)
        M_ant = 6
        # Low-rank so last eigenvalues are near 0 (possibly slightly negative due to numerics)
        A = rng.standard_normal((M_ant, 2)) + 1j * rng.standard_normal((M_ant, 2))
        Q_lr = A @ A.conj().T
        Q_lr = (Q_lr + Q_lr.conj().T) / 2
        # Add a tiny negative perturbation to expose clamping
        eps = 1e-14
        Q_lr -= eps * np.eye(M_ant)
        eigenvalues, _ = eigendecompose_Q(Q_lr)
        assert np.all(eigenvalues >= 0.0), f"Negative eigenvalues not clamped: {eigenvalues}"

    # --- compute_rho ---

    def test_rho_zero_h(self, simple_Q):
        """rho returns 0.0 when h is the zero vector."""
        h_zero = np.zeros(4, dtype=complex)
        rho = compute_rho(h_zero, simple_Q)
        assert rho == 0.0

    def test_rho_zero_Q(self, simple_h):
        """rho returns 0.0 when Q is the zero matrix."""
        Q_zero = np.zeros((4, 4), dtype=complex)
        rho = compute_rho(simple_h, Q_zero)
        assert rho == 0.0

    def test_rho_in_unit_interval(self, rng, simple_Q, simple_h):
        """rho is in [0, 1] for generic h and Q."""
        rho = compute_rho(simple_h, simple_Q)
        assert 0.0 <= rho <= 1.0 + 1e-10

    def test_rho_eigenvector_of_max_gives_one(self, rng):
        """rho == 1 when h equals the eigenvector of the largest eigenvalue."""
        M_ant = 4
        Q = _random_hermitian_psd(M_ant, rng, scale=0.5)
        eigenvalues, eigenvectors = eigendecompose_Q(Q)
        h_dominant = eigenvectors[:, 0]  # column of max eigenvalue
        rho = compute_rho(h_dominant, Q, lambda_max=float(eigenvalues[0]))
        assert rho == pytest.approx(1.0, abs=1e-8)


# ---------------------------------------------------------------------------
# Precoder edge cases
# ---------------------------------------------------------------------------


class TestPrecoderEdgeCases:
    def test_2d_x_raises(self):
        """Precoder rejects a 2D array for x."""
        x_2d = np.ones((2, 3), dtype=complex)
        with pytest.raises(ValueError, match="1D"):
            Precoder(x=x_2d)

    def test_mrt_zero_h_returns_valid_precoder(self):
        """Precoder.mrt with zero h returns a valid precoder with power == P."""
        h_zero = np.zeros(4, dtype=complex)
        p = Precoder.mrt(h_zero, P=1.5)
        assert p.power == pytest.approx(1.5, rel=1e-10)
        assert p.n_elements == 4

    def test_mrt_power_matches_P(self, rng):
        """Precoder.mrt: ||x||^2 equals the requested power P."""
        h = _random_channel(4, rng)
        P = 3.7
        p = Precoder.mrt(h, P=P)
        assert p.power == pytest.approx(P, rel=1e-10)

    def test_power_real_and_non_negative(self, rng):
        """Precoder.power is real and >= 0 for an arbitrary x."""
        x = rng.standard_normal(5) + 1j * rng.standard_normal(5)
        p = Precoder(x=x)
        power = p.power
        assert isinstance(power, float)
        assert power >= 0.0

    def test_n_elements_matches_x_length(self, rng):
        """Precoder.n_elements equals len(x)."""
        for M in [1, 3, 8]:
            x = rng.standard_normal(M) + 1j * rng.standard_normal(M)
            p = Precoder(x=x)
            assert p.n_elements == M

    def test_repr_works(self, rng):
        """Precoder.__repr__ does not raise and includes key info."""
        x = rng.standard_normal(4) + 1j * rng.standard_normal(4)
        p = Precoder(x=x)
        r = repr(p)
        assert "Precoder" in r
        assert "M=" in r
        assert "P=" in r


# ---------------------------------------------------------------------------
# Field channel edge cases
# ---------------------------------------------------------------------------


class TestFieldChannelEdgeCases:
    def test_single_element_single_path_shape(self):
        """compute_field_channel returns (1, 3, 1) for 1 triangle, 1 path, 1 element."""
        centroids = np.array([[0.0, 0.0, 0.0]])
        k_hat = np.array([[0.0, 0.0, -1.0]])
        psi = np.array([[1.0 + 0j, 0.0, 0.0]])
        element_index = np.array([0])
        freq_hz = 28e9
        G = compute_field_channel(centroids, k_hat, psi, element_index, freq_hz, n_elements=1)
        assert G.shape == (1, 3, 1)

    def test_multiple_elements_correct_shape(self):
        """G has shape (M_tri, 3, M_ant) for multi-element, multi-path case."""
        M_tri = 4
        N = 6  # paths
        M_ant = 3
        rng = np.random.default_rng(55)
        centroids = rng.standard_normal((M_tri, 3))
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        psi = rng.standard_normal((N, 3)) + 1j * rng.standard_normal((N, 3))
        element_index = np.array([0, 1, 2, 0, 1, 2])
        freq_hz = 28e9
        G = compute_field_channel(centroids, k_hat, psi, element_index, freq_hz, n_elements=M_ant)
        assert G.shape == (M_tri, 3, M_ant)

    def test_zero_psi_gives_zero_G(self):
        """If all psi are zero, G should be zero everywhere."""
        centroids = np.array([[0.0, 0.0, 1.0], [1.0, 0.0, 0.0]])
        k_hat = np.array([[0.0, 0.0, -1.0]])
        psi = np.zeros((1, 3), dtype=complex)
        element_index = np.array([0])
        G = compute_field_channel(centroids, k_hat, psi, element_index, freq_hz=28e9, n_elements=2)
        np.testing.assert_allclose(G, 0.0, atol=1e-30)

    def test_element_with_no_paths_is_zero_column(self):
        """An element index that receives no paths should have all-zero column in G."""
        centroids = np.array([[0.0, 0.0, 0.0]])
        k_hat = np.array([[0.0, 0.0, -1.0]])
        psi = np.array([[1.0 + 0j, 0.0, 0.0]])
        # Only element 0 gets a path; element 1 gets nothing
        element_index = np.array([0])
        G = compute_field_channel(centroids, k_hat, psi, element_index, freq_hz=28e9, n_elements=2)
        assert G.shape == (1, 3, 2)
        np.testing.assert_allclose(G[0, :, 1], 0.0, atol=1e-30)

    def test_out_of_range_element_index_raises(self):
        """element_index values >= n_elements should raise."""
        centroids = np.array([[0.0, 0.0, 0.0]])
        k_hat = np.array([[0.0, 0.0, -1.0]])
        psi = np.array([[1.0 + 0j, 0.0, 0.0]])
        element_index = np.array([5])  # out of range
        with pytest.raises(ValueError, match="element_index"):
            compute_field_channel(centroids, k_hat, psi, element_index, 28e9, n_elements=4)

    def test_negative_element_index_raises(self):
        """Negative element_index values should raise."""
        centroids = np.array([[0.0, 0.0, 0.0]])
        k_hat = np.array([[0.0, 0.0, -1.0]])
        psi = np.array([[1.0 + 0j, 0.0, 0.0]])
        element_index = np.array([-1])
        with pytest.raises(ValueError, match="element_index"):
            compute_field_channel(centroids, k_hat, psi, element_index, 28e9, n_elements=4)

    def test_valid_element_index_accepted(self):
        """Valid element_index should not raise."""
        centroids = np.array([[0.0, 0.0, 0.0]])
        k_hat = np.array([[0.0, 0.0, -1.0]])
        psi = np.array([[1.0 + 0j, 0.0, 0.0]])
        element_index = np.array([0])
        G = compute_field_channel(centroids, k_hat, psi, element_index, 28e9, n_elements=1)
        assert G.shape == (1, 3, 1)


# ---------------------------------------------------------------------------
# accumulate_by_element edge cases
# ---------------------------------------------------------------------------


class TestAccumulateByElement:
    def test_empty_paths(self):
        """Should produce zero G when no paths are given."""
        from aegis.coherent._accumulate import accumulate_by_element

        weighted = np.zeros((5, 0, 3), dtype=complex)
        element_index = np.array([], dtype=int)
        G = accumulate_by_element(weighted, element_index, M=5, n_elements=4)
        assert G.shape == (5, 3, 4)
        np.testing.assert_array_equal(G, 0)

    def test_single_element_single_path(self):
        """Single path to single element should accumulate correctly."""
        from aegis.coherent._accumulate import accumulate_by_element

        weighted = np.array([[[1.0 + 2j, 0.5 + 0j, 0.0 + 1j]]], dtype=complex)  # (1, 1, 3)
        element_index = np.array([0])
        G = accumulate_by_element(weighted, element_index, M=1, n_elements=1)
        assert G.shape == (1, 3, 1)
        np.testing.assert_allclose(G[0, :, 0], [1.0 + 2j, 0.5 + 0j, 0.0 + 1j])

    def test_duplicate_element_indices_accumulate(self):
        """Multiple paths to same element should be summed."""
        from aegis.coherent._accumulate import accumulate_by_element

        # Two paths both to element 0, at one triangle
        weighted = np.array(
            [
                [
                    [1.0 + 0j, 0.0, 0.0],
                    [0.0 + 0j, 1.0 + 0j, 0.0],
                ]
            ],
            dtype=complex,
        )  # (1, 2, 3)
        element_index = np.array([0, 0])
        G = accumulate_by_element(weighted, element_index, M=1, n_elements=1)
        assert G.shape == (1, 3, 1)
        np.testing.assert_allclose(G[0, :, 0], [1.0, 1.0, 0.0])
