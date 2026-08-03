"""The source set with no threshold in it, taken straight off the skyline.

Two earlier attempts put base station sites on the mesh by testing surface
samples. `measure_source_thickness.py` shows that a band of given thickness fails
outright: the thickness moves the answer by 3.6 to 6.1 dB and reorders the
squares. `measure_source_construction.py` repairs part of that by counting
footprint cells rather than wall area, but it still carries four thresholds, a
sky test, a drop, a drop radius and a minimum height, and its coverage of the
visible skyline saturates near 0.57 however small the cells get.

Both share one flaw. They ask the mesh where its roof edges are, and a
photogrammetric mesh does not know. Its roofs are lumpy at the half metre scale,
so any test sharp enough to reject a wall also rejects real edges.

There is a way to never ask that question. The skyline is not a property of the
mesh, it is a property of a viewpoint: it is the boundary between surface and sky
in the picture taken there. A ray fan from a standpoint finds it exactly, with no
threshold, because it is defined by what the ray hits and not by how the surface
is shaped. So build the source set out of the fan itself. The union of the
silhouettes seen along the walk is the set of surfaces that are skyline from the
street, and that is a fair description of where an operator can put a site and
have it serve the street.

This is also the same idea the rest of the study runs on. The set is the sky
boundary of the panorama, put back on the geometry. Nothing enters it that the
photograph does not show.

What replaces the thresholds are three resolutions, and the difference matters. A
thickness has no limit, so there is no value of it that is more right than
another. A resolution has one. Send more rays, take more standpoints, or shrink
the cell the set is thinned onto, and the set approaches the visible skyline
itself. This script measures all three approaching it.

The thinning needs one word of explanation. A fan samples evenly in angle, so a
wall seen edge on crowds many samples into a narrow slice of azimuth and would be
over weighted. Thinning to one site per occupied cell undoes that without a
correction factor: a cell holds one site whether one ray found it or a thousand
did. That is also why no obliquity term appears anywhere here.

What the sweeps actually found, at 250 m over Korenmarkt and Brussels:

- **The number of standpoints that build the set does converge.** Going 64 to 128
  to 256 moves the answer by 0.02 and 0.29 dB at Korenmarkt and 0.00 and 0.09 at
  Brussels, while coverage of what a held out standpoint sees saturates at 0.99
  and 0.88. So 128 is enough and more does not help.
- **The cell does not converge in the range measured.** It drifts up by 0.2 to
  0.5 dB per halving, at both squares, on a flat grid and on a solid one alike.
  Refining keeps resolving skyline that a coarser cell had merged away, which
  shows up as the visible fraction climbing about 40 percent from 4 m cells to
  0.5 m ones.
- **It drifts both squares together, so it cancels where it is read.** Korenmarkt
  stands 0.63 to 0.83 dB above Brussels on a solid grid and 0.65 to 1.10 dB on a
  flat one, across a factor of eight in cell size. The comparison between cities
  is what this study reports, and that is stable to about 0.2 dB.

One earlier reading of these sweeps has to be retracted rather than quietly
dropped. With 8 held out standpoints Korenmarkt appeared not to converge in cell
size while Brussels did, and that difference was attributed first to a pole
standing near the pedestrian and then to the flat grid. With 48 held out
standpoints the difference is not there: both squares drift by the same 0.2 to
0.5 dB per halving. It was noise in a median over 8 numbers.

The solid grid is still the better default, on an argument that does not rest on
that comparison. See `thin`.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import time

import numpy as np
from scipy.spatial import cKDTree

from semantic_twin.propagation.geometry import MitsubaGeometry
from semantic_twin.propagation.skyline import silhouette
from semantic_twin.propagation.sources import thin
from semantic_twin.propagation.walk import build_walk, measure_ground_datum

from source_support import direct_from_sites, silhouette_cloud

ROOT = pathlib.Path(__file__).resolve().parent

COVERAGE_RADIUS_M = 2.0


# `thin` lives in the package, because the tracer builds source sets with it too.
# It is re-exported here so this script and its tests read the way they did.
__all__ = ["thin", "coverage", "main"]


def coverage(sites: np.ndarray, cloud: np.ndarray) -> float:
    if sites.shape[0] == 0 or cloud.shape[0] == 0:
        return float("nan")
    near, _ = cKDTree(sites).query(cloud, distance_upper_bound=COVERAGE_RADIUS_M)
    return float(np.mean(np.isfinite(near)))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", nargs="*", default=["korenmarkt", "brussels_grandplace", "newyork_timessquare"])
    ap.add_argument("--crop-m", type=int, default=250)
    ap.add_argument("--cell-m", nargs="*", type=float, default=[8.0, 4.0, 2.0, 1.0, 0.5])
    ap.add_argument("--builders", nargs="*", type=int, default=[4, 8, 16, 32])
    ap.add_argument("--azimuths", nargs="*", type=int, default=[360, 720, 1440])
    ap.add_argument("--elevations", type=int, default=600)
    ap.add_argument(
        "--floor-m",
        type=float,
        default=0.0,
        help="drop silhouette hits nearer than this from the standpoint that found them",
    )
    ap.add_argument("--held-out", type=int, default=8)
    ap.add_argument("--walk-radius-m", type=float, default=90.0)
    ap.add_argument("--head-height-m", type=float, default=1.5)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--variant", default="llvm_ad_rgb")
    ap.add_argument("--tag", default="silhouette")
    ap.add_argument(
        "--pick",
        choices=["highest", "uniform"],
        default="highest",
        help="which member of an occupied cell becomes the site",
    )
    ap.add_argument(
        "--dims",
        type=int,
        choices=[2, 3],
        default=2,
        help="thin on a flat grid or a solid one",
    )
    args = ap.parse_args()

    geometry_root = ROOT / "data" / "geometry"
    out_dir = ROOT / "outputs" / "skyline"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for site in args.sites:
        mesh = geometry_root / site / f"inhouse_leaf_{args.crop_m}m_f64.ply"
        if not mesh.exists():
            mesh = geometry_root / site / f"inhouse_leaf_{args.crop_m}m.ply"
        if not mesh.exists():
            print(f"{site:24s} no {args.crop_m} m mesh, skipped")
            continue

        started = time.perf_counter()
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

        # The standpoints that build the set and the standpoints the answer is
        # read at are disjoint. Without that split a standpoint would be scored
        # against a source set it wrote itself, and every site it can see would be
        # in there by construction, which reads as convergence and is not.
        rng = np.random.default_rng(args.seed)
        order = rng.permutation(points.shape[0])
        evaluate = points[order[: args.held_out]]
        pool = points[order[args.held_out :]]

        # What the held out standpoints see, measured once at the finest fan. It
        # does not depend on the builders, and judging every case against the same
        # truth is what stops a coarse fan from scoring well by being graded
        # against its own coarseness.
        # The floor applies here too. It is a statement about which surfaces count
        # as roofline, so the set being judged and the truth it is judged against
        # have to agree on it, or the floor would simply read as missing coverage.
        truth = silhouette_cloud(
            geometry,
            evaluate,
            silhouette,
            azimuths=max(args.azimuths),
            elevations=args.elevations,
            floor_m=args.floor_m,
        )

        per_case = []
        for azimuths in args.azimuths:
            for builders in args.builders:
                if builders > pool.shape[0]:
                    continue
                index = np.linspace(0, pool.shape[0] - 1, builders).round().astype(int)
                cloud = silhouette_cloud(
                    geometry,
                    pool[index],
                    silhouette,
                    azimuths=azimuths,
                    elevations=args.elevations,
                    floor_m=args.floor_m,
                )
                for cell_m in args.cell_m:
                    pick = np.random.default_rng(args.seed) if args.pick == "uniform" else None
                    station = thin(cloud, cell_m, pick, dims=args.dims)
                    direct, seen = direct_from_sites(geometry, evaluate, station)
                    per_case.append(
                        {
                            "azimuths": int(azimuths),
                            "builders": int(builders),
                            "cell_m": float(cell_m),
                            "cloud": int(cloud.shape[0]),
                            "sites": int(station.shape[0]),
                            "coverage_of_held_out": coverage(station, truth),
                            "direct_median": float(np.median(direct)),
                            "spread_db": float(10.0 * np.log10(np.percentile(direct, 95) / np.percentile(direct, 5))),
                            "visible_fraction_median": float(np.median(seen)),
                            "direct_per_standpoint": [float(v) for v in direct],
                        }
                    )
                    print(
                        f"{site:20s} az {azimuths:5d} build {builders:3d} cell {cell_m:4.1f}  "
                        f"sites {station.shape[0]:6d}  cover {per_case[-1]['coverage_of_held_out']:.3f}  "
                        f"direct {per_case[-1]['direct_median']:.4e}  "
                        f"vis {per_case[-1]['visible_fraction_median']:.3f}"
                    )
        rows.append(
            {
                "site": site,
                "crop_radius_m": args.crop_m,
                "mesh": str(mesh.relative_to(ROOT)),
                "walk_standpoints": int(points.shape[0]),
                "held_out": int(evaluate.shape[0]),
                "elevations": args.elevations,
                "pick": args.pick,
                "dims": args.dims,
                "floor_m": args.floor_m,
                "ground_datum_m": datum.z_m,
                "per_case": per_case,
                "seconds": time.perf_counter() - started,
            }
        )
        print()

    payload = {
        "question": "whether the visible skyline itself can be the source set",
        "construction": "union of ray fan silhouettes along the walk, thinned to one site per occupied cell",
        "estimator": "mean over sites of visible / r**2, exact over the whole set",
        "note": "builders and evaluation standpoints are disjoint, so no standpoint is scored against a set it wrote",
        "coverage_radius_m": COVERAGE_RADIUS_M,
        "rows": rows,
    }
    path = out_dir / f"{args.tag}_{args.crop_m}m.json"
    path.write_text(json.dumps(payload, indent=1))
    print(f"wrote {path.relative_to(ROOT)}")

    for row in rows:
        finest = max(args.azimuths)
        for name, key in (("cell", "cell_m"), ("builders", "builders")):
            fixed = "builders" if key == "cell_m" else "cell_m"
            hold = max(args.builders) if fixed == "builders" else min(args.cell_m)
            case = [c for c in row["per_case"] if c["azimuths"] == finest and c[fixed] == hold]
            if len(case) < 2:
                continue
            case.sort(key=lambda c: c[key])
            terms = np.array([c["direct_median"] for c in case])
            steps = 10.0 * np.log10(terms[1:] / terms[:-1])
            print(f"{row['site']:20s} in {name:9s} " + " ".join(f"{s:+.2f}" for s in steps) + " dB per step")


if __name__ == "__main__":
    main()
