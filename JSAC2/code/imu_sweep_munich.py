"""IMU sensitivity sweep, rate-loss y-axis (proper channel-prediction-error
experiment).

The IMU model: at each control tick, the on-device twin sees the user's pose
through a noisy IMU readout. The twin therefore renders the body mesh and
predicts the channel at theta_imu = theta_true + N(0, sigma_joint^2). The
gradient ascent on the twin's predicted SINR is therefore offset from the
true SINR landscape; the actuated z* is the optimum of the perturbed SINR,
not of the true SINR. The user's actually achieved SINR at z* is what
matters, and may be below the noiseless oracle.

Implementation: encode theta_true -> z_true, run a noiseless oracle loop to
get z_oracle and SINR(z_oracle). Then for each MC trial, sample a
joint-space noise eps, compute the corresponding latent offset
delta_z = encode(theta_true + eps) - z_true, and run a perturbed loop where
  g_k = grad_z[ SINR(z_k + delta_z) ]   # twin's perceived gradient
  z_{k+1} = Proj(z_k + eta * g_k)
  s_actual_k = SINR(z_k)                  # true channel
The reported terminal SINR is s_actual at the loop's exit z_K.

Output:
  outputs/munich_imu_sweep.npz
  outputs/imu_gamma_overlay.{pdf,png}  (figure for SI §S6)
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import jax
import jax.numpy as jnp
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from JSAC2.code.pose_pipeline_jax import (
    load_smplx_jax, load_vposer_jax, make_sinr_fn, _n_complex,
    LATENT_D,
)
from JSAC2.code.vposer_v2 import VPoser
from JSAC2.code.latent_sweep_munich_jax import (
    list_scenes, build_sinr_for_scene, encode_pose_to_z,
    P_TX_DBM, NOISE_DBM, F_C, RHO_NATURAL,
)
from aegis.geometry.pose_stream import PoseStream

jax.config.update("jax_enable_x64", True)

SEED = 42
SIGMA_DEG_GRID = (0.0, 2.0, 4.0, 8.0, 16.0)
N_TRIALS = 5
K_ITER = 8
PLAZA_DIR = Path("/home/user/aegis/data/poses/plaza_run_walks")
OUT_DIR = Path("/home/user/aegis/JSAC2/code/outputs")


def perturbed_grad_ascent(z0, sinr_fn, grad_fn_perturbed, delta_z,
                            n_iter, eta=0.4):
    """Gradient ascent where the twin's perceived gradient comes from
    the channel evaluated at z + delta_z (latent-space IMU offset),
    while the user's actually achieved SINR is sinr_fn(z) at the
    noiseless channel."""
    z = z0.copy()
    sinr_traj = np.zeros(n_iter + 1)
    sinr_traj[0] = float(sinr_fn(jnp.asarray(z)))
    best_sinr = sinr_traj[0]
    best_z = z.copy()
    delta_jax = jnp.asarray(delta_z)
    for k in range(n_iter):
        g = np.asarray(grad_fn_perturbed(jnp.asarray(z), delta_jax))
        gn = float(np.linalg.norm(g))
        if gn < 1e-6:
            sinr_traj[k + 1] = sinr_traj[k]
            continue
        z_new = z + eta * g / gn
        zn = float(np.linalg.norm(z_new))
        if zn > RHO_NATURAL:
            z_new = z_new * (RHO_NATURAL / zn)
        s_new = float(sinr_fn(jnp.asarray(z_new)))  # true channel
        if s_new > sinr_traj[k] - 0.5:
            z = z_new
        else:
            z = best_z.copy()
            eta *= 0.7
        if s_new > best_sinr:
            best_sinr = s_new
            best_z = z_new.copy()
        sinr_traj[k + 1] = s_new
    return np.maximum.accumulate(sinr_traj), best_z


def main():
    print("Loading SMPL-X + VPoser ...")
    sm = load_smplx_jax()
    vw = load_vposer_jax()
    betas = jnp.zeros(10, dtype=jnp.float64)
    vp_torch = VPoser.from_checkpoint()

    rng = np.random.default_rng(SEED)
    walks = sorted(PLAZA_DIR.rglob("*.npz"))
    pose_pool = []
    for w in walks[:60]:
        ps = PoseStream.load(w)
        for f in range(0, len(ps.poses), 30):
            poses = ps.poses[f, :66].reshape(22, 3).copy()
            poses[0] = 0.0
            pose_pool.append(poses)
    pose_pool = np.array(pose_pool)
    print(f"  pose pool: {len(pose_pool)} frames")

    scene_ids = list_scenes()
    sigma_grid_rad = np.deg2rad(np.array(SIGMA_DEG_GRID))
    n_scenes = len(scene_ids)
    n_sigma = len(SIGMA_DEG_GRID)

    sinr_oracle = np.zeros(n_scenes)
    sinr_perturbed = np.zeros((n_scenes, n_sigma, N_TRIALS))
    los_flags = []

    t0 = time.time()
    for s_i, scene_idx in enumerate(scene_ids):
        baseline_pose22 = pose_pool[rng.integers(0, len(pose_pool))]
        sinr_fn, los_flag, label, _ = build_sinr_for_scene(
            scene_idx, sm, vw, betas
        )
        # Perturbed-channel SINR: SINR evaluated at z + delta_z (twin's view)
        @jax.jit
        def sinr_perturbed_fn(z, delta_z):
            return sinr_fn(z + delta_z)
        grad_fn_perturbed = jax.jit(jax.grad(sinr_perturbed_fn, argnums=0))
        los_flags.append(los_flag)

        # Oracle loop (noiseless): delta_z = 0
        z_true = encode_pose_to_z(baseline_pose22, vp_torch)
        # warm-up jit
        _ = float(sinr_fn(jnp.asarray(z_true)))
        _ = grad_fn_perturbed(jnp.asarray(z_true), jnp.zeros(LATENT_D))
        traj_oracle, _ = perturbed_grad_ascent(
            z_true, sinr_fn, grad_fn_perturbed,
            np.zeros(LATENT_D), K_ITER,
        )
        sinr_oracle[s_i] = traj_oracle[-1]

        for sg_i, sigma_rad in enumerate(sigma_grid_rad):
            for tr_i in range(N_TRIALS):
                if sigma_rad == 0:
                    sinr_perturbed[s_i, sg_i, tr_i] = sinr_oracle[s_i]
                    continue
                rng_t = np.random.default_rng(SEED + scene_idx * 10000
                                               + sg_i * 100 + tr_i)
                # Sample joint-space IMU noise, encode through VPoser to get
                # the equivalent latent-space offset delta_z.
                noise = rng_t.standard_normal((22, 3)) * sigma_rad
                noise[0] = 0  # leave global_orient (we never used it anyway)
                theta_noisy = baseline_pose22 + noise
                z_noisy = encode_pose_to_z(theta_noisy, vp_torch)
                delta_z = z_noisy - z_true
                # Run perturbed-grad loop from z_true
                traj_p, _ = perturbed_grad_ascent(
                    z_true, sinr_fn, grad_fn_perturbed,
                    delta_z, K_ITER,
                )
                sinr_perturbed[s_i, sg_i, tr_i] = traj_p[-1]

        loss16 = sinr_oracle[s_i] - sinr_perturbed[s_i, -1, :].mean()
        print(f"    [{s_i+1:2d}/{n_scenes}] scene {scene_idx:2d} "
              f"[{los_flag}] oracle={sinr_oracle[s_i]:+5.1f} dB, "
              f"loss@16deg={loss16:+4.1f} dB, t={time.time()-t0:.0f}s")

    los_flag_arr = np.array(los_flags)
    out_path = OUT_DIR / "munich_imu_sweep.npz"
    np.savez(out_path, sigma_deg=np.array(SIGMA_DEG_GRID),
             sinr_oracle=sinr_oracle, sinr_perturbed=sinr_perturbed,
             los_flag=los_flag_arr, n_trials=N_TRIALS, K_iter=K_ITER, seed=SEED)
    print(f"  finished in {time.time()-t0:.1f}s, wrote {out_path}")

    # Plot
    import matplotlib.pyplot as plt
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "theory" / "scripts"))
    try:
        from _plot_style import apply_monograph_style, fig_size_ieee as _fig_size
        apply_monograph_style()
        def fig_size_ieee(cols=1, ar=0.62):
            return _fig_size(columns=cols, aspect=ar)
    except Exception:
        def fig_size_ieee(cols=1, ar=0.62):
            return (3.5 * cols, 3.5 * cols * ar)

    loss = sinr_oracle[:, None, None] - sinr_perturbed
    flags = ["LOS", "NLOS"]
    colors = {"LOS": "#1F4E79", "NLOS": "#B26A00"}
    fig, ax = plt.subplots(figsize=fig_size_ieee(cols=1, ar=0.62))
    sigma_x = np.array(SIGMA_DEG_GRID)
    for flag in flags:
        m = los_flag_arr == flag
        if not m.any(): continue
        loss_class = loss[m]                              # (S, sigma, trials)
        loss_class = loss_class.transpose(1, 0, 2).reshape(n_sigma, -1)
        mean = loss_class.mean(axis=1)
        std = loss_class.std(axis=1)
        ax.plot(sigma_x, mean, "o-", color=colors[flag],
                label=f"{flag} (n={m.sum()})", linewidth=1.5, markersize=5)
        ax.fill_between(sigma_x, mean - std, mean + std,
                        color=colors[flag], alpha=0.18)
    ax.axhline(0, color="black", linewidth=0.5, linestyle="--", alpha=0.5)
    ax.set_xlabel(r"per-joint IMU attitude noise $\sigma_\mathrm{joint}$ (deg)")
    ax.set_ylabel("closed-loop SINR loss vs noiseless oracle (dB)")
    ax.set_title(rf"IMU sensitivity, $K = {K_ITER}$, "
                 rf"{N_TRIALS} MC trials/cell, $\rho_\mathrm{{nat}} = {RHO_NATURAL}$",
                 fontsize=8)
    ax.set_xticks(sigma_x)
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        p = OUT_DIR / f"imu_gamma_overlay.{ext}"
        fig.savefig(p, dpi=200, bbox_inches="tight")
        print(f"  wrote {p}")


if __name__ == "__main__":
    main()
