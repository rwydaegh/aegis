"""Focused checks for authenticated cross-topology sensitivity reports."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from semantic_twin.cli.roofline_topology_sensitivity import arguments
from semantic_twin.report.roofline_campaign_comparison import CampaignComparisonError
from semantic_twin.report.roofline_topology_sensitivity import (
    _ALLOWED_IDENTITY_PATHS,
    _REMOVED_IDENTITY_PATHS,
    compare_topologies,
    write_topology_sensitivity,
)
from test_roofline_campaign_comparison import _write_campaign


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _seal_route_fields(root: Path, *, offset: float = 0.0) -> None:
    path = root / "locations.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    for index, row in enumerate(rows):
        row["body_yaw_deg"] = 15.0
        row["ground_z_m"] = offset if index == 0 else 0.0
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"]["locations.jsonl"] = _sha256(path)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


def _change_rays_and_reseal(root: Path, rays: int) -> None:
    identity_path = root / "campaign_identity.json"
    identity = json.loads(identity_path.read_text(encoding="utf-8"))
    identity["data"]["transport"]["tracer"]["configuration"]["rays"] = rays
    canonical = json.dumps(identity["data"], sort_keys=True, separators=(",", ":"), allow_nan=False)
    identity["sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    identity_path.write_text(json.dumps(identity), encoding="utf-8")
    checkpoint_path = root / "checkpoint" / "index.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    checkpoint["identity_sha256"] = identity["sha256"]
    checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["identity_sha256"] = identity["sha256"]
    manifest["files"]["campaign_identity.json"] = _sha256(identity_path)
    manifest["files"]["checkpoint/index.json"] = _sha256(checkpoint_path)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


def _pair(tmp_path: Path, *, incompatible: bool = False) -> tuple[Path, Path]:
    hybrid = tmp_path / "hybrid"
    first = tmp_path / "first"
    _write_campaign(hybrid, "iid")
    _write_campaign(first, "iid", first_interaction=True, incompatible=incompatible)
    _seal_route_fields(hybrid)
    _seal_route_fields(first)
    return hybrid, first


def test_topology_report_writes_authenticated_machine_and_figure_artifacts(tmp_path: Path) -> None:
    hybrid, first = _pair(tmp_path)

    artifacts = write_topology_sensitivity(hybrid, first, tmp_path / "paper" / "topology")

    for path in artifacts.__dict__.values():
        assert path.is_file()
        assert path.stat().st_size > 0
    report = json.loads(artifacts.json.read_text(encoding="utf-8"))
    assert report["hybrid"]["components"] == ["direct", "specular", "diffuse", "total"]
    assert report["first_material_interaction"]["components"] == [
        "direct",
        "all_specular",
        "first_diffuse",
        "total",
    ]
    assert report["common_seeds"] == list(range(1, 17))
    assert len(report["per_seed_point"]) == 48
    first_row = report["per_seed_point"][0]
    assert first_row["raw_transfer"]["first_all_specular"] == pytest.approx(0.25)
    assert "q90" in report["final_route"]["total_body_metrics"]["sar_wb_w_kg"]["route_quantiles"]
    assert report["zero_direct_strata"]["shared"] == []
    assert len(report["convergence"]) == 4
    assert "first_all_specular" in artifacts.csv.read_text(encoding="utf-8").splitlines()[0]
    manifest = json.loads(artifacts.manifest.read_text(encoding="utf-8"))
    assert manifest["artifacts"][artifacts.json.name]["sha256"] == _sha256(artifacts.json)


def test_topology_report_fails_closed_on_undeclared_material_drift(tmp_path: Path) -> None:
    hybrid, first = _pair(tmp_path, incompatible=True)

    with pytest.raises(CampaignComparisonError, match="configuration.material_mode"):
        compare_topologies(hybrid, first)


def test_topology_report_requires_exact_ground_registered_route(tmp_path: Path) -> None:
    hybrid, first = _pair(tmp_path)
    _seal_route_fields(first, offset=0.25)

    with pytest.raises(CampaignComparisonError, match="ground_z_m"):
        compare_topologies(hybrid, first)


def test_topology_report_rejects_ray_budget_drift(tmp_path: Path) -> None:
    hybrid, first = _pair(tmp_path)
    _change_rays_and_reseal(first, 64)

    with pytest.raises(CampaignComparisonError, match="transport.tracer.configuration.rays"):
        compare_topologies(hybrid, first)


def test_topology_sensitivity_cli_parses_inputs() -> None:
    parsed = arguments(["hybrid", "first", "--output", "paper/topology"])

    assert parsed.hybrid_directory == Path("hybrid")
    assert parsed.first_material_interaction_directory == Path("first")
    assert parsed.output == Path("paper/topology")


def test_reported_identity_allowlist_is_derived_from_removed_paths() -> None:
    removed = {".".join(path) for path in _REMOVED_IDENTITY_PATHS}
    reported = set(_ALLOWED_IDENTITY_PATHS)

    assert reported == removed | {
        "configuration.planned_seeds[tail_after_common_prefix]",
        "inputs.files[roofline_campaign_run_config]",
    }
