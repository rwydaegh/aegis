"""
Integrated diffraction effect on Thelonious whole-body absorbed power
=====================================================================

Reports (P_diff - P_simp) / P_simp on the Thelonious phantom at 1, 3,
6, 10, 15, 28, 40, 60, 77, 100 GHz, averaged over 6 cardinal incidence
directions. Both baselines use T_0 (so the entry isolates the
diffraction correction, with no Fresnel-angular contribution).

  - P_simp = T_0 * sum(area * [mu]_+)
  - P_diff = T_0 * sum(area * GELU(mu)) + T_0 * (H/k) * GELU(mu)^2 * area

Mean curvature H is taken from the cotangent Laplacian on the
merged-vertex Thelonious mesh.

Reproduces Table tab:si-diffraction in the SI.
"""
from __future__ import annotations
from pathlib import Path

import numpy as np
from scipy.special import erf
from scipy.spatial import cKDTree

from _geom import load_stl_binary, triangle_areas
from mie_theory_corrected import cole_cole_permittivity, get_gabriel_params

EPS_0 = 8.854187817e-12
C_0 = 299792458.0

MESH = str(Path(__file__).resolve().parent.parent / "data" / "thelonious.stl")

DIRS = {
    "+x": np.array([1, 0, 0]),
    "-x": np.array([-1, 0, 0]),
    "+y": np.array([0, 1, 0]),
    "-y": np.array([0, -1, 0]),
    "+z": np.array([0, 0, 1]),
    "-z": np.array([0, 0, -1]),
}

FREQS_GHZ = [1.0, 3.0, 6.0, 10.0, 15.0, 28.0, 40.0, 60.0, 77.0, 100.0]


def skin_t0(f_hz: float) -> float:
    params = get_gabriel_params("Skin")
    if params is None:
        raise RuntimeError("Missing IT'IS Gabriel parameters for skin.")
    eps_c = cole_cole_permittivity(f_hz, params)
    n_t = np.sqrt(eps_c)
    if n_t.real < 0:
        n_t = -n_t
    return float(1 - abs((1 - n_t) / (1 + n_t)) ** 2)


def compute_curvature_2h(stl_path: str, raw_normals: np.ndarray, raw_centroids: np.ndarray) -> np.ndarray:
    """Per-triangle twice-mean-curvature estimate, aligned to raw STL faces."""
    import trimesh

    tm = trimesh.load(stl_path, process=True)
    if not tm.is_watertight:
        raise RuntimeError(f"{stl_path} is not watertight after vertex merge")

    V = tm.vertices
    F = tm.faces
    nV = len(V)
    A_face = tm.area_faces
    n_face = tm.face_normals

    H_vec = np.zeros((nV, 3))
    vert_area = np.zeros(nV)

    for fi, (i, j, k) in enumerate(F):
        vi, vj, vk = V[i], V[j], V[k]
        e_ij, e_jk, e_ki = vj - vi, vk - vj, vi - vk
        li, lj, lk = (np.linalg.norm(e_ki), np.linalg.norm(e_ij), np.linalg.norm(e_jk))

        cos_i = np.dot(-e_ki, e_ij) / (li * lj + 1e-30)
        cos_j = np.dot(-e_ij, e_jk) / (lj * lk + 1e-30)
        cos_k = np.dot(-e_jk, e_ki) / (lk * li + 1e-30)
        cot_i = cos_i / np.sqrt(max(1 - cos_i**2, 1e-30))
        cot_j = cos_j / np.sqrt(max(1 - cos_j**2, 1e-30))
        cot_k = cos_k / np.sqrt(max(1 - cos_k**2, 1e-30))

        H_vec[i] += cot_k * (vj - vi) + cot_j * (vk - vi)
        H_vec[j] += cot_k * (vi - vj) + cot_i * (vk - vj)
        H_vec[k] += cot_i * (vj - vk) + cot_j * (vi - vk)
        vert_area[i] += A_face[fi] / 3
        vert_area[j] += A_face[fi] / 3
        vert_area[k] += A_face[fi] / 3

    mean_curv_normal = H_vec / (4.0 * vert_area[:, None] + 1e-30)
    n_vert = np.zeros((nV, 3))
    for fi, face in enumerate(F):
        for vi in face:
            n_vert[vi] += A_face[fi] * n_face[fi]
    n_vert /= np.linalg.norm(n_vert, axis=1, keepdims=True) + 1e-30

    H_vert = -np.einsum("vd,vd->v", mean_curv_normal, n_vert)
    H_vert = np.clip(H_vert, -200, 200)
    H_face = (H_vert[F[:, 0]] + H_vert[F[:, 1]] + H_vert[F[:, 2]]) / 3
    H_face = np.clip(H_face, -50, 200)

    if len(H_face) == len(raw_normals) and np.linalg.norm(raw_normals - n_face, axis=1).max() <= 1e-3:
        return 2.0 * H_face

    tree = cKDTree(tm.triangles_center)
    _, idx = tree.query(raw_centroids)
    return 2.0 * H_face[idx]


def main() -> None:
    vertices, normals, centroids = load_stl_binary(MESH)
    areas = triangle_areas(vertices)
    H_2x = compute_curvature_2h(MESH, normals, centroids)
    H = 0.5 * H_2x  # mean curvature 1/m
    H_safe = np.maximum(H, 0.0)

    print(f"Thelonious: {len(areas)} triangles, area = {areas.sum() * 1e4:.1f} cm^2")

    print()
    print("Integrated diffraction effect on Thelonious (6 cardinal dirs averaged)")
    print("-" * 64)
    print(f"{'f [GHz]':>10} {'P_simp [mW/m2]':>16} {'P_diff [mW/m2]':>16} "
          f"{'effect':>10}")

    for f_ghz in FREQS_GHZ:
        f_hz = f_ghz * 1e9
        T0 = skin_t0(f_hz)
        wavelength = C_0 / f_hz
        k = 2 * np.pi / wavelength
        sigma_j = np.sqrt(np.maximum(wavelength * H_safe / (4 * np.pi), 1e-20))

        P_simp_list, P_diff_list = [], []
        for k_hat in DIRS.values():
            mu = normals @ (-k_hat)
            mu_plus = np.maximum(mu, 0.0)
            P_simp = T0 * float((areas * mu_plus).sum())

            ratio = np.divide(mu, sigma_j, where=sigma_j > 0,
                              out=np.zeros_like(mu))
            mu_gelu = mu * 0.5 * (1.0 + erf(ratio))
            sab = T0 * mu_gelu + T0 * (H_safe / k) * mu_gelu ** 2
            P_diff = float((areas * np.maximum(sab, 0.0)).sum())

            P_simp_list.append(P_simp)
            P_diff_list.append(P_diff)

        P_simp = float(np.mean(P_simp_list))
        P_diff = float(np.mean(P_diff_list))
        effect = (P_diff / P_simp - 1) * 100
        print(f"{f_ghz:>10.3f} {P_simp * 1e3:>16.4f} {P_diff * 1e3:>16.4f} "
              f"{effect:>+9.2f}%")


if __name__ == "__main__":
    main()
