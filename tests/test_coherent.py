"""Tests for coherent MIMO dosimetry (Levels 7-8).

Validates against monograph Theorem 4.1, Corollaries 4.1-4.2,
and physical invariants (Q is Hermitian PSD, energy conservation,
single-wave and incoherent limits).
"""

import numpy as np
import pytest

from aegis.coherent.body_channel import compute_body_channel
from aegis.coherent.ecbf import solve_ecbf
from aegis.coherent.exposure_operator import (
    compute_exposure_operator,
    compute_rho,
    eigendecompose_Q,
)
from aegis.coherent.fresnel_operator import (
    apply_fresnel_operator,
    compute_fresnel_operator,
    te_tm_basis,
)
from aegis.paths import PropagationPaths
from aegis.precoder import Precoder
from aegis.tissue.dielectric import SKIN_28GHZ
from aegis.tissue.fresnel import fresnel_amplitude, fresnel_transmission
from tests.conftest import NUMERICAL_FLOOR

# Fixtures (flat_mesh, ico_mesh, engine, single_path_down, multi_path)
# are provided by conftest.py.


# ---------------------------------------------------------------------------
# Fresnel amplitude tests
# ---------------------------------------------------------------------------


class TestFresnelAmplitude:
    def test_normal_incidence_matches_T0(self):
        """At mu=1, |t_s|^2 and |t_p|^2 relate to T0 via energy conservation."""
        n = SKIN_28GHZ.n_complex
        t_s, t_p = fresnel_amplitude(1.0, n)
        T_s, T_p = fresnel_transmission(1.0, n)
        # T = 1 - |r|^2, and at normal incidence r_s = (1-n)/(1+n)
        # t_s = 2/(1+n), |t_s|^2 * Re(n)/1 should relate to T_s
        # Check consistency: T_s = 1 - |r_s|^2
        r_s = (1.0 - np.sqrt(n**2)) / (1.0 + np.sqrt(n**2))
        assert abs(T_s - (1 - abs(r_s) ** 2)) < 0.01

    def test_grazing_incidence_small(self):
        """At grazing incidence (mu->0), transmission vanishes."""
        n = SKIN_28GHZ.n_complex
        t_s, t_p = fresnel_amplitude(0.01, n)
        assert abs(t_s) < 0.1
        assert abs(t_p) < 0.5  # TM has a smaller effect at grazing

    def test_vectorised(self):
        """fresnel_amplitude works with arrays."""
        n = SKIN_28GHZ.n_complex
        mu = np.linspace(0.1, 1.0, 10)
        t_s, t_p = fresnel_amplitude(mu, n)
        assert t_s.shape == (10,)
        assert t_p.shape == (10,)

    def test_power_consistency(self):
        """Power T = 1-|r|^2 and amplitude t are consistent at normal incidence."""
        n = SKIN_28GHZ.n_complex
        t_s, t_p = fresnel_amplitude(1.0, n)
        # At normal incidence t_s = t_p, and T_0 = 4*Re(n)/|1+n|^2
        # The amplitude t = 2/(1+n) at normal incidence
        expected_t = 2.0 / (1.0 + n)
        assert abs(t_s - expected_t) < 1e-10


# ---------------------------------------------------------------------------
# TE/TM basis tests
# ---------------------------------------------------------------------------


class TestTeTmBasis:
    def test_orthogonal_to_k(self):
        """e_s and e_p should be perpendicular to k_hat."""
        k_hat = np.array([[0, 0, -1.0], [1, 0, 0], [0, 1, 0]])
        normals = np.array([[0, 0, 1.0], [1, 0, 0], [0, 0, 1.0]])
        e_s, e_p = te_tm_basis(k_hat, normals)
        for n_idx in range(3):
            for m_idx in range(3):
                dot_s = abs(np.dot(e_s[m_idx, n_idx], k_hat[n_idx]))
                dot_p = abs(np.dot(e_p[m_idx, n_idx], k_hat[n_idx]))
                assert dot_s < 1e-10, f"e_s not perp to k at ({m_idx},{n_idx})"
                assert dot_p < 1e-10, f"e_p not perp to k at ({m_idx},{n_idx})"

    def test_unit_vectors(self):
        """e_s and e_p should be unit vectors."""
        k_hat = np.array([[0, 0, -1.0], [1, 0, 0]])
        normals = np.array([[0, 0, 1.0], [0, 1, 0], [1, 0, 0]])
        e_s, e_p = te_tm_basis(k_hat, normals)
        for m in range(3):
            for n in range(2):
                assert abs(np.linalg.norm(e_s[m, n]) - 1.0) < 1e-10
                assert abs(np.linalg.norm(e_p[m, n]) - 1.0) < 1e-10

    def test_e_s_perp_e_p(self):
        """e_s and e_p should be mutually perpendicular."""
        k_hat = np.array([[0.5, 0.5, -np.sqrt(0.5)]])
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        normals = np.array([[0, 0, 1.0]])
        e_s, e_p = te_tm_basis(k_hat, normals)
        dot = abs(np.dot(e_s[0, 0], e_p[0, 0]))
        assert dot < 1e-10


# ---------------------------------------------------------------------------
# Fresnel operator tests
# ---------------------------------------------------------------------------


class TestFresnelOperator:
    def test_back_facing_zeroed(self):
        """Back-facing paths (mu <= 0) have zero transmission."""
        normals = np.array([[0, 0, 1.0]])
        k_hat = np.array([[0, 0, 1.0]])  # coming from below
        n = SKIN_28GHZ.n_complex
        mu, t_s, t_p, e_s, e_p = compute_fresnel_operator(normals, k_hat, n)
        assert mu[0, 0] < 0
        assert t_s[0, 0] == 0.0
        assert t_p[0, 0] == 0.0

    def test_front_facing_nonzero(self):
        """Front-facing paths have non-zero transmission."""
        normals = np.array([[0, 0, 1.0]])
        k_hat = np.array([[0, 0, -1.0]])  # from above
        n = SKIN_28GHZ.n_complex
        mu, t_s, t_p, e_s, e_p = compute_fresnel_operator(normals, k_hat, n)
        assert mu[0, 0] > 0
        assert abs(t_s[0, 0]) > 0
        assert abs(t_p[0, 0]) > 0

    def test_apply_preserves_polarisation_at_normal(self):
        """At normal incidence, t_s = t_p, so F @ psi = t * psi (up to projection)."""
        normals = np.array([[0, 0, 1.0]])
        k_hat = np.array([[0, 0, -1.0]])
        n = SKIN_28GHZ.n_complex
        mu, t_s, t_p, e_s, e_p = compute_fresnel_operator(normals, k_hat, n)

        # psi perpendicular to k_hat
        psi = np.array([[1.0 + 0j, 0, 0]])
        F_psi = apply_fresnel_operator(psi, t_s, t_p, e_s, e_p)
        # At normal incidence, t_s = t_p = 2/(1+n)
        expected_amp = abs(2.0 / (1.0 + n))
        assert abs(np.linalg.norm(F_psi[0, 0]) - expected_amp) < 0.01


# ---------------------------------------------------------------------------
# Body channel tests
# ---------------------------------------------------------------------------


class TestBodyChannel:
    def test_output_shape(self, flat_mesh):
        """G_tilde has shape (M, 3, M_ant)."""
        N, M_ant = 5, 3
        rng = np.random.default_rng(99)
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        psi = rng.standard_normal((N, 3)) + 1j * rng.standard_normal((N, 3))
        # Make psi perpendicular to k_hat
        for i in range(N):
            psi[i] -= np.dot(psi[i], k_hat[i]) * k_hat[i]
        element_index = np.array([0, 0, 1, 1, 2])

        G_tilde = compute_body_channel(
            flat_mesh.normals,
            flat_mesh.centroids,
            k_hat,
            psi,
            element_index,
            SKIN_28GHZ.n_complex,
            SKIN_28GHZ.sigma,
            SKIN_28GHZ.freq_hz,
            n_elements=M_ant,
        )
        assert G_tilde.shape == (flat_mesh.n_triangles, 3, M_ant)

    def test_back_facing_contributes_nothing(self):
        """A path from below a flat plane contributes zero to G_tilde."""
        normals = np.array([[0, 0, 1.0]])
        centroids = np.array([[0, 0, 0.0]])
        k_hat = np.array([[0, 0, 1.0]])  # from below
        psi = np.array([[1.0 + 0j, 0, 0]])
        element_index = np.array([0])

        G_tilde = compute_body_channel(
            normals,
            centroids,
            k_hat,
            psi,
            element_index,
            SKIN_28GHZ.n_complex,
            SKIN_28GHZ.sigma,
            SKIN_28GHZ.freq_hz,
            n_elements=1,
        )
        assert np.allclose(G_tilde, 0.0, atol=1e-15)


# ---------------------------------------------------------------------------
# Exposure operator Q tests
# ---------------------------------------------------------------------------


class TestExposureOperator:
    def _make_G_tilde(self, M_tri=20, M_ant=4, rng=None):
        if rng is None:
            rng = np.random.default_rng(42)
        G = rng.standard_normal((M_tri, 3, M_ant)) + 1j * rng.standard_normal((M_tri, 3, M_ant))
        return G

    def test_hermitian(self):
        """Q must be Hermitian."""
        G_tilde = self._make_G_tilde()
        areas = np.ones(20) * 0.01
        Q = compute_exposure_operator(G_tilde, areas)
        np.testing.assert_allclose(Q, Q.conj().T, atol=1e-12)

    def test_psd(self):
        """Q must be positive semidefinite (all eigenvalues >= 0)."""
        G_tilde = self._make_G_tilde()
        areas = np.ones(20) * 0.01
        Q = compute_exposure_operator(G_tilde, areas)
        eigenvalues = np.linalg.eigvalsh(Q)
        assert np.all(eigenvalues >= NUMERICAL_FLOOR)

    def test_total_power_via_Q(self, ico_mesh, engine):
        """P_abs = x^H Q x should match sum(sab * areas)."""
        rng = np.random.default_rng(77)
        N, M_ant = 10, 4
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        psi = rng.standard_normal((N, 3)) + 1j * rng.standard_normal((N, 3))
        for i in range(N):
            psi[i] -= np.dot(psi[i], k_hat[i]) * k_hat[i]
        element_index = rng.integers(0, M_ant, size=N)

        paths = PropagationPaths(
            k_hat=k_hat,
            psi=psi,
            element_index=element_index,
            delay=np.zeros(N),
            is_los=np.ones(N, dtype=bool),
        )

        x = rng.standard_normal(M_ant) + 1j * rng.standard_normal(M_ant)
        precoder = Precoder(x=x)

        result = engine.compute(ico_mesh, paths, level=7, precoder=precoder)

        # P_abs from result
        p_abs_surface = result.p_abs
        # P_abs from Q
        p_abs_Q = float(np.real(x.conj() @ result.Q @ x))

        np.testing.assert_allclose(p_abs_surface, p_abs_Q, rtol=1e-6)

    def test_eigenvalues_non_negative(self):
        """Eigenvalues of Q should be non-negative."""
        G_tilde = self._make_G_tilde(M_tri=50, M_ant=8)
        areas = np.ones(50) * 0.01
        Q = compute_exposure_operator(G_tilde, areas)
        eigenvalues, _ = eigendecompose_Q(Q)
        assert np.all(eigenvalues >= 0)

    def test_eigenvalues_descending(self):
        """Eigenvalues should be in descending order."""
        G_tilde = self._make_G_tilde(M_tri=50, M_ant=8)
        areas = np.ones(50) * 0.01
        Q = compute_exposure_operator(G_tilde, areas)
        eigenvalues, _ = eigendecompose_Q(Q)
        assert np.all(np.diff(eigenvalues) <= 1e-12)


# ---------------------------------------------------------------------------
# rho tests
# ---------------------------------------------------------------------------


class TestRho:
    def test_rho_in_unit_interval(self):
        """rho should be in [0, 1]."""
        rng = np.random.default_rng(88)
        M_ant = 4
        G_tilde = rng.standard_normal((20, 3, M_ant)) + 1j * rng.standard_normal((20, 3, M_ant))
        areas = np.ones(20) * 0.01
        Q = compute_exposure_operator(G_tilde, areas)
        h = rng.standard_normal(M_ant) + 1j * rng.standard_normal(M_ant)
        rho = compute_rho(h, Q)
        assert 0.0 <= rho <= 1.0 + 1e-10

    def test_rho_one_for_dominant_eigenvector(self):
        """When h = conj(v_1), MRT produces the worst-case precoder, so rho = 1."""
        rng = np.random.default_rng(99)
        M_ant = 4
        G_tilde = rng.standard_normal((20, 3, M_ant)) + 1j * rng.standard_normal((20, 3, M_ant))
        areas = np.ones(20) * 0.01
        Q = compute_exposure_operator(G_tilde, areas)
        eigenvalues, eigenvectors = eigendecompose_Q(Q)
        # MRT with h = conj(v_1) gives x = sqrt(P)*v_1/||v_1||, the worst-case precoder
        h = np.conj(eigenvectors[:, 0])
        rho = compute_rho(h, Q, lambda_max=float(eigenvalues[0]))
        assert rho == pytest.approx(1.0, abs=1e-8)

    def test_rho_matches_mrt_pabs(self):
        """rho must equal P_abs_MRT / (P * lambda_max) exactly (monograph eq:rho-def)."""
        rng = np.random.default_rng(77)
        M_ant = 4
        G_tilde = rng.standard_normal((20, 3, M_ant)) + 1j * rng.standard_normal((20, 3, M_ant))
        areas = np.ones(20) * 0.01
        Q = np.asarray(compute_exposure_operator(G_tilde, areas))
        eigenvalues, _ = eigendecompose_Q(Q)
        lam_max = float(eigenvalues[0])
        h = rng.standard_normal(M_ant) + 1j * rng.standard_normal(M_ant)
        P = 2.0
        # MRT precoder: x = sqrt(P) * h* / ||h||
        x_mrt = np.sqrt(P) * h.conj() / np.linalg.norm(h)
        p_abs_mrt = float(np.real(x_mrt.conj() @ Q @ x_mrt))
        rho_from_pabs = p_abs_mrt / (P * lam_max)
        rho = compute_rho(h, Q, lambda_max=lam_max)
        assert rho == pytest.approx(rho_from_pabs, abs=1e-10)


# ---------------------------------------------------------------------------
# Corollary 4.1: single-wave limit
# ---------------------------------------------------------------------------


class TestSingleWaveLimit:
    def test_coherent_matches_incoherent_single_path(self, ico_mesh, engine):
        """Corollary 4.1: with N=M=1, coherent Level 7 matches incoherent Level 3.

        For a single path from a single element, the coherent formula reduces
        to S_ab = S_inc * T_eff * ReLU(mu), which matches Level 3 (exact Fresnel).
        """
        k_hat = np.array([[0.0, 0.0, -1.0]])
        power = np.array([1.0])
        paths = PropagationPaths.from_powers(k_hat=k_hat, power=power)

        # Incoherent Level 3
        r3 = engine.compute(ico_mesh, paths, level=3)

        # Coherent Level 7 with trivial precoder (single element)
        x = np.array([1.0 + 0j])
        # Scale psi so that |psi|^2 / (2*Z_0) * |x|^2 gives the same power
        # from_powers already sets psi correctly for power=1.0
        precoder = Precoder(x=x)
        r7 = engine.compute(ico_mesh, paths, level=7, precoder=precoder)

        # Total power should be close (within ~5% for Approx 1+2 errors)
        rel_err = abs(r7.p_abs - r3.p_abs) / max(r3.p_abs, 1e-20)
        assert rel_err < 0.10, f"Single-wave limit failed: L7={r7.p_abs:.6f}, L3={r3.p_abs:.6f}, rel_err={rel_err:.2%}"


# ---------------------------------------------------------------------------
# Corollary 4.2: incoherent limit
# ---------------------------------------------------------------------------


class TestIncoherentLimit:
    def test_random_phases_average_to_incoherent(self, ico_mesh, engine):
        """Corollary 4.2: random phases, averaged over realisations, match incoherent.

        With many random-phase realisations, cross-terms average to zero,
        and the coherent result converges to the incoherent (Level 3) result.
        """
        rng = np.random.default_rng(42)
        N = 10
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        power = rng.uniform(0.5, 2.0, size=N)

        # Incoherent Level 3
        paths_incoh = PropagationPaths.from_powers(k_hat=k_hat, power=power)
        r3 = engine.compute(ico_mesh, paths_incoh, level=3)

        # Average coherent Level 7 over many random phase realisations
        n_realisations = 200
        sab_avg = np.zeros(ico_mesh.n_triangles)

        for _ in range(n_realisations):
            # Random phases on each path
            phases = np.exp(2j * np.pi * rng.uniform(0, 1, size=N))
            psi = paths_incoh.psi * phases[:, np.newaxis]
            element_index = np.arange(N, dtype=np.intp)

            paths_coh = PropagationPaths(
                k_hat=k_hat,
                psi=psi,
                element_index=element_index,
                delay=np.zeros(N),
                is_los=np.ones(N, dtype=bool),
            )

            # Each path from separate element, x = [1, 1, ..., 1]
            x = np.ones(N, dtype=complex)
            precoder = Precoder(x=x)

            r7 = engine.compute(ico_mesh, paths_coh, level=7, precoder=precoder)
            sab_avg += r7.sab

        sab_avg /= n_realisations
        p_abs_avg = float(np.sum(sab_avg * ico_mesh.areas))

        # Should converge to incoherent result within ~15%
        # (Monte Carlo variance + approximation errors)
        rel_err = abs(p_abs_avg - r3.p_abs) / max(r3.p_abs, 1e-20)
        assert rel_err < 0.15, (
            f"Incoherent limit failed: avg coherent={p_abs_avg:.6f}, incoherent={r3.p_abs:.6f}, rel_err={rel_err:.2%}"
        )


# ---------------------------------------------------------------------------
# ECBF tests
# ---------------------------------------------------------------------------


class TestECBF:
    def test_mrt_when_unconstrained(self):
        """When P_abs_max is large, ECBF returns MRT."""
        rng = np.random.default_rng(55)
        M_ant = 4
        Q = np.eye(M_ant, dtype=complex) * 0.01
        h = rng.standard_normal(M_ant) + 1j * rng.standard_normal(M_ant)
        P = 1.0
        P_abs_max = 1e6  # very loose

        x_star = solve_ecbf(h, Q, P_abs_max, P)
        x_mrt = np.sqrt(P) * h.conj() / np.linalg.norm(h)

        # Should be proportional to MRT
        # Normalise both and compare
        x_star_n = x_star / np.linalg.norm(x_star)
        x_mrt_n = x_mrt / np.linalg.norm(x_mrt)
        alignment = abs(np.vdot(x_star_n, x_mrt_n))
        assert alignment > 0.99

    def test_ecbf_sweep_matches_per_point(self):
        """solve_ecbf_sweep must equal looping solve_ecbf, but with one eigh.

        The budget sweep shares one (h, Q) across many absorbed-power budgets, so
        the sweep solver factorises Q once and reuses it. It must be numerically
        identical to calling solve_ecbf per budget (otherwise the fast path would
        silently change the chart). Covers the MRT-feasible, binding, and
        power-slack branches by spanning loose to tight budgets.
        """
        from aegis.coherent.ecbf import solve_ecbf_sweep

        rng = np.random.default_rng(2024)
        M_ant = 12
        G_tilde = rng.standard_normal((40, 3, M_ant)) + 1j * rng.standard_normal((40, 3, M_ant))
        areas = np.ones(40) * 0.01
        Q = compute_exposure_operator(G_tilde, areas)
        h = rng.standard_normal(M_ant) + 1j * rng.standard_normal(M_ant)
        P = 1.5
        x_mrt = np.sqrt(P) * h.conj() / np.linalg.norm(h)
        p_abs_mrt = float(np.real(x_mrt.conj() @ Q @ x_mrt))
        budgets = [f * p_abs_mrt for f in (0.01, 0.05, 0.2, 0.5, 0.8, 0.99, 1.0, 1.5)]

        swept = solve_ecbf_sweep(h, Q, budgets, P)
        assert len(swept) == len(budgets)
        for b, x_sweep in zip(budgets, swept, strict=True):
            x_ref = np.asarray(solve_ecbf(h, Q, b, P))
            np.testing.assert_allclose(np.asarray(x_sweep), x_ref, rtol=0, atol=1e-12)

    def test_ecbf_respects_power_budget(self):
        """||x*||^2 must not exceed P (may be strictly less in the slack regime)."""
        rng = np.random.default_rng(66)
        M_ant = 4
        G_tilde = rng.standard_normal((20, 3, M_ant)) + 1j * rng.standard_normal((20, 3, M_ant))
        areas = np.ones(20) * 0.01
        Q = compute_exposure_operator(G_tilde, areas)
        h = rng.standard_normal(M_ant) + 1j * rng.standard_normal(M_ant)
        P = 2.0
        P_abs_max = 0.001

        x_star = np.asarray(solve_ecbf(h, Q, P_abs_max=P_abs_max, P=P))
        power = float(np.real(np.vdot(x_star, x_star)))
        p_abs = float(np.real(x_star.conj() @ Q @ x_star))
        assert power <= P * (1.0 + 1e-6), f"||x||^2 = {power} exceeds P = {P}"
        assert p_abs <= P_abs_max * (1.0 + 1e-6), f"p_abs = {p_abs} exceeds P_abs_max = {P_abs_max}"

    def test_ecbf_reduces_absorption(self):
        """ECBF should reduce P_abs compared to MRT when constraint is feasible."""
        rng = np.random.default_rng(77)
        M_ant = 8
        P = 1.0

        # Construct Q with a large spread in eigenvalues so ECBF has room
        # to steer away from large-eigenvalue directions.
        eigvals = np.array([10.0, 5.0, 1.0, 0.5, 0.1, 0.01, 0.001, 0.0001])
        V = np.linalg.qr(rng.standard_normal((M_ant, M_ant)) + 1j * rng.standard_normal((M_ant, M_ant)))[0]
        Q = (V * eigvals[np.newaxis, :]) @ V.conj().T
        Q = (Q + Q.conj().T) / 2

        # h mostly aligned with the largest eigenvalue direction
        h = V[:, 0] + 0.1 * (rng.standard_normal(M_ant) + 1j * rng.standard_normal(M_ant))

        # MRT
        x_mrt = np.sqrt(P) * h.conj() / np.linalg.norm(h)
        p_abs_mrt = float(np.real(x_mrt.conj() @ Q @ x_mrt))

        # Set feasible constraint well above minimum
        P_abs_max = p_abs_mrt * 0.5

        x_star = solve_ecbf(h, Q, P_abs_max, P)
        p_abs_ecbf = float(np.real(x_star.conj() @ Q @ x_star))

        assert p_abs_ecbf <= P_abs_max * 1.001
        assert p_abs_ecbf < p_abs_mrt

    def test_ecbf_power_slack_regime(self):
        """ECBF must handle the power-slack regime where ||x||^2 < P.

        When Q is invertible and h is not aligned with the smallest eigenvalue
        directions, the power constraint may be slack at optimality. The solver
        must still satisfy x^H Q x <= P_abs_max AND must return the true
        slack-regime optimum (x = alpha * Q^{-1} h*), not a degenerate
        zero-objective fallback.
        """
        Q = np.diag([10.0, 1.0, 0.001])
        h = np.array([1.0, 1.0, 0.0], dtype=complex)
        P = 1.0
        P_abs_max = 0.5

        x_star = np.asarray(solve_ecbf(h, Q, P_abs_max, P))
        p_abs = float(np.real(x_star.conj() @ Q @ x_star))
        power = float(np.real(np.vdot(x_star, x_star)))
        obj = float(np.abs(h @ x_star) ** 2)

        assert p_abs <= P_abs_max * 1.001, f"Exposure constraint violated: p_abs={p_abs:.4f} > P_abs_max={P_abs_max}"
        assert power <= P * 1.001, f"Power budget exceeded: ||x||^2={power:.4f} > P={P}"

        # Closed-form slack-regime optimum: x = alpha * Q^{-1} h*, alpha chosen so x^H Q x = P_abs_max.
        # Solver must reach (or exceed) this objective; falling back to the smallest-eigenvalue
        # direction (the dead-code bug) gives obj=0 here because h is orthogonal to it.
        qinv_h = np.linalg.solve(Q, h.conj())
        alpha = np.sqrt(P_abs_max / float(np.real(h.conj() @ qinv_h)))
        obj_optimal = float(np.abs(h @ (alpha * qinv_h)) ** 2)
        assert obj >= obj_optimal * 0.99, (
            f"Solver returned suboptimal objective: {obj:.6f} vs optimum {obj_optimal:.6f}"
        )


# ---------------------------------------------------------------------------
# Precoder tests
# ---------------------------------------------------------------------------


class TestPrecoder:
    def test_mrt_power(self):
        h = np.array([1.0, 0, 0, 0], dtype=complex)
        p = Precoder.mrt(h, P=2.0)
        assert p.power == pytest.approx(2.0, rel=1e-10)

    def test_mrt_direction(self):
        h = np.array([1.0, 1j, 0, 0], dtype=complex)
        p = Precoder.mrt(h, P=1.0)
        # x should be proportional to h*
        x_dir = p.x / np.linalg.norm(p.x)
        h_conj_dir = h.conj() / np.linalg.norm(h.conj())
        alignment = abs(np.vdot(x_dir, h_conj_dir))
        assert alignment > 0.999


# ---------------------------------------------------------------------------
# Level 7 engine integration
# ---------------------------------------------------------------------------


class TestLevel7Engine:
    def test_returns_Q_and_eigenvalues(self, ico_mesh, engine):
        """Level 7 result should include Q and eigenvalues."""
        rng = np.random.default_rng(42)
        N, M_ant = 5, 2
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        psi = rng.standard_normal((N, 3)) + 1j * rng.standard_normal((N, 3))
        for i in range(N):
            psi[i] -= np.dot(psi[i], k_hat[i]) * k_hat[i]
        element_index = rng.integers(0, M_ant, size=N)
        paths = PropagationPaths(
            k_hat=k_hat,
            psi=psi,
            element_index=element_index,
            delay=np.zeros(N),
            is_los=np.ones(N, dtype=bool),
        )
        x = rng.standard_normal(M_ant) + 1j * rng.standard_normal(M_ant)
        precoder = Precoder(x=x)

        result = engine.compute(ico_mesh, paths, level=7, precoder=precoder)

        assert result.Q is not None
        assert result.Q.shape == (M_ant, M_ant)
        assert result.eigenvalues is not None
        assert result.eigenvalues.shape == (M_ant,)
        assert result.fidelity_level == 7

    def test_sab_non_negative(self, ico_mesh, engine):
        """S_ab should be non-negative for all triangles."""
        rng = np.random.default_rng(55)
        N, M_ant = 10, 3
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        psi = rng.standard_normal((N, 3)) + 1j * rng.standard_normal((N, 3))
        for i in range(N):
            psi[i] -= np.dot(psi[i], k_hat[i]) * k_hat[i]
        element_index = rng.integers(0, M_ant, size=N)
        paths = PropagationPaths(
            k_hat=k_hat,
            psi=psi,
            element_index=element_index,
            delay=np.zeros(N),
            is_los=np.ones(N, dtype=bool),
        )
        precoder = Precoder(x=np.ones(M_ant, dtype=complex))

        result = engine.compute(ico_mesh, paths, level=7, precoder=precoder)
        assert np.all(result.sab >= 0)


# ---------------------------------------------------------------------------
# Level 8 engine integration
# ---------------------------------------------------------------------------


class TestLevel8Engine:
    def test_requires_h(self, ico_mesh, engine):
        """Level 8 must raise ValueError if h is not provided."""
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0, 0, -1.0]]),
            power=np.array([1.0]),
        )
        precoder = Precoder(x=np.array([1.0 + 0j]))
        with pytest.raises(ValueError, match="h"):
            engine.compute(ico_mesh, paths, level=8, precoder=precoder)

    def test_level8_reduces_absorption(self, ico_mesh, engine):
        """Level 8 ECBF should reduce absorption vs MRT under tight constraint."""
        rng = np.random.default_rng(88)
        N, M_ant = 8, 4
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        psi = rng.standard_normal((N, 3)) + 1j * rng.standard_normal((N, 3))
        for i in range(N):
            psi[i] -= np.dot(psi[i], k_hat[i]) * k_hat[i]
        element_index = rng.integers(0, M_ant, size=N)
        paths = PropagationPaths(
            k_hat=k_hat,
            psi=psi,
            element_index=element_index,
            delay=np.zeros(N),
            is_los=np.ones(N, dtype=bool),
        )

        h = rng.standard_normal(M_ant) + 1j * rng.standard_normal(M_ant)

        # MRT precoder
        precoder_mrt = Precoder.mrt(h, P=1.0)
        r7 = engine.compute(ico_mesh, paths, level=7, precoder=precoder_mrt, h=h)

        # ECBF with tight constraint
        P_abs_max = r7.p_abs * 0.3
        r8 = engine.compute(
            ico_mesh,
            paths,
            level=8,
            h=h,
            P_abs_max=P_abs_max,
        )

        assert r8.p_abs <= P_abs_max * 1.05
        assert r8.Q is not None
        assert r8.rho is not None
        assert 0.0 <= r8.rho <= 1.0 + 1e-10


# ---------------------------------------------------------------------------
# Factored body channel equivalence
# ---------------------------------------------------------------------------


class TestFactoredBodyChannel:
    """Verify compute_body_channel_factored matches compute_body_channel."""

    def test_factored_matches_original(self, flat_mesh):
        """Factored Fresnel must produce the same G_tilde as the original."""
        from aegis.coherent.body_channel import compute_body_channel_factored
        from aegis.mimo.array import AntennaArray
        from aegis.mimo.array_paths import expand_paths_to_array

        freq_hz = 28e9
        tissue = SKIN_28GHZ
        n_tilde = tissue.n_complex
        sigma = tissue.sigma

        # 2-element array with offset
        positions = np.array([[0.0, 0.0, 1.0], [0.05, 0.0, 1.0]])
        array = AntennaArray(element_positions=positions)

        # Center paths: 3 paths from above
        rng = np.random.default_rng(42)
        N_center = 3
        k_raw = rng.standard_normal((N_center, 3))
        k_raw[:, 2] = -np.abs(k_raw[:, 2])  # downward
        k_hat = k_raw / np.linalg.norm(k_raw, axis=1, keepdims=True)
        psi = (rng.standard_normal((N_center, 3)) + 1j * rng.standard_normal((N_center, 3))) * 0.01

        center_paths = PropagationPaths(
            k_hat=k_hat,
            psi=psi,
            element_index=np.zeros(N_center, dtype=np.intp),
            delay=np.zeros(N_center),
            is_los=np.array([True, False, False]),
        )

        # Expand to per-element paths
        expanded = expand_paths_to_array(center_paths, array, freq_hz)

        # Original: compute with expanded paths
        G_original = compute_body_channel(
            normals=flat_mesh.normals,
            centroids=flat_mesh.centroids,
            k_hat=expanded.k_hat,
            psi=expanded.psi,
            element_index=expanded.element_index,
            n_tilde=n_tilde,
            sigma=sigma,
            freq_hz=freq_hz,
            n_elements=array.n_elements,
        )

        # Factored: compute with center + element psi
        G_factored = compute_body_channel_factored(
            normals=flat_mesh.normals,
            centroids=flat_mesh.centroids,
            center_k_hat=center_paths.k_hat,
            center_psi=center_paths.psi,
            element_psi=expanded.psi,
            element_index=expanded.element_index,
            n_tilde=n_tilde,
            sigma=sigma,
            freq_hz=freq_hz,
            n_elements=array.n_elements,
        )

        np.testing.assert_allclose(
            G_factored,
            G_original,
            rtol=1e-10,
            atol=1e-15,
            err_msg="Factored body channel must match original",
        )
