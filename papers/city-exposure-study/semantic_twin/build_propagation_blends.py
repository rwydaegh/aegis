"""Build propagation walkthrough blends for the study sites and zip them."""

from __future__ import annotations

import argparse
import pathlib
import sys

from semantic_twin.viz.blender import propagation_blends_build

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
OUTPUT = SCRIPT_DIR / "outputs" / "propagation_viz"
BLENDER = pathlib.Path.home() / "blender-4.5" / "blender"


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sites", nargs="*", default=list(propagation_blends_build.SITES))
    parser.add_argument("--locations", type=int, default=60)
    parser.add_argument("--paths", type=int, default=900)
    parser.add_argument("--rays", type=int, default=200_000)
    parser.add_argument("--draw-radius-m", type=float, default=110.0)
    parser.add_argument("--samples", type=int, default=48)
    parser.add_argument("--resolution-scale", type=float, default=1.0)
    parser.add_argument("--skip-render", action="store_true")
    parser.add_argument(
        "--gpu", action="store_true", help="Render on the accelerator, and fail loudly if there is none"
    )
    parser.add_argument("--retrace", action="store_true", help="Retrace even if a payload exists")
    parser.add_argument("--out", type=pathlib.Path, default=OUTPUT)
    parser.add_argument("--archive", type=pathlib.Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
    propagation_blends_build.build_propagation_blends(
        propagation_blends_build.PropagationBlendBuildConfig(
            script_dir=SCRIPT_DIR,
            blender=BLENDER,
            out=args.out,
            sites=tuple(args.sites),
            locations=args.locations,
            paths=args.paths,
            rays=args.rays,
            draw_radius_m=args.draw_radius_m,
            samples=args.samples,
            resolution_scale=args.resolution_scale,
            skip_render=args.skip_render,
            gpu=args.gpu,
            retrace=args.retrace,
            archive=args.archive,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
