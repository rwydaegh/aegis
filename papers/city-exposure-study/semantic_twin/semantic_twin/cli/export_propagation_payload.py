"""Trace and export the payload for a propagation walkthrough blend."""

from __future__ import annotations

import argparse
import pathlib
import sys

from semantic_twin.exposure.study import OUTPUT as EXPOSURE_OUTPUT
from semantic_twin.viz.blender import export_contract
from semantic_twin.viz.blender.export_contract import (
    DEFAULT_DRAW_RADIUS_M,
    DEFAULT_MAX_BOUNCES,
    OUTPUT,
    ProductionFiles,
    export,
    stamp_bundle_identity,
    production_files,
    verify_bundle_identity,
)

__all__ = [
    "DEFAULT_DRAW_RADIUS_M",
    "DEFAULT_MAX_BOUNCES",
    "EXPOSURE_OUTPUT",
    "OUTPUT",
    "ProductionFiles",
    "arguments",
    "export",
    "main",
    "production_files",
    "stamp_bundle_identity",
    "verify_bundle_identity",
]


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse the payload exporter options, preserving the script defaults."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", default="korenmarkt")
    parser.add_argument("--crop-m", type=int, default=250, help="Traced crop radius, the converged one")
    parser.add_argument("--draw-radius-m", type=float, default=DEFAULT_DRAW_RADIUS_M)
    parser.add_argument("--locations", type=int, default=60)
    parser.add_argument("--walk-radius-m", type=float, default=60.0)
    parser.add_argument(
        "--walk",
        choices=["route", "grid"],
        default="route",
        help="route stands where the cameras stood, grid scatters heads over a disc",
    )
    parser.add_argument(
        "--walk-path",
        choices=["links", "street", "closest"],
        default="links",
        help="links walks the capture path, street asks Google Routes, closest measures both and keeps the nearer",
    )
    parser.add_argument(
        "--walk-stride-m",
        type=float,
        default=6.0,
        help="extra standpoints this far apart along the street between cameras, 0 for cameras only",
    )
    parser.add_argument("--paths", type=int, default=1200, help="Ray polylines kept at the hero location")
    parser.add_argument("--sources", type=int, default=400, help="Illumination source markers per model")
    parser.add_argument(
        "--nee-paths",
        type=int,
        default=16,
        help="Recorded paths drawn with their next event connections. A few dozen stays readable",
    )
    parser.add_argument("--rays", type=int, default=200_000)
    parser.add_argument("--local-cells", type=int, default=512)
    parser.add_argument("--max-bounces", type=int, default=DEFAULT_MAX_BOUNCES)
    parser.add_argument("--frequency-hz", type=float, default=15.0e9)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--variant", default="llvm_ad_rgb")
    parser.add_argument("--out", type=pathlib.Path, default=OUTPUT)
    parser.add_argument(
        "--production-stem",
        type=pathlib.Path,
        help=(
            "Load one production exposure run instead of retracing its walk. A bare stem is resolved "
            "under outputs/exposure_korenmarkt; a path is used in place."
        ),
    )
    parser.add_argument("--production-locations", type=pathlib.Path, help="Exact production locations JSONL")
    parser.add_argument("--production-spectra", type=pathlib.Path, help="Exact production spectra NPZ")
    parser.add_argument("--production-manifest", type=pathlib.Path, help="Exact production manifest JSON")
    parser.add_argument(
        "--no-evidence",
        dest="evidence",
        action="store_false",
        help="Skip the image side layers and export the traced ones alone",
    )
    parser.add_argument(
        "--evidence-only",
        action="store_true",
        help="Reuse the traced half of an existing payload and rebuild only the image side layers",
    )
    parser.add_argument(
        "--rim-only",
        action="store_true",
        help="Keep an existing payload whole and measure the facade tip rim into it",
    )
    parser.add_argument(
        "--depth-stride",
        type=int,
        default=4,
        help="Pixel stride of the two depth clouds. Four keeps a 1024 crop at 256 by 256",
    )
    args = parser.parse_args(argv)
    try:
        args.production_files = production_files(
            stem=args.production_stem,
            locations=args.production_locations,
            spectra=args.production_spectra,
            manifest=args.production_manifest,
            default_directory=EXPOSURE_OUTPUT,
        )
    except ValueError as error:
        parser.error(str(error))
    if args.production_files is not None and args.rim_only:
        parser.error("production input cannot be combined with --rim-only")
    return args


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and invoke the package-owned exporter."""
    return export_contract.export(arguments(argv))


if __name__ == "__main__":
    sys.exit(main())
