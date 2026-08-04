"""Cut rectilinear label and confidence maps from fused panorama semantics."""

from __future__ import annotations

import argparse
import pathlib

from semantic_twin.vision import fused_semantic_crops


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--semantics", type=pathlib.Path, required=True, help="directory with panorama_semantics.npz")
    parser.add_argument("--panorama", type=pathlib.Path, help="equirectangular image, for the RGB crops")
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--yaws", type=int, nargs="+", default=[0, 90, 180, 270])
    parser.add_argument("--pitch", type=float, default=0.0)
    parser.add_argument("--fov-deg", type=float, default=90.0)
    parser.add_argument("--size", type=int, default=1536)
    parser.add_argument(
        "--equirect-width",
        type=int,
        help="resample the fused map to this width before cutting, for the resolution ablation",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = arguments(argv)
    fused_semantic_crops.crop_fused_semantics(
        fused_semantic_crops.FusedSemanticCropConfig(
            semantics=args.semantics,
            panorama=args.panorama,
            out=args.out,
            yaws=tuple(args.yaws),
            pitch=args.pitch,
            fov_deg=args.fov_deg,
            size=args.size,
            equirect_width=args.equirect_width,
        )
    )


if __name__ == "__main__":
    main()
