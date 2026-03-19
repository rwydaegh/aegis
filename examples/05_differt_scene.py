"""Full pipeline: load a scene from DiffeRT, run dosimetry, visualize.

Requires: pip install aegis[rt]  (installs differt)

If DiffeRT is not installed, this example falls back to synthetic paths
that mimic what a ray tracer would produce.

Usage
-----
    py -3.12 examples/05_differt_scene.py
    py -3.12 examples/05_differt_scene.py --scene path/to/scene.xml
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import aegis
from aegis.constants import C_0, Z_0
from aegis.tissue.dielectric import SKIN_28GHZ
from aegis.viz.heatmap import plot_heatmap
from aegis.viz.dashboard import plot_dashboard


def synthetic_rt_paths(
    n_elements: int = 4,
    n_paths: int = 30,
    rng: np.random.Generator | None = None,
) -> aegis.PropagationPaths:
    """Simulate what a ray tracer would produce: paths with realistic
    amplitude decay, delays, and LOS/NLOS mix."""
    if rng is None:
        rng = np.random.default_rng(99)

    # Mix of LOS and reflected paths
    n_los = n_paths // 3
    n_nlos = n_paths - n_los

    # LOS paths: direct, stronger, frontal
    k_los = np.column_stack([
        rng.normal(0, 0.1, n_los),
        -np.ones(n_los),
        rng.normal(0, 0.1, n_los),
    ])

    # NLOS paths: scattered directions, weaker
    theta = rng.uniform(0, 2 * np.pi, n_nlos)
    phi = rng.uniform(0.3, np.pi - 0.3, n_nlos)
    k_nlos = np.column_stack([
        np.sin(phi) * np.cos(theta),
        np.sin(phi) * np.sin(theta),
        np.cos(phi),
    ])

    k_hat = np.vstack([k_los, k_nlos])
    norms = np.linalg.norm(k_hat, axis=1, keepdims=True)
    k_hat = k_hat / norms

    # Amplitudes: LOS stronger than NLOS
    amp_los = rng.uniform(0.5, 1.0, n_los)
    amp_nlos = rng.uniform(0.05, 0.3, n_nlos)
    amplitude = np.concatenate([amp_los, amp_nlos])
    phase = rng.uniform(0, 2 * np.pi, n_paths)

    # Build psi
    ref = np.zeros_like(k_hat)
    abs_k = np.abs(k_hat)
    min_axis = np.argmin(abs_k, axis=1)
    ref[np.arange(n_paths), min_axis] = 1.0
    e_perp = np.cross(k_hat, ref)
    e_norms = np.linalg.norm(e_perp, axis=1, keepdims=True)
    e_perp = e_perp / np.where(e_norms > 0, e_norms, 1.0)

    E_scale = np.sqrt(2 * Z_0 * 1.0)
    psi = (E_scale * amplitude * np.exp(1j * phase))[:, np.newaxis] * e_perp

    # Element assignment
    element_index = rng.integers(0, n_elements, size=n_paths)

    # Delays (5-50 ns for indoor)
    delay_los = rng.uniform(5e-9, 15e-9, n_los)
    delay_nlos = rng.uniform(15e-9, 50e-9, n_nlos)
    delay = np.concatenate([delay_los, delay_nlos])

    is_los = np.concatenate([np.ones(n_los, dtype=bool), np.zeros(n_nlos, dtype=bool)])

    return aegis.PropagationPaths(
        k_hat=k_hat,
        psi=psi.astype(complex),
        element_index=element_index.astype(np.intp),
        delay=delay,
        is_los=is_los,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="DiffeRT scene example")
    parser.add_argument("--scene", default=None, help="Path to Sionna/Mitsuba XML scene")
    parser.add_argument("--stl", default=None, help="Path to body STL file")
    parser.add_argument("--n-elements", type=int, default=4)
    parser.add_argument("--no-show", action="store_true")
    args = parser.parse_args()

    # Try DiffeRT if scene provided
    paths = None
    if args.scene:
        try:
            from aegis.integration.differt import paths_from_differt_scene

            tx_positions = np.array([
                [5.0, 0.0, 3.0],  # base station position
            ])
            # Repeat for array elements
            tx_positions = np.tile(tx_positions, (args.n_elements, 1))
            # Add small offsets for array spacing
            tx_positions[:, 0] += np.arange(args.n_elements) * 0.05

            rx_position = np.array([0.0, 0.0, 1.0])  # body position

            print(f"Running DiffeRT on {args.scene}...")
            paths = paths_from_differt_scene(
                args.scene,
                tx_positions=tx_positions,
                rx_position=rx_position,
                freq_hz=28e9,
                tx_power_dbm=30.0,
            )
            print(f"DiffeRT found {paths.n_paths} paths")
        except ImportError:
            print("DiffeRT not installed. Install with: pip install aegis[rt]")
            print("Falling back to synthetic paths.\n")
            paths = None

    if paths is None:
        print("Using synthetic ray-traced paths (simulates indoor multipath).")
        paths = synthetic_rt_paths(n_elements=args.n_elements)

    print(f"Paths: {paths.n_paths} ({int(np.sum(paths.is_los))} LOS, "
          f"{int(np.sum(~paths.is_los))} NLOS)")
    print(f"Elements: {paths.n_elements}")

    # Load body
    if args.stl:
        body = aegis.BodyMesh.load(args.stl)
    else:
        data_dir = Path(__file__).resolve().parent.parent.parent / "data"
        stl_path = data_dir / "thelonious.stl"
        if stl_path.exists():
            body = aegis.BodyMesh.load(str(stl_path))
        else:
            print("Thelonious mesh not found. Use --stl.")
            return

    print(f"Body: {body.name}, {body.n_triangles:,} triangles")

    tissue = SKIN_28GHZ
    engine = aegis.DosimetryEngine(tissue)

    # Run full pipeline: incoherent (Level 2) and coherent (Level 7)
    # Level 2: incoherent
    result_l2 = engine.compute(body, paths, level=2)
    print(f"\nLevel 2 (incoherent):")
    print(f"  P_abs = {result_l2.p_abs * 1e3:.2f} mW, peak = {result_l2.peak_sab:.3f} W/m\u00b2")

    # Build UE channel for coherent
    h = np.zeros(paths.n_elements, dtype=complex)
    for j in range(paths.n_elements):
        mask = paths.element_index == j
        h[j] = np.sum(paths.psi[mask, 0]) + 1j * np.sum(paths.psi[mask, 1])

    # Level 7: coherent with MRT
    precoder = aegis.Precoder.mrt(h, P=1.0)
    result_l7 = engine.compute(body, paths, level=7, precoder=precoder, h=h)
    print(f"\nLevel 7 (coherent MRT):")
    print(f"  P_abs = {result_l7.p_abs * 1e3:.2f} mW, peak = {result_l7.peak_sab:.3f} W/m\u00b2")
    print(f"  rho = {result_l7.rho:.4f}")

    out_dir = Path(__file__).resolve().parent / "_output"

    # Heatmaps
    print("\nRendering heatmaps...")
    plot_heatmap(
        body.vertices, result_l7.sab,
        title="Level 7: coherent MIMO with multipath",
        out_path=out_dir / "05_differt_heatmap.html",
        show=not args.no_show,
    )

    # Dashboard
    print("Rendering dashboard...")
    plot_dashboard(
        result_l7,
        title="Full pipeline: multipath -> coherent dosimetry",
        out_path=out_dir / "05_differt_dashboard.png",
        show=not args.no_show,
    )

    print("Done.")


if __name__ == "__main__":
    main()
