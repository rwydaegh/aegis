"""Write the batch files and exact prompt for material VLM calls."""

from __future__ import annotations

import argparse
import pathlib

from semantic_twin.vision.vlm_batches import make_vlm_batches


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=pathlib.Path, default=pathlib.Path("outputs/material_vlm"))
    parser.add_argument("--draws", type=int, default=2)
    parser.add_argument("--batches", type=int, default=6)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    make_vlm_batches(args.out, draws=args.draws, batches=args.batches, seed=args.seed)


if __name__ == "__main__":
    main()
