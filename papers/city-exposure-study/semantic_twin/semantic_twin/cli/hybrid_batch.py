"""Run the pinned hybrid panorama semantic pipeline over explicit stations.

The single-panorama runner is deliberately the scientific implementation.  This
module is only an operations wrapper around it: it expands a walk manifest (or
a newline-delimited station list), validates a complete output before skipping
it, and writes an atomic job ledger after every station.  A partially written
station is therefore safe to rerun, and a killed GPU job can resume without
guessing from directory names.

Typical production invocation::

    python -m semantic_twin.cli.hybrid_batch \
        --walk-manifest data/panoramas/tokyo_hachiko/walk_manifest.json \
        --job-manifest outputs/hybrid_batch/tokyo.json

The manifest's ``panorama_dirs`` entries are resolved relative to the walk
manifest.  ``--stations-file`` accepts one directory per line; blank lines and
``#`` comments are ignored.
"""

from __future__ import annotations

import argparse
import datetime as _datetime
import hashlib
import json
import os
import pathlib
import tempfile
import time
import zipfile
from collections.abc import Callable, Iterable
from typing import Any

import numpy as np

from .. import paths
from ..pano_geometry import inference_views
from ..vision.dense import MODEL as DENSE_MODEL
from ..vision.dense import PRODUCTION_REVISION as DENSE_REVISION
from ..vision.dense import file_digest
from ..vision.panorama import PanoramaModelSession, PanoramaRunConfig, run
from ..vision.prompted import MODEL as SAM3_MODEL
from ..vision.prompted import PRODUCTION_CONCEPT_ID_COUNT
from ..vision.prompted import PRODUCTION_REPOSITORY_COMMIT as SAM3_REPOSITORY_COMMIT
from ..vision.prompted import PRODUCTION_REVISION as SAM3_REVISION

SCHEMA = "hybrid-panorama-batch-v1"
CONTRACT_FILENAME = "hybrid_batch_contract.json"
# Keep the model revision and reviewed vocabulary size in the directory name.
# This prevents a production hybrid rebuild from mutating or being mistaken for
# an older dense-only ``semantics`` directory beside the same panorama.
SEMANTICS_DIRNAME = f"semantics_sam3_{SAM3_REVISION[:16]}_{PRODUCTION_CONCEPT_ID_COUNT}id"
DEFAULT_VIEW_SIZE = 1536
DEFAULT_INFERENCE_SIZE = 1536
DEFAULT_CONCEPT_RESOLUTION = 1008
DEFAULT_CONCEPT_THRESHOLD = 0.35
DEFAULT_PROMPT_BATCH = 32
DEFAULT_OUTPUT_WIDTH = 4096
DEFAULT_GATE_MIN_PIXELS = 256
DEFAULT_CONCEPTS_FILENAME = "semantic_concepts.json"

# These values are intentionally duplicated as a small, inspectable operations
# contract.  The runner passes the same values to PanoramaRunConfig and records
# them in each station's sidecar.  A future model update must make an explicit
# contract change rather than silently turning a resume into a mixed run.
PRODUCTION_CONTRACT: dict[str, Any] = {
    "backend": "hybrid",
    "device": "cuda",
    "model": DENSE_MODEL,
    "dense_revision": DENSE_REVISION,
    "inference_size": DEFAULT_INFERENCE_SIZE,
    "view_size": DEFAULT_VIEW_SIZE,
    "concept_resolution": DEFAULT_CONCEPT_RESOLUTION,
    "concept_threshold": DEFAULT_CONCEPT_THRESHOLD,
    "prompt_batch": DEFAULT_PROMPT_BATCH,
    "output_width": DEFAULT_OUTPUT_WIDTH,
    "gate_min_pixels": DEFAULT_GATE_MIN_PIXELS,
    "sam_revision": SAM3_REVISION,
    "sam_repository_commit": SAM3_REPOSITORY_COMMIT,
    "concept_id_count": PRODUCTION_CONCEPT_ID_COUNT,
    "semantics_dirname": SEMANTICS_DIRNAME,
    "production": True,
}

_MANIFEST_KEYS = frozenset(
    {
        "stations",
        "station_dirs",
        "station_directories",
        "panorama_dirs",
        "panorama_directories",
        "panoramas",
        "captures",
        "cameras",
        "walk",
    }
)
_PATH_KEYS = frozenset(
    {
        "station",
        "station_dir",
        "directory",
        "dir",
        "folder",
        "path",
        "panorama",
        "panorama_dir",
        "capture",
    }
)


def _utc_now() -> str:
    return _datetime.datetime.now(_datetime.UTC).isoformat(timespec="seconds")


def _sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_digest(document: Any) -> str:
    encoded = json.dumps(document, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _write_json_atomic(path: pathlib.Path, document: dict[str, Any]) -> None:
    """Replace one JSON file atomically, including after a worker is killed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
    ) as handle:
        temporary = pathlib.Path(handle.name)
        json.dump(document, handle, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def _resolve_path(value: str, *, base: pathlib.Path) -> pathlib.Path:
    path = pathlib.Path(value).expanduser()
    if path.is_absolute():
        return path.resolve()
    # Walk manifests produced by fetch_site_panoramas use names relative to the
    # acquisition directory.  A hand-written list is usually relative to cwd.
    candidate = (base / path).resolve()
    if candidate.exists():
        return candidate
    return path.resolve()


def _candidate_from_record(record: dict[str, Any]) -> str | None:
    for key in _PATH_KEYS:
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _manifest_values(value: Any, *, under_station_key: bool = False) -> Iterable[str]:
    """Yield station strings from the small set of supported walk schemas."""
    if isinstance(value, str):
        if under_station_key and value.strip():
            yield value.strip()
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            # A JSON array is also a useful hand-written walk manifest.  Once a
            # list is encountered, its entries are station records by the
            # schema boundary, even when the outer document had no key.
            yield from _manifest_values(item, under_station_key=True)
        return
    if not isinstance(value, dict):
        return
    direct = _candidate_from_record(value)
    if direct is not None:
        yield direct
    for key, child in value.items():
        if key in _MANIFEST_KEYS:
            yield from _manifest_values(child, under_station_key=True)
        elif key == "walk" or key in _MANIFEST_KEYS:
            yield from _manifest_values(child, under_station_key=False)


def read_station_sources(
    *, walk_manifest: pathlib.Path | None, stations_file: pathlib.Path | None
) -> list[pathlib.Path]:
    """Read and deduplicate explicit station directories in stable order."""
    if (walk_manifest is None) == (stations_file is None):
        raise ValueError("provide exactly one of --walk-manifest or --stations-file")
    if walk_manifest is not None:
        manifest = walk_manifest.expanduser().resolve()
        try:
            document = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"could not read walk manifest {manifest}: {exc}") from exc
        names = list(_manifest_values(document))
        base = manifest.parent
    else:
        source = stations_file.expanduser().resolve()
        try:
            lines = source.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            raise ValueError(f"could not read station list {source}: {exc}") from exc
        names = [line.split("#", 1)[0].strip() for line in lines]
        names = [line for line in names if line]
        base = source.parent
    if not names:
        raise ValueError("the station source contains no explicit station directories")
    result: list[pathlib.Path] = []
    seen: set[pathlib.Path] = set()
    for name in names:
        station = _resolve_path(name, base=base)
        if station not in seen:
            result.append(station)
            seen.add(station)
    return result


def panorama_image(station: pathlib.Path) -> pathlib.Path:
    """Find one deterministic stitched panorama image in a station directory."""
    zoomed: set[pathlib.Path] = set()
    for pattern in ("panorama_z*.jpg", "panorama_z*.jpeg", "panorama_z*.png"):
        zoomed.update(station.glob(pattern))
    if zoomed:

        def zoom(path: pathlib.Path) -> int:
            value = path.stem.partition("_z")[2]
            return int(value) if value.isdigit() else -1

        return min(zoomed, key=lambda path: (-zoom(path), path.name))

    fallback: set[pathlib.Path] = set()
    for pattern in ("panorama*.jpg", "panorama*.jpeg", "panorama*.png"):
        fallback.update(station.glob(pattern))
    if not fallback:
        raise FileNotFoundError(f"{station}: no stitched panorama image (panorama_z*.jpg/png)")
    return min(fallback)


def pipeline_config(station: pathlib.Path, *, concepts: pathlib.Path | None = None) -> PanoramaRunConfig:
    """Build the immutable current production pipeline configuration."""
    panorama = panorama_image(station)
    return PanoramaRunConfig(
        panorama=panorama,
        out=station / SEMANTICS_DIRNAME,
        model=DENSE_MODEL,
        device="cuda",
        backend="hybrid",
        concepts=concepts or paths.config_dir() / DEFAULT_CONCEPTS_FILENAME,
        view_size=DEFAULT_VIEW_SIZE,
        inference_size=DEFAULT_INFERENCE_SIZE,
        concept_resolution=DEFAULT_CONCEPT_RESOLUTION,
        concept_threshold=DEFAULT_CONCEPT_THRESHOLD,
        prompt_batch=DEFAULT_PROMPT_BATCH,
        gate_min_pixels=DEFAULT_GATE_MIN_PIXELS,
        output_width=DEFAULT_OUTPUT_WIDTH,
        force=False,
        dense_revision=DENSE_REVISION,
        sam_revision=SAM3_REVISION,
        sam_repository_commit=SAM3_REPOSITORY_COMMIT,
        production=True,
    )


def _contract_for(*, concepts: pathlib.Path) -> dict[str, Any]:
    contract = dict(PRODUCTION_CONTRACT)
    contract["concepts_sha256"] = _sha256(concepts)
    return contract


_REQUIRED_ARRAYS = frozenset({"entity", "rf_material", "material_concept", "material_source", "confidence"})


def _load_semantic_artifacts(
    output: pathlib.Path, *, contract: dict[str, Any]
) -> tuple[tuple[dict[str, Any], dict[str, Any]] | None, str | None]:
    metadata_path = output / "semantics.json"
    arrays_path = output / "panorama_semantics.npz"
    views_stamp = output / "views" / "cache_settings.json"
    if not metadata_path.is_file() or not arrays_path.is_file() or not views_stamp.is_file():
        return None, "required semantic output is missing"
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        cache = json.loads(views_stamp.read_text(encoding="utf-8"))
        with np.load(arrays_path, allow_pickle=False) as arrays:
            missing = sorted(_REQUIRED_ARRAYS - set(arrays.files))
            if missing:
                return None, f"semantic array keys are missing: {', '.join(missing)}"
            expected_shape = (contract["output_width"] // 2, contract["output_width"])
            if tuple(arrays["entity"].shape) != expected_shape:
                return None, f"entity raster shape is {arrays['entity'].shape}, expected {expected_shape}"
            if any(tuple(arrays[name].shape) != expected_shape for name in _REQUIRED_ARRAYS):
                return None, "semantic arrays do not share the production raster shape"
    except (OSError, ValueError, TypeError, zipfile.BadZipFile) as exc:
        return None, f"invalid semantic artifact: {exc}"
    if not isinstance(metadata, dict) or not isinstance(cache, dict):
        return None, "semantic metadata or cache settings is not a JSON object"
    return (metadata, cache), None


def _validate_pipeline_metadata(metadata: dict[str, Any], *, contract: dict[str, Any]) -> tuple[bool, str]:
    if metadata.get("backend") != "hybrid" or metadata.get("model") != contract["model"]:
        return False, "semantic backend/model does not match the production contract"
    if (
        metadata.get("view_size") != contract["view_size"]
        or metadata.get("inference_size") != contract["inference_size"]
    ):
        return False, "semantic view/inference size does not match the production contract"
    if metadata.get("output_width") != contract["output_width"]:
        return False, "semantic output width does not match the production contract"
    return True, "complete"


def _validate_dense_revision(metadata: dict[str, Any], *, contract: dict[str, Any]) -> tuple[bool, str]:
    dense_identity = metadata.get("model_revision")
    dense_revision = dense_identity.get("resolved_revision") if isinstance(dense_identity, dict) else None
    if dense_revision != contract["dense_revision"]:
        return False, "semantic dense checkpoint revision is not the pinned production revision"
    return True, "complete"


def _validate_concept_metadata(metadata: dict[str, Any], *, contract: dict[str, Any]) -> tuple[bool, str]:
    concept_backend = metadata.get("concept_backend", {})
    if not isinstance(concept_backend, dict):
        return False, "semantic SAM 3 metadata is not an object"
    if (
        concept_backend.get("model") != SAM3_MODEL
        or concept_backend.get("revision") != contract["sam_revision"]
        or concept_backend.get("repository_commit") != contract["sam_repository_commit"]
    ):
        return False, "semantic SAM 3 backend is not the pinned production revision"
    vocabulary = metadata.get("concept_vocabulary", {})
    if not isinstance(vocabulary, dict):
        return False, "semantic concept vocabulary is not an object"
    if vocabulary.get("id_count") != contract["concept_id_count"]:
        return False, "semantic concept vocabulary is not the reviewed production catalogue"
    return True, "complete"


def _validate_view_cache_stamp(
    cache: dict[str, Any], *, panorama: pathlib.Path, contract: dict[str, Any]
) -> tuple[bool, str]:
    if cache.get("model") != contract["model"] or cache.get("inference_size") != contract["inference_size"]:
        return False, "dense view cache settings do not match the production contract"
    expected_panorama_digest = file_digest(panorama)
    if cache.get("panorama") != expected_panorama_digest:
        return False, "dense view cache was produced from a different panorama"
    cache_identity = cache.get("model_revision")
    cache_revision = cache_identity.get("resolved_revision") if isinstance(cache_identity, dict) else None
    if cache_revision != contract["dense_revision"]:
        return False, "dense view cache checkpoint revision is not pinned"
    return True, "complete"


def _validate_concept_cache(output: pathlib.Path, *, metadata: dict[str, Any], view_name: str) -> tuple[bool, str]:
    concept_file = output / "concepts" / f"{view_name}.npz"
    if not concept_file.is_file():
        return False, f"SAM 3 concept cache is incomplete: {view_name}.npz"
    try:
        with np.load(concept_file, allow_pickle=False) as concept:
            if "cache_key" not in concept or str(concept["cache_key"]) != str(metadata.get("concept_cache_key")):
                return False, f"SAM 3 concept cache key mismatch: {view_name}.npz"
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        return False, f"invalid SAM 3 concept cache {view_name}.npz: {exc}"
    return True, "complete"


def _validate_view_artifacts(
    output: pathlib.Path, *, metadata: dict[str, Any], expected_view_names: tuple[str, ...]
) -> tuple[bool, str]:
    view_records = metadata.get("views", ())
    if not isinstance(view_records, list) or len(view_records) != len(expected_view_names):
        return (
            False,
            f"semantic manifest has {len(view_records) if isinstance(view_records, list) else 0} views, expected {len(expected_view_names)}",
        )
    for view_name in expected_view_names:
        for suffix in (".jpg", "_labels.npy", "_confidence.npy"):
            if not (output / "views" / f"{view_name}{suffix}").is_file():
                return False, f"view cache is incomplete: {view_name}{suffix}"
        valid, reason = _validate_concept_cache(output, metadata=metadata, view_name=view_name)
        if not valid:
            return False, reason
    return True, "complete"


def _metadata_contract_valid(
    output: pathlib.Path, *, panorama: pathlib.Path, contract: dict[str, Any]
) -> tuple[bool, str]:
    artifacts, reason = _load_semantic_artifacts(output, contract=contract)
    if reason is not None:
        return False, reason
    if artifacts is None:
        return False, "semantic artifact loader returned no artifacts"
    metadata, cache = artifacts
    checks: tuple[Callable[[], tuple[bool, str]], ...] = (
        lambda: _validate_pipeline_metadata(metadata, contract=contract),
        lambda: _validate_dense_revision(metadata, contract=contract),
        lambda: _validate_concept_metadata(metadata, contract=contract),
        lambda: _validate_view_cache_stamp(cache, panorama=panorama, contract=contract),
        lambda: _validate_view_artifacts(
            output, metadata=metadata, expected_view_names=tuple(view.name for view in inference_views())
        ),
    )
    for check in checks:
        valid, reason = check()
        if not valid:
            return False, reason
    return True, "complete"


def _artifact_hashes(output: pathlib.Path) -> dict[str, str]:
    return {
        str(path.relative_to(output)): _sha256(path)
        for path in sorted(output.rglob("*"))
        if path.is_file() and path.name != CONTRACT_FILENAME
    }


def complete_output(
    station: pathlib.Path,
    *,
    concepts: pathlib.Path,
    expected_contract: dict[str, Any] | None = None,
) -> tuple[bool, str]:
    """Validate a resumable output, including source and every artifact hash."""
    output = station / SEMANTICS_DIRNAME
    sidecar = output / CONTRACT_FILENAME
    if not sidecar.is_file():
        return False, "batch contract sidecar is missing"
    try:
        record = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, f"invalid batch contract sidecar: {exc}"
    if not isinstance(record, dict):
        return False, "invalid batch contract sidecar: root is not an object"
    contract = expected_contract or _contract_for(concepts=concepts)
    if record.get("schema") != SCHEMA or record.get("contract") != contract:
        return False, "batch contract differs from the current production pins"
    try:
        panorama = panorama_image(station)
        source = record["panorama"]
        if source.get("sha256") != _sha256(panorama) or source.get("path") != str(panorama):
            return False, "source panorama hash or path changed"
        artifacts = record["artifacts"]
        if not isinstance(artifacts, dict) or not artifacts:
            return False, "batch contract has no artifact hashes"
        for relative, digest in artifacts.items():
            path = output / relative
            if not path.is_file() or _sha256(path) != digest:
                return False, f"artifact is missing or changed: {relative}"
    except (KeyError, TypeError, OSError) as exc:
        return False, f"invalid batch contract records: {exc}"
    return _metadata_contract_valid(output, panorama=panorama, contract=contract)


def _load_job(path: pathlib.Path, *, contract: dict[str, Any], source: pathlib.Path) -> dict[str, Any]:
    if path.exists():
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid existing job manifest {path}: {exc}") from exc
        if not isinstance(document, dict):
            raise ValueError(f"invalid existing job manifest {path}: root is not an object")
        if document.get("schema") != SCHEMA or document.get("contract") != contract:
            raise ValueError("existing job manifest belongs to a different production contract")
        return document
    return {
        "schema": SCHEMA,
        "contract": contract,
        "source": str(source),
        "started_at": _utc_now(),
        "updated_at": _utc_now(),
        "stations": [],
    }


def _sidecar(
    station: pathlib.Path,
    *,
    panorama: pathlib.Path,
    output: pathlib.Path,
    contract: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "station": str(station),
        "panorama": {"path": str(panorama), "sha256": _sha256(panorama), "size": panorama.stat().st_size},
        "contract": contract,
        "artifacts": _artifact_hashes(output),
    }


def _new_station_row(station: pathlib.Path, *, previous: dict[str, Any] | None = None) -> dict[str, Any]:
    output = station / SEMANTICS_DIRNAME
    row = dict(previous or {})
    row.update({"station": str(station), "output": str(output), "updated_at": _utc_now()})
    return row


def _persist_job(
    path: pathlib.Path,
    document: dict[str, Any],
    ordered_rows: list[dict[str, Any]],
    original_rows: list[dict[str, Any]],
    *,
    current: dict[str, Any] | None = None,
) -> None:
    """Persist completed rows plus an optional in-flight row atomically."""
    processed = ordered_rows + ([current] if current is not None else [])
    seen = {row.get("station") for row in processed}
    document["stations"] = processed + [row for row in original_rows if row.get("station") not in seen]
    document["updated_at"] = _utc_now()
    _write_json_atomic(path, document)


def _prepare_station(
    station: pathlib.Path,
    *,
    row: dict[str, Any],
    concepts: pathlib.Path,
    contract: dict[str, Any],
) -> tuple[dict[str, Any], PanoramaRunConfig | None]:
    """Validate a station and return either a skip row or a runnable config."""
    if not station.is_dir():
        raise FileNotFoundError(f"station directory does not exist: {station}")
    complete, reason = complete_output(station, concepts=concepts, expected_contract=contract)
    if complete:
        row.update({"status": "skipped_complete", "reason": reason, "elapsed_seconds": 0.0})
        return row, None
    config = pipeline_config(station, concepts=concepts)
    row["input_panorama"] = str(config.panorama)
    row["status"] = "running"
    return row, config


def _run_and_finalize(
    station: pathlib.Path,
    *,
    row: dict[str, Any],
    config: PanoramaRunConfig,
    concepts: pathlib.Path,
    contract: dict[str, Any],
    started: float,
    session: PanoramaModelSession,
) -> dict[str, Any]:
    """Run one station and write its versioned sidecar after validation."""
    run(config, session=session)
    output = station / SEMANTICS_DIRNAME
    output.mkdir(parents=True, exist_ok=True)
    valid, reason = _metadata_contract_valid(output, panorama=config.panorama, contract=contract)
    if not valid:
        raise RuntimeError(f"pipeline returned without a complete production output: {reason}")
    sidecar = output / CONTRACT_FILENAME
    _write_json_atomic(sidecar, _sidecar(station, panorama=config.panorama, output=output, contract=contract))
    valid, reason = complete_output(station, concepts=concepts, expected_contract=contract)
    if not valid:
        raise RuntimeError(f"output sidecar failed self-validation: {reason}")
    row.update({"status": "completed", "reason": reason})
    row["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    return row


def _summary(station_dirs: list[pathlib.Path], rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total": len(station_dirs),
        "completed": sum(row.get("status") == "completed" for row in rows),
        "skipped_complete": sum(row.get("status") == "skipped_complete" for row in rows),
        "failed": sum(row.get("status") == "failed" for row in rows),
    }


def execute(
    *,
    walk_manifest: pathlib.Path | None = None,
    stations_file: pathlib.Path | None = None,
    job_manifest: pathlib.Path,
    concepts: pathlib.Path | None = None,
    fail_fast: bool = False,
) -> dict[str, Any]:
    """Run or resume a batch and return its JSON-serialisable job document."""
    concept_path = (concepts or paths.config_dir() / DEFAULT_CONCEPTS_FILENAME).expanduser().resolve()
    if not concept_path.is_file():
        raise FileNotFoundError(f"semantic concept catalogue is missing: {concept_path}")
    contract = _contract_for(concepts=concept_path)
    source = (walk_manifest or stations_file).expanduser().resolve()  # type: ignore[union-attr]
    station_dirs = read_station_sources(walk_manifest=walk_manifest, stations_file=stations_file)
    job_path = job_manifest.expanduser().resolve()
    document = _load_job(job_path, contract=contract, source=source)
    original_rows = [row for row in document.get("stations", []) if isinstance(row, dict)]
    rows = {row.get("station"): row for row in original_rows}
    ordered_rows: list[dict[str, Any]] = []
    session: PanoramaModelSession | None = None

    for station in station_dirs:
        row = _new_station_row(station, previous=rows.get(str(station)))
        started = time.perf_counter()
        try:
            row, config = _prepare_station(
                station,
                row=row,
                concepts=concept_path,
                contract=contract,
            )
            if config is None:
                ordered_rows.append(row)
                _persist_job(job_path, document, ordered_rows, original_rows)
                continue
            _persist_job(job_path, document, ordered_rows, original_rows, current=row)
            if session is None:
                session = PanoramaModelSession(config)
            row = _run_and_finalize(
                station,
                row=row,
                config=config,
                concepts=concept_path,
                contract=contract,
                started=started,
                session=session,
            )
        except Exception as exc:
            row.update({"status": "failed", "error": f"{type(exc).__name__}: {exc}"})
            row["elapsed_seconds"] = round(time.perf_counter() - started, 3)
            ordered_rows.append(row)
            _persist_job(job_path, document, ordered_rows, original_rows)
            if fail_fast:
                raise
            continue
        if "elapsed_seconds" not in row:
            row["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        ordered_rows.append(row)
        _persist_job(job_path, document, ordered_rows, original_rows)
    document["finished_at"] = _utc_now()
    document["summary"] = _summary(station_dirs, ordered_rows)
    document["updated_at"] = _utc_now()
    _write_json_atomic(job_path, document)
    return document


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--walk-manifest", type=pathlib.Path, help="JSON walk manifest containing panorama_dirs/stations"
    )
    source.add_argument("--stations-file", type=pathlib.Path, help="newline-delimited explicit station directories")
    parser.add_argument("--job-manifest", type=pathlib.Path, required=True, help="atomic resumable job ledger")
    parser.add_argument(
        "--concepts",
        type=pathlib.Path,
        default=paths.config_dir() / DEFAULT_CONCEPTS_FILENAME,
        help="reviewed semantic concept catalogue (the production default is pinned)",
    )
    parser.add_argument("--fail-fast", action="store_true", help="stop after the first station failure")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
    document = execute(
        walk_manifest=args.walk_manifest,
        stations_file=args.stations_file,
        job_manifest=args.job_manifest,
        concepts=args.concepts,
        fail_fast=args.fail_fast,
    )
    summary = document["summary"]
    print(
        f"[hybrid-batch] total={summary['total']} completed={summary['completed']} "
        f"skipped={summary['skipped_complete']} failed={summary['failed']} -> {args.job_manifest}"
    )
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
