"""MIMO peak S_ab optimizer via projected gradient descent.

Minimizes soft_peak_exposure(coherent_sab(G_tilde, x)) subject to
||x||^2 <= p_max. Uses Adam optimizer with projection onto the power
constraint after each step.
"""

from __future__ import annotations

from collections import deque
from typing import Any

import numpy as np

from aegis._array_backend import JAX_AVAILABLE
from aegis.optim import coherent_sab, soft_peak_exposure

if JAX_AVAILABLE:
    import jax
    import jax.numpy as jnp

    _JAX = True
else:
    _JAX = False


def setup(
    *,
    G_tilde: np.ndarray,
    x_init: np.ndarray,
    signal_threshold: float = 0.0,
    p_max: float = 1.0,
    lr: float = 0.005,
    temperature: float = 100.0,
) -> dict[str, Any]:
    """Initialize optimizer state."""
    M_ant = G_tilde.shape[2]
    if x_init.shape != (M_ant,):
        raise ValueError(f"x_init shape {x_init.shape} must be ({M_ant},)")

    x = np.array(x_init, dtype=complex)
    norm_sq = float(np.sum(np.abs(x) ** 2))
    if norm_sq > p_max:
        x = x * np.sqrt(p_max / norm_sq)

    sab = coherent_sab(G_tilde, x)
    obj = float(soft_peak_exposure(sab, temperature=temperature))

    return {
        "G_tilde": G_tilde,
        "x": x,
        "p_max": p_max,
        "signal_threshold": signal_threshold,
        "lr": lr,
        "temperature": temperature,
        "objective": obj,
        "iter": 0,
        "m": np.zeros(M_ant, dtype=complex),
        "v_adam": np.zeros(M_ant, dtype=np.float64),
        "history": deque(maxlen=10),
    }


def _project_power(x: np.ndarray, p_max: float) -> np.ndarray:
    """Project x onto ||x||^2 <= p_max."""
    norm_sq = float(np.sum(np.abs(x) ** 2))
    if norm_sq > p_max:
        return x * np.sqrt(p_max / norm_sq)
    return x


def _compute_gradient(G_tilde, x, temperature):
    """Gradient of soft_peak_exposure(coherent_sab(G_tilde, x)) w.r.t. x."""
    if _JAX:
        G_j = jnp.asarray(G_tilde)
        x_j = jnp.asarray(x)

        def loss_fn(x_var):
            # Keep the differentiated path fully in JAX. The generic helpers
            # use the repository backend shim, which may still point at NumPy
            # even when JAX is installed.
            field = jnp.einsum("mia,a->mi", G_j, x_var)
            sab = jnp.maximum(jnp.real(jnp.sum(jnp.conj(field) * field, axis=1)), 0.0)
            sab_max = jnp.max(sab)
            shifted = temperature * (sab - sab_max)
            return sab_max + jnp.log(jnp.sum(jnp.exp(shifted))) / temperature

        grad = jax.grad(loss_fn)(x_j)
        return np.array(grad)

    # Finite-difference fallback
    eps = 1e-6
    grad = np.zeros_like(x)
    f0 = float(soft_peak_exposure(coherent_sab(G_tilde, x), temperature=temperature))
    for i in range(len(x)):
        x_p = x.copy()
        x_p[i] += eps
        f_r = float(soft_peak_exposure(coherent_sab(G_tilde, x_p), temperature=temperature))
        x_p = x.copy()
        x_p[i] += 1j * eps
        f_i = float(soft_peak_exposure(coherent_sab(G_tilde, x_p), temperature=temperature))
        grad[i] = (f_r - f0) / eps + 1j * (f_i - f0) / eps
    return grad


def step(state: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run one optimizer step. Returns (updated_state, result_dict)."""
    G_tilde = state["G_tilde"]
    x = state["x"]
    p_max = state["p_max"]
    lr = state["lr"]
    temp = state["temperature"]
    it = state["iter"] + 1

    grad = _compute_gradient(G_tilde, x, temp)

    beta1, beta2, eps_adam = 0.9, 0.999, 1e-8
    m = beta1 * state["m"] + (1 - beta1) * grad
    v_adam = beta2 * state["v_adam"] + (1 - beta2) * np.abs(grad) ** 2
    m_hat = m / (1 - beta1**it)
    v_hat = v_adam / (1 - beta2**it)
    x = x - lr * m_hat / (np.sqrt(v_hat) + eps_adam)

    x = _project_power(x, p_max)

    sab = np.array(coherent_sab(G_tilde, x))
    obj = float(soft_peak_exposure(sab, temperature=temp))
    grad_norm = float(np.sqrt(np.sum(np.abs(grad) ** 2)))
    peak_sab = float(np.max(sab)) if sab.size > 0 else 0.0

    history = state["history"]
    history.append(obj)
    converged = False
    if len(history) >= 6:
        old = history[-6]
        if old > 0 and abs(old - obj) / old < 0.001:
            converged = True

    new_state = {
        **state,
        "x": x,
        "m": m,
        "v_adam": v_adam,
        "objective": obj,
        "iter": it,
        "history": history,
    }
    result = {
        "iter": it,
        "objective": obj,
        "grad_norm": grad_norm,
        "sab": sab,
        "params": {
            "x_real": x.real.tolist(),
            "x_imag": x.imag.tolist(),
            "power": float(np.sum(np.abs(x) ** 2)),
        },
        "stats": {"peak_sab": peak_sab, "peaks": {"sab": peak_sab}},
        "converged": converged,
    }
    return new_state, result
