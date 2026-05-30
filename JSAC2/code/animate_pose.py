"""Animate the in-silico body posing through a sequence, with the BS
illumination, the per-triangle absorbed-power heatmap, the per-triangle
Kirchhoff-to-phone power, and the resulting cascaded SINR/rate trajectory.

Layout: 2x2 panel
  (top-left)    body close-up colored by Sab (absorbed flux proxy)
  (top-right)   body close-up colored by per-triangle |Lambda_t|^2
  (bottom-left) full scene top-down: BS, body trajectory, phone
  (bottom-right) SINR + rate trajectory with current-pose marker

Saves as GIF.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from JSAC2.code.kirchhoff import Body, kirchhoff_h_body, mrt_sinr_db, rate_bps_shannon
from JSAC2.code.scene_nlos import BSArray, los_path_dict, los_h_at_phone
from JSAC2.code.scene_smplx import make_body_yaw_smplx as make_body


OUT_DIR = Path("/home/user/aegis/JSAC2/code/outputs")


def main(scene_loss_db: float = 80.0):
    body_centroid = np.array([30.0, 0.0, 1.2])
    phone_offset = np.array([0.55, 0.0, 0.10])
    r_phone = body_centroid + phone_offset

    bs = BSArray(n_x=8, n_y=8, center=np.array([0.0, 0.0, 8.0]),
                 normal=np.array([1.0, 0.0, 0.0]), f_c=28e9)
    h_los = los_h_at_phone(bs, r_phone, scene_loss_db=scene_loss_db)

    # Pose trajectory: a few sweeps. ~36 frames total.
    yaws = np.concatenate([
        np.linspace(0, 30, 9),
        np.linspace(30, -30, 18),
        np.linspace(-30, 0, 9),
    ])

    print(f"Pre-computing {len(yaws)} pose frames...")
    frames = []
    for i, yaw in enumerate(yaws):
        body = make_body(yaw, body_centroid)
        paths = los_path_dict(bs, body.mesh.centroid)
        h_body, extras = kirchhoff_h_body(body, paths, r_phone,
                                           f_c=bs.f_c, M=bs.M,
                                           return_per_triangle=True)
        Lambda = extras["Lambda"]
        tri_idx = extras["tri_vis_idx"]
        per_tri_pow = np.sum(np.abs(Lambda) ** 2, axis=0)

        bs_to_tri = body.centroids - bs.center
        bs_dist = np.linalg.norm(bs_to_tri, axis=1)
        bs_dir = bs_to_tri / np.maximum(bs_dist[:, None], 1e-9)
        mu_bs = -np.einsum("ij,ij->i", bs_dir, body.normals)
        sab_proxy = np.maximum(mu_bs, 0.0)

        sinr_cas = mrt_sinr_db(h_los + h_body, p_tx_dbm=43, noise_dbm=-94)
        rate_cas = rate_bps_shannon(sinr_cas) / 1e6
        frames.append(dict(
            yaw=yaw, body=body, tri_idx=tri_idx, per_tri_pow=per_tri_pow,
            sab_proxy=sab_proxy, sinr_cas=sinr_cas, rate_cas=rate_cas,
        ))
    print("  Pre-compute done.")

    yaws_arr = np.array([fr["yaw"] for fr in frames])
    sinr_arr = np.array([fr["sinr_cas"] for fr in frames])
    rate_arr = np.array([fr["rate_cas"] for fr in frames])

    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    ax_sab = axes[0, 0]
    ax_kir = axes[0, 1]
    ax_scene = axes[1, 0]
    ax_metric = axes[1, 1]

    art = {}

    body0 = frames[0]["body"]
    cents0 = body0.centroids
    sab0 = frames[0]["sab_proxy"]
    tri_idx0 = frames[0]["tri_idx"]

    # -- Top-left: body Sab heatmap (front view: y vs z) --
    front = np.einsum("j,ij->i", np.array([1.0, 0.0, 0.0]), body0.normals) > -0.5
    cents_local0 = cents0 - body0.mesh.centroid
    art["sab"] = ax_sab.scatter(
        cents_local0[front, 1], cents_local0[front, 2],
        c=sab0[front], cmap="hot", s=8, vmin=0, vmax=1,
    )
    ax_sab.set_xlabel("body-local y [m]")
    ax_sab.set_ylabel("body-local z [m]")
    ax_sab.set_title("Per-triangle absorption proxy: $\\mu^+$ (BS-side)")
    ax_sab.set_aspect("equal")
    ax_sab.set_xlim(-0.4, 0.4)
    ax_sab.set_ylim(-0.5, 0.7)
    cbar1 = fig.colorbar(art["sab"], ax=ax_sab, fraction=0.04)
    cbar1.set_label("$\\max(0, -\\hat k \\cdot \\hat n)$")

    # Phone marker
    rp_local = r_phone - body0.mesh.centroid
    ax_sab.scatter([rp_local[1]], [rp_local[2]], s=120, c="cyan",
                   marker="*", edgecolors="k", linewidths=0.6, label="phone")
    ax_sab.legend(loc="upper left", fontsize=8)

    # -- Top-right: per-triangle Kirchhoff to phone --
    per_tri_pow0 = frames[0]["per_tri_pow"]
    cents_vis_local0 = cents0[tri_idx0] - body0.mesh.centroid
    powers_db0 = 10 * np.log10(per_tri_pow0 / max(per_tri_pow0.max(), 1e-30) + 1e-30)
    art["kir"] = ax_kir.scatter(
        cents_vis_local0[:, 1], cents_vis_local0[:, 2],
        c=powers_db0, cmap="viridis", s=8, vmin=-30, vmax=0,
    )
    ax_kir.set_xlabel("body-local y [m]")
    ax_kir.set_ylabel("body-local z [m]")
    ax_kir.set_title("Per-triangle Kirchhoff power to phone")
    ax_kir.set_aspect("equal")
    ax_kir.set_xlim(-0.4, 0.4)
    ax_kir.set_ylim(-0.5, 0.7)
    cbar2 = fig.colorbar(art["kir"], ax=ax_kir, fraction=0.04)
    cbar2.set_label("$|\\Lambda_t|^2$ [dB rel.\\ max]")
    ax_kir.scatter([rp_local[1]], [rp_local[2]], s=120, c="red",
                   marker="*", edgecolors="k", linewidths=0.6, label="phone")
    ax_kir.legend(loc="upper left", fontsize=8)

    # -- Bottom-left: bird's-eye scene (top-down x,y) --
    ax_scene.scatter([0], [0], s=200, c="red", marker="^", label="BS @ (0,0,8m)")
    body_xy = body0.centroids[:, :2]
    art["scene_body"] = ax_scene.scatter(body_xy[::40, 0], body_xy[::40, 1],
                                          s=4, c="C0", alpha=0.7,
                                          label="body @ (30m,0,1.2m)")
    ax_scene.scatter([r_phone[0]], [r_phone[1]], s=120, c="orange",
                     marker="*", edgecolors="k", linewidths=0.6,
                     label="phone (chest+0.55m)")
    ax_scene.plot([0, body_centroid[0]], [0, body_centroid[1]],
                  "k--", linewidth=0.7, alpha=0.4, label="BS--body LOS")
    ax_scene.set_xlim(-2, 33)
    ax_scene.set_ylim(-3, 3)
    ax_scene.set_xlabel("x [m]")
    ax_scene.set_ylabel("y [m]")
    ax_scene.set_title("Top-down scene")
    ax_scene.legend(loc="lower left", fontsize=7)
    ax_scene.set_aspect("equal")

    # -- Bottom-right: SINR + rate trajectory --
    ax_metric.plot(yaws_arr, sinr_arr, "C0-", alpha=0.4, label="cascaded SINR")
    ax_metric.set_xlabel("torso yaw $\\theta$ [°]")
    ax_metric.set_ylabel("SINR [dB]", color="C0")
    ax_metric.tick_params(axis="y", labelcolor="C0")
    ax_metric.set_xlim(yaws_arr.min() - 5, yaws_arr.max() + 5)
    ax_metric.set_ylim(min(sinr_arr) - 2, max(sinr_arr) + 2)
    ax_metric2 = ax_metric.twinx()
    ax_metric2.plot(yaws_arr, rate_arr, "C3-", alpha=0.4, label="rate (capped)")
    ax_metric2.set_ylabel("Rate [Mbps]", color="C3")
    ax_metric2.tick_params(axis="y", labelcolor="C3")
    art["dot_sinr"] = ax_metric.plot([yaws_arr[0]], [sinr_arr[0]],
                                       "C0o", markersize=10)[0]
    art["dot_rate"] = ax_metric2.plot([yaws_arr[0]], [rate_arr[0]],
                                        "C3o", markersize=10)[0]
    art["title"] = fig.suptitle(
        f"Pose: yaw={yaws_arr[0]:+.1f}°  |  Cascaded SINR={sinr_arr[0]:.1f} dB  "
        f"|  Rate={rate_arr[0]:.0f} Mbps  |  scene_loss=80 dB (NLOS)",
        fontsize=12,
    )

    fig.tight_layout(rect=[0, 0, 1, 0.96])

    def update(frame_i):
        fr = frames[frame_i]
        body = fr["body"]
        sab = fr["sab_proxy"]
        cents = body.centroids
        cents_local = cents - body.mesh.centroid
        # Filter to "front" triangles (similar to init)
        front = np.einsum("j,ij->i", np.array([1.0, 0.0, 0.0]), body.normals) > -0.5
        art["sab"].set_offsets(cents_local[front, 1:3])
        art["sab"].set_array(sab[front])

        tri_idx = fr["tri_idx"]
        per_tri_pow = fr["per_tri_pow"]
        cents_vis_local = cents[tri_idx] - body.mesh.centroid
        if len(per_tri_pow) > 0:
            powers_db = 10 * np.log10(per_tri_pow / max(per_tri_pow.max(), 1e-30) + 1e-30)
        else:
            powers_db = np.zeros(len(tri_idx))
        art["kir"].set_offsets(cents_vis_local[:, [1, 2]])
        art["kir"].set_array(powers_db)

        body_xy = body.centroids[:, :2]
        art["scene_body"].set_offsets(body_xy[::40])

        art["dot_sinr"].set_data([fr["yaw"]], [fr["sinr_cas"]])
        art["dot_rate"].set_data([fr["yaw"]], [fr["rate_cas"]])
        art["title"].set_text(
            f"Pose: yaw={fr['yaw']:+.1f}°  |  Cascaded SINR={fr['sinr_cas']:.1f} dB  "
            f"|  Rate={fr['rate_cas']:.0f} Mbps  |  scene_loss=80 dB (NLOS)"
        )
        return list(art.values())

    ani = FuncAnimation(fig, update, frames=range(len(frames)),
                         interval=120, blit=False)

    out_gif = OUT_DIR / "anim_pose_sweep_smplx.gif"
    print(f"Writing {out_gif}...")
    ani.save(out_gif, writer=PillowWriter(fps=8), dpi=80)
    print(f"  saved {out_gif}")
    plt.close(fig)


if __name__ == "__main__":
    main(scene_loss_db=80.0)
