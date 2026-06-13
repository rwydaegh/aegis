"""Oriented field-slice reconstruction for the Coherent Exposure Studio.

Reconstructs the coherent free-space field on a 2D plane through the focus and
derives a scalar map for rendering. Fork-free.

The field is always built from the collapsed per-direction plane-wave weights
``(k_unique, weights)`` (see ``aegis.hotspot.collapse_paths``). Most beams
collapse the precoder ``x`` directly; the decohered baseline instead scrambles
the inter-direction phase of those weights AFTER collapse (it is not expressible
as a per-element precoder), so the slice route passes a precomputed weight
source via ``field_source``.
"""

from __future__ import annotations

import numpy as np

# Base-station position in the e11 world frame (Z-up, metres).
_BS = np.array([-13.0, 0.0, 3.0])
_WORLD_UP = np.array([0.0, 0.0, 1.0])

# Decohered baseline phase-scramble seed. Fixed so a given scene is
# reproducible: same seed -> identical scrambled weights -> identical slice.
_DECOHERE_SEED = 0xBEEF

# World xyz component index for the signed real-part quantities.
_RE_COMPONENT = {"ReEx": 0, "ReEy": 1, "ReEz": 2}


def _beam_axis(center: np.ndarray) -> np.ndarray:
    """Unit vector from the focus toward the base station."""
    v = _BS - center
    n = np.linalg.norm(v)
    return v / n if n > 0 else np.array([1.0, 0.0, 0.0])


def decohered_field_source(
    paths: tuple[np.ndarray, np.ndarray, np.ndarray, int],
    x_base: np.ndarray,
    seed: int = _DECOHERE_SEED,
) -> tuple[np.ndarray, np.ndarray]:
    """Collapsed weights for the decohered baseline.

    Collapses ``x_base`` (an MRT/unit base precoder) to per-direction weights
    and scrambles the inter-direction phase with ``decohere_weights``. This is
    the paper's matched-illumination decohered baseline: the per-direction power
    ``||w_u||`` (hence the total power delivered to the region) is preserved
    while the coherent focus is destroyed. The scramble uses a fixed RNG seed so
    the result is reproducible. Returns ``(k_unique, weights_scrambled)`` ready
    for ``compute_slice(..., field_source=...)``.
    """
    from aegis.hotspot import collapse_paths, decohere_weights

    k_hat, psi, element_index, _n = paths
    k_unique, weights = collapse_paths(k_hat, psi, element_index, x_base)
    rng = np.random.default_rng(seed)
    return k_unique, decohere_weights(weights, rng)


def compute_slice(
    paths,
    x,
    plane_spec: dict,
    freq_hz: float,
    quantity: str,
    *,
    field_source: tuple[np.ndarray, np.ndarray] | None = None,
) -> dict:
    """Reconstruct E on an oriented plane and return the scalar map for ``quantity``.

    ``plane_spec`` carries ``center`` (the focus), ``orientation`` in
    {``transverse``, ``axial``, ``free``}, ``normal_xyz`` (free only),
    ``extent_m`` and ``res``.

    The field source is either ``field_source`` (precomputed
    ``(k_unique, weights)``, used by the decohered baseline) or, when that is
    ``None``, the collapse of the precoder ``x``.

    Quantities: ``S`` (power density), ``absE`` (|E|), ``ReEx``/``ReEy``/``ReEz``
    (signed real E components in the world basis), ``absH`` (|H|) and
    ``poynting`` (time-averaged Poynting magnitude). ``Sab`` (at-skin absorbed
    power density) is deferred: it needs body-intersection machinery the
    free-space slice does not carry.
    """
    from aegis.constants import Z_0
    from aegis.hotspot import SlicePlane, collapse_paths, power_density, synthesize_field

    k_hat, psi, element_index, _n_elements = paths
    center = np.asarray(plane_spec["center"], dtype=float)
    orientation = plane_spec.get("orientation", "transverse")
    # Bound client-supplied geometry: an unbounded res allocates (res, res, 3)
    # and OOMs the server, an unbounded extent is physically meaningless.
    extent = float(plane_spec.get("extent_m", 0.08))
    extent = min(max(extent, 1e-3), 3.0)
    res = min(max(int(plane_spec.get("res", 160)), 8), 512)
    beam = _beam_axis(center)

    if orientation == "transverse":
        normal = beam
        in_plane = _WORLD_UP
    elif orientation == "axial":
        normal = np.cross(beam, _WORLD_UP)
        if np.linalg.norm(normal) < 1e-8:
            normal = np.cross(beam, np.array([1.0, 0.0, 0.0]))
        in_plane = beam
    elif orientation == "free":
        normal_xyz = plane_spec.get("normal_xyz")
        if normal_xyz is None:
            raise ValueError("free orientation requires normal_xyz")
        normal = np.asarray(normal_xyz, dtype=float)
        if np.linalg.norm(normal) < 1e-9:
            raise ValueError("free orientation normal_xyz must be non-degenerate")
        in_plane = None
    else:
        raise ValueError(f"unknown plane orientation: {orientation!r}")

    plane = SlicePlane.oriented(center, normal, extent, res, in_plane_axis=in_plane)

    # Single collapse, reused for E (and for H when the quantity needs it).
    if field_source is not None:
        k_unique, weights = field_source
        k_unique = np.asarray(k_unique, dtype=float)
        weights = np.asarray(weights)
    else:
        k_unique, weights = collapse_paths(k_hat, psi, element_index, x)

    e_field = plane.reshape(synthesize_field(plane.points, k_unique, weights, freq_hz))

    if quantity == "S":
        scalar = np.asarray(power_density(e_field), dtype=float)
        units = "W/m^2"
    elif quantity == "absE":
        scalar = np.asarray(np.linalg.norm(e_field, axis=-1), dtype=float)
        units = "V/m"
    elif quantity in _RE_COMPONENT:
        scalar = np.real(e_field[..., _RE_COMPONENT[quantity]]).astype(float)
        units = "V/m"
    elif quantity in ("absH", "poynting"):
        # H has the same plane-wave phase per direction as E, so it synthesises
        # from the same (k_unique, weights) with magnetic weights
        # h_u = (k_hat_u x w_u) / Z_0 (free-space plane-wave relation).
        h_weight = np.cross(k_unique, weights) / Z_0
        h_field = plane.reshape(synthesize_field(plane.points, k_unique, h_weight, freq_hz))
        if quantity == "absH":
            scalar = np.asarray(np.linalg.norm(h_field, axis=-1), dtype=float)
            units = "A/m"
        else:
            # Time-averaged Poynting vector S = 1/2 Re(E x conj(H)); report |S|.
            s_vec = 0.5 * np.real(np.cross(e_field, np.conj(h_field)))
            scalar = np.asarray(np.linalg.norm(s_vec, axis=-1), dtype=float)
            units = "W/m^2"
    elif quantity == "Sab":
        raise NotImplementedError(
            "Sab (at-skin absorbed power density) needs the phantom mesh and "
            "plane-skin intersection, which the free-space slice does not carry; "
            "use the body-map endpoint for Sab"
        )
    else:
        raise NotImplementedError(f"unknown slice quantity: {quantity!r}")

    # Compute stats from the same float32 array that ships in the buffer so the
    # X-Stats header agrees exactly with the payload. The peak tracks field
    # strength (largest magnitude), so for the signed ReEx/y/z components it
    # locks onto the strongest lobe even when that lobe is negative; peak_value
    # then reports the signed field there. For non-negative quantities argmax of
    # the magnitude is identical to argmax of the value.
    scalar = scalar.astype(np.float32)
    flat_i = int(np.argmax(np.abs(scalar)))
    i, j = np.unravel_index(flat_i, scalar.shape)
    peak_xyz = plane.coords[i, j].tolist()

    return {
        "scalar": scalar,
        "world": {
            "center": center.tolist(),
            "e1": plane.e1.tolist(),
            "e2": plane.e2.tolist(),
            "extent": [float(plane.extent1), float(plane.extent2)],
        },
        "vmin": float(np.min(scalar)),
        "vmax": float(np.max(scalar)),
        "units": units,
        "peak_xyz": peak_xyz,
        "peak_value": float(scalar[i, j]),
        "quantity": quantity,
    }
