"""Top-down render of the manually-picked Munich RX layout.
Used as Figure 4 in the JSAC2 paper.
"""
from __future__ import annotations
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

OUT = Path("/home/user/aegis/JSAC2/code/outputs/munich")
PAPER_FIG = Path("/home/user/aegis/JSAC2/paper/figures/rx_grid_annotated.png")

BS_TGT_XY = np.array([33.0, 91.0])     # panel boresight (xy projection)


def main():
    rx = json.loads(Path("/home/user/aegis/JSAC2/code/scenes/munich_rx.json").read_text())
    bs = np.asarray(rx["bs_pos_xyz_m"])
    los  = np.array([(r["x"], r["y"]) for r in rx["rx"] if r["los_flag"] == "LOS"])
    nlos = np.array([(r["x"], r["y"]) for r in rx["rx"] if r["los_flag"] == "NLOS"])

    bg = OUT / "los_scan_bg.png"
    # Wider window since user picks span x in [-69, 136], y in [-27, 159].
    xlim = (-90, 150); ylim = (-50, 170)

    fig, ax = plt.subplots(figsize=(6.5, 6.5))
    if bg.exists():
        img = plt.imread(bg)
        ax.imshow(img, extent=[*xlim, *ylim], origin="upper", alpha=0.85)
    else:
        ax.set_facecolor("#cdc9c0")

    for k, (x, y) in enumerate(los):
        ax.plot(x, y, "o", color="lime", markersize=14, mec="black", mew=1.2,
                zorder=10)
        ax.annotate(f"L{k}", (x, y), xytext=(8, 8), textcoords="offset points",
                    fontsize=9, color="white",
                    bbox={"facecolor": "lime", "alpha": 0.95,
                          "edgecolor": "none", "pad": 1.5}, zorder=11)
    for k, (x, y) in enumerate(nlos):
        ax.plot(x, y, "o", color="red", markersize=14, mec="black", mew=1.2,
                zorder=10)
        ax.annotate(f"N{k}", (x, y), xytext=(8, 8), textcoords="offset points",
                    fontsize=9, color="white",
                    bbox={"facecolor": "red", "alpha": 0.95,
                          "edgecolor": "none", "pad": 1.5}, zorder=11)

    ax.plot(bs[0], bs[1], "x", color="yellow", markersize=22, mew=4, zorder=20)
    ax.annotate("BS", (bs[0], bs[1]), xytext=(7, 7), textcoords="offset points",
                fontsize=12, color="yellow", fontweight="bold", zorder=20)

    arrow = (BS_TGT_XY - bs[:2])
    arrow = arrow / np.linalg.norm(arrow) * 28.0
    ax.annotate("", xy=(bs[0]+arrow[0], bs[1]+arrow[1]),
                xytext=(bs[0], bs[1]),
                arrowprops={"arrowstyle": "->", "color": "yellow",
                             "lw": 3.0, "shrinkA": 0, "shrinkB": 0},
                zorder=20)
    ax.text(bs[0]+arrow[0]*1.05, bs[1]+arrow[1]*1.05, "panel\nbroadside",
            color="yellow", fontsize=10, fontweight="bold", zorder=20)

    ax.set_xlim(*xlim); ax.set_ylim(*ylim)
    ax.set_aspect("equal")
    ax.set_xlabel("world $x$ [m]")
    ax.set_ylabel("world $y$ [m]")
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    PAPER_FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(PAPER_FIG, dpi=160, bbox_inches="tight")
    print(f"wrote {PAPER_FIG}")


if __name__ == "__main__":
    main()
