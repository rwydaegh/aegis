"""Build a visible semantic surface set with the fishnet cutter."""

from __future__ import annotations

import argparse
import pathlib

from semantic_twin.scene import fishnet_build


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh", type=pathlib.Path, required=True)
    parser.add_argument("--pose", type=pathlib.Path, required=True)
    parser.add_argument("--views", type=pathlib.Path, required=True, help="directory with h+00_YYY_labels.npy")
    parser.add_argument("--mesh-depth", type=pathlib.Path, required=True)
    parser.add_argument("--depth-compare", type=pathlib.Path)
    parser.add_argument("--semantics-json", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--yaws", type=int, nargs="+", default=[0, 90, 180, 270])
    parser.add_argument("--min-confidence", type=float, default=0.35)
    parser.add_argument("--boundary-tolerance-px", type=float, default=1.5)
    parser.add_argument("--min-region-pixels", type=int, default=64)
    parser.add_argument("--depth-break-ratio", type=float, default=0.15)
    parser.add_argument("--min-piece-area-px", type=float, default=1.0)
    parser.add_argument("--baseline", action="store_true", help="also count the image-tile quadtree for comparison")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = arguments(argv)
    fishnet_build.build_fishnet_surface(
        fishnet_build.FishnetBuildConfig(
            mesh=args.mesh,
            pose=args.pose,
            views=args.views,
            mesh_depth=args.mesh_depth,
            depth_compare=args.depth_compare,
            semantics_json=args.semantics_json,
            out=args.out,
            yaws=tuple(args.yaws),
            min_confidence=args.min_confidence,
            boundary_tolerance_px=args.boundary_tolerance_px,
            min_region_pixels=args.min_region_pixels,
            depth_break_ratio=args.depth_break_ratio,
            min_piece_area_px=args.min_piece_area_px,
            baseline=args.baseline,
        )
    )


if __name__ == "__main__":
    main()
