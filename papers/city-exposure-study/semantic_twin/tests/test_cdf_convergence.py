from __future__ import annotations

import hashlib
import json
import pathlib
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

from run_cdf_convergence import arguments
from semantic_twin.exposure.cdf_convergence import (
    CdfConvergenceConfig,
    CampaignCheckpoint,
    StoppingThresholds,
    _analyse_checkpoint,
    _bootstrap_peak_of_mean_sab,
    _campaign_manifest,
    _final_ensemble,
    _load_campaign_checkpoint,
    _prepare_campaign_plan,
    _quarantine_stale_generation,
    _trace_replica,
    _validate_production_tissue_database,
    _write_campaign_checkpoint,
    _write_reached_formal_analyses,
    analyse_chi_replicas,
    analyse_joint_replicas,
)
from semantic_twin.illumination import fibonacci_sphere


def _quiet_replicas() -> np.ndarray:
    rng = np.random.default_rng(41)
    point = np.geomspace(0.01, 1.0, 13)[:, None]
    model = np.asarray([1.0, 0.5, 0.1])[None, :]
    noise_db = rng.normal(0.0, 0.003, size=(32, 13, 3))
    return point[None, :, :] * model[None, :, :] * 10.0 ** (noise_db / 10.0)


def test_quiet_full_walk_replicas_stop_at_the_second_formal_look() -> None:
    report = analyse_chi_replicas(
        _quiet_replicas(),
        looks=(8, 16, 24, 32),
        formal_looks=(16, 24, 32),
        bootstrap_replicates=500,
        bootstrap_seed=19,
    )

    assert report["stopped"] is True
    assert report["stop_at_replicas"] == 24
    assert report["looks"][0]["formal_look"] is False
    assert report["looks"][1]["consecutive_formal_passes"] == 1
    assert report["looks"][2]["consecutive_formal_passes"] == 2
    assert report["planned_look_coverage"]["alpha_per_formal_look"] == pytest.approx(1.0 / 60.0)
    assert report["looks"][1]["coverage"]["per_look_confidence_nominal"] == pytest.approx(59.0 / 60.0)
    assert report["route_sample"] == {
        "standpoints": 13,
        "cdf_step": pytest.approx(1.0 / 13.0),
        "spatial_sampling_uncertainty_included": False,
    }


def test_seed_average_is_linear_before_the_decibel_conversion() -> None:
    replicas = np.ones((8, 2, 3), dtype=np.float64)
    replicas[:4] *= 1.0
    replicas[4:] *= 100.0
    report = analyse_chi_replicas(
        replicas,
        looks=(8,),
        formal_looks=(8,),
        bootstrap_replicates=500,
        thresholds=StoppingThresholds(
            point_p90_db=100.0,
            point_max_db=100.0,
            cdf_q50_db=100.0,
            cdf_q10_q90_db=100.0,
            cdf_endpoint_db=100.0,
            stability_wasserstein_db=100.0,
            stability_q50_db=100.0,
            stability_q10_q90_db=100.0,
            stability_endpoint_db=100.0,
            body_peak_max_db=100.0,
        ),
    )

    expected = 10.0 * np.log10(50.5)
    assert report["looks"][0]["point_estimate_db"]["isotropic"] == pytest.approx([expected, expected])
    assert expected != pytest.approx(10.0)


def test_route_endpoints_and_neighbours_are_preserved() -> None:
    base = np.arange(1.0, 14.0)[:, None] * np.asarray([[1.0, 2.0, 3.0]])
    replicas = np.repeat(base[None, :, :], 8, axis=0)
    report = analyse_chi_replicas(
        replicas,
        looks=(8,),
        formal_looks=(8,),
        bootstrap_replicates=200,
    )

    endpoints = report["looks"][0]["endpoint_values_db"]["isotropic"]
    assert endpoints == pytest.approx(
        {
            "minimum": 0.0,
            "second_lowest": 10.0 * np.log10(2.0),
            "second_highest": 10.0 * np.log10(12.0),
            "maximum": 10.0 * np.log10(13.0),
        }
    )
    ordered = report["looks"][0]["fixed_route_cdf"]["models"]["isotropic"]["ordered_estimate_db"]
    assert len(ordered) == 13
    assert ordered[0] == pytest.approx(endpoints["minimum"])
    assert ordered[-1] == pytest.approx(endpoints["maximum"])


def test_large_seed_noise_fails_the_uncertainty_gate() -> None:
    rng = np.random.default_rng(7)
    replicas = 10.0 ** rng.normal(0.0, 2.0 / 10.0, size=(32, 13, 3))
    report = analyse_chi_replicas(
        replicas,
        looks=(8, 16, 24, 32),
        formal_looks=(16, 24, 32),
        bootstrap_replicates=500,
    )

    assert report["stopped"] is False
    assert report["cap_reached"] is True
    assert any(not look["point_uncertainty"]["pass"] for look in report["looks"])


def test_config_pins_the_production_replica_sequence(tmp_path: pathlib.Path) -> None:
    document = {
        "contract": "korenmarkt_cdf_stopping_4096_v1",
        "root": ".",
        "output_dir": "output",
        "reference": {"manifest": "m.json", "locations": "l.jsonl", "spectra": "s.npz"},
        "base_seeds": list(range(7, 39)),
        "diagnostic_look": 8,
        "looks": [16, 24, 32],
        "bootstrap": {"replicates": 20000, "seed": 20260805, "confidence": 0.95},
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(document))
    config = CdfConvergenceConfig.load(path)

    assert config.all_looks == (8, 16, 24, 32)
    assert config.base_seeds == tuple(range(7, 39))
    document["looks"] = [16, 32]
    path.write_text(json.dumps(document))
    with pytest.raises(ValueError, match="production CDF stopping contract changed"):
        CdfConvergenceConfig.load(path)


def test_cli_exposes_input_only_and_archived_validation_modes() -> None:
    assert arguments(["--dry-run"]).dry_run is True
    assert arguments(["--analyse-only"]).analyse_only is True
    assert arguments(["--archived-rooftop-diagnostic"]).archived_rooftop_diagnostic is True


def test_compact_checkpoint_round_trip_rejects_a_different_identity(tmp_path: pathlib.Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "root": ".",
                "output_dir": "output",
                "reference": {"manifest": "m", "locations": "l", "spectra": "s"},
                "base_seeds": list(range(7, 39)),
                "looks": [16, 24, 32],
                "bootstrap": {"replicates": 100, "seed": 4},
            }
        )
    )
    config = CdfConvergenceConfig.load(config_path)
    reference = SimpleNamespace(
        standpoints=SimpleNamespace(index=np.asarray([0, 2]), sha256="points"),
        manifest={"run": {"local_cells": 3}, "body": {"triangles": 3}},
    )
    checkpoint = CampaignCheckpoint(
        base_seeds=np.asarray([7]),
        chi=np.ones((1, 2, 3)),
        chi_direct=np.full((1, 2, 3), 0.5),
        body_peak_rooftop=np.ones((1, 2)),
        body_mean_rooftop=np.full((1, 2), 0.5),
        body_sab_rooftop=np.tile(np.asarray([1.0, 0.5, 0.0]), (1, 2, 1)),
        trace_seconds=np.full((1, 2), 0.1),
        rho_sum=np.ones((2, 3, 3)),
        local_grid=fibonacci_sphere(3),
        solid_angle=4.0 * np.pi / 3.0,
    )
    path = tmp_path / "checkpoint.npz"
    _write_campaign_checkpoint(path, checkpoint, "identity", reference, "tissue")

    loaded = _load_campaign_checkpoint(path, "identity", reference, config, "tissue")
    assert loaded is not None
    assert np.array_equal(loaded.rho_sum, checkpoint.rho_sum)
    assert _load_campaign_checkpoint(path, "other", reference, config, "tissue") is None
    assert _load_campaign_checkpoint(path, "identity", reference, config, "changed-tissue") is None

    changed_grid = checkpoint.local_grid.copy()
    changed_grid[0, 0] = np.nextafter(changed_grid[0, 0], np.inf)
    altered = replace(checkpoint, local_grid=changed_grid)
    _write_campaign_checkpoint(path, altered, "identity", reference, "tissue")
    assert _load_campaign_checkpoint(path, "identity", reference, config, "tissue") is None


def test_replica_keeps_the_base_seed_mapping_and_only_one_spectrum_sum() -> None:
    grid = np.eye(3)
    calls: list[int] = []

    class Result:
        local_grid = grid
        local_solid_angle = 4.0 * np.pi / 3.0
        seconds = 0.2

        def __init__(self, seed: int) -> None:
            self.rho = {
                name: np.full(3, float(seed + model + 1))
                for model, name in enumerate(
                    (
                        "isotropic",
                        "rooftop",
                        "street_small_cell",
                    )
                )
            }

        def scalars(self) -> dict[str, float]:
            out: dict[str, float] = {}
            for model, name in enumerate(("isotropic", "rooftop", "street_small_cell")):
                out[f"chi_{name}"] = float(model + 1)
                out[f"chi_{name}_direct"] = float(model + 1) / 2.0
            return out

    class Tracer:
        def trace(self, point: np.ndarray, models: object, *, ground_z_m: float, seed: int) -> Result:
            calls.append(seed)
            return Result(seed)

    exposure = SimpleNamespace(peak_sab_w_m2=2.0, mean_sab_w_m2=1.0)
    coupler = SimpleNamespace(couple_many_with_sab=lambda *args, **kwargs: ((exposure,), np.asarray([[2.0, 1.0, 0.0]])))
    reference = SimpleNamespace(
        standpoints=SimpleNamespace(
            index=np.asarray([0, 3]),
            points=np.zeros((2, 3)),
            ground_z_m=np.zeros(2),
        ),
        manifest={"reference_s0_w_m2": 1.0},
    )
    empty = CampaignCheckpoint(
        base_seeds=np.empty(0, dtype=np.int64),
        chi=np.empty((0, 2, 3)),
        chi_direct=np.empty((0, 2, 3)),
        body_peak_rooftop=np.empty((0, 2)),
        body_mean_rooftop=np.empty((0, 2)),
        body_sab_rooftop=np.empty((0, 2, 3)),
        trace_seconds=np.empty((0, 2)),
        rho_sum=np.zeros((2, 3, 3)),
        local_grid=grid,
        solid_angle=4.0 * np.pi / 3.0,
    )

    result = _trace_replica(SimpleNamespace(body_chunk_cells=2), reference, Tracer(), coupler, empty, 7)

    assert calls == [7, 3007]
    assert result.base_seeds.tolist() == [7]
    assert result.chi.shape == (1, 2, 3)
    assert result.rho_sum.shape == (2, 3, 3)
    assert result.body_peak_rooftop.tolist() == [[2.0, 2.0]]
    assert result.body_sab_rooftop.shape == (1, 2, 3)


def test_checkpoint_analysis_covers_every_curve_in_the_published_cdf(tmp_path: pathlib.Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "root": ".",
                "output_dir": "output",
                "reference": {"manifest": "m", "locations": "l", "spectra": "s"},
                "base_seeds": list(range(7, 39)),
                "looks": [16, 24, 32],
                "bootstrap": {"replicates": 200, "seed": 4},
            }
        )
    )
    config = CdfConvergenceConfig.load(config_path)
    replicas = _quiet_replicas()
    rooftop_peak = replicas[:, :, 1] * 0.2
    checkpoint = CampaignCheckpoint(
        base_seeds=np.arange(7, 39),
        chi=replicas,
        chi_direct=replicas * 0.8,
        body_peak_rooftop=rooftop_peak,
        body_mean_rooftop=replicas[:, :, 1] * 0.1,
        body_sab_rooftop=np.stack((rooftop_peak, np.zeros_like(rooftop_peak)), axis=2),
        trace_seconds=np.ones((32, 13)),
        rho_sum=np.ones((13, 3, 4)),
        local_grid=np.ones((4, 3)),
        solid_angle=np.pi,
    )

    report = _analyse_checkpoint(config, checkpoint, "campaign")

    final = report["looks"][-1]
    assert set(final["direct_susceptibility"]["models"]) == {
        "isotropic",
        "rooftop",
        "street_small_cell",
    }
    assert len(final["body_peak_rooftop"]["fixed_route_cdf"]["ordered_estimate_db"]) == 13
    assert len(final["body_mean_rooftop"]["fixed_route_cdf"]["ordered_estimate_db"]) == 13
    assert final["coverage"]["joint_family_statistics"] == 150
    assert final["body_peak_rooftop"]["face_mean_family_statistics"] == 26
    assert final["coverage"]["per_look_confidence_nominal"] == pytest.approx(59.0 / 60.0)
    assert report["planned_look_coverage"]["production_exact_values"]["alpha_per_formal_look"] == "1/60"
    assert report["identity_sha256"] == "campaign"
    assert report["stop_at_replicas"] == 24


def test_joint_analysis_keeps_physical_direct_zeros_without_a_db_floor() -> None:
    total = np.ones((16, 3, 1), dtype=np.float64)
    direct = np.ones_like(total)
    direct[:, 0, 0] = 0.0
    direct[:8, 1, 0] = 0.0
    sab = np.zeros((16, 3, 2), dtype=np.float64)
    sab[:, :, 0] = 0.2
    mean = np.full((16, 3), 0.1)

    report = analyse_joint_replicas(
        total,
        direct,
        sab,
        mean,
        looks=(8, 16),
        planned_formal_looks=(8, 16),
        model_names=("rooftop",),
        bootstrap_replicates=200,
    )

    direct_report = report["looks"][-1]["direct_susceptibility"]
    rooftop = direct_report["models"]["rooftop"]
    assert rooftop["point_estimate_linear"][0] == 0.0
    assert rooftop["point_estimate_db"][0] is None
    assert rooftop["cdf_atom_at_zero"] == pytest.approx(1.0 / 3.0)
    assert rooftop["zero_replica_count_by_standpoint"] == [16, 8, 0]
    assert "No logarithmic floor" in direct_report["zero_policy"]
    assert any("direct susceptibility" in value for value in report["confidence_family"]["excluded"])


def test_body_peak_targets_maximum_of_the_mean_surface_field() -> None:
    replicas = 16
    total = np.ones((replicas, 2, 1), dtype=np.float64)
    direct = np.full_like(total, 0.5)
    sab = np.empty((replicas, 2, 2), dtype=np.float64)
    sab[0::2, 0] = (1.01, 1.0)
    sab[1::2, 0] = (1.0, 1.01)
    sab[:, 1] = (4.0, 1.0)
    mean = np.mean(sab, axis=2)

    report = analyse_joint_replicas(
        total,
        direct,
        sab,
        mean,
        looks=(16,),
        planned_formal_looks=(16,),
        model_names=("rooftop",),
        bootstrap_replicates=200,
    )

    body = report["looks"][0]["body_peak_rooftop"]
    assert body["point_estimate_db"][0] == pytest.approx(10.0 * np.log10(1.005))
    assert body["point_estimate_db"][0] != pytest.approx(10.0 * np.log10(1.01))
    selection = body["peak_selection_stability"]
    assert selection["points"][0]["seed_mean_peak_minus_physical_peak_db"] == pytest.approx(
        10.0 * np.log10(1.01 / 1.005)
    )
    assert selection["points"][0]["pass"] is False
    assert "tied peak surfaces" in body["interval_method"]
    assert report["looks"][0]["uncertainty_pass"] is True


def test_chunked_body_peak_bootstrap_matches_brute_force() -> None:
    rng = np.random.default_rng(104)
    sab = rng.uniform(0.1, 2.0, size=(4, 2, 5))
    indices = rng.integers(0, 4, size=(101, 4))

    estimate, face_band, _selection = _bootstrap_peak_of_mean_sab(
        sab,
        indices,
        minimum_stable_fraction=0.5,
        bootstrap_batch=3,
    )
    brute_fields = np.mean(sab[indices], axis=1)
    scale = np.std(sab, axis=0, ddof=0) / np.sqrt(4)
    standardized = np.divide(
        np.abs(brute_fields - np.mean(sab, axis=0)),
        scale,
        out=np.zeros_like(brute_fields),
        where=scale > 0.0,
    )

    assert estimate == pytest.approx(np.max(np.mean(sab, axis=0), axis=1))
    assert face_band["estimate_surface"] == pytest.approx(np.mean(sab, axis=0))
    assert face_band["scale_surface"] == pytest.approx(scale)
    assert face_band["standardized_max"] == pytest.approx(np.max(standardized, axis=(1, 2)))

    _estimate_one, face_band_one, _selection_one = _bootstrap_peak_of_mean_sab(
        sab,
        indices,
        minimum_stable_fraction=0.5,
        bootstrap_batch=1,
    )
    assert face_band_one["standardized_max"] == pytest.approx(face_band["standardized_max"])


def test_identity_mismatch_quarantines_every_managed_look_file(tmp_path: pathlib.Path) -> None:
    output = tmp_path / "output"
    output.mkdir()
    (output / "plan.json").write_text(json.dumps({"identity_sha256": "old"}))
    (output / "analysis_look16.json").write_text(json.dumps({"identity_sha256": "old"}))
    (output / "cdf_convergence.png").write_bytes(b"figure")
    diagnostic = output / "existing_rooftop_diagnostic.json"
    diagnostic.write_text("{}")

    destination = _quarantine_stale_generation(output, "new")

    assert destination is not None
    assert not (output / "plan.json").exists()
    assert not (output / "analysis_look16.json").exists()
    assert (destination / "plan.json").is_file()
    assert (destination / "analysis_look16.json").is_file()
    assert (destination / "cdf_convergence.png").is_file()
    assert diagnostic.is_file()
    record = json.loads((destination / "quarantine_record.json").read_text())
    assert record["replacement_identity_sha256"] == "new"

    (output / "plan.json").write_text(json.dumps({"identity_sha256": "new"}))
    assert _quarantine_stale_generation(output, "new") is None


def test_manifest_names_only_matching_planned_look_analyses(tmp_path: pathlib.Path) -> None:
    output = tmp_path / "output"
    output.mkdir()
    identity = "campaign"
    for name in ("plan.json", "analysis.json"):
        (output / name).write_text(json.dumps({"identity_sha256": identity}))
    for look in (16, 24):
        (output / f"analysis_look{look}.json").write_text(json.dumps({"identity_sha256": identity}))
    (output / "analysis_look32.json").write_text(json.dumps({"identity_sha256": "stale"}))
    for name in ("checkpoint.npz", "ensemble_locations.jsonl", "cdf_convergence.png", "cdf_convergence.pdf"):
        (output / name).write_bytes(name.encode())

    config = SimpleNamespace(
        output_dir=output,
        looks=(16, 24, 32),
        scientific_config=lambda: {"test": True},
    )
    reference = SimpleNamespace(as_dict=lambda: {"reference": True})
    checkpoint = SimpleNamespace(
        replicas=24,
        base_seeds=np.arange(24),
        trace_seconds=np.ones((24, 2)),
    )
    manifest = _campaign_manifest(
        config,
        reference,
        checkpoint,
        identity,
        {"source": True},
        {"sha256": "tissue"},
        output / "analysis.json",
    )

    assert "formal_look_16" in manifest["artifacts"]
    assert "formal_look_24" in manifest["artifacts"]
    assert "formal_look_32" not in manifest["artifacts"]

    (output / "analysis_look24.json").write_text(json.dumps({"identity_sha256": "stale"}))
    with pytest.raises(RuntimeError, match="different campaign identity"):
        _campaign_manifest(
            config,
            reference,
            checkpoint,
            identity,
            {"source": True},
            {"sha256": "tissue"},
            output / "analysis.json",
        )


def test_reached_look_files_are_regenerated_after_checkpoint_crash(tmp_path: pathlib.Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "root": ".",
                "output_dir": "output",
                "reference": {"manifest": "m", "locations": "l", "spectra": "s"},
                "base_seeds": list(range(7, 39)),
                "diagnostic_look": 8,
                "looks": [16, 24, 32],
                "bootstrap": {"replicates": 100, "seed": 4},
            }
        )
    )
    config = CdfConvergenceConfig.load(config_path)
    replicas = _quiet_replicas()[:24]
    peak = replicas[:, :, 1] * 0.2
    checkpoint = CampaignCheckpoint(
        base_seeds=np.arange(7, 31),
        chi=replicas,
        chi_direct=replicas * 0.8,
        body_peak_rooftop=peak,
        body_mean_rooftop=peak / 2.0,
        body_sab_rooftop=np.stack((peak, np.zeros_like(peak)), axis=2),
        trace_seconds=np.ones((24, 13)),
        rho_sum=np.ones((13, 3, 4)),
        local_grid=np.ones((4, 3)),
        solid_angle=np.pi,
    )

    report = _write_reached_formal_analyses(config, checkpoint, "campaign")

    assert report is not None
    look16_path = config.output_dir / "analysis_look16.json"
    look24_path = config.output_dir / "analysis_look24.json"
    assert [look["replicas"] for look in json.loads(look16_path.read_text())["looks"]] == [8, 16]
    assert [look["replicas"] for look in json.loads(look24_path.read_text())["looks"]] == [8, 16, 24]
    look24_bytes = look24_path.read_bytes()

    look16_path.unlink()
    _write_reached_formal_analyses(config, checkpoint, "campaign")

    assert look16_path.is_file()
    assert look24_path.read_bytes() == look24_bytes


def test_same_identity_dry_run_preserves_a_sealed_plan(tmp_path: pathlib.Path) -> None:
    output = tmp_path / "output"
    output.mkdir()
    identity = "campaign"
    plan_path = output / "plan.json"
    analysis_path = output / "analysis.json"
    plan_path.write_text(json.dumps({"identity_sha256": identity, "created_utc": "original"}) + "\n")
    analysis_path.write_text("sealed analysis\n")

    def metadata(path: pathlib.Path) -> dict[str, object]:
        payload = path.read_bytes()
        return {
            "path": path.name,
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }

    (output / "manifest.json").write_text(
        json.dumps(
            {
                "identity_sha256": identity,
                "artifacts": {"plan": metadata(plan_path), "analysis": metadata(analysis_path)},
            }
        )
    )
    original = plan_path.read_bytes()

    prepared = _prepare_campaign_plan(
        output,
        identity,
        {"identity_sha256": identity, "created_utc": "replacement"},
        dry_run=True,
    )

    assert prepared == plan_path
    assert plan_path.read_bytes() == original

    analysis_path.write_text("changed\n")
    with pytest.raises(RuntimeError, match="does not match its manifest"):
        _prepare_campaign_plan(
            output,
            identity,
            {"identity_sha256": identity, "created_utc": "replacement"},
            dry_run=True,
        )


@pytest.mark.parametrize("dry_run", [False, True])
def test_missing_sealed_plan_is_never_recreated(tmp_path: pathlib.Path, dry_run: bool) -> None:
    output = tmp_path / "output"
    output.mkdir()
    identity = "campaign"
    plan_path = output / "plan.json"
    payload = json.dumps({"identity_sha256": identity, "created_utc": "sealed"}) + "\n"
    plan_path.write_text(payload)
    (output / "manifest.json").write_text(
        json.dumps(
            {
                "identity_sha256": identity,
                "artifacts": {
                    "plan": {
                        "path": plan_path.name,
                        "bytes": len(payload.encode()),
                        "sha256": hashlib.sha256(payload.encode()).hexdigest(),
                    }
                },
            }
        )
    )
    plan_path.unlink()

    with pytest.raises(RuntimeError, match="sealed artifact plan is missing"):
        _prepare_campaign_plan(
            output,
            identity,
            {"identity_sha256": identity, "created_utc": "replacement"},
            dry_run=dry_run,
        )

    assert not plan_path.exists()


def test_production_tissue_database_hash_is_pinned() -> None:
    config = SimpleNamespace(contract="korenmarkt_cdf_stopping_4096_v1")
    expected = {
        "path": "/data/itis_v5.db",
        "sha256": "51dc983da2fa4e40bde9ca4e9830ecd6b41739c2b92b28b5efbdc5d5e556aa8f",
        "bytes": 7_094_272,
    }
    _validate_production_tissue_database(config, expected)
    with pytest.raises(ValueError, match="IT'IS tissue database changed"):
        _validate_production_tissue_database(config, {**expected, "sha256": "changed"})


def test_final_rows_publish_the_body_peak_estimator_that_the_stop_bounds() -> None:
    checkpoint = CampaignCheckpoint(
        base_seeds=np.asarray([7, 8]),
        chi=np.ones((2, 2, 3)),
        chi_direct=np.full((2, 2, 3), 0.5),
        body_peak_rooftop=np.asarray([[4.0, 7.0], [3.0, 6.0]]),
        body_mean_rooftop=np.asarray([[2.5, 5.5], [2.5, 5.5]]),
        body_sab_rooftop=np.asarray(
            [
                [[4.0, 1.0], [7.0, 4.0]],
                [[2.0, 3.0], [5.0, 6.0]],
            ]
        ),
        trace_seconds=np.ones((2, 2)),
        rho_sum=np.ones((2, 3, 2)),
        local_grid=fibonacci_sphere(2),
        solid_angle=2.0 * np.pi,
    )

    class Exposure:
        def __init__(self, value: float) -> None:
            self.susceptibility = value
            self.peak_sab_w_m2 = value + 1.0

        def as_dict(self) -> dict[str, float]:
            return {
                "reference_s0_w_m2": 1.0,
                "arriving_power_density_w_m2": self.susceptibility,
                "susceptibility": self.susceptibility,
                "peak_sab_w_m2": self.peak_sab_w_m2,
                "mean_sab_w_m2": self.susceptibility + 0.5,
                "absorbed_power_w": 1.0,
                "sar_wb_w_kg": 0.1,
            }

    exposures = tuple(Exposure(float(index + 1)) for index in range(6))
    coupler = SimpleNamespace(couple_many=lambda *args, **kwargs: exposures)
    study = SimpleNamespace(
        PHANTOM="body",
        PHANTOM_MASS_KG=70.0,
        BodyCoupler=lambda *args, **kwargs: coupler,
    )
    reference = SimpleNamespace(
        manifest={"run": {"frequency_hz": 15.0e9}, "reference_s0_w_m2": 1.0},
        standpoints=SimpleNamespace(
            index=np.asarray([0, 1]),
            points=np.zeros((2, 3)),
            ground_z_m=np.zeros(2),
            point_kind=("camera_registered", "stride_interpolated"),
        ),
    )

    ensemble = _final_ensemble(
        SimpleNamespace(looks=(2, 3), body_chunk_cells=2),
        reference,
        checkpoint,
        {"stop_at_replicas": 2},
        study,
    )

    assert [row["rooftop_peak_sab_w_m2"] for row in ensemble["rows"]] == [3.0, 6.0]
    assert [row["rooftop_seed_mean_peak_sab_w_m2"] for row in ensemble["rows"]] == [3.5, 6.5]
    assert ensemble["published_body_peak"]["field"] == "rooftop_peak_sab_w_m2"
    assert ensemble["body_peak_jensen_diagnostic"]["confidence_bounded"] is False
    assert ensemble["body_peak_retained_field_check"]["maximum_absolute_difference_db"] == pytest.approx(0.0)
