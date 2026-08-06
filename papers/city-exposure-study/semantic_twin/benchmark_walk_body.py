"""Run the diagnostic separate-versus-batched body coupling benchmark."""

from __future__ import annotations

import pathlib

from semantic_twin.cli.body_benchmark import (
    arguments as _arguments,
    main as _main,
    run as _run,
)


def arguments(argv: list[str] | None = None):
    """Keep the historical script parser available to diagnostic callers."""
    return _arguments(argv)


def run(args):
    """Keep the historical script entry point while delegating the work."""
    return _run(args, benchmark_source=pathlib.Path(__file__))


def main(argv: list[str] | None = None) -> int:
    return _main(argv, benchmark_source=pathlib.Path(__file__))


if __name__ == "__main__":
    raise SystemExit(main())
