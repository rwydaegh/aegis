"""Solidify, voxel-remesh and planar-decimate a support mesh in Blender."""

from __future__ import annotations

import argparse
import math
import pathlib
import sys

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from semantic_twin.scene import support_remesh  # noqa: E402


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    def positive_float(value: str) -> float:
        result = float(value)
        if not math.isfinite(result) or result <= 0.0:
            raise argparse.ArgumentTypeError("must be a finite number greater than zero")
        return result

    def non_negative_float(value: str) -> float:
        result = float(value)
        if not math.isfinite(result) or result < 0.0:
            raise argparse.ArgumentTypeError("must be a finite non-negative number")
        return result

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh", type=pathlib.Path, required=True, help="Input support mesh PLY")
    parser.add_argument("--out", type=pathlib.Path, required=True, help="Output binary PLY")
    parser.add_argument("--solidify-m", type=non_negative_float, default=0.3)
    parser.add_argument("--solidify-offset", type=float, default=0.0)
    parser.add_argument("--collapse-ratio", type=non_negative_float, default=0.0)
    parser.add_argument("--collapse-stage", choices=("before", "after"), default="after")
    parser.add_argument("--voxel-size-m", type=positive_float, required=True)
    parser.add_argument("--adaptivity", type=non_negative_float, default=0.0)
    parser.add_argument("--planar-angle-deg", type=non_negative_float, default=1.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = arguments(argv)
    support_remesh.remesh_support_mesh(
        support_remesh.SupportRemeshConfig(
            mesh=args.mesh,
            out=args.out,
            voxel_size_m=args.voxel_size_m,
            solidify_m=args.solidify_m,
            solidify_offset=args.solidify_offset,
            collapse_ratio=args.collapse_ratio,
            collapse_stage=args.collapse_stage,
            adaptivity=args.adaptivity,
            planar_angle_deg=args.planar_angle_deg,
        )
    )


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    main(argv)
