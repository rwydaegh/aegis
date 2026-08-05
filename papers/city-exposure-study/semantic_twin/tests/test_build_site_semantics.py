from __future__ import annotations

import importlib
import json
import types

import numpy as np
import pytest

import build_site_semantics
import semantic_twin.scene.site_semantics as site_semantics
from semantic_twin.scene.site_semantics import _modal_class, _prior_semantics, station_verdict, stations

GATE = {"max_residual_deg": 4.0, "max_sky_conflict": 0.5, "min_conflict_range_m": 2.0}


def test_module_import_does_not_require_ignored_station_data(monkeypatch):
    monkeypatch.setattr(site_semantics.paths, "panorama_stations", lambda *_args, **_kwargs: ())

    imported = importlib.reload(site_semantics)

    assert imported.SITES


def test_material_prior_keeps_the_original_korenmarkt_source(tmp_path, monkeypatch):
    site = types.SimpleNamespace(stations=lambda: (tmp_path / "korenmarkt",))
    monkeypatch.setattr(site_semantics.Site, "get", lambda name: site)

    assert _prior_semantics() == tmp_path / "korenmarkt" / "semantics" / "semantics.json"


def pose(residual: float, sky_hit: float | None = 0.02, conflict_range: float = 30.0) -> dict:
    document: dict = {"skyline_score_mean_deg": residual}
    if sky_hit is not None:
        document["sky_conflict"] = {
            "sky_with_mesh_hit_fraction": sky_hit,
            "conflict_median_range_m": conflict_range,
        }
    return document


def test_a_clean_pose_inside_the_residual_gate_is_admitted():
    verdict = station_verdict(pose(1.3), **GATE)
    assert verdict["admitted"]
    assert verdict["sky_conflict_state"] == "clear"
    assert verdict["refused_because"] == []


def test_a_pose_outside_the_residual_gate_is_refused():
    verdict = station_verdict(pose(9.9), **GATE)
    assert not verdict["admitted"]
    assert "skyline residual" in verdict["refused_because"][0]


def test_the_residual_gate_alone_admits_a_camera_that_is_inside_a_wall():
    # The whole reason for the second test. This is the shape of six of the
    # poses in the repository: a low residual and a sky that is entirely mesh
    # at arm's length.
    inside = pose(2.7, sky_hit=1.0, conflict_range=0.9)
    assert inside["skyline_score_mean_deg"] <= GATE["max_residual_deg"]
    verdict = station_verdict(inside, **GATE)
    assert not verdict["admitted"]
    assert verdict["sky_conflict_state"] == "inside the geometry"
    assert "inside a building" in verdict["refused_because"][0]


def test_a_distant_sky_conflict_is_not_a_camera_inside_the_geometry():
    # A tall neighbour the segmentation called sky is a segmentation error, not
    # a pose error, and it should not cost the station.
    verdict = station_verdict(pose(1.1, sky_hit=0.9, conflict_range=60.0), **GATE)
    assert verdict["admitted"]
    assert verdict["sky_conflict_state"] == "clear"


def test_a_missing_sky_conflict_is_recorded_as_unknown_rather_than_passed():
    verdict = station_verdict(pose(1.1, sky_hit=None), **GATE)
    assert verdict["sky_conflict_state"] == "unknown"
    assert verdict["admitted"]


def test_the_pose_sigma_is_the_horizontal_part_of_the_seed_covariance():
    document = pose(1.0)
    document["pose_uncertainty"] = {"covariance": np.diag([0.09, 0.16, 1.0, 4.0]).tolist()}
    assert station_verdict(document, **GATE)["position_sigma_m"] == pytest.approx(0.5)


def test_modal_class_picks_the_most_common_class_per_face():
    face = np.array([0, 0, 0, 2, 2, 2, 3], dtype=np.int32)
    label = np.array([7, 7, 4, 1, 5, 5, 9], dtype=np.int16)
    modal = _modal_class(face, label, face_count=5, classes=16)
    assert modal.tolist() == [7, -1, 5, 9, -1]


def test_modal_class_breaks_a_tie_on_the_lowest_class_index():
    face = np.array([0, 0], dtype=np.int32)
    label = np.array([5, 1], dtype=np.int16)
    assert _modal_class(face, label, face_count=1, classes=16).tolist() == [1]


def test_modal_class_leaves_an_unseen_face_at_minus_one():
    modal = _modal_class(np.zeros(0, dtype=np.int32), np.zeros(0, dtype=np.int16), face_count=3, classes=8)
    assert modal.tolist() == [-1, -1, -1]


def test_modal_class_agrees_with_the_dense_table_it_replaces():
    rng = np.random.default_rng(4)
    faces, classes = 40, 12
    face = rng.integers(0, faces, 2000).astype(np.int32)
    label = rng.integers(0, classes, 2000).astype(np.int16)
    tally = np.zeros((faces, classes), dtype=np.int32)
    np.add.at(tally, (face, label), 1)
    dense = np.where(tally.sum(axis=1) > 0, tally.argmax(axis=1), -1)
    assert _modal_class(face, label, faces, classes).tolist() == dense.tolist()


def test_the_command_builds_package_options(tmp_path, monkeypatch):
    captured = {}

    def fake_build(site, options):
        captured.update(site=site, options=options)
        return None

    monkeypatch.setattr(build_site_semantics, "_build", fake_build)
    result = build_site_semantics.main(
        [
            "--site",
            "korenmarkt",
            "--crop-m",
            "250",
            "--grid-height",
            "768",
            "--block-rows",
            "64",
            "--workers",
            "3",
            "--max-residual-deg",
            "3.5",
            "--max-sky-conflict",
            "0.4",
            "--min-conflict-range-m",
            "1.5",
            "--out",
            str(tmp_path),
        ]
    )

    assert result == 0
    assert captured["site"] == "korenmarkt"
    assert captured["options"].crop_m == 250
    assert captured["options"].grid_height == 768
    assert captured["options"].block_rows == 64
    assert captured["options"].workers == 3
    assert captured["options"].max_residual_deg == 3.5
    assert captured["options"].max_sky_conflict == 0.4
    assert captured["options"].min_conflict_range_m == 1.5
    assert captured["options"].out_root == tmp_path


def build(root, name, *, residual=1.0):
    """A registered, segmented station directory, thin but complete."""
    folder = root / name
    (folder / "alignment").mkdir(parents=True)
    (folder / "semantics").mkdir(parents=True)
    (folder / "alignment" / "pose_aligned.json").write_text(
        json.dumps(pose(residual) | {"position_enu_m": [0.0, 0.0, 2.0]})
    )
    (folder / "semantics" / "panorama_semantics.npz").write_bytes(b"")
    (folder / "semantics" / "semantics.json").write_text(json.dumps({"backend": "mask2former"}))
    return folder


def test_a_companion_campaign_is_read_as_the_same_site(tmp_path):
    panoramas = tmp_path / "data" / "panoramas"
    build(panoramas / "korenmarkt", "pano_00_a")
    for index in range(3):
        build(panoramas / "korenmarkt_walk", f"walk_{index:02d}_b")
    admitted, refused = stations("korenmarkt", root=tmp_path, **GATE)
    assert refused == []
    assert [entry["station"] for entry in admitted] == ["pano_00_a", "walk_00_b", "walk_01_b", "walk_02_b"]


def test_a_site_without_a_companion_reads_only_its_own_directory(tmp_path):
    panoramas = tmp_path / "data" / "panoramas"
    build(panoramas / "madrid_plazamayor", "pano_00_a")
    build(panoramas / "korenmarkt_walk", "walk_00_b")
    admitted, _ = stations("madrid_plazamayor", root=tmp_path, **GATE)
    assert [entry["station"] for entry in admitted] == ["pano_00_a"]


def test_the_probe_of_a_rejected_indoor_capture_is_not_a_station(tmp_path):
    panoramas = tmp_path / "data" / "panoramas"
    build(panoramas / "tokyo_hachiko", "pano_00_a")
    build(panoramas / "tokyo_hachiko", "indoor_2018-05_00_c")
    admitted, refused = stations("tokyo_hachiko", root=tmp_path, **GATE)
    assert [entry["station"] for entry in admitted] == ["pano_00_a"]
    assert refused == []


def test_a_walk_manifest_beside_the_stations_is_not_counted_as_one(tmp_path):
    # Every multi panorama site carries a walk_manifest.json, which matches the
    # walk_ prefix and is a file. Counting it inflates the denominator in every
    # "n admitted of N" line without changing the answer, which is the worst
    # kind of wrong number.
    panoramas = tmp_path / "data" / "panoramas"
    build(panoramas / "prague_staromestske", "pano_00_a")
    (panoramas / "prague_staromestske" / "walk_manifest.json").write_text("{}")
    admitted, refused = stations("prague_staromestske", root=tmp_path, **GATE)
    assert [entry["station"] for entry in admitted] == ["pano_00_a"]
    assert refused == []
