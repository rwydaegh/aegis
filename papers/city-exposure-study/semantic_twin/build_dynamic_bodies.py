"""Place SAM 3D Body reconstructions into scene ENU."""

from __future__ import annotations

import argparse
import pathlib

from semantic_twin.vision.body_placement import USABLE_DEPTH_DECISIONS, BodyPlacementConfig, place_dynamic_bodies

__all__ = ["USABLE_DEPTH_DECISIONS"]


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reconstructions", type=pathlib.Path, required=True)
    parser.add_argument("--pose", type=pathlib.Path, required=True)
    parser.add_argument("--mesh", type=pathlib.Path, required=True)
    parser.add_argument("--depth-compare", type=pathlib.Path)
    parser.add_argument("--mesh-depth", type=pathlib.Path)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--fov-deg", type=float, default=90.0)
    return parser.parse_args()


def main() -> None:
    args = arguments()
    place_dynamic_bodies(
        BodyPlacementConfig(
            reconstructions=args.reconstructions,
            pose=args.pose,
            mesh=args.mesh,
            depth_compare=args.depth_compare,
            mesh_depth=args.mesh_depth,
            out=args.out,
        )
    )


if __name__ == "__main__":
    main()
