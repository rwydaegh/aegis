"""Targeted diagnostic: is the stable worst-patch in the Codex far-field
cone simulation a physical coherent hotspot or a geometric artefact?

Test A: fixed cone (Codex's original setup). Place N equally spaced
        directions on a 20 deg cone around -x; precoder = dominant
        eigenvector of the worst local Q. Report the worst patch index
        for N in {1, 2, 4, 8, 16, 32, 64}. If the index is invariant
        in N, the hotspot is geometric (determined by body surface
        geometry) and the coherent gain is spurious.

Test B: moved cone. Same as Test A but cone around +y (rotating the
        "incidence" direction by 90 deg). Different index? -> confirmed
        geometric.

Test C: near-field MRT. Place a 3 cm UPA at distance 10 cm from the
        chest centroid; MRT focuses at r_target. Report the worst
        patch index and its distance to r_target in cm. If it tracks
        the target (< 2 cm), the hotspot is physical.

Output: geometric_vs_physical_codex_opus.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from aegis.coherent.body_channel import compute_body_channel
from aegis.coherent.exposure_operator import compute_exposure_operator
from aegis.constants import Z_0
from aegis.geometry.averaging import precompute_averaging_matrix
from aegis.geometry.mesh import BodyMesh
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import SKIN_28GHZ

AVERAGING_AREA_M2 = 4e-4


def cone_directions(center: np.ndarray, spread_deg: float, n_paths: int) -> np.ndarray:
    center = np.asarray(center, dtype=np.float64)
    center = center / np.linalg.norm(center)
    ref = np.array([0.0, 0.0, 1.0]) if abs(center[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    u = np.cross(center, ref); u /= np.linalg.norm(u)
    v = np.cross(center, u)
    if n_paths == 1:
        return center[None, :]
    ang = np.deg2rad(spread_deg)
    dirs = np.empty((n_paths, 3))
    for k in range(n_paths):
        phi = 2 * np.pi * k / n_paths
        d = center * np.cos(ang) + (u * np.cos(phi) + v * np.sin(phi)) * np.sin(ang)
        dirs[k] = d / np.linalg.norm(d)
    return dirs


def local_operators(G_avg, G_tilde: np.ndarray) -> np.ndarray:
    """Q_loc[m] = sum_i G_avg[m,i] G_i^H G_i."""
    gram = np.einsum("mia,mib->mab", np.conj(G_tilde), G_tilde)
    n_tri, _, n_ant = G_tilde.shape
    Q_loc = np.empty((n_tri, n_ant, n_ant), dtype=complex)
    for a in range(n_ant):
        for b in range(n_ant):
            Q_loc[:, a, b] = G_avg @ gram[:, a, b]
    return Q_loc


def worst_patch_fixed_cone(body: BodyMesh, G_avg, center_dir: np.ndarray, N: int):
    """Codex-style: worst patch from eigenvector of worst local Q.
    Returns (worst_index, centroid, eta_4cm2, peak_apd)."""
    paths = PropagationPaths.from_powers(
        k_hat=cone_directions(center_dir, spread_deg=20.0, n_paths=N),
        power=np.ones(N),
    )
    G_tilde = np.asarray(compute_body_channel(
        body.normals, body.centroids, paths.k_hat, paths.psi,
        paths.element_index, SKIN_28GHZ.n_complex, SKIN_28GHZ.sigma,
        SKIN_28GHZ.freq_hz, n_elements=paths.n_elements,
    ))
    Q = np.asarray(compute_exposure_operator(G_tilde, body.areas))
    Q_loc = local_operators(G_avg, G_tilde)
    local_lmax = np.linalg.eigvalsh(Q_loc)[:, -1]
    idx = int(np.argmax(local_lmax))
    _, V = np.linalg.eigh(Q_loc[idx])
    x = V[:, -1]
    peak_apd = float(np.real(x.conj() @ Q_loc[idx] @ x))
    p_abs = float(np.real(x.conj() @ Q @ x))
    eta = peak_apd / (p_abs / body.total_area) if p_abs > 0 else float("nan")
    return idx, body.centroids[idx].copy(), eta, peak_apd, p_abs


def worst_patch_near_field_mrt(body: BodyMesh, G_avg, r_target, n_target, N, d_m=0.10, aperture_m=0.03):
    """Near-field MRT at r_target, N-element UPA normal to n_target at distance d_m."""
    from JSAC.direction_4_sim_codex_opus.real_phantom_near_field_codex_opus import (  # noqa
        build_upa_positions, project_polarisation,
    )
    from aegis.constants import C_0
    p_center = r_target + d_m * n_target
    positions = build_upa_positions(p_center, n_target, N, aperture_m)
    vec = r_target[None, :] - positions
    dist = np.linalg.norm(vec, axis=1, keepdims=True)
    k_hat = vec / dist
    e_ref = np.array([0.0, 0.0, 1.0]) if abs(n_target[2]) < 0.9 else np.array([0.0, 1.0, 0.0])
    pol = project_polarisation(k_hat, e_ref)
    psi = (np.sqrt(2 * Z_0) * pol).astype(complex)
    element_index = np.arange(len(positions), dtype=np.int64)
    G_tilde = np.asarray(compute_body_channel(
        body.normals, body.centroids, k_hat, psi, element_index,
        SKIN_28GHZ.n_complex, SKIN_28GHZ.sigma, SKIN_28GHZ.freq_hz,
        n_elements=len(positions),
    ))
    freq_hz = SKIN_28GHZ.freq_hz
    k0 = 2 * np.pi * freq_hz / C_0
    x_unnorm = np.exp(1j * k0 * (k_hat @ r_target))
    x = x_unnorm / np.linalg.norm(x_unnorm)
    field = np.einsum("mia,a->mi", G_tilde, x)
    sab = np.maximum(np.real(np.sum(np.conj(field) * field, axis=1)), 0.0)
    apd = np.asarray(G_avg @ sab)
    idx = int(np.argmax(apd))
    dist_cm = 100.0 * float(np.linalg.norm(body.centroids[idx] - r_target))
    # Equivalent eta
    p_abs = float(np.sum(body.areas * sab))
    eta = float(apd[idx]) / (p_abs / body.total_area) if p_abs > 0 else float("nan")
    return idx, body.centroids[idx].copy(), eta, float(apd[idx]), p_abs, dist_cm


def main():
    body = BodyMesh.load(REPO_ROOT / "data" / "thelonious.stl")
    G_avg = precompute_averaging_matrix(body.centroids, body.areas, AVERAGING_AREA_M2)
    print(f"thelonious: {body.n_triangles} tri, {body.total_area:.4f} m^2")

    out = {
        "phantom": {"name": body.name, "n_triangles": body.n_triangles,
                    "total_area_m2": body.total_area},
        "test_A_fixed_cone_minus_x": [],
        "test_B_fixed_cone_plus_y": [],
        "test_C_near_field_mrt": [],
    }

    print("\n=== Test A: fixed cone around -x (Codex original) ===")
    minus_x = np.array([-1.0, 0.0, 0.0])
    for N in [1, 2, 4, 8, 16, 32, 64]:
        idx, c, eta, peak, pa = worst_patch_fixed_cone(body, G_avg, minus_x, N)
        row = {"N": N, "worst_idx": idx, "centroid": c.tolist(),
               "eta": eta, "peak_apd": peak, "p_abs": pa}
        out["test_A_fixed_cone_minus_x"].append(row)
        print(f"  N={N:3d} idx={idx:5d} centroid=[{c[0]:+.3f},{c[1]:+.3f},{c[2]:+.3f}] "
              f"eta={eta:6.2f} peak={peak:.3f} Pabs={pa:.3f}")

    print("\n=== Test B: fixed cone around +y (rotate incidence 90 deg) ===")
    plus_y = np.array([0.0, 1.0, 0.0])
    for N in [1, 2, 4, 8, 16, 32, 64]:
        idx, c, eta, peak, pa = worst_patch_fixed_cone(body, G_avg, plus_y, N)
        row = {"N": N, "worst_idx": idx, "centroid": c.tolist(),
               "eta": eta, "peak_apd": peak, "p_abs": pa}
        out["test_B_fixed_cone_plus_y"].append(row)
        print(f"  N={N:3d} idx={idx:5d} centroid=[{c[0]:+.3f},{c[1]:+.3f},{c[2]:+.3f}] "
              f"eta={eta:6.2f} peak={peak:.3f} Pabs={pa:.3f}")

    print("\n=== Test C: near-field MRT at chest (d=10cm, N=16) ===")
    # Pick chest centroid
    c_mesh = body.centroids
    n_mesh = body.normals
    mask = (c_mesh[:, 2] > -0.05) & (c_mesh[:, 2] < 0.05) & (c_mesh[:, 1] < -0.05) & (n_mesh[:, 1] < -0.5)
    pool = np.where(mask)[0]
    chest_idx = int(pool[int(np.argmax(-n_mesh[pool, 1]))])
    r_target = c_mesh[chest_idx].copy()
    n_target = n_mesh[chest_idx].copy()
    print(f"  chest target idx={chest_idx} at {r_target}, normal {n_target}")
    for N in [1, 2, 4, 8, 16, 32, 64]:
        for d in [0.05, 0.10, 0.30, 1.00]:
            idx, c, eta, peak, pa, dist_cm = worst_patch_near_field_mrt(
                body, G_avg, r_target, n_target, N=N, d_m=d
            )
            row = {"N": N, "d_m": d, "worst_idx": idx, "centroid": c.tolist(),
                   "eta": eta, "peak_apd": peak, "p_abs": pa,
                   "dist_to_target_cm": dist_cm}
            out["test_C_near_field_mrt"].append(row)
            print(f"  N={N:3d} d={100*d:5.1f}cm idx={idx:5d} dist={dist_cm:5.1f}cm "
                  f"eta={eta:6.2f} peak={peak:.3f} Pabs={pa:.3f}")

    out_path = Path(__file__).resolve().parent / "geometric_vs_physical_codex_opus.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
