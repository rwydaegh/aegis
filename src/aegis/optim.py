"""Differentiable optimization helpers for exposure-aware design.

Functions return raw arrays (JAX when available) for use inside jax.grad
boundaries. All functions work with or without JAX installed.
"""

from __future__ import annotations

from aegis._array_backend import xp


def peak_exposure(sab):
    """Peak per-triangle S_ab [W/m^2].

    Differentiable via JAX subgradient of max.
    """
    return xp.max(sab)


def total_absorbed_power(sab, areas):
    """Total absorbed power P_abs = sum(S_ab * area) [W]."""
    return xp.sum(sab * areas)


def soft_peak_exposure(sab, temperature=100.0):
    """Smooth approximation to peak S_ab via log-sum-exp.

    Higher temperature gives a tighter bound but sharper gradients.
    temperature=100 gives < 0.1 W/m^2 error for typical inputs.
    """
    sab_max = xp.max(sab)
    shifted = temperature * (sab - sab_max)
    return sab_max + xp.log(xp.sum(xp.exp(shifted))) / temperature


def coherent_sab(G_tilde, x):
    """Per-triangle S_ab from body channel and precoding vector.

    S_ab(r) = ||G_tilde(r) @ x||^2

    This is the inner loop of beamforming optimization. Build G_tilde
    once with compute_body_channel(), then call this repeatedly while
    optimizing x.

    Parameters
    ----------
    G_tilde : (M, 3, M_ant) body-surface channel
    x : (M_ant,) complex precoding vector

    Returns
    -------
    sab : (M,) absorbed power density [W/m^2]
    """
    field = xp.einsum("mia,a->mi", G_tilde, x)
    sab = xp.real(xp.sum(xp.conj(field) * field, axis=1))
    return xp.maximum(sab, 0.0)
