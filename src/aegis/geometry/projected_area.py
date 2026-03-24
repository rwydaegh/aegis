"""Projected area A_perp(k_hat) lookup table.

Extracted from scripts/compute_projected_area_table.py.
"""

from __future__ import annotations

import numpy as np

_fibonacci_sphere_cache: dict[int, np.ndarray] = {}
_FIBONACCI_CACHE_MAX: int = 32


def fibonacci_sphere(n: int) -> np.ndarray:
    """Deterministic near-uniform sampling on S^2 via golden spiral.

    Returns k_hat of shape (n, 3).
    """
    if n <= 0:
        raise ValueError("n must be positive")

    cached = _fibonacci_sphere_cache.get(n)
    if cached is not None:
        return cached

    i = np.arange(n, dtype=np.float64)
    golden_ratio = (1.0 + np.sqrt(5.0)) / 2.0

    z = 1.0 - 2.0 * (i + 0.5) / n
    r = np.sqrt(np.maximum(0.0, 1.0 - z * z))
    phi = 2.0 * np.pi * i / golden_ratio

    x = r * np.cos(phi)
    y = r * np.sin(phi)
    k_hat = np.stack([x, y, z], axis=1)
    k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
    out = np.array(k_hat, copy=True)
    out.flags.writeable = False
    while len(_fibonacci_sphere_cache) >= _FIBONACCI_CACHE_MAX:
        _fibonacci_sphere_cache.pop(next(iter(_fibonacci_sphere_cache)))
    _fibonacci_sphere_cache[n] = out
    return out


def compute_projected_area(
    normals: np.ndarray,
    areas: np.ndarray,
    k_hat: np.ndarray,
    chunk_dirs: int = 128,
) -> np.ndarray:
    """Compute A_perp(k_hat) = sum_j a_j * [n_j . (-k_hat)]_+ for each direction.

    Parameters
    ----------
    normals : (M, 3) unit triangle normals
    areas : (M,) triangle areas
    k_hat : (N, 3) incident directions (unit vectors)
    chunk_dirs : chunk size for memory-bounded BLAS

    Returns
    -------
    A_perp : (N,) projected areas
    """
    normals = np.asarray(normals, dtype=np.float64)
    areas = np.asarray(areas, dtype=np.float64)
    k_hat = np.asarray(k_hat, dtype=np.float64)

    n_dirs = k_hat.shape[0]
    A_perp = np.zeros(n_dirs, dtype=np.float64)
    minus_k = -k_hat

    for start in range(0, n_dirs, chunk_dirs):
        end = min(start + chunk_dirs, n_dirs)
        k_chunk = minus_k[start:end]  # (C, 3)
        mu = normals @ k_chunk.T  # (M, C)
        mu_pos = np.maximum(0.0, mu)
        A_perp[start:end] = areas @ mu_pos  # (C,)

    return A_perp
