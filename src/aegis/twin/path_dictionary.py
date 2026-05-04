"""Scene path dictionary calibration (paper §V.B).

The scene path dictionary D is a static catalogue of ray-traced paths between
the BS and a per-cell body position grid. Per-path complex amplitudes carry
residual error relative to the deployed channel (uncatalogued scatterers,
foliage, building material mismatches, weather). The deployed twin closes
this gap via uplink-CSI-based least-squares calibration of the dictionary
amplitudes for one served / cooperating UE at a time.

Per the paper, for user k the twin predicts the M-element BS-side channel as
``h_hat_k = sum_n alpha_n * a_n`` where ``a_n in C^M`` is the BS-side
departure steering vector for path n and ``alpha_n in C`` is the in-silico
per-path amplitude. Stacking columns gives an ``A in C^{M x N}`` design
matrix; the per-path scale factor ``beta in C^N`` is the LS solution to
``h_meas approx A @ beta``.

This module ships only the calibration LS itself. The full PathDictionary
(load/save/grid lookup) lives downstream of brief 08 (plaza assembly).
"""

from __future__ import annotations

import numpy as np


def calibrate_amplitudes(
    steering: np.ndarray,
    alpha_insilico: np.ndarray,
    h_meas: np.ndarray,
    ridge: float = 0.0,
) -> np.ndarray:
    """Per-path complex scale factors that align in-silico paths with measured CSI.

    Solves ``argmin_beta ||h_meas - A @ beta||^2 (+ ridge ||beta||^2)`` where
    ``A[:, n] = alpha_insilico[n] * steering[:, n]``. Returns the LS-optimal
    per-path scale ``beta in C^N``. Calibrated amplitudes for downstream Q
    construction are ``alpha_calibrated = beta * alpha_insilico``.

    Parameters
    ----------
    steering : (M, N) complex BS-side departure steering vectors per path.
    alpha_insilico : (N,) complex in-silico per-path amplitudes from the
        path dictionary (i.e. ray-traced reflection / transmission /
        polarisation product carried by D).
    h_meas : (M,) complex measured uplink CSI vector for the served UE.
    ridge : non-negative Tikhonov regularisation strength on beta. Default 0
        (plain LS). Useful when ``N >= M`` (under- or just-determined system)
        or when the steering matrix is ill-conditioned.

    Returns
    -------
    beta : (N,) complex per-path scale factors.
    """
    steering = np.asarray(steering)
    alpha_insilico = np.asarray(alpha_insilico)
    h_meas = np.asarray(h_meas)
    if steering.ndim != 2:
        raise ValueError(f"steering must be (M, N), got {steering.shape}")
    m, n = steering.shape
    if alpha_insilico.shape != (n,):
        raise ValueError(f"alpha_insilico must be (N,)={n}, got {alpha_insilico.shape}")
    if h_meas.shape != (m,):
        raise ValueError(f"h_meas must be (M,)={m}, got {h_meas.shape}")
    if ridge < 0:
        raise ValueError(f"ridge must be non-negative, got {ridge}")

    A = steering * alpha_insilico[None, :]
    if ridge == 0.0:
        beta, *_ = np.linalg.lstsq(A, h_meas, rcond=None)
        return beta
    AhA = A.conj().T @ A + ridge * np.eye(n)
    Ahb = A.conj().T @ h_meas
    return np.linalg.solve(AhA, Ahb)
