"""Report an atlas evidence layer versus geometric fallback campaign pair."""

from __future__ import annotations

import argparse
from pathlib import Path

from semantic_twin.report.material_evidence_ablation import (
    MaterialEvidenceAblationError,
    write_material_evidence_ablation,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("atlas_directory", type=Path)
    parser.add_argument("geometric_directory", type=Path)
    parser.add_argument("--output", type=Path, required=True, help="Dedicated report output directory")
    return parser


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    return _parser().parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Validate the pair and write the report artifacts."""
    parser = _parser()
    parsed = parser.parse_args(argv)
    try:
        artifacts = write_material_evidence_ablation(
            parsed.atlas_directory,
            parsed.geometric_directory,
            parsed.output,
        )
    except MaterialEvidenceAblationError as exc:
        parser.error(str(exc))
    print(
        "wrote "
        + ", ".join(
            str(path) for path in (artifacts.json, artifacts.csv, artifacts.pdf, artifacts.png, artifacts.manifest)
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["arguments", "main"]
