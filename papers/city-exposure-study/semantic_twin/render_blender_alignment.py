"""Render photogrammetry from a recovered panorama camera in Blender."""

import argparse
import pathlib
import sys

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from semantic_twin.viz.blender.alignment import (  # noqa: E402
    camera_matrix,
    cylinder_between,
    local_view_basis,
    look_at,
    material,
    panorama_rotation,
    render_alignment,
    setup_scene,
)

__all__ = [
    "camera_matrix",
    "cylinder_between",
    "local_view_basis",
    "look_at",
    "main",
    "material",
    "panorama_rotation",
    "setup_scene",
]


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh", type=pathlib.Path, required=True)
    parser.add_argument("--pose", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--size", type=int, default=1024)
    parser.add_argument("--yaws", type=float, nargs="+", default=[0.0, 90.0, 180.0, 270.0])
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def main() -> None:
    render_alignment(arguments())


if __name__ == "__main__":
    main()
