from __future__ import annotations

import ast
import pathlib

import propagation_blender
from semantic_twin.cli import propagation_blender as blender_cli


ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_root_script_is_only_a_blender_bootstrap() -> None:
    source = (ROOT / "propagation_blender.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert not any(
        alias.name == "bpy" for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names
    )
    assert source.index("sys.path.insert") < source.index("from semantic_twin")
    assert len(source.splitlines()) <= 40


def test_runner_import_does_not_import_blender() -> None:
    source = (ROOT / "semantic_twin" / "viz" / "blender" / "runner.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    bpy_imports = [
        node for node in tree.body if isinstance(node, ast.Import) and any(alias.name == "bpy" for alias in node.names)
    ]
    assert bpy_imports == []
    assert not any(
        isinstance(node, ast.Import) and any(alias.name == "argparse" for alias in node.names) for node in tree.body
    )
    assert not any(isinstance(node, ast.FunctionDef) and node.name == "main" for node in tree.body)
    build = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "build_blend")
    assert any(
        isinstance(node, ast.Import) and any(alias.name == "bpy" for alias in node.names) for node in ast.walk(build)
    )


def test_cli_module_owns_parser_and_main() -> None:
    source = (ROOT / "semantic_twin" / "cli" / "propagation_blender.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert any(
        isinstance(node, ast.Import) and any(alias.name == "argparse" for alias in node.names) for node in tree.body
    )
    assert any(isinstance(node, ast.FunctionDef) and node.name == "main" for node in tree.body)


def test_root_and_package_cli_preserve_parser_defaults(tmp_path: pathlib.Path) -> None:
    argv = ["--payload", str(tmp_path / "payload.npz"), "--blend", str(tmp_path / "scene.blend")]
    root_args = propagation_blender.arguments(argv)
    package_args = blender_cli.arguments(argv)
    assert vars(root_args) == vars(package_args)
    assert root_args.asset_root == ROOT
    assert root_args.walk_model == "rooftop"
    assert root_args.animation_paths == 12
    assert root_args.animation_nee_paths == 12


def test_external_asset_root_is_forwarded_to_package_parser(tmp_path: pathlib.Path) -> None:
    asset_root = tmp_path / "sealed-checkout"
    args = blender_cli.arguments(
        [
            "--payload",
            str(tmp_path / "payload.npz"),
            "--blend",
            str(tmp_path / "scene.blend"),
            "--asset-root",
            str(asset_root),
            "--animation-ranked-paths",
            "0",
            "--animation-nee-paths",
            "0",
        ]
    )
    assert args.asset_root == asset_root
    assert args.animation_paths == 0
    assert args.animation_nee_paths == 0
