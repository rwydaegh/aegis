"""
Full dosimetric demonstration on the Thelonious anatomical phantom.

Computes every quantity from the geometric framework on a real phantom,
using the *exact* non-convex formulas (A_ab, not A/4):

  Single direction (frontal plane wave, k_hat from front):
    - Per-triangle S_ab(r) = S_inc · T_0 · ReLU[n̂·(−k̂)]
    - Total absorbed power  P_abs = S_inc · T_0 · A_perp(k̂)
    - Whole-body SAR         SAR_wb = P_abs / m
    - Peak S_ab              max S_ab = S_inc · T_0  (at normal incidence)
    - 4 cm² spatially averaged S_ab  →  peak <S_ab>_4cm2

  All-directions (isotropic illumination, same total S_inc):
    - Per-triangle S_ab(r) = S_total · T_0 · η(r) / 4
    - P_abs  = S_total · T_0 · A_ab / 4
    - SAR_wb = S_total · T_0 · A_ab / (4m)
    - Peak S_ab, peak <S_ab>_4cm2

  Worst-case direction:
    - Direction k̂* with max A_perp  →  worst-case P_abs, SAR_wb

  Timing for everything.

Outputs
-------
  artifacts/sab_demo/results.npz
  artifacts/sab_demo/summary.txt

Usage
-----
    python scripts/sab_demo.py
    python scripts/sab_demo.py --sinc 10 --freq 28e9

Author: Geometric Dosimetry project
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Tuple

import numpy as np

# Shared helpers (run from repo root: python scripts/sab_demo.py)
from _geom import load_stl_binary, triangle_areas
from _fresnel import n_complex as n_complex_from_params


# ---------------------------------------------------------------------------
# Physical / phantom parameters
# ---------------------------------------------------------------------------

# Thelonious = Virtual Population 6-year-old male (IT'IS Foundation)
THELONIOUS_MASS_KG = 20.0  # approximate mass


def tissue_T0(eps_r: float, sigma: float, freq_hz: float) -> float:
    """Normal-incidence power transmission coefficient T_0."""
    n = n_complex_from_params(eps_r, sigma, freq_hz)
    r = (1 - n) / (1 + n)
    return float(1 - abs(r) ** 2)


# ---------------------------------------------------------------------------
# 4 cm² spatial averaging
# ---------------------------------------------------------------------------

def build_averaging_matrix(
    centroids: np.ndarray,
    areas: np.ndarray,
    target_area_m2: float = 4e-4,  # 4 cm² in m²
) -> np.ndarray:
    """
    Build sparse row-stochastic averaging matrix G such that
        S̄_ab = G @ S_ab
    averages S_ab over ~4 cm² patches around each triangle.

    For each triangle i, find neighbours within a growing radius until
    the summed area ≥ target_area.  Then compute area-weighted average.

    Returns G as a dense (M, M) matrix (fine for 23k triangles: ~4 GB
    would be too large — we use a sparse approach internally and return
    the averaged result directly via `apply_averaging`).
    """
    # For 23k triangles, building a full (M,M) dense matrix is ~4 GB.
    # Instead, we provide an apply function.
    raise NotImplementedError("Use apply_spatial_averaging() instead.")


def apply_spatial_averaging(
    sab: np.ndarray,
    centroids: np.ndarray,
    areas: np.ndarray,
    target_area_m2: float = 4e-4,
) -> np.ndarray:
    """
    Apply ICNIRP 4 cm² spatial averaging to per-triangle S_ab.

    For each triangle, find the minimal set of neighbours (sorted by
    distance from centroid) whose cumulative area reaches target_area.
    The averaged S_ab is the area-weighted mean over that patch.

    Uses a KD-tree for efficient neighbour lookup.

    Parameters
    ----------
    sab : (M,) per-triangle absorbed power density
    centroids : (M, 3) triangle centroids
    areas : (M,) triangle areas
    target_area_m2 : float, default 4e-4 (= 4 cm²)

    Returns
    -------
    sab_avg : (M,) spatially averaged S_ab
    """
    from scipy.spatial import cKDTree

    M = len(sab)
    sab_avg = np.empty(M)

    tree = cKDTree(centroids)

    # Estimate search radius: for a roughly uniform mesh, the radius
    # to capture 4 cm² is sqrt(target_area / pi).  Multiply by 2 for safety.
    mean_tri_area = np.mean(areas)
    n_tri_needed = max(1, int(np.ceil(target_area_m2 / mean_tri_area)))
    r_est = np.sqrt(target_area_m2 / np.pi) * 2.5

    for i in range(M):
        # Query neighbours within estimated radius
        idx = tree.query_ball_point(centroids[i], r_est)

        if len(idx) == 0:
            sab_avg[i] = sab[i]
            continue

        idx = np.array(idx)

        # Sort by distance
        dists = np.linalg.norm(centroids[idx] - centroids[i], axis=1)
        order = np.argsort(dists)
        idx_sorted = idx[order]

        # Accumulate area until we reach target
        cum_area = np.cumsum(areas[idx_sorted])
        # Find cutoff
        cutoff = np.searchsorted(cum_area, target_area_m2, side='right')
        cutoff = max(cutoff, 1)  # at least one triangle
        # If we don't reach target area, use all we have (small patch)
        cutoff = min(cutoff, len(idx_sorted))

        patch_idx = idx_sorted[:cutoff]
        patch_areas = areas[patch_idx]
        patch_sab = sab[patch_idx]

        # Area-weighted average
        sab_avg[i] = np.average(patch_sab, weights=patch_areas)

    return sab_avg


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def compute_single_direction(
    normals: np.ndarray,
    areas: np.ndarray,
    k_hat: np.ndarray,
    T_0: float,
    S_inc: float,
    mass_kg: float,
) -> dict:
    """Compute all dosimetric quantities for a single plane wave direction."""
    k_hat = np.asarray(k_hat, dtype=np.float64)
    k_hat = k_hat / np.linalg.norm(k_hat)

    # μ = n̂ · (−k̂)
    mu = normals @ (-k_hat)
    mu_pos = np.maximum(0, mu)

    # Per-triangle S_ab
    sab = S_inc * T_0 * mu_pos

    # Projected area
    A_perp = float(np.sum(areas * mu_pos))

    # Total absorbed power
    P_abs = S_inc * T_0 * A_perp

    # Whole-body SAR (exact, not conservative bound)
    SAR_wb = P_abs / mass_kg

    # Peak S_ab
    peak_sab = float(np.max(sab))

    # Mean S_ab over illuminated triangles
    illuminated = mu_pos > 0
    mean_sab_illum = float(np.mean(sab[illuminated])) if np.any(illuminated) else 0.0

    return {
        'k_hat': k_hat,
        'sab': sab,
        'mu_pos': mu_pos,
        'A_perp': A_perp,
        'P_abs': P_abs,
        'SAR_wb': SAR_wb,
        'peak_sab': peak_sab,
        'mean_sab_illum': mean_sab_illum,
        'n_illuminated': int(np.sum(illuminated)),
    }


def compute_isotropic(
    eta: np.ndarray,
    areas: np.ndarray,
    T_0: float,
    S_total: float,
    mass_kg: float,
) -> dict:
    """Compute dosimetric quantities for isotropic illumination using η(r)."""
    # S_ab(r) = S_total · T_0 · η(r) / 4
    sab = S_total * T_0 * eta / 4.0

    # A_ab = ∫ η dA
    A_ab = float(np.sum(eta * areas))

    # P_abs = S_total · T_0 · A_ab / 4
    P_abs = S_total * T_0 * A_ab / 4.0

    # SAR_wb
    SAR_wb = P_abs / mass_kg

    # Peak S_ab
    peak_sab = float(np.max(sab))

    return {
        'sab': sab,
        'A_ab': A_ab,
        'P_abs': P_abs,
        'SAR_wb': SAR_wb,
        'peak_sab': peak_sab,
        'mean_sab': float(np.mean(sab)),
    }


def find_worst_case_direction(
    normals: np.ndarray,
    areas: np.ndarray,
    n_dirs: int = 4096,
) -> Tuple[np.ndarray, float, int]:
    """
    Find the direction with maximum projected area A_perp.

    Returns (k_hat_worst, A_perp_max, idx).
    """
    from compute_projected_area_table import fibonacci_sphere, compute_A_perp_lut

    k_dirs = fibonacci_sphere(n_dirs)
    A_perp = compute_A_perp_lut(normals, areas, k_dirs)
    idx = int(np.argmax(A_perp))
    return k_dirs[idx], float(A_perp[idx]), idx


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Full dosimetric demo on Thelonious.")
    p.add_argument("--stl", default=None, help="STL path (default: data/thelonious.stl)")
    p.add_argument("--eta_npz", default=None, help="eta.npz path")
    p.add_argument("--sinc", type=float, default=10.0,
                   help="Incident power density S_inc (W/m²), default 10")
    p.add_argument("--freq", type=float, default=28e9,
                   help="Frequency (Hz), default 28 GHz")
    p.add_argument("--mass", type=float, default=THELONIOUS_MASS_KG,
                   help="Body mass (kg)")
    p.add_argument("--out", default=None, help="Output directory")
    p.add_argument("--skip-4cm2", action="store_true",
                   help="Skip 4 cm² averaging (slow)")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    root = Path(__file__).resolve().parent.parent
    stl_path = Path(args.stl) if args.stl else root / "data" / "thelonious.stl"
    eta_path = Path(args.eta_npz) if args.eta_npz else root / "artifacts" / "eta" / "thelonious" / "eta.npz"
    out_dir = Path(args.out) if args.out else root / "artifacts" / "sab_demo"
    out_dir.mkdir(parents=True, exist_ok=True)

    S_inc = args.sinc
    freq_hz = args.freq
    mass_kg = args.mass

    # Skin dielectric properties at frequency
    # 28 GHz: eps_r ≈ 17, sigma ≈ 25 S/m (IT'IS v5.0)
    if abs(freq_hz - 28e9) < 1e9:
        eps_r, sigma = 17.0, 25.0
    elif abs(freq_hz - 60e9) < 1e9:
        eps_r, sigma = 7.9, 36.4
    else:
        print(f"WARNING: Using 28 GHz skin properties for freq={freq_hz/1e9:.1f} GHz")
        eps_r, sigma = 17.0, 25.0

    T_0 = tissue_T0(eps_r, sigma, freq_hz)
    n_tilde = n_complex_from_params(eps_r, sigma, freq_hz)

    print("=" * 72)
    print("  GEOMETRIC DOSIMETRY — FULL DEMONSTRATION")
    print("  Thelonious phantom · skin at {:.0f} GHz".format(freq_hz / 1e9))
    print("=" * 72)
    print(f"\n  S_inc       = {S_inc} W/m²")
    print(f"  Frequency   = {freq_hz/1e9:.0f} GHz")
    print(f"  Body mass   = {mass_kg} kg")
    print(f"  eps_r       = {eps_r}")
    print(f"  sigma       = {sigma} S/m")
    print(f"  n_tilde     = {n_tilde:.4f}  (|n| = {abs(n_tilde):.3f})")
    print(f"  T_0         = {T_0:.4f}")

    # ------------------------------------------------------------------
    # Load mesh
    # ------------------------------------------------------------------
    print(f"\nLoading mesh: {stl_path}")
    t0 = time.perf_counter()
    vertices, normals, centroids = load_stl_binary(str(stl_path))
    areas = triangle_areas(vertices)
    t_load = time.perf_counter() - t0

    M = len(areas)
    surface_area = float(np.sum(areas))
    print(f"  {M:,} triangles")
    print(f"  Surface area A = {surface_area:.6f} m²  ({surface_area*1e4:.1f} cm²)")
    print(f"  Load time: {t_load*1e3:.1f} ms")

    # ------------------------------------------------------------------
    # Load precomputed η
    # ------------------------------------------------------------------
    print(f"\nLoading η: {eta_path}")
    eta_data = np.load(str(eta_path))
    eta = eta_data['eta']
    assert eta.shape[0] == M, f"η length {eta.shape[0]} != mesh triangles {M}"

    A_ab = float(np.sum(eta * areas))
    eta_mean = float(np.mean(eta))
    eta_median = float(np.median(eta))
    print(f"  mean eta  = {eta_mean:.4f}")
    print(f"  median eta = {eta_median:.4f}")
    print(f"  A_ab    = {A_ab:.6f} m²  ({A_ab*1e4:.1f} cm²)")
    print(f"  A_ab/A  = {A_ab/surface_area:.4f}")

    # ==================================================================
    # 1) SINGLE DIRECTION — frontal plane wave
    # ==================================================================
    # Frontal: wave travels in -y direction (hits the front of the body)
    # Thelonious STL convention: +y is anterior (front)
    k_hat_front = np.array([0.0, -1.0, 0.0])

    print("\n" + "─" * 72)
    print("  1. SINGLE DIRECTION: frontal (k̂ = [0, −1, 0])")
    print("─" * 72)

    t0 = time.perf_counter()
    res_front = compute_single_direction(normals, areas, k_hat_front, T_0, S_inc, mass_kg)
    t_single = time.perf_counter() - t0

    print(f"\n  A_⊥(front) = {res_front['A_perp']*1e4:.2f} cm²")
    print(f"  P_abs      = {res_front['P_abs']*1e3:.3f} mW")
    print(f"  SAR_wb     = {res_front['SAR_wb']*1e3:.4f} mW/kg  "
          f"({res_front['SAR_wb']:.6f} W/kg)")
    print(f"  Peak S_ab  = {res_front['peak_sab']:.4f} W/m²")
    print(f"  Mean S_ab (illuminated) = {res_front['mean_sab_illum']:.4f} W/m²")
    print(f"  Illuminated triangles: {res_front['n_illuminated']:,} / {M:,}")
    print(f"  ⏱  Computation time: {t_single*1e3:.2f} ms")

    # Directivity for this direction: D = A_perp / <A_perp>
    # Use no-occlusion mean(A_perp) = A/4 for consistency with compute_body_directivity.py
    mean_A_perp = surface_area / 4.0
    D_front = res_front['A_perp'] / mean_A_perp
    print(f"  D(front)   = {D_front:.4f}")

    # ICNIRP checks
    icnirp_sar_limit = 0.08  # W/kg
    icnirp_sab_limit = 10.0  # W/m² (local peak, averaged over 4 cm²)
    print(f"\n  ICNIRP SAR_wb limit:  {icnirp_sar_limit} W/kg  → "
          f"{'COMPLIANT' if res_front['SAR_wb'] < icnirp_sar_limit else 'NON-COMPLIANT'}  "
          f"(margin: {(1 - res_front['SAR_wb']/icnirp_sar_limit)*100:.1f}%)")
    print(f"  ICNIRP S_ab limit:    {icnirp_sab_limit} W/m²  → "
          f"Peak raw: {res_front['peak_sab']:.2f} W/m²")

    # ==================================================================
    # 2) WORST-CASE DIRECTION
    # ==================================================================
    print("\n" + "─" * 72)
    print("  2. WORST-CASE DIRECTION (max A_⊥ over 4096 directions)")
    print("─" * 72)

    t0 = time.perf_counter()
    k_hat_worst, A_perp_max, idx_worst = find_worst_case_direction(normals, areas, n_dirs=4096)
    t_worst = time.perf_counter() - t0

    res_worst = compute_single_direction(normals, areas, k_hat_worst, T_0, S_inc, mass_kg)
    D_worst = A_perp_max / mean_A_perp

    print(f"\n  k̂*         = [{k_hat_worst[0]:.4f}, {k_hat_worst[1]:.4f}, {k_hat_worst[2]:.4f}]")
    print(f"  A_⊥(max)   = {A_perp_max*1e4:.2f} cm²")
    print(f"  D(max)     = {D_worst:.4f}")
    print(f"  P_abs      = {res_worst['P_abs']*1e3:.3f} mW")
    print(f"  SAR_wb     = {res_worst['SAR_wb']*1e3:.4f} mW/kg  "
          f"({res_worst['SAR_wb']:.6f} W/kg)")
    print(f"  ⏱  Direction search: {t_worst*1e3:.1f} ms")

    # ==================================================================
    # 3) ISOTROPIC ILLUMINATION (all directions, using η)
    # ==================================================================
    print("\n" + "─" * 72)
    print("  3. ISOTROPIC ILLUMINATION (S_total = S_inc = {:.1f} W/m²)".format(S_inc))
    print("─" * 72)

    t0 = time.perf_counter()
    res_iso = compute_isotropic(eta, areas, T_0, S_inc, mass_kg)
    t_iso = time.perf_counter() - t0

    print(f"\n  A_ab       = {res_iso['A_ab']*1e4:.2f} cm²")
    print(f"  P_abs      = {res_iso['P_abs']*1e3:.3f} mW")
    print(f"  SAR_wb     = {res_iso['SAR_wb']*1e3:.4f} mW/kg  "
          f"({res_iso['SAR_wb']:.6f} W/kg)")
    print(f"  Peak S_ab  = {res_iso['peak_sab']:.4f} W/m²")
    print(f"  Mean S_ab  = {res_iso['mean_sab']:.4f} W/m²")
    print(f"  ⏱  Computation time: {t_iso*1e3:.2f} ms")

    print(f"\n  ICNIRP SAR_wb:  "
          f"{'COMPLIANT' if res_iso['SAR_wb'] < icnirp_sar_limit else 'NON-COMPLIANT'}  "
          f"(margin: {(1 - res_iso['SAR_wb']/icnirp_sar_limit)*100:.1f}%)")

    # ==================================================================
    # 4) 4 cm² SPATIAL AVERAGING
    # ==================================================================
    sab_front_4cm2 = None
    sab_iso_4cm2 = None
    t_avg = 0

    if not args.skip_4cm2:
        print("\n" + "─" * 72)
        print("  4. SPATIAL AVERAGING (4 cm² ICNIRP patches)")
        print("─" * 72)

        t0 = time.perf_counter()

        print("\n  Averaging frontal S_ab over 4 cm² patches...")
        sab_front_4cm2 = apply_spatial_averaging(
            res_front['sab'], centroids, areas, target_area_m2=4e-4)
        t_mid = time.perf_counter()
        print(f"    Peak ⟨S_ab⟩_4cm² (front) = {np.max(sab_front_4cm2):.4f} W/m²")
        print(f"    ⏱  {(t_mid - t0)*1e3:.0f} ms")

        print("  Averaging isotropic S_ab over 4 cm² patches...")
        sab_iso_4cm2 = apply_spatial_averaging(
            res_iso['sab'], centroids, areas, target_area_m2=4e-4)
        t_avg = time.perf_counter() - t0
        print(f"    Peak ⟨S_ab⟩_4cm² (iso)   = {np.max(sab_iso_4cm2):.4f} W/m²")
        print(f"    ⏱  Total: {t_avg*1e3:.0f} ms")

        print(f"\n  ICNIRP peak ⟨S_ab⟩ limit: {icnirp_sab_limit} W/m²")
        print(f"    Frontal:   {np.max(sab_front_4cm2):.2f} W/m²  → "
              f"{'COMPLIANT' if np.max(sab_front_4cm2) < icnirp_sab_limit else 'NON-COMPLIANT'}")
        print(f"    Isotropic: {np.max(sab_iso_4cm2):.2f} W/m²  → "
              f"{'COMPLIANT' if np.max(sab_iso_4cm2) < icnirp_sab_limit else 'NON-COMPLIANT'}")

    # ==================================================================
    # SUMMARY TABLE
    # ==================================================================
    print("\n" + "=" * 72)
    print("  SUMMARY TABLE")
    print("=" * 72)
    print(f"\n  {'Quantity':<35s} {'Frontal':>12s} {'Worst-case':>12s} {'Isotropic':>12s}")
    print(f"  {'─'*35} {'─'*12} {'─'*12} {'─'*12}")
    print(f"  {'A_⊥ (cm²)':<35s} {res_front['A_perp']*1e4:>12.2f} {A_perp_max*1e4:>12.2f} {'—':>12s}")
    print(f"  {'P_abs (mW)':<35s} {res_front['P_abs']*1e3:>12.3f} {res_worst['P_abs']*1e3:>12.3f} {res_iso['P_abs']*1e3:>12.3f}")
    print(f"  {'SAR_wb (mW/kg)':<35s} {res_front['SAR_wb']*1e3:>12.4f} {res_worst['SAR_wb']*1e3:>12.4f} {res_iso['SAR_wb']*1e3:>12.4f}")
    print(f"  {'Peak S_ab (W/m²)':<35s} {res_front['peak_sab']:>12.4f} {res_worst['peak_sab']:>12.4f} {res_iso['peak_sab']:>12.4f}")
    if sab_front_4cm2 is not None:
        print(f"  {'Peak ⟨S_ab⟩_4cm² (W/m²)':<35s} {np.max(sab_front_4cm2):>12.4f} {'—':>12s} {np.max(sab_iso_4cm2):>12.4f}")
    print(f"  {'D(k̂)':<35s} {D_front:>12.4f} {D_worst:>12.4f} {'1.0000':>12s}")

    total_time = t_load + t_single + t_worst + t_iso + t_avg
    print(f"\n  Total wall time (all computations): {total_time*1e3:.0f} ms")
    print(f"    Mesh load:           {t_load*1e3:.1f} ms")
    print(f"    Single direction:    {t_single*1e3:.2f} ms")
    print(f"    Worst-case search:   {t_worst*1e3:.1f} ms")
    print(f"    Isotropic:           {t_iso*1e3:.2f} ms")
    if not args.skip_4cm2:
        print(f"    4 cm² averaging:     {t_avg*1e3:.0f} ms")

    # ==================================================================
    # Save
    # ==================================================================
    out_npz = out_dir / "results.npz"
    save_dict = {
        'S_inc': S_inc,
        'freq_hz': freq_hz,
        'T_0': T_0,
        'mass_kg': mass_kg,
        'surface_area': surface_area,
        'A_ab': res_iso['A_ab'],
        'M': M,
        # Frontal
        'sab_front': res_front['sab'],
        'k_hat_front': k_hat_front,
        'A_perp_front': res_front['A_perp'],
        'P_abs_front': res_front['P_abs'],
        'SAR_wb_front': res_front['SAR_wb'],
        'peak_sab_front': res_front['peak_sab'],
        'mean_A_perp': mean_A_perp,
        'D_front': D_front,
        # Worst case
        'k_hat_worst': k_hat_worst,
        'A_perp_worst': A_perp_max,
        'P_abs_worst': res_worst['P_abs'],
        'SAR_wb_worst': res_worst['SAR_wb'],
        'D_worst': D_worst,
        'sab_worst': res_worst['sab'],
        # Isotropic
        'sab_iso': res_iso['sab'],
        'P_abs_iso': res_iso['P_abs'],
        'SAR_wb_iso': res_iso['SAR_wb'],
        'peak_sab_iso': res_iso['peak_sab'],
        # Timing
        't_load_ms': t_load * 1e3,
        't_single_ms': t_single * 1e3,
        't_worst_ms': t_worst * 1e3,
        't_iso_ms': t_iso * 1e3,
    }
    if sab_front_4cm2 is not None:
        save_dict['sab_front_4cm2'] = sab_front_4cm2
        save_dict['sab_iso_4cm2'] = sab_iso_4cm2
        save_dict['peak_sab_front_4cm2'] = float(np.max(sab_front_4cm2))
        save_dict['peak_sab_iso_4cm2'] = float(np.max(sab_iso_4cm2))
        save_dict['t_4cm2_ms'] = t_avg * 1e3

    np.savez_compressed(str(out_npz), **save_dict)
    print(f"\n  Saved: {out_npz}")

    print("\n" + "=" * 72)
    print("  DONE")
    print("=" * 72)


if __name__ == "__main__":
    main()
