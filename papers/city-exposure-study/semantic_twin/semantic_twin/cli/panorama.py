"""Segment one panorama and record the dense and prompted evidence."""

from __future__ import annotations

import argparse
import pathlib

from semantic_twin.vision.dense import (
    DEFAULT_GATE_MIN_PIXELS,
    DEFAULT_INFERENCE_SIZE,
    MODEL,
    PRODUCTION_REVISION,
)
from semantic_twin.vision.panorama import PanoramaRunConfig, run
from semantic_twin.vision.prompted import (
    PRODUCTION_REPOSITORY_COMMIT as SAM3_PRODUCTION_REPOSITORY_COMMIT,
)
from semantic_twin.vision.prompted import PRODUCTION_REVISION as SAM3_PRODUCTION_REVISION
from semantic_twin.vision.views import DEFAULT_VIEW_SIZE


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panorama", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--model", default=MODEL)
    parser.add_argument(
        "--dense-revision",
        help=(
            "Hugging Face revision for Mask2Former. Production requires the immutable "
            f"reviewed commit {PRODUCTION_REVISION}."
        ),
    )
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument(
        "--backend",
        choices=("mask2former", "hybrid"),
        default="mask2former",
        help="hybrid adds the SAM 3 concept pass and resolves the RF material axis.",
    )
    parser.add_argument("--concepts", type=pathlib.Path, help="concept catalogue, required by --backend hybrid")
    parser.add_argument("--view-size", type=int, default=DEFAULT_VIEW_SIZE)
    parser.add_argument(
        "--inference-size",
        type=int,
        default=DEFAULT_INFERENCE_SIZE,
        help="Square input the segmenter actually sees, instead of the checkpoint processor's 384.",
    )
    parser.add_argument("--concept-resolution", type=int, default=1008)
    parser.add_argument("--concept-threshold", type=float, default=0.35)
    parser.add_argument("--prompt-batch", type=int, default=32)
    parser.add_argument(
        "--sam-revision",
        help=f"Hugging Face revision for facebook/sam3. Production requires {SAM3_PRODUCTION_REVISION}.",
    )
    parser.add_argument(
        "--sam-repository-commit",
        help=f"installed SAM 3 source commit. Production requires {SAM3_PRODUCTION_REPOSITORY_COMMIT}.",
    )
    parser.add_argument(
        "--production",
        action="store_true",
        help="require the reviewed immutable revisions for every model used by the selected backend",
    )
    parser.add_argument("--gate-min-pixels", type=int, default=DEFAULT_GATE_MIN_PIXELS)
    parser.add_argument("--output-width", type=int, default=8192)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    run(PanoramaRunConfig(**vars(arguments(argv))))


if __name__ == "__main__":
    main()
