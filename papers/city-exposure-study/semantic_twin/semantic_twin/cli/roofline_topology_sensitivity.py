"""Write an authenticated hybrid versus first-interaction sensitivity report."""

from __future__ import annotations

import argparse
from pathlib import Path

from semantic_twin.report.roofline_campaign_comparison import CampaignComparisonError
from semantic_twin.report.roofline_topology_sensitivity import write_topology_sensitivity


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hybrid_directory", type=Path)
    parser.add_argument("first_material_interaction_directory", type=Path)
    parser.add_argument("--output", type=Path, required=True, help="output path prefix without an extension")
    return parser


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    return _parser().parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Validate the topology pair and write result artifacts."""
    parser = _parser()
    parsed = parser.parse_args(argv)
    try:
        artifacts = write_topology_sensitivity(
            parsed.hybrid_directory,
            parsed.first_material_interaction_directory,
            parsed.output,
        )
    except (CampaignComparisonError, OSError, ValueError) as exc:
        parser.error(str(exc))
    print("wrote " + ", ".join(str(path) for path in artifacts.__dict__.values()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["arguments", "main"]
