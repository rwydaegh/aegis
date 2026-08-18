"""Write authenticated ray-reached semantic-evidence coverage artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from semantic_twin.report.ray_reached_evidence_coverage import (
    RayReachedEvidenceCoverageError,
    write_ray_reached_evidence_coverage,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("replay_result", type=Path, help="authenticated compact replay JSON or its artifact directory")
    parser.add_argument("--output", type=Path, required=True, help="dedicated report output directory")
    return parser


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    return _parser().parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Validate replay provenance and write JSON, CSV, PDF, PNG, and manifest."""
    parser = _parser()
    parsed = parser.parse_args(argv)
    try:
        artifacts = write_ray_reached_evidence_coverage(parsed.replay_result, parsed.output)
    except (RayReachedEvidenceCoverageError, OSError) as error:
        parser.error(str(error))
    print("wrote " + ", ".join(str(path) for path in artifacts.__dict__.values()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["arguments", "main"]
