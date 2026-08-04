from __future__ import annotations

import json

import numpy as np
import pytest

from semantic_twin.exposure import study as run_exposure
from semantic_twin.report.coverage import (
    CoverageReportConfig,
    CoverageReportEnvironment,
    LadderReportConfig,
    LadderReportEnvironment,
)


def test_report_uses_the_current_output_directory(tmp_path, monkeypatch):
    def fake_report(stem, output):
        assert output == tmp_path
        return output / f"{stem}_summary.json"

    monkeypatch.setattr(run_exposure, "OUTPUT", tmp_path)
    monkeypatch.setattr(run_exposure, "exposure_report", fake_report)

    assert run_exposure.report("trial") == tmp_path / "trial_summary.json"


def test_coverage_report_forwards_the_current_report_dependencies(tmp_path, monkeypatch):
    result = object()
    model_keys = ("model",)
    calls = []

    def rungs_for(site, crop_m, seed):
        return ()

    def key_for(site, crop_m, seed):
        return "key"

    def compare_to_baseline(baseline, values):
        return {}

    def fake_report(*args, **kwargs):
        calls.append((args, kwargs))
        return result

    monkeypatch.setattr(run_exposure, "OUTPUT", tmp_path)
    monkeypatch.setattr(run_exposure, "coverage_ladder", rungs_for)
    monkeypatch.setattr(run_exposure, "ladder_key", key_for)
    monkeypatch.setattr(run_exposure, "LADDER_MODELS", model_keys)
    monkeypatch.setattr(run_exposure, "_against_baseline", compare_to_baseline)
    monkeypatch.setattr(run_exposure, "write_coverage_report", fake_report)

    assert run_exposure.coverage_report(15.0e9, "_trial", site="site", crop_m=250, seed=9) is result
    assert calls == [
        (
            (
                CoverageReportConfig(15.0e9, "_trial", "site", 250, 9),
                CoverageReportEnvironment(tmp_path, rungs_for, key_for, model_keys, compare_to_baseline),
            ),
            {},
        )
    ]


def test_coverage_ladder_report_forwards_the_current_report_dependencies(tmp_path, monkeypatch):
    result = object()
    model_keys = ("model",)
    refused = {"missing": "reason"}
    failures = {"failed": "error"}
    calls = []

    def key_for(site, crop_m, seed):
        return "key"

    def one_value(values):
        return values[0]

    def spread(values):
        return {"values": values}

    def plotter(rows, path, crop_m, frequency_hz):
        return path

    def markdown(rows):
        return "table"

    def fake_report(*args, **kwargs):
        calls.append((args, kwargs))
        return result

    monkeypatch.setattr(run_exposure, "OUTPUT", tmp_path)
    monkeypatch.setattr(run_exposure, "ladder_key", key_for)
    monkeypatch.setattr(run_exposure, "LADDER_MODELS", model_keys)
    monkeypatch.setattr(run_exposure, "_one_value", one_value)
    monkeypatch.setattr(run_exposure, "_spread", spread)
    monkeypatch.setattr(run_exposure, "plot_cross_site_ladder", plotter)
    monkeypatch.setattr(run_exposure, "ladder_markdown", markdown)
    monkeypatch.setattr(run_exposure, "write_coverage_ladder_report", fake_report)

    assert (
        run_exposure.coverage_ladder_report(
            ["site"],
            250,
            (7, 9),
            15.0e9,
            tag_suffix="_trial",
            refused=refused,
            failures=failures,
        )
        is result
    )
    assert calls == [
        (
            (
                LadderReportConfig(["site"], 250, (7, 9), 15.0e9, "_trial", refused, failures),
                LadderReportEnvironment(tmp_path, key_for, model_keys, one_value, spread, plotter, markdown),
            ),
            {},
        )
    ]


def test_cross_city_report_forwards_the_current_report_dependencies(tmp_path, monkeypatch):
    result = object()
    sites_expected = ("site", "other")
    calls = []

    def fake_report(*args, **kwargs):
        calls.append((args, kwargs))
        return result

    monkeypatch.setattr(run_exposure, "OUTPUT", tmp_path)
    monkeypatch.setattr(run_exposure, "REFERENCE_S0_W_M2", 2.5)
    monkeypatch.setattr(run_exposure, "CROP_BOUND_NOTE", "bound note")
    monkeypatch.setattr(run_exposure, "write_cross_city_report", fake_report)

    assert (
        run_exposure.cross_city_report(["site"], 15.0e9, crop_m=250, tag_suffix="_trial", sites_expected=sites_expected)
        is result
    )
    assert calls == [
        (
            (["site"], 15.0e9),
            {
                "crop_m": 250,
                "tag_suffix": "_trial",
                "sites_expected": sites_expected,
                "output": tmp_path,
                "reference_s0_w_m2": 2.5,
                "crop_bound_note": "bound note",
            },
        )
    ]


def test_a_site_with_a_binding_at_that_crop_resolves(tmp_path, monkeypatch):
    monkeypatch.setattr(run_exposure, "SITE_SEMANTICS", tmp_path)
    site = tmp_path / "prague_staromestske"
    site.mkdir()
    (site / "walk_semantic_250m.npz").write_bytes(b"")
    assert run_exposure.site_walk_semantics("prague_staromestske", 250) is not None


def test_the_same_site_at_another_crop_does_not(tmp_path, monkeypatch):
    # A binding is indexed by triangle with no join key, so the crop radius is
    # part of its identity and a 250 m file must not answer for a 130 m run.
    monkeypatch.setattr(run_exposure, "SITE_SEMANTICS", tmp_path)
    site = tmp_path / "prague_staromestske"
    site.mkdir()
    (site / "walk_semantic_250m.npz").write_bytes(b"")
    assert run_exposure.site_walk_semantics("prague_staromestske", 130) is None


def test_korenmarkt_keeps_its_published_mapillary_binding_at_130_m(tmp_path, monkeypatch):
    monkeypatch.setattr(run_exposure, "SITE_SEMANTICS", tmp_path)
    legacy = tmp_path / "legacy.npz"
    legacy.write_bytes(b"")
    monkeypatch.setattr(run_exposure, "WALK_SEMANTIC", legacy)
    assert run_exposure.site_walk_semantics("korenmarkt", 130) == legacy


def test_korenmarkt_falls_through_to_its_own_binding_at_another_crop(tmp_path, monkeypatch):
    monkeypatch.setattr(run_exposure, "SITE_SEMANTICS", tmp_path)
    legacy = tmp_path / "legacy.npz"
    legacy.write_bytes(b"")
    monkeypatch.setattr(run_exposure, "WALK_SEMANTIC", legacy)
    site = tmp_path / "korenmarkt"
    site.mkdir()
    (site / "walk_semantic_250m.npz").write_bytes(b"")
    assert run_exposure.site_walk_semantics("korenmarkt", 250) == site / "walk_semantic_250m.npz"


def test_a_site_with_no_binding_resolves_to_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(run_exposure, "SITE_SEMANTICS", tmp_path)
    assert run_exposure.site_walk_semantics("krakow_rynek", 250) is None


def fishnet_at(root, site, *, mesh="data/geometry/{site}/inhouse_leaf_130m.ply", manifest="fishnet_manifest.json"):
    directory = root / "outputs" / f"{site}_fishnet_vistas"
    directory.mkdir(parents=True, exist_ok=True)
    np.savez(directory / "h+00_000_fishnet.npz", face_class=np.zeros(1))
    (directory / manifest).write_text(json.dumps({"site": site, "mesh": mesh.format(site=site)}))
    return directory


def test_the_fishnet_resolver_needs_a_surface_set_and_the_mesh_it_was_cut_against(tmp_path, monkeypatch):
    monkeypatch.setattr(run_exposure, "ROOT", tmp_path)
    directory = tmp_path / "outputs" / "milan_duomo_fishnet_vistas"
    directory.mkdir(parents=True)
    assert run_exposure.site_fishnet("milan_duomo") is None, "an empty directory is not a fishnet"

    fishnet_at(tmp_path, "milan_duomo")
    assert run_exposure.site_fishnet("milan_duomo") is None, "and neither is one without its mesh"

    mesh = tmp_path / "data" / "geometry" / "milan_duomo"
    mesh.mkdir(parents=True)
    (mesh / "inhouse_leaf_130m.ply").write_bytes(b"")
    resolved = run_exposure.site_fishnet("milan_duomo")
    assert resolved is not None
    assert resolved[0] == directory
    assert resolved[1] == mesh / "inhouse_leaf_130m.ply"


def test_the_mesh_comes_from_the_manifest_and_not_from_the_crop_being_run(tmp_path, monkeypatch):
    # Every fishnet in this repository was cut against the 130 m mesh. Pairing
    # it with the 250 m mesh because the run is 250 m would hand bind() two
    # different triangle numberings and it would join them without complaining.
    monkeypatch.setattr(run_exposure, "ROOT", tmp_path)
    fishnet_at(tmp_path, "newyork_timessquare")
    geometry = tmp_path / "data" / "geometry" / "newyork_timessquare"
    geometry.mkdir(parents=True)
    for crop in (130, 250):
        (geometry / f"inhouse_leaf_{crop}m.ply").write_bytes(b"")
    assert run_exposure.site_fishnet("newyork_timessquare")[1] == geometry / "inhouse_leaf_130m.ply"


def test_a_manifest_naming_a_bare_file_resolves_against_the_site_geometry(tmp_path, monkeypatch):
    monkeypatch.setattr(run_exposure, "ROOT", tmp_path)
    fishnet_at(tmp_path, "prague_staromestske", mesh="inhouse_leaf_130m.ply", manifest="site_fishnet_manifest.json")
    geometry = tmp_path / "data" / "geometry" / "prague_staromestske"
    geometry.mkdir(parents=True)
    (geometry / "inhouse_leaf_130m.ply").write_bytes(b"")
    assert run_exposure.site_fishnet("prague_staromestske")[1] == geometry / "inhouse_leaf_130m.ply"


def test_a_fishnet_with_no_manifest_at_all_does_not_resolve(tmp_path, monkeypatch):
    monkeypatch.setattr(run_exposure, "ROOT", tmp_path)
    directory = tmp_path / "outputs" / "madrid_plazamayor_fishnet_vistas"
    directory.mkdir(parents=True)
    np.savez(directory / "h+00_000_fishnet.npz", face_class=np.zeros(1))
    geometry = tmp_path / "data" / "geometry" / "madrid_plazamayor"
    geometry.mkdir(parents=True)
    (geometry / "inhouse_leaf_130m.ply").write_bytes(b"")
    assert run_exposure.site_fishnet("madrid_plazamayor") is None


def test_a_fishnet_written_one_level_down_is_named_rather_than_silently_missed(tmp_path, monkeypatch):
    # bind() globs the top of the directory and does not recurse, so surfaces in
    # a folder per panorama are built but unreachable. Returning None would read
    # as "not built yet" and send someone to rebuild what is already there.
    monkeypatch.setattr(run_exposure, "ROOT", tmp_path)
    nested = tmp_path / "outputs" / "newyork_timessquare_fishnet_vistas" / "pano_07_CAoSFkNJSE0wb2dL"
    nested.mkdir(parents=True)
    np.savez(nested / "h+00_000_fishnet.npz", face_class=np.zeros(1))
    with pytest.raises(ValueError, match="one level down"):
        run_exposure.site_fishnet("newyork_timessquare")


def test_a_flat_fishnet_beside_a_nested_one_still_resolves(tmp_path, monkeypatch):
    monkeypatch.setattr(run_exposure, "ROOT", tmp_path)
    directory = tmp_path / "outputs" / "newyork_timessquare_fishnet_vistas"
    (directory / "pano_07_CAoSFkNJSE0wb2dL").mkdir(parents=True)
    np.savez(directory / "pano_07_CAoSFkNJSE0wb2dL" / "h+00_000_fishnet.npz", face_class=np.zeros(1))
    np.savez(directory / "pano_07_CAoSFkNJSE0wb2dL_h+00_000_fishnet.npz", face_class=np.zeros(1))
    (directory / "site_fishnet_manifest.json").write_text(json.dumps({"mesh": "inhouse_leaf_130m.ply"}))
    mesh = tmp_path / "data" / "geometry" / "newyork_timessquare"
    mesh.mkdir(parents=True)
    (mesh / "inhouse_leaf_130m.ply").write_bytes(b"")
    assert run_exposure.site_fishnet("newyork_timessquare") == (directory, mesh / "inhouse_leaf_130m.ply")
