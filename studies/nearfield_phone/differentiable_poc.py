"""Differentiable near-field dosimetry: proof of concept.

Demonstrates that the whole near-field exposure pipeline is end-to-end
differentiable, and uses the gradients for three things FDTD cannot do cheaply:

1. **Sensitivity Jacobian.** d(metric)/d(phone pose) at the nominal
   front-of-eyes placement, for SAR_wb, psSAR10g and peak APD against the 6
   pose degrees of freedom (3 position, 3 orientation). One reverse-mode pass.

2. **Inverse design by gradient descent.** Find the device orientation that
   *minimises* head psSAR10g at a fixed position, then check the optimum against
   a brute-force scan over the random orientation ensemble. The gradient route
   reaches the same (or lower) value in a handful of steps.

3. **Compliance distance by Newton's method.** Solve for the smallest
   source-to-body distance at which a given radiated power stays under the
   ICNIRP 2020 local psSAR10g limit, using the analytic derivative
   d(psSAR10g)/d(distance). This is exactly the "distance vs dose" relation the
   dose-model team asked about, solved as an equation rather than tabulated.

Run with the JAX backend (set automatically below)::

    python -m studies.nearfield_phone.differentiable_poc
"""

from __future__ import annotations

import json
import os

os.environ.setdefault("AEGIS_ARRAY_BACKEND", "jax")

import jax
import jax.numpy as jnp
import matplotlib

matplotlib.use("Agg")
import sys

import matplotlib.pyplot as plt
import numpy as np

from aegis.geometry.averaging import averaging_matrix_to_jax, precompute_averaging_matrix
from aegis.nearfield.metrics import alpha_field, cube_side_length, h_depth_efficiency
from aegis.nearfield.phone import PhoneSource, compute_sab, euler_to_matrix
from aegis.nearfield.scenarios import _rotation_aligning_z_to, standard_placements
from studies.nearfield_phone import config as C

sys.path.insert(0, str(C.REPO / "theory" / "scripts"))
from _plot_style import apply_monograph_style, fig_size_ieee  # noqa: E402

jax.config.update("jax_enable_x64", True)

# ICNIRP 2020 local psSAR10g basic restriction, head/trunk, general public.
ICNIRP_LOCAL_PSSAR_LIMIT = 2.0  # W/kg
BAND_MHZ = 2450
PLACEMENT = "front_of_eyes"
METRIC_NAMES = ["SAR_wb", "psSAR10g", "peak_APD"]
DOF_NAMES = ["x", "y", "z", "yaw", "pitch", "roll"]


def _soft_max(v, beta):
    """Smooth maximum sum(v * softmax(beta v)); -> max(v) as beta -> inf."""
    return jnp.sum(v * jax.nn.softmax(beta * v))


def build_forward(mesh, band, placement, rho, mass):
    """Return jitted metric functions of the pose parameters (6,) = [pos, euler].

    Position is in metres (world); euler are intrinsic Z-Y-X angles [rad] applied
    on top of the nominal boresight-at-body base rotation.
    """
    centroids = jnp.asarray(mesh.centroids)
    normals = jnp.asarray(mesh.normals)
    areas = jnp.asarray(mesh.areas)
    base_rot = jnp.asarray(_rotation_aligning_z_to(placement.look_dir))

    # Cube averaging matrix (L^2 area) as a differentiable sparse operator.
    L = cube_side_length(rho)
    G_cube = averaging_matrix_to_jax(
        precompute_averaging_matrix(np.asarray(mesh.centroids), np.asarray(mesh.areas), L**2)
    )
    alpha = alpha_field(band.n_tilde, band.freq_hz)
    h = float(h_depth_efficiency(2.0 * alpha * L))
    sar_scale = 2.0 * alpha / rho

    def sab_of(params):
        pos = params[:3]
        rot = euler_to_matrix(params[3], params[4], params[5]) @ base_rot
        src = PhoneSource(position=pos, rotation=rot, pattern=band.pattern, radiated_power_w=1.0)
        return compute_sab(centroids, normals, src, band.t0, band.n_tilde, fresnel=True)

    @jax.jit
    def metrics(params, beta=300.0):
        sab = sab_of(params)
        sar_wb = jnp.sum(sab * areas) / mass
        cube_avg = G_cube @ sab
        pssar = sar_scale * _soft_max(cube_avg, beta) * h
        peak_apd = _soft_max(sab, beta)
        return jnp.stack([sar_wb, pssar, peak_apd])

    @jax.jit
    def pssar_hard(params):
        sab = sab_of(params)
        return sar_scale * jnp.max(G_cube @ sab) * h

    return metrics, pssar_hard


def sensitivity_jacobian(metrics, params0):
    """Jacobian d(metric)/d(pose) and a dimensionless normalised version."""
    jac = np.asarray(jax.jacobian(metrics)(params0))  # (3 metrics, 6 dof)
    vals = np.asarray(metrics(params0))
    # Normalise: per-cm for position, per-10deg for angles, relative to value.
    units = np.array([0.01, 0.01, 0.01, np.deg2rad(10), np.deg2rad(10), np.deg2rad(10)])
    norm = jac * units[None, :] / vals[:, None]
    return jac, norm, vals


def optimise_orientation(metrics, pssar_hard, params0, steps=120, lr=0.05):
    """Adam descent on psSAR10g over the 3 orientation DOF (position fixed)."""
    grad_fn = jax.jit(jax.grad(lambda p: metrics(p)[1]))
    p = np.array(params0, dtype=float)
    m = np.zeros(6)
    v = np.zeros(6)
    mask = np.array([0, 0, 0, 1, 1, 1.0])  # only orientation moves
    b1, b2, eps = 0.9, 0.999, 1e-8
    hist = []
    for t in range(1, steps + 1):
        g = np.asarray(grad_fn(jnp.asarray(p))) * mask
        m = b1 * m + (1 - b1) * g
        v = b2 * v + (1 - b2) * g * g
        mhat = m / (1 - b1**t)
        vhat = v / (1 - b2**t)
        p = p - lr * mhat / (np.sqrt(vhat) + eps)
        hist.append(float(pssar_hard(jnp.asarray(p))))
    return p, np.array(hist)


def brute_force_orientation(pssar_hard, params0, n=512, seed=7):
    """Scan random orientations for the psSAR10g minimum (validation oracle)."""
    rng = np.random.default_rng(seed)
    eulers = rng.uniform(-np.pi, np.pi, size=(n, 3))
    vals = []
    for e in eulers:
        p = np.array(params0)
        p[3:] = e
        vals.append(float(pssar_hard(jnp.asarray(p))))
    vals = np.array(vals)
    return float(vals.min()), float(vals.max()), float(vals.mean()), vals


def compliance_distance(pssar_hard, placement, look_dir, params0, radiated_power_w, target):
    """Newton solve for the smallest distance with P * psSAR10g(d) <= target.

    Uses the analytic derivative d(psSAR10g)/d(distance) along the look axis.
    """
    landmark = jnp.asarray(placement.landmark)
    look = jnp.asarray(look_dir)
    base_orient = jnp.asarray(params0[3:])

    def pssar_of_d(d):
        pos = landmark - look * d
        p = jnp.concatenate([pos, base_orient])
        return radiated_power_w * pssar_hard(p)

    val_grad = jax.jit(jax.value_and_grad(pssar_of_d))
    d = 0.05  # start 5 cm
    hist = []
    for _ in range(40):
        f, fp = val_grad(d)
        f, fp = float(f), float(fp)
        hist.append((d, f))
        # Newton step toward f(d) = target.
        step = (f - target) / fp
        d = float(np.clip(d - step, 1e-3, 1.0))
        if abs(f - target) < 1e-3 * target:
            break
    return d, hist


def main() -> None:
    mesh = C.load_mesh("duke")
    patterns = C.load_patterns()
    band = C.band_tissues(patterns)[BAND_MHZ]
    mass = C.phantom_masses()["duke"]
    placement = standard_placements(mesh)[PLACEMENT]

    metrics, pssar_hard = build_forward(mesh, band, placement, C.RHO_SKIN, mass)
    params0 = np.concatenate([placement.position(), np.zeros(3)])

    print(f"Differentiable PoC: duke / {PLACEMENT} / {BAND_MHZ} MHz")
    vals0 = np.asarray(metrics(jnp.asarray(params0)))
    print(f"  nominal metrics: SAR_wb={vals0[0]:.4e}  psSAR10g={vals0[1]:.4e}  peakAPD={vals0[2]:.4e} (per W)")

    # 1. Sensitivity Jacobian -------------------------------------------------
    jac, norm, vals = sensitivity_jacobian(metrics, jnp.asarray(params0))
    print("\n  normalised sensitivity (relative change per +1 cm / +10 deg):")
    for i, mn in enumerate(METRIC_NAMES):
        print(f"    {mn:9s} " + "  ".join(f"{d}={norm[i, j]:+.3f}" for j, d in enumerate(DOF_NAMES)))

    # 2. Inverse design -------------------------------------------------------
    p_opt, hist = optimise_orientation(metrics, pssar_hard, params0)
    bf_min, bf_max, bf_mean, bf_vals = brute_force_orientation(pssar_hard, params0)
    nominal_pssar = float(pssar_hard(jnp.asarray(params0)))
    print("\n  orientation inverse design (psSAR10g per W, position fixed):")
    print(f"    nominal pose      : {nominal_pssar:.4e}")
    print(f"    gradient optimum  : {hist[-1]:.4e}  ({len(hist)} steps)")
    print(f"    brute-force min   : {bf_min:.4e}  (512 random orientations)")
    print(f"    brute-force range : [{bf_min:.3e}, {bf_max:.3e}], mean {bf_mean:.3e}")

    # 3. Compliance distance --------------------------------------------------
    radiated = 0.25  # 250 mW handset
    d_star, dhist = compliance_distance(
        pssar_hard, placement, placement.look_dir, params0, radiated, ICNIRP_LOCAL_PSSAR_LIMIT
    )
    print(f"\n  compliance distance for {radiated * 1e3:.0f} mW @ limit {ICNIRP_LOCAL_PSSAR_LIMIT} W/kg:")
    print(f"    d* = {d_star * 1e3:.1f} mm  ({len(dhist)} Newton iters)")

    results = {
        "band_mhz": BAND_MHZ,
        "placement": PLACEMENT,
        "nominal_metrics_per_W": dict(zip(METRIC_NAMES, [float(v) for v in vals0], strict=False)),
        "jacobian_raw": jac.tolist(),
        "jacobian_normalised": norm.tolist(),
        "dof_names": DOF_NAMES,
        "metric_names": METRIC_NAMES,
        "orientation_opt": {
            "nominal_pssar_per_W": nominal_pssar,
            "gradient_optimum_per_W": float(hist[-1]),
            "bruteforce_min_per_W": bf_min,
            "bruteforce_max_per_W": bf_max,
            "bruteforce_mean_per_W": bf_mean,
            "n_steps": len(hist),
            "convergence": [float(x) for x in hist],
        },
        "compliance_distance": {
            "radiated_power_W": radiated,
            "limit_W_per_kg": ICNIRP_LOCAL_PSSAR_LIMIT,
            "d_star_mm": d_star * 1e3,
            "newton_history": [[d * 1e3, f] for d, f in dhist],
        },
    }
    (C.OUT_DIR / "poc_results.json").write_text(json.dumps(results, indent=2))
    print(f"\n  wrote {C.OUT_DIR / 'poc_results.json'}")

    _make_figures(norm, hist, bf_vals, bf_min, nominal_pssar, dhist)


def _make_figures(norm, hist, bf_vals, bf_min, nominal_pssar, dhist):
    apply_monograph_style(mode="png")

    # Figure A: sensitivity + inverse-design convergence (two-column).
    fig, (ax0, ax1) = plt.subplots(1, 2, figsize=fig_size_ieee(columns=2, aspect=0.42))
    x = np.arange(len(DOF_NAMES))
    w = 0.26
    for i, mn in enumerate(METRIC_NAMES):
        ax0.bar(x + (i - 1) * w, np.abs(norm[i]), w, label=mn)
    ax0.set_xticks(x)
    ax0.set_xticklabels(["$x$", "$y$", "$z$", "yaw", "pitch", "roll"])
    ax0.set_ylabel(r"$|\partial \log M / \partial p|$  (per cm, per $10^\circ$)")
    ax0.set_title("Pose sensitivity of exposure metrics")
    ax0.legend(frameon=False)

    ax1.plot(np.arange(1, len(hist) + 1), np.array(hist) * 1e3, label="gradient descent")
    ax1.axhline(bf_min * 1e3, ls="--", color="C3", label="brute-force min (512)")
    ax1.axhline(nominal_pssar * 1e3, ls=":", color="0.4", label="nominal pose")
    ax1.set_xlabel("optimisation step")
    ax1.set_ylabel(r"psSAR10g  [mW/kg per W]")
    ax1.set_title("Orientation inverse design")
    ax1.legend(frameon=False)
    fig.savefig(C.FIG_DIR / "poc_sensitivity_opt.pdf")
    fig.savefig(C.FIG_DIR / "poc_sensitivity_opt.png", dpi=200)
    plt.close(fig)
    print(f"  wrote {C.FIG_DIR / 'poc_sensitivity_opt.pdf'}")


if __name__ == "__main__":
    main()
