"""The payload command stays one package contract behind its root script."""

from __future__ import annotations

import ast
import pathlib
import subprocess
import sys

import export_propagation_payload as root_cli
import pytest

from semantic_twin.propagation import DEFAULT_MAX_BOUNCES
from semantic_twin.cli import export_propagation_payload as cli
from semantic_twin.viz.blender import export_contract

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_root_exporter_is_a_thin_compatibility_wrapper() -> None:
    source = (ROOT / "export_propagation_payload.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {alias.name for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) for alias in node.names}
    assert "semantic_twin.cli.export_propagation_payload" in {
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    }
    assert "argparse" not in imported
    assert "semantic_twin.viz.blender.exporter" not in imported
    assert len(source.splitlines()) <= 30


def test_root_and_package_export_contracts_preserve_defaults(tmp_path: pathlib.Path) -> None:
    argv = ["--production-stem", str(tmp_path / "production"), "--out", str(tmp_path / "viz")]
    root_args = root_cli.arguments(argv)
    package_args = cli.arguments(argv)
    assert vars(root_args) == vars(package_args)
    assert root_args.max_bounces == DEFAULT_MAX_BOUNCES
    assert root_cli.DEFAULT_MAX_BOUNCES == export_contract.DEFAULT_MAX_BOUNCES == DEFAULT_MAX_BOUNCES
    assert root_cli.DEFAULT_DRAW_RADIUS_M == export_contract.DEFAULT_DRAW_RADIUS_M
    assert root_cli.OUTPUT == export_contract.OUTPUT


def test_root_main_invokes_the_package_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[object] = []

    def fake_export(args: object) -> int:
        seen.append(args)
        return 23

    monkeypatch.setattr(export_contract, "export", fake_export)
    assert root_cli.main(["--no-evidence"]) == 23
    assert len(seen) == 1
    assert getattr(seen[0], "evidence") is False


def test_package_import_does_not_import_the_root_script() -> None:
    code = (
        "import sys; "
        "import semantic_twin.viz.blender.export_contract; "
        "assert 'export_propagation_payload' not in sys.modules"
    )
    subprocess.run([sys.executable, "-c", code], cwd=ROOT, check=True)
