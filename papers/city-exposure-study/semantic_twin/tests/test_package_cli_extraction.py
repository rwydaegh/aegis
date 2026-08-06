from __future__ import annotations

import ast
import pathlib

import pytest

from semantic_twin.cli import antenna as antenna_cli
from semantic_twin.cli import bystanders as bystanders_cli
from semantic_twin.cli import sionna_check as sionna_cli
from semantic_twin.propagation.antenna import MACRO_TILT_DEG, MICRO_TILT_DEG, AntennaStudyConfig
from semantic_twin.propagation.bystanders import (
    CLOTHING_RMS_HEIGHT_M,
    DENSITY_LADDER,
    STATURE_MODES,
    BystanderStudyConfig,
)
from semantic_twin.transport.sionna_check import MODES
from semantic_twin.transport.tracer import DEFAULT_MAX_BOUNCES


ROOT = pathlib.Path(__file__).resolve().parents[1]
DOMAIN_MODULES = (
    ROOT / "semantic_twin" / "propagation" / "bystanders.py",
    ROOT / "semantic_twin" / "propagation" / "antenna.py",
    ROOT / "semantic_twin" / "transport" / "sionna_check.py",
)
COMMAND_MODULES = (
    ROOT / "semantic_twin" / "cli" / "bystanders.py",
    ROOT / "semantic_twin" / "cli" / "antenna.py",
    ROOT / "semantic_twin" / "cli" / "sionna_check.py",
)


@pytest.mark.parametrize("path", DOMAIN_MODULES)
def test_domain_modules_have_no_command_line_interface(path: pathlib.Path) -> None:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {alias.name for node in tree.body if isinstance(node, ast.Import) for alias in node.names}
    functions = {node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    assert "argparse" not in imports
    assert "main" not in functions
    assert "__main__" not in source


@pytest.mark.parametrize("path", COMMAND_MODULES)
def test_command_modules_own_argparse_and_main(path: pathlib.Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = {alias.name for node in tree.body if isinstance(node, ast.Import) for alias in node.names}
    functions = {node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    assert "argparse" in imports
    assert "main" in functions


def test_bystander_parser_preserves_defaults() -> None:
    root = ROOT
    assert vars(bystanders_cli.arguments([])) == {
        "locations": 12,
        "realisations": 3,
        "rays": 200_000,
        "max_bounces": DEFAULT_MAX_BOUNCES,
        "local_cells": 512,
        "frequency_ghz": 15.0,
        "crop_m": 250,
        "site": "korenmarkt",
        "seed": 7,
        "tag": "korenmarkt",
        "target_faces": 600,
        "max_radius_m": 30.0,
        "mean_free_paths": float("inf"),
        "clothing_rms_mm": CLOTHING_RMS_HEIGHT_M * 1e3,
        "body_absorber": False,
        "densities": list(DENSITY_LADDER),
        "stature_modes": list(STATURE_MODES),
        "bodies": str(root / "outputs" / "korenmarkt_dynamic_bodies"),
        "output": str(root / "outputs" / "bystander_study"),
        "variant": "llvm_ad_rgb",
        "report": None,
        "resume": False,
        "noise_floor": False,
    }


def test_bystander_main_forwards_a_typed_config(monkeypatch: pytest.MonkeyPatch) -> None:
    received: list[BystanderStudyConfig] = []
    monkeypatch.setattr(bystanders_cli, "run_bystander_study", received.append)

    assert bystanders_cli.main(["--locations", "5", "--noise-floor", "--densities", "0.1", "0.2"]) == 0
    assert isinstance(received[0], BystanderStudyConfig)
    assert received[0].locations == 5
    assert received[0].noise_floor is True
    assert received[0].densities == [0.1, 0.2]


def test_antenna_parser_preserves_defaults() -> None:
    assert vars(antenna_cli.arguments([])) == {
        "sites": ["korenmarkt"],
        "all_sites": False,
        "kernel": False,
        "artefact": False,
        "locations": 80,
        "rays": 200_000,
        "max_bounces": DEFAULT_MAX_BOUNCES,
        "frequency_hz": 15.0e9,
        "crop_m": 250,
        "walk_radius_m": 90.0,
        "seed": 7,
        "grid_rotation_deg": 0.0,
        "macro_tilt_deg": MACRO_TILT_DEG,
        "micro_tilt_deg": MICRO_TILT_DEG,
        "tag": "antenna",
    }


def test_antenna_main_forwards_a_typed_config(monkeypatch: pytest.MonkeyPatch) -> None:
    received: list[AntennaStudyConfig] = []
    monkeypatch.setattr(antenna_cli, "run_antenna_study", received.append)

    assert antenna_cli.main(["--sites", "korenmarkt", "ghent", "--kernel", "--locations", "7"]) == 0
    assert isinstance(received[0], AntennaStudyConfig)
    assert received[0].sites == ["korenmarkt", "ghent"]
    assert received[0].kernel is True
    assert received[0].locations == 7


def test_sionna_site_parser_preserves_defaults() -> None:
    assert vars(sionna_cli.arguments(["site"])) == {
        "command": "site",
        "site": "korenmarkt",
        "crop_m": 250,
        "locations": 8,
        "sky_samples": 900,
        "rays": 200_000,
        "samples_per_src": 200_000,
        "target_chunk": 32,
        "max_paths": 16_000_000,
        "max_depth": 4,
        "modes": ",".join(MODES),
        "diffraction": False,
        "local": False,
        "gpu": "L4",
    }


@pytest.mark.parametrize(
    ("command", "expected"),
    (
        ("plane", {"command": "plane", "local": False, "gpu": "L4"}),
        (
            "tessellation",
            {
                "command": "tessellation",
                "local": False,
                "gpu": "L4",
                "cell_m": 1.0,
                "sky_samples": 1500,
                "jitters_mm": "0,1,5,20,50,200",
                "tag": "",
            },
        ),
        ("sampling", {"command": "sampling", "local": False, "gpu": "L4", "sky_samples": 600}),
        (
            "convergence",
            {
                "command": "convergence",
                "site": "korenmarkt",
                "crop_m": 250,
                "locations": 12,
                "bounce_rays": 200_000,
                "range_rays": 100_000,
            },
        ),
    ),
)
def test_sionna_other_parsers_preserve_defaults(command: str, expected: dict[str, object]) -> None:
    assert vars(sionna_cli.arguments([command])) == expected


def test_sionna_main_forwards_and_converts_values(monkeypatch: pytest.MonkeyPatch) -> None:
    received: list[dict[str, object]] = []
    monkeypatch.setattr(sionna_cli, "tessellation_experiment", lambda **kwargs: received.append(kwargs))

    assert sionna_cli.main(["tessellation", "--local", "--jitters-mm", "0.1,2", "--tag", "_fine"]) == 0
    assert received == [
        {
            "local": True,
            "gpu": "L4",
            "cell_m": 1.0,
            "sky_samples": 1500,
            "jitters_m": (0.0001, 0.002),
            "tag": "_fine",
        }
    ]
