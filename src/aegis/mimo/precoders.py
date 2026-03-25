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
    X = np.linalg.solve(HHH, H)  # (K, M), solves HHH @ X = H
    W_raw = X.conj().T  # (M, K)
    frob = np.sqrt(float(np.real(np.trace(W_raw.conj().T @ W_raw))))
    if frob < 1e-30:
        return np.zeros((M, K), dtype=complex)
    return W_raw * np.sqrt(P) / frob


def mmse(H: np.ndarray, P: float = 1.0, noise_power: float = 0.01) -> np.ndarray:
    """MMSE: W_raw = H^H @ inv(H @ H^H + alpha * I), normalized to ||W||_F^2 = P."""
    H = np.asarray(H, dtype=complex)
    if H.ndim == 1:
        H = H.reshape(1, -1)
    K, M = H.shape
    HHH = H @ H.conj().T
    X = np.linalg.solve(HHH + noise_power * np.eye(K), H)  # (K, M)
    W_raw = X.conj().T  # (M, K)
    frob = np.sqrt(float(np.real(np.trace(W_raw.conj().T @ W_raw))))
    if frob < 1e-30:
        return np.zeros((M, K), dtype=complex)
    return W_raw * np.sqrt(P) / frob


def zf_exposure(
    H: np.ndarray,
    Q_list: list[np.ndarray],
    P_abs_max: float,
    P: float = 1.0,
) -> np.ndarray:
    """ZF directions, per-column power scaled to satisfy exposure constraints.

    Uses a conservative per-column budget: each column k is scaled so that
    w_k^H Q_u w_k <= P_abs_max / K for every user u. This guarantees the
    joint constraint sum_k w_k^H Q_u w_k <= P_abs_max but may be overly
    conservative when columns have unequal exposure contributions.
    """
    H = np.asarray(H, dtype=complex)
    if H.ndim == 1:
        H = H.reshape(1, -1)
    K, M = H.shape
    W_zf = zf(H, P=P)

    # Extract unit directions from ZF columns
    norms = np.linalg.norm(W_zf, axis=0, keepdims=True)
    norms = np.maximum(norms, 1e-30)
    directions = W_zf / norms

    # Start from ZF's per-column power allocation
    gamma_sq = np.real(np.einsum("ij,ij->j", W_zf.conj(), W_zf))

    # Scale down per-column power to satisfy exposure constraints
    for k in range(K):
        d_k = directions[:, k]
        for Q_u in Q_list:
            dQd = float(np.real(np.vdot(d_k, Q_u @ d_k)))
            if dQd > 1e-30:
                max_gamma_sq = P_abs_max / (K * dQd)
                gamma_sq[k] = min(gamma_sq[k], max_gamma_sq)

    return directions * np.sqrt(gamma_sq)[np.newaxis, :]


def compute_precoder(
    H: np.ndarray,
    precoder_type: str = "zf",
    P: float = 1.0,
    noise_power: float = 0.01,
    Q_list: list[np.ndarray] | None = None,
    P_abs_max: float | None = None,
) -> np.ndarray:
    """Dispatch to precoder by name. Returns W: (M_ant, K)."""
    if precoder_type == "mrt":
        return mrt(H, P=P)
    if precoder_type == "zf":
        return zf(H, P=P)
    if precoder_type == "mmse":
        return mmse(H, P=P, noise_power=noise_power)
    if precoder_type == "zf_exposure":
        if Q_list is None or P_abs_max is None:
            msg = "zf_exposure requires Q_list and P_abs_max"
            raise ValueError(msg)
        return zf_exposure(H, Q_list, P_abs_max=P_abs_max, P=P)
    msg = f"Unknown precoder type: {precoder_type!r}"
    raise ValueError(msg)
