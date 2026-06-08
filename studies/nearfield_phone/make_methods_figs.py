"""Methods figures: placement geometry and an example surface APD map."""

from __future__ import annotations

import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from aegis.nearfield.phone import compute_sab
from aegis.nearfield.scenarios import make_source, standard_placements
from studies.nearfield_phone import config as C

sys.path.insert(0, str(C.REPO / "theory" / "scripts"))
from _plot_style import apply_monograph_style  # noqa: E402

# Single-column report: full text width (~6.5 in), wider than tall.
REPORT_W_IN = 6.5


def rsize(aspect: float) -> tuple[float, float]:
    return (REPORT_W_IN, REPORT_W_IN * float(aspect))


def fig_geometry():
    apply_monograph_style(mode="png")
    mesh = C.load_mesh("duke")
    c = np.asarray(mesh.centroids) * 1e3
    pl = standard_placements(mesh)
    fig, axes = plt.subplots(1, 2, figsize=rsize(0.5))
    for ax, (a, b) in zip(axes, [(1, 2), (0, 2)], strict=False):
        ax.scatter(c[:, a], c[:, b], s=0.15, color="0.78", rasterized=True)
        for name, p in pl.items():
            pos = p.position() * 1e3
            lm = p.landmark * 1e3
            ax.plot([pos[a], lm[a]], [pos[b], lm[b]], "-", lw=1, color="C3")
            ax.scatter(pos[a], pos[b], s=55, marker="*", zorder=5, label=name.replace("_", " "))
        ax.set_aspect("equal")
    axes[0].set_xlabel("y [mm] (face at -y)")
    axes[0].set_ylabel("z [mm]")
    axes[1].set_xlabel("x [mm]")
    axes[0].legend(frameon=False, fontsize=8, loc="lower left")
    axes[0].set_title("Hand-held placements on the Duke phantom")
    fig.tight_layout()
    _save(fig, "fig_geometry")


def fig_apd_map():
    apply_monograph_style(mode="png")
    mesh = C.load_mesh("duke")
    patterns = C.load_patterns()
    band = C.band_tissues(patterns)[2450]
    c = np.asarray(mesh.centroids) * 1e3
    pl = standard_placements(mesh)["front_of_eyes"]
    src = make_source(pl, band.pattern, radiated_power_w=1.0)
    sab = np.asarray(compute_sab(mesh.centroids, mesh.normals, src, band.t0, band.n_tilde))

    # Zoom on the head/upper torso, only lit triangles, ordered so hot on top.
    lit = sab > 0
    order = np.argsort(sab[lit])
    cc = c[lit][order]
    ss = sab[lit][order]
    zhi = c[:, 2].max() + 20
    zlo = c[:, 2].max() - 450
    fig, axes = plt.subplots(1, 2, figsize=rsize(0.62))
    scat = None
    for ax, (h, hlabel) in zip(axes, [(0, "x [mm]"), (1, "y [mm] (face at -y)")], strict=False):
        scat = ax.scatter(cc[:, h], cc[:, 2], c=ss, s=2.5, cmap="inferno", rasterized=True)
        ax.set_aspect("equal")
        ax.set_ylim(zlo, zhi)
        ax.set_xlabel(hlabel)
    axes[0].set_ylabel("z [mm]")
    axes[0].set_title("front view")
    axes[1].set_title("side view")
    fig.suptitle("Surface absorbed power, front of eyes (2450 MHz, 1 W radiated)", y=1.0)
    cb = fig.colorbar(scat, ax=axes, shrink=0.8)
    cb.set_label(r"$S_{ab}$  [W/m$^2$ per W]")
    _save(fig, "fig_apd_map")


def _save(fig, name):
    fig.savefig(C.FIG_DIR / f"{name}.pdf", dpi=300)
    fig.savefig(C.FIG_DIR / f"{name}.png", dpi=200)
    plt.close(fig)
    print(f"wrote {C.FIG_DIR / name}.pdf")


if __name__ == "__main__":
    fig_geometry()
    fig_apd_map()
