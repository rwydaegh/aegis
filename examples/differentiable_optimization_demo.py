"""Differentiable optimization demos for AEGIS.

Three scenarios showing end-to-end gradient-based optimization through
the dosimetry pipeline using JAX autodiff:

1. Antenna placement: push antenna away until peak S_ab meets ICNIRP
2. Sector uptilt: find the minimum uptilt for ICNIRP compliance at 50 W
3. MIMO peak exposure: minimize peak S_ab (not total P_abs!) under signal
   constraint - something the closed-form ECBF cannot do

Run:  python3 examples/differentiable_optimization_demo.py
"""

from __future__ import annotations

import time

import jax
import jax.numpy as jnp
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.gridspec import GridSpec

from aegis.coherent import compute_body_channel, compute_exposure_operator, eigendecompose_Q
from aegis.compliance import icnirp_limits
from aegis.constants import Z_0
from aegis.geometry.mesh import BodyMesh
from aegis.kernels.level3_fresnel import level3_fresnel
from aegis.optim import coherent_sab, soft_peak_exposure
from aegis.tissue.dielectric import TissueModel

# ---------------------------------------------------------------------------
# Shared setup
# ---------------------------------------------------------------------------

FREQ_HZ = 28e9
TISSUE = TissueModel.from_database("Skin", FREQ_HZ)
N_TILDE = TISSUE.n_complex
T0 = TISSUE.T0
ICNIRP = icnirp_limits(freq_hz=FREQ_HZ)
K0 = 2 * np.pi * FREQ_HZ / 3e8
SAB_LIMIT = float(ICNIRP.sab_4cm2)  # 20 W/m^2

print(f"Tissue: {TISSUE.name}")
print(f"  eps_r = {TISSUE.eps_r:.2f}, sigma = {TISSUE.sigma:.2f} S/m")
print(f"  T0 = {T0:.4f}, n_tilde = {N_TILDE:.4f}")
print(f"ICNIRP S_ab limit (4 cm^2): {SAB_LIMIT} W/m^2")
print()


# ---------------------------------------------------------------------------
# Demo 1: Antenna placement optimization
# ---------------------------------------------------------------------------


def demo_antenna_placement():
    """Gradient descent on antenna position to minimize peak S_ab.

    63 W EIRP small cell, 28 GHz. Body at origin. Antenna starts at
    0.3 m (above ICNIRP limit) and gets pushed to the compliant distance.
    """
    print("=" * 60)
    print("DEMO 1: Antenna placement optimization")
    print("=" * 60)

    body = BodyMesh.sphere(radius=0.15, n_subdivisions=3)
    normals = jnp.array(body.normals)
    n_tilde = jnp.array(N_TILDE)

    tx_eirp_w = 63.0  # 1 W + 18 dBi
    pos_init = jnp.array([0.3, 0.0, 0.0])

    def peak_sab(pos):
        d = jnp.linalg.norm(pos)
        k_hat = (-pos / d)[None, :]
        power_density = tx_eirp_w / (4 * jnp.pi * d**2)
        sab = level3_fresnel(normals, k_hat, jnp.array([power_density]), n_tilde)
        return soft_peak_exposure(sab)

    grad_fn = jax.jit(jax.grad(peak_sab))
    loss_fn = jax.jit(peak_sab)

    pos = pos_init
    lr = 0.001
    history = {"pos": [np.array(pos)], "loss": [float(loss_fn(pos))]}

    t0 = time.perf_counter()
    for i in range(300):
        g = grad_fn(pos)
        pos = pos - lr * g
        d = jnp.linalg.norm(pos)
        pos = jnp.where(d < 0.2, pos * 0.2 / d, pos)
        pos = jnp.where(d > 5.0, pos * 5.0 / d, pos)

        loss_val = float(loss_fn(pos))
        history["pos"].append(np.array(pos))
        history["loss"].append(loss_val)

        if i % 60 == 0:
            tag = "PASS" if loss_val <= SAB_LIMIT else "FAIL"
            print(f"  iter {i:3d}: S_ab = {loss_val:.2f} W/m^2 [{tag}], d = {float(d):.3f} m")

    elapsed = time.perf_counter() - t0
    d_analytical = np.sqrt(T0 * tx_eirp_w / (4 * np.pi * SAB_LIMIT))
    print(f"  {elapsed:.2f}s ({len(history['loss']) / elapsed:.0f} iter/s)")
    print(f"  Start: d = {float(jnp.linalg.norm(pos_init)):.3f} m, S_ab = {history['loss'][0]:.2f} W/m^2")
    print(f"  End:   d = {float(jnp.linalg.norm(pos)):.3f} m, S_ab = {history['loss'][-1]:.2f} W/m^2")
    print(f"  Analytical ICNIRP boundary: d = {d_analytical:.3f} m")
    print()
    return history


# ---------------------------------------------------------------------------
# Demo 2: Sector antenna uptilt optimization
# ---------------------------------------------------------------------------


def demo_uptilt():
    """Find the minimum uptilt for ICNIRP compliance of a 50 W sector antenna.

    Sector antenna (cos^3 pattern, 9 dBi peak) at 0.8 m from a cylindrical
    torso. At boresight (tilt=0), S_ab exceeds the ICNIRP limit. Gradient
    descent finds the exact tilt where S_ab = 20 W/m^2. Then shows the
    power headroom available at steeper tilts.
    """
    print("=" * 60)
    print("DEMO 2: Sector antenna uptilt")
    print("=" * 60)

    body = BodyMesh.cylinder(radius=0.15, height=0.6, n_segments=48)
    normals = jnp.array(body.normals)
    n_tilde = jnp.array(N_TILDE)

    to_body = jnp.array([0.0, -1.0, 0.0])
    up = jnp.array([0.0, 0.0, 1.0])
    dist = 0.8

    g_peak = 8.0  # cos^3 pattern, ~9 dBi
    n_cosine = 3
    tx_power_w = 50.0

    def peak_sab_at_tilt(tilt):
        boresight = jnp.cos(tilt) * to_body + jnp.sin(tilt) * up
        cos_off = jnp.dot(boresight, to_body)
        gain = g_peak * jnp.maximum(cos_off, 0.0) ** n_cosine
        pd = tx_power_w * gain / (4 * jnp.pi * dist**2)
        sab = level3_fresnel(normals, to_body[None, :], jnp.array([pd]), n_tilde)
        return soft_peak_exposure(sab)

    # Objective: find tilt where peak S_ab = ICNIRP limit
    def loss(tilt):
        return (peak_sab_at_tilt(tilt) - SAB_LIMIT) ** 2

    grad_fn = jax.jit(jax.grad(loss))
    peak_fn = jax.jit(peak_sab_at_tilt)

    # Compute S_ab at boresight
    sab_boresight = float(peak_fn(jnp.array(0.0)))
    print(f"  At tilt=0: S_ab = {sab_boresight:.2f} W/m^2 (limit: {SAB_LIMIT})")

    # Sweep tilt to show the full curve
    tilts_sweep = np.linspace(0, 70, 200)
    sab_sweep = []
    for t in tilts_sweep:
        sab_sweep.append(float(peak_fn(jnp.radians(t))))
    sab_sweep = np.array(sab_sweep)

    # Gradient descent to find exact compliance tilt
    # Start at 20 deg (nonzero to have gradient from cos^n)
    tilt = jnp.radians(20.0)
    lr = 0.0005
    history = {"tilt_deg": [float(jnp.degrees(tilt))], "peak_sab": [float(peak_fn(tilt))]}

    t0 = time.perf_counter()
    for i in range(400):
        g = grad_fn(tilt)
        tilt = tilt - lr * g
        tilt = jnp.clip(tilt, jnp.radians(1.0), jnp.radians(80.0))

        td = float(jnp.degrees(tilt))
        pk = float(peak_fn(tilt))
        history["tilt_deg"].append(td)
        history["peak_sab"].append(pk)

        if i % 80 == 0:
            tag = "PASS" if pk <= SAB_LIMIT else "FAIL"
            print(f"  iter {i:3d}: tilt = {td:.2f} deg, S_ab = {pk:.4f} W/m^2 [{tag}]")

    elapsed = time.perf_counter() - t0
    opt_tilt = float(jnp.degrees(tilt))
    opt_sab = history["peak_sab"][-1]
    print(f"  {elapsed:.2f}s")
    print(f"  Optimal tilt: {opt_tilt:.2f} deg (S_ab = {opt_sab:.4f} W/m^2, target: {SAB_LIMIT})")

    # Power headroom at optimal tilt
    if opt_sab > 0:
        max_power = tx_power_w * SAB_LIMIT / opt_sab
        print(f"  Max compliant power at {opt_tilt:.1f} deg: {max_power:.1f} W (vs {tx_power_w:.0f} W)")
    print()

    history["tilts_sweep"] = tilts_sweep
    history["sab_sweep"] = sab_sweep
    return history


# ---------------------------------------------------------------------------
# Demo 3: MIMO peak-exposure minimization (beyond ECBF)
# ---------------------------------------------------------------------------


def demo_mimo_peak_sab():
    """Minimize peak S_ab on the body under a signal power constraint.

    ECBF minimizes total absorbed power x^H Q x. But ICNIRP limits
    PEAK spatially-averaged S_ab, not total. Gradient descent through
    the full S_ab(r) = ||G_tilde(r) x||^2 map can directly minimize
    the peak, which is a different (and often more useful) objective.

    4-element ULA, 3 multipath components per element, body at 1 m.
    """
    print("=" * 60)
    print("DEMO 3: MIMO peak S_ab minimization (beyond ECBF)")
    print("=" * 60)

    body = BodyMesh.sphere(radius=0.15, n_subdivisions=3)
    normals_np, centroids_np, areas_np = body.normals, body.centroids, body.areas

    n_elements = 4
    wavelength = 3e8 / FREQ_HZ
    d_ant = wavelength / 2

    element_positions = np.array([
        [(i - (n_elements - 1) / 2) * d_ant, 1.0, 0.0]
        for i in range(n_elements)
    ])

    # 3 multipath components per element
    path_directions = np.array([
        [0.0, -1.0, 0.0],
        [0.3, -0.95, 0.0],
        [-0.2, -0.9, 0.3],
    ])
    path_directions /= np.linalg.norm(path_directions, axis=1, keepdims=True)
    path_amplitudes = np.array([1.0, 0.5, 0.3])

    n_paths_per_elem = len(path_directions)
    n_total = n_elements * n_paths_per_elem

    E0 = np.sqrt(2 * Z_0 * 5.0)

    k_hat_np = np.zeros((n_total, 3))
    psi_np = np.zeros((n_total, 3), dtype=complex)
    element_index_np = np.zeros(n_total, dtype=np.intp)

    for j in range(n_elements):
        for p in range(n_paths_per_elem):
            idx = j * n_paths_per_elem + p
            kd = path_directions[p]
            k_hat_np[idx] = kd

            phase = -K0 * np.dot(kd, element_positions[j])
            amp = E0 * path_amplitudes[p]
            e_perp = np.cross(kd, [0, 0, 1])
            n = np.linalg.norm(e_perp)
            if n < 1e-6:
                e_perp = np.cross(kd, [1, 0, 0])
                n = np.linalg.norm(e_perp)
            e_perp /= n

            psi_np[idx] = amp * e_perp * np.exp(1j * phase)
            element_index_np[idx] = j

    print("  Building body channel G_tilde...")
    G_tilde_np = compute_body_channel(
        normals_np, centroids_np,
        k_hat_np, psi_np, element_index_np,
        N_TILDE, TISSUE.sigma, FREQ_HZ, n_elements,
    )
    G_tilde = jnp.array(G_tilde_np)

    Q_np = compute_exposure_operator(G_tilde_np, areas_np)
    eigs, _ = eigendecompose_Q(Q_np)
    print(f"  Q eigenvalues: [{', '.join(f'{e:.4e}' for e in eigs)}]")

    # UE channel at 20 deg azimuth
    ue_angle = np.radians(20)
    h = np.array([
        np.exp(1j * K0 * (i - (n_elements - 1) / 2) * d_ant * np.sin(ue_angle))
        for i in range(n_elements)
    ], dtype=complex)
    h /= np.linalg.norm(h)
    h_j = jnp.array(h)

    x_mrt = jnp.array(h / np.linalg.norm(h))
    mrt_sab = coherent_sab(G_tilde, x_mrt)
    mrt_peak = float(jnp.max(mrt_sab))
    mrt_signal = float(jnp.abs(jnp.vdot(h_j, x_mrt))**2)
    print(f"  MRT: signal = {mrt_signal:.4f}, peak S_ab = {mrt_peak:.4f} W/m^2")

    signal_min = 0.5 * mrt_signal

    def loss(x_flat):
        x = x_flat[:n_elements] + 1j * x_flat[n_elements:]
        x = x / jnp.linalg.norm(x)

        sab = coherent_sab(G_tilde, x)
        peak = soft_peak_exposure(sab, temperature=50.0)

        sig = jnp.abs(jnp.vdot(h_j, x))**2
        sig_violation = jnp.maximum(signal_min - sig, 0.0)

        return peak + 500.0 * sig_violation**2

    grad_fn = jax.jit(jax.grad(loss))

    def metrics(x_flat):
        x = x_flat[:n_elements] + 1j * x_flat[n_elements:]
        x = x / jnp.linalg.norm(x)
        sab = coherent_sab(G_tilde, x)
        return float(jnp.max(sab)), float(jnp.abs(jnp.vdot(h_j, x))**2)

    x_flat = jnp.concatenate([jnp.real(x_mrt), jnp.imag(x_mrt)])
    lr = 0.01
    history = {"peak_sab": [], "signal": []}

    pk, sig = metrics(x_flat)
    history["peak_sab"].append(pk)
    history["signal"].append(sig)

    t0 = time.perf_counter()
    for i in range(800):
        g = grad_fn(x_flat)
        x_flat = x_flat - lr * g

        pk, sig = metrics(x_flat)
        history["peak_sab"].append(pk)
        history["signal"].append(sig)

        if i % 160 == 0:
            sig_ok = "OK" if sig >= signal_min else "LOW"
            print(f"  iter {i:3d}: peak S_ab = {pk:.4f} W/m^2, signal = {sig:.4f} [{sig_ok}]")

    elapsed = time.perf_counter() - t0
    print(f"  {elapsed:.2f}s")
    print(f"  MRT:     peak S_ab = {history['peak_sab'][0]:.4f}, signal = {history['signal'][0]:.4f}")
    print(f"  Optimal: peak S_ab = {history['peak_sab'][-1]:.4f}, signal = {history['signal'][-1]:.4f}")
    if history["peak_sab"][0] > 0:
        print(f"  Peak S_ab reduction: {(1 - history['peak_sab'][-1] / history['peak_sab'][0]) * 100:.1f}%")
    print(f"  Signal constraint ({signal_min:.4f}): {'met' if history['signal'][-1] >= signal_min else 'not met'}")
    print()
    return history, signal_min


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------


def plot_all(h1, h2, h3, signal_min):
    fig = plt.figure(figsize=(16, 10))
    gs = GridSpec(2, 3, figure=fig, hspace=0.35, wspace=0.35)

    # (a) Placement: S_ab convergence
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.plot(h1["loss"], color="#2563eb", linewidth=1.5)
    ax1.axhline(y=SAB_LIMIT, color="#dc2626", linestyle="--", linewidth=1, label=f"ICNIRP {SAB_LIMIT} W/m^2")
    ax1.set_xlabel("Iteration")
    ax1.set_ylabel("Peak S_ab (W/m^2)")
    ax1.set_title("(a) Placement: exposure convergence")
    ax1.legend(fontsize=8)
    ax1.grid(True, alpha=0.3)

    # (b) Placement: trajectory
    ax2 = fig.add_subplot(gs[0, 1])
    positions = np.array(h1["pos"])
    n_pts = len(positions)
    sc = ax2.scatter(positions[:, 0], positions[:, 1], c=np.arange(n_pts), cmap="viridis", s=6, zorder=2)
    ax2.plot(positions[0, 0], positions[0, 1], "rs", ms=10, label="Start", zorder=3)
    ax2.plot(positions[-1, 0], positions[-1, 1], "g*", ms=15, label="End", zorder=3)
    circle = plt.Circle((0, 0), 0.15, fill=True, fc="#ffe0e0", ec="black", lw=2)
    ax2.add_patch(circle)
    ax2.set_xlabel("x (m)")
    ax2.set_ylabel("y (m)")
    ax2.set_title("(b) Placement: antenna trajectory")
    ax2.legend(fontsize=8)
    ax2.set_aspect("equal")
    ax2.grid(True, alpha=0.3)
    plt.colorbar(sc, ax=ax2, label="Iteration", shrink=0.8)

    # (c) Tilt sweep + optimizer convergence
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.plot(h2["tilts_sweep"], h2["sab_sweep"], color="#94a3b8", lw=2, label="S_ab vs tilt (sweep)")
    ax3.axhline(y=SAB_LIMIT, color="#dc2626", ls="--", lw=1, label=f"ICNIRP {SAB_LIMIT} W/m^2")
    ax3.scatter(h2["tilt_deg"][-1], h2["peak_sab"][-1], color="#16a34a", s=100, zorder=3, label=f"Optimal: {h2['tilt_deg'][-1]:.1f} deg")
    ax3.scatter(h2["tilt_deg"][0], h2["peak_sab"][0], color="#dc2626", s=80, zorder=3, marker="s", label=f"Start: {h2['tilt_deg'][0]:.1f} deg")
    ax3.set_xlabel("Uptilt (deg)")
    ax3.set_ylabel("Peak S_ab (W/m^2)")
    ax3.set_title("(c) Uptilt: S_ab vs tilt angle")
    ax3.legend(fontsize=7, loc="upper right")
    ax3.grid(True, alpha=0.3)

    # (d) Tilt convergence
    ax4 = fig.add_subplot(gs[1, 0])
    ax4.plot(h2["tilt_deg"], color="#16a34a", lw=1.5, label="Tilt (deg)")
    ax4.set_xlabel("Iteration")
    ax4.set_ylabel("Uptilt (deg)")
    ax4.set_title("(d) Uptilt: convergence")
    ax4t = ax4.twinx()
    ax4t.plot(h2["peak_sab"], color="#2563eb", lw=1.5, alpha=0.7, label="S_ab")
    ax4t.axhline(y=SAB_LIMIT, color="#dc2626", ls="--", lw=1)
    ax4t.set_ylabel("S_ab (W/m^2)", color="#2563eb")
    ax4.grid(True, alpha=0.3)

    # (e) MIMO peak S_ab
    ax5 = fig.add_subplot(gs[1, 1])
    ax5.plot(h3["peak_sab"], color="#2563eb", lw=1.5)
    ax5.set_xlabel("Iteration")
    ax5.set_ylabel("Peak S_ab (W/m^2)")
    ax5.set_title("(e) MIMO: peak S_ab minimization")
    ax5.grid(True, alpha=0.3)

    # (f) MIMO signal constraint
    ax6 = fig.add_subplot(gs[1, 2])
    ax6.plot(h3["signal"], color="#2563eb", lw=1.5, label="|h$^H$x|$^2$")
    ax6.axhline(y=signal_min, color="#dc2626", ls="--", lw=1.5, label=f"Min signal = {signal_min:.3f}")
    ax6.set_xlabel("Iteration")
    ax6.set_ylabel("Signal power")
    ax6.set_title("(f) MIMO: signal constraint")
    ax6.legend(fontsize=8)
    ax6.grid(True, alpha=0.3)

    fig.suptitle(
        "AEGIS: gradient-based exposure optimization at 28 GHz (JAX autodiff, level 3 Fresnel)",
        fontsize=13, fontweight="bold",
    )
    out = "examples/differentiable_optimization_demo.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print(f"Figure saved to {out}")
    plt.close()


if __name__ == "__main__":
    print("AEGIS Differentiable Optimization Demos")
    print(f"28 GHz | Skin tissue | Level 3 Fresnel kernel")
    print()

    h1 = demo_antenna_placement()
    h2 = demo_uptilt()
    h3, sig_min = demo_mimo_peak_sab()

    plot_all(h1, h2, h3, sig_min)
    print("All demos complete.")
