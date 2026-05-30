"""Peak local absorbed-power-density (APD) sensitivity to IMU pose noise.

For each Munich scene + IMU noise level, asks two questions:

  Q1 (whole-body integrated): how wrong is the body's total absorbed power
      P_abs_perturbed when the twin renders at noisy theta_hat instead of
      true theta?
  Q2 (peak local):  how far does the peak local absorption move on the
      body surface under the same noise?

Both quantities are evaluated for a fixed operator precoder (MRT against
the noiseless cascaded channel) -- the regulator's view: "given the
precoder the network is using right now, where is the hotspot and what
is the integrated dose, and how robust are those readings to the
on-device pose estimate?"

Output:
  outputs/munich_peak_apd_sensitivity.npz
    fields:
      sigma_deg       (n_sigma,)
      los_flag        (n_scenes,)  'LOS' or 'NLOS'
      peak_dist_m     (n_scenes, n_sigma, n_trials)
      pabs_ratio_db   (n_scenes, n_sigma, n_trials)  # 10*log10(P_perturbed / P_oracle)
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
    load_smplx_jax, load_vposer_jax, _n_complex,
    LATENT_D, vposer_decode_jax,
    smplx_lbs_jax, world_verts, tri_centroids_normals_areas,
)
from JSAC2.code.vposer_v2 import VPoser
from JSAC2.code.latent_sweep_munich_jax import (
    list_scenes, encode_pose_to_z, F_C, P_TX_DBM, NOISE_DBM, TRACE_DIR,
)
from aegis.geometry.pose_stream import PoseStream

jax.config.update("jax_enable_x64", True)

SEED = 42
SIGMA_DEG_GRID = (0.0, 2.0, 4.0, 8.0, 16.0)
N_TRIALS = 8
PLAZA_DIR = Path("/home/user/aegis/data/poses/plaza_run_walks")
OUT_DIR = Path("/home/user/aegis/JSAC2/code/outputs")


def per_triangle_apd_jit(sm, betas, body_centroid, face_az,
                          r_phone, k_dod, k_doa, psi_path, amp_path,
                          bs_positions, bs_center, n_tilde, k0,
                          h_total_oracle):
    """Build a JIT'd function (theta22) -> (sab_per_tri_arbitrary_units,
    centroids_world, areas, peak_idx).

    We use a fixed precoder: MRT against the noiseless h_total_oracle
    (i.e., what the operator would commit to once at the slot the
    regulator audits). The Sab on each triangle is then the sum over
    paths of |beta_n|^2 * |psi_n|^2 * ReLU(-k_doa_n . n_t) (incoherent,
    transmissivity factor T0 absorbed in the proportionality).
    """
    bs_positions = jnp.asarray(bs_positions, jnp.float64)
    bs_center = jnp.asarray(bs_center, jnp.float64)
    body_centroid = jnp.asarray(body_centroid, jnp.float64)
    face_az = jnp.float64(face_az)
    r_phone = jnp.asarray(r_phone, jnp.float64)
    k_dod = jnp.asarray(k_dod, jnp.float64)
    k_doa = jnp.asarray(k_doa, jnp.float64)
    psi_path = jnp.asarray(psi_path, jnp.complex128)
    amp_path = jnp.asarray(amp_path, jnp.complex128)
    h_total_oracle = jnp.asarray(h_total_oracle, jnp.complex128)
    faces_np = sm["faces"]

    # Operator precoder: MRT against the oracle cascaded channel
    h_norm = jnp.linalg.norm(h_total_oracle)
    x_precoder = jnp.conj(h_total_oracle) / jnp.maximum(h_norm, 1e-30)

    # Per-path beta = sum_m x_m * exp(-j k0 (bs_m - bs_c) . k_dod_n)
    rel = bs_positions - bs_center[None, :]                    # (M, 3)
    elem_phase = jnp.exp(-1j * k0 * (rel @ k_dod.T))           # (M, P)
    beta = (jnp.conj(x_precoder)[None, :] @ elem_phase)[0, :]  # (P,)
    # Per-path "incident power" weight (independent of triangle)
    psi_pwr = (jnp.abs(psi_path) ** 2).sum(axis=1)              # (P,)
    p_n = (jnp.abs(amp_path) ** 2) * psi_pwr * (jnp.abs(beta) ** 2)  # (P,)

    @jax.jit
    def sab_per_tri(theta22):
        verts_local = smplx_lbs_jax(theta22, betas, sm)
        verts_w = world_verts(verts_local, body_centroid, face_az, faces_np)
        c, n, a = tri_centroids_normals_areas(verts_w, faces_np)
        # cos(incidence) for each (path, triangle); facing = mu_nt > 0
        mu = -jnp.einsum("nj,tj->nt", k_doa, n)                 # (P, T)
        mu_pos = jnp.maximum(mu, 0.0)
        # Sab(t) ∝ sum_n p_n * mu_pos[n,t]  (proportional to power flux)
        sab_per_tri_val = (p_n[:, None] * mu_pos).sum(axis=0)   # (T,)
        return sab_per_tri_val, c, a

    return sab_per_tri


def main():
    print("Loading SMPL-X + VPoser ...")
    sm = load_smplx_jax()
    vw = load_vposer_jax()
    betas = jnp.zeros(10, dtype=jnp.float64)
    vp_torch = VPoser.from_checkpoint()

    # Pose pool
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

    peak_dist_m = np.zeros((n_scenes, n_sigma, N_TRIALS))
    pabs_ratio_db = np.zeros((n_scenes, n_sigma, N_TRIALS))
    los_flag_arr = []

    t0 = time.time()
    for s_i, scene_idx in enumerate(scene_ids):
        # Load scene
        npz = np.load(TRACE_DIR / f"scene_{scene_idx:02d}.npz",
                       allow_pickle=False)
        bs_pos = npz["bs_pos"]
        bs_positions = npz["bs_positions"]
        body_centroid = npz["body_centroid"]
        face_az = float(npz["face_azimuth_rad"])
        r_phone = npz["phone_xyz"]
        h_scene = npz["h_scene"]
        k_dod = npz["body_k_dod"]
        k_doa = npz["body_k_doa"]
        psi_path = npz["body_psi_path"]
        amp_path = npz["body_amp_path"]
        los_flag = str(npz["los_flag"]) if npz["los_flag"].ndim == 0 \
                                          else str(npz["los_flag"].item())
        los_flag_arr.append(los_flag)

        n_tilde = jnp.complex128(_n_complex(16.5, 25.8, F_C))
        k0 = float(2.0 * np.pi * F_C / 2.99792458e8)

        # Pick a baseline pose for this scene
        baseline_pose22 = pose_pool[rng.integers(0, len(pose_pool))]

        # Compute h_total at oracle pose (for the MRT precoder)
        # Use the SAME pipeline that latent_sweep uses; we re-import h_body
        # via the kirchhoff path inside.
        from JSAC2.code.pose_pipeline_jax import kirchhoff_h_body_native
        verts_local = smplx_lbs_jax(jnp.asarray(baseline_pose22),
                                     betas, sm)
        verts_w = world_verts(verts_local, body_centroid, face_az,
                                sm["faces"])
        c0, n0, a0 = tri_centroids_normals_areas(verts_w, sm["faces"])
        h_body_oracle = kirchhoff_h_body_native(
            c0, n0, a0, r_phone, k_dod, k_doa, psi_path, amp_path,
            bs_positions, bs_pos, n_tilde, k0,
        )
        h_total_oracle = jnp.asarray(h_scene) + h_body_oracle

        # Build the per-triangle APD function with this scene's precoder
        sab_fn = per_triangle_apd_jit(
            sm, betas, body_centroid, face_az, r_phone,
            k_dod, k_doa, psi_path, amp_path,
            bs_positions, bs_pos, n_tilde, k0,
            h_total_oracle,
        )

        # Oracle peak
        sab_o, c_o, a_o = sab_fn(jnp.asarray(baseline_pose22))
        sab_o = np.asarray(sab_o); c_o_np = np.asarray(c_o); a_o_np = np.asarray(a_o)
        peak_o = int(np.argmax(sab_o))
        peak_o_xyz = c_o_np[peak_o]
        p_abs_o = float((sab_o * a_o_np).sum())

        # Per-(sigma, trial)
        rng_scene = np.random.default_rng(SEED + scene_idx * 10000)
        for k_sig, sigma_rad in enumerate(sigma_grid_rad):
            if sigma_rad == 0:
                # No noise: numerically reproduces oracle
                peak_dist_m[s_i, k_sig, :] = 0.0
                pabs_ratio_db[s_i, k_sig, :] = 0.0
                continue
            for t_i in range(N_TRIALS):
                # Per-axis-component Gaussian noise on each joint axis-angle
                eps = rng_scene.normal(0, sigma_rad, baseline_pose22.shape)
                eps[0] = 0.0  # don't perturb root (joint 0)
                theta_noisy = baseline_pose22 + eps
                sab_p, c_p, a_p = sab_fn(jnp.asarray(theta_noisy))
                sab_p = np.asarray(sab_p); c_p_np = np.asarray(c_p); a_p_np = np.asarray(a_p)
                peak_p = int(np.argmax(sab_p))
                peak_p_xyz = c_p_np[peak_p]
                p_abs_p = float((sab_p * a_p_np).sum())
                peak_dist_m[s_i, k_sig, t_i] = float(
                    np.linalg.norm(peak_p_xyz - peak_o_xyz)
                )
                pabs_ratio_db[s_i, k_sig, t_i] = 10.0 * np.log10(
                    max(p_abs_p, 1e-30) / max(p_abs_o, 1e-30)
                )

        sig16_dist = peak_dist_m[s_i, -1, :].mean()
        sig16_pabs = pabs_ratio_db[s_i, -1, :].mean()
        print(f"    [{s_i+1:2d}/{n_scenes}] scene {scene_idx:2d} [{los_flag:4s}] "
              f"peak_dist@16deg={sig16_dist*100:5.1f} cm  "
              f"P_abs ratio@16deg={sig16_pabs:+5.2f} dB  t={time.time()-t0:.0f}s")

    los_flag_arr = np.array(los_flag_arr)
    out = OUT_DIR / "munich_peak_apd_sensitivity.npz"
    np.savez(out,
             sigma_deg=np.array(SIGMA_DEG_GRID),
             los_flag=los_flag_arr,
             peak_dist_m=peak_dist_m,
             pabs_ratio_db=pabs_ratio_db,
             n_trials=N_TRIALS, seed=SEED)
    print(f"  finished in {time.time()-t0:.1f}s, wrote {out}")

    # Quick aggregate report
    print("\nSummary (mean +/- std across scenes & trials):")
    print(f"  {'sigma':>6}  {'peak dist (cm)':>16}  {'P_abs ratio (dB)':>18}")
    for k_sig, sg in enumerate(SIGMA_DEG_GRID):
        d = peak_dist_m[:, k_sig, :].flatten() * 100  # m -> cm
        p = pabs_ratio_db[:, k_sig, :].flatten()
        print(f"  {sg:>5.1f}d  {d.mean():>7.1f} +/- {d.std():4.1f}  "
              f"{p.mean():>+8.2f} +/- {p.std():4.2f}")

    # Plot
    import matplotlib.pyplot as plt
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "theory" / "scripts"))
    try:
        from _plot_style import apply_monograph_style, fig_size_ieee as _fig_size
        apply_monograph_style()
        def fig_size_ieee(cols=1, ar=0.55):
            return _fig_size(columns=cols, aspect=ar)
    except Exception:
        def fig_size_ieee(cols=1, ar=0.55):
            return (3.5 * cols, 3.5 * cols * ar)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=fig_size_ieee(cols=2, ar=0.45))
    sig_x = np.array(SIGMA_DEG_GRID)
    colors = {"LOS": "#1F4E79", "NLOS": "#B26A00"}
    for flag in ("LOS", "NLOS"):
        m = los_flag_arr == flag
        if not m.any(): continue
        d_m = peak_dist_m[m].reshape(-1, n_sigma, N_TRIALS) * 100  # cm
        d_mean = d_m.mean(axis=(0, 2)); d_std = d_m.std(axis=(0, 2))
        ax1.plot(sig_x, d_mean, "o-", color=colors[flag],
                 label=f"{flag} (n={m.sum()})", lw=1.5, ms=5)
        ax1.fill_between(sig_x, d_mean - d_std, d_mean + d_std,
                          color=colors[flag], alpha=0.18)
        p_db = pabs_ratio_db[m].reshape(-1, n_sigma, N_TRIALS)
        p_mean = p_db.mean(axis=(0, 2)); p_std = p_db.std(axis=(0, 2))
        ax2.plot(sig_x, p_mean, "o-", color=colors[flag], lw=1.5, ms=5)
        ax2.fill_between(sig_x, p_mean - p_std, p_mean + p_std,
                          color=colors[flag], alpha=0.18)
    ax1.set_xlabel(r"per-joint IMU attitude noise $\sigma_\mathrm{joint}$ (deg)")
    ax1.set_ylabel("peak-APD location error (cm)")
    ax1.set_xticks(sig_x); ax1.legend(loc="upper left", fontsize=8)
    ax1.grid(True, alpha=0.3)
    ax2.set_xlabel(r"per-joint IMU attitude noise $\sigma_\mathrm{joint}$ (deg)")
    ax2.set_ylabel(r"whole-body $P_\mathrm{abs}$ ratio (dB, perturbed/oracle)")
    ax2.set_xticks(sig_x); ax2.axhline(0, color="black", lw=0.5, ls="--", alpha=0.5)
    ax2.grid(True, alpha=0.3)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        p = OUT_DIR / f"peak_apd_sensitivity.{ext}"
        fig.savefig(p, dpi=200, bbox_inches="tight")
        print(f"  wrote {p}")


if __name__ == "__main__":
    main()
