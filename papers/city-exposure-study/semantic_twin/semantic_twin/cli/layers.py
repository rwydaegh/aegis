"""Fuse prompted concepts into spherical semantic layers."""

from __future__ import annotations

import argparse
import pathlib

from semantic_twin.vision.layers import LayerFusionConfig, fuse


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", type=pathlib.Path, required=True)
    parser.add_argument("--concepts", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument(
        "--panorama",
        type=pathlib.Path,
        help="optional equirectangular source image for a diagnostic alpha overlay",
    )
    parser.add_argument("--output-width", type=int, default=8192)
    parser.add_argument("--row-chunk", type=int, default=128)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    fuse(LayerFusionConfig(**vars(arguments(argv))))


if __name__ == "__main__":
    main()
