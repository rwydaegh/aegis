"""Screen candidate sites on Street View metadata before acquiring tiles."""

from __future__ import annotations

import argparse
import pathlib
import sys

from semantic_twin import paths
from semantic_twin.screening import DEFAULT_MAX_PANORAMAS, DEFAULT_SCREEN_RADIUS_M
from semantic_twin.screening_workflow import screen_candidates


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=pathlib.Path, default=paths.output("city_screening"))
    parser.add_argument("--radius-m", type=float, default=DEFAULT_SCREEN_RADIUS_M)
    parser.add_argument("--max-panoramas", type=int, default=DEFAULT_MAX_PANORAMAS)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--only", nargs="*", default=None, help="Screen only these candidate keys")
    args = parser.parse_args()
    document = screen_candidates(
        args.out,
        radius_m=args.radius_m,
        max_panoramas=args.max_panoramas,
        workers=args.workers,
        only=args.only,
    )
    if document is None:
        print("No candidate matched --only", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
