"""Re-run skyline registration for a site against a named support mesh."""

from __future__ import annotations

import argparse
import pathlib

from semantic_twin.vision.registration_repair import RepairOptions, reregister_site


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--site", required=True)
    parser.add_argument("--crop-m", type=int, default=250)
    parser.add_argument("--workers", type=int, default=1, help="independent station registrations to run in parallel")
    parser.add_argument("--station", action="append", help="Limit to named station directories")
    parser.add_argument(
        "--cohort-dir",
        type=pathlib.Path,
        help=(
            "Restrict station discovery to this explicitly selected panorama cohort. "
            "Relative paths are resolved from the study root."
        ),
    )
    parser.add_argument(
        "--semantics-dirname",
        default="semantics",
        help="Semantic evidence directory beneath each selected panorama station",
    )
    parser.add_argument(
        "--dz-bounds",
        type=float,
        nargs=2,
        help=(
            "Vertical search bound in metres around the measured camera altitude, passed through to "
            "vision.align. The default there is -3 3, which permits a camera half a metre under its own "
            "pavement. Every one of the 25 poses the sky conflict test calls inside the geometry has dived "
            "more than 1.5 m and the median is 2.97 m, against a median of 0.58 m among the 41 admitted "
            "poses, so -1.5 3 keeps the rig at least a metre above the ground it is standing on and "
            "excludes no pose that was ever any good."
        ),
    )
    parser.add_argument("--dry-run", action="store_true", help="Print the commands and change nothing")
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Overwrite the existing pose without keeping a copy. Off by default and rarely what you want.",
    )
    args = parser.parse_args()
    reregister_site(
        RepairOptions(
            site=args.site,
            crop_m=args.crop_m,
            station_names=tuple(args.station) if args.station else None,
            cohort_dir=args.cohort_dir,
            semantics_dirname=args.semantics_dirname,
            dz_bounds=tuple(args.dz_bounds) if args.dz_bounds else None,
            dry_run=args.dry_run,
            no_backup=args.no_backup,
            workers=args.workers,
        )
    )


if __name__ == "__main__":
    main()
