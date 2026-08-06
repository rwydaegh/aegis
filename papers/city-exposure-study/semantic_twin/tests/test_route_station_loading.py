"""Portable, identity-checked station bindings for panorama routes."""

from __future__ import annotations

import hashlib
import json
import pathlib

import pytest

from semantic_twin.walk.route import load_admitted_stations


def _write_station(
    root: pathlib.Path,
    site: str,
    directory: str,
    station: str,
    metadata: dict,
    *,
    report_fields: dict | None = None,
    canonical_image_id: str | None = None,
) -> tuple[pathlib.Path, bytes]:
    folder = root / "data" / "panoramas" / directory / station
    folder.mkdir(parents=True)
    payload = json.dumps(metadata, sort_keys=True).encode()
    (folder / "metadata.json").write_bytes(payload)
    report = root / "outputs" / "site_semantics" / site
    report.mkdir(parents=True)
    entry = {
        "station": station,
        "folder": f"/home/admin/aegis/papers/city-exposure-study/semantic_twin/data/panoramas/{directory}/{station}",
        "position_enu_m": [1.0, 2.0, 3.0],
        "residual_deg": 0.75,
        **(report_fields or {}),
    }
    (report / "walk_semantic_250m.json").write_text(json.dumps({"stations_admitted": [entry]}))
    image_id = str(canonical_image_id or metadata.get("panoId") or metadata.get("id"))
    screening = root / "outputs" / "city_screening"
    screening.mkdir(parents=True)
    (screening / "screening.json").write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "key": site,
                        "panoramas": [{"pano_id": image_id, "east_m": 1.0, "north_m": 2.0, "links": []}],
                    }
                ]
            }
        )
    )
    return folder, payload


def test_a_frozen_absolute_path_is_provenance_and_the_active_root_supplies_the_capture(
    tmp_path: pathlib.Path,
) -> None:
    station = "pano_00_4CxfyuveHLZwX5MG"
    image_id = "4CxfyuveHLZwX5MGoFES4A"
    folder, payload = _write_station(
        tmp_path,
        "prague_staromestske",
        "prague_staromestske",
        station,
        {"panoId": image_id, "date": "2014-06"},
    )

    loaded = load_admitted_stations("prague_staromestske", root=tmp_path)

    assert loaded[0]["node"] == image_id
    assert loaded[0]["provider"] == "google_streetview"
    assert loaded[0]["folder"] == str(folder)
    assert loaded[0]["folder_provenance"].startswith("/home/admin/aegis/")
    assert loaded[0]["metadata_sha256"] == hashlib.sha256(payload).hexdigest()


def test_a_missing_capture_at_the_active_root_is_refused_even_if_the_recorded_absolute_path_exists_elsewhere(
    tmp_path: pathlib.Path,
) -> None:
    report = tmp_path / "outputs" / "site_semantics" / "prague_staromestske"
    report.mkdir(parents=True)
    report.joinpath("walk_semantic_250m.json").write_text(
        json.dumps(
            {
                "stations_admitted": [
                    {
                        "station": "pano_00_4CxfyuveHLZwX5MG",
                        "folder": "/home/admin/aegis/data/panoramas/prague_staromestske/pano_00_4CxfyuveHLZwX5MG",
                        "capture_id": "4CxfyuveHLZwX5MGoFES4A",
                        "position_enu_m": [1.0, 2.0, 3.0],
                    }
                ]
            }
        )
    )

    with pytest.raises(FileNotFoundError, match="recorded folder is provenance"):
        load_admitted_stations("prague_staromestske", root=tmp_path)


def test_a_metadata_hash_mismatch_is_refused(tmp_path: pathlib.Path) -> None:
    _write_station(
        tmp_path,
        "prague_staromestske",
        "prague_staromestske",
        "pano_00_4CxfyuveHLZwX5MG",
        {"panoId": "4CxfyuveHLZwX5MGoFES4A"},
        report_fields={"metadata_sha256": "0" * 64},
    )

    with pytest.raises(ValueError, match="metadata SHA-256 mismatch"):
        load_admitted_stations("prague_staromestske", root=tmp_path)


def test_a_capture_identity_mismatch_is_refused(tmp_path: pathlib.Path) -> None:
    _write_station(
        tmp_path,
        "prague_staromestske",
        "prague_staromestske",
        "pano_00_4CxfyuveHLZwX5MG",
        {"panoId": "another_capture_identifier"},
        canonical_image_id="4CxfyuveHLZwX5MGoFES4A",
    )

    with pytest.raises(ValueError, match="capture identity mismatch"):
        load_admitted_stations("prague_staromestske", root=tmp_path)


def test_a_same_prefix_full_capture_replacement_is_refused_for_a_legacy_report(tmp_path: pathlib.Path) -> None:
    prefix = "abcdefghijklmnop"
    _write_station(
        tmp_path,
        "prague_staromestske",
        "prague_staromestske",
        f"pano_00_{prefix}",
        {"panoId": f"{prefix}DIFFERENT"},
        canonical_image_id=f"{prefix}ORIGINAL",
    )

    with pytest.raises(ValueError, match="provider link graph says"):
        load_admitted_stations("prague_staromestske", root=tmp_path)


def test_a_provider_mismatch_is_refused(tmp_path: pathlib.Path) -> None:
    _write_station(
        tmp_path,
        "prague_staromestske",
        "prague_staromestske",
        "pano_00_4CxfyuveHLZwX5MG",
        {"id": "4CxfyuveHLZwX5MGoFES4A"},
    )

    with pytest.raises(ValueError, match="provider mismatch"):
        load_admitted_stations("prague_staromestske", root=tmp_path)


@pytest.mark.parametrize(
    ("site", "directory", "station", "metadata", "provider"),
    [
        (
            "prague_staromestske",
            "prague_staromestske",
            "pano_00_4CxfyuveHLZwX5MG",
            {"panoId": "4CxfyuveHLZwX5MGoFES4A"},
            "google_streetview",
        ),
        (
            "korenmarkt",
            "korenmarkt_walk",
            "walk_00_986493819697753",
            {"id": "986493819697753", "sequence": "walk"},
            "mapillary",
        ),
    ],
)
def test_prague_and_korenmarkt_resolve_their_current_registered_imagery_sets(
    tmp_path: pathlib.Path,
    site: str,
    directory: str,
    station: str,
    metadata: dict,
    provider: str,
) -> None:
    folder, _ = _write_station(tmp_path, site, directory, station, metadata)

    loaded = load_admitted_stations(site, root=tmp_path)

    assert loaded[0]["folder"] == str(folder)
    assert loaded[0]["provider"] == provider
