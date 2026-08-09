"""CLI contracts for acquisition commands, without external requests."""

from __future__ import annotations

import ast
import pathlib
import sys
from dataclasses import asdict

import fetch_site_panoramas
import reregister_site
import screen_cities
import summarise_panorama_routes
import summarise_site_panoramas
from semantic_twin import paths
from semantic_twin import screening_workflow


def test_fetch_runner_maps_every_option(monkeypatch, tmp_path):
    called = {}

    def fake_fetch(scene, options):
        called.update(scene=scene, **asdict(options))
        return {
            "site": "test",
            "panorama_dirs": ["pano_00_a"],
            "selection": {"minimum_separation_m": None, "walk_panoramas_dropped_as_roofed": 0},
            "approximate_requests": 1,
        }

    monkeypatch.setattr(fetch_site_panoramas, "fetch_site_panoramas", fake_fetch)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "fetch_site_panoramas.py",
            "--scene",
            "scene.json",
            "--count",
            "9",
            "--zoom",
            "4",
            "--screening",
            "screening.json",
            "--workers",
            "3",
            "--out",
            str(tmp_path),
            "--walk-date",
            "2024-03",
            "--open-sky-m",
            "1.75",
            "--along-links",
        ],
    )

    fetch_site_panoramas.main()

    assert called == {
        "scene": pathlib.Path("scene.json"),
        "count": 9,
        "zoom": 4,
        "screening": pathlib.Path("screening.json"),
        "workers": 3,
        "out_root": tmp_path,
        "walk_date": "2024-03",
        "open_sky_m": 1.75,
        "along_links": True,
    }


def test_fetch_runner_default_screening_is_independent_of_cwd(monkeypatch, tmp_path):
    called = {}

    def fake_fetch(scene, options):
        called.update(scene=scene, **asdict(options))
        return {
            "site": "test",
            "panorama_dirs": [],
            "selection": {"minimum_separation_m": None, "walk_panoramas_dropped_as_roofed": 0},
            "approximate_requests": 1,
        }

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(fetch_site_panoramas, "fetch_site_panoramas", fake_fetch)
    monkeypatch.setattr(sys, "argv", ["fetch_site_panoramas.py", "--scene", "scene.json"])

    fetch_site_panoramas.main()

    assert called["screening"] == paths.screening()


def test_screen_runner_keeps_portable_defaults_without_network(monkeypatch, tmp_path):
    called = {}

    def fake_screen(out, **kwargs):
        called.update(out=out, **kwargs)
        return {"rows": []}

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(screen_cities, "screen_candidates", fake_screen)
    monkeypatch.setattr(sys, "argv", ["screen_cities.py"])

    assert screen_cities.main() == 0
    assert called == {
        "out": paths.output("city_screening"),
        "radius_m": 60.0,
        "max_panoramas": 400,
        "workers": 8,
        "only": None,
    }


def test_empty_screen_selection_does_not_request_an_api_key(monkeypatch, tmp_path):
    def fail():
        raise AssertionError("API key should be read only after a candidate matches")

    monkeypatch.setattr(screening_workflow, "google_api_key", fail)
    assert screening_workflow.screen_candidates(tmp_path, only=["not-a-candidate"]) is None


def test_registration_runner_maps_every_option(monkeypatch):
    called = {}

    def fake_reregister(options):
        called.update(asdict(options))

    monkeypatch.setattr(reregister_site, "reregister_site", fake_reregister)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "reregister_site.py",
            "--site",
            "tokyo_hachiko",
            "--crop-m",
            "300",
            "--station",
            "pano_01_a",
            "--station",
            "pano_02_b",
            "--cohort-dir",
            "data/panorama_cohorts/tokyo_2024",
            "--dz-bounds",
            "-1.5",
            "2.0",
            "--dry-run",
            "--no-backup",
        ],
    )

    reregister_site.main()

    assert called == {
        "site": "tokyo_hachiko",
        "crop_m": 300,
        "station_names": ("pano_01_a", "pano_02_b"),
        "cohort_dir": pathlib.Path("data/panorama_cohorts/tokyo_2024"),
        "semantics_dirname": "semantics",
        "dz_bounds": (-1.5, 2.0),
        "dry_run": True,
        "no_backup": True,
        "root_dir": None,
    }


def test_registration_summary_runner_maps_paths(monkeypatch, tmp_path):
    sites = [tmp_path / "one", tmp_path / "two"]
    output = tmp_path / "report"
    called = {}

    def fake_write(site_dirs, output_dir):
        called.update(site_dirs=site_dirs, output_dir=output_dir)
        return "table"

    monkeypatch.setattr(summarise_site_panoramas, "write_summary", fake_write)
    assert summarise_site_panoramas.main(["--site", *(str(site) for site in sites), "--out", str(output)]) == 0
    assert called == {"site_dirs": sites, "output_dir": output}


def test_route_summary_runner_maps_sites_root_and_output(monkeypatch, tmp_path):
    called = {}
    output = tmp_path / "report"

    def fake_build(sites, root):
        called.update(sites=sites, root=root)
        return [{"site": "one"}], "table"

    def fake_write(rows, rendered, output_dir):
        called.update(rows=rows, rendered=rendered, output_dir=output_dir)

    monkeypatch.setattr(summarise_panorama_routes, "build_report", fake_build)
    monkeypatch.setattr(summarise_panorama_routes, "write_report", fake_write)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "summarise_panorama_routes.py",
            "--root",
            str(tmp_path),
            "--out",
            str(output),
            "--site",
            "two",
            "--site",
            "one",
        ],
    )

    summarise_panorama_routes.main()

    assert called == {
        "sites": ["two", "one"],
        "root": tmp_path,
        "rows": [{"site": "one"}],
        "rendered": "table",
        "output_dir": output,
    }


def test_domain_modules_have_no_command_entry_points():
    modules = (
        paths.root() / "semantic_twin" / "acquire" / "site_panoramas.py",
        paths.root() / "semantic_twin" / "acquire" / "panorama_selection.py",
        paths.root() / "semantic_twin" / "screening_workflow.py",
        paths.root() / "semantic_twin" / "vision" / "registration_repair.py",
        paths.root() / "semantic_twin" / "report" / "panorama_registration.py",
        paths.root() / "semantic_twin" / "report" / "panorama_routes.py",
    )
    for module in modules:
        tree = ast.parse(module.read_text(encoding="utf-8"))
        assert not any(
            isinstance(node, (ast.Import, ast.ImportFrom)) and "argparse" in ast.unparse(node) for node in tree.body
        )
        assert not any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "main" for node in tree.body
        )
        assert "__main__" not in module.read_text(encoding="utf-8")
