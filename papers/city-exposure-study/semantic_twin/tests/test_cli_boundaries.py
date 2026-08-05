from __future__ import annotations

import ast
import pathlib

import pytest

from semantic_twin.acquire.streetview import StreetViewAcquireConfig
from semantic_twin.cli import align as align_cli
from semantic_twin.cli import layers as layers_cli
from semantic_twin.cli import panorama as panorama_cli
from semantic_twin.cli import prompted as prompted_cli
from semantic_twin.cli import streetview as streetview_cli
from semantic_twin.vision.align import AlignmentConfig
from semantic_twin.vision.dense import DEFAULT_GATE_MIN_PIXELS, DEFAULT_INFERENCE_SIZE, MODEL, PRODUCTION_REVISION
from semantic_twin.vision.layers import LayerFusionConfig
from semantic_twin.vision.panorama import PanoramaRunConfig
from semantic_twin.vision.prompted import (
    DEFAULT_PROMPT_BATCH,
    DEFAULT_RESOLUTION,
    DEFAULT_THRESHOLD,
    PromptedRunConfig,
)
from semantic_twin.vision.register import DEFAULT_SEEDS
from semantic_twin.vision.views import DEFAULT_VIEW_SIZE


ROOT = pathlib.Path(__file__).resolve().parents[1]

COMMANDS = {
    "streetview": ROOT / "semantic_twin" / "acquire" / "streetview.py",
    "prompted": ROOT / "semantic_twin" / "vision" / "prompted.py",
    "layers": ROOT / "semantic_twin" / "vision" / "layers.py",
    "panorama": ROOT / "semantic_twin" / "vision" / "panorama.py",
    "align": ROOT / "semantic_twin" / "vision" / "align.py",
}


def test_every_domain_module_is_free_of_command_line_code() -> None:
    package = ROOT / "semantic_twin"
    command_directory = package / "cli"
    for module in package.rglob("*.py"):
        if command_directory in module.parents:
            continue
        tree = ast.parse(module.read_text(encoding="utf-8"))
        imports_argparse = any(
            isinstance(node, ast.Import)
            and any(alias.name == "argparse" for alias in node.names)
            or isinstance(node, ast.ImportFrom)
            and node.module == "argparse"
            for node in tree.body
        )
        has_main = any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "main" for node in tree.body
        )
        assert not imports_argparse, module
        assert not has_main, module


@pytest.mark.parametrize(("command", "domain_module"), COMMANDS.items())
def test_command_line_code_is_separate_from_domain_code(command: str, domain_module: pathlib.Path) -> None:
    domain_tree = ast.parse(domain_module.read_text(encoding="utf-8"))
    domain_imports = {alias.name for node in domain_tree.body if isinstance(node, ast.Import) for alias in node.names}
    domain_functions = {
        node.name for node in domain_tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "argparse" not in domain_imports
    assert "main" not in domain_functions
    assert "__main__" not in domain_module.read_text(encoding="utf-8")

    command_module = ROOT / "semantic_twin" / "cli" / f"{command}.py"
    command_tree = ast.parse(command_module.read_text(encoding="utf-8"))
    command_imports = {alias.name for node in command_tree.body if isinstance(node, ast.Import) for alias in node.names}
    command_functions = {
        node.name for node in command_tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "argparse" in command_imports
    assert "main" in command_functions


def test_streetview_defaults_and_forwarding(monkeypatch: pytest.MonkeyPatch) -> None:
    assert vars(streetview_cli.arguments(["--scene", "scene.json"])) == {
        "scene": pathlib.Path("scene.json"),
        "zoom": 5,
        "workers": 8,
        "max_tiles": 600,
        "out": None,
    }
    received: list[StreetViewAcquireConfig] = []
    monkeypatch.setattr(streetview_cli, "acquire_panorama", received.append)
    streetview_cli.main(
        ["--scene", "custom.json", "--zoom", "3", "--workers", "2", "--max-tiles", "70", "--out", "result"]
    )
    assert received == [
        StreetViewAcquireConfig(
            scene=pathlib.Path("custom.json"),
            zoom=3,
            workers=2,
            max_tiles=70,
            out=pathlib.Path("result"),
        )
    ]


def test_prompted_defaults_and_forwarding(monkeypatch: pytest.MonkeyPatch) -> None:
    required = ["--views", "views", "--concepts", "concepts.json", "--out", "result"]
    assert vars(prompted_cli.arguments(required)) == {
        "views": pathlib.Path("views"),
        "concepts": pathlib.Path("concepts.json"),
        "out": pathlib.Path("result"),
        "threshold": DEFAULT_THRESHOLD,
        "resolution": DEFAULT_RESOLUTION,
        "prompt_batch": DEFAULT_PROMPT_BATCH,
        "limit_views": None,
        "force": False,
        "sam_revision": None,
        "sam_repository_commit": None,
        "production": False,
    }
    received: list[PromptedRunConfig] = []
    monkeypatch.setattr(prompted_cli, "run_prompted", received.append)
    prompted_cli.main(
        [
            "--views",
            "custom_views",
            "--concepts",
            "custom.json",
            "--out",
            "custom_out",
            "--threshold",
            "0.61",
            "--resolution",
            "720",
            "--prompt-batch",
            "9",
            "--limit-views",
            "4",
            "--force",
            "--sam-revision",
            "1" * 40,
            "--sam-repository-commit",
            "2" * 40,
            "--production",
        ]
    )
    assert received == [
        PromptedRunConfig(
            views=pathlib.Path("custom_views"),
            concepts=pathlib.Path("custom.json"),
            out=pathlib.Path("custom_out"),
            threshold=0.61,
            resolution=720,
            prompt_batch=9,
            limit_views=4,
            force=True,
            sam_revision="1" * 40,
            sam_repository_commit="2" * 40,
            production=True,
        )
    ]


def test_layer_defaults_and_forwarding(monkeypatch: pytest.MonkeyPatch) -> None:
    required = ["--predictions", "predictions", "--concepts", "concepts.json", "--out", "result"]
    assert vars(layers_cli.arguments(required)) == {
        "predictions": pathlib.Path("predictions"),
        "concepts": pathlib.Path("concepts.json"),
        "out": pathlib.Path("result"),
        "panorama": None,
        "output_width": 8192,
        "row_chunk": 128,
    }
    received: list[LayerFusionConfig] = []
    monkeypatch.setattr(layers_cli, "fuse", received.append)
    layers_cli.main(
        [
            "--predictions",
            "custom_predictions",
            "--concepts",
            "custom.json",
            "--out",
            "custom_out",
            "--panorama",
            "pano.jpg",
            "--output-width",
            "4096",
            "--row-chunk",
            "32",
        ]
    )
    assert received == [
        LayerFusionConfig(
            predictions=pathlib.Path("custom_predictions"),
            concepts=pathlib.Path("custom.json"),
            out=pathlib.Path("custom_out"),
            panorama=pathlib.Path("pano.jpg"),
            output_width=4096,
            row_chunk=32,
        )
    ]


def test_panorama_defaults_and_forwarding(monkeypatch: pytest.MonkeyPatch) -> None:
    required = ["--panorama", "pano.jpg", "--out", "result"]
    assert vars(panorama_cli.arguments(required)) == {
        "panorama": pathlib.Path("pano.jpg"),
        "out": pathlib.Path("result"),
        "model": MODEL,
        "dense_revision": None,
        "device": "auto",
        "backend": "mask2former",
        "concepts": None,
        "view_size": DEFAULT_VIEW_SIZE,
        "inference_size": DEFAULT_INFERENCE_SIZE,
        "concept_resolution": 1008,
        "concept_threshold": 0.35,
        "prompt_batch": 32,
        "gate_min_pixels": DEFAULT_GATE_MIN_PIXELS,
        "output_width": 8192,
        "force": False,
        "sam_revision": None,
        "sam_repository_commit": None,
        "production": False,
    }
    received: list[PanoramaRunConfig] = []
    monkeypatch.setattr(panorama_cli, "run", received.append)
    panorama_cli.main(
        [
            "--panorama",
            "custom.jpg",
            "--out",
            "custom_out",
            "--model",
            "checkpoint",
            "--dense-revision",
            PRODUCTION_REVISION,
            "--device",
            "cuda",
            "--backend",
            "hybrid",
            "--concepts",
            "concepts.json",
            "--view-size",
            "900",
            "--inference-size",
            "700",
            "--concept-resolution",
            "800",
            "--concept-threshold",
            "0.42",
            "--prompt-batch",
            "12",
            "--gate-min-pixels",
            "321",
            "--output-width",
            "4096",
            "--force",
            "--sam-revision",
            "3" * 40,
            "--sam-repository-commit",
            "4" * 40,
            "--production",
        ]
    )
    assert received == [
        PanoramaRunConfig(
            panorama=pathlib.Path("custom.jpg"),
            out=pathlib.Path("custom_out"),
            model="checkpoint",
            dense_revision=PRODUCTION_REVISION,
            device="cuda",
            backend="hybrid",
            concepts=pathlib.Path("concepts.json"),
            view_size=900,
            inference_size=700,
            concept_resolution=800,
            concept_threshold=0.42,
            prompt_batch=12,
            gate_min_pixels=321,
            output_width=4096,
            force=True,
            sam_revision="3" * 40,
            sam_repository_commit="4" * 40,
            production=True,
        )
    ]


def test_alignment_defaults_and_forwarding(monkeypatch: pytest.MonkeyPatch) -> None:
    required = [
        "--mesh",
        "mesh.ply",
        "--semantics",
        "semantics.npz",
        "--semantics-json",
        "semantics.json",
        "--pose",
        "pose.json",
        "--out",
        "result",
    ]
    assert vars(align_cli.arguments(required)) == {
        "mesh": pathlib.Path("mesh.ply"),
        "semantics": pathlib.Path("semantics.npz"),
        "semantics_json": pathlib.Path("semantics.json"),
        "pose": pathlib.Path("pose.json"),
        "panorama": None,
        "out": pathlib.Path("result"),
        "bins": 1024,
        "maxiter": 600,
        "minimum_skyline_distance": 8.0,
        "skyline_percentile": 90.0,
        "smoothing_size": 11,
        "dz_bounds": (-3.0, 3.0),
        "fit_bias": (0.0, 0.0),
        "seeds": list(DEFAULT_SEEDS),
        "ground_from_mesh": True,
        "ground_patch_m": 3.0,
        "camera_height_m": None,
        "sky_conflict": True,
        "sky_conflict_width": 512,
        "profile": False,
        "profile_tolerance_deg": 0.02,
    }
    received: list[AlignmentConfig] = []
    monkeypatch.setattr(align_cli, "run_alignment", received.append)
    align_cli.main(
        [
            "--mesh",
            "custom.ply",
            "--semantics",
            "custom.npz",
            "--semantics-json",
            "custom.json",
            "--pose",
            "custom_pose.json",
            "--panorama",
            "pano.jpg",
            "--out",
            "custom_out",
            "--bins",
            "256",
            "--maxiter",
            "90",
            "--minimum-skyline-distance",
            "4.5",
            "--skyline-percentile",
            "75",
            "--smoothing-size",
            "7",
            "--dz-bounds",
            "-1.5",
            "2.5",
            "--fit-bias",
            "-0.2",
            "0.3",
            "--seeds",
            "2",
            "8",
            "--no-ground-from-mesh",
            "--ground-patch-m",
            "1.25",
            "--camera-height-m",
            "1.7",
            "--no-sky-conflict",
            "--sky-conflict-width",
            "300",
            "--profile",
            "--profile-tolerance-deg",
            "0.04",
        ]
    )
    assert received == [
        AlignmentConfig(
            mesh=pathlib.Path("custom.ply"),
            semantics=pathlib.Path("custom.npz"),
            semantics_json=pathlib.Path("custom.json"),
            pose=pathlib.Path("custom_pose.json"),
            panorama=pathlib.Path("pano.jpg"),
            out=pathlib.Path("custom_out"),
            bins=256,
            maxiter=90,
            minimum_skyline_distance=4.5,
            skyline_percentile=75.0,
            smoothing_size=7,
            dz_bounds=(-1.5, 2.5),
            fit_bias=(-0.2, 0.3),
            seeds=(2, 8),
            ground_from_mesh=False,
            ground_patch_m=1.25,
            camera_height_m=1.7,
            sky_conflict=False,
            sky_conflict_width=300,
            profile=True,
            profile_tolerance_deg=0.04,
        )
    ]
