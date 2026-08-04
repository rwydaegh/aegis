"""Exposure from an explicit set of rooftop sites, with the direct term set to 1.

Everywhere else in this study the base station population is marginalised into
an angular density and read off the direction a ray escapes in. That assumes the
sources are far enough away that only their direction matters, which is not true
here: the skyline sits 18 to 70 m from the head, and a bounce happens tens of
metres away, so which rooftops are visible really does differ between the head
and the wall the ray bounced off.

This script runs the other estimator. The sources are explicit points on the
roofline, built by `semantic_twin.illumination`, and a path reaches one by
connecting to it. The visibility question is then answered from the point where
it is asked.

What it reports is deliberately a ratio. The line of sight term is computed
exactly over the whole source set, the bounced term is estimated by connecting
at every path vertex, and the answer is printed as

    surplus = (direct + bounced) / direct

so the direct term is 1 by construction. That kills every constant this study
would otherwise have to state and defend: how many antennas there are, what they
transmit, and the `4 pi` in front of both terms. All of them sit in front of the
direct term and the bounced term identically, so they cancel. What is left is the
one thing the geometry decides, which is how much more a pedestrian gets than the
rooftops they can see would give on their own.

The standpoints that build the source set and the standpoints the answer is read
at are kept disjoint, so no standpoint is scored against a set it wrote itself.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import time

import numpy as np

from typing import Any

from semantic_twin.illumination import ISOTROPIC, ROOFTOP, SITE_LIFT_M, build_source_set, silhouette
from semantic_twin.materials import classify_faces, clutter_triangles, load_table
from semantic_twin.paths import site_mesh
from semantic_twin.propagation.geometry import MitsubaGeometry
from semantic_twin.transport import SbrTracer, TraceConfig
from semantic_twin.transport.next_event import NextEventGather
from semantic_twin.walk import build_walk, measure_ground_datum, site_walk

ROOT = pathlib.Path(__file__).resolve().parent
CONFIG = ROOT / "config"


def site_clutter(site: str, geometry: Any, args: argparse.Namespace) -> tuple[np.ndarray | None, dict[str, Any]]:
    """The mask of triangles the panoramas call clutter, or nothing if not asked.

    A missing fishnet is reported rather than raised. Every site that has one
    should use it, but a site that has none still has a silhouette, and refusing
    to trace it would remove a square from the study over a missing input rather
    than over anything measured.
    """
    if not args.drop_clutter:
        return None, {"used": False, "reason": "not asked for"}
    fishnet = ROOT / "outputs" / f"{site}_fishnet_vistas_{args.crop_m}m"
    semantics = next((ROOT / "data" / "panoramas" / site).glob("**/semantics/semantics.json"), None)
    if not fishnet.is_dir() or semantics is None:
        print(f"{site:24s} no {args.crop_m} m fishnet, every silhouette tip kept")
        return None, {"used": False, "reason": f"no fishnet at {fishnet.name}"}
    mask, report = clutter_triangles(geometry.faces.shape[0], fishnet_dir=fishnet, semantics_path=semantics)
    print(
        f"{site:24s} clutter mask {int(mask.sum())} triangles, "
        f"{report['clutter_fraction_of_seen']:.1%} of what the panoramas saw"
    )
    return mask, {"used": True, **report}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", nargs="*", default=["korenmarkt", "brussels_grandplace"])
    ap.add_argument("--crop-m", type=int, default=250)
    ap.add_argument("--rays", type=int, default=200_000)
    ap.add_argument("--builders", type=int, default=128)
    ap.add_argument("--held-out", type=int, default=16)
    ap.add_argument("--azimuths", type=int, default=1440)
    ap.add_argument("--elevations", type=int, default=600)
    ap.add_argument("--cell-m", type=float, default=1.0)
    ap.add_argument("--dims", type=int, choices=[2, 3], default=3)
    ap.add_argument("--site-lift-m", type=float, default=SITE_LIFT_M)
    ap.add_argument("--connections", type=int, default=1, help="sites connected per path vertex")
    ap.add_argument("--frequency-hz", type=float, default=15.0e9)
    ap.add_argument("--max-bounces", type=int, default=3)
    ap.add_argument("--walk-radius-m", type=float, default=90.0)
    ap.add_argument("--head-height-m", type=float, default=1.5)
    ap.add_argument("--walk", choices=["route", "grid"], default="route")
    ap.add_argument(
        "--walk-path",
        choices=["links", "street", "closest"],
        default="links",
        help="links walks the capture path, street asks Google Routes, closest measures both and keeps the nearer",
    )
    ap.add_argument("--walk-stride-m", type=float, default=6.0)
    ap.add_argument(
        "--drop-clutter",
        action="store_true",
        help="keep sites off the tips the panoramas call a sign, a pole or a canopy",
    )
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--variant", default="llvm_ad_rgb")
    ap.add_argument("--tag", default="next_event")
    args = ap.parse_args()

    out_dir = ROOT / "outputs" / "next_event"
    out_dir.mkdir(parents=True, exist_ok=True)

    models = {"isotropic": ISOTROPIC, "rooftop": ROOFTOP}
    rows = []
    for site in args.sites:
        try:
            mesh = site_mesh(site, args.crop_m)
        except FileNotFoundError:
            print(f"{site:24s} no {args.crop_m} m mesh, skipped")
            continue

        started = time.perf_counter()
        geometry = MitsubaGeometry(mesh, variant=args.variant)
        datum = measure_ground_datum(geometry, radius_m=args.walk_radius_m)
        if args.walk == "route":
            walk, provenance = site_walk(
                geometry,
                site,
                stride_m=args.walk_stride_m,
                head_height_m=args.head_height_m,
                path=args.walk_path,
            )
            print(
                f"{site:24s} capture route, {provenance['stations']} cameras, "
                f"{provenance['standpoints']} standpoints over {provenance['road_length_m']:.0f} m"
            )
        else:
            walk = build_walk(
                geometry,
                ground_datum_m=datum.z_m,
                radius_m=args.walk_radius_m,
                head_height_m=args.head_height_m,
                seed=args.seed,
            )
        points = np.asarray(walk.points)
        # The capture route is as long as the street the camera drove, and at
        # Korenmarkt that is 49 m. Asking it for 144 standpoints would either
        # fail or quietly space them 0.3 m apart and call them independent.
        # Neither is honest, so the split shrinks with the route and says so.
        held_out = args.held_out
        if points.shape[0] < args.held_out + args.builders:
            held_out = max(2, round(points.shape[0] * args.held_out / (args.held_out + args.builders)))
            print(
                f"{site:24s} {points.shape[0]} standpoints is short of the "
                f"{args.held_out + args.builders} asked for, holding out {held_out}"
            )
        rng = np.random.default_rng(args.seed)
        order = rng.permutation(points.shape[0])
        evaluate = points[order[:held_out]]
        pool = points[order[held_out:]]
        index = np.linspace(0, pool.shape[0] - 1, min(args.builders, pool.shape[0])).round().astype(int)

        clutter, clutter_report = site_clutter(site, geometry, args)
        sources = build_source_set(
            geometry,
            pool[index],
            silhouette,
            azimuths=args.azimuths,
            elevations=args.elevations,
            cell_m=args.cell_m,
            dims=args.dims,
            site_lift_m=args.site_lift_m,
            clutter_triangles=clutter,
        )
        direct, seen = sources.direct(geometry, evaluate)

        face_class = classify_faces(geometry.vertices, geometry.faces, datum.z_m)
        binding = load_table(CONFIG, args.frequency_hz)
        config = TraceConfig(
            frequency_hz=args.frequency_hz,
            rays=args.rays,
            max_bounces=args.max_bounces,
            seed=args.seed,
        )
        tracer = SbrTracer(geometry, face_class, binding.permittivity, binding.rms_height_m, config)

        per_point = []
        for i, origin in enumerate(evaluate):
            gather = NextEventGather(
                geometry=geometry,
                sources=sources,
                rng=np.random.default_rng(args.seed + 1000 + i),
                samples=args.connections,
                max_order=args.max_bounces,
            )
            point = tracer.trace(origin, models, ground_z_m=datum.z_m, seed=args.seed + i, gather=gather)
            bounced = gather.chi_bounce()
            total = float(direct[i]) + bounced
            per_point.append(
                {
                    "origin": [float(v) for v in origin],
                    "direct": float(direct[i]),
                    "bounced": bounced,
                    "surplus": total / direct[i] if direct[i] > 0.0 else float("nan"),
                    "surplus_db": (10.0 * np.log10(total / direct[i]) if direct[i] > 0.0 else float("nan")),
                    "by_order": [float(v) for v in gather.chi_by_order()],
                    "visible_fraction": float(seen[i]),
                    "sky_fraction": point.sky_fraction,
                    "mean_bounces": point.mean_bounces,
                    "escape_chi": {name: point.susceptibility[name] for name in models},
                    "escape_chi_direct": {name: point.susceptibility_direct[name] for name in models},
                    "connections": gather.connections,
                    "clear_fraction": gather.cleared / max(gather.connections, 1),
                }
            )

        surplus_db = np.array([p["surplus_db"] for p in per_point])
        # The escape estimator's own surplus, as the same ratio, so the two
        # constructions are compared on a quantity neither of them normalises.
        escape_db = []
        for p in per_point:
            whole = p["escape_chi"]["rooftop"]
            line = p["escape_chi_direct"]["rooftop"]
            escape_db.append(10.0 * np.log10(whole / line) if line > 0.0 else float("nan"))
        escape_db = np.array(escape_db)

        print(
            f"{site:22s} sites {len(sources):6d}  visible {np.median([p['visible_fraction'] for p in per_point]):.3f}  "
            f"surplus {np.median(surplus_db):+.2f} dB  "
            f"(5th {np.percentile(surplus_db, 5):+.2f}, 95th {np.percentile(surplus_db, 95):+.2f})  "
            f"escape surplus {np.nanmedian(escape_db):+.2f} dB  "
            f"{time.perf_counter() - started:.0f} s"
        )
        rows.append(
            {
                "site": site,
                "crop_radius_m": args.crop_m,
                "mesh": str(mesh.relative_to(ROOT)),
                "sources": sources.as_dict(),
                "ground_datum_m": datum.z_m,
                "rays": args.rays,
                "max_bounces": args.max_bounces,
                "held_out": int(evaluate.shape[0]),
                "clutter": clutter_report,
                "surplus_db_median": float(np.median(surplus_db)),
                "surplus_db_p5": float(np.percentile(surplus_db, 5)),
                "surplus_db_p95": float(np.percentile(surplus_db, 95)),
                "escape_surplus_db_median": float(np.nanmedian(escape_db)),
                "per_point": per_point,
                "seconds": time.perf_counter() - started,
            }
        )

    payload = {
        "question": "how much more a pedestrian gets than the rooftops they can see would give on their own",
        "estimator": "next event estimation onto an explicit skyline source set",
        "normalisation": "the line of sight term is 1, so antenna count, transmit power and the 4 pi all cancel",
        "note": "builders and evaluation standpoints are disjoint",
        "rows": rows,
    }
    path = out_dir / f"{args.tag}_{args.crop_m}m.json"
    path.write_text(json.dumps(payload, indent=1))
    print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
