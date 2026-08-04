"""Contracts between experiment commands and their package implementations."""

from __future__ import annotations

import ast
import importlib
import pathlib

import numpy as np
import pytest

from semantic_twin import paths
from semantic_twin.exposure.crop_convergence_study import candidate_meshes
from semantic_twin.exposure.crop_convergence_study import CropConvergenceConfig
from semantic_twin.exposure.law_comparison_study import LawComparisonConfig
from semantic_twin.exposure.material_ablation_study import MaterialAblationConfig
from semantic_twin.exposure.material_ablation_study import variants
from semantic_twin.exposure.next_event_study import NextEventStudyConfig
from semantic_twin.exposure.substreet_ablation_study import SubstreetAblationConfig
from semantic_twin.exposure.substreet_ablation_study import write_culled
from semantic_twin.report.city_metrics import walk_sky

RUNNER_MAP = {
    "run_next_event.py": "semantic_twin.exposure.next_event_study",
    "run_material_ablation.py": "semantic_twin.exposure.material_ablation_study",
    "run_crop_convergence.py": "semantic_twin.exposure.crop_convergence_study",
    "run_law_comparison.py": "semantic_twin.exposure.law_comparison_study",
    "run_substreet_ablation.py": "semantic_twin.exposure.substreet_ablation_study",
    "measure_city_metrics.py": "semantic_twin.report.city_metrics",
}


@pytest.mark.parametrize(("runner", "implementation"), RUNNER_MAP.items())
def test_runner_contains_only_command_line_plumbing(runner: str, implementation: str) -> None:
    tree = ast.parse((paths.root() / runner).read_text())
    functions = [node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    imports = {node.module for node in tree.body if isinstance(node, ast.ImportFrom) and node.module is not None}
    assert functions == ["main"]
    assert implementation in imports


@pytest.mark.parametrize("implementation", RUNNER_MAP.values())
def test_package_implementation_has_no_command_line_parser(implementation: str) -> None:
    module = importlib.import_module(implementation)
    tree = ast.parse(pathlib.Path(module.__file__).read_text())
    assert not any(
        isinstance(node, ast.Import) and any(alias.name == "argparse" for alias in node.names) for node in tree.body
    )
    assert not any(isinstance(node, ast.ImportFrom) and node.module == "argparse" for node in tree.body)
    assert not any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "main" for node in tree.body
    )


def test_next_event_runner_forwards_every_option(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = importlib.import_module("run_next_event")
    calls = []
    monkeypatch.setattr(runner, "run_next_event_study", calls.append)
    status = runner.main(
        [
            "--sites",
            "one",
            "two",
            "--crop-m",
            "90",
            "--rays",
            "10",
            "--builders",
            "4",
            "--held-out",
            "3",
            "--azimuths",
            "20",
            "--elevations",
            "10",
            "--cell-m",
            "2",
            "--dims",
            "2",
            "--site-lift-m",
            "1.25",
            "--connections",
            "5",
            "--frequency-hz",
            "2e9",
            "--max-bounces",
            "2",
            "--walk-radius-m",
            "30",
            "--head-height-m",
            "1.7",
            "--walk",
            "grid",
            "--walk-path",
            "closest",
            "--walk-stride-m",
            "2.5",
            "--drop-clutter",
            "--seed",
            "19",
            "--variant",
            "scalar_rgb",
            "--tag",
            "trial",
        ]
    )
    config = calls[0]
    assert status == 0
    assert config.sites == ("one", "two")
    assert (config.crop_m, config.rays, config.builders, config.held_out) == (90, 10, 4, 3)
    assert (config.azimuths, config.elevations, config.cell_m, config.dims) == (20, 10, 2.0, 2)
    assert (config.site_lift_m, config.connections, config.frequency_hz) == (1.25, 5, 2.0e9)
    assert (config.max_bounces, config.walk_radius_m, config.head_height_m) == (2, 30.0, 1.7)
    assert (config.walk, config.walk_path, config.walk_stride_m) == ("grid", "closest", 2.5)
    assert (config.drop_clutter, config.seed, config.variant, config.tag) == (True, 19, "scalar_rgb", "trial")


@pytest.mark.parametrize(
    ("module_name", "call_name", "argv", "expected"),
    [
        (
            "run_material_ablation",
            "run_material_ablation",
            [
                "--out",
                "result",
                "--locations",
                "7",
                "--rays",
                "11",
                "--frequency-ghz",
                "28",
                "--seed",
                "3",
                "--material-seeds",
                "4",
                "5",
                "--only",
                "brick",
                "pure_metal",
            ],
            {
                "out": pathlib.Path("result"),
                "locations": 7,
                "rays": 11,
                "frequency_ghz": 28.0,
                "seed": 3,
                "material_seeds": (4, 5),
                "only": ("brick", "pure_metal"),
            },
        ),
        (
            "run_crop_convergence",
            "run_crop_convergence",
            [
                "--site",
                "square",
                "--out",
                "result",
                "--locations",
                "7",
                "--rays",
                "11",
                "--max-bounces",
                "2",
                "--observer-radius-m",
                "35",
                "--frequency-hz",
                "2e9",
                "--seed",
                "3",
            ],
            {
                "site": "square",
                "out": pathlib.Path("result"),
                "locations": 7,
                "rays": 11,
                "max_bounces": 2,
                "observer_radius_m": 35.0,
                "frequency_hz": 2.0e9,
                "seed": 3,
            },
        ),
        (
            "run_law_comparison",
            "run_law_comparison",
            [
                "--site",
                "square",
                "--crops",
                "90",
                "140",
                "--anchor-crop-m",
                "90",
                "--locations",
                "7",
                "--walk-radius-m",
                "35",
                "--rays",
                "11",
                "--frequency-hz",
                "2e9",
                "--seed",
                "3",
                "--out",
                "result",
            ],
            {
                "site": "square",
                "crops": (90, 140),
                "anchor_crop_m": 90,
                "locations": 7,
                "walk_radius_m": 35.0,
                "rays": 11,
                "frequency_hz": 2.0e9,
                "seed": 3,
                "out": pathlib.Path("result"),
            },
        ),
        (
            "run_substreet_ablation",
            "run_substreet_ablation",
            [
                "--site",
                "square",
                "--crop-m",
                "140",
                "--locations",
                "7",
                "--walk-radius-m",
                "35",
                "--rays",
                "11",
                "--floor-below-datum-m",
                "4",
                "--seed",
                "3",
                "--out",
                "result",
            ],
            {
                "site": "square",
                "crop_m": 140,
                "locations": 7,
                "walk_radius_m": 35.0,
                "rays": 11,
                "floor_below_datum_m": 4.0,
                "seed": 3,
                "out": pathlib.Path("result"),
            },
        ),
    ],
)
def test_experiment_runner_builds_package_config(
    monkeypatch: pytest.MonkeyPatch,
    module_name: str,
    call_name: str,
    argv: list[str],
    expected: dict[str, object],
) -> None:
    runner = importlib.import_module(module_name)
    calls = []
    monkeypatch.setattr(runner, call_name, calls.append)
    assert runner.main(argv) == 0
    config = calls[0]
    assert {name: getattr(config, name) for name in expected} == expected


def test_city_metrics_runner_calls_the_package(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = importlib.import_module("measure_city_metrics")
    calls = []
    monkeypatch.setattr(runner, "measure_city_metrics", lambda: calls.append(True))
    runner.main()
    assert calls == [True]


def test_custom_study_root_routes_mesh_and_walk_lookups(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    study = importlib.import_module("semantic_twin.exposure.next_event_study")
    mesh_calls = []
    walk_calls = []

    def stop_after_mesh(site, crop_m, root_dir=None):
        mesh_calls.append((site, crop_m, root_dir))
        raise RuntimeError("mesh lookup observed")

    monkeypatch.setattr(study, "site_mesh", stop_after_mesh)
    config = NextEventStudyConfig(sites=("square",), root=tmp_path)
    with pytest.raises(RuntimeError, match="mesh lookup observed"):
        study.run_next_event_study(config)
    assert mesh_calls == [("square", 250, tmp_path)]

    class Walk:
        points = np.arange(450, dtype=float).reshape(150, 3)

    monkeypatch.setattr(
        study,
        "site_walk",
        lambda *args, **kwargs: (
            walk_calls.append(kwargs) or Walk(),
            {"stations": 1, "standpoints": 150, "road_length_m": 1.0},
        ),
    )
    study._standpoints("square", object(), object(), config)
    assert walk_calls[0]["root"] == tmp_path


def test_custom_root_controls_default_output_directories(tmp_path: pathlib.Path) -> None:
    assert MaterialAblationConfig(root=tmp_path).output_dir == tmp_path / "outputs" / "material_vlm"
    assert CropConvergenceConfig(root=tmp_path).output_dir == tmp_path / "outputs" / "crop_convergence"
    assert LawComparisonConfig(root=tmp_path).output_dir == tmp_path / "outputs" / "law_comparison"
    assert SubstreetAblationConfig(root=tmp_path).output_dir == tmp_path / "outputs" / "substreet_ablation"


@pytest.mark.parametrize(
    ("implementation", "function", "calls"),
    [
        ("semantic_twin.exposure.law_comparison_study", "trace_site", 2),
        ("semantic_twin.exposure.substreet_ablation_study", "run_substreet_ablation", 1),
    ],
)
def test_every_site_mesh_lookup_carries_the_config_root(
    implementation: str,
    function: str,
    calls: int,
) -> None:
    module = importlib.import_module(implementation)
    tree = ast.parse(pathlib.Path(module.__file__).read_text())
    target = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == function)
    lookups = [
        node
        for node in ast.walk(target)
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "site_mesh"
    ]
    assert len(lookups) == calls
    assert all(any(keyword.arg == "root_dir" for keyword in lookup.keywords) for lookup in lookups)


def test_material_variant_order_and_controls_are_pinned() -> None:
    plan = variants(
        {
            "composition": {
                "fixed_building_prior": {"brick": 0.7},
                "vlm_panorama": {"glass": 0.2},
                "vlm_texture": {"wood": 0.1},
            }
        }
    )
    assert list(plan) == [
        "brick",
        "pure_brick",
        "prior_draw",
        "vlm_panorama",
        "vlm_texture",
        "pure_plasterboard",
        "pure_concrete",
        "pure_marble",
        "pure_glass",
        "pure_wood",
        "pure_metal",
    ]
    assert plan["brick"] is None
    assert plan["pure_brick"] == {"brick": 1.0}
    assert plan["prior_draw"] == {"brick": 0.7}


def test_crop_mesh_selection_keeps_radius_order_and_prefers_f64(tmp_path: pathlib.Path) -> None:
    geometry = tmp_path / "data" / "geometry" / "square"
    geometry.mkdir(parents=True)
    for name in ("inhouse_leaf_250m.ply", "inhouse_leaf_130m.ply", "inhouse_leaf_130m_f64.ply"):
        (geometry / name).touch()
    assert [path.name for path in candidate_meshes("square", tmp_path)] == [
        "inhouse_leaf_130m_f64.ply",
        "inhouse_leaf_250m.ply",
    ]


def test_walk_sky_reduction_is_deterministic(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "city250_L3_square_15ghz_locations.jsonl"
    path.write_text("\n".join('{"sky_fraction": ' + str(value) + "}" for value in (0.1, 0.2, 0.4, 0.8)))
    assert walk_sky("square", tmp_path) == pytest.approx((0.3, 0.115, 0.74, 4))


def test_culled_mesh_writer_is_byte_deterministic(tmp_path: pathlib.Path) -> None:
    class Geometry:
        vertices = np.array([[0, 0, -2], [1, 0, -2], [0, 1, -2], [0, 0, 1], [1, 0, 1]], dtype=float)
        faces = np.array([[0, 1, 2], [0, 3, 4]], dtype=np.int64)

    first, before, after = write_culled(Geometry(), 0.0, tmp_path / "first.ply")
    second, _, _ = write_culled(Geometry(), 0.0, tmp_path / "second.ply")
    assert (before, after) == (2, 1)
    assert first.read_bytes() == second.read_bytes()
    assert b"element vertex 3\n" in first.read_bytes()
    assert b"element face 1\n" in first.read_bytes()
