"""Render an RF hit crosshair and exact-pixel zoom for a vision agent."""

from __future__ import annotations

import argparse
import pathlib

from semantic_twin.vision.rf_visual import render_hit_evidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=pathlib.Path)
    parser.add_argument("output", type=pathlib.Path)
    parser.add_argument("--x", type=int, required=True)
    parser.add_argument("--y", type=int, required=True)
    parser.add_argument("--footprint-radius-px", type=int, default=4)
    parser.add_argument("--zoom-radius-px", type=int, default=12)
    args = parser.parse_args()
    output = render_hit_evidence(
        args.image,
        args.output,
        x=args.x,
        y=args.y,
        footprint_radius_px=args.footprint_radius_px,
        zoom_radius_px=args.zoom_radius_px,
    )
    print(output)


if __name__ == "__main__":
    main()
