from __future__ import annotations

import json
import pathlib
from types import SimpleNamespace

import numpy as np
import pytest

from run_cdf_convergence import arguments
from semantic_twin.exposure.cdf_convergence import (
    CdfConvergenceConfig,
    CampaignCheckpoint,
    StoppingThresholds,
    _analyse_checkpoint,
    _load_campaign_checkpoint,
    _trace_replica,
    _write_campaign_checkpoint,
    analyse_body_peak_replicas,
    analyse_chi_replicas,
)


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


def test_body_peak_bootstrap_uses_linear_seed_means() -> None:
    values = np.ones((8, 2), dtype=np.float64)
    values[4:] = 100.0
    report = analyse_body_peak_replicas(
        values,
        looks=(8,),
        bootstrap_replicates=500,
        bootstrap_seed=8,
        confidence=0.95,
        maximum_half_width_db=100.0,
    )

    assert report[8]["point_estimate_db"] == pytest.approx([10.0 * np.log10(50.5)] * 2)
    assert report[8]["pass"] is True


def test_config_pins_the_production_replica_sequence(tmp_path: pathlib.Path) -> None:
    document = {
        "contract": "korenmarkt_cdf_stopping_4096_v1",
        "root": ".",
        "output_dir": "output",
        "reference": {"manifest": "m.json", "locations": "l.jsonl", "spectra": "s.npz"},
        "base_seeds": list(range(7, 39)),
        "diagnostic_look": 8,
        "looks": [16, 24, 32],
        "bootstrap": {"replicates": 100, "seed": 2, "confidence": 0.95},
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
        manifest={"run": {"local_cells": 3}},
    )
    checkpoint = CampaignCheckpoint(
        base_seeds=np.asarray([7]),
        chi=np.ones((1, 2, 3)),
        chi_direct=np.full((1, 2, 3), 0.5),
        body_peak_rooftop=np.ones((1, 2)),
        body_mean_rooftop=np.full((1, 2), 0.5),
        trace_seconds=np.full((1, 2), 0.1),
        rho_sum=np.ones((2, 3, 3)),
        local_grid=np.eye(3),
        solid_angle=4.0 * np.pi / 3.0,
    )
    path = tmp_path / "checkpoint.npz"
    _write_campaign_checkpoint(path, checkpoint, "identity", reference)

    loaded = _load_campaign_checkpoint(path, "identity", reference, config)
    assert loaded is not None
    assert np.array_equal(loaded.rho_sum, checkpoint.rho_sum)
    assert _load_campaign_checkpoint(path, "other", reference, config) is None


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
    coupler = SimpleNamespace(couple_many=lambda *args, **kwargs: (exposure,))
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
    checkpoint = CampaignCheckpoint(
        base_seeds=np.arange(7, 39),
        chi=replicas,
        chi_direct=replicas * 0.8,
        body_peak_rooftop=replicas[:, :, 1] * 0.2,
        body_mean_rooftop=replicas[:, :, 1] * 0.1,
        trace_seconds=np.ones((32, 13)),
        rho_sum=np.ones((13, 3, 4)),
        local_grid=np.ones((4, 3)),
        solid_angle=np.pi,
    )

    report = _analyse_checkpoint(config, checkpoint)

    final = report["looks"][-1]
    assert set(final["direct_susceptibility"]["fixed_route_cdf"]["models"]) == {
        "isotropic",
        "rooftop",
        "street_small_cell",
    }
    assert len(final["body_peak_rooftop"]["ordered_estimate_db"]) == 13
    assert len(final["body_mean_rooftop"]["ordered_estimate_db"]) == 13
    assert report["stop_at_replicas"] == 24
