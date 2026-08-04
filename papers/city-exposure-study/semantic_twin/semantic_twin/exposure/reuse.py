"""Decide whether a streamed exposure run is complete and identical."""

from __future__ import annotations

import json
import math
import pathlib
import zipfile
from collections.abc import Mapping
from dataclasses import fields
from typing import Any

import numpy as np

from semantic_twin.runconfig import MATERIALS, RunConfig


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
    except (OSError, TypeError, ValueError):
        return False
    return (
        complete_output(manifest, config, rows_path, spectra_path)
        and same_run_identity(manifest, config, models)
        and same_models(manifest, config, models)
    )


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
        row_indices = _read_row_indices(rows_path, required_keys)
        spectrum_indices, rho, local_grid, solid_angle = _read_spectra(spectra_path)
    except (EOFError, KeyError, OSError, TypeError, ValueError, zipfile.BadZipFile):
        return False
    checks = (
        len(row_indices) == expected,
        len(set(row_indices)) == expected,
        all(left < right for left, right in zip(row_indices, row_indices[1:], strict=False)),
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


def _read_row_indices(rows_path: pathlib.Path, required_keys: frozenset[str]) -> list[int]:
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
    return indices


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
            if not isinstance(recorded, dict) or set(recorded) != {field.name for field in fields(RunConfig)}:
                return False
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
        tag=requested.tag,
    )


def materials_from_tag(tag: str) -> str:
    """Read the historical ladder material mode encoded in its output tag."""
    for material in sorted(MATERIALS, key=len, reverse=True):
        if tag == material or tag.endswith(f"_{material}"):
            return material
    return "geometric"
