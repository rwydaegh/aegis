"""Level 8: exposure-constrained beamforming (ECBF).

Same as Level 7, but solves the QCQP to find the optimal precoder x* that
maximizes signal power |h^T x|^2 subject to absorbed power and transmit
power constraints.

Monograph: sec:ecbf, eq:QCQP, eq:optimal-x.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from aegis._array_backend import xp
from aegis.coherent.body_channel import compute_body_channel
from aegis.coherent.ecbf import solve_ecbf
from aegis.coherent.exposure_operator import (
    compute_exposure_operator,
    compute_rho,
    eigendecompose_Q,
)
from aegis.defaults import DEFAULT_P_ABS_MAX


def level8_ecbf(
    normals: NDArray[np.floating],
    centroids: NDArray[np.floating],
    areas: NDArray[np.floating],
    k_hat: NDArray[np.floating],
    psi: NDArray[np.complexfloating],
    element_index: NDArray[np.integer],
    h: NDArray[np.complexfloating],
    n_tilde: complex | NDArray[np.complexfloating],
    sigma: float,
    freq_hz: float,
    n_elements: int,
    P: float = 1.0,
    P_abs_max: float = DEFAULT_P_ABS_MAX,
    fock_R: NDArray[np.floating] | None = None,
    q_F_s: complex | None = None,
    q_F_h: complex | None = None,
    clearance: NDArray[np.floating] | None = None,
    R_occ: NDArray[np.floating] | None = None,
    distal_d1: NDArray[np.floating] | None = None,
    distal_d2: NDArray[np.floating] | None = None,
) -> tuple[
    NDArray[np.floating],
    NDArray[np.complexfloating],
    NDArray[np.floating],
    NDArray[np.complexfloating],
    float,
]:
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
    fock_R : (M,) or (M, N) or None
        In-incidence-plane curvature radius [m] for the Fock shadow gate. ``None``
        disables the gate (exact GO/Fresnel channel, back-compat).
    q_F_s, q_F_h : complex or None
        Soft/hard impedance-Fock parameters (``None`` selects the PEC gate).

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
        fock_R=fock_R,
        q_F_s=q_F_s,
        q_F_h=q_F_h,
        clearance=clearance,
        R_occ=R_occ,
        distal_d1=distal_d1,
        distal_d2=distal_d2,
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
