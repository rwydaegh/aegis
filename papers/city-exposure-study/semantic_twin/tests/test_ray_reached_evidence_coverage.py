from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from semantic_twin.cli import ray_reached_evidence_coverage as command
from semantic_twin.report.ray_reached_evidence_coverage import (
    CATEGORIES,
    RayReachedEvidenceCoverageError,
    build_report,
    write_ray_reached_evidence_coverage,
)


def _sha(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(payload).hexdigest()


def _body(value: float) -> dict[str, float]:
    return {"mean_sab_w_m2": value, "absorbed_power_w": value / 10.0, "sar_wb_w_kg": value / 100.0}


def _family(*, diffuse: bool, value: float) -> dict:
    categories = {
        category: {
            "event_count": 1 if category == "atlas_interface" else 0,
            "contribution": value if category == "atlas_interface" else 0.0,
            "body_coupled": _body(value) if category == "atlas_interface" else _body(0.0),
        }
        for category in CATEGORIES
    }
    return {
        "accepted_event_count" if diffuse else "event_count": 1,
        "contribution": value,
        "body_coupled": _body(value),
        "categories": categories,
    }


def _document() -> dict:
    identity = {"topology": "first_material_interaction_v1", "frequency_hz": 15_000_000_000}
    records = [
        {
            "site": "fixture",
            "standpoint": 0,
            "route_distance_m": 3.0,
            "direct": "N/A",
            "specular": _family(diffuse=False, value=2.0),
            "first_diffuse": _family(diffuse=True, value=1.0),
        }
    ]
    checks = {"status": "pass", "records": [{"site": "fixture", "standpoint": 0, "status": "pass"}]}
    return {
        "schema": "ray_reached_evidence_replay_v1",
        "authenticated": True,
        "complete": True,
        "identity": identity,
        "identity_sha256": _sha(identity),
        "source_hashes": {"replay_code": "a" * 64},
        "parity": checks,
        "closure": checks,
        "records": records,
    }


def test_category_and_body_closure_and_direct_na() -> None:
    report = build_report(_document())
    assert report["categories"] == list(CATEGORIES)
    assert report["pooled"]["direct"]["status"] == "N/A"
    assert report["pooled"]["specular"]["event_count"] == 1
    assert report["pooled"]["specular"]["count"] == 1
    assert report["pooled"]["specular"]["contribution"] == pytest.approx(2.0)
    assert report["pooled"]["first_diffuse"]["transport_contribution"] == pytest.approx(1.0)
    assert report["pooled"]["first_diffuse"]["accepted_event_count"] == 1
    assert report["headline"]["panorama_informed_sar_fraction"] == pytest.approx(1.0)
    json.dumps(report, allow_nan=False)


def test_missing_category_and_authentication_are_refused() -> None:
    document = _document()
    del document["records"][0]["specular"]["categories"][CATEGORIES[-1]]
    with pytest.raises(RayReachedEvidenceCoverageError, match="categories"):
        build_report(document)
    document = _document()
    document["authenticated"] = False
    with pytest.raises(RayReachedEvidenceCoverageError, match="authenticated"):
        build_report(document)
    document = _document()
    document["records"][0].pop("direct")
    with pytest.raises(RayReachedEvidenceCoverageError, match="direct.*N/A"):
        build_report(document)


def test_category_contribution_and_body_closure_are_refused() -> None:
    document = _document()
    document["records"][0]["first_diffuse"]["categories"]["atlas_interface"]["contribution"] = 0.5
    with pytest.raises(RayReachedEvidenceCoverageError, match="contribution closure"):
        build_report(document)
    document = _document()
    document["records"][0]["first_diffuse"]["categories"]["atlas_interface"]["body_coupled"]["sar_wb_w_kg"] = 0.0
    with pytest.raises(RayReachedEvidenceCoverageError, match="body closure"):
        build_report(document)


def test_write_artifacts_and_input_manifest_authentication(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    replay = input_dir / "ray_reached_evidence_replay.json"
    replay.write_text(json.dumps(_document()) + "\n", encoding="utf-8")
    (input_dir / "manifest.json").write_text(
        json.dumps({"files": [{"path": replay.name, "sha256": hashlib.sha256(replay.read_bytes()).hexdigest()}]}),
        encoding="utf-8",
    )
    artifacts = write_ray_reached_evidence_coverage(input_dir, tmp_path / "report")
    for path in artifacts.__dict__.values():
        assert path.is_file() and path.stat().st_size > 0
    manifest = json.loads(artifacts.manifest.read_text(encoding="utf-8"))
    assert manifest["authenticated"] is True
    assert {entry["path"] for entry in manifest["files"]} == {
        artifacts.json.name,
        artifacts.csv.name,
        artifacts.pdf.name,
        artifacts.png.name,
    }


def test_cli_arguments_and_dispatch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys) -> None:
    parsed = command.arguments(["replay.json", "--output", "report"])
    assert parsed.replay_result == Path("replay.json")
    assert parsed.output == Path("report")
    calls = []
    monkeypatch.setattr(
        command,
        "write_ray_reached_evidence_coverage",
        lambda replay, output: (
            calls.append((replay, output)) or type("Artifacts", (), {"__dict__": {"json": tmp_path / "result.json"}})()
        ),
    )
    assert command.main(["replay.json", "--output", "report"]) == 0
    assert calls == [(Path("replay.json"), Path("report"))]
    assert "wrote" in capsys.readouterr().out
