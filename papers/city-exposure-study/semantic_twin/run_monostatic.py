"""Run the co-located return study at exposure or camera standpoints."""

from __future__ import annotations

import argparse

from semantic_twin.exposure.monostatic_study import MonostaticStudyConfig, execute
from semantic_twin.exposure.study import SITES


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sites", default="korenmarkt", help="comma separated, or 'all'")
    parser.add_argument("--locations", type=int, default=80)
    parser.add_argument("--rays", type=int, default=200_000)
    parser.add_argument("--max-bounces", type=int, default=3)
    parser.add_argument("--crop-m", type=int, default=250)
    parser.add_argument("--frequency-ghz", type=float, default=15.0)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--variant", default="llvm_ad_rgb")
    parser.add_argument("--walk-radius-m", type=float, default=90.0)
    parser.add_argument("--walk-spacing-m", type=float, default=3.0)
    parser.add_argument("--tag", default="mono250")
    parser.add_argument("--evidence", action="store_true", help="carry the panorama observed mask")
    parser.add_argument("--stations", action="store_true", help="stand at the registered cameras instead")
    parser.add_argument("--visibility", action="store_true", help="score the ledger against visibility alone")
    parser.add_argument("--analyse", action="store_true")
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args(argv)
    sites = SITES if args.sites == "all" else tuple(name.strip() for name in args.sites.split(","))
    execute(
        MonostaticStudyConfig(
            sites=sites,
            locations=args.locations,
            rays=args.rays,
            max_bounces=args.max_bounces,
            crop_m=args.crop_m,
            frequency_hz=args.frequency_ghz * 1e9,
            seed=args.seed,
            variant=args.variant,
            walk_radius_m=args.walk_radius_m,
            walk_spacing_m=args.walk_spacing_m,
            tag=args.tag,
            evidence=args.evidence,
            stations=args.stations,
            visibility=args.visibility,
            analyse_only=args.analyse,
            validate_only=args.validate,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
