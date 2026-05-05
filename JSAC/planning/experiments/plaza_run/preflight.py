"""Visual preflight: load the assembled scene + 50 initial body positions.

Writes a screenshot + a body-position scatter to the experiment dir so brief 08
can eyeball that bodies stand on the plaza ground, the BS panel sits on a
facade, and the spawn distribution is reasonable before going headless.
"""

from __future__ import annotations

import argparse
import logging
import random
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from .scenario import (
    BS_BROADSIDE,
    BS_POSITION,
    PLAZA_HALF_WIDTH_M,
    RANGE_MAX_M,
    RANGE_MIN_M,
    TIER_COUNTS,
    assign_bodies,
    discover_walks,
)
from .scene_cache import load_or_scrape

logger = logging.getLogger(__name__)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", type=Path, default=Path("JSAC/planning/experiments/plaza_run/outputs/preflight.png"))
    p.add_argument("--no-osm", action="store_true", help="Skip Overpass scrape")
    p.add_argument("--log-level", default="INFO")
    args = p.parse_args()

    logging.basicConfig(level=args.log_level.upper())
    rng = random.Random(args.seed)
    walks = discover_walks()
    n_bodies = sum(TIER_COUNTS.values())
    bodies = assign_bodies(n_bodies, rng, walks)

    fig, axes = plt.subplots(1, 2, figsize=(12, 6))

    # Top-down plaza scatter
    ax = axes[0]
    if not args.no_osm:
        try:
            mesh, scene_hash = load_or_scrape()
            v = mesh.vertices
            # Draw a plaza-floor footprint by projecting wall vertices.
            ax.plot(v[:, 0], v[:, 1], ".", markersize=0.4, color="0.7", alpha=0.4, label="OSM mesh verts")
            ax.set_title(f"Plaza top-down (scene={scene_hash[:6]})")
        except Exception as exc:
            logger.warning("OSM preflight skipped: %s", exc)
            ax.set_title("Plaza top-down (no OSM)")
    else:
        ax.set_title("Plaza top-down (--no-osm)")

    colors = {"A": "C0", "B": "C1", "C": "C3"}
    for tier in ("A", "B", "C"):
        xy = np.array([b.spawn_xy for b in bodies if b.tier == tier])
        ax.scatter(xy[:, 0], xy[:, 1], c=colors[tier], label=f"tier {tier}", s=30, edgecolor="black", linewidth=0.4)
    ax.scatter([BS_POSITION[0]], [BS_POSITION[1]], marker="^", s=140, c="k", label="BS panel")

    # Show range annulus.
    theta = np.linspace(0, 2 * np.pi, 200)
    for r in (RANGE_MIN_M, RANGE_MAX_M):
        ax.plot(BS_POSITION[0] + r * np.cos(theta), BS_POSITION[1] + r * np.sin(theta), "k--", linewidth=0.5)
    ax.set_xlim(-PLAZA_HALF_WIDTH_M - 5, PLAZA_HALF_WIDTH_M + 5)
    ax.set_ylim(BS_POSITION[1] - 5, BS_POSITION[1] + RANGE_MAX_M + 5)
    ax.set_xlabel("x [m]  (east)")
    ax.set_ylabel("y [m]  (north)")
    ax.set_aspect("equal")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper right", fontsize=8)

    # Side view: BS panel + bodies' z=0
    ax = axes[1]
    for tier in ("A", "B", "C"):
        xy = np.array([b.spawn_xy for b in bodies if b.tier == tier])
        ax.scatter(np.linalg.norm(xy - BS_POSITION[:2], axis=1), np.zeros(len(xy)), c=colors[tier], s=20)
    ax.scatter([0], [BS_POSITION[2]], marker="^", s=180, c="k")
    ax.annotate(
        f"broadside={BS_BROADSIDE.round(2).tolist()}",
        xy=(0, BS_POSITION[2]),
        xytext=(2, BS_POSITION[2] + 1),
        fontsize=8,
    )
    ax.set_xlabel("range from BS [m]")
    ax.set_ylabel("z [m]")
    ax.set_title("Side view (BS panel + body feet)")
    ax.grid(alpha=0.3)
    ax.set_xlim(0, RANGE_MAX_M + 5)
    ax.set_ylim(-1, BS_POSITION[2] + 5)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(args.out, dpi=140)
    logger.info("Wrote %s", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
