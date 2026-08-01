from __future__ import annotations

import ast
import pathlib


def test_mesh_depth_script_has_no_import_time_blender_execution() -> None:
    """The CLI must stay importable enough for static tooling outside Blender."""
    source = pathlib.Path(__file__).parents[1] / "raycast_mesh_depth.py"
    ast.parse(source.read_text())
