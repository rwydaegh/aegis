"""Hero figure for §VIII (Munich variant): pick the highest-gain Munich
scene, render baseline-vs-best body silhouette + SINR-over-samples panel.

Drop-in replacement for fig_hero_latent.py that uses the cached Munich
traces instead of synthetic free-space.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "theory" / "scripts"))

try:
    from _plot_style import apply_monograph_style, fig_size_ieee as _fig_size
    apply_monograph_style()
    def fig_size_ieee(cols=2, ar=0.34):
        return _fig_size(columns=cols, aspect=ar)
except Exception:
    def fig_size_ieee(cols=2, ar=0.34):
        return (3.5 * cols, 3.5 * cols * ar)

from JSAC2.code.latent_sweep_munich import (
    load_munich_scene, encode_pose, decode_z, rate_at_z_munich, RHO_Z,
    LATENT_D, P_TX_DBM, NOISE_DBM,
)
from JSAC2.code.scene_smplx import make_body_smplx
from JSAC2.code.kirchhoff import kirchhoff_h_body, mrt_sinr_db
from aegis.geometry.pose_stream import PoseStream

NPZ = Path("/home/user/aegis/JSAC2/code/outputs/munich_existence.npz")
OUT_DIR = Path("/home/user/aegis/JSAC2/code/outputs")


def render_body_bs_view(ax, body, bs_pos, view="bs"):
    """Render mesh from BS perspective with cosine illumination shading.

    view='bs' projects onto the (y, z) plane of the body's local frame
    (which we approximate by world (y, z) for BS roughly above)."""
    verts = np.asarray(body.mesh.vertices)
    faces = np.asarray(body.mesh.faces)
    centroid = body.mesh.centroid
    verts_local = verts - centroid

    if view == "bs":
        xi, yi, depth_axis = 1, 2, 0
    elif view == "top":
        xi, yi, depth_axis = 0, 1, 2
    else:
        raise ValueError(view)

    polys = verts_local[faces][:, :, [xi, yi]]
    centroid_depth = verts_local[faces].mean(axis=1)[:, depth_axis]
    order = np.argsort(centroid_depth)
    polys = polys[order]

    bs_local = bs_pos - body.mesh.centroid
    tri_centers = verts_local[faces].mean(axis=1)
    to_bs = bs_local - tri_centers
    to_bs /= np.linalg.norm(to_bs, axis=1, keepdims=True)
    normals = body.mesh.face_normals
    illum = np.einsum("ij,ij->i", normals, to_bs)[order]
    illum = np.clip(illum, 0, 1)
    cmap = plt.colormaps["inferno"]
    colors = cmap(0.2 + 0.7 * illum)

    pc = PolyCollection(polys, facecolors=colors, edgecolors="none")
    ax.add_collection(pc)
    ax.set_xlim(verts_local[:, xi].min() - 0.05, verts_local[:, xi].max() + 0.05)
    ax.set_ylim(verts_local[:, yi].min() - 0.05, verts_local[:, yi].max() + 0.05)
    ax.set_aspect("equal")


def main():
    d = np.load(NPZ, allow_pickle=False)
    los_flag = np.array([s.decode() if isinstance(s, bytes) else str(s)
                         for s in d["los_flag"]])
    sinr_baseline = d["sinr_baseline"]
    sinr_existence_max = d["sinr_existence_max"]

    gains = sinr_existence_max - sinr_baseline
    # Pick highest-gain NLOS scene (hero for the body-RIS rescue story);
    # fall back to any scene if no NLOS.
    nlos_mask = los_flag == "NLOS"
    if nlos_mask.any() and gains[nlos_mask].max() > 0:
        cand = np.where(nlos_mask)[0]
        best_scene = int(cand[np.argmax(gains[nlos_mask])])
    else:
        best_scene = int(np.argmax(gains))
    best_gain = gains[best_scene]
    print(f"  hero scene: idx={best_scene}, los={los_flag[best_scene]}, "
          f"gain={best_gain:.2f} dB, baseline={sinr_baseline[best_scene]:.1f} dB, "
          f"best={sinr_existence_max[best_scene]:.1f} dB")

    SEED = int(d["seed"])
    # Replay the same z0 selection used in the Munich sweep
    rng = np.random.default_rng(SEED)
    walks = sorted(Path("/home/user/aegis/data/poses/plaza_run_walks").rglob("*.npz"))
    pose_pool = []
    for w in walks[:60]:
        ps = PoseStream.load(w)
        for f in range(0, len(ps.poses), 30):
            poses = ps.poses[f, :66].reshape(22, 3).copy()
            poses[0] = 0.0
            pose_pool.append(poses)
    pose_pool = np.array(pose_pool)
    # Match latent_sweep_munich.main(): pose draws done in scene order
    baseline_pose = None
    for s in range(best_scene + 1):
        baseline_pose = pose_pool[rng.integers(0, len(pose_pool))]

    (bs, h_scene, r_phone, body_paths, body_centroid, face_az, flag, label,
     _) = load_munich_scene(best_scene)
    z0 = encode_pose(baseline_pose)

    # Reproduce the existence sampling to find best_z (use SEED + best_scene).
    # Sampling is on the global naturalness ball ||z|| <= rho_nat anchored at
    # origin -- NOT around z_0 -- to match latent_sweep_munich_jax.py.
    scene_seed = SEED + best_scene
    rng_scene = np.random.default_rng(scene_seed)
    n_samples = 100
    best_z = z0.copy()
    best_sinr_seen = -np.inf
    sinrs = []
    for i in range(n_samples):
        d_dir = rng_scene.standard_normal(LATENT_D)
        d_dir /= np.linalg.norm(d_dir)
        r = RHO_Z * rng_scene.random() ** (1.0 / LATENT_D)
        z_try = r * d_dir
        s, _ = rate_at_z_munich(z_try, bs, h_scene, r_phone, body_paths,
                                 body_centroid, face_az)
        sinrs.append(s)
        if s > best_sinr_seen:
            best_sinr_seen = s
            best_z = z_try.copy()
    sinrs = np.array(sinrs)

    body_base = make_body_smplx(decode_z(z0), body_centroid,
                                  face_azimuth_rad=face_az)
    body_best = make_body_smplx(decode_z(best_z), body_centroid,
                                  face_azimuth_rad=face_az)

    fig, axes = plt.subplots(1, 3, figsize=fig_size_ieee(cols=2, ar=0.32))

    render_body_bs_view(axes[0], body_base, bs.center, view="bs")
    axes[0].set_title(f"(a) baseline pose, SINR = {sinr_baseline[best_scene]:.1f}$~$dB",
                      fontsize=8)
    axes[0].grid(False); axes[0].set_xticks([]); axes[0].set_yticks([])

    render_body_bs_view(axes[1], body_best, bs.center, view="bs")
    axes[1].set_title(f"(b) best-found pose, SINR = {best_sinr_seen:.1f}$~$dB",
                      fontsize=8)
    axes[1].grid(False); axes[1].set_xticks([]); axes[1].set_yticks([])

    ax = axes[2]
    ax.plot(np.arange(len(sinrs)), sinrs, "o-", color="C0",
            markersize=4, linewidth=0.8, alpha=0.6, label="random latent samples")
    ax.axhline(sinr_baseline[best_scene], color="red", linestyle="--",
               linewidth=0.7, label="baseline ($\\boldsymbol{z}_0$)")
    ax.axhline(best_sinr_seen, color="green", linestyle="--", linewidth=0.7,
               label=f"best of N={n_samples}")
    ax.set_xlabel("latent sample $i$")
    ax.set_ylabel("cascaded SINR [dB]")
    ax.set_title(f"(c) Munich {flag}, scene {best_scene} ({label})", fontsize=8)
    ax.legend(loc="lower right", fontsize=7)
    ax.grid(True, alpha=0.3)
    ax.text(0.03, 0.97, f"$\\Delta = {best_gain:.1f}$$~$dB",
            transform=ax.transAxes, ha="left", va="top",
            fontsize=8, bbox={"facecolor": "white", "alpha": 0.85, "edgecolor": "none"})

    fig.tight_layout()
    for ext in ("pdf", "png"):
        p = OUT_DIR / f"fig_hero_munich.{ext}"
        fig.savefig(p, dpi=200, bbox_inches="tight")
        print(f"  wrote {p}")
    plt.close(fig)


if __name__ == "__main__":
    main()
