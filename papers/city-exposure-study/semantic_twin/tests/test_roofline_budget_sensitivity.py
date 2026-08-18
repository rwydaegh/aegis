"""Focused contracts for the Priority 3 roofline budget diagnostic."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from semantic_twin.cli.roofline_budget_sensitivity import arguments
from semantic_twin.exposure.roofline_budget_sensitivity import (
    BASELINE_BUDGET,
    COMMON_SUPPORT_CELLS,
    FirstDiffuseCapture,
    REQUIRED_BUDGETS,
    REQUIRED_SEEDS,
    REQUIRED_SITES,
    load_budget_schedule,
    materialize_budget_configs,
)
from semantic_twin.exposure.roofline_campaign import ReferenceScale
from semantic_twin.illumination.sphere import fibonacci_sphere
from semantic_twin.report.roofline_budget_sensitivity import (
    _directional_error,
    _normalised_identity,
    compare_budget_schedule,
    write_budget_sensitivity,
)
from semantic_twin.report.roofline_campaign_comparison import CampaignComparisonError
from semantic_twin.transport.directional import DirectionalMeasure
from test_roofline_campaign_comparison import _write_campaign


def _schedule(tmp_path: Path) -> Path:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    sites = {}
    for site in REQUIRED_SITES:
        base = config_dir / f"{site}.json"
        base.write_text(
            json.dumps(
                {
                    "run": {
                        "site": site,
                        "rays": 200000,
                        "batch": 400000,
                        "local_cells": 4096,
                        "launch_sampling": "iid",
                        "variant": "cuda_ad_rgb",
                        "transport_kernel": "drjit",
                        "max_bounces": 1,
                        "tag": "base",
                    },
                    "campaign": {
                        "output_dir": f"sealed/{site}",
                        "planned_seeds": list(REQUIRED_SEEDS),
                        "convergence_looks": [4, 8, 12, 16],
                        "body_chunk_cells": 512,
                        "transport_topology": "first_material_interaction_v1",
                        "specular_acceptance": "first_material_interaction_exact_order_1",
                    },
                }
            ),
            encoding="utf-8",
        )
        sites[site] = str(base.relative_to(tmp_path))
    schedule = config_dir / "schedule.json"
    schedule.write_text(
        json.dumps(
            {
                "schema": "aegis.roofline-budget-sensitivity-schedule.v1",
                "study_root": ".",
                "output_dir": "results",
                "sites": sites,
                "sealed_baselines": {site: f"sealed/{site}" for site in REQUIRED_SITES},
                "budgets": [{"rays": rays, "cells": cells} for rays, cells in REQUIRED_BUDGETS],
                "baseline": {"rays": BASELINE_BUDGET[0], "cells": BASELINE_BUDGET[1]},
                "seeds": list(REQUIRED_SEEDS),
                "common_support_cells": COMMON_SUPPORT_CELLS,
                "common_random_numbers": "drjit_counter_keyed_seed_ray_depth_dimension_prefix_v1",
                "mexico_shadow_points": [0, 1, 3],
                "bootstrap": {"replicates": 100, "seed": 31, "confidence": 0.95},
                "capture_first_diffuse": True,
            }
        ),
        encoding="utf-8",
    )
    return schedule


def test_schedule_materializes_exact_three_route_six_arm_campaigns(tmp_path: Path) -> None:
    schedule = load_budget_schedule(_schedule(tmp_path))

    written = materialize_budget_configs(schedule)

    assert len(written) == len(REQUIRED_SITES) * len(REQUIRED_BUDGETS)
    assert schedule.seeds == REQUIRED_SEEDS
    assert schedule.common_support_cells == 512
    for site in REQUIRED_SITES:
        for rays, cells in REQUIRED_BUDGETS:
            document = json.loads(
                schedule.generated_config(
                    site, next(arm for arm in schedule.arms if arm.rays == rays and arm.cells == cells)
                ).read_text()
            )
            assert document["run"]["rays"] == rays
            assert document["run"]["local_cells"] == cells
            assert document["run"]["launch_sampling"] == "iid"
            assert document["campaign"]["planned_seeds"] == list(range(7, 23))
            assert document["campaign"]["body_chunk_cells"] == 512
            assert document["campaign"]["transport_topology"] == "first_material_interaction_v1"


def test_schedule_rejects_nonprefix_seed_design(tmp_path: Path) -> None:
    path = _schedule(tmp_path)
    document = json.loads(path.read_text())
    document["seeds"][-1] = 99
    path.write_text(json.dumps(document))

    with pytest.raises(ValueError, match="exact prefix"):
        load_budget_schedule(path)


def test_schedule_binds_sealed_baseline_to_source_config(tmp_path: Path) -> None:
    path = _schedule(tmp_path)
    document = json.loads(path.read_text())
    document["sealed_baselines"]["madrid_plazamayor"] = "sealed/not-the-source-campaign"
    path.write_text(json.dumps(document))

    with pytest.raises(ValueError, match="does not match the source config output_dir"):
        load_budget_schedule(path)


def test_first_diffuse_capture_projects_with_exact_mass_closure(tmp_path: Path) -> None:
    capture = FirstDiffuseCapture(tmp_path / "capture", points=2, common_cells=8)
    directions = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float64)
    empty = np.empty((0, 3), dtype=np.float64)
    measure = DirectionalMeasure(empty, np.empty(0), directions, np.array([0.25, 0.75]))
    field = SimpleNamespace(bounced_mass=np.array([0.5, 1.5], dtype=np.float64))
    scale = ReferenceScale(2.0, 1.0, "per_density_eirp")
    for point in range(2):
        capture(
            seed=7,
            point_index=point,
            point_seed=100 + point,
            measures={"first_diffuse": measure},
            field=field,
            scale=scale,
        )

    manifest_path = capture.finalize(campaign_identity_sha256="a" * 64, schedule_sha256="b" * 64)

    manifest = json.loads(manifest_path.read_text())
    shard = manifest_path.parent / manifest["entries"][0]["path"]
    assert manifest["entries"][0]["sha256"] == hashlib.sha256(shard.read_bytes()).hexdigest()
    with np.load(shard, allow_pickle=False) as payload:
        assert payload["first_diffuse_mass"].shape == (2, 8)
        assert np.sum(payload["first_diffuse_mass"], axis=1).tolist() == pytest.approx([1.0, 1.0])
        assert payload["raw_first_diffuse_m_inv2"].tolist() == pytest.approx([2.0, 2.0])


def test_first_diffuse_capture_rejects_any_partial_sidecar(tmp_path: Path) -> None:
    root = tmp_path / "capture"
    root.mkdir()
    (root / "seed_0000000007.npz").write_bytes(b"partial")

    with pytest.raises(ValueError, match="new and empty"):
        FirstDiffuseCapture(root, points=2)


def test_directional_error_reports_paired_absolute_and_normalized_l1() -> None:
    baseline = np.array(
        [
            [[1.0, 1.0], [0.0, 2.0]],
            [[2.0, 0.0], [1.0, 1.0]],
        ],
        dtype=np.float64,
    )
    candidate = np.array(
        [
            [[1.5, 0.5], [0.0, 2.0]],
            [[1.0, 1.0], [2.0, 0.0]],
        ],
        dtype=np.float64,
    )

    report = _directional_error(candidate, baseline)

    assert report["paired_seed_point_shape"] == [2, 2]
    assert np.asarray(report["absolute_l1_by_seed_and_standpoint"]) == pytest.approx(np.array([[1.0, 0.0], [2.0, 2.0]]))
    assert np.asarray(report["normalized_l1_by_seed_and_standpoint"]) == pytest.approx(
        np.array([[0.5, 0.0], [1.0, 1.0]])
    )
    assert report["absolute_l1_quantiles"] == pytest.approx({"q10": 0.3, "q50": 1.5, "q90": 2.0})
    assert report["normalized_l1_quantiles"] == pytest.approx({"q10": 0.15, "q50": 0.75, "q90": 1.0})
    assert report["mass_closure"]["absolute_l1_upper_bounded_by_total_mass"] is True
    assert report["minimum_cosine_similarity"] >= 0.0


def test_budget_cli_exposes_complete_campaign_lifecycle() -> None:
    for command in ("materialize", "preflight", "run", "report", "all"):
        argv = ["--schedule", "schedule.json", command]
        if command in ("report", "all"):
            argv.extend(["--output", "report/budget"])
        parsed = arguments(argv)
        assert parsed.command == command


@pytest.mark.parametrize("local_grid_sha256", [None, 123])
def test_budget_identity_requires_typed_local_grid_provenance(local_grid_sha256: object) -> None:
    tracer: dict[str, object] = {
        "configuration": {"rays": 25_000, "local_cells": 1_024},
    }
    if local_grid_sha256 is not None:
        tracer["local_grid_sha256"] = local_grid_sha256
    campaign = SimpleNamespace(
        identity_data={
            "configuration": {},
            "transport": {"tracer": tracer},
            "inputs": {
                "files": [{"path": "roofline_campaign_fixture.json", "bytes": 1, "sha256": "a" * 64}],
                "file_count": 1,
                "bytes": 1,
            },
        }
    )

    with pytest.raises(CampaignComparisonError, match="tracer local_grid_sha256"):
        _normalised_identity(campaign)


def _reseal_budget(root: Path, rays: int, cells: int, *, run_config_path: str) -> str:
    identity_path = root / "campaign_identity.json"
    identity = json.loads(identity_path.read_text())
    tracer = identity["data"]["transport"]["tracer"]["configuration"]
    tracer["rays"] = rays
    tracer["local_cells"] = cells
    identity["data"]["transport"]["tracer"]["local_grid_sha256"] = hashlib.sha256(
        f"fixture-fibonacci-grid:{cells}".encode()
    ).hexdigest()
    identity["data"]["transport"]["tracer"]["permittivity_sha256"] = "c" * 64
    identity["data"]["inputs"] = {
        "files": [{"path": run_config_path, "bytes": 1, "sha256": "a" * 64}],
        "file_count": 1,
        "bytes": 1,
    }
    canonical = json.dumps(identity["data"], sort_keys=True, separators=(",", ":"), allow_nan=False)
    identity["sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    identity_path.write_text(json.dumps(identity))
    checkpoint_path = root / "checkpoint" / "index.json"
    checkpoint = json.loads(checkpoint_path.read_text())
    checkpoint["identity_sha256"] = identity["sha256"]
    checkpoint_path.write_text(json.dumps(checkpoint))
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["identity_sha256"] = identity["sha256"]
    manifest["files"]["campaign_identity.json"] = hashlib.sha256(identity_path.read_bytes()).hexdigest()
    manifest["files"]["checkpoint/index.json"] = hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    return identity["sha256"]


def _set_tracer_hash_and_reseal(root: Path, field: str, value: str) -> None:
    identity_path = root / "campaign_identity.json"
    identity = json.loads(identity_path.read_text())
    identity["data"]["transport"]["tracer"][field] = value
    canonical = json.dumps(identity["data"], sort_keys=True, separators=(",", ":"), allow_nan=False)
    identity["sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    identity_path.write_text(json.dumps(identity))

    checkpoint_path = root / "checkpoint" / "index.json"
    checkpoint = json.loads(checkpoint_path.read_text())
    checkpoint["identity_sha256"] = identity["sha256"]
    checkpoint_path.write_text(json.dumps(checkpoint))

    capture_manifest_path = root / "first_diffuse_common_support" / "manifest.json"
    capture_manifest = json.loads(capture_manifest_path.read_text())
    capture_manifest["campaign_identity_sha256"] = identity["sha256"]
    capture_manifest_path.write_text(json.dumps(capture_manifest))

    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["identity_sha256"] = identity["sha256"]
    manifest["files"]["campaign_identity.json"] = hashlib.sha256(identity_path.read_bytes()).hexdigest()
    manifest["files"]["checkpoint/index.json"] = hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))


def _expand_campaign_to_four_points(root: Path) -> None:
    checkpoint_path = root / "checkpoint" / "index.json"
    checkpoint = json.loads(checkpoint_path.read_text())
    checkpoint["points"] = 4
    for entry in checkpoint["committed"]:
        shard = root / "checkpoint" / entry["path"]
        with np.load(shard, allow_pickle=False) as payload:
            arrays = {name: np.concatenate([payload[name], payload[name][-1:]], axis=0) for name in payload.files}
        np.savez_compressed(shard, **arrays)
        entry["sha256"] = hashlib.sha256(shard.read_bytes()).hexdigest()
        diagnostics_path = root / "checkpoint" / entry["diagnostics_path"]
        diagnostics = json.loads(diagnostics_path.read_text())
        diagnostics.append(diagnostics[-1])
        diagnostics_path.write_text(json.dumps(diagnostics))
        entry["diagnostics_sha256"] = hashlib.sha256(diagnostics_path.read_bytes()).hexdigest()
    checkpoint_path.write_text(json.dumps(checkpoint))
    locations_path = root / "locations.jsonl"
    locations = [json.loads(line) for line in locations_path.read_text().splitlines()]
    locations.append({"standpoint": 3, "position_m": [3.0, 0.0, 1.5]})
    locations_path.write_text("\n".join(json.dumps(row) for row in locations) + "\n")
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"]["locations.jsonl"] = hashlib.sha256(locations_path.read_bytes()).hexdigest()
    manifest["files"]["checkpoint/index.json"] = hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()
    for entry in checkpoint["committed"]:
        manifest["files"][f"checkpoint/{entry['path']}"] = entry["sha256"]
        manifest["files"][f"checkpoint/{entry['diagnostics_path']}"] = entry["diagnostics_sha256"]
    manifest_path.write_text(json.dumps(manifest))


def _add_cumulative_sab(root: Path) -> None:
    checkpoint_path = root / "checkpoint" / "index.json"
    checkpoint = json.loads(checkpoint_path.read_text())
    cumulative_dir = root / "checkpoint" / "cumulative"
    cumulative_dir.mkdir()
    entries = []
    for replicas, seed in ((4, 10), (8, 14), (12, 18), (16, 22)):
        path = cumulative_dir / f"sab_sum_{replicas:04d}_seed_{seed:010d}.npz"
        np.savez_compressed(path, sab_sum=np.full((4, 1), float(replicas), dtype=np.float64))
        entries.append(
            {
                "replicas": replicas,
                "path": f"cumulative/{path.name}",
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    checkpoint["look_sab"] = entries
    checkpoint["cumulative_sab"] = entries[-1]
    checkpoint_path.write_text(json.dumps(checkpoint))
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"]["checkpoint/index.json"] = hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()
    for entry in entries:
        manifest["files"][f"checkpoint/{entry['path']}"] = entry["sha256"]
    manifest_path.write_text(json.dumps(manifest))


def _write_capture(root: Path, identity: str, schedule_sha256: str) -> None:
    capture = root / "first_diffuse_common_support"
    capture.mkdir()
    grid = fibonacci_sphere(COMMON_SUPPORT_CELLS)
    entries = []
    for seed in REQUIRED_SEEDS:
        path = capture / f"seed_{seed:010d}.npz"
        mass = np.full((4, COMMON_SUPPORT_CELLS), 1.0 / COMMON_SUPPORT_CELLS, dtype=np.float64)
        np.savez_compressed(
            path,
            common_grid=grid,
            first_diffuse_mass=mass,
            raw_first_diffuse_m_inv2=np.ones(4, dtype=np.float64),
            reference_transfer_m_inv2=np.ones(4, dtype=np.float64),
            point_seed=np.arange(4, dtype=np.uint64),
        )
        entries.append(
            {
                "seed": seed,
                "path": path.name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "bytes": path.stat().st_size,
            }
        )
    (capture / "manifest.json").write_text(
        json.dumps(
            {
                "schema": "aegis.roofline-budget-first-diffuse-capture.v1",
                "campaign_identity_sha256": identity,
                "schedule_sha256": schedule_sha256,
                "common_support_cells": COMMON_SUPPORT_CELLS,
                "points": 4,
                "entries": entries,
            }
        )
    )


def _mutate_first_shard_and_reseal(root: Path) -> None:
    checkpoint_path = root / "checkpoint" / "index.json"
    checkpoint = json.loads(checkpoint_path.read_text())
    entry = checkpoint["committed"][0]
    shard = root / "checkpoint" / entry["path"]
    with np.load(shard, allow_pickle=False) as payload:
        arrays = {name: np.asarray(payload[name]).copy() for name in payload.files}
    arrays["raw_transfer"][0, 0] += 0.125
    arrays["raw_transfer"][0, 3] += 0.125
    np.savez_compressed(shard, **arrays)
    entry["sha256"] = hashlib.sha256(shard.read_bytes()).hexdigest()
    checkpoint_path.write_text(json.dumps(checkpoint))
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"][f"checkpoint/{entry['path']}"] = entry["sha256"]
    manifest["files"]["checkpoint/index.json"] = hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))


def _mutate_timing_only_and_reseal(root: Path) -> None:
    checkpoint_path = root / "checkpoint" / "index.json"
    checkpoint = json.loads(checkpoint_path.read_text())
    entry = checkpoint["committed"][0]
    shard = root / "checkpoint" / entry["path"]
    with np.load(shard, allow_pickle=False) as payload:
        arrays = {name: np.asarray(payload[name]).copy() for name in payload.files}
    arrays["timings"] += 17.0
    np.savez_compressed(shard, **arrays)
    entry["sha256"] = hashlib.sha256(shard.read_bytes()).hexdigest()
    diagnostics_path = root / "checkpoint" / entry["diagnostics_path"]
    diagnostics = json.loads(diagnostics_path.read_text())
    diagnostics[0]["measured_seconds"] = 17.0
    diagnostics_path.write_text(json.dumps(diagnostics))
    entry["diagnostics_sha256"] = hashlib.sha256(diagnostics_path.read_bytes()).hexdigest()
    checkpoint_path.write_text(json.dumps(checkpoint))
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"][f"checkpoint/{entry['path']}"] = entry["sha256"]
    manifest["files"][f"checkpoint/{entry['diagnostics_path']}"] = entry["diagnostics_sha256"]
    manifest["files"]["checkpoint/index.json"] = hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))


def _set_location_diagnostics_and_reseal(root: Path, *, seconds: float, diagnostic_sha256: str) -> None:
    locations_path = root / "locations.jsonl"
    locations = [json.loads(line) for line in locations_path.read_text().splitlines()]
    locations[0]["timing_seconds_per_replica_mean"] = {"estimator": seconds}
    locations[0]["specular_diagnostic_variants"] = [
        {
            "data": {
                "measured_seconds": seconds,
                "diagnostic_sha256": diagnostic_sha256,
            }
        }
    ]
    locations_path.write_text("\n".join(json.dumps(row) for row in locations) + "\n")
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"]["locations.jsonl"] = hashlib.sha256(locations_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))


def _mutate_location_and_reseal(root: Path, delta_x_m: float) -> None:
    locations_path = root / "locations.jsonl"
    locations = [json.loads(line) for line in locations_path.read_text().splitlines()]
    locations[0]["position_m"][0] += delta_x_m
    locations_path.write_text("\n".join(json.dumps(row) for row in locations) + "\n")
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"]["locations.jsonl"] = hashlib.sha256(locations_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))


def test_authenticated_report_covers_all_arms_and_artifacts(tmp_path: Path) -> None:
    schedule = load_budget_schedule(_schedule(tmp_path))
    for site in REQUIRED_SITES:
        sealed = schedule.sealed_baselines[site]
        _write_campaign(sealed, "iid", seeds=REQUIRED_SEEDS, first_interaction=True)
        _expand_campaign_to_four_points(sealed)
        _add_cumulative_sab(sealed)
        _reseal_budget(
            sealed,
            200_000,
            4_096,
            run_config_path=f"config/roofline_campaign_{site}_source_iid.json",
        )
    for site in REQUIRED_SITES:
        for arm in schedule.arms:
            root = schedule.campaign_dir(site, arm)
            _write_campaign(root, "iid", seeds=REQUIRED_SEEDS, first_interaction=True)
            _expand_campaign_to_four_points(root)
            _add_cumulative_sab(root)
            identity = _reseal_budget(
                root,
                arm.rays,
                arm.cells,
                run_config_path=f"outputs/generated_configs/roofline_campaign_{site}_budget_{arm.key}_iid.json",
            )
            _write_capture(root, identity, schedule.sha256)
    madrid_replay = schedule.campaign_dir("madrid_plazamayor", schedule.baseline)
    madrid_sealed = schedule.sealed_baselines["madrid_plazamayor"]
    _mutate_timing_only_and_reseal(madrid_replay)
    _set_location_diagnostics_and_reseal(
        madrid_sealed,
        seconds=1.0,
        diagnostic_sha256="a" * 64,
    )
    _set_location_diagnostics_and_reseal(
        madrid_replay,
        seconds=17.0,
        diagnostic_sha256="b" * 64,
    )

    artifacts = write_budget_sensitivity(schedule, tmp_path / "report" / "budget")

    for path in artifacts.__dict__.values():
        assert path.is_file()
        assert path.stat().st_size > 0
    report = json.loads(artifacts.json.read_text())
    assert len(report["budgets"]) == 6
    assert all(set(arm["sites"]) == set(REQUIRED_SITES) for arm in report["budgets"])
    assert report["budgets"][0]["sites"]["mexico_zocalo"]["mexico_shadow_points"]["standpoints"] == [0, 1, 3]
    assert report["budgets"][0]["recommendation"]["migration_recommended"] is True
    assert all(value["status"] == "pass" for value in report["sealed_baseline_replay_parity"].values())
    madrid_parity = report["sealed_baseline_replay_parity"]["madrid_plazamayor"]
    assert madrid_parity["non_timing_shard_arrays"]["compared_arrays"] == [
        "body_metrics",
        "field_meta",
        "raw_transfer",
        "reference",
    ]
    assert madrid_parity["cumulative_sab"]["replica_looks"] == [4, 8, 12, 16]
    direction = report["budgets"][0]["sites"]["madrid_plazamayor"]["directional_first_diffuse"]
    assert set(direction["absolute_l1_quantiles"]) == {"q10", "q50", "q90"}
    assert set(direction["normalized_l1_quantiles"]) == {"q10", "q50", "q90"}
    assert direction["paired_seed_point_shape"] == [16, 4]
    assert direction["mass_closure"]["absolute_l1_upper_bounded_by_total_mass"] is True
    manifest = json.loads(artifacts.manifest.read_text())
    assert (
        manifest["artifacts"][artifacts.json.name]["sha256"] == hashlib.sha256(artifacts.json.read_bytes()).hexdigest()
    )

    first_arm = schedule.arms[0]
    capture_manifest = (
        schedule.campaign_dir("madrid_plazamayor", first_arm) / "first_diffuse_common_support" / "manifest.json"
    )
    capture = json.loads(capture_manifest.read_text())
    capture["schedule_sha256"] = "0" * 64
    capture_manifest.write_text(json.dumps(capture))
    with pytest.raises(CampaignComparisonError, match="active budget schedule"):
        compare_budget_schedule(schedule)
    capture["schedule_sha256"] = schedule.sha256
    capture_manifest.write_text(json.dumps(capture))

    drift_arm = schedule.arms[0]
    drift_campaign = schedule.campaign_dir("madrid_plazamayor", drift_arm)
    _set_tracer_hash_and_reseal(drift_campaign, "permittivity_sha256", "d" * 64)
    with pytest.raises(CampaignComparisonError, match=r"transport\.tracer\.permittivity_sha256"):
        compare_budget_schedule(schedule)
    _set_tracer_hash_and_reseal(drift_campaign, "permittivity_sha256", "c" * 64)

    _mutate_location_and_reseal(madrid_replay, 0.125)
    with pytest.raises(CampaignComparisonError, match="locations_without_timing_and_diagnostics"):
        compare_budget_schedule(schedule)

    _mutate_location_and_reseal(madrid_replay, -0.125)
    _set_location_diagnostics_and_reseal(
        madrid_replay,
        seconds=17.0,
        diagnostic_sha256="b" * 64,
    )
    _mutate_first_shard_and_reseal(madrid_replay)
    with pytest.raises(CampaignComparisonError, match="non_timing_shard_arrays"):
        compare_budget_schedule(schedule)
