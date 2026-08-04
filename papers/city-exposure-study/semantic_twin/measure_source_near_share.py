"""Where in range the silhouette source set puts its direct term, and whether
that changes as the cells shrink.

`measure_source_silhouette.py` leaves one thing unsettled. Refine the thinning
cell and Brussels settles down while Korenmarkt does not: its last halving still
moves the direct term by 0.65 dB, and the fraction of sites its standpoints can
see climbs at every step while Brussels holds flat.

The first guess was clutter standing next to the pedestrian, so
`silhouette_cloud` grew a floor that drops tips found close to the standpoint
that found them. It changed the answer by 0.04 dB, which rules that guess out.
The reason is worth keeping: the floor cuts by distance from the standpoint that
*built* the set, and the term is read at held out standpoints somewhere else. A
facade three metres from where you are reading is in the set legitimately,
because some other standpoint saw it from thirty.

So ask the question at the reading end instead. Split the direct term by how far
the site is from the standpoint it is read at, and watch each band as the cells
shrink. If the near band is what grows, the construction is putting more and more
weight on surfaces near the pedestrian and the cell is not a resolution. If every
band grows together, the set is simply still filling in.

What it found. **Nothing within 10 m contributes anything at either square**, and
at Korenmarkt nothing within 5 m contributes even on a solid grid at 128
builders. That is not a surprise once said out loud: a standpoint 1.5 m up
looking at a roofline 20 m up is at least 18 m away from it whatever the building
does, so the range is set by building height and not by how close you stand. It
also rules out the first guess for good.

Korenmarkt does carry 4 to 7 percent of its term in the 5 to 10 m band where
Brussels carries exactly zero, which is a low object standing near the
pedestrian. It is real but it is not what drives the cell size drift.

Note that this range is the slant range to a site, not the horizontal distance
that `measure_near_clutter.py` cuts on. A tip 2 m away horizontally and 82
degrees up is 14 m away in slant. The two measurements do not disagree, they are
distances between different pairs of points.
"""

from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np

from semantic_twin.propagation.geometry import MitsubaGeometry
from semantic_twin.illumination.roofline import silhouette
from semantic_twin.walk.grid import build_walk
from semantic_twin.walk.ground import measure_ground_datum

from measure_source_silhouette import thin
from source_support import silhouette_cloud

ROOT = pathlib.Path(__file__).resolve().parent

EDGES_M = (0.0, 5.0, 10.0, 20.0, 40.0, 80.0, np.inf)


def banded_direct(
    geometry,
    origins: np.ndarray,
    sites: np.ndarray,
    *,
    epsilon_m: float = 1.0e-3,
    chunk: int = 400_000,
) -> np.ndarray:
    """The same estimator, kept split by range band instead of summed.

    Rows are standpoints, columns are the bands between ``EDGES_M``. Every column
    is divided by the whole site count, not by the count in its own band, so the
    columns add up to the direct term the other scripts report.
    """
    out = np.zeros((origins.shape[0], len(EDGES_M) - 1), dtype=np.float64)
    if sites.shape[0] == 0:
        return out
    for i, origin in enumerate(origins):
        for start in range(0, sites.shape[0], chunk):
            target = sites[start : start + chunk]
            delta = target - origin
            distance = np.linalg.norm(delta, axis=1)
            direction = delta / np.maximum(distance, 1.0e-12)[:, None]
            hit, travel, _, _ = geometry.intersect(
                np.broadcast_to(origin, direction.shape) + epsilon_m * direction, direction
            )
            visible = (~hit) | (travel >= distance - 2.0 * epsilon_m)
            good = visible & (distance > 0.0)
            r = distance[good]
            weight = 1.0 / r**2
            for b in range(len(EDGES_M) - 1):
                inside = (r >= EDGES_M[b]) & (r < EDGES_M[b + 1])
                out[i, b] += float(np.sum(weight[inside]))
    return out / sites.shape[0]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", nargs="*", default=["korenmarkt", "brussels_grandplace"])
    ap.add_argument("--crop-m", type=int, default=250)
    ap.add_argument("--cell-m", nargs="*", type=float, default=[4.0, 2.0, 1.0, 0.5])
    ap.add_argument("--builders", type=int, default=32)
    ap.add_argument("--dims", type=int, choices=[2, 3], default=2)
    ap.add_argument("--azimuths", type=int, default=1440)
    ap.add_argument("--elevations", type=int, default=600)
    ap.add_argument("--held-out", type=int, default=8)
    ap.add_argument("--walk-radius-m", type=float, default=90.0)
    ap.add_argument("--head-height-m", type=float, default=1.5)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--variant", default="llvm_ad_rgb")
    args = ap.parse_args()

    out_dir = ROOT / "outputs" / "skyline"
    out_dir.mkdir(parents=True, exist_ok=True)

    labels = []
    for b in range(len(EDGES_M) - 1):
        high = EDGES_M[b + 1]
        labels.append(f"{EDGES_M[b]:.0f}-{'inf' if not np.isfinite(high) else f'{high:.0f}'}")

    rows = []
    for site in args.sites:
        mesh = ROOT / "data" / "geometry" / site / f"inhouse_leaf_{args.crop_m}m_f64.ply"
        if not mesh.exists():
            mesh = ROOT / "data" / "geometry" / site / f"inhouse_leaf_{args.crop_m}m.ply"
        if not mesh.exists():
            print(f"{site:24s} no {args.crop_m} m mesh, skipped")
            continue

        geometry = MitsubaGeometry(mesh, variant=args.variant)
        datum = measure_ground_datum(geometry, radius_m=args.walk_radius_m)
        walk = build_walk(
            geometry,
            ground_datum_m=datum.z_m,
            radius_m=args.walk_radius_m,
            head_height_m=args.head_height_m,
            seed=args.seed,
        )
        points = np.asarray(walk.points)
        rng = np.random.default_rng(args.seed)
        order = rng.permutation(points.shape[0])
        evaluate = points[order[: args.held_out]]
        pool = points[order[args.held_out :]]

        index = np.linspace(0, pool.shape[0] - 1, args.builders).round().astype(int)
        cloud = silhouette_cloud(
            geometry,
            pool[index],
            silhouette,
            azimuths=args.azimuths,
            elevations=args.elevations,
        )

        print(f"{site}   bands in metres, each as a share of the whole direct term")
        print("  cell    sites  " + "  ".join(f"{lab:>9s}" for lab in labels) + "     total")
        per_cell = []
        for cell_m in args.cell_m:
            station = thin(cloud, cell_m, dims=args.dims)
            banded = banded_direct(geometry, evaluate, station)
            median = np.median(banded, axis=0)
            total = float(np.median(banded.sum(axis=1)))
            share = median / max(median.sum(), 1e-300)
            per_cell.append(
                {
                    "cell_m": float(cell_m),
                    "sites": int(station.shape[0]),
                    "band_median": [float(v) for v in median],
                    "band_share": [float(v) for v in share],
                    "direct_median": total,
                }
            )
            print(f"  {cell_m:4.1f} {station.shape[0]:8d}  " + "  ".join(f"{v:9.3f}" for v in share) + f"  {total:.4e}")
        # The question is which band carries the refinement, so report each band's
        # own change per halving rather than only the change in the sum.
        table = np.array([c["band_median"] for c in per_cell])
        print("  change per halving of the cell, decibels, by band")
        for j in range(1, table.shape[0]):
            steps = 10.0 * np.log10(np.maximum(table[j], 1e-300) / np.maximum(table[j - 1], 1e-300))
            print(
                f"  {per_cell[j - 1]['cell_m']:4.1f} to {per_cell[j]['cell_m']:4.1f}  "
                + "  ".join(f"{s:+9.2f}" for s in steps)
            )
        print()
        rows.append({"site": site, "builders": args.builders, "per_cell": per_cell})

    payload = {
        "question": "which range band carries the cell size dependence of the silhouette source set",
        "edges_m": [float(e) for e in EDGES_M],
        "labels": labels,
        "note": "bands are distances from the standpoint the term is read at, not from the standpoint that built the set",
        "rows": rows,
    }
    path = out_dir / f"near_share_{args.crop_m}m.json"
    path.write_text(json.dumps(payload, indent=1))
    print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
