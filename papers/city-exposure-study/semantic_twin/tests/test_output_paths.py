"""Portable defaults for the study's small output-producing scripts."""

from __future__ import annotations

import ast
import pathlib

import fetch_site_panoramas
import run_foliage_study
import screen_cities
import summarise_site_panoramas
from semantic_twin import paths
from semantic_twin.viz import figures


def test_screening_scripts_keep_their_defaults_when_cwd_changes(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    assert fetch_site_panoramas.DEFAULT_SCREENING == paths.screening()
    assert fetch_site_panoramas.arguments(["--scene", "scene.json"]).screening == paths.screening()
    assert screen_cities.arguments([]).out == paths.output("city_screening")
    assert summarise_site_panoramas.arguments(["--site", "panoramas"]).out == paths.output("city_screening")


def test_explicit_screening_paths_still_win(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    screening = pathlib.Path("chosen.json")
    output = pathlib.Path("chosen")

    assert (
        fetch_site_panoramas.arguments(["--scene", "scene.json", "--screening", str(screening)]).screening == screening
    )
    assert screen_cities.arguments(["--out", str(output)]).out == output
    assert summarise_site_panoramas.arguments(["--site", "panoramas", "--out", str(output)]).out == output
    assert output.resolve() == tmp_path / "chosen"


def test_foliage_output_is_independent_of_cwd(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    assert run_foliage_study.OUTPUT == paths.output("foliage_study")


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
