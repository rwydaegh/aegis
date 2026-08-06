"""Score material VLM evidence against the fixed prior it would replace."""

from __future__ import annotations

import argparse
import pathlib

from semantic_twin.vision.material_vlm_study import analyse_material_vlm

ROOT = pathlib.Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=pathlib.Path, default=ROOT / "outputs" / "material_vlm")
    parser.add_argument("--frequency-ghz", type=float, default=15.0)
    args = parser.parse_args()
    analyse_material_vlm(args.out, args.frequency_ghz)


if __name__ == "__main__":
    main()
