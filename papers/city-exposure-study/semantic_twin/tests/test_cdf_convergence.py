from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

import semantic_twin.exposure.cdf_convergence as cdf_convergence
import semantic_twin.exposure.cdf_contracts as cdf_contracts
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
    _validate_production_reference,
    _write_campaign_checkpoint,
    _write_reached_formal_analyses,
    analyse_chi_replicas,
    analyse_joint_replicas,
    archived_rooftop_diagnostic,
)
from semantic_twin.exposure.cdf_contracts import (
    CdfProductionContract,
    KORENMARKT_CDF_STOPPING_4096_V1,
    PRODUCTION_CDF_CONTRACTS,
    body_sources,
    registered_body_sources,
    registered_reference_triples,
)
from semantic_twin.illumination import fibonacci_sphere
from tools.cdf_contract_references import main as reference_helper_main

STUDY_ROOT = pathlib.Path(__file__).resolve().parents[1]
PRODUCTION_CONFIG = STUDY_ROOT / "config" / "cdf_convergence_4096.json"


def _custom_config_document() -> dict[str, object]:
    return {
        "contract": "custom",
        "root": ".",
        "output_dir": "output",
        "reference": {"manifest": "m", "locations": "l", "spectra": "s"},
        "base_seeds": list(range(7, 39)),
        "seed_stream_stride": 1000,
        "diagnostic_look": 8,
        "looks": [16, 24, 32],
        "bootstrap": {"replicates": 100, "seed": 4, "confidence": 0.95},
        "body_model": "rooftop",
        "body_source": {"phantom": "duke", "mass_kg": 72.4},
    }


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


def test_config_pins_the_production_replica_sequence() -> None:
    config = CdfConvergenceConfig.load(PRODUCTION_CONFIG)
    assert config.all_looks == (8, 16, 24, 32)
    assert config.base_seeds == tuple(range(7, 39))
    assert config.body_model == "rooftop"
    assert config.body_source == "duke"
    assert config.seed_stream_stride == 1000
    assert config.production_contract is KORENMARKT_CDF_STOPPING_4096_V1


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("output_dir",), "outputs/changed"),
        (("reference", "manifest"), "outputs/changed_manifest.json"),
        (("reference", "locations"), "outputs/changed_locations.jsonl"),
        (("reference", "spectra"), "outputs/changed_spectra.npz"),
        (("base_seeds",), list(range(8, 40))),
        (("seed_stream_stride",), 999),
        (("diagnostic_look",), 9),
        (("looks",), [16, 25, 32]),
        (("bootstrap", "replicates"), 19_999),
        (("bootstrap", "seed"), 20260806),
        (("bootstrap", "confidence"), 0.94),
        (("bootstrap", "alpha_allocation"), "changed allocation"),
        (("body_peak", "chunk_cells"), 256),
        (("body_peak", "selection_stability_min_fraction"), 0.90),
        (("body_model",), "isotropic"),
        (("body_source", "phantom"), "ella"),
        (("body_source", "mass_kg"), 58.0),
        (("thresholds", "point_p90_db"), 0.11),
        (("thresholds", "point_max_db"), 0.16),
        (("thresholds", "cdf_q50_db"), 0.06),
        (("thresholds", "cdf_q10_q90_db"), 0.11),
        (("thresholds", "cdf_endpoint_db"), 0.16),
        (("thresholds", "stability_wasserstein_db"), 0.04),
        (("thresholds", "stability_q50_db"), 0.04),
        (("thresholds", "stability_q10_q90_db"), 0.06),
        (("thresholds", "stability_endpoint_db"), 0.11),
        (("thresholds", "body_peak_max_db"), 0.16),
    ],
)
def test_every_production_config_pin_rejects_mutation(
    tmp_path: pathlib.Path,
    path: tuple[str, ...],
    replacement: object,
) -> None:
    document = json.loads(PRODUCTION_CONFIG.read_text())
    document["root"] = str(STUDY_ROOT)
    target = document
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = replacement
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(document))

    with pytest.raises(ValueError, match="production CDF stopping contract changed"):
        CdfConvergenceConfig.load(config_path)


def test_unknown_named_contract_fails_and_custom_is_visibly_unpinned(tmp_path: pathlib.Path) -> None:
    document = _custom_config_document()
    document["contract"] = "tokyo_unsealed_claim"
    path = tmp_path / "unknown.json"
    path.write_text(json.dumps(document))
    with pytest.raises(ValueError, match="unknown production CDF contract"):
        CdfConvergenceConfig.load(path)

    document["contract"] = "custom"
    path.write_text(json.dumps(document))
    config = CdfConvergenceConfig.load(path)
    assert config.production_contract is None
    assert config.scientific_config()["contract_pinning"] == {
        "production": False,
        "status": "unpinned custom campaign",
    }


def test_cli_exposes_input_only_and_archived_validation_modes() -> None:
    assert arguments(["--dry-run"]).dry_run is True
    assert arguments(["--analyse-only"]).analyse_only is True
    assert arguments(["--archived-rooftop-diagnostic"]).archived_rooftop_diagnostic is True


def test_compact_checkpoint_round_trip_rejects_a_different_identity(tmp_path: pathlib.Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(_custom_config_document()))
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


def test_non_thirteen_point_custom_route_keeps_checkpoint_and_bootstrap_guarantees(
    tmp_path: pathlib.Path,
) -> None:
    document = _custom_config_document()
    document.update(
        {
            "base_seeds": [7, 8, 9, 10],
            "diagnostic_look": 2,
            "looks": [3, 4],
        }
    )
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(document))
    config = CdfConvergenceConfig.load(config_path)
    replicas = 4
    points = 5
    chi = np.ones((replicas, points, 3), dtype=np.float64)
    body_sab = np.tile(np.asarray([2.0, 0.0]), (replicas, points, 1))
    checkpoint = CampaignCheckpoint(
        base_seeds=np.asarray(config.base_seeds),
        chi=chi,
        chi_direct=chi / 2.0,
        body_peak_rooftop=np.full((replicas, points), 2.0),
        body_mean_rooftop=np.ones((replicas, points)),
        body_sab_rooftop=body_sab,
        trace_seconds=np.ones((replicas, points)),
        rho_sum=np.ones((points, 3, 3)),
        local_grid=fibonacci_sphere(3),
        solid_angle=4.0 * np.pi / 3.0,
    )
    reference = SimpleNamespace(
        standpoints=SimpleNamespace(index=np.arange(points), sha256="five-points"),
        manifest={"run": {"local_cells": 3}, "body": {"triangles": 2}},
    )
    path = tmp_path / "checkpoint.npz"
    _write_campaign_checkpoint(path, checkpoint, "custom-five", reference, "tissue")

    loaded = _load_campaign_checkpoint(path, "custom-five", reference, config, "tissue")
    assert loaded is not None
    report = _analyse_checkpoint(config, loaded, "custom-five")
    assert report["route_sample"] == {
        "standpoints": 5,
        "cdf_step": pytest.approx(0.2),
        "spatial_sampling_uncertainty_included": False,
    }
    assert report["bootstrap"]["resampling"].startswith("base-seed walk clusters")
    assert [look["replicas"] for look in report["looks"]] == [2, 3, 4]


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

    result = _trace_replica(
        SimpleNamespace(
            body_chunk_cells=2,
            body_model="rooftop",
            seed_stream_stride=1000,
        ),
        reference,
        Tracer(),
        coupler,
        empty,
        7,
    )

    assert calls == [7, 3007]
    assert result.base_seeds.tolist() == [7]
    assert result.chi.shape == (1, 2, 3)
    assert result.rho_sum.shape == (2, 3, 3)
    assert result.body_peak_rooftop.tolist() == [[2.0, 2.0]]
    assert result.body_sab_rooftop.shape == (1, 2, 3)


def test_body_spectrum_follows_its_name_when_model_order_changes(monkeypatch: pytest.MonkeyPatch) -> None:
    order = ("street_small_cell", "isotropic", "rooftop")
    monkeypatch.setattr(cdf_convergence, "MODEL_NAMES", order)
    selected: list[np.ndarray] = []

    class Result:
        local_grid = np.eye(3)
        local_solid_angle = 4.0 * np.pi / 3.0
        seconds = 0.1
        rho = {
            "isotropic": np.full(3, 1.0),
            "rooftop": np.full(3, 22.0),
            "street_small_cell": np.full(3, 333.0),
        }

        def scalars(self) -> dict[str, float]:
            return {
                **{f"chi_{name}": float(index + 1) for index, name in enumerate(order)},
                **{f"chi_{name}_direct": 0.5 for name in order},
            }

    tracer = SimpleNamespace(trace=lambda *args, **kwargs: Result())
    exposure = SimpleNamespace(peak_sab_w_m2=2.0, mean_sab_w_m2=1.0)

    def couple(
        _grid: np.ndarray, spectra: np.ndarray, *_args: object, **_kwargs: object
    ) -> tuple[tuple[object], np.ndarray]:
        selected.append(np.array(spectra, copy=True))
        return (exposure,), np.asarray([[2.0, 1.0, 0.0]])

    reference = SimpleNamespace(
        standpoints=SimpleNamespace(
            index=np.asarray([4]),
            points=np.zeros((1, 3)),
            ground_z_m=np.zeros(1),
        ),
        manifest={"reference_s0_w_m2": 1.0},
    )
    checkpoint = CampaignCheckpoint(
        base_seeds=np.empty(0, dtype=np.int64),
        chi=np.empty((0, 1, 3)),
        chi_direct=np.empty((0, 1, 3)),
        body_peak_rooftop=np.empty((0, 1)),
        body_mean_rooftop=np.empty((0, 1)),
        body_sab_rooftop=np.empty((0, 1, 3)),
        trace_seconds=np.empty((0, 1)),
        rho_sum=np.zeros((1, 3, 3)),
        local_grid=np.eye(3),
        solid_angle=4.0 * np.pi / 3.0,
    )

    _trace_replica(
        SimpleNamespace(body_chunk_cells=2, body_model="rooftop", seed_stream_stride=1000),
        reference,
        tracer,
        SimpleNamespace(couple_many_with_sab=couple),
        checkpoint,
        7,
    )

    assert len(selected) == 1
    assert selected[0] == pytest.approx(np.full((1, 3), 22.0))


def test_checkpoint_analysis_covers_every_curve_in_the_published_cdf(tmp_path: pathlib.Path) -> None:
    config_path = tmp_path / "config.json"
    document = _custom_config_document()
    document["bootstrap"] = {"replicates": 200, "seed": 4, "confidence": 0.95}
    config_path.write_text(json.dumps(document))
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
    config_path.write_text(json.dumps(_custom_config_document()))
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
    config = CdfConvergenceConfig.load(PRODUCTION_CONFIG)
    expected = {
        "path": "/data/itis_v5.db",
        "sha256": "51dc983da2fa4e40bde9ca4e9830ecd6b41739c2b92b28b5efbdc5d5e556aa8f",
        "bytes": 7_094_272,
    }
    _validate_production_tissue_database(config, expected)
    with pytest.raises(ValueError, match="IT'IS tissue database changed"):
        _validate_production_tissue_database(config, {**expected, "sha256": "changed"})


def _production_reference(
    contract: CdfProductionContract = KORENMARKT_CDF_STOPPING_4096_V1,
) -> SimpleNamespace:
    identity = {
        **contract.identity_hash_values(),
        "body_sha256": contract.body.sha256,
        "reference_files": {name: {"sha256": sha256} for name, sha256 in contract.reference.hashes().items()},
    }
    return SimpleNamespace(
        manifest={
            "run": contract.run_setting_values(),
            "body": contract.body.manifest_fields(),
        },
        standpoints=SimpleNamespace(
            index=np.arange(sum(contract.point_kind_count_values().values())),
            point_kind=tuple(kind for kind, count in contract.point_kind_counts for _ in range(count)),
        ),
        as_dict=lambda: identity,
    )


def test_unchanged_production_reference_hashes_and_run_settings_pass() -> None:
    _validate_production_reference(CdfConvergenceConfig.load(PRODUCTION_CONFIG), _production_reference())


@pytest.mark.parametrize(
    "field",
    (*KORENMARKT_CDF_STOPPING_4096_V1.identity_hash_values(), "body_sha256"),
)
def test_each_production_identity_hash_mutation_fails(field: str) -> None:
    reference = _production_reference()
    identity = reference.as_dict()
    identity[field] = "changed"
    with pytest.raises(ValueError, match="reference hashes changed"):
        _validate_production_reference(CdfConvergenceConfig.load(PRODUCTION_CONFIG), reference)


@pytest.mark.parametrize("field", KORENMARKT_CDF_STOPPING_4096_V1.reference.hashes())
def test_each_production_reference_file_hash_mutation_fails(field: str) -> None:
    reference = _production_reference()
    reference.as_dict()["reference_files"][field]["sha256"] = "changed"
    with pytest.raises(ValueError, match="output generation changed"):
        _validate_production_reference(CdfConvergenceConfig.load(PRODUCTION_CONFIG), reference)


@pytest.mark.parametrize("field", KORENMARKT_CDF_STOPPING_4096_V1.run_setting_values())
def test_each_production_run_setting_mutation_fails(field: str) -> None:
    reference = _production_reference()
    reference.manifest["run"][field] = "changed"
    with pytest.raises(ValueError, match="run settings changed"):
        _validate_production_reference(CdfConvergenceConfig.load(PRODUCTION_CONFIG), reference)


@pytest.mark.parametrize("field", KORENMARKT_CDF_STOPPING_4096_V1.body.manifest_fields())
def test_each_production_body_source_mutation_fails(field: str) -> None:
    reference = _production_reference()
    reference.manifest["body"][field] = "changed"
    with pytest.raises(ValueError, match="body source changed"):
        _validate_production_reference(CdfConvergenceConfig.load(PRODUCTION_CONFIG), reference)


def test_production_point_kind_counts_are_pinned() -> None:
    reference = _production_reference()
    reference.standpoints.point_kind = (*reference.standpoints.point_kind[:-1], "camera_registered")
    with pytest.raises(ValueError, match="point kinds changed"):
        _validate_production_reference(CdfConvergenceConfig.load(PRODUCTION_CONFIG), reference)


def test_archived_rooftop_diagnostic_rejects_non_korenmarkt_contract(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "custom.json"
    path.write_text(json.dumps(_custom_config_document()))
    with pytest.raises(ValueError, match="only for the Korenmarkt production contract"):
        archived_rooftop_diagnostic(CdfConvergenceConfig.load(path))


def test_reference_enumeration_matches_every_registered_production_config() -> None:
    enumerated = registered_reference_triples()
    assert {config for config, _reference in enumerated} == {
        contract.config_path for contract in PRODUCTION_CDF_CONTRACTS.values()
    }
    assert enumerated == (
        (
            "config/cdf_convergence_4096.json",
            KORENMARKT_CDF_STOPPING_4096_V1.reference.paths(),
        ),
    )


def test_blgpu_sync_propagates_inventory_failure_and_cleans_its_temp_dir(tmp_path: pathlib.Path) -> None:
    helper = tmp_path / "fail_inventory.py"
    helper.write_text("raise SystemExit(23)\n")
    scratch = tmp_path / "tmp"
    scratch.mkdir()
    environment = {
        **os.environ,
        "TMPDIR": str(scratch),
        "BLGPU_CDF_CONTRACT_HELPER": str(helper),
        "BLGPU_PYTHON": sys.executable,
    }

    result = subprocess.run(
        [STUDY_ROOT / "tools" / "blgpu.sh", "sync"],
        cwd=STUDY_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 23
    assert sorted(path.name for path in scratch.iterdir()) == [f"blgpu-ssh-{os.getuid()}"]


def test_registered_body_sources_are_hash_pinned_and_deduplicate_duke() -> None:
    contract = KORENMARKT_CDF_STOPPING_4096_V1
    expected = (("duke.stl", contract.body.sha256),)
    assert registered_body_sources() == expected
    hachiko = replace(contract, name="hachiko", config_path="config/hachiko.json")
    assert body_sources((contract, hachiko)) == expected

    conflicting_body = replace(contract.body, sha256="changed")
    conflicting_hachiko = replace(hachiko, body=conflicting_body)
    with pytest.raises(ValueError, match="conflicting production body hashes"):
        body_sources((contract, conflicting_hachiko))


def test_non_duke_named_contract_controls_body_path_hash_and_sync_inventory(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ella_path = tmp_path / "ella.stl"
    ella_path.write_bytes(b"named Ella body")
    ella_sha = hashlib.sha256(ella_path.read_bytes()).hexdigest()
    base = KORENMARKT_CDF_STOPPING_4096_V1
    ella_body = replace(base.body, phantom="ella", mass_kg=58.0, sha256=ella_sha)
    contract = replace(
        base,
        name="ella_cdf_contract",
        config_path="config/cdf_ella.json",
        body=ella_body,
    )
    monkeypatch.setattr(cdf_contracts, "PRODUCTION_CDF_CONTRACTS", {contract.name: contract})
    monkeypatch.setenv("AEGIS_DATA_DIR", str(tmp_path))
    document = json.loads(PRODUCTION_CONFIG.read_text())
    document.update(
        {
            "contract": contract.name,
            "root": str(STUDY_ROOT),
            "body_source": {"phantom": "ella", "mass_kg": 58.0},
        }
    )
    config_path = tmp_path / "cdf_ella.json"
    config_path.write_text(json.dumps(document))

    config = CdfConvergenceConfig.load(config_path)
    assert config.body_path == ella_path
    assert hashlib.sha256(config.body_path.read_bytes()).hexdigest() == contract.body.sha256
    _validate_production_reference(config, _production_reference(contract))

    assert reference_helper_main(["--sync-inventory"]) == 0
    inventory = capsys.readouterr().out.splitlines()
    assert f"body\tella.stl\t{ella_sha}" in inventory
    assert any(line.startswith("reference\tconfig/cdf_ella.json\t") for line in inventory)


@pytest.mark.parametrize(
    ("stride", "indices"),
    [
        (1, [0, 1]),
        (1000, [0, 0]),
    ],
)
def test_custom_contract_rejects_seed_stream_collisions_after_route_load(
    tmp_path: pathlib.Path,
    stride: int,
    indices: list[int],
) -> None:
    document = _custom_config_document()
    document["seed_stream_stride"] = stride
    path = tmp_path / "custom.json"
    path.write_text(json.dumps(document))
    config = CdfConvergenceConfig.load(path)
    reference = SimpleNamespace(standpoints=SimpleNamespace(index=np.asarray(indices)))

    with pytest.raises(ValueError, match="random-stream collision"):
        _validate_production_reference(config, reference)


def test_custom_contract_accepts_collision_free_seed_streams_after_route_load(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "custom.json"
    path.write_text(json.dumps(_custom_config_document()))
    config = CdfConvergenceConfig.load(path)
    reference = SimpleNamespace(standpoints=SimpleNamespace(index=np.asarray([0, 3, 8])))

    _validate_production_reference(config, reference)


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
        SimpleNamespace(
            looks=(2, 3),
            body_chunk_cells=2,
            body_model="rooftop",
            body_path=pathlib.Path("duke.stl"),
            body_mass_kg=72.4,
        ),
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
