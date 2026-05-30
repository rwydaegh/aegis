"""
Compute exposure fraction eta(r) on a triangle mesh via cosine-weighted
ambient-occlusion-style visibility.

Task 04 (agent_tasks/04_exposure_fraction_eta_ambient_occlusion.md)

Definition
----------
For each surface point r with unit normal n̂(r), the exposure fraction η(r) is
the cosine-weighted fraction of the local hemisphere that is visible:

    η(r) = (1/π) ∫_{ω·n̂>0} V(r, ω) (ω·n̂) dω

If we sample ω from the cosine-weighted hemisphere distribution
    p(ω) = (ω·n̂)/π,
then η(r) = E_p[ V(r, ω) ] can be estimated as a simple unoccluded-ray fraction.

Implementation notes
--------------------
- Uses a small, self-contained AABB BVH for ray-mesh "any-hit" occlusion tests.
- No optional dependencies required.
- Deterministic: fixed RNG seed + fixed sampler.

Outputs
-------
- data/eta/<phantom_name>/eta.npz with keys: eta, centroids, normals
- figures/eta_hist_<phantom_name>.png histogram of eta
"""

from __future__ import annotations

import argparse
import struct
import time
from pathlib import Path
from typing import Optional, Tuple

import numpy as np


def load_stl_binary(filepath: str | Path) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Load a *binary* STL file.

    Returns
    -------
    vertices : (N, 3, 3) float array
        Triangle vertices.
    normals : (N, 3) float array
        Triangle normals (unit length; STL normals may be inconsistent).
    centroids : (N, 3) float array
        Triangle centroids.
    """
    filepath = str(filepath)
    with open(filepath, "rb") as f:
        f.read(80)  # header
        num_triangles = struct.unpack("<I", f.read(4))[0]

        vertices = np.zeros((num_triangles, 3, 3), dtype=np.float64)
        normals = np.zeros((num_triangles, 3), dtype=np.float64)

        for i in range(num_triangles):
            normals[i] = struct.unpack("<3f", f.read(12))
            for j in range(3):
                vertices[i, j] = struct.unpack("<3f", f.read(12))
            f.read(2)  # attribute byte count

    centroids = np.mean(vertices, axis=1)

    # Normalize normals; if a normal is zero, recompute from vertices.
    n_norm = np.linalg.norm(normals, axis=1, keepdims=True)
    bad = (n_norm[:, 0] <= 0)
    if np.any(bad):
        v0 = vertices[bad, 0]
        v1 = vertices[bad, 1]
        v2 = vertices[bad, 2]
        nn = np.cross(v1 - v0, v2 - v0)
        nn_norm = np.linalg.norm(nn, axis=1, keepdims=True)
        nn = nn / np.where(nn_norm > 0, nn_norm, 1.0)
        normals[bad] = nn
        n_norm = np.linalg.norm(normals, axis=1, keepdims=True)

    normals = normals / np.where(n_norm > 0, n_norm, 1.0)

    return vertices, normals, centroids


def _normalize(v: np.ndarray, eps: float = 1e-30) -> np.ndarray:
    n = np.linalg.norm(v)
    if n < eps:
        return v * 0.0
    return v / n


def cosine_weighted_hemisphere_samples(n: int, rng: np.random.Generator) -> np.ndarray:
    """
    Samples directions on +Z hemisphere with cosine-weighted distribution.

    Returns: (n, 3) array with z >= 0.
    """
    u1 = rng.random(n)
    u2 = rng.random(n)

    r = np.sqrt(u1)
    phi = 2.0 * np.pi * u2

    x = r * np.cos(phi)
    y = r * np.sin(phi)
    z = np.sqrt(np.maximum(0.0, 1.0 - u1))

    return np.stack([x, y, z], axis=1)


def make_tangent_frame(n: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Build an orthonormal (t, b) basis for a given unit normal n (right-handed: t x b = n).
    """
    n = _normalize(n)
    # Pick a helper vector not parallel to n
    if abs(n[2]) < 0.999:
        a = np.array([0.0, 0.0, 1.0])
    else:
        a = np.array([1.0, 0.0, 0.0])
    t = _normalize(np.cross(a, n))
    b = np.cross(n, t)
    return t, b


def _segment_bbox(tri_indices: np.ndarray, start: int, end: int,
                  tri_bmin: np.ndarray, tri_bmax: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    idx = tri_indices[start:end]
    bmin = np.min(tri_bmin[idx], axis=0)
    bmax = np.max(tri_bmax[idx], axis=0)
    return bmin, bmax


def build_bvh(tri_bmin: np.ndarray, tri_bmax: np.ndarray, tri_centroids: np.ndarray,
              max_leaf: int = 8) -> Tuple[dict[str, np.ndarray], np.ndarray]:
    """
    Build a median-split BVH over triangle AABBs.

    Returns
    -------
    bvh : dict of flat node arrays:
        - bmin, bmax: (Nnodes, 3) float64
        - left, right, start, count: (Nnodes,) int32
    tri_indices : (N,) int array of triangle indices in BVH leaf order
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
        # partition so that [start:mid] are smaller half
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


def ray_aabb_any_hit_scalar(ox: float, oy: float, oz: float,
                            idx: float, idy: float, idz: float,
                            bminx: float, bminy: float, bminz: float,
                            bmaxx: float, bmaxy: float, bmaxz: float) -> bool:
    """
    Slab test for ray-AABB intersection (any hit). Ray parameter t >= 0.
    """
    tmin = -1.0e300
    tmax = 1.0e300

    # X
    t1 = (bminx - ox) * idx
    t2 = (bmaxx - ox) * idx
    if t1 > t2:
        t1, t2 = t2, t1
    tmin = t1 if t1 > tmin else tmin
    tmax = t2 if t2 < tmax else tmax
    if tmax < tmin:
        return False

    # Y
    t1 = (bminy - oy) * idy
    t2 = (bmaxy - oy) * idy
    if t1 > t2:
        t1, t2 = t2, t1
    tmin = t1 if t1 > tmin else tmin
    tmax = t2 if t2 < tmax else tmax
    if tmax < tmin:
        return False

    # Z
    t1 = (bminz - oz) * idz
    t2 = (bmaxz - oz) * idz
    if t1 > t2:
        t1, t2 = t2, t1
    tmin = t1 if t1 > tmin else tmin
    tmax = t2 if t2 < tmax else tmax
    if tmax < tmin:
        return False

    # Require intersection at t >= 0
    return tmax >= 0.0


def ray_triangle_hit_scalar(
    ox: float, oy: float, oz: float,
    dx: float, dy: float, dz: float,
    v0x: float, v0y: float, v0z: float,
    e1x: float, e1y: float, e1z: float,
    e2x: float, e2y: float, e2z: float,
    t_min: float,
) -> bool:
    """
    Möller–Trumbore ray-triangle intersection, any hit with t > t_min.
    """
    # pvec = d x e2
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

    # qvec = tvec x e1
    qx = ty * e1z - tz * e1y
    qy = tz * e1x - tx * e1z
    qz = tx * e1y - ty * e1x
    v = (dx * qx + dy * qy + dz * qz) * inv_det
    if v < 0.0 or (u + v) > 1.0:
        return False

    t = (e2x * qx + e2y * qy + e2z * qz) * inv_det
    return t > t_min


def ray_mesh_any_hit_bvh(
    ox: float, oy: float, oz: float,
    dx: float, dy: float, dz: float,
    bvh: dict[str, np.ndarray],
    tri_indices: np.ndarray,
    tri_v0x: np.ndarray, tri_v0y: np.ndarray, tri_v0z: np.ndarray,
    tri_e1x: np.ndarray, tri_e1y: np.ndarray, tri_e1z: np.ndarray,
    tri_e2x: np.ndarray, tri_e2y: np.ndarray, tri_e2z: np.ndarray,
    ignore_tri: Optional[int],
    t_min: float,
) -> bool:
    """
    BVH traversal for any-hit ray-mesh intersection.
    """
    # Robust inverse direction (avoid division by zero)
    idx = 1.0 / dx if abs(dx) > 1e-15 else 1.0e30
    idy = 1.0 / dy if abs(dy) > 1e-15 else 1.0e30
    idz = 1.0 / dz if abs(dz) > 1e-15 else 1.0e30

    stack = [0]
    bmin = bvh["bmin"]
    bmax = bvh["bmax"]
    left = bvh["left"]
    right = bvh["right"]
    start = bvh["start"]
    count = bvh["count"]
    while stack:
        ni = stack.pop()
        bminx, bminy, bminz = float(bmin[ni, 0]), float(bmin[ni, 1]), float(bmin[ni, 2])
        bmaxx, bmaxy, bmaxz = float(bmax[ni, 0]), float(bmax[ni, 1]), float(bmax[ni, 2])
        if not ray_aabb_any_hit_scalar(ox, oy, oz, idx, idy, idz, bminx, bminy, bminz, bmaxx, bmaxy, bmaxz):
            continue

        li = int(left[ni])
        ri = int(right[ni])
        if li < 0 and ri < 0:
            s0 = int(start[ni])
            e0 = s0 + int(count[ni])
            for k in range(s0, e0):
                ti = int(tri_indices[k])
                if ignore_tri is not None and ti == ignore_tri:
                    continue
                if ray_triangle_hit_scalar(
                    ox, oy, oz, dx, dy, dz,
                    float(tri_v0x[ti]), float(tri_v0y[ti]), float(tri_v0z[ti]),
                    float(tri_e1x[ti]), float(tri_e1y[ti]), float(tri_e1z[ti]),
                    float(tri_e2x[ti]), float(tri_e2y[ti]), float(tri_e2z[ti]),
                    t_min=t_min,
                ):
                    return True
        else:
            # Depth-first; order doesn't matter for any-hit.
            stack.append(li)
            stack.append(ri)

    return False


def save_eta_histogram_png(eta: np.ndarray, out_path: Path, title: str, bins: int = 50) -> None:
    """
    Save a simple histogram PNG without matplotlib (robust in constrained envs).
    """
    try:
        from PIL import Image, ImageDraw, ImageFont  # type: ignore
    except Exception:
        # Fallback to matplotlib if Pillow isn't available.
        import matplotlib.pyplot as plt

        eta = np.asarray(eta, dtype=np.float64)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        plt.figure(figsize=(6, 4))
        plt.hist(eta, bins=bins, range=(0.0, 1.0), density=False, color="#4C72B0", alpha=0.9)
        plt.xlabel(r"exposure fraction $\eta$")
        plt.ylabel("triangle count")
        plt.title(title)
        plt.tight_layout()
        plt.savefig(out_path, dpi=160)
        plt.close()
        return

    eta = np.asarray(eta, dtype=np.float64)
    counts, edges = np.histogram(eta, bins=bins, range=(0.0, 1.0))
    counts = counts.astype(np.float64)

    W, H = 900, 520
    pad_l, pad_r, pad_t, pad_b = 80, 30, 60, 70
    plot_w = W - pad_l - pad_r
    plot_h = H - pad_t - pad_b

    im = Image.new("RGB", (W, H), (255, 255, 255))
    dr = ImageDraw.Draw(im)

    # Title
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    dr.text((pad_l, 20), title, fill=(0, 0, 0), font=font)

    # Axes
    x0, y0 = pad_l, pad_t
    x1, y1 = pad_l + plot_w, pad_t + plot_h
    dr.rectangle([x0, y0, x1, y1], outline=(0, 0, 0), width=2)

    # Bars
    maxc = float(np.max(counts)) if counts.size else 1.0
    if maxc <= 0:
        maxc = 1.0
    bar_w = plot_w / bins
    for i, c in enumerate(counts):
        h = (float(c) / maxc) * plot_h
        bx0 = x0 + i * bar_w
        bx1 = x0 + (i + 1) * bar_w
        by0 = y1 - h
        dr.rectangle([bx0, by0, bx1, y1], fill=(76, 114, 176), outline=None)

    # Labels
    dr.text((pad_l, H - 40), "exposure fraction η (0..1)", fill=(0, 0, 0), font=font)
    dr.text((15, pad_t + plot_h / 2), "triangle count", fill=(0, 0, 0), font=font)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    im.save(out_path, format="PNG")


def infer_repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    root = infer_repo_root()
    p = argparse.ArgumentParser(description="Compute exposure fraction eta on an STL mesh.")
    p.add_argument("--stl", type=str, default=str(root / "data" / "thelonious.stl"))
    p.add_argument("--n_rays", type=int, default=64)
    p.add_argument("--out", type=str, default=None, help="Output dir (default: data/eta/<name>/)")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--max_leaf", type=int, default=8, help="BVH leaf size (triangles).")
    p.add_argument("--progress_every", type=int, default=500, help="Print progress every N triangles.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    stl_path = Path(args.stl)
    phantom = stl_path.stem

    root = infer_repo_root()
    out_dir = Path(args.out) if args.out is not None else (root / "data" / "eta" / phantom)
    out_dir.mkdir(parents=True, exist_ok=True)
    figures_dir = root / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading mesh: {stl_path}")
    t0 = time.time()
    vertices, normals, centroids = load_stl_binary(stl_path)
    n_tri = int(centroids.shape[0])
    print(f"  triangles: {n_tri}")

    # Mesh scale (for robust eps offsets)
    mesh_bmin = np.min(vertices.reshape(-1, 3), axis=0)
    mesh_bmax = np.max(vertices.reshape(-1, 3), axis=0)
    mesh_scale = float(np.linalg.norm(mesh_bmax - mesh_bmin))
    origin_eps = 1e-6 * mesh_scale
    t_min = 10.0 * origin_eps

    # Triangle data for intersection tests
    v0 = vertices[:, 0].astype(np.float64, copy=False)
    v1 = vertices[:, 1].astype(np.float64, copy=False)
    v2 = vertices[:, 2].astype(np.float64, copy=False)
    e1 = (v1 - v0).astype(np.float64, copy=False)
    e2 = (v2 - v0).astype(np.float64, copy=False)

    tri_v0x = v0[:, 0].astype(np.float64, copy=False)
    tri_v0y = v0[:, 1].astype(np.float64, copy=False)
    tri_v0z = v0[:, 2].astype(np.float64, copy=False)
    tri_e1x = e1[:, 0].astype(np.float64, copy=False)
    tri_e1y = e1[:, 1].astype(np.float64, copy=False)
    tri_e1z = e1[:, 2].astype(np.float64, copy=False)
    tri_e2x = e2[:, 0].astype(np.float64, copy=False)
    tri_e2y = e2[:, 1].astype(np.float64, copy=False)
    tri_e2z = e2[:, 2].astype(np.float64, copy=False)

    tri_bmin = np.minimum(np.minimum(v0, v1), v2)
    tri_bmax = np.maximum(np.maximum(v0, v1), v2)

    print("Building BVH...")
    bvh_t0 = time.time()
    bvh, tri_order = build_bvh(tri_bmin, tri_bmax, centroids, max_leaf=int(args.max_leaf))
    print(f"  nodes: {bvh['bmin'].shape[0]}  (leaf size <= {args.max_leaf})")
    print(f"  BVH build time: {time.time() - bvh_t0:.2f} s")

    rng = np.random.default_rng(int(args.seed))
    base_dirs = cosine_weighted_hemisphere_samples(int(args.n_rays), rng=rng)  # (R,3) in local frame

    eta = np.zeros(n_tri, dtype=np.float64)

    print("Casting rays (cosine-weighted hemisphere)...")
    cast_t0 = time.time()
    visible_total = 0
    rays_total = n_tri * int(args.n_rays)

    for i in range(n_tri):
        n = normals[i]
        o = centroids[i] + origin_eps * n
        ox, oy, oz = float(o[0]), float(o[1]), float(o[2])

        t, b = make_tangent_frame(n)
        # Rotate local +Z hemisphere samples to world frame
        dirs = (
            base_dirs[:, 0:1] * t[None, :]
            + base_dirs[:, 1:2] * b[None, :]
            + base_dirs[:, 2:3] * n[None, :]
        )

        vis = 0
        for r in range(dirs.shape[0]):
            d = dirs[r]
            dx, dy, dz = float(d[0]), float(d[1]), float(d[2])
            hit = ray_mesh_any_hit_bvh(
                ox, oy, oz,
                dx, dy, dz,
                bvh,
                tri_order,
                tri_v0x, tri_v0y, tri_v0z,
                tri_e1x, tri_e1y, tri_e1z,
                tri_e2x, tri_e2y, tri_e2z,
                ignore_tri=i,
                t_min=t_min,
            )
            if not hit:
                vis += 1

        eta[i] = vis / float(args.n_rays)
        visible_total += vis

        if args.progress_every > 0 and (i + 1) % int(args.progress_every) == 0:
            elapsed = time.time() - cast_t0
            done = i + 1
            frac = done / n_tri
            rays_done = done * int(args.n_rays)
            rate = rays_done / max(elapsed, 1e-9)
            eta_mean = visible_total / max(rays_done, 1)
            print(f"  {done}/{n_tri} ({frac*100:.1f}%)  rays/s={rate:,.0f}  eta_mean~{eta_mean:.3f}")

    cast_dt = time.time() - cast_t0
    print(f"Ray casting time: {cast_dt:.2f} s  ({rays_total / max(cast_dt, 1e-9):,.0f} rays/s)")

    # Clamp to [0, 1] (numerical safety)
    eta = np.clip(eta, 0.0, 1.0)

    # Save npz
    out_npz = out_dir / "eta.npz"
    np.savez_compressed(out_npz, eta=eta, centroids=centroids, normals=normals)
    print(f"Wrote: {out_npz}")

    # Histogram
    fig_path = figures_dir / f"eta_hist_{phantom}.png"
    save_eta_histogram_png(
        eta,
        fig_path,
        title=f"Exposure fraction histogram: {phantom}  (n_rays={args.n_rays})",
        bins=50,
    )
    print(f"Wrote: {fig_path}")

    print(f"Total runtime: {time.time() - t0:.2f} s")


if __name__ == "__main__":
    main()
