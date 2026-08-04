"""Build and render the configured semantic-twin showcase views."""

from __future__ import annotations

import argparse
import pathlib
import shutil
import sys

from semantic_twin.viz.showcase_driver import DEFAULT_BLENDER, crop_basis, render_showcase

__all__ = ["crop_basis", "main"]


SCRIPT_DIR = pathlib.Path(__file__).resolve().parent


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", required=True)
    parser.add_argument("--config", type=pathlib.Path, default=SCRIPT_DIR / "config" / "showcase.json")
    parser.add_argument("--out", type=pathlib.Path, help="Output directory, defaults to outputs/showcase_<site>")
    parser.add_argument("--stage", nargs="*", choices=["payload", "render", "annotate"], default=None)
    parser.add_argument("--views", nargs="*", help="Restrict rendering and annotation to these views")
    parser.add_argument("--blender", type=pathlib.Path, default=DEFAULT_BLENDER)
    parser.add_argument("--render-host", help="ssh host with a GPU, for example blgpu")
    parser.add_argument("--remote-root", default="~/showcase")
    parser.add_argument("--device", default="GPU", choices=["GPU", "CPU"])
    parser.add_argument("--draft", action="store_true", help="Low samples and half resolution")
    parser.add_argument("--samples", type=int)
    parser.add_argument("--resolution-scale", type=float, default=1.0)
    parser.add_argument("--blend", action="store_true", help="Also save the assembled .blend")
    parser.add_argument("--skip-tiles", action="store_true", help="Leave the textured leaves out, for fast iteration")
    return parser.parse_args()


def main() -> None:
    render_showcase(arguments())


if __name__ == "__main__":
    if shutil.which("rsync") is None:
        print("[driver] rsync is not on PATH, remote rendering will fail", file=sys.stderr)
    main()
