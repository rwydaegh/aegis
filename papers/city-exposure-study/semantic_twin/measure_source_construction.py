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

import argparse
import json
import pathlib
import time

import numpy as np
from scipy.spatial import cKDTree

from semantic_twin.propagation.geometry import MitsubaGeometry
from semantic_twin.illumination.roofline import UP_EPSILON_M, sample_surface, silhouette
from semantic_twin.walk.grid import build_walk
from semantic_twin.walk.ground import measure_ground_datum

from source_support import direct_from_sites, silhouette_cloud

ROOT = pathlib.Path(__file__).resolve().parent

#: A site is placed this far above the highest surface in its cell, so a ray sent
#: at it from a clear direction passes over the roof rather than grazing it. It is
#: a numerical offset and not a mast: five centimetres carries no physics at these
#: distances, and the sweep in this script covers values a thousand times larger.
SITE_LIFT_M = 0.05

#: A silhouette point counts as covered if a site sits within this far of it.
COVERAGE_RADIUS_M = 2.0


def vote(
    geometry: MitsubaGeometry,
    *,
    samples: int,
    rng: np.random.Generator,
    drop_radius_m: float,
    drop_m: float,
    min_height_above_ground_m: float,
    ground_datum_m: float,
) -> np.ndarray:
    """Surface samples that are evidence of a facade, before any lifting.

    Three tests. The sky is open straight above, so the sample is on an outer
    surface and not under an arcade. Something sits well below it nearby, so it is
    on a facade rather than in the middle of a roof. And it is above the ground,
    so it is not a kerb or a parked van.
    """
    points = sample_surface(geometry.vertices, geometry.faces, samples, rng)
    up = np.tile(np.array([0.0, 0.0, 1.0]), (points.shape[0], 1))
    hit, _, _, _ = geometry.intersect(points + UP_EPSILON_M * up, up)
    keep = (~hit) & (points[:, 2] - ground_datum_m >= min_height_above_ground_m)
    kept = points[keep]
    if kept.shape[0] == 0:
        raise RuntimeError("no sky exposed samples above the ground, check the datum")

    lowest = _cell_extreme(kept, drop_radius_m, np.minimum, np.inf, neighbours=True)
    return kept[kept[:, 2] - lowest >= drop_m]


def _cell_extreme(points: np.ndarray, cell_m: float, op, fill: float, *, neighbours: bool) -> np.ndarray:
    """Extreme ``z`` in each point's cell, or in the nine cells touching it.

    Linear in the sample count. The roofline of a 250 m crop is tens of kilometres
    long, so the draw has to be dense and a per point radius query cannot pay for
    itself.
    """
    key = np.floor(points[:, :2] / cell_m).astype(np.int64)
    key -= key.min(axis=0)
    width = int(key[:, 1].max()) + 1
    flat = key[:, 0] * width + key[:, 1]
    cells = int(key[:, 0].max() + 1) * width

    grid = np.full(cells, fill)
    op.at(grid, flat, points[:, 2])
    if not neighbours:
        return grid[flat]

    grid = grid.reshape(-1, width)
    padded = np.pad(grid, 1, constant_values=fill)
    out = np.full_like(grid, fill)
    for dx in range(3):
        for dy in range(3):
            out = op(out, padded[dx : dx + grid.shape[0], dy : dy + width])
    return out.reshape(-1)[flat]


def sites_from_votes(votes: np.ndarray, cell_m: float) -> np.ndarray:
    """One site per occupied cell, at the highest sample that fell in it.

    Equal weight per cell rather than per sample. A tall building has more wall
    area than a short one and therefore more votes, and counting votes rather than
    cells would put more sites on it. The density assumption says sites go along
    the roofline, so the footprint is what should be counted.

    The site takes the position of the highest sample rather than the centre of
    its cell. A cell that straddles a facade has street on one side of it, and a
    site at the centre of such a cell floats in mid air with nothing under it.
    """
    key = np.floor(votes[:, :2] / cell_m).astype(np.int64)
    key -= key.min(axis=0)
    width = int(key[:, 1].max()) + 1
    flat = key[:, 0] * width + key[:, 1]

    order = np.lexsort((-votes[:, 2], flat))
    flat_sorted = flat[order]
    first = np.concatenate(([True], flat_sorted[1:] != flat_sorted[:-1]))
    return votes[order][first]


def lift_to_top(geometry: MitsubaGeometry, points: np.ndarray) -> np.ndarray:
    """Raise each point to the highest surface directly above or below it.

    A downward ray from above the scene finds the true top at that horizontal
    position, which is what a sample on a vertical wall wants: the tip of that
    wall. Doing it by ray rather than by taking the highest sample in the cell is
    what keeps the cell size and the sample count from being tangled together.
    Without it a small cell holds few samples, its highest sample sits below the
    real edge, and the sweep reads that as a change of answer with cell size when
    it is only a change of sampling.
    """
    ceiling = float(geometry.vertices[:, 2].max()) + 10.0
    above = points.copy()
    above[:, 2] = ceiling
    down = np.tile(np.array([0.0, 0.0, -1.0]), (points.shape[0], 1))
    hit, distance, _, _ = geometry.intersect(above, down)

    top = points.copy()
    found = hit & np.isfinite(distance)
    top[found, 2] = ceiling - distance[found]
    # A downward ray that finds nothing leaves the sample where it was. That can
    # only happen if the point is not under any surface, which the sky test above
    # already made unlikely, so it is a fallback and not a case.
    top[:, 2] = np.maximum(top[:, 2], points[:, 2])
    top[:, 2] += SITE_LIFT_M
    return top


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", nargs="*", default=["korenmarkt", "brussels_grandplace", "newyork_timessquare"])
    ap.add_argument("--crop-m", type=int, default=250)
    ap.add_argument("--cell-m", nargs="*", type=float, default=[8.0, 4.0, 2.0, 1.0, 0.5])
    ap.add_argument("--drop-m", nargs="*", type=float, default=[3.0])
    ap.add_argument("--samples", type=int, default=4_000_000)
    ap.add_argument("--standpoints", type=int, default=8)
    ap.add_argument("--azimuths", type=int, default=360)
    ap.add_argument("--elevations", type=int, default=400)
    ap.add_argument("--drop-radius-m", type=float, default=2.0)
    ap.add_argument("--min-height-m", type=float, default=4.0)
    ap.add_argument("--walk-radius-m", type=float, default=90.0)
    ap.add_argument("--head-height-m", type=float, default=1.5)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--variant", default="llvm_ad_rgb")
    ap.add_argument("--tag", default="construction")
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
        if points.shape[0] > args.standpoints:
            index = np.linspace(0, points.shape[0] - 1, args.standpoints).round().astype(int)
            points = points[index]

        cloud = silhouette_cloud(geometry, points, silhouette, azimuths=args.azimuths, elevations=args.elevations)
        tree = cKDTree(cloud) if cloud.shape[0] else None

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
                covered = float("nan")
                if tree is not None and station.shape[0]:
                    near, _ = cKDTree(station).query(cloud, distance_upper_bound=COVERAGE_RADIUS_M)
                    covered = float(np.mean(np.isfinite(near)))
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


if __name__ == "__main__":
    main()
