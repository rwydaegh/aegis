from __future__ import annotations

import pathlib

import pytest

import build_fishnet_surface
import build_inhouse_mesh
import build_propagation_blends
import crop_fused_semantics
import project_semantics
import remesh_support_mesh


@pytest.mark.parametrize(
    "script",
    ("build_inhouse_mesh.py", "remesh_support_mesh.py", "project_semantics.py"),
)
def test_blender_runners_add_the_study_directory_before_package_imports(script: str) -> None:
    source = (pathlib.Path(__file__).resolve().parents[1] / script).read_text(encoding="utf-8")
    assert source.index("sys.path.insert") < source.index("from semantic_twin")


def test_inhouse_mesh_runner_builds_package_config(monkeypatch) -> None:
    captured = []
    monkeypatch.setattr(build_inhouse_mesh.inhouse_mesh_build, "build_inhouse_mesh", captured.append)

    build_inhouse_mesh.main(
        ["--tiles", "tiles", "--out", "mesh.ply", "--crop-radius-m", "130", "--blend", "inspect.blend"]
    )

    config = captured[0]
    assert config.tiles == pathlib.Path("tiles")
    assert config.out == pathlib.Path("mesh.ply")
    assert config.crop_radius_m == 130.0
    assert config.blend == pathlib.Path("inspect.blend")


def test_support_remesh_runner_builds_package_config(monkeypatch) -> None:
    captured = []
    monkeypatch.setattr(remesh_support_mesh.support_remesh, "remesh_support_mesh", captured.append)

    remesh_support_mesh.main(
        [
            "--mesh",
            "source.ply",
            "--out",
            "remeshed.ply",
            "--voxel-size-m",
            "0.5",
            "--solidify-m",
            "0.4",
            "--collapse-ratio",
            "0.25",
            "--collapse-stage",
            "before",
            "--adaptivity",
            "0.2",
            "--planar-angle-deg",
            "2",
        ]
    )

    config = captured[0]
    assert config.mesh == pathlib.Path("source.ply")
    assert config.voxel_size_m == 0.5
    assert config.solidify_m == 0.4
    assert config.collapse_ratio == 0.25
    assert config.collapse_stage == "before"
    assert config.adaptivity == 0.2
    assert config.planar_angle_deg == 2.0


def test_fishnet_runner_builds_package_config(monkeypatch) -> None:
    captured = []
    monkeypatch.setattr(build_fishnet_surface.fishnet_build, "build_fishnet_surface", captured.append)

    build_fishnet_surface.main(
        [
            "--mesh",
            "mesh.ply",
            "--pose",
            "pose.json",
            "--views",
            "views",
            "--mesh-depth",
            "depth",
            "--depth-compare",
            "comparison",
            "--semantics-json",
            "semantics.json",
            "--out",
            "out",
            "--yaws",
            "45",
            "135",
            "--baseline",
        ]
    )

    config = captured[0]
    assert config.mesh == pathlib.Path("mesh.ply")
    assert config.depth_compare == pathlib.Path("comparison")
    assert config.yaws == (45, 135)
    assert config.baseline


def test_fused_crop_runner_builds_package_config(monkeypatch) -> None:
    captured = []
    monkeypatch.setattr(crop_fused_semantics.fused_semantic_crops, "crop_fused_semantics", captured.append)

    crop_fused_semantics.main(
        [
            "--semantics",
            "semantics",
            "--panorama",
            "panorama.jpg",
            "--out",
            "out",
            "--yaws",
            "20",
            "220",
            "--pitch",
            "-5",
            "--fov-deg",
            "80",
            "--size",
            "512",
            "--equirect-width",
            "4096",
        ]
    )

    config = captured[0]
    assert config.panorama == pathlib.Path("panorama.jpg")
    assert config.yaws == (20, 220)
    assert config.pitch == -5.0
    assert config.fov_deg == 80.0
    assert config.size == 512
    assert config.equirect_width == 4096


def test_semantic_projection_runner_builds_package_config(monkeypatch) -> None:
    captured = []
    monkeypatch.setattr(project_semantics.semantic_projection, "project_semantics", captured.append)

    project_semantics.main(
        [
            "--mesh",
            "mesh.ply",
            "--semantics",
            "semantics.npz",
            "--semantics-json",
            "semantics.json",
            "--pose",
            "pose.json",
            "--out",
            "out",
            "--min-confidence",
            "0.6",
        ]
    )

    config = captured[0]
    assert config.mesh == pathlib.Path("mesh.ply")
    assert config.semantics == pathlib.Path("semantics.npz")
    assert config.min_confidence == 0.6


def test_propagation_blends_runner_builds_package_config(monkeypatch) -> None:
    captured = []
    monkeypatch.setattr(
        build_propagation_blends.propagation_blends_build,
        "build_propagation_blends",
        captured.append,
    )

    result = build_propagation_blends.main(
        [
            "--sites",
            "korenmarkt",
            "milan_duomo",
            "--locations",
            "8",
            "--paths",
            "90",
            "--rays",
            "1000",
            "--draw-radius-m",
            "75",
            "--samples",
            "16",
            "--resolution-scale",
            "0.5",
            "--skip-render",
            "--gpu",
            "--retrace",
            "--out",
            "out",
            "--archive",
            "bundle.zip",
        ]
    )

    config = captured[0]
    assert result == 0
    assert config.sites == ("korenmarkt", "milan_duomo")
    assert config.locations == 8
    assert config.paths == 90
    assert config.rays == 1000
    assert config.draw_radius_m == 75.0
    assert config.samples == 16
    assert config.resolution_scale == 0.5
    assert config.skip_render and config.gpu and config.retrace
    assert config.out == pathlib.Path("out")
    assert config.archive == pathlib.Path("bundle.zip")
