"""Paired comparison of two completed roofline campaign directories.

The campaign runner stores one scalar shard per seed.  This report reads those
shards directly so that the IID and rotated-Fibonacci estimates remain paired by
seed and standpoint.  It intentionally reports measured differences and ratios
only.  No stopping rule or acceptance threshold is applied here.

The paired identity deliberately differs in the launch sampler only.  Config
``run.tag`` and ``campaign.output_dir`` are operational fields and are not sealed
into ``campaign_identity.json``.  The loader therefore normalizes only the
historical omitted-IID versus explicit-Fibonacci sampler field, and rejects every
other identity drift.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from semantic_twin.exposure.roofline_campaign import (
    BODY_METRICS,
    COMPONENTS,
    FIELD_META,
    REFERENCE_FIELDS,
    SCHEMA_VERSION,
    TIMING_FIELDS,
)

REPORT_SCHEMA_VERSION = "roofline_campaign_pair_comparison_v1"
_SAMPLING_MODES = ("iid", "rotated_fibonacci")
_OPTIONAL_ALL_SPECULAR_KEYS = (
    "all_specular_transfer",
    "deterministic_all_specular_transfer",
    "all_specular_order_1",
    "all_specular_mass",
)
_OPTIONAL_SUFFIX_KEYS = (
    "sampled_suffix_transfer",
    "sampled_specular_transfer",
    "mixed_specular_transfer",
    "chi_specular_suffix",
)


class CampaignComparisonError(ValueError):
    """The two directories cannot form a valid paired comparison."""


def _json_read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CampaignComparisonError(f"campaign artifact is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CampaignComparisonError(f"campaign artifact is not valid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise CampaignComparisonError(f"campaign artifact must be a JSON object: {path}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _safe_relative_path(root: Path, relative: Any, *, context: str) -> Path:
    if not isinstance(relative, str) or not relative or "\x00" in relative:
        raise CampaignComparisonError(f"{context} must be a non-empty relative path")
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise CampaignComparisonError(f"{context} escapes the campaign directory: {relative!r}")
    root_resolved = root.resolve()
    path = (root_resolved / candidate).resolve()
    try:
        path.relative_to(root_resolved)
    except ValueError as exc:
        raise CampaignComparisonError(f"{context} escapes the campaign directory: {relative!r}") from exc
    return path


def _required_path(root: Path, name: str) -> Path:
    path = root / name
    if not path.is_file():
        raise CampaignComparisonError(f"completed campaign is missing {name}: {root}")
    return path


def _normalise_launch_sampling(data: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """Return identity data with the historical omitted IID value made explicit."""
    normalised = copy.deepcopy(data)
    transport = normalised.get("transport")
    tracer = transport.get("tracer") if isinstance(transport, dict) else None
    configuration = tracer.get("configuration") if isinstance(tracer, dict) else None
    if not isinstance(configuration, dict):
        raise CampaignComparisonError("campaign identity does not seal tracer configuration")
    mode = configuration.get("launch_sampling", "iid")
    if mode not in _SAMPLING_MODES:
        raise CampaignComparisonError(f"unknown launch sampling mode in campaign identity: {mode!r}")
    # Launch design is the one deliberate difference in this comparison.  Keep
    # its value separately and remove it from the compatibility fingerprint.
    configuration.pop("launch_sampling", None)
    return normalised, mode


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _identity_wrapper_hash(identity_data: dict[str, Any]) -> str:
    try:
        canonical = _canonical(identity_data)
    except (TypeError, ValueError) as exc:
        raise CampaignComparisonError("campaign identity data is not canonical JSON") from exc
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _as_float_array(value: Any, *, name: str, shape: tuple[int, ...] | None = None) -> np.ndarray:
    array = np.asarray(value)
    if shape is not None and array.shape != shape:
        raise CampaignComparisonError(f"{name} has shape {array.shape}, expected {shape}")
    if array.dtype != np.float64:
        raise CampaignComparisonError(f"{name} must be float64, got {array.dtype}")
    if np.any(~np.isfinite(array)):
        raise CampaignComparisonError(f"{name} contains non-finite values")
    return array


def _optional_array(value: Any, *, name: str, shape: tuple[int, ...]) -> np.ndarray:
    array = np.asarray(value, dtype=np.float64)
    if array.shape != shape or np.any(~np.isfinite(array)) or np.any(array < 0.0):
        raise CampaignComparisonError(f"{name} must be finite, nonnegative, and have shape {shape}")
    return array


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CampaignComparisonError(f"locations.jsonl has invalid line {line_number}: {path}") from exc
        if not isinstance(row, dict):
            raise CampaignComparisonError(f"locations.jsonl line {line_number} is not an object: {path}")
        rows.append(row)
    return rows


@dataclass(frozen=True)
class _Campaign:
    root: Path
    identity: dict[str, Any]
    identity_data: dict[str, Any]
    sampling: str
    manifest: dict[str, Any]
    checkpoint: dict[str, Any]
    seeds: tuple[int, ...]
    points: int
    locations: tuple[dict[str, Any], ...]
    raw_transfer: np.ndarray
    body_metrics: np.ndarray
    timings: np.ndarray
    diagnostics: tuple[tuple[dict[str, Any], ...], ...]
    all_specular_transfer: np.ndarray | None
    suffix_transfer: np.ndarray | None

    @property
    def planned_seeds(self) -> tuple[int, ...]:
        configuration = self.identity_data.get("configuration", {})
        return tuple(int(seed) for seed in configuration.get("planned_seeds", ()))

    @property
    def convergence_looks(self) -> tuple[int, ...]:
        configuration = self.identity_data.get("configuration", {})
        return tuple(int(look) for look in configuration.get("convergence_looks", ()))


@dataclass(frozen=True)
class _Shard:
    raw: np.ndarray
    body: np.ndarray
    timing: np.ndarray
    diagnostics: tuple[dict[str, Any], ...]
    all_specular: np.ndarray | None
    suffix: np.ndarray | None


def _check_manifest_files(root: Path, manifest: dict[str, Any]) -> None:
    files = manifest.get("files", {})
    if not isinstance(files, dict) or not files:
        raise CampaignComparisonError("manifest.files must be a non-empty object")
    for name, expected in files.items():
        path = _safe_relative_path(root, name, context="manifest file path")
        if not _is_sha256(expected):
            raise CampaignComparisonError(f"manifest hash is not a SHA-256 digest for {path}")
        if not path.is_file() or _sha256(path) != expected:
            raise CampaignComparisonError(f"manifest hash validation failed for {path}")


def _manifest_checkpoint_path(root: Path, relative: Any) -> str:
    path = _checkpoint_artifact(root, relative)
    return path.relative_to(root.resolve()).as_posix()


def _check_manifest_completeness(root: Path, manifest: dict[str, Any], checkpoint: dict[str, Any]) -> None:
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise CampaignComparisonError("manifest.files must be an object")
    required = {"campaign_identity.json", "locations.jsonl", "summary.json", "checkpoint/index.json"}
    committed = checkpoint.get("committed", [])
    if not isinstance(committed, list):
        raise CampaignComparisonError(f"checkpoint committed entries must be a list: {root}")
    for entry in committed:
        if not isinstance(entry, dict):
            raise CampaignComparisonError(f"checkpoint committed entry must be an object: {root}")
        required.add(_manifest_checkpoint_path(root, entry.get("path")))
        required.add(_manifest_checkpoint_path(root, entry.get("diagnostics_path")))
    cumulative = checkpoint.get("cumulative_sab")
    if cumulative is not None:
        if not isinstance(cumulative, dict):
            raise CampaignComparisonError(f"checkpoint cumulative_sab entry must be an object: {root}")
        required.add(_manifest_checkpoint_path(root, cumulative.get("path")))
    look_sab = checkpoint.get("look_sab", [])
    if not isinstance(look_sab, list):
        raise CampaignComparisonError(f"checkpoint look_sab entries must be a list: {root}")
    for entry in look_sab:
        if not isinstance(entry, dict):
            raise CampaignComparisonError(f"checkpoint look_sab entry must be an object: {root}")
        required.add(_manifest_checkpoint_path(root, entry.get("path")))
    missing = sorted(required.difference(files))
    if missing:
        raise CampaignComparisonError(f"manifest is missing required artifact hashes: {', '.join(missing)}")


def _load_optional_from_diagnostics(
    diagnostics: list[list[dict[str, Any]]], keys: Iterable[str], points: int
) -> np.ndarray | None:
    values = [[_diagnostic_optional(replica[point], keys) for point in range(points)] for replica in diagnostics]
    if not values or any(value is None for replica in values for value in replica):
        return None
    return np.asarray(values, dtype=np.float64)


def _coerce_optional_diagnostic_value(found: Any, key: str) -> float | None:
    if isinstance(found, dict):
        found = found.get("transfer", found.get("mass", found.get("value")))
    if found is None:
        return None
    try:
        value = float(found)
    except (TypeError, ValueError) as exc:
        raise CampaignComparisonError(f"diagnostic optional value is not numeric: {key}") from exc
    if not np.isfinite(value) or value < 0.0:
        raise CampaignComparisonError(f"diagnostic optional value is not finite and nonnegative: {key}")
    return value


def _diagnostic_optional(diagnostic: dict[str, Any], keys: Iterable[str]) -> float | None:
    nested = diagnostic.get("sampled_specular_suffix")
    for key in keys:
        found = diagnostic.get(key)
        if found is None and isinstance(nested, dict):
            found = nested.get(key)
        if found is not None:
            return _coerce_optional_diagnostic_value(found, key)
    return None


def _checkpoint_artifact(root: Path, relative: Any) -> Path:
    if not isinstance(relative, str):
        raise CampaignComparisonError(f"checkpoint entry has no shard path: {root}")
    if relative.startswith("checkpoint/"):
        return _safe_relative_path(root, relative, context="checkpoint artifact path")
    return _safe_relative_path(root, str(Path("checkpoint") / relative), context="checkpoint artifact path")


def _load_shard(root: Path, entry: dict[str, Any], points: int) -> _Shard:
    shard_path = _checkpoint_artifact(root, entry.get("path"))
    diagnostics_path = _checkpoint_artifact(root, entry.get("diagnostics_path"))
    if not shard_path.is_file() or not diagnostics_path.is_file():
        raise CampaignComparisonError(f"checkpoint shard is missing in {root}: {shard_path}")
    shard_hash = entry.get("sha256")
    diagnostics_hash = entry.get("diagnostics_sha256")
    if not _is_sha256(shard_hash) or not _is_sha256(diagnostics_hash):
        raise CampaignComparisonError(f"checkpoint shard hashes are required and must be SHA-256: {shard_path}")
    if _sha256(shard_path) != shard_hash:
        raise CampaignComparisonError(f"checkpoint shard hash validation failed: {shard_path}")
    if _sha256(diagnostics_path) != diagnostics_hash:
        raise CampaignComparisonError(f"checkpoint diagnostics hash validation failed: {diagnostics_path}")
    with np.load(shard_path, allow_pickle=False) as payload:
        raw, body, timing, all_specular, suffix = _load_shard_payload(payload, shard_path, points)
    try:
        diagnostic_value = json.loads(diagnostics_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CampaignComparisonError(f"checkpoint diagnostics are not valid JSON: {diagnostics_path}") from exc
    if not isinstance(diagnostic_value, list) or len(diagnostic_value) != points:
        raise CampaignComparisonError(f"checkpoint diagnostics do not align with route: {diagnostics_path}")
    if not all(isinstance(item, dict) for item in diagnostic_value):
        raise CampaignComparisonError(f"checkpoint diagnostics contain a non-object row: {diagnostics_path}")
    return _Shard(raw, body, timing, tuple(diagnostic_value), all_specular, suffix)


def _load_shard_payload(
    payload: Any, path: Path, points: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray | None, np.ndarray | None]:
    required = {"raw_transfer", "body_metrics", "timings", "field_meta", "reference"}
    if not required.issubset(payload.files):
        raise CampaignComparisonError(f"checkpoint shard is missing required arrays: {path}")
    raw = _as_float_array(payload["raw_transfer"], name=f"{path}:raw_transfer", shape=(points, 4))
    body = _as_float_array(payload["body_metrics"], name=f"{path}:body_metrics", shape=(points, 4, len(BODY_METRICS)))
    timing = np.asarray(payload["timings"])
    if timing.dtype != np.float64 or timing.shape != (points, len(TIMING_FIELDS)):
        raise CampaignComparisonError(f"{path}:timings has the wrong dtype or shape")
    if np.any(np.isinf(timing)) or np.any(timing[np.isfinite(timing)] < 0.0):
        raise CampaignComparisonError(f"{path}:timings are not nonnegative or NaN")
    _as_float_array(payload["field_meta"], name=f"{path}:field_meta", shape=(points, len(FIELD_META)))
    _as_float_array(payload["reference"], name=f"{path}:reference", shape=(points, len(REFERENCE_FIELDS)))
    if np.any(raw < 0.0) or np.any(body < 0.0):
        raise CampaignComparisonError(f"{path} has negative transfer or body values")
    if not np.allclose(raw[:, 3], np.sum(raw[:, :3], axis=1), rtol=2.0e-10, atol=1.0e-14):
        raise CampaignComparisonError(f"{path} raw components do not conserve total transfer")
    all_specular = _first_optional_array(payload, _OPTIONAL_ALL_SPECULAR_KEYS, points, path)
    suffix = _first_optional_array(payload, _OPTIONAL_SUFFIX_KEYS, points, path)
    return raw, body, timing, all_specular, suffix


def _first_optional_array(payload: Any, keys: Iterable[str], points: int, path: Path) -> np.ndarray | None:
    for key in keys:
        if key in payload.files:
            return _optional_array(payload[key], name=f"{path}:{key}", shape=(points,))
    return None


def _load_campaign_documents(
    root: Path,
) -> tuple[dict[str, Any], dict[str, Any], str, dict[str, Any], dict[str, Any], dict[str, Any]]:
    identity = _json_read(_required_path(root, "campaign_identity.json"))
    identity_data = identity.get("data")
    if not isinstance(identity_data, dict):
        raise CampaignComparisonError(f"campaign identity has no data object: {root}")
    identity_hash = identity.get("sha256")
    expected_identity_hash = _identity_wrapper_hash(identity_data)
    if not _is_sha256(identity_hash) or identity_hash != expected_identity_hash:
        raise CampaignComparisonError(f"campaign identity SHA-256 wrapper is invalid: {root}")
    _, sampling = _normalise_launch_sampling(identity_data)
    manifest = _json_read(_required_path(root, "manifest.json"))
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise CampaignComparisonError(f"unsupported roofline campaign schema in {root}")
    if manifest.get("identity_sha256") != identity.get("sha256"):
        raise CampaignComparisonError(f"manifest and campaign identity disagree in {root}")
    _check_manifest_files(root, manifest)
    summary = _json_read(_required_path(root, "summary.json"))
    checkpoint = _json_read(_required_path(root / "checkpoint", "index.json"))
    if checkpoint.get("schema_version") != SCHEMA_VERSION:
        raise CampaignComparisonError(f"unsupported checkpoint schema in {root}")
    if checkpoint.get("identity_sha256") != identity.get("sha256"):
        raise CampaignComparisonError(f"checkpoint and campaign identity disagree in {root}")
    _check_manifest_completeness(root, manifest, checkpoint)
    return identity, identity_data, sampling, manifest, summary, checkpoint


def _validate_checkpoint_schema(root: Path, checkpoint: dict[str, Any]) -> tuple[int, list[dict[str, Any]]]:
    points = int(checkpoint.get("points", 0))
    if points < 1:
        raise CampaignComparisonError(f"campaign has no standpoints: {root}")
    if checkpoint.get("components") != list(COMPONENTS):
        raise CampaignComparisonError(f"campaign component schema differs in {root}")
    if checkpoint.get("body_metrics") != list(BODY_METRICS):
        raise CampaignComparisonError(f"campaign body metric schema differs in {root}")
    if checkpoint.get("timing_fields") != list(TIMING_FIELDS):
        raise CampaignComparisonError(f"campaign timing schema differs in {root}")
    if checkpoint.get("reference_fields") != list(REFERENCE_FIELDS):
        raise CampaignComparisonError(f"campaign reference schema differs in {root}")
    committed = checkpoint.get("committed", [])
    if not isinstance(committed, list) or not committed:
        raise CampaignComparisonError(f"campaign has no committed replica shards: {root}")
    return points, committed


def _validate_seed_metadata(
    root: Path,
    identity_data: dict[str, Any],
    committed: list[dict[str, Any]],
    summary: dict[str, Any],
) -> tuple[int, ...]:
    if not all(isinstance(entry, dict) for entry in committed):
        raise CampaignComparisonError(f"campaign checkpoint contains a non-object replica entry: {root}")
    try:
        seeds = tuple(int(entry["seed"]) for entry in committed)
    except (KeyError, TypeError, ValueError) as exc:
        raise CampaignComparisonError(f"campaign checkpoint has an invalid replica seed: {root}") from exc
    if len(set(seeds)) != len(seeds):
        raise CampaignComparisonError(f"campaign has duplicate replica seeds: {root}")
    if seeds != tuple(sorted(seeds)):
        raise CampaignComparisonError(f"campaign replica seeds are not in order: {root}")
    try:
        planned = tuple(int(seed) for seed in identity_data.get("configuration", {}).get("planned_seeds", ()))
    except (TypeError, ValueError) as exc:
        raise CampaignComparisonError(f"campaign identity has invalid planned seeds: {root}") from exc
    if planned and seeds != planned[: len(seeds)]:
        raise CampaignComparisonError(f"campaign replicas are not a complete planned-seed prefix: {root}")
    try:
        summary_seeds = tuple(int(seed) for seed in summary.get("seeds", ()))
        summary_replicas = int(summary.get("replicas", -1))
    except (TypeError, ValueError) as exc:
        raise CampaignComparisonError(f"summary has invalid replica metadata: {root}") from exc
    if summary_replicas != len(seeds) or summary_seeds != seeds:
        raise CampaignComparisonError(f"summary and checkpoint seed sets disagree in {root}")
    return seeds


def _validate_campaign_metadata(
    root: Path,
    identity_data: dict[str, Any],
    checkpoint: dict[str, Any],
    summary: dict[str, Any],
) -> tuple[tuple[int, ...], int, list[dict[str, Any]], list[dict[str, Any]]]:
    points, committed = _validate_checkpoint_schema(root, checkpoint)
    seeds = _validate_seed_metadata(root, identity_data, committed, summary)
    locations = _load_jsonl(_required_path(root, "locations.jsonl"))
    if len(locations) != points or [row.get("standpoint") for row in locations] != list(range(points)):
        raise CampaignComparisonError(f"locations.jsonl is not an ordered complete route: {root}")
    return seeds, points, locations, committed


def _load_campaign(path: str | Path) -> _Campaign:
    root = Path(path).resolve()
    if not root.is_dir():
        raise CampaignComparisonError(f"campaign output directory does not exist: {root}")
    identity, identity_data, sampling, manifest, summary, checkpoint = _load_campaign_documents(root)
    seeds, points, locations, committed = _validate_campaign_metadata(root, identity_data, checkpoint, summary)

    shards = [_load_shard(root, entry, points) for entry in committed]
    raw_parts = [shard.raw for shard in shards]
    body_parts = [shard.body for shard in shards]
    timing_parts = [shard.timing for shard in shards]
    diagnostic_parts = [shard.diagnostics for shard in shards]
    all_optional = [shard.all_specular for shard in shards]
    suffix_optional = [shard.suffix for shard in shards]
    all_specular = None if any(item is None for item in all_optional) else np.stack(all_optional)
    suffix_transfer = None if any(item is None for item in suffix_optional) else np.stack(suffix_optional)
    if all_specular is None:
        suffix_enabled = any(
            bool(item.get("sampled_specular_suffix", {}).get("enabled", False))
            for replica in diagnostic_parts
            for item in replica
            if isinstance(item.get("sampled_specular_suffix"), dict)
        )
        estimator_config = identity_data.get("transport", {}).get("estimator", {}).get("configuration", {})
        if not suffix_enabled and estimator_config.get("specular_suffix_mode", "exact") == "disabled":
            all_specular = np.asarray(raw_parts, dtype=np.float64)[:, :, COMPONENTS.index("specular")]
        else:
            all_specular = _load_optional_from_diagnostics(
                [list(replica) for replica in diagnostic_parts], _OPTIONAL_ALL_SPECULAR_KEYS, points
            )
    if suffix_transfer is None:
        suffix_transfer = _load_optional_from_diagnostics(
            [list(replica) for replica in diagnostic_parts], _OPTIONAL_SUFFIX_KEYS, points
        )
    return _Campaign(
        root,
        identity,
        identity_data,
        sampling,
        manifest,
        checkpoint,
        seeds,
        points,
        tuple(locations),
        np.stack(raw_parts),
        np.stack(body_parts),
        np.stack(timing_parts),
        tuple(diagnostic_parts),
        all_specular,
        suffix_transfer,
    )


def _db_array(values: np.ndarray) -> np.ndarray:
    result = np.empty(values.shape, dtype=object)
    for index in np.ndindex(values.shape):
        value = float(values[index])
        result[index] = None if value <= 0.0 else float(10.0 * np.log10(value))
    return result


def _db_difference(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    result = np.empty(left.shape, dtype=object)
    for index in np.ndindex(left.shape):
        a, b = float(left[index]), float(right[index])
        result[index] = None if a <= 0.0 or b <= 0.0 else float(10.0 * np.log10(b / a))
    return result


def _plain(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return [_plain(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return _plain(value.item())
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    return value


def _difference(left: np.ndarray, right: np.ndarray) -> dict[str, Any]:
    delta = right - left
    return {
        "iid_linear": _plain(left),
        "rotated_fibonacci_linear": _plain(right),
        "difference_linear": _plain(delta),
        "iid_db": _plain(_db_array(left)),
        "rotated_fibonacci_db": _plain(_db_array(right)),
        "difference_db": _plain(_db_difference(left, right)),
    }


def _route_summary(values: np.ndarray) -> dict[str, float | None]:
    array = np.asarray(values, dtype=np.float64).ravel()
    finite = array[np.isfinite(array)]
    if finite.size == 0:
        return {"count": 0, "minimum": None, "q10": None, "q50": None, "q90": None, "maximum": None}
    return {
        "count": int(finite.size),
        "minimum": float(np.min(finite)),
        "q10": float(np.quantile(finite, 0.10)),
        "q50": float(np.quantile(finite, 0.50)),
        "q90": float(np.quantile(finite, 0.90)),
        "maximum": float(np.max(finite)),
    }


def _route_cdf(left: np.ndarray, right: np.ndarray) -> dict[str, Any]:
    left = np.asarray(left, dtype=np.float64).ravel()
    right = np.asarray(right, dtype=np.float64).ravel()
    if left.shape != right.shape:
        raise CampaignComparisonError("paired route CDF arrays have different lengths")
    quantiles = (0.10, 0.50, 0.90)
    left_db = _db_array(left)
    right_db = _db_array(right)
    difference = right - left
    difference_db = _db_difference(left, right)
    left_positive = left > 0.0
    right_positive = right > 0.0
    linear_wasserstein = float(np.mean(np.abs(np.sort(left) - np.sort(right))))
    db_wasserstein = None
    if np.all(left_positive) and np.all(right_positive):
        db_wasserstein = float(
            np.mean(
                np.abs(np.sort(np.asarray(left_db, dtype=np.float64)) - np.sort(np.asarray(right_db, dtype=np.float64)))
            )
        )
    left_linear = _route_summary(left)
    right_linear = _route_summary(right)
    left_db_summary = _route_summary(np.asarray(left_db, dtype=object)[left_positive].astype(np.float64))
    right_db_summary = _route_summary(np.asarray(right_db, dtype=object)[right_positive].astype(np.float64))
    q_difference_linear = {f"q{int(q * 100)}": float(np.quantile(right, q) - np.quantile(left, q)) for q in quantiles}
    q_difference_db = {
        f"q{int(q * 100)}": (
            None
            if np.quantile(left, q) <= 0.0 or np.quantile(right, q) <= 0.0
            else float(10.0 * np.log10(np.quantile(right, q) / np.quantile(left, q)))
        )
        for q in quantiles
    }
    endpoint_difference_db = _db_difference(
        np.asarray([np.min(left), np.max(left)], dtype=np.float64),
        np.asarray([np.min(right), np.max(right)], dtype=np.float64),
    )
    return {
        "iid": {"linear": left_linear, "db": left_db_summary},
        "rotated_fibonacci": {"linear": right_linear, "db": right_db_summary},
        "difference": {
            "linear": {
                **q_difference_linear,
                "minimum": float(np.min(right) - np.min(left)),
                "maximum": float(np.max(right) - np.max(left)),
            },
            "db": {
                **q_difference_db,
                "minimum": endpoint_difference_db[0],
                "maximum": endpoint_difference_db[1],
            },
        },
        "wasserstein": {"linear": linear_wasserstein, "db": db_wasserstein},
        "paired_point_difference": {"linear": _plain(difference), "db": _plain(difference_db)},
    }


def _ratio_summary(values: np.ndarray) -> dict[str, Any]:
    array = np.asarray(values, dtype=np.float64).ravel()
    finite = array[np.isfinite(array)]
    if finite.size == 0:
        return {"count": 0, "minimum": None, "q10": None, "q50": None, "q90": None, "maximum": None}
    return {
        "count": int(finite.size),
        "minimum": float(np.min(finite)),
        "q10": float(np.quantile(finite, 0.10)),
        "q50": float(np.quantile(finite, 0.50)),
        "q90": float(np.quantile(finite, 0.90)),
        "maximum": float(np.max(finite)),
    }


def _variance_ratio(left: np.ndarray, right: np.ndarray) -> dict[str, Any]:
    if left.shape[0] < 2:
        ratio = np.full(left.shape[1:], np.nan, dtype=np.float64)
    else:
        left_variance = np.var(left, axis=0, ddof=1)
        right_variance = np.var(right, axis=0, ddof=1)
        ratio = np.full(left_variance.shape, np.nan, dtype=np.float64)
        valid = left_variance > 0.0
        ratio[valid] = right_variance[valid] / left_variance[valid]
    return {"by_standpoint": _plain(ratio), "summary": _ratio_summary(ratio)}


def _timing_report(left: np.ndarray, right: np.ndarray) -> dict[str, Any]:
    left_count = np.sum(np.isfinite(left), axis=0)
    right_count = np.sum(np.isfinite(right), axis=0)
    left_mean = np.divide(
        np.nansum(left, axis=0), left_count, out=np.full(left_count.shape, np.nan), where=left_count > 0
    )
    right_mean = np.divide(
        np.nansum(right, axis=0), right_count, out=np.full(right_count.shape, np.nan), where=right_count > 0
    )
    left_finite = left_mean[np.isfinite(left_mean)]
    right_finite = right_mean[np.isfinite(right_mean)]
    return {
        "iid": {
            "by_standpoint_seconds": _plain(left_mean),
            "mean_seconds": None if left_finite.size == 0 else float(np.mean(left_finite)),
            "observations": _plain(left_count),
        },
        "rotated_fibonacci": {
            "by_standpoint_seconds": _plain(right_mean),
            "mean_seconds": None if right_finite.size == 0 else float(np.mean(right_finite)),
            "observations": _plain(right_count),
        },
        "difference_seconds": _plain(right_mean - left_mean),
        "speed_ratio_rotated_over_iid": _plain(
            np.divide(right_mean, left_mean, out=np.full(left_mean.shape, np.nan), where=left_mean > 0.0)
        ),
    }


def _suffix_stats(campaign: _Campaign, look: int) -> dict[str, Any]:
    trials = accepted = candidates = 0
    enabled = False
    for replica in campaign.diagnostics[:look]:
        for diagnostic in replica:
            nested = diagnostic.get("sampled_specular_suffix", {})
            if not isinstance(nested, dict):
                nested = {}
            enabled = enabled or bool(nested.get("enabled", False))
            trials += int(nested.get("trials", 0) or 0)
            accepted += int(nested.get("accepted", diagnostic.get("specular_suffix_accepted", 0)) or 0)
            candidates += int(nested.get("candidates", diagnostic.get("specular_suffix_candidates", 0)) or 0)
    return {
        "enabled": enabled,
        "trials": trials,
        "accepted": accepted,
        "candidates": candidates,
        "acceptance": (float(accepted / trials) if trials else None),
    }


def _suffix_report(left: _Campaign, right: _Campaign, look: int) -> dict[str, Any]:
    left_stats = _suffix_stats(left, look)
    right_stats = _suffix_stats(right, look)
    if left.suffix_transfer is None or right.suffix_transfer is None:
        status = "disabled" if not left_stats["enabled"] and not right_stats["enabled"] else "not_persisted"
        impact: dict[str, Any] = {
            "status": status,
            "note": "the campaign schema does not persist a separate sampled-suffix transfer",
        }
    else:
        left_values = np.mean(left.suffix_transfer[:look], axis=0)
        right_values = np.mean(right.suffix_transfer[:look], axis=0)
        impact = {"status": "available", "transfer": _difference(left_values, right_values)}
    return {"iid": left_stats, "rotated_fibonacci": right_stats, "impact": impact}


def _invariant(left: np.ndarray | None, right: np.ndarray | None, look: int, *, name: str) -> dict[str, Any]:
    if left is None or right is None:
        return {"status": "unavailable", "name": name, "reason": "separate values are not persisted"}
    lhs, rhs = left[:look], right[:look]
    delta = np.asarray(rhs - lhs, dtype=np.float64)
    exact = bool(np.array_equal(lhs, rhs))
    return {
        "status": "pass" if exact else "fail",
        "name": name,
        "exact": exact,
        "max_abs_linear": float(np.max(np.abs(delta))),
        "max_abs_db": _plain(np.nanmax(np.abs(np.asarray(_db_difference(lhs, rhs), dtype=object).astype(float))))
        if np.all(lhs > 0.0) and np.all(rhs > 0.0)
        else None,
    }


def _metric_reports(left: _Campaign, right: _Campaign, look: int) -> tuple[dict[str, Any], dict[str, Any]]:
    left_raw = np.mean(left.raw_transfer[:look], axis=0)
    right_raw = np.mean(right.raw_transfer[:look], axis=0)
    raw = {
        component: _difference(left_raw[:, index], right_raw[:, index]) for index, component in enumerate(COMPONENTS)
    }
    left_body = np.mean(left.body_metrics[:look], axis=0)
    right_body = np.mean(right.body_metrics[:look], axis=0)
    body = {
        component: {
            metric: _difference(
                left_body[:, component_index, metric_index], right_body[:, component_index, metric_index]
            )
            for metric_index, metric in enumerate(BODY_METRICS)
        }
        for component_index, component in enumerate(COMPONENTS)
    }
    return {"raw_transfer": raw, "body_metrics": body}, {
        "raw_transfer": left_raw,
        "body_metrics": left_body,
        "right_raw": right_raw,
        "right_body": right_body,
    }


def _route_reports(
    left_raw: np.ndarray, right_raw: np.ndarray, left_body: np.ndarray, right_body: np.ndarray
) -> dict[str, Any]:
    raw = {component: _route_cdf(left_raw[:, index], right_raw[:, index]) for index, component in enumerate(COMPONENTS)}
    body = {
        component: {
            metric: _route_cdf(
                left_body[:, component_index, metric_index], right_body[:, component_index, metric_index]
            )
            for metric_index, metric in enumerate(BODY_METRICS)
        }
        for component_index, component in enumerate(COMPONENTS)
    }
    return {"raw_transfer": raw, "body_metrics": body}


def _variance_reports(left: _Campaign, right: _Campaign, look: int) -> dict[str, Any]:
    raw = {
        component: _variance_ratio(left.raw_transfer[:look, :, index], right.raw_transfer[:look, :, index])
        for index, component in enumerate(COMPONENTS)
    }
    body = {
        component: {
            metric: _variance_ratio(
                left.body_metrics[:look, :, component_index, metric_index],
                right.body_metrics[:look, :, component_index, metric_index],
            )
            for metric_index, metric in enumerate(BODY_METRICS)
        }
        for component_index, component in enumerate(COMPONENTS)
    }
    return {
        "stochastic_raw_transfer": {name: raw[name] for name in ("specular", "diffuse")},
        "total_raw_transfer": {"total": raw["total"]},
        "body_metrics": body,
        "all_raw_transfer": raw,
    }


def _point_change(previous: np.ndarray, current: np.ndarray) -> dict[str, Any]:
    previous = np.asarray(previous, dtype=np.float64)
    current = np.asarray(current, dtype=np.float64)
    valid = (previous > 0.0) & (current > 0.0)
    absolute_db = np.full(previous.shape, np.nan, dtype=np.float64)
    absolute_db[valid] = np.abs(10.0 * np.log10(current[valid] / previous[valid]))
    finite = absolute_db[np.isfinite(absolute_db)]
    return {
        "by_standpoint_abs_db": _plain(absolute_db),
        "p90_abs_db": None if finite.size == 0 else float(np.quantile(finite, 0.90)),
        "maximum_abs_db": None if finite.size == 0 else float(np.max(finite)),
        "difference_linear": _plain(current - previous),
    }


def _cdf_movement(
    previous: np.ndarray,
    current: np.ndarray,
    *,
    previous_look: int | None = None,
    current_look: int | None = None,
) -> dict[str, Any]:
    report = _route_cdf(previous, current)
    return {
        "from_look": previous_look,
        "to_look": current_look,
        "from": report["iid"],
        "to": report["rotated_fibonacci"],
        "movement": report["difference"],
        "wasserstein": report["wasserstein"],
    }


def _standard_error(values: np.ndarray) -> dict[str, Any]:
    values = np.asarray(values, dtype=np.float64)
    count = values.shape[0]
    if count < 2:
        return {
            "replicas": count,
            "status": "unavailable",
            "reason": "at least two replicas are required for a standard error",
            "by_standpoint_linear": None,
            "by_standpoint_db_delta_approximation": None,
            "p90_linear": None,
            "maximum_linear": None,
            "p90_db_delta_approximation": None,
            "maximum_db_delta_approximation": None,
        }
    mean = np.mean(values, axis=0)
    standard_error = np.std(values, axis=0, ddof=1) / np.sqrt(count)
    db_standard_error = np.full(mean.shape, np.nan, dtype=np.float64)
    positive = mean > 0.0
    db_standard_error[positive] = 10.0 / np.log(10.0) * standard_error[positive] / mean[positive]
    finite_linear = standard_error[np.isfinite(standard_error)]
    finite_db = db_standard_error[np.isfinite(db_standard_error)]
    return {
        "replicas": count,
        "status": "available",
        "by_standpoint_linear": _plain(standard_error),
        "by_standpoint_db_delta_approximation": _plain(db_standard_error),
        "p90_linear": None if finite_linear.size == 0 else float(np.quantile(finite_linear, 0.90)),
        "maximum_linear": None if finite_linear.size == 0 else float(np.max(finite_linear)),
        "p90_db_delta_approximation": None if finite_db.size == 0 else float(np.quantile(finite_db, 0.90)),
        "maximum_db_delta_approximation": None if finite_db.size == 0 else float(np.max(finite_db)),
    }


def _convergence_evidence(campaign: _Campaign, looks: tuple[int, ...]) -> dict[str, Any]:
    scalar_means = {look: np.mean(campaign.raw_transfer[:look, :, COMPONENTS.index("total")], axis=0) for look in looks}
    body_means = {
        look: np.mean(campaign.body_metrics[:look, :, COMPONENTS.index("total"), :], axis=0) for look in looks
    }
    standard_error = {
        str(look): {
            "total_transfer": _standard_error(campaign.raw_transfer[:look, :, COMPONENTS.index("total")]),
            "body_metrics": {
                metric: _standard_error(campaign.body_metrics[:look, :, COMPONENTS.index("total"), index])
                for index, metric in enumerate(BODY_METRICS)
            },
        }
        for look in looks
    }
    changes: dict[str, Any] = {}
    for previous, current in zip(looks, looks[1:]):
        changes[f"{previous}_to_{current}"] = {
            "total_transfer": {
                "pointwise": _point_change(scalar_means[previous], scalar_means[current]),
                "route_cdf": _cdf_movement(
                    scalar_means[previous], scalar_means[current], previous_look=previous, current_look=current
                ),
            },
            "body_metrics": {
                metric: {
                    "pointwise": _point_change(body_means[previous][:, index], body_means[current][:, index]),
                    "route_cdf": _cdf_movement(
                        body_means[previous][:, index],
                        body_means[current][:, index],
                        previous_look=previous,
                        current_look=current,
                    ),
                }
                for index, metric in enumerate(BODY_METRICS)
            },
        }
    return {"standard_error": standard_error, "look_to_look": changes}


def _validate_pair(left: _Campaign, right: _Campaign, looks: tuple[int, ...]) -> None:
    if left.sampling != "iid" or right.sampling != "rotated_fibonacci":
        raise CampaignComparisonError("comparison requires one IID directory and one rotated_fibonacci directory")
    if left.seeds != right.seeds:
        raise CampaignComparisonError(
            f"campaigns are not paired by seed: IID={left.seeds!r}, rotated_fibonacci={right.seeds!r}"
        )
    normal_left, _ = _normalise_launch_sampling(left.identity_data)
    normal_right, _ = _normalise_launch_sampling(right.identity_data)
    if _canonical(normal_left) != _canonical(normal_right):
        raise CampaignComparisonError("campaign identities are incompatible after launch-sampling normalization")
    if left.points != right.points:
        raise CampaignComparisonError("campaigns have different route lengths")
    for lhs, rhs in zip(left.locations, right.locations, strict=True):
        if lhs.get("standpoint") != rhs.get("standpoint") or lhs.get("position_m") != rhs.get("position_m"):
            raise CampaignComparisonError("campaign routes are not paired by standpoint")
    for look in looks:
        if look > len(left.seeds) or look not in left.convergence_looks or look not in right.convergence_looks:
            raise CampaignComparisonError(f"requested look {look} is not common to both completed campaigns")


def compare_campaigns(
    iid_directory: str | Path,
    rotated_fibonacci_directory: str | Path,
    *,
    looks: tuple[int, ...] = (4, 8, 12, 16),
) -> dict[str, Any]:
    """Compare paired IID and rotated-Fibonacci campaign outputs.

    Values are averaged in linear units over the requested seed prefix.  Route
    CDF summaries are reported in both linear and dB units, while dB differences
    are only emitted where both operands are positive.
    """
    requested = tuple(int(look) for look in looks)
    if not requested or tuple(sorted(set(requested))) != requested or requested[0] < 1:
        raise CampaignComparisonError("looks must be unique, increasing, and positive")
    left = _load_campaign(iid_directory)
    right = _load_campaign(rotated_fibonacci_directory)
    _validate_pair(left, right, requested)
    reports: dict[str, Any] = {}
    for look in requested:
        differences, arrays = _metric_reports(left, right, look)
        left_raw = arrays["raw_transfer"]
        right_raw = arrays["right_raw"]
        left_body = arrays["body_metrics"]
        right_body = arrays["right_body"]
        reports[str(look)] = {
            "replicas": look,
            "seeds": list(left.seeds[:look]),
            "linear_db_differences": differences,
            "route_cdf": _route_reports(left_raw, right_raw, left_body, right_body),
            "across_seed_variance_ratios": _variance_reports(left, right, look),
            "component_work_timings": {
                name: _timing_report(left.timings[:look, :, index], right.timings[:look, :, index])
                for index, name in enumerate(TIMING_FIELDS)
            },
            "deterministic_invariants": {
                "direct": _invariant(
                    left.raw_transfer[:, :, COMPONENTS.index("direct")],
                    right.raw_transfer[:, :, COMPONENTS.index("direct")],
                    look,
                    name="direct transfer",
                ),
                "direct_body_metrics": _invariant(
                    left.body_metrics[:, :, COMPONENTS.index("direct"), :],
                    right.body_metrics[:, :, COMPONENTS.index("direct"), :],
                    look,
                    name="direct body metrics",
                ),
                "all_specular": _invariant(
                    left.all_specular_transfer,
                    right.all_specular_transfer,
                    look,
                    name="deterministic all-specular transfer",
                ),
            },
            "sampled_suffix": _suffix_report(left, right, look),
        }
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "campaign_schema_version": SCHEMA_VERSION,
        "iid_directory": str(left.root),
        "rotated_fibonacci_directory": str(right.root),
        "sampling_modes": {"iid": left.sampling, "rotated_fibonacci": right.sampling},
        "compatibility": {
            "compatible": True,
            "identity_sha256": {"iid": left.identity.get("sha256"), "rotated_fibonacci": right.identity.get("sha256")},
            "paired_seeds": list(left.seeds),
            "standpoints": left.points,
        },
        "within_mode_convergence": {
            "iid": _convergence_evidence(left, requested),
            "rotated_fibonacci": _convergence_evidence(right, requested),
        },
        "looks": reports,
    }


def write_report(
    iid_directory: str | Path,
    rotated_fibonacci_directory: str | Path,
    output: str | Path,
    *,
    looks: tuple[int, ...] = (4, 8, 12, 16),
) -> Path:
    """Write :func:`compare_campaigns` as a JSON report."""
    report = compare_campaigns(iid_directory, rotated_fibonacci_directory, looks=looks)
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iid_directory", type=Path)
    parser.add_argument("rotated_fibonacci_directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--looks", default="4,8,12,16", help="comma-separated common replica looks")
    arguments = parser.parse_args(argv)
    try:
        looks = tuple(int(value) for value in arguments.looks.split(",") if value.strip())
        write_report(arguments.iid_directory, arguments.rotated_fibonacci_directory, arguments.output, looks=looks)
    except ValueError as exc:
        parser.error(str(exc))
    return 0


__all__ = ["CampaignComparisonError", "compare_campaigns", "write_report"]


if __name__ == "__main__":
    raise SystemExit(main())
