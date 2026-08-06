"""Acquire one Google Street View panorama and its pose."""

from __future__ import annotations

import argparse
import pathlib

from semantic_twin.acquire.streetview import StreetViewAcquireConfig, acquire_panorama


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", type=pathlib.Path, required=True)
    parser.add_argument("--zoom", type=int, choices=range(0, 6), default=5)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--max-tiles", type=int, default=600)
    parser.add_argument("--out", type=pathlib.Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    acquire_panorama(StreetViewAcquireConfig(**vars(arguments(argv))))


if __name__ == "__main__":
    main()
