"""Coherent exposure: per-slot Q refresh and per-triangle Sab map.

Two cadences share one set of center-of-array paths:

- Per slot (cheap): the body's bulk translation is applied analytically by the
  Q translation phasor. ``build_static_gram`` is computed once per (body, pose,
  path-set); ``refresh_Q`` then gives Q for any translation, and the headline
  scalar exposure is ``x^H Q x``.
- At the recompute cadence (expensive): ``per_triangle_sab`` runs the coherent
  Sab kernel for the full per-triangle map.

Distinct sites are uncorrelated transmitters and sum in power.
"""

from __future__ import annotations

import numpy as np

from aegis.coherent.translation import (
    compute_static_path_gram,
    q_translate,
    translation_phasor,
)


def tissue_skin_params(freq_hz: float) -> tuple[complex, float]:
    """Complex refractive index and conductivity of skin at freq_hz."""
    from aegis.tissue.dielectric import TissueModel

    tissue = TissueModel.from_database("Skin", freq_hz)
    return tissue.n_complex, float(tissue.sigma)


def build_static_gram(body, center_paths, array, freq_hz, n_tilde=None, sigma=None):
    """Static path-correlation Gram for a body under one pose and path-set.

    ``center_paths`` are the center-of-array paths (one direction set, with
    per-element phase supplied by the array geometry). center_psi is folded
    with the per-direction element gain, mirroring expand_paths_to_array.
    """
    if n_tilde is None or sigma is None:
        n_tilde, sigma = tissue_skin_params(freq_hz)
    # Element pattern and steering act on the departure direction at the array
    # (differs from arrival for bounced paths); fall back to arrival for
    # producers without departure angles.
    k_dep = center_paths.k_hat_tx if getattr(center_paths, "k_hat_tx", None) is not None else center_paths.k_hat
    gain = array.element_gain(k_dep)  # (N,)
    psi_gained = center_paths.psi * gain[:, None]
    array_offsets = array.element_positions - array.reference_position
    M_static = compute_static_path_gram(
        normals=body.normals,
        centroids_0=body.centroids,
        areas=body.areas,
        center_k_hat=center_paths.k_hat,
        center_psi=psi_gained,
        array_offsets=array_offsets,
        n_tilde=n_tilde,
        sigma=sigma,
        freq_hz=freq_hz,
        center_k_hat_tx=k_dep,
    )
    return np.asarray(M_static)


def refresh_Q(M_static, center_k_hat, delta_t, freq_hz):
    """Q under a rigid body translation delta_t, via the phasor identity."""
    phi = translation_phasor(np.asarray(center_k_hat), np.asarray(delta_t, dtype=float), freq_hz)
    return np.asarray(q_translate(M_static, phi))


def scalar_exposure_w(Q, x) -> float:
    """Total absorbed power x^H Q x [W]. Real by Hermiticity of Q."""
    x = np.asarray(x, dtype=complex)
    Q = np.asarray(Q)
    return float(np.real(np.conj(x) @ Q @ x))


def per_triangle_sab(engine, body, paths, precoder, level=7):
    """Full per-triangle absorbed power density via the coherent Sab kernel."""
    result = engine.compute(body, paths, level=level, precoder=precoder)
    return result.sab


def exposure_with_Q(engine, body, paths, precoder, level=7):
    """Coherent result carrying both the per-triangle sab and the Q operator."""
    return engine.compute(body, paths, level=level, precoder=precoder)


def combine_sites_power(per_site_watts) -> float:
    """Distinct sites are uncorrelated transmitters: sum their absorbed power."""
    return float(np.sum(np.asarray(per_site_watts, dtype=float)))
