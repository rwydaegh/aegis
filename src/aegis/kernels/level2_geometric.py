"""Level 2: Geometric ReLU spatial map."""

from __future__ import annotations

from aegis._array_backend import jit
from aegis.kernels._base import incidence_geometry


@jit
def level2_geometric(normals, k_hat, power, T0):
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
    sab = T0 * (mu_plus @ power)
    return sab
