"""Cosine-weighted ambient occlusion (exposure fraction eta).

Extracted from scripts/compute_exposure_fraction_eta.py.
Uses Numba JIT compilation for the BVH traversal and ray intersection
hot path when available, giving ~50-100x speedup on large meshes.
"""

from __future__ import annotations

import numpy as np

from aegis.geometry.mesh import BodyMesh

try:
    from numba import njit

    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False

    def njit(*args, **kwargs):
        """No-op decorator when Numba is not installed."""
        if len(args) == 1 and callable(args[0]):
            return args[0]
        return lambda f: f

# ---------------------------------------------------------------------------
# Sampling
# ---------------------------------------------------------------------------


def cosine_weighted_hemisphere_samples(n: int, rng: np.random.Generator) -> np.ndarray:
    """Sample n directions on the +Z hemisphere with cosine-weighted distribution.

    Returns (n, 3) array with z >= 0.
    """
    u1 = rng.random(n)
    u2 = rng.random(n)
    r = np.sqrt(u1)
    phi = 2.0 * np.pi * u2
    x = r * np.cos(phi)
    y = r * np.sin(phi)
    z = np.sqrt(np.maximum(0.0, 1.0 - u1))
    return np.stack([x, y, z], axis=1)


def _normalize(v: np.ndarray, eps: float = 1e-30) -> np.ndarray:
    n = np.linalg.norm(v)
    if n < eps:
        return v * 0.0
    return v / n


def make_tangent_frame(n: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Build orthonormal (t, b) for unit normal n so that t x b = n."""
    n = _normalize(n)
    a = np.array([0.0, 0.0, 1.0]) if abs(n[2]) < 0.999 else np.array([1.0, 0.0, 0.0])
    t = _normalize(np.cross(a, n))
    b = np.cross(n, t)
    return t, b


# ---------------------------------------------------------------------------
# BVH
# ---------------------------------------------------------------------------


def _segment_bbox(
    tri_indices: np.ndarray,
    start: int,
    end: int,
    tri_bmin: np.ndarray,
    tri_bmax: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    idx = tri_indices[start:end]
    return np.min(tri_bmin[idx], axis=0), np.max(tri_bmax[idx], axis=0)


def build_bvh(
    tri_bmin: np.ndarray,
    tri_bmax: np.ndarray,
    tri_centroids: np.ndarray,
    max_leaf: int = 8,
) -> tuple[dict[str, np.ndarray], np.ndarray]:
    """Build a median-split BVH over triangle AABBs.

    Returns (bvh_dict, tri_indices) where bvh_dict has keys
    bmin, bmax, left, right, start, count.
    """
    n_tris = tri_centroids.shape[0]
    tri_indices = np.arange(n_tris, dtype=np.int32)
    bmin_list: list[np.ndarray] = []
    bmax_list: list[np.ndarray] = []
    left_list: list[int] = []
    right_list: list[int] = []
    start_list: list[int] = []
    count_list: list[int] = []

    def build_node(start: int, end: int) -> int:
        bmin, bmax = _segment_bbox(tri_indices, start, end, tri_bmin, tri_bmax)
        node_idx = len(bmin_list)
        bmin_list.append(bmin)
        bmax_list.append(bmax)
        left_list.append(-1)
        right_list.append(-1)
        start_list.append(int(start))
        count_list.append(int(end - start))

        count = end - start
        if count <= max_leaf:
            return node_idx

        extent = bmax - bmin
        axis = int(np.argmax(extent))
        mid = start + count // 2

        seg = tri_indices[start:end]
        keys = tri_centroids[seg, axis]
        order = np.argpartition(keys, mid - start)
        tri_indices[start:end] = seg[order]

        left = build_node(start, mid)
        right = build_node(mid, end)
        left_list[node_idx] = int(left)
        right_list[node_idx] = int(right)
        return node_idx

    build_node(0, n_tris)
    bvh = {
        "bmin": np.asarray(bmin_list, dtype=np.float64),
        "bmax": np.asarray(bmax_list, dtype=np.float64),
        "left": np.asarray(left_list, dtype=np.int32),
        "right": np.asarray(right_list, dtype=np.int32),
        "start": np.asarray(start_list, dtype=np.int32),
        "count": np.asarray(count_list, dtype=np.int32),
    }
    return bvh, tri_indices


# ---------------------------------------------------------------------------
# Ray-mesh intersection
# ---------------------------------------------------------------------------


@njit(cache=True)
def _ray_aabb_hit(
    ox: float,
    oy: float,
    oz: float,
    idx: float,
    idy: float,
    idz: float,
    bminx: float,
    bminy: float,
    bminz: float,
    bmaxx: float,
    bmaxy: float,
    bmaxz: float,
) -> bool:
    """Slab test for ray-AABB intersection (any hit, t >= 0)."""
    tmin = -1.0e300
    tmax = 1.0e300

    t1 = (bminx - ox) * idx
    t2 = (bmaxx - ox) * idx
    if t1 > t2:
        t1, t2 = t2, t1
    tmin = t1 if t1 > tmin else tmin
    tmax = t2 if t2 < tmax else tmax
    if tmax < tmin:
        return False

    t1 = (bminy - oy) * idy
    t2 = (bmaxy - oy) * idy
    if t1 > t2:
        t1, t2 = t2, t1
    tmin = t1 if t1 > tmin else tmin
    tmax = t2 if t2 < tmax else tmax
    if tmax < tmin:
        return False

    t1 = (bminz - oz) * idz
    t2 = (bmaxz - oz) * idz
    if t1 > t2:
        t1, t2 = t2, t1
    tmin = t1 if t1 > tmin else tmin
    tmax = t2 if t2 < tmax else tmax
    if tmax < tmin:
        return False

    return tmax >= 0.0


@njit(cache=True)
def _ray_triangle_hit(
    ox: float,
    oy: float,
    oz: float,
    dx: float,
    dy: float,
    dz: float,
    v0x: float,
    v0y: float,
    v0z: float,
    e1x: float,
    e1y: float,
    e1z: float,
    e2x: float,
    e2y: float,
    e2z: float,
    t_min: float,
) -> bool:
    """Moller-Trumbore ray-triangle intersection, any hit with t > t_min."""
    px = dy * e2z - dz * e2y
    py = dz * e2x - dx * e2z
    pz = dx * e2y - dy * e2x

    det = e1x * px + e1y * py + e1z * pz
    if abs(det) < 1e-12:
        return False
    inv_det = 1.0 / det

    tx = ox - v0x
    ty = oy - v0y
    tz = oz - v0z
    u = (tx * px + ty * py + tz * pz) * inv_det
    if u < 0.0 or u > 1.0:
        return False

    qx = ty * e1z - tz * e1y
    qy = tz * e1x - tx * e1z
    qz = tx * e1y - ty * e1x
    v = (dx * qx + dy * qy + dz * qz) * inv_det
    if v < 0.0 or (u + v) > 1.0:
        return False

    t = (e2x * qx + e2y * qy + e2z * qz) * inv_det
    return t > t_min


@njit(cache=True)
def _ray_mesh_any_hit_numba(
    ox,
    oy,
    oz,
    dx,
    dy,
    dz,
    bvh_bmin,
    bvh_bmax,
    bvh_left,
    bvh_right,
    bvh_start,
    bvh_count,
    tri_indices,
    tri_v0x,
    tri_v0y,
    tri_v0z,
    tri_e1x,
    tri_e1y,
    tri_e1z,
    tri_e2x,
    tri_e2y,
    tri_e2z,
    ignore_tri,
    t_min,
):
    """Numba-JIT BVH traversal for any-hit ray-mesh intersection."""
    inv_dx = 1.0 / dx if abs(dx) > 1e-15 else (1.0e30 if dx >= 0 else -1.0e30)
    inv_dy = 1.0 / dy if abs(dy) > 1e-15 else (1.0e30 if dy >= 0 else -1.0e30)
    inv_dz = 1.0 / dz if abs(dz) > 1e-15 else (1.0e30 if dz >= 0 else -1.0e30)

    # Fixed-size stack (BVH depth is O(log n), 64 is plenty)
    stack = np.empty(64, dtype=np.int32)
    stack[0] = 0
    sp = 1

    while sp > 0:
        sp -= 1
        ni = stack[sp]
        bminx = bvh_bmin[ni, 0]
        bminy = bvh_bmin[ni, 1]
        bminz = bvh_bmin[ni, 2]
        bmaxx = bvh_bmax[ni, 0]
        bmaxy = bvh_bmax[ni, 1]
        bmaxz = bvh_bmax[ni, 2]
        if not _ray_aabb_hit(ox, oy, oz, inv_dx, inv_dy, inv_dz, bminx, bminy, bminz, bmaxx, bmaxy, bmaxz):
            continue

        li = bvh_left[ni]
        ri = bvh_right[ni]
        if li < 0 and ri < 0:
            s0 = bvh_start[ni]
            e0 = s0 + bvh_count[ni]
            for k in range(s0, e0):
                ti = tri_indices[k]
                if ti == ignore_tri:
                    continue
                if _ray_triangle_hit(
                    ox,
                    oy,
                    oz,
                    dx,
                    dy,
                    dz,
                    tri_v0x[ti],
                    tri_v0y[ti],
                    tri_v0z[ti],
                    tri_e1x[ti],
                    tri_e1y[ti],
                    tri_e1z[ti],
                    tri_e2x[ti],
                    tri_e2y[ti],
                    tri_e2z[ti],
                    t_min,
                ):
                    return True
        else:
            stack[sp] = li
            sp += 1
            stack[sp] = ri
            sp += 1

    return False


def ray_mesh_any_hit(
    ox: float,
    oy: float,
    oz: float,
    dx: float,
    dy: float,
    dz: float,
    bvh: dict[str, np.ndarray],
    tri_indices: np.ndarray,
    tri_v0x: np.ndarray,
    tri_v0y: np.ndarray,
    tri_v0z: np.ndarray,
    tri_e1x: np.ndarray,
    tri_e1y: np.ndarray,
    tri_e1z: np.ndarray,
    tri_e2x: np.ndarray,
    tri_e2y: np.ndarray,
    tri_e2z: np.ndarray,
    ignore_tri: int | None,
    t_min: float,
) -> bool:
    """BVH traversal for any-hit ray-mesh intersection.

    Public API wrapper that extracts flat arrays from the BVH dict
    and delegates to the Numba-JIT inner function.
    """
    return _ray_mesh_any_hit_numba(
        ox,
        oy,
        oz,
        dx,
        dy,
        dz,
        bvh["bmin"],
        bvh["bmax"],
        bvh["left"],
        bvh["right"],
        bvh["start"],
        bvh["count"],
        tri_indices,
        tri_v0x,
        tri_v0y,
        tri_v0z,
        tri_e1x,
        tri_e1y,
        tri_e1z,
        tri_e2x,
        tri_e2y,
        tri_e2z,
        ignore_tri if ignore_tri is not None else -1,
        t_min,
    )


# ---------------------------------------------------------------------------
# Ambient occlusion (exposure fraction eta)
# ---------------------------------------------------------------------------


def _precompute_triangle_data(vertices: np.ndarray) -> dict[str, np.ndarray]:
    """Precompute per-triangle geometry arrays for ray intersection.

    Parameters
    ----------
    vertices : (N, 3, 3) array of triangle vertices

    Returns
    -------
    dict with keys: tri_v0x, tri_v0y, tri_v0z, tri_e1x, tri_e1y, tri_e1z,
    tri_e2x, tri_e2y, tri_e2z, tri_bmin, tri_bmax
    """
    v0 = vertices[:, 0].astype(np.float64, copy=False)
    v1 = vertices[:, 1].astype(np.float64, copy=False)
    v2 = vertices[:, 2].astype(np.float64, copy=False)
    e1 = (v1 - v0).astype(np.float64, copy=False)
    e2 = (v2 - v0).astype(np.float64, copy=False)
    return {
        "tri_v0x": v0[:, 0],
        "tri_v0y": v0[:, 1],
        "tri_v0z": v0[:, 2],
        "tri_e1x": e1[:, 0],
        "tri_e1y": e1[:, 1],
        "tri_e1z": e1[:, 2],
        "tri_e2x": e2[:, 0],
        "tri_e2y": e2[:, 1],
        "tri_e2z": e2[:, 2],
        "tri_bmin": np.minimum(np.minimum(v0, v1), v2),
        "tri_bmax": np.maximum(np.maximum(v0, v1), v2),
    }


@njit(cache=True)
def _fire_rays_numba(
    ox,
    oy,
    oz,
    dirs,
    n_rays,
    ignore_tri,
    t_min,
    bvh_bmin,
    bvh_bmax,
    bvh_left,
    bvh_right,
    bvh_start,
    bvh_count,
    tri_order,
    tri_v0x,
    tri_v0y,
    tri_v0z,
    tri_e1x,
    tri_e1y,
    tri_e1z,
    tri_e2x,
    tri_e2y,
    tri_e2z,
):
    """Fire n_rays from origin and count unoccluded ones. Numba-JIT."""
    vis = 0
    for r in range(n_rays):
        dx = dirs[r, 0]
        dy = dirs[r, 1]
        dz = dirs[r, 2]
        if not _ray_mesh_any_hit_numba(
            ox,
            oy,
            oz,
            dx,
            dy,
            dz,
            bvh_bmin,
            bvh_bmax,
            bvh_left,
            bvh_right,
            bvh_start,
            bvh_count,
            tri_order,
            tri_v0x,
            tri_v0y,
            tri_v0z,
            tri_e1x,
            tri_e1y,
            tri_e1z,
            tri_e2x,
            tri_e2y,
            tri_e2z,
            ignore_tri,
            t_min,
        ):
            vis += 1
    return vis


def _sample_and_test(
    i: int,
    centroid: np.ndarray,
    normal: np.ndarray,
    base_dirs: np.ndarray,
    n_rays: int,
    origin_eps: float,
    t_min: float,
    bvh: dict[str, np.ndarray],
    tri_order: np.ndarray,
    tri_data: dict[str, np.ndarray],
) -> float:
    """Fire hemisphere rays from triangle i and return the unoccluded fraction."""
    o = centroid + origin_eps * normal
    ox, oy, oz = float(o[0]), float(o[1]), float(o[2])

    t, b = make_tangent_frame(normal)
    dirs = base_dirs[:, 0:1] * t[None, :] + base_dirs[:, 1:2] * b[None, :] + base_dirs[:, 2:3] * normal[None, :]

    vis = _fire_rays_numba(
        ox,
        oy,
        oz,
        dirs,
        n_rays,
        i,
        t_min,
        bvh["bmin"],
        bvh["bmax"],
        bvh["left"],
        bvh["right"],
        bvh["start"],
        bvh["count"],
        tri_order,
        tri_data["tri_v0x"],
        tri_data["tri_v0y"],
        tri_data["tri_v0z"],
        tri_data["tri_e1x"],
        tri_data["tri_e1y"],
        tri_data["tri_e1z"],
        tri_data["tri_e2x"],
        tri_data["tri_e2y"],
        tri_data["tri_e2z"],
    )

    return vis / float(n_rays)


def compute_ambient_occlusion(
    mesh: BodyMesh,
    n_rays: int = 64,
    seed: int = 0,
    max_leaf: int = 8,
) -> np.ndarray:
    """Compute cosine-weighted ambient occlusion (exposure fraction eta).

    For each triangle, eta is the fraction of cosine-weighted hemisphere
    directions that are not occluded by other triangles.

    Parameters
    ----------
    mesh : BodyMesh
    n_rays : number of hemisphere samples per triangle
    seed : RNG seed for reproducibility
    max_leaf : BVH leaf size

    Returns
    -------
    eta : (N,) array in [0, 1]
    """
    normals = mesh.normals
    centroids = mesh.centroids
    n_tri = mesh.n_triangles

    origin_eps = 1e-6 * mesh.scale
    t_min = 10.0 * origin_eps

    tri_data = _precompute_triangle_data(mesh.vertices)
    bvh, tri_order = build_bvh(tri_data["tri_bmin"], tri_data["tri_bmax"], centroids, max_leaf=max_leaf)

    rng = np.random.default_rng(seed)
    base_dirs = cosine_weighted_hemisphere_samples(n_rays, rng=rng)

    eta = np.zeros(n_tri, dtype=np.float64)
    for i in range(n_tri):
        eta[i] = _sample_and_test(
            i,
            centroids[i],
            normals[i],
            base_dirs,
            n_rays,
            origin_eps,
            t_min,
            bvh,
            tri_order,
            tri_data,
        )

    return np.clip(eta, 0.0, 1.0)
