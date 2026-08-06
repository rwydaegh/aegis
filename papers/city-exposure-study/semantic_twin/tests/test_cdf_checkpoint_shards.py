"""Integration checks for the shard-backed CDF tracing loop."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

import semantic_twin.exposure.cdf_convergence as cdf_convergence
from semantic_twin.exposure.checkpoint_store import CheckpointSpec, CheckpointStore
from semantic_twin.exposure.cdf_convergence import (
    CampaignCheckpoint,
    _campaign_checkpoint_from_prefix,
    _load_campaign_checkpoint,
    _performance_ledger,
    _trace_replica,
    _trace_until_stop,
    _write_campaign_checkpoint,
)
from semantic_twin.illumination import fibonacci_sphere


def _reference() -> SimpleNamespace:
    return SimpleNamespace(
        standpoints=SimpleNamespace(
            index=np.asarray([0, 3]),
            points=np.zeros((2, 3)),
            ground_z_m=np.zeros(2),
            sha256="standpoints",
        ),
        manifest={
            "reference_s0_w_m2": 1.0,
            "run": {"local_cells": 3},
            "body": {"triangles": 3},
        },
    )


def _empty() -> CampaignCheckpoint:
    return CampaignCheckpoint(
        base_seeds=np.empty(0, dtype=np.int64),
        chi=np.empty((0, 2, 3), dtype=np.float64),
        chi_direct=np.empty((0, 2, 3), dtype=np.float64),
        body_peak_rooftop=np.empty((0, 2), dtype=np.float64),
        body_mean_rooftop=np.empty((0, 2), dtype=np.float64),
        body_sab_rooftop=np.empty((0, 2, 3), dtype=np.float64),
        trace_seconds=np.empty((0, 2), dtype=np.float64),
        rho_sum=np.zeros((2, 3, 3), dtype=np.float64),
        local_grid=np.eye(3, dtype=np.float64),
        solid_angle=4.0 * np.pi / 3.0,
        body_surface_areas=np.asarray([1.0, 2.0, 3.0], dtype=np.float64),
    )


def _tracer() -> object:
    grid = np.eye(3, dtype=np.float64)

    class Result:
        local_grid = grid
        local_solid_angle = 4.0 * np.pi / 3.0
        seconds = 0.2

        def __init__(self, seed: int) -> None:
            self.rho = {
                name: np.full(3, float(seed + model + 1), dtype=np.float64)
                for model, name in enumerate(("isotropic", "rooftop", "street_small_cell"))
            }

        def scalars(self) -> dict[str, float]:
            return {
                **{
                    f"chi_{name}": float(model + 1)
                    for model, name in enumerate(("isotropic", "rooftop", "street_small_cell"))
                },
                **{
                    f"chi_{name}_direct": float(model + 1) / 2.0
                    for model, name in enumerate(("isotropic", "rooftop", "street_small_cell"))
                },
            }

    class Tracer:
        def trace(self, point: np.ndarray, models: object, *, ground_z_m: float, seed: int) -> Result:
            del point, models, ground_z_m
            return Result(seed)

    return Tracer()


def _coupler() -> SimpleNamespace:
    exposure = SimpleNamespace(peak_sab_w_m2=2.0, mean_sab_w_m2=4.0 / 6.0)
    return SimpleNamespace(
        couple_many_with_sab=lambda *args, **kwargs: (
            (exposure,),
            np.asarray([[2.0, 1.0, 0.0]], dtype=np.float64),
        )
    )


def _config() -> SimpleNamespace:
    return SimpleNamespace(
        base_seeds=(7, 8),
        body_chunk_cells=2,
        body_model="rooftop",
        seed_stream_stride=1000,
        looks=(3,),
    )


def _store(tmp_path) -> CheckpointStore:
    return CheckpointStore(
        tmp_path / "checkpoint_shards",
        CheckpointSpec(
            identity_sha256="identity",
            standpoint_array_sha256="standpoints",
            tissue_database_sha256="tissue",
            model_names=("isotropic", "rooftop", "street_small_cell"),
            planned_seeds=(7, 8),
            surface_elements=3,
            body_surface_areas=np.asarray([1.0, 2.0, 3.0], dtype=np.float64),
            local_grid=np.eye(3, dtype=np.float64),
            solid_angle=4.0 * np.pi / 3.0,
        ),
    )


def test_trace_loop_appends_shards_and_reconstructs_campaign_checkpoint(tmp_path) -> None:
    store = _store(tmp_path)
    performance = _performance_ledger("shards")
    checkpoint, analysis = _trace_until_stop(
        _config(),
        _reference(),
        _tracer(),
        _coupler(),
        _empty(),
        None,
        "identity",
        "tissue",
        checkpoint_store=store,
        performance=performance,
    )
    assert analysis is None
    assert store.replicas == 2
    restored = _campaign_checkpoint_from_prefix(store.load_prefix())
    np.testing.assert_array_equal(restored.base_seeds, checkpoint.base_seeds)
    np.testing.assert_array_equal(restored.chi, checkpoint.chi)
    np.testing.assert_array_equal(restored.body_sab_rooftop, checkpoint.body_sab_rooftop)
    np.testing.assert_array_equal(restored.rho_sum, checkpoint.rho_sum)
    assert len(performance["shard_append"]) == 2
    assert all(record["shard_bytes"] > 0 for record in performance["shard_append"])


def test_shard_trace_does_not_grow_history_arrays_per_replica(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = SimpleNamespace(
        base_seeds=(7, 8, 9),
        body_chunk_cells=2,
        body_model="rooftop",
        seed_stream_stride=1000,
        looks=(5,),
    )
    store = CheckpointStore(
        tmp_path / "checkpoint_shards",
        CheckpointSpec(
            identity_sha256="identity",
            standpoint_array_sha256="standpoints",
            tissue_database_sha256="tissue",
            model_names=("isotropic", "rooftop", "street_small_cell"),
            planned_seeds=(7, 8, 9),
            surface_elements=3,
            body_surface_areas=np.asarray([1.0, 2.0, 3.0], dtype=np.float64),
            local_grid=np.eye(3, dtype=np.float64),
            solid_angle=4.0 * np.pi / 3.0,
        ),
    )

    def fail_history_concatenate(*args: object, **kwargs: object) -> np.ndarray:
        del args, kwargs
        raise AssertionError("replica tracing must not concatenate a full history")

    monkeypatch.setattr(cdf_convergence.np, "concatenate", fail_history_concatenate)
    checkpoint, analysis = _trace_until_stop(
        config,
        _reference(),
        _tracer(),
        _coupler(),
        _empty(),
        None,
        "identity",
        "tissue",
        checkpoint_store=store,
    )

    assert analysis is None
    assert checkpoint.replicas == 3
    assert store.replicas == 3


def test_shard_accumulation_matches_legacy_trace_and_resume_exactly(tmp_path) -> None:
    seeds = (7, 8, 9)
    config = SimpleNamespace(
        base_seeds=seeds,
        body_chunk_cells=2,
        body_model="rooftop",
        seed_stream_stride=1000,
        looks=(5,),
    )

    def make_store(path):
        return CheckpointStore(
            path,
            CheckpointSpec(
                identity_sha256="identity",
                standpoint_array_sha256="standpoints",
                tissue_database_sha256="tissue",
                model_names=("isotropic", "rooftop", "street_small_cell"),
                planned_seeds=seeds,
                surface_elements=3,
                body_surface_areas=np.asarray([1.0, 2.0, 3.0], dtype=np.float64),
                local_grid=np.eye(3, dtype=np.float64),
                solid_angle=4.0 * np.pi / 3.0,
            ),
        )

    full_store = make_store(tmp_path / "full" / "checkpoint_shards")
    full, _ = _trace_until_stop(
        config,
        _reference(),
        _tracer(),
        _coupler(),
        _empty(),
        None,
        "identity",
        "tissue",
        checkpoint_store=full_store,
    )

    legacy = _empty()
    for seed in seeds:
        legacy = _trace_replica(config, _reference(), _tracer(), _coupler(), legacy, seed)

    first = make_store(tmp_path / "resume" / "checkpoint_shards")
    _trace_until_stop(
        SimpleNamespace(**{**vars(config), "base_seeds": (7,)}),
        _reference(),
        _tracer(),
        _coupler(),
        _empty(),
        None,
        "identity",
        "tissue",
        checkpoint_store=first,
    )
    restarted_store = make_store(tmp_path / "resume" / "checkpoint_shards")
    resumed, _ = _trace_until_stop(
        config,
        _reference(),
        _tracer(),
        _coupler(),
        _campaign_checkpoint_from_prefix(restarted_store.load_prefix()),
        None,
        "identity",
        "tissue",
        checkpoint_store=restarted_store,
    )

    for name in (
        "base_seeds",
        "chi",
        "chi_direct",
        "body_peak_rooftop",
        "body_mean_rooftop",
        "body_sab_rooftop",
        "trace_seconds",
        "rho_sum",
        "local_grid",
    ):
        np.testing.assert_array_equal(getattr(full, name), getattr(legacy, name))
        np.testing.assert_array_equal(getattr(full, name), getattr(resumed, name))
    assert full.solid_angle == resumed.solid_angle == legacy.solid_angle


def test_interruption_after_trace_before_index_resumes_from_last_shard(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _store(tmp_path)
    original_append = store.append

    def fail_second(replica, payload):
        if replica == 1:
            raise RuntimeError("forced interruption")
        original_append(replica, payload)

    monkeypatch.setattr(store, "append", fail_second)
    with pytest.raises(RuntimeError, match="forced interruption"):
        _trace_until_stop(
            _config(),
            _reference(),
            _tracer(),
            _coupler(),
            _empty(),
            None,
            "identity",
            "tissue",
            checkpoint_store=store,
        )
    assert store.replicas == 1

    restarted = CheckpointStore(tmp_path / "checkpoint_shards", store.spec)
    prefix = _campaign_checkpoint_from_prefix(restarted.load_prefix())
    checkpoint, analysis = _trace_until_stop(
        _config(),
        _reference(),
        _tracer(),
        _coupler(),
        prefix,
        None,
        "identity",
        "tissue",
        checkpoint_store=restarted,
    )
    assert analysis is None
    assert checkpoint.replicas == 2
    assert restarted.replicas == 2


def test_legacy_checkpoint_path_still_writes_and_reads_monolithic_prefix(tmp_path) -> None:
    checkpoint = CampaignCheckpoint(
        base_seeds=np.asarray([7], dtype=np.int64),
        chi=np.ones((1, 2, 3), dtype=np.float64),
        chi_direct=np.full((1, 2, 3), 0.5, dtype=np.float64),
        body_peak_rooftop=np.full((1, 2), 2.0, dtype=np.float64),
        body_mean_rooftop=np.full((1, 2), 4.0 / 6.0, dtype=np.float64),
        body_sab_rooftop=np.asarray([[[2.0, 1.0, 0.0], [2.0, 1.0, 0.0]]], dtype=np.float64),
        trace_seconds=np.full((1, 2), 0.2, dtype=np.float64),
        rho_sum=np.ones((2, 3, 3), dtype=np.float64),
        local_grid=fibonacci_sphere(3),
        solid_angle=4.0 * np.pi / 3.0,
        body_surface_areas=np.asarray([1.0, 2.0, 3.0], dtype=np.float64),
    )
    reference = _reference()
    config = SimpleNamespace(base_seeds=(7, 8), looks=(3,), body_model="rooftop")
    path = tmp_path / "checkpoint.npz"
    _write_campaign_checkpoint(path, checkpoint, "identity", reference, "tissue")
    loaded = _load_campaign_checkpoint(path, "identity", reference, config, "tissue")
    assert loaded is not None
    np.testing.assert_array_equal(loaded.base_seeds, [7])
    np.testing.assert_array_equal(loaded.rho_sum, checkpoint.rho_sum)


def test_legacy_checkpoint_migrates_plain_mean_for_unequal_surface_areas(tmp_path) -> None:
    checkpoint = CampaignCheckpoint(
        base_seeds=np.asarray([7], dtype=np.int64),
        chi=np.ones((1, 2, 3), dtype=np.float64),
        chi_direct=np.full((1, 2, 3), 0.5, dtype=np.float64),
        body_peak_rooftop=np.full((1, 2), 2.0, dtype=np.float64),
        body_mean_rooftop=np.ones((1, 2), dtype=np.float64),
        body_sab_rooftop=np.asarray([[[2.0, 1.0, 0.0], [2.0, 1.0, 0.0]]], dtype=np.float64),
        trace_seconds=np.full((1, 2), 0.2, dtype=np.float64),
        rho_sum=np.ones((2, 3, 3), dtype=np.float64),
        local_grid=fibonacci_sphere(3),
        solid_angle=4.0 * np.pi / 3.0,
        body_surface_areas=np.asarray([1.0, 2.0, 3.0], dtype=np.float64),
    )
    reference = _reference()
    config = SimpleNamespace(base_seeds=(7, 8), looks=(3,), body_model="rooftop")
    path = tmp_path / "checkpoint.npz"
    _write_campaign_checkpoint(path, checkpoint, "identity", reference, "tissue")
    with np.load(path, allow_pickle=False) as artifact:
        legacy = {name: np.asarray(artifact[name]) for name in artifact.files if not name.startswith("body_surface")}
    np.savez_compressed(path, **legacy)
    loaded = _load_campaign_checkpoint(
        path,
        "identity",
        reference,
        config,
        "tissue",
        body_surface_areas=np.asarray([1.0, 2.0, 3.0], dtype=np.float64),
    )
    assert loaded is not None
    np.testing.assert_array_equal(loaded.body_mean_rooftop, np.full((1, 2), 4.0 / 6.0))


@pytest.mark.parametrize("missing", ["body_surface_areas", "body_surface_areas_sha256"])
def test_legacy_checkpoint_rejects_incomplete_area_metadata(tmp_path, missing: str) -> None:
    checkpoint = CampaignCheckpoint(
        base_seeds=np.asarray([7], dtype=np.int64),
        chi=np.ones((1, 2, 3), dtype=np.float64),
        chi_direct=np.full((1, 2, 3), 0.5, dtype=np.float64),
        body_peak_rooftop=np.full((1, 2), 2.0, dtype=np.float64),
        body_mean_rooftop=np.full((1, 2), 4.0 / 6.0, dtype=np.float64),
        body_sab_rooftop=np.asarray([[[2.0, 1.0, 0.0], [2.0, 1.0, 0.0]]], dtype=np.float64),
        trace_seconds=np.full((1, 2), 0.2, dtype=np.float64),
        rho_sum=np.ones((2, 3, 3), dtype=np.float64),
        local_grid=fibonacci_sphere(3),
        solid_angle=4.0 * np.pi / 3.0,
        body_surface_areas=np.asarray([1.0, 2.0, 3.0], dtype=np.float64),
    )
    reference = _reference()
    config = SimpleNamespace(base_seeds=(7, 8), looks=(3,), body_model="rooftop")
    path = tmp_path / "checkpoint.npz"
    _write_campaign_checkpoint(path, checkpoint, "identity", reference, "tissue")
    with np.load(path, allow_pickle=False) as artifact:
        incomplete = {name: np.asarray(artifact[name]) for name in artifact.files if name != missing}
    np.savez_compressed(path, **incomplete)
    assert _load_campaign_checkpoint(path, "identity", reference, config, "tissue") is None


def test_legacy_checkpoint_rejects_non_float64_area_metadata(tmp_path) -> None:
    checkpoint = CampaignCheckpoint(
        base_seeds=np.asarray([7], dtype=np.int64),
        chi=np.ones((1, 2, 3), dtype=np.float64),
        chi_direct=np.full((1, 2, 3), 0.5, dtype=np.float64),
        body_peak_rooftop=np.full((1, 2), 2.0, dtype=np.float64),
        body_mean_rooftop=np.full((1, 2), 4.0 / 6.0, dtype=np.float64),
        body_sab_rooftop=np.asarray([[[2.0, 1.0, 0.0], [2.0, 1.0, 0.0]]], dtype=np.float64),
        trace_seconds=np.full((1, 2), 0.2, dtype=np.float64),
        rho_sum=np.ones((2, 3, 3), dtype=np.float64),
        local_grid=fibonacci_sphere(3),
        solid_angle=4.0 * np.pi / 3.0,
        body_surface_areas=np.asarray([1.0, 2.0, 3.0], dtype=np.float64),
    )
    reference = _reference()
    config = SimpleNamespace(base_seeds=(7, 8), looks=(3,), body_model="rooftop")
    path = tmp_path / "checkpoint.npz"
    _write_campaign_checkpoint(path, checkpoint, "identity", reference, "tissue")
    with np.load(path, allow_pickle=False) as artifact:
        altered = {name: np.asarray(artifact[name]) for name in artifact.files}
    altered["body_surface_areas"] = altered["body_surface_areas"].astype(np.float32)
    altered["body_surface_areas_sha256"] = np.asarray(cdf_convergence._array_sha256(altered["body_surface_areas"]))
    np.savez_compressed(path, **altered)
    assert _load_campaign_checkpoint(path, "identity", reference, config, "tissue") is None


def test_legacy_checkpoint_rejects_area_array_different_from_runtime(tmp_path) -> None:
    checkpoint = CampaignCheckpoint(
        base_seeds=np.asarray([7], dtype=np.int64),
        chi=np.ones((1, 2, 3), dtype=np.float64),
        chi_direct=np.full((1, 2, 3), 0.5, dtype=np.float64),
        body_peak_rooftop=np.full((1, 2), 2.0, dtype=np.float64),
        body_mean_rooftop=np.full((1, 2), 4.0 / 6.0, dtype=np.float64),
        body_sab_rooftop=np.asarray([[[2.0, 1.0, 0.0], [2.0, 1.0, 0.0]]], dtype=np.float64),
        trace_seconds=np.full((1, 2), 0.2, dtype=np.float64),
        rho_sum=np.ones((2, 3, 3), dtype=np.float64),
        local_grid=fibonacci_sphere(3),
        solid_angle=4.0 * np.pi / 3.0,
        body_surface_areas=np.asarray([1.0, 2.0, 3.0], dtype=np.float64),
    )
    reference = _reference()
    config = SimpleNamespace(base_seeds=(7, 8), looks=(3,), body_model="rooftop")
    path = tmp_path / "checkpoint.npz"
    _write_campaign_checkpoint(path, checkpoint, "identity", reference, "tissue")
    assert (
        _load_campaign_checkpoint(
            path,
            "identity",
            reference,
            config,
            "tissue",
            body_surface_areas=np.asarray([1.0, 4.0, 3.0], dtype=np.float64),
        )
        is None
    )
