"""Top-down render of the OSM scene + entry-node overlay.

Loads `data/scenes/brussels_grand_place/mesh.npz`, projects every triangle
to the xy plane, fills walls grey, and overlays the configured
`ENTRY_NODES_M` as red circles. Saves an annotated PNG so we can verify
that each declared entry node actually sits in a street opening between
buildings.

Usage:
    python -m JSAC.code.experiments.plaza_run.figures.plaza_top \
        --out JSAC/code/experiments/plaza_run/figures/plaza_top.png

The figure is the iteration target: render -> read PNG -> nudge
`scenario.ENTRY_NODES_M` -> re-render until every visible street opening
in the building polygon has a node parked roughly at its mouth.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import PolyCollection

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scenario import BS_X_M, BS_Y_M, ENTRY_NODES_M  # noqa: E402

MESH_PATH = Path("data/scenes/brussels_grand_place/mesh.npz")


def render(
    out_path: Path,
    *,
    half_extent: float = 60.0,
    show_grid: bool = True,
) -> Path:
    m = np.load(MESH_PATH)
    verts = m["vertices"]
    tris = m["triangles"]

    # Keep only triangles with at least one non-ground vertex (z > 0.5),
    # so the wall polygons cast a clean top-down silhouette and the ground
    # plane doesn't paint over everything.
    tri_z = verts[tris][:, :, 2]
    wall_mask = tri_z.max(axis=1) > 0.5

    # XY polygons for each wall triangle.
    polys = verts[tris[wall_mask]][:, :, :2]
    pc = PolyCollection(polys, facecolors="#9aa0aa", edgecolors="none", alpha=0.85, zorder=2)

    fig, ax = plt.subplots(figsize=(14, 14), dpi=140)
    ax.set_aspect("equal")
    ax.set_facecolor("#f0eee8")  # plaza ground tone
    ax.add_collection(pc)

    # Plaza extent ring (visual reference) and origin axes.
    ax.axhline(0.0, color="#888", lw=0.4, zorder=1)
    ax.axvline(0.0, color="#888", lw=0.4, zorder=1)

    # BS panel.
    ax.scatter(
        [BS_X_M],
        [BS_Y_M],
        marker="s",
        s=160,
        c="#cc4422",
        edgecolors="black",
        lw=1.0,
        zorder=4,
    )
    ax.annotate(
        "BS (south facade)",
        xy=(BS_X_M, BS_Y_M),
        xytext=(BS_X_M + 3, BS_Y_M + 3),
        fontsize=9,
        color="#882211",
    )

    # Entry nodes.
    for name, (x, y) in ENTRY_NODES_M.items():
        ax.scatter([x], [y], marker="o", s=120, c="#cc1144", edgecolors="black", lw=1.0, zorder=5)
        ax.annotate(name, xy=(x, y), xytext=(x + 1.5, y + 1.5), fontsize=8, color="#aa1133")

    ax.set_xlim(-half_extent, half_extent)
    ax.set_ylim(-half_extent, half_extent)
    if show_grid:
        ax.grid(color="#cccccc", lw=0.3, alpha=0.5)
    ax.set_xlabel("x [m] (east)")
    ax.set_ylabel("y [m] (north)")
    ax.set_title("Brussels Grand Place — OSM top view + ENTRY_NODES_M overlay")

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--out",
        type=Path,
        default=Path("JSAC/code/experiments/plaza_run/figures/plaza_top.png"),
    )
    p.add_argument("--half-extent", type=float, default=60.0)
    args = p.parse_args()
    out = render(args.out, half_extent=args.half_extent)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
