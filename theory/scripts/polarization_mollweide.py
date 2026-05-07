"""
Polarisation Response Mollweide Maps — Task 2
==============================================

Produces a 2×2 figure for monograph §10.3:
  (a) Ã_⊥(k̂)  Mollweide  — unpolarised absorption vs direction
  (b) |B̃(k̂)| Mollweide  — polarisation correction magnitude
  (c) D_B(k̂)  Mollweide  — fractional correction |B̃|/(2Ã_⊥), capped at 30%
  (d) Histogram of D_B    — vertical lines at max, mean, cylinder bound (27.9%)

Uses ~2000 fibonacci-sphere directions on the Thelonious phantom at 28 GHz.
Tissue properties are derived from the IT'IS v5 database (4-Cole-Cole model).

The per-direction (Ã_⊥, B_c, B_s) computation is reused from
compute_polarization_response_tables.py.
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")

import argparse
import cmath
import sqlite3
import struct
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib import cm

# ---------------------------------------------------------------------------
# Project helpers (added to sys.path so we can import from scripts/)
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from _plot_style import apply_monograph_style, fig_size_textwidth, TEXTWIDTH_IN
from _geom import load_stl_binary, triangle_areas
from _fresnel import fresnel_transmission, n_complex as _n_complex

# Reuse core functions from the existing polarisation script
from compute_polarization_response_tables import (
    fibonacci_sphere,
    reference_frame_from_k,
    compute_tables,
)

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------
EPS_0 = 8.854187817e-12  # F/m
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"

# ---------------------------------------------------------------------------
# IT'IS database helpers  (mirrors mie_theory_corrected.py)
# ---------------------------------------------------------------------------

DB_PATHS = [
    DATA_DIR / "itis_v5.db",
    SCRIPT_DIR / "itis_v5.db",
    PROJECT_ROOT / "EMT" / "itis_v5.db",
]


def find_database() -> Path:
    for p in DB_PATHS:
        if p.exists():
            return p
    raise FileNotFoundError("IT'IS v5 database not found in expected locations.")


def get_gabriel_params(tissue_name: str = "Skin") -> dict:
    db_path = find_database()
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute("SELECT prop_id FROM properties WHERE name = ?", ("Gabriel Parameters",))
    prop_result = c.fetchone()
    if not prop_result:
        conn.close()
        raise ValueError("Gabriel Parameters property not found in DB.")
    prop_id = prop_result[0]
    c.execute(
        """SELECT m.mat_id, v.vals
           FROM materials m
           JOIN vectors v ON m.mat_id = v.mat_id
           WHERE m.name = ? AND v.prop_id = ?
           LIMIT 1""",
        (tissue_name, prop_id),
    )
    result = c.fetchone()
    conn.close()
    if not result:
        raise ValueError(f"Tissue '{tissue_name}' not found in DB.")
    blob = result[1]
    if len(blob) >= 14 * 8:
        values = struct.unpack("d" * 14, blob[: 14 * 8])
        return {
            "ef": values[0],
            "del1": values[1], "tau1": values[2], "alf1": values[3],
            "del2": values[4], "tau2": values[5], "alf2": values[6],
            "del3": values[7], "tau3": values[8], "alf3": values[9],
            "del4": values[10], "tau4": values[11], "alf4": values[12],
            "sig": values[13],
        }
    raise ValueError("Blob too short for 4-Cole-Cole parameters.")


def cole_cole_permittivity(freq_hz: float, params: dict) -> complex:
    omega = 2 * np.pi * freq_hz
    eps = complex(params["ef"], 0)
    tau_units = [1e-12, 1e-9, 1e-6, 1e-3]
    for i in range(4):
        delta = params[f"del{i+1}"]
        tau = params[f"tau{i+1}"] * tau_units[i]
        alpha = params[f"alf{i+1}"]
        if delta != 0 and tau != 0:
            denom = 1 + (1j * omega * tau) ** (1 - alpha)
            eps += delta / denom
    if params["sig"] != 0 and omega != 0:
        eps -= 1j * params["sig"] / (omega * EPS_0)
    return eps


def get_tissue_n(tissue_name: str, freq_hz: float) -> complex:
    """Return complex refractive index from IT'IS 4-Cole-Cole model."""
    params = get_gabriel_params(tissue_name)
    eps_c = cole_cole_permittivity(freq_hz, params)
    m = cmath.sqrt(eps_c)
    if m.real < 0:
        m = -m
    return m


# ---------------------------------------------------------------------------
# Cylinder bound (analytical)
# ---------------------------------------------------------------------------

def compute_cylinder_bound(n_tilde: complex, n_mu: int = 5000) -> float:
    """
    Compute D_B^{cyl} = ∫₀¹ ΔT(μ)·μ dμ  /  (2 ∫₀¹ T_avg(μ)·μ dμ).
    This is the theoretical worst-case polarisation correction for any
    convex body (achieved by an infinite cylinder at broadside).
    """
    mu = np.linspace(0, 1, n_mu + 1)
    T_s, T_p = fresnel_transmission(mu, n_tilde)
    T_avg = 0.5 * (T_s + T_p)
    dT = T_p - T_s
    # Trapezoidal integration
    integrand_avg = T_avg * mu
    integrand_dT = dT * mu
    I_avg = np.trapezoid(integrand_avg, mu)
    I_dT = np.trapezoid(integrand_dT, mu)
    return I_dT / (2 * I_avg)


# ---------------------------------------------------------------------------
# Mollweide projection helper
# ---------------------------------------------------------------------------

def directions_to_lonlat(directions: np.ndarray):
    """Convert unit vectors (N,3) → (longitude, latitude) in radians."""
    x, y, z = directions[:, 0], directions[:, 1], directions[:, 2]
    lon = np.arctan2(y, x)
    lat = np.arcsin(np.clip(z, -1, 1))
    return lon, lat


def plot_mollweide(ax, lon, lat, values, title, cmap="viridis",
                   vmin=None, vmax=None, cbar_label="", marker_size=12):
    """Scatter-based Mollweide map on a pre-created projection axis."""
    if vmin is None:
        vmin = np.nanmin(values)
    if vmax is None:
        vmax = np.nanmax(values)
    norm = Normalize(vmin=vmin, vmax=vmax)
    sc = ax.scatter(lon, lat, c=values, cmap=cmap, s=marker_size,
                    norm=norm, edgecolors="none", rasterized=True)
    ax.set_title(title, fontsize=10, pad=6)
    ax.grid(False)
    # Clean up Mollweide ticks and grid artifacts
    ax.set_xticks([])
    ax.set_yticks([])
    ax.tick_params(axis='both', which='both', length=0, width=0, pad=0)
    cb = plt.colorbar(sc, ax=ax, shrink=0.75, pad=0.04, aspect=25)
    cb.set_label(cbar_label, fontsize=8)
    cb.ax.tick_params(labelsize=7)
    return sc


# ---------------------------------------------------------------------------
# Main computation + plotting
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Polarisation Response Mollweide Maps (Task 2)."
    )
    parser.add_argument("--mode", choices=["png", "pdf"], default="png",
                        help="Output format (default: png).")
    parser.add_argument("--outdir", type=str, default=None,
                        help="Output directory (default: monograph/figures).")
    parser.add_argument("--n_dirs", type=int, default=2000,
                        help="Number of fibonacci-sphere directions (default: 2000).")
    parser.add_argument("--stl", type=str, default=None,
                        help="Path to STL file (default: data/thelonious.stl).")
    parser.add_argument("--freq_ghz", type=float, default=28.0,
                        help="Frequency in GHz (default: 28).")
    args = parser.parse_args()

    # Paths
    stl_path = Path(args.stl) if args.stl else DATA_DIR / "thelonious.stl"
    out_dir = Path(args.outdir) if args.outdir else PROJECT_ROOT / "monograph" / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    freq_hz = args.freq_ghz * 1e9

    # Style
    apply_monograph_style(mode=args.mode)

    # -----------------------------------------------------------------------
    # 1. Tissue properties from IT'IS database
    # -----------------------------------------------------------------------
    n_tilde = get_tissue_n("Skin", freq_hz)
    print(f"Tissue: Skin at {args.freq_ghz} GHz")
    print(f"  n_tilde = {n_tilde.real:.4f} - j{-n_tilde.imag:.4f}")
    T0 = 4 * n_tilde.real / ((1 + n_tilde.real)**2 + n_tilde.imag**2)
    print(f"  T0 = {T0:.4f}")

    # -----------------------------------------------------------------------
    # 2. Load mesh
    # -----------------------------------------------------------------------
    print(f"\nLoading mesh: {stl_path}")
    vertices, normals, centroids = load_stl_binary(str(stl_path))
    areas = triangle_areas(vertices)
    phantom_name = stl_path.stem.capitalize()
    print(f"  {phantom_name}: {len(areas):,} triangles, "
          f"total area = {np.sum(areas)*1e4:.1f} cm²")

    # -----------------------------------------------------------------------
    # 3. Compute polarisation tables
    # -----------------------------------------------------------------------
    n_dirs = args.n_dirs
    print(f"\nComputing polarisation tables for {n_dirs} directions...")
    directions = fibonacci_sphere(n_dirs)
    A_tilde, Bc, Bs = compute_tables(
        normals=normals, areas=areas,
        directions=directions, n_complex=n_tilde,
    )

    # Derived quantities
    B_mag = np.sqrt(Bc**2 + Bs**2)          # |B̃(k̂)|
    D_B = B_mag / (2.0 * A_tilde)            # fractional correction
    D_B_pct = D_B * 100.0                     # in percent

    # -----------------------------------------------------------------------
    # 4. Cylinder bound (analytical)
    # -----------------------------------------------------------------------
    D_B_cyl = compute_cylinder_bound(n_tilde)
    print(f"\nCylinder bound D_B^cyl = {D_B_cyl*100:.1f}%")
    print(f"Worst-case D_B on {phantom_name} = {np.max(D_B)*100:.1f}%")
    print(f"Mean D_B on {phantom_name} = {np.mean(D_B)*100:.1f}%")
    print(f"Fraction of cylinder limit = {np.max(D_B)/D_B_cyl*100:.0f}%")

    # -----------------------------------------------------------------------
    # 5. Verification checks
    # -----------------------------------------------------------------------
    print("\n=== Verification ===")

    # Check B_s ≈ 0 for frontal illumination (k̂ ≈ ±ŷ)
    # Find directions closest to +y and -y
    for label, target in [("front (+y)", np.array([0, 1, 0])),
                          ("back (−y)", np.array([0, -1, 0]))]:
        dots = directions @ target
        idx = np.argmax(dots)
        print(f"  {label}: k̂ ≈ {directions[idx]}")
        print(f"    Ã_⊥ = {A_tilde[idx]:.6f},  B_c = {Bc[idx]:.6f},  "
              f"B_s = {Bs[idx]:.6f}")
        if abs(Bc[idx]) > 1e-10:
            print(f"    |B_s/B_c| = {abs(Bs[idx]/Bc[idx]):.4f}")
        print(f"    D_B = {D_B[idx]*100:.2f}%")

    # -----------------------------------------------------------------------
    # 6. Identify most polarisation-sensitive directions
    # -----------------------------------------------------------------------
    print("\n=== Most polarisation-sensitive directions ===")
    top_k = 10
    top_idx = np.argsort(D_B)[::-1][:top_k]
    for rank, idx in enumerate(top_idx, 1):
        k = directions[idx]
        lon_deg = np.degrees(np.arctan2(k[1], k[0]))
        lat_deg = np.degrees(np.arcsin(np.clip(k[2], -1, 1)))
        print(f"  #{rank}: D_B = {D_B[idx]*100:.1f}%,  "
              f"lon = {lon_deg:+6.1f}°,  lat = {lat_deg:+5.1f}°,  "
              f"k̂ = ({k[0]:+.3f}, {k[1]:+.3f}, {k[2]:+.3f})")

    # -----------------------------------------------------------------------
    # 7. Create figure
    # -----------------------------------------------------------------------
    lon, lat = directions_to_lonlat(directions)

    fig = plt.figure(figsize=(TEXTWIDTH_IN, TEXTWIDTH_IN * 0.72))

    # (a) Ã_⊥ Mollweide
    ax_a = fig.add_subplot(2, 2, 1, projection="mollweide")
    plot_mollweide(ax_a, lon, lat, A_tilde * 1e4, 
                   r"(a) $\tilde{A}_\perp(\hat{k})$" if args.mode == "pdf" 
                   else "(a) A_perp(k)",
                   cmap="cividis",
                   cbar_label="cm²" if args.mode == "pdf" else "cm^2",
                   marker_size=10)

    # (b) |B̃| Mollweide
    ax_b = fig.add_subplot(2, 2, 2, projection="mollweide")
    plot_mollweide(ax_b, lon, lat, B_mag * 1e4,
                   r"(b) $|\tilde{B}(\hat{k})|$" if args.mode == "pdf"
                   else "(b) |B(k)|",
                   cmap="inferno",
                   cbar_label="cm²" if args.mode == "pdf" else "cm^2",
                   marker_size=10)

    # (c) D_B Mollweide (capped at 30%)
    ax_c = fig.add_subplot(2, 2, 3, projection="mollweide")
    plot_mollweide(ax_c, lon, lat, np.clip(D_B_pct, 0, 30),
                   r"(c) $D_B(\hat{k})$" if args.mode == "pdf"
                   else "(c) D_B(k)  [%]",
                   cmap="RdYlGn_r", vmin=0, vmax=30,
                   cbar_label="%",
                   marker_size=10)

    # (d) Histogram of D_B
    ax_d = fig.add_subplot(2, 2, 4)
    ax_d.hist(D_B_pct, bins=50, color="#4C72B0", alpha=0.8, edgecolor="white",
              linewidth=0.3, density=True)
    # Vertical lines
    ax_d.axvline(np.max(D_B_pct), color="#C44E52", linestyle="-", linewidth=1.5,
                 label=f"max = {np.max(D_B_pct):.1f}%")
    ax_d.axvline(np.mean(D_B_pct), color="#DD8452", linestyle="--", linewidth=1.5,
                 label=f"mean = {np.mean(D_B_pct):.1f}%")
    ax_d.axvline(D_B_cyl * 100, color="#8C8C8C", linestyle=":", linewidth=1.5,
                 label=f"cylinder = {D_B_cyl*100:.1f}%")
    ax_d.set_xlabel(r"$D_B$ (\%)" if args.mode == "pdf" else r"D_B (\%)")
    ax_d.set_ylabel("Density")
    ax_d.set_title("(d) Distribution of $D_B$" if args.mode == "pdf"
                   else "(d) Distribution of D_B")
    ax_d.legend(fontsize=7, loc="upper right")
    ax_d.set_xlim(0, 32)

    fig.tight_layout(pad=1.2)

    # Save
    ext = args.mode
    fname = f"polarization_mollweide_thelonious.{ext}"
    out_path = out_dir / fname
    dpi = 250 if ext == "png" else None
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight")
    print(f"\nSaved: {out_path}")
    plt.close(fig)

    # -----------------------------------------------------------------------
    # 8. Summary statistics for report
    # -----------------------------------------------------------------------
    print("\n=== Summary Statistics ===")
    print(f"Phantom: {phantom_name}")
    print(f"Frequency: {args.freq_ghz} GHz")
    print(f"Directions: {n_dirs}")
    print(f"n_tilde = {n_tilde.real:.4f} - j{-n_tilde.imag:.4f}")
    print(f"T0 = {T0:.4f}")
    print(f"")
    print(f"Ã_⊥:  min={np.min(A_tilde)*1e4:.2f} cm²,  "
          f"max={np.max(A_tilde)*1e4:.2f} cm²,  "
          f"mean={np.mean(A_tilde)*1e4:.2f} cm²")
    print(f"|B̃|:  min={np.min(B_mag)*1e4:.2f} cm²,  "
          f"max={np.max(B_mag)*1e4:.2f} cm²,  "
          f"mean={np.mean(B_mag)*1e4:.2f} cm²")
    print(f"D_B:   min={np.min(D_B)*100:.2f}%,  "
          f"max={np.max(D_B)*100:.2f}%,  "
          f"mean={np.mean(D_B)*100:.2f}%,  "
          f"median={np.median(D_B)*100:.2f}%")
    print(f"Cylinder bound: {D_B_cyl*100:.1f}%")
    print(f"Fraction of cylinder limit: {np.max(D_B)/D_B_cyl*100:.0f}%")


if __name__ == "__main__":
    main()
