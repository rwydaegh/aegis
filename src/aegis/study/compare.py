"""Deterministic vs stochastic exposure comparison primitives.

The study's headline question is whether the geometry-blind stochastic 3GPP
TR 38.901 channel reproduces the ray-traced (deterministic) population exposure.
This module holds the comparison core: the P_LOS-weighted LOS/NLOS exposure
blend and the paired, scale-invariant agreement metric.

The blend is at the exposure-operator level. Absorbed power is x^H Q x, linear in
Q, so the statistical mixture E[Sab] = p*E[Sab|LOS] + (1-p)*E[Sab|NLOS] is the
convex blend of the two operators, Q = p*Q_LOS + (1-p)*Q_NLOS. (LOS and NLOS
cluster sets have different path counts, so the blend is done at Q, which is
always M_ant x M_ant, not at the path-correlation gram.)
"""

from __future__ import annotations

import numpy as np

from aegis.study.exposure import build_static_gram, refresh_Q, scalar_exposure_w


def blend_Q(q_los, q_nlos, p_los_val):
    """Convex P_LOS blend of two exposure operators: p*Q_LOS + (1-p)*Q_NLOS."""
    p = float(np.clip(p_los_val, 0.0, 1.0))
    q = p * np.asarray(q_los) + (1.0 - p) * np.asarray(q_nlos)
    return 0.5 * (q + np.conj(q).T)  # keep Hermitian against round-off


def stochastic_Q(body, center_los, center_nlos, array, freq_hz, p_los_val):
    """Blended exposure operator from a LOS and an NLOS coherent 38.901 channel.

    Each channel is a center-of-array path set (from generate_coherent_channel);
    its gram is built and evaluated at zero translation to get Q, then the two
    are P_LOS-blended.
    """
    q_los = refresh_Q(build_static_gram(body, center_los, array, freq_hz), center_los.k_hat, np.zeros(3), freq_hz)
    q_nlos = refresh_Q(build_static_gram(body, center_nlos, array, freq_hz), center_nlos.k_hat, np.zeros(3), freq_hz)
    return blend_Q(np.asarray(q_los), np.asarray(q_nlos), p_los_val)


def stochastic_exposure_w(body, center_los, center_nlos, array, freq_hz, p_los_val, x) -> float:
    """Per-person stochastic absorbed power x^H Q x with the P_LOS-blended Q."""
    return scalar_exposure_w(stochastic_Q(body, center_los, center_nlos, array, freq_hz, p_los_val), x)


def paired_db_error(det_w, stoch_w, floor=1e-18):
    """Paired, scale-invariant error per person: 10 log10(stoch / det) [dB].

    Magnitude divides out, so high-exposure cities do not dominate. Values are
    clamped at ``floor`` to keep the log finite for uncovered (zero-exposure)
    pedestrians.
    """
    det = np.maximum(np.asarray(det_w, dtype=float), floor)
    stoch = np.maximum(np.asarray(stoch_w, dtype=float), floor)
    return 10.0 * np.log10(stoch / det)
