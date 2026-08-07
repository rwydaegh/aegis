from __future__ import annotations

import pathlib

import build_surface_atlas
from semantic_twin.cli import surface_atlas as surface_atlas_cli
from semantic_twin.scene import surface_atlas_builder


def test_legacy_driver_reexports_package_implementation() -> None:
    for name in (
        "DEFAULT_OUT",
        "REQUIRED_RASTERS",
        "VEGETATION_RASTERS",
        "SurfaceAtlasBuildOptions",
        "_camera_provenance",
        "_concept_catalogue_record",
        "_semantic_artifact_reasons",
        "_semantics_directory",
        "_validate_catalogue_identity",
        "_vegetation_evidence_summary",
    ):
        assert getattr(build_surface_atlas, name) is getattr(surface_atlas_builder, name)
    assert build_surface_atlas.arguments is surface_atlas_cli.arguments


def test_legacy_driver_is_a_thin_cli_compatibility_wrapper() -> None:
    path = pathlib.Path(build_surface_atlas.__file__)

    # Keep this as an architectural guard, not a formatting checksum.  A blank
    # line or compatibility export must not fail an otherwise thin wrapper.
    assert len(path.read_text(encoding="utf-8").splitlines()) <= 80
    assert build_surface_atlas.build.__module__ == "build_surface_atlas"
    assert surface_atlas_builder.build.__module__ == "semantic_twin.scene.surface_atlas_builder"


def test_legacy_main_keeps_the_historical_summary(monkeypatch, capsys) -> None:
    captured: dict[str, object] = {}

    def fake_build(site: str, options: build_surface_atlas.SurfaceAtlasBuildOptions) -> dict[str, object]:
        captured["site"] = site
        captured["options"] = options
        return {
            "atlas": {"observed_triangle_count": 12},
            "camera_ids": ["pano_00", "pano_01"],
            "artifact": {"path": "/tmp/atlas.npz"},
        }

    monkeypatch.setattr(build_surface_atlas, "build", fake_build)

    assert build_surface_atlas.main(["--site", "korenmarkt"]) == 0

    assert captured["site"] == "korenmarkt"
    assert isinstance(captured["options"], build_surface_atlas.SurfaceAtlasBuildOptions)
    assert capsys.readouterr().out == "wrote 12 observed triangles from 2 cameras to /tmp/atlas.npz\n"


def test_surface_atlas_cli_threads_cohort_and_semantics_selection(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_build(site: str, options: build_surface_atlas.SurfaceAtlasBuildOptions) -> dict[str, object]:
        captured["site"] = site
        captured["options"] = options
        return {"atlas": {"observed_triangle_count": 1}, "camera_ids": [], "artifact": {"path": "atlas.npz"}}

    monkeypatch.setattr(build_surface_atlas, "build", fake_build)

    assert (
        build_surface_atlas.main(
            [
                "--site",
                "toulouse_capitole",
                "--cohort-dir",
                "data/panorama_cohorts/toulouse_capitole_2018-05",
                "--semantics-dirname",
                "semantics_sam3_revision",
            ]
        )
        == 0
    )

    options = captured["options"]
    assert isinstance(options, build_surface_atlas.SurfaceAtlasBuildOptions)
    assert options.cohort_dir == pathlib.Path("data/panorama_cohorts/toulouse_capitole_2018-05")
    assert options.semantics_dirname == "semantics_sam3_revision"
