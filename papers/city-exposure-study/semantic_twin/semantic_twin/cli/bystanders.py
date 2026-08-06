"""Run the two-arm bystander blockage study."""

from __future__ import annotations

import argparse
import pathlib

from semantic_twin.exposure.bystander_study import (
    STATURE_MODES,
    BystanderStudyConfig,
    run_bystander_study,
)
from semantic_twin.propagation.bystander_geometry import (
    CLOTHING_RMS_HEIGHT_M,
    DENSITY_LADDER,
)
from semantic_twin.transport.tracer import DEFAULT_MAX_BOUNCES


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    root = pathlib.Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Bystander blockage study, both arms.")
    parser.add_argument("--locations", type=int, default=12)
    parser.add_argument("--realisations", type=int, default=3)
    parser.add_argument("--rays", type=int, default=200_000)
    parser.add_argument("--max-bounces", type=int, default=DEFAULT_MAX_BOUNCES)
    parser.add_argument("--local-cells", type=int, default=512)
    parser.add_argument("--frequency-ghz", type=float, default=15.0)
    parser.add_argument("--crop-m", type=int, default=250)
    parser.add_argument("--site", default="korenmarkt")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--tag", default="korenmarkt")
    parser.add_argument("--target-faces", type=int, default=600)
    parser.add_argument("--max-radius-m", type=float, default=30.0)
    parser.add_argument("--mean-free-paths", type=float, default=float("inf"))
    parser.add_argument("--clothing-rms-mm", type=float, default=CLOTHING_RMS_HEIGHT_M * 1e3)
    parser.add_argument(
        "--body-absorber",
        action="store_true",
        help="make the bodies index matched absorbers, the control that removes re-illumination",
    )
    parser.add_argument("--densities", type=float, nargs="+", default=list(DENSITY_LADDER))
    parser.add_argument("--stature-modes", nargs="+", default=list(STATURE_MODES), choices=list(STATURE_MODES))
    parser.add_argument("--bodies", default=str(root / "outputs" / "korenmarkt_dynamic_bodies"))
    parser.add_argument("--output", default=str(root / "outputs" / "bystander_study"))
    parser.add_argument("--variant", default="llvm_ad_rgb")
    parser.add_argument("--report", metavar="STEM", default=None, help="resummarise an existing run")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="keep the standpoints already fully traced, drop the partial one, and carry on",
    )
    parser.add_argument(
        "--noise-floor",
        action="store_true",
        help="measure how large a dB shift the estimator's own variance can fake, then stop",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    run_bystander_study(BystanderStudyConfig(**vars(arguments(argv))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
