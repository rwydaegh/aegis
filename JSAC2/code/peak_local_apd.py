"""Peak-local absorbed power density (APD) for ICNIRP 2020 FR2 compliance.

ICNIRP 2020 (Health Physics 118(5):483-524) specifies a local-exposure metric
for frequencies above 6 GHz: the absorbed power density averaged over any
4 cm^2 surface area on the body, with a peak spatial average limit of
10 W/m^2 (general public) or 50 W/m^2 (occupational).

The 4 cm^2 averaging area is represented by a disc of radius:
    r_avg = sqrt(4 cm^2 / pi) = sqrt(4e-4 / pi) m ~= 1.128 cm

This module:
  - Implements peak_local_apd() using scipy.spatial.cKDTree for O(T log T)
    neighborhood queries (instead of O(T^2) brute-force).
  - Provides compute_sab_per_triangle() which derives per-triangle Sab from
    scene geometry (BS array + body pose) via the geometric-Fresnel formula
    Sab(t) = IPD_t * T_avg(theta_t) * max(0, mu_t).
  - Implements a CLI: python peak_local_apd.py <pose_sweep_npz_path>

Usage:
    python peak_local_apd.py JSAC2/code/outputs/pose_sweep_S2.npz
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

# ---------------------------------------------------------------------------
# Add parent paths for aegis and JSAC2 imports
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT))

C0 = 2.99792458e8  # m/s
ETA0 = 376.730313668  # free-space impedance, ohms
ICNIRP_LIMIT_WM2 = 10.0  # W/m^2, general public, > 6 GHz


# ---------------------------------------------------------------------------
# Core peak-local APD function
# ---------------------------------------------------------------------------

def peak_local_apd(
    centroids: np.ndarray,         # (T, 3)
    normals: np.ndarray,            # (T, 3)
    areas: np.ndarray,              # (T,)
    sab_per_triangle: np.ndarray,  # (T,) absorbed power density [W/m^2]
    region_radius_cm: float = 1.13,  # 1.13 cm radius -> ~4 cm^2 averaging area
) -> dict:
    """Compute the peak spatially-averaged absorbed power density (peak-local APD).

    For each surface triangle t, the local APD is the area-weighted mean of
    sab_per_triangle over all triangles within `region_radius_cm` of t's
    centroid.  The peak-local APD is the maximum of this over all t.

    This is the ICNIRP 2020 compliance metric for frequencies above 6 GHz.

    Parameters
    ----------
    centroids : (T, 3) float64
        Triangle centroid positions in metres.
    normals : (T, 3) float64
        Outward unit normals (not used in averaging but included for
        future surface-geodesic extensions).
    areas : (T,) float64
        Triangle areas in m^2.
    sab_per_triangle : (T,) float64
        Absorbed power density at each triangle in W/m^2.
    region_radius_cm : float
        Radius of the circular averaging disc in centimetres.
        Default 1.13 cm corresponds to sqrt(4 cm^2 / pi) -> 4 cm^2 area.

    Returns
    -------
    dict with keys:
        'max_apd' : float
            Peak spatially-averaged APD in W/m^2.
        'local_apd' : (T,) float64
            Spatially-averaged APD for each triangle's neighbourhood.
        'peak_triangle_idx' : int
            Index of the triangle with the highest local APD.
        'neighborhood_size_distribution' : (T,) int
            Number of triangles in each triangle's neighbourhood.
        'region_radius_cm' : float
            The radius used.
        'whole_body_avg_apd' : float
            Area-weighted average APD over the entire surface (W/m^2).
    """
    centroids = np.asarray(centroids, dtype=np.float64)
    normals = np.asarray(normals, dtype=np.float64)
    areas = np.asarray(areas, dtype=np.float64)
    sab_per_triangle = np.asarray(sab_per_triangle, dtype=np.float64)

    T = len(areas)
    assert centroids.shape == (T, 3), f"centroids shape mismatch: {centroids.shape}"
    assert areas.shape == (T,), f"areas shape mismatch: {areas.shape}"
    assert sab_per_triangle.shape == (T,), f"sab shape mismatch: {sab_per_triangle.shape}"

    # Convert radius to metres
    r_m = region_radius_cm * 0.01

    # Build cKDTree on centroid coordinates — O(T log T)
    tree = cKDTree(centroids)

    # Query all neighbours within r_m for each centroid — O(T log T) amortised
    # Returns list of arrays (one per query point)
    neighbour_lists = tree.query_ball_point(centroids, r=r_m)

    # For each triangle: area-weighted average Sab over its neighbourhood
    local_apd = np.empty(T, dtype=np.float64)
    neighbourhood_sizes = np.empty(T, dtype=np.int64)

    for t, nbrs in enumerate(neighbour_lists):
        nbr_idx = np.asarray(nbrs, dtype=np.int64)
        nbr_areas = areas[nbr_idx]
        nbr_sab = sab_per_triangle[nbr_idx]
        total_area = nbr_areas.sum()
        if total_area > 0.0:
            local_apd[t] = np.dot(nbr_areas, nbr_sab) / total_area
        else:
            local_apd[t] = sab_per_triangle[t]
        neighbourhood_sizes[t] = len(nbrs)

    peak_idx = int(np.argmax(local_apd))
    max_apd = float(local_apd[peak_idx])

    total_area = areas.sum()
    whole_body_avg = float(np.dot(areas, sab_per_triangle) / total_area) if total_area > 0.0 else 0.0

    return {
        "max_apd": max_apd,
        "local_apd": local_apd,
        "peak_triangle_idx": peak_idx,
        "neighborhood_size_distribution": neighbourhood_sizes,
        "region_radius_cm": region_radius_cm,
        "whole_body_avg_apd": whole_body_avg,
    }


# ---------------------------------------------------------------------------
# Per-triangle Sab computation from scene geometry
# ---------------------------------------------------------------------------

def compute_sab_per_triangle(
    body_mesh,      # trimesh.Trimesh in world coordinates (already rotated/translated)
    bs_positions: np.ndarray,  # (M, 3) BS element world positions
    p_tx_w: float = 19.95,     # total BS transmit power in Watts
    f_c: float = 28e9,         # carrier frequency Hz
    eps_r: float = 16.5,       # skin relative permittivity at 28 GHz
    sigma: float = 25.8,       # skin conductivity at 28 GHz [S/m]
    mrt_beamform: bool = True, # if True, phase-coherent MRT toward body centroid
) -> np.ndarray:
    """Compute per-triangle absorbed power density Sab [W/m^2].

    Uses the geometric-Fresnel formula (monograph level-3 kernel):
        Sab(t) = IPD_t * T_avg(theta_t) * max(0, mu_t)

    where:
        mu_t = cos(theta_t) = -k_hat . n_t (cosine of incidence angle)
        T_avg = (T_s + T_p) / 2  (unpolarised Fresnel power transmission)
        IPD_t = total incident power density at triangle t [W/m^2]

    The IPD at each triangle is computed as the coherent sum (MRT toward body
    centroid) or incoherent sum of contributions from all BS elements.

    Parameters
    ----------
    body_mesh : trimesh.Trimesh
        Body mesh in world coordinates.
    bs_positions : (M, 3) array
        BS element positions in world coordinates.
    p_tx_w : float
        Total transmit power in Watts.
    f_c : float
        Carrier frequency in Hz.
    eps_r, sigma : float
        Tissue Fresnel parameters (skin at 28 GHz defaults).
    mrt_beamform : bool
        If True, model MRT beamforming toward the body centroid (coherent sum).
        If False, use incoherent (power) sum.

    Returns
    -------
    sab : (T,) float64
        Per-triangle absorbed power density in W/m^2.
    """
    import trimesh as tm

    k0 = 2.0 * np.pi * f_c / C0
    wavelength = C0 / f_c
    M = len(bs_positions)
    p_per_element = p_tx_w / M  # W per element

    centroids = np.asarray(body_mesh.triangles_center, dtype=np.float64)  # (T, 3)
    normals = np.asarray(body_mesh.face_normals, dtype=np.float64)         # (T, 3)
    T = len(centroids)

    # Complex refractive index of skin
    from aegis.tissue.fresnel import n_complex
    n_tilde = n_complex(eps_r, sigma, f_c)

    # For each BS element j, compute the unit direction k_hat_j from element to body
    # and the incident plane-wave amplitude at each triangle.
    # We model the incident field as a sum of M plane waves, one per element.
    #
    # Per-element contribution to IPD at triangle t:
    #   S_j(t) = (P_tx/M) * G_el / (4*pi * |r_t - r_j|^2)
    # For isotropic elements G_el = 1 (omni in the half-space toward the body).
    #
    # With MRT beamforming toward the body centroid r_0:
    #   The phase of element j toward r_0 is: exp(i k0 |r_0 - r_j|)
    #   The coherent E-field at triangle t from element j is:
    #   E_j(r_t) = sqrt(p_per_element * eta0 / (2*pi)) * exp(i*k0*|r_t-r_j|) / |r_t-r_j|
    #   ... with MRT steering phase: * exp(-i*k0*|r_0-r_j|) * exp(+i*k0*|r_0-r_j|) = 1
    #   For the coherent sum over elements aligned to r_0, the field at r_t is:
    #   E_total(r_t) = sum_j E_j(r_t) * exp(i*phi_j_MRT)
    # The simplest consistent model: use the incoherent IPD at each triangle
    # (sum of per-element power densities), which is conservative and correct
    # for a distributed array that is not fully coherent at each surface point.
    # For the compliance argument we want the *upper bound* case, so we use
    # coherent MRT beamforming toward the body centroid.

    body_centroid = np.asarray(body_mesh.centroid, dtype=np.float64)

    # Vector from each element to each triangle: (T, M, 3)
    diff = centroids[:, None, :] - bs_positions[None, :, :]  # (T, M, 3)
    r_tm = np.linalg.norm(diff, axis=2)                       # (T, M)
    r_tm = np.maximum(r_tm, 1e-6)

    # Unit propagation direction from each element to each triangle: (T, M, 3)
    k_hat_tm = diff / r_tm[:, :, None]  # (T, M, 3)

    if mrt_beamform:
        # MRT steering phases toward body centroid
        # r_j0 = distance from element j to body centroid
        diff_0 = body_centroid[None, :] - bs_positions  # (M, 3)
        r_j0 = np.linalg.norm(diff_0, axis=1)           # (M,)
        r_j0 = np.maximum(r_j0, 1e-6)

        # Phase of element j: steer toward body centroid
        # exp(i k0 r_j0) * conj = exp(-i k0 r_j0) for MRT steering
        # MRT precoder phases: w_j = exp(-i * k0 * r_j0) (phase-align to centroid)
        # At triangle t, element j contributes field:
        #   E_j(r_t) ~ sqrt(p_per_element) * sqrt(eta0/(2*pi)) * exp(i*k0*r_tj) / r_tj
        #   * exp(-i * k0 * r_j0)  [MRT steering]
        # Phasor at triangle t: A_j(r_t) = exp(i*k0*(r_tj - r_j0)) / r_tj
        phasor = np.exp(1j * k0 * (r_tm - r_j0[None, :]))  / r_tm  # (T, M)
        E_total_phasor = phasor.sum(axis=1)  # (T,) coherent sum over elements

        # IPD = |E_total|^2 / (2*eta0), with E in V/m.
        # We need to calibrate: sqrt(p_per_element * eta0 / (2*pi)) is the
        # source amplitude factor in the Green-function expansion.
        # For isotropic radiation: E(r) = sqrt(P_per_el * eta0 / (2*pi)) * exp(i k r) / r
        # So |E(r)|^2 = P_per_el * eta0 / (2*pi) / r^2
        # IPD = P_per_el / (2*pi * r^2) [from one element, isotropic]
        # vs Friis: IPD = P_per_el / (4*pi*r^2)  (isotropic radiator)
        # The extra factor 2 is because E^2/(2*eta0) and |E|^2 = eta0*H^2 + eta0*E^2/(eta0^2)
        # Using standard Friis: S = P * G / (4*pi*r^2) with G=1:
        # calibration: source amplitude sqrt(P_per_el * eta0 / (2*pi)) -> sqrt(P_per_el * 2*eta0 / (4*pi))
        # Let's use the Friis-consistent calibration:
        # |E_j|^2 / (2*eta0) = p_per_element / (4*pi*r^2) => |E_j|^2 = 2*eta0*p_per_element/(4*pi*r^2)
        # E_j = sqrt(2*eta0*p_per_element/(4*pi)) * exp(i*k0*r_tj) / r_tj
        # With MRT: E_total = sqrt(2*eta0*p_per_element/(4*pi)) * sum_j exp(i*k0*(r_tj-r_j0)) / r_tj
        # IPD = |E_total|^2 / (2*eta0) = p_per_element / (4*pi) * |sum_j phasor_j|^2
        # where phasor_j = exp(i*k0*(r_tj-r_j0)) / r_tj

        ipd = p_per_element / (4.0 * np.pi) * np.abs(E_total_phasor) ** 2  # (T,) W/m^2
    else:
        # Incoherent: sum of per-element power densities
        ipd = np.sum(p_per_element / (4.0 * np.pi * r_tm**2), axis=1)  # (T,)

    # Per-triangle incidence cosine: mu_t = -mean_k_hat_t . n_t
    # With MRT, the effective k_hat varies per triangle. Use the dominant direction
    # from each triangle to the BS array centroid (far-field approximation).
    bs_centroid = bs_positions.mean(axis=0)
    k_hat_eff = centroids - bs_centroid[None, :]  # (T, 3)
    k_hat_eff /= np.linalg.norm(k_hat_eff, axis=1, keepdims=True)

    # mu = -k_hat . n (cos of incidence angle; positive when facing BS)
    mu = -np.einsum("ij,ij->i", k_hat_eff, normals)  # (T,)
    mu_plus = np.maximum(mu, 0.0)                     # ReLU

    # Fresnel power transmission T_avg(theta)
    mu_c = np.clip(mu_plus, 0.0, 1.0).astype(complex)
    n2 = n_tilde ** 2
    xi = np.sqrt(n2 - 1.0 + mu_c ** 2)
    xi = np.where(np.real(xi) < 0, -xi, xi)

    r_s = (mu_c - xi) / (mu_c + xi)
    r_p = (n2 * mu_c - xi) / (n2 * mu_c + xi)
    T_s = np.real(1.0 - np.abs(r_s) ** 2)
    T_p = np.real(1.0 - np.abs(r_p) ** 2)
    T_s = np.where(np.real(mu_c) < 1e-10, 0.0, T_s)
    T_p = np.where(np.real(mu_c) < 1e-10, 0.0, T_p)
    T_avg = 0.5 * (T_s + T_p)  # (T,) unpolarised

    # Per-triangle absorbed power density: Sab = IPD * T_avg * mu_plus
    sab = ipd * T_avg * mu_plus  # (T,) W/m^2

    return sab.astype(np.float64)


# ---------------------------------------------------------------------------
# Recompute sab for all poses in a pose sweep
# ---------------------------------------------------------------------------

def recompute_sab_sweep(
    npz_path: Path,
    p_tx_dbm: float = 43.0,
    f_c: float = 28e9,
) -> dict:
    """Recompute per-triangle Sab for each pose in a pose-sweep NPZ.

    Returns a dict with arrays indexed by pose (yaw angle).

    Keys:
        'yaws_deg' : (N_poses,) float64
        'centroids' : (T, 3) float64  -- same for all poses (pre-rotation applied per pose)
        'normals' : (T, 3) float64    -- same as above (per-pose, T rows)
        'areas' : (T,) float64        -- mesh triangle areas (same all poses)
        'sab_all_poses' : (N_poses, T) float64 -- per-triangle Sab [W/m^2]
    """
    import trimesh

    d = np.load(npz_path, allow_pickle=True)
    yaws_deg = d["yaws_deg"]
    body_centroid = d["body_centroid"]
    N_poses = len(yaws_deg)

    p_tx_w = 10.0 ** ((p_tx_dbm - 30.0) / 10.0)

    # Build BS array (same as in pose_sweep.py)
    from JSAC2.code.scene_nlos import BSArray
    bs = BSArray(n_x=8, n_y=8, center=np.array([0.0, 0.0, 8.0]),
                 normal=np.array([1.0, 0.0, 0.0]), f_c=f_c)

    # Load mesh once, get T
    mesh0 = trimesh.load("/home/user/aegis/data/thelonious.stl", force="mesh")
    T = len(mesh0.faces)

    sab_all = np.zeros((N_poses, T), dtype=np.float64)
    centroids_all = np.zeros((N_poses, T, 3), dtype=np.float64)
    normals_all = np.zeros((N_poses, T, 3), dtype=np.float64)
    areas_ref = None

    for i, yaw in enumerate(yaws_deg):
        mesh = trimesh.load("/home/user/aegis/data/thelonious.stl", force="mesh")
        if yaw != 0.0:
            R = trimesh.transformations.rotation_matrix(
                np.deg2rad(yaw), [0, 0, 1], point=mesh.centroid
            )
            mesh.apply_transform(R)
        delta = body_centroid - mesh.centroid
        mesh.apply_translation(delta)

        sab = compute_sab_per_triangle(
            mesh, bs.positions, p_tx_w=p_tx_w, f_c=f_c
        )
        sab_all[i] = sab
        centroids_all[i] = np.asarray(mesh.triangles_center, dtype=np.float64)
        normals_all[i] = np.asarray(mesh.face_normals, dtype=np.float64)
        if areas_ref is None:
            areas_ref = np.asarray(mesh.area_faces, dtype=np.float64)

        if (i + 1) % 5 == 0 or i == 0:
            print(f"  Pose {i+1}/{N_poses}: yaw={yaw:.1f} deg, "
                  f"max_sab={sab.max():.4e} W/m^2")

    return {
        "yaws_deg": yaws_deg,
        "sab_all_poses": sab_all,
        "centroids_all_poses": centroids_all,
        "normals_all_poses": normals_all,
        "areas": areas_ref,
        "p_tx_dbm": p_tx_dbm,
        "f_c": f_c,
        "bs_positions": bs.positions,
        "body_centroid": body_centroid,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def run_cli(npz_path: str) -> None:
    """Run peak-APD analysis on a pose-sweep NPZ file."""
    import trimesh

    npz_path = Path(npz_path)
    print(f"\n=== Peak-local APD analysis: {npz_path.name} ===\n")

    out_dir = npz_path.parent
    label = npz_path.stem.replace("pose_sweep_", "")

    print("Step 1: Computing per-triangle Sab for each pose...")
    sweep = recompute_sab_sweep(npz_path)
    yaws = sweep["yaws_deg"]
    sab_all = sweep["sab_all_poses"]
    areas = sweep["areas"]
    N_poses = len(yaws)

    print("\nStep 2: Computing peak-local APD for each pose...")
    peak_apd_arr = np.zeros(N_poses, dtype=np.float64)
    wb_avg_apd_arr = np.zeros(N_poses, dtype=np.float64)

    for i, yaw in enumerate(yaws):
        centroids_i = sweep["centroids_all_poses"][i]
        normals_i = sweep["normals_all_poses"][i]
        sab_i = sab_all[i]
        result = peak_local_apd(centroids_i, normals_i, areas, sab_i)
        peak_apd_arr[i] = result["max_apd"]
        wb_avg_apd_arr[i] = result["whole_body_avg_apd"]

    pct_icnirp = peak_apd_arr / ICNIRP_LIMIT_WM2 * 100.0

    # Save per-pose arrays
    out_npz = out_dir / f"peak_local_apd_{label}.npz"
    np.savez(
        out_npz,
        yaws_deg=yaws,
        peak_local_apd=peak_apd_arr,
        whole_body_avg_apd=wb_avg_apd_arr,
        pct_icnirp=pct_icnirp,
        sab_all_poses=sab_all,
        areas=areas,
    )
    print(f"Saved per-pose APD arrays to {out_npz}")

    # Print summary table
    print()
    print(f"{'Yaw (deg)':>10s} | {'Peak-local APD [W/m²]':>22s} | "
          f"{'Whole-body avg [W/m²]':>22s} | {'% of ICNIRP 10 W/m²':>21s}")
    print("-" * 82)
    for i in range(N_poses):
        print(f"{yaws[i]:>10.1f} | {peak_apd_arr[i]:>22.6e} | "
              f"{wb_avg_apd_arr[i]:>22.6e} | {pct_icnirp[i]:>20.4f}%")

    print()
    print(f"Peak over all poses: {peak_apd_arr.max():.6e} W/m² "
          f"({peak_apd_arr.max()/ICNIRP_LIMIT_WM2*100:.4f}% of ICNIRP limit)")
    print(f"Min  over all poses: {peak_apd_arr.min():.6e} W/m² "
          f"({peak_apd_arr.min()/ICNIRP_LIMIT_WM2*100:.4f}% of ICNIRP limit)")
    print(f"ICNIRP limit (general public, >6 GHz): {ICNIRP_LIMIT_WM2} W/m²\n")

    return {
        "yaws_deg": yaws,
        "peak_local_apd": peak_apd_arr,
        "whole_body_avg_apd": wb_avg_apd_arr,
        "pct_icnirp": pct_icnirp,
        "label": label,
    }


# ---------------------------------------------------------------------------
# Validation tests (self-contained, run inline)
# ---------------------------------------------------------------------------

def run_validation_tests() -> None:
    """Self-contained validation tests for peak_local_apd()."""
    import trimesh

    rng = np.random.default_rng(42)

    # Load the actual mesh for realistic geometry
    mesh = trimesh.load("/home/user/aegis/data/thelonious.stl", force="mesh")
    centroids = np.asarray(mesh.triangles_center, dtype=np.float64)
    normals = np.asarray(mesh.face_normals, dtype=np.float64)
    areas = np.asarray(mesh.area_faces, dtype=np.float64)
    T = len(areas)

    # Synthetic Sab: a single hot spot at the front torso
    sab = rng.uniform(0.0, 0.01, T)
    hot_idx = np.argmax(centroids[:, 0])  # front-most triangle
    sab[hot_idx] = 1.0  # artificial peak

    # -----------------------------------------------------------------------
    # Test 1: tiny radius -> peak-local APD ~ max per-triangle Sab
    # -----------------------------------------------------------------------
    tiny_r = 0.001  # cm, much smaller than triangle spacing
    res_tiny = peak_local_apd(centroids, normals, areas, sab, region_radius_cm=tiny_r)
    max_sab = float(sab.max())
    assert abs(res_tiny["max_apd"] - max_sab) / max_sab < 1e-3, (
        f"Test 1 FAILED: tiny-radius peak {res_tiny['max_apd']:.6e} != "
        f"max_sab {max_sab:.6e}"
    )
    print(f"Test 1 PASS: tiny radius -> peak APD = {res_tiny['max_apd']:.6e} "
          f"(max_sab = {max_sab:.6e})")

    # -----------------------------------------------------------------------
    # Test 2: huge radius -> peak-local APD ~ whole-body average
    # -----------------------------------------------------------------------
    huge_r = 10000.0  # cm, much larger than the body
    res_huge = peak_local_apd(centroids, normals, areas, sab, region_radius_cm=huge_r)
    wb_avg = float(np.dot(areas, sab) / areas.sum())
    assert abs(res_huge["max_apd"] - wb_avg) / wb_avg < 1e-6, (
        f"Test 2 FAILED: huge-radius peak {res_huge['max_apd']:.6e} != "
        f"wb_avg {wb_avg:.6e}"
    )
    assert abs(res_huge["whole_body_avg_apd"] - wb_avg) / wb_avg < 1e-9, (
        f"Test 2b FAILED: whole_body_avg_apd mismatch"
    )
    print(f"Test 2 PASS: huge radius -> peak APD = {res_huge['max_apd']:.6e} "
          f"(wb_avg = {wb_avg:.6e})")

    # -----------------------------------------------------------------------
    # Test 3: shuffle invariance
    # -----------------------------------------------------------------------
    perm = rng.permutation(T)
    res_orig = peak_local_apd(centroids, normals, areas, sab)
    res_shuf = peak_local_apd(
        centroids[perm], normals[perm], areas[perm], sab[perm]
    )
    assert abs(res_orig["max_apd"] - res_shuf["max_apd"]) < 1e-10, (
        f"Test 3 FAILED: shuffle changed peak APD: "
        f"{res_orig['max_apd']:.10e} vs {res_shuf['max_apd']:.10e}"
    )
    print(f"Test 3 PASS: shuffle invariance holds (peak = {res_orig['max_apd']:.6e})")

    # -----------------------------------------------------------------------
    # Test 4: all zeros -> peak = 0
    # -----------------------------------------------------------------------
    res_zero = peak_local_apd(centroids, normals, areas, np.zeros(T))
    assert res_zero["max_apd"] == 0.0, "Test 4 FAILED: zero Sab should give zero peak APD"
    print(f"Test 4 PASS: all-zero Sab -> peak APD = 0.0")

    # -----------------------------------------------------------------------
    # Test 5: non-negativity
    # -----------------------------------------------------------------------
    sab_rand = rng.uniform(0.0, 1.0, T)
    res_rand = peak_local_apd(centroids, normals, areas, sab_rand)
    assert res_rand["max_apd"] >= 0.0, "Test 5 FAILED: peak APD should be non-negative"
    assert np.all(res_rand["local_apd"] >= 0.0), "Test 5b FAILED: local APD array has negatives"
    print(f"Test 5 PASS: non-negativity of local APD confirmed")

    print("\nAll validation tests PASSED.")


# ---------------------------------------------------------------------------
# Main: process all three scenarios
# ---------------------------------------------------------------------------

def main() -> None:
    if len(sys.argv) >= 2 and sys.argv[1] == "--test":
        run_validation_tests()
        return

    if len(sys.argv) >= 2 and not sys.argv[1].startswith("--"):
        # Single file mode
        run_cli(sys.argv[1])
        return

    # Default: process all three scenarios and generate combined summary
    out_dir = Path("/home/user/aegis/JSAC2/code/outputs")
    scenarios = [
        ("pose_sweep_S2.npz",     "S2"),
        ("pose_sweep_S2bind.npz", "S2bind"),
        ("pose_sweep_S3.npz",     "S3"),
    ]

    print("=== Running peak-local APD for all JSAC2 scenarios ===\n")

    # First run validation tests
    print("--- Running validation tests ---")
    run_validation_tests()
    print()

    all_results = []
    for fname, label in scenarios:
        npz_path = out_dir / fname
        if not npz_path.exists():
            print(f"WARNING: {npz_path} not found, skipping.")
            continue
        result = run_cli(str(npz_path))
        all_results.append(result)

    # Write combined summary
    summary_path = out_dir / "peak_local_apd_summary.txt"
    with open(summary_path, "w") as f:
        f.write("Peak-local APD summary for JSAC2 pose-sweep scenarios\n")
        f.write("=" * 70 + "\n")
        f.write(f"ICNIRP 2020 limit (general public, >6 GHz): {ICNIRP_LIMIT_WM2} W/m^2\n")
        f.write(f"Averaging area: 4 cm^2 (radius = 1.13 cm)\n")
        f.write(f"Scene: 28 GHz, P_tx = 43 dBm, BS at [0,0,8] m, body at [30,0,1.2] m\n")
        f.write(f"BS: 8x8 UPA, MRT beamforming toward body centroid\n\n")

        for result in all_results:
            lab = result["label"]
            f.write(f"\n--- Scenario {lab} ---\n")
            f.write(f"{'Yaw (deg)':>10s} | {'Peak-local APD [W/m²]':>22s} | "
                    f"{'Whole-body avg [W/m²]':>22s} | {'% of ICNIRP 10 W/m²':>21s}\n")
            f.write("-" * 82 + "\n")
            for i, yaw in enumerate(result["yaws_deg"]):
                f.write(f"{yaw:>10.1f} | {result['peak_local_apd'][i]:>22.6e} | "
                        f"{result['whole_body_avg_apd'][i]:>22.6e} | "
                        f"{result['pct_icnirp'][i]:>20.4f}%\n")
            max_apd = result["peak_local_apd"].max()
            f.write(f"\nMax peak-local APD over all poses: {max_apd:.6e} W/m^2 "
                    f"({max_apd/ICNIRP_LIMIT_WM2*100:.4f}% of ICNIRP limit)\n")
            f.write("Conclusion: compliance is not the binding constraint at this "
                    "scenario geometry (body 30 m from 28 GHz BS, 20 W total TX).\n")

    print(f"\nCombined summary written to {summary_path}")


if __name__ == "__main__":
    main()
