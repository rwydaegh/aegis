"""Level 8: exposure-constrained beamforming (ECBF).

Same as Level 7, but solves the QCQP to find the optimal precoder x* that
maximizes signal power |h^T x|^2 subject to absorbed power and transmit
power constraints.

Monograph: sec:ecbf, eq:QCQP, eq:optimal-x.
"""

from __future__ import annotations

from aegis._array_backend import xp
from aegis.coherent.body_channel import compute_body_channel
from aegis.coherent.ecbf import solve_ecbf
from aegis.coherent.exposure_operator import (
    compute_exposure_operator,
    compute_rho,
    eigendecompose_Q,
)


def level8_ecbf(
    normals,
    centroids,
    areas,
    k_hat,
    psi,
    element_index,
    h,
    n_tilde,
    sigma,
    freq_hz,
    n_elements,
    P=1.0,
    P_abs_max=0.1,
):
    """Compute ECBF-optimised absorbed power density map.

    Parameters
    ----------
    normals : (M, 3)
    centroids : (M, 3)
    areas : (M,)
    k_hat : (N, 3)
    psi : (N, 3)
    element_index : (N,)
    h : (M_ant,) UE channel vector
    n_tilde : complex refractive index
    sigma : tissue conductivity [S/m]
    freq_hz : frequency [Hz]
    n_elements : int
    P : total transmit power [W]
    P_abs_max : maximum absorbed power [W]

    Returns
    -------
    sab : (M,) absorbed power density per triangle [W/m^2]
    Q : (M_ant, M_ant) exposure operator
    eigenvalues : (M_ant,) eigenvalues of Q (descending)
    x_star : (M_ant,) optimal precoding vector
    rho : float, exposure-signal alignment
    """
    G_tilde = compute_body_channel(
        normals,
        centroids,
        k_hat,
        psi,
        element_index,
        n_tilde,
        sigma,
        freq_hz,
        n_elements,
    )

    # Exposure operator Q
    Q = compute_exposure_operator(G_tilde, areas)
    eigenvalues, _ = eigendecompose_Q(Q)

    # Solve ECBF QCQP
    x_star = solve_ecbf(h, Q, P_abs_max, P)

    # S_ab with optimal precoder
    field = xp.einsum("mia,a->mi", G_tilde, x_star)  # (M, 3)
    sab = xp.real(xp.sum(xp.conj(field) * field, axis=1))  # (M,)
    sab = xp.maximum(sab, 0.0)

    # Exposure-signal alignment
    rho = compute_rho(h, Q, lambda_max=float(eigenvalues[0]))

    return sab, Q, eigenvalues, x_star, rho
