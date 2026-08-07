"""Write publication figures and exports for paired roofline campaigns.

The validated report and figure-writing implementation lives in
:mod:`semantic_twin.report.roofline_result_figures`.  This module owns only
command-line parsing and dispatch.

Example::

    python -m semantic_twin.cli.roofline_result_figures \
        --city korenmarkt outputs/korenmarkt_iid outputs/korenmarkt_fibonacci \
        --city prague outputs/prague_iid outputs/prague_fibonacci \
        --output outputs/paper/roofline_results
"""

from __future__ import annotations

import argparse
from pathlib import Path

from semantic_twin.report.roofline_result_figures import (
    DEFAULT_LOOKS,
    CampaignPair,
    write_publication_results,
)
from semantic_twin.report.roofline_campaign_comparison import CampaignComparisonError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--city",
        nargs=3,
        action="append",
        metavar=("NAME", "IID_DIRECTORY", "FIBONACCI_DIRECTORY"),
        required=True,
        help="city name and its paired IID and rotated-Fibonacci directories (repeatable)",
    )
    parser.add_argument("--output", type=Path, required=True, help="output path stem")
    parser.add_argument("--looks", default=",".join(str(value) for value in DEFAULT_LOOKS))
    parser.add_argument("--final-look", type=int, default=None)
    return parser


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for publication result generation."""
    return _parser().parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and write publication figures and machine-readable exports."""
    parser = _parser()
    parsed = parser.parse_args(argv)
    try:
        looks = tuple(int(value) for value in parsed.looks.split(",") if value.strip())
        campaigns = [CampaignPair(name, Path(iid), Path(fibonacci)) for name, iid, fibonacci in parsed.city]
        artifacts = write_publication_results(
            campaigns,
            parsed.output,
            looks=looks,
            final_look=parsed.final_look,
        )
    except (CampaignComparisonError, OSError, ValueError) as exc:
        parser.error(str(exc))
    print("wrote " + ", ".join(str(path) for path in artifacts.__dict__.values()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["arguments", "main"]
