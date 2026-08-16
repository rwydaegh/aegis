"""Focused checks for authenticated geometric fixed-grid screening reports."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from semantic_twin.cli.geometric_grid_screening import arguments
from semantic_twin.exposure.roofline_campaign import (
    BODY_METRICS,
    FIELD_META,
    FIRST_MATERIAL_INTERACTION_COMPONENTS,
    FIRST_MATERIAL_INTERACTION_SCHEMA_VERSION,
    REFERENCE_FIELDS,
    TIMING_FIELDS,
)
from semantic_twin.report.geometric_grid_screening import (
    CampaignInput,
    EXPECTED_SITES,
    GeometricGridScreeningError,
    write_geometric_grid_screening,
)
from semantic_twin.report.roofline_campaign_comparison import CampaignComparisonError


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def _array_digest(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(str(array.shape).encode("ascii"))
    digest.update(array.tobytes())
    return digest.hexdigest()


def _write_campaign(
    root: Path,
    site: str,
    *,
    material_mode: str = "geometric",
    fixed_yaw: float = 0.0,
    grid_spacing_m: float = 6.0,
    body_closure_drift: bool = False,
) -> None:
    seeds = (7, 8, 9, 10)
    points = 16
    components = tuple(FIRST_MATERIAL_INTERACTION_COMPONENTS)
    positions = np.column_stack(
        (
            np.arange(points, dtype=np.float64),
            np.arange(points, dtype=np.float64) * 0.5,
            np.full(points, 1.5, dtype=np.float64),
        )
    )
    yaws = np.full(points, fixed_yaw, dtype=np.float64)
    identity_data = {
        "configuration": {
            "schema_version": FIRST_MATERIAL_INTERACTION_SCHEMA_VERSION,
            "site": site,
            "cohort": "geometric_fixed_grid_screening",
            "material_mode": material_mode,
            "planned_seeds": list(seeds),
            "reference_mode": "per_density_eirp",
            "sampling_claim": "geometric_fixed_grid_screening_v1",
            "grid_contract": "fixed_ground_grid_v1",
            "convergence_looks": [4],
            "minimum_completed_specular_order": 1,
            "specular_acceptance": "first_material_interaction_exact_order_1",
            "transport_topology": "first_material_interaction_v1",
            "components": list(components),
        },
        "components": list(components),
        "walk": {
            "walk_kind": "grid",
            "walk_site": site,
            "walk_rule": "fixed fixture grid",
            "standpoints": points,
            "points_sha256": _array_digest(positions),
            "ground_z_sha256": "1" * 64,
            "step_m_sha256": "2" * 64,
            "body_yaw_sha256": _array_digest(yaws),
            "provenance": {
                "sampling_claim": "geometric_fixed_grid_screening_v1",
                "grid_contract": "fixed_ground_grid_v1",
                "spacing_m": grid_spacing_m,
                "radius_m": 90.0,
                "full_grid_standpoints": 64,
                "full_grid_points_sha256": "3" * 64,
                "selection_indices": list(range(points)),
                "selection_count": points,
                "selected_points_sha256": _array_digest(positions),
                "point_kind": ["fixed_ground_grid"] * points,
                "body_yaw_rule": "fixed_north_v1",
                "body_yaw_deg": [float(fixed_yaw)] * points,
            },
        },
        "body": {
            "phantom": "duke",
            "level": 2,
            "frequency_hz": 15_000_000_000.0,
            "surface_elements": 56_024,
        },
        "materials": {
            "material_mode": material_mode,
            "atlas_material_present": False,
            "binding": {"materials": "geometric"},
        },
        "transport": {
            "estimator": {
                "configuration": {
                    "transport_topology": "first_material_interaction_v1",
                    "max_order": 1,
                    "specular_order": 1,
                    "specular_suffix_mode": "disabled",
                }
            },
            "tracer": {
                "atlas_material": None,
                "configuration": {
                    "launch_sampling": "iid",
                    "frequency_hz": 15_000_000_000,
                    "rays": 200_000,
                    "local_cells": 4096,
                    "max_bounces": 1,
                },
            },
        },
    }
    root.mkdir(parents=True)
    identity = {"sha256": _canonical_sha256(identity_data), "data": identity_data}
    (root / "campaign_identity.json").write_text(json.dumps(identity), encoding="utf-8")

    replicas = root / "checkpoint" / "replicas"
    replicas.mkdir(parents=True)
    committed = []
    for replica_index, seed in enumerate(seeds):
        scale = np.arange(1, points + 1, dtype=np.float64) * 1.0e-6
        direct = scale
        specular = 0.3 * scale
        diffuse = (0.1 + 0.02 * replica_index) * scale
        raw = np.stack((direct, specular, diffuse, direct + specular + diffuse), axis=1)
        body = np.repeat(raw[:, :, None], len(BODY_METRICS), axis=2)
        if body_closure_drift:
            body[:, -1, BODY_METRICS.index("sar_wb_w_kg")] += 1.0e-7
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
        diagnostics.write_text(json.dumps([{} for _index in range(points)]), encoding="utf-8")
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
        "schema_version": FIRST_MATERIAL_INTERACTION_SCHEMA_VERSION,
        "identity_sha256": identity["sha256"],
        "points": points,
        "surfaces": 1,
        "components": list(components),
        "body_metrics": list(BODY_METRICS),
        "reference_fields": list(REFERENCE_FIELDS),
        "timing_fields": list(TIMING_FIELDS),
        "convergence_looks": [4],
        "committed": committed,
    }
    (root / "checkpoint" / "index.json").write_text(json.dumps(checkpoint), encoding="utf-8")
    locations = [
        {
            "site": site,
            "cohort": "geometric_fixed_grid_screening",
            "standpoint": index,
            "point_kind": "fixed_ground_grid",
            "position_m": [float(value) for value in positions[index]],
            "body_yaw_deg": float(yaws[index]),
        }
        for index in range(points)
    ]
    (root / "locations.jsonl").write_text("".join(json.dumps(row) + "\n" for row in locations), encoding="utf-8")
    (root / "summary.json").write_text(
        json.dumps(
            {
                "schema_version": FIRST_MATERIAL_INTERACTION_SCHEMA_VERSION,
                "components": list(components),
                "replicas": len(seeds),
                "seeds": list(seeds),
            }
        ),
        encoding="utf-8",
    )
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
        json.dumps(
            {
                "schema_version": FIRST_MATERIAL_INTERACTION_SCHEMA_VERSION,
                "identity_sha256": identity["sha256"],
                "files": files,
            }
        ),
        encoding="utf-8",
    )


def _campaign_set(tmp_path: Path, **site_options: dict[str, object]) -> list[CampaignInput]:
    inputs = []
    for site in EXPECTED_SITES:
        root = tmp_path / site
        _write_campaign(root, site, **site_options.get(site, {}))
        inputs.append(CampaignInput(site, root))
    return inputs


def test_writer_emits_compact_authenticated_screening_artifacts(tmp_path: Path) -> None:
    artifacts = write_geometric_grid_screening(_campaign_set(tmp_path), tmp_path / "report" / "screen")

    for path in artifacts.__dict__.values():
        assert path.is_file()
        assert path.stat().st_size > 0
    report = json.loads(artifacts.json.read_text(encoding="utf-8"))
    assert report["authentication"] == {
        "campaigns_authenticated": 10,
        "method": (
            "identity wrapper, manifest, checkpoint, shard hash, schema, seed, grid, yaw, material, "
            "transport, and additive component-closure checks"
        ),
        "status": "pass",
    }
    assert list(report["sites"]) == sorted(EXPECTED_SITES)
    site = report["sites"]["korenmarkt"]
    assert len(site["grid_points"]) == 16
    assert site["normalized_wbsar_quantiles"]["q10"]["estimate"] > 0.0
    assert site["normalized_wbsar_quantiles"]["q50"]["seed_standard_error"] > 0.0
    assert len(site["normalized_wbsar_quantiles"]["q90"]["seed_quantile_values"]) == 4
    assert sum(site["normalized_wbsar_component_shares"].values()) == pytest.approx(1.0)
    assert site["closure"]["status"] == "pass"
    assert site["timing"]["nonoverlapping_observed_compute_seconds"] == pytest.approx(320.0)
    assert any("no panorama-derived semantic evidence" in line for line in report["disclosures"])
    assert any("do not support pedestrian-path" in line for line in report["disclosures"])

    csv_lines = artifacts.csv.read_text(encoding="utf-8").splitlines()
    assert len(csv_lines) == 1 + 10 * 3
    assert "normalized_wbsar_estimate" in csv_lines[0]
    manifest = json.loads(artifacts.manifest.read_text(encoding="utf-8"))
    assert manifest["authenticated"] is True
    assert (
        manifest["sources"]["korenmarkt"]["campaign_identity_sha256"]
        == site["authentication"]["campaign_identity_sha256"]
    )
    assert manifest["artifacts"][artifacts.json.name]["sha256"] == _sha256(artifacts.json)


def test_writer_rejects_mutation_before_reporting(tmp_path: Path) -> None:
    inputs = _campaign_set(tmp_path)
    with (inputs[0].directory / "locations.jsonl").open("a", encoding="utf-8") as handle:
        handle.write("{}\n")

    with pytest.raises(CampaignComparisonError, match="manifest hash validation failed"):
        write_geometric_grid_screening(inputs, tmp_path / "screen")


def test_writer_rejects_contract_and_fixed_yaw_drift(tmp_path: Path) -> None:
    material_inputs = _campaign_set(tmp_path / "material", korenmarkt={"material_mode": "atlas"})
    with pytest.raises(GeometricGridScreeningError, match="configuration.material_mode"):
        write_geometric_grid_screening(material_inputs, tmp_path / "material_report")

    yaw_inputs = _campaign_set(tmp_path / "yaw", korenmarkt={"fixed_yaw": 90.0})
    with pytest.raises(GeometricGridScreeningError, match="body_yaw_deg"):
        write_geometric_grid_screening(yaw_inputs, tmp_path / "yaw_report")

    spacing_inputs = _campaign_set(tmp_path / "spacing", korenmarkt={"grid_spacing_m": 3.0})
    with pytest.raises(GeometricGridScreeningError, match="walk.provenance.spacing_m"):
        write_geometric_grid_screening(spacing_inputs, tmp_path / "spacing_report")


def test_writer_rejects_additive_body_closure_failure(tmp_path: Path) -> None:
    inputs = _campaign_set(tmp_path, korenmarkt={"body_closure_drift": True})

    with pytest.raises(GeometricGridScreeningError, match="component closure failed"):
        write_geometric_grid_screening(inputs, tmp_path / "screen")


def test_writer_requires_exact_declared_site_set(tmp_path: Path) -> None:
    inputs = _campaign_set(tmp_path)

    with pytest.raises(GeometricGridScreeningError, match="ten screening sites exactly once"):
        write_geometric_grid_screening(inputs[:-1], tmp_path / "screen")


def test_cli_parses_repeated_site_campaigns() -> None:
    argv: list[str] = []
    for site in EXPECTED_SITES:
        argv.extend(("--campaign", site, f"outputs/{site}"))
    argv.extend(("--output", "outputs/screening/geometric_grid"))

    parsed = arguments(argv)

    assert parsed.campaign[0] == ["korenmarkt", "outputs/korenmarkt"]
    assert parsed.campaign[-1] == ["toulouse_capitole", "outputs/toulouse_capitole"]
    assert parsed.output == Path("outputs/screening/geometric_grid")
