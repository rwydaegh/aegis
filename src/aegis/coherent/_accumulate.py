"""Shared scatter-add accumulation for coherent channel matrices.

Both field_channel.py and body_channel.py need to accumulate weighted
contributions by antenna element index. This module provides the NumPy
and JAX implementations in one place.
"""

from __future__ import annotations

import numpy as np

from aegis._array_backend import JAX_AVAILABLE, xp


def _accumulate_by_element_numpy(weighted, element_index, M, n_elements):
    """NumPy: vectorized scatter-add using np.add.at."""
    G = np.zeros((M, 3, n_elements), dtype=complex)
    weighted_t = np.transpose(weighted, (0, 2, 1))  # (M, 3, N)
    np.add.at(G, (slice(None), slice(None), element_index), weighted_t)
    return G


def _accumulate_by_element_jax(weighted, element_index, M, n_elements):
    """JAX: use scatter-add for JIT compatibility."""
    import jax.numpy as jnp

    G = jnp.zeros((M, 3, n_elements), dtype=complex)
    weighted_t = jnp.transpose(weighted, (0, 2, 1))  # (M, 3, N)
    G = G.at[:, :, element_index].add(weighted_t)
    return G


def accumulate_by_element(weighted, element_index, M, n_elements):
    """Accumulate weighted contributions by antenna element index.

    Parameters
    ----------
    weighted : (M, N, 3) complex
        Per-triangle, per-path weighted contributions.
    element_index : (N,) int
        Antenna element index for each path.
    M : int
        Number of triangles.
    n_elements : int
        Number of antenna elements.

    Returns
    -------
    G : (M, 3, n_elements) complex
        Accumulated channel matrix.
    """
    if JAX_AVAILABLE:
        return _accumulate_by_element_jax(weighted, element_index, M, n_elements)
    G = _accumulate_by_element_numpy(np.asarray(weighted), np.asarray(element_index), M, n_elements)
    return xp.asarray(G)
