"""Hero figure: SMPL-X body at worst-yaw vs best-yaw, side-by-side.

Loads the pose_sweep_smplx outputs to find the yaws giving the worst and
best cascaded SINR, re-renders the body at those poses with the per-triangle
absorbed-flux proxy as a colormap, annotates the BS direction and phone,
and reports the SINR/rate at each pose.

IEEE single-column output by default; switch to two-column for the hero
slot via --columns 2.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib

matplotlib.use("Agg")

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "theory" / "scripts"))

from JSAC2.code.scene_smplx import make_body_yaw_smplx
from JSAC2.code.scene_nlos import BSArray, los_path_dict
from JSAC2.code.kirchhoff import kirchhoff_h_body

from _plot_style import apply_monograph_style, fig_size_ieee


OUT_DIR = Path(__file__).resolve().parent / "outputs"


def load_sweep(regime: str) -> dict:
    npz = OUT_DIR / f"pose_sweep_smplx_{regime}.npz"
    return dict(np.load(npz))


def render_body_panel(ax, body, color_per_triangle, r_phone, body_centroid,
                      bs_center, vmax, title=None, ylabel=True,
                      colormap="viridis"):
    """Render body as 2D scatter colored by per-triangle scalar."""
    cents = body.centroids
    cents_local = cents - body_centroid

    # Show all triangles (full silhouette), color those with non-zero
    # contribution; back-facing remain at 0.
    sc = ax.scatter(cents_local[:, 1], cents_local[:, 2],
                    c=color_per_triangle, cmap=colormap,
                    s=2.0, vmin=0, vmax=vmax, edgecolors="none")

    # Phone marker
    rp_local = r_phone - body_centroid
    ax.scatter([rp_local[1]], [rp_local[2]], s=110, c="#00d4ff",
               marker="*", edgecolors="black", linewidths=0.8, zorder=5,
               label="phone")

    ax.set_aspect("equal")
    ax.set_xlim(-0.5, 0.5)
    ax.set_ylim(-1.0, 1.0)
    ax.set_xlabel("body-local $y$ [m]")
    if ylabel:
        ax.set_ylabel("body-local $z$ [m]")
    else:
        ax.set_yticklabels([])
    if title is not None:
        ax.set_title(title, fontsize=8.5)
    ax.tick_params(axis="both", which="both", labelsize=7)
    return sc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--regime", default="S2",
                    choices=["S2", "S2bind", "S3"])
    ap.add_argument("--columns", type=int, default=2, choices=[1, 2])
    ap.add_argument("--mode", default="png", choices=["png", "pdf"])
    args = ap.parse_args()

    apply_monograph_style(mode=args.mode)

    sweep = load_sweep(args.regime)
    yaws = sweep["yaws_deg"]
    sinrs = sweep["sinr_cas_db"]
    rates = sweep["rate_cas_mbps"]

    yaw_best = float(yaws[np.argmax(sinrs)])
    yaw_worst = float(yaws[np.argmin(sinrs)])
    sinr_best = float(np.max(sinrs))
    sinr_worst = float(np.min(sinrs))
    rate_best = float(rates[np.argmax(sinrs)])
    rate_worst = float(rates[np.argmin(sinrs)])
    delta_db = sinr_best - sinr_worst

    print(f"[{args.regime}] worst yaw={yaw_worst:+.1f}d "
          f"SINR={sinr_worst:.1f}dB rate={rate_worst:.0f}Mbps")
    print(f"[{args.regime}] best  yaw={yaw_best:+.1f}d "
          f"SINR={sinr_best:.1f}dB rate={rate_best:.0f}Mbps")
    print(f"[{args.regime}] delta = {delta_db:.1f} dB")

    body_centroid = np.array([10.0, 0.0, 1.2])
    phone_offset = np.array([0.55, 0.0, 0.10])
    r_phone = body_centroid + phone_offset

    bs = BSArray(n_x=8, n_y=8, center=np.array([0.0, 0.0, 5.0]),
                 normal=np.array([1.0, 0.0, 0.0]), f_c=28e9)

    body_w = make_body_yaw_smplx(yaw_worst, body_centroid)
    body_b = make_body_yaw_smplx(yaw_best, body_centroid)

    paths_w = los_path_dict(bs, body_w.mesh.centroid)
    paths_b = los_path_dict(bs, body_b.mesh.centroid)

    _, extras_w = kirchhoff_h_body(body_w, paths_w, r_phone,
                                    f_c=bs.f_c, M=bs.M,
                                    return_per_triangle=True)
    _, extras_b = kirchhoff_h_body(body_b, paths_b, r_phone,
                                    f_c=bs.f_c, M=bs.M,
                                    return_per_triangle=True)

    # Per-triangle Kirchhoff power to the phone (sum over BS elements)
    Lambda_w = extras_w["Lambda"]  # (M, T_vis)
    Lambda_b = extras_b["Lambda"]
    tri_idx_w = extras_w["tri_vis_idx"]
    tri_idx_b = extras_b["tri_vis_idx"]

    pow_w = np.zeros(len(body_w.centroids))
    pow_b = np.zeros(len(body_b.centroids))
    pow_w[tri_idx_w] = np.sum(np.abs(Lambda_w) ** 2, axis=0)
    pow_b[tri_idx_b] = np.sum(np.abs(Lambda_b) ** 2, axis=0)

    # Normalise both panels to a common dB scale
    pow_w_db = 10 * np.log10(pow_w / max(pow_w.max(), pow_b.max()) + 1e-12)
    pow_b_db = 10 * np.log10(pow_b / max(pow_w.max(), pow_b.max()) + 1e-12)
    pow_w_db = np.clip(pow_w_db, -25, 0) + 25  # map to [0, 25] for vmax
    pow_b_db = np.clip(pow_b_db, -25, 0) + 25
    vmax = 25.0

    # Three-panel: body-worst, body-best, SINR trajectory
    fig_w, fig_h = fig_size_ieee(columns=args.columns, aspect=0.36)
    fig = plt.figure(figsize=(fig_w, fig_h), constrained_layout=True)
    gs = fig.add_gridspec(1, 3, width_ratios=[1, 1, 1.3])
    ax_a = fig.add_subplot(gs[0])
    ax_b = fig.add_subplot(gs[1])
    ax_c = fig.add_subplot(gs[2])

    sc_w = render_body_panel(ax_a, body_w, pow_w_db, r_phone, body_centroid,
                             bs.center, vmax=vmax, ylabel=True,
                             title=f"(a) $\\theta = {yaw_worst:+.0f}^\\circ$",
                             colormap="inferno")
    sc_b = render_body_panel(ax_b, body_b, pow_b_db, r_phone, body_centroid,
                             bs.center, vmax=vmax, ylabel=False,
                             title=f"(b) $\\theta = {yaw_best:+.0f}^\\circ$",
                             colormap="inferno")

    cb = fig.colorbar(sc_b, ax=[ax_a, ax_b], fraction=0.038, pad=0.02,
                      shrink=0.72, location="right")
    cb.set_label("$|\\Lambda_t|^2$ [dB]", fontsize=8)
    cb.ax.tick_params(labelsize=7)
    cb.set_ticks([0, 5, 10, 15, 20, 25])
    cb.set_ticklabels([r"$-25$", r"$-20$", r"$-15$",
                       r"$-10$", r"$-5$", r"$0$"])

    # Panel (c): SINR vs yaw trajectory
    ax_c.plot(yaws, sinrs, "o-", color="C0", linewidth=1.0, markersize=3,
              markerfacecolor="white", markeredgewidth=0.8)
    ax_c.axhline(y=sinr_worst, color="gray", linewidth=0.5, linestyle=":")
    ax_c.axhline(y=sinr_best, color="gray", linewidth=0.5, linestyle=":")
    # Mark worst and best
    ax_c.scatter([yaw_worst], [sinr_worst], s=70, color="C3",
                 marker="o", edgecolors="black", linewidths=0.8, zorder=5,
                 label="(a) worst")
    ax_c.scatter([yaw_best], [sinr_best], s=70, color="C2",
                 marker="o", edgecolors="black", linewidths=0.8, zorder=5,
                 label="(b) best")
    # Annotate the gap
    ax_c.annotate("", xy=(yaws.min() + 5, sinr_best),
                  xytext=(yaws.min() + 5, sinr_worst),
                  arrowprops=dict(arrowstyle="<->", color="black",
                                  linewidth=0.8))
    ax_c.text(yaws.min() + 7, (sinr_best + sinr_worst) / 2,
              f"$\\Delta = {delta_db:.1f}\\,$dB",
              fontsize=8, ha="left", va="center")
    ax_c.set_xlabel("torso yaw $\\theta$ [deg]")
    ax_c.set_ylabel("cascaded SINR [dB]")
    regime_label = {"S2": "LOS-attenuated (35 dB)",
                    "S2bind": "binding (55 dB)",
                    "S3": "NLOS (80 dB)"}[args.regime]
    ax_c.set_title(f"(c) {regime_label}", fontsize=8.5)
    ax_c.legend(loc="lower right", fontsize=7, frameon=True,
                framealpha=1.0, edgecolor="black", fancybox=False)
    ax_c.tick_params(axis="both", which="both", labelsize=7)
    ax_c.grid(True, alpha=0.25, linewidth=0.4)

    out_pdf = OUT_DIR / f"fig_hero_pose_{args.regime}.pdf"
    out_png = OUT_DIR / f"fig_hero_pose_{args.regime}.png"
    fig.savefig(out_pdf, dpi=300, bbox_inches="tight")
    fig.savefig(out_png, dpi=200, bbox_inches="tight")
    print(f"saved {out_pdf} and {out_png}")
    plt.close(fig)


if __name__ == "__main__":
    main()
