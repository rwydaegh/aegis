"""Contracts for the material and diffraction study commands."""

from __future__ import annotations

import ast
import hashlib
import json

import numpy as np
import pytest

import bound_diffraction
import run_foliage_study
import run_masonry_grating
import run_masonry_spectrum
from semantic_twin import paths
from semantic_twin.materials import foliage_study
from semantic_twin.materials.foliage import POWER_DB_PER_NEPER
from semantic_twin.materials.masonry import grating_study, spectrum_study
from semantic_twin.materials.serialization import publication_json
from semantic_twin.propagation import diffraction_bound


def test_foliage_runner_maps_every_argument(monkeypatch):
    calls = []
    monkeypatch.setattr(foliage_study, "run", lambda stages, **options: calls.append((stages, options)))

    run_foliage_study.main(["leaf", "figure", "--rays", "1234", "--seed", "29"])

    assert calls == [(["leaf", "figure"], {"rays": 1234, "seed": 29})]


def test_masonry_grating_runner_maps_the_stage(monkeypatch):
    calls = []
    monkeypatch.setattr(grating_study, "run", calls.append)

    run_masonry_grating.main(["--stage", "maps"])

    assert calls == ["maps"]


def test_masonry_spectrum_runner_maps_every_argument(monkeypatch):
    calls = []
    monkeypatch.setattr(spectrum_study, "run", lambda stage, **options: calls.append((stage, options)))

    run_masonry_spectrum.main(
        ["--stage", "spectrum", "--memory-budget-gib", "21", "--time-budget-s", "90", "--multiplier", "1.75"]
    )

    assert calls == [
        (
            "spectrum",
            {"memory_budget_gib": 21.0, "time_budget_s": 90.0, "multiplier": 1.75},
        )
    ]


def test_diffraction_runner_maps_every_argument(monkeypatch):
    calls = []
    monkeypatch.setattr(diffraction_bound, "run", calls.append)

    bound_diffraction.main(
        [
            "--site",
            "milan_duomo",
            "--locations",
            "locations.jsonl",
            "--mesh",
            "mesh.ply",
            "--standpoints",
            "7",
            "--azimuth",
            "36",
            "--elevation",
            "24",
            "--elevation-floor-deg",
            "0.2",
            "--out",
            "bound.json",
        ]
    )

    assert calls == [
        diffraction_bound.DiffractionBoundConfig(
            site="milan_duomo",
            locations="locations.jsonl",
            mesh="mesh.ply",
            standpoints=7,
            azimuth=36,
            elevation=24,
            elevation_floor_deg=0.2,
            out="bound.json",
        )
    ]


@pytest.mark.parametrize(
    "module_path",
    [
        paths.root() / "semantic_twin" / "materials" / "foliage_study.py",
        paths.root() / "semantic_twin" / "materials" / "masonry" / "grating_study.py",
        paths.root() / "semantic_twin" / "materials" / "masonry" / "spectrum_study.py",
        paths.root() / "semantic_twin" / "propagation" / "diffraction_bound.py",
    ],
)
def test_domain_study_modules_have_no_command_line_interface(module_path):
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imported_modules = {alias.name for node in tree.body if isinstance(node, ast.Import) for alias in node.names}
    function_names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    has_main_guard = any(
        isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and isinstance(node.test.left, ast.Name)
        and node.test.left.id == "__name__"
        for node in tree.body
    )

    assert "argparse" not in imported_modules
    assert "main" not in function_names
    assert not has_main_guard


def test_study_output_roots_survive_the_move():
    assert foliage_study.OUTPUT == paths.output("foliage_study")
    assert grating_study.ROOT == paths.root()
    assert spectrum_study.ROOT == paths.root()
    assert diffraction_bound.ROOT == paths.root()


def test_domain_run_apis_dispatch_stages_in_the_original_order(monkeypatch):
    foliage_calls = []
    monkeypatch.setattr(foliage_study, "stage_sweep", lambda rays, seed: foliage_calls.append(("sweep", rays, seed)))
    monkeypatch.setattr(foliage_study, "stage_leaf", lambda: foliage_calls.append(("leaf",)))
    monkeypatch.setattr(foliage_study, "stage_figure", lambda: foliage_calls.append(("figure",)))
    foliage_study.run(None, rays=80, seed=4)

    grating_calls = []
    for stage in ("census", "rcwa", "kirchhoff", "maps", "model", "validate"):
        monkeypatch.setattr(grating_study, f"stage_{stage}", lambda stage=stage: grating_calls.append(stage))
    grating_study.run()

    spectrum_calls = []
    monkeypatch.setattr(
        spectrum_study,
        "stage_converge",
        lambda memory, seconds: spectrum_calls.append(("converge", memory, seconds)),
    )
    monkeypatch.setattr(
        spectrum_study, "stage_spectrum", lambda multiplier: spectrum_calls.append(("spectrum", multiplier))
    )
    spectrum_study.run(memory_budget_gib=12.0, time_budget_s=60.0, multiplier=1.25)

    assert foliage_calls == [("sweep", 80, 4), ("leaf",), ("figure",)]
    assert grating_calls == ["census", "rcwa", "kirchhoff", "maps", "model", "validate"]
    assert spectrum_calls == [("converge", 12.0, 60.0), ("spectrum", 1.25)]


def test_foliage_leaf_output_is_deterministic_and_keeps_its_schema(monkeypatch, tmp_path):
    monkeypatch.setattr(foliage_study, "OUTPUT", tmp_path)

    foliage_study.run(["leaf"])
    first = (tmp_path / "leaf.json").read_bytes()
    foliage_study.run(["leaf"])

    assert (tmp_path / "leaf.json").read_bytes() == first
    assert hashlib.sha256(first).hexdigest() == "aa2bd38f375b16456559cfa1da2335a0e08af4d55e7b81c6a87ac7abafed96bc"
    document = json.loads(first)
    assert list(document) == [
        "leaf_thickness_m",
        "leaf_thickness_source",
        "permittivity_source",
        "curves",
        "canopy_boundary_reflectance",
    ]
    assert list(document["curves"]) == ["7", "15", "28"]
    assert len(document["curves"]["15"]["incidence_deg"]) == 86


def test_foliage_sweep_converts_figure_two_power_loss_to_optical_depth(monkeypatch, tmp_path):
    monkeypatch.setattr(foliage_study, "OUTPUT", tmp_path)
    monkeypatch.setattr(foliage_study, "HALF_WIDTHS_M", (0.0,))
    monkeypatch.setattr(foliage_study, "OPTICAL_DEPTHS", (1.0,))
    monkeypatch.setattr(
        foliage_study,
        "_trace",
        lambda *args, **kwargs: {"canopy_solid_angle_fraction": 0.0, "susceptibility": {"isotropic": 1.0}},
    )

    foliage_study.stage_sweep(rays=1, seed=0)

    document = json.loads((tmp_path / "sensitivity.json").read_text())
    gamma = document["figure2_specific_attenuation_db_per_m"]
    assert document["figure2_implied_optical_depth_over_canopy_depth"] == pytest.approx(
        gamma / POWER_DB_PER_NEPER * foliage_study.CANOPY_DEPTH_M
    )


def test_masonry_census_output_keeps_its_exact_contents(monkeypatch, tmp_path):
    monkeypatch.setattr(grating_study, "OUTPUT", tmp_path)

    grating_study.run("census")

    census = (tmp_path / "census.json").read_bytes()
    assert hashlib.sha256(census).hexdigest() == "b842c2906d38e865726bf65e7e5bfd89c98101a6797ebd022a0a812439f7eeca"
    document = json.loads(census)
    assert len(document["walls"]) == 20
    assert list(document["tolerance_classes"]) == ["T1", "T2", "R1", "R2"]


def test_publication_json_removes_cpu_tail_bits_but_keeps_a_change_at_13_digits():
    reference = publication_json({"value": 1.23456789012341, "computed_here": True})

    assert json.loads(reference)["computed_here"] is True
    assert publication_json({"value": 1.23456789012342, "computed_here": True}) == reference
    assert publication_json({"value": 1.234567890124, "computed_here": True}) != reference


def test_diffraction_grid_integrates_the_sampled_sky_cap():
    _, omega, _ = diffraction_bound.direction_grid(48, 35, 0.05)
    expected = 2.0 * np.pi * (1.0 - np.sin(np.radians(0.05)))

    assert float(np.sum(omega)) == pytest.approx(expected, rel=1e-14)
    assert diffraction_bound.knife_edge_loss_db(np.array([0.0]))[0] == pytest.approx(6.032852208563606)


def test_diffraction_workflow_sorts_locations_and_keeps_output_schema(monkeypatch, tmp_path):
    locations = tmp_path / "study_locations.jsonl"
    locations.write_text(
        "\n".join(
            json.dumps(
                {
                    "index": index,
                    "x": float(index),
                    "y": 2.0,
                    "z": 1.5,
                    "sky_fraction": sky,
                    "chi_isotropic_direct": 0.1,
                    "chi_isotropic": 0.2,
                    "chi_rooftop_direct": 0.3,
                    "chi_rooftop": 0.4,
                    "chi_street_small_cell_direct": 0.5,
                    "chi_street_small_cell": 0.6,
                }
            )
            for index, sky in ((4, 0.4), (1, 0.1))
        )
    )
    manifest = {
        "mesh": "ignored.ply",
        "trace_config": {"frequency_hz": 15.0e9},
    }
    locations.with_name("study_manifest.json").write_text(json.dumps(manifest))
    monkeypatch.setattr(diffraction_bound, "MitsubaGeometry", lambda mesh: ("geometry", mesh))
    monkeypatch.setattr(
        diffraction_bound,
        "direction_grid",
        lambda azimuth, elevation, floor: (np.ones((1, 3)), np.ones(1), np.ones(1)),
    )
    monkeypatch.setattr(
        diffraction_bound,
        "bound_one",
        lambda geometry, origin, unit, omega, models, wavelengths: {
            "rooftop_direct": float(origin[0]),
            "rooftop_diff_edge_15ghz": 0.01,
        },
    )
    output = tmp_path / "result.json"

    config = diffraction_bound.DiffractionBoundConfig(
        site="test_site",
        locations=locations,
        mesh="chosen.ply",
        standpoints=1,
        azimuth=8,
        elevation=6,
        elevation_floor_deg=0.5,
        out=output,
    )
    returned = diffraction_bound.run(config)

    assert returned == output
    document = json.loads(output.read_text())
    assert list(document) == ["site", "mesh", "frequency_hz", "grid", "standpoints"]
    assert document["mesh"] == "chosen.ply"
    assert document["grid"] == {"azimuth": 8, "elevation": 6, "elevation_floor_deg": 0.5}
    assert [row["index"] for row in document["standpoints"]] == [1]
