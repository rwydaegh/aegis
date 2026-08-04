"""Run next-event exposure against explicit rooftop source points."""

from __future__ import annotations

import argparse

from semantic_twin.exposure.next_event_study import NextEventStudyConfig, run_next_event_study
from semantic_twin.illumination import SITE_LIFT_M


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
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
    args = ap.parse_args(argv)
    run_next_event_study(
        NextEventStudyConfig(
            sites=tuple(args.sites),
            crop_m=args.crop_m,
            rays=args.rays,
            builders=args.builders,
            held_out=args.held_out,
            azimuths=args.azimuths,
            elevations=args.elevations,
            cell_m=args.cell_m,
            dims=args.dims,
            site_lift_m=args.site_lift_m,
            connections=args.connections,
            frequency_hz=args.frequency_hz,
            max_bounces=args.max_bounces,
            walk_radius_m=args.walk_radius_m,
            head_height_m=args.head_height_m,
            walk=args.walk,
            walk_path=args.walk_path,
            walk_stride_m=args.walk_stride_m,
            drop_clutter=args.drop_clutter,
            seed=args.seed,
            variant=args.variant,
            tag=args.tag,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
