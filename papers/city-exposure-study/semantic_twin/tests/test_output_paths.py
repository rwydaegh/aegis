"""Portable defaults for the study's small output-producing scripts."""

from __future__ import annotations

import ast

from semantic_twin import paths
from semantic_twin.materials import foliage_study
from semantic_twin.viz import figures


def test_foliage_output_is_independent_of_cwd(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    assert foliage_study.OUTPUT == paths.output("foliage_study")


def test_remesh_panel_uses_the_root_and_figure_registry_without_importing_it():
    source_path = paths.root() / "make_remesh_panel.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    assignments = {
        target.id: ast.unparse(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }

    assert assignments["ROOT"] == "paths.root()"
    assert assignments["out"] == "figures.get('remesh_visual').path()"
    assert figures.get("remesh_visual").path().name == "10_remesh_visual.png"
