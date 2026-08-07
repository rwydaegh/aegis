"""Resumable full-walk exposure campaigns for explicit roofline sources.

This module is the production join between the explicit-source next-event
estimator and AEGIS body dosimetry.  It deliberately accepts already prepared
transport objects.  Scene acquisition, semantic material binding, and roofline
construction remain separate, inspectable stages and cannot silently fall back
inside a long campaign.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol

import numpy as np

from ..illumination.sources import normalized_source_weights
from ..transport.directional import DirectionalMeasure
from ..transport.next_event import NextEventField
from ..transport.specular_sampling import SampledOneBounceSpecularEstimator
from ..walk.model import PANORAMA_LINKS, STREET_ROUTE, Walk
from .coupler import BodyExposure

COMPONENTS = ("direct", "specular", "diffuse", "total")
BODY_METRICS = (
    "arriving_power_density_w_m2",
    "susceptibility",
    "peak_sab_w_m2",
    "mean_sab_w_m2",
    "absorbed_power_w",
    "sar_wb_w_kg",
)
FIELD_META = (
    "includes_specular",
    "missing_specular",
    "maximum_completed_all_specular_order",
    "maximum_completed_specular_suffix_order",
    "direct_atom_count",
    "specular_atom_count",
    "nonzero_diffuse_cell_count",
)
REFERENCE_FIELDS = ("d_ref_m_inv2", "reference_s0_w_m2")
TIMING_FIELDS = (
    "estimator_wall_seconds",
    "direct_shadow_seconds",
    "stochastic_trace_seconds",
    "specular_seconds",
    "body_coupling_seconds",
)
SCHEMA_VERSION = "roofline_body_campaign_v1"
POINT_SEED_ALGORITHM = "blake2b_64_person_AEGIS_NEE_v1(seed_u64,standpoint_u64)"
TEMPORARY_GLOB = ".*.tmp-*"
IDENTITY_FILENAME = "campaign_identity.json"
LOCATIONS_FILENAME = "locations.jsonl"
SUMMARY_FILENAME = "summary.json"
MANIFEST_FILENAME = "manifest.json"


class FieldEstimator(Protocol):
    """Narrow transport interface consumed by the campaign."""

    sources: Any

    def estimate_field(
        self,
        origin: np.ndarray,
        *,
        ground_z_m: float = 0.0,
        seed: int | None = None,
    ) -> tuple[Any, NextEventField]: ...


class SurfaceBodyCoupler(Protocol):
    """Narrow body interface consumed by the campaign."""

    body: Any

    def couple_measure_with_sab(
        self,
        measure: DirectionalMeasure,
        reference_s0_w_m2: float,
        *,
        chunk_cells: int = 512,
        body_yaw_deg: float | None = None,
    ) -> tuple[BodyExposure, np.ndarray]: ...


def _validate_campaign_names(config: RooflineCampaignConfig) -> None:
    if config.cohort not in ("primary_semantic_route", "geometric_transfer_extension"):
        raise ValueError(f"unknown cohort {config.cohort!r}")
    if config.material_mode not in ("walk", "semantic", "atlas", "geometric"):
        raise ValueError(f"unknown material mode {config.material_mode!r}")
    if config.reference_mode not in ("per_density_eirp", "physical"):
        raise ValueError(f"unknown reference mode {config.reference_mode!r}")
    if not config.site:
        raise ValueError("site must be non-empty")


def _validate_campaign_seeds(config: RooflineCampaignConfig) -> None:
    if not config.planned_seeds:
        raise ValueError("planned_seeds must not be empty")
    if len(set(config.planned_seeds)) != len(config.planned_seeds):
        raise ValueError("planned_seeds must be unique")
    if any(not isinstance(seed, int) or isinstance(seed, bool) or seed < 0 for seed in config.planned_seeds):
        raise ValueError("planned_seeds must contain nonnegative integers")
    if (
        not isinstance(config.body_chunk_cells, int)
        or isinstance(config.body_chunk_cells, bool)
        or config.body_chunk_cells < 1
    ):
        raise ValueError("body_chunk_cells must be positive")
    if any(seed >= 2**64 for seed in config.planned_seeds):
        raise ValueError("planned seeds must fit in the device-safe 64-bit point-seed derivation")


def _validate_campaign_specular_policy(config: RooflineCampaignConfig) -> None:
    if not isinstance(config.minimum_completed_specular_order, int) or isinstance(
        config.minimum_completed_specular_order, bool
    ):
        raise ValueError("minimum_completed_specular_order must be integer zero or one")
    if config.minimum_completed_specular_order not in (0, 1):
        raise ValueError("minimum_completed_specular_order must be zero or one")
    if config.specular_acceptance not in (
        "exact_complete",
        "adaptive_converged",
        "adaptive_all_specular_sampled_mixed_order_1",
        "omitted_diagnostic",
    ):
        raise ValueError(f"unknown specular acceptance policy {config.specular_acceptance!r}")
    expected_order = 1 if config.specular_acceptance == "exact_complete" else 0
    if config.minimum_completed_specular_order != expected_order:
        raise ValueError(f"{config.specular_acceptance} requires minimum_completed_specular_order={expected_order}")


def _validate_campaign_looks_and_cohort(config: RooflineCampaignConfig) -> None:
    if any(look < 1 or look > len(config.planned_seeds) for look in config.convergence_looks):
        raise ValueError("convergence looks must lie within the planned seed count")
    if tuple(sorted(set(config.convergence_looks))) != config.convergence_looks:
        raise ValueError("convergence_looks must be sorted and unique")
    if config.cohort == "primary_semantic_route" and config.material_mode == "geometric":
        raise ValueError("the primary semantic-route cohort cannot use geometric materials")
    if config.cohort == "geometric_transfer_extension" and config.material_mode != "geometric":
        raise ValueError("the geometric transfer extension must be explicitly geometric")


@dataclass(frozen=True)
class RooflineCampaignConfig:
    """Decisions that define one resumable production campaign."""

    site: str
    cohort: Literal["primary_semantic_route", "geometric_transfer_extension"]
    material_mode: Literal["walk", "semantic", "atlas", "geometric"]
    output_dir: Path
    planned_seeds: tuple[int, ...]
    reference_mode: Literal["per_density_eirp", "physical"] = "per_density_eirp"
    sampling_claim: str = "full_declared_walk"
    body_chunk_cells: int = 512
    convergence_looks: tuple[int, ...] = ()
    minimum_completed_specular_order: int = 1
    specular_acceptance: Literal[
        "exact_complete",
        "adaptive_converged",
        "adaptive_all_specular_sampled_mixed_order_1",
        "omitted_diagnostic",
    ] = "exact_complete"

    def __post_init__(self) -> None:
        _validate_campaign_names(self)
        _validate_campaign_seeds(self)
        _validate_campaign_specular_policy(self)
        _validate_campaign_looks_and_cohort(self)
        object.__setattr__(self, "output_dir", Path(self.output_dir))

    def identity_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "site": self.site,
            "cohort": self.cohort,
            "material_mode": self.material_mode,
            "planned_seeds": list(self.planned_seeds),
            "reference_mode": self.reference_mode,
            "sampling_claim": self.sampling_claim,
            "point_seed_derivation": POINT_SEED_ALGORITHM,
            "body_chunk_cells": self.body_chunk_cells,
            "convergence_looks": list(self.convergence_looks),
            "minimum_completed_specular_order": self.minimum_completed_specular_order,
            "specular_acceptance": self.specular_acceptance,
        }


def _validate_walk_arrays(prepared: PreparedRooflineCampaign) -> np.ndarray:
    points = np.asarray(prepared.walk.points, dtype=np.float64)
    ground = np.asarray(prepared.walk.ground_z_m, dtype=np.float64)
    step = np.asarray(prepared.walk.step_m, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3 or points.shape[0] == 0:
        raise ValueError("walk points must have non-empty shape (P, 3)")
    if ground.shape != (points.shape[0],):
        raise ValueError("walk ground_z_m must align with points")
    if step.shape != (points.shape[0],):
        raise ValueError("walk step_m must align with points")
    if not np.all(np.isfinite(points)) or not np.all(np.isfinite(ground)) or not np.all(np.isfinite(step)):
        raise ValueError("walk coordinates must be finite")
    if np.any(step < 0.0) or np.count_nonzero(step[:1]):
        raise ValueError("walk step_m must be nonnegative and start at zero")
    return points


def _validate_prepared_contract(prepared: PreparedRooflineCampaign, points: int) -> None:
    point_kind = prepared.walk.provenance.get("point_kind")
    if not isinstance(point_kind, list) or len(point_kind) != points:
        raise ValueError("walk provenance point_kind must align with every standpoint")
    if prepared.walk.body_yaw_deg is None:
        raise ValueError("production roofline campaigns require one fixed route yaw per standpoint")
    body_mass = getattr(prepared.coupler, "body_mass_kg", None)
    if body_mass is None or not np.isfinite(body_mass) or body_mass <= 0.0:
        raise ValueError("production roofline campaigns require a positive body mass for wbSAR")
    if prepared.walk.site is not None and prepared.walk.site != prepared.config.site:
        raise ValueError(f"walk site {prepared.walk.site!r} does not match campaign site {prepared.config.site!r}")
    if prepared.config.sampling_claim != "full_declared_walk":
        raise ValueError("this runner only supports the full declared walk")


def _validate_prepared_provenance_shape(prepared: PreparedRooflineCampaign) -> None:
    for name, value in (
        ("source_provenance", prepared.source_provenance),
        ("material_provenance", prepared.material_provenance),
        ("input_provenance", prepared.input_provenance),
        ("transport_provenance", prepared.transport_provenance),
        ("coupler_provenance", prepared.coupler_provenance),
    ):
        if not value:
            raise ValueError(f"{name} must be explicit and non-empty")
    if not isinstance(prepared.transport_provenance.get("estimator"), dict):
        raise ValueError("transport_provenance must seal an estimator dictionary")
    if not isinstance(prepared.transport_provenance.get("tracer"), dict):
        raise ValueError("transport_provenance must seal a tracer dictionary")
    if not prepared.transport_provenance["estimator"].get("configuration"):
        raise ValueError("transport_provenance must seal estimator configuration")
    if not prepared.transport_provenance["tracer"].get("configuration"):
        raise ValueError("transport_provenance must seal tracer configuration")


def _validate_prepared_live_provenance(prepared: PreparedRooflineCampaign) -> None:
    if _canonical_bytes(prepared.transport_provenance) != _canonical_bytes(
        seal_transport_provenance(prepared.estimator)
    ):
        raise ValueError("transport_provenance does not match the prepared estimator and tracer")
    sources = prepared.estimator.sources
    if not hasattr(sources, "source_provenance"):
        raise ValueError("production sources must expose source_provenance()")
    if _canonical_bytes(prepared.source_provenance) != _canonical_bytes(sources.source_provenance()):
        raise ValueError("source_provenance does not match the prepared source population")
    if _canonical_bytes(prepared.coupler_provenance) != _canonical_bytes(seal_coupler_provenance(prepared.coupler)):
        raise ValueError("coupler_provenance does not match the prepared body coupler")


def _validate_prepared_seeds_and_cohort(prepared: PreparedRooflineCampaign) -> None:
    point_seeds = [
        derive_point_seed(seed, point_index)
        for seed in prepared.config.planned_seeds
        for point_index in range(len(prepared.walk))
    ]
    if len(point_seeds) != len(set(point_seeds)):
        raise ValueError("derived 64-bit point seeds collide within the planned campaign")
    if prepared.material_provenance.get("material_mode") != prepared.config.material_mode:
        raise ValueError("material provenance mode does not match campaign material_mode")
    if prepared.config.cohort == "primary_semantic_route":
        if prepared.walk.kind != PANORAMA_LINKS:
            raise ValueError("primary semantic cohort requires a panorama-link route")
    elif prepared.walk.kind != STREET_ROUTE:
        raise ValueError("geometric transfer extension requires a declared street route")


@dataclass(frozen=True)
class PreparedRooflineCampaign:
    """Fully bound transport and body objects plus their sealed provenance."""

    config: RooflineCampaignConfig
    walk: Walk
    estimator: FieldEstimator
    coupler: SurfaceBodyCoupler
    source_provenance: dict[str, Any]
    material_provenance: dict[str, Any]
    input_provenance: dict[str, Any]
    transport_provenance: dict[str, Any]
    coupler_provenance: dict[str, Any]

    def __post_init__(self) -> None:
        points = _validate_walk_arrays(self)
        _validate_prepared_contract(self, points.shape[0])
        _validate_prepared_provenance_shape(self)
        _validate_prepared_live_provenance(self)
        _validate_prepared_seeds_and_cohort(self)


@dataclass(frozen=True)
class ReferenceScale:
    """The two scales that normalize transport and restore physical units."""

    transfer_m_inv2: float
    reference_s0_w_m2: float
    mode: str


@dataclass(frozen=True)
class ReplicaData:
    """One complete seed shard before it is sealed on disk."""

    raw_transfer: np.ndarray
    body_metrics: np.ndarray
    total_sab: np.ndarray
    timings: np.ndarray
    field_meta: np.ndarray
    reference: np.ndarray
    diagnostics: tuple[dict[str, Any], ...]


@dataclass
class _InvariantBodyCache:
    """Bounded in-memory cache for replica-invariant body components."""

    capacity: int
    values: dict[tuple[int, str], tuple[np.ndarray, np.ndarray]]

    @classmethod
    def for_walk(cls, points: int) -> _InvariantBodyCache:
        return cls(capacity=max(1, 2 * points), values={})

    def get(self, key: tuple[int, str]) -> tuple[np.ndarray, np.ndarray] | None:
        return self.values.get(key)

    def put(self, key: tuple[int, str], metrics: np.ndarray, sab: np.ndarray) -> None:
        if key not in self.values and len(self.values) >= self.capacity:
            raise RuntimeError("replica-invariant body cache exceeded its sealed route bound")
        self.values[key] = (np.asarray(metrics, dtype=np.float64).copy(), np.asarray(sab, dtype=np.float64).copy())


def _json_value(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(_json_value(value), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def derive_point_seed(seed: int, point_index: int) -> int:
    """Mix a campaign seed and standpoint into a stable device-safe uint64."""
    if not isinstance(seed, int) or isinstance(seed, bool) or not 0 <= seed < 2**64:
        raise ValueError("seed must be an unsigned 64-bit integer")
    if not isinstance(point_index, int) or isinstance(point_index, bool) or not 0 <= point_index < 2**64:
        raise ValueError("point_index must be an unsigned 64-bit integer")
    payload = seed.to_bytes(8, "little") + point_index.to_bytes(8, "little")
    digest = hashlib.blake2b(payload, digest_size=8, person=b"AEGIS_NEE_v1").digest()
    return int.from_bytes(digest, "little")


def _array_digest(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(str(array.shape).encode("ascii"))
    digest.update(array.tobytes())
    return digest.hexdigest()


def _specular_transport_configuration(specular_transport: Any) -> dict[str, Any] | None:
    if specular_transport is None:
        return None
    surfaces = specular_transport.surfaces
    return {
        "candidate_chunk": int(specular_transport.candidate_chunk),
        "candidate_budget": int(specular_transport.candidate_budget),
        "epsilon_m": float(specular_transport.epsilon_m),
        "support_complete": bool(surfaces.support_complete),
        "scene_face_count": int(surfaces.scene_face_count),
        "construction": str(surfaces.construction),
        "triangles_sha256": _array_digest(np.asarray(surfaces.triangles, dtype=np.float64)),
        "normals_sha256": _array_digest(np.asarray(surfaces.normals, dtype=np.float64)),
        "face_index_sha256": _array_digest(np.asarray(surfaces.face_index, dtype=np.int64)),
        "material_class_sha256": _array_digest(np.asarray(surfaces.material_class, dtype=np.int64)),
    }


def _estimator_configuration(estimator: FieldEstimator) -> dict[str, Any]:
    configuration = {
        name: _json_value(getattr(estimator, name))
        for name in (
            "samples",
            "max_order",
            "connection_lift_m",
            "specular_order",
            "specular_candidate_budget",
            "specular_refinement_relative_tolerance",
            "gather_seed_offset",
            "deterministic_cache_size",
            "specular_suffix_mode",
            "sampled_specular_samples",
            "sampled_specular_seed_offset",
        )
        if hasattr(estimator, name)
    }
    if not configuration:
        raise ValueError("estimator exposes no sealed numerical configuration")
    visible_candidates = getattr(estimator, "visible_face_candidates", None)
    if visible_candidates is not None:
        configuration["visible_face_candidates"] = {
            name: _json_value(getattr(visible_candidates, name))
            for name in ("sample_levels", "growth_factor", "epsilon_m")
            if hasattr(visible_candidates, name)
        }
    source_quadrature = getattr(estimator, "source_quadrature", None)
    if source_quadrature is not None:
        configuration["source_quadrature"] = {
            name: _json_value(getattr(source_quadrature, name))
            for name in ("strata_levels", "growth_factor")
            if hasattr(source_quadrature, name)
        }
    diagnostic_models = getattr(estimator, "diagnostic_models", {})
    configuration["diagnostic_models"] = {
        str(name): _json_value(model.describe()) for name, model in sorted(diagnostic_models.items())
    }
    specular_transport = getattr(estimator, "specular_transport", None)
    configuration["specular_transport"] = _specular_transport_configuration(specular_transport)
    sampled = getattr(estimator, "specular_suffix_mode", "exact") == "sampled" and specular_transport is not None
    configuration["sampled_specular"] = (
        SampledOneBounceSpecularEstimator(specular_transport, estimator.sources).sampling_identity()
        if sampled
        else None
    )
    return configuration


def _geometry_provenance(geometry: Any) -> dict[str, Any]:
    provenance: dict[str, Any] = {
        "class": f"{type(geometry).__module__}.{type(geometry).__qualname__}",
        "face_count": None if getattr(geometry, "face_count", None) is None else int(geometry.face_count),
        "intersection_variant": getattr(geometry, "variant", None),
    }
    for name, dtype in (("vertices", np.float64), ("faces", np.int64)):
        value = getattr(geometry, name, None)
        provenance[f"{name}_sha256"] = None if value is None else _array_digest(np.asarray(value, dtype=dtype))
    return provenance


def _atlas_provenance(atlas: Any) -> dict[str, Any] | None:
    if atlas is None:
        return None
    return {
        "class": f"{type(atlas).__module__}.{type(atlas).__qualname__}",
        "face_count": int(atlas.face_count),
        "material_names": list(atlas.material_names),
        "provenance": _json_value(atlas.provenance),
        **{
            f"{name}_sha256": _array_digest(np.asarray(getattr(atlas, name)))
            for name in (
                "face_to_atlas_row",
                "material_probability",
                "supported",
                "valid_texels",
                "material_class",
                "nonblocking",
            )
        },
    }


def seal_transport_provenance(estimator: FieldEstimator) -> dict[str, Any]:
    """Read every numerical estimator and tracer control into a stable record."""
    tracer = getattr(estimator, "tracer", None)
    if tracer is None:
        raise ValueError("field estimator must expose its tracer for production identity")
    trace_config = getattr(tracer, "config", None)
    if trace_config is None or not hasattr(trace_config, "as_dict"):
        raise ValueError("tracer configuration must expose as_dict() for production identity")
    face_class = getattr(tracer, "face_class", None)
    atlas = getattr(tracer, "atlas_material", None)
    tracer_configuration = _json_value(trace_config.as_dict())
    return {
        "estimator": {
            "class": f"{type(estimator).__module__}.{type(estimator).__qualname__}",
            "configuration": _estimator_configuration(estimator),
        },
        "tracer": {
            "class": f"{type(tracer).__module__}.{type(tracer).__qualname__}",
            "configuration": tracer_configuration,
            "local_grid_sha256": _array_digest(np.asarray(tracer.local_grid, dtype=np.float64)),
            "face_class_sha256": None if face_class is None else _array_digest(np.asarray(face_class)),
            "permittivity_sha256": _array_digest(np.asarray(tracer.permittivity, dtype=np.complex128)),
            "rms_height_sha256": _array_digest(np.asarray(tracer.rms_height_m, dtype=np.float64)),
            "atlas_material": _atlas_provenance(atlas),
            "geometry": _geometry_provenance(tracer.geometry),
        },
    }


def seal_coupler_provenance(coupler: SurfaceBodyCoupler) -> dict[str, Any]:
    """Seal the body and level-2 transfer state used by a campaign."""
    anterior = np.asarray(getattr(coupler, "body_anterior_axis", None), dtype=np.float64)
    if anterior.shape != (3,) or not np.all(np.isfinite(anterior)):
        raise ValueError("body coupler must expose a finite body_anterior_axis")
    level = getattr(coupler, "level", None)
    if level != 2:
        raise ValueError("roofline surface-field campaigns require body coupling level 2")
    frequency = getattr(coupler, "frequency_hz", None)
    body_mass = getattr(coupler, "body_mass_kg", None)
    transmission = getattr(getattr(coupler, "engine", None), "T0", None)
    values = (frequency, body_mass, transmission)
    if any(value is None or not np.isfinite(value) or value <= 0.0 for value in values):
        raise ValueError("body coupler must expose positive frequency, mass, and transmission factor")
    body = coupler.body
    areas = np.asarray(body.areas, dtype=np.float64)
    normals = np.asarray(body.normals, dtype=np.float64)
    vertices = getattr(body, "vertices", None)
    if vertices is None:
        raise ValueError("body coupler must expose the exact triangle vertices used by AEGIS")
    vertices = np.asarray(vertices, dtype=np.float64)
    if vertices.shape != (areas.size, 3, 3) or np.any(~np.isfinite(vertices)):
        raise ValueError("body vertices must be finite triangle soup aligned with surface elements")
    return {
        "class": f"{type(coupler).__module__}.{type(coupler).__qualname__}",
        "phantom": getattr(body, "name", type(body).__name__),
        "level": 2,
        "frequency_hz": float(frequency),
        "body_mass_kg": float(body_mass),
        "T0": float(transmission),
        "body_anterior_axis": anterior.tolist(),
        "surface_elements": int(areas.size),
        "areas_sha256": _array_digest(areas),
        "normals_sha256": _array_digest(normals),
        "vertices_sha256": _array_digest(vertices),
    }


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    payload = json.dumps(_json_value(value), indent=2, sort_keys=True, allow_nan=False) + "\n"
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def campaign_identity(prepared: PreparedRooflineCampaign) -> dict[str, Any]:
    """Return stable identity data for strict checkpoint reuse."""
    walk = prepared.walk
    body = prepared.coupler.body
    body_areas = np.asarray(body.areas, dtype=np.float64)
    body_normals = np.asarray(body.normals, dtype=np.float64)
    live_transport = seal_transport_provenance(prepared.estimator)
    live_coupler = seal_coupler_provenance(prepared.coupler)
    live_sources = prepared.estimator.sources.source_provenance()
    if _canonical_bytes(live_transport) != _canonical_bytes(prepared.transport_provenance):
        raise ValueError("prepared estimator or tracer drifted after provenance was sealed")
    if _canonical_bytes(live_coupler) != _canonical_bytes(prepared.coupler_provenance):
        raise ValueError("prepared body coupler drifted after provenance was sealed")
    if _canonical_bytes(live_sources) != _canonical_bytes(prepared.source_provenance):
        raise ValueError("prepared source population drifted after provenance was sealed")
    identity = {
        "configuration": prepared.config.identity_dict(),
        "walk": {
            **walk.identity(),
            "points_sha256": _array_digest(np.asarray(walk.points, dtype=np.float64)),
            "ground_z_sha256": _array_digest(np.asarray(walk.ground_z_m, dtype=np.float64)),
            "step_m_sha256": _array_digest(np.asarray(walk.step_m, dtype=np.float64)),
            "body_yaw_sha256": _array_digest(np.asarray(walk.body_yaw_deg, dtype=np.float64)),
            "provenance": walk.provenance,
        },
        "body": {
            **live_coupler,
            "surface_elements": int(body_areas.size),
            "body_mass_kg": float(prepared.coupler.body_mass_kg),
            "surface_area_m2": float(np.sum(body_areas, dtype=np.float64)),
            "areas_sha256": _array_digest(body_areas),
            "normals_sha256": _array_digest(body_normals),
        },
        "sources": {
            "provenance": live_sources,
            "sites_sha256": _array_digest(np.asarray(prepared.estimator.sources.sites(), dtype=np.float64)),
            "normalized_weights_sha256": _array_digest(normalized_source_weights(prepared.estimator.sources)),
            "crop_area_m2": float(prepared.estimator.sources.crop_area_m2),
            "density_per_m2": (
                None
                if getattr(prepared.estimator.sources, "density_per_m2", None) is None
                else float(prepared.estimator.sources.density_per_m2)
            ),
            "eirp_w": (
                None
                if getattr(prepared.estimator.sources, "eirp_w", None) is None
                else float(prepared.estimator.sources.eirp_w)
            ),
            "physical_expected_count": (
                None
                if getattr(prepared.estimator.sources, "physical_expected_count", None) is None
                else float(prepared.estimator.sources.physical_expected_count)
            ),
        },
        "materials": prepared.material_provenance,
        "inputs": prepared.input_provenance,
        "transport": live_transport,
        "components": list(COMPONENTS),
        "body_metrics": list(BODY_METRICS),
        "reference_fields": list(REFERENCE_FIELDS),
        "timing_fields": list(TIMING_FIELDS),
    }
    return {"sha256": _sha256_bytes(_canonical_bytes(identity)), "data": identity}


def reference_scale(sources: Any, origin: np.ndarray, mode: str) -> ReferenceScale:
    """Compute the unobstructed reference transfer and paired density scale."""
    sites = np.asarray(sources.sites(), dtype=np.float64)
    if sites.ndim != 2 or sites.shape[1] != 3 or sites.shape[0] == 0:
        raise ValueError("the explicit source population must contain finite (N, 3) sites")
    if not np.all(np.isfinite(sites)):
        raise ValueError("source sites must be finite")
    delta = sites - np.asarray(origin, dtype=np.float64)[None, :]
    distance_squared = np.einsum("ij,ij->i", delta, delta)
    if np.any(distance_squared <= 0.0):
        raise ValueError("a source is co-located with a receiver, so the free-space reference is singular")
    weights = normalized_source_weights(sources)
    transfer = float(np.sum(weights / distance_squared, dtype=np.float64))
    if not np.isfinite(transfer) or transfer <= 0.0:
        raise ValueError("free-space reference transfer must be positive and finite")
    if getattr(sources, "curve", None) is None:
        raise ValueError("production scaling requires a declared facade-tip curve")
    crop_area = getattr(sources, "crop_area_m2", None)
    if crop_area is None or not np.isfinite(crop_area) or crop_area <= 0.0:
        raise ValueError("production scaling requires a positive crop_area_m2")
    if mode == "per_density_eirp":
        scale = float(crop_area) / (4.0 * np.pi)
    elif mode == "physical":
        count = getattr(sources, "physical_expected_count", None)
        eirp = getattr(sources, "eirp_w", None)
        if count is None or eirp is None or not np.isfinite(count) or not np.isfinite(eirp) or count <= 0 or eirp <= 0:
            raise ValueError("physical scaling requires positive expected source count and EIRP")
        scale = float(count) * float(eirp) / (4.0 * np.pi)
    else:
        raise ValueError(f"unknown reference mode {mode!r}")
    return ReferenceScale(transfer_m_inv2=transfer, reference_s0_w_m2=transfer * scale, mode=mode)


def component_measures(
    field: NextEventField, scale: ReferenceScale, reference_id: str
) -> dict[str, DirectionalMeasure]:
    """Split a next-event field into non-overlapping body arrival measures."""
    reference = scale.transfer_m_inv2
    empty_directions = np.empty((0, 3), dtype=np.float64)
    empty_mass = np.empty(0, dtype=np.float64)
    direct = DirectionalMeasure(
        field.direct_k_hat,
        field.direct_atom_mass / reference,
        empty_directions,
        empty_mass,
        reference_id=f"{reference_id}:direct",
    )
    specular = DirectionalMeasure(
        field.specular_k_hat,
        field.specular_atom_mass / reference,
        empty_directions,
        empty_mass,
        reference_id=f"{reference_id}:specular",
    )
    diffuse = DirectionalMeasure(
        empty_directions,
        empty_mass,
        -field.local_grid,
        field.bounced_mass / reference,
        reference_id=f"{reference_id}:diffuse",
    )
    total = field.directional_measure(reference, reference_id=f"{reference_id}:total")
    measures = {"direct": direct, "specular": specular, "diffuse": diffuse, "total": total}
    component_sum = direct.total + specular.total + diffuse.total
    if not np.isclose(total.total, component_sum, rtol=2.0e-12, atol=1.0e-15):
        raise RuntimeError("directional component split does not conserve transfer")
    return measures


def _body_metric_array(exposure: BodyExposure) -> np.ndarray:
    return np.asarray([getattr(exposure, name) for name in BODY_METRICS], dtype=np.float64)


def _total_metrics_from_components(
    component_metrics: np.ndarray,
    component_sab: tuple[np.ndarray, np.ndarray, np.ndarray],
    areas: np.ndarray,
    body_mass_kg: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Reduce three linear body solves without a redundant fourth solve."""
    sab = component_sab[0] + component_sab[1] + component_sab[2]
    absorbed = float(np.sum(sab * areas, dtype=np.float64))
    total_area = float(np.sum(areas, dtype=np.float64))
    total = np.array(
        [
            float(np.sum(component_metrics[:, BODY_METRICS.index("arriving_power_density_w_m2")])),
            float(np.sum(component_metrics[:, BODY_METRICS.index("susceptibility")])),
            float(np.max(sab)),
            absorbed / total_area,
            absorbed,
            absorbed / body_mass_kg,
        ],
        dtype=np.float64,
    )
    return total, sab


def _combined_component_metrics(
    component_metrics: tuple[np.ndarray, ...],
    sab: np.ndarray,
    areas: np.ndarray,
    body_mass_kg: float,
) -> np.ndarray:
    """Combine linear subterms while reducing peak only after Sab addition."""
    absorbed = float(np.sum(sab * areas, dtype=np.float64))
    return np.asarray(
        [
            sum(float(value[BODY_METRICS.index("arriving_power_density_w_m2")]) for value in component_metrics),
            sum(float(value[BODY_METRICS.index("susceptibility")]) for value in component_metrics),
            float(np.max(sab)),
            absorbed / float(np.sum(areas, dtype=np.float64)),
            absorbed,
            absorbed / body_mass_kg,
        ],
        dtype=np.float64,
    )


class RooflineCheckpoint:
    """Compact scalar shards plus bounded cumulative surface-field snapshots."""

    def __init__(
        self,
        root: Path,
        identity: dict[str, Any],
        points: int,
        surfaces: int,
        convergence_looks: tuple[int, ...],
    ) -> None:
        self.root = root
        self.index_path = root / "index.json"
        self.shard_dir = root / "replicas"
        self.cumulative_dir = root / "cumulative"
        self.identity = identity
        self.points = int(points)
        self.surfaces = int(surfaces)
        self.convergence_looks = convergence_looks
        self.root.mkdir(parents=True, exist_ok=True)
        self.shard_dir.mkdir(parents=True, exist_ok=True)
        self.cumulative_dir.mkdir(parents=True, exist_ok=True)
        if self.index_path.exists():
            self.index = json.loads(self.index_path.read_text(encoding="utf-8"))
            self._validate_index()
        else:
            self.index = {
                "schema_version": SCHEMA_VERSION,
                "identity_sha256": identity["sha256"],
                "points": self.points,
                "surfaces": self.surfaces,
                "components": list(COMPONENTS),
                "body_metrics": list(BODY_METRICS),
                "reference_fields": list(REFERENCE_FIELDS),
                "timing_fields": list(TIMING_FIELDS),
                "convergence_looks": list(convergence_looks),
                "committed": [],
                "cumulative_sab": None,
                "look_sab": [],
            }
            _atomic_json(self.index_path, self.index)
        self._remove_unindexed_artifacts()

    def _remove_unindexed_artifacts(self) -> None:
        """Garbage-collect only files owned by this checkpoint schema."""
        referenced = {entry["path"] for entry in self.index.get("committed", [])}
        referenced.update(entry["diagnostics_path"] for entry in self.index.get("committed", []))
        cumulative = self.index.get("cumulative_sab")
        if cumulative is not None:
            referenced.add(cumulative["path"])
        referenced.update(entry["path"] for entry in self.index.get("look_sab", []))
        candidates = [
            *self.shard_dir.glob("seed_*.npz"),
            *self.shard_dir.glob("seed_*.json"),
            *self.shard_dir.glob(TEMPORARY_GLOB),
            *self.cumulative_dir.glob("sab_sum_*.npz"),
            *self.cumulative_dir.glob(TEMPORARY_GLOB),
            *self.root.glob(TEMPORARY_GLOB),
        ]
        for path in candidates:
            relative = str(path.relative_to(self.root))
            if relative not in referenced:
                path.unlink(missing_ok=True)

    def _validate_index(self) -> None:
        expected = self._expected_index_header()
        for name, value in expected.items():
            if self.index.get(name) != value:
                raise ValueError(f"checkpoint {name} does not match this campaign")
        seeds = self._validate_committed_entries()
        self._validate_cumulative_entries(seeds)

    def _expected_index_header(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "identity_sha256": self.identity["sha256"],
            "points": self.points,
            "surfaces": self.surfaces,
            "components": list(COMPONENTS),
            "body_metrics": list(BODY_METRICS),
            "reference_fields": list(REFERENCE_FIELDS),
            "timing_fields": list(TIMING_FIELDS),
            "convergence_looks": list(self.convergence_looks),
        }

    def _validate_committed_entries(self) -> list[Any]:
        seeds = [entry.get("seed") for entry in self.index.get("committed", [])]
        if len(seeds) != len(set(seeds)):
            raise ValueError("checkpoint contains duplicate committed seeds")
        for entry in self.index.get("committed", []):
            path = self.root / entry["path"]
            if not path.is_file() or _file_sha256(path) != entry["sha256"]:
                raise ValueError(f"checkpoint shard failed hash validation: {path}")
            self._validate_arrays(self.load(int(entry["seed"])))
            diagnostics_path = self.root / entry["diagnostics_path"]
            if not diagnostics_path.is_file() or _file_sha256(diagnostics_path) != entry["diagnostics_sha256"]:
                raise ValueError(f"checkpoint diagnostics failed hash validation: {diagnostics_path}")
            if len(self.load_diagnostics(int(entry["seed"]))) != self.points:
                raise ValueError("checkpoint diagnostics do not align with standpoints")
        return seeds

    def _validate_cumulative_entries(self, seeds: list[Any]) -> None:
        cumulative = self.index.get("cumulative_sab")
        if bool(seeds) != bool(cumulative):
            raise ValueError("checkpoint cumulative Sab state disagrees with committed seeds")
        if cumulative is not None:
            self._validate_surface_entry(cumulative, len(seeds))
        for entry in self.index.get("look_sab", []):
            self._validate_surface_entry(entry, int(entry["replicas"]))

    @property
    def committed_seeds(self) -> tuple[int, ...]:
        return tuple(int(entry["seed"]) for entry in self.index["committed"])

    def _entry(self, seed: int) -> dict[str, Any]:
        for entry in self.index["committed"]:
            if int(entry["seed"]) == seed:
                return entry
        raise KeyError(seed)

    def load(self, seed: int) -> dict[str, np.ndarray]:
        path = self.root / self._entry(seed)["path"]
        with np.load(path, allow_pickle=False) as payload:
            return {name: np.asarray(payload[name]) for name in payload.files}

    def load_diagnostics(self, seed: int) -> list[dict[str, Any]]:
        path = self.root / self._entry(seed)["diagnostics_path"]
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, list):
            raise ValueError("checkpoint diagnostics must be a list")
        return value

    def _validate_surface_entry(self, entry: dict[str, Any], replicas: int) -> None:
        if int(entry.get("replicas", -1)) != replicas:
            raise ValueError("cumulative Sab replica count is inconsistent")
        path = self.root / entry["path"]
        if not path.is_file() or _file_sha256(path) != entry["sha256"]:
            raise ValueError(f"cumulative Sab failed hash validation: {path}")
        with np.load(path, allow_pickle=False) as payload:
            sab_sum = np.asarray(payload["sab_sum"])
        if sab_sum.shape != (self.points, self.surfaces) or sab_sum.dtype != np.float64:
            raise ValueError("cumulative Sab has the wrong shape or dtype")
        if np.any(~np.isfinite(sab_sum)) or np.any(sab_sum < 0.0):
            raise ValueError("cumulative Sab must be finite and nonnegative")

    def load_sab_sum(self, replicas: int | None = None) -> np.ndarray:
        if replicas is None or replicas == len(self.committed_seeds):
            entry = self.index["cumulative_sab"]
        else:
            entry = next(
                (item for item in self.index.get("look_sab", []) if int(item["replicas"]) == replicas),
                None,
            )
        if entry is None:
            raise ValueError(f"no cumulative Sab snapshot exists at {replicas} replicas")
        with np.load(self.root / entry["path"], allow_pickle=False) as payload:
            return np.asarray(payload["sab_sum"], dtype=np.float64)

    def _validate_arrays(self, arrays: dict[str, np.ndarray]) -> None:
        expected_shapes = {
            "raw_transfer": (self.points, len(COMPONENTS)),
            "body_metrics": (self.points, len(COMPONENTS), len(BODY_METRICS)),
            "timings": (self.points, len(TIMING_FIELDS)),
            "field_meta": (self.points, len(FIELD_META)),
            "reference": (self.points, len(REFERENCE_FIELDS)),
        }
        if set(arrays) != set(expected_shapes):
            raise ValueError(f"checkpoint shard arrays differ: {sorted(arrays)}")
        for name, shape in expected_shapes.items():
            value = np.asarray(arrays[name])
            if value.shape != shape or value.dtype != np.float64:
                raise ValueError(f"checkpoint {name} must be float64 with shape {shape}")
            if name == "timings":
                if np.any(np.isinf(value)) or np.any(value[np.isfinite(value)] < 0.0):
                    raise ValueError("checkpoint timings must be nonnegative or NaN when unavailable")
            elif not np.all(np.isfinite(value)):
                raise ValueError(f"checkpoint {name} must be finite")
        if np.any(arrays["raw_transfer"] < 0.0) or np.any(arrays["body_metrics"] < 0.0):
            raise ValueError("checkpoint transfer and body metrics must be nonnegative")
        component_sum = np.sum(arrays["raw_transfer"][:, :3], axis=1)
        if not np.allclose(arrays["raw_transfer"][:, 3], component_sum, rtol=2.0e-10, atol=1.0e-14):
            raise ValueError("checkpoint raw transfer components do not conserve total transfer")

    def commit(self, seed: int, data: ReplicaData) -> None:
        if seed in self.committed_seeds:
            raise ValueError(f"seed {seed} is already committed")
        arrays = {
            "raw_transfer": np.asarray(data.raw_transfer, dtype=np.float64),
            "body_metrics": np.asarray(data.body_metrics, dtype=np.float64),
            "timings": np.asarray(data.timings, dtype=np.float64),
            "field_meta": np.asarray(data.field_meta, dtype=np.float64),
            "reference": np.asarray(data.reference, dtype=np.float64),
        }
        self._validate_arrays(arrays)
        sab = np.asarray(data.total_sab, dtype=np.float64)
        if sab.shape != (self.points, self.surfaces) or np.any(~np.isfinite(sab)) or np.any(sab < 0.0):
            raise ValueError("replica total_sab must be finite, nonnegative, and aligned")
        if len(data.diagnostics) != self.points:
            raise ValueError("replica diagnostics must align with standpoints")
        relative = Path("replicas") / f"seed_{seed:010d}.npz"
        path = self.root / relative
        temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
        with temporary.open("wb") as handle:
            np.savez_compressed(handle, **arrays)
            handle.flush()
            os.fsync(handle.fileno())
        digest = _file_sha256(temporary)
        os.replace(temporary, path)
        diagnostics_relative = Path("replicas") / f"seed_{seed:010d}.json"
        diagnostics_path = self.root / diagnostics_relative
        _atomic_json(diagnostics_path, list(data.diagnostics))

        replicas = len(self.committed_seeds) + 1
        previous_entry = self.index.get("cumulative_sab")
        previous = np.zeros_like(sab) if previous_entry is None else self.load_sab_sum()
        cumulative = previous + sab
        cumulative_relative = Path("cumulative") / f"sab_sum_{replicas:04d}_seed_{seed:010d}.npz"
        cumulative_path = self.root / cumulative_relative
        cumulative_temporary = cumulative_path.with_name(f".{cumulative_path.name}.tmp-{os.getpid()}")
        with cumulative_temporary.open("wb") as handle:
            np.savez_compressed(handle, sab_sum=cumulative)
            handle.flush()
            os.fsync(handle.fileno())
        cumulative_digest = _file_sha256(cumulative_temporary)
        os.replace(cumulative_temporary, cumulative_path)
        cumulative_entry = {
            "replicas": replicas,
            "path": str(cumulative_relative),
            "sha256": cumulative_digest,
        }
        self.index["committed"].append(
            {
                "seed": seed,
                "path": str(relative),
                "sha256": digest,
                "diagnostics_path": str(diagnostics_relative),
                "diagnostics_sha256": _file_sha256(diagnostics_path),
            }
        )
        self.index["cumulative_sab"] = cumulative_entry
        if replicas in self.convergence_looks:
            self.index["look_sab"].append(cumulative_entry)
        _atomic_json(self.index_path, self.index)
        if previous_entry is not None:
            retained = {entry["path"] for entry in self.index.get("look_sab", [])}
            if previous_entry["path"] not in retained:
                (self.root / previous_entry["path"]).unlink(missing_ok=True)


@dataclass
class _ReplicaBuffers:
    raw_transfer: np.ndarray
    body_metrics: np.ndarray
    total_sab: np.ndarray
    timings: np.ndarray
    field_meta: np.ndarray
    reference: np.ndarray
    diagnostics: list[dict[str, Any]]

    @classmethod
    def empty(cls, points: int, surfaces: int) -> _ReplicaBuffers:
        return cls(
            raw_transfer=np.zeros((points, len(COMPONENTS)), dtype=np.float64),
            body_metrics=np.zeros((points, len(COMPONENTS), len(BODY_METRICS)), dtype=np.float64),
            total_sab=np.zeros((points, surfaces), dtype=np.float64),
            timings=np.full((points, len(TIMING_FIELDS)), np.nan, dtype=np.float64),
            field_meta=np.zeros((points, len(FIELD_META)), dtype=np.float64),
            reference=np.zeros((points, len(REFERENCE_FIELDS)), dtype=np.float64),
            diagnostics=[],
        )

    def replica_data(self) -> ReplicaData:
        return ReplicaData(
            self.raw_transfer,
            self.body_metrics,
            self.total_sab,
            self.timings,
            self.field_meta,
            self.reference,
            tuple(self.diagnostics),
        )


def _estimate_point_transport(
    prepared: PreparedRooflineCampaign,
    seed: int,
    point_index: int,
    origin: np.ndarray,
    ground_z: float,
) -> tuple[int, Any, NextEventField, ReferenceScale, dict[str, DirectionalMeasure], float]:
    point_seed = derive_point_seed(seed, point_index)
    estimator_started = time.perf_counter()
    surplus, field = prepared.estimator.estimate_field(origin, ground_z_m=float(ground_z), seed=point_seed)
    estimator_seconds = time.perf_counter() - estimator_started
    scale = reference_scale(prepared.estimator.sources, origin, prepared.config.reference_mode)
    if not np.isclose(field.direct, field.direct_atoms, rtol=2.0e-10, atol=1.0e-14):
        raise RuntimeError("diagnostic direct bins disagree with exact direct atoms")
    if not np.isclose(float(surplus.direct), field.direct, rtol=2.0e-10, atol=1.0e-14):
        raise RuntimeError("scalar and directional estimates disagree on visible-direct transfer")
    if not np.isclose(float(surplus.total), field.total, rtol=2.0e-10, atol=1.0e-14):
        raise RuntimeError("scalar and directional estimates disagree on total transfer")
    _validate_specular_acceptance(field, surplus.detail, prepared.config)
    measures = component_measures(field, scale, f"{prepared.config.site}:{point_index}:seed:{seed}")
    return point_seed, surplus, field, scale, measures, estimator_seconds


def _couple_separable_specular(
    prepared: PreparedRooflineCampaign,
    field: NextEventField,
    scale: ReferenceScale,
    point_index: int,
    seed: int,
    yaw: float,
    invariant_body_cache: _InvariantBodyCache | None,
    body_areas: np.ndarray,
    body_mass: float,
    body_cache_hits: dict[str, bool],
) -> tuple[np.ndarray, np.ndarray]:
    empty_direction = np.empty((0, 3), dtype=np.float64)
    empty_mass = np.empty(0, dtype=np.float64)
    all_measure = DirectionalMeasure(
        field.all_specular_k_hat,
        field.all_specular_atom_mass / scale.transfer_m_inv2,
        empty_direction,
        empty_mass,
        reference_id=f"{prepared.config.site}:{point_index}:all-specular",
    )
    mixed_measure = DirectionalMeasure(
        field.mixed_specular_k_hat,
        field.mixed_specular_atom_mass / scale.transfer_m_inv2,
        empty_direction,
        empty_mass,
        reference_id=f"{prepared.config.site}:{point_index}:seed:{seed}:mixed-specular",
    )
    all_key = (point_index, "all_specular")
    all_cached = None if invariant_body_cache is None else invariant_body_cache.get(all_key)
    if all_cached is None:
        all_exposure, all_sab = prepared.coupler.couple_measure_with_sab(
            all_measure,
            scale.reference_s0_w_m2,
            chunk_cells=prepared.config.body_chunk_cells,
            body_yaw_deg=float(yaw),
        )
        all_metric = _body_metric_array(all_exposure)
        all_field = np.asarray(all_sab, dtype=np.float64)
        if invariant_body_cache is not None:
            invariant_body_cache.put(all_key, all_metric, all_field)
        body_cache_hits["all_specular"] = False
    else:
        all_metric, all_field = all_cached
        body_cache_hits["all_specular"] = True
    if not mixed_measure.total:
        mixed_metric = np.zeros(len(BODY_METRICS), dtype=np.float64)
        mixed_field = np.zeros_like(all_field)
    else:
        mixed_exposure, mixed_sab = prepared.coupler.couple_measure_with_sab(
            mixed_measure,
            scale.reference_s0_w_m2,
            chunk_cells=prepared.config.body_chunk_cells,
            body_yaw_deg=float(yaw),
        )
        mixed_metric = _body_metric_array(mixed_exposure)
        mixed_field = np.asarray(mixed_sab, dtype=np.float64)
    component_field = all_field + mixed_field
    component_metric = _combined_component_metrics((all_metric, mixed_metric), component_field, body_areas, body_mass)
    return component_metric, component_field


def _couple_body_component(
    prepared: PreparedRooflineCampaign,
    component: str,
    measures: dict[str, DirectionalMeasure],
    field: NextEventField,
    scale: ReferenceScale,
    point_index: int,
    seed: int,
    yaw: float,
    invariant_body_cache: _InvariantBodyCache | None,
    body_areas: np.ndarray,
    body_mass: float,
    body_cache_hits: dict[str, bool],
) -> tuple[np.ndarray, np.ndarray]:
    cache_key = (point_index, component)
    cacheable = component == "direct"
    cached = None if invariant_body_cache is None or not cacheable else invariant_body_cache.get(cache_key)
    if cached is not None:
        body_cache_hits[component] = True
        return cached
    if component == "specular" and field.specular_components_separable:
        result = _couple_separable_specular(
            prepared,
            field,
            scale,
            point_index,
            seed,
            yaw,
            invariant_body_cache,
            body_areas,
            body_mass,
            body_cache_hits,
        )
        body_cache_hits[component] = False
        return result
    exposure, sab = prepared.coupler.couple_measure_with_sab(
        measures[component],
        scale.reference_s0_w_m2,
        chunk_cells=prepared.config.body_chunk_cells,
        body_yaw_deg=float(yaw),
    )
    component_metric = _body_metric_array(exposure)
    component_field = np.asarray(sab, dtype=np.float64)
    if invariant_body_cache is not None and cacheable:
        invariant_body_cache.put(cache_key, component_metric, component_field)
    body_cache_hits[component] = False
    return component_metric, component_field


def _couple_body_components(
    prepared: PreparedRooflineCampaign,
    measures: dict[str, DirectionalMeasure],
    field: NextEventField,
    scale: ReferenceScale,
    point_index: int,
    seed: int,
    yaw: float,
    invariant_body_cache: _InvariantBodyCache | None,
    body_areas: np.ndarray,
    body_mass: float,
) -> tuple[np.ndarray, np.ndarray, dict[str, bool]]:
    metrics = np.zeros((len(COMPONENTS), len(BODY_METRICS)), dtype=np.float64)
    component_sab: list[np.ndarray] = []
    body_cache_hits: dict[str, bool] = {}
    for component_index, component in enumerate(COMPONENTS[:3]):
        component_metric, component_field = _couple_body_component(
            prepared,
            component,
            measures,
            field,
            scale,
            point_index,
            seed,
            yaw,
            invariant_body_cache,
            body_areas,
            body_mass,
            body_cache_hits,
        )
        metrics[component_index] = component_metric
        component_sab.append(component_field)
    metrics[3], total_sab = _total_metrics_from_components(metrics[:3], tuple(component_sab), body_areas, body_mass)
    return metrics, total_sab, body_cache_hits


def _point_timing_row(
    estimator_seconds: float, body_seconds: float, field: NextEventField, detail: dict[str, Any]
) -> tuple[float, ...]:
    all_specular_seconds = float(field.all_specular_diagnostics.get("seconds", 0.0))
    suffix_specular_seconds = float(detail.get("specular_suffix_seconds", 0.0))
    return (
        estimator_seconds,
        float(detail["direct_seconds"]) if "direct_seconds" in detail else np.nan,
        float(detail["stochastic_trace_seconds"]) if "stochastic_trace_seconds" in detail else np.nan,
        all_specular_seconds + suffix_specular_seconds,
        body_seconds,
    )


def _point_field_meta(field: NextEventField) -> tuple[float, ...]:
    return (
        float(field.includes_specular),
        float(field.missing_specular),
        float(field.maximum_completed_all_specular_order),
        float(field.maximum_completed_specular_suffix_order),
        float(field.direct_atom_mass.size),
        float(field.specular_atom_mass.size),
        float(np.count_nonzero(field.bounced_mass)),
    )


def _point_diagnostic(
    point_seed: int,
    field: NextEventField,
    detail: dict[str, Any],
    body_cache_hits: dict[str, bool],
) -> dict[str, Any]:
    return {
        "point_seed": point_seed,
        "specular_estimate_kind": field.specular_estimate_kind,
        "finite_resolution_specular_estimate": field.finite_resolution_specular_estimate,
        "specular_bounce_cap": field.specular_bounce_cap,
        "specular_order_one_complete": field.specular_order_one_complete,
        "specular_complete_through_bounce_cap": field.specular_complete_through_bounce_cap,
        "specular_result_complete": field.specular_result_complete,
        "specular_work": field.specular_work,
        "all_specular_diagnostics": field.all_specular_diagnostics,
        "specular_source_refinement": list(field.specular_source_refinement),
        "specular_suffix_candidates": detail.get("specular_suffix_candidates"),
        "specular_suffix_accepted": detail.get("specular_suffix_accepted"),
        "sampled_specular_suffix_full_support": field.sampled_specular_suffix_full_support,
        "sampled_specular_suffix": detail.get("sampled_specular_suffix", {"enabled": False}),
        "body_component_cache_hits": body_cache_hits,
        "timing_availability": {
            "direct_shadow_seconds": "direct_seconds" in detail,
            "stochastic_trace_seconds": "stochastic_trace_seconds" in detail,
        },
    }


def _run_replica(
    prepared: PreparedRooflineCampaign,
    seed: int,
    invariant_body_cache: _InvariantBodyCache | None = None,
) -> ReplicaData:
    points = len(prepared.walk)
    surfaces = int(np.asarray(prepared.coupler.body.areas).size)
    buffers = _ReplicaBuffers.empty(points, surfaces)
    body_areas = np.asarray(prepared.coupler.body.areas, dtype=np.float64)
    body_mass = float(prepared.coupler.body_mass_kg)
    for point_index, (origin, ground_z, yaw) in enumerate(
        zip(prepared.walk.points, prepared.walk.ground_z_m, prepared.walk.body_yaw_deg, strict=True)
    ):
        point_seed, surplus, field, scale, measures, estimator_seconds = _estimate_point_transport(
            prepared, seed, point_index, origin, ground_z
        )
        buffers.raw_transfer[point_index] = (
            field.direct_atoms,
            field.specular,
            float(np.sum(field.bounced_mass, dtype=np.float64)),
            field.total,
        )
        buffers.reference[point_index] = (scale.transfer_m_inv2, scale.reference_s0_w_m2)
        body_started = time.perf_counter()
        point_metrics, point_sab, body_cache_hits = _couple_body_components(
            prepared,
            measures,
            field,
            scale,
            point_index,
            seed,
            yaw,
            invariant_body_cache,
            body_areas,
            body_mass,
        )
        body_seconds = time.perf_counter() - body_started
        detail = surplus.detail
        buffers.body_metrics[point_index] = point_metrics
        buffers.total_sab[point_index] = point_sab
        buffers.timings[point_index] = _point_timing_row(estimator_seconds, body_seconds, field, detail)
        buffers.field_meta[point_index] = _point_field_meta(field)
        buffers.diagnostics.append(_point_diagnostic(point_seed, field, detail, body_cache_hits))
    return buffers.replica_data()


def _validate_specular_acceptance(
    field: NextEventField, detail: dict[str, Any], config: RooflineCampaignConfig
) -> None:
    """Refuse a field that does not meet the campaign's declared specular claim."""
    policy = config.specular_acceptance
    if policy == "exact_complete":
        _validate_exact_complete_specular(field)
        return
    if policy == "adaptive_converged":
        _validate_adaptive_specular(field, detail.get("finite_resolution_specular_work"))
        return
    if policy == "adaptive_all_specular_sampled_mixed_order_1":
        _validate_sampled_mixed_specular(field, detail)
        return
    if policy == "omitted_diagnostic":
        _validate_omitted_specular(field)
        return
    raise AssertionError(f"unvalidated specular acceptance policy {policy!r}")


def _validate_exact_complete_specular(field: NextEventField) -> None:
    if field.maximum_completed_all_specular_order < 1:
        raise RuntimeError("field did not complete exact all-specular order one")
    if field.maximum_completed_specular_suffix_order < 1:
        raise RuntimeError("field did not complete exact specular-suffix order one")
    if (
        not field.includes_specular
        or field.specular_estimate_kind != "exact_order_1"
        or field.finite_resolution_specular_estimate
        or not field.specular_order_one_complete
    ):
        raise RuntimeError("exact-complete campaign received a non-exact specular field")


def _adaptive_work_accepted(work: Any) -> bool:
    return (
        isinstance(work, dict)
        and bool(work.get("enabled", False))
        and bool(work.get("numerically_converged", False))
        and work.get("stop_reason") == "relative_tolerance_reached"
    )


def _validate_adaptive_specular(field: NextEventField, work: Any) -> None:
    field_accepted = (
        field.includes_specular
        and field.finite_resolution_specular_estimate
        and field.specular_numerically_converged
        and not field.specular_order_one_complete
        and not field.specular_complete_through_bounce_cap
    )
    if not field_accepted or not _adaptive_work_accepted(work):
        raise RuntimeError("adaptive-specular field did not reach its declared numerical tolerance")


def _sampled_field_accepted(field: NextEventField) -> bool:
    return (
        field.includes_specular
        and field.specular_estimate_kind == "adaptive_all_sampled_mixed_order_1"
        and field.finite_resolution_specular_estimate
        and field.specular_numerically_converged
        and field.maximum_completed_all_specular_order == 0
        and field.maximum_completed_specular_suffix_order == 0
        and not field.specular_order_one_complete
        and not field.specular_complete_through_bounce_cap
        and field.sampled_specular_suffix_full_support
        and field.specular_components_separable
    )


def _sampled_suffix_accepted(sampled: Any) -> bool:
    if not isinstance(sampled, dict):
        return False
    try:
        samples_per_vertex = int(sampled.get("samples_per_vertex", 0))
    except (TypeError, ValueError):
        return False
    return (
        bool(sampled.get("enabled", False))
        and samples_per_vertex >= 1
        and "conditional_on_traced_diffuse_vertices" in str(sampled.get("uncertainty_scope", ""))
    )


def _sampled_identity_accepted(sampled: dict[str, Any]) -> bool:
    identity = sampled.get("sampling_identity", {})
    return (
        identity.get("status") == "experimental_opt_in"
        and bool(identity.get("surface_support_complete", False))
        and identity.get("source_support") == identity.get("source_count")
    )


def _sampled_mixed_failed_clauses(
    field: NextEventField,
    work: Any,
    sampled: Any,
) -> list[str]:
    """Describe every failed acceptance invariant with its observed value."""
    work_dict = work if isinstance(work, dict) else {}
    sampled_dict = sampled if isinstance(sampled, dict) else {}
    identity_value = sampled_dict.get("sampling_identity", {})
    identity = identity_value if isinstance(identity_value, dict) else {}
    sample_value = sampled_dict.get("samples_per_vertex", None)
    try:
        positive_sample_count = int(sample_value) >= 1
    except (TypeError, ValueError):
        positive_sample_count = False
    scope = str(sampled_dict.get("uncertainty_scope", ""))
    checks: dict[str, tuple[Any, bool]] = {
        "field.includes_specular": (field.includes_specular, field.includes_specular),
        "field.specular_estimate_kind": (
            field.specular_estimate_kind,
            field.specular_estimate_kind == "adaptive_all_sampled_mixed_order_1",
        ),
        "field.finite_resolution_specular_estimate": (
            field.finite_resolution_specular_estimate,
            field.finite_resolution_specular_estimate,
        ),
        "field.specular_numerically_converged": (
            field.specular_numerically_converged,
            field.specular_numerically_converged,
        ),
        "field.maximum_completed_all_specular_order": (
            field.maximum_completed_all_specular_order,
            field.maximum_completed_all_specular_order == 0,
        ),
        "field.maximum_completed_specular_suffix_order": (
            field.maximum_completed_specular_suffix_order,
            field.maximum_completed_specular_suffix_order == 0,
        ),
        "field.specular_order_one_complete": (field.specular_order_one_complete, not field.specular_order_one_complete),
        "field.specular_complete_through_bounce_cap": (
            field.specular_complete_through_bounce_cap,
            not field.specular_complete_through_bounce_cap,
        ),
        "field.sampled_specular_suffix_full_support": (
            field.sampled_specular_suffix_full_support,
            field.sampled_specular_suffix_full_support,
        ),
        "field.specular_components_separable": (
            field.specular_components_separable,
            field.specular_components_separable,
        ),
        "work.is_mapping": (type(work).__name__, isinstance(work, dict)),
        "work.enabled": (work_dict.get("enabled"), bool(work_dict.get("enabled", False))),
        "work.numerically_converged": (
            work_dict.get("numerically_converged"),
            bool(work_dict.get("numerically_converged", False)),
        ),
        "work.stop_reason": (
            work_dict.get("stop_reason"),
            work_dict.get("stop_reason") == "relative_tolerance_reached",
        ),
        "sampled.is_mapping": (type(sampled).__name__, isinstance(sampled, dict)),
        "sampled.enabled": (sampled_dict.get("enabled"), bool(sampled_dict.get("enabled", False))),
        "sampled.samples_per_vertex>=1": (sample_value, positive_sample_count),
        "sampled.uncertainty_scope_contains_conditional_on_traced_diffuse_vertices": (
            scope,
            "conditional_on_traced_diffuse_vertices" in scope,
        ),
        "sampled.sampling_identity.is_mapping": (
            type(identity_value).__name__,
            isinstance(identity_value, dict),
        ),
        "sampled.sampling_identity.status": (
            identity.get("status"),
            identity.get("status") == "experimental_opt_in",
        ),
        "sampled.sampling_identity.surface_support_complete": (
            identity.get("surface_support_complete"),
            bool(identity.get("surface_support_complete", False)),
        ),
        "sampled.sampling_identity.source_support==source_count": (
            (identity.get("source_support"), identity.get("source_count")),
            identity.get("source_support") == identity.get("source_count"),
        ),
    }
    return [f"{name}={observed!r}" for name, (observed, passed) in checks.items() if not passed]


def _validate_sampled_mixed_specular(field: NextEventField, detail: dict[str, Any]) -> None:
    work = detail.get("finite_resolution_specular_work")
    sampled = detail.get("sampled_specular_suffix")
    accepted = (
        _sampled_field_accepted(field)
        and _adaptive_work_accepted(work)
        and _sampled_suffix_accepted(sampled)
        and _sampled_identity_accepted(sampled)
    )
    if not accepted:
        failures = ", ".join(_sampled_mixed_failed_clauses(field, work, sampled))
        raise RuntimeError(
            "combined adaptive all-specular and sampled mixed-suffix field failed its declared acceptance. "
            f"Failed clauses: {failures}"
        )


def _validate_omitted_specular(field: NextEventField) -> None:
    if (
        field.includes_specular
        or field.specular_estimate_kind != "absent"
        or field.specular_order_one_complete
        or field.specular_complete_through_bounce_cap
    ):
        raise RuntimeError("specular-omitted diagnostic unexpectedly contains a specular estimate")


def _mean_and_se(total: np.ndarray, total_sq: np.ndarray, count: int) -> tuple[np.ndarray, np.ndarray]:
    mean = total / count
    if count < 2:
        return mean, np.zeros_like(mean)
    variance = np.maximum((total_sq - np.square(total) / count) / (count - 1), 0.0)
    return mean, np.sqrt(variance / count)


def _db_change(current: np.ndarray, previous: np.ndarray) -> dict[str, float | None]:
    valid = (current > 0.0) & (previous > 0.0)
    if not np.any(valid):
        return {"max_abs_db": None, "p90_abs_db": None}
    change = np.abs(10.0 * np.log10(current[valid] / previous[valid]))
    return {"max_abs_db": float(np.max(change)), "p90_abs_db": float(np.quantile(change, 0.9))}


def _convergence(
    checkpoint: RooflineCheckpoint, seeds: tuple[int, ...], looks: tuple[int, ...]
) -> list[dict[str, Any]]:
    reached = tuple(sorted(set((*looks, len(seeds)))))
    answer = []
    previous_raw = None
    previous_mean_sab = None
    previous_peak = None
    for look in reached:
        raw_sum = np.zeros((checkpoint.points, len(COMPONENTS)), dtype=np.float64)
        metric_sum = np.zeros((checkpoint.points, len(COMPONENTS), len(BODY_METRICS)), dtype=np.float64)
        for seed in seeds[:look]:
            data = checkpoint.load(seed)
            raw_sum += data["raw_transfer"]
            metric_sum += data["body_metrics"]
        raw_mean = raw_sum[:, 3] / look
        mean_sab = metric_sum[:, 3, BODY_METRICS.index("mean_sab_w_m2")] / look
        peak = np.max(checkpoint.load_sab_sum(look) / look, axis=1)
        record: dict[str, Any] = {"seeds": look}
        if previous_raw is not None:
            record["change_from_previous_look"] = {
                "total_transfer": _db_change(raw_mean, previous_raw),
                "area_mean_sab": _db_change(mean_sab, previous_mean_sab),
                "ensemble_field_peak_sab": _db_change(peak, previous_peak),
            }
        answer.append(record)
        previous_raw, previous_mean_sab, previous_peak = raw_mean, mean_sab, peak
    return answer


def _diagnostic_variants(checkpoint: RooflineCheckpoint, seeds: tuple[int, ...]) -> list[list[dict[str, Any]]]:
    """Compact exact diagnostics by counting identical per-point variants."""
    variants: list[dict[str, dict[str, Any]]] = [dict() for _ in range(checkpoint.points)]
    for seed in seeds:
        for point_index, diagnostic in enumerate(checkpoint.load_diagnostics(seed)):
            stable = dict(diagnostic)
            stable.pop("point_seed", None)
            digest = _sha256_bytes(_canonical_bytes(stable))
            if digest not in variants[point_index]:
                variants[point_index][digest] = {"sha256": digest, "replicas": 0, "data": stable}
            variants[point_index][digest]["replicas"] += 1
    return [list(point.values()) for point in variants]


@dataclass(frozen=True)
class _SummaryAccumulation:
    raw_sum: np.ndarray
    raw_sq: np.ndarray
    metric_sum: np.ndarray
    metric_sq: np.ndarray
    timing_sum: np.ndarray
    timing_count: np.ndarray
    field_meta_min: np.ndarray
    field_meta_max: np.ndarray
    reference: np.ndarray | None


@dataclass(frozen=True)
class _SummaryMoments:
    raw_mean: np.ndarray
    raw_se: np.ndarray
    metric_mean: np.ndarray
    metric_se: np.ndarray
    ensemble_peak: np.ndarray


def _accumulate_summary(checkpoint: RooflineCheckpoint, seeds: tuple[int, ...]) -> _SummaryAccumulation:
    raw_sum = np.zeros((checkpoint.points, len(COMPONENTS)), dtype=np.float64)
    raw_sq = np.zeros_like(raw_sum)
    metric_sum = np.zeros((checkpoint.points, len(COMPONENTS), len(BODY_METRICS)), dtype=np.float64)
    metric_sq = np.zeros_like(metric_sum)
    timing_sum = np.zeros((checkpoint.points, len(TIMING_FIELDS)), dtype=np.float64)
    timing_count = np.zeros_like(timing_sum)
    field_meta_min = np.full((checkpoint.points, len(FIELD_META)), np.inf, dtype=np.float64)
    field_meta_max = np.full((checkpoint.points, len(FIELD_META)), -np.inf, dtype=np.float64)
    reference_value = None
    for seed in seeds:
        data = checkpoint.load(seed)
        raw_sum += data["raw_transfer"]
        raw_sq += np.square(data["raw_transfer"])
        metric_sum += data["body_metrics"]
        metric_sq += np.square(data["body_metrics"])
        finite_timing = np.isfinite(data["timings"])
        timing_sum += np.where(finite_timing, data["timings"], 0.0)
        timing_count += finite_timing
        field_meta_min = np.minimum(field_meta_min, data["field_meta"])
        field_meta_max = np.maximum(field_meta_max, data["field_meta"])
        if reference_value is None:
            reference_value = data["reference"]
        elif not np.array_equal(reference_value, data["reference"]):
            raise ValueError("reference transfer changed between replicas")
    return _SummaryAccumulation(
        raw_sum,
        raw_sq,
        metric_sum,
        metric_sq,
        timing_sum,
        timing_count,
        field_meta_min,
        field_meta_max,
        reference_value,
    )


def _location_components(
    point_index: int,
    raw_mean: np.ndarray,
    raw_se: np.ndarray,
    metric_mean: np.ndarray,
    metric_se: np.ndarray,
    ensemble_peak: np.ndarray,
) -> dict[str, Any]:
    components: dict[str, Any] = {}
    for component_index, component in enumerate(COMPONENTS):
        body = {}
        for metric_index, name in enumerate(BODY_METRICS):
            output_name = "mean_per_replica_peak_sab_w_m2" if name == "peak_sab_w_m2" else name
            body[output_name] = {
                "mean": float(metric_mean[point_index, component_index, metric_index]),
                "se": float(metric_se[point_index, component_index, metric_index]),
            }
        if component == "total":
            body["ensemble_field_peak_sab_w_m2"] = float(ensemble_peak[point_index])
        components[component] = {
            "raw_transfer_m_inv2": {
                "mean": float(raw_mean[point_index, component_index]),
                "se": float(raw_se[point_index, component_index]),
            },
            "body": body,
        }
    return components


def _location_row(
    prepared: PreparedRooflineCampaign,
    point_index: int,
    origin: np.ndarray,
    count: int,
    route_distance: float,
    point_kinds: Any,
    reference_value: np.ndarray,
    moments: _SummaryMoments,
    accumulation: _SummaryAccumulation,
    diagnostic_variants: list[list[dict[str, Any]]],
) -> dict[str, Any]:
    direct = moments.raw_mean[point_index, 0]
    total = moments.raw_mean[point_index, 3]
    return {
        "site": prepared.config.site,
        "cohort": prepared.config.cohort,
        "standpoint": point_index,
        "point_kind": None if point_kinds is None else point_kinds[point_index],
        "position_m": [float(value) for value in origin],
        "ground_z_m": float(prepared.walk.ground_z_m[point_index]),
        "body_yaw_deg": float(prepared.walk.body_yaw_deg[point_index]),
        "route_distance_m": float(route_distance),
        "replicas": count,
        "reference": {
            "d_ref_m_inv2": float(reference_value[point_index, 0]),
            "d_vis_m_inv2": float(direct),
            "reference_s0_w_m2": float(reference_value[point_index, 1]),
            "scale_mode": prepared.config.reference_mode,
        },
        "multipath_surplus": {
            "ratio": float(total / direct) if direct > 0.0 else None,
            "db": float(10.0 * np.log10(total / direct)) if direct > 0.0 and total > 0.0 else None,
        },
        "components": _location_components(
            point_index,
            moments.raw_mean,
            moments.raw_se,
            moments.metric_mean,
            moments.metric_se,
            moments.ensemble_peak,
        ),
        "timing_seconds_per_replica_mean": {
            name: (
                float(accumulation.timing_sum[point_index, index] / accumulation.timing_count[point_index, index])
                if accumulation.timing_count[point_index, index] > 0
                else None
            )
            for index, name in enumerate(TIMING_FIELDS)
        },
        "field_metadata_range": {
            name: [
                float(accumulation.field_meta_min[point_index, index]),
                float(accumulation.field_meta_max[point_index, index]),
            ]
            for index, name in enumerate(FIELD_META)
        },
        "specular_diagnostic_variants": diagnostic_variants[point_index],
    }


def _summary_payload(
    prepared: PreparedRooflineCampaign,
    checkpoint: RooflineCheckpoint,
    seeds: tuple[int, ...],
    accumulation: _SummaryAccumulation,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "site": prepared.config.site,
        "cohort": prepared.config.cohort,
        "standpoints": checkpoint.points,
        "replicas": len(seeds),
        "seeds": list(seeds),
        "reference_mode": prepared.config.reference_mode,
        "timing_seconds_observed_total": {
            name: float(np.sum(accumulation.timing_sum[:, index], dtype=np.float64))
            for index, name in enumerate(TIMING_FIELDS)
        },
        "timing_observation_counts": {
            name: int(np.sum(accumulation.timing_count[:, index], dtype=np.float64))
            for index, name in enumerate(TIMING_FIELDS)
        },
        "convergence": _convergence(checkpoint, seeds, prepared.config.convergence_looks),
    }


def _summarize(prepared: PreparedRooflineCampaign, checkpoint: RooflineCheckpoint) -> dict[str, Any]:
    seeds = checkpoint.committed_seeds
    count = len(seeds)
    if not count:
        raise ValueError("cannot summarize an empty campaign")
    sab_sum = checkpoint.load_sab_sum()
    accumulation = _accumulate_summary(checkpoint, seeds)
    reference_value = accumulation.reference
    if reference_value is None:
        raise RuntimeError("reference transfer was not collected")
    raw_mean, raw_se = _mean_and_se(accumulation.raw_sum, accumulation.raw_sq, count)
    metric_mean, metric_se = _mean_and_se(accumulation.metric_sum, accumulation.metric_sq, count)
    ensemble_peak = np.max(sab_sum / count, axis=1)
    moments = _SummaryMoments(raw_mean, raw_se, metric_mean, metric_se, ensemble_peak)
    rows = []
    cumulative = np.cumsum(np.asarray(prepared.walk.step_m, dtype=np.float64))
    point_kinds = prepared.walk.provenance.get("point_kind")
    diagnostic_variants = _diagnostic_variants(checkpoint, seeds)
    for point_index, origin in enumerate(prepared.walk.points):
        rows.append(
            _location_row(
                prepared,
                point_index,
                origin,
                count,
                cumulative[point_index],
                point_kinds,
                reference_value,
                moments,
                accumulation,
                diagnostic_variants,
            )
        )
    return {
        "rows": rows,
        "summary": _summary_payload(prepared, checkpoint, seeds, accumulation),
    }


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(_json_value(row), sort_keys=True, allow_nan=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def run_roofline_campaign(prepared: PreparedRooflineCampaign) -> dict[str, Path]:
    """Run or resume all declared seeds, then write compact CDF-ready outputs."""
    identity = campaign_identity(prepared)
    output = prepared.config.output_dir
    output.mkdir(parents=True, exist_ok=True)
    for name in (IDENTITY_FILENAME, LOCATIONS_FILENAME, SUMMARY_FILENAME, MANIFEST_FILENAME):
        for temporary in output.glob(f".{name}.tmp-*"):
            temporary.unlink(missing_ok=True)
    identity_path = output / IDENTITY_FILENAME
    if identity_path.exists():
        existing = json.loads(identity_path.read_text(encoding="utf-8"))
        if existing.get("sha256") != identity["sha256"]:
            raise ValueError("output directory belongs to a different roofline campaign")
    else:
        _atomic_json(identity_path, identity)
    checkpoint = RooflineCheckpoint(
        output / "checkpoint",
        identity,
        len(prepared.walk),
        int(np.asarray(prepared.coupler.body.areas).size),
        prepared.config.convergence_looks,
    )
    committed = checkpoint.committed_seeds
    planned_prefix = prepared.config.planned_seeds[: len(committed)]
    if committed != planned_prefix:
        raise ValueError("checkpoint seeds are not a complete prefix of the planned campaign")
    invariant_body_cache = _InvariantBodyCache.for_walk(len(prepared.walk))
    for seed in prepared.config.planned_seeds[len(committed) :]:
        checkpoint.commit(seed, _run_replica(prepared, seed, invariant_body_cache))
    result = _summarize(prepared, checkpoint)
    locations_path = output / LOCATIONS_FILENAME
    summary_path = output / SUMMARY_FILENAME
    manifest_path = output / MANIFEST_FILENAME
    _write_jsonl(locations_path, result["rows"])
    _atomic_json(summary_path, result["summary"])
    surface_files: dict[str, str] = {}
    for entry in [checkpoint.index["cumulative_sab"], *checkpoint.index["look_sab"]]:
        if entry is not None:
            surface_files[f"checkpoint/{entry['path']}"] = entry["sha256"]
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "identity_sha256": identity["sha256"],
        "output_profile": "minimal_results_plus_resumable_seed_shards",
        "optional_audit_and_blender_artifacts": "not_generated",
        "files": {
            IDENTITY_FILENAME: _file_sha256(identity_path),
            LOCATIONS_FILENAME: _file_sha256(locations_path),
            SUMMARY_FILENAME: _file_sha256(summary_path),
            "checkpoint/index.json": _file_sha256(checkpoint.index_path),
            **{f"checkpoint/{entry['path']}": entry["sha256"] for entry in checkpoint.index["committed"]},
            **{
                f"checkpoint/{entry['diagnostics_path']}": entry["diagnostics_sha256"]
                for entry in checkpoint.index["committed"]
            },
            **surface_files,
        },
    }
    _atomic_json(manifest_path, manifest)
    return {
        "manifest": manifest_path,
        "locations": locations_path,
        "summary": summary_path,
        "checkpoint": checkpoint.index_path,
    }
