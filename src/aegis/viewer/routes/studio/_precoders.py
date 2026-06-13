"""Precoder synthesis for the Coherent Exposure Studio.

Builds the transmit precoding vector ``x`` for each beam kind from the loaded
ray pack. All kinds are matched-power (``||x||^2 = power``) except ``ecbf``,
whose QCQP optimum may sit in the power-slack regime (``||x||^2 <= power``)
when the absorption constraint binds.

Fork-free: imports only ``aegis.hotspot``/``aegis.coherent`` and numpy. The
tissue dielectric table mirrors ``scripts/studio_precompute.py`` so a runtime
ECBF precoder matches the offline body-map packs.
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

# IT'IS v5.0 Gabriel 4-pole Cole-Cole skin (eps_r, sigma [S/m]) per dosimetry
# frequency, copied from SKIN_BY_GHZ in scripts/studio_precompute.py.
_SKIN_BY_GHZ = {
    8.0: (33.18, 5.82),
    10.0: (31.29, 8.01),
    12.0: (29.33, 10.34),
    15.0: (26.40, 13.85),
    20.0: (21.96, 19.22),
    28.0: (16.55, 25.82),
}


def _skin_props(freq_ghz: float) -> tuple[complex, float]:
    """Complex refractive index and conductivity of skin at a frequency."""
    from aegis.tissue.dielectric import SKIN_28GHZ
    from aegis.tissue.fresnel import n_complex

    if abs(freq_ghz - 28.0) < 1e-9:
        return complex(SKIN_28GHZ.n_complex), float(SKIN_28GHZ.sigma)
    if freq_ghz not in _SKIN_BY_GHZ:
        raise ValueError(f"no skin dielectric for {freq_ghz} GHz; known: {sorted(_SKIN_BY_GHZ)} (or 28)")
    eps_r, sigma = _SKIN_BY_GHZ[freq_ghz]
    return complex(n_complex(eps_r, sigma, freq_ghz * 1e9)), float(sigma)


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
    phantom: dict | None = None,
) -> np.ndarray:
    """Build the precoder ``x`` of shape ``(n_elements,)`` for ``kind``.

    Kinds: ``mrt``, ``unfocused``, ``decohered``, ``decoy``, ``worstcase``,
    ``ecbf``. ``ecbf`` requires ``phantom`` (normals, centroids, areas) to
    build the tissue exposure operator.
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
        # Element-level phase scramble of MRT: per-element power (hence the
        # regional illumination) is preserved while the coherent focus is
        # destroyed. The field-domain decohere_weights cannot be expressed as
        # a per-element precoder, so this is its precoder-space analogue.
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
        return _build_ecbf(paths, focus, freq_hz, power, phantom)

    raise ValueError(f"unknown precoder kind: {kind!r}")


def _build_ecbf(paths, focus, freq_hz, power, phantom):
    # COST: rebuilding the full-body tissue channel from scratch (~8000 tris x
    # ~67k expanded paths) is ~8 minutes single-threaded, far too slow for an
    # interactive request. ECBF is correct here but is not the default beam and
    # is not exercised in Phase 1. A runtime-feasible ECBF needs either a
    # precomputed exposure-operator Q pack served like the body maps, or the
    # factored body channel over the ~260 unique directions (Phase 2).
    from aegis.coherent import compute_exposure_operator, solve_ecbf
    from aegis.coherent.body_channel import compute_body_channel
    from aegis.hotspot import channel_at, make_rx_response

    if phantom is None:
        raise ValueError("ecbf precoder requires a phantom (normals, centroids, areas)")
    k_hat, psi, element_index, n_elements = paths
    n_tilde, sigma = _skin_props(freq_hz / 1e9)
    normals = phantom["normals"]
    centroids = phantom["centroids"]
    areas = phantom["areas"]

    # Tissue channel in triangle chunks to bound the (T, N, 3) intermediate.
    n_tri = normals.shape[0]
    g_tilde = np.empty((n_tri, 3, n_elements), dtype=complex)
    chunk = 128
    for a in range(0, n_tri, chunk):
        b = min(a + chunk, n_tri)
        g_tilde[a:b] = np.asarray(
            compute_body_channel(
                normals[a:b], centroids[a:b], k_hat, psi, element_index, n_tilde, sigma, freq_hz, n_elements
            )
        )
    q = np.asarray(compute_exposure_operator(g_tilde, areas))
    ue_rx = make_rx_response("dipole", freq_hz)
    h = channel_at(focus, k_hat, psi, element_index, freq_hz, n_elements, rx_response=ue_rx)
    x_mrt = np.sqrt(power) * np.conj(h) / np.linalg.norm(h)
    p_abs_mrt = float(np.real(x_mrt.conj() @ q @ x_mrt))
    return np.asarray(solve_ecbf(h, q, _ECBF_BUDGET_FRAC * p_abs_mrt, power))
