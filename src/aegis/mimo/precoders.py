"""Multi-user MIMO precoders.

Implements MRT, ZF, MMSE, and ZF with exposure scaling for K users
served by an M-element antenna array.

Design doc: section D1 (precoders), D4 (power allocation).
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class PrecoderMatrix:
    """Multi-user precoding matrix W = [w_1, ..., w_K].

    Attributes
    ----------
    W : (M_ant, K) complex precoding matrix.
    method : name of the precoding method used.
    total_power : sum of per-column powers ||w_k||^2.
    """

    W: np.ndarray = field(repr=False)
    method: str = ""

    def __post_init__(self) -> None:
        if self.W.ndim != 2:
            raise ValueError(f"W must be 2D, got shape {self.W.shape}")

    @property
    def n_elements(self) -> int:
        return self.W.shape[0]

    @property
    def n_users(self) -> int:
        return self.W.shape[1]

    @property
    def total_power(self) -> float:
        """Total transmit power ||W||_F^2 [W]."""
        return float(np.real(np.trace(self.W.conj().T @ self.W)))

    def per_user_power(self) -> np.ndarray:
        """Per-user transmit power ||w_k||^2, shape (K,)."""
        return np.real(np.sum(self.W.conj() * self.W, axis=0))

    def column(self, k: int) -> np.ndarray:
        """Return precoding vector w_k for user k."""
        return self.W[:, k]

    def __repr__(self) -> str:
        return (
            f"PrecoderMatrix(method={self.method!r}, M={self.n_elements}, K={self.n_users}, P={self.total_power:.4g} W)"
        )


def mrt(H: np.ndarray, P: float = 1.0) -> PrecoderMatrix:
    """Maximum ratio transmission (matched filter) precoder.

    w_k = sqrt(P/K) * h_k^* / ||h_k||

    Each user gets equal power P/K. Maximizes per-user SNR but ignores
    inter-user interference.

    Parameters
    ----------
    H : (K, M_ant) channel matrix. Row k is user k's channel vector.
    P : total transmit power budget [W].

    Returns
    -------
    PrecoderMatrix with ||W||_F^2 = P.
    """
    H = np.asarray(H, dtype=complex)
    if H.ndim == 1:
        H = H[np.newaxis, :]
    K, M = H.shape

    W = np.zeros((M, K), dtype=complex)
    p_per_user = P / K

    for k in range(K):
        h_conj = H[k].conj()
        norm = np.sqrt(float(np.real(np.vdot(h_conj, h_conj))))
        if norm < 1e-30:
            W[0, k] = np.sqrt(p_per_user)
        else:
            W[:, k] = np.sqrt(p_per_user) * h_conj / norm

    return PrecoderMatrix(W=W, method="mrt")


def zf(H: np.ndarray, P: float = 1.0) -> PrecoderMatrix:
    """Zero-forcing precoder.

    W = H^H (H H^H)^{-1}, Frobenius-normalized to ||W||_F^2 = P.

    Nulls inter-user interference: H @ W = alpha * I for some scalar alpha.
    Requires M_ant >= K. Falls back to MRT with a warning if M_ant < K.

    Parameters
    ----------
    H : (K, M_ant) channel matrix.
    P : total transmit power budget [W].

    Returns
    -------
    PrecoderMatrix with ||W||_F^2 = P.
    """
    H = np.asarray(H, dtype=complex)
    if H.ndim == 1:
        H = H[np.newaxis, :]
    K, M = H.shape

    if M < K:
        warnings.warn(
            f"ZF requires M_ant >= K ({M} < {K}), falling back to MRT",
            stacklevel=2,
        )
        return PrecoderMatrix(W=mrt(H, P).W, method="zf_fallback_mrt")

    # W_raw = H^H (H H^H)^{-1}
    G = H @ H.conj().T  # (K, K)

    # Check conditioning before inverting
    cond = np.linalg.cond(G)
    if not np.isfinite(cond) or cond > 1e12:
        warnings.warn(
            f"ZF: H H^H is ill-conditioned (cond={cond:.1e}), falling back to MRT",
            stacklevel=2,
        )
        return PrecoderMatrix(W=mrt(H, P).W, method="zf_fallback_mrt")

    try:
        G_inv = np.linalg.inv(G)
    except np.linalg.LinAlgError:
        warnings.warn(
            "ZF: H H^H is singular, falling back to MRT",
            stacklevel=2,
        )
        return PrecoderMatrix(W=mrt(H, P).W, method="zf_fallback_mrt")

    W_raw = H.conj().T @ G_inv  # (M, K)

    # Check for numerical issues (NaN, inf, or near-zero norm)
    frob = np.sqrt(float(np.real(np.trace(W_raw.conj().T @ W_raw))))
    if not np.isfinite(frob) or frob < 1e-30:
        warnings.warn("ZF: degenerate W, falling back to MRT", stacklevel=2)
        return PrecoderMatrix(W=mrt(H, P).W, method="zf_fallback_mrt")

    # Frobenius normalize: ||W||_F^2 = P
    W = W_raw * np.sqrt(P) / frob
    if not np.all(np.isfinite(W)):
        warnings.warn("ZF: NaN in W after normalization, falling back to MRT", stacklevel=2)
        return PrecoderMatrix(W=mrt(H, P).W, method="zf_fallback_mrt")

    return PrecoderMatrix(W=W, method="zf")


def mmse(
    H: np.ndarray,
    P: float = 1.0,
    alpha: float | None = None,
    snr_db: float = 20.0,
) -> PrecoderMatrix:
    """Regularized zero-forcing (MMSE) precoder.

    W = H^H (H H^H + alpha I)^{-1}, Frobenius-normalized to ||W||_F^2 = P.

    Trades interference suppression for noise resilience. Better conditioned
    than ZF when users have similar channel directions.

    Parameters
    ----------
    H : (K, M_ant) channel matrix.
    P : total transmit power budget [W].
    alpha : regularization parameter. If None, set to K/SNR_linear.
    snr_db : SNR in dB, used to compute alpha when alpha is None.

    Returns
    -------
    PrecoderMatrix with ||W||_F^2 = P.
    """
    H = np.asarray(H, dtype=complex)
    if H.ndim == 1:
        H = H[np.newaxis, :]
    K, M = H.shape

    if alpha is None:
        snr_linear = 10 ** (snr_db / 10)
        alpha = K / snr_linear

    G = H @ H.conj().T + alpha * np.eye(K, dtype=complex)  # (K, K)
    G_inv = np.linalg.inv(G)  # always invertible due to regularization
    W_raw = H.conj().T @ G_inv  # (M, K)

    # Frobenius normalize
    frob = np.sqrt(float(np.real(np.trace(W_raw.conj().T @ W_raw))))
    if frob < 1e-30:
        return PrecoderMatrix(W=mrt(H, P).W, method="mmse_fallback_mrt")

    W = W_raw * np.sqrt(P) / frob

    return PrecoderMatrix(W=W, method="mmse")


def zf_exposure_scaled(
    H: np.ndarray,
    Qs: list[np.ndarray],
    P: float = 1.0,
    P_abs_max: float = 0.02,
) -> PrecoderMatrix:
    """Zero-forcing precoder with per-user exposure scaling.

    Starts from ZF directions, then scales each column w_k down if
    the total exposure on any body exceeds P_abs_max.

    For body u, total absorbed power from all streams is:
        P_abs^(u) = sum_k w_k^H Q_u w_k

    If any user's body is over-exposed, the column causing the most
    exposure on that body is scaled down to satisfy the constraint.

    Parameters
    ----------
    H : (K, M_ant) channel matrix.
    Qs : list of K exposure operators, each (M_ant, M_ant) Hermitian PSD.
        Qs[u] is the exposure operator for body u.
    P : total transmit power budget [W].
    P_abs_max : maximum allowed absorbed power per body [W].

    Returns
    -------
    PrecoderMatrix with exposure constraints satisfied (when feasible).
    """
    H = np.asarray(H, dtype=complex)
    if H.ndim == 1:
        H = H[np.newaxis, :]
    K, M = H.shape

    if len(Qs) != K:
        raise ValueError(f"Need {K} exposure operators, got {len(Qs)}")

    # Start from ZF precoder
    W_zf = zf(H, P)
    W = W_zf.W.copy()

    # Iterative per-body scaling (converges in few iterations for typical scenarios)
    for _iteration in range(20):
        all_satisfied = True

        for u in range(K):
            Q_u = np.asarray(Qs[u], dtype=complex)

            # Total exposure on body u from all streams
            # P_abs^(u) = sum_k w_k^H Q_u w_k = trace(W^H Q_u W)
            p_abs_total = float(np.real(np.trace(W.conj().T @ Q_u @ W)))

            if p_abs_total <= P_abs_max:
                continue

            all_satisfied = False

            # Scale all columns proportionally to bring total to P_abs_max
            if p_abs_total > 0:
                scale = np.sqrt(P_abs_max / p_abs_total)
                W *= scale

        if all_satisfied:
            break

    return PrecoderMatrix(W=W, method="zf_exposure_scaled")
