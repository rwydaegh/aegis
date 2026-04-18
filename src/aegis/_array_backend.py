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
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar, overload

import numpy as np

# For type-checking, present xp as the numpy module. At runtime xp may be
# jax.numpy; jax.numpy is API-compatible with numpy for the ops kernels use,
# so the numpy type is accurate enough to unblock strict type checking.
if TYPE_CHECKING:
    import numpy as _xp_type

_F = TypeVar("_F", bound=Callable[..., Any])

_BACKEND = os.environ.get("AEGIS_ARRAY_BACKEND", "numpy").strip().lower()

if _BACKEND not in {"numpy", "jax", "auto"}:
    raise ValueError(f"AEGIS_ARRAY_BACKEND must be one of 'numpy', 'jax', or 'auto', got {_BACKEND!r}")

JAX_AVAILABLE: bool

if TYPE_CHECKING:
    # Static view: jit accepts a callable (or None for kwarg-form) and returns
    # a callable with the same signature. Runtime uses jax.jit when available.
    @overload
    def jit(fn: _F, **kwargs: Any) -> _F: ...
    @overload
    def jit(fn: None = None, **kwargs: Any) -> Callable[[_F], _F]: ...
    def jit(fn: _F | None = None, **kwargs: Any) -> _F | Callable[[_F], _F]: ...


if _BACKEND in {"jax", "auto"}:
    try:
        import jax

        jax.config.update("jax_enable_x64", True)
        import jax.numpy as jnp

        JAX_AVAILABLE = True
        xp = jnp
        if not TYPE_CHECKING:
            jit = jax.jit
    except ImportError:
        if _BACKEND == "jax":
            raise
        JAX_AVAILABLE = False
        xp = np

        if not TYPE_CHECKING:

            def jit(fn=None, **kwargs):
                """No-op jit decorator when JAX is unavailable."""
                if fn is None:
                    return lambda f: f
                return fn
else:
    JAX_AVAILABLE = False
    xp = np

    if not TYPE_CHECKING:

        def jit(fn=None, **kwargs):
            """No-op jit decorator when JAX is not installed."""
            if fn is None:
                return lambda f: f
            return fn


if JAX_AVAILABLE:
    from jax.scipy.special import erf as _erf
else:
    from scipy.special import erf as _erf  # pyright: ignore[reportAssignmentType]

erf: Any = _erf

# Type-checker view: xp is numpy. Runtime behavior unchanged.
if TYPE_CHECKING:
    xp = _xp_type
