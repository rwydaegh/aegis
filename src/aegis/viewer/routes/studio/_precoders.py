"""Precoder synthesis for the Coherent Exposure Studio.

Builds the transmit precoding vector ``x`` for each beam kind from the loaded
ray pack. All kinds are matched-power (``||x||^2 = power``) except ``ecbf``,
whose QCQP optimum may sit in the power-slack regime (``||x||^2 <= power``)
when the absorption constraint binds.

``ecbf`` is built by :func:`build_ecbf_from_q` from the precomputed exposure
operator Q served on disk (``data/studio/qop/``); the old request-time full-body
tissue-channel build (~8 min) is gone. The decohered baseline is a field-domain
inter-direction phase scramble that cannot be a per-element precoder, so the
canonical path lives in ``_slice.decohered_field_source``; the ``decohered``
branch here keeps a per-element analogue as a working fallback only.

Fork-free: imports only ``aegis.hotspot``/``aegis.coherent`` and numpy.
"""

from __future__ import annotations

import numpy as np

# Random-phase precoders use a fixed seed so a given scene is reproducible.
_UNFOCUSED_SEED = 0xC0FFEE
_DECOHERE_SEED = 0xBEEF
# ECBF absorbed-power budget as a fraction of the MRT-induced absorption,
# matching ECBF_BUDGET_FRAC in scripts/studio_precompute.py.
_ECBF_BUDGET_FRAC = 0.5
# Decoy focus offset along world +z [m].
_DECOY_OFFSET = np.array([0.0, 0.0, 0.06])


def _mrt(focus, k_hat, psi, element_index, freq_hz, n_elements, ue_rx, power):
    from aegis.hotspot import channel_at

    h = channel_at(focus, k_hat, psi, element_index, freq_hz, n_elements, rx_response=ue_rx)
    return np.sqrt(power) * np.conj(h) / np.linalg.norm(h)


def build_precoder(
    kind: str,
    paths: tuple[np.ndarray, np.ndarray, np.ndarray, int],
    focus_xyz,
    freq_hz: float,
    power: float = 1.0,
) -> np.ndarray:
    """Build the precoder ``x`` of shape ``(n_elements,)`` for ``kind``.

    Kinds: ``mrt``, ``unfocused``, ``decohered``, ``decoy``, ``worstcase``.
    ``ecbf`` is not built here: call :func:`build_ecbf_from_q` with the
    precomputed exposure operator Q. The ``decohered`` kind returns a
    per-element phase-scramble analogue (a working fallback); the canonical
    decohered baseline is the field-domain scramble in
    ``_slice.decohered_field_source``.
    """
    from aegis.hotspot import field_channel_at, local_max_intensity, make_rx_response

    k_hat, psi, element_index, n_elements = paths
    focus = np.asarray(focus_xyz, dtype=float)
    ue_rx = make_rx_response("dipole", freq_hz)

    if kind == "mrt":
        return _mrt(focus, k_hat, psi, element_index, freq_hz, n_elements, ue_rx, power)

    if kind == "unfocused":
        rng = np.random.default_rng(_UNFOCUSED_SEED)
        phases = rng.uniform(0.0, 2 * np.pi, n_elements)
        return np.sqrt(power / n_elements) * np.exp(1j * phases)

    if kind == "decohered":
        # Per-element phase scramble of MRT: per-element power (hence the
        # regional illumination) is preserved while the coherent focus is
        # destroyed. The canonical decohered baseline scrambles inter-direction
        # phase AFTER collapse (see _slice.decohered_field_source); that cannot
        # be a per-element precoder, so this is a fallback for x-only callers.
        x_mrt = _mrt(focus, k_hat, psi, element_index, freq_hz, n_elements, ue_rx, power)
        rng = np.random.default_rng(_DECOHERE_SEED)
        phases = rng.uniform(0.0, 2 * np.pi, n_elements)
        return np.abs(x_mrt) * np.exp(1j * phases)

    if kind == "decoy":
        decoy_focus = focus + _DECOY_OFFSET
        return _mrt(decoy_focus, k_hat, psi, element_index, freq_hz, n_elements, ue_rx, power)

    if kind == "worstcase":
        g = field_channel_at(focus, k_hat, psi, element_index, freq_hz, n_elements)
        _lam, x_opt = local_max_intensity(g, power)
        return np.asarray(x_opt)

    if kind == "ecbf":
        raise ValueError("ecbf precoder is built from the precomputed Q pack; call build_ecbf_from_q")

    raise ValueError(f"unknown precoder kind: {kind!r}")


def build_ecbf_from_q(
    paths: tuple[np.ndarray, np.ndarray, np.ndarray, int],
    focus_xyz,
    freq_hz: float,
    q: np.ndarray,
    power: float = 1.0,
) -> np.ndarray:
    """Solve the ECBF QCQP against a precomputed exposure operator ``q``.

    ``q`` is the served Hermitian PSD exposure operator
    (``data/studio/qop/{condition}_bs{N}_{ghz}.npz``). The absorbed-power budget
    is set exactly as the offline precompute defines it:
    ``P_abs_max = _ECBF_BUDGET_FRAC * (x_mrt^H q x_mrt)`` with an MRT precoder.
    ``solve_ecbf`` may return ``||x||^2 <= power`` (power-slack regime); that is
    the correct QCQP optimum, so the result is not renormalised.
    """
    from aegis.coherent import solve_ecbf
    from aegis.hotspot import channel_at, make_rx_response

    k_hat, psi, element_index, n_elements = paths
    focus = np.asarray(focus_xyz, dtype=float)
    q = np.asarray(q)
    ue_rx = make_rx_response("dipole", freq_hz)
    h = channel_at(focus, k_hat, psi, element_index, freq_hz, n_elements, rx_response=ue_rx)
    x_mrt = np.sqrt(power) * np.conj(h) / np.linalg.norm(h)
    p_abs_mrt = float(np.real(x_mrt.conj() @ q @ x_mrt))
    return np.asarray(solve_ecbf(h, q, _ECBF_BUDGET_FRAC * p_abs_mrt, power))
