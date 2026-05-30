"""Geometry / setup visualization.

Top-down + side view of the BS, body, phone, with the LOS ray and body's
visible-from-phone triangle subset highlighted.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "theory" / "scripts"))

from _plot_style import apply_monograph_style, fig_size_textwidth
from JSAC2.code.kirchhoff import Body, kirchhoff_h_body
from JSAC2.code.scene_nlos import BSArray, los_path_dict
from JSAC2.code.pose_sweep import make_body


OUT_DIR = Path("/home/user/aegis/JSAC2/code/outputs")


def main():
    body_centroid = np.array([30.0, 0.0, 1.2])
    phone_offset = np.array([0.55, 0.0, 0.10])
    r_phone = body_centroid + phone_offset

    body = make_body(0.0, body_centroid)
    bs = BSArray(n_x=8, n_y=8, center=np.array([0.0, 0.0, 8.0]),
                 normal=np.array([1.0, 0.0, 0.0]), f_c=28e9)

    paths = los_path_dict(bs, body.mesh.centroid)
    h_body, extras = kirchhoff_h_body(body, paths, r_phone, f_c=bs.f_c, M=bs.M,
                                       return_per_triangle=True)
    Lambda = extras["Lambda"]
    tri_idx = extras["tri_vis_idx"]

    # Per-triangle |contribution| summed across BS elements: this is roughly
    # how much each visible triangle contributes to ||h_body||^2.
    per_tri_pow = np.sum(np.abs(Lambda) ** 2, axis=0)  # (T_vis,)

    apply_monograph_style(mode="png")
    fig, axes = plt.subplots(1, 3, figsize=fig_size_textwidth(aspect=0.32, scale=1.0))

    # Top-down (x, y)
    ax = axes[0]
    ax.scatter(0, 0, s=80, c="C3", marker="^", label="BS array (rooftop)")
    ax.scatter(*body.mesh.centroid[:2], s=60, c="C0", marker="o", label="body centroid")
    ax.scatter(*r_phone[:2], s=40, c="C2", marker="*", label="phone")
    body_2d = body.centroids[:, :2]
    ax.scatter(body_2d[::100, 0], body_2d[::100, 1], s=2, c="0.7", alpha=0.5,
               label="body triangles (every 100th)")
    ax.set_xlabel("x [m]")
    ax.set_ylabel("y [m]")
    ax.set_title("(a) top-down")
    ax.legend(loc="lower left", fontsize=6.5)
    ax.set_aspect("equal")

    # Side view (x, z)
    ax = axes[1]
    ax.scatter(0, 8, s=80, c="C3", marker="^", label="BS array")
    ax.scatter(body.mesh.centroid[0], body.mesh.centroid[2], s=60, c="C0", marker="o")
    ax.scatter(r_phone[0], r_phone[2], s=40, c="C2", marker="*")
    body_2d = body.centroids[:, [0, 2]]
    ax.scatter(body_2d[::100, 0], body_2d[::100, 1], s=2, c="0.7", alpha=0.5)
    # LOS ray
    ax.plot([0, r_phone[0]], [8, r_phone[2]], "k:", lw=0.9, alpha=0.7,
            label="LOS direction")
    ax.set_xlabel("x [m]")
    ax.set_ylabel("z [m]")
    ax.set_title("(b) side view")
    ax.legend(loc="upper left", fontsize=6.5)

    # Per-triangle contribution heatmap (zoomed in to body)
    ax = axes[2]
    body_centroids_local = body.centroids[tri_idx] - body.mesh.centroid
    sc = ax.scatter(
        body_centroids_local[:, 1],  # y (lateral)
        body_centroids_local[:, 2],  # z (vertical)
        c=10 * np.log10(per_tri_pow / per_tri_pow.max() + 1e-30),
        s=4, cmap="viridis",
    )
    ax.scatter(*((r_phone - body.mesh.centroid)[[1, 2]]),
               s=80, c="C3", marker="*", label="phone (rel. to body)")
    cbar = plt.colorbar(sc, ax=ax)
    cbar.set_label(r"$|\Lambda_t|^2$ [dB, rel. max]", fontsize=8)
    ax.set_xlabel("body-local y [m]")
    ax.set_ylabel("body-local z [m]")
    ax.set_title(f"(c) per-triangle Kirchhoff contrib.\n({len(tri_idx)} visible from phone)")
    ax.legend(loc="lower left", fontsize=6.5)
    ax.set_aspect("equal")

    fig.tight_layout()
    fig.savefig(OUT_DIR / "fig4_setup.png", dpi=180)
    fig.savefig(OUT_DIR / "fig4_setup.pdf")
    print(f"  saved fig4_setup.{{png,pdf}}")
    plt.close(fig)


if __name__ == "__main__":
    main()
