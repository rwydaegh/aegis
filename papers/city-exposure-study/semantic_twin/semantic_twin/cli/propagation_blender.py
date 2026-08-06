"""Build a propagation walkthrough blend from a sealed payload."""

from __future__ import annotations

import argparse
import pathlib
import sys

from semantic_twin.viz.blender import runner
from semantic_twin.viz.blender.style import MODEL_NAMES

DEFAULT_ASSET_ROOT = pathlib.Path(__file__).resolve().parents[2]


def arguments(
    argv: list[str] | None = None,
    *,
    default_asset_root: pathlib.Path | None = None,
) -> argparse.Namespace:
    """Parse the Blender runner options, preserving its historical defaults."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=pathlib.Path, required=True)
    parser.add_argument("--manifest", type=pathlib.Path)
    parser.add_argument("--blend", type=pathlib.Path, required=True)
    parser.add_argument(
        "--asset-root",
        type=pathlib.Path,
        default=default_asset_root or DEFAULT_ASSET_ROOT,
        help="Repository-relative evidence root. Defaults to the checkout containing this runner.",
    )
    parser.add_argument("--walk-model", default="rooftop", choices=list(MODEL_NAMES))
    parser.add_argument("--lobe-scale-m", type=float, default=7.0)
    parser.add_argument("--lobe-offset-m", type=float, default=13.0)
    parser.add_argument("--lobe-floor", type=float, default=0.14)
    parser.add_argument("--ray-radius-m", type=float, default=0.11)
    parser.add_argument(
        "--rim-width-scale",
        type=float,
        default=0.04,
        help="Rim radius in metres per square root metre of slant range",
    )
    parser.add_argument(
        "--rim-site-step",
        type=int,
        default=10,
        help="One drawn site every this many azimuths. Ten of 720 is every five degrees",
    )
    parser.add_argument("--nee-ray-radius-m", type=float, default=0.09)
    parser.add_argument("--nee-line-radius-m", type=float, default=0.05)
    parser.add_argument(
        "--nee-sky-leg-m",
        type=float,
        default=30.0,
        help="Drawn length of the leg that left the scene, which in 09 runs to the sky sphere",
    )
    parser.add_argument(
        "--animation-ranked-paths",
        "--animation-paths",
        dest="animation_paths",
        type=int,
        default=12,
        help="Top rooftop-weighted visual-trace samples, one complete chain per frame",
    )
    parser.add_argument(
        "--animation-nee-paths",
        type=int,
        default=12,
        help="Stored SBR chains with qualitative roofline NEE connections, one per frame",
    )
    parser.add_argument(
        "--animation-escape-leg-m",
        type=float,
        default=24.0,
        help="Short display length for a final semi-infinite escaped direction",
    )
    parser.add_argument("--point-radius-m", type=float, default=0.09, help="Drawn size of one depth cloud point")
    parser.add_argument(
        "--pose-sigma-scale",
        type=float,
        default=10.0,
        help="Life sizes the pose covariance ellipsoid is drawn at. One sigma here is centimetres",
    )
    parser.add_argument("--render-dir", type=pathlib.Path, help="Also render one PNG per camera")
    parser.add_argument(
        "--prepared-render-dir",
        type=pathlib.Path,
        help="Render one ready-to-read still from every prepared scene",
    )
    parser.add_argument(
        "--prepared-render-layers",
        action="store_true",
        help="Render every audit view layer, rather than only the first layer of each prepared scene",
    )
    parser.add_argument(
        "--gpu", action="store_true", help="Render on the accelerator, and fail loudly if there is none"
    )
    parser.add_argument(
        "--figures",
        nargs="+",
        help="Render only the figures whose name starts with one of these, for iterating on one layer",
    )
    parser.add_argument("--samples", type=int, default=64)
    parser.add_argument("--resolution-scale", type=float, default=1.0)
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    args = parser.parse_args(argv)
    if args.animation_paths < 0:
        parser.error("--animation-ranked-paths must be zero or greater")
    if args.animation_nee_paths < 0:
        parser.error("--animation-nee-paths must be zero or greater")
    return args


def main(argv: list[str] | None = None, *, default_asset_root: pathlib.Path | None = None) -> int:
    """Parse options and ask the reusable runner to build one blend."""
    return runner.build_blend(arguments(argv, default_asset_root=default_asset_root))


__all__ = ["DEFAULT_ASSET_ROOT", "arguments", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
