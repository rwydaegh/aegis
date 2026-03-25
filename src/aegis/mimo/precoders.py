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
