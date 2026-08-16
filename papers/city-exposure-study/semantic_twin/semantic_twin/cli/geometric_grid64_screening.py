"""Write the authenticated ten-site, 64-point geometric screening report."""

from __future__ import annotations

import argparse
from pathlib import Path

from semantic_twin.report.geometric_grid_screening import (
    CampaignInput,
    write_geometric_grid64_screening,
)
from semantic_twin.report.roofline_campaign_comparison import CampaignComparisonError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--campaign",
        nargs=2,
        action="append",
        metavar=("SITE", "CAMPAIGN_DIR"),
        required=True,
        help="repeat for all ten completed site campaigns",
    )
    parser.add_argument("--output", type=Path, required=True, help="output path prefix without an extension")
    return parser


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    return _parser().parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Validate inputs and write 64-point screening artifacts."""
    parser = _parser()
    parsed = parser.parse_args(argv)
    try:
        inputs = [CampaignInput(site, Path(directory)) for site, directory in parsed.campaign]
        artifacts = write_geometric_grid64_screening(inputs, parsed.output)
    except (CampaignComparisonError, OSError, ValueError) as exc:
        parser.error(str(exc))
    print("wrote " + ", ".join(str(path) for path in artifacts.__dict__.values()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["arguments", "main"]
