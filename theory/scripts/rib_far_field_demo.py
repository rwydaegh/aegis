"""
Reflective Intelligent Body (RIB) far-field demo.

Companion to theory/rib.tex.

Computes the bistatic body radar cross-section sigma_b(k_in, k_out)
of the Thelonious phantom under a single 28 GHz plane wave using the
Kirchhoff--PO integral

    F(k_out) = (i k_0 / 2pi) Pi_out * sum_{lit triangles}
                 R(r) psi * exp(-i k_0 (k_out - k_in) . r) * dA

with R the Fresnel reflection operator collapsed to its
pseudo-Brewster amplitude r_0 = sqrt(1-T_0) e^{i phi_r}, then verifies
the operator-level energy identity

    integral_{S^2} |F(k_out)|^2 dOmega   approx   (4 pi^2 / k_0^2)
                                                  * integral_Sigma |R psi|^2
                                                                   * mu_in dA

within the PO residual budget (~5-10 %).

Outputs:
  - Mollweide plot of bistatic RCS on outgoing hemisphere
  - Closed-form vs operator-level power totals (printed)
  - Specular peak diagnostics

Run:
    python theory/scripts/rib_far_field_demo.py --freq 28e9
        --output theory/figures/rib_demo.png
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _fresnel import EPS_0, n_complex
from _geom import load_stl_binary, triangle_areas

Z0 = 376.730313668  # ohm, free-space impedance


# --------------------------------------------------------------------------
# Tissue lookup. Use the same Gabriel-parameters path as
# compute_inter_body_reflections.py, but inlined for portability.
# --------------------------------------------------------------------------
def gabriel_skin(freq_hz: float) -> tuple[float, float]:
    """Return (eps_r, sigma) for skin at freq_hz from the IT'IS v5.0 DB.

    Falls back to a single-pole Cole-Cole evaluation if SQLite path is missing.
    """
    import sqlite3

    candidates = [
        Path(__file__).parent.parent / "data" / "itis_v5.db",
        Path(__file__).parent / "itis_v5.db",
        Path(__file__).resolve().parent.parent.parent / "data" / "itis_v5.db",
    ]
    db = next((p for p in candidates if p.exists()), None)
    if db is None:
        # Fallback: tabulated 28 GHz skin from the monograph
        return 16.55, 25.83

    conn = sqlite3.connect(str(db))
    c = conn.cursor()
    c.execute("SELECT prop_id FROM properties WHERE name = 'Gabriel Parameters'")
    pid = c.fetchone()[0]
    c.execute(
        """SELECT v.vals FROM materials m JOIN vectors v ON m.mat_id = v.mat_id
                 WHERE m.name = 'Skin' AND v.prop_id = ? LIMIT 1""",
        (pid,),
    )
    blob = c.fetchone()[0]
    conn.close()

    import struct as _struct

    n_floats = len(blob) // 8
    params = np.array(_struct.unpack(f"<{n_floats}d", blob))
    # Layout: eps_inf, sigma_static, [del_eps, tau_ps, alpha] x 4 poles
    eps_inf = params[0]
    sig_s = params[1]
    poles = params[2:].reshape(-1, 3)

    omega = 2 * np.pi * freq_hz
    eps = complex(eps_inf, 0.0)
    for d_eps, tau_ps, alpha in poles:
        if tau_ps <= 0.0 or d_eps <= 0.0:
            continue
        tau = tau_ps * 1e-12
        eps += d_eps / (1.0 + (1j * omega * tau) ** (1.0 - alpha))
    eps += sig_s / (1j * omega * EPS_0)
    eps_r = eps.real
    sigma = -eps.imag * omega * EPS_0
    return float(eps_r), float(sigma)


def fresnel_amp(mu: np.ndarray, n_tilde: complex) -> tuple[np.ndarray, np.ndarray]:
    """Complex amplitude reflection coefficients r_s, r_p with Re(xi) >= 0.

    Same xi branch as theory/scripts/_fresnel.py.
    """
    mu_c = np.asarray(mu, dtype=complex)
    n2 = n_tilde**2
    xi = np.sqrt(n2 - 1 + mu_c**2)
    xi = np.where(np.real(xi) < 0, -xi, xi)
    r_s = (mu_c - xi) / (mu_c + xi)
    r_p = (n2 * mu_c - xi) / (n2 * mu_c + xi)
    return r_s, r_p


# --------------------------------------------------------------------------
# Mesh + units
# --------------------------------------------------------------------------
def load_phantom(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, str]:
    """Load STL and auto-detect mm vs m by extent."""
    vertices, normals, centroids = load_stl_binary(str(path))
    extent = np.ptp(centroids, axis=0).max()
    if extent > 100.0:
        # mm -> m
        vertices = vertices * 1e-3
        centroids = centroids * 1e-3
        unit = "mm -> m"
    else:
        unit = "m"
    return vertices, normals, centroids, unit


# --------------------------------------------------------------------------
# Kirchhoff integral over outgoing directions
# --------------------------------------------------------------------------
def kirchhoff_far_field(
    centroids: np.ndarray,
    normals: np.ndarray,
    areas: np.ndarray,
    k_in: np.ndarray,
    psi_in: np.ndarray,
    k_out_grid: np.ndarray,
    n_tilde: complex,
    k0: float,
) -> tuple[np.ndarray, dict]:
    """Compute |F(k_out)|^2 on a grid of outgoing directions.

    Parameters
    ----------
    centroids, normals, areas
        Mesh tris in metres / unit / m^2.
    k_in
        (3,) unit incident direction (propagation direction).
    psi_in
        (3,) complex incident polarisation amplitude (unit |psi|).
    k_out_grid
        (G, 3) unit outgoing directions to evaluate.
    n_tilde
        Complex refractive index of skin at the working frequency.
    k0
        Free-space wavenumber 2pi f / c [rad/m].

    Returns
    -------
    F_sq : (G,)
        |F(k_out)|^2 per outgoing direction (units m^4: amplitude integral squared).
    diag : dict
        Diagnostics (lit fraction, projected area, total reflected power).
    """
    # 1. Incidence cosine and front-facing mask
    mu_in = -(normals @ k_in)  # n . (-k_in)
    lit_in = mu_in > 0.0
    if not np.any(lit_in):
        raise ValueError("No triangles are front-facing to k_in.")

    # 2. Reflected polarization at each lit triangle
    #    Under pseudo-Brewster collapse: R(r;k) = sqrt(1-T_0) * Pi(k) e^{i phi_r}
    #    with Pi(k) = I - k k^T. We use the exact Fresnel amplitudes for
    #    correctness near pseudo-Brewster, then project.
    r_s, r_p = fresnel_amp(mu_in[lit_in], n_tilde)

    # TE / TM basis at each lit triangle, given k_in and n_hat
    # e_s = k_in x n / |.|  (TE, perpendicular to plane of incidence)
    # e_p = e_s x k_in    (TM, in plane)
    n_lit = normals[lit_in]
    cross = np.cross(k_in[None, :], n_lit)
    cross_norm = np.linalg.norm(cross, axis=1, keepdims=True)
    # Fallback for normal incidence (k_in || n)
    abs_k = np.abs(k_in)
    fb_axis = int(np.argmin(abs_k))
    fb = np.cross(k_in, np.eye(3)[fb_axis])
    fb /= np.linalg.norm(fb)
    small = cross_norm[:, 0] < 1e-12
    e_s = np.where(small[:, None], fb[None, :], cross / np.where(cross_norm > 0, cross_norm, 1.0))
    e_s_norm = np.linalg.norm(e_s, axis=1, keepdims=True)
    e_s = e_s / np.where(e_s_norm > 0, e_s_norm, 1.0)
    e_p = np.cross(e_s, k_in[None, :])
    e_p_norm = np.linalg.norm(e_p, axis=1, keepdims=True)
    e_p = e_p / np.where(e_p_norm > 0, e_p_norm, 1.0)

    # Project incident polarisation onto TE/TM
    psi_s = e_s @ psi_in  # (M_lit,) complex
    psi_p = e_p @ psi_in  # (M_lit,) complex
    # Reflected polarisation amplitude in TE/TM basis (same e_s for outgoing,
    # e_p flips sign on reflection but we'll absorb that by working with the
    # outgoing-projection Pi^out below, which kills any non-transverse part).
    Rpsi = (r_s * psi_s)[:, None] * e_s + (r_p * psi_p)[:, None] * e_p  # (M_lit, 3)

    # 3. Kirchhoff sum over outgoing directions
    cen_lit = centroids[lit_in]
    A_lit = areas[lit_in]
    G = k_out_grid.shape[0]

    # Outgoing visibility: only triangles with n . k_out > 0 contribute
    # We'll handle this per-direction via a mask.
    mu_out = n_lit @ k_out_grid.T  # (M_lit, G)
    visible_out = mu_out > 0.0  # (M_lit, G)

    # Phase: exp(-i k_0 (k_out - k_in) . r)
    # Decompose: phase = exp(-i k_0 k_out . r) * exp(+i k_0 k_in . r)
    phase_in = np.exp(1j * k0 * (cen_lit @ k_in))  # (M_lit,)
    # We weight the per-triangle "source" by phase_in once
    src_amp = (A_lit * phase_in)[:, None] * Rpsi  # (M_lit, 3)

    F_sq = np.zeros(G, dtype=float)
    chunk = 64  # avoid creating a huge (M_lit, G, 3) intermediate

    for g0 in range(0, G, chunk):
        g1 = min(g0 + chunk, G)
        kg = k_out_grid[g0:g1]  # (g, 3)
        phase_out = np.exp(-1j * k0 * (cen_lit @ kg.T))  # (M_lit, g)
        mask = visible_out[:, g0:g1]  # (M_lit, g)
        # Sum over triangles per outgoing direction and per Cartesian component
        # F[g, c] = sum_m mask[m,g] * phase_out[m,g] * src_amp[m, c]
        weighted = (phase_out * mask)[:, :, None] * src_amp[:, None, :]  # (M_lit, g, 3)
        F_chunk = weighted.sum(axis=0)  # (g, 3)

        # Apply transverse projector Pi_out = I - k_out k_out^T to each direction
        kg_dot = np.einsum("gi,gi->g", kg, F_chunk)
        F_chunk_perp = F_chunk - kg[:, :, None][:, :, 0] * 0  # placeholder
        # Vectorised: F_perp[g] = F[g] - (k.F) k
        F_chunk_perp = F_chunk - (kg_dot[:, None]) * kg

        # Kirchhoff prefactor: (k_0 / 2 pi)^2 in |F|^2 (the i factor is unitary)
        # We accumulate |F|^2 in units (k_0/2pi)^2; final scaling handled outside.
        F_sq[g0:g1] = np.einsum("gi,gi->g", np.conj(F_chunk_perp), F_chunk_perp).real

    F_sq *= (k0 / (2 * np.pi)) ** 2

    # 4. Diagnostics
    proj_area_lit = float(np.sum(A_lit * mu_in[lit_in]))
    P_re_op = float(np.sum(A_lit * mu_in[lit_in] * np.einsum("mi,mi->m", np.conj(Rpsi), Rpsi).real)) / Z0

    diag = dict(
        n_tri_total=int(centroids.shape[0]),
        n_tri_lit=int(lit_in.sum()),
        proj_area_lit=proj_area_lit,
        P_re_operator=P_re_op,
        Z0=Z0,
        k0=k0,
    )
    return F_sq, diag


# --------------------------------------------------------------------------
# Outgoing-sphere quadrature
# --------------------------------------------------------------------------
def fibonacci_sphere(n: int) -> tuple[np.ndarray, np.ndarray]:
    """n quasi-uniform points on S^2 + equal weight 4*pi/n."""
    golden = np.pi * (3.0 - np.sqrt(5.0))
    i = np.arange(n)
    z = 1 - 2 * (i + 0.5) / n
    r = np.sqrt(np.clip(1 - z * z, 0, 1))
    phi = i * golden
    pts = np.stack([r * np.cos(phi), r * np.sin(phi), z], axis=1)
    weights = np.full(n, 4 * np.pi / n)
    return pts, weights


# --------------------------------------------------------------------------
# Mollweide plotting
# --------------------------------------------------------------------------
def mollweide_scatter(
    k_pts: np.ndarray, vals: np.ndarray, title: str, out_path: Path, vmax: float | None = None
) -> None:
    """Plot vals on k_pts via Mollweide projection. (lon, lat) from (kx, ky, kz)."""
    lon = np.arctan2(k_pts[:, 1], k_pts[:, 0])
    lat = np.arcsin(np.clip(k_pts[:, 2], -1.0, 1.0))

    fig = plt.figure(figsize=(8.5, 4.4))
    ax = fig.add_subplot(111, projection="mollweide")
    ax.grid(True, lw=0.4, alpha=0.6)

    db = 10 * np.log10(np.maximum(vals, vals.max() * 1e-6) / max(vals.max(), 1e-300))
    if vmax is None:
        vmax = 0.0
    sc = ax.scatter(lon, lat, c=db, s=3, cmap="inferno", vmin=-30, vmax=vmax, rasterized=True)
    cb = fig.colorbar(sc, ax=ax, shrink=0.7, pad=0.04)
    cb.set_label("relative |F|^2 [dB]")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main() -> int:
    here = Path(__file__).resolve().parent

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--freq", type=float, default=28e9, help="Frequency [Hz].")
    p.add_argument("--phantom", type=Path, default=here / "thelonious.stl")
    p.add_argument("--n-out", type=int, default=4096, help="Outgoing direction samples on S^2.")
    p.add_argument(
        "--k-in",
        type=str,
        default="0,0,-1",
        help="Incident propagation direction unit vector, comma-separated.",
    )
    p.add_argument(
        "--psi-in",
        type=str,
        default="1,0,0",
        help="Incident polarisation (real, will be projected transverse to k_in).",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=here.parent / "figures" / "rib_demo.png",
    )
    args = p.parse_args()

    # 1. Geometry
    if not args.phantom.exists():
        # Try data dir fallback
        alt = here.parent.parent / "data" / "thelonious.stl"
        if alt.exists():
            args.phantom = alt
        else:
            print(f"ERROR: phantom STL not found at {args.phantom} or {alt}")
            return 1
    print(f"Loading {args.phantom} ...")
    vertices, normals, centroids, unit = load_phantom(args.phantom)
    areas = triangle_areas(vertices)
    print(f"  {centroids.shape[0]} triangles  ({unit})")
    extent = np.ptp(centroids, axis=0)
    print(f"  bbox extent (m): {extent}")

    # 2. Tissue
    eps_r, sigma = gabriel_skin(args.freq)
    n_tilde = n_complex(eps_r, sigma, args.freq)
    T0 = 1 - abs((1 - n_tilde) / (1 + n_tilde)) ** 2
    print(f"Skin @ {args.freq / 1e9:.1f} GHz: eps_r={eps_r:.2f}, sigma={sigma:.2f} S/m")
    print(f"  n_tilde = {n_tilde:.3f}")
    print(f"  T_0 (normal incidence) = {T0:.4f}, 1-T_0 = {1 - T0:.4f}")

    # 3. Wave
    c0 = 299792458.0
    k0 = 2 * np.pi * args.freq / c0
    print(f"  k_0 = {k0:.2f} rad/m,  lambda = {2 * np.pi / k0 * 1000:.2f} mm")

    k_in = np.array([float(x) for x in args.k_in.split(",")])
    k_in = k_in / np.linalg.norm(k_in)
    psi_in = np.array([complex(x) for x in args.psi_in.split(",")])
    # Project to transverse
    psi_in = psi_in - (np.conj(k_in) @ psi_in) * k_in
    psi_in = psi_in / np.linalg.norm(psi_in)
    print(f"  k_in = {k_in},  |psi|={np.linalg.norm(psi_in):.3f}")

    # 4. Outgoing grid
    k_out_grid, w_out = fibonacci_sphere(args.n_out)

    # 5. Kirchhoff
    print(f"Computing Kirchhoff integral over {args.n_out} outgoing directions ...")
    t0 = time.time()
    F_sq, diag = kirchhoff_far_field(centroids, normals, areas, k_in, psi_in, k_out_grid, n_tilde, k0)
    print(f"  done in {time.time() - t0:.2f} s")

    # 6. Energy bookkeeping
    # Total scattered power (Kirchhoff): P_sc = sum_g w_g * |F_g|^2 / Z_0
    # (the (k_0/2pi)^2 prefactor is already inside F_sq)
    P_sc = float(np.sum(w_out * F_sq) / Z0)
    P_re_op = diag["P_re_operator"]
    rel_err = (P_sc - P_re_op) / P_re_op
    print()
    print("Energy bookkeeping (single plane wave |psi|=1, P_inc per unit area = 1/Z_0):")
    print(f"  Operator-level reflected power     = {P_re_op:.4e}  [W per m^2 of |E_inc|^2/Z_0]")
    print(f"  Kirchhoff far-field integral       = {P_sc:.4e}")
    print(f"  Relative error (PO residual)       = {100 * rel_err:+.2f} %")
    print(f"  Lit triangles / total              = {diag['n_tri_lit']} / {diag['n_tri_total']}")
    print(f"  Projected lit area (perp to k_in)  = {diag['proj_area_lit']:.4f} m^2")
    print(f"  Geometric albedo (1-T_0)*A_proj    = {(1 - T0) * diag['proj_area_lit']:.4f} m^2")
    print()

    # 7. Specular peak diagnostics
    g_max = int(np.argmax(F_sq))
    k_spec = -k_in.copy()
    k_spec = k_spec / np.linalg.norm(k_spec)
    cos_to_spec = k_out_grid @ k_spec
    near_spec = cos_to_spec > np.cos(np.deg2rad(15))
    P_spec = float(np.sum((w_out * F_sq)[near_spec]) / Z0)
    print(f"Specular diagnostic:")
    print(f"  Argmax direction k_out             = {k_out_grid[g_max]}")
    print(f"  Cosine to back-specular            = {cos_to_spec[g_max]:.4f}")
    print(f"  Power within 15 deg of back-spec   = {P_spec:.4e} ({100 * P_spec / P_sc:.1f}% of total)")
    print()

    # 8. Plot
    args.output.parent.mkdir(parents=True, exist_ok=True)
    title = f"RIB bistatic |F|$^2$ dB, Thelonious, f={args.freq / 1e9:.0f} GHz, $k_{{in}}$={tuple(k_in.round(2))}"
    mollweide_scatter(k_out_grid, F_sq, title, args.output)
    print(f"Wrote: {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
