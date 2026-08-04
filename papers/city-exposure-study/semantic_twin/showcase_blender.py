"""Render a semantic-twin showcase payload in Blender."""

import argparse
import pathlib
import sys

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from semantic_twin.viz.blender.showcase_scene import render_payload  # noqa: E402


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--blend", type=pathlib.Path)
    parser.add_argument("--views", nargs="*", help="Render only these view names")
    parser.add_argument("--samples", type=int, help="Override the sample count of every view")
    parser.add_argument("--resolution-scale", type=float, default=1.0)
    parser.add_argument("--device", default="GPU", choices=["GPU", "CPU"])
    parser.add_argument("--skip-tiles", action="store_true", help="Leave the textured leaves out, for fast iteration")
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(argv)


def main() -> None:
    render_payload(arguments())


if __name__ == "__main__":
    main()
