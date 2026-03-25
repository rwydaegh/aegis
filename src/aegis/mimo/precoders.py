"""Multi-user MIMO precoders.

All precoders take H: (K, M_ant) channel matrix and return W: (M_ant, K)
precoding matrix. Convention: ||W||_F^2 = P (total transmit power).

Design doc: sections D1-D4.
"""

from __future__ import annotations

import numpy as np


def mrt(H: np.ndarray, P: float = 1.0) -> np.ndarray:
    """Maximum ratio transmission (per-user matched filter).

    w_k = sqrt(P/K) * conj(h_k) / ||h_k||

    Returns W: (M_ant, K). Each column has power P/K.
    """
    H = np.asarray(H, dtype=complex)
    if H.ndim == 1:
        H = H.reshape(1, -1)
    K = H.shape[0]
    W_conj = H.conj().T  # (M, K)
    norms = np.linalg.norm(W_conj, axis=0, keepdims=True)  # (1, K)
    norms = np.maximum(norms, 1e-30)
    return np.sqrt(P / K) * W_conj / norms


def zf(H: np.ndarray, P: float = 1.0) -> np.ndarray:
    """Zero-forcing: W_raw = H^H @ inv(H @ H^H), normalized to ||W||_F^2 = P.

    Requires M_ant >= K.
    """
    H = np.asarray(H, dtype=complex)
    if H.ndim == 1:
        H = H.reshape(1, -1)
    K, M = H.shape
    if M < K:
        msg = f"M_ant ({M}) must be >= K ({K}) for ZF precoding"
        raise ValueError(msg)
    HHH = H @ H.conj().T
    W_raw = H.conj().T @ np.linalg.inv(HHH)
    frob = np.sqrt(float(np.real(np.trace(W_raw.conj().T @ W_raw))))
    if frob < 1e-30:
        return np.zeros((M, K), dtype=complex)
    return W_raw * np.sqrt(P) / frob
