"""Geometry helpers for the FDTD validation: curvature, visibility, polarisation basis.

Public API:
    compute_curvature_2H(stl_path) -> ndarray (M,)
    compute_visibility(stl_path, k_hats) -> dict[str_or_tuple, ndarray (M,)]
    goliat_basis(direction_name) -> (k_hat, e_theta, e_phi)
    q_field(normals, k_hat, e_E) -> ndarray (M, 1)

All array outputs are aligned to AEGIS's `BodyMesh.load(stl_path)` face order.
"""

from __future__ import annotations
from typing import Iterable
import numpy as np

# Goliat orthogonal-direction map (verified from goliat/setups/far_field_setup.py).
# Stored as (phi_deg, theta_deg) representing the wave PROPAGATION direction.
GOLIAT_DIRS = {
    "x_pos": (0, 90),
    "x_neg": (180, 90),
    "y_pos": (90, 90),
    "y_neg": (270, 90),
    "z_pos": (0, 0),
    "z_neg": (0, 180),
}


def goliat_basis(name: str):
    """Return (k_hat, e_theta, e_phi) for a goliat orthogonal direction.

    Goliat sets `Psi=0` for theta-pol (E along e_theta) and `Psi=90` for phi-pol.
    """
    phi_deg, theta_deg = GOLIAT_DIRS[name]
    th, ph = np.deg2rad(theta_deg), np.deg2rad(phi_deg)
    k_hat = np.array([np.sin(th) * np.cos(ph), np.sin(th) * np.sin(ph), np.cos(th)])
    e_theta = np.array([np.cos(th) * np.cos(ph), np.cos(th) * np.sin(ph), -np.sin(th)])
    e_phi = np.array([-np.sin(ph), np.cos(ph), 0.0])
    # NOTE: at the poles (theta=0 or 180) the spherical (theta, phi) basis is
    # technically degenerate for arbitrary phi, but goliat always uses phi=0
    # at the poles (z_pos and z_neg), and the formulas above give the
    # correct right-handed limits in that case (verified by
    # preflight_check.check_direction_basis). Do NOT override at the pole.
    return k_hat, e_theta, e_phi


def q_field(normals: np.ndarray, k_hat: np.ndarray, e_E: np.ndarray, eps: float = 1e-9) -> np.ndarray:
    """Per-triangle TM excess q = |e_p|^2 - |e_s|^2 ∈ [-1, 1].

    Inputs:
        normals: (M, 3) outward triangle normals
        k_hat:   (3,) wave propagation direction
        e_E:     (3,) unit incident-E direction (must satisfy e_E . k_hat ≈ 0)

    Output: (M, 1) q array, suitable for AEGIS engine.compute(level=4, q=...).
    """
    cross = np.cross(k_hat[None, :], normals)
    n_cross = np.linalg.norm(cross, axis=1, keepdims=True)
    safe = np.where(n_cross > eps, n_cross, 1.0)
    e_s_hat = cross / safe
    e_p_hat = np.cross(e_s_hat, k_hat[None, :])
    e_s_proj = e_s_hat @ e_E
    e_p_proj = e_p_hat @ e_E
    q = e_p_proj**2 - e_s_proj**2
    q[(n_cross[:, 0] < eps)] = 0.0  # normal incidence: degenerate basis -> q=0
    return q.reshape(-1, 1)


def compute_curvature_2H(stl_path: str) -> np.ndarray:
    """Per-triangle 2H (twice mean curvature, 1/m) via cotangent Laplacian.

    Sign convention: positive on convex regions (outward normal pointing
    away from the centre of curvature). Output is clipped to [-50, 200] to
    suppress spikes on near-degenerate triangles.

    Aligned to `BodyMesh.load(stl_path)` face order. Requires `trimesh` for
    vertex merging (the raw STL has duplicated vertices and the cotangent
    Laplacian gives zero on it).
    """
    import trimesh
    from aegis.geometry.mesh import BodyMesh

    tm = trimesh.load(stl_path)  # process=True merges duplicate vertices
    if not tm.is_watertight:
        raise RuntimeError(f"{stl_path} is not watertight after vertex merge")

    V = tm.vertices
    F = tm.faces
    nV = len(V)
    nF = len(F)

    # Cotangent Laplacian: Δx_i ≈ (1/(2 A_voronoi_i)) · sum over neighbours
    # Here we use the simpler 1/3-area lumped mass and accumulate cot weights.
    A_face = tm.area_faces
    n_face = tm.face_normals

    H_vec = np.zeros((nV, 3))
    vert_area = np.zeros(nV)

    for fi in range(nF):
        i, j, k = F[fi]
        vi, vj, vk = V[i], V[j], V[k]
        e_ij, e_jk, e_ki = vj - vi, vk - vj, vi - vk
        li, lj, lk = (np.linalg.norm(e_ki), np.linalg.norm(e_ij), np.linalg.norm(e_jk))

        cos_i = np.dot(-e_ki, e_ij) / (li * lj + 1e-30)
        cos_j = np.dot(-e_ij, e_jk) / (lj * lk + 1e-30)
        cos_k = np.dot(-e_jk, e_ki) / (lk * li + 1e-30)
        sin_i = np.sqrt(max(1 - cos_i**2, 1e-30))
        sin_j = np.sqrt(max(1 - cos_j**2, 1e-30))
        sin_k = np.sqrt(max(1 - cos_k**2, 1e-30))
        cot_i, cot_j, cot_k = cos_i / sin_i, cos_j / sin_j, cos_k / sin_k

        H_vec[i] += cot_k * (vj - vi) + cot_j * (vk - vi)
        H_vec[j] += cot_k * (vi - vj) + cot_i * (vk - vj)
        H_vec[k] += cot_i * (vj - vk) + cot_j * (vi - vk)
        vert_area[i] += A_face[fi] / 3
        vert_area[j] += A_face[fi] / 3
        vert_area[k] += A_face[fi] / 3

    mean_curv_normal = H_vec / (4.0 * vert_area[:, None] + 1e-30)

    # Per-vertex outward normal (area-weighted).
    n_vert = np.zeros((nV, 3))
    for fi in range(nF):
        for vi in F[fi]:
            n_vert[vi] += A_face[fi] * n_face[fi]
    n_vert /= np.linalg.norm(n_vert, axis=1, keepdims=True) + 1e-30

    # Cotangent Laplacian sign: Δx points TOWARD the centre of curvature.
    # For an outward normal, mean_curv_normal · n_outward < 0 on convex.
    # We want H > 0 on convex, so flip sign.
    H_vert = -np.einsum("vd,vd->v", mean_curv_normal, n_vert)
    H_vert = np.clip(H_vert, -200, 200)

    H_face_merged = (H_vert[F[:, 0]] + H_vert[F[:, 1]] + H_vert[F[:, 2]]) / 3
    H_face_merged = np.clip(H_face_merged, -50, 200)

    # Re-align to AEGIS BodyMesh face order. BodyMesh.load uses unmerged STL,
    # but trimesh.load with process=True keeps the same face order while only
    # remapping vertex indices. We confirm by comparing face normals.
    body = BodyMesh.load(stl_path)
    diff = np.linalg.norm(body.normals - n_face, axis=1).max()
    if diff > 1e-3:
        # Fall back to centroid nearest-neighbour
        from scipy.spatial import cKDTree

        tree = cKDTree(tm.triangles_center)
        _, idx = tree.query(body.centroids)
        H_face_merged = H_face_merged[idx]

    return 2.0 * H_face_merged  # kernel expects 2H, not H


def compute_visibility(stl_path: str, k_hats: dict | Iterable) -> dict:
    """Per-direction binary O(r, k_hat) by ray-tracing toward the source.

    Inputs:
        stl_path: phantom STL
        k_hats:   either a dict {label: k_hat} or an iterable of k_hat 3-vectors
                  (in which case labels are 'k0', 'k1', ...).

    Output: dict {label: ndarray (M,)} with values in {0, 1}.
        - 1 if the triangle is front-facing AND a ray from its centroid in
          direction `-k_hat` (toward source) escapes without hitting another
          triangle of the mesh.
        - 0 if back-facing or self-shadowed.
    """
    from aegis.geometry.mesh import BodyMesh
    from aegis.geometry.occlusion import build_bvh, _precompute_triangle_data, ray_mesh_any_hit

    body = BodyMesh.load(stl_path)
    M = body.n_triangles

    tri_data = _precompute_triangle_data(body.vertices)
    bvh, tri_order = build_bvh(tri_data["tri_bmin"], tri_data["tri_bmax"], body.centroids, max_leaf=8)
    origin_eps = 1e-6 * body.scale
    t_min = 10.0 * origin_eps
    origins = body.centroids + origin_eps * body.normals
    v0x, v0y, v0z = tri_data["tri_v0x"], tri_data["tri_v0y"], tri_data["tri_v0z"]
    e1x, e1y, e1z = tri_data["tri_e1x"], tri_data["tri_e1y"], tri_data["tri_e1z"]
    e2x, e2y, e2z = tri_data["tri_e2x"], tri_data["tri_e2y"], tri_data["tri_e2z"]

    if isinstance(k_hats, dict):
        items = list(k_hats.items())
    else:
        items = [(f"k{i}", np.asarray(k)) for i, k in enumerate(k_hats)]

    out = {}
    for label, k_hat in items:
        k_hat = np.asarray(k_hat, dtype=np.float64)
        dx, dy, dz = -k_hat
        vis = np.ones(M, dtype=np.float64)
        for i in range(M):
            if body.normals[i] @ (-k_hat) <= 0:
                vis[i] = 0.0
                continue
            hit = ray_mesh_any_hit(
                float(origins[i, 0]),
                float(origins[i, 1]),
                float(origins[i, 2]),
                float(dx),
                float(dy),
                float(dz),
                bvh,
                tri_order,
                v0x,
                v0y,
                v0z,
                e1x,
                e1y,
                e1z,
                e2x,
                e2y,
                e2z,
                int(i),
                t_min,
            )
            vis[i] = 0.0 if hit else 1.0
        out[label] = vis
    return out


def cache_geometry(stl_path: str, cache_dir: str) -> dict:
    """Compute or load cached H_2x, eta, and visibility for the 6 goliat
    cardinal directions. Returns dict with keys H_2x, eta, vis_<dir_name>.
    """
    import os
    import hashlib
    from aegis.geometry.mesh import BodyMesh
    from aegis.geometry.occlusion import compute_ambient_occlusion

    os.makedirs(cache_dir, exist_ok=True)
    body = BodyMesh.load(stl_path)
    key = hashlib.md5(open(stl_path, "rb").read()).hexdigest()[:8]
    cache_file = os.path.join(cache_dir, f"geometry_{key}.npz")

    if os.path.exists(cache_file):
        return dict(np.load(cache_file))

    print(f"[geometry] computing 2H...")
    H_2x = compute_curvature_2H(stl_path)
    print(f"[geometry] computing eta(r) (n_rays=128)...")
    eta = compute_ambient_occlusion(body, n_rays=128, seed=0)
    print(f"[geometry] computing visibility for 6 cardinal directions...")
    k_hats = {name: goliat_basis(name)[0] for name in GOLIAT_DIRS}
    vis = compute_visibility(stl_path, k_hats)

    payload = {"H_2x": H_2x, "eta": eta}
    payload.update({f"vis_{n}": v for n, v in vis.items()})
    np.savez(cache_file, **payload)
    print(f"[geometry] cached -> {cache_file}")
    return payload
