"""
26 GHz Mobile Phone Exposure on the Human Face
================================================

Computes the absorbed power density (APD) on the facial skin for
a 26 GHz mobile phone held at various distances, using the geometric
dosimetry framework.

Physical scenario
-----------------
A mobile phone radiating at 26 GHz (n258 / n261 band) is held at
distances from 5 cm to 1 m from the face.  The phone is modelled as
a point source with specified EIRP.

3GPP specifications (TS 38.101-2):
  - Power class 3:  max EIRP = 23 dBm  (200 mW)
  - Power class 1:  max EIRP = 40 dBm  (10 W) — base station only
  - Typical UE TRP: ~14–17 dBm with 6–10 dBi array gain

This script uses the point-source formula from the monograph:

    S_ab(r) = [P_t · G(k̂)] / [4π d(r)²] · T_0 · ReLU[n̂(r) · (−k̂(r))]

with T_0 computed from the IT'IS v5.0 4-Cole-Cole skin model at 26 GHz.

Outputs
-------
  1.  Summary table with incident and absorbed PD at reference distances
  2.  APD map on the phantom head (3D visualisation data)
  3.  Distance sweep: peak APD, 4-cm²-averaged APD vs distance
  4.  Comparison with ICNIRP 2020 limits and INERIS study levels
  5.  Publication-quality figure (PNG)

Author: Geometric Dosimetry project
"""

from __future__ import annotations

import sys, os, struct, sqlite3, cmath, time, argparse
from pathlib import Path
from typing import Optional

# Matplotlib backend BEFORE pyplot
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.colors import Normalize
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np

# Ensure scripts/ is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _geom import load_stl_binary, triangle_areas
from _fresnel import fresnel_transmission, n_complex as n_complex_from_params

# ===========================================================================
# Constants
# ===========================================================================
C_0 = 299792458.0       # speed of light [m/s]
EPS_0 = 8.854187817e-12 # vacuum permittivity [F/m]
Z_0 = 376.73            # free-space impedance [Ω]

# ===========================================================================
# IT'IS tissue database
# ===========================================================================
DB_PATHS = [
    Path(__file__).parent.parent / "data" / "itis_v5.db",
    Path(__file__).parent / "itis_v5.db",
]

def find_database():
    for p in DB_PATHS:
        if p.exists():
            return p
    raise FileNotFoundError("Could not find itis_v5.db")


def get_gabriel_params(tissue_name="Skin"):
    """Get 4-Cole-Cole parameters from the IT'IS v5 database."""
    db_path = find_database()
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute("SELECT prop_id FROM properties WHERE name = ?",
              ("Gabriel Parameters",))
    prop_id = c.fetchone()[0]
    c.execute(
        """SELECT v.vals FROM materials m
           JOIN vectors v ON m.mat_id = v.mat_id
           WHERE m.name = ? AND v.prop_id = ? LIMIT 1""",
        (tissue_name, prop_id),
    )
    blob = c.fetchone()[0]
    conn.close()
    vals = struct.unpack("d" * 14, blob[:14 * 8])
    return {
        "ef": vals[0],
        "del1": vals[1], "tau1": vals[2], "alf1": vals[3],
        "del2": vals[4], "tau2": vals[5], "alf2": vals[6],
        "del3": vals[7], "tau3": vals[8], "alf3": vals[9],
        "del4": vals[10], "tau4": vals[11], "alf4": vals[12],
        "sig": vals[13],
    }


def cole_cole_permittivity(freq_hz, params):
    """Complex permittivity from 4-Cole-Cole model."""
    omega = 2 * np.pi * freq_hz
    eps = complex(params["ef"], 0)
    tau_units = [1e-12, 1e-9, 1e-6, 1e-3]
    for i in range(4):
        delta = params[f"del{i+1}"]
        tau = params[f"tau{i+1}"] * tau_units[i]
        alpha = params[f"alf{i+1}"]
        if delta != 0 and tau != 0:
            eps += delta / (1 + (1j * omega * tau) ** (1 - alpha))
    if params["sig"] != 0 and omega != 0:
        eps -= 1j * params["sig"] / (omega * EPS_0)
    return eps


def get_tissue_props(freq_hz, tissue_name="Skin"):
    """Return (T_0, n_tilde, eps_c, skin_depth) at specified frequency."""
    params = get_gabriel_params(tissue_name)
    eps_c = cole_cole_permittivity(freq_hz, params)
    n_tilde = cmath.sqrt(eps_c)
    if n_tilde.real < 0:
        n_tilde = -n_tilde
    n_r = n_tilde.real
    kappa = abs(n_tilde.imag)
    T0 = 4 * n_r / ((1 + n_r)**2 + kappa**2)
    lam = C_0 / freq_hz
    skin_depth = lam / (2 * np.pi * kappa)
    return T0, n_tilde, eps_c, skin_depth


# ===========================================================================
# Flux-averaged transmission T_bar (exact for hemispherical averaging)
# ===========================================================================
def compute_Tbar(n_tilde, n_pts=500):
    """Flux-averaged transmission: Tbar = 2 * integral_0^1 Tavg(mu) * mu dmu."""
    mu = np.linspace(1e-6, 1.0, n_pts)
    Ts, Tp = fresnel_transmission(mu, n_tilde)
    Tavg = 0.5 * (Ts + Tp)
    # Trapezoidal integration
    Tbar = 2.0 * np.trapz(Tavg * mu, mu)
    return Tbar


# ===========================================================================
# Core computation: point-source APD on mesh
# ===========================================================================
def compute_point_source_apd(centroids, normals, areas, source_pos,
                              eirp_w, T0):
    """
    Per-triangle absorbed power density for an isotropic point source.

    S_ab(r_i) = EIRP / (4π d_i²) · T_0 · [n̂_i · (−k̂_i)]₊

    For a directional antenna, replace EIRP with P_t · G(k̂_i) per triangle.
    Here we assume isotropic (worst case for compliance — the phone
    beam points at the face).

    Returns
    -------
    sab : (N,) per-triangle APD in W/m²
    sinc : (N,) per-triangle incident PD in W/m²
    """
    diff = source_pos[None, :] - centroids      # (N, 3)
    d_sq = np.sum(diff**2, axis=1)              # (N,)
    d = np.sqrt(d_sq)                           # (N,)

    # Unit vector from surface to source → direction of incidence is opposite
    k_hat = diff / d[:, None]                   # (N, 3): toward source
    # μ = n̂ · (−k̂_propagation) = n̂ · (toward source)
    mu = np.sum(normals * k_hat, axis=1)        # (N,)
    mu_pos = np.maximum(mu, 0.0)                # ReLU

    # Incident power density
    sinc = eirp_w / (4 * np.pi * d_sq)          # (N,)

    # Absorbed power density
    sab = sinc * T0 * mu_pos                    # (N,)

    return sab, sinc, mu_pos


# ===========================================================================
# 4 cm² spatial averaging (ICNIRP compliance quantity)
# ===========================================================================
def apply_spatial_averaging(sab, centroids, areas,
                            target_area_m2=4e-4):
    """
    ICNIRP 4 cm² spatial averaging of per-triangle APD.

    For each triangle, find the nearest neighbours whose cumulative
    area reaches 4 cm² and compute the area-weighted average.
    """
    from scipy.spatial import cKDTree

    M = len(sab)
    sab_avg = np.empty(M)
    tree = cKDTree(centroids)

    # Estimate search radius
    r_est = np.sqrt(target_area_m2 / np.pi) * 2.5

    for i in range(M):
        idx = tree.query_ball_point(centroids[i], r_est)
        if len(idx) == 0:
            sab_avg[i] = sab[i]
            continue

        idx = np.array(idx)
        dists = np.linalg.norm(centroids[idx] - centroids[i], axis=1)
        order = np.argsort(dists)
        idx_sorted = idx[order]

        cum_area = np.cumsum(areas[idx_sorted])
        cutoff = np.searchsorted(cum_area, target_area_m2, side='right')
        cutoff = max(cutoff, 1)
        cutoff = min(cutoff, len(idx_sorted))

        patch_idx = idx_sorted[:cutoff]
        sab_avg[i] = np.average(sab[patch_idx], weights=areas[patch_idx])

    return sab_avg


# ===========================================================================
# Extract head region
# ===========================================================================
def extract_head(centroids, normals, areas, vertices,
                 z_fraction=0.12):
    """
    Extract the head region (top z_fraction of the body).

    Returns mask array.
    """
    bb_max = centroids.max(axis=0)
    bb_min = centroids.min(axis=0)
    extent = bb_max - bb_min
    # Find the vertical axis (axis with largest extent)
    up_axis = np.argmax(extent)
    z_threshold = bb_max[up_axis] - z_fraction * extent[up_axis]
    mask = centroids[:, up_axis] > z_threshold
    return mask


# ===========================================================================
# Find face center and approach direction
# ===========================================================================
def find_face_center(centroids, normals, head_mask):
    """
    Find the face center: the centroid of head triangles whose normals
    point predominantly forward (anterior).
    
    Excludes the vertical axis from face-direction candidates because
    the scalp always has many upward-facing normals.
    
    Returns face_center, face_normal (unit vector from face outward).
    """
    head_c = centroids[head_mask]
    head_n = normals[head_mask]

    # Identify the vertical axis: largest extent in the FULL body
    bb_full = centroids.max(axis=0) - centroids.min(axis=0)
    up_axis = int(np.argmax(bb_full))

    # Only consider the two horizontal axes for face direction
    # Try all 4 horizontal directions (+X, -X, +Y, -Y etc.) and pick
    # the one with the most outward-facing normals.
    horizontal_axes = [i for i in range(3) if i != up_axis]
    
    forward_candidates = []
    for axis in horizontal_axes:
        for sign in [1, -1]:
            direction = np.zeros(3)
            direction[axis] = sign
            dots = head_n @ direction
            n_facing = np.sum(dots > 0.3)
            forward_candidates.append((n_facing, direction))

    forward_candidates.sort(key=lambda x: -x[0])
    face_direction = forward_candidates[0][1]

    # Face triangles: head triangles whose normal has component > 0.3
    # along the face direction
    face_dots = head_n @ face_direction
    face_mask_local = face_dots > 0.3
    face_centroids = head_c[face_mask_local]

    face_center = face_centroids.mean(axis=0)

    return face_center, face_direction


# ===========================================================================
# Main computation
# ===========================================================================
def run_analysis(
    stl_name: str = "duke",
    freq_hz: float = 26e9,
    eirp_dbm: float = 23.0,
    out_dir: Optional[Path] = None,
):
    root = Path(__file__).resolve().parent.parent
    stl_path = root / "data" / f"{stl_name}.stl"
    if out_dir is None:
        out_dir = root / "artifacts" / "phone_exposure_26ghz"
    out_dir.mkdir(parents=True, exist_ok=True)

    # =================================================================
    # Tissue properties
    # =================================================================
    T0, n_tilde, eps_c, skin_depth = get_tissue_props(freq_hz)
    Tbar = compute_Tbar(n_tilde)
    lam = C_0 / freq_hz
    freq_ghz = freq_hz / 1e9

    print("=" * 74)
    print(f"  26 GHz MOBILE PHONE EXPOSURE ANALYSIS")
    print(f"  Phantom: {stl_name}")
    print("=" * 74)
    print(f"\n  Frequency        = {freq_ghz:.1f} GHz")
    print(f"  Wavelength       = {lam*1e3:.2f} mm")
    print(f"  Skin δ           = {skin_depth*1e3:.3f} mm")
    print(f"  ε_c              = {eps_c.real:.3f} − j{abs(eps_c.imag):.3f}")
    print(f"  ñ                = {n_tilde.real:.4f} − j{abs(n_tilde.imag):.4f}")
    print(f"  |ñ|              = {abs(n_tilde):.4f}")
    print(f"  T_0              = {T0:.4f}")
    print(f"  T̄  (flux-avg)    = {Tbar:.4f}")
    print(f"  R = T_0/T̄        = {T0/Tbar:.4f}")

    # =================================================================
    # EIRP / Power
    # =================================================================
    eirp_w = 10**((eirp_dbm - 30) / 10)
    print(f"\n  EIRP             = {eirp_dbm:.0f} dBm = {eirp_w*1e3:.1f} mW")

    # =================================================================
    # Load mesh
    # =================================================================
    print(f"\n  Loading mesh: {stl_path.name}")
    t0 = time.perf_counter()
    vertices, normals, centroids = load_stl_binary(str(stl_path))
    areas = triangle_areas(vertices)
    t_load = time.perf_counter() - t0

    M = len(areas)
    total_area = np.sum(areas)
    print(f"  {M:,} triangles, area = {total_area:.4f} m²")
    print(f"  Load time: {t_load*1e3:.0f} ms")

    # =================================================================
    # Extract head and find face
    # =================================================================
    head_mask = extract_head(centroids, normals, areas, vertices,
                             z_fraction=0.18)  # top 18%
    face_center, face_direction = find_face_center(centroids, normals,
                                                    head_mask)
    n_head = head_mask.sum()
    head_area = np.sum(areas[head_mask])

    print(f"\n  Head region: {n_head:,} triangles ({head_area*1e4:.1f} cm²)")
    print(f"  Face center: [{face_center[0]:.3f}, {face_center[1]:.3f}, "
          f"{face_center[2]:.3f}] m")
    print(f"  Face direction: [{face_direction[0]:.2f}, "
          f"{face_direction[1]:.2f}, {face_direction[2]:.2f}]")

    # =================================================================
    # Reference scenario: phone at 30 cm from face
    # =================================================================
    print("\n" + "─" * 74)
    print("  REFERENCE SCENARIO: EIRP = {:.0f} dBm at d = 30 cm".format(
        eirp_dbm))
    print("─" * 74)

    # Find the nose tip (furthest point along face_direction)
    head_c = centroids[head_mask]
    projections = head_c @ face_direction
    nose_tip_proj = np.max(projections)
    nose_tip_point = face_center + (nose_tip_proj - (face_center @ face_direction)) * face_direction

    d_ref = 0.30  # 30 cm
    source_ref = nose_tip_point + d_ref * face_direction

    sab_ref, sinc_ref, mu_ref = compute_point_source_apd(
        centroids[head_mask], normals[head_mask], areas[head_mask],
        source_ref, eirp_w, T0)

    # Free-space incident PD at reference distance (on-axis)
    sinc_center = eirp_w / (4 * np.pi * d_ref**2)
    E_center = np.sqrt(sinc_center * Z_0)

    peak_sab = np.max(sab_ref)
    mean_sab = np.mean(sab_ref[sab_ref > 0])
    peak_sinc = np.max(sinc_ref)

    # Total absorbed power on head
    P_abs_head = np.sum(sab_ref * areas[head_mask])

    print(f"\n  Source position   = face_center + 30cm × face_direction")
    print(f"  S_inc (on axis)  = {sinc_center:.4f} W/m²")
    print(f"  E_inc (on axis)  = {E_center:.2f} V/m")
    print(f"  Peak S_ab        = {peak_sab:.4f} W/m²")
    print(f"  Peak S_inc (any) = {peak_sinc:.4f} W/m²")
    print(f"  Mean S_ab (illum)= {mean_sab:.4f} W/m²")
    print(f"  P_abs (head)     = {P_abs_head*1e6:.2f} µW")

    # 4 cm² averaging on head
    print("\n  Computing 4 cm² averaging on head...")
    t0 = time.perf_counter()
    sab_4cm2 = apply_spatial_averaging(
        sab_ref, centroids[head_mask], areas[head_mask], 4e-4)
    t_avg = time.perf_counter() - t0
    peak_sab_4cm2 = np.max(sab_4cm2)
    print(f"  Peak ⟨S_ab⟩_4cm² = {peak_sab_4cm2:.4f} W/m²")
    print(f"  Averaging time: {t_avg:.1f} s")

    # =================================================================
    # Distance sweep
    # =================================================================
    print("\n" + "─" * 74)
    print("  DISTANCE SWEEP: 2 cm to 100 cm from face")
    print("─" * 74)

    distances = np.array([0.02, 0.05, 0.10, 0.15, 0.20, 0.30,
                          0.40, 0.50, 0.75, 1.00])

    sweep_results = []
    for d in distances:
        src = nose_tip_point + d * face_direction
        sab_d, sinc_d, mu_d = compute_point_source_apd(
            centroids[head_mask], normals[head_mask], areas[head_mask],
            src, eirp_w, T0)

        S_inc_axis = eirp_w / (4 * np.pi * d**2)
        E_axis = np.sqrt(S_inc_axis * Z_0)
        p_sab = np.max(sab_d)
        p_abs = np.sum(sab_d * areas[head_mask])

        sweep_results.append({
            'd_m': d,
            'S_inc_axis': S_inc_axis,
            'E_axis': E_axis,
            'peak_sab': p_sab,
            'P_abs_head_uW': p_abs * 1e6,
            'sab': sab_d,
        })

    # 4cm² averaging for key distances
    key_distances_idx = [i for i, r in enumerate(sweep_results)
                         if r['d_m'] in [0.05, 0.10, 0.20, 0.30, 0.50]]
    for idx in key_distances_idx:
        r = sweep_results[idx]
        sab_avg = apply_spatial_averaging(
            r['sab'], centroids[head_mask], areas[head_mask], 4e-4)
        r['peak_sab_4cm2'] = np.max(sab_avg)

    # Print results table
    print(f"\n  {'d (cm)':>7s}  {'S_inc':>10s}  {'E_inc':>8s}  "
          f"{'peak S_ab':>10s}  {'⟨S_ab⟩_4cm²':>12s}  {'P_abs':>10s}")
    print(f"  {'':>7s}  {'(W/m²)':>10s}  {'(V/m)':>8s}  "
          f"{'(W/m²)':>10s}  {'(W/m²)':>12s}  {'(µW)':>10s}")
    print(f"  {'─'*7}  {'─'*10}  {'─'*8}  {'─'*10}  {'─'*12}  {'─'*10}")
    for r in sweep_results:
        avg_str = f"{r.get('peak_sab_4cm2', float('nan')):.4f}" \
                  if 'peak_sab_4cm2' in r else "—"
        print(f"  {r['d_m']*100:>6.0f}   {r['S_inc_axis']:>10.4f}  "
              f"{r['E_axis']:>8.2f}  {r['peak_sab']:>10.4f}  "
              f"{avg_str:>12s}  {r['P_abs_head_uW']:>10.2f}")

    # =================================================================
    # EIRP sensitivity: what EIRP needed for ICNIRP limits?
    # =================================================================
    print("\n" + "─" * 74)
    print("  EIRP SENSITIVITY: What EIRP gives 1 W/m² at the face?")
    print("─" * 74)

    # At distance d, peak S_ab ≈ EIRP/(4πd²) * T_0
    # For S_ab = 1 W/m²: EIRP = 4πd² * 1 / T_0
    for d in [0.10, 0.20, 0.30, 0.50]:
        eirp_needed = 4 * np.pi * d**2 * 1.0 / T0
        eirp_needed_dbm = 10 * np.log10(eirp_needed * 1000)
        print(f"  d = {d*100:.0f} cm:  EIRP = {eirp_needed*1000:.1f} mW "
              f"= {eirp_needed_dbm:.1f} dBm for peak S_ab = 1 W/m²")

    # ICNIRP limit: 10 W/m² (general public, 4cm² average)
    print(f"\n  For S_ab = 10 W/m² (ICNIRP limit), at 30 cm:")
    eirp_10 = 4 * np.pi * 0.30**2 * 10.0 / T0
    print(f"  EIRP = {eirp_10*1000:.0f} mW = {10*np.log10(eirp_10*1000):.1f} dBm")
    print(f"  This is {10*np.log10(eirp_10*1000) - eirp_dbm:.1f} dB above "
          f"the UE max of {eirp_dbm:.0f} dBm")

    # =================================================================
    # Context for György: comparison with INERIS levels
    # =================================================================
    print("\n" + "─" * 74)
    print("  CONTEXT FOR HUMAN STUDY (György)")
    print("─" * 74)

    ineris_E = 2.0     # V/m
    ineris_S = 0.01    # W/m²
    proposed_E = 20.0   # V/m
    proposed_S = 1.0    # W/m²

    print(f"\n  INERIS far-field exposure:  E = {ineris_E} V/m, "
          f"S = {ineris_S} W/m²")
    print(f"  Proposed maximum:          E = {proposed_E} V/m, "
          f"S = {proposed_S} W/m²")

    # Find what distance gives these levels
    for label, S_target in [("INERIS (0.01 W/m²)", 0.01),
                            ("Proposed max (1 W/m²)", 1.0),
                            ("ICNIRP limit (10 W/m²)", 10.0)]:
        d_target = np.sqrt(eirp_w / (4 * np.pi * S_target))
        sab_target = S_target * T0
        print(f"\n  {label}:")
        print(f"    Distance for S_inc = {S_target} W/m²: "
              f"{d_target*100:.1f} cm")
        print(f"    Peak S_ab at this level: {sab_target:.4f} W/m²")
        print(f"    Peak E_field: {np.sqrt(S_target * Z_0):.2f} V/m")

    print(f"\n  At 30 cm from face (real phone scenario):")
    print(f"    S_inc = {sinc_center:.4f} W/m² = "
          f"{sinc_center/proposed_S*100:.1f}% of proposed 1 W/m²")
    print(f"    E_inc = {E_center:.2f} V/m = "
          f"{E_center/proposed_E*100:.1f}% of proposed 20 V/m")
    print(f"    Peak S_ab = {peak_sab:.4f} W/m²")
    print(f"    This is {peak_sab/1.0*100:.1f}% of the proposed 1 W/m²")
    print(f"    This is {peak_sab/10.0*100:.2f}% of the ICNIRP limit (10 W/m²)")

    # Check whether the proposed 1 W/m² is realistic
    print(f"\n  ⚠  CONCLUSION:")
    print(f"     The proposed 20 V/m (~1 W/m²) is about "
          f"{proposed_S/sinc_center:.0f}× ABOVE the real-life phone exposure")
    print(f"     at 30 cm.  This provides a safety margin for the study.")
    print(f"     A real 26 GHz phone at 30 cm gives only ~{E_center:.1f} V/m")
    print(f"     ({sinc_center:.3f} W/m²), well below the proposed level.")
    print(f"     The ICNIRP limit (10 W/m²) is ~{10/sinc_center:.0f}× above.")

    # =================================================================
    # Multi-EIRP comparison table
    # =================================================================
    print("\n" + "─" * 74)
    print("  MULTI-EIRP COMPARISON AT 30 cm")
    print("─" * 74)
    print(f"\n  {'Scenario':<35s} {'EIRP':>8s}  {'S_inc':>10s}  "
          f"{'E_inc':>8s}  {'S_ab':>10s}")
    print(f"  {'':35s} {'(dBm)':>8s}  {'(W/m²)':>10s}  "
          f"{'(V/m)':>8s}  {'(W/m²)':>10s}")
    print(f"  {'─'*35}  {'─'*8}  {'─'*10}  {'─'*8}  {'─'*10}")

    scenarios = [
        ("3GPP PC3 max (mobile phone)", 23),
        ("3GPP PC2 (higher capability)", 26),
        ("5G FWA CPE (fixed wireless)", 33),
        ("Small cell / femto BS", 35),
        ("Micro BS", 40),
    ]
    d_30 = 0.30
    for label, eirp_db in scenarios:
        eirp_val = 10**((eirp_db - 30) / 10)
        s_inc = eirp_val / (4 * np.pi * d_30**2)
        e_inc = np.sqrt(s_inc * Z_0)
        s_ab = s_inc * T0
        print(f"  {label:<35s} {eirp_db:>8.0f}  {s_inc:>10.4f}  "
              f"{e_inc:>8.2f}  {s_ab:>10.4f}")

    # =================================================================
    # Generate figure
    # =================================================================
    print("\n  Generating figure...")

    fig = plt.figure(figsize=(16, 10))
    fig.patch.set_facecolor('#0a0a1a')

    gs = gridspec.GridSpec(2, 3, figure=fig, wspace=0.35, hspace=0.40,
                           left=0.06, right=0.96, top=0.92, bottom=0.08)

    # Color scheme
    GOLD = '#FFD700'
    CYAN = '#00BFFF'
    MAGENTA = '#FF1493'
    GREEN = '#00FF7F'
    ORANGE = '#FF8C00'
    text_color = '#cccccc'

    for ax_spec in [gs[0, 0], gs[0, 1], gs[0, 2], gs[1, 0], gs[1, 1]]:
        ax = fig.add_subplot(ax_spec)
        ax.set_facecolor('#0f0f2a')
        ax.tick_params(colors=text_color, labelsize=8)
        ax.spines['bottom'].set_color('#333355')
        ax.spines['left'].set_color('#333355')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.xaxis.label.set_color(text_color)
        ax.yaxis.label.set_color(text_color)
        ax.title.set_color('white')

    # -------------------------------------------------------------------
    # Panel (a): Distance sweep — S_inc and S_ab vs distance
    # -------------------------------------------------------------------
    ax_a = fig.axes[0]
    d_dense = np.linspace(0.02, 1.0, 200)
    sinc_dense = eirp_w / (4 * np.pi * d_dense**2)
    sab_dense = sinc_dense * T0

    ax_a.semilogy(d_dense * 100, sinc_dense, color=CYAN, lw=2.0,
                  label=r'$S_{\rm inc}$')
    ax_a.semilogy(d_dense * 100, sab_dense, color=GOLD, lw=2.0,
                  label=r'Peak $S_{\rm ab} = S_{\rm inc} \times T_0$')

    # Mark key distances
    for d, r in [(30, sweep_results[5])]:
        ax_a.axvline(d, color='white', ls=':', alpha=0.3, lw=0.8)
        ax_a.plot(d, r['peak_sab'], 'o', color=GOLD, ms=8, zorder=5)
        ax_a.plot(d, r['S_inc_axis'], 'o', color=CYAN, ms=8, zorder=5)

    # Reference levels
    ax_a.axhline(1.0, color=ORANGE, ls='--', alpha=0.5, lw=1.0)
    ax_a.text(95, 1.15, r'Proposed 1 W/m²', fontsize=7, ha='right',
              color=ORANGE, alpha=0.7)
    ax_a.axhline(10.0, color=MAGENTA, ls='--', alpha=0.5, lw=1.0)
    ax_a.text(95, 12, r'ICNIRP 10 W/m²', fontsize=7, ha='right',
              color=MAGENTA, alpha=0.7)
    ax_a.axhline(0.01, color=GREEN, ls='--', alpha=0.5, lw=1.0)
    ax_a.text(95, 0.012, r'INERIS 0.01 W/m²', fontsize=7, ha='right',
              color=GREEN, alpha=0.7)

    ax_a.set_xlabel('Distance from face (cm)')
    ax_a.set_ylabel(r'Power density (W/m²)')
    ax_a.set_title(f'(a) Power density vs distance\nEIRP = {eirp_dbm:.0f} dBm '
                   f'({eirp_w*1e3:.0f} mW) at {freq_ghz:.0f} GHz',
                   fontsize=10)
    ax_a.legend(fontsize=8, facecolor='#1a1a3a', edgecolor='#333355',
                labelcolor=text_color)
    ax_a.set_xlim([2, 100])
    ax_a.set_ylim([1e-4, 100])

    # -------------------------------------------------------------------
    # Panel (b): E-field vs distance
    # -------------------------------------------------------------------
    ax_b = fig.axes[1]
    E_dense = np.sqrt(sinc_dense * Z_0)

    ax_b.semilogy(d_dense * 100, E_dense, color=CYAN, lw=2.0,
                  label=r'$E = \sqrt{S_{\rm inc} \times Z_0}$')

    ax_b.axhline(20.0, color=ORANGE, ls='--', alpha=0.5, lw=1.0)
    ax_b.text(95, 22, r'Proposed 20 V/m', fontsize=7, ha='right',
              color=ORANGE, alpha=0.7)
    ax_b.axhline(2.0, color=GREEN, ls='--', alpha=0.5, lw=1.0)
    ax_b.text(95, 2.2, r'INERIS 2 V/m', fontsize=7, ha='right',
              color=GREEN, alpha=0.7)
    ax_b.axhline(61.4, color=MAGENTA, ls='--', alpha=0.5, lw=1.0)
    ax_b.text(95, 70, r'ICNIRP 61 V/m', fontsize=7, ha='right',
              color=MAGENTA, alpha=0.7)

    ax_b.axvline(30, color='white', ls=':', alpha=0.3, lw=0.8)
    ax_b.plot(30, E_center, 'o', color=CYAN, ms=8, zorder=5)

    ax_b.set_xlabel('Distance from face (cm)')
    ax_b.set_ylabel(r'$E$-field (V/m)')
    ax_b.set_title('(b) Electric field strength vs distance', fontsize=10)
    ax_b.legend(fontsize=8, facecolor='#1a1a3a', edgecolor='#333355',
                labelcolor=text_color)
    ax_b.set_xlim([2, 100])
    ax_b.set_ylim([0.5, 200])

    # -------------------------------------------------------------------
    # Panel (c): EIRP comparison at 30 cm
    # -------------------------------------------------------------------
    ax_c = fig.axes[2]
    eirp_vals = np.array([e[1] for e in scenarios])
    sab_vals = np.array([10**((e[1]-30)/10)/(4*np.pi*0.09)*T0
                         for e in scenarios])
    labels_short = ['PC3\n(phone)', 'PC2\n(phone+)', 'FWA\nCPE',
                    'Femto\nBS', 'Micro\nBS']

    bars = ax_c.bar(range(len(scenarios)), sab_vals,
                    color=[CYAN, CYAN, GOLD, ORANGE, MAGENTA],
                    alpha=0.85, width=0.6)

    ax_c.axhline(1.0, color=ORANGE, ls='--', alpha=0.5, lw=1.2)
    ax_c.text(4.4, 1.1, '1 W/m²', fontsize=7, ha='right', color=ORANGE)
    ax_c.axhline(10.0, color=MAGENTA, ls='--', alpha=0.5, lw=1.2)
    ax_c.text(4.4, 11, '10 W/m²', fontsize=7, ha='right', color=MAGENTA)

    ax_c.set_xticks(range(len(scenarios)))
    ax_c.set_xticklabels(labels_short, fontsize=7, color=text_color)
    ax_c.set_ylabel(r'Peak $S_{\rm ab}$ (W/m²)')
    ax_c.set_title('(c) Peak APD at 30 cm by device class', fontsize=10)
    ax_c.set_yscale('log')
    ax_c.set_ylim([0.01, 30])

    # Add value labels on bars
    for bar_item, val in zip(bars, sab_vals):
        ax_c.text(bar_item.get_x() + bar_item.get_width()/2, val * 1.15,
                  f'{val:.2f}', ha='center', va='bottom',
                  fontsize=7, color='white')

    # -------------------------------------------------------------------
    # Panel (d): Framework illustration — S_ab on head cross-section
    # -------------------------------------------------------------------
    ax_d = fig.axes[3]

    # Show a polar-like plot of S_ab vs angle around the head
    # Use head triangles, project onto the plane perpendicular to z
    head_c = centroids[head_mask]
    head_center = head_c.mean(axis=0)

    # Angle of each triangle around the head (in the horizontal plane)
    dx = head_c[:, 0] - head_center[0]
    dy = head_c[:, 1] - head_center[1]
    angles = np.arctan2(dy, dx)
    angle_sorted = np.argsort(angles)

    # Bin the S_ab by angle
    n_bins = 72
    angle_bins = np.linspace(-np.pi, np.pi, n_bins + 1)
    sab_binned = np.zeros(n_bins)
    for b in range(n_bins):
        mask_bin = (angles >= angle_bins[b]) & (angles < angle_bins[b+1])
        if mask_bin.any():
            sab_binned[b] = np.average(sab_ref[mask_bin],
                                        weights=areas[head_mask][mask_bin])

    angle_centers = 0.5 * (angle_bins[:-1] + angle_bins[1:])

    # Convert to polar in a cartesian plot
    r_base = 1.0  # head radius (normalized)
    r_sab = r_base + sab_binned / np.max(sab_binned) * 0.6
    x_head = r_base * np.cos(angle_centers)
    y_head = r_base * np.sin(angle_centers)
    x_sab = r_sab * np.cos(angle_centers)
    y_sab = r_sab * np.sin(angle_centers)

    # Draw head outline
    theta_circle = np.linspace(0, 2*np.pi, 100)
    ax_d.plot(np.cos(theta_circle), np.sin(theta_circle),
              color='#555577', lw=1.5, ls='--', alpha=0.5)
    ax_d.fill(x_sab, y_sab, alpha=0.3, color=GOLD)
    ax_d.plot(x_sab, y_sab, color=GOLD, lw=1.5)

    # Draw source direction
    src_angle = np.arctan2(face_direction[1], face_direction[0])
    ax_d.annotate('', xy=(2.0*np.cos(src_angle), 2.0*np.sin(src_angle)),
                  xytext=(2.8*np.cos(src_angle), 2.8*np.sin(src_angle)),
                  arrowprops=dict(arrowstyle='->', color=CYAN, lw=2))
    ax_d.text(2.9*np.cos(src_angle), 2.9*np.sin(src_angle),
              'Phone\n(30 cm)', fontsize=7, ha='center', color=CYAN)

    # Label face and back
    ax_d.text(0, 0, 'Head\n(top view)', fontsize=8, ha='center',
              va='center', color=text_color, style='italic')

    ax_d.set_xlim([-3.5, 3.5])
    ax_d.set_ylim([-2.5, 2.5])
    ax_d.set_aspect('equal')
    ax_d.set_title(f'(d) APD distribution around head\n'
                   f'(ref: d = 30 cm, EIRP = {eirp_dbm:.0f} dBm)',
                   fontsize=10)
    ax_d.axis('off')

    # -------------------------------------------------------------------
    # Panel (e): Summary text
    # -------------------------------------------------------------------
    ax_e = fig.axes[4]
    ax_e.axis('off')

    summary_text = (
        f"SUMMARY: 26 GHz Mobile Phone Exposure\n"
        f"{'─' * 50}\n\n"
        f"Frequency:     {freq_ghz:.0f} GHz  (λ = {lam*1e3:.1f} mm)\n"
        f"Phantom:       {stl_name.capitalize()} ({n_head:,} head triangles)\n"
        f"Tissue:        Skin (IT'IS v5.0)\n"
        f"  T₀ = {T0:.4f},  |ñ| = {abs(n_tilde):.2f},  δ = {skin_depth*1e3:.2f} mm\n\n"
        f"Phone: 3GPP PC3,  EIRP = {eirp_dbm:.0f} dBm ({eirp_w*1e3:.0f} mW)\n\n"
        f"{'─' * 50}\n"
        f"AT 30 cm FROM FACE:\n"
        f"  Incident PD:    {sinc_center:.3f} W/m²\n"
        f"  E-field:        {E_center:.1f} V/m\n"
        f"  Peak S_ab:      {peak_sab:.3f} W/m²\n"
        f"  ⟨S_ab⟩₄cm²:    {peak_sab_4cm2:.3f} W/m²\n\n"
        f"{'─' * 50}\n"
        f"COMPARISON:\n"
        f"  INERIS study:   {ineris_E} V/m ({ineris_S} W/m²)\n"
        f"  Proposed max:   {proposed_E} V/m ({proposed_S} W/m²)\n"
        f"  Real phone@30cm: {E_center:.1f} V/m ({sinc_center:.3f} W/m²)\n"
        f"  ICNIRP limit:   61.4 V/m (10 W/m²)\n\n"
        f"  → Real exposure is ~{sinc_center/proposed_S*100:.0f}% of proposed max\n"
        f"  → Proposed 1 W/m² is ~{proposed_S/sinc_center:.0f}× above real phone\n"
        f"  → ICNIRP limit is ~{10/sinc_center:.0f}× above real phone"
    )

    ax_e.text(0.05, 0.95, summary_text, transform=ax_e.transAxes,
              fontsize=8, verticalalignment='top', fontfamily='monospace',
              color=text_color,
              bbox=dict(facecolor='#1a1a3a', edgecolor='#333355',
                        boxstyle='round,pad=0.5', alpha=0.8))

    ax_e.set_title('(e) Key Results', fontsize=10, color='white')

    # -------------------------------------------------------------------
    # Panel (f): Add a text panel in remaining space
    # -------------------------------------------------------------------
    ax_f = fig.add_subplot(gs[1, 2])
    ax_f.set_facecolor('#0f0f2a')
    ax_f.axis('off')

    methodology_text = (
        "METHODOLOGY\n"
        f"{'─' * 40}\n\n"
        "Geometric Dosimetry Framework:\n\n"
        "  S_ab(r) = S_inc(r) · T₀ · [n̂·(−k̂)]₊\n\n"
        "Point-source extension:\n\n"
        "  S_inc(r) = EIRP / (4π d²)\n\n"
        "Key assumptions:\n"
        "  • Phone modelled as isotropic source\n"
        "    (conservative: real beam is directional)\n"
        "  • Pseudo-Brewster compensation:\n"
        f"    T_avg ≈ T₀ = {T0:.3f} (max err: 5.6%)\n"
        "  • Geometric optics valid for\n"
        f"    d > 3λ = {3*lam*100:.1f} cm\n"
        "  • No diffraction modelling (conservative)\n\n"
        "4 cm² averaging:\n"
        "  ICNIRP 2020 compliance quantity\n"
        "  for local exposure above 6 GHz\n\n"
        "Tissue data:\n"
        "  IT'IS v5.0 4-Cole-Cole model\n"
        "  (Gabriel parametrisation)"
    )

    ax_f.text(0.05, 0.95, methodology_text, transform=ax_f.transAxes,
              fontsize=8, verticalalignment='top', fontfamily='monospace',
              color=text_color,
              bbox=dict(facecolor='#1a1a3a', edgecolor='#333355',
                        boxstyle='round,pad=0.5', alpha=0.8))

    ax_f.set_title('(f) Methodology', fontsize=10, color='white')

    # Main title
    fig.suptitle(
        f'26 GHz Mobile Phone Exposure on the Human Face — Geometric Dosimetry Analysis',
        fontsize=14, color='white', fontweight='bold', y=0.97)

    # Save
    fig_path = out_dir / "phone_exposure_26ghz.png"
    fig.savefig(str(fig_path), dpi=200, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"\n  Figure saved: {fig_path}")

    # =================================================================
    # Save machine-readable results
    # =================================================================
    results_path = out_dir / "results.npz"
    np.savez_compressed(str(results_path),
        freq_hz=freq_hz,
        eirp_dbm=eirp_dbm,
        eirp_w=eirp_w,
        T0=T0,
        Tbar=Tbar,
        n_tilde_real=n_tilde.real,
        n_tilde_imag=n_tilde.imag,
        skin_depth=skin_depth,
        distances=distances,
        sinc_axis=[r['S_inc_axis'] for r in sweep_results],
        E_axis=[r['E_axis'] for r in sweep_results],
        peak_sab=[r['peak_sab'] for r in sweep_results],
        P_abs_head_uW=[r['P_abs_head_uW'] for r in sweep_results],
        peak_sab_4cm2_30cm=peak_sab_4cm2,
        face_center=face_center,
        face_direction=face_direction,
    )
    print(f"  Results saved: {results_path}")

    # =================================================================
    # Write summary markdown
    # =================================================================
    md_path = out_dir / "summary_for_gyorgy.md"
    with open(str(md_path), 'w', encoding='utf-8') as f:
        f.write("# 26 GHz Mobile Phone Exposure on the Human Face\n\n")
        f.write("## Key Question\n")
        f.write("What is the power density (field strength) that a 26 GHz "
                "mobile phone at ~30 cm from the face generates on the "
                "facial skin?\n\n")

        f.write("## Answer\n\n")
        f.write("### At 30 cm from the face (3GPP Power Class 3, EIRP = 23 dBm = 200 mW):\n\n")
        f.write(f"| Quantity | Value |\n")
        f.write(f"|----------|-------|\n")
        f.write(f"| Incident power density S_inc | **{sinc_center:.3f} W/m²** |\n")
        f.write(f"| Electric field strength | **{E_center:.1f} V/m** |\n")
        f.write(f"| Peak absorbed power density S_ab | **{peak_sab:.3f} W/m²** |\n")
        f.write(f"| Peak ⟨S_ab⟩ averaged over 4 cm² | **{peak_sab_4cm2:.3f} W/m²** |\n")
        f.write(f"| Total absorbed power on head | **{P_abs_head*1e6:.1f} µW** |\n\n")

        f.write("### Comparison with reference levels:\n\n")
        f.write(f"| Level | S (W/m²) | E (V/m) | vs phone@30cm |\n")
        f.write(f"|-------|----------|---------|---------------|\n")
        f.write(f"| INERIS study | 0.01 | 2.0 | "
                f"{0.01/sinc_center:.1f}× lower |\n")
        f.write(f"| Real phone@30cm | {sinc_center:.3f} | {E_center:.1f} | "
                f"**reference** |\n")
        f.write(f"| Proposed maximum | 1.0 | 20.0 | "
                f"{1.0/sinc_center:.0f}× higher |\n")
        f.write(f"| ICNIRP limit | 10.0 | 61.4 | "
                f"{10/sinc_center:.0f}× higher |\n\n")

        f.write("### Distance-dependent values:\n\n")
        f.write(f"| d (cm) | S_inc (W/m²) | E (V/m) | Peak S_ab (W/m²) | "
                f"⟨S_ab⟩_4cm² (W/m²) |\n")
        f.write(f"|--------|-------------|---------|-----------------|----"
                f"--------------|\n")
        for r in sweep_results:
            avg_str = f"{r.get('peak_sab_4cm2', float('nan')):.4f}" \
                      if 'peak_sab_4cm2' in r else "—"
            f.write(f"| {r['d_m']*100:.0f} | {r['S_inc_axis']:.4f} | "
                    f"{r['E_axis']:.2f} | {r['peak_sab']:.4f} | {avg_str} |\n")

        f.write("\n### Key conclusions:\n\n")
        f.write("1. **The real-life exposure at 30 cm is very low**: "
                f"~{sinc_center:.2f} W/m² incident, ~{peak_sab:.2f} W/m² "
                "absorbed (peak).\n\n")
        f.write("2. **The proposed maximum of 20 V/m (1 W/m²) is "
                "conservative**: it is about "
                f"{proposed_S/sinc_center:.0f}× above "
                "the real phone exposure at 30 cm.\n\n")
        f.write("3. **The INERIS level of 2 V/m (0.01 W/m²) is realistic** "
                "for far-field exposure at >1 m.\n\n")
        f.write("4. **4 cm² averaging has minimal effect at 30 cm** because "
                "the beam footprint is much wider than 4 cm² at this "
                "distance.\n\n")
        f.write("5. **At extreme close range (5 cm)**, the exposure reaches "
                f"~{sweep_results[1]['peak_sab']:.1f} W/m², still below "
                "the ICNIRP limit of 10 W/m².\n\n")

        f.write("## Technical details\n\n")
        f.write(f"- **Framework**: Geometric dosimetry (point-source formula)\n")
        f.write(f"- **Tissue model**: IT'IS v5.0, Skin, 4-Cole-Cole\n")
        f.write(f"- **Phantom**: {stl_name.capitalize()} (IT'IS Virtual "
                f"Population), head region ({n_head:,} triangles)\n")
        f.write(f"- **T₀**: {T0:.4f} (normal-incidence Fresnel transmission)\n")
        f.write(f"- **|ñ|**: {abs(n_tilde):.2f}\n")
        f.write(f"- **Skin depth**: {skin_depth*1e3:.2f} mm\n")
        f.write(f"- **Wavelength**: {lam*1e3:.1f} mm\n")
        f.write(f"- **Geometric optics valid for** d > 3λ = {3*lam*100:.1f} cm\n")
        f.write(f"- **Pseudo-Brewster error**: < 6% for 0°–75° incidence\n")

    print(f"  Summary saved: {md_path}")

    print("\n" + "=" * 74)
    print("  ANALYSIS COMPLETE")
    print("=" * 74)

    return sweep_results


# ===========================================================================
# CLI
# ===========================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="26 GHz mobile phone exposure analysis on human face."
    )
    parser.add_argument(
        "--phantom", type=str, default="duke",
        choices=["duke", "ella", "thelonious", "eartha"],
        help="Phantom STL to use (default: duke)."
    )
    parser.add_argument(
        "--freq", type=float, default=26.0,
        help="Frequency in GHz (default: 26)."
    )
    parser.add_argument(
        "--eirp", type=float, default=23.0,
        help="EIRP in dBm (default: 23, i.e. 3GPP PC3 max)."
    )
    parser.add_argument(
        "--outdir", type=str, default=None,
        help="Output directory."
    )
    args = parser.parse_args()

    out = Path(args.outdir) if args.outdir else None
    run_analysis(
        stl_name=args.phantom,
        freq_hz=args.freq * 1e9,
        eirp_dbm=args.eirp,
        out_dir=out,
    )
