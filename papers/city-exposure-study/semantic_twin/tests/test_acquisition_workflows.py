"""Behavioral tests for the acquisition package workflows."""

from __future__ import annotations

import json
from types import SimpleNamespace

from semantic_twin.acquire import site_panoramas
from semantic_twin.acquire.site_panoramas import FetchOptions, fetch_site_panoramas
from semantic_twin.acquire.source import PanoramaPose
from semantic_twin.screening import Candidate
from semantic_twin import screening_workflow
from semantic_twin.vision import registration_repair
from semantic_twin.vision.registration_repair import RepairOptions, reregister_site


class FakeStreetView:
    def __init__(self, metadata):
        self.reply = metadata
        self.metadata_calls = []

    def create_session(self):
        return {
            "expiry": "2099-01-01T00:00:00Z",
            "tileWidth": 512,
            "tileHeight": 512,
            "imageFormat": "jpeg",
            "session": "private-token",
        }

    def metadata(self, *, pano_id):
        self.metadata_calls.append(pano_id)
        return self.reply


def test_fetch_uses_cached_native_zoom_and_writes_exact_request_accounting(tmp_path, monkeypatch):
    screening = tmp_path / "screening.json"
    screening.write_text(json.dumps({"rows": [{"key": "test-site"}]}))
    out = tmp_path / "panoramas"
    cached = out / "pano_19_cached-id"
    cached.mkdir(parents=True)
    (cached / "metadata.json").write_text(json.dumps({"imageWidth": 8192, "imageHeight": 4096, "tileWidth": 512}))
    (cached / "panorama_z4.jpg").write_bytes(b"cached")

    fresh_metadata = {
        "panoId": "fresh-id",
        "date": "2024-03",
        "imageWidth": 4096,
        "imageHeight": 2048,
        "tileWidth": 512,
    }
    client = FakeStreetView(fresh_metadata)
    selected = [
        {"pano_id": "cached-id"},
        {"pano_id": "fresh-id"},
    ]
    provenance = {"selection": "fixture", "selected": 2}
    selection_options = []
    downloads = []

    def fake_select(row, options):
        selection_options.append((row, options))
        return selected, provenance

    def fake_download(client_arg, metadata, directory, **kwargs):
        downloads.append((client_arg, metadata, directory, kwargs))
        destination = directory / f"panorama_z{kwargs['zoom']}.jpg"
        destination.write_bytes(b"fresh")
        return destination

    pose = PanoramaPose(
        position_enu_m=(1.0, 2.0, 3.0),
        position_wgs84=(51.0, 3.0),
        heading_deg=90.0,
        tilt_deg=90.0,
        roll_deg=0.0,
        camera_height_m=2.5,
    )
    monkeypatch.setattr(
        site_panoramas,
        "load_scene",
        lambda _path: {"name": "test-site", "camera_ground_z_m": 0.5},
    )
    monkeypatch.setattr(site_panoramas, "load_support_mesh", lambda _scene, root: (object(), object()))
    monkeypatch.setattr(site_panoramas, "select", fake_select)
    monkeypatch.setattr(site_panoramas, "google_api_key", lambda: "secret")
    monkeypatch.setattr(site_panoramas, "StreetViewTiles", lambda key: client if key == "secret" else None)
    monkeypatch.setattr(site_panoramas, "pose_from_metadata", lambda *_args, **_kwargs: pose)
    monkeypatch.setattr(site_panoramas, "download_panorama", fake_download)

    manifest = fetch_site_panoramas(
        tmp_path / "scene.json",
        FetchOptions(count=2, zoom=5, screening=screening, workers=3, out_root=out),
    )

    assert client.metadata_calls == ["fresh-id"]
    assert len(downloads) == 1
    _, downloaded_metadata, fresh_dir, download_options = downloads[0]
    assert downloaded_metadata == fresh_metadata
    assert fresh_dir.name == "pano_01_fresh-id"
    assert download_options == {"zoom": 3, "workers": 3, "max_tiles": 40}
    assert manifest == {
        "site": "test-site",
        "zoom": 5,
        "panorama_zoom": {"pano_19_cached-id": 4, "pano_01_fresh-id": 3},
        "panorama_dirs": ["pano_19_cached-id", "pano_01_fresh-id"],
        "selection": provenance,
        "approximate_requests": 34,
    }
    manifest_text = (out / "walk_manifest.json").read_text()
    assert manifest_text.endswith("\n")
    assert json.loads(manifest_text) == manifest
    assert json.loads((fresh_dir / "session.json").read_text()) == {
        "expiry": "2099-01-01T00:00:00Z",
        "tileWidth": 512,
        "tileHeight": 512,
        "imageFormat": "jpeg",
    }
    assert json.loads((fresh_dir / "pose_initial.json").read_text())["position_enu_m"] == [1.0, 2.0, 3.0]
    assert selection_options[0][0] == {"key": "test-site"}
    assert selection_options[0][1].count == 2


def make_registration_station(root, site="test-site", name="pano_00_a"):
    station = root / "data" / "panoramas" / site / name
    (station / "semantics").mkdir(parents=True)
    (station / "alignment").mkdir()
    (station / "pose_initial.json").write_text("{}")
    (station / "semantics" / "panorama_semantics.npz").write_bytes(b"fixture")
    return station


def test_registration_repair_backs_up_and_records_support_provenance(tmp_path, monkeypatch):
    mesh = tmp_path / "data" / "geometry" / "test-site" / "inhouse_leaf_250m.ply"
    mesh.parent.mkdir(parents=True)
    mesh.write_bytes(b"mesh")
    mesh.with_suffix(".json").write_text(json.dumps({"format_version": 3}))
    station = make_registration_station(tmp_path)
    old_pose = {
        "crop_m": 130,
        "position_enu_m": [0.0, 0.0, 2.5],
        "skyline_score_mean_deg": 4.0,
    }
    aligned = station / "alignment" / "pose_aligned.json"
    aligned.write_text(json.dumps(old_pose))
    calls = []

    def fake_register(folder, support_mesh, **kwargs):
        calls.append((folder, support_mesh, kwargs))
        (folder / "alignment" / "pose_aligned.json").write_text(
            json.dumps({"position_enu_m": [1.0, 2.0, 3.0], "skyline_score_mean_deg": 1.25})
        )
        return ["align"]

    monkeypatch.setattr(registration_repair, "register", fake_register)
    changed = reregister_site(
        RepairOptions(
            site="test-site",
            crop_m=250,
            dz_bounds=(-1.5, 3.0),
            root_dir=tmp_path,
        )
    )

    assert changed == ["pano_00_a"]
    assert json.loads((station / "alignment" / "pose_aligned_before_130m.json").read_text()) == old_pose
    repaired = json.loads(aligned.read_text())
    assert repaired["crop_m"] == 250
    assert repaired["support_mesh"] == "data/geometry/test-site/inhouse_leaf_250m.ply"
    assert "cannot sit below the pavement" in repaired["dz_bounds_rationale"]
    assert calls == [
        (
            station,
            mesh,
            {
                "dry_run": False,
                "dz_bounds": (-1.5, 3.0),
                "root_dir": tmp_path,
                "semantics_dirname": "semantics",
            },
        )
    ]


def test_registration_dry_run_changes_no_pose_and_makes_no_backup(tmp_path, monkeypatch):
    mesh = tmp_path / "data" / "geometry" / "test-site" / "inhouse_leaf_250m.ply"
    mesh.parent.mkdir(parents=True)
    mesh.write_bytes(b"mesh")
    mesh.with_suffix(".json").write_text(json.dumps({"format_version": 3}))
    station = make_registration_station(tmp_path)
    old_pose = {"crop_m": 130, "position_enu_m": [0.0, 0.0, 2.5]}
    aligned = station / "alignment" / "pose_aligned.json"
    aligned.write_text(json.dumps(old_pose))
    calls = []

    def fake_register(folder, support_mesh, **kwargs):
        calls.append((folder, support_mesh, kwargs))
        return ["python", "align"]

    monkeypatch.setattr(registration_repair, "register", fake_register)
    changed = reregister_site(RepairOptions(site="test-site", crop_m=250, dry_run=True, root_dir=tmp_path))

    assert changed == []
    assert json.loads(aligned.read_text()) == old_pose
    assert not list((station / "alignment").glob("pose_aligned_before_*m.json"))
    assert calls[0][2] == {
        "dry_run": True,
        "dz_bounds": None,
        "root_dir": tmp_path,
        "semantics_dirname": "semantics",
    }


def screening_row(candidate, *, connected, walk_count, spacing, requests):
    return {
        "key": candidate.key,
        "name": candidate.name,
        "country": candidate.country,
        "panorama_count": walk_count + 3,
        "distinct_dates": 1,
        "walk_date": "2024-03",
        "walk_count": walk_count,
        "walk_spacing_m": spacing,
        "walk_span_m": 80.0,
        "walk_azimuth_spread": 0.75,
        "walk_coverage": 0.9,
        "connected": connected,
        "recent_walk": None,
        "requests": requests,
    }


def test_screening_success_ranks_and_writes_the_public_schema(tmp_path, monkeypatch):
    candidates = [
        Candidate("broken", "Broken square", "Nowhere", 1.0, 2.0, "broken"),
        Candidate("whole", "Whole square", "Nowhere", 3.0, 4.0, "whole"),
    ]
    source = SimpleNamespace(requests=47)
    calls = []
    clock = iter((10.0, 11.0, 20.0, 22.0))

    def fake_screen(source_arg, candidate, **kwargs):
        calls.append((source_arg, candidate, kwargs))
        if candidate.key == "broken":
            return screening_row(candidate, connected=False, walk_count=80, spacing=2.0, requests=30)
        return screening_row(candidate, connected=True, walk_count=25, spacing=4.0, requests=17)

    monkeypatch.setattr(screening_workflow, "CANDIDATES", candidates)
    monkeypatch.setattr(screening_workflow, "screening_source", lambda key: source if key == "secret" else None)
    monkeypatch.setattr(screening_workflow, "screen", fake_screen)
    monkeypatch.setattr(screening_workflow.time, "time", lambda: next(clock))

    document = screening_workflow.screen_candidates(
        tmp_path / "screening",
        api_key="secret",
        radius_m=75.0,
        max_panoramas=123,
        workers=6,
    )

    assert document is not None
    assert set(document) == {
        "generator",
        "screen_radius_m",
        "max_panoramas",
        "total_metadata_requests",
        "candidates_screened",
        "rows",
    }
    assert document["generator"] == "semantic_twin/screen_cities.py"
    assert document["screen_radius_m"] == 75.0
    assert document["max_panoramas"] == 123
    assert document["total_metadata_requests"] == 47
    assert document["candidates_screened"] == 2
    assert [row["key"] for row in document["rows"]] == ["whole", "broken"]
    assert [row["rank"] for row in document["rows"]] == [1, 2]
    assert {row["key"]: row["seconds"] for row in document["rows"]} == {"whole": 2.0, "broken": 1.0}
    assert [call[1].key for call in calls] == ["broken", "whole"]
    assert all(call[0] is source for call in calls)
    assert all(call[2] == {"radius_m": 75.0, "max_panoramas": 123, "workers": 6} for call in calls)

    output = tmp_path / "screening"
    json_text = (output / "screening.json").read_text()
    assert json_text.endswith("\n")
    assert json.loads(json_text) == document
    assert (output / "screening_table.md").read_text() == screening_workflow.markdown_table(document["rows"])
