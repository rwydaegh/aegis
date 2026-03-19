"""Level 1: Aggregate absorbed power via directivity.

    P_abs = T_0 * (A_ab / 4) * sum_i S_i * D(k_hat_i)

This is O(N): one directivity lookup per path, no per-triangle loop.
Returns exact total absorbed power and uniform per-triangle S_ab
(since this level does not resolve the spatial map).
"""

from __future__ import annotations

import numpy as np

from aegis.geometry.directivity import eval_sh, spherical_angles_from_k_hat


def level1_aggregate(
    total_area: float,
    A_ab: float,
    k_hat: np.ndarray,
    power: np.ndarray,
    T0: float,
    n_triangles: int,
    sh_coeffs: np.ndarray | None = None,
    sh_L: int = 4,
    D_table: np.ndarray | None = None,
    D_dirs: np.ndarray | None = None,
) -> tuple[np.ndarray, float]:
    """Compute aggregate absorbed power via directivity.

    Uses either SH coefficients or a directivity LUT (nearest-neighbour
    lookup). If neither is provided, falls back to D=1 (isotropic).

    Parameters
    ----------
    total_area : total body surface area [m^2]
    A_ab : absorption area [m^2]
    k_hat : (N, 3) incident directions
    power : (N,) per-path power density [W/m^2]
    T0 : normal-incidence transmission
    n_triangles : number of mesh triangles
    sh_coeffs : SH coefficients for D(k_hat), from fit_sh()
    sh_L : SH degree
    D_table : (K,) precomputed directivity values
    D_dirs : (K, 3) directions corresponding to D_table

    Returns
    -------
    sab : (M,) uniform S_ab per triangle [W/m^2]
    p_abs : total absorbed power [W]
    """
    N = k_hat.shape[0]

    if sh_coeffs is not None:
        # Evaluate D(k_hat) from SH expansion
        theta, phi = spherical_angles_from_k_hat(k_hat)
        D = eval_sh(sh_coeffs, theta, phi, sh_L)
    elif D_table is not None and D_dirs is not None:
        # Nearest-neighbour lookup
        dots = k_hat @ D_dirs.T  # (N, K)
        nearest = np.argmax(dots, axis=1)
        D = D_table[nearest]
    else:
        # Fallback: isotropic D = 1
        D = np.ones(N)

    p_abs = T0 * (A_ab / 4.0) * float(np.sum(power * D))

    # Uniform per-triangle distribution (no spatial resolution)
    sab_uniform = p_abs / total_area if total_area > 0 else 0.0
    sab = np.full(n_triangles, sab_uniform)
    return sab, p_abs
