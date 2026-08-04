"""Render first-hit range from a recovered panorama camera into a mesh."""

from __future__ import annotations

import argparse
import pathlib

from semantic_twin.vision.mesh_depth import MeshDepthConfig, first_hit_range, ground_offset_m, render_mesh_depth

__all__ = ["first_hit_range", "ground_offset_m"]


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh", type=pathlib.Path, required=True)
    parser.add_argument("--pose", type=pathlib.Path, required=True)
    parser.add_argument("--views", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--yaws", type=int, nargs="+", default=[0, 90, 180, 270])
    parser.add_argument("--pitch", type=float, default=0.0)
    parser.add_argument("--fov-deg", type=float, default=90.0)
    parser.add_argument("--ground-lock-height-m", type=float)
    return parser.parse_args()


def main() -> None:
    args = arguments()
    render_mesh_depth(
        MeshDepthConfig(
            mesh=args.mesh,
            pose=args.pose,
            views=args.views,
            out=args.out,
            yaws=tuple(args.yaws),
            pitch=args.pitch,
            fov_deg=args.fov_deg,
            ground_lock_height_m=args.ground_lock_height_m,
        )
    )


if __name__ == "__main__":
    main()
