"""
Compute projected area LUT A_perp(k_hat) for an STL phantom.

For a triangle mesh with per-triangle areas a_j and outward unit normals n_hat_j,
the (no-occlusion) projected area for an incident direction k_hat is approximated by:

    A_perp(k_hat) ≈ Σ_j a_j [ μ_j(k_hat) ]_+,
    μ_j(k_hat) = n_hat_j · (-k_hat),
    [x]_+ = max(0, x)

This matches the convention used across the repo (see scripts/apd_pipeline.py).

Outputs:
  artifacts/body/<phantom_name>/A_perp_lut.npz containing:
    - k_hat: (N, 3) float array of directions (unit vectors)
    - A_perp: (N,) float array of projected areas (m^2 if STL is in meters)
    - n_triangles, surface_area, stl_path, sampler metadata

Acceptance checks (task 01):
  - A_perp is non-negative
  - mean(A_perp) close to surface_area/4 (Cauchy projection identity for convex bodies)

Note: This LUT does NOT include self-occlusion unless explicitly modeled elsewhere.
"""

from __future__ import annotations

import argparse
import struct
from pathlib import Path
from typing import Tuple

import numpy as np


def load_stl_binary(filepath: str | Path) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Load a binary STL file.

    Returns
    -------
    vertices : (M, 3, 3) float array
        Triangle vertices.
    normals : (M, 3) float array
        Unit triangle normals (STL normals are renormalized).
    centroids : (M, 3) float array
        Triangle centroids.
    """
    filepath = Path(filepath)
    with filepath.open("rb") as f:
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
    norms = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = normals / np.where(norms > 0, norms, 1.0)
    return vertices, normals, centroids


def triangle_areas(vertices: np.ndarray) -> np.ndarray:
    """Compute per-triangle areas for vertices shaped (M, 3, 3)."""
    v0, v1, v2 = vertices[:, 0], vertices[:, 1], vertices[:, 2]
    cross = np.cross(v1 - v0, v2 - v0)
    return 0.5 * np.linalg.norm(cross, axis=1)


def fibonacci_sphere(n: int, *, seed: int = 0) -> np.ndarray:
    """
    Deterministic near-uniform sampling on S^2 via Fibonacci / golden spiral.

    Returns k_hat of shape (n, 3).
    """
    if n <= 0:
        raise ValueError("n must be positive")

    # Deterministic: no RNG used; seed kept for future-proof CLI compatibility.
    _ = seed

    i = np.arange(n, dtype=np.float64)
    golden_ratio = (1.0 + np.sqrt(5.0)) / 2.0

    # z in (-1, 1) using half-offset to avoid exact poles
    z = 1.0 - 2.0 * (i + 0.5) / n
    r = np.sqrt(np.maximum(0.0, 1.0 - z * z))
    phi = 2.0 * np.pi * i / golden_ratio

    x = r * np.cos(phi)
    y = r * np.sin(phi)
    k_hat = np.stack([x, y, z], axis=1)

    # Normalize defensively (should already be unit-length up to floating error)
    k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
    return k_hat


def compute_A_perp_lut(
    normals: np.ndarray,
    areas: np.ndarray,
    k_hat: np.ndarray,
    *,
    chunk_dirs: int = 128,
) -> np.ndarray:
    """
    Compute A_perp(k_hat) for all directions.

    Uses chunking over directions to keep memory bounded while leveraging BLAS.
    """
    normals = np.asarray(normals, dtype=np.float64)
    areas = np.asarray(areas, dtype=np.float64)
    k_hat = np.asarray(k_hat, dtype=np.float64)

    if normals.ndim != 2 or normals.shape[1] != 3:
        raise ValueError("normals must have shape (M, 3)")
    if areas.ndim != 1 or areas.shape[0] != normals.shape[0]:
        raise ValueError("areas must have shape (M,) matching normals")
    if k_hat.ndim != 2 or k_hat.shape[1] != 3:
        raise ValueError("k_hat must have shape (N, 3)")
    if chunk_dirs <= 0:
        raise ValueError("chunk_dirs must be positive")

    n_dirs = k_hat.shape[0]
    A_perp = np.zeros(n_dirs, dtype=np.float64)

    # mu = n · (-k); for a chunk of directions, compute mu as (M, C)
    minus_k = -k_hat

    for start in range(0, n_dirs, chunk_dirs):
        end = min(start + chunk_dirs, n_dirs)
        k_chunk = minus_k[start:end]  # (C, 3)
        mu = normals @ k_chunk.T  # (M, C)
        mu_pos = np.maximum(0.0, mu)
        A_perp[start:end] = areas @ mu_pos  # (C,)

    return A_perp


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Compute projected area LUT A_perp(k_hat) for an STL mesh.")
    p.add_argument("--stl", type=str, default="data/thelonious.stl", help="Path to binary STL (default: data/thelonious.stl)")
    p.add_argument("--n", type=int, default=4096, help="Number of directions (default: 4096)")
    p.add_argument(
        "--out",
        type=str,
        default=None,
        help="Output directory (default: artifacts/body/<phantom_name>/)",
    )
    p.add_argument("--chunk", type=int, default=128, help="Direction chunk size for computation (default: 128)")
    p.add_argument("--plot", action="store_true", help="Write a quick diagnostic plot next to the LUT")
    return p.parse_args()


def main() -> None:
    args = _parse_args()

    stl_path = Path(args.stl)
    if not stl_path.exists():
        raise FileNotFoundError(f"STL not found: {stl_path}")

    phantom_name = stl_path.stem
    out_dir = Path(args.out) if args.out is not None else (Path("artifacts") / "body" / phantom_name)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading STL: {stl_path}")
    vertices, normals, centroids = load_stl_binary(stl_path)
    areas = triangle_areas(vertices)

    n_triangles = int(vertices.shape[0])
    surface_area = float(np.sum(areas))

    print(f"Mesh stats:")
    print(f"  triangles: {n_triangles}")
    print(f"  surface_area: {surface_area:.6g} (units^2; depends on STL units)")

    print(f"Sampling directions: N={args.n} (Fibonacci sphere)")
    k_hat = fibonacci_sphere(args.n)

    print(f"Computing A_perp LUT (chunk={args.chunk})...")
    A_perp = compute_A_perp_lut(normals, areas, k_hat, chunk_dirs=args.chunk)

    # Sanity checks required by the task
    A_min = float(np.min(A_perp))
    A_max = float(np.max(A_perp))
    A_mean = float(np.mean(A_perp))

    nonneg = bool(np.all(A_perp >= -1e-12))
    if not nonneg:
        # Clip tiny negatives from rounding for reporting
        n_bad = int(np.sum(A_perp < -1e-12))
        print(f"WARNING: Found {n_bad} A_perp values < -1e-12 (numerical issue?)")

    # Cauchy projection identity: for convex bodies, mean projected area = surface_area / 4
    cauchy_target = surface_area / 4.0
    rel_err = (A_mean - cauchy_target) / cauchy_target if cauchy_target != 0 else np.nan

    i_min = int(np.argmin(A_perp))
    i_max = int(np.argmax(A_perp))

    print("\nSanity checks:")
    print(f"  A_perp non-negative: {nonneg} (min={A_min:.6g})")
    print(f"  mean(A_perp): {A_mean:.6g}")
    print(f"  surface_area/4: {cauchy_target:.6g}")
    print(f"  deviation: {A_mean - cauchy_target:.6g}  (relative {rel_err * 100:.3f}%)")
    print(f"  A_perp range: [{A_min:.6g}, {A_max:.6g}]")
    print(f"  argmin direction k_hat[{i_min}] = {k_hat[i_min]}")
    print(f"  argmax direction k_hat[{i_max}] = {k_hat[i_max]}")

    out_npz = out_dir / "A_perp_lut.npz"
    np.savez_compressed(
        out_npz,
        k_hat=k_hat.astype(np.float64),
        A_perp=A_perp.astype(np.float64),
        n_triangles=n_triangles,
        surface_area=surface_area,
        stl_path=str(stl_path),
        sampler="fibonacci_sphere",
        mu_definition="mu = n_hat · (-k_hat)",
        note_no_occlusion=True,
    )
    print(f"\nWrote: {out_npz}")

    if args.plot:
        try:
            import matplotlib.pyplot as plt
            from matplotlib.colors import Normalize

            fig, ax = plt.subplots(1, 1, figsize=(8, 4.5))
            ax.hist(A_perp, bins=60, color="#377eb8", alpha=0.85, edgecolor="black", linewidth=0.3)
            ax.axvline(cauchy_target, color="gray", linestyle="--", linewidth=2, label="surface_area/4")
            ax.set_title(f"Projected area histogram: {phantom_name} (N={args.n})")
            ax.set_xlabel("A_perp")
            ax.set_ylabel("count")
            ax.grid(True, alpha=0.25)
            ax.legend()

            fig.tight_layout()
            out_png = out_dir / "A_perp_hist.png"
            fig.savefig(out_png, dpi=150, bbox_inches="tight")
            plt.close(fig)
            print(f"Wrote: {out_png}")

            # Directional map (bin on lon/lat, show mean A_perp per bin)
            # k_hat is a direction on the sphere; visualize A_perp(k_hat) as a sky map.
            lon = np.arctan2(k_hat[:, 1], k_hat[:, 0])  # [-pi, pi]
            lat = np.arcsin(np.clip(k_hat[:, 2], -1.0, 1.0))  # [-pi/2, pi/2]

            n_lon = 360
            n_lat = 180
            lon_edges = np.linspace(-np.pi, np.pi, n_lon + 1)
            lat_edges = np.linspace(-np.pi / 2, np.pi / 2, n_lat + 1)

            # Weighted mean per bin: sum(A) / count
            sum_A, _, _ = np.histogram2d(lat, lon, bins=[lat_edges, lon_edges], weights=A_perp)
            cnt, _, _ = np.histogram2d(lat, lon, bins=[lat_edges, lon_edges])
            mean_A = np.divide(sum_A, cnt, out=np.full_like(sum_A, np.nan), where=cnt > 0)

            lon_centers = 0.5 * (lon_edges[:-1] + lon_edges[1:])
            lat_centers = 0.5 * (lat_edges[:-1] + lat_edges[1:])
            Lon, Lat = np.meshgrid(lon_centers, lat_centers)

            fig2 = plt.figure(figsize=(10, 5.5))
            ax2 = fig2.add_subplot(111, projection="mollweide")
            norm = Normalize(vmin=np.nanpercentile(mean_A, 1), vmax=np.nanpercentile(mean_A, 99))
            im = ax2.pcolormesh(Lon, Lat, mean_A, shading="nearest", cmap="viridis", norm=norm)
            ax2.grid(True, alpha=0.25)
            ax2.set_title(f"A_perp(k_hat) directional map (binned): {phantom_name} (N={args.n})")
            cbar = fig2.colorbar(im, ax=ax2, orientation="horizontal", pad=0.08, fraction=0.06)
            cbar.set_label("mean A_perp in bin")

            fig2.tight_layout()
            out_png2 = out_dir / "A_perp_mollweide.png"
            fig2.savefig(out_png2, dpi=150, bbox_inches="tight")
            plt.close(fig2)
            print(f"Wrote: {out_png2}")
        except Exception as e:
            print(f"WARNING: plot requested but failed: {e}")


if __name__ == "__main__":
    main()

