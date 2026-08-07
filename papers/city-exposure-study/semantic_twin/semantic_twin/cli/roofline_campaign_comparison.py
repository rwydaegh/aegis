"""Write a paired comparison report for two completed roofline campaigns.

The comparison and validation implementation lives in
:mod:`semantic_twin.report.roofline_campaign_comparison`.  This module owns
only command-line parsing and dispatch, so the report can be imported without
bringing command-line concerns into the report layer.

Example::

    python -m semantic_twin.cli.roofline_campaign_comparison \
        outputs/korenmarkt_iid outputs/korenmarkt_fibonacci \
        --output outputs/paper/korenmarkt_comparison.json
"""

from __future__ import annotations

import argparse
from pathlib import Path

from semantic_twin.report.roofline_campaign_comparison import CampaignComparisonError, write_report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iid_directory", type=Path)
    parser.add_argument("rotated_fibonacci_directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--looks", default="4,8,12,16", help="comma-separated common replica looks")
    return parser


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the paired campaign report."""
    return _parser().parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and write the paired campaign comparison report."""
    parser = _parser()
    parsed = parser.parse_args(argv)
    try:
        looks = tuple(int(value) for value in parsed.looks.split(",") if value.strip())
        write_report(parsed.iid_directory, parsed.rotated_fibonacci_directory, parsed.output, looks=looks)
    except (CampaignComparisonError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["arguments", "main"]
