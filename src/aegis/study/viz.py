"""Top-down visualization of a study run: city fabric, deployment, and walks.

Reads the ``scene.json`` a run writes (sites + per-agent walks + exposure) and,
if present, the city building mesh, and renders a top-down map: building
footprints, base-station sites with their sector coverage wedges, and pedestrian
walks coloured by per-person absorbed power. This is the study's spatial sanity
check and the figure behind "see it visually".
"""

from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

import numpy as np


def _building_polys(city_dir: Path):
    """Building footprint triangles (XY) from the cached concrete mesh, or None."""
    plys = glob.glob(str(city_dir / "scene_concrete.ply")) or glob.glob(str(city_dir / "scene_radio_itu_concrete.ply"))
    if not plys:
        return None
    try:
        import trimesh

        m = trimesh.load(plys[0], process=False)
        v = np.asarray(m.vertices)
        f = np.asarray(m.faces)
        return v[f][:, :, :2]
    except Exception:
        return None


def plot_scene(run_dir, out_path=None, title=None):
    """Render the top-down scene map for a study run directory."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection, PolyCollection
    from matplotlib.patches import Wedge

    run_dir = Path(run_dir)
    scene = json.loads((run_dir / "scene.json").read_text(encoding="utf-8"))
    out_path = Path(out_path) if out_path else run_dir / "scene_map.png"

    fig, ax = plt.subplots(figsize=(7.5, 7.0))

    polys = _building_polys(run_dir / "city")
    if polys is not None:
        ax.add_collection(PolyCollection(polys, facecolors="0.82", edgecolors="none", zorder=1))

    # base-station sites + sector coverage wedges
    for s in scene.get("sites", []):
        px, py = s["position"][0], s["position"][1]
        for sec in s.get("sectors", []):
            half = sec["az_coverage_deg"] / 2.0
            ax.add_patch(
                Wedge(
                    (px, py),
                    sec["max_range_m"],
                    sec["boresight_az_deg"] - half,
                    sec["boresight_az_deg"] + half,
                    facecolor="orange",
                    alpha=0.06,
                    edgecolor="orange",
                    lw=0.4,
                    zorder=2,
                )
            )
        ax.scatter([px], [py], marker="^", c="red", s=80, zorder=6, edgecolors="black", linewidths=0.5)

    # walks coloured by per-person exposure (log10 W)
    segs, vals, users = [], [], []
    for a in scene.get("agents", []):
        pos = np.asarray(a["positions"], dtype=float)
        if pos.shape[0] < 2:
            continue
        segs.append(pos)
        e = a.get("exposure_w") or 1e-13
        vals.append(np.log10(max(e, 1e-13)))
        users.append(a.get("is_user", False))
    if segs:
        lc = LineCollection(segs, cmap="viridis", zorder=4, linewidths=2.6)
        lc.set_array(np.array(vals))
        ax.add_collection(lc)
        cb = fig.colorbar(lc, ax=ax, fraction=0.046, pad=0.02)
        cb.set_label(r"$\log_{10}$ per-person absorbed power [W]")
        for pos, isu in zip(segs, users, strict=False):
            ax.scatter(
                [pos[0, 0]],
                [pos[0, 1]],
                marker="o" if isu else "s",
                c="white",
                s=24,
                zorder=5,
                edgecolors="black",
                linewidths=0.6,
            )

    ax.set_aspect("equal")
    ax.autoscale_view()
    ax.set_xlabel("x [m] (east)")
    ax.set_ylabel("y [m] (north)")
    ax.set_title(title or f"{run_dir.name}: city + deployment + walks", fontsize=11)
    fig.tight_layout()
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return out_path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Top-down study scene map")
    ap.add_argument("run_dir")
    ap.add_argument("--out", default=None)
    ap.add_argument("--title", default=None)
    args = ap.parse_args(argv)
    out = plot_scene(args.run_dir, args.out, args.title)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
