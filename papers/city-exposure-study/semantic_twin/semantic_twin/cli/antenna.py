"""Run the antenna illumination or steering artefact study."""

from __future__ import annotations

import argparse

from semantic_twin.propagation import antenna as antenna_domain
from semantic_twin.propagation.antenna import (
    MACRO_TILT_DEG,
    MICRO_TILT_DEG,
    AntennaStudyConfig,
    run_antenna_study,
)
from semantic_twin.transport.tracer import DEFAULT_MAX_BOUNCES


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=antenna_domain.__doc__)
    parser.add_argument("--sites", nargs="+", default=["korenmarkt"])
    parser.add_argument("--all-sites", action="store_true")
    parser.add_argument("--kernel", action="store_true", help="add the elevation kernel probes to the model set")
    parser.add_argument(
        "--artefact",
        action="store_true",
        help="measure the geometric steering reduction instead of scoring the model set",
    )
    parser.add_argument("--locations", type=int, default=80)
    parser.add_argument("--rays", type=int, default=200_000)
    parser.add_argument("--max-bounces", type=int, default=DEFAULT_MAX_BOUNCES)
    parser.add_argument("--frequency-hz", type=float, default=15.0e9)
    parser.add_argument("--crop-m", type=int, default=250)
    parser.add_argument("--walk-radius-m", type=float, default=90.0)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--grid-rotation-deg", type=float, default=0.0)
    parser.add_argument("--macro-tilt-deg", type=float, default=MACRO_TILT_DEG)
    parser.add_argument("--micro-tilt-deg", type=float, default=MICRO_TILT_DEG)
    parser.add_argument("--tag", default="antenna")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    run_antenna_study(AntennaStudyConfig(**vars(arguments(argv))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
