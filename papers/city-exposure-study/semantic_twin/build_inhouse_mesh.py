"""Build a local-ENU PLY from downloaded Inhouse Photorealistic 3D Tiles."""

from __future__ import annotations

import argparse
import math
import pathlib
import sys

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from semantic_twin.scene import inhouse_mesh_build  # noqa: E402


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    def positive_float(value: str) -> float:
        result = float(value)
        if not math.isfinite(result) or result <= 0.0:
            raise argparse.ArgumentTypeError("must be a finite number greater than zero")
        return result

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tiles", type=pathlib.Path, required=True, help="Directory containing manifest.json and GLBs")
    parser.add_argument("--out", type=pathlib.Path, required=True, help="Output binary PLY")
    parser.add_argument("--crop-radius-m", type=positive_float, help="Keep faces wholly inside this horizontal radius")
    parser.add_argument("--blend", type=pathlib.Path, help="Optional Blender scene containing the aligned source tiles")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = arguments(argv)
    inhouse_mesh_build.build_inhouse_mesh(
        inhouse_mesh_build.InhouseMeshBuildConfig(
            tiles=args.tiles,
            out=args.out,
            crop_radius_m=args.crop_radius_m,
            blend=args.blend,
        )
    )


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    main(argv)
