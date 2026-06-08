"""Level 7: coherent MIMO absorption map.

S_ab(r) = ||G_tilde(r) @ x||^2

Computes per-triangle absorbed power density from the body-surface channel
G_tilde(r) and a precoding vector x. Uses Approximations 1 and 2 from the
monograph (combined error < 5% for skin at 28 GHz).

Monograph: thm:coherent-law (Theorem 4.1).
"""

from __future__ import annotations

import os

import numpy as np
from numpy.typing import NDArray

from aegis._array_backend import xp
from aegis.coherent.body_channel import compute_body_channel
from aegis.coherent.exposure_operator import (
    compute_exposure_operator,
    compute_rho,
    eigendecompose_Q,
)

# Triangle-chunk budget: the body channel's transient (B, N, 3) intermediate
# (B triangles, N paths) is the kernel's memory peak. At full phantom resolution
# (56k triangles) with a diffraction-rich path set it reaches tens of GB, which
# overflows a GPU. Process triangles in blocks sized so B*N stays near this many
# (m, n) pairs; Q is a triangle-sum (additive) and sab is per-triangle, so the
# blocked result is identical to the unchunked one. Override per device with
# AEGIS_TRI_CHUNK_MN.
_TRI_CHUNK_MN = int(os.environ.get("AEGIS_TRI_CHUNK_MN", 6_000_000))


def _triangle_chunk(n_tri: int, n_paths: int) -> int:
    """Number of triangles per block so the (B, N, 3) intermediate stays bounded."""
    if n_paths <= 0:
        return max(1, n_tri)
    return max(1, min(n_tri, _TRI_CHUNK_MN // max(1, n_paths)))


def level7_coherent(
    normals: NDArray[np.floating],
    centroids: NDArray[np.floating],
    areas: NDArray[np.floating],
    k_hat: NDArray[np.floating],
    psi: NDArray[np.complexfloating],
    element_index: NDArray[np.integer],
    x: NDArray[np.complexfloating],
    n_tilde: complex | NDArray[np.complexfloating],
    sigma: float,
    freq_hz: float,
    n_elements: int,
    h: NDArray[np.complexfloating] | None = None,
    fock_R: NDArray[np.floating] | None = None,
    q_F_s: complex | None = None,
    q_F_h: complex | None = None,
) -> tuple[
    NDArray[np.floating],
    NDArray[np.complexfloating],
    NDArray[np.floating],
    float | None,
]:
    """Compute coherent absorbed power density map.

    Parameters
    ----------
    normals : (M, 3)
    centroids : (M, 3)
    areas : (M,)
    k_hat : (N, 3)
    psi : (N, 3)
    element_index : (N,)
    x : (M_ant,) precoding vector
    n_tilde : complex refractive index
    sigma : tissue conductivity [S/m]
    freq_hz : frequency [Hz]
    n_elements : int
    h : (M_ant,) UE channel vector (optional, for rho computation)
    fock_R : (M,) or (M, N) or None
        In-incidence-plane curvature radius [m] for the Fock shadow gate. ``None``
        disables the gate (exact GO/Fresnel channel, back-compat).
    q_F_s, q_F_h : complex or None
        Soft/hard impedance-Fock parameters (``None`` selects the PEC gate).

    Returns
    -------
    sab : (M,) absorbed power density per triangle [W/m^2]
    Q : (M_ant, M_ant) exposure operator
    eigenvalues : (M_ant,) or None, eigenvalues of Q
    rho : float or None, exposure-signal alignment
    """
    # Process triangles in blocks. Building G_tilde for all M triangles at once
    # peaks at the (M, N, 3) body-channel intermediate, which overflows a GPU at
    # full resolution. Q is a triangle-sum and sab is per-triangle, so blocking
    # gives the identical result (up to floating-point summation order) at a
    # bounded memory footprint.
    M = normals.shape[0]
    n_paths = int(np.asarray(k_hat).shape[0]) if np.asarray(k_hat).ndim else 0
    chunk = _triangle_chunk(M, n_paths)

    sab_blocks: list[NDArray[np.floating]] = []
    # Lowercase accumulator inside the loop: Q is bound once, after the loop, so
    # the all-caps return name is a single definition, not a reassigned constant.
    q_acc: NDArray[np.complexfloating] = xp.zeros((n_elements, n_elements), dtype=complex)
    # Slice the per-triangle Fock radius to match each triangle block. A (M, N)
    # radius (per path) is row-sliced too; a scalar/None passes through unchanged.
    fock_R_arr = None if fock_R is None else xp.asarray(fock_R)

    for start in range(0, M, chunk):
        sl = slice(start, start + chunk)
        fock_R_blk = None if fock_R_arr is None else fock_R_arr[sl]
        G_blk = compute_body_channel(
            normals[sl],
            centroids[sl],
            k_hat,
            psi,
            element_index,
            n_tilde,
            sigma,
            freq_hz,
            n_elements,
            fock_R=fock_R_blk,
            q_F_s=q_F_s,
            q_F_h=q_F_h,
        )  # (B, 3, M_ant)

        # S_ab(r) = ||G_tilde(r) @ x||^2 for this block
        field = xp.einsum("mia,a->mi", G_blk, x)  # (B, 3)
        power: NDArray[np.floating] = xp.real(xp.sum(xp.conj(field) * field, axis=1))
        sab_blocks.append(xp.maximum(power, 0.0))

        # Q accumulates over triangles (each block already Hermitian-symmetrised)
        q_acc = q_acc + compute_exposure_operator(G_blk, areas[sl])

    sab: NDArray[np.floating] = sab_blocks[0] if len(sab_blocks) == 1 else xp.concatenate(sab_blocks)
    Q: NDArray[np.complexfloating] = q_acc
    eigenvalues, _ = eigendecompose_Q(Q)

    # Exposure-signal alignment rho
    rho: float | None = None
    if h is not None:
        rho = compute_rho(h, Q, lambda_max=float(eigenvalues[0]))

    return sab, Q, eigenvalues, rho
