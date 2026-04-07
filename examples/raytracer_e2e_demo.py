"""End-to-end ray tracer demos: real scene geometry through AEGIS dosimetry.

Tests the full pipeline: XML scene -> DiffeRT ray tracing -> PropagationPaths
-> DosimetryEngine -> exposure map. Also tests JAX gradient flow through the
DiffeRT converter into the Fresnel kernel.

Requires: pip install aegis[rt] (DiffeRT)
Optional: pip install aegis[sionna] (Sionna RT, for the Sionna demo)

Run:  python3 examples/raytracer_e2e_demo.py
"""

from __future__ import annotations

import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.gridspec import GridSpec

# ---------------------------------------------------------------------------
# Check what's available
# ---------------------------------------------------------------------------

DIFFERT_AVAILABLE = False
SIONNA_AVAILABLE = False
JAX_AVAILABLE = False

try:
    import differt  # noqa: F401

    DIFFERT_AVAILABLE = True
except ImportError:
    pass

try:
    import sionna  # noqa: F401

    SIONNA_AVAILABLE = True
except ImportError:
    pass

try:
    import jax
    import jax.numpy as jnp

    JAX_AVAILABLE = True
except ImportError:
    pass

from aegis.engine import DosimetryEngine
from aegis.geometry.mesh import BodyMesh
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import TissueModel

FREQ_HZ = 28e9
TISSUE = TissueModel.from_database("Skin", FREQ_HZ)
ENGINE = DosimetryEngine(TISSUE)

SCENES_DIR = Path("data/scenes")
SCENES = [
    "simple_street_canyon",
    "floor_wall",
    "simple_reflector",
    "double_reflector",
]

print(f"DiffeRT: {'installed' if DIFFERT_AVAILABLE else 'NOT installed'}")
print(f"Sionna:  {'installed' if SIONNA_AVAILABLE else 'NOT installed'}")
print(f"JAX:     {'installed' if JAX_AVAILABLE else 'NOT installed'}")
print(f"Tissue:  {TISSUE.name} (T0={TISSUE.T0:.4f})")
print()


# ---------------------------------------------------------------------------
# Demo 1: DiffeRT multi-scene survey
# ---------------------------------------------------------------------------


def demo_differt_scenes():
    """Run DiffeRT on multiple XML scenes and compare exposure across them."""
    if not DIFFERT_AVAILABLE:
        print("SKIP: DiffeRT not installed")
        return None

    from aegis.integration import paths_from_differt_scene

    print("=" * 60)
    print("DEMO 1: DiffeRT multi-scene exposure survey")
    print("=" * 60)

    body = BodyMesh.sphere(radius=0.15, n_subdivisions=3)
    results = {}

    for scene_name in SCENES:
        scene_path = SCENES_DIR / scene_name / f"{scene_name}.xml"
        if not scene_path.exists():
            print(f"  {scene_name}: scene file not found, skipping")
            continue

        t0 = time.perf_counter()
        try:
            paths = paths_from_differt_scene(
                scene_path=str(scene_path),
                tx_positions=np.array([[5.0, 0.0, 3.0]]),
                rx_position=np.array([0.0, 0.0, 1.0]),
                freq_hz=FREQ_HZ,
                max_bounces=2,
                tx_power_dbm=30.0,  # 1 W
            )
        except Exception as e:
            print(f"  {scene_name}: FAILED ({e})")
            continue

        rt_time = time.perf_counter() - t0

        # Run dosimetry at levels 2 and 3
        t1 = time.perf_counter()
        result_l2 = ENGINE.compute(body, paths, level=2)
        result_l3 = ENGINE.compute(body, paths, level=3)
        dose_time = time.perf_counter() - t1

        results[scene_name] = {
            "n_paths": paths.n_paths,
            "n_los": paths.los_paths.n_paths,
            "n_nlos": paths.nlos_paths.n_paths,
            "total_power": paths.total_power,
            "peak_sab_l2": result_l2.peak_sab,
            "peak_sab_l3": result_l3.peak_sab,
            "p_abs_l3": result_l3.p_abs,
            "rt_time": rt_time,
            "dose_time": dose_time,
        }

        print(
            f"  {scene_name:30s}: {paths.n_paths:3d} paths "
            f"({paths.los_paths.n_paths} LOS, {paths.nlos_paths.n_paths} NLOS), "
            f"S_ab = {result_l3.peak_sab:.4f} W/m^2, "
            f"RT {rt_time:.2f}s + dose {dose_time*1000:.1f}ms"
        )

    print()
    return results


# ---------------------------------------------------------------------------
# Demo 2: DiffeRT + JAX gradient (bounce point perturbation)
# ---------------------------------------------------------------------------


def demo_differt_jax_grad():
    """Show JAX gradient flowing through DiffeRT path converter + Fresnel kernel.

    Uses synthetic path vertices (not real DiffeRT scene computation) to
    demonstrate that the DiffeRT -> AEGIS pipeline is fully differentiable.
    Moving bounce points changes the exposure on the body, and JAX computes
    the exact gradient.
    """
    if not JAX_AVAILABLE:
        print("SKIP: JAX not installed")
        return None

    from aegis.integration.differt import paths_from_differt
    from aegis.kernels.level3_fresnel import level3_fresnel
    from aegis.optim import soft_peak_exposure

    print("=" * 60)
    print("DEMO 2: JAX gradient through DiffeRT converter")
    print("=" * 60)

    body = BodyMesh.sphere(radius=0.15, n_subdivisions=3)
    normals = jnp.array(body.normals)
    n_tilde = jnp.array(TISSUE.n_complex)

    # Synthetic multipath: 8 paths, each TX -> bounce -> RX
    rng = np.random.default_rng(42)
    n_paths = 8
    tx_pos = np.array([5.0, 0.0, 3.0])
    rx_pos = np.array([0.0, 0.0, 1.0])

    path_vertices_np = np.zeros((n_paths, 3, 3))
    for i in range(n_paths):
        path_vertices_np[i, 0] = tx_pos
        path_vertices_np[i, -1] = rx_pos
        # Random bounce points between TX and RX
        path_vertices_np[i, 1] = rx_pos + rng.uniform(-3, 3, 3)

    scene_vertices = np.zeros((1, 3))
    scene_normals = np.array([[0.0, 0.0, 1.0]])
    tx_positions = tx_pos[None, :]

    def loss_fn(bounce_points):
        """Peak S_ab as a function of bounce point locations."""
        pv = jnp.zeros((n_paths, 3, 3))
        pv = pv.at[:, 0, :].set(jnp.array(tx_pos))
        pv = pv.at[:, 2, :].set(jnp.array(rx_pos))
        pv = pv.at[:, 1, :].set(bounce_points)

        paths = paths_from_differt(
            vertices=scene_vertices,
            normals=scene_normals,
            path_vertices=pv,
            tx_positions=tx_positions,
            freq_hz=FREQ_HZ,
        )
        sab = level3_fresnel(normals, paths.k_hat, paths.power, n_tilde)
        return soft_peak_exposure(sab)

    bounce_pts = jnp.array(path_vertices_np[:, 1, :])

    # Forward
    t0 = time.perf_counter()
    loss_val = loss_fn(bounce_pts)
    fwd_time = time.perf_counter() - t0
    print(f"  Forward pass: peak S_ab = {float(loss_val):.6f} W/m^2 ({fwd_time*1000:.1f}ms)")

    # Gradient
    t1 = time.perf_counter()
    grad = jax.grad(loss_fn)(bounce_pts)
    grad_time = time.perf_counter() - t1
    print(f"  Gradient: shape {grad.shape}, max |g| = {float(jnp.max(jnp.abs(grad))):.4e} ({grad_time*1000:.1f}ms)")
    print(f"  All finite: {bool(jnp.all(jnp.isfinite(grad)))}")

    # Finite-difference validation
    print("  Validating against finite differences...")
    eps = 1e-5
    fd_grad = np.zeros_like(np.array(bounce_pts))
    for i in range(min(3, n_paths)):  # check first 3 paths
        for j in range(3):
            bp_plus = bounce_pts.at[i, j].set(bounce_pts[i, j] + eps)
            bp_minus = bounce_pts.at[i, j].set(bounce_pts[i, j] - eps)
            fd_grad[i, j] = (float(loss_fn(bp_plus)) - float(loss_fn(bp_minus))) / (2 * eps)

    jax_grad_np = np.array(grad)[:3]
    max_err = np.max(np.abs(jax_grad_np - fd_grad[:3]))
    rel_err = max_err / (np.max(np.abs(fd_grad[:3])) + 1e-30)
    print(f"  Max absolute error (first 3 paths): {max_err:.2e}")
    print(f"  Max relative error: {rel_err:.2e}")
    match = rel_err < 1e-2
    print(f"  Gradient validation: {'PASS' if match else 'FAIL'}")

    # Gradient descent: move bounce points to minimize exposure
    print("\n  Running gradient descent on bounce points...")
    bp = bounce_pts
    lr = 0.05
    history = [float(loss_fn(bp))]

    for i in range(100):
        g = jax.grad(loss_fn)(bp)
        bp = bp - lr * g
        history.append(float(loss_fn(bp)))

    print(f"  Start: S_ab = {history[0]:.6f} W/m^2")
    print(f"  End:   S_ab = {history[-1]:.6f} W/m^2")
    print(f"  Reduction: {(1 - history[-1] / history[0]) * 100:.1f}%")
    print()

    return history


# ---------------------------------------------------------------------------
# Demo 3: DiffeRT real scene + dosimetry level sweep
# ---------------------------------------------------------------------------


def demo_differt_level_sweep():
    """Run all incoherent fidelity levels on DiffeRT paths from a real scene."""
    if not DIFFERT_AVAILABLE:
        print("SKIP: DiffeRT not installed")
        return None

    from aegis.integration import paths_from_differt_scene

    print("=" * 60)
    print("DEMO 3: Fidelity level sweep on street canyon scene")
    print("=" * 60)

    scene_path = SCENES_DIR / "simple_street_canyon" / "simple_street_canyon.xml"
    body = BodyMesh.sphere(radius=0.15, n_subdivisions=3)

    paths = paths_from_differt_scene(
        scene_path=str(scene_path),
        tx_positions=np.array([[5.0, 0.0, 3.0]]),
        rx_position=np.array([0.0, 0.0, 1.0]),
        freq_hz=FREQ_HZ,
        max_bounces=3,
        tx_power_dbm=30.0,
    )
    print(f"  Scene: simple_street_canyon")
    print(f"  Paths: {paths.n_paths} ({paths.los_paths.n_paths} LOS, {paths.nlos_paths.n_paths} NLOS)")
    print(f"  Total incident power: {paths.total_power:.4f} W/m^2")
    print()

    # Sweep levels 0-6
    level_results = ENGINE.sweep_levels(
        body, paths,
        A_ab=body.total_area * 0.3,  # 30% of sphere projected area
        D_max=2.0,
        body_mass=5.0,  # small body
    )

    results = {}
    for level, result in sorted(level_results.items()):
        results[level] = {
            "peak_sab": result.peak_sab,
            "mean_sab": result.mean_sab,
            "p_abs": result.p_abs,
        }
        print(
            f"  Level {level}: peak S_ab = {result.peak_sab:.4f} W/m^2, "
            f"mean = {result.mean_sab:.4f}, P_abs = {result.p_abs:.6f} W"
        )

    print()
    return results


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------


def plot_results(scene_results, grad_history, level_results):
    fig = plt.figure(figsize=(15, 5))
    gs = GridSpec(1, 3, figure=fig, wspace=0.35)

    # (a) Scene comparison
    if scene_results:
        ax1 = fig.add_subplot(gs[0, 0])
        names = list(scene_results.keys())
        peaks = [scene_results[n]["peak_sab_l3"] for n in names]
        n_paths = [scene_results[n]["n_paths"] for n in names]
        short_names = [n.replace("simple_", "").replace("_", "\n") for n in names]

        bars = ax1.bar(range(len(names)), peaks, color="#2563eb", alpha=0.8)
        for i, (bar, np_) in enumerate(zip(bars, n_paths)):
            ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                     f"{np_}p", ha="center", va="bottom", fontsize=8)
        ax1.set_xticks(range(len(names)))
        ax1.set_xticklabels(short_names, fontsize=8)
        ax1.set_ylabel("Peak S_ab (W/m^2)")
        ax1.set_title("(a) DiffeRT: scene comparison (level 3)")
        ax1.grid(True, alpha=0.3, axis="y")

    # (b) Gradient descent on bounce points
    if grad_history:
        ax2 = fig.add_subplot(gs[0, 1])
        ax2.plot(grad_history, color="#2563eb", lw=1.5)
        ax2.set_xlabel("Iteration")
        ax2.set_ylabel("Peak S_ab (W/m^2)")
        ax2.set_title("(b) JAX grad: bounce-point optimization")
        ax2.grid(True, alpha=0.3)

    # (c) Level sweep
    if level_results:
        ax3 = fig.add_subplot(gs[0, 2])
        levels = sorted(level_results.keys())
        peaks = [level_results[l]["peak_sab"] for l in levels]
        ax3.bar(levels, peaks, color="#2563eb", alpha=0.8)
        ax3.set_xticks(levels)
        ax3.set_xlabel("Fidelity level")
        ax3.set_ylabel("Peak S_ab (W/m^2)")
        ax3.set_title("(c) Level sweep: street canyon")
        ax3.grid(True, alpha=0.3, axis="y")

    fig.suptitle(
        "AEGIS ray tracer integration: DiffeRT + dosimetry at 28 GHz",
        fontsize=13, fontweight="bold",
    )
    out = "examples/raytracer_e2e_demo.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print(f"Figure saved to {out}")
    plt.close()


if __name__ == "__main__":
    print("AEGIS Ray Tracer End-to-End Demos")
    print(f"28 GHz | Skin tissue | DiffeRT + JAX")
    print()

    r1 = demo_differt_scenes()
    r2 = demo_differt_jax_grad()
    r3 = demo_differt_level_sweep()

    plot_results(r1, r2, r3)
    print("All demos complete.")
