"""Write a scene config for a screened site, with the ground datum measured."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

from semantic_twin import paths
from semantic_twin.scene.site_config_build import DEFAULT_SCREENING, build


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", required=True)
    parser.add_argument("--crop-m", type=int, default=130)
    parser.add_argument("--screening", type=pathlib.Path, default=DEFAULT_SCREENING)
    parser.add_argument("--radius-m", type=float, default=80.0)
    parser.add_argument(
        "--walk-date",
        help="capture date to record, as YYYY-MM, overriding the screener's largest-component choice",
    )
    parser.add_argument("--out", type=pathlib.Path)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
    scene = build(
        args.site,
        crop_m=args.crop_m,
        screening=args.screening,
        walk_date=args.walk_date,
        radius_m=args.radius_m,
    )
    text = json.dumps(scene, indent=2) + "\n"
    if args.dry_run:
        print(text)
        return 0
    path = args.out or paths.site_config(args.site)
    path.write_text(text)
    print(
        f"[config] {args.site}: camera_ground_z_m={scene['camera_ground_z_m']:.3f} m, "
        f"anchor surface {scene['camera_ground_z_note'].split('the anchor itself is ')[1].split(' m.')[0]} m, "
        f"walk {scene['walk_selection']['walk_date']} -> {path}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
