"""Tests for MIMO peak S_ab optimizer."""

import numpy as np
import pytest


def _make_synthetic_scene(n_triangles=50, n_ant=16, seed=42):
    """Build a synthetic G_tilde with a clear hotspot for MRT to create.

    Uses 16 antennas (enough DOF to redistribute energy) and a single
    triangle with a correlated channel that MRT focuses all power onto.
    """
    rng = np.random.default_rng(seed)
    G_tilde = (rng.standard_normal((n_triangles, 3, n_ant)) + 1j * rng.standard_normal((n_triangles, 3, n_ant))) * 0.01
    # Single hotspot triangle with strong correlated channel
    G_tilde[0, :, :] = 0.5 * np.ones((3, n_ant))
    # MRT precoder: aligns perfectly with hotspot
    h = G_tilde[0, 0, :]
    x_mrt = np.conj(h) / np.linalg.norm(h)
    return G_tilde, x_mrt


class TestMimoPeakSetup:
    def test_setup_returns_state(self):
        from aegis.optim.mimo_peak import setup

        G_tilde, x_mrt = _make_synthetic_scene()
        state = setup(
            G_tilde=G_tilde,
            x_init=x_mrt,
            signal_threshold=0.0,
            p_max=1.0,
        )
        assert state["x"].shape == (16,)
        assert state["G_tilde"].shape == (50, 3, 16)

    def test_setup_rejects_mismatched_shapes(self):
        from aegis.optim.mimo_peak import setup

        G_tilde, _ = _make_synthetic_scene()
        x_bad = np.ones(8, dtype=complex)
        with pytest.raises(ValueError, match="x_init shape"):
            setup(G_tilde=G_tilde, x_init=x_bad, signal_threshold=0.0, p_max=1.0)


class TestMimoPeakStep:
    def test_step_reduces_peak(self):
        from aegis.optim.mimo_peak import setup, step

        G_tilde, x_mrt = _make_synthetic_scene()
        state = setup(G_tilde=G_tilde, x_init=x_mrt, signal_threshold=0.0, p_max=1.0)

        initial_peak = state["objective"]
        for _ in range(100):
            state, result = step(state)

        assert result["objective"] < initial_peak * 0.5  # at least 50% reduction
        assert result["sab"].shape == (50,)
        assert np.all(result["sab"] >= 0)

    def test_step_respects_power_constraint(self):
        from aegis.optim.mimo_peak import setup, step

        G_tilde, x_mrt = _make_synthetic_scene()
        p_max = 0.5
        state = setup(G_tilde=G_tilde, x_init=x_mrt, signal_threshold=0.0, p_max=p_max)

        for _ in range(20):
            state, result = step(state)

        x_norm_sq = float(np.sum(np.abs(state["x"]) ** 2))
        assert x_norm_sq <= p_max + 1e-6

    def test_convergence_detected(self):
        from aegis.optim.mimo_peak import setup, step

        G_tilde, x_mrt = _make_synthetic_scene()
        state = setup(G_tilde=G_tilde, x_init=x_mrt, signal_threshold=0.0, p_max=1.0)

        for _ in range(200):
            state, result = step(state)
            if result.get("converged"):
                break

        assert result["converged"]
