"""Run prompted SAM 3 concept segmentation over prepared views."""

from __future__ import annotations

import argparse
import pathlib

from semantic_twin.vision.prompted import (
    DEFAULT_PROMPT_BATCH,
    DEFAULT_RESOLUTION,
    DEFAULT_THRESHOLD,
    PromptedRunConfig,
    run_prompted,
)


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--views", type=pathlib.Path, required=True)
    parser.add_argument("--concepts", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--resolution", type=int, default=DEFAULT_RESOLUTION)
    parser.add_argument("--prompt-batch", type=int, default=DEFAULT_PROMPT_BATCH)
    parser.add_argument("--limit-views", type=int)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    run_prompted(PromptedRunConfig(**vars(arguments(argv))))


if __name__ == "__main__":
    main()
