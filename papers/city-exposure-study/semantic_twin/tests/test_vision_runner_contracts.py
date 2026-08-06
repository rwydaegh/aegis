from __future__ import annotations

import importlib
import pathlib
import sys

import pytest


def _runner(name: str):
    """Import an optional runner only when its contract test executes."""
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as error:
        pytest.skip(f"{name} needs optional dependency {error.name}")


def test_script_compatibility_exports_remain_available() -> None:
    build_dynamic_bodies = _runner("build_dynamic_bodies")
    compare_mesh_depth = _runner("compare_mesh_depth")
    infer_unidepth = _runner("infer_unidepth")
    comparison_names = {
        "AGREEMENT_Z",
        "BLOCKER_Z",
        "COLOURS",
        "DECISIONS",
        "DEFAULT_REFERENCE_LOG_SIGMA",
        "DYNAMIC_OBJECT_LABELS",
        "MAX_CROSS_VIEW_SCALE_SPREAD",
        "MIN_DISAGREEMENT_LOG_SIGMA",
        "OBJECT_IDS",
        "PLAUSIBLE_SCALE_BAND",
        "SECOND_OPINION_LOG_SIGMA",
        "STATIC_CALIBRATION_IDS",
        "STATIC_CALIBRATION_LABELS",
        "classify",
        "depth_log_sigma",
        "fit_log_scale",
        "scale_plausibility",
    }
    assert comparison_names == set(compare_mesh_depth.__all__)
    assert all(hasattr(compare_mesh_depth, name) for name in comparison_names)
    assert "UNCERTAINTY_FIELD" in infer_unidepth.__all__
    assert infer_unidepth.UNCERTAINTY_FIELD
    assert build_dynamic_bodies.USABLE_DEPTH_DECISIONS == (1, 2, 5)


def test_compare_depth_wrapper_reexports_package_objects() -> None:
    wrapper = _runner("compare_mesh_depth")
    package = importlib.import_module("semantic_twin.vision.depth_comparison")
    cli = importlib.import_module("semantic_twin.cli.depth_comparison")
    names = (
        "AGREEMENT_Z",
        "BLOCKER_Z",
        "COLOURS",
        "DECISIONS",
        "DEFAULT_REFERENCE_LOG_SIGMA",
        "DYNAMIC_OBJECT_LABELS",
        "MAX_CROSS_VIEW_SCALE_SPREAD",
        "MIN_DISAGREEMENT_LOG_SIGMA",
        "OBJECT_IDS",
        "PLAUSIBLE_SCALE_BAND",
        "SECOND_OPINION_LOG_SIGMA",
        "STATIC_CALIBRATION_IDS",
        "STATIC_CALIBRATION_LABELS",
        "classify",
        "compare_mesh_depth",
        "depth_log_sigma",
        "fit_log_scale",
        "scale_plausibility",
    )
    assert all(getattr(wrapper, name) is getattr(package, name) for name in names)
    assert wrapper.arguments is cli.arguments


def test_compare_depth_package_parser_preserves_cli_values(monkeypatch) -> None:
    package = importlib.import_module("semantic_twin.cli.depth_comparison")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "compare_mesh_depth.py",
            "--views",
            "views",
            "--mesh-depth",
            "mesh-depth",
            "--unidepth",
            "unidepth",
            "--sam-labels",
            "labels",
            "--out",
            "out",
            "--yaws",
            "15",
            "195",
            "--on-implausible-scale",
            "classify",
        ],
    )

    config = package.arguments()

    assert config.views == pathlib.Path("views")
    assert config.mesh_depth == pathlib.Path("mesh-depth")
    assert config.yaws == [15, 195]
    assert config.on_implausible_scale == "classify"


def test_compare_depth_runner_builds_package_config(monkeypatch) -> None:
    compare_mesh_depth = _runner("compare_mesh_depth")
    captured = []
    monkeypatch.setattr(compare_mesh_depth, "compare_mesh_depth", captured.append)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "compare_mesh_depth.py",
            "--views",
            "views",
            "--mesh-depth",
            "mesh-depth",
            "--unidepth",
            "unidepth",
            "--depth-anything",
            "depth-anything",
            "--sam-labels",
            "labels",
            "--semantics-json",
            "semantics.json",
            "--out",
            "out",
            "--yaws",
            "45",
            "135",
            "--reference-log-sigma",
            "0.2",
            "--plausible-scale-band",
            "0.4",
            "2.5",
            "--max-cross-view-scale-spread",
            "1.7",
            "--second-opinion-log-sigma",
            "0.3",
            "--on-implausible-scale",
            "degrade",
        ],
    )

    compare_mesh_depth.main()

    config = captured[0]
    assert config.views == pathlib.Path("views")
    assert config.depth_anything == pathlib.Path("depth-anything")
    assert config.yaws == (45, 135)
    assert config.reference_log_sigma == 0.2
    assert config.plausible_scale_band == (0.4, 2.5)
    assert config.max_cross_view_scale_spread == 1.7
    assert config.second_opinion_log_sigma == 0.3
    assert config.on_implausible_scale == "degrade"


def test_depth_model_runners_forward_cli_values(monkeypatch) -> None:
    infer_depth_anything = _runner("infer_depth_anything")
    infer_unidepth = _runner("infer_unidepth")
    unidepth_calls = []
    anything_calls = []
    monkeypatch.setattr(infer_unidepth, "run_unidepth", lambda *args, **kwargs: unidepth_calls.append((args, kwargs)))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "infer_unidepth.py",
            "--views",
            "views",
            "--out",
            "out",
            "--model",
            "model-a",
            "--resolution-level",
            "5",
            "--reference-log-sigma",
            "0.25",
            "--limit",
            "3",
        ],
    )
    infer_unidepth.main()

    monkeypatch.setattr(
        infer_depth_anything,
        "run_depth_anything",
        lambda *args, **kwargs: anything_calls.append((args, kwargs)),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["infer_depth_anything.py", "--views", "views", "--out", "out", "--model", "model-b"],
    )
    infer_depth_anything.main()

    assert unidepth_calls == [
        (
            (pathlib.Path("views"), pathlib.Path("out")),
            {"model_name": "model-a", "resolution_level": 5.0, "reference_log_sigma": 0.25, "limit": 3},
        )
    ]
    assert anything_calls == [((pathlib.Path("views"), pathlib.Path("out")), {"model_name": "model-b"})]


def test_mesh_depth_runner_builds_package_config(monkeypatch) -> None:
    raycast_mesh_depth = _runner("raycast_mesh_depth")
    captured = []
    monkeypatch.setattr(raycast_mesh_depth, "render_mesh_depth", captured.append)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "raycast_mesh_depth.py",
            "--mesh",
            "mesh.glb",
            "--pose",
            "pose.json",
            "--views",
            "views",
            "--out",
            "out",
            "--yaws",
            "10",
            "20",
            "--pitch",
            "-5",
            "--fov-deg",
            "80",
            "--ground-lock-height-m",
            "1.6",
        ],
    )

    raycast_mesh_depth.main()

    config = captured[0]
    assert config.mesh == pathlib.Path("mesh.glb")
    assert config.yaws == (10, 20)
    assert config.pitch == -5.0
    assert config.fov_deg == 80.0
    assert config.ground_lock_height_m == 1.6


def test_body_runners_build_package_configs(monkeypatch) -> None:
    build_dynamic_bodies = _runner("build_dynamic_bodies")
    infer_sam3_body = _runner("infer_sam3_body")
    inference = []
    placement = []
    monkeypatch.setattr(infer_sam3_body, "infer_bodies", inference.append)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "infer_sam3_body.py",
            "--views",
            "views",
            "--semantics-json",
            "semantics.json",
            "--out",
            "out",
            "--view-names",
            "a",
            "b",
            "--checkpoint",
            "model.ckpt",
            "--mhr-path",
            "mhr",
            "--fov-deg",
            "75",
            "--min-pixels",
            "20",
            "--min-height-px",
            "10",
            "--max-people-per-view",
            "2",
        ],
    )
    infer_sam3_body.main()

    monkeypatch.setattr(build_dynamic_bodies, "place_dynamic_bodies", placement.append)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build_dynamic_bodies.py",
            "--reconstructions",
            "reconstructions",
            "--pose",
            "pose.json",
            "--mesh",
            "mesh.glb",
            "--depth-compare",
            "compare",
            "--mesh-depth",
            "mesh-depth",
            "--out",
            "out",
        ],
    )
    build_dynamic_bodies.main()

    inference_config = inference[0]
    assert inference_config.view_names == ("a", "b")
    assert inference_config.checkpoint == pathlib.Path("model.ckpt")
    assert inference_config.mhr_path == pathlib.Path("mhr")
    assert inference_config.fov_deg == 75.0
    assert inference_config.min_pixels == 20
    assert inference_config.min_height_px == 10
    assert inference_config.max_people_per_view == 2

    placement_config = placement[0]
    assert placement_config.reconstructions == pathlib.Path("reconstructions")
    assert placement_config.depth_compare == pathlib.Path("compare")
    assert placement_config.mesh_depth == pathlib.Path("mesh-depth")


def test_vision_study_runners_build_typed_configs(monkeypatch) -> None:
    facade = _runner("build_facade_crops")
    texture = _runner("build_texture_evidence")
    walk = _runner("build_walk_twin")

    facade_calls = []
    monkeypatch.setattr(facade, "build_facade_crops", facade_calls.append)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build_facade_crops.py",
            "--out",
            "facades",
            "--size",
            "256",
            "--stride",
            "64",
            "--min-building-fraction",
            "0.8",
            "--per-view",
            "3",
            "--per-wall",
            "4",
            "--per-patch",
            "1",
            "--patch-separation-m",
            "7",
            "--crop-radius-m",
            "120",
            "--max-range-m",
            "75",
        ],
    )
    facade.main()
    facade_config = facade_calls[0]
    assert facade_config.out == pathlib.Path("facades")
    assert (
        facade_config.size,
        facade_config.stride,
        facade_config.min_building_fraction,
        facade_config.per_view,
        facade_config.per_wall,
        facade_config.per_patch,
        facade_config.patch_separation_m,
        facade_config.crop_radius_m,
        facade_config.max_range_m,
    ) == (256, 64, 0.8, 3, 4, 1, 7.0, 120.0, 75.0)

    texture_calls = []
    monkeypatch.setattr(texture, "run_texture_study", texture_calls.append)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build_texture_evidence.py",
            "--tiles",
            "tiles",
            "--mesh",
            "mesh.ply",
            "--mesh-manifest",
            "mesh.json",
            "--panorama-semantics",
            "semantics.npz",
            "--semantics-json",
            "semantics.json",
            "--panorama",
            "panorama.jpg",
            "--pose",
            "pose.json",
            "--concepts",
            "concepts.json",
            "--output",
            "texture-out",
            "--grid-height",
            "512",
            "--folds",
            "4",
            "--seed",
            "19",
        ],
    )
    texture.main()
    texture_config = texture_calls[0]
    assert texture_config.tiles == pathlib.Path("tiles")
    assert texture_config.mesh == pathlib.Path("mesh.ply")
    assert texture_config.mesh_manifest == pathlib.Path("mesh.json")
    assert texture_config.panorama_semantics == pathlib.Path("semantics.npz")
    assert texture_config.semantics_json == pathlib.Path("semantics.json")
    assert texture_config.panorama == pathlib.Path("panorama.jpg")
    assert texture_config.pose == pathlib.Path("pose.json")
    assert texture_config.concepts == pathlib.Path("concepts.json")
    assert texture_config.output == pathlib.Path("texture-out")
    assert (texture_config.grid_height, texture_config.folds, texture_config.seed) == (512, 4, 19)

    walk_calls = []
    monkeypatch.setattr(walk, "run_stage", walk_calls.append)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build_walk_twin.py",
            "saturate",
            "--scene",
            "scene.json",
            "--mesh",
            "mesh.ply",
            "--out",
            "walk-out",
            "--panorama-root",
            "panoramas",
            "--permutations",
            "12",
            "--workers",
            "2",
            "--radius-m",
            "85",
            "--recast",
        ],
    )
    walk.main()
    walk_config = walk_calls[0]
    assert walk_config.stage == "saturate"
    assert walk_config.scene == "scene.json"
    assert walk_config.mesh == "mesh.ply"
    assert walk_config.out == "walk-out"
    assert walk_config.panorama_root == "panoramas"
    assert (walk_config.permutations, walk_config.workers, walk_config.radius_m, walk_config.recast) == (
        12,
        2,
        85.0,
        True,
    )


def test_material_vlm_utility_runners_forward_cli_values(monkeypatch) -> None:
    analysis = _runner("analyse_material_vlm")
    blinding = _runner("blind_facade_crops")
    batches = _runner("make_vlm_batches")

    analysis_calls = []
    monkeypatch.setattr(analysis, "analyse_material_vlm", lambda *args: analysis_calls.append(args))
    monkeypatch.setattr(sys, "argv", ["analyse_material_vlm.py", "--out", "analysis", "--frequency-ghz", "28"])
    analysis.main()
    assert analysis_calls == [(pathlib.Path("analysis"), 28.0)]

    blind_calls = []
    monkeypatch.setattr(blinding, "blind_facade_crops", blind_calls.append)
    monkeypatch.setattr(sys, "argv", ["blind_facade_crops.py", "--out", "blind"])
    blinding.main()
    assert blind_calls == [pathlib.Path("blind")]

    batch_calls = []
    monkeypatch.setattr(batches, "make_vlm_batches", lambda *args, **kwargs: batch_calls.append((args, kwargs)))
    monkeypatch.setattr(
        sys,
        "argv",
        ["make_vlm_batches.py", "--out", "batches", "--draws", "3", "--batches", "4", "--seed", "23"],
    )
    batches.main()
    assert batch_calls == [((pathlib.Path("batches"),), {"draws": 3, "batches": 4, "seed": 23})]
