"""Array backend shim: JAX when available, NumPy fallback.

Usage in kernel files:
    from aegis._array_backend import xp, jit

    @jit
    def my_kernel(normals, k_hat, power, T0):
        mu = normals @ (-k_hat).T
        mu_plus = xp.maximum(mu, 0.0)
        return T0 * (mu_plus @ power)
"""

from __future__ import annotations

import numpy as np

try:
    import jax

    jax.config.update("jax_enable_x64", True)
    import jax.numpy as jnp

    JAX_AVAILABLE = True
    xp = jnp
    jit = jax.jit
except ImportError:
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
