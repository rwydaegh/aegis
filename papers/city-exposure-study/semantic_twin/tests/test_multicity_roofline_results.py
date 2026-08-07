"""Focused checks for authenticated single-IID multicity exports."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from semantic_twin.cli.multicity_roofline_results import arguments
from semantic_twin.exposure.roofline_campaign import (
    BODY_METRICS,
    COMPONENTS,
    FIELD_META,
    REFERENCE_FIELDS,
    SCHEMA_VERSION,
    TIMING_FIELDS,
)
from semantic_twin.report.multicity_roofline_results import CampaignInput, write_multicity_results
from semantic_twin.report.roofline_campaign_comparison import CampaignComparisonError


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def _write_campaign(root: Path, *, reference_mode: str = "per_density_eirp", zero_direct: bool = False) -> None:
    seeds = (7, 8)
    points = 2
    identity_data = {
        "configuration": {
            "site": "fixture",
            "cohort": "comparable_city",
            "route_contract": "provider_corridor_v1",
            "material_mode": "atlas",
            "reference_mode": reference_mode,
            "planned_seeds": list(seeds),
            "convergence_looks": [1, 2],
            "specular_acceptance": "fixture",
        },
        "transport": {
            "estimator": {"configuration": {"specular_suffix_mode": "disabled"}},
            "tracer": {"configuration": {"launch_sampling": "iid", "rays": 8}},
        },
    }
    root.mkdir(parents=True)
    identity = {"sha256": _canonical_sha256(identity_data), "data": identity_data}
    (root / "campaign_identity.json").write_text(json.dumps(identity), encoding="utf-8")

    replicas = root / "checkpoint" / "replicas"
    replicas.mkdir(parents=True)
    committed = []
    for replica_index, seed in enumerate(seeds):
        direct = np.asarray([0.0 if zero_direct else 1.0, 2.0], dtype=np.float64)
        specular = np.asarray([0.2, 0.4], dtype=np.float64)
        diffuse = np.asarray([0.1, 0.2], dtype=np.float64) * (replica_index + 1)
        raw = np.stack((direct, specular, diffuse, direct + specular + diffuse), axis=1)
        body = np.repeat(raw[:, :, None], len(BODY_METRICS), axis=2)
        timings = np.full((points, len(TIMING_FIELDS)), replica_index + 1.0, dtype=np.float64)
        shard = replicas / f"seed_{seed:010d}.npz"
        np.savez_compressed(
            shard,
            raw_transfer=raw,
            body_metrics=body,
            timings=timings,
            field_meta=np.zeros((points, len(FIELD_META)), dtype=np.float64),
            reference=np.ones((points, len(REFERENCE_FIELDS)), dtype=np.float64),
        )
        diagnostics = replicas / f"seed_{seed:010d}.json"
        diagnostics.write_text(json.dumps([{}, {}]), encoding="utf-8")
        committed.append(
            {
                "seed": seed,
                "path": f"replicas/{shard.name}",
                "sha256": _sha256(shard),
                "diagnostics_path": f"replicas/{diagnostics.name}",
                "diagnostics_sha256": _sha256(diagnostics),
            }
        )

    checkpoint = {
        "schema_version": SCHEMA_VERSION,
        "identity_sha256": identity["sha256"],
        "points": points,
        "surfaces": 1,
        "components": list(COMPONENTS),
        "body_metrics": list(BODY_METRICS),
        "reference_fields": list(REFERENCE_FIELDS),
        "timing_fields": list(TIMING_FIELDS),
        "convergence_looks": [1, 2],
        "committed": committed,
    }
    (root / "checkpoint" / "index.json").write_text(json.dumps(checkpoint), encoding="utf-8")
    locations = [
        {
            "standpoint": 0,
            "position_m": [0.0, 0.0, 1.5],
            "components": {"total": {"body": {"ensemble_field_peak_sab_w_m2": 1.3}}},
        },
        {
            "standpoint": 1,
            "position_m": [3.0, 4.0, 1.5],
            "components": {"total": {"body": {"ensemble_field_peak_sab_w_m2": 2.6}}},
        },
    ]
    (root / "locations.jsonl").write_text("".join(json.dumps(row) + "\n" for row in locations), encoding="utf-8")
    (root / "summary.json").write_text(json.dumps({"replicas": len(seeds), "seeds": list(seeds)}), encoding="utf-8")
    files = {
        "campaign_identity.json": _sha256(root / "campaign_identity.json"),
        "checkpoint/index.json": _sha256(root / "checkpoint" / "index.json"),
        "locations.jsonl": _sha256(root / "locations.jsonl"),
        "summary.json": _sha256(root / "summary.json"),
    }
    for entry in committed:
        files[f"checkpoint/{entry['path']}"] = entry["sha256"]
        files[f"checkpoint/{entry['diagnostics_path']}"] = entry["diagnostics_sha256"]
    (root / "manifest.json").write_text(
        json.dumps({"schema_version": SCHEMA_VERSION, "identity_sha256": identity["sha256"], "files": files}),
        encoding="utf-8",
    )


def test_multicity_writer_validates_and_exports_route_results(tmp_path: Path) -> None:
    campaign = tmp_path / "campaign"
    _write_campaign(campaign)

    artifacts = write_multicity_results([CampaignInput("fixture", campaign)], tmp_path / "paper" / "current")

    for path in artifacts.__dict__.values():
        assert path.is_file()
        assert path.stat().st_size > 0
    data = json.loads(artifacts.json.read_text(encoding="utf-8"))
    city = data["cities"]["fixture"]
    assert city["replicas"] == 2
    assert city["route"][1]["route_distance_m"] == pytest.approx(5.0)
    assert city["route"][0]["wbsar"] == pytest.approx(1.35)
    assert city["route"][0]["peak_sab_ensemble_field"] == pytest.approx(1.3)
    assert city["route_cdf"]["wbsar"]["probability"] == pytest.approx([0.25, 0.75])
    assert city["convergence"]["look_to_look"][0]["to_replicas"] == 2
    uncertainty = city["route_quantile_uncertainty"]
    assert uncertainty["bootstrap_replicates"] == 2000
    assert uncertainty["quantiles"]["wbsar"]["q50"]["estimate"] == pytest.approx(2.025)
    assert len(uncertainty["quantiles"]["wbsar"]["q50"]["ci95_percentile"]) == 2
    assert city["tail_instability"]["status"] == "finite_direct_support"
    assert city["tail_instability"]["look_to_look"][0]["route_quantile_abs_change_db"]["q10"] > 0.0
    manifest = json.loads(artifacts.manifest.read_text(encoding="utf-8"))
    assert manifest["sources"]["fixture"]["campaign_identity_sha256"] == city["provenance"]["campaign_identity_sha256"]
    assert manifest["artifacts"][artifacts.json.name]["sha256"] == _sha256(artifacts.json)


def test_bootstrap_is_byte_deterministic_for_same_campaign(tmp_path: Path) -> None:
    campaign = tmp_path / "campaign"
    _write_campaign(campaign)

    first = write_multicity_results([CampaignInput("fixture", campaign)], tmp_path / "first")
    second = write_multicity_results([CampaignInput("fixture", campaign)], tmp_path / "second")

    assert first.json.read_bytes() == second.json.read_bytes()


def test_tail_diagnostic_exposes_zero_direct_support(tmp_path: Path) -> None:
    campaign = tmp_path / "campaign"
    _write_campaign(campaign, zero_direct=True)

    artifacts = write_multicity_results([CampaignInput("fixture", campaign)], tmp_path / "result")
    city = json.loads(artifacts.json.read_text(encoding="utf-8"))["cities"]["fixture"]

    assert city["tail_instability"]["status"] == "structural_zero_direct_present"
    assert city["tail_instability"]["zero_direct_standpoints"] == [0]
    assert city["route"][0]["multipath_surplus_db"] is None
    assert (
        city["route_quantile_uncertainty"]["quantiles"]["multipath_surplus_db"]["q50"]["finite_bootstrap_replicates"]
        == 2000
    )


def test_multicity_writer_rejects_manifest_mutation(tmp_path: Path) -> None:
    campaign = tmp_path / "campaign"
    _write_campaign(campaign)
    with (campaign / "locations.jsonl").open("a", encoding="utf-8") as handle:
        handle.write("{}\n")

    with pytest.raises(CampaignComparisonError, match="manifest hash validation failed"):
        write_multicity_results([CampaignInput("fixture", campaign)], tmp_path / "result")


def test_multicity_writer_rejects_physical_scale_campaign(tmp_path: Path) -> None:
    campaign = tmp_path / "campaign"
    _write_campaign(campaign, reference_mode="physical")

    with pytest.raises(CampaignComparisonError, match="per_density_eirp"):
        write_multicity_results([CampaignInput("fixture", campaign)], tmp_path / "result")


def test_multicity_cli_parses_repeated_cities_and_looks() -> None:
    parsed = arguments(
        [
            "--city",
            "korenmarkt",
            "outputs/korenmarkt",
            "--city",
            "prague",
            "outputs/prague",
            "--output",
            "outputs/paper/current",
            "--looks",
            "4,8,16",
        ]
    )

    assert parsed.city == [
        ["korenmarkt", "outputs/korenmarkt"],
        ["prague", "outputs/prague"],
    ]
    assert parsed.looks == "4,8,16"
