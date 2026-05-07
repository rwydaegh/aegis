"""Near-field hotspot-tracking case study for direction 4 (codex + opus).

Question addressed: in Codex's earlier sim the worst patch index stayed at
14654 across all N. This script tests whether that is a *physical* coherent
hotspot or a *geometric* artifact (the single body triangle most normal
to -x). The test: vary the MRT focus point across the body and/or move the
antenna array closer to the phantom; if the worst patch follows the target,
it's physical; if it stays put, it's geometric.

Setup:
  - Real phantom:          thelonious (23,826 triangles, 0.79 m^2, h=1.18 m)
  - Tissue:                SKIN_28GHZ
  - Antenna array:         N elements on a square UPA of aperture
                           aperture_m, placed at position
                                p_array_center = r_target + d * n_hat_target
                           with orientation perpendicular to n_hat_target.
  - Each antenna emits a plane wave from direction (r_target - p_j)/||.||.
    Each path is co-polarised via a projection of e_vert onto k_hat^perp.
  - Precoder: MRT focused at r_target:
      x_j = exp(+i k0 k_hat_j . r_target)  (phases cancel at r_target).

Sweeps:
  - r_target over four body regions (chest/head/shoulder/thigh).
  - d over {5, 10, 30, 100} cm (near to far field for a 3 cm aperture).
  - N over {1, 4, 16, 64}.

Metrics reported per (target, d, N):
  - peak_apd_w_m2            = max over 4 cm^2 patches of APD
  - p_abs_w                  = x^H Q x
  - worst_patch_distance_cm  = || centroid(argmax) - r_target || * 100
  - eta_4cm2                 = peak_apd / (P_abs / A_body)
  - kappa_inv_m2             = peak_apd / P_abs               [m^-2]
  - A_eff_cm2                = 1 / kappa                       [cm^2]
  - array_angular_spread_deg = aperture_m / d  (rad -> deg)
  - apd_at_target_w_m2       = 4 cm^2 APD at the patch nearest r_target

A target-tracking score defined as:
  track = apd_at_target / peak_apd         in [0, 1]
  (1.0 = hotspot is exactly where we aimed; small = geometric artefact)

Output written to real_phantom_near_field_codex_opus.json.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from aegis.coherent.body_channel import compute_body_channel
from aegis.coherent.exposure_operator import compute_exposure_operator
from aegis.constants import C_0, Z_0
from aegis.geometry.averaging import precompute_averaging_matrix
from aegis.geometry.mesh import BodyMesh
from aegis.tissue.dielectric import SKIN_28GHZ

# Constants
ICNIRP_SAB_4CM2_PUBLIC = 20.0       # W/m^2
ICNIRP_SAR_WB_PUBLIC   = 0.08       # W/kg
AVERAGING_AREA_M2      = 4.0e-4     # 4 cm^2
ADULT_M_KG             = 70.0
ADULT_AREA_M2          = 1.8
AEFF_STAR_ADULT_M2     = ADULT_M_KG * ICNIRP_SAR_WB_PUBLIC / ICNIRP_SAB_4CM2_PUBLIC  # 0.28


def pick_body_target(body: BodyMesh, region: str) -> tuple[int, np.ndarray, np.ndarray]:
    """Pick a body triangle representative of the named region.

    Returns (triangle_index, centroid, outward_normal). The target for MRT
    is the centroid; the antenna array is offset along the outward normal.
    Regions are defined relative to thelonious's coordinate frame where
    +z is up, -y is toward the chest (empirical: min y side).
    """
    c = body.centroids
    n = body.normals
    z = c[:, 2]
    y = c[:, 1]
    x = c[:, 0]

    if region == "chest":
        # Upper torso front: moderate z, most -y, normal close to -y_hat
        mask = (z > -0.05) & (z < 0.05) & (y < -0.05) & (n[:, 1] < -0.5)
    elif region == "head":
        # Top of head: maximum z, normal close to +z_hat
        mask = (z > 0.15) & (n[:, 2] > 0.5)
    elif region == "shoulder":
        # Upper lateral: +x side, around shoulder height on thelonious
        mask = (z > -0.05) & (z < 0.10) & (x > 0.10) & (n[:, 0] > 0.3)
    elif region == "thigh":
        # Mid thigh front
        mask = (z > -0.55) & (z < -0.35) & (y < -0.02) & (n[:, 1] < -0.3)
    else:
        raise ValueError(f"unknown region {region!r}")

    idx_pool = np.where(mask)[0]
    if idx_pool.size == 0:
        raise RuntimeError(f"no triangle found in region {region!r}")
    # Pick the one with the strongest outward normal in its region direction
    # (helps ensure it's a good stand-in for a flat illumination target)
    if region == "chest":
        scores = -n[idx_pool, 1]
    elif region == "head":
        scores = n[idx_pool, 2]
    elif region == "shoulder":
        scores = n[idx_pool, 0]
    elif region == "thigh":
        scores = -n[idx_pool, 1]
    else:
        scores = np.ones(idx_pool.size)
    idx = idx_pool[int(np.argmax(scores))]
    return int(idx), c[idx].copy(), n[idx].copy()


def build_upa_positions(center: np.ndarray, n_hat: np.ndarray, N: int, aperture_m: float):
    """Build N antenna positions on a planar grid of side aperture_m,
    centered at `center` with plane normal to `n_hat`.

    For non-square N, uses the smallest enclosing square grid and selects the
    first N positions in row-major order. Returns (N, 3) positions.
    """
    # Two orthonormal axes in the plane perpendicular to n_hat
    n_hat = n_hat / np.linalg.norm(n_hat)
    ref = np.array([0.0, 0.0, 1.0]) if abs(n_hat[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    u = np.cross(n_hat, ref)
    u /= np.linalg.norm(u)
    v = np.cross(n_hat, u)

    side = int(np.ceil(np.sqrt(N)))
    if side == 1:
        return center[None, :].copy()
    # grid coordinates in [-aperture/2, aperture/2]
    ts = np.linspace(-aperture_m / 2, aperture_m / 2, side)
    uu, vv = np.meshgrid(ts, ts, indexing="ij")
    offs = uu[..., None] * u[None, None, :] + vv[..., None] * v[None, None, :]
    positions = center[None, None, :] + offs
    positions = positions.reshape(-1, 3)[:N]
    return positions


def project_polarisation(k_hat: np.ndarray, e_ref: np.ndarray) -> np.ndarray:
    """Project e_ref onto the plane perpendicular to each k_hat row. Returns
    (N, 3) unit vectors."""
    # e_perp = e_ref - (e_ref . k_hat) k_hat
    proj = (k_hat @ e_ref)[:, None] * k_hat
    e_perp = e_ref[None, :] - proj
    norm = np.linalg.norm(e_perp, axis=1, keepdims=True)
    # if e_ref is parallel to some k_hat, fallback to another axis
    bad = (norm[:, 0] < 1e-6)
    if np.any(bad):
        e_alt = np.array([1.0, 0.0, 0.0]) if abs(e_ref[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
        proj_alt = (k_hat[bad] @ e_alt)[:, None] * k_hat[bad]
        e_perp[bad] = e_alt[None, :] - proj_alt
        norm[bad] = np.linalg.norm(e_perp[bad], axis=1, keepdims=True)
    return e_perp / norm


_CACHE: dict = {}


def _get_body_and_averaging():
    if "body" not in _CACHE:
        body = BodyMesh.load(REPO_ROOT / "data" / "thelonious.stl")
        G_avg = precompute_averaging_matrix(body.centroids, body.areas, AVERAGING_AREA_M2)
        _CACHE["body"] = body
        _CACHE["G_avg"] = G_avg
    return _CACHE["body"], _CACHE["G_avg"]


def run_one(
    region: str,
    distance_m: float,
    N: int,
    aperture_m: float = 0.03,
    freq_hz: float = 28e9,
    P_tx: float = 1.0,
    e_vert: np.ndarray | None = None,
) -> dict:
    """Run one (region, distance, N) configuration and return metrics."""
    body, G_avg = _get_body_and_averaging()
    tri_idx, r_target, n_hat = pick_body_target(body, region)
    p_center = r_target + distance_m * n_hat
    positions = build_upa_positions(p_center, n_hat, N, aperture_m)
    N_eff = positions.shape[0]

    # Directions from each antenna to the target (propagation direction)
    vec = r_target[None, :] - positions  # (N, 3)
    dist = np.linalg.norm(vec, axis=1, keepdims=True)
    k_hat = vec / dist

    # Polarisation reference: vertical if n_hat not vertical, else horizontal
    if e_vert is None:
        if abs(n_hat[2]) < 0.9:
            e_vert = np.array([0.0, 0.0, 1.0])
        else:
            e_vert = np.array([0.0, 1.0, 0.0])
    pol = project_polarisation(k_hat, e_vert)
    # |psi|^2 / (2 Z_0) = 1 W/m^2 per path (unit reference incident power).
    psi = (np.sqrt(2 * Z_0) * pol).astype(complex)

    element_index = np.arange(N_eff, dtype=np.int64)

    # Compute body channel
    G_tilde = compute_body_channel(
        body.normals,
        body.centroids,
        k_hat,
        psi,
        element_index,
        SKIN_28GHZ.n_complex,
        SKIN_28GHZ.sigma,
        freq_hz,
        n_elements=N_eff,
    )

    # MRT precoder focused at r_target:
    # at r_target, g_j contribution has phase exp(-i k0 k_hat_j . r_target);
    # x_j = exp(+i k0 k_hat_j . r_target) cancels it for unit-power transmit.
    k0 = 2 * np.pi * freq_hz / C_0
    x_unnorm = np.exp(1j * k0 * (k_hat @ r_target))
    x = np.sqrt(P_tx) * x_unnorm / np.linalg.norm(x_unnorm)

    # S_ab per triangle
    G_tilde_np = np.asarray(G_tilde)
    field = np.einsum("mia,a->mi", G_tilde_np, x)
    sab = np.real(np.sum(np.conj(field) * field, axis=1))
    sab = np.maximum(sab, 0.0)

    # ICNIRP 4 cm^2 averaging
    apd = np.asarray(G_avg @ sab)
    peak_idx = int(np.argmax(apd))
    peak_apd = float(apd[peak_idx])
    peak_patch_centroid = body.centroids[peak_idx]
    tracking_distance_cm = float(np.linalg.norm(peak_patch_centroid - r_target) * 100.0)

    # APD at the patch nearest the intended target
    target_idx = tri_idx  # centroids[tri_idx] == r_target by construction
    apd_at_target = float(apd[target_idx])

    # Whole-body P_abs and mean
    P_abs = float(np.sum(body.areas * sab))
    body_mean_apd = P_abs / body.total_area
    eta_4cm2 = peak_apd / body_mean_apd if body_mean_apd > 0 else float("nan")
    kappa = peak_apd / P_abs if P_abs > 0 else float("nan")  # [1/m^2]
    A_eff_m2 = 1.0 / kappa if kappa > 0 else float("inf")
    # crossover threshold using monograph's adult reference
    # (independent of phantom mass; we scale by adult m/A*)
    A_eff_star_m2 = AEFF_STAR_ADULT_M2

    angular_spread_deg = float(np.degrees(aperture_m / distance_m))

    return {
        "region": region,
        "distance_m": distance_m,
        "N": N,
        "N_eff": N_eff,
        "aperture_m": aperture_m,
        "r_target": r_target.tolist(),
        "n_target": n_hat.tolist(),
        "peak_apd_w_m2": peak_apd,
        "apd_at_target_w_m2": apd_at_target,
        "tracking_ratio": apd_at_target / peak_apd if peak_apd > 0 else float("nan"),
        "worst_patch_index": peak_idx,
        "worst_patch_distance_cm": tracking_distance_cm,
        "p_abs_w": P_abs,
        "body_mean_apd_w_m2": body_mean_apd,
        "eta_4cm2": eta_4cm2,
        "kappa_inv_m2": kappa,
        "A_eff_cm2": 1.0e4 * A_eff_m2,
        "A_eff_star_cm2_adult": 1.0e4 * A_eff_star_m2,
        "apd_binds_adult": bool(A_eff_m2 < A_eff_star_m2),
        "array_angular_spread_deg": angular_spread_deg,
    }


def main():
    body, _ = _get_body_and_averaging()
    print(
        f"phantom {body.name}: {body.n_triangles} tri, "
        f"area {body.total_area:.4f} m^2, height {body.height:.3f} m"
    )
    print(
        f"adult A_eff* = {1e4 * AEFF_STAR_ADULT_M2:.0f} cm^2 "
        f"(m={ADULT_M_KG} kg, L_SAR={ADULT_M_KG*ICNIRP_SAR_WB_PUBLIC:.2f} W, "
        f"L_APD={ICNIRP_SAB_4CM2_PUBLIC:.0f} W/m^2)"
    )
    regions = ["chest", "head", "shoulder", "thigh"]
    distances = [0.05, 0.10, 0.30, 1.00]  # m
    Ns = [1, 4, 16, 64]

    rows = []
    t0 = time.time()
    for region in regions:
        for d in distances:
            for N in Ns:
                r = run_one(region, d, N)
                rows.append(r)
                print(
                    f"{region:8s} d={100*d:5.1f}cm N={N:3d}  "
                    f"track={r['tracking_ratio']:.2f} "
                    f"dist={r['worst_patch_distance_cm']:5.1f}cm  "
                    f"peakAPD={r['peak_apd_w_m2']:6.2f}  "
                    f"Pabs={r['p_abs_w']:.4f}  "
                    f"eta={r['eta_4cm2']:6.2f}  "
                    f"A_eff={r['A_eff_cm2']:6.1f}cm^2  "
                    f"binds_adult={r['apd_binds_adult']!s:5s}  "
                    f"[{time.time()-t0:5.1f}s]",
                    flush=True,
                )

    out = {
        "phantom": {
            "name": body.name,
            "n_triangles": body.n_triangles,
            "total_area_m2": body.total_area,
            "height_m": body.height,
        },
        "constants": {
            "freq_hz": 28e9,
            "adult_m_kg": ADULT_M_KG,
            "adult_A_sigma_m2": ADULT_AREA_M2,
            "L_APD_W_m2": ICNIRP_SAB_4CM2_PUBLIC,
            "L_SAR_wb_W_kg": ICNIRP_SAR_WB_PUBLIC,
            "A_eff_star_adult_m2": AEFF_STAR_ADULT_M2,
            "aperture_m": 0.03,
        },
        "rows": rows,
    }
    out_path = Path(__file__).resolve().parent / "real_phantom_near_field_codex_opus.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
