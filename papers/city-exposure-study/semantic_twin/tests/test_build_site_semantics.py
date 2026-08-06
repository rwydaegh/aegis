from __future__ import annotations

import importlib
import json
import types

import numpy as np
import pytest

import build_site_semantics
import semantic_twin.scene.site_semantics as site_semantics
from semantic_twin.scene.site_fishnets import pose_verdict
from semantic_twin.scene.site_semantics import _modal_class, _prior_semantics, station_verdict, stations
from semantic_twin.vision.provenance import AdmissionGate, Registration
from semantic_twin.vision.surface_atlas import REQUIRED_SEMANTIC_RASTERS

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
    document: dict = {"skyline_score_mean_deg": residual, "skyline_dz_at_bound": False}
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
    assert verdict["sky_conflict_state"] == "large sky-mesh mismatch"


def test_a_missing_sky_conflict_is_recorded_as_unknown_and_refused():
    verdict = station_verdict(pose(1.1, sky_hit=None), **GATE)
    assert verdict["sky_conflict_state"] == "unknown"
    assert not verdict["admitted"]


def test_semantic_builder_refuses_a_boundary_optimum():
    document = pose(0.2)
    document["skyline_dz_at_bound"] = True
    verdict = station_verdict(document, **GATE)
    assert not verdict["admitted"]
    assert "altitude search bound" in " ".join(verdict["refused_because"])


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


def write_hybrid(folder, dirname="semantics_sam3_revision"):
    """Write the smallest selected hybrid product accepted by station gating."""
    selected = folder / dirname
    selected.mkdir(parents=True)
    arrays = {name: np.zeros((2, 4), dtype=np.float32) for name in REQUIRED_SEMANTIC_RASTERS}
    np.savez_compressed(selected / "panorama_semantics.npz", **arrays)
    (selected / "semantics.json").write_text(json.dumps({"backend": "hybrid"}))
    return selected


def build_with_selected_semantics(root, name, dirname="semantics_sam3_revision"):
    folder = root / name
    (folder / "alignment").mkdir(parents=True)
    (folder / "alignment" / "pose_aligned.json").write_text(json.dumps(pose(1.0) | {"position_enu_m": [0.0, 0.0, 2.0]}))
    return folder, write_hybrid(folder, dirname)


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


def test_station_artifacts_are_reported_separately(tmp_path):
    folder = tmp_path / "data" / "panoramas" / "prague_staromestske" / "pano_05_missing"
    folder.mkdir(parents=True)

    admitted, refused = stations("prague_staromestske", root=tmp_path, **GATE)

    assert admitted == []
    assert refused[0]["refused_because"] == [
        "missing pose artifact: alignment/pose_aligned.json",
        "missing dense semantic artifact: semantics/panorama_semantics.npz",
        "missing semantic metadata artifact: semantics/semantics.json",
    ]


def test_explicit_hybrid_directory_is_discovered_without_legacy_semantics(tmp_path):
    panoramas = tmp_path / "data" / "panoramas"
    folder, selected = build_with_selected_semantics(panoramas / "korenmarkt", ".")
    # The flat Korenmarkt layout used to be discoverable only through this
    # legacy directory, even when another evidence product was selected.
    assert not (folder / "semantics").exists()  # nosec B101 - pytest assertion

    admitted, refused = stations(
        "korenmarkt",
        root=tmp_path,
        semantics_dirname="semantics_sam3_revision",
        **GATE,
    )

    assert refused == []  # nosec B101 - pytest assertion
    assert [record["station"] for record in admitted] == ["korenmarkt"]  # nosec B101 - pytest assertion
    assert admitted[0]["semantic_evidence_directory"] == str(selected)  # nosec B101 - pytest assertion


def test_explicit_hybrid_directory_refuses_partial_product_without_legacy_fallback(tmp_path):
    panoramas = tmp_path / "data" / "panoramas"
    folder = build(panoramas / "prague_staromestske", "pano_00_complete_legacy")
    selected = folder / "semantics_sam3_revision"
    selected.mkdir()
    (selected / "semantics.json").write_text(json.dumps({"backend": "hybrid"}))
    np.savez_compressed(
        selected / "panorama_semantics.npz",
        entity=np.zeros((2, 4)),
        confidence=np.ones((2, 4)),
    )

    admitted, refused = stations(
        "prague_staromestske",
        root=tmp_path,
        semantics_dirname="semantics_sam3_revision",
        **GATE,
    )

    assert admitted == []  # nosec B101 - pytest assertion
    assert refused[0]["semantic_evidence_directory"] == str(selected)  # nosec B101 - pytest assertion
    assert refused[0]["refused_because"] == [  # nosec B101 - pytest assertion
        "incomplete SAM material artifact: material_concept, material_confidence, material_source, "
        "rf_material, rf_material_prior_mass"
    ]


def test_explicit_hybrid_directory_reports_corrupt_artifacts_without_mixing(tmp_path):
    panoramas = tmp_path / "data" / "panoramas"
    folder = build(panoramas / "prague_staromestske", "pano_00_complete_legacy")
    selected = folder / "semantics_sam3_revision"
    selected.mkdir()
    (selected / "semantics.json").write_text("not json")
    (selected / "panorama_semantics.npz").write_bytes(b"not an npz")

    admitted, refused = stations(
        "prague_staromestske",
        root=tmp_path,
        semantics_dirname="semantics_sam3_revision",
        **GATE,
    )

    assert admitted == []  # nosec B101 - pytest assertion
    reasons = refused[0]["refused_because"]
    assert reasons[0].startswith("invalid semantic metadata artifact: semantics.json")  # nosec B101
    assert reasons[1].startswith("invalid dense semantic artifact: panorama_semantics.npz")  # nosec B101
    assert reasons[2].startswith("invalid SAM material artifact: panorama_semantics.npz")  # nosec B101


def test_explicit_hybrid_directory_never_borrows_a_missing_npz_from_legacy(tmp_path):
    panoramas = tmp_path / "data" / "panoramas"
    folder = build(panoramas / "prague_staromestske", "pano_00_complete_legacy")
    selected = folder / "semantics_sam3_revision"
    selected.mkdir()
    (selected / "semantics.json").write_text(json.dumps({"backend": "hybrid"}))

    admitted, refused = stations(
        "prague_staromestske",
        root=tmp_path,
        semantics_dirname="semantics_sam3_revision",
        **GATE,
    )

    assert admitted == []  # nosec B101 - pytest assertion
    assert refused[0]["refused_because"] == [  # nosec B101 - pytest assertion
        "missing dense semantic artifact: panorama_semantics.npz",
        "missing SAM material artifact: panorama_semantics.npz",
    ]


def test_prague_pano05_inside_geometry_regression():
    document = pose(0.481, sky_hit=1.0, conflict_range=0.559)
    verdict = station_verdict(document, **GATE)
    assert verdict["sky_conflict_state"] == "inside the geometry"
    assert not verdict["admitted"]


@pytest.mark.parametrize(
    ("fraction", "distance"),
    [(0.5, 1.999), (0.500001, 1.999), (0.500001, 2.0), (0.9, 60.0), (0.9997, 4.95)],
)
def test_semantic_and_fishnet_builders_share_the_central_verdict(tmp_path, fraction, distance):
    document = pose(0.3, sky_hit=fraction, conflict_range=distance)
    pose_path = tmp_path / "pose_aligned.json"
    pose_path.write_text(json.dumps(document))
    central = Registration.from_pose(document).verdict(AdmissionGate())
    semantic = station_verdict(document, **GATE)
    fishnet = pose_verdict(
        pose_path,
        max_residual_deg=GATE["max_residual_deg"],
        max_sky_hit=GATE["max_sky_conflict"],
        min_conflict_range_m=GATE["min_conflict_range_m"],
    )
    assert semantic["admitted"] is central.admitted
    assert fishnet["admitted"] is central.admitted
    assert semantic["sky_conflict_state"] == central.sky_conflict_state
    assert fishnet["sky_conflict_state"] == central.sky_conflict_state
