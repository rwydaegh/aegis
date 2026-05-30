"""Hero figure for §VIII: VPoser-latent before-vs-after pose comparison.

Loads latent_existence.npz, picks the scene with the largest SINR gain
(best - baseline), regenerates the baseline and best body poses with
the same scene geometry, and renders a 3-panel hero:

  (a) baseline pose (VPoser-encoded AMASS frame), per-triangle |Lambda|^2 colour
  (b) best-found pose, same colourmap
  (c) SINR vs. existence-sample index, with baseline and best marked
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.collections import PolyCollection
import torch

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

from JSAC2.code.kirchhoff import kirchhoff_h_body, mrt_sinr_db
from JSAC2.code.scene_nlos import BSArray, los_h_at_phone, los_path_dict
from JSAC2.code.scene_smplx import make_body_smplx
from JSAC2.code.vposer_v2 import VPoser
from JSAC2.code.latent_sweep import (
    BS_REGIMES, BODY_WORLD_CENTROID, PHONE_OFFSET,
    P_TX_DBM, NOISE_DBM, RHO_Z, make_scene, decode_z, encode_pose,
)
from aegis.geometry.pose_stream import PoseStream

NPZ = Path("/home/user/aegis/JSAC2/code/outputs/latent_existence.npz")
OUT_DIR = Path("/home/user/aegis/JSAC2/code/outputs")


def render_body_with_lambda(ax, body, sab_per_triangle, view="bs"):
    """Project the body mesh and colour each triangle by |Lambda|^2 magnitude.

    view='bs': project to (y, z) — what the BS sees.
    view='top': project to (x, y) — top-down.
    """
    verts = np.asarray(body.mesh.vertices)
    faces = np.asarray(body.mesh.faces)
    centroid = body.mesh.centroid
    verts_local = verts - centroid

    if view == "bs":
        xi, yi = 1, 2  # y, z
    elif view == "top":
        xi, yi = 0, 1
    else:
        raise ValueError(view)

    # Compute per-triangle 2D vertices.
    polys = verts_local[faces][:, :, [xi, yi]]
    # Sort by depth (along the orthogonal axis) for a stable z-order.
    depth_axis = {"bs": 0, "top": 2}[view]
    centroid_depth = verts_local[faces].mean(axis=1)[:, depth_axis]
    order = np.argsort(centroid_depth)
    polys = polys[order]
    sab = sab_per_triangle[order]

    # Colour each triangle by its incidence cosine to the BS direction
    # (proxy for "how well-illuminated", more visually informative than |Λ|²
    # which is dominated by phase coherence at 28 GHz).
    # We compute n_hat·(-k_hat) where k_hat points BS->triangle.
    bs_pos_local = np.array([0.0, 0.0, 8.0]) - body.mesh.centroid  # rough BS direction
    tri_centers = verts_local[faces].mean(axis=1)
    to_bs = bs_pos_local - tri_centers
    to_bs /= np.linalg.norm(to_bs, axis=1, keepdims=True)
    normals = body.mesh.face_normals - 0  # numpy
    # Reorder by depth_axis ordering used above
    illum = np.einsum("ij,ij->i", normals, to_bs)[order]
    illum = np.clip(illum, 0, 1)  # back-face cull
    cmap = plt.colormaps["inferno"]
    cmap_in = 0.2 + 0.7 * illum  # avoid pure black
    colors = cmap(cmap_in)

    pc = PolyCollection(polys, facecolors=colors, edgecolors="none", linewidths=0.0)
    ax.add_collection(pc)
    ax.set_xlim(verts_local[:, xi].min() - 0.05, verts_local[:, xi].max() + 0.05)
    ax.set_ylim(verts_local[:, yi].min() - 0.05, verts_local[:, yi].max() + 0.05)
    ax.set_aspect("equal")
    return pc


def main():
    d = np.load(NPZ, allow_pickle=False)
    regime_idx = d["regime_idx"]
    sinr_baseline = d["sinr_baseline"]
    sinr_existence_max = d["sinr_existence_max"]
    sinr_samples = d["sinr_samples"]
    scene_loss = d["scene_loss"]

    gains = sinr_existence_max - sinr_baseline
    # Pick the scene with the largest gain.
    best_scene = int(np.argmax(gains))
    best_gain = gains[best_scene]
    best_regime = int(regime_idx[best_scene])
    print(f"  hero scene: idx={best_scene}, regime={BS_REGIMES[best_regime][1]}, "
          f"gain={best_gain:.2f} dB, baseline={sinr_baseline[best_scene]:.1f} dB, "
          f"best={sinr_existence_max[best_scene]:.1f} dB")

    # Reconstruct the scene.  We need to re-find the baseline_pose used.
    # latent_sweep used a specific seed-driven random selection -- easiest
    # is to rerun the random draw from the same seed.
    SEED = int(d["seed"])
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

    # Replay the same draws used in latent_sweep.main() for scene best_scene
    n_regimes = len(BS_REGIMES)
    for s in range(best_scene + 1):
        regime_idx_s = s % n_regimes
        bs_pos = BS_REGIMES[regime_idx_s][0]
        scene_loss_db = float(rng.choice([35.0, 55.0, 80.0]))
        baseline_pose = pose_pool[rng.integers(0, len(pose_pool))]
        if s == best_scene:
            assert regime_idx_s == best_regime
            print(f"  replayed: regime={regime_idx_s}, scene_loss={scene_loss_db:.0f}")
            break

    body_centroid = BODY_WORLD_CENTROID.copy()
    bs, h_los, r_phone = make_scene(bs_pos, scene_loss_db, body_centroid)
    z0 = encode_pose(baseline_pose)

    # Find the best z by re-running the existence sampling with same seed
    scene_seed = SEED + best_scene
    rng_scene = np.random.default_rng(scene_seed)
    LATENT_D = 32
    n_samples = 24
    best_z = z0.copy()
    best_sinr_seen = -np.inf
    sinrs = []
    for i in range(n_samples):
        d_dir = rng_scene.standard_normal(LATENT_D)
        d_dir /= np.linalg.norm(d_dir)
        r = RHO_Z * rng_scene.random() ** (1.0 / LATENT_D)
        z_try = z0 + r * d_dir
        # decode + render
        body_try = make_body_smplx(decode_z(z_try), body_centroid)
        paths_try = los_path_dict(bs, body_try.mesh.centroid)
        h_body_try, _ = kirchhoff_h_body(body_try, paths_try, r_phone, M=bs.M)
        h_cas = h_los + h_body_try
        s = mrt_sinr_db(h_cas, p_tx_dbm=P_TX_DBM, noise_dbm=NOISE_DBM)
        sinrs.append(s)
        if s > best_sinr_seen:
            best_sinr_seen = s
            best_z = z_try.copy()
    sinrs = np.array(sinrs)

    # Render baseline body
    body_base = make_body_smplx(decode_z(z0), body_centroid)
    paths_base = los_path_dict(bs, body_base.mesh.centroid)
    h_body_base, extras_base = kirchhoff_h_body(
        body_base, paths_base, r_phone, M=bs.M, return_per_triangle=True
    )
    Lambda_base = extras_base.get("Lambda")
    sab_base = (np.abs(Lambda_base) ** 2).sum(axis=0) if Lambda_base is not None else np.ones(len(body_base.mesh.faces))
    # Embed sab_base into full mesh (nan-zero)
    full_sab_base = np.zeros(len(body_base.mesh.faces))
    full_sab_base[extras_base["tri_vis_idx"]] = sab_base

    # Render best body
    body_best = make_body_smplx(decode_z(best_z), body_centroid)
    paths_best = los_path_dict(bs, body_best.mesh.centroid)
    h_body_best, extras_best = kirchhoff_h_body(
        body_best, paths_best, r_phone, M=bs.M, return_per_triangle=True
    )
    Lambda_best = extras_best.get("Lambda")
    sab_best = (np.abs(Lambda_best) ** 2).sum(axis=0) if Lambda_best is not None else np.ones(len(body_best.mesh.faces))
    full_sab_best = np.zeros(len(body_best.mesh.faces))
    full_sab_best[extras_best["tri_vis_idx"]] = sab_best

    # ---- Plot ----
    fig, axes = plt.subplots(1, 3, figsize=fig_size_ieee(cols=2, ar=0.32))

    pc_a = render_body_with_lambda(axes[0], body_base, full_sab_base, view="bs")
    axes[0].set_title(f"(a) baseline pose, SINR = {sinr_baseline[best_scene]:.1f}$~$dB",
                      fontsize=8)
    axes[0].set_xlabel("y [m]"); axes[0].set_ylabel("z [m]")
    axes[0].grid(False); axes[0].set_xticks([]); axes[0].set_yticks([])

    pc_b = render_body_with_lambda(axes[1], body_best, full_sab_best, view="bs")
    axes[1].set_title(f"(b) best-found pose, SINR = {best_sinr_seen:.1f}$~$dB",
                      fontsize=8)
    axes[1].set_xlabel("y [m]"); axes[1].set_ylabel("z [m]")
    axes[1].grid(False); axes[1].set_xticks([]); axes[1].set_yticks([])

    # Panel (c): SINR vs sample index
    ax = axes[2]
    ax.plot(np.arange(len(sinrs)), sinrs, "o-", color="C0",
            markersize=4, linewidth=0.8, alpha=0.6, label="random latent samples")
    ax.axhline(sinr_baseline[best_scene], color="red", linestyle="--",
               linewidth=0.7, label="baseline ($\\boldsymbol{z}_0$)")
    ax.axhline(best_sinr_seen, color="green", linestyle="--", linewidth=0.7,
               label="best of N=24")
    ax.set_xlabel("latent sample $i$")
    ax.set_ylabel("cascaded SINR [dB]")
    ax.set_title(f"(c) SINR over latent ball ($\\rho_z={RHO_Z}$)", fontsize=8)
    ax.legend(loc="lower right", fontsize=7)
    ax.grid(True, alpha=0.3)
    ax.text(0.03, 0.97, f"$\\Delta = {best_gain:.1f}$$~$dB",
            transform=ax.transAxes, ha="left", va="top",
            fontsize=8, bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "none"})

    fig.tight_layout()
    for ext in ("pdf", "png"):
        p = OUT_DIR / f"fig_hero_latent.{ext}"
        fig.savefig(p, dpi=200, bbox_inches="tight")
        print(f"  wrote {p}")
    plt.close(fig)


if __name__ == "__main__":
    main()
