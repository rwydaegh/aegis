"""Bootstrap the package propagation-blend runner for headless Blender.

Blender executes this file directly, so it cannot rely on the current working
directory to find the study package. The parser and build orchestration live in
:mod:`semantic_twin.viz.blender.runner`.
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    # Blender runs this with its own interpreter and path. Add the study root
    # before importing the package so ``semantic_twin`` is always found.
    sys.path.insert(0, str(ROOT))

from semantic_twin.cli import propagation_blender as cli  # noqa: E402


def arguments(argv: list[str] | None = None):
    """Keep the historical parser import path while using the package parser."""
    return cli.arguments(argv, default_asset_root=ROOT)


def main(argv: list[str] | None = None) -> int:
    """Keep the historical Blender entry point while delegating the build."""
    # The package keeps animation.build_path_animation before
    # scene.hide_heavy_collections so saved collection status is accurate.
    return cli.main(argv, default_asset_root=ROOT)


if __name__ == "__main__":
    sys.exit(main())
