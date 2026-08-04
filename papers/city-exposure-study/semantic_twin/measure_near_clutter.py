"""How much of the direct term comes from whatever stands next to the pedestrian.

The facade tip law weights each azimuth by ``cos^2(alpha)/d``. It divides by the
distance, so a tip a few metres away counts for a great deal. That is correct for
a real facade. It is not correct for a lamp post, a tree, an awning, or a lump of
photogrammetry, and a mesh cannot tell those apart from a wall.

Two other measurements in this study point here. `SKYLINE_FUNCTION.md` finds a
pole two metres from a Korenmarkt camera that the photogrammetry built 1.5 m
across, covering 45 degrees of azimuth. The blend render finds the brightest
objects in the frame sitting 1.6 to 2.3 m from the head in the middle of an open
square, where no facade tip can be.

This measures the size of it over the walk rather than at one standpoint, and asks
the question that decides whether it matters: does dropping the near tips change
which squares come out highest.

A facade tip cannot be within a few metres of someone standing in a square, so a
cut on distance needs no class labels and no segmentation. It is crude, and it is
deliberately crude: it is a bound on how much the answer rests on objects the
method has no business placing a base station on.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import time

import numpy as np

from semantic_twin.propagation.geometry import MitsubaGeometry
from semantic_twin.illumination.roofline import silhouette
from semantic_twin.walk.grid import build_walk
from semantic_twin.walk.ground import measure_ground_datum

ROOT = pathlib.Path(__file__).resolve().parent

SITES = [
    "brussels_grandplace",
    "korenmarkt",
    "krakow_rynek",
    "london_trafalgar",
    "madrid_plazamayor",
    "mexico_zocalo",
    "milan_duomo",
    "newyork_timessquare",
    "prague_staromestske",
    "tokyo_hachiko",
    "toulouse_capitole",
]


def term(alpha: np.ndarray, horizontal: np.ndarray, found: np.ndarray, floor_m: float) -> float:
    """``mean over azimuth of cos^2(alpha)/d``, ignoring tips closer than the floor."""
    good = found & np.isfinite(horizontal) & (horizontal > floor_m)
    weight = np.zeros_like(alpha)
    weight[good] = np.cos(alpha[good]) ** 2 / horizontal[good]
    return float(weight.mean())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", nargs="*", default=SITES)
    ap.add_argument("--crop-m", type=int, default=250)
    ap.add_argument("--standpoints", type=int, default=16)
    ap.add_argument("--azimuths", type=int, default=720)
    ap.add_argument("--elevations", type=int, default=400)
    ap.add_argument("--floors-m", nargs="*", type=float, default=[0.0, 3.0, 5.0, 8.0, 12.0])
    ap.add_argument("--walk-radius-m", type=float, default=90.0)
    ap.add_argument("--head-height-m", type=float, default=1.5)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--variant", default="llvm_ad_rgb")
    ap.add_argument("--tag", default="near_clutter")
    args = ap.parse_args()

    out_dir = ROOT / "outputs" / "skyline"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for site in args.sites:
        mesh = ROOT / "data" / "geometry" / site / f"inhouse_leaf_{args.crop_m}m_f64.ply"
        if not mesh.exists():
            mesh = ROOT / "data" / "geometry" / site / f"inhouse_leaf_{args.crop_m}m.ply"
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

        per_floor: dict[float, list[float]] = {f: [] for f in args.floors_m}
        near_share = []
        for point in points:
            alpha, horizontal, found = silhouette(geometry, point, azimuths=args.azimuths, elevations=args.elevations)
            for floor in args.floors_m:
                per_floor[floor].append(term(alpha, horizontal, found, floor))
            good = found & np.isfinite(horizontal) & (horizontal > 0.0)
            near_share.append(float(np.mean(good & (horizontal <= 5.0))))

        medians = {f: float(np.median(v)) for f, v in per_floor.items()}
        base = medians[min(args.floors_m)]
        row = {
            "site": site,
            "standpoints": int(points.shape[0]),
            "crop_radius_m": args.crop_m,
            "direct_term_by_floor_m": {str(f): medians[f] for f in args.floors_m},
            "near_azimuth_fraction_median": float(np.median(near_share)),
            "share_from_within_5_m": float(1.0 - medians[5.0] / base) if 5.0 in medians else None,
            "seconds": time.perf_counter() - started,
        }
        rows.append(row)
        print(
            f"{site:22s} term {base:.5f}  under 5 m carries {row['share_from_within_5_m']:.2f}  "
            f"of azimuths {row['near_azimuth_fraction_median']:.3f}  "
            + "  ".join(f"{f:.0f}m {medians[f]:.5f}" for f in args.floors_m if f > 0)
        )

    payload = {
        "question": "how much of the direct term comes from tips a few metres from the head",
        "note": "a facade tip cannot be that close to someone standing in a square, so these are clutter",
        "rows": rows,
    }
    path = out_dir / f"{args.tag}_{args.crop_m}m.json"
    path.write_text(json.dumps(payload, indent=1))
    print(f"\nwrote {path.relative_to(ROOT)}")

    if len(rows) > 1:
        print("\nordering, highest direct term first")
        for floor in args.floors_m:
            order = sorted(rows, key=lambda r: -r["direct_term_by_floor_m"][str(floor)])
            print(f"  floor {floor:4.0f} m  " + "  ".join(r["site"][:11] for r in order))


if __name__ == "__main__":
    main()
