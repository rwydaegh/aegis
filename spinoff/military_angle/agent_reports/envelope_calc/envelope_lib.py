"""Near-field exposure-envelope calculation for a shipboard X-band phased array.

Builds the AEGIS coherent body-surface channel G_tilde(r) of shape (T, 3, M) for
an M-element planar array illuminating a human phantom at close range, using
true near-field spherical-wave phase and amplitude (NOT the plane-wave
compute_body_channel path, which assumes the body is angularly unresolved).

All AEGIS physics primitives (Fresnel transmission, depth coupling, tissue
dielectric, exposure operator) are reused from src/aegis. Only the geometry
(per-element per-triangle spherical wave) is assembled here.

Calibration (verified against paths.py / differt.py):
  psi = peak complex E-field vector [V/m]
  S_inc = |psi|^2 / (2 Z0)   [W/m^2]
  isotropic element, P_elem watts, distance d:  |E| = sqrt(2 Z0 P_elem/(4 pi)) / d
  S_ab(t) = sum_axis |G_tilde_t . x|^2   [W/m^2 absorbed power density]
  P_abs   = x^H Q x,   Q = sum_t area_t G_tilde_t^H G_tilde_t   [W]

Results are built at a 1 W total-radiated reference (per element unit-power,
||x||=1 => 1 W total). Absorbed densities scale linearly with total power.
"""

from __future__ import annotations

import numpy as np

from aegis.constants import C_0, Z_0
from aegis.tissue.dielectric import _n_complex, SKIN_BY_GHZ
from aegis.tissue.fresnel import _fresnel_core, xi_from_mu

NUMERICAL_FLOOR = 1e-30


def skin_at(freq_ghz: float):
    """Nearest-tabulated IT'IS skin (n_tilde, sigma) for the carrier."""
    keys = np.array(sorted(SKIN_BY_GHZ))
    k = float(keys[np.argmin(np.abs(keys - freq_ghz))])
    eps_r, sigma = SKIN_BY_GHZ[k]
    return complex(_n_complex(eps_r, sigma, k * 1e9)), float(sigma), k


def planar_array(n_side: int, spacing_m: float, center=(0.0, 0.0, 0.0)):
    """Vertical planar array in the y-z plane, boresight along +x.

    Returns element positions (M, 3), M = n_side**2.
    """
    off = (np.arange(n_side) - (n_side - 1) / 2.0) * spacing_m
    yy, zz = np.meshgrid(off, off, indexing="ij")
    p = np.stack([np.zeros(yy.size), yy.ravel(), zz.ravel()], axis=1)
    return p + np.asarray(center)


def _unit(v, axis=-1):
    n = np.linalg.norm(v, axis=axis, keepdims=True)
    return v / np.where(n > 0, n, 1.0)


def build_G_tilde(
    centroids, normals, p_elem, n_tilde, sigma, freq_hz,
    pol=(0.0, 0.0, 1.0), g_elem=1.0, p_elem_w=1.0,
):
    """Near-field body-surface channel G_tilde, shape (T, 3, M).

    centroids, normals : (T, 3) body triangles (m)
    p_elem : (M, 3) element positions (m)
    n_tilde, sigma : skin complex refractive index and conductivity
    freq_hz : carrier
    pol : global element polarization axis (projected transverse per ray)
    g_elem : element directivity boost (linear). g_elem = pi reproduces a filled
             lambda/2 aperture boresight gain 4 pi A / lambda^2 = pi M.
    p_elem_w : per-element radiated power at unit drive (W). Keep 1.0 for the
               per-1W-total reference; total radiated = p_elem_w * ||x||^2.
    """
    T = centroids.shape[0]
    M = p_elem.shape[0]
    k0 = 2 * np.pi * freq_hz / C_0
    pol = np.asarray(pol, float)
    amp0 = np.sqrt(2 * Z_0 * p_elem_w * g_elem / (4 * np.pi))

    G = np.zeros((T, 3, M), dtype=np.complex128)
    for j in range(M):
        vec = centroids - p_elem[j]            # (T,3) source->triangle
        d = np.linalg.norm(vec, axis=1)        # (T,)
        khat = vec / d[:, None]                # propagation dir
        mu = -np.sum(normals * khat, axis=1)   # incidence cosine n.(-khat)

        t_s, t_p = _fresnel_core(mu.astype(complex), n_tilde)[4:6]
        lit = mu > 0
        t_s = np.where(lit, t_s, 0.0)
        t_p = np.where(lit, t_p, 0.0)

        # TE/TM basis (te_tm_basis convention: e_s = khat x n, e_p = e_s x khat)
        e_s = np.cross(khat, normals)
        small = np.linalg.norm(e_s, axis=1) < 1e-12
        if small.any():  # near-normal incidence: ref = axis of smallest |khat|
            ks = khat[small]
            ref = np.zeros_like(ks)
            ref[np.arange(ks.shape[0]), np.argmin(np.abs(ks), axis=1)] = 1.0
            e_s[small] = np.cross(ks, ref)
        e_s = _unit(e_s)
        e_p = _unit(np.cross(e_s, khat))

        # incident field vector psi = amp * transverse polarization
        pol_perp = pol - np.outer(khat @ pol, np.ones(3)) * khat
        pol_perp = _unit(pol_perp)
        amp = amp0 / d
        psi = amp[:, None] * pol_perp          # (T,3)

        psi_s = np.sum(e_s * psi, axis=1)
        psi_p = np.sum(e_p * psi, axis=1)
        F_psi = (t_s * psi_s)[:, None] * e_s + (t_p * psi_p)[:, None] * e_p

        xi = xi_from_mu(mu.astype(complex), n_tilde)
        alpha = np.maximum(-np.imag(k0 * xi), NUMERICAL_FLOOR)
        depth_w = np.sqrt(sigma / (4 * alpha))
        phase = np.exp(-1j * k0 * d)

        G[:, :, j] = (depth_w * phase)[:, None] * F_psi
    return G


def exposure_operator(G, areas):
    """Q = sum_t area_t G_t^H G_t  (M x M Hermitian PSD). G:(T,3,M)."""
    # Ghat = stack of sqrt(area) * G_t rows -> (3T, M); Q = Ghat^H Ghat
    w = np.sqrt(areas)[:, None, None]
    Gh = (w * G).reshape(-1, G.shape[2])       # (3T, M)
    Q = Gh.conj().T @ Gh
    return (Q + Q.conj().T) / 2


def sab_of_beam(G, x):
    """Per-triangle absorbed power density for precoder x. Returns (T,)."""
    Gx = G @ x                                  # (T,3)
    return np.sum(np.abs(Gx) ** 2, axis=1)


def worst_case_local_apd(G):
    """max over unit-norm x of S_ab(t) per triangle = ||G_t||_2^2 (spectral). (T,)"""
    # spectral norm of each 3xM block, squared
    s = np.linalg.svd(G, compute_uv=False)      # (T, 3)
    return s[:, 0] ** 2
