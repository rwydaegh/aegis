"""CLI for authenticated multicity roofline campaign result exports."""

from __future__ import annotations

import argparse
from pathlib import Path

from semantic_twin.report.multicity_roofline_results import CampaignInput, write_multicity_results
from semantic_twin.report.roofline_campaign_comparison import CampaignComparisonError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--city",
        nargs=2,
        action="append",
        metavar=("NAME", "CAMPAIGN_DIR"),
        required=True,
        help="repeat for each completed single-IID city campaign",
    )
    parser.add_argument("--output", type=Path, required=True, help="output path prefix without an extension")
    parser.add_argument(
        "--looks",
        help="optional comma-separated common convergence looks, otherwise use each campaign's declared looks",
    )
    return parser


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    return _parser().parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Validate inputs and write multicity result artifacts."""
    parser = _parser()
    parsed = parser.parse_args(argv)
    try:
        looks = None
        if parsed.looks is not None:
            looks = tuple(int(value.strip()) for value in parsed.looks.split(",") if value.strip())
        inputs = [CampaignInput(city, Path(directory)) for city, directory in parsed.city]
        artifacts = write_multicity_results(inputs, parsed.output, looks=looks)
    except (CampaignComparisonError, OSError, ValueError) as exc:
        parser.error(str(exc))
    print("wrote " + ", ".join(str(path) for path in artifacts.__dict__.values()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["arguments", "main"]
