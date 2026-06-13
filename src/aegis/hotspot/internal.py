"""Internal (transmitted) field a focused beam drives into tissue, in 2D.

This is the paper's coherent absorption model evaluated *before* the two
approximations collapse it to a surface norm, so it can be drawn as a field
that crosses the skin rather than a number on the surface. Under the paper's
own assumptions:

- the body is uncoupled in propagation: the incident field is the free-space
  ray-traced plane-wave sum E_inc(r) = sum_n x_n psi_n exp(-i k0 k_n . r), the
  same one the field channel uses (no body in the RT);
- a single homogeneous skin half-space (Approximation: locally flat interface
  on the wavelength scale), refractive index n_tilde, conductivity sigma;
- per-path Fresnel transmission into tissue and an exponential depth factor.

At a surface point r_s with outward normal n_hat, the transmitted field of
path n at depth z (eq. E-trans in the monograph) is

    E_n(r_s, z) = F_n(r_s) psi_n  x_{j(n)} exp(-i k0 k_n . r_s) exp(-i k0 xi_n z)

with F_n the Fresnel transmission operator (t_s, t_p onto the TE/TM basis,
gated to front-facing paths) and k0 xi_n = beta_n - i alpha_n the complex
normal wavenumber in tissue, so exp(-i k0 xi_n z) = exp(-alpha_n z) exp(-i
beta_n z) decays into the body. The total internal field sums coherently over
paths, E = sum_n E_n, and the local SAR is (sigma / 2 rho) |E|^2.

The Fresnel operator and the depth factor depend on the path only through its
arrival direction k_n, so paths sharing a direction (the synthetic-array
layout) collapse: with w_u = sum_{n in u} x_{j(n)} psi_n the per-direction
incident weight,

    E(r_s, z) = sum_u [F_u(r_s) w_u] exp(-i k0 k_u . r_s) exp(-i k0 xi_u z).

That makes the internal-field sum run over the ~10^2 unique directions, not
the ~10^4-10^5 paths. F is linear in the incident vector, so folding the
precoder into w_u first is exact.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from aegis.constants import C_0, Z_0
from aegis.tissue.fresnel import xi_from_mu


def _te_tm(k, normals):
    """TE/TM basis for one direction k against per-point normals (Q, 3).

    Matches ``fresnel_operator.te_tm_basis``: e_s = k x n / |k x n| (with a
    perpendicular fallback at normal incidence), e_p = e_s x k.
    """
    k = np.asarray(k, float)
    cross = np.cross(k[None, :], normals)  # (Q, 3)
    cn = np.linalg.norm(cross, axis=1, keepdims=True)
    # fallback perpendicular to k where k || n
    ref = np.zeros(3)
    ref[int(np.argmin(np.abs(k)))] = 1.0
    fb = np.cross(k, ref)
    fb = fb / np.linalg.norm(fb)
    e_s = np.where(cn < 1e-12, fb[None, :], cross / np.where(cn > 0, cn, 1.0))
    e_s = e_s / np.linalg.norm(e_s, axis=1, keepdims=True)
    e_p = np.cross(e_s, k[None, :])
    e_p = e_p / np.linalg.norm(e_p, axis=1, keepdims=True)
    return e_s, e_p


def transmitted_field(
    r_s: np.ndarray,
    normals: np.ndarray,
    z: np.ndarray,
    k_unique: np.ndarray,
    weights: np.ndarray,
    freq_hz: float,
    n_tilde: complex,
) -> np.ndarray:
    """Coherent transmitted field E(r_s, z) at interior points.

    Parameters
    ----------
    r_s : (Q, 3)
        Surface entry point for each interior sample (the locally flat
        interface point above it).
    normals : (Q, 3)
        Outward unit normal at each entry point.
    z : (Q,)
        Depth into tissue [m], >= 0.
    k_unique : (U, 3), weights : (U, 3)
        Collapsed arrival directions and per-direction incident weights
        (precoder folded in, from ``collapse_paths``).
    n_tilde : complex
        Skin refractive index.

    Returns
    -------
    E : (Q, 3) complex
        Transmitted field phasor at each interior sample.
    """
    r_s = np.asarray(r_s, float)
    normals = np.asarray(normals, float)
    z = np.asarray(z, float)
    k0 = 2 * np.pi * freq_hz / C_0
    n2 = n_tilde**2
    E = np.zeros((r_s.shape[0], 3), dtype=complex)

    for u in range(k_unique.shape[0]):
        k = k_unique[u]
        w = weights[u]
        mu = normals @ (-k)  # (Q,) incidence cosine
        front = mu > 0
        if not front.any():
            continue
        xi = xi_from_mu(mu, n_tilde)  # (Q,) complex
        t_s = 2 * mu / (mu + xi)
        t_p = 2 * n_tilde * mu / (n2 * mu + xi)
        e_s, e_p = _te_tm(k, normals)  # (Q, 3) each
        w_s = e_s @ w  # (Q,) scalar projections of the incident weight
        w_p = e_p @ w
        F_w = (t_s * w_s)[:, None] * e_s + (t_p * w_p)[:, None] * e_p  # (Q, 3)
        lateral = np.exp(-1j * k0 * (r_s @ k))  # (Q,)
        depth = np.exp(-1j * k0 * xi * z)  # (Q,) -> exp(-alpha z) exp(-i beta z)
        contrib = F_w * (lateral * depth)[:, None]
        contrib[~front] = 0.0
        E += contrib
    return E


@dataclass
class InternalPanel:
    """A 2D lateral-by-depth slice of the field crossing the skin."""

    lateral_cm: np.ndarray  # (n_l,) along-surface coordinate [cm]
    depth_mm: np.ndarray  # (n_d,) depth axis [mm], negative = air side
    S: np.ndarray  # (n_l, n_d) |E|^2 / 2Z0 [W/m^2], incident in air, transmitted in tissue
    sar: np.ndarray  # (n_l, n_d) local SAR (sigma/2rho)|E|^2 in tissue, 0 in air
    surface_index: int  # depth index of the air/tissue interface (z = 0)


def internal_panel(
    focus: np.ndarray,
    normal: np.ndarray,
    in_surface_axis: np.ndarray,
    k_unique: np.ndarray,
    weights: np.ndarray,
    freq_hz: float,
    n_tilde: complex,
    sigma: float,
    *,
    lateral_extent_m: float = 0.04,
    depth_extent_m: float = 6e-3,
    air_margin_m: float = 1.5e-3,
    n_lateral: int = 320,
    n_depth: int = 240,
    rho: float = 1109.0,
) -> InternalPanel:
    """Field crossing the skin on a (along-surface) x (into-depth) plane.

    The plane is centred on the surface focus point: one axis runs along the
    surface (``in_surface_axis`` projected tangent), the other runs from
    ``air_margin`` above the skin down to ``depth_extent`` below it. Air-side
    samples get the incident free-space field; tissue-side samples get the
    coherent transmitted field. This shows the cm-scale lateral hotspot and
    the sub-mm depth decay in one panel: the field actually crossing into the
    body, under the paper's single-half-space assumption.
    """
    focus = np.asarray(focus, float)
    n_hat = np.asarray(normal, float)
    n_hat = n_hat / np.linalg.norm(n_hat)
    # along-surface axis: project the requested axis tangent to the surface
    t = np.asarray(in_surface_axis, float)
    t = t - (t @ n_hat) * n_hat
    if np.linalg.norm(t) < 1e-8:
        t = np.cross(n_hat, [0, 0, 1.0])
    t = t / np.linalg.norm(t)
    depth_dir = -n_hat  # into the body

    lat = np.linspace(-lateral_extent_m / 2, lateral_extent_m / 2, n_lateral)
    dep = np.linspace(-air_margin_m, depth_extent_m, n_depth)  # <0 air, >0 tissue
    LAT, DEP = np.meshgrid(lat, dep, indexing="ij")  # (n_l, n_d)
    pts = (
        focus[None, None, :] + LAT[..., None] * t[None, None, :] + DEP[..., None] * depth_dir[None, None, :]
    ).reshape(-1, 3)
    depth_flat = DEP.reshape(-1)
    tissue = depth_flat > 0

    E = np.zeros((pts.shape[0], 3), dtype=complex)
    # air side: incident free-space field
    if (~tissue).any():
        from aegis.hotspot.synthesis import synthesize_field

        E[~tissue] = synthesize_field(pts[~tissue], k_unique, weights, freq_hz, dtype=np.complex128)
    # tissue side: transmitted coherent field, entry point is the surface point
    # directly above (locally flat half-space at the focus normal)
    if tissue.any():
        r_s = pts[tissue] - depth_flat[tissue][:, None] * depth_dir[None, :]  # back up to z=0
        nrm = np.broadcast_to(n_hat, (int(tissue.sum()), 3))
        E[tissue] = transmitted_field(r_s, nrm, depth_flat[tissue], k_unique, weights, freq_hz, n_tilde)

    S = (np.abs(E) ** 2).sum(1) / (2 * Z_0)
    sar = np.where(tissue, sigma * (np.abs(E) ** 2).sum(1) / (2 * rho), 0.0)
    surface_index = int(np.argmin(np.abs(dep)))
    return InternalPanel(
        lateral_cm=lat * 100,
        depth_mm=dep * 1000,
        S=S.reshape(n_lateral, n_depth),
        sar=sar.reshape(n_lateral, n_depth),
        surface_index=surface_index,
    )


def nearest_surface(points: np.ndarray, centroids: np.ndarray, normals: np.ndarray):
    """Nearest surface element per point: (r_s, n_hat, signed_depth).

    ``signed_depth > 0`` means the point is inside the body (below the surface
    along the inward normal). Uses nearest centroid, the locally flat
    half-space the paper assumes.
    """
    from scipy.spatial import cKDTree

    tree = cKDTree(centroids)
    _, idx = tree.query(points)
    r_s = centroids[idx]
    n_hat = normals[idx]
    signed = -np.einsum("ij,ij->i", points - r_s, n_hat)  # >0 inside
    return r_s, n_hat, signed, idx
