"""Quickstart: single plane wave on a body, Level 2, Plotly heatmap.

Loads the Thelonious phantom (or a synthetic sphere), computes absorbed
power density at Level 2 (geometric ReLU), and renders an interactive
3D heatmap in the browser.

Usage
-----
    python examples/01_quickstart.py
    python examples/01_quickstart.py --no-show    # save HTML only
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

# Add src to path if running from repo
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import aegis
from aegis.tissue.dielectric import SKIN_28GHZ
from aegis.viz.heatmap import plot_heatmap


def make_sphere(n_subdivisions: int = 20) -> aegis.BodyMesh:
    """Create a UV sphere as a synthetic body mesh for testing."""
    from aegis.geometry.mesh import BodyMesh

    u = np.linspace(0, 2 * np.pi, n_subdivisions, endpoint=False)
    v = np.linspace(0, np.pi, n_subdivisions)

    vertices_list = []
    for i in range(len(u)):
        for j in range(len(v) - 1):
            # Two triangles per quad
            u0, u1 = u[i], u[(i + 1) % len(u)]
            v0, v1 = v[j], v[j + 1]

            r = 0.15  # 15 cm radius (roughly head-sized)
            p00 = r * np.array([np.sin(v0) * np.cos(u0), np.sin(v0) * np.sin(u0), np.cos(v0)])
            p10 = r * np.array([np.sin(v0) * np.cos(u1), np.sin(v0) * np.sin(u1), np.cos(v0)])
            p01 = r * np.array([np.sin(v1) * np.cos(u0), np.sin(v1) * np.sin(u0), np.cos(v1)])
            p11 = r * np.array([np.sin(v1) * np.cos(u1), np.sin(v1) * np.sin(u1), np.cos(v1)])

            vertices_list.append([p00, p10, p01])
            vertices_list.append([p10, p11, p01])

    tri_vertices = np.array(vertices_list)
    # Shift up so sphere center is at z=0.15
    tri_vertices[:, :, 2] += r

    # Compute normals from cross products
    v0 = tri_vertices[:, 1] - tri_vertices[:, 0]
    v1 = tri_vertices[:, 2] - tri_vertices[:, 0]
    normals = np.cross(v0, v1)
    norms = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = normals / np.where(norms > 0, norms, 1.0)

    # Flip normals outward (should point away from center)
    centroids = np.mean(tri_vertices, axis=1)
    center = np.array([0, 0, r])
    dot = np.sum(normals * (centroids - center), axis=1)
    flip = dot < 0
    normals[flip] *= -1

    areas = 0.5 * np.linalg.norm(np.cross(v0, v1), axis=1)

    return BodyMesh(
        vertices=tri_vertices,
        normals=normals,
        centroids=centroids,
        areas=areas,
        name="Sphere r=0.15m",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="AEGIS quickstart example")
    parser.add_argument("--stl", default=None, help="Path to STL file")
    parser.add_argument("--no-show", action="store_true", help="Save only, don't open browser")
    parser.add_argument("--backend", default="plotly", choices=["plotly", "matplotlib"])
    args = parser.parse_args()

    # Load body mesh
    if args.stl:
        body = aegis.BodyMesh.load(args.stl)
    else:
        # Try Thelonious, fall back to synthetic sphere
        data_dir = Path(__file__).resolve().parent.parent.parent / "data"
        stl_path = data_dir / "thelonious.stl"
        if stl_path.exists():
            body = aegis.BodyMesh.load(str(stl_path))
        else:
            print("Thelonious mesh not found, using synthetic sphere.")
            body = make_sphere()

    print(f"Body: {body.name}, {body.n_triangles:,} triangles, {body.total_area * 1e4:.0f} cm\u00b2")

    # Tissue: skin at 28 GHz
    tissue = SKIN_28GHZ
    print(f"Tissue: {tissue.name}, T0 = {tissue.T0:.4f}")

    # Single plane wave from the front
    k_hat = np.array([0, -1, 0])  # frontal incidence
    S_inc = 10.0  # W/m^2
    paths = aegis.PropagationPaths.from_powers(
        k_hat=k_hat[np.newaxis, :],
        power=np.array([S_inc]),
    )
    print(f"Paths: {paths.n_paths} path, S_inc = {S_inc} W/m\u00b2")

    # Compute dosimetry at Level 2 (geometric ReLU)
    engine = aegis.DosimetryEngine(tissue)
    result = engine.compute(body, paths, level=2)

    print(f"\nResults (Level 2):")
    print(f"  P_abs:    {result.p_abs * 1e3:.2f} mW")
    print(f"  Peak Sab: {result.peak_sab:.3f} W/m\u00b2")

    # Render heatmap
    out_dir = Path(__file__).resolve().parent / "_output"
    ext = "html" if args.backend == "plotly" else "png"
    out_path = out_dir / f"01_quickstart.{ext}"

    print(f"\nRendering heatmap ({args.backend})...")
    plot_heatmap(
        body.vertices,
        result.sab,
        title=f"Level 2: S_inc={S_inc} W/m\u00b2, T0={tissue.T0:.3f}",
        sab_max=S_inc * tissue.T0,
        out_path=out_path,
        show=not args.no_show,
        backend=args.backend,
    )
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
