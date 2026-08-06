"""The re-registration driver, which rewrites poses and so has to be reversible."""

from __future__ import annotations

import json

import numpy as np
import pytest

from semantic_twin.vision import registration_repair
from semantic_twin.vision.registration_repair import BACKUP_SUFFIX, panorama_image, register, stations, summarise


def station(root, site, name, *, semantics=True, pose=True, image="panorama_z5.jpg"):
    folder = root / "data" / "panoramas" / site / name
    folder.mkdir(parents=True)
    if pose:
        (folder / "pose_initial.json").write_text(json.dumps({"position_enu_m": [0.0, 0.0, 2.5]}))
    if semantics:
        (folder / "semantics").mkdir()
        np.savez(folder / "semantics" / "panorama_semantics.npz", entity=np.zeros((4, 8), dtype=np.int16))
        (folder / "semantics" / "semantics.json").write_text(json.dumps({"backend": "mask2former"}))
    if image:
        (folder / image).write_bytes(b"")
    return folder


def test_a_station_missing_its_segmentation_is_not_offered_for_registration(tmp_path, monkeypatch):
    station(tmp_path, "tokyo_hachiko", "pano_00_a")
    station(tmp_path, "tokyo_hachiko", "pano_01_b", semantics=False)
    monkeypatch.setattr(registration_repair.paths, "root", lambda: tmp_path)
    assert [f.name for f in stations("tokyo_hachiko")] == ["pano_00_a"]


def test_a_station_missing_its_initial_pose_is_not_offered_either(tmp_path, monkeypatch):
    station(tmp_path, "tokyo_hachiko", "pano_00_a")
    station(tmp_path, "tokyo_hachiko", "pano_01_b", pose=False)
    monkeypatch.setattr(registration_repair.paths, "root", lambda: tmp_path)
    assert [f.name for f in stations("tokyo_hachiko")] == ["pano_00_a"]


def test_a_single_panorama_site_is_read_from_the_top_of_its_directory(tmp_path, monkeypatch):
    root = tmp_path / "data" / "panoramas" / "milan_duomo"
    (root / "semantics").mkdir(parents=True)
    (root / "pose_initial.json").write_text("{}")
    np.savez(root / "semantics" / "panorama_semantics.npz", entity=np.zeros((2, 2)))
    monkeypatch.setattr(registration_repair.paths, "root", lambda: tmp_path)
    assert [f.name for f in stations("milan_duomo")] == ["milan_duomo"]


def test_an_unknown_site_is_refused_rather_than_returning_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(registration_repair.paths, "root", lambda: tmp_path)
    with pytest.raises(SystemExit, match="no panorama directory"):
        stations("atlantis")


def test_the_panorama_is_found_at_whatever_zoom_it_was_acquired(tmp_path, monkeypatch):
    monkeypatch.setattr(registration_repair.paths, "root", lambda: tmp_path)
    # Times Square is zoom 4 and every other site is zoom 5, so the driver
    # cannot hard code either.
    four = station(tmp_path, "newyork_timessquare", "pano_00_a", image="panorama_z4.jpg")
    five = station(tmp_path, "tokyo_hachiko", "pano_00_a", image="panorama_z5.jpg")
    assert panorama_image(four).name == "panorama_z4.jpg"
    assert panorama_image(five).name == "panorama_z5.jpg"


def test_a_station_with_no_stitched_image_still_registers(tmp_path, monkeypatch):
    monkeypatch.setattr(registration_repair.paths, "root", lambda: tmp_path)
    folder = station(tmp_path, "tokyo_hachiko", "pano_00_a", image=None)
    assert panorama_image(folder) is None
    command = register(folder, tmp_path / "mesh.ply", dry_run=True)
    assert "--panorama" not in command, "the diagnostic render is optional, the fit is not"


def test_the_dz_clamp_reaches_the_optimiser(tmp_path, monkeypatch):
    monkeypatch.setattr(registration_repair.paths, "root", lambda: tmp_path)
    folder = station(tmp_path, "tokyo_hachiko", "pano_00_a")
    command = register(folder, tmp_path / "mesh.ply", dry_run=True, dz_bounds=(-1.5, 3.0))
    assert command[command.index("--dz-bounds") + 1 : command.index("--dz-bounds") + 3] == ["-1.5", "3.0"]


def test_no_clamp_is_passed_when_none_is_asked_for(tmp_path, monkeypatch):
    monkeypatch.setattr(registration_repair.paths, "root", lambda: tmp_path)
    folder = station(tmp_path, "tokyo_hachiko", "pano_00_a")
    assert "--dz-bounds" not in register(folder, tmp_path / "mesh.ply", dry_run=True)


def test_a_dry_run_names_the_mesh_it_would_fit_against(tmp_path, monkeypatch):
    monkeypatch.setattr(registration_repair.paths, "root", lambda: tmp_path)
    folder = station(tmp_path, "tokyo_hachiko", "pano_00_a")
    mesh = tmp_path / "data" / "geometry" / "tokyo_hachiko" / "inhouse_leaf_250m.ply"
    command = register(folder, mesh, dry_run=True)
    assert str(mesh) in command
    assert command[command.index("--out") + 1].endswith("alignment")


def test_the_backup_name_records_the_crop_the_old_pose_came_from():
    # A pose file carries no crop until this driver writes one, so the first
    # backup at a site is explicitly "unknown" rather than silently "130".
    assert BACKUP_SUFFIX.format(crop="unknown") == "pose_aligned_before_unknownm.json"
    assert BACKUP_SUFFIX.format(crop=130) == "pose_aligned_before_130m.json"


def test_the_summary_reports_a_pose_that_is_inside_the_geometry():
    pose = {
        "skyline_score_mean_deg": 6.53,
        "position_enu_m": [0.0, 0.0, 50.95],
        "skyline_dz_at_bound": True,
        "sky_conflict": {"sky_with_mesh_hit_fraction": 1.0, "conflict_median_range_m": 0.5},
    }
    line = summarise(pose)
    assert "6.53" in line and "sky 1.00 at 0.5 m" in line and "dz at bound True" in line


def test_the_summary_does_not_invent_a_sky_conflict_it_was_not_given():
    pose = {"skyline_score_mean_deg": 1.42, "position_enu_m": [0.0, 0.0, 53.9]}
    assert "sky conflict unknown" in summarise(pose)


def test_an_unregistered_station_summarises_as_such():
    assert summarise({}) == "not registered"
