"""Persistent exact-direct and all-specular cache contracts."""

from __future__ import annotations

import hashlib
import io
import json
import threading
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pytest

from semantic_twin import paths
from semantic_twin.cli import roofline_campaign as roofline_command
from semantic_twin.exposure.roofline_campaign import seal_transport_provenance
from semantic_twin.illumination.curve import FacadeTipCurve
from semantic_twin.illumination.sources import SourceSet
from semantic_twin.propagation.closed_form import PEC_PERMITTIVITY
from semantic_twin.transport.next_event import NextEventEstimator
from semantic_twin.transport.persistent_cache import (
    CACHE_SCHEMA,
    DirectCacheValue,
    PersistentTransportCache,
    SpecularCacheValue,
    cache_key,
)
from semantic_twin.transport.specular import (
    OneBounceSpecularTransport,
    ReceiverVisibleFaceCandidates,
    StratifiedSourceQuadrature,
)
from semantic_twin.transport.tracer import SbrTracer, TraceConfig


class TriangleGeometry:
    """Small indexed triangle intersector with content-addressable geometry."""

    def __init__(self, vertices: np.ndarray | None = None) -> None:
        self.vertices = np.asarray(
            vertices if vertices is not None else [[-20.0, -20.0, 0.0], [20.0, -20.0, 0.0], [0.0, 20.0, 0.0]],
            dtype=np.float64,
        )
        self.faces = np.array([[0, 1, 2]], dtype=np.int64)

    @property
    def face_count(self) -> int:
        return 1

    def intersect(self, origins: np.ndarray, directions: np.ndarray):
        triangle = self.vertices[self.faces]
        edge1 = triangle[:, 1] - triangle[:, 0]
        edge2 = triangle[:, 2] - triangle[:, 0]
        pvec = np.cross(directions[:, None, :], edge2[None, :, :])
        determinant = np.einsum("fj,rfj->rf", edge1, pvec)
        inverse = np.divide(
            1.0,
            determinant,
            out=np.zeros_like(determinant),
            where=np.abs(determinant) > 1.0e-12,
        )
        offset = origins[:, None, :] - triangle[None, :, 0]
        u = np.einsum("rfj,rfj->rf", offset, pvec) * inverse
        qvec = np.cross(offset, edge1[None, :, :])
        v = np.einsum("rj,rfj->rf", directions, qvec) * inverse
        distance = np.einsum("fj,rfj->rf", edge2, qvec) * inverse
        valid = (
            (np.abs(determinant) > 1.0e-12)
            & (u >= -1.0e-9)
            & (v >= -1.0e-9)
            & (u + v <= 1.0 + 1.0e-9)
            & (distance > 1.0e-10)
        )
        distance = np.where(valid, distance, np.inf)
        face = np.argmin(distance, axis=1)
        travel = distance[np.arange(origins.shape[0]), face]
        hit = np.isfinite(travel)
        cross = np.cross(edge1, edge2)
        face_normal = cross / np.linalg.norm(cross, axis=1)[:, None]
        normal = np.where(hit[:, None], face_normal[face], 0.0)
        return hit, np.where(hit, travel, 1.0e30), normal, np.where(hit, face, 0)


def estimator(
    cache_dir,
    *,
    seed: int = 4,
    launch_sampling: str = "iid",
    source_weights: np.ndarray | None = None,
    geometry: TriangleGeometry | None = None,
    permittivity: complex = PEC_PERMITTIVITY,
    epsilon_m: float = 1.0e-3,
    tolerance: float = 0.02,
) -> NextEventEstimator:
    geometry = TriangleGeometry() if geometry is None else geometry
    config = TraceConfig(
        rays=16,
        batch=16,
        local_cells=32,
        max_bounces=1,
        seed=seed,
        launch_sampling=launch_sampling,
    )
    tracer = SbrTracer(
        geometry,
        np.zeros(geometry.face_count, dtype=np.int64),
        np.array([permittivity]),
        np.zeros(1),
        config,
    )
    sources = SourceSet(
        positions=np.array([[-3.0, 0.0, 5.0], [5.0, 1.0, 4.0]]),
        cell_m=1.0,
        dims=3,
        azimuths=0,
        builders=0,
        source_weights=source_weights,
    )
    transport = OneBounceSpecularTransport(tracer, epsilon_m=epsilon_m)
    return NextEventEstimator(
        tracer,
        geometry,
        sources,
        specular_transport=transport,
        specular_refinement_relative_tolerance=tolerance,
        persistent_cache_dir=cache_dir,
    )


def test_new_estimator_roundtrips_direct_atoms_and_final_specular_paths(tmp_path) -> None:
    origin = np.array([2.0, 0.0, 2.0])
    first_result, first_field = estimator(tmp_path / "cache", seed=4).estimate_field(origin, seed=4)
    second_result, second_field = estimator(
        tmp_path / "cache",
        seed=99,
        launch_sampling="rotated_fibonacci",
    ).estimate_field(origin, seed=99)

    assert first_result.detail["deterministic_specular_persistent_cache_hit"] is False
    assert first_result.detail["direct_persistent_cache_hit"] is False
    assert second_result.detail["deterministic_specular_persistent_cache_hit"] is True
    assert second_result.detail["direct_persistent_cache_hit"] is True
    assert second_result.detail["deterministic_specular_seconds"] == 0.0
    assert second_result.detail["direct_seconds"] == 0.0
    assert second_result.detail["all_specular_diagnostics"]["seconds"] == 0.0
    assert second_result.detail["persistent_transport_cache"]["schema"] == CACHE_SCHEMA
    assert len(second_result.detail["persistent_transport_cache"]["direct_key_sha256"]) == 64
    np.testing.assert_array_equal(second_field.direct_k_hat, first_field.direct_k_hat)
    np.testing.assert_array_equal(second_field.direct_atom_mass, first_field.direct_atom_mass)
    np.testing.assert_array_equal(second_field.all_specular_k_hat, first_field.all_specular_k_hat)
    np.testing.assert_array_equal(second_field.all_specular_atom_mass, first_field.all_specular_atom_mass)
    assert second_field.all_specular_diagnostics["seconds"] == 0.0


def test_persistent_hit_zeros_historical_refinement_timings_but_keeps_counts(tmp_path) -> None:
    current = estimator(tmp_path / "unused")
    transport = current.specular_transport
    assert transport is not None
    paths = transport.solve_all_sources(
        current.sources.sites(),
        np.array([2.0, 0.0, 2.0]),
        current.sources.normalized_source_weights(),
    )
    work = transport.work_estimate(sources=2, rays=16, samples=1, max_bounces=1)
    refinement = [
        {
            "step": 0,
            "axis_refined": "initial",
            "face_level": 0,
            "source_level": 0,
            "angular_samples": 16,
            "cumulative_visibility_rays": 16,
            "candidates": 2,
            "cumulative_candidates": 2,
            "executed_candidates": 2,
            "avoided_candidates": 0,
            "cumulative_executed_candidates": 2,
            "cumulative_avoided_candidates": 0,
            "accepted": paths.diagnostics.accepted,
            "selected_faces": 1,
            "requested_strata": 2,
            "selected_sources": 2,
            "candidate_support_complete": False,
            "source_support_complete": True,
            "finite_resolution_support_incomplete": True,
            "transfer": paths.total,
            "seconds": 3.0,
            "executed_seconds": 2.0,
            "cumulative_executed_seconds": 2.0,
            "logical_solution_seconds": 3.0,
            "reused_block_seconds": 1.0,
            "absolute_change_from_previous_face_level": None,
            "relative_change_from_previous_face_level": None,
            "absolute_change_from_previous_source_level": None,
            "relative_change_from_previous_source_level": None,
            "face_axis_converged": False,
            "source_axis_converged": True,
            "numerically_converged": False,
            "relative_tolerance": 0.02,
        }
    ]
    finite_work = {
        "method": "adaptive_receiver_faces_and_probability_strata",
        "candidate_budget": 100,
        "relative_tolerance": 0.02,
        "numerically_converged": True,
        "support_complete": False,
        "stop_reason": "relative_tolerance_reached",
        "enabled": True,
        "executed_candidate_seconds": 4.0,
    }
    value = SpecularCacheValue(work, paths, refinement, finite_work, False)
    identity = {"schema": CACHE_SCHEMA, "case": "timing-normalization"}
    cache = PersistentTransportCache(tmp_path / "cache")
    _, first_hit = cache.specular(identity, lambda: value)
    loaded, second_hit = cache.specular(identity, lambda: (_ for _ in ()).throw(AssertionError("recomputed")))

    assert first_hit is False and second_hit is True
    assert loaded.paths is not None
    assert loaded.paths.diagnostics.seconds == 0.0
    assert loaded.refinement[0]["candidates"] == 2
    for name in (
        "seconds",
        "executed_seconds",
        "cumulative_executed_seconds",
        "logical_solution_seconds",
        "reused_block_seconds",
    ):
        assert loaded.refinement[0][name] == 0.0
    assert loaded.finite_work is not None
    assert loaded.finite_work["executed_candidate_seconds"] == 0.0


def test_adaptive_final_paths_and_full_refinement_evidence_roundtrip(tmp_path) -> None:
    points = np.column_stack((np.linspace(-3.5, 3.5, 32), np.zeros(32), np.full(32, 5.0)))
    curve = FacadeTipCurve(points, np.ones(32), {"fixture": True})

    def adaptive(cache_dir, seed: int) -> NextEventEstimator:
        geometry = TriangleGeometry()
        tracer = SbrTracer(
            geometry,
            np.zeros(1, dtype=np.int64),
            np.array([PEC_PERMITTIVITY]),
            np.zeros(1),
            TraceConfig(rays=16, batch=16, local_cells=32, max_bounces=1, seed=seed),
        )
        return NextEventEstimator(
            tracer,
            geometry,
            SourceSet.from_curve(curve),
            max_order=1,
            specular_candidate_budget=21,
            specular_transport=OneBounceSpecularTransport(tracer, candidate_budget=21),
            visible_face_candidates=ReceiverVisibleFaceCandidates((3,)),
            source_quadrature=StratifiedSourceQuadrature((1,)),
            persistent_cache_dir=cache_dir,
        )

    origin = np.array([0.0, 0.0, 2.0])
    first, first_field = adaptive(tmp_path / "cache", 1).estimate_field(origin, seed=1)
    second, second_field = adaptive(tmp_path / "cache", 9).estimate_field(origin, seed=9)
    first_rows = first.detail["specular_source_refinement"]
    second_rows = second.detail["specular_source_refinement"]

    assert first_rows
    assert second.detail["deterministic_specular_persistent_cache_hit"] is True
    assert [row["candidates"] for row in second_rows] == [row["candidates"] for row in first_rows]
    assert [row["transfer"] for row in second_rows] == [row["transfer"] for row in first_rows]
    assert all(row["seconds"] == 0.0 and row["executed_seconds"] == 0.0 for row in second_rows)
    assert second.detail["finite_resolution_specular_work"]["executed_candidate_seconds"] == 0.0
    np.testing.assert_array_equal(second_field.all_specular_k_hat, first_field.all_specular_k_hat)
    np.testing.assert_array_equal(second_field.all_specular_atom_mass, first_field.all_specular_atom_mass)


def test_content_identity_excludes_seed_launch_and_cache_location_but_invalidates_inputs(tmp_path) -> None:
    origin = np.array([2.0, 0.0, 2.0])

    def identity(value: NextEventEstimator, point: np.ndarray = origin) -> dict:
        cache = value._persistent_cache
        assert cache is not None
        document = cache.identity(
            value,
            kind="deterministic_one_reflection",
            origin=point,
            maximum_order=1,
            transport=value.specular_transport,
        )
        assert document is not None
        return document

    baseline = estimator(tmp_path / "one", seed=1)
    same_science_other_cache = estimator(tmp_path / "two", seed=1)
    stochastic_variant = estimator(tmp_path / "three", seed=999, launch_sampling="rotated_fibonacci")
    assert cache_key(identity(baseline)) == cache_key(identity(stochastic_variant))
    assert seal_transport_provenance(baseline) == seal_transport_provenance(same_science_other_cache)

    variants = (
        (estimator(tmp_path / "v1", source_weights=np.array([1.0, 3.0])), origin),
        (estimator(tmp_path / "v2", permittivity=4.0 - 0.2j), origin),
        (estimator(tmp_path / "v3", epsilon_m=2.0e-3), origin),
        (estimator(tmp_path / "v4", tolerance=0.03), origin),
        (estimator(tmp_path / "v5", geometry=TriangleGeometry(TriangleGeometry().vertices + [1.0, 0.0, 0.0])), origin),
        (estimator(tmp_path / "v6"), origin + [0.1, 0.0, 0.0]),
    )
    baseline_key = cache_key(identity(baseline))
    assert all(cache_key(identity(value, point)) != baseline_key for value, point in variants)


def test_corrupt_entry_is_a_miss_and_is_atomically_replaced(tmp_path) -> None:
    origin = np.array([2.0, 0.0, 2.0])
    first, _field = estimator(tmp_path / "cache").estimate_field(origin)
    key = first.detail["persistent_transport_cache"]["deterministic_specular_key_sha256"]
    entry = tmp_path / "cache" / CACHE_SCHEMA / key[:2] / f"{key}.stcache"
    entry.write_bytes(b"corrupt")

    repaired, _field = estimator(tmp_path / "cache", seed=5).estimate_field(origin, seed=5)
    reused, _field = estimator(tmp_path / "cache", seed=6).estimate_field(origin, seed=6)
    assert repaired.detail["deterministic_specular_persistent_cache_hit"] is False
    assert reused.detail["deterministic_specular_persistent_cache_hit"] is True
    assert entry.read_bytes()[:2] == b"PK"


@pytest.mark.parametrize(
    "replacement",
    (np.array([0.25], dtype=np.float32), np.array([0.25, 0.5]), np.array([-0.25])),
    ids=("dtype", "shape", "invariant"),
)
def test_forged_array_dtype_shape_or_invariant_is_a_miss(tmp_path, replacement) -> None:
    identity = {"schema": CACHE_SCHEMA, "case": "strict-array-validation"}
    cache = PersistentTransportCache(tmp_path / "cache")
    original = DirectCacheValue(np.array([0.25]), np.array([0.5]), None)
    cache.direct(identity, lambda: original, field_cells=None)
    entry = cache._entry_path(cache_key(identity))
    with zipfile.ZipFile(entry, "r") as archive:
        members = {name: archive.read(name) for name in archive.namelist()}

    stream = io.BytesIO()
    np.save(stream, replacement, allow_pickle=False)
    members["direct.npy"] = stream.getvalue()
    manifest = json.loads(members["manifest.json"])
    description = manifest["arrays"]["direct.npy"]
    description.update(
        {
            "dtype": replacement.dtype.str,
            "shape": list(replacement.shape),
            "sha256": hashlib.sha256(members["direct.npy"]).hexdigest(),
            "bytes": len(members["direct.npy"]),
        }
    )
    manifest.pop("record_sha256")
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    manifest["record_sha256"] = hashlib.sha256(canonical).hexdigest()
    members["manifest.json"] = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    with zipfile.ZipFile(entry, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, content in members.items():
            archive.writestr(name, content)

    repaired, hit = cache.direct(identity, lambda: original, field_cells=None)
    assert hit is False
    np.testing.assert_array_equal(repaired.direct, original.direct)


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("candidate_budget", True),
        ("candidate_work_used", False),
        ("executed_candidate_seconds", -0.1),
        ("face_level_counts", [1, True]),
        (
            "blocked_next_cycle",
            {"angular_samples": 8, "projected_refinement_work": -1},
        ),
    ),
    ids=("boolean-budget", "boolean-work", "negative-seconds", "boolean-level", "negative-projection"),
)
def test_forged_finite_work_metadata_is_a_miss(tmp_path, field, replacement) -> None:
    identity = {"schema": CACHE_SCHEMA, "case": f"strict-finite-work-{field}"}
    cache = PersistentTransportCache(tmp_path / "cache")
    finite_work = {
        "method": "adaptive_receiver_faces_and_probability_strata",
        "candidate_budget": 100,
        "candidate_work_used": 4,
        "executed_candidate_work_used": 3,
        "avoided_candidate_work": 1,
        "executed_candidate_seconds": 0.25,
        "total_candidates_upper_bound": 4,
        "visibility_rays_used": 2,
        "refinement_work_used": 6,
        "relative_tolerance": 0.02,
        "numerically_converged": False,
        "support_complete": False,
        "mixed_specular_suffix_enabled": False,
        "stop_reason": "candidate_budget_exhausted",
        "enabled": True,
        "estimate_count": 1,
        "budget_remaining": 94,
        "blocked_next_cycle": {"angular_samples": 8, "projected_refinement_work": 20},
        "face_level_counts": [1, 3],
        "source_strata_levels": [2, 4],
    }
    original = SpecularCacheValue(None, None, [], finite_work, False)
    cache.specular(identity, lambda: original)
    entry = cache._entry_path(cache_key(identity))
    with zipfile.ZipFile(entry, "r") as archive:
        members = {name: archive.read(name) for name in archive.namelist()}

    manifest = json.loads(members["manifest.json"])
    manifest["metadata"]["finite_work"][field] = replacement
    manifest.pop("record_sha256")
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    manifest["record_sha256"] = hashlib.sha256(canonical).hexdigest()
    members["manifest.json"] = json.dumps(
        manifest,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode()
    with zipfile.ZipFile(entry, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, content in members.items():
            archive.writestr(name, content)

    repaired, hit = cache.specular(identity, lambda: original)
    assert hit is False
    assert repaired.finite_work == finite_work


def test_atomic_directory_lock_allows_one_concurrent_writer(tmp_path) -> None:
    calls = 0
    guard = threading.Lock()
    identity = {"schema": CACHE_SCHEMA, "case": "concurrent-direct"}

    def compute() -> DirectCacheValue:
        nonlocal calls
        with guard:
            calls += 1
        time.sleep(0.05)
        return DirectCacheValue(np.array([0.25]), np.array([0.5]), None)

    def one_call(_index: int) -> bool:
        cache = PersistentTransportCache(tmp_path / "cache")
        _value, hit = cache.direct(identity, compute, field_cells=None)
        return hit

    with ThreadPoolExecutor(max_workers=8) as pool:
        hits = list(pool.map(one_call, range(8)))
    assert calls == 1
    assert hits.count(False) == 1
    assert hits.count(True) == 7
    assert not list((tmp_path / "cache" / CACHE_SCHEMA).rglob("*.tmp-*"))


def test_roofline_cli_passes_runtime_cache_without_putting_it_in_campaign_identity(monkeypatch, tmp_path) -> None:
    first = roofline_command.arguments(
        ["--config", str(tmp_path / "campaign.json"), "--persistent-transport-cache", str(tmp_path / "cache-a")]
    )
    second = roofline_command.arguments(
        ["--config", str(tmp_path / "campaign.json"), "--persistent-transport-cache", str(tmp_path / "cache-b")]
    )
    default = roofline_command.arguments(["--config", str(tmp_path / "campaign.json")])
    assert first.persistent_transport_cache == tmp_path / "cache-a"
    assert second.persistent_transport_cache == tmp_path / "cache-b"
    assert default.persistent_transport_cache is None

    setup = type("Setup", (), {})()
    setup.study_root = paths.root().resolve()
    setup.campaign = type("Campaign", (), {"output_dir": tmp_path / "output"})()
    prepared = object()
    seen: list[object] = []
    report = {
        "ready_to_trace": True,
        "campaign_identity": "unchanged-scientific-identity",
        "staged_inputs": {"files": []},
    }
    monkeypatch.setattr(roofline_command, "load_roofline_setup", lambda *_args, **_kwargs: setup)

    def prepare(_setup, _environment, *, persistent_cache_dir=None):
        seen.append(persistent_cache_dir)
        return prepared

    monkeypatch.setattr(roofline_command, "prepare_roofline_campaign", prepare)
    monkeypatch.setattr(roofline_command, "preflight_report", lambda _prepared: report)
    for index, arguments in enumerate((first, second)):
        arguments.dry_run = True
        arguments.preflight_output = tmp_path / f"preflight-{index}.json"
        arguments.staging_manifest = tmp_path / f"staging-{index}.json"
        assert roofline_command.run(arguments, environment=object()) == 0
    assert seen == [tmp_path / "cache-a", tmp_path / "cache-b"]
    assert {
        json.loads((tmp_path / f"preflight-{index}.json").read_text())["campaign_identity"] for index in range(2)
    } == {"unchanged-scientific-identity"}
