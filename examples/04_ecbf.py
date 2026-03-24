"""MRT vs ECBF comparison.

Shows how exposure-constrained beamforming (ECBF, Level 8) reduces
absorbed power density compared to maximum ratio transmission (MRT),
while maintaining communication performance.

Usage
-----
    python examples/04_ecbf.py
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
from aegis.viz.comparison import plot_level_comparison


def make_mimo_paths(
    n_elements: int = 8,
    n_paths_per_element: int = 5,
    rng: np.random.Generator | None = None,
) -> tuple[aegis.PropagationPaths, np.ndarray]:
    """Create synthetic MIMO paths. Returns (paths, h)."""
    if rng is None:
        rng = np.random.default_rng(123)

    n_total = n_elements * n_paths_per_element

    # Arrival directions clustered in front
    theta = rng.normal(0, 0.4, size=n_total)
    phi = rng.normal(np.pi / 2, 0.25, size=n_total)
    k_hat = np.column_stack(
        [
            np.sin(phi) * np.cos(theta),
            -np.cos(phi),
            np.sin(phi) * np.sin(theta),
        ]
    )
    norms = np.linalg.norm(k_hat, axis=1, keepdims=True)
    k_hat = k_hat / norms

    # Complex psi
    amplitude = rng.uniform(0.1, 1.0, size=n_total)
    phase = rng.uniform(0, 2 * np.pi, size=n_total)

    ref = np.zeros_like(k_hat)
    abs_k = np.abs(k_hat)
    min_axis = np.argmin(abs_k, axis=1)
    ref[np.arange(n_total), min_axis] = 1.0
    e_perp = np.cross(k_hat, ref)
    e_norms = np.linalg.norm(e_perp, axis=1, keepdims=True)
    e_perp = e_perp / np.where(e_norms > 0, e_norms, 1.0)

    E_scale = np.sqrt(2 * Z_0 * 1.0)
    psi = (E_scale * amplitude * np.exp(1j * phase))[:, np.newaxis] * e_perp

    element_index = np.repeat(np.arange(n_elements), n_paths_per_element)

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
    parser = argparse.ArgumentParser(description="MRT vs ECBF comparison")
    parser.add_argument("--stl", default=None, help="Path to STL file")
    parser.add_argument("--n-elements", type=int, default=8)
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
    print(f"MIMO: {args.n_elements} elements, {paths.n_paths} paths")

    tissue = SKIN_28GHZ
    engine = aegis.DosimetryEngine(tissue)

    # --- MRT (Level 7) ---
    precoder_mrt = aegis.Precoder.mrt(h, P=1.0)
    result_mrt = engine.compute(body, paths, level=7, precoder=precoder_mrt, h=h)

    print(f"\nMRT (Level 7):")
    print(f"  P_abs:    {result_mrt.p_abs * 1e3:.2f} mW")
    print(f"  Peak Sab: {result_mrt.peak_sab:.3f} W/m\u00b2")
    print(f"  rho:      {result_mrt.rho:.4f}")
    print(f"  |h^T x|^2 = {abs(h @ precoder_mrt.x) ** 2:.4f}")

    # --- ECBF (Level 8) ---
    # Set P_abs_max to half of MRT's absorbed power
    P_abs_target = result_mrt.p_abs * 0.5
    result_ecbf = engine.compute(
        body,
        paths,
        level=8,
        h=h,
        P_abs_max=P_abs_target,
        precoder=precoder_mrt,
    )

    # Get the ECBF precoder for signal comparison
    precoder_ecbf = aegis.Precoder.ecbf(h, result_mrt.Q, P_abs_max=P_abs_target, P=1.0)
    signal_ecbf = abs(h @ precoder_ecbf.x) ** 2

    print(f"\nECBF (Level 8, P_abs_max = {P_abs_target * 1e3:.2f} mW):")
    print(f"  P_abs:    {result_ecbf.p_abs * 1e3:.2f} mW")
    print(f"  Peak Sab: {result_ecbf.peak_sab:.3f} W/m\u00b2")
    print(f"  rho:      {result_ecbf.rho:.4f}")
    print(f"  |h^T x|^2 = {signal_ecbf:.4f}")

    # Reduction stats
    p_reduction = (1 - result_ecbf.p_abs / result_mrt.p_abs) * 100
    signal_ratio = signal_ecbf / abs(h @ precoder_mrt.x) ** 2
    print(f"\nComparison:")
    print(f"  Absorption reduction: {p_reduction:.1f}%")
    print(f"  Signal retention:     {signal_ratio * 100:.1f}%")

    # Side-by-side comparison
    out_dir = Path(__file__).resolve().parent / "_output"

    print("\nRendering MRT vs ECBF comparison...")
    plot_level_comparison(
        body.vertices,
        {7: result_mrt.sab, 8: result_ecbf.sab},
        title=f"MRT (Level 7) vs ECBF (Level 8): {p_reduction:.0f}% absorption reduction",
        out_path=out_dir / "04_ecbf_comparison.png",
        show=not args.no_show,
        backend="matplotlib",
    )

    print("Done.")


if __name__ == "__main__":
    main()
