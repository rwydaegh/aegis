"""Precoder synthesis for the Coherent Exposure Studio.

Builds the transmit precoding vector ``x`` for each beam kind from the loaded
ray pack. All kinds are matched-power (``||x||^2 = power``) except ``ecbf``,
whose QCQP optimum may sit in the power-slack regime (``||x||^2 <= power``)
when the absorption constraint binds.

``ecbf`` is built by :func:`build_ecbf_from_q` from the precomputed exposure
operator Q served on disk (``data/studio/qop/``); the old request-time full-body
tissue-channel build (~8 min) is gone. The ``decohered`` baseline is a
field-domain inter-direction phase scramble that cannot be a per-element
precoder, so it is not built here at all: the slice route synthesizes it via
``_slice.decohered_field_source``.

Fork-free: imports only ``aegis.hotspot``/``aegis.coherent`` and numpy.
"""

from __future__ import annotations

import numpy as np

# Random-phase precoders use a fixed seed so a given scene is reproducible.
_UNFOCUSED_SEED = 0xC0FFEE
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
    *,
    ue_antenna: str = "dipole",
    body_normal=None,
    n_tilde: complex | None = None,
    sigma: float | None = None,
) -> np.ndarray:
    """Build the precoder ``x`` of shape ``(n_elements,)`` for ``kind``.

    Kinds: ``mrt``, ``unfocused``, ``decoy``, ``worstcase``. ``ecbf`` is built
    from the precomputed exposure operator Q (call :func:`build_ecbf_from_q`),
    and ``decohered`` is a field-domain scramble that is not a per-element
    precoder (synthesize it via ``_slice.decohered_field_source``); both raise
    here.

    ``ue_antenna`` selects the UE receive pattern C_R(k) the matched-filter
    channel projects onto (``isotropic`` / ``vertical`` / ``dipole`` / ``patch``,
    see :func:`aegis.hotspot.make_rx_response`). It reshapes h and so the MRT /
    decoy precoders; ``unfocused`` is antenna-independent (random phases).

    For ``worstcase``, passing ``body_normal`` + ``n_tilde`` + ``sigma`` builds
    the precoder from the tissue channel ``G_tilde`` at the focus surface, so it
    maximises absorbed power density (matching the worst-case body map) rather
    than free-space field intensity. Without them it falls back to the
    free-space field channel (the only well-defined worst case for an in-air
    focus). The worst-case beam maximises absorption directly and so does not use
    the UE antenna.
    """
    from aegis.hotspot import field_channel_at, local_max_intensity, make_rx_response

    k_hat, psi, element_index, n_elements = paths
    focus = np.asarray(focus_xyz, dtype=float)
    ue_rx = make_rx_response(ue_antenna, freq_hz)

    if kind == "mrt":
        return _mrt(focus, k_hat, psi, element_index, freq_hz, n_elements, ue_rx, power)

    if kind == "unfocused":
        rng = np.random.default_rng(_UNFOCUSED_SEED)
        phases = rng.uniform(0.0, 2 * np.pi, n_elements)
        return np.sqrt(power / n_elements) * np.exp(1j * phases)

    if kind == "decohered":
        raise ValueError(
            "decohered baseline scrambles inter-direction phase after collapse and "
            "cannot be a per-element precoder; synthesize via _slice.decohered_field_source"
        )

    if kind == "decoy":
        decoy_focus = focus + _DECOY_OFFSET
        return _mrt(decoy_focus, k_hat, psi, element_index, freq_hz, n_elements, ue_rx, power)

    if kind == "worstcase":
        if body_normal is not None and n_tilde is not None and sigma is not None:
            # Absorption-optimal: leading right singular vector of the tissue
            # channel G_tilde at the focus triangle, so the deposited map peaks at
            # the same lambda_max(G_tilde^H G_tilde) the worst-case body map shows.
            from aegis.coherent.body_channel import compute_body_channel

            g_tilde = compute_body_channel(
                np.asarray(body_normal, dtype=float).reshape(1, 3),
                focus.reshape(1, 3),
                k_hat,
                psi,
                element_index,
                n_tilde,
                float(sigma),
                freq_hz,
                n_elements,
            )  # (1, 3, n_elements)
            _lam, x_opt = local_max_intensity(g_tilde[0], power)
            return np.asarray(x_opt)
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
    budget_frac: float = _ECBF_BUDGET_FRAC,
    ue_antenna: str = "dipole",
) -> np.ndarray:
    """Solve the ECBF QCQP against a precomputed exposure operator ``q``.

    ``q`` is the served Hermitian PSD exposure operator
    (``data/studio/qop/{mesh}_{condition}_bs{N}_{ghz}_seed{s}.npz``). The absorbed-power budget
    is ``P_abs_max = budget_frac * (x_mrt^H q x_mrt)`` with an MRT precoder, so
    ``budget_frac`` traces the exposure / signal Pareto front: 1.0 reproduces
    the MRT operating point, smaller values trade received signal for lower
    absorbed power. It defaults to the offline-precompute fraction and is
    clipped to ``[1e-3, 1]``. ``solve_ecbf`` may return ``||x||^2 <= power``
    (power-slack regime); that is the correct QCQP optimum, so the result is not
    renormalised.
    """
    from aegis.coherent import solve_ecbf
    from aegis.hotspot import channel_at, make_rx_response

    k_hat, psi, element_index, n_elements = paths
    focus = np.asarray(focus_xyz, dtype=float)
    q = np.asarray(q)
    frac = float(np.clip(budget_frac, 1e-3, 1.0))
    ue_rx = make_rx_response(ue_antenna, freq_hz)
    h = channel_at(focus, k_hat, psi, element_index, freq_hz, n_elements, rx_response=ue_rx)
    x_mrt = np.sqrt(power) * np.conj(h) / np.linalg.norm(h)
    p_abs_mrt = float(np.real(x_mrt.conj() @ q @ x_mrt))
    return np.asarray(solve_ecbf(h, q, frac * p_abs_mrt, power))
