"""Oriented field-slice reconstruction for the Coherent Exposure Studio.

Reconstructs the coherent free-space field on a 2D plane through the focus and
derives a scalar map for rendering. Fork-free.
"""

from __future__ import annotations

import numpy as np

# Base-station position in the e11 world frame (Z-up, metres).
_BS = np.array([-13.0, 0.0, 3.0])
_WORLD_UP = np.array([0.0, 0.0, 1.0])


def _beam_axis(center: np.ndarray) -> np.ndarray:
    """Unit vector from the focus toward the base station."""
    v = _BS - center
    n = np.linalg.norm(v)
    return v / n if n > 0 else np.array([1.0, 0.0, 0.0])


def compute_slice(paths, x, plane_spec: dict, freq_hz: float, quantity: str) -> dict:
    """Reconstruct E on an oriented plane and return the scalar map for ``quantity``.

    ``plane_spec`` carries ``center`` (the focus), ``orientation`` in
    {``transverse``, ``axial``, ``free``}, ``normal_xyz`` (free only),
    ``extent_m`` and ``res``. Phase 1 implements ``S`` (power density) and
    ``absE`` (field magnitude); other quantities raise NotImplementedError.
    """
    from aegis.hotspot import SlicePlane, field_on, power_density

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
    e_field = field_on(plane, k_hat, psi, element_index, x, freq_hz)

    if quantity == "S":
        scalar = np.asarray(power_density(e_field), dtype=float)
        units = "W/m^2"
    elif quantity == "absE":
        scalar = np.asarray(np.linalg.norm(e_field, axis=-1), dtype=float)
        units = "V/m"
    else:
        raise NotImplementedError(f"quantity {quantity!r} arrives in Phase 2")

    # Compute stats from the same float32 array that ships in the buffer so the
    # X-Stats header agrees exactly with the payload.
    scalar = scalar.astype(np.float32)
    flat_i = int(np.argmax(scalar))
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
