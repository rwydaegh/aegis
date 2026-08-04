"""Fetch a spatially spread set of panoramas for one screened site."""

from __future__ import annotations

import argparse
import pathlib

from semantic_twin import paths
from semantic_twin.acquire.site_panoramas import FetchOptions, fetch_site_panoramas


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", type=pathlib.Path, required=True)
    parser.add_argument("--count", type=int, default=14)
    parser.add_argument("--zoom", type=int, choices=range(0, 6), default=5)
    parser.add_argument("--screening", type=pathlib.Path, default=paths.screening())
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--out", type=pathlib.Path)
    parser.add_argument(
        "--walk-date",
        help="capture date to walk, as YYYY-MM, overriding the screener's largest-component choice",
    )
    parser.add_argument(
        "--open-sky-m",
        type=float,
        default=2.5,
        help=(
            "drop a candidate whose topmost tile surface sits more than this far above the scene "
            "ground datum, which is what an arcade or a concourse looks like from above. 0 disables it."
        ),
    )
    parser.add_argument(
        "--along-links",
        action="store_true",
        help=(
            "take consecutive panoramas along the capture instead of spreading them out. Use this "
            "when the cameras are the walk rather than the evidence: it gives the capture's own "
            "spacing, a few metres, where spreading gives tens of metres."
        ),
    )
    args = parser.parse_args()
    manifest = fetch_site_panoramas(
        args.scene,
        FetchOptions(
            count=args.count,
            zoom=args.zoom,
            screening=args.screening,
            workers=args.workers,
            out_root=args.out,
            walk_date=args.walk_date,
            open_sky_m=args.open_sky_m,
            along_links=args.along_links,
        ),
    )
    selection = manifest["selection"]
    print(
        f"[done] {manifest['site']}: {len(manifest['panorama_dirs'])} panoramas, "
        f"minimum separation {selection['minimum_separation_m']} m, "
        f"{selection['walk_panoramas_dropped_as_roofed']} candidates dropped as roofed, "
        f"about {manifest['approximate_requests']} requests"
    )


if __name__ == "__main__":
    main()
