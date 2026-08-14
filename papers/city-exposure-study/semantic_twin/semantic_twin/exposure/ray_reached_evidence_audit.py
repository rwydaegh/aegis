"""Authenticated audit replay for ray-reached panorama evidence coverage.

The replay is deliberately separate from the production campaign checkpoint.
It authenticates a completed campaign, rebuilds its original configuration,
then records only category reductions needed by the coverage reporter.  It
never writes per-ray records or mutates the authenticated source campaign.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Mapping

import numpy as np

from ..transport.directional import DirectionalMeasure
from ..report.roofline_campaign_comparison import _Campaign, _load_campaign
from .roofline_campaign import (
    BODY_METRICS,
    FIRST_MATERIAL_INTERACTION_COMPONENTS,
    PreparedRooflineCampaign,
    _InvariantBodyCache,
    _run_replica,
    campaign_identity,
)
from .roofline_setup import RooflineSetupConfig, load_roofline_setup, prepare_roofline_campaign

SCHEMA = "aegis.ray-reached-evidence-audit-replay"
VERSION = 1
CATEGORY_NAMES = (
    "atlas_interface",
    "nonblocking_woody_atlas",
    "geometric_no_panorama_evidence",
    "geometric_evidence_refused_host_compatibility",
    "geometric_evidence_refused_atlas_state",
    "geometric_evidence_refused_insufficient_structural_mass",
    "geometric_fallback_other",
)
ADDITIVE_BODY_METRIC_INDICES = (0, 3, 4, 5)


class RayReachedEvidenceAuditError(ValueError):
    """Raised when authentication, replay parity, or category closure fails."""


@dataclass(frozen=True)
class AuditReplaySource:
    """One original run configuration paired with its sealed campaign."""

    config_path: Path
    campaign_dir: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "config_path", Path(self.config_path).resolve())
        object.__setattr__(self, "campaign_dir", Path(self.campaign_dir).resolve())


@dataclass(frozen=True)
class AuditReplayPlan:
    """Five-site replay plan and isolated output directory."""

    sources: tuple[AuditReplaySource, ...]
    output_dir: Path

    def __post_init__(self) -> None:
        if not self.sources:
            raise RayReachedEvidenceAuditError("audit replay requires at least one source campaign")
        object.__setattr__(self, "sources", tuple(self.sources))
        object.__setattr__(self, "output_dir", Path(self.output_dir).resolve())
        source_roots = {source.campaign_dir for source in self.sources}
        if len(source_roots) != len(self.sources):
            raise RayReachedEvidenceAuditError("source campaign directories must be unique")
        for source in self.sources:
            if self.output_dir == source.campaign_dir or self.output_dir.is_relative_to(source.campaign_dir):
                raise RayReachedEvidenceAuditError("audit output must not be inside a sealed source campaign")


@dataclass(frozen=True)
class _CategoryAudit:
    event_count: np.ndarray
    transfer: np.ndarray
    local_cell_mass: np.ndarray | None = None
    atom_category: np.ndarray | None = None


@dataclass
class _SeedCapture:
    points: int
    cells: int
    categories: int
    diffuse_event_count: np.ndarray
    diffuse_transfer: np.ndarray
    diffuse_local_cell_mass: np.ndarray
    specular_event_count: np.ndarray
    specular_transfer: np.ndarray
    specular_body_metrics: np.ndarray
    first_diffuse_body_metrics: np.ndarray
    body_coupling_seconds: np.ndarray
    total_sab_sum: np.ndarray

    @classmethod
    def empty(cls, points: int, cells: int, categories: int, surfaces: int) -> _SeedCapture:
        return cls(
            points=points,
            cells=cells,
            categories=categories,
            diffuse_event_count=np.zeros((points, categories), dtype=np.int64),
            diffuse_transfer=np.zeros((points, categories), dtype=np.float64),
            diffuse_local_cell_mass=np.zeros((points, categories, cells), dtype=np.float64),
            specular_event_count=np.zeros((points, categories), dtype=np.int64),
            specular_transfer=np.zeros((points, categories), dtype=np.float64),
            specular_body_metrics=np.zeros((points, categories, len(BODY_METRICS)), dtype=np.float64),
            first_diffuse_body_metrics=np.zeros((points, categories, len(BODY_METRICS)), dtype=np.float64),
            body_coupling_seconds=np.zeros(points, dtype=np.float64),
            total_sab_sum=np.zeros((points, surfaces), dtype=np.float64),
        )


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _array_digest(value: Any) -> str:
    array = np.ascontiguousarray(value)
    digest = hashlib.sha256()
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(str(array.shape).encode("ascii"))
    digest.update(array.tobytes())
    return digest.hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    payload = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _atomic_npz(path: Path, arrays: Mapping[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with temporary.open("wb") as handle:
        np.savez_compressed(handle, **arrays)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _as_mapping(value: Any, *, name: str) -> Mapping[str, Any]:
    if hasattr(value, "as_dict"):
        value = value.as_dict()
    if not isinstance(value, Mapping):
        raise RayReachedEvidenceAuditError(f"{name} must be a mapping or expose as_dict()")
    return value


def _category_names(value: Mapping[str, Any], *, name: str) -> tuple[str, ...]:
    names = tuple(str(item) for item in value.get("category_names", ()))
    if names != CATEGORY_NAMES:
        raise RayReachedEvidenceAuditError(f"{name} category vocabulary/order differs from the audit contract")
    return names


def _nonnegative_array(value: Any, shape: tuple[int, ...], *, name: str, integer: bool = False) -> np.ndarray:
    array = np.asarray(value)
    if array.shape != shape:
        raise RayReachedEvidenceAuditError(f"{name} has shape {array.shape}, expected {shape}")
    if integer:
        if array.size and not np.issubdtype(array.dtype, np.integer):
            raise RayReachedEvidenceAuditError(f"{name} must contain integer counts")
        result = np.asarray(array, dtype=np.int64)
    else:
        result = np.asarray(array, dtype=np.float64)
        if np.any(~np.isfinite(result)):
            raise RayReachedEvidenceAuditError(f"{name} contains non-finite values")
    if np.any(result < 0):
        raise RayReachedEvidenceAuditError(f"{name} contains negative values")
    return result


def _parse_diffuse_audit(detail: Mapping[str, Any], cells: int) -> _CategoryAudit:
    value = _as_mapping(detail.get("first_diffuse_audit"), name="first_diffuse_audit")
    _category_names(value, name="first_diffuse_audit")
    event_count = _nonnegative_array(
        value.get("accepted_event_count"),
        (len(CATEGORY_NAMES),),
        name="first_diffuse_audit.accepted_event_count",
        integer=True,
    )
    transfer = _nonnegative_array(
        value.get("contribution_transfer"), (len(CATEGORY_NAMES),), name="first_diffuse_audit.contribution_transfer"
    )
    field = _nonnegative_array(
        value.get("local_cell_mass"),
        (len(CATEGORY_NAMES), cells),
        name="first_diffuse_audit.local_cell_mass",
    )
    return _CategoryAudit(event_count, transfer, local_cell_mass=field)


def _parse_specular_audit(detail: Mapping[str, Any], atoms: int) -> _CategoryAudit:
    value = _as_mapping(detail.get("order_one_specular_audit"), name="order_one_specular_audit")
    _category_names(value, name="order_one_specular_audit")
    event_count = _nonnegative_array(
        value.get("accepted_event_count"),
        (len(CATEGORY_NAMES),),
        name="order_one_specular_audit.accepted_event_count",
        integer=True,
    )
    transfer = _nonnegative_array(
        value.get("contribution_transfer"),
        (len(CATEGORY_NAMES),),
        name="order_one_specular_audit.contribution_transfer",
    )
    atom_category = _nonnegative_array(
        value.get("atom_category"), (atoms,), name="order_one_specular_audit.atom_category", integer=True
    )
    if np.any(atom_category >= len(CATEGORY_NAMES)):
        raise RayReachedEvidenceAuditError("order_one_specular_audit.atom_category leaves the category vocabulary")
    return _CategoryAudit(event_count, transfer, atom_category=atom_category)


def _validate_category_closure(diffuse: _CategoryAudit, specular: _CategoryAudit, field: Any) -> None:
    diffuse_field = np.asarray(diffuse.local_cell_mass, dtype=np.float64)
    if not np.allclose(diffuse_field.sum(axis=0), field.bounced_mass, rtol=2.0e-12, atol=1.0e-15):
        raise RayReachedEvidenceAuditError("first-diffuse category fields do not close to the production field")
    bounced = float(np.sum(field.bounced_mass, dtype=np.float64))
    if not np.isclose(diffuse.transfer.sum(dtype=np.float64), bounced, rtol=2.0e-12, atol=1.0e-15):
        raise RayReachedEvidenceAuditError("first-diffuse category contributions do not close")
    if not np.isclose(specular.transfer.sum(dtype=np.float64), field.all_specular_mass, rtol=2.0e-12, atol=1.0e-15):
        raise RayReachedEvidenceAuditError("order-one specular category contributions do not close")
    atom_category = np.asarray(specular.atom_category, dtype=np.int64)
    expected_count = np.bincount(atom_category, minlength=len(CATEGORY_NAMES))
    expected_transfer = np.bincount(
        atom_category,
        weights=np.asarray(field.all_specular_atom_mass, dtype=np.float64),
        minlength=len(CATEGORY_NAMES),
    )
    if not np.array_equal(specular.event_count, expected_count):
        raise RayReachedEvidenceAuditError("order-one specular category counts do not reconcile with atoms")
    if not np.allclose(specular.transfer, expected_transfer, rtol=2.0e-12, atol=1.0e-15):
        raise RayReachedEvidenceAuditError("order-one specular category transfer does not reconcile with atoms")


def _category_measure(
    field: Any,
    scale: Any,
    category: int,
    diffuse: _CategoryAudit,
    specular: _CategoryAudit,
    *,
    family: str,
) -> DirectionalMeasure:
    atom_category = np.asarray(specular.atom_category, dtype=np.int64)
    selected = atom_category == category
    if family == "specular":
        atom_k_hat = np.asarray(field.all_specular_k_hat[selected], dtype=np.float64)
        atom_mass = np.asarray(field.all_specular_atom_mass[selected], dtype=np.float64) / scale.transfer_m_inv2
        diffuse_k_hat = np.empty((0, 3), dtype=np.float64)
        diffuse_mass = np.empty(0, dtype=np.float64)
    elif family == "first_diffuse":
        atom_k_hat = np.empty((0, 3), dtype=np.float64)
        atom_mass = np.empty(0, dtype=np.float64)
        diffuse_k_hat = -np.asarray(field.local_grid, dtype=np.float64)
        diffuse_mass = np.asarray(diffuse.local_cell_mass[category], dtype=np.float64) / scale.transfer_m_inv2
    else:
        raise ValueError(f"unknown non-direct audit family {family!r}")
    return DirectionalMeasure(
        atom_k_hat=atom_k_hat,
        atom_mass=atom_mass,
        diffuse_k_hat=diffuse_k_hat,
        diffuse_mass=diffuse_mass,
        reference_id=f"ray-reached-evidence:{family}:{category}",
    )


def _metric_array(exposure: Any) -> np.ndarray:
    return np.asarray([getattr(exposure, name) for name in BODY_METRICS], dtype=np.float64)


def _couple_category_measures(
    prepared: PreparedRooflineCampaign,
    field: Any,
    scale: Any,
    yaw: float,
    diffuse: _CategoryAudit,
    specular: _CategoryAudit,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    family_metrics = np.zeros((2, len(CATEGORY_NAMES), len(BODY_METRICS)), dtype=np.float64)
    family_sab = np.zeros((2, np.asarray(prepared.coupler.body.areas).size), dtype=np.float64)
    for family_index, family in enumerate(("specular", "first_diffuse")):
        for category in range(len(CATEGORY_NAMES)):
            measure = _category_measure(field, scale, category, diffuse, specular, family=family)
            if measure.total == 0.0:
                continue
            exposure, sab = prepared.coupler.couple_measure_with_sab(
                measure,
                scale.reference_s0_w_m2,
                chunk_cells=prepared.config.body_chunk_cells,
                body_yaw_deg=float(yaw),
            )
            family_metrics[family_index, category] = _metric_array(exposure)
            family_sab[family_index] += np.asarray(sab, dtype=np.float64)
    return family_metrics[0], family_metrics[1], family_sab[0], family_sab[1]


def _validate_split_body_closure(
    specular_metrics: np.ndarray,
    first_diffuse_metrics: np.ndarray,
    expected_component_metrics: np.ndarray,
) -> None:
    for family, observed, component_index in (
        ("specular", specular_metrics, 1),
        ("first-diffuse", first_diffuse_metrics, 2),
    ):
        expected = expected_component_metrics[component_index, list(ADDITIVE_BODY_METRIC_INDICES)]
        actual = observed[:, ADDITIVE_BODY_METRIC_INDICES].sum(axis=0)
        if not np.allclose(actual, expected, rtol=2.0e-12, atol=1.0e-15):
            raise RayReachedEvidenceAuditError(f"{family} category body metrics do not close")


def _assert_replay_point_parity(
    replay_raw: np.ndarray,
    replay_body: np.ndarray,
    source: _Campaign,
    seed_index: int,
    point_index: int,
) -> None:
    expected_raw = source.raw_transfer[seed_index, point_index]
    expected_body = source.body_metrics[seed_index, point_index]
    if not np.allclose(replay_raw, expected_raw, rtol=2.0e-10, atol=1.0e-14):
        raise RayReachedEvidenceAuditError(
            f"raw replay parity failed at seed {source.seeds[seed_index]}, standpoint {point_index}"
        )
    if not np.allclose(replay_body, expected_body, rtol=2.0e-12, atol=1.0e-15):
        raise RayReachedEvidenceAuditError(
            f"body replay parity failed at seed {source.seeds[seed_index]}, standpoint {point_index}"
        )


def _source_cumulative_sab(source: _Campaign) -> np.ndarray:
    checkpoint_path = source.root / "checkpoint" / "index.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    entry = checkpoint.get("cumulative_sab")
    if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
        raise RayReachedEvidenceAuditError(f"source campaign has no cumulative body field: {source.root}")
    path = source.root / "checkpoint" / entry["path"]
    if not path.is_file() or _file_sha256(path) != entry.get("sha256"):
        raise RayReachedEvidenceAuditError(f"source cumulative body field failed authentication: {path}")
    with np.load(path, allow_pickle=False) as payload:
        return np.asarray(payload["sab_sum"], dtype=np.float64)


def _validate_source_contract(
    source: _Campaign, setup: RooflineSetupConfig, prepared: PreparedRooflineCampaign
) -> None:
    if source.components != FIRST_MATERIAL_INTERACTION_COMPONENTS:
        raise RayReachedEvidenceAuditError("audit source is not a first-material-interaction campaign")
    if source.seeds != tuple(range(7, 23)):
        raise RayReachedEvidenceAuditError("audit source must contain the complete seeds 7 through 22")
    tracer = prepared.estimator.tracer
    if int(tracer.config.rays) != 200_000 or int(tracer.local_grid.shape[0]) != 4_096:
        raise RayReachedEvidenceAuditError("audit source must use 200,000 rays and 4,096 output cells")
    if setup.campaign.output_dir.resolve() != source.root:
        raise RayReachedEvidenceAuditError("original configuration output does not name the sealed source campaign")
    replay_identity = campaign_identity(prepared)
    if replay_identity != {"sha256": source.identity["sha256"], "data": source.identity_data}:
        raise RayReachedEvidenceAuditError("prepared replay identity differs from the authenticated source identity")


def _default_audit_configurer(
    prepared: PreparedRooflineCampaign, setup: RooflineSetupConfig
) -> PreparedRooflineCampaign:
    """Enable the opt-in classifier/tallies without changing sealed provenance."""
    try:
        from ..materials.evidence_audit import RayReachedEvidenceClassifier
        from ..transport.device_next_event import DeviceFirstDiffuseAuditCategories
    except ImportError as exc:
        raise RayReachedEvidenceAuditError("ray-reached classifier/device audit support is unavailable") from exc

    atlas_npz = setup.run.atlas_npz
    if atlas_npz is None:
        raise RayReachedEvidenceAuditError("ray-reached evidence audit requires an explicit source atlas")
    classifier = RayReachedEvidenceClassifier.from_files(
        Path(atlas_npz),
        prepared.estimator.tracer.atlas_material,
        geometric_class=np.asarray(prepared.estimator.tracer.face_class),
    )
    categories = DeviceFirstDiffuseAuditCategories(
        face_to_category_row=classifier.face_to_category_row,
        category_by_texel=classifier.category_by_texel,
        fallback_category_by_face=classifier.fallback_category_by_face,
    )
    estimator = replace(
        prepared.estimator,
        first_diffuse_audit=categories,
        ray_reached_evidence_classifier=classifier,
    )
    object.__setattr__(prepared, "estimator", estimator)
    return prepared


def _record_arrays(capture: _SeedCapture) -> dict[str, np.ndarray]:
    return {
        "diffuse_event_count": capture.diffuse_event_count,
        "diffuse_transfer": capture.diffuse_transfer,
        "diffuse_local_cell_mass": capture.diffuse_local_cell_mass,
        "specular_event_count": capture.specular_event_count,
        "specular_transfer": capture.specular_transfer,
        "specular_body_metrics": capture.specular_body_metrics,
        "first_diffuse_body_metrics": capture.first_diffuse_body_metrics,
        "body_coupling_seconds": capture.body_coupling_seconds,
    }


def _run_site_replay(
    source_spec: AuditReplaySource,
    output_dir: Path,
    environment: Any,
    *,
    persistent_cache_dir: Path | None,
    audit_configurer: Callable[[PreparedRooflineCampaign, RooflineSetupConfig], PreparedRooflineCampaign],
    dry_run: bool,
) -> dict[str, Any]:
    source = _load_campaign(source_spec.campaign_dir)
    setup = load_roofline_setup(source_spec.config_path)
    prepared = prepare_roofline_campaign(setup, environment, persistent_cache_dir=persistent_cache_dir)
    _validate_source_contract(source, setup, prepared)
    site = prepared.config.site
    site_dir = output_dir / site
    source_info = {
        "site": site,
        "source_campaign": str(source.root),
        "source_config": str(source_spec.config_path),
        "source_identity_sha256": source.identity["sha256"],
        "source_manifest_sha256": _file_sha256(source.root / "manifest.json"),
        "source_config_sha256": _file_sha256(source_spec.config_path),
        "seeds": list(source.seeds),
        "standpoints": source.points,
    }
    if dry_run:
        return {**source_info, "ready_to_replay": True, "files": {}}

    prepared = audit_configurer(prepared, setup)
    invariant_cache = _InvariantBodyCache.for_walk(source.points)
    surfaces = int(np.asarray(prepared.coupler.body.areas).size)
    cells = int(prepared.estimator.tracer.local_grid.shape[0])
    cumulative_sab = np.zeros((source.points, surfaces), dtype=np.float64)
    record_files: dict[str, str] = {}
    audit_categories = prepared.estimator.first_diffuse_audit
    audit_configuration = {
        "category_names": list(CATEGORY_NAMES),
        "face_to_category_row_sha256": _array_digest(audit_categories.face_to_category_row),
        "category_by_texel_sha256": _array_digest(audit_categories.category_by_texel),
        "fallback_category_by_face_sha256": _array_digest(audit_categories.fallback_category_by_face),
        "category_by_texel_shape": list(audit_categories.category_by_texel.shape),
        "collection": [
            "accepted_event_count",
            "contribution_transfer",
            "category_resolved_local_cell_mass",
            "category_resolved_specular_body_metrics",
            "category_resolved_first_diffuse_body_metrics",
        ],
        "raw_per_ray_records": False,
    }
    identity_data = {
        "schema": SCHEMA,
        "version": VERSION,
        "category_names": list(CATEGORY_NAMES),
        "source": source_info,
        "audit_configuration": audit_configuration,
        "output_contract": "compact_category_reductions_no_per_ray_records",
        "direct_category": "not_applicable_no_material_interaction",
        "body_metrics": list(BODY_METRICS),
        "additive_body_metrics": [BODY_METRICS[index] for index in ADDITIVE_BODY_METRIC_INDICES],
    }
    identity = {"sha256": _sha256_bytes(_canonical_bytes(identity_data)), "data": identity_data}
    identity_path = site_dir / "audit_identity.json"
    if identity_path.exists():
        existing_identity = json.loads(identity_path.read_text(encoding="utf-8"))
        if existing_identity != identity:
            raise RayReachedEvidenceAuditError(f"audit output belongs to a different replay: {site_dir}")
    else:
        _atomic_json(identity_path, identity)
    site_started = time.perf_counter()

    for seed_index, seed in enumerate(source.seeds):
        capture = _SeedCapture.empty(source.points, cells, len(CATEGORY_NAMES), surfaces)

        def point_capture(**point: Any) -> None:
            point_index = int(point["point_index"])
            field = point["field"]
            detail = point["detail"]
            diffuse = _parse_diffuse_audit(detail, cells)
            specular = _parse_specular_audit(detail, int(field.all_specular_atom_mass.size))
            _validate_category_closure(diffuse, specular, field)
            started = time.perf_counter()
            specular_metrics, first_diffuse_metrics, specular_sab, first_diffuse_sab = _couple_category_measures(
                prepared,
                field,
                point["scale"],
                float(prepared.walk.body_yaw_deg[point_index]),
                diffuse,
                specular,
            )
            direct_measure = point["measures"]["direct"]
            direct_exposure, direct_sab = prepared.coupler.couple_measure_with_sab(
                direct_measure,
                point["scale"].reference_s0_w_m2,
                chunk_cells=prepared.config.body_chunk_cells,
                body_yaw_deg=float(prepared.walk.body_yaw_deg[point_index]),
            )
            del direct_exposure
            non_direct_sab = specular_sab + first_diffuse_sab
            expected_non_direct = np.asarray(point["total_sab"], dtype=np.float64) - np.asarray(
                direct_sab, dtype=np.float64
            )
            if not np.allclose(non_direct_sab, expected_non_direct, rtol=2.0e-12, atol=1.0e-15):
                raise RayReachedEvidenceAuditError(
                    f"body-coupled category fields do not close at seed {seed}, standpoint {point_index}"
                )
            _validate_split_body_closure(
                specular_metrics,
                first_diffuse_metrics,
                source.body_metrics[seed_index, point_index],
            )
            capture.diffuse_event_count[point_index] = diffuse.event_count
            capture.diffuse_transfer[point_index] = diffuse.transfer
            capture.diffuse_local_cell_mass[point_index] = diffuse.local_cell_mass
            capture.specular_event_count[point_index] = specular.event_count
            capture.specular_transfer[point_index] = specular.transfer
            capture.specular_body_metrics[point_index] = specular_metrics
            capture.first_diffuse_body_metrics[point_index] = first_diffuse_metrics
            capture.body_coupling_seconds[point_index] = time.perf_counter() - started
            capture.total_sab_sum[point_index] = point["total_sab"]

        replica = _run_replica(prepared, seed, invariant_cache, point_capture=point_capture)
        for point_index in range(source.points):
            _assert_replay_point_parity(
                replica.raw_transfer[point_index],
                replica.body_metrics[point_index],
                source,
                seed_index,
                point_index,
            )
        cumulative_sab += capture.total_sab_sum
        record_path = site_dir / "records" / f"seed_{seed:010d}.npz"
        _atomic_npz(record_path, _record_arrays(capture))
        record_files[str(record_path.relative_to(site_dir))] = _file_sha256(record_path)

    expected_sab = _source_cumulative_sab(source)
    if not np.allclose(cumulative_sab, expected_sab, rtol=2.0e-12, atol=1.0e-15):
        raise RayReachedEvidenceAuditError(f"cumulative body-field replay parity failed for {site}")
    elapsed = time.perf_counter() - site_started
    record_files[str(identity_path.relative_to(site_dir))] = _file_sha256(identity_path)
    manifest = {
        "schema": SCHEMA,
        "version": VERSION,
        "identity_sha256": identity["sha256"],
        "elapsed_seconds": elapsed,
        "files": dict(sorted(record_files.items())),
    }
    manifest_path = site_dir / "manifest.json"
    _atomic_json(manifest_path, manifest)
    return {**source_info, "ready_to_replay": True, "elapsed_seconds": elapsed, "files": manifest["files"]}


def run_ray_reached_evidence_audit(
    plan: AuditReplayPlan,
    environment: Any,
    *,
    persistent_cache_root: Path | None = None,
    audit_configurer: Callable[
        [PreparedRooflineCampaign, RooflineSetupConfig], PreparedRooflineCampaign
    ] = _default_audit_configurer,
    dry_run: bool = False,
) -> Path | dict[str, Any]:
    """Authenticate and replay every source campaign in the plan."""
    root = plan.output_dir
    sites: list[dict[str, Any]] = []
    for source in plan.sources:
        cache = None
        if persistent_cache_root is not None:
            cache = Path(persistent_cache_root).resolve() / source.campaign_dir.name
        sites.append(
            _run_site_replay(
                source,
                root,
                environment,
                persistent_cache_dir=cache,
                audit_configurer=audit_configurer,
                dry_run=dry_run,
            )
        )
    if dry_run:
        return {"schema": SCHEMA, "version": VERSION, "ready_to_replay": True, "sites": sites}
    manifest_files = {
        f"{site['site']}/manifest.json": _file_sha256(root / site["site"] / "manifest.json") for site in sites
    }
    manifest = {
        "schema": SCHEMA,
        "version": VERSION,
        "category_names": list(CATEGORY_NAMES),
        "sites": sites,
        "files": manifest_files,
    }
    path = root / "manifest.json"
    _atomic_json(path, manifest)
    return path
