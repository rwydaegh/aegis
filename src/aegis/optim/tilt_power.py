"""Tilt/power optimizer: maximize TX power while staying ICNIRP compliant.

Joint gradient descent on (tilt_deg, log_power_dbm) with a quadratic
penalty for ICNIRP violation:

    loss = -power_dbm + lambda * max(0, peak_sab - limit)^2

Paths are cached from the initial RT call. Only the radiation pattern
weighting changes per iteration (cos^n pattern applied to path powers).
"""

from __future__ import annotations

from collections import deque
from typing import Any

import numpy as np


def _cos_n_pattern(k_hat: np.ndarray, boresight: np.ndarray, n: float = 3.0) -> np.ndarray:
    """Cosine^n radiation pattern gain. Returns (N_paths,) in [0, 1]."""
    cos_angle = np.clip(k_hat @ boresight, 0, 1)
    return cos_angle**n


def _rotate_boresight(antenna_direction: np.ndarray, tilt_deg: float) -> np.ndarray:
    """Tilt the antenna boresight downward by tilt_deg degrees.

    Rotation around the horizontal axis perpendicular to the antenna
    direction projected onto the XY plane.
    """
    tilt_rad = np.radians(tilt_deg)
    d_xy = antenna_direction[:2]
    norm_xy = np.linalg.norm(d_xy)
    axis = np.array([1.0, 0.0, 0.0]) if norm_xy < 1e-10 else np.array([-d_xy[1], d_xy[0], 0.0]) / norm_xy

    # Rodrigues rotation
    k = axis
    cos_t = np.cos(tilt_rad)
    sin_t = np.sin(tilt_rad)
    v = antenna_direction
    rotated = v * cos_t + np.cross(k, v) * sin_t + k * np.dot(k, v) * (1 - cos_t)
    norm = np.linalg.norm(rotated)
    if norm < 1e-12:
        return antenna_direction
    return rotated / norm


def _evaluate(state: dict, tilt_deg: float, power_dbm: float):
    """Compute S_ab for given tilt and power. Returns (sab, peak_sab)."""
    boresight = _rotate_boresight(state["antenna_direction"], tilt_deg)
    gain = _cos_n_pattern(state["k_hat"], boresight, state["pattern_exponent"])
    power_linear = 10 ** ((power_dbm - 60) / 10)
    weighted = state["base_power"] * gain * power_linear
    cos_inc = np.maximum((-state["k_hat"]) @ state["normals"].T, 0)
    sab = weighted @ cos_inc
    return sab, float(np.max(sab))


def setup(
    *,
    paths,
    normals: np.ndarray,
    antenna_direction: np.ndarray,
    tilt_init_deg: float = 0.0,
    power_init_dbm: float = 60.0,
    icnirp_limit: float = 20.0,
    lr: float = 0.1,
    penalty_lambda: float = 10.0,
    pattern_exponent: float = 3.0,
) -> dict[str, Any]:
    """Initialize tilt/power optimizer state.

    Parameters
    ----------
    paths : PropagationPaths from the initial RT call
    normals : (M, 3) body surface normals
    antenna_direction : (3,) unit vector from antenna toward body
    tilt_init_deg : initial downtilt in degrees
    power_init_dbm : initial TX power in dBm
    icnirp_limit : S_ab limit in W/m^2
    lr : learning rate
    penalty_lambda : penalty weight for ICNIRP violation
    pattern_exponent : exponent n for cos^n radiation pattern
    """
    base_power = np.array(paths.power, dtype=np.float64)
    k_hat = np.array(paths.k_hat, dtype=np.float64)

    state = {
        "base_power": base_power,
        "k_hat": k_hat,
        "normals": normals,
        "antenna_direction": np.asarray(antenna_direction, dtype=np.float64),
        "tilt_deg": tilt_init_deg,
        "power_dbm": power_init_dbm,
        "icnirp_limit": icnirp_limit,
        "lr": lr,
        "penalty_lambda": penalty_lambda,
        "pattern_exponent": pattern_exponent,
        "iter": 0,
        "history": deque(maxlen=10),
    }

    _, peak = _evaluate(state, tilt_init_deg, power_init_dbm)
    state["objective"] = peak
    return state


def step(state: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """One optimization step. Returns (updated_state, result_dict)."""
    tilt = state["tilt_deg"]
    pwr = state["power_dbm"]
    limit = state["icnirp_limit"]
    lr = state["lr"]
    lam = state["penalty_lambda"]
    it = state["iter"] + 1

    eps_tilt = 0.1
    eps_pwr = 0.1

    _, peak_0 = _evaluate(state, tilt, pwr)
    _, peak_t = _evaluate(state, tilt + eps_tilt, pwr)
    _, peak_p = _evaluate(state, tilt, pwr + eps_pwr)

    def loss(peak, power_dbm):
        violation = max(0, peak - limit)
        return -power_dbm + lam * violation**2

    l0 = loss(peak_0, pwr)
    lt = loss(peak_t, pwr)
    lp = loss(peak_p, pwr + eps_pwr)

    grad_tilt = (lt - l0) / eps_tilt
    grad_pwr = (lp - l0) / eps_pwr

    tilt = tilt - lr * grad_tilt
    pwr = pwr - lr * grad_pwr

    tilt = float(np.clip(tilt, 0, 90))
    pwr = float(np.clip(pwr, 0, 90))

    sab, peak = _evaluate(state, tilt, pwr)
    obj = loss(peak, pwr)

    history = state["history"]
    history.append(obj)
    converged = False
    if len(history) >= 6:
        old = history[-6]
        if abs(old) > 1e-12 and abs(old - obj) / (abs(old) + 1e-30) < 0.001:
            converged = True

    compliant = peak <= limit

    new_state = {
        **state,
        "tilt_deg": tilt,
        "power_dbm": pwr,
        "objective": obj,
        "iter": it,
        "history": history,
    }
    result = {
        "iter": it,
        "objective": obj,
        "grad_norm": float(np.sqrt(grad_tilt**2 + grad_pwr**2)),
        "sab": np.asarray(sab, dtype=np.float32),
        "params": {"tilt_deg": tilt, "power_dbm": pwr},
        "stats": {"peak_sab": peak, "compliant": compliant},
        "converged": converged,
        "constraint_satisfied": compliant,
    }
    return new_state, result
