"""Append-only, restart-safe storage for fixed-walk exposure replicas.

The production CDF checkpoint is large because it retains one body surface
field for every completed replica.  Rewriting that growing array after every
replica causes quadratic I/O.  :class:`CheckpointStore` writes one compressed
NPZ shard per replica and commits a small JSON index only after the shard is
sealed.  An interrupted shard which never reached the index is ignored on the
next run.  An indexed shard is always checked before it is used.

The store is deliberately independent of the tracing and analysis code.  The
``ReplicaPayload`` and ``CheckpointPrefix`` field names mirror the existing
``CampaignCheckpoint`` so a caller can convert between them without changing
the numerical code.  Every numerical value is required to be float64.  No
cast or lossy conversion is performed while loading or exporting.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import zipfile
from dataclasses import dataclass
from typing import Any, ClassVar

import numpy as np


SCHEMA = "fixed-walk-cdf-checkpoint-shards-v1"
CONSOLIDATED_SCHEMA = "fixed-walk-cdf-checkpoint-v3"
_INDEX_NAME = "index.json"
_SHARD_PREFIX = "replica-"
_SHARD_SUFFIX = ".npz"
_ARRAY_NAMES = (
    "chi",
    "chi_direct",
    "body_peak_rooftop",
    "body_mean_rooftop",
    "body_sab_rooftop",
    "trace_seconds",
    "rho",
)
_SHARD_NAMES = frozenset({"schema", "replica", "base_seed", *_ARRAY_NAMES})


class CheckpointStoreError(ValueError):
    """Base class for invalid, incompatible, or corrupt stores."""


class CheckpointIdentityError(CheckpointStoreError):
    """The store belongs to a different scientific campaign."""


class CheckpointCorruptionError(CheckpointStoreError):
    """A committed index or shard failed integrity checks."""


class CheckpointOrderError(CheckpointStoreError):
    """A replica was appended out of order or with the wrong seed."""


def array_sha256(array: np.ndarray) -> str:
    """Hash dtype, shape, and exact contiguous bytes of an array."""
    value = np.ascontiguousarray(array)
    digest = hashlib.sha256()
    digest.update(value.dtype.str.encode("ascii"))
    digest.update(str(value.shape).encode("ascii"))
    digest.update(value.tobytes())
    return digest.hexdigest()


def file_sha256(path: pathlib.Path) -> str:
    """Hash a file without loading it all into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_json(path: pathlib.Path, document: dict[str, Any]) -> None:
    """Publish JSON with a same-directory temporary file and fsync."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as stream:
            json.dump(document, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def _fsync_directory(path: pathlib.Path) -> None:
    """Best-effort directory fsync on platforms that expose one."""
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise CheckpointStoreError(f"{label} must be a nonempty string")
    return value


def _read_scalar(artifact: np.lib.npyio.NpzFile, name: str, *, kind: type) -> Any:
    value = np.asarray(artifact[name])
    if value.shape != ():
        raise CheckpointCorruptionError(f"shard field {name!r} is not scalar")
    item = value.item()
    if not isinstance(item, kind):
        raise CheckpointCorruptionError(f"shard field {name!r} has the wrong type")
    return item


@dataclass(frozen=True)
class CheckpointSpec:
    """Immutable campaign identity and shape information for a store."""

    identity_sha256: str
    standpoint_array_sha256: str
    tissue_database_sha256: str
    model_names: tuple[str, ...]
    planned_seeds: tuple[int, ...]
    surface_elements: int
    local_grid: np.ndarray
    solid_angle: float
    schema: ClassVar[str] = SCHEMA

    def __post_init__(self) -> None:
        _text(self.identity_sha256, "identity_sha256")
        _text(self.standpoint_array_sha256, "standpoint_array_sha256")
        _text(self.tissue_database_sha256, "tissue_database_sha256")
        if not self.model_names or len(set(self.model_names)) != len(self.model_names):
            raise CheckpointStoreError("model_names must be nonempty and unique")
        if any(not isinstance(name, str) or not name for name in self.model_names):
            raise CheckpointStoreError("model_names must contain nonempty strings")
        if not self.planned_seeds:
            raise CheckpointStoreError("planned_seeds must be nonempty")
        if any(not isinstance(seed, (int, np.integer)) or int(seed) < 0 for seed in self.planned_seeds):
            raise CheckpointStoreError("planned_seeds must contain nonnegative integers")
        if len(set(int(seed) for seed in self.planned_seeds)) != len(self.planned_seeds):
            raise CheckpointStoreError("planned_seeds must be unique")
        if not isinstance(self.surface_elements, (int, np.integer)) or int(self.surface_elements) < 1:
            raise CheckpointStoreError("surface_elements must be a positive integer")
        grid = np.asarray(self.local_grid)
        if grid.dtype != np.dtype(np.float64) or grid.ndim != 2 or grid.shape[1] != 3:
            raise CheckpointStoreError("local_grid must be a finite float64 array with shape (cells, 3)")
        if grid.shape[0] < 1 or not np.all(np.isfinite(grid)):
            raise CheckpointStoreError("local_grid must contain finite cells")
        if not np.isfinite(self.solid_angle) or self.solid_angle <= 0.0:
            raise CheckpointStoreError("solid_angle must be finite and positive")
        grid_copy = np.array(grid, dtype=np.float64, copy=True)
        grid_copy.setflags(write=False)
        object.__setattr__(self, "model_names", tuple(self.model_names))
        object.__setattr__(self, "planned_seeds", tuple(int(seed) for seed in self.planned_seeds))
        object.__setattr__(self, "surface_elements", int(self.surface_elements))
        object.__setattr__(self, "local_grid", grid_copy)
        object.__setattr__(self, "solid_angle", float(self.solid_angle))

    @property
    def points(self) -> int:
        """Number of standpoints in each replica."""
        return int(getattr(self, "_points", 0))

    @property
    def cells(self) -> int:
        """Number of local angular cells."""
        return int(self.local_grid.shape[0])

    @property
    def local_grid_sha256(self) -> str:
        return array_sha256(self.local_grid)

    def with_points(self, points: int) -> CheckpointSpec:
        """Return a spec carrying the first shard's standpoint count."""
        if points < 1:
            raise CheckpointStoreError("points must be positive")
        clone = object.__new__(CheckpointSpec)
        for field in (
            "identity_sha256",
            "standpoint_array_sha256",
            "tissue_database_sha256",
            "model_names",
            "planned_seeds",
            "surface_elements",
            "local_grid",
            "solid_angle",
        ):
            object.__setattr__(clone, field, getattr(self, field))
        object.__setattr__(clone, "_points", int(points))
        return clone


@dataclass(frozen=True)
class ReplicaPayload:
    """One complete replica, ready to be atomically sealed as a shard."""

    base_seed: int
    chi: np.ndarray
    chi_direct: np.ndarray
    body_peak_rooftop: np.ndarray
    body_mean_rooftop: np.ndarray
    body_sab_rooftop: np.ndarray
    trace_seconds: np.ndarray
    rho: np.ndarray

    def arrays(self) -> dict[str, np.ndarray]:
        return {name: np.asarray(getattr(self, name)) for name in _ARRAY_NAMES}


@dataclass(frozen=True)
class CheckpointPrefix:
    """Exact committed prefix loaded from a :class:`CheckpointStore`."""

    base_seeds: np.ndarray
    chi: np.ndarray
    chi_direct: np.ndarray
    body_peak_rooftop: np.ndarray
    body_mean_rooftop: np.ndarray
    body_sab_rooftop: np.ndarray
    trace_seconds: np.ndarray
    rho_sum: np.ndarray
    local_grid: np.ndarray
    solid_angle: float

    @property
    def replicas(self) -> int:
        return int(self.base_seeds.size)


class CheckpointStore:
    """Append complete replica shards and read an integrity-checked prefix."""

    def __init__(self, root: str | pathlib.Path, spec: CheckpointSpec) -> None:
        self.root = pathlib.Path(root)
        self.spec = spec
        self.index_path = self.root / _INDEX_NAME
        self.root.mkdir(parents=True, exist_ok=True)
        if self.index_path.is_file():
            self._index = self._read_index()
            try:
                self._validate_index_identity(self._index)
                self._validate_committed_entries(self._index)
            except CheckpointStoreError as exc:
                raise type(exc)(f"{self.index_path}: {exc}") from exc
        elif self.index_path.exists():
            raise CheckpointCorruptionError(f"checkpoint index is not a regular file: {self.index_path}")
        else:
            self._index = self._empty_index()
            _atomic_json(self.index_path, self._index)

    def _empty_index(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "identity_sha256": self.spec.identity_sha256,
            "standpoint_array_sha256": self.spec.standpoint_array_sha256,
            "tissue_database_sha256": self.spec.tissue_database_sha256,
            "model_names": list(self.spec.model_names),
            "planned_seeds": list(self.spec.planned_seeds),
            "surface_elements": self.spec.surface_elements,
            "local_grid": self.spec.local_grid.tolist(),
            "local_grid_dtype": self.spec.local_grid.dtype.str,
            "local_grid_sha256": self.spec.local_grid_sha256,
            "solid_angle": self.spec.solid_angle,
            "entries": [],
        }

    def _read_index(self) -> dict[str, Any]:
        try:
            document = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CheckpointCorruptionError(f"cannot read checkpoint index {self.index_path}: {exc}") from exc
        if not isinstance(document, dict):
            raise CheckpointCorruptionError("checkpoint index must be a JSON object")
        return document

    def _validate_index_identity(self, index: dict[str, Any]) -> None:
        required = {
            "schema",
            "identity_sha256",
            "standpoint_array_sha256",
            "tissue_database_sha256",
            "model_names",
            "planned_seeds",
            "surface_elements",
            "local_grid",
            "local_grid_dtype",
            "local_grid_sha256",
            "solid_angle",
            "entries",
        }
        missing = required - set(index)
        if missing:
            raise CheckpointCorruptionError(f"checkpoint index is missing {', '.join(sorted(missing))}")
        if not isinstance(index["schema"], str):
            raise CheckpointCorruptionError("checkpoint schema must be a string")
        if index["schema"] != SCHEMA:
            raise CheckpointIdentityError(f"checkpoint schema is {index['schema']!r}, expected {SCHEMA!r}")
        identity_fields = ("identity_sha256", "standpoint_array_sha256", "tissue_database_sha256")
        if any(not isinstance(index[name], str) or not index[name] for name in identity_fields):
            raise CheckpointCorruptionError("checkpoint index identity fields must be nonempty strings")
        for name in ("identity_sha256", "standpoint_array_sha256", "tissue_database_sha256"):
            if index[name] != getattr(self.spec, name):
                raise CheckpointIdentityError(f"checkpoint {name} does not match the requested campaign")
        model_names = index["model_names"]
        if (
            not isinstance(model_names, list)
            or not model_names
            or any(not isinstance(name, str) or not name for name in model_names)
        ):
            raise CheckpointCorruptionError("checkpoint model_names must be a nonempty string list")
        if tuple(model_names) != self.spec.model_names:
            raise CheckpointIdentityError("checkpoint model_names do not match the requested campaign")
        planned_seeds = index["planned_seeds"]
        if (
            not isinstance(planned_seeds, list)
            or not planned_seeds
            or any(not isinstance(seed, int) or isinstance(seed, bool) for seed in planned_seeds)
        ):
            raise CheckpointCorruptionError("checkpoint planned_seeds must be a nonempty integer list")
        if tuple(planned_seeds) != self.spec.planned_seeds:
            raise CheckpointIdentityError("checkpoint planned_seeds do not match the requested campaign")
        surface_elements = index["surface_elements"]
        if not isinstance(surface_elements, int) or isinstance(surface_elements, bool) or surface_elements < 1:
            raise CheckpointCorruptionError("checkpoint surface_elements must be a positive integer")
        if surface_elements != self.spec.surface_elements:
            raise CheckpointIdentityError("checkpoint surface element count does not match the requested campaign")
        if not isinstance(index["local_grid_dtype"], str):
            raise CheckpointCorruptionError("checkpoint local_grid_dtype must be a string")
        if index["local_grid_dtype"] != np.dtype(np.float64).str:
            raise CheckpointIdentityError("checkpoint local_grid dtype does not match the requested campaign")
        try:
            grid = np.asarray(index["local_grid"], dtype=np.float64)
        except (TypeError, ValueError) as exc:
            raise CheckpointCorruptionError("checkpoint local_grid is not a numeric array") from exc
        if grid.ndim != 2 or grid.shape != self.spec.local_grid.shape or not np.all(np.isfinite(grid)):
            raise CheckpointCorruptionError("checkpoint local_grid has invalid values or shape")
        if not isinstance(index["local_grid_sha256"], str) or not index["local_grid_sha256"]:
            raise CheckpointCorruptionError("checkpoint local_grid_sha256 must be a nonempty string")
        if not np.array_equal(grid, self.spec.local_grid) or index["local_grid_sha256"] != self.spec.local_grid_sha256:
            raise CheckpointIdentityError("checkpoint local_grid does not match the requested campaign")
        if not isinstance(index["solid_angle"], (int, float)) or isinstance(index["solid_angle"], bool):
            raise CheckpointCorruptionError("checkpoint solid_angle is not numeric")
        solid_angle = float(index["solid_angle"])
        if not np.isfinite(solid_angle) or solid_angle <= 0.0:
            raise CheckpointCorruptionError("checkpoint solid_angle must be finite and positive")
        if solid_angle != self.spec.solid_angle:
            raise CheckpointIdentityError("checkpoint solid_angle does not match the requested campaign")
        if not isinstance(index["entries"], list):
            raise CheckpointCorruptionError("checkpoint index entries must be a list")

    def _validate_committed_entries(self, index: dict[str, Any]) -> None:
        entries = index["entries"]
        points: int | None = None
        for position, entry in enumerate(entries):
            if not isinstance(entry, dict):
                raise CheckpointCorruptionError(f"checkpoint entry {position} is not an object")
            if entry.get("replica") != position:
                raise CheckpointOrderError(f"checkpoint entry {position} is not sequential")
            if position >= len(self.spec.planned_seeds) or entry.get("base_seed") != self.spec.planned_seeds[position]:
                raise CheckpointOrderError(f"checkpoint entry {position} has the wrong base seed")
            payload = self._validate_entry(entry, position, points)
            if points is None:
                points = int(payload.chi.shape[0])
                object.__setattr__(self.spec, "_points", points)
            elif payload.body_sab_rooftop.shape[1] != self.spec.surface_elements:
                raise CheckpointCorruptionError("checkpoint shards change surface element count")

    def _validate_entry(
        self,
        entry: dict[str, Any],
        position: int,
        points: int | None = None,
    ) -> ReplicaPayload:
        required = {"replica", "base_seed", "shard", "shard_sha256", "bytes", "arrays"}
        missing = required - set(entry)
        if missing:
            raise CheckpointCorruptionError(f"checkpoint entry {position} is missing {', '.join(sorted(missing))}")
        shard = self.root / str(entry["shard"])
        expected_name = f"{_SHARD_PREFIX}{position:06d}{_SHARD_SUFFIX}"
        if shard.name != expected_name or not shard.is_file():
            raise CheckpointCorruptionError(f"checkpoint shard for replica {position} is missing: {shard}")
        if int(entry["bytes"]) != shard.stat().st_size or entry["shard_sha256"] != file_sha256(shard):
            raise CheckpointCorruptionError(f"checkpoint shard for replica {position} failed its file hash")
        arrays = entry["arrays"]
        if not isinstance(arrays, dict) or set(arrays) != set(_ARRAY_NAMES):
            raise CheckpointCorruptionError(f"checkpoint shard {position} has an invalid array hash record")
        payload = self._read_shard(shard, position, points)
        for name, value in payload.arrays().items():
            if arrays[name] != array_sha256(value):
                raise CheckpointCorruptionError(f"checkpoint shard {position} array {name!r} failed its hash")
        return payload

    @property
    def replicas(self) -> int:
        """Number of committed replicas."""
        return len(self._index["entries"])

    @property
    def committed_seeds(self) -> tuple[int, ...]:
        return tuple(int(entry["base_seed"]) for entry in self._index["entries"])

    def append(self, replica: int, payload: ReplicaPayload) -> None:
        """Atomically append one sequential replica.

        The shard is published before the index.  If the process stops between
        those two operations, the unindexed shard is harmless and the next
        append overwrites it.
        """
        if not isinstance(replica, (int, np.integer)):
            raise CheckpointOrderError("replica must be an integer")
        replica = int(replica)
        if replica != self.replicas:
            raise CheckpointOrderError(f"expected replica {self.replicas}, received {replica}")
        if replica >= len(self.spec.planned_seeds):
            raise CheckpointOrderError("all planned replicas are already committed")
        expected_seed = self.spec.planned_seeds[replica]
        if not isinstance(payload, ReplicaPayload):
            raise CheckpointStoreError("payload must be a ReplicaPayload")
        if not isinstance(payload.base_seed, (int, np.integer)) or isinstance(payload.base_seed, bool):
            raise CheckpointStoreError("base_seed must be an integer")
        if int(payload.base_seed) != expected_seed:
            raise CheckpointOrderError(f"replica {replica} requires base seed {expected_seed}")
        checked = self._validate_payload(payload)
        if self.spec.points == 0:
            object.__setattr__(self.spec, "_points", int(checked.chi.shape[0]))
        elif checked.chi.shape[0] != self.spec.points:
            raise CheckpointOrderError("replica changes the standpoint count")
        elif checked.body_sab_rooftop.shape[1] != self.spec.surface_elements:
            raise CheckpointOrderError("replica changes the surface element count")
        shard_name = f"{_SHARD_PREFIX}{replica:06d}{_SHARD_SUFFIX}"
        shard_path = self.root / shard_name
        temporary = self.root / f".{shard_name}.{os.getpid()}.tmp"
        try:
            with temporary.open("wb") as stream:
                np.savez_compressed(
                    stream,
                    schema=np.asarray(SCHEMA),
                    replica=np.asarray(replica, dtype=np.int64),
                    base_seed=np.asarray(expected_seed, dtype=np.int64),
                    **checked.arrays(),
                )
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, shard_path)
            _fsync_directory(self.root)
            entry = {
                "replica": replica,
                "base_seed": expected_seed,
                "shard": shard_name,
                "shard_sha256": file_sha256(shard_path),
                "bytes": shard_path.stat().st_size,
                "arrays": {name: array_sha256(value) for name, value in checked.arrays().items()},
            }
            updated = dict(self._index)
            updated["entries"] = [*self._index["entries"], entry]
            _atomic_json(self.index_path, updated)
            self._index = updated
        finally:
            temporary.unlink(missing_ok=True)

    def _validate_payload(self, payload: ReplicaPayload) -> ReplicaPayload:
        if not isinstance(payload, ReplicaPayload):
            raise CheckpointStoreError("payload must be a ReplicaPayload")
        if not isinstance(payload.base_seed, (int, np.integer)) or isinstance(payload.base_seed, bool):
            raise CheckpointStoreError("base_seed must be an integer")
        arrays = payload.arrays()
        for name, value in arrays.items():
            if value.dtype != np.dtype(np.float64):
                raise CheckpointStoreError(f"{name} must be float64, not {value.dtype}")
            if not np.all(np.isfinite(value)):
                raise CheckpointStoreError(f"{name} contains non-finite values")
        chi = arrays["chi"]
        if chi.ndim != 2 or chi.shape[1] != len(self.spec.model_names) or np.any(chi <= 0.0):
            raise CheckpointStoreError("chi must have shape (points, models) and be positive")
        points = int(chi.shape[0])
        if points < 1:
            raise CheckpointStoreError("replica arrays must contain at least one standpoint")
        if arrays["chi_direct"].shape != chi.shape:
            raise CheckpointStoreError("chi_direct shape does not match chi")
        if arrays["body_peak_rooftop"].shape != (points,):
            raise CheckpointStoreError("body_peak_rooftop shape does not match chi")
        if arrays["body_mean_rooftop"].shape != (points,):
            raise CheckpointStoreError("body_mean_rooftop shape does not match chi")
        sab = arrays["body_sab_rooftop"]
        if sab.ndim != 2 or sab.shape != (points, self.spec.surface_elements):
            raise CheckpointStoreError("body_sab_rooftop shape does not match (points, surface_elements)")
        if arrays["trace_seconds"].shape != (points,):
            raise CheckpointStoreError("trace_seconds shape does not match chi")
        rho = arrays["rho"]
        expected_rho = (points, len(self.spec.model_names), self.spec.cells)
        if rho.shape != expected_rho:
            raise CheckpointStoreError(f"rho shape {rho.shape} does not match {expected_rho}")
        if np.any(arrays["chi_direct"] < 0.0) or np.any(arrays["body_peak_rooftop"] <= 0.0):
            raise CheckpointStoreError("chi_direct and body_peak_rooftop contain invalid values")
        if np.any(arrays["body_mean_rooftop"] <= 0.0) or np.any(sab < 0.0) or np.any(rho < 0.0):
            raise CheckpointStoreError("body or rho arrays contain invalid values")
        if not np.array_equal(np.max(sab, axis=1), arrays["body_peak_rooftop"]):
            raise CheckpointStoreError("body_peak_rooftop is not the exact surface maximum")
        if not np.array_equal(np.mean(sab, axis=1), arrays["body_mean_rooftop"]):
            raise CheckpointStoreError("body_mean_rooftop is not the exact surface mean")
        return ReplicaPayload(int(payload.base_seed), **arrays)

    def _read_shard(self, path: pathlib.Path, replica: int, points: int | None = None) -> ReplicaPayload:
        try:
            with np.load(path, allow_pickle=False) as artifact:
                if set(artifact.files) != _SHARD_NAMES:
                    raise CheckpointCorruptionError(f"shard {path.name} has unexpected fields")
                schema = str(_read_scalar(artifact, "schema", kind=str))
                saved_replica = int(_read_scalar(artifact, "replica", kind=(int, np.integer)))
                saved_seed = int(_read_scalar(artifact, "base_seed", kind=(int, np.integer)))
                if schema != SCHEMA or saved_replica != replica:
                    raise CheckpointCorruptionError(f"shard {path.name} has an invalid schema or replica")
                arrays = {name: np.asarray(artifact[name]) for name in _ARRAY_NAMES}
        except CheckpointStoreError:
            raise
        except (KeyError, OSError, ValueError, zipfile.BadZipFile) as exc:
            raise CheckpointCorruptionError(f"cannot read shard {path}: {exc}") from exc
        payload = ReplicaPayload(saved_seed, **arrays)
        if points is not None and payload.chi.shape[0] != points:
            raise CheckpointCorruptionError(f"shard {path.name} changes standpoint count")
        try:
            checked = self._validate_payload(payload)
        except CheckpointStoreError as exc:
            raise CheckpointCorruptionError(f"shard {path.name} failed array validation: {exc}") from exc
        return checked

    def _establish_points(self, payload: ReplicaPayload) -> int:
        points = int(payload.chi.shape[0])
        existing = getattr(self.spec, "_points", None)
        if existing is not None and existing != points:
            raise CheckpointCorruptionError(f"standpoint count changed from {existing} to {points}")
        object.__setattr__(self.spec, "_points", points)
        return points

    def load_prefix(self, count: int | None = None) -> CheckpointPrefix:
        """Load exactly the first ``count`` committed replicas.

        ``count=None`` loads the whole committed prefix.  Missing, partial, or
        modified committed shards raise :class:`CheckpointCorruptionError`.
        """
        committed = self.replicas
        if count is None:
            count = committed
        if not isinstance(count, (int, np.integer)) or not 0 <= int(count) <= committed:
            raise CheckpointStoreError(f"prefix count must lie between 0 and {committed}")
        count = int(count)
        if count == 0:
            points = int(getattr(self.spec, "_points", 0))
            if points == 0:
                # An empty store has no shape evidence.  The first append
                # establishes points, while an empty load remains unambiguous.
                points = 0
            return self._empty_prefix(points)
        entries = self._index["entries"][:count]
        payloads: list[ReplicaPayload] = []
        points: int | None = None
        for position, entry in enumerate(entries):
            path = self.root / entry["shard"]
            payload = self._validate_entry(entry, position, points)
            if points is None:
                points = self._establish_points(payload)
            elif payload.body_sab_rooftop.shape[1] != self.spec.surface_elements:
                raise CheckpointCorruptionError(f"shard {path.name} changes surface element count")
            for name, value in payload.arrays().items():
                if entry["arrays"][name] != array_sha256(value):
                    raise CheckpointCorruptionError(f"checkpoint shard {position} array {name!r} failed its hash")
            payloads.append(payload)
        if points is None:
            raise CheckpointCorruptionError("non-empty checkpoint index contains no shard payloads")
        base_seeds = np.asarray([payload.base_seed for payload in payloads], dtype=np.int64)
        arrays = {name: np.stack([payload.arrays()[name] for payload in payloads], axis=0) for name in _ARRAY_NAMES}
        rho_sum = np.zeros((points, len(self.spec.model_names), self.spec.cells), dtype=np.float64)
        for payload in payloads:
            rho_sum += payload.rho
        return CheckpointPrefix(
            base_seeds=base_seeds,
            chi=arrays["chi"],
            chi_direct=arrays["chi_direct"],
            body_peak_rooftop=arrays["body_peak_rooftop"],
            body_mean_rooftop=arrays["body_mean_rooftop"],
            body_sab_rooftop=arrays["body_sab_rooftop"],
            trace_seconds=arrays["trace_seconds"],
            rho_sum=rho_sum,
            local_grid=np.array(self.spec.local_grid, copy=True),
            solid_angle=self.spec.solid_angle,
        )

    def _empty_prefix(self, points: int) -> CheckpointPrefix:
        surface = self.spec.surface_elements
        return CheckpointPrefix(
            base_seeds=np.empty(0, dtype=np.int64),
            chi=np.empty((0, points, len(self.spec.model_names)), dtype=np.float64),
            chi_direct=np.empty((0, points, len(self.spec.model_names)), dtype=np.float64),
            body_peak_rooftop=np.empty((0, points), dtype=np.float64),
            body_mean_rooftop=np.empty((0, points), dtype=np.float64),
            body_sab_rooftop=np.empty((0, points, surface), dtype=np.float64),
            trace_seconds=np.empty((0, points), dtype=np.float64),
            rho_sum=np.zeros((points, len(self.spec.model_names), self.spec.cells), dtype=np.float64),
            local_grid=np.array(self.spec.local_grid, copy=True),
            solid_angle=self.spec.solid_angle,
        )

    def consolidate(self, destination: str | pathlib.Path, *, retire_shards: bool = True) -> pathlib.Path:
        """Export one legacy-compatible checkpoint and retire shards after validation.

        The consolidated file is written and reopened successfully before
        shard retirement starts.  If writing or validation is interrupted, the
        shards remain available for restart.  Set ``retire_shards=False`` for
        diagnostics or a repeated-write benchmark.
        """
        destination = pathlib.Path(destination)
        prefix = self.load_prefix()
        temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            with temporary.open("wb") as stream:
                np.savez_compressed(
                    stream,
                    schema=np.asarray(CONSOLIDATED_SCHEMA),
                    identity_sha256=np.asarray(self.spec.identity_sha256),
                    standpoint_array_sha256=np.asarray(self.spec.standpoint_array_sha256),
                    tissue_database_sha256=np.asarray(self.spec.tissue_database_sha256),
                    base_seeds=prefix.base_seeds,
                    chi=prefix.chi,
                    chi_direct=prefix.chi_direct,
                    body_peak_rooftop=prefix.body_peak_rooftop,
                    body_mean_rooftop=prefix.body_mean_rooftop,
                    body_sab_rooftop=prefix.body_sab_rooftop,
                    body_sab_sha256=np.asarray(array_sha256(prefix.body_sab_rooftop)),
                    trace_seconds=prefix.trace_seconds,
                    rho_sum=prefix.rho_sum,
                    local_grid=prefix.local_grid,
                    local_grid_sha256=np.asarray(array_sha256(prefix.local_grid)),
                    solid_angle=np.asarray(prefix.solid_angle, dtype=np.float64),
                    model_names=np.asarray(self.spec.model_names),
                )
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, destination)
            _fsync_directory(destination.parent)
        finally:
            temporary.unlink(missing_ok=True)
        self._validate_consolidated(destination, prefix)
        if retire_shards:
            self._retire_shards()
        return destination

    def _validate_consolidated(self, path: pathlib.Path, prefix: CheckpointPrefix) -> None:
        """Check the published legacy artifact before deleting its shards."""
        try:
            with np.load(path, allow_pickle=False) as artifact:
                expected = {
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
                }
                if set(artifact.files) != expected:
                    raise CheckpointCorruptionError("consolidated checkpoint has unexpected fields")
                if str(np.asarray(artifact["schema"]).item()) != CONSOLIDATED_SCHEMA:
                    raise CheckpointCorruptionError("consolidated checkpoint has the wrong schema")
                if str(np.asarray(artifact["identity_sha256"]).item()) != self.spec.identity_sha256:
                    raise CheckpointCorruptionError("consolidated checkpoint has the wrong identity")
                if str(np.asarray(artifact["standpoint_array_sha256"]).item()) != self.spec.standpoint_array_sha256:
                    raise CheckpointCorruptionError("consolidated checkpoint has the wrong standpoint identity")
                if str(np.asarray(artifact["tissue_database_sha256"]).item()) != self.spec.tissue_database_sha256:
                    raise CheckpointCorruptionError("consolidated checkpoint has the wrong tissue identity")
                if tuple(str(value) for value in artifact["model_names"]) != self.spec.model_names:
                    raise CheckpointCorruptionError("consolidated checkpoint has the wrong model names")
                arrays = {
                    name: np.asarray(artifact[name])
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
                    )
                }
                expected_arrays = {
                    "base_seeds": prefix.base_seeds,
                    "chi": prefix.chi,
                    "chi_direct": prefix.chi_direct,
                    "body_peak_rooftop": prefix.body_peak_rooftop,
                    "body_mean_rooftop": prefix.body_mean_rooftop,
                    "body_sab_rooftop": prefix.body_sab_rooftop,
                    "trace_seconds": prefix.trace_seconds,
                    "rho_sum": prefix.rho_sum,
                    "local_grid": prefix.local_grid,
                }
                for name, expected_array in expected_arrays.items():
                    if arrays[name].dtype != expected_array.dtype or not np.array_equal(arrays[name], expected_array):
                        raise CheckpointCorruptionError(f"consolidated checkpoint array {name!r} changed")
                if str(np.asarray(artifact["body_sab_sha256"]).item()) != array_sha256(prefix.body_sab_rooftop):
                    raise CheckpointCorruptionError("consolidated checkpoint body hash changed")
                if str(np.asarray(artifact["local_grid_sha256"]).item()) != self.spec.local_grid_sha256:
                    raise CheckpointCorruptionError("consolidated checkpoint grid hash changed")
                if float(np.asarray(artifact["solid_angle"]).item()) != self.spec.solid_angle:
                    raise CheckpointCorruptionError("consolidated checkpoint solid angle changed")
        except CheckpointStoreError:
            raise
        except (OSError, KeyError, TypeError, ValueError, zipfile.BadZipFile) as exc:
            raise CheckpointCorruptionError(f"cannot validate consolidated checkpoint {path}: {exc}") from exc

    def _retire_shards(self) -> None:
        """Remove only this store's files after the consolidated file is sealed."""
        if not self.root.is_dir():
            return
        for path in self.root.iterdir():
            if path.name == _INDEX_NAME or (path.name.startswith(_SHARD_PREFIX) and path.name.endswith(_SHARD_SUFFIX)):
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    continue
            elif path.name.startswith(".") and path.name.endswith(".tmp"):
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    continue
        _fsync_directory(self.root)
        try:
            self.root.rmdir()
        except OSError:
            # Leave unexpected files in place rather than deleting them.
            return


def benchmark_write_amplification(
    root: str | pathlib.Path,
    spec: CheckpointSpec,
    payloads: list[ReplicaPayload],
) -> dict[str, float | int]:
    """Compare shard bytes with repeated full-checkpoint writes.

    This is a small, deterministic benchmark helper for reports and tests. It
    measures bytes written rather than wall time, because compression speed and
    storage hardware vary widely.  The full path writes a consolidated file
    after each append, matching the old checkpoint behavior.
    """
    root = pathlib.Path(root)
    shard_root = root / "shards"
    full_root = root / "full"
    store = CheckpointStore(shard_root, spec)
    shard_data_bytes = 0
    store_cumulative_bytes = 0
    full_bytes = 0
    for replica, payload in enumerate(payloads):
        store.append(replica, payload)
        shard_size = (shard_root / f"{_SHARD_PREFIX}{replica:06d}{_SHARD_SUFFIX}").stat().st_size
        shard_data_bytes += shard_size
        store_cumulative_bytes += shard_size + store.index_path.stat().st_size
        output = store.consolidate(full_root / "checkpoint.npz", retire_shards=False)
        full_bytes += output.stat().st_size
    return {
        "replicas": len(payloads),
        "shard_data_bytes": shard_data_bytes,
        "store_cumulative_bytes": store_cumulative_bytes,
        "full_cumulative_bytes": full_bytes,
        "write_reduction": (1.0 - store_cumulative_bytes / full_bytes) if full_bytes else 0.0,
    }


__all__ = [
    "SCHEMA",
    "CONSOLIDATED_SCHEMA",
    "CheckpointCorruptionError",
    "CheckpointIdentityError",
    "CheckpointOrderError",
    "CheckpointPrefix",
    "CheckpointSpec",
    "CheckpointStore",
    "CheckpointStoreError",
    "ReplicaPayload",
    "array_sha256",
    "benchmark_write_amplification",
    "file_sha256",
]
