"""Command-line entry point for the illumination sensitivity study."""

import argparse

from semantic_twin.illumination import sensitivity_study as study
from semantic_twin.illumination.sensitivity_study import LOCATIONS, RAYS, run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=study.__doc__)
    parser.add_argument("--harvest", action="store_true")
    parser.add_argument("--analyse", action="store_true")
    parser.add_argument("--figures", action="store_true")
    parser.add_argument("--sites", nargs="*", default=None)
    parser.add_argument("--locations", type=int, default=LOCATIONS)
    parser.add_argument("--rays", type=int, default=RAYS)
    parser.add_argument(
        "--stride",
        type=int,
        default=1,
        help="trace every nth published standpoint, so every harvested one stays checkable",
    )
    args = parser.parse_args(argv)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
