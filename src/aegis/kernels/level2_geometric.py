"""Level 2: Geometric ReLU spatial map.

The core incoherent dosimetry formula:
    S_ab(r) = T_0 * ReLU(N @ (-K)^T) @ s

where:
    N: (M, 3) triangle normals
    K: (N, 3) incident directions
    s: (N,) per-path power densities [W/m^2]
    T_0: normal-incidence power transmission coefficient

Cost: O(M * N). This is the workhorse level for compliance assessment.
"""

from __future__ import annotations

import numpy as np

from aegis.kernels._base import incidence_geometry


def level2_geometric(
    normals: np.ndarray,
    k_hat: np.ndarray,
    power: np.ndarray,
    T0: float,
) -> np.ndarray:
    """Compute per-triangle S_ab using the geometric absorption law.

    Parameters
    ----------
    normals : (M, 3) unit outward normals
    k_hat : (N, 3) incident directions (unit vectors)
    power : (N,) per-path power density [W/m^2]
    T0 : normal-incidence transmission coefficient

    Returns
    -------
    sab : (M,) absorbed power density per triangle [W/m^2]
    """
    _mu, mu_plus = incidence_geometry(normals, k_hat)
    sab = T0 * (mu_plus @ power)  # (M,)
    return sab
