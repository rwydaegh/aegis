"""Level 0: Worst-case power bound.

    P_abs <= T_0 * (A_ab * D_max / 4) * sum(S_i)

This is O(1) in M and O(N) in paths (just a sum). Returns a scalar bound
on total absorbed power, not a spatial map. The per-triangle S_ab is set
to a uniform upper bound: P_abs_bound / A_total spread over all triangles.
"""

from __future__ import annotations

import numpy as np


def level0_bound(
    total_area: float,
    A_ab: float,
    D_max: float,
    power: np.ndarray,
    T0: float,
    n_triangles: int,
) -> tuple[np.ndarray, float]:
    """Compute worst-case absorbed power bound.

    Parameters
    ----------
    total_area : total body surface area [m^2]
    A_ab : absorption area (eta-weighted mean projected area * 4) [m^2]
    D_max : maximum absorption directivity
    power : (N,) per-path power density [W/m^2]
    T0 : normal-incidence transmission
    n_triangles : number of mesh triangles

    Returns
    -------
    sab : (M,) uniform upper-bound S_ab per triangle [W/m^2]
    p_abs_bound : scalar upper bound on total absorbed power [W]
    """
    S_total = float(np.sum(power))
    p_abs_bound = T0 * (A_ab * D_max / 4.0) * S_total

    # Distribute bound uniformly across all triangles
    sab_uniform = p_abs_bound / total_area if total_area > 0 else 0.0
    sab = np.full(n_triangles, sab_uniform)
    return sab, p_abs_bound
