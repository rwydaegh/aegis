"""Per-body directional visibility: baked signed angular-clearance LUT and
the distal self-shadowing query.

This module is the foundation for the distal Fock self-shadowing gate. It
provides the LUT angular parameterization (octahedral encode/decode), the
``VisibilityLUT`` dataclass with its int8 clearance codec and seam-aware
bilinear gather, the exact binary-visibility oracle (``compute_visibility``,
reusing the ``occlusion.py`` BVH), and the convexity short-circuit that lets a
convex body skip the bake entirely (keeping the Mie canary exact).

See docs/superpowers/specs/2026-06-06-self-shadowing-visibility-design.md and
docs/superpowers/plans/2026-06-08-visibility-distal-gate.md.
"""

from __future__ import annotations

import dataclasses

import numpy as np
from numpy.typing import NDArray

from aegis.geometry import occlusion
from aegis.geometry.mesh import BodyMesh

try:
    from numba import njit, prange

    NUMBA_AVAILABLE = True
except (ImportError, OSError):
    NUMBA_AVAILABLE = False
    prange = range

    def njit(*args, **kwargs):
        """No-op decorator when Numba is not installed."""
        if len(args) == 1 and callable(args[0]):
            return args[0]
        return lambda f: f


# ---------------------------------------------------------------------------
# Octahedral mapping (simple, full-sphere; Cigolle/Meyer)
# ---------------------------------------------------------------------------


def oct_encode(omega: NDArray[np.floating]) -> NDArray[np.floating]:
    """Unit directions (..., 3) -> octahedral (u, v) in [-1, 1]^2 (simple map)."""
    w = np.asarray(omega, dtype=np.float64)
    denom = np.sum(np.abs(w), axis=-1, keepdims=True)
    p = w / np.where(denom > 1e-300, denom, 1.0)
    px, py, pz = p[..., 0], p[..., 1], p[..., 2]
    lower = pz < 0.0
    u = np.where(lower, (1.0 - np.abs(py)) * np.sign(px), px)
    v = np.where(lower, (1.0 - np.abs(px)) * np.sign(py), py)
    return np.stack([u, v], axis=-1)


def oct_decode(uv: NDArray[np.floating]) -> NDArray[np.floating]:
    """Octahedral (u, v) -> unit directions (..., 3)."""
    a = np.asarray(uv, dtype=np.float64)
    u, v = a[..., 0], a[..., 1]
    z = 1.0 - np.abs(u) - np.abs(v)
    x = np.where(z < 0.0, (1.0 - np.abs(v)) * np.sign(u), u)
    y = np.where(z < 0.0, (1.0 - np.abs(u)) * np.sign(v), v)
    w = np.stack([x, y, z], axis=-1)
    return w / np.linalg.norm(w, axis=-1, keepdims=True)


# ---------------------------------------------------------------------------
# int8 signed-clearance codec
# ---------------------------------------------------------------------------

CLEARANCE_SCALE = 0.5 / 127.0  # rad per LSB, +-0.5 rad (~+-29 deg) span


def _encode_int8(c: NDArray[np.floating]) -> NDArray[np.int8]:
    q = np.round(np.asarray(c, np.float64) / CLEARANCE_SCALE)
    return np.clip(q, -127, 127).astype(np.int8)


def _decode_int8(q: NDArray[np.int8]) -> NDArray[np.float64]:
    return q.astype(np.float64) * CLEARANCE_SCALE


# ---------------------------------------------------------------------------
# VisibilityLUT dataclass + bilinear gather
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class VisibilityLUT:
    """Per-body baked directional visibility (frequency-independent).

    Fields
    ------
    clearance : (M_active, R, R) int8 octahedral signed clearance c(tri, omega)
    clearance_scale : radians per LSB used to decode ``clearance``
    d_occ : (M_active,) binding-occluder distance (mean over shadowed dirs)
    R_occ : (M_active,) binding-occluder in-plane radius
    active_index : (M_active,) -> full triangle index
    exposed_mask : (M,) True where the triangle is fully exposed (gate == 1)
    resolution : R (octahedral axis length)
    vertex_hash : pose-dependent content hash of the source body
    """

    clearance: NDArray[np.int8]
    clearance_scale: float
    d_occ: NDArray[np.float32]
    R_occ: NDArray[np.float32]
    active_index: NDArray[np.int32]
    exposed_mask: NDArray[np.bool_]
    resolution: int
    vertex_hash: int


def _uv_to_grid(coord: NDArray[np.floating], R: int) -> tuple[NDArray[np.int64], NDArray[np.floating]]:
    """Map one octahedral axis in [-1, 1] to continuous grid coords in [0, R-1].

    Returns the floored integer index (clamped so the 2x2 stencil stays in
    range) and the fractional part.
    """
    g = (np.asarray(coord, np.float64) + 1.0) * 0.5 * (R - 1)
    i0 = np.clip(np.floor(g).astype(np.int64), 0, R - 2)
    frac = g - i0
    return i0, frac


def _gather_clearance(
    lut: VisibilityLUT,
    active_rows: NDArray[np.integer],
    dirs: NDArray[np.floating],
) -> NDArray[np.float64]:
    """Decoded clearance (radians) per query.

    ``active_rows`` (K,) integer rows into the stored (M_active, R, R) field;
    ``dirs`` (K, 3) the gather directions omega. Bilinear in (u, v). int8
    corners are decoded to float64 before blending (never blend int8). The
    simple octahedral map folds at the boundary, so clamping the stencil to
    R-2 keeps it in range with negligible seam error at R >= 16.
    """
    R = lut.resolution
    uv = oct_encode(dirs)
    iu, fu = _uv_to_grid(uv[..., 0], R)
    iv, fv = _uv_to_grid(uv[..., 1], R)
    rows = np.asarray(active_rows, np.int64)
    field = lut.clearance
    s = lut.clearance_scale
    c00 = field[rows, iu, iv].astype(np.float64) * s
    c10 = field[rows, iu + 1, iv].astype(np.float64) * s
    c01 = field[rows, iu, iv + 1].astype(np.float64) * s
    c11 = field[rows, iu + 1, iv + 1].astype(np.float64) * s
    w00 = (1.0 - fu) * (1.0 - fv)
    w10 = fu * (1.0 - fv)
    w01 = (1.0 - fu) * fv
    w11 = fu * fv
    return c00 * w00 + c10 * w10 + c01 * w01 + c11 * w11


# ---------------------------------------------------------------------------
# Binary visibility oracle (exact, reuses the occlusion BVH)
# ---------------------------------------------------------------------------


@njit(parallel=True, cache=True)
def _visibility_kernel(
    centroids,
    normals,
    omegas,
    eps,
    t_min,
    delta,
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
    """Per-(triangle, direction) binary visibility. True = source visible.

    Front filter: only cast where omega . n_i > delta; back-facing cells are
    left visible (True) by convention (the kernel's mu>0 rule never reads them,
    and the clearance transform must not see the terminator as a boundary).
    """
    M = centroids.shape[0]
    N = omegas.shape[0]
    out = np.ones((M, N), dtype=np.bool_)
    for i in prange(M):
        nx = normals[i, 0]
        ny = normals[i, 1]
        nz = normals[i, 2]
        ox = centroids[i, 0] + eps * nx
        oy = centroids[i, 1] + eps * ny
        oz = centroids[i, 2] + eps * nz
        for j in range(N):
            wx = omegas[j, 0]
            wy = omegas[j, 1]
            wz = omegas[j, 2]
            if wx * nx + wy * ny + wz * nz <= delta:
                continue  # back-facing -> visible by convention
            hit = occlusion._ray_mesh_any_hit_numba(
                ox,
                oy,
                oz,
                wx,
                wy,
                wz,
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
                i,
                t_min,
            )
            out[i, j] = not hit
    return out


def compute_visibility(
    body: BodyMesh,
    k_hats: NDArray[np.floating],
    *,
    delta: float = 1e-4,
) -> NDArray[np.bool_]:
    """Binary (M, N) source visibility, ``True`` where the source is visible.

    The exact ray-cast oracle the LUT is validated against, and a no-LUT
    hard-occlusion path. Reuses the ``occlusion.py`` BVH; casts one shadow ray
    per (triangle, direction) toward the source ``omega = -k_hat``, ignoring the
    originating triangle. Back-facing cells (``omega . n <= delta``) are
    returned visible by convention.

    Parameters
    ----------
    body : BodyMesh
    k_hats : (N, 3) or (3,) propagation directions (need not be unit; normalised
        internally so the front-face margin is consistent)
    delta : strict front-face margin (rad-equivalent dot threshold)
    """
    k = np.ascontiguousarray(k_hats, dtype=np.float64)
    if k.ndim == 1:
        k = k[None, :]
    k = k / np.linalg.norm(k, axis=1, keepdims=True)
    omegas = np.ascontiguousarray(-k)

    tri_data = occlusion._precompute_triangle_data(body.vertices)
    bvh, tri_order = occlusion.build_bvh(tri_data["tri_bmin"], tri_data["tri_bmax"], body.centroids)

    eps = 1e-6 * body.scale
    t_min = 10.0 * eps

    return _visibility_kernel(
        np.ascontiguousarray(body.centroids, np.float64),
        np.ascontiguousarray(body.normals, np.float64),
        omegas,
        eps,
        t_min,
        delta,
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


# ---------------------------------------------------------------------------
# Octahedral grid directions (shared by the bake and the clearance transform)
# ---------------------------------------------------------------------------

_GRID_DIR_CACHE: dict[int, NDArray[np.float64]] = {}


def _grid_directions(resolution: int) -> NDArray[np.float64]:
    """Unit directions for the ``R x R`` octahedral cell centers, shape (R, R, 3).

    The cell at grid index (i, j) maps to ``u, v = -1 + 2 i/(R-1), -1 + 2 j/(R-1)``
    so it is the exact inverse of ``_uv_to_grid`` (the gather and the bake share
    the same lattice). Cached by resolution.
    """
    cached = _GRID_DIR_CACHE.get(resolution)
    if cached is not None:
        return cached
    axis = np.linspace(-1.0, 1.0, resolution)
    uu, vv = np.meshgrid(axis, axis, indexing="ij")
    uv = np.stack([uu, vv], axis=-1)  # (R, R, 2)
    dirs = oct_decode(uv)  # (R, R, 3)
    _GRID_DIR_CACHE[resolution] = dirs
    return dirs


# ---------------------------------------------------------------------------
# Ray-cast bake: binary map + binding distance + occluder index
# ---------------------------------------------------------------------------


@njit(cache=True)
def _closest_hit_t_tri(
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
    """BVH traversal returning the nearest hit ``(t, tri)``; ``(inf, -1)`` on miss.

    A distance-tracking twin of ``occlusion._ray_mesh_closest_hit_numba`` (which
    returns only the triangle index). The bake needs the hit distance ``t`` to set
    the binding-edge-to-point distance ``d2``, so this lives here rather than
    bloating ``occlusion.py``.
    """
    inv_dx = 1.0 / dx if abs(dx) > 1e-15 else (1.0e30 if dx >= 0 else -1.0e30)
    inv_dy = 1.0 / dy if abs(dy) > 1e-15 else (1.0e30 if dy >= 0 else -1.0e30)
    inv_dz = 1.0 / dz if abs(dz) > 1e-15 else (1.0e30 if dz >= 0 else -1.0e30)

    stack = np.empty(64, dtype=np.int32)
    stack[0] = 0
    sp = 1

    best_t = 1.0e300
    best_tri = -1

    while sp > 0:
        sp -= 1
        ni = stack[sp]
        if not occlusion._ray_aabb_hit(
            ox,
            oy,
            oz,
            inv_dx,
            inv_dy,
            inv_dz,
            bvh_bmin[ni, 0],
            bvh_bmin[ni, 1],
            bvh_bmin[ni, 2],
            bvh_bmax[ni, 0],
            bvh_bmax[ni, 1],
            bvh_bmax[ni, 2],
        ):
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
                t = occlusion._ray_triangle_t(
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
                )
                if t > 0.0 and t < best_t:
                    best_t = t
                    best_tri = ti
        else:
            stack[sp] = li
            sp += 1
            stack[sp] = ri
            sp += 1

    if best_tri < 0:
        return np.inf, -1
    return best_t, best_tri


@njit(parallel=True, cache=True)
def _bake_kernel(
    centroids,
    normals,
    grid_dirs,
    eps,
    t_min,
    delta,
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
    """Per-(triangle, grid cell) closest-hit bake.

    Returns ``(vis, d2, occ_idx)`` flattened over the ``G = R*R`` grid cells: ``vis``
    True where the source direction is visible, ``d2`` the binding hit distance
    (``inf`` where visible/back-facing), ``occ_idx`` the binding triangle (``-1``
    where visible/back-facing). Front filter: cells with ``omega . n <= delta``
    are visible by convention (the terminator is not a distal boundary).
    """
    M = centroids.shape[0]
    G = grid_dirs.shape[0]
    vis = np.ones((M, G), dtype=np.bool_)
    d2 = np.full((M, G), np.inf)
    occ_idx = np.full((M, G), -1, dtype=np.int64)
    for i in prange(M):
        nx = normals[i, 0]
        ny = normals[i, 1]
        nz = normals[i, 2]
        ox = centroids[i, 0] + eps * nx
        oy = centroids[i, 1] + eps * ny
        oz = centroids[i, 2] + eps * nz
        for g in range(G):
            wx = grid_dirs[g, 0]
            wy = grid_dirs[g, 1]
            wz = grid_dirs[g, 2]
            if wx * nx + wy * ny + wz * nz <= delta:
                continue  # back-facing -> visible by convention
            t, tri = _closest_hit_t_tri(
                ox,
                oy,
                oz,
                wx,
                wy,
                wz,
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
                i,
                t_min,
            )
            if tri >= 0:
                vis[i, g] = False
                d2[i, g] = t
                occ_idx[i, g] = tri
    return vis, d2, occ_idx


def _bake_raw_maps(
    body: BodyMesh,
    resolution: int = 32,
    *,
    delta: float = 1e-4,
) -> tuple[NDArray[np.bool_], NDArray[np.float64], NDArray[np.int64], NDArray[np.float64]]:
    """Cast the full octahedral grid per triangle.

    Returns ``(vis, d2, occ_idx, grid_dirs)``: ``vis`` (M, R, R) bool visibility,
    ``d2`` (M, R, R) binding hit distance (``inf`` where visible), ``occ_idx``
    (M, R, R) binding triangle index (``-1`` where visible), and ``grid_dirs``
    (R, R, 3) the shared cell-center directions.
    """
    grid_dirs = _grid_directions(resolution)  # (R, R, 3)
    flat_dirs = np.ascontiguousarray(grid_dirs.reshape(-1, 3))

    tri_data = occlusion._precompute_triangle_data(body.vertices)
    bvh, tri_order = occlusion.build_bvh(tri_data["tri_bmin"], tri_data["tri_bmax"], body.centroids)

    eps = 1e-6 * body.scale
    t_min = 10.0 * eps

    vis, d2, occ_idx = _bake_kernel(
        np.ascontiguousarray(body.centroids, np.float64),
        np.ascontiguousarray(body.normals, np.float64),
        flat_dirs,
        eps,
        t_min,
        delta,
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
    R = resolution
    return (
        vis.reshape(body.n_triangles, R, R),
        d2.reshape(body.n_triangles, R, R),
        occ_idx.reshape(body.n_triangles, R, R),
        grid_dirs,
    )


# ---------------------------------------------------------------------------
# Convexity short-circuit
# ---------------------------------------------------------------------------


def _is_convex(body: BodyMesh, area_tol: float = 0.02) -> bool:
    """True if the mesh surface area matches its convex-hull area within tol.

    A convex body never self-shadows, so the bake is skipped (Mie canary stays
    exact). Degenerate hulls (QhullError) are treated as non-convex (safe).
    """
    from scipy.spatial import ConvexHull, QhullError

    pts = np.unique(body.vertices.reshape(-1, 3), axis=0)
    try:
        hull = ConvexHull(pts)
    except (QhullError, ValueError):
        return False
    if hull.area <= 0.0:
        return False
    return abs(body.total_area - hull.area) / hull.area < area_tol
