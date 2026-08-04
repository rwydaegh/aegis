"""Blind the facade crop set before it is shown to a model."""

from __future__ import annotations

import argparse
import pathlib

from semantic_twin.vision.facade_blinding import blind_facade_crops, blind_name

__all__ = ["blind_name"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=pathlib.Path, default=pathlib.Path("outputs/material_vlm"))
    blind_facade_crops(parser.parse_args().out)


if __name__ == "__main__":
    main()
