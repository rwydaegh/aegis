"""Array backend shim: explicit JAX opt-in, NumPy fallback.

Usage in kernel files:
    from aegis._array_backend import xp, jit

    @jit
    def my_kernel(normals, k_hat, power, T0):
        mu = normals @ (-k_hat).T
        mu_plus = xp.maximum(mu, 0.0)
        return T0 * (mu_plus @ power)
"""

from __future__ import annotations

import os

import numpy as np

_BACKEND = os.environ.get("AEGIS_ARRAY_BACKEND", "numpy").strip().lower()

if _BACKEND not in {"numpy", "jax", "auto"}:
    raise ValueError(f"AEGIS_ARRAY_BACKEND must be one of 'numpy', 'jax', or 'auto', got {_BACKEND!r}")

if _BACKEND in {"jax", "auto"}:
    try:
        import jax

        jax.config.update("jax_enable_x64", True)
        import jax.numpy as jnp

        JAX_AVAILABLE = True
        xp = jnp
        jit = jax.jit
    except ImportError:
        if _BACKEND == "jax":
            raise
        JAX_AVAILABLE = False
        xp = np

        def jit(fn=None, **kwargs):
            """No-op jit decorator when JAX is unavailable."""
            if fn is None:
                return lambda f: f
            return fn
else:
    JAX_AVAILABLE = False
    xp = np

    def jit(fn=None, **kwargs):
        """No-op jit decorator when JAX is not installed."""
        if fn is None:
            return lambda f: f
        return fn


if JAX_AVAILABLE:
    from jax.scipy.special import erf as _erf
else:
    from scipy.special import erf as _erf

erf = _erf
