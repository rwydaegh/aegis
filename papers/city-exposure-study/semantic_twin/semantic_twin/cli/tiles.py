"""Download Google Photorealistic 3D Tiles for one site, from the command line.

The traversal, region of interest and cache live in
:mod:`semantic_twin.acquire.tiles`. This module owns the command-line boundary.

The historical ``download_inhouse_tiles.py`` filename remains a compatibility
entry point because acquisition records and mesh documentation still reference
it. New invocations can use this module directly::

    python -m semantic_twin.cli.tiles \
      --lat 51.0550 --lon 3.7220 --radius-m 100 \
      --geometric-error-cutoff-m 0 --out /tmp/korenmarkt-tiles

Set ``GOOGLE_MAPS_API_KEY`` (preferred) or ``GOOGLE_API_KEY`` first. A zero
geometric-error cutoff means descend to the deepest available leaves. Positive
cutoffs stop at a tile whose geometric error is at or below the requested value.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys

from semantic_twin.acquire.tiles import (
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_REQUESTS,
    DEFAULT_VERTICAL_HALF_EXTENT_M,
    MAX_RADIUS_M,
    DownloadLimitExceeded,
    TilesAcquireConfig,
    api_key,
    acquire_tiles,
)


def positive_int(value: str) -> int:
    result = int(value)
    if result <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return result


def finite_float(value: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise argparse.ArgumentTypeError("must be finite")
    return result


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lat", type=finite_float, required=True, help="region centre latitude in WGS84 degrees")
    parser.add_argument("--lon", type=finite_float, required=True, help="region centre longitude in WGS84 degrees")
    parser.add_argument(
        "--radius-m",
        "--radius",
        dest="radius_m",
        type=finite_float,
        required=True,
        help=f"Horizontal region radius in metres, at most {MAX_RADIUS_M:g}",
    )
    parser.add_argument(
        "--vertical-half-extent-m",
        type=finite_float,
        default=DEFAULT_VERTICAL_HALF_EXTENT_M,
        help=(
            "Half height of the region cylinder about the ellipsoid in metres "
            f"(default: {DEFAULT_VERTICAL_HALF_EXTENT_M:g}). Raise it above 3 km terrain"
        ),
    )
    parser.add_argument(
        "--site-height-m",
        type=finite_float,
        default=None,
        help=(
            "The site's ellipsoidal ground height, when it is known. Checked against the vertical band, "
            "so a high site is refused with its own number rather than returning no tiles"
        ),
    )
    parser.add_argument(
        "--geometric-error-cutoff-m",
        "--cutoff",
        dest="geometric_error_cutoff_m",
        type=finite_float,
        default=0.0,
        help="Stop at this geometric error in metres. Zero downloads deepest leaves (default: 0)",
    )
    parser.add_argument(
        "--max-requests",
        type=positive_int,
        default=DEFAULT_MAX_REQUESTS,
        help=f"Hard HTTP request cap (default: {DEFAULT_MAX_REQUESTS})",
    )
    parser.add_argument(
        "--max-bytes",
        type=positive_int,
        default=DEFAULT_MAX_BYTES,
        help=f"Hard aggregate response-byte cap (default: {DEFAULT_MAX_BYTES})",
    )
    parser.add_argument("--out", type=pathlib.Path, required=True, help="Output directory for GLBs and manifest.json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
    key = api_key()
    if not key:
        print("Set GOOGLE_MAPS_API_KEY or GOOGLE_API_KEY", file=sys.stderr)
        return 2
    try:
        manifest = acquire_tiles(
            TilesAcquireConfig(
                api_key=key,
                lat=args.lat,
                lon=args.lon,
                radius_m=args.radius_m,
                geometric_error_cutoff_m=args.geometric_error_cutoff_m,
                out=args.out,
                vertical_half_extent_m=args.vertical_half_extent_m,
                site_height_m=args.site_height_m,
                max_requests=args.max_requests,
                max_bytes=args.max_bytes,
            )
        )
    except (DownloadLimitExceeded, RuntimeError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"Download failed: {exc}", file=sys.stderr)
        return 1

    print(
        f"[done] {len(manifest['tiles'])} tiles, {manifest['reused_from_disk']} kept from a previous run, "
        f"{manifest['requests']} requests, {manifest['total_bytes'] / 1e6:.1f} MB "
        f"-> {args.out / 'manifest.json'}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
