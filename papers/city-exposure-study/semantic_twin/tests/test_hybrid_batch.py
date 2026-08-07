from __future__ import annotations

import json
import pathlib
from types import SimpleNamespace

import numpy as np

from semantic_twin.cli import hybrid_batch


def _station(root: pathlib.Path, name: str) -> pathlib.Path:
    station = root / name
    station.mkdir(parents=True)
    (station / "panorama_z5.jpg").write_bytes(f"image-{name}".encode())
    return station


def test_walk_manifest_resolves_relative_panorama_dirs_and_deduplicates(tmp_path):
    first = _station(tmp_path, "pano_00_a")
    second = _station(tmp_path, "pano_01_b")
    manifest = tmp_path / "walk_manifest.json"
    manifest.write_text(json.dumps({"site": "test", "panorama_dirs": [first.name, second.name, first.name]}))

    assert hybrid_batch.read_station_sources(walk_manifest=manifest, stations_file=None) == [first, second]


def test_station_list_ignores_comments_and_blank_lines(tmp_path):
    first = _station(tmp_path, "pano_00_a")
    second = _station(tmp_path, "pano_01_b")
    source = tmp_path / "stations.txt"
    source.write_text(f"# selected\n{first.name}  # open sky\n\n{second.name}\n")

    assert hybrid_batch.read_station_sources(walk_manifest=None, stations_file=source) == [first, second]


def test_json_station_list_is_supported(tmp_path):
    first = _station(tmp_path, "pano_00_a")
    manifest = tmp_path / "stations.json"
    manifest.write_text(json.dumps([first.name]))

    assert hybrid_batch.read_station_sources(walk_manifest=manifest, stations_file=None) == [first]


def test_panorama_image_prefers_highest_zoom_over_legacy_fallback(tmp_path):
    station = tmp_path / "pano_00_a"
    station.mkdir()
    (station / "panorama.jpg").write_bytes(b"legacy")
    (station / "panorama_z4.jpg").write_bytes(b"zoom-four")
    expected = station / "panorama_z5.jpg"
    expected.write_bytes(b"zoom-five")

    assert hybrid_batch.panorama_image(station) == expected


def test_metadata_contract_rejects_wrong_source_and_accepts_complete_output(tmp_path, monkeypatch):
    station = _station(tmp_path, "pano_00_a")
    output = station / hybrid_batch.SEMANTICS_DIRNAME
    (output / "views").mkdir(parents=True)
    (output / "concepts").mkdir()
    concepts = tmp_path / "semantic_concepts.json"
    concepts.write_text('{"concepts": []}')
    contract = hybrid_batch._contract_for(concepts=concepts)
    contract["output_width"] = 8
    monkeypatch.setattr(
        hybrid_batch,
        "inference_views",
        lambda: (SimpleNamespace(name="one"), SimpleNamespace(name="two")),
    )

    arrays = {
        name: np.zeros((4, 8), dtype=np.float32)
        for name in ("entity", "rf_material", "material_concept", "material_source", "confidence")
    }
    np.savez_compressed(output / "panorama_semantics.npz", **arrays)
    for name in ("one", "two"):
        (output / "views" / f"{name}.jpg").write_bytes(b"view")
        np.save(output / "views" / f"{name}_labels.npy", np.zeros((2, 2), dtype=np.uint8))
        np.save(output / "views" / f"{name}_confidence.npy", np.zeros((2, 2), dtype=np.float16))
        np.savez(output / "concepts" / f"{name}.npz", cache_key=np.asarray("concept-key"))
    (output / "views" / "cache_settings.json").write_text(
        json.dumps(
            {
                "model": contract["model"],
                "inference_size": contract["inference_size"],
                "view_size": contract["view_size"],
                "panorama": hybrid_batch.file_digest(station / "panorama_z5.jpg"),
                "model_revision": {"resolved_revision": contract["dense_revision"]},
            }
        )
    )
    (output / "semantics.json").write_text(
        json.dumps(
            {
                "backend": "hybrid",
                "model": contract["model"],
                "model_revision": {"resolved_revision": contract["dense_revision"]},
                "view_size": contract["view_size"],
                "inference_size": contract["inference_size"],
                "output_width": contract["output_width"],
                "concept_backend": {
                    "model": hybrid_batch.SAM3_MODEL,
                    "revision": contract["sam_revision"],
                    "repository_commit": contract["sam_repository_commit"],
                },
                "concept_vocabulary": {"id_count": contract["concept_id_count"]},
                "concept_cache_key": "concept-key",
                "views": [{}, {}],
            }
        )
    )
    assert hybrid_batch._metadata_contract_valid(output, panorama=station / "panorama_z5.jpg", contract=contract)[0]

    cache = json.loads((output / "views" / "cache_settings.json").read_text())
    cache["panorama"] = "changed"
    (output / "views" / "cache_settings.json").write_text(json.dumps(cache))
    assert not hybrid_batch._metadata_contract_valid(output, panorama=station / "panorama_z5.jpg", contract=contract)[0]


def test_execute_writes_ledger_and_skips_only_after_sidecar(monkeypatch, tmp_path):
    station = _station(tmp_path, "pano_00_a")
    source = tmp_path / "stations.txt"
    source.write_text(f"{station.name}\n")
    concepts = tmp_path / "concepts.json"
    concepts.write_text("{}")
    job = tmp_path / "job.json"
    calls: list[pathlib.Path] = []

    def fake_config(path: pathlib.Path, *, concepts: pathlib.Path | None = None):
        return SimpleNamespace(panorama=path / "panorama_z5.jpg", out=path / hybrid_batch.SEMANTICS_DIRNAME)

    def fake_run(config):
        calls.append(config.panorama)
        config.out.mkdir(parents=True, exist_ok=True)
        (config.out / "semantics.json").write_text("{}")
        (config.out / "panorama_semantics.npz").write_bytes(b"arrays")
        valid_sidecar["value"] = True

    monkeypatch.setattr(hybrid_batch, "pipeline_config", fake_config)
    monkeypatch.setattr(hybrid_batch, "run", fake_run)
    monkeypatch.setattr(hybrid_batch, "_metadata_contract_valid", lambda *args, **kwargs: (True, "complete"))

    valid_sidecar = {"value": False}

    def fake_complete(path, **kwargs):
        return (valid_sidecar["value"], "complete" if valid_sidecar["value"] else "missing")

    monkeypatch.setattr(hybrid_batch, "complete_output", fake_complete)
    first = hybrid_batch.execute(stations_file=source, walk_manifest=None, job_manifest=job, concepts=concepts)
    assert calls == [station / "panorama_z5.jpg"]
    assert first["summary"]["completed"] == 1
    assert json.loads(job.read_text())["stations"][0]["status"] == "completed"

    second = hybrid_batch.execute(stations_file=source, walk_manifest=None, job_manifest=job, concepts=concepts)
    assert calls == [station / "panorama_z5.jpg"]
    assert second["summary"]["skipped_complete"] == 1
    assert second["stations"][0]["status"] == "skipped_complete"
