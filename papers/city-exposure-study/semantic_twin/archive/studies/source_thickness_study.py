"""How much the answer depends on how thick the source is.

A base station site sits on a facade tip, and a tip is a line, so in principle the
source has no thickness at all. A photogrammetric mesh cannot carry that. Its
roofs are lumpy at the half metre scale, so a test that asks for nothing higher
within two metres throws away genuine top edges along with the wall faces it is
meant to remove. Measured at Korenmarkt, a strict test finds a tip near only 38
percent of the silhouette, and that number saturates between 800 thousand and 4
million surface samples, so it is the mesh and not the sampling.

The repair is to let the source occupy the top ``thickness`` metres of the facade
rather than the tip alone. Nothing is lifted above the roof, so this is not a
mast. It is a statement that the top few metres of a wall are where a site can
be, which is also closer to true.

This script measures what that choice costs. For each thickness it extracts the
source band, connects every standpoint to every point in it with one shadow ray,
and reports the direct term. The estimator is

    direct  proportional to  mean over band points of  visible / r**2

with ``r`` the slant range. The mean is over all sampled points and not over the
visible ones, which is what makes the number independent of the band thickness
by construction: a band twice as thick holds twice as many samples standing for
half as much roofline each. Any dependence on thickness that survives is a real
change in which surfaces the standpoint can see, which is the thing worth
knowing.

The count comes from the density assumption. Antennas per square kilometre are
taken equal across cities, so a crop of fixed radius holds a fixed number of
them however long its roofline is, and each sampled band point stands for the
same number of antennas at every site. That is why no roofline length appears.

Reported next to it is the silhouette coverage: the fraction of the visible
skyline, found independently by a ray fan, that has a band point within two
metres of it. That is the diagnostic the thickness is meant to repair.
"""

from __future__ import annotations

from typing import Any

import json
import time

import numpy as np

from semantic_twin import paths

from semantic_twin.propagation.geometry import MitsubaGeometry
from semantic_twin.illumination.roofline import silhouette
from semantic_twin.illumination.source_studies import COVERAGE_RADIUS_M, coverage, prepare_source_band as prepare
from semantic_twin.illumination.sources import direct_from_sites, silhouette_cloud
from semantic_twin.walk.grid import build_walk
from semantic_twin.walk.ground import measure_ground_datum

ROOT = paths.root()


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

        # The silhouette is measured once, by a fan, and never reads the band.
        # That independence is what makes the coverage number mean something.
        silhouette_points = silhouette_cloud(
            geometry, points, silhouette, azimuths=args.azimuths, elevations=args.elevations
        )

        rng = np.random.default_rng(args.seed)
        kept, lowest, highest = prepare(
            geometry,
            samples=args.samples,
            rng=rng,
            edge_radius_m=args.edge_radius_m,
            min_height_above_ground_m=args.min_height_m,
            ground_datum_m=datum.z_m,
        )
        has_drop = kept[:, 2] - lowest >= args.edge_drop_m

        per_thickness = []
        for thickness in args.thickness_m:
            band = kept[has_drop & (highest - kept[:, 2] < thickness)]
            if band.shape[0] == 0:
                print(f"{site:24s} thickness {thickness:4.1f} m  empty band")
                continue
            direct, seen = direct_from_sites(geometry, points, band)
            per_thickness.append(
                {
                    "thickness_m": float(thickness),
                    "band_points": int(band.shape[0]),
                    "coverage": coverage(band, silhouette_points),
                    "direct_median": float(np.median(direct)),
                    "direct_p05": float(np.percentile(direct, 5)),
                    "direct_p95": float(np.percentile(direct, 95)),
                    "spread_db": float(10.0 * np.log10(np.percentile(direct, 95) / np.percentile(direct, 5))),
                    "visible_fraction_median": float(np.median(seen)),
                    "direct_per_standpoint": [float(v) for v in direct],
                }
            )
            print(
                f"{site:24s} thickness {thickness:4.1f} m  "
                f"band {band.shape[0]:7d}  cover {per_thickness[-1]['coverage']:.3f}  "
                f"direct {per_thickness[-1]['direct_median']:.4e}  "
                f"spread {per_thickness[-1]['spread_db']:+.2f} dB  "
                f"vis {per_thickness[-1]['visible_fraction_median']:.4f}"
            )

        if per_thickness:
            terms = np.array([t["direct_median"] for t in per_thickness])
            drift = 10.0 * np.log10(terms.max() / terms.min())
            print(f"{site:24s} direct term moves {drift:.2f} dB across the thickness sweep\n")
        else:
            drift = float("nan")

        rows.append(
            {
                "site": site,
                "crop_radius_m": args.crop_m,
                "mesh": str(mesh.relative_to(ROOT)),
                "standpoints": int(points.shape[0]),
                "surface_samples": int(args.samples),
                "sky_exposed": int(kept.shape[0]),
                "ground_datum_m": datum.z_m,
                "edge_radius_m": args.edge_radius_m,
                "edge_drop_m": args.edge_drop_m,
                "direct_drift_db": float(drift),
                "per_thickness": per_thickness,
                "seconds": time.perf_counter() - started,
            }
        )

    payload = {
        "question": "how much the direct term depends on how thick the source band is",
        "estimator": "mean over band points of visible / r**2, exact over the whole band",
        "note": "the mean is over all band points, so the band thickness cancels by construction",
        "coverage_radius_m": COVERAGE_RADIUS_M,
        "rows": rows,
    }
    path = out_dir / f"{args.tag}_{args.crop_m}m.json"
    path.write_text(json.dumps(payload, indent=1))
    print(f"wrote {path.relative_to(ROOT)}")

    if len(rows) > 1:
        print("\nbetween site ratio against the thinnest band, per thickness")
        for i, thickness in enumerate(args.thickness_m):
            values = []
            for row in rows:
                match = [t for t in row["per_thickness"] if t["thickness_m"] == thickness]
                if match:
                    values.append(match[0]["direct_median"])
            if len(values) == len(rows):
                values = np.array(values)
                print(
                    f"  {thickness:4.1f} m  "
                    + "  ".join(
                        f"{row['site'][:12]:12s} {10.0 * np.log10(v / values[0]):+6.2f} dB"
                        for row, v in zip(rows, values)
                    )
                )
            _ = i
