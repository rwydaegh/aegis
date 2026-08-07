"""Run next-event exposure against explicit rooftop source points.

The study implementation lives in
:mod:`semantic_twin.exposure.next_event_study`.  This module owns the command
line parser and the small adapter from parsed arguments to its typed config.
The module-level ``run_next_event_study`` name is deliberately patchable for
tests and for callers that used the historical runner as an integration hook.
"""

from __future__ import annotations

import argparse

from semantic_twin.exposure.next_event_study import NextEventStudyConfig, run_next_event_study
from semantic_twin.illumination import SITE_LIFT_M


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse the options accepted by the historical next-event runner."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sites", nargs="*", default=["korenmarkt", "brussels_grandplace"])
    parser.add_argument("--crop-m", type=int, default=250)
    parser.add_argument("--rays", type=int, default=200_000)
    parser.add_argument("--builders", type=int, default=128)
    parser.add_argument("--held-out", type=int, default=16)
    parser.add_argument("--azimuths", type=int, default=1440)
    parser.add_argument("--elevations", type=int, default=600)
    parser.add_argument("--cell-m", type=float, default=1.0)
    parser.add_argument("--dims", type=int, choices=[2, 3], default=3)
    parser.add_argument("--site-lift-m", type=float, default=SITE_LIFT_M)
    parser.add_argument("--connections", type=int, default=1, help="sites connected per path vertex")
    parser.add_argument("--frequency-hz", type=float, default=15.0e9)
    parser.add_argument("--max-bounces", type=int, default=3)
    parser.add_argument("--walk-radius-m", type=float, default=90.0)
    parser.add_argument("--head-height-m", type=float, default=1.5)
    parser.add_argument("--walk", choices=["route", "grid"], default="route")
    parser.add_argument(
        "--walk-path",
        choices=["links", "street", "closest"],
        default="links",
        help="links walks the capture path, street asks Google Routes, closest measures both and keeps the nearer",
    )
    parser.add_argument("--walk-stride-m", type=float, default=6.0)
    parser.add_argument(
        "--drop-clutter",
        action="store_true",
        help="keep sites off the tips the panoramas call a sign, a pole or a canopy",
    )
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--variant", default="llvm_ad_rgb")
    parser.add_argument("--transport-kernel", choices=["numpy", "drjit"], default="numpy")
    parser.add_argument("--launch-sampling", choices=["iid", "rotated_fibonacci"], default="iid")
    parser.add_argument("--specular-order", type=int, choices=[0, 1], default=1)
    parser.add_argument("--tag", default="next_event")
    return parser.parse_args(argv)


def config_from_arguments(args: argparse.Namespace) -> NextEventStudyConfig:
    """Build the typed study configuration from parsed command arguments."""
    return NextEventStudyConfig(
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
        transport_kernel=args.transport_kernel,
        launch_sampling=args.launch_sampling,
        specular_order=args.specular_order,
        tag=args.tag,
    )


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, construct a config, and run the study."""
    run_next_event_study(config_from_arguments(arguments(argv)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
