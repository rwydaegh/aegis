"""Building the source set without a free number in it.

`measure_source_thickness.py` shows that letting the source occupy the top few
metres of a facade does not work. The thickness moves the direct term by 3.6 dB
at Korenmarkt, 6.1 dB at Brussels and 4.4 dB at New York, and it reorders the
squares: New York sits below Korenmarkt at half a metre and above it at eight.
That is the same failure the height band had. A number nobody can measure sets
the answer.

The reason it fails also says how to fix it. A sample eight metres down a wall is
more visible from the street than the tip above it, so a thicker band moves sites
downward and the flux rises. But that sample is still evidence that a facade
stands there. Lift it to the top of its own footprint and it lands on the tip,
which is where it belonged.

So the construction here keeps three tests and throws the fourth away.

A sample is kept if the sky is open straight above it, if something sits at least
``drop`` metres below it nearby, and if it is above the ground. The test that
asked for nothing higher within a radius is gone. It existed only to separate a
tip from the wall beneath it, and lifting makes that separation unnecessary,
which is the whole point: the test that needed the mesh to have crisp roof edges
is the test that a photogrammetric mesh cannot pass.

What is left of the wall is a vote for a footprint. Votes are counted on a grid
of cells ``cell`` metres across, one site per occupied cell, at the highest
surface in that cell. That removes the last bias too. Without it a ten storey
building would carry ten times the wall area of a two storey one and would draw
ten times the sites, when what the density assumption says is that sites go along
the roofline and not up the wall.

The one number left is the cell size, and it is a different kind of number. It is
a resolution, so it has a limit: shrink it and the answer converges, because the
site set approaches the roofline curve itself. A thickness has no such limit. The
sweep below shows the convergence, which is what turns the last parameter into a
measurement.
"""

from __future__ import annotations

from typing import Any

import json
import time

import numpy as np

from semantic_twin import paths

from semantic_twin.propagation.geometry import MitsubaGeometry
from semantic_twin.illumination.roofline import silhouette
from semantic_twin.illumination.source_studies import (
    COVERAGE_RADIUS_M,
    SOURCE_LIFT_M as SITE_LIFT_M,
    coverage,
    facade_votes as vote,
    lift_to_top,
    sites_from_votes,
)
from semantic_twin.illumination.sources import direct_from_sites, silhouette_cloud
from semantic_twin.walk.grid import build_walk
from semantic_twin.walk.ground import measure_ground_datum

ROOT = paths.root()


#: A site is placed this far above the highest surface in its cell, so a ray sent
#: at it from a clear direction passes over the roof rather than grazing it. It is
#: a numerical offset and not a mast: five centimetres carries no physics at these
#: distances, and the sweep in this script covers values a thousand times larger.
def run(args: Any) -> None:

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
        if points.shape[0] > args.standpoints:
            index = np.linspace(0, points.shape[0] - 1, args.standpoints).round().astype(int)
            points = points[index]

        cloud = silhouette_cloud(geometry, points, silhouette, azimuths=args.azimuths, elevations=args.elevations)
        per_case = []
        for drop_m in args.drop_m:
            votes = vote(
                geometry,
                samples=args.samples,
                rng=np.random.default_rng(args.seed),
                drop_radius_m=args.drop_radius_m,
                drop_m=drop_m,
                min_height_above_ground_m=args.min_height_m,
                ground_datum_m=datum.z_m,
            )
            for cell_m in args.cell_m:
                station = lift_to_top(geometry, sites_from_votes(votes, cell_m))
                direct, seen = direct_from_sites(geometry, points, station)
                covered = coverage(station, cloud)
                per_case.append(
                    {
                        "drop_m": float(drop_m),
                        "cell_m": float(cell_m),
                        "votes": int(votes.shape[0]),
                        "sites": int(station.shape[0]),
                        "coverage": covered,
                        "direct_median": float(np.median(direct)),
                        "spread_db": float(10.0 * np.log10(np.percentile(direct, 95) / np.percentile(direct, 5))),
                        "visible_fraction_median": float(np.median(seen)),
                        "direct_per_standpoint": [float(v) for v in direct],
                    }
                )
                print(
                    f"{site:22s} drop {drop_m:4.1f} cell {cell_m:4.1f} m  "
                    f"sites {station.shape[0]:6d}  cover {covered:.3f}  "
                    f"direct {per_case[-1]['direct_median']:.4e}  "
                    f"spread {per_case[-1]['spread_db']:+.2f} dB  "
                    f"vis {per_case[-1]['visible_fraction_median']:.4f}"
                )
        rows.append(
            {
                "site": site,
                "crop_radius_m": args.crop_m,
                "mesh": str(mesh.relative_to(ROOT)),
                "standpoints": int(points.shape[0]),
                "surface_samples": int(args.samples),
                "ground_datum_m": datum.z_m,
                "drop_radius_m": args.drop_radius_m,
                "min_height_above_ground_m": args.min_height_m,
                "site_lift_m": SITE_LIFT_M,
                "per_case": per_case,
                "seconds": time.perf_counter() - started,
            }
        )
        print()

    payload = {
        "question": "whether the source set can be built without a free number in it",
        "construction": "sky exposed samples with a drop nearby, one site per occupied cell at the top of that cell",
        "estimator": "mean over sites of visible / r**2, exact over the whole set",
        "note": "cell size is a resolution and converges, unlike a band thickness, which does not",
        "coverage_radius_m": COVERAGE_RADIUS_M,
        "rows": rows,
    }
    path = out_dir / f"{args.tag}_{args.crop_m}m.json"
    path.write_text(json.dumps(payload, indent=1))
    print(f"wrote {path.relative_to(ROOT)}")

    for row in rows:
        for drop_m in args.drop_m:
            case = [c for c in row["per_case"] if c["drop_m"] == drop_m]
            if len(case) < 2:
                continue
            terms = np.array([c["direct_median"] for c in case])
            steps = 10.0 * np.log10(terms[1:] / terms[:-1])
            print(f"{row['site']:22s} drop {drop_m:4.1f}  step to step " + " ".join(f"{s:+.2f}" for s in steps) + " dB")
