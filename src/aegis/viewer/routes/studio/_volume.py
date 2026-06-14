"""3D field-volume reconstruction for the Coherent Exposure Studio.

Reconstructs the coherent free-space power density on an axis-aligned box of
sample points centred on the focus, so the frontend can render the focal lobe
as a 3D field cloud. Reuses the same plane-wave synthesis as the 2D slice (just
on a 3D grid via :class:`aegis.hotspot.FieldVolume`). Fork-free.
"""

from __future__ import annotations

import numpy as np

# The box is more expensive than the 2D slice (res^3 points), so the resolution
# is bounded tighter: 48^3 ~ 110k points is already a few seconds on CPU.
_MAX_RES = 48
_MIN_RES = 8


def compute_volume(
    paths,
    x,
    center,
    freq_hz: float,
    extent_m: float,
    res: int,
    *,
    field_source: tuple[np.ndarray, np.ndarray] | None = None,
) -> dict:
    """Reconstruct power density on a 3D box centred on ``center``.

    ``extent_m`` is the full side length (the box is a cube); ``res`` the per
    axis point count (clamped to [8, 48]). The field source is either
    ``field_source`` (precomputed ``(k_unique, weights)``, used by the decohered
    baseline) or the collapse of the precoder ``x``.

    Returns the scalar grid plus the box geometry (origin = the min corner,
    spacing = point pitch) so the client can place each voxel in world space.
    """
    from aegis.hotspot import FieldVolume, collapse_paths, power_density, synthesize_field

    k_hat, psi, element_index, _n_elements = paths
    center = np.asarray(center, dtype=float)
    extent = min(max(float(extent_m), 1e-3), 3.0)
    res = min(max(int(res), _MIN_RES), _MAX_RES)

    vol = FieldVolume.centered(center, extent, res)

    if field_source is not None:
        k_unique, weights = field_source
        k_unique = np.asarray(k_unique, dtype=float)
        weights = np.asarray(weights)
    else:
        k_unique, weights = collapse_paths(k_hat, psi, element_index, x)

    e_field = vol.reshape(synthesize_field(vol.points, k_unique, weights, freq_hz))
    scalar = np.asarray(power_density(e_field), dtype=np.float32)

    # Box geometry: linspace is inclusive of both ends, so the pitch is
    # size / (res - 1) and the origin is the centre of the min-corner voxel.
    spacing = float(extent / (res - 1)) if res > 1 else 0.0
    origin = (center - extent / 2.0).tolist()

    flat_i = int(np.argmax(scalar))
    i, j, k = np.unravel_index(flat_i, scalar.shape)
    peak_xyz = [
        float(vol.x[i]),
        float(vol.y[j]),
        float(vol.z[k]),
    ]

    return {
        "scalar": scalar,
        "shape": [int(n) for n in scalar.shape],
        "origin": origin,
        "spacing": spacing,
        "vmin": float(np.min(scalar)),
        "vmax": float(np.max(scalar)),
        "units": "W/m^2",
        "peak_xyz": peak_xyz,
        "peak_value": float(scalar[i, j, k]),
        "quantity": "S",
    }
