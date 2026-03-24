"""Multi-source illumination with level comparison.

Generates N random plane waves and compares Levels 2-6 on the same body.
Shows how higher fidelity levels add corrections (Fresnel, polarisation,
curvature, diffraction) to the base geometric ReLU formula.

Usage
-----
    python examples/02_multi_source.py
    python examples/02_multi_source.py --n-sources 50
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import aegis
from aegis.tissue.dielectric import SKIN_28GHZ
from aegis.viz.comparison import plot_level_comparison


def random_directions(n: int, rng: np.random.Generator | None = None) -> np.ndarray:
    """Generate n uniformly distributed directions on the sphere."""
    if rng is None:
        rng = np.random.default_rng(42)
    # Marsaglia method
    u = rng.uniform(-1, 1, size=n)
    phi = rng.uniform(0, 2 * np.pi, size=n)
    r = np.sqrt(1 - u**2)
    return np.column_stack([r * np.cos(phi), r * np.sin(phi), u])


def main() -> None:
    parser = argparse.ArgumentParser(description="Multi-source level comparison")
    parser.add_argument("--stl", default=None, help="Path to STL file")
    parser.add_argument("--n-sources", type=int, default=20, help="Number of plane waves")
    parser.add_argument("--no-show", action="store_true")
    parser.add_argument("--backend", default="matplotlib", choices=["matplotlib", "plotly"])
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
            # Use the sphere from example 01
            from examples import _make_sphere  # noqa: this won't work standalone

            print("Thelonious mesh not found. Use --stl to specify a mesh file.")
            return

    print(f"Body: {body.name}, {body.n_triangles:,} triangles")

    # Random plane waves
    rng = np.random.default_rng(42)
    k_hat = random_directions(args.n_sources, rng)
    power = rng.uniform(0.5, 5.0, size=args.n_sources)  # varied S_inc per path

    paths = aegis.PropagationPaths.from_powers(k_hat=k_hat, power=power)
    print(f"Paths: {paths.n_paths} sources, total power = {np.sum(power):.1f} W/m\u00b2")

    # Compute at multiple levels
    tissue = SKIN_28GHZ
    engine = aegis.DosimetryEngine(tissue)
    levels = [2, 3, 4]
    results = {}

    for level in levels:
        result = engine.compute(body, paths, level=level)
        results[level] = result.sab
        print(f"  Level {level}: P_abs = {result.p_abs * 1e3:.2f} mW, peak = {result.peak_sab:.3f} W/m\u00b2")

    # Comparison plot
    out_dir = Path(__file__).resolve().parent / "_output"
    ext = "png" if args.backend == "matplotlib" else "html"
    out_path = out_dir / f"02_multi_source.{ext}"

    print(f"\nRendering level comparison...")
    plot_level_comparison(
        body.vertices,
        results,
        title=f"Level comparison: {args.n_sources} sources",
        out_path=out_path,
        show=not args.no_show,
        backend=args.backend,
    )
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
