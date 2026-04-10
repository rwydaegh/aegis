"""Inter-parameter correlation matrix builder for QuaDRiGa LSPs."""

from __future__ import annotations

import functools

import numpy as np
import scipy.linalg

# LSP order: DS(0), KF(1), SF(2), ASD(3), ASA(4), ESD(5), ESA(6), XPR(7)
LSP_NAMES = ("DS", "KF", "SF", "ASD", "ASA", "ESD", "ESA", "XPR")

_N = len(LSP_NAMES)

_CORR_KEY_MAP: dict[str, tuple[int, int]] = {
    "ds_kf": (0, 1),
    "ds_sf": (0, 2),
    "asD_ds": (0, 3),
    "asA_ds": (0, 4),
    "esD_ds": (0, 5),
    "esA_ds": (0, 6),
    "xpr_ds": (0, 7),
    "sf_kf": (1, 2),
    "asD_kf": (1, 3),
    "asA_kf": (1, 4),
    "esD_kf": (1, 5),
    "esA_kf": (1, 6),
    "xpr_kf": (1, 7),
    "asD_sf": (2, 3),
    "asA_sf": (2, 4),
    "esD_sf": (2, 5),
    "esA_sf": (2, 6),
    "xpr_sf": (2, 7),
    "asD_asA": (3, 4),
    "esD_asD": (3, 5),
    "esA_asD": (3, 6),
    "xpr_asd": (3, 7),
    "esD_asA": (4, 5),
    "esA_asA": (4, 6),
    "xpr_asa": (4, 7),
    "esD_esA": (5, 6),
    "xpr_esd": (5, 7),
    "xpr_esa": (6, 7),
}


@functools.lru_cache(maxsize=16)
def _build_cached(corr_key: tuple) -> tuple[np.ndarray, np.ndarray]:
    """Build from a hashable key of (key, value) pairs."""
    params = dict(corr_key)
    R = np.eye(_N)
    for key, (i, j) in _CORR_KEY_MAP.items():
        if key in params:
            val = float(params[key])
            R[i, j] = val
            R[j, i] = val

    # Ensure positive definiteness via eigendecomposition
    eigvals, eigvecs = np.linalg.eigh(R)
    clipped = np.maximum(eigvals, 1e-6)
    R = eigvecs @ np.diag(clipped) @ eigvecs.T

    # Renormalize diagonal to 1
    d = np.sqrt(np.diag(R))
    R = R / np.outer(d, d)

    L = scipy.linalg.cholesky(R, lower=True)

    return R, L


def build_correlation_matrix(params: dict) -> tuple[np.ndarray, np.ndarray]:
    """Build 8x8 inter-parameter correlation matrix and Cholesky factor.

    Returns (R, L) where R is the correlation matrix and L is lower-triangular
    Cholesky factor such that L @ L.T = R.
    """
    corr_key = tuple(sorted((k, float(params[k])) for k in _CORR_KEY_MAP if k in params))
    return _build_cached(corr_key)
