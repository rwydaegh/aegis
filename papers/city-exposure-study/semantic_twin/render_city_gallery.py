"""Render one comparable establishing view for each acquired city."""

import argparse
import pathlib
import sys

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from semantic_twin.viz.blender.city_gallery import render_gallery  # noqa: E402


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tiles-root", type=pathlib.Path, default=SCRIPT_DIR / "data/tiles")
    parser.add_argument("--out", type=pathlib.Path, default=SCRIPT_DIR / "outputs/city_gallery")
    parser.add_argument("--sites", nargs="*", help="Restrict to these site directories")
    parser.add_argument("--crop-radius-m", type=float, default=130.0)
    parser.add_argument("--samples", type=int, default=96)
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--height", type=int, default=1000)
    parser.add_argument("--azimuth-deg", type=float, default=215.0)
    parser.add_argument("--elevation-deg", type=float, default=30.0)
    parser.add_argument("--fov-deg", type=float, default=46.0)
    parser.add_argument("--margin", type=float, default=1.12, help="Standoff slack beyond a tight fit")
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(argv)


def main() -> None:
    render_gallery(arguments())


if __name__ == "__main__":
    main()
