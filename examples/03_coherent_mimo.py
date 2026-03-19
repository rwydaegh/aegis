"""Coherent MIMO dosimetry (Level 7).

Creates synthetic MIMO paths from a 4-element antenna array,
applies MRT precoding, and shows the resulting S_ab map with
Q eigenspectrum via the compliance dashboard.

Usage
-----
    py -3.12 examples/03_coherent_mimo.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import aegis
from aegis.constants import Z_0
from aegis.tissue.dielectric import SKIN_28GHZ
from aegis.viz.heatmap import plot_heatmap
from aegis.viz.dashboard import plot_dashboard


def make_mimo_paths(
    n_elements: int = 4,
    n_paths_per_element: int = 5,
    freq_hz: float = 28e9,
    rng: np.random.Generator | None = None,
) -> tuple[aegis.PropagationPaths, np.ndarray]:
    """Create synthetic MIMO paths with complex amplitudes.

    Returns (paths, h) where h is the UE channel vector.
    """
    if rng is None:
        rng = np.random.default_rng(42)

    n_total = n_elements * n_paths_per_element

    # Random arrival directions (clustered around frontal)
    theta = rng.normal(0, 0.5, size=n_total)  # azimuth spread
    phi = rng.normal(np.pi / 2, 0.3, size=n_total)  # elevation spread
    k_hat = np.column_stack([
        np.sin(phi) * np.cos(theta),
        -np.cos(phi),  # mostly frontal
        np.sin(phi) * np.sin(theta),
    ])
    # Normalise
    norms = np.linalg.norm(k_hat, axis=1, keepdims=True)
    k_hat = k_hat / norms

    # Complex polarisation-amplitude vectors
    # Random amplitude with phase from path delay
    amplitude = rng.uniform(0.1, 1.0, size=n_total)
    phase = rng.uniform(0, 2 * np.pi, size=n_total)

    # Perpendicular polarisation to k_hat
    ref = np.zeros_like(k_hat)
    abs_k = np.abs(k_hat)
    min_axis = np.argmin(abs_k, axis=1)
    ref[np.arange(n_total), min_axis] = 1.0
    e_perp = np.cross(k_hat, ref)
    e_norms = np.linalg.norm(e_perp, axis=1, keepdims=True)
    e_perp = e_perp / np.where(e_norms > 0, e_norms, 1.0)

    # Scale amplitude to get reasonable power levels
    E_scale = np.sqrt(2 * Z_0 * 1.0)  # 1 W/m^2 reference
    psi = (E_scale * amplitude * np.exp(1j * phase))[:, np.newaxis] * e_perp

    # Element indices
    element_index = np.repeat(np.arange(n_elements), n_paths_per_element)

    # UE channel vector (sum of psi per element, projected to scalar)
    h = np.zeros(n_elements, dtype=complex)
    for j in range(n_elements):
        mask = element_index == j
        h[j] = np.sum(psi[mask, 0]) + 1j * np.sum(psi[mask, 1])

    paths = aegis.PropagationPaths(
        k_hat=k_hat,
        psi=psi.astype(complex),
        element_index=element_index.astype(np.intp),
        delay=np.zeros(n_total),
        is_los=np.zeros(n_total, dtype=bool),
    )

    return paths, h


def main() -> None:
    parser = argparse.ArgumentParser(description="Coherent MIMO example (Level 7)")
    parser.add_argument("--stl", default=None, help="Path to STL file")
    parser.add_argument("--n-elements", type=int, default=4, help="Antenna elements")
    parser.add_argument("--no-show", action="store_true")
    args = parser.parse_args()

    # Load body
    if args.stl:
        body = aegis.BodyMesh.load(args.stl)
    else:
        data_dir = Path(__file__).resolve().parent.parent.parent / "data"
        stl_path = data_dir / "thelonious.stl"
        if stl_path.exists():
            body = aegis.BodyMesh.load(str(stl_path))
        else:
            print("Thelonious mesh not found. Use --stl to specify a mesh file.")
            return

    print(f"Body: {body.name}, {body.n_triangles:,} triangles")

    # MIMO paths
    paths, h = make_mimo_paths(n_elements=args.n_elements)
    print(f"MIMO: {args.n_elements} elements, {paths.n_paths} total paths")
    print(f"UE channel ||h|| = {np.linalg.norm(h):.3f}")

    # MRT precoder
    precoder = aegis.Precoder.mrt(h, P=1.0)
    print(f"MRT precoder: ||x||^2 = {precoder.power:.3f} W")

    # Compute at Level 7 (coherent)
    tissue = SKIN_28GHZ
    engine = aegis.DosimetryEngine(tissue)
    result = engine.compute(body, paths, level=7, precoder=precoder, h=h)

    print(f"\nResults (Level 7, coherent):")
    print(f"  P_abs:       {result.p_abs * 1e3:.2f} mW")
    print(f"  Peak Sab:    {result.peak_sab:.3f} W/m\u00b2")
    print(f"  rho:         {result.rho:.4f}")
    if result.eigenvalues is not None:
        print(f"  Q eigenvalues: {result.eigenvalues[:4]}")

    out_dir = Path(__file__).resolve().parent / "_output"

    # Heatmap
    print("\nRendering S_ab heatmap...")
    plot_heatmap(
        body.vertices, result.sab,
        title=f"Level 7 coherent MIMO ({args.n_elements} elements, MRT)",
        out_path=out_dir / "03_coherent_heatmap.html",
        show=not args.no_show,
    )

    # Dashboard
    print("Rendering compliance dashboard...")
    plot_dashboard(
        result,
        title=f"MIMO dashboard ({args.n_elements} elements)",
        out_path=out_dir / "03_coherent_dashboard.png",
        show=not args.no_show,
    )

    print("Done.")


if __name__ == "__main__":
    main()
