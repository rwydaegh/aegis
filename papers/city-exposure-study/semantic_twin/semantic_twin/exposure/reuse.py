"""Decide whether a streamed exposure run is complete and identical."""

from __future__ import annotations

import hashlib
import json
import math
import pathlib
import zipfile
from collections.abc import Mapping
from dataclasses import fields
from typing import Any

import numpy as np

from semantic_twin import paths
from semantic_twin.runconfig import MATERIALS, RunConfig
from semantic_twin.walk.model import CAMERA_REGISTERED, REGISTERED_ROAD_V1, STRIDE_INTERPOLATED


_COMMON_ROW_KEYS = frozenset(
    {
        "index",
        "x",
        "y",
        "z",
        "ground_z_m",
        "seconds",
        "sky_fraction",
        "mean_bounces",
        "mean_excess_delay_ns",
        "escaped_fraction",
        "truncated_throughput_share",
    }
)
_BODY_RESULT_SUFFIXES = (
    "reference_s0_w_m2",
    "arriving_power_density_w_m2",
    "susceptibility",
    "peak_sab_w_m2",
    "mean_sab_w_m2",
    "absorbed_power_w",
    "sar_wb_w_kg",
)


def reusable(config: RunConfig, output: pathlib.Path, models: Mapping[str, Any]) -> bool:
    """Whether a complete run on disk has the requested numerical identity."""
    stem = f"{config.tag}_{config.frequency_ghz:g}ghz"
    manifest_path = output / f"{stem}_manifest.json"
    rows_path = output / f"{stem}_locations.jsonl"
    spectra_path = output / f"{stem}_spectra.npz"
    if not manifest_path.exists() or not rows_path.exists() or not spectra_path.exists():
        return False
    try:
        manifest = json.loads(manifest_path.read_text())
        mesh_path = paths.site_mesh(config.site, config.crop_m)
    except (OSError, TypeError, ValueError):
        return False
    return (
        complete_output(manifest, config, rows_path, spectra_path)
        and same_output_generation(manifest, rows_path, spectra_path)
        and same_run_identity(manifest, config, models)
        and same_models(manifest, config, models)
        and same_support_mesh(manifest, mesh_path)
        and same_atlas_artifact(manifest, config, mesh_path)
    )


def same_support_mesh(manifest: dict[str, Any], mesh_path: pathlib.Path) -> bool:
    """Require reuse to resolve to the exact support-mesh bytes that were traced."""
    recorded = manifest.get("mesh_sha256")
    if not _valid_sha256(recorded):
        return False
    try:
        return _file_sha256(mesh_path) == recorded
    except OSError:
        return False


def same_atlas_artifact(
    manifest: dict[str, Any],
    config: RunConfig,
    mesh_path: pathlib.Path,
) -> bool:
    """Require an atlas and its canonical sidecar to remain the traced pair."""
    if config.materials != "atlas":
        return True
    atlas_path = (
        pathlib.Path(config.atlas_npz)
        if config.atlas_npz is not None
        else paths.joint_atlas(config.site, config.crop_m, resolution=8)
    )
    binding = manifest.get("semantic_binding")
    if not isinstance(binding, dict):
        return False
    recorded_npz = binding.get("atlas_npz_sha256")
    recorded_manifest = binding.get("atlas_manifest_sha256")
    if not _valid_sha256(recorded_npz) or not _valid_sha256(recorded_manifest):
        return False
    atlas_manifest = atlas_path.with_suffix(".json")
    try:
        current_npz = _file_sha256(atlas_path)
        current_manifest = _file_sha256(atlas_manifest)
        sidecar = json.loads(atlas_manifest.read_text(encoding="utf-8"))
        mesh_sha256 = _file_sha256(mesh_path)
    except (OSError, TypeError, ValueError):
        return False
    artifact = sidecar.get("artifact")
    atlas_mesh = sidecar.get("mesh")
    return (
        current_npz == recorded_npz
        and current_manifest == recorded_manifest
        and sidecar.get("schema") == "aegis.joint_semantic_material_atlas"
        and sidecar.get("format_version") == 1
        and isinstance(artifact, dict)
        and artifact.get("path") == atlas_path.name
        and artifact.get("sha256") == current_npz
        and _valid_sha256(artifact.get("content_sha256"))
        and isinstance(atlas_mesh, dict)
        and atlas_mesh.get("sha256") == mesh_sha256
    )


def same_output_generation(
    manifest: dict[str, Any],
    rows_path: pathlib.Path,
    spectra_path: pathlib.Path,
    *,
    require_published_names: bool = True,
) -> bool:
    """Verify that rows and spectra are the one generation committed by the manifest."""
    generation = manifest.get("output_generation")
    if not isinstance(generation, dict) or generation.get("format_version") != 1:
        return False
    generation_id = generation.get("id")
    if (
        not isinstance(generation_id, str)
        or len(generation_id) != 32
        or any(character not in "0123456789abcdef" for character in generation_id.lower())
    ):
        return False
    artifacts = generation.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != {"locations", "spectra"}:
        return False
    try:
        return _same_artifact(artifacts["locations"], rows_path, require_published_names) and _same_artifact(
            artifacts["spectra"], spectra_path, require_published_names
        )
    except OSError:
        return False


def _same_artifact(record: Any, path: pathlib.Path, require_name: bool) -> bool:
    if not isinstance(record, dict) or set(record) != {"path", "sha256", "bytes"}:
        return False
    size = record.get("bytes")
    return (
        (not require_name or record.get("path") == path.name)
        and _valid_sha256(record.get("sha256"))
        and type(size) is int
        and size >= 0
        and path.stat().st_size == size
        and _file_sha256(path) == record["sha256"]
    )


def _valid_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value.lower())
    )


def _file_sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def complete_output(
    manifest: dict[str, Any],
    config: RunConfig,
    rows_path: pathlib.Path,
    spectra_path: pathlib.Path,
) -> bool:
    """Prove that every requested result and spectrum reached disk together."""
    try:
        expected = manifest["locations_traced"]
        if type(expected) is not int or expected < 0:
            raise ValueError("locations_traced must be a nonnegative integer")
        if expected != _intended_locations(manifest, config):
            raise ValueError("locations_traced does not cover the requested walk")
        required_keys = _required_row_keys(config.models)
        rows = _read_rows(rows_path, required_keys)
        row_indices = [row["index"] for row in rows]
        spectrum_indices, rho, local_grid, solid_angle = _read_spectra(spectra_path)
    except (EOFError, KeyError, OSError, TypeError, ValueError, zipfile.BadZipFile):
        return False
    checks = (
        len(row_indices) == expected,
        len(set(row_indices)) == expected,
        all(left < right for left, right in zip(row_indices, row_indices[1:], strict=False)),
        _indices_fit_walk(manifest, row_indices),
        _valid_route_rows(manifest, config, rows),
        spectrum_indices.ndim == 1,
        np.issubdtype(spectrum_indices.dtype, np.integer),
        spectrum_indices.tolist() == row_indices,
        _valid_rho(rho, (expected, config.local_cells)),
        _valid_grid(local_grid, config.local_cells),
        _valid_solid_angle(solid_angle, config.local_cells),
    )
    return all(checks)


def _intended_locations(manifest: dict[str, Any], config: RunConfig) -> int:
    requested = manifest.get("locations_requested", config.locations)
    if type(requested) is not int or requested != config.locations:
        raise ValueError("locations_requested does not match the run")
    walk = manifest.get("walk", {})
    candidates = walk.get("candidates_after_clearance") if isinstance(walk, dict) else None
    if candidates is None:
        if requested <= 0:
            raise ValueError("an all-location run must record the walk size")
        return requested
    if type(candidates) is not int or candidates < 0:
        raise ValueError("walk candidate count must be a nonnegative integer")
    return candidates if requested <= 0 else min(requested, candidates)


def _required_row_keys(models: tuple[str, ...]) -> frozenset[str]:
    model_keys = {
        key
        for name in models
        for key in (
            f"chi_{name}",
            f"chi_{name}_direct",
            *(f"{name}_{suffix}" for suffix in _BODY_RESULT_SUFFIXES),
        )
    }
    return _COMMON_ROW_KEYS | model_keys


def _read_rows(rows_path: pathlib.Path, required_keys: frozenset[str]) -> list[dict[str, Any]]:
    text = rows_path.read_text()
    if text and not text.endswith("\n"):
        raise ValueError("the final JSON row is incomplete")
    rows = [json.loads(line) for line in text.splitlines()]
    if any(not isinstance(row, dict) or not required_keys.issubset(row) for row in rows):
        raise ValueError("a JSON row is missing a required result")
    numeric_keys = required_keys - {"index"}
    if any(type(row[key]) not in (int, float) or not math.isfinite(row[key]) for row in rows for key in numeric_keys):
        raise ValueError("a JSON result is not a finite number")
    indices = [row["index"] for row in rows]
    if any(type(index) is not int or index < 0 for index in indices):
        raise ValueError("row indices must be nonnegative integers")
    return rows


def _indices_fit_walk(manifest: dict[str, Any], indices: list[int]) -> bool:
    walk = manifest.get("walk")
    candidates = walk.get("candidates_after_clearance") if isinstance(walk, dict) else None
    return candidates is None or all(index < candidates for index in indices)


def _valid_route_rows(manifest: dict[str, Any], config: RunConfig, rows: list[dict[str, Any]]) -> bool:
    if config.walk != "route":
        return True
    walk = manifest.get("walk")
    if not isinstance(walk, dict) or walk.get("route_geometry") != REGISTERED_ROAD_V1:
        return False
    candidates = walk.get("candidates_after_clearance")
    point_kind = walk.get("point_kind")
    allowed = {CAMERA_REGISTERED, STRIDE_INTERPOLATED}
    if type(candidates) is not int or not isinstance(point_kind, list) or len(point_kind) != candidates:
        return False
    if any(kind not in allowed for kind in point_kind):
        return False
    return all(row["index"] < candidates and row.get("point_kind") == point_kind[row["index"]] for row in rows)


def _read_spectra(
    spectra_path: pathlib.Path,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    with np.load(spectra_path) as spectra:
        return tuple(np.asarray(spectra[name]) for name in ("index", "rho_rooftop", "local_grid", "solid_angle"))


def _valid_rho(rho: np.ndarray, shape: tuple[int, int]) -> bool:
    return (
        rho.shape == shape
        and np.issubdtype(rho.dtype, np.floating)
        and bool(np.all(np.isfinite(rho)))
        and bool(np.all(rho >= 0.0))
    )


def _valid_grid(local_grid: np.ndarray, local_cells: int) -> bool:
    return (
        local_grid.shape == (local_cells, 3)
        and np.issubdtype(local_grid.dtype, np.floating)
        and bool(np.all(np.isfinite(local_grid)))
        and bool(np.allclose(np.linalg.norm(local_grid, axis=1), 1.0, rtol=1.0e-12, atol=1.0e-12))
    )


def _valid_solid_angle(solid_angle: np.ndarray, local_cells: int) -> bool:
    return (
        solid_angle.ndim == 0
        and np.issubdtype(solid_angle.dtype, np.floating)
        and bool(np.isfinite(solid_angle))
        and float(solid_angle) == 4.0 * np.pi / local_cells
    )


def same_run_identity(manifest: dict[str, Any], config: RunConfig, models: Mapping[str, Any]) -> bool:
    """Compare a full run record, with a conservative old-manifest reader."""
    recorded = manifest.get("run")
    try:
        if recorded is not None:
            if not isinstance(recorded, dict):
                return False
            expected_fields = {field.name for field in fields(RunConfig)}
            recorded_fields = set(recorded)
            missing = expected_fields - recorded_fields
            if recorded_fields - expected_fields or missing not in (set(), {"transport_kernel"}):
                return False
            if missing:
                # NumPy was the sole transport family before the field existed.
                # This also classifies old ``cuda_ad_rgb`` manifests correctly:
                # CUDA named their intersection backend, not a resident kernel.
                recorded = dict(recorded, transport_kernel="numpy")
            previous = RunConfig.from_dict(recorded)
            digest_matches = manifest.get("run_digest") == previous.digest()
        else:
            previous = legacy_run(manifest, config, models)
            digest_matches = True
    except (KeyError, TypeError, ValueError):
        return False
    return digest_matches and previous.identity() == config.identity()


def same_models(manifest: dict[str, Any], config: RunConfig, models: Mapping[str, Any]) -> bool:
    """Keep concrete source-model implementations inside reuse identity."""
    try:
        recorded = {
            name: {key: entry.get(key) for key in ("elevation_deg", "law", "height_band_m", "range_band_m")}
            for name, entry in manifest.get("illumination_models", {}).items()
        }
        expected = {name: model_identity(models[name]) for name in config.models}
    except (AttributeError, KeyError, TypeError):
        return False
    return recorded == expected


def model_identity(model: Any) -> dict[str, Any]:
    """The numerical source definition used while scoring escaped rays."""
    return {
        "elevation_deg": [model.elevation_min_deg, model.elevation_max_deg],
        "law": model.law,
        "height_band_m": list(model.height_band_m) if model.height_band_m else None,
        "range_band_m": list(model.range_band_m) if model.range_band_m else None,
    }


def legacy_run(manifest: dict[str, Any], requested: RunConfig, models: Mapping[str, Any]) -> RunConfig:
    """Recover the explicit defaults used before manifests stored RunConfig."""
    trace = manifest.get("trace_config", {})
    walk = manifest.get("walk", {})
    binding = manifest.get("semantic_binding", {})
    model_names = tuple(manifest.get("illumination_models", {}))
    materials = binding.get("materials") or materials_from_tag(requested.tag)
    return RunConfig(
        site=manifest.get("site", "korenmarkt"),
        crop_m=manifest.get("crop_radius_m", 130),
        law="band",
        models=model_names or tuple(models),
        estimator="escape",
        next_event=None,
        walk="grid",
        walk_path="links",
        walk_radius_m=walk.get("radius_m", 90.0),
        walk_spacing_m=walk.get("spacing_m", 3.0),
        walk_stride_m=6.0,
        head_height_m=walk.get("head_height_m", 1.5),
        locations=manifest.get("locations_requested", manifest.get("locations_traced", 0)),
        frequency_hz=trace.get("frequency_hz", 15.0e9),
        max_bounces=trace.get("max_bounces", 3),
        roulette_start=trace.get("roulette_start", 4),
        roulette_floor=trace.get("roulette_floor", 0.05),
        ray_epsilon_m=trace.get("ray_epsilon_m", 1.0e-3),
        range_weighted_escape=trace.get("range_weighted_escape", False),
        materials=materials,
        walk_npz=None,
        rays=trace.get("rays", 200_000),
        batch=trace.get("batch", 400_000),
        local_cells=trace.get("local_cells", 512),
        exit_bands=trace.get("exit_bands", 18),
        seed=trace.get("seed", 7),
        variant=manifest.get("variant", "llvm_ad_rgb"),
        transport_kernel="numpy",
        tag=requested.tag,
    )


def materials_from_tag(tag: str) -> str:
    """Read the historical ladder material mode encoded in its output tag."""
    for material in sorted(MATERIALS, key=len, reverse=True):
        if tag == material or tag.endswith(f"_{material}"):
            return material
    return "geometric"
