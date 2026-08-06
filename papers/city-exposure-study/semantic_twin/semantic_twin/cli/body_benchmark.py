"""Command-line boundary for the diagnostic body-coupling benchmark."""

from __future__ import annotations

import argparse
import json
import pathlib

from semantic_twin.exposure.body_benchmark import (
    DEFAULT_OUTPUT,
    DEFAULT_SPECTRA,
    BodyBenchmarkConfig,
    benchmark,
    write_report,
)


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse benchmark options without constructing an AEGIS body."""
    parser = argparse.ArgumentParser(
        description="Benchmark separate and batched body coupling on stored Korenmarkt spectra."
    )
    parser.add_argument("--spectra", type=pathlib.Path, nargs="+", default=DEFAULT_SPECTRA)
    parser.add_argument("--point", type=int, default=0, help="row within each stored full-walk spectrum")
    parser.add_argument("--repeat", type=int, default=2)
    parser.add_argument("--chunk-cells", type=int, default=512)
    parser.add_argument("--output", type=pathlib.Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def config_from_args(args: argparse.Namespace) -> BodyBenchmarkConfig:
    """Build a typed benchmark configuration from parsed options."""
    return BodyBenchmarkConfig(
        spectra=tuple(args.spectra),
        point=int(args.point),
        repeat=int(args.repeat),
        chunk_cells=int(args.chunk_cells),
    )


def run(args: argparse.Namespace, *, benchmark_source: pathlib.Path | None = None) -> dict[str, object]:
    """Run one parsed benchmark command and return its report."""
    return benchmark(config_from_args(args), benchmark_source=benchmark_source)


def main(argv: list[str] | None = None, *, benchmark_source: pathlib.Path | None = None) -> int:
    """Run the benchmark, write its report, and print the result."""
    args = arguments(argv)
    report = run(args, benchmark_source=benchmark_source)
    write_report(report, args.output)
    print(json.dumps(report, indent=2, sort_keys=True))
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
