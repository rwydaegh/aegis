"""Summarise the image evidence available at each study site."""

from __future__ import annotations

import argparse
import pathlib

from semantic_twin.report.evidence_coverage import SCRIPT_DIR, EvidenceCoverageConfig, execute


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crop-m", type=int, nargs="+", default=[130, 250])
    parser.add_argument("--max-residual-deg", type=float, default=4.0)
    parser.add_argument("--max-sky-conflict", type=float, default=0.5)
    parser.add_argument("--min-conflict-range-m", type=float, default=2.0)
    parser.add_argument("--out", type=pathlib.Path, default=SCRIPT_DIR / "outputs" / "evidence_coverage.json")
    parser.add_argument("--into", type=pathlib.Path, default=SCRIPT_DIR / "docs" / "COVERAGE.md")
    parser.add_argument("--no-write", action="store_true", help="print the table and touch nothing")
    parser.add_argument("--measure-semantic", action="store_true", help="refresh cached semantic coverage")
    args = parser.parse_args(argv)
    return execute(
        EvidenceCoverageConfig(
            crops_m=tuple(args.crop_m),
            max_residual_deg=args.max_residual_deg,
            max_sky_conflict=args.max_sky_conflict,
            min_conflict_range_m=args.min_conflict_range_m,
            out=args.out,
            into=args.into,
            write=not args.no_write,
            measure_semantic=args.measure_semantic,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
