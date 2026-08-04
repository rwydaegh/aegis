"""Build texture-derived material evidence and measure its value."""

from __future__ import annotations

import argparse
import pathlib

from semantic_twin.vision.texture_study import TextureStudyConfig, run_texture_study


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tiles", type=pathlib.Path, required=True)
    parser.add_argument("--mesh", type=pathlib.Path, required=True)
    parser.add_argument("--mesh-manifest", type=pathlib.Path, required=True)
    parser.add_argument("--panorama-semantics", type=pathlib.Path, required=True)
    parser.add_argument("--semantics-json", type=pathlib.Path, required=True)
    parser.add_argument("--panorama", type=pathlib.Path, required=True)
    parser.add_argument("--pose", type=pathlib.Path, required=True)
    parser.add_argument("--concepts", type=pathlib.Path, default=pathlib.Path("config/semantic_concepts.json"))
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--crop-radius-m", type=float, default=140.0)
    parser.add_argument("--grid-height", type=int, default=1536)
    parser.add_argument("--block-m", type=float, default=12.0)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--min-texels", type=int, default=8)
    parser.add_argument("--min-purity", type=float, default=0.7)
    parser.add_argument("--collapse-threshold", type=float, default=0.55)
    parser.add_argument("--l2", type=float, default=3.0)
    parser.add_argument("--seed", type=int, default=7)
    return parser.parse_args()


def main() -> None:
    run_texture_study(TextureStudyConfig(**vars(arguments())))


if __name__ == "__main__":
    main()
