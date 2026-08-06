"""Focused integrity and restart tests for the append-only CDF store."""

from __future__ import annotations

import json
import pathlib
from dataclasses import replace

import numpy as np
import pytest

import semantic_twin.exposure.checkpoint_store as store_module
from semantic_twin.exposure.checkpoint_store import (
    CheckpointCorruptionError,
    CheckpointIdentityError,
    CheckpointOrderError,
    CheckpointSpec,
    CheckpointStoreError,
    CheckpointStore,
    ReplicaPayload,
    benchmark_write_amplification,
)


MODEL_NAMES = ("isotropic", "rooftop", "street_small_cell")
BODY_AREAS = np.asarray([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)


def _spec() -> CheckpointSpec:
    return CheckpointSpec(
        identity_sha256="campaign-identity",
        standpoint_array_sha256="standpoints",
        tissue_database_sha256="tissue",
        model_names=MODEL_NAMES,
        planned_seeds=(7, 8, 9),
        surface_elements=5,
        body_surface_areas=BODY_AREAS,
        local_grid=np.arange(12, dtype=np.float64).reshape(4, 3),
        solid_angle=0.25,
    )


def _payload(seed: int, offset: float = 0.0) -> ReplicaPayload:
    sab = np.arange(15, dtype=np.float64).reshape(3, 5) + 1.0 + offset
    return ReplicaPayload(
        base_seed=seed,
        chi=np.full((3, 3), 2.0 + offset, dtype=np.float64),
        chi_direct=np.full((3, 3), 1.0 + offset, dtype=np.float64),
        body_peak_rooftop=np.max(sab, axis=1),
        body_mean_rooftop=np.sum(sab * BODY_AREAS[None, :], axis=1) / np.sum(BODY_AREAS),
        body_sab_rooftop=sab,
        trace_seconds=np.full(3, 0.5 + offset, dtype=np.float64),
        rho=np.full((3, 3, 4), 0.25 + offset, dtype=np.float64),
    )


def test_append_restart_and_exact_prefix(tmp_path: pathlib.Path) -> None:
    root = tmp_path / "campaign"
    first = CheckpointStore(root, _spec())
    first.append(0, _payload(7))
    first.append(1, _payload(8, 1.0))
    index = json.loads((root / "index.json").read_text())
    assert "body_surface_areas" not in index
    assert index["body_surface_areas_count"] == BODY_AREAS.size
    assert index["body_surface_areas_sha256"] == _spec().body_surface_areas_sha256

    restarted = CheckpointStore(root, _spec())
    prefix = restarted.load_prefix(1)
    assert restarted.replicas == 2
    assert prefix.base_seeds.tolist() == [7]
    np.testing.assert_array_equal(prefix.chi[0], _payload(7).chi)
    np.testing.assert_array_equal(prefix.rho_sum, _payload(7).rho)

    full = restarted.load_prefix()
    np.testing.assert_array_equal(full.base_seeds, np.array([7, 8], dtype=np.int64))
    np.testing.assert_array_equal(full.rho_sum, _payload(7).rho + _payload(8, 1.0).rho)


def test_unequal_surface_areas_reject_a_plain_triangle_mean(tmp_path: pathlib.Path) -> None:
    checkpoint = CheckpointStore(tmp_path / "campaign", _spec())
    bad = _payload(7)
    bad = ReplicaPayload(
        base_seed=bad.base_seed,
        chi=bad.chi,
        chi_direct=bad.chi_direct,
        body_peak_rooftop=bad.body_peak_rooftop,
        body_mean_rooftop=np.mean(bad.body_sab_rooftop, axis=1),
        body_sab_rooftop=bad.body_sab_rooftop,
        trace_seconds=bad.trace_seconds,
        rho=bad.rho,
    )
    with pytest.raises(CheckpointStoreError, match="area-weighted"):
        checkpoint.append(0, bad)


def test_uniform_legacy_index_remains_recoverable(tmp_path: pathlib.Path) -> None:
    spec = replace(_spec(), body_surface_areas=np.ones(5, dtype=np.float64))
    payload = _payload(7)
    payload = ReplicaPayload(
        base_seed=payload.base_seed,
        chi=payload.chi,
        chi_direct=payload.chi_direct,
        body_peak_rooftop=payload.body_peak_rooftop,
        body_mean_rooftop=np.mean(payload.body_sab_rooftop, axis=1),
        body_sab_rooftop=payload.body_sab_rooftop,
        trace_seconds=payload.trace_seconds,
        rho=payload.rho,
    )
    root = tmp_path / "campaign"
    checkpoint = CheckpointStore(root, spec)
    checkpoint.append(0, payload)
    index_path = root / "index.json"
    index = json.loads(index_path.read_text())
    for key in (
        "body_surface_areas",
        "body_surface_areas_count",
        "body_surface_areas_dtype",
        "body_surface_areas_sha256",
    ):
        index.pop(key, None)
    index_path.write_text(json.dumps(index))
    recovered = CheckpointStore(root, spec)
    assert recovered.replicas == 1


def test_stray_surface_area_array_is_not_a_valid_index_identity(tmp_path: pathlib.Path) -> None:
    root = tmp_path / "campaign"
    checkpoint = CheckpointStore(root, _spec())
    checkpoint.append(0, _payload(7))
    index_path = root / "index.json"
    index = json.loads(index_path.read_text())
    index["body_surface_areas"] = BODY_AREAS.tolist()
    for key in ("body_surface_areas_count", "body_surface_areas_dtype", "body_surface_areas_sha256"):
        index.pop(key, None)
    index_path.write_text(json.dumps(index))
    with pytest.raises(CheckpointCorruptionError, match="surface area identity"):
        CheckpointStore(root, _spec())


def test_seed_order_and_identity_are_closed(tmp_path: pathlib.Path) -> None:
    root = tmp_path / "campaign"
    checkpoint = CheckpointStore(root, _spec())
    with pytest.raises(CheckpointOrderError):
        checkpoint.append(1, _payload(8))
    with pytest.raises(CheckpointOrderError):
        checkpoint.append(0, _payload(8))

    other = _spec()
    object.__setattr__(other, "identity_sha256", "another-campaign")
    with pytest.raises(CheckpointIdentityError):
        CheckpointStore(root, other)


def test_uncommitted_partial_shard_is_replaced_on_restart(tmp_path: pathlib.Path, monkeypatch) -> None:
    root = tmp_path / "campaign"
    checkpoint = CheckpointStore(root, _spec())

    original_atomic = store_module._atomic_json

    def fail_commit(path: pathlib.Path, document: dict) -> None:
        if path.name == "index.json" and document["entries"]:
            raise OSError("simulated interruption before index commit")
        original_atomic(path, document)

    monkeypatch.setattr(store_module, "_atomic_json", fail_commit)
    with pytest.raises(OSError, match="simulated interruption"):
        checkpoint.append(0, _payload(7))
    assert (root / "replica-000000.npz").is_file()
    assert json.loads((root / "index.json").read_text())["entries"] == []

    monkeypatch.setattr(store_module, "_atomic_json", original_atomic)
    restarted = CheckpointStore(root, _spec())
    restarted.append(0, _payload(7))
    assert restarted.replicas == 1
    np.testing.assert_array_equal(restarted.load_prefix().body_sab_rooftop[0], _payload(7).body_sab_rooftop)


@pytest.mark.parametrize("mode", ["truncate", "delete"])
def test_committed_corruption_is_rejected(tmp_path: pathlib.Path, mode: str) -> None:
    root = tmp_path / "campaign"
    checkpoint = CheckpointStore(root, _spec())
    checkpoint.append(0, _payload(7))
    shard = root / "replica-000000.npz"
    if mode == "truncate":
        shard.write_bytes(shard.read_bytes()[:-7])
    else:
        shard.unlink()
    with pytest.raises(CheckpointCorruptionError):
        CheckpointStore(root, _spec())


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("local_grid", [["not", "numeric"]]),
        ("solid_angle", []),
        ("model_names", "rooftop"),
        ("surface_elements", 5.0),
    ),
)
def test_malformed_index_values_raise_store_corruption(tmp_path: pathlib.Path, field: str, value) -> None:
    root = tmp_path / "campaign"
    checkpoint = CheckpointStore(root, _spec())
    checkpoint.append(0, _payload(7))
    index_path = root / "index.json"
    document = json.loads(index_path.read_text())
    document[field] = value
    index_path.write_text(json.dumps(document))
    with pytest.raises(CheckpointCorruptionError):
        CheckpointStore(root, _spec())


def test_consolidated_export_keeps_legacy_names_and_float64(tmp_path: pathlib.Path) -> None:
    root = tmp_path / "campaign"
    checkpoint = CheckpointStore(root, _spec())
    checkpoint.append(0, _payload(7))
    checkpoint.append(1, _payload(8, 1.0))
    output = checkpoint.consolidate(tmp_path / "checkpoint.npz")
    assert not root.exists()
    with np.load(output, allow_pickle=False) as artifact:
        assert {
            "schema",
            "identity_sha256",
            "standpoint_array_sha256",
            "tissue_database_sha256",
            "base_seeds",
            "chi",
            "chi_direct",
            "body_peak_rooftop",
            "body_mean_rooftop",
            "body_sab_rooftop",
            "body_sab_sha256",
            "trace_seconds",
            "rho_sum",
            "local_grid",
            "local_grid_sha256",
            "solid_angle",
            "model_names",
        } <= set(artifact.files)
        assert artifact["chi"].dtype == np.float64
        assert artifact["rho_sum"].dtype == np.float64
        np.testing.assert_array_equal(artifact["base_seeds"], [7, 8])


def test_failed_consolidated_validation_retains_shards(tmp_path: pathlib.Path, monkeypatch) -> None:
    root = tmp_path / "campaign"
    checkpoint = CheckpointStore(root, _spec())
    checkpoint.append(0, _payload(7))

    def fail_validation(*args, **kwargs):
        raise CheckpointCorruptionError("forced validation failure")

    monkeypatch.setattr(checkpoint, "_validate_consolidated", fail_validation)
    with pytest.raises(CheckpointCorruptionError, match="forced validation"):
        checkpoint.consolidate(tmp_path / "checkpoint.npz")
    assert root.is_dir()
    assert (root / "replica-000000.npz").is_file()


def test_small_write_benchmark_favors_shards(tmp_path: pathlib.Path) -> None:
    metrics = benchmark_write_amplification(tmp_path, _spec(), [_payload(7), _payload(8, 1.0), _payload(9, 2.0)])
    assert metrics["replicas"] == 3
    assert metrics["shard_data_bytes"] > 0
    assert metrics["full_cumulative_bytes"] > metrics["shard_data_bytes"]
    assert metrics["write_reduction"] == pytest.approx(
        1.0 - metrics["store_cumulative_bytes"] / metrics["full_cumulative_bytes"]
    )
