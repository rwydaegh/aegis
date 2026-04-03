"""Tests for optimization loop dispatcher."""

import threading

import numpy as np
import pytest


def test_run_mimo_peak():
    from aegis.optim.loop import run_optimization

    rng = np.random.default_rng(42)
    n_tri, n_ant = 50, 16
    G_tilde = (rng.standard_normal((n_tri, 3, n_ant)) + 1j * rng.standard_normal((n_tri, 3, n_ant))) * 0.01
    G_tilde[0, :, :] = 0.5 * np.ones((3, n_ant))
    x_init = np.conj(G_tilde[0, 0, :]) / np.linalg.norm(G_tilde[0, 0, :])

    config = {
        "mode": "mimo_peak",
        "G_tilde": G_tilde,
        "x_init": x_init,
        "p_max": 1.0,
        "signal_threshold": 0.0,
        "max_iters": 10,
    }

    results = list(run_optimization(config, cancel_event=threading.Event()))
    assert len(results) >= 2
    assert all("sab" in r for r in results if not r.get("done"))
    assert all("iter" in r for r in results)


def test_cancellation():
    from aegis.optim.loop import run_optimization

    rng = np.random.default_rng(42)
    G_tilde = (rng.standard_normal((50, 3, 16)) + 1j * rng.standard_normal((50, 3, 16))) * 0.01
    x_init = np.ones(16, dtype=complex) / 4

    cancel = threading.Event()
    cancel.set()

    config = {
        "mode": "mimo_peak",
        "G_tilde": G_tilde,
        "x_init": x_init,
        "p_max": 1.0,
        "max_iters": 100,
    }

    results = list(run_optimization(config, cancel_event=cancel))
    assert len(results) <= 1
    if results:
        assert results[-1].get("cancelled") or results[-1].get("done")


def test_unknown_mode_raises():
    from aegis.optim.loop import run_optimization

    with pytest.raises(ValueError, match="Unknown optimization mode"):
        list(run_optimization({"mode": "bogus"}, cancel_event=threading.Event()))


def test_tilt_power_T0_passthrough():
    """T0 must flow from config through loop to the optimizer state."""
    from aegis.optim.loop import run_optimization
    from aegis.paths import PropagationPaths

    rng = np.random.default_rng(42)
    k_hat = rng.standard_normal((20, 3))
    k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
    paths = PropagationPaths.from_powers(k_hat=k_hat, power=rng.uniform(0.1, 1.0, 20))

    config = {
        "mode": "tilt_power",
        "paths": paths,
        "normals": np.tile([0, 0, 1], (50, 1)).astype(np.float64),
        "antenna_direction": np.array([0.0, 0.0, -1.0]),
        "T0": 0.44,
        "max_iters": 3,
    }

    results = list(run_optimization(config, cancel_event=threading.Event()))
    assert len(results) >= 1

    # Verify T0 was applied: run again with T0=1.0 and compare
    config_no_T0 = {**config, "T0": 1.0}
    results_no_T0 = list(run_optimization(config_no_T0, cancel_event=threading.Event()))

    peak_with_T0 = results[0]["stats"]["peak_sab"]
    peak_without_T0 = results_no_T0[0]["stats"]["peak_sab"]
    assert peak_with_T0 < peak_without_T0 * 0.5  # T0=0.44 should give ~44% of T0=1.0
