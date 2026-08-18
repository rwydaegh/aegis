"""Authenticate and report ray-reached semantic-evidence coverage.

The transport replay that feeds this report is deliberately compact.  It keeps
one record per site and standpoint, rather than storing rays or paths::

    {
      "schema": "ray_reached_evidence_replay_v1",
      "authenticated": true,
      "complete": true,
      "identity": {"topology": "first_material_interaction_v1", ...},
      "identity_sha256": "...",
      "source_hashes": {"...": "..."},
      "parity": {"status": "pass", "records": [...]},
      "closure": {"status": "pass", "records": [...]},
      "records": [{
        "site": "Madrid", "standpoint": 0,
        "direct": "N/A",
        "specular": {
          "event_count": 2, "contribution": 0.25,
          "categories": {"atlas_interface": {
            "event_count": 2, "contribution": 0.25,
            "body_coupled": {"mean_sab_w_m2": 0.1,
              "absorbed_power_w": 0.01, "sar_wb_w_kg": 0.0001}} , ...}
        },
        "first_diffuse": {"accepted_event_count": 3, ...}
      }]
    }

All seven category keys are required, including explicit zero entries.  This
prevents a missing classifier state from being mistaken for no coverage.  The
reporter does not run a replay and never writes raw event data.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np

REPORT_SCHEMA = "ray_reached_evidence_coverage_v1"
INPUT_SCHEMA = "ray_reached_evidence_replay_v1"
MANIFEST_SCHEMA = "ray_reached_evidence_coverage_artifacts_v1"

CATEGORIES = (
    "atlas_interface",
    "nonblocking_woody_atlas",
    "geometric_no_panorama_evidence",
    "geometric_evidence_refused_host_compatibility",
    "geometric_evidence_refused_atlas_state",
    "geometric_evidence_refused_insufficient_structural_mass",
    "geometric_fallback_other",
)
PANORAMA_INFORMED = frozenset(("atlas_interface", "nonblocking_woody_atlas"))
GEOMETRIC_FALLBACK = frozenset(CATEGORIES) - PANORAMA_INFORMED
FAMILIES = ("specular", "first_diffuse")
BODY_FIELDS = ("mean_sab_w_m2", "absorbed_power_w", "sar_wb_w_kg")
AUDIT_REPLAY_SCHEMA = "aegis.ray-reached-evidence-audit-replay"
BODY_METRIC_NAMES = (
    "arriving_power_density_w_m2",
    "susceptibility",
    "peak_sab_w_m2",
    "mean_sab_w_m2",
    "absorbed_power_w",
    "sar_wb_w_kg",
)
AUDIT_BODY_INDICES = {"mean_sab_w_m2": 3, "absorbed_power_w": 4, "sar_wb_w_kg": 5}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ATOL = 1.0e-12
_RTOL = 2.0e-9


class RayReachedEvidenceCoverageError(ValueError):
    """The replay result is unauthenticated, incomplete, or internally inconsistent."""


@dataclass(frozen=True)
class RayReachedEvidenceCoverageArtifacts:
    """Paths written by :func:`write_ray_reached_evidence_coverage`."""

    json: Path
    csv: Path
    pdf: Path
    png: Path
    manifest: Path


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fail(message: str) -> None:
    raise RayReachedEvidenceCoverageError(message)


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(f"{label} must be an object")
    return value


def _finite_nonnegative(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(f"{label} must be a finite nonnegative number")
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        _fail(f"{label} must be a finite nonnegative number")
    return result


def _nonnegative_count(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        _fail(f"{label} must be a nonnegative integer")
    return int(value)


def _close(actual: float, expected: float) -> bool:
    return bool(math.isclose(actual, expected, rel_tol=_RTOL, abs_tol=_ATOL))


def _require_sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        _fail(f"{label} must be a lowercase SHA-256 digest")
    return value


def _normalise_input_document(value: Any) -> dict[str, Any]:
    document = dict(_mapping(value, "replay result"))
    if document.get("schema") != INPUT_SCHEMA and document.get("schema_version") != INPUT_SCHEMA:
        _fail(f"replay result schema must be {INPUT_SCHEMA!r}")
    if document.get("authenticated") is not True:
        _fail("replay result is not authenticated")
    if document.get("complete") is not True:
        _fail("replay result is incomplete")
    identity = _mapping(document.get("identity"), "identity")
    identity_hash = _require_sha(document.get("identity_sha256"), "identity_sha256")
    if identity_hash != _sha256_bytes(_canonical(identity)):
        _fail("identity_sha256 does not authenticate identity")
    source_hashes = _mapping(document.get("source_hashes"), "source_hashes")
    if not source_hashes:
        _fail("replay result must carry source hashes")
    for name, digest in source_hashes.items():
        if not isinstance(name, str) or not name:
            _fail("source hash names must be nonempty strings")
        _require_sha(digest, f"source_hashes[{name!r}]")

    for name in ("parity", "closure"):
        check = _mapping(document.get(name), name)
        if check.get("status") != "pass":
            _fail(f"{name} check must have status='pass'")
        records = check.get("records")
        if not isinstance(records, list) or not records:
            _fail(f"{name}.records must be a non-empty list")
        for index, record in enumerate(records):
            if not isinstance(record, Mapping):
                _fail(f"{name}.records[{index}] must be an object")

    records = document.get("records")
    if not isinstance(records, list) or not records:
        _fail("replay result records must be a non-empty list")
    document["identity"] = dict(identity)
    document["source_hashes"] = dict(source_hashes)
    return document


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        _fail(f"could not read replay result {path}: {error}")
    return _normalise_input_document(value)


def _manifest_file_records(manifest: Mapping[str, Any]) -> dict[str, str]:
    files = manifest.get("files")
    if isinstance(files, Mapping):
        records = files.items()
    elif isinstance(files, list):
        records = ((item.get("path"), item.get("sha256")) for item in files if isinstance(item, Mapping))
    else:
        _fail("input manifest files must be a list or object")
    result: dict[str, str] = {}
    for name, digest in records:
        if not isinstance(name, str):
            _fail("input manifest file paths must be strings")
        result[name] = _require_sha(digest, f"input manifest files[{name!r}]")
    if not result:
        _fail("input manifest has no file records")
    return result


def _audit_manifest(path: Path) -> tuple[dict[str, Any], dict[str, str]]:
    try:
        manifest = _mapping(json.loads(path.read_text(encoding="utf-8")), f"audit manifest {path}")
    except (OSError, json.JSONDecodeError) as error:
        _fail(f"could not read audit manifest {path}: {error}")
    if manifest.get("schema") != AUDIT_REPLAY_SCHEMA:
        _fail(f"audit manifest {path} has an unexpected schema")
    files = _manifest_file_records(manifest)
    for relative, digest in files.items():
        target = (path.parent / relative).resolve()
        if not target.is_relative_to(path.parent.resolve()):
            _fail(f"audit manifest path escapes its artifact directory: {relative}")
        if not target.is_file() or _sha256(target) != digest:
            _fail(f"audit replay artifact failed its manifest hash: {target}")
    return dict(manifest), files


def _audit_identity(path: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    try:
        wrapper = _mapping(json.loads(path.read_text(encoding="utf-8")), f"audit identity {path}")
    except (OSError, json.JSONDecodeError) as error:
        _fail(f"could not read audit identity {path}: {error}")
    digest = _require_sha(wrapper.get("sha256"), f"audit identity {path}.sha256")
    data = _mapping(wrapper.get("data"), f"audit identity {path}.data")
    if digest != _sha256_bytes(_canonical(data)) or digest != manifest.get("identity_sha256"):
        _fail(f"audit identity is not authenticated: {path}")
    if tuple(data.get("category_names", ())) != CATEGORIES:
        _fail(f"audit identity category vocabulary differs from the production vocabulary: {path}")
    return dict(data)


def _source_shard(source_root: Path, seed: int) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    try:
        index = _mapping(
            json.loads((source_root / "checkpoint" / "index.json").read_text(encoding="utf-8")), "checkpoint index"
        )
    except (OSError, json.JSONDecodeError) as error:
        _fail(f"could not read source checkpoint index {source_root}: {error}")
    entry = next(
        (item for item in index.get("committed", []) if isinstance(item, Mapping) and item.get("seed") == seed), None
    )
    if entry is None or not isinstance(entry.get("path"), str):
        _fail(f"source checkpoint has no committed seed {seed}: {source_root}")
    path = source_root / "checkpoint" / str(entry["path"])
    if not path.is_file() or _sha256(path) != entry.get("sha256"):
        _fail(f"source checkpoint shard failed authentication: {path}")
    try:
        with np.load(path, allow_pickle=False) as payload:
            arrays = {name: np.asarray(payload[name], dtype=np.float64) for name in payload.files}
    except (OSError, ValueError) as error:
        _fail(f"could not read source checkpoint shard {path}: {error}")
    return arrays, dict(index)


def _source_info(identity: Mapping[str, Any], site_root: Path) -> tuple[Path, dict[str, str]]:
    source = _mapping(identity.get("source"), f"{site_root}/audit_identity source")
    campaign = Path(str(source.get("source_campaign", ""))).expanduser().resolve()
    config = Path(str(source.get("source_config", ""))).expanduser().resolve()
    if not campaign.is_dir() or not config.is_file():
        _fail(f"audit source campaign/config is unavailable for {site_root}")
    records = {
        "source_identity": _require_sha(source.get("source_identity_sha256"), "source identity hash"),
        "source_manifest": _require_sha(source.get("source_manifest_sha256"), "source manifest hash"),
        "source_config": _require_sha(source.get("source_config_sha256"), "source config hash"),
    }
    identity_path = campaign / "campaign_identity.json"
    manifest_path = campaign / "manifest.json"
    try:
        source_identity = _mapping(json.loads(identity_path.read_text(encoding="utf-8")), "source campaign identity")
    except (OSError, json.JSONDecodeError) as error:
        _fail(f"could not read sealed source identity {identity_path}: {error}")
    source_identity_data = source_identity.get("data")
    if (
        not identity_path.is_file()
        or source_identity.get("sha256") != records["source_identity"]
        or not isinstance(source_identity_data, Mapping)
        or _sha256_bytes(_canonical(source_identity_data)) != records["source_identity"]
    ):
        _fail(f"sealed source identity failed authentication: {identity_path}")
    if not manifest_path.is_file() or _sha256(manifest_path) != records["source_manifest"]:
        _fail(f"sealed source manifest failed authentication: {manifest_path}")
    if _sha256(config) != records["source_config"]:
        _fail(f"sealed source config failed authentication: {config}")
    try:
        source_manifest = _mapping(json.loads(manifest_path.read_text(encoding="utf-8")), "sealed source manifest")
    except (OSError, json.JSONDecodeError) as error:
        _fail(f"could not read sealed source manifest {manifest_path}: {error}")
    source_files = _manifest_file_records(source_manifest)
    for relative in ("campaign_identity.json", "locations.jsonl", "checkpoint/index.json"):
        target = campaign / relative
        digest = source_files.get(relative)
        if digest is None or not target.is_file() or _sha256(target) != digest:
            _fail(f"sealed source artifact failed authentication: {target}")
    return campaign, records


def _load_audit_replay(root: Path) -> tuple[dict[str, Any], str]:
    """Convert the replay directory's NPZ reductions into reporter schema."""
    root_manifest, root_files = _audit_manifest(root / "manifest.json")
    names = root_manifest.get("category_names")
    if tuple(names or ()) != CATEGORIES:
        _fail("audit replay root manifest category vocabulary differs from the production vocabulary")
    site_manifest_paths = sorted(path for path in root_files if path.endswith("/manifest.json"))
    if not site_manifest_paths:
        _fail("audit replay root manifest contains no site manifests")
    records: list[dict[str, Any]] = []
    parity_records: list[dict[str, Any]] = []
    closure_records: list[dict[str, Any]] = []
    site_identities: dict[str, str] = {}
    configurations: dict[str, dict[str, Any]] = {}
    source_hashes: dict[str, str] = {}
    for relative_manifest in site_manifest_paths:
        site_root = root / relative_manifest.rsplit("/", 1)[0]
        site_manifest, site_files = _audit_manifest(site_root / "manifest.json")
        identity_path = site_root / "audit_identity.json"
        if "audit_identity.json" not in site_files:
            _fail(f"site manifest omits audit_identity.json: {site_root}")
        identity = _audit_identity(identity_path, site_manifest)
        source_root, source_hashes_for_site = _source_info(identity, site_root)
        site = str(identity.get("source", {}).get("site", ""))
        if not site:
            _fail(f"audit identity has no site: {identity_path}")
        if site in site_identities:
            _fail(f"audit replay contains duplicate site identity: {site}")
        site_identities[site] = str(site_manifest["identity_sha256"])
        audit_configuration = identity.get("audit_configuration")
        if not isinstance(audit_configuration, Mapping):
            _fail(f"audit identity has no exact audit configuration: {identity_path}")
        configurations[site] = dict(audit_configuration)
        source_hashes.update({f"{site}/{key}": value for key, value in source_hashes_for_site.items()})
        seeds = identity.get("source", {}).get("seeds")
        points_count = identity.get("source", {}).get("standpoints")
        if seeds != list(range(7, 23)):
            _fail(f"audit identity has no complete seed list: {identity_path}")
        if not isinstance(points_count, int) or points_count < 1:
            _fail(f"audit identity has no valid standpoint count: {identity_path}")
        record_paths = sorted(path for path in site_files if path.startswith("records/") and path.endswith(".npz"))
        if len(record_paths) != len(seeds):
            _fail(f"audit replay is incomplete for {site}: {len(record_paths)} records for {len(seeds)} seeds")
        locations_path = source_root / "locations.jsonl"
        try:
            locations = [
                json.loads(line) for line in locations_path.read_text(encoding="utf-8").splitlines() if line.strip()
            ]
        except (OSError, json.JSONDecodeError) as error:
            _fail(f"could not read source locations for {site}: {error}")
        if not all(isinstance(location, Mapping) for location in locations):
            _fail(f"source locations are not JSON objects for {site}")
        if len(locations) != points_count:
            _fail(f"source location count does not match replay for {site}")
        sums = {
            "diffuse_event_count": np.zeros((points_count, len(CATEGORIES)), dtype=np.int64),
            "diffuse_transfer": np.zeros((points_count, len(CATEGORIES)), dtype=np.float64),
            "specular_event_count": np.zeros((points_count, len(CATEGORIES)), dtype=np.int64),
            "specular_transfer": np.zeros((points_count, len(CATEGORIES)), dtype=np.float64),
            "specular_body_metrics": np.zeros(
                (points_count, len(CATEGORIES), len(BODY_METRIC_NAMES)), dtype=np.float64
            ),
            "first_diffuse_body_metrics": np.zeros(
                (points_count, len(CATEGORIES), len(BODY_METRIC_NAMES)), dtype=np.float64
            ),
        }
        max_raw_residual = 0.0
        max_body_residual = 0.0
        for record_path, seed in zip(record_paths, seeds, strict=True):
            with np.load(site_root / record_path, allow_pickle=False) as payload:
                base_names = set(sums) - {"specular_body_metrics", "first_diffuse_body_metrics"}
                expected_names = base_names | {"diffuse_local_cell_mass", "body_coupling_seconds"}
                split_body_names = {"specular_body_metrics", "first_diffuse_body_metrics"}
                if not (
                    set(payload.files) == expected_names or set(payload.files) == expected_names | split_body_names
                ):
                    _fail(f"audit record has incomplete fields: {site_root / record_path}")
                arrays = {name: np.asarray(payload[name]) for name in payload.files}
            expected_shapes = {
                "diffuse_event_count": (points_count, len(CATEGORIES)),
                "diffuse_transfer": (points_count, len(CATEGORIES)),
                "specular_event_count": (points_count, len(CATEGORIES)),
                "specular_transfer": (points_count, len(CATEGORIES)),
            }
            for name, shape in expected_shapes.items():
                if arrays[name].shape != shape or np.any(~np.isfinite(arrays[name])) or np.any(arrays[name] < 0.0):
                    _fail(f"audit record field {name} is invalid: {site_root / record_path}")
            diffuse_field = arrays["diffuse_local_cell_mass"]
            if (
                diffuse_field.ndim != 3
                or diffuse_field.shape[:2] != (points_count, len(CATEGORIES))
                or np.any(~np.isfinite(diffuse_field))
                or np.any(diffuse_field < 0.0)
            ):
                _fail(f"audit diffuse field reduction is invalid: {site_root / record_path}")
            timing = arrays["body_coupling_seconds"]
            if timing.shape != (points_count,) or np.any(~np.isfinite(timing)) or np.any(timing < 0.0):
                _fail(f"audit body timing reduction is invalid: {site_root / record_path}")
            has_split_body = "specular_body_metrics" in arrays
            if has_split_body:
                for name in ("specular_body_metrics", "first_diffuse_body_metrics"):
                    split_shape = (points_count, len(CATEGORIES), len(BODY_METRIC_NAMES))
                    if (
                        arrays[name].shape != split_shape
                        or np.any(~np.isfinite(arrays[name]))
                        or np.any(arrays[name] < 0.0)
                    ):
                        _fail(f"audit split body field {name} is invalid: {site_root / record_path}")
            else:
                _fail(
                    "audit replay does not retain separate specular and first-diffuse body metrics. "
                    "The reporter refuses combined category body fields because the family split cannot be inferred."
                )
            if (
                arrays["diffuse_event_count"].dtype.kind not in "iu"
                or arrays["specular_event_count"].dtype.kind not in "iu"
            ):
                _fail(f"audit event counts must be integral: {site_root / record_path}")
            sums["diffuse_event_count"] += arrays["diffuse_event_count"].astype(np.int64)
            sums["diffuse_transfer"] += arrays["diffuse_transfer"].astype(np.float64)
            sums["specular_event_count"] += arrays["specular_event_count"].astype(np.int64)
            sums["specular_transfer"] += arrays["specular_transfer"].astype(np.float64)
            sums["specular_body_metrics"] += arrays["specular_body_metrics"].astype(np.float64)
            sums["first_diffuse_body_metrics"] += arrays["first_diffuse_body_metrics"].astype(np.float64)
            source_arrays, _ = _source_shard(source_root, seed)
            if source_arrays.get("raw_transfer", np.empty(0)).shape != (points_count, 4):
                _fail(f"source raw transfer shape is invalid for {site}, seed {seed}")
            if source_arrays.get("body_metrics", np.empty(0)).shape != (points_count, 4, len(BODY_METRIC_NAMES)):
                _fail(f"source body metric shape is invalid for {site}, seed {seed}")
            for point_index in range(points_count):
                raw = source_arrays["raw_transfer"][point_index]
                diffuse_residual = float(arrays["diffuse_transfer"][point_index].sum() - raw[2])
                specular_residual = float(arrays["specular_transfer"][point_index].sum() - raw[1])
                total_residual = float(raw[3] - raw[:3].sum())
                max_raw_residual = max(
                    max_raw_residual, abs(diffuse_residual), abs(specular_residual), abs(total_residual)
                )
                body_expected = source_arrays["body_metrics"][point_index]
                for field_name, metric_index in AUDIT_BODY_INDICES.items():
                    spec_body = float(
                        arrays["specular_body_metrics"][point_index, :, metric_index].sum()
                        - body_expected[1, metric_index]
                    )
                    diff_body = float(
                        arrays["first_diffuse_body_metrics"][point_index, :, metric_index].sum()
                        - body_expected[2, metric_index]
                    )
                    max_body_residual = max(max_body_residual, abs(spec_body), abs(diff_body))
        if max_raw_residual > 2.0e-10 or max_body_residual > 2.0e-10:
            _fail(f"audit replay parity/closure failed for {site}: raw={max_raw_residual}, body={max_body_residual}")
        for point_index, location in enumerate(locations):

            def family(prefix: str, diffuse: bool) -> dict[str, Any]:
                count_key = f"{prefix}_event_count"
                transfer_key = f"{prefix}_transfer"
                body_metric = sums[f"{'first_diffuse' if diffuse else 'specular'}_body_metrics"][point_index]
                categories = {}
                for category_index, category in enumerate(CATEGORIES):
                    categories[category] = {
                        "event_count": int(sums[count_key][point_index, category_index]),
                        "contribution": float(sums[transfer_key][point_index, category_index]),
                        "body_coupled": {
                            field_name: float(body_metric[category_index, metric_index])
                            for field_name, metric_index in AUDIT_BODY_INDICES.items()
                        },
                    }
                return {
                    "accepted_event_count" if diffuse else "event_count": int(sums[count_key][point_index].sum()),
                    "contribution": float(sums[transfer_key][point_index].sum()),
                    "body_coupled": {
                        field_name: float(body_metric[:, metric_index].sum())
                        for field_name, metric_index in AUDIT_BODY_INDICES.items()
                    },
                    "categories": categories,
                }

            records.append(
                {
                    "site": site,
                    "standpoint": point_index,
                    "route_distance_m": location.get("route_distance_m"),
                    "direct": "N/A",
                    "specular": family("specular", False),
                    "first_diffuse": family("diffuse", True),
                }
            )
            parity_records.append(
                {"site": site, "standpoint": point_index, "status": "pass", "max_abs_residual": max_raw_residual}
            )
            closure_records.append(
                {
                    "site": site,
                    "standpoint": point_index,
                    "status": "pass",
                    "max_abs_residual": max(max_raw_residual, max_body_residual),
                }
            )
    identity = {
        "schema": AUDIT_REPLAY_SCHEMA,
        "version": 1,
        "site_identities": site_identities,
        "configurations": configurations,
        "category_names": list(CATEGORIES),
    }
    document = {
        "schema": INPUT_SCHEMA,
        "authenticated": True,
        "complete": True,
        "identity": identity,
        "identity_sha256": _sha256_bytes(_canonical(identity)),
        "configuration": {"sites": configurations},
        "source_hashes": source_hashes,
        "parity": {"status": "pass", "records": parity_records, "rule": "replay reductions match sealed scalar shards"},
        "closure": {
            "status": "pass",
            "records": closure_records,
            "rule": "category counts, transfer, and additive body fields close",
        },
        "records": records,
    }
    return document, _sha256(root / "manifest.json")


def _load_input(path: str | Path) -> tuple[dict[str, Any], Path, str]:
    root = Path(path).expanduser().resolve()
    if root.is_dir():
        root_manifest_path = root / "manifest.json"
        if root_manifest_path.is_file():
            try:
                root_manifest_value = json.loads(root_manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                _fail(f"could not read input manifest {root_manifest_path}: {error}")
            if isinstance(root_manifest_value, Mapping) and root_manifest_value.get("schema") == AUDIT_REPLAY_SCHEMA:
                document, manifest_hash = _load_audit_replay(root)
                return _normalise_input_document(document), root_manifest_path, manifest_hash
        candidates = [root / "ray_reached_evidence_replay.json", root / "replay_result.json"]
        replay = next((candidate for candidate in candidates if candidate.is_file()), None)
        if replay is None:
            json_files = sorted(root.glob("*.json"))
            replay = next((candidate for candidate in json_files if "manifest" not in candidate.name), None)
        manifest_path = root / "manifest.json"
        if replay is None or not manifest_path.is_file():
            _fail("input directory must contain a replay JSON and manifest.json")
        try:
            manifest = _mapping(json.loads(manifest_path.read_text(encoding="utf-8")), "input manifest")
        except (OSError, json.JSONDecodeError) as error:
            _fail(f"could not read input manifest {manifest_path}: {error}")
        records = _manifest_file_records(manifest)
        relative = replay.relative_to(root).as_posix()
        if relative not in records or records[relative] != _sha256(replay):
            _fail("input replay JSON does not match its manifest hash")
        return _read_json(replay), replay, _sha256(replay)
    if not root.is_file():
        _fail(f"replay result does not exist: {root}")
    return _read_json(root), root, _sha256(root)


def _body(value: Any, label: str) -> dict[str, float]:
    body = _mapping(value, label)
    result = {name: _finite_nonnegative(body.get(name), f"{label}.{name}") for name in BODY_FIELDS}
    return result


def _value_alias(mapping: Mapping[str, Any], names: Iterable[str], label: str) -> Any:
    for name in names:
        if name in mapping:
            return mapping[name]
    _fail(f"{label} is missing")


def _family(value: Any, label: str, *, diffuse: bool) -> dict[str, Any]:
    family = _mapping(value, label)
    count = _nonnegative_count(
        _value_alias(
            family,
            ("accepted_event_count", "accepted_events", "event_count", "events", "count")
            if diffuse
            else ("event_count", "events", "count", "accepted_event_count"),
            f"{label}.event_count",
        ),
        f"{label}.event_count",
    )
    contribution = _finite_nonnegative(
        _value_alias(
            family,
            ("transport_contribution", "contribution", "contribution_m_inv2", "mass"),
            f"{label}.contribution",
        ),
        f"{label}.contribution",
    )
    categories = _mapping(family.get("categories"), f"{label}.categories")
    if set(categories) != set(CATEGORIES):
        missing = sorted(set(CATEGORIES) - set(categories))
        extra = sorted(set(categories) - set(CATEGORIES))
        _fail(f"{label}.categories must contain exactly the seven production states; missing={missing}, extra={extra}")
    normalised: dict[str, dict[str, Any]] = {}
    total_count = 0
    total_contribution = 0.0
    total_body = dict.fromkeys(BODY_FIELDS, 0.0)
    for category in CATEGORIES:
        item = _mapping(categories[category], f"{label}.categories.{category}")
        item_count = _nonnegative_count(
            _value_alias(
                item,
                ("accepted_event_count", "accepted_events", "event_count", "events", "count"),
                f"{label}.categories.{category}.event_count",
            ),
            f"{label}.categories.{category}.event_count",
        )
        item_contribution = _finite_nonnegative(
            _value_alias(
                item,
                ("transport_contribution", "contribution", "contribution_m_inv2", "mass"),
                f"{label}.categories.{category}.contribution",
            ),
            f"{label}.categories.{category}.contribution",
        )
        item_body = _body(
            _value_alias(item, ("body_coupled", "body", "body_metrics"), f"{label}.categories.{category}.body_coupled"),
            f"{label}.categories.{category}.body_coupled",
        )
        normalised[category] = {
            "event_count": item_count,
            "count": item_count,
            "transport_contribution": item_contribution,
            "contribution": item_contribution,
            "body_coupled": item_body,
        }
        if diffuse:
            normalised[category]["accepted_event_count"] = item_count
        total_count += item_count
        total_contribution += item_contribution
        for name in BODY_FIELDS:
            total_body[name] += item_body[name]
    family_body = _body(
        _value_alias(family, ("body_coupled", "body", "body_metrics"), f"{label}.body_coupled"),
        f"{label}.body_coupled",
    )
    if total_count != count:
        _fail(f"{label} category event closure failed: {total_count} != {count}")
    if not _close(total_contribution, contribution):
        _fail(f"{label} category contribution closure failed: {total_contribution} != {contribution}")
    for name in BODY_FIELDS:
        if not _close(total_body[name], family_body[name]):
            _fail(f"{label} category body closure failed for {name}: {total_body[name]} != {family_body[name]}")
    result = {
        "event_count": count,
        "count": count,
        "transport_contribution": contribution,
        "contribution": contribution,
        "categories": normalised,
        "body_coupled": family_body,
    }
    if diffuse:
        result["accepted_event_count"] = count
    return result


def _point(record: Any, index: int) -> dict[str, Any]:
    raw = _mapping(record, f"records[{index}]")
    site = raw.get("site")
    standpoint = raw.get("standpoint")
    if not isinstance(site, str) or not site:
        _fail(f"records[{index}].site must be a nonempty string")
    if isinstance(standpoint, bool) or not isinstance(standpoint, int) or standpoint < 0:
        _fail(f"records[{index}].standpoint must be a nonnegative integer")
    direct = raw.get("direct")
    if direct != "N/A":
        _fail(f"records[{index}].direct must be explicitly N/A")
    specular = _family(raw.get("specular", raw.get("all_specular")), f"records[{index}].specular", diffuse=False)
    diffuse = _family(raw.get("first_diffuse", raw.get("diffuse")), f"records[{index}].first_diffuse", diffuse=True)
    site_distance = raw.get("route_distance_m")
    if site_distance is not None:
        site_distance = _finite_nonnegative(site_distance, f"records[{index}].route_distance_m")
    closure = raw.get("closure")
    if closure is not None and not isinstance(closure, Mapping):
        _fail(f"records[{index}].closure must be an object")
    return {
        "site": site,
        "standpoint": int(standpoint),
        "route_distance_m": site_distance,
        "direct": "N/A",
        "specular": specular,
        "first_diffuse": diffuse,
        "closure": dict(closure) if isinstance(closure, Mapping) else None,
    }


def _empty_body() -> dict[str, float]:
    return dict.fromkeys(BODY_FIELDS, 0.0)


def _aggregate(points: list[dict[str, Any]], family_name: str) -> dict[str, Any]:
    total_count = 0
    total_contribution = 0.0
    body = _empty_body()
    categories = {
        category: {
            "event_count": 0,
            "count": 0,
            "transport_contribution": 0.0,
            "contribution": 0.0,
            "body_coupled": _empty_body(),
        }
        for category in CATEGORIES
    }
    for point in points:
        family = point[family_name]
        total_count += family["event_count"]
        total_contribution += family["transport_contribution"]
        for name in BODY_FIELDS:
            body[name] += family["body_coupled"][name]
        for category in CATEGORIES:
            source = family["categories"][category]
            target = categories[category]
            target["event_count"] += source["event_count"]
            target["count"] += source["event_count"]
            target["transport_contribution"] += source["transport_contribution"]
            target["contribution"] += source["transport_contribution"]
            for name in BODY_FIELDS:
                target["body_coupled"][name] += source["body_coupled"][name]
    result = {
        "event_count": total_count,
        "count": total_count,
        "transport_contribution": total_contribution,
        "contribution": total_contribution,
        "categories": categories,
        "body_coupled": body,
    }
    if family_name == "first_diffuse":
        result["accepted_event_count"] = total_count
    return result


def _shares(family: dict[str, Any]) -> dict[str, Any]:
    contribution = family["transport_contribution"]
    body = family["body_coupled"]
    categories: dict[str, Any] = {}
    for category in CATEGORIES:
        item = family["categories"][category]
        categories[category] = {
            **item,
            "transport_fraction": (item["transport_contribution"] / contribution if contribution > 0.0 else 0.0),
            "body_fraction": {
                name: (item["body_coupled"][name] / body[name] if body[name] > 0.0 else 0.0) for name in BODY_FIELDS
            },
        }
    return {**family, "categories": categories}


def _non_direct(specular: dict[str, Any], diffuse: dict[str, Any]) -> dict[str, Any]:
    result = {
        "event_count": specular["event_count"] + diffuse["event_count"],
        "count": specular["event_count"] + diffuse["event_count"],
        "transport_contribution": specular["transport_contribution"] + diffuse["transport_contribution"],
        "contribution": specular["transport_contribution"] + diffuse["transport_contribution"],
        "categories": {},
        "body_coupled": _empty_body(),
    }
    for name in BODY_FIELDS:
        result["body_coupled"][name] = specular["body_coupled"][name] + diffuse["body_coupled"][name]
    for category in CATEGORIES:
        result["categories"][category] = {
            "event_count": specular["categories"][category]["event_count"]
            + diffuse["categories"][category]["event_count"],
            "count": specular["categories"][category]["event_count"] + diffuse["categories"][category]["event_count"],
            "transport_contribution": specular["categories"][category]["transport_contribution"]
            + diffuse["categories"][category]["transport_contribution"],
            "contribution": specular["categories"][category]["transport_contribution"]
            + diffuse["categories"][category]["transport_contribution"],
            "body_coupled": {
                name: specular["categories"][category]["body_coupled"][name]
                + diffuse["categories"][category]["body_coupled"][name]
                for name in BODY_FIELDS
            },
        }
    return result


def _check_unique_points(points: list[dict[str, Any]]) -> None:
    keys = [(point["site"], point["standpoint"]) for point in points]
    if len(keys) != len(set(keys)):
        _fail("replay result contains duplicate site/standpoint records")


def _record_parity_and_closure(document: Mapping[str, Any], points: list[dict[str, Any]]) -> dict[str, Any]:
    expected = {(point["site"], point["standpoint"]) for point in points}
    for name in ("parity", "closure"):
        records = _mapping(document[name], name)["records"]
        keys: set[tuple[str, int]] = set()
        for index, value in enumerate(records):
            if not isinstance(value, Mapping):
                _fail(f"{name}.records[{index}] must be an object")
            site, standpoint = value.get("site"), value.get("standpoint")
            if not isinstance(site, str) or not isinstance(standpoint, int) or isinstance(standpoint, bool):
                _fail(f"{name}.records[{index}] must identify site and standpoint")
            key = (site, standpoint)
            keys.add(key)
            if value.get("status") not in (None, "pass"):
                _fail(f"{name}.records[{index}] is not passing")
        if not expected.issubset(keys):
            _fail(f"{name}.records is missing site/standpoint entries")
    return {"parity": dict(document["parity"]), "closure": dict(document["closure"])}


def build_report(document: Mapping[str, Any]) -> dict[str, Any]:
    """Validate an authenticated replay document and build compact coverage data."""
    source = _normalise_input_document(document)
    points = [_point(record, index) for index, record in enumerate(source["records"])]
    _check_unique_points(points)
    checks = _record_parity_and_closure(source, points)
    sites = sorted({point["site"] for point in points})
    specular = _aggregate(points, "specular")
    diffuse = _aggregate(points, "first_diffuse")
    non_direct = _non_direct(specular, diffuse)
    for point in points:
        point["specular"] = _shares(point["specular"])
        point["first_diffuse"] = _shares(point["first_diffuse"])
        point["non_direct"] = _shares(_non_direct(point["specular"], point["first_diffuse"]))
    pooled = {
        "direct": {"status": "N/A", "reason": "direct transport has no material interaction"},
        "specular": _shares(specular),
        "first_diffuse": _shares(diffuse),
        "non_direct": _shares(non_direct),
    }
    informed = sum(non_direct["categories"][category]["body_coupled"]["sar_wb_w_kg"] for category in PANORAMA_INFORMED)
    fallback = sum(non_direct["categories"][category]["body_coupled"]["sar_wb_w_kg"] for category in GEOMETRIC_FALLBACK)
    total_body = non_direct["body_coupled"]["sar_wb_w_kg"]
    headline = {
        "denominator": "retained modeled non-direct body-coupled contribution",
        "panorama_informed_sar_fraction": informed / total_body if total_body > 0.0 else 0.0,
        "geometric_fallback_sar_fraction": fallback / total_body if total_body > 0.0 else 0.0,
        "panorama_informed_categories": sorted(PANORAMA_INFORMED),
        "geometric_fallback_categories": sorted(GEOMETRIC_FALLBACK),
    }
    report = {
        "schema": REPORT_SCHEMA,
        "authenticated": True,
        "complete": True,
        "input_schema": INPUT_SCHEMA,
        "identity": source["identity"],
        "identity_sha256": source["identity_sha256"],
        "source_hashes": source["source_hashes"],
        "configuration": source.get("configuration", {}),
        "categories": list(CATEGORIES),
        "sites": sites,
        "standpoints": len(points),
        "checks": checks,
        "headline": headline,
        "pooled": pooled,
        "records": points,
    }
    report["payload_sha256"] = _sha256_bytes(
        _canonical({key: value for key, value in report.items() if key != "payload_sha256"})
    )
    return report


def _csv_rows(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    fields = (
        "scope",
        "site",
        "standpoint",
        "component",
        "category",
        "event_count",
        "transport_contribution",
        "transport_fraction",
        "mean_sab_w_m2",
        "absorbed_power_w",
        "sar_wb_w_kg",
        "body_fraction_sar_wb_w_kg",
        "status",
    )
    rows: list[dict[str, Any]] = []

    def add(scope: str, site: str, standpoint: int | str, component: str, value: Any, category: str) -> None:
        if value == "N/A":
            rows.append(
                {field: ("N/A" if field in fields[5:] else value) for field in fields}
                | {
                    "scope": scope,
                    "site": site,
                    "standpoint": standpoint,
                    "component": component,
                    "category": category,
                    "status": "N/A",
                }
            )
            return
        item = value["categories"][category] if category != "__total__" else value
        rows.append(
            {
                "scope": scope,
                "site": site,
                "standpoint": standpoint,
                "component": component,
                "category": category,
                "event_count": item["event_count"],
                "transport_contribution": item["transport_contribution"],
                "transport_fraction": item.get("transport_fraction", "N/A"),
                "mean_sab_w_m2": item["body_coupled"]["mean_sab_w_m2"],
                "absorbed_power_w": item["body_coupled"]["absorbed_power_w"],
                "sar_wb_w_kg": item["body_coupled"]["sar_wb_w_kg"],
                "body_fraction_sar_wb_w_kg": item.get("body_fraction", {}).get("sar_wb_w_kg", "N/A"),
                "status": "pass",
            }
        )

    for point in report["records"]:
        for component in ("direct", "specular", "first_diffuse", "non_direct"):
            value = point[component] if component == "direct" else point[component]
            if component == "direct":
                add("standpoint", point["site"], point["standpoint"], component, "N/A", "N/A")
            else:
                for category in CATEGORIES:
                    family = value
                    add("standpoint", point["site"], point["standpoint"], component, family, category)
    for component in ("direct", "specular", "first_diffuse", "non_direct"):
        if component == "direct":
            add("pooled", "__pooled__", "__pooled__", component, "N/A", "N/A")
        else:
            family = report["pooled"][component]
            for category in CATEGORIES:
                add("pooled", "__pooled__", "__pooled__", component, family, category)
    return rows


def _write_csv(path: Path, report: Mapping[str, Any]) -> None:
    rows = _csv_rows(report)
    fields = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _plot(report: Mapping[str, Any], pdf: Path, png: Path) -> None:
    try:
        import matplotlib.pyplot as plt
        import scienceplots  # noqa: F401
    except ImportError as error:
        raise RayReachedEvidenceCoverageError("SciencePlots and matplotlib are required for the figure") from error
    plt.style.use(["science", "no-latex"])
    values = report["headline"]
    informed = 100.0 * float(values["panorama_informed_sar_fraction"])
    fallback = 100.0 * float(values["geometric_fallback_sar_fraction"])
    pooled = report["pooled"]["non_direct"]["categories"]
    labels = ["Panorama\ninformed", "Geometric\nfallback"]
    fig, axes = plt.subplots(
        1,
        2,
        figsize=(7.1, 3.0),
        constrained_layout=True,
        gridspec_kw={"width_ratios": (0.8, 1.4)},
    )
    axes[0].bar(labels, [informed, fallback], color=["#0072B2", "#D55E00"])
    axes[0].set_ylabel("Non-direct body-coupled share (%)", fontsize=8)
    axes[0].set_ylim(0.0, 100.0)
    axes[0].set_title("(a) Body contribution", loc="left", fontsize=9)
    axes[0].grid(axis="y", color="0.88", linewidth=0.6)
    plot_categories = (
        "atlas_interface",
        "geometric_no_panorama_evidence",
        "geometric_evidence_refused_host_compatibility",
        "geometric_evidence_refused_insufficient_structural_mass",
        "geometric_evidence_refused_atlas_state",
        "geometric_fallback_other",
        "nonblocking_woody_atlas",
    )
    short_labels = (
        "Atlas interface",
        "No panorama evidence",
        "Host incompatibility",
        "Insufficient structure",
        "Atlas-state refusal",
        "Other fallback",
        "Nonblocking woody",
    )
    counts_million = [float(pooled[name]["event_count"]) / 1.0e6 for name in plot_categories]
    axes[1].barh(np.arange(len(plot_categories)), counts_million, color="#009E73")
    axes[1].set_yticks(np.arange(len(plot_categories)), short_labels)
    axes[1].invert_yaxis()
    axes[1].set_xlabel("Accepted interactions (million)", fontsize=8)
    axes[1].set_title("(b) Pooled event counts", loc="left", fontsize=9)
    axes[1].grid(axis="x", color="0.88", linewidth=0.6)
    for axis in axes:
        axis.spines[["top", "right"]].set_visible(False)
        axis.tick_params(labelsize=7)
    fig.savefig(pdf, bbox_inches="tight")
    fig.savefig(png, dpi=300, bbox_inches="tight")
    plt.close(fig)


def _artifact_record(path: Path) -> dict[str, Any]:
    return {"path": path.name, "bytes": path.stat().st_size, "sha256": _sha256(path)}


def write_ray_reached_evidence_coverage(
    input_path: str | Path, output_directory: str | Path
) -> RayReachedEvidenceCoverageArtifacts:
    """Read, validate, and write authenticated compact coverage artifacts."""
    document, replay_path, replay_hash = _load_input(input_path)
    report = build_report(document)
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    artifacts = RayReachedEvidenceCoverageArtifacts(
        output / "ray_reached_evidence_coverage.json",
        output / "ray_reached_evidence_coverage.csv",
        output / "ray_reached_evidence_coverage.pdf",
        output / "ray_reached_evidence_coverage.png",
        output / "ray_reached_evidence_coverage_manifest.json",
    )
    artifacts.json.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    _write_csv(artifacts.csv, report)
    _plot(report, artifacts.pdf, artifacts.png)
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "authenticated": True,
        "report_schema": REPORT_SCHEMA,
        "input": {"path": str(replay_path), "sha256": replay_hash, "identity_sha256": report["identity_sha256"]},
        "configuration": report["configuration"],
        "source_hashes": report["source_hashes"],
        "files": [_artifact_record(path) for path in (artifacts.json, artifacts.csv, artifacts.pdf, artifacts.png)],
    }
    artifacts.manifest.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    return artifacts


def validate_replay_result(document: Mapping[str, Any]) -> dict[str, Any]:
    """Public validation entry point returning the compact report."""
    return build_report(document)


def read_replay_result(path: str | Path) -> dict[str, Any]:
    """Read and authenticate a replay JSON or audit-replay directory."""
    document, _source, _digest = _load_input(path)
    return document


write_report = write_ray_reached_evidence_coverage

__all__ = [
    "BODY_FIELDS",
    "CATEGORIES",
    "FAMILIES",
    "GEOMETRIC_FALLBACK",
    "INPUT_SCHEMA",
    "MANIFEST_SCHEMA",
    "PANORAMA_INFORMED",
    "REPORT_SCHEMA",
    "RayReachedEvidenceCoverageArtifacts",
    "RayReachedEvidenceCoverageError",
    "build_report",
    "read_replay_result",
    "validate_replay_result",
    "write_report",
    "write_ray_reached_evidence_coverage",
]
