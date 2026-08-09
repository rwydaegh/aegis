"""Validated persistent cache for seed-invariant next-event work."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import os
import socket
import time
import uuid
import zipfile
from collections.abc import Callable, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, BinaryIO, TypeVar

import numpy as np

from ..illumination.sources import normalized_source_weights
from .specular import SpecularDiagnostics, SpecularPaths, SpecularWorkEstimate

CACHE_SCHEMA = "aegis_transport_persistent_cache_v1"
CACHE_ALGORITHM = "exact_direct_adaptive_one_reflection_v1"
_DIRECT_KIND = "exact_direct"
_SPECULAR_KIND = "deterministic_one_reflection"
_MAX_MANIFEST_BYTES = 8 * 1024 * 1024
_LOCK_WAIT_SECONDS = 12 * 60 * 60
_LOCK_POLL_SECONDS = 0.05
_LOCK_STALE_SECONDS = 7 * 24 * 60 * 60
_LOCK_INCOMPLETE_SECONDS = 30.0
_ARRAY_MEMBERS = {
    _DIRECT_KIND: frozenset(("direct.npy", "seen.npy")),
    _SPECULAR_KIND: frozenset(
        (
            "k_hat.npy",
            "transfer.npy",
            "reflection_point.npy",
            "source_index.npy",
            "endpoint_index.npy",
            "surface_sequence.npy",
            "unfolded_length_m.npy",
        )
    ),
}
_FIELD_MEMBERS = frozenset(("direct_mass.npy", "direct_k_hat.npy", "direct_atom_mass.npy"))
_REFINEMENT_FIELDS = frozenset(
    (
        "step",
        "axis_refined",
        "face_level",
        "source_level",
        "angular_samples",
        "cumulative_visibility_rays",
        "selected_faces",
        "requested_strata",
        "selected_sources",
        "candidate_support_complete",
        "source_support_complete",
        "finite_resolution_support_incomplete",
        "candidates",
        "cumulative_candidates",
        "executed_candidates",
        "avoided_candidates",
        "cumulative_executed_candidates",
        "cumulative_avoided_candidates",
        "accepted",
        "seconds",
        "executed_seconds",
        "cumulative_executed_seconds",
        "logical_solution_seconds",
        "reused_block_seconds",
        "transfer",
        "absolute_change_from_previous_face_level",
        "relative_change_from_previous_face_level",
        "absolute_change_from_previous_source_level",
        "relative_change_from_previous_source_level",
        "face_axis_converged",
        "source_axis_converged",
        "numerically_converged",
        "relative_tolerance",
    )
)
_FINITE_WORK_REQUIRED_FIELDS = frozenset(
    (
        "method",
        "candidate_budget",
        "relative_tolerance",
        "numerically_converged",
        "support_complete",
        "stop_reason",
        "enabled",
    )
)
_FINITE_WORK_OPTIONAL_FIELDS = frozenset(
    (
        "candidate_work_used",
        "executed_candidate_work_used",
        "avoided_candidate_work",
        "executed_candidate_seconds",
        "total_candidates_upper_bound",
        "visibility_rays_used",
        "refinement_work_used",
        "mixed_specular_suffix_enabled",
        "mixed_specular_suffix_method",
        "estimate_count",
        "budget_remaining",
        "blocked_next_cycle",
        "face_level_counts",
        "source_strata_levels",
    )
)
_FINITE_WORK_METHODS = frozenset(
    (
        "exact_all_specular_order_1",
        "adaptive_receiver_faces_and_probability_strata",
    )
)
_FINITE_WORK_STOP_REASONS = frozenset(
    (
        "full_reflection_and_source_support_enumerated",
        "source_curve_required_for_bounded_source_refinement",
        "initial_visibility_screen_exceeds_candidate_budget",
        "initial_estimate_exceeds_candidate_budget",
        "candidate_budget_exhausted",
        "relative_tolerance_reached",
    )
)


class _CacheMiss(ValueError):
    """Internal signal for corrupt, stale, or incompatible cache entries."""


@dataclass(frozen=True)
class DirectCacheValue:
    """Final exact-direct arrays retained by the persistent cache."""

    direct: np.ndarray
    seen: np.ndarray
    field_data: tuple[np.ndarray, np.ndarray, np.ndarray, float, float] | None


@dataclass(frozen=True)
class SpecularCacheValue:
    """Final deterministic specular output and its complete work evidence."""

    specular_work: SpecularWorkEstimate | None
    paths: SpecularPaths | None
    refinement: list[dict[str, Any]]
    finite_work: dict[str, Any] | None
    suffix_transport_enabled: bool


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not np.isfinite(value):
            raise ValueError("cache metadata must contain only finite numbers")
        return value
    if isinstance(value, np.generic):
        return _json_value(value.item())
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    raise TypeError(f"cache metadata cannot encode {type(value).__name__}")


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant {value!r}")


def _array_identity(value: Any, dtype: np.dtype[Any] | type[Any]) -> dict[str, Any]:
    target = np.dtype(dtype).newbyteorder("<")
    array = np.ascontiguousarray(np.asarray(value, dtype=target))
    if np.issubdtype(array.dtype, np.inexact) and np.any(~np.isfinite(array)):
        raise ValueError("cache identity arrays must be finite")
    digest = hashlib.sha256()
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(_canonical_json(list(array.shape)))
    digest.update(array.tobytes(order="C"))
    return {"dtype": array.dtype.str, "shape": list(array.shape), "sha256": digest.hexdigest()}


def _optional_array_identity(owner: Any, name: str, dtype: np.dtype[Any] | type[Any]) -> dict[str, Any] | None:
    value = getattr(owner, name, None)
    return None if value is None else _array_identity(value, dtype)


def _geometry_identity(geometry: Any) -> dict[str, Any] | None:
    vertices = getattr(geometry, "vertices", None)
    faces = getattr(geometry, "faces", None)
    if vertices is None or faces is None:
        return None
    return {
        "class": f"{type(geometry).__module__}.{type(geometry).__qualname__}",
        "variant": getattr(geometry, "variant", None),
        "vertices": _array_identity(vertices, np.float64),
        "faces": _array_identity(faces, np.int64),
    }


def _atlas_identity(atlas: Any) -> dict[str, Any] | None:
    if atlas is None:
        return None
    arrays = {
        name: _array_identity(getattr(atlas, name), np.asarray(getattr(atlas, name)).dtype)
        for name in (
            "face_to_atlas_row",
            "material_probability",
            "supported",
            "valid_texels",
            "material_class",
            "nonblocking",
        )
    }
    return {
        "class": f"{type(atlas).__module__}.{type(atlas).__qualname__}",
        "material_names": list(atlas.material_names),
        "arrays": arrays,
    }


def _surface_identity(transport: Any) -> dict[str, Any] | None:
    if transport is None:
        return None
    surfaces = transport.surfaces
    return {
        "transport_class": f"{type(transport).__module__}.{type(transport).__qualname__}",
        "triangles": _array_identity(surfaces.triangles, np.float64),
        "normals": _array_identity(surfaces.normals, np.float64),
        "face_index": _array_identity(surfaces.face_index, np.int64),
        "material_class": _array_identity(surfaces.material_class, np.int64),
        "support_complete": bool(surfaces.support_complete),
        "scene_face_count": int(surfaces.scene_face_count),
        "construction": str(surfaces.construction),
        "candidate_chunk": int(transport.candidate_chunk),
        "candidate_budget": int(transport.candidate_budget),
        "epsilon_m": float(transport.epsilon_m),
    }


def _common_identity(estimator: Any) -> dict[str, Any] | None:
    geometry = _geometry_identity(estimator.geometry)
    if geometry is None:
        return None
    tracer = estimator.tracer
    sites = np.asarray(estimator.sources.sites(), dtype=np.float64)
    weights = normalized_source_weights(estimator.sources)
    atlas = _atlas_identity(getattr(tracer, "atlas_material", None))
    # Late imports keep this module import-light and avoid a cycle with
    # next_event, which imports this cache. The identity must read the live
    # constants: a literal here would keep serving stale entries after an
    # algorithm constant changed.
    from .next_event import DIRECT_EPSILON_M, MIN_CONNECT_M
    from .specular_broadphase import _DEFAULT_INSIDE_TOLERANCE, _ROUND_OFF_MULTIPLIER

    deterministic_settings = {
        "samples": int(estimator.samples),
        "max_order": None if estimator.max_order is None else int(estimator.max_order),
        "connection_lift_m": float(estimator.connection_lift_m),
        "direct_epsilon_m": float(DIRECT_EPSILON_M),
        "minimum_connect_m": float(MIN_CONNECT_M),
        "broadphase_inside_tolerance": float(_DEFAULT_INSIDE_TOLERANCE),
        "broadphase_round_off_multiplier": float(_ROUND_OFF_MULTIPLIER),
        "specular_order": int(estimator.specular_order),
        "specular_candidate_budget": int(estimator.specular_candidate_budget),
        "specular_suffix_mode": str(estimator.specular_suffix_mode),
        "visible_face_candidates": {
            "class": (
                f"{type(estimator.visible_face_candidates).__module__}."
                f"{type(estimator.visible_face_candidates).__qualname__}"
            ),
            "sample_levels": list(estimator.visible_face_candidates.sample_levels),
            "growth_factor": int(estimator.visible_face_candidates.growth_factor),
            "epsilon_m": float(estimator.visible_face_candidates.epsilon_m),
        },
        "source_quadrature": {
            "class": (
                f"{type(estimator.source_quadrature).__module__}.{type(estimator.source_quadrature).__qualname__}"
            ),
            "strata_levels": list(estimator.source_quadrature.strata_levels),
            "growth_factor": int(estimator.source_quadrature.growth_factor),
        },
        "specular_refinement_relative_tolerance": float(estimator.specular_refinement_relative_tolerance),
        "trace_rays": int(tracer.config.rays),
        "trace_max_bounces": int(tracer.config.max_bounces),
        "trace_frequency_hz": float(tracer.config.frequency_hz),
        "trace_ray_epsilon_m": float(tracer.config.ray_epsilon_m),
    }
    if getattr(estimator, "transport_topology", "hybrid_max_bounces_v1") != "hybrid_max_bounces_v1":
        deterministic_settings["transport_topology"] = str(estimator.transport_topology)
    return {
        "schema": CACHE_SCHEMA,
        "algorithm": CACHE_ALGORITHM,
        "tracer_class": f"{type(tracer).__module__}.{type(tracer).__qualname__}",
        "geometry": geometry,
        "sources": {
            "class": f"{type(estimator.sources).__module__}.{type(estimator.sources).__qualname__}",
            "sites": _array_identity(sites, np.float64),
            "normalized_weights": _array_identity(weights, np.float64),
        },
        "material": {
            "face_class": _optional_array_identity(tracer, "face_class", np.int64),
            "permittivity": _array_identity(tracer.permittivity, np.complex128),
            "rms_height_m": _array_identity(tracer.rms_height_m, np.float64),
            "atlas": atlas,
        },
        "deterministic_settings": deterministic_settings,
    }


def cache_key(identity: Mapping[str, Any]) -> str:
    """Return the SHA256 address of one canonical deterministic identity."""
    return hashlib.sha256(_canonical_json(_json_value(identity))).hexdigest()


def cache_identity(
    common: Mapping[str, Any],
    *,
    kind: str,
    origin: np.ndarray,
    maximum_order: int,
    field_grid: np.ndarray | None = None,
    reflection_support: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Add per-computation content to a seed-independent base identity."""
    point = np.asarray(origin, dtype=np.float64)
    if point.shape != (3,) or np.any(~np.isfinite(point)):
        raise ValueError("origin must be one finite three-vector")
    return {
        **dict(common),
        "kind": kind,
        "origin": _array_identity(point, np.float64),
        "maximum_order": int(maximum_order),
        "field_grid": None if field_grid is None else _array_identity(field_grid, np.float64),
        "reflection_support": None if reflection_support is None else dict(reflection_support),
    }


class _HashingWriter:
    def __init__(self, handle: BinaryIO) -> None:
        self.handle = handle
        self.digest = hashlib.sha256()
        self.size = 0

    def write(self, data: bytes) -> int:
        written = self.handle.write(data)
        if written != len(data):
            raise OSError("short write while creating persistent cache entry")
        self.digest.update(data)
        self.size += written
        return written

    def flush(self) -> None:
        self.handle.flush()


T = TypeVar("T")


@dataclass
class PersistentTransportCache:
    """Content-addressed atomic storage beneath one explicitly selected root."""

    root: Path
    _common_by_estimator: dict[int, tuple[Any, dict[str, Any] | None]] = field(
        default_factory=dict, init=False, repr=False
    )
    _surface_by_transport: dict[int, tuple[Any, dict[str, Any] | None]] = field(
        default_factory=dict, init=False, repr=False
    )

    def __post_init__(self) -> None:
        self.root = Path(self.root)

    def identity(
        self,
        estimator: Any,
        *,
        kind: str,
        origin: np.ndarray,
        maximum_order: int,
        field_grid: np.ndarray | None = None,
        transport: Any = None,
    ) -> dict[str, Any] | None:
        common_entry = self._common_by_estimator.get(id(estimator))
        if common_entry is None or common_entry[0] is not estimator:
            common = _common_identity(estimator)
            self._common_by_estimator[id(estimator)] = (estimator, common)
        else:
            common = common_entry[1]
        if common is None:
            return None
        support = None
        if transport is not None:
            surface_entry = self._surface_by_transport.get(id(transport))
            if surface_entry is None or surface_entry[0] is not transport:
                support = _surface_identity(transport)
                self._surface_by_transport[id(transport)] = (transport, support)
            else:
                support = surface_entry[1]
        return cache_identity(
            common,
            kind=kind,
            origin=origin,
            maximum_order=maximum_order,
            field_grid=field_grid,
            reflection_support=support,
        )

    def direct(
        self,
        identity: Mapping[str, Any] | None,
        compute: Callable[[], DirectCacheValue],
        *,
        field_cells: int | None,
    ) -> tuple[DirectCacheValue, bool]:
        if identity is None:
            return compute(), False
        return self._get_or_compute(
            identity,
            lambda: self._load_direct(identity, field_cells),
            compute,
            self._write_direct,
        )

    def specular(
        self,
        identity: Mapping[str, Any] | None,
        compute: Callable[[], SpecularCacheValue],
    ) -> tuple[SpecularCacheValue, bool]:
        if identity is None:
            return compute(), False
        return self._get_or_compute(
            identity,
            lambda: self._load_specular(identity),
            compute,
            self._write_specular,
        )

    def _get_or_compute(
        self,
        identity: Mapping[str, Any],
        load: Callable[[], T | None],
        compute: Callable[[], T],
        write: Callable[[Mapping[str, Any], T], None],
    ) -> tuple[T, bool]:
        key = cache_key(identity)
        with self._lock(key):
            cached = load()
            if cached is not None:
                return cached, True
            value = compute()
            write(identity, value)
            return value, False

    def _entry_path(self, key: str) -> Path:
        return self.root / CACHE_SCHEMA / key[:2] / f"{key}.stcache"

    @contextmanager
    def _lock(self, key: str):
        lock_dir = self.root / CACHE_SCHEMA / ".locks"
        lock_dir.mkdir(parents=True, exist_ok=True)
        lock_path = lock_dir / f"{key}.lock"
        owner_path = lock_path / "owner.json"
        token = uuid.uuid4().hex
        owner = {
            "hostname": socket.gethostname(),
            "pid": os.getpid(),
            "token": token,
            "created_unix_seconds": time.time(),
        }
        deadline = time.monotonic() + _LOCK_WAIT_SECONDS
        while True:
            try:
                lock_path.mkdir(mode=0o700)
                descriptor = os.open(owner_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                try:
                    content = _canonical_json(owner)
                    if os.write(descriptor, content) != len(content):
                        raise OSError("short write while creating persistent cache lock")
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
                _fsync_directory(lock_dir)
                break
            except FileExistsError:
                if _recover_stale_lock(lock_path, owner_path):
                    continue
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"timed out waiting for persistent cache lock {key}") from None
                time.sleep(_LOCK_POLL_SECONDS)
            except BaseException:
                try:
                    owner_path.unlink()
                except FileNotFoundError:
                    pass
                try:
                    lock_path.rmdir()
                except OSError:
                    pass
                raise
        try:
            yield
        finally:
            try:
                recorded = json.loads(owner_path.read_text(), parse_constant=_reject_constant)
            except (OSError, ValueError, TypeError):
                recorded = None
            if isinstance(recorded, dict) and recorded.get("token") == token:
                try:
                    owner_path.unlink()
                    lock_path.rmdir()
                    _fsync_directory(lock_dir)
                except FileNotFoundError:
                    pass

    def _load_direct(self, identity: Mapping[str, Any], field_cells: int | None) -> DirectCacheValue | None:
        try:
            manifest, arrays = self._read(identity, _DIRECT_KIND)
            if set(manifest["metadata"]) != {"has_field"} or manifest["diagnostics"] is not None:
                raise _CacheMiss("direct metadata members do not match the schema")
            has_field = manifest["metadata"]["has_field"]
            if not isinstance(has_field, bool) or has_field != (field_cells is not None):
                raise _CacheMiss("direct field variant does not match")
            expected_arrays = set(_ARRAY_MEMBERS[_DIRECT_KIND])
            if has_field:
                expected_arrays.update(_FIELD_MEMBERS)
            if set(arrays) != expected_arrays:
                raise _CacheMiss("direct array members do not match the schema")
            direct = arrays["direct.npy"]
            seen = arrays["seen.npy"]
            field_data = None
            if has_field:
                if field_cells is None:
                    raise _CacheMiss("direct field cell count is absent")
                mass = arrays["direct_mass.npy"]
                k_hat = arrays["direct_k_hat.npy"]
                atom_mass = arrays["direct_atom_mass.npy"]
                if mass.shape != (field_cells,):
                    raise _CacheMiss("direct field shape does not match its grid")
                field_data = (mass, k_hat, atom_mass, float(direct[0]), float(seen[0]))
            return _validate_direct(DirectCacheValue(direct, seen, field_data))
        except (OSError, ValueError, TypeError, KeyError, zipfile.BadZipFile, EOFError):
            return None

    def _load_specular(self, identity: Mapping[str, Any]) -> SpecularCacheValue | None:
        try:
            manifest, arrays = self._read(identity, _SPECULAR_KIND)
            metadata = manifest["metadata"]
            expected = {"has_paths", "specular_work", "refinement", "finite_work", "suffix_transport_enabled"}
            if set(metadata) != expected:
                raise _CacheMiss("specular metadata members do not match the schema")
            expected_arrays = set(_ARRAY_MEMBERS[_SPECULAR_KIND]) if metadata["has_paths"] else set()
            if set(arrays) != expected_arrays:
                raise _CacheMiss("specular array members do not match the schema")
            work = _specular_work_from_dict(metadata["specular_work"])
            paths = None
            if metadata["has_paths"]:
                expected_dtypes = {
                    "k_hat.npy": np.dtype(np.float64),
                    "transfer.npy": np.dtype(np.float64),
                    "reflection_point.npy": np.dtype(np.float64),
                    "source_index.npy": np.dtype(np.int64),
                    "endpoint_index.npy": np.dtype(np.int64),
                    "surface_sequence.npy": np.dtype(np.int64),
                    "unfolded_length_m.npy": np.dtype(np.float64),
                }
                if any(arrays[name].dtype != dtype for name, dtype in expected_dtypes.items()):
                    raise _CacheMiss("specular arrays have incompatible dtypes")
                diagnostics = _diagnostics_from_dict(manifest["diagnostics"])
                paths = SpecularPaths(
                    arrays["k_hat.npy"],
                    arrays["transfer.npy"],
                    arrays["reflection_point.npy"],
                    arrays["source_index.npy"],
                    arrays["endpoint_index.npy"],
                    arrays["surface_sequence.npy"],
                    arrays["unfolded_length_m.npy"],
                    diagnostics,
                )
                if (
                    np.any(paths.source_index < 0)
                    or np.any(paths.endpoint_index < 0)
                    or np.any(paths.surface_sequence < 0)
                ):
                    raise _CacheMiss("specular path indices must be nonnegative")
            elif arrays or manifest["diagnostics"] is not None:
                raise _CacheMiss("path-free specular records must not contain path evidence")
            refinement = _zero_measured_timings(_validate_refinement(metadata["refinement"]))
            finite_work = _zero_measured_timings(_validate_finite_work(metadata["finite_work"]))
            suffix = metadata["suffix_transport_enabled"]
            if not isinstance(suffix, bool):
                raise _CacheMiss("suffix transport flag must be boolean")
            return SpecularCacheValue(work, paths, refinement, finite_work, suffix)
        except (OSError, ValueError, TypeError, KeyError, zipfile.BadZipFile, EOFError):
            return None

    def _read(self, identity: Mapping[str, Any], kind: str) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
        key = cache_key(identity)
        path = self._entry_path(key)
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as raw, zipfile.ZipFile(raw, "r") as archive:
            names = archive.namelist()
            if len(names) != len(set(names)) or "manifest.json" not in names:
                raise _CacheMiss("cache archive has duplicate or missing members")
            manifest_info = archive.getinfo("manifest.json")
            if manifest_info.file_size > _MAX_MANIFEST_BYTES or manifest_info.compress_type != zipfile.ZIP_STORED:
                raise _CacheMiss("cache manifest is oversized or compressed")
            manifest = json.loads(archive.read(manifest_info), parse_constant=_reject_constant)
            if not isinstance(manifest, dict):
                raise _CacheMiss("cache manifest must be an object")
            record_digest = manifest.pop("record_sha256", None)
            expected_manifest = {
                "schema",
                "algorithm",
                "kind",
                "key_sha256",
                "identity",
                "arrays",
                "metadata",
                "diagnostics",
            }
            if set(manifest) != expected_manifest:
                raise _CacheMiss("cache manifest members do not match the schema")
            if (
                not isinstance(record_digest, str)
                or hashlib.sha256(_canonical_json(manifest)).hexdigest() != record_digest
            ):
                raise _CacheMiss("cache record digest does not match")
            if (
                manifest.get("schema") != CACHE_SCHEMA
                or manifest.get("algorithm") != CACHE_ALGORITHM
                or manifest.get("kind") != kind
                or manifest.get("key_sha256") != key
                or manifest.get("identity") != _json_value(identity)
            ):
                raise _CacheMiss("cache identity or version does not match")
            descriptors = manifest.get("arrays")
            if not isinstance(descriptors, dict):
                raise _CacheMiss("cache array table is absent")
            metadata = manifest.get("metadata")
            if not isinstance(metadata, dict):
                raise _CacheMiss("cache metadata is absent")
            if kind == _DIRECT_KIND:
                expected_arrays = set(_ARRAY_MEMBERS[kind])
                if metadata.get("has_field") is True:
                    expected_arrays.update(_FIELD_MEMBERS)
            elif kind == _SPECULAR_KIND:
                expected_arrays = set(_ARRAY_MEMBERS[kind]) if metadata.get("has_paths") is True else set()
            else:
                raise _CacheMiss("cache kind is unknown")
            if set(descriptors) != expected_arrays:
                raise _CacheMiss("cache array members do not match the schema")
            _validate_descriptor_layout(kind, descriptors)
            expected_members = set(descriptors) | {"manifest.json"}
            if set(names) != expected_members:
                raise _CacheMiss("cache archive member set does not match its manifest")
            arrays: dict[str, np.ndarray] = {}
            for name, description in descriptors.items():
                if not isinstance(description, dict) or set(description) != {"dtype", "shape", "sha256", "bytes"}:
                    raise _CacheMiss("cache array descriptor is malformed")
                info = archive.getinfo(name)
                if info.compress_type != zipfile.ZIP_STORED or info.file_size != description["bytes"]:
                    raise _CacheMiss("cache array storage does not match its descriptor")
                digest = hashlib.sha256()
                with archive.open(info, "r") as member:
                    for chunk in iter(lambda: member.read(1024 * 1024), b""):
                        digest.update(chunk)
                if digest.hexdigest() != description["sha256"]:
                    raise _CacheMiss("cache array digest does not match")
                with archive.open(info, "r") as member:
                    array = np.load(member, allow_pickle=False)
                if array.dtype.str != description["dtype"] or list(array.shape) != description["shape"]:
                    raise _CacheMiss("cache array dtype or shape does not match")
                arrays[name] = array
            manifest["record_sha256"] = record_digest
            return manifest, arrays

    def _write_direct(self, identity: Mapping[str, Any], value: DirectCacheValue) -> None:
        validated = _validate_direct(value)
        arrays = {"direct.npy": validated.direct, "seen.npy": validated.seen}
        if validated.field_data is not None:
            arrays.update(
                {
                    "direct_mass.npy": validated.field_data[0],
                    "direct_k_hat.npy": validated.field_data[1],
                    "direct_atom_mass.npy": validated.field_data[2],
                }
            )
        self._write(
            identity,
            _DIRECT_KIND,
            arrays,
            {"has_field": validated.field_data is not None},
            None,
        )

    def _write_specular(self, identity: Mapping[str, Any], value: SpecularCacheValue) -> None:
        work = None if value.specular_work is None else _specular_work_from_dict(value.specular_work.as_dict())
        refinement = _validate_refinement(value.refinement)
        finite_work = _validate_finite_work(value.finite_work)
        if not isinstance(value.suffix_transport_enabled, bool):
            raise TypeError("suffix transport cache flag must be boolean")
        arrays: dict[str, np.ndarray] = {}
        diagnostics = None
        if value.paths is not None:
            source_paths = value.paths
            paths = SpecularPaths(
                source_paths.k_hat,
                source_paths.transfer,
                source_paths.reflection_point,
                source_paths.source_index,
                source_paths.endpoint_index,
                source_paths.surface_sequence,
                source_paths.unfolded_length_m,
                source_paths.diagnostics,
            )
            if np.any(paths.source_index < 0) or np.any(paths.endpoint_index < 0) or np.any(paths.surface_sequence < 0):
                raise ValueError("specular path indices must be nonnegative")
            arrays = {
                "k_hat.npy": paths.k_hat,
                "transfer.npy": paths.transfer,
                "reflection_point.npy": paths.reflection_point,
                "source_index.npy": paths.source_index,
                "endpoint_index.npy": paths.endpoint_index,
                "surface_sequence.npy": paths.surface_sequence,
                "unfolded_length_m.npy": paths.unfolded_length_m,
            }
            diagnostics = paths.diagnostics.as_dict()
        self._write(
            identity,
            _SPECULAR_KIND,
            arrays,
            {
                "has_paths": value.paths is not None,
                "specular_work": None if work is None else work.as_dict(),
                "refinement": refinement,
                "finite_work": finite_work,
                "suffix_transport_enabled": bool(value.suffix_transport_enabled),
            },
            diagnostics,
        )

    def _write(
        self,
        identity: Mapping[str, Any],
        kind: str,
        arrays: Mapping[str, np.ndarray],
        metadata: Mapping[str, Any],
        diagnostics: Mapping[str, Any] | None,
    ) -> None:
        key = cache_key(identity)
        path = self._entry_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        stage = path.parent / f".{key}.tmp-{uuid.uuid4().hex}"
        try:
            descriptions: dict[str, Any] = {}
            with zipfile.ZipFile(stage, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
                for name, raw_array in arrays.items():
                    array = np.ascontiguousarray(raw_array)
                    with archive.open(name, "w", force_zip64=True) as member:
                        writer = _HashingWriter(member)
                        np.lib.format.write_array(writer, array, allow_pickle=False)
                    descriptions[name] = {
                        "dtype": array.dtype.str,
                        "shape": list(array.shape),
                        "sha256": writer.digest.hexdigest(),
                        "bytes": writer.size,
                    }
                manifest = {
                    "schema": CACHE_SCHEMA,
                    "algorithm": CACHE_ALGORITHM,
                    "kind": kind,
                    "key_sha256": key,
                    "identity": _json_value(identity),
                    "arrays": descriptions,
                    "metadata": _json_value(metadata),
                    "diagnostics": _json_value(diagnostics),
                }
                manifest["record_sha256"] = hashlib.sha256(_canonical_json(manifest)).hexdigest()
                archive.writestr("manifest.json", _canonical_json(manifest), compress_type=zipfile.ZIP_STORED)
            with stage.open("rb") as handle:
                os.fsync(handle.fileno())
            os.replace(stage, path)
            _fsync_directory(path.parent)
        finally:
            try:
                stage.unlink()
            except FileNotFoundError:
                pass


def _validate_direct(value: DirectCacheValue) -> DirectCacheValue:
    direct = np.asarray(value.direct)
    seen = np.asarray(value.seen)
    if direct.dtype != np.dtype(np.float64) or seen.dtype != np.dtype(np.float64):
        raise ValueError("direct cache scalars must use float64")
    if direct.shape != (1,) or seen.shape != (1,):
        raise ValueError("direct cache scalars must each have one row")
    if np.any(~np.isfinite(direct)) or np.any(direct < 0.0):
        raise ValueError("direct transfer must be finite and nonnegative")
    if np.any(~np.isfinite(seen)) or np.any(seen < 0.0) or np.any(seen > 1.0 + 1.0e-12):
        raise ValueError("direct visible fraction must lie in [0, 1]")
    if value.field_data is None:
        return DirectCacheValue(direct, seen, None)
    mass, k_hat, atom_mass, direct_value, seen_value = value.field_data
    mass = np.asarray(mass)
    k_hat = np.asarray(k_hat)
    atom_mass = np.asarray(atom_mass)
    if any(array.dtype != np.dtype(np.float64) for array in (mass, k_hat, atom_mass)):
        raise ValueError("direct field cache arrays must use float64")
    if mass.ndim != 1 or k_hat.ndim != 2 or k_hat.shape[1:] != (3,) or atom_mass.shape != (k_hat.shape[0],):
        raise ValueError("direct field cache arrays have incompatible shapes")
    if any(np.any(~np.isfinite(array)) for array in (mass, k_hat, atom_mass)):
        raise ValueError("direct field cache arrays must be finite")
    if np.any(mass < 0.0) or np.any(atom_mass < 0.0):
        raise ValueError("direct field masses must be nonnegative")
    if k_hat.size and not np.allclose(np.linalg.norm(k_hat, axis=1), 1.0, rtol=1.0e-10, atol=1.0e-10):
        raise ValueError("direct cache directions must be unit length")
    if direct_value != float(direct[0]) or seen_value != float(seen[0]):
        raise ValueError("direct field scalar bookkeeping does not match")
    if not np.isclose(np.sum(atom_mass, dtype=np.float64), direct[0], rtol=2.0e-12, atol=1.0e-15):
        raise ValueError("direct atom masses do not sum to the direct transfer")
    if not np.isclose(np.sum(mass, dtype=np.float64), direct[0], rtol=2.0e-12, atol=1.0e-15):
        raise ValueError("direct field masses do not sum to the direct transfer")
    return DirectCacheValue(direct, seen, (mass, k_hat, atom_mass, direct_value, seen_value))


def _validate_descriptor_layout(kind: str, descriptors: Mapping[str, Any]) -> None:
    expected_dtype = {
        "direct.npy": np.dtype(np.float64),
        "seen.npy": np.dtype(np.float64),
        "direct_mass.npy": np.dtype(np.float64),
        "direct_k_hat.npy": np.dtype(np.float64),
        "direct_atom_mass.npy": np.dtype(np.float64),
        "k_hat.npy": np.dtype(np.float64),
        "transfer.npy": np.dtype(np.float64),
        "reflection_point.npy": np.dtype(np.float64),
        "source_index.npy": np.dtype(np.int64),
        "endpoint_index.npy": np.dtype(np.int64),
        "surface_sequence.npy": np.dtype(np.int64),
        "unfolded_length_m.npy": np.dtype(np.float64),
    }
    for name, description in descriptors.items():
        if not isinstance(description, dict) or set(description) != {"dtype", "shape", "sha256", "bytes"}:
            raise _CacheMiss("cache array descriptor is malformed")
        shape = description["shape"]
        if (
            description["dtype"] != expected_dtype[name].str
            or not isinstance(shape, list)
            or any(not isinstance(size, int) or isinstance(size, bool) or size < 0 for size in shape)
            or not isinstance(description["bytes"], int)
            or isinstance(description["bytes"], bool)
            or description["bytes"] < 0
            or not isinstance(description["sha256"], str)
            or len(description["sha256"]) != 64
            or any(character not in "0123456789abcdef" for character in description["sha256"])
        ):
            raise _CacheMiss("cache array descriptor dtype, shape, size, or digest is invalid")
        data_bytes = math.prod(shape) * expected_dtype[name].itemsize
        if description["bytes"] < data_bytes or description["bytes"] > data_bytes + 4096:
            raise _CacheMiss("cache array member size is inconsistent with its shape")

    if kind == _DIRECT_KIND:
        if descriptors["direct.npy"]["shape"] != [1] or descriptors["seen.npy"]["shape"] != [1]:
            raise _CacheMiss("direct scalar array shapes are invalid")
        if "direct_mass.npy" in descriptors:
            atom_count = descriptors["direct_atom_mass.npy"]["shape"]
            if (
                len(descriptors["direct_mass.npy"]["shape"]) != 1
                or len(atom_count) != 1
                or descriptors["direct_k_hat.npy"]["shape"] != [atom_count[0], 3]
            ):
                raise _CacheMiss("direct field array shapes are invalid")
        return
    count_shape = descriptors.get("transfer.npy", {}).get("shape")
    if count_shape is None:
        return
    if len(count_shape) != 1:
        raise _CacheMiss("specular transfer shape is invalid")
    count = count_shape[0]
    expected_shapes = {
        "k_hat.npy": [count, 3],
        "transfer.npy": [count],
        "reflection_point.npy": [count, 3],
        "source_index.npy": [count],
        "endpoint_index.npy": [count],
        "surface_sequence.npy": [count, 1],
        "unfolded_length_m.npy": [count],
    }
    if any(descriptors[name]["shape"] != shape for name, shape in expected_shapes.items()):
        raise _CacheMiss("specular array shapes are invalid")


def _diagnostics_from_dict(value: Any) -> SpecularDiagnostics:
    if not isinstance(value, dict):
        raise _CacheMiss("specular diagnostics are absent")
    expected = {item.name for item in dataclasses.fields(SpecularDiagnostics)}
    if set(value) != expected:
        raise _CacheMiss("specular diagnostic members do not match")
    normalized = _zero_measured_timings(value)
    return SpecularDiagnostics(**normalized)


def _specular_work_from_dict(value: Any) -> SpecularWorkEstimate | None:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != {item.name for item in dataclasses.fields(SpecularWorkEstimate)}:
        raise _CacheMiss("specular work members do not match")
    work = SpecularWorkEstimate(**value)
    expected = SpecularWorkEstimate.exact_order_one(
        faces=work.faces,
        sources=work.sources,
        rays=work.rays,
        samples=work.samples,
        max_bounces=work.max_bounces,
        candidate_budget=work.candidate_budget,
        support_complete=work.support_complete,
    )
    if work != expected:
        raise _CacheMiss("specular work invariants do not match")
    return work


def _validate_refinement(value: Any) -> list[dict[str, Any]]:
    normalized = _json_value(value)
    if not isinstance(normalized, list) or any(not isinstance(row, dict) for row in normalized):
        raise _CacheMiss("specular refinement must be a list of objects")
    for index, row in enumerate(normalized):
        if set(row) != _REFINEMENT_FIELDS:
            raise _CacheMiss("specular refinement members do not match the schema")
        if row.get("step") != index:
            raise _CacheMiss("specular refinement steps must be consecutive")
        for name in (
            "step",
            "face_level",
            "source_level",
            "angular_samples",
            "cumulative_visibility_rays",
            "candidates",
            "cumulative_candidates",
            "executed_candidates",
            "avoided_candidates",
            "cumulative_executed_candidates",
            "cumulative_avoided_candidates",
            "accepted",
            "selected_faces",
            "requested_strata",
            "selected_sources",
        ):
            item = row.get(name)
            if not isinstance(item, int) or isinstance(item, bool) or item < 0:
                raise _CacheMiss(f"specular refinement {name} must be nonnegative")
        transfer = row.get("transfer")
        if not isinstance(transfer, (int, float)) or isinstance(transfer, bool) or transfer < 0.0:
            raise _CacheMiss("specular refinement transfer must be nonnegative")
        if row["axis_refined"] not in ("initial", "receiver_faces", "source_quadrature", "crossed_corner"):
            raise _CacheMiss("specular refinement axis is unknown")
        for name in (
            "candidate_support_complete",
            "source_support_complete",
            "finite_resolution_support_incomplete",
            "face_axis_converged",
            "source_axis_converged",
            "numerically_converged",
        ):
            if not isinstance(row[name], bool):
                raise _CacheMiss(f"specular refinement {name} must be boolean")
        for name in (
            "seconds",
            "executed_seconds",
            "cumulative_executed_seconds",
            "logical_solution_seconds",
            "reused_block_seconds",
            "relative_tolerance",
        ):
            if not isinstance(row[name], (int, float)) or isinstance(row[name], bool) or row[name] < 0.0:
                raise _CacheMiss(f"specular refinement {name} must be nonnegative")
        for name in (
            "absolute_change_from_previous_face_level",
            "relative_change_from_previous_face_level",
            "absolute_change_from_previous_source_level",
            "relative_change_from_previous_source_level",
        ):
            item = row[name]
            if item is not None and (not isinstance(item, (int, float)) or isinstance(item, bool) or item < 0.0):
                raise _CacheMiss(f"specular refinement {name} must be nonnegative or null")
    return normalized


def _validate_finite_work(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    normalized = _json_value(value)
    if not isinstance(normalized, dict):
        raise _CacheMiss("finite specular work must be an object")
    fields = set(normalized)
    if not _FINITE_WORK_REQUIRED_FIELDS.issubset(fields):
        raise _CacheMiss("finite specular work lacks required evidence")
    if not fields.issubset(_FINITE_WORK_REQUIRED_FIELDS | _FINITE_WORK_OPTIONAL_FIELDS):
        raise _CacheMiss("finite specular work contains unknown evidence")
    if normalized["method"] not in _FINITE_WORK_METHODS:
        raise _CacheMiss("finite specular work method is unknown")
    if normalized["stop_reason"] not in _FINITE_WORK_STOP_REASONS:
        raise _CacheMiss("finite specular work stop reason is unknown")
    budget = normalized["candidate_budget"]
    if not isinstance(budget, int) or isinstance(budget, bool) or budget < 1:
        raise _CacheMiss("finite specular candidate budget must be positive")
    tolerance = normalized["relative_tolerance"]
    if not isinstance(tolerance, (int, float)) or isinstance(tolerance, bool) or not 0.0 < tolerance < 1.0:
        raise _CacheMiss("finite specular tolerance must lie in (0, 1)")
    for name in ("numerically_converged", "support_complete", "enabled", "mixed_specular_suffix_enabled"):
        if name not in normalized:
            continue
        if not isinstance(normalized[name], bool):
            raise _CacheMiss(f"finite specular {name} must be boolean")
    integer_fields = (
        "candidate_work_used",
        "executed_candidate_work_used",
        "avoided_candidate_work",
        "total_candidates_upper_bound",
        "visibility_rays_used",
        "refinement_work_used",
        "estimate_count",
        "budget_remaining",
    )
    for name in integer_fields:
        if name in normalized:
            _validate_nonnegative_integer(normalized[name], f"finite specular {name}")
    if "executed_candidate_seconds" in normalized:
        seconds = normalized["executed_candidate_seconds"]
        if not isinstance(seconds, (int, float)) or isinstance(seconds, bool) or seconds < 0.0:
            raise _CacheMiss("finite specular executed_candidate_seconds must be nonnegative")
    if (
        "mixed_specular_suffix_method" in normalized
        and normalized["mixed_specular_suffix_method"] != "full_support_sampled_one_reflection"
    ):
        raise _CacheMiss("finite specular mixed suffix method is unknown")
    for name in ("face_level_counts", "source_strata_levels"):
        if name not in normalized:
            continue
        levels = normalized[name]
        if not isinstance(levels, list):
            raise _CacheMiss(f"finite specular {name} must be a list")
        for level in levels:
            _validate_nonnegative_integer(level, f"finite specular {name} item")
        if levels != sorted(set(levels)):
            raise _CacheMiss(f"finite specular {name} must be sorted and unique")
    if "blocked_next_cycle" in normalized:
        _validate_blocked_next_cycle(normalized["blocked_next_cycle"])
    _validate_finite_work_relations(normalized)
    return normalized


def _validate_nonnegative_integer(value: Any, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise _CacheMiss(f"{label} must be a nonnegative integer")


def _validate_blocked_next_cycle(value: Any) -> None:
    if value is None:
        return
    required = {"angular_samples", "projected_refinement_work"}
    allowed = required | {"selected_faces", "requested_strata", "projected_image_candidates"}
    if not isinstance(value, dict) or not required.issubset(value) or not set(value).issubset(allowed):
        raise _CacheMiss("finite specular blocked-next-cycle evidence is malformed")
    for name, item in value.items():
        _validate_nonnegative_integer(item, f"finite specular blocked_next_cycle.{name}")


def _validate_finite_work_relations(value: Mapping[str, Any]) -> None:
    candidate_work = value.get("candidate_work_used")
    executed_work = value.get("executed_candidate_work_used")
    avoided_work = value.get("avoided_candidate_work")
    if candidate_work is not None and candidate_work > value["candidate_budget"]:
        raise _CacheMiss("finite specular candidate work exceeds its budget")
    if executed_work is not None and (candidate_work is None or executed_work > candidate_work):
        raise _CacheMiss("finite specular executed work exceeds candidate work")
    if avoided_work is not None and (
        candidate_work is None or executed_work is None or avoided_work != candidate_work - executed_work
    ):
        raise _CacheMiss("finite specular avoided work does not reconcile")
    visibility_rays = value.get("visibility_rays_used")
    refinement_work = value.get("refinement_work_used")
    if refinement_work is not None and (
        candidate_work is None or visibility_rays is None or refinement_work != candidate_work + visibility_rays
    ):
        raise _CacheMiss("finite specular refinement work does not reconcile")
    if "budget_remaining" in value and (
        refinement_work is None or value["budget_remaining"] != value["candidate_budget"] - refinement_work
    ):
        raise _CacheMiss("finite specular remaining budget does not reconcile")
    upper_bound = value.get("total_candidates_upper_bound")
    if upper_bound is not None and candidate_work is not None and upper_bound < candidate_work:
        raise _CacheMiss("finite specular candidate upper bound is too small")


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _zero_measured_timings(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: 0.0 if key == "seconds" or key.endswith("_seconds") else _zero_measured_timings(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_zero_measured_timings(item) for item in value]
    return value


def _pid_is_live(pid: Any) -> bool:
    if not isinstance(pid, int) or isinstance(pid, bool) or pid < 1:
        return False
    if os.name == "nt":
        # Python's Windows os.kill implementation is not a harmless existence
        # probe for every signal value. Age-based recovery remains portable.
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return True
    return True


def _recover_stale_lock(lock_path: Path, owner_path: Path) -> bool:
    try:
        owner = json.loads(owner_path.read_text(), parse_constant=_reject_constant)
        age = time.time() - float(owner["created_unix_seconds"])
        same_host_dead = owner.get("hostname") == socket.gethostname() and not _pid_is_live(owner.get("pid"))
        stale = same_host_dead or age > _LOCK_STALE_SECONDS
    except (OSError, ValueError, TypeError, KeyError):
        try:
            stale = time.time() - lock_path.stat().st_mtime > _LOCK_INCOMPLETE_SECONDS
        except OSError:
            return True
    if not stale:
        return False
    try:
        owner_path.unlink()
    except FileNotFoundError:
        pass
    try:
        lock_path.rmdir()
    except FileNotFoundError:
        return True
    except OSError:
        return False
    return True
