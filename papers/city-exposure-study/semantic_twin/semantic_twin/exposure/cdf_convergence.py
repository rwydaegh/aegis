"""Sequential Monte Carlo stopping for the frozen Korenmarkt walk CDF.

One complete 13-point walk is one Monte Carlo replica.  The points within a
walk remain together when replicas are resampled.  This preserves their shared
base seed and avoids treating nearby route points as independent observations.

All seed averages are taken in linear power.  The conversion to decibels is
done only after the average.  The route itself is fixed, so the intervals in
this module measure ray-tracing error and not spatial sampling error.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import pathlib
import platform
import time
from dataclasses import dataclass
from typing import Any

import numpy as np

MODEL_NAMES = ("isotropic", "rooftop", "street_small_cell")
CDF_STATISTICS = ("minimum", "q10", "q50", "q90", "maximum")
ENDPOINT_RANKS = ("minimum", "second_lowest", "second_highest", "maximum")


@dataclass(frozen=True)
class StoppingThresholds:
    """Maximum allowed 95 percent confidence half-widths and look shifts."""

    point_p90_db: float = 0.10
    point_max_db: float = 0.15
    cdf_q50_db: float = 0.05
    cdf_q10_q90_db: float = 0.10
    cdf_endpoint_db: float = 0.15
    stability_wasserstein_db: float = 0.03
    stability_q50_db: float = 0.03
    stability_q10_q90_db: float = 0.05
    stability_endpoint_db: float = 0.10
    body_peak_max_db: float = 0.15

    @classmethod
    def from_dict(cls, document: dict[str, Any] | None) -> StoppingThresholds:
        if document is None:
            return cls()
        unknown = set(document) - {field.name for field in dataclasses.fields(cls)}
        if unknown:
            raise ValueError(f"unknown stopping thresholds: {', '.join(sorted(unknown))}")
        return cls(**{name: float(value) for name, value in document.items()})

    def validate(self) -> None:
        for field in dataclasses.fields(self):
            if getattr(self, field.name) <= 0.0:
                raise ValueError(f"{field.name} must be positive")


@dataclass(frozen=True)
class CdfConvergenceConfig:
    """File-backed definition of one sequential full-walk replica campaign."""

    root: pathlib.Path
    output_dir: pathlib.Path
    reference_manifest: pathlib.Path
    reference_locations: pathlib.Path
    reference_spectra: pathlib.Path
    base_seeds: tuple[int, ...]
    diagnostic_look: int
    looks: tuple[int, ...]
    bootstrap_replicates: int
    bootstrap_seed: int
    confidence: float
    body_chunk_cells: int
    thresholds: StoppingThresholds
    contract: str
    config_path: pathlib.Path
    config_sha256: str

    @classmethod
    def load(cls, path: str | pathlib.Path) -> CdfConvergenceConfig:
        from semantic_twin.exposure.angular_convergence import file_sha256

        config_path = pathlib.Path(path).resolve()
        document = json.loads(config_path.read_text())
        root_value = pathlib.Path(document.get("root", ".."))
        root = (config_path.parent / root_value).resolve()

        def resolve(value: str) -> pathlib.Path:
            candidate = pathlib.Path(value)
            return candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()

        reference = document["reference"]
        bootstrap = document["bootstrap"]
        body = document.get("body_peak", {})
        config = cls(
            root=root,
            output_dir=resolve(document["output_dir"]),
            reference_manifest=resolve(reference["manifest"]),
            reference_locations=resolve(reference["locations"]),
            reference_spectra=resolve(reference["spectra"]),
            base_seeds=tuple(int(value) for value in document["base_seeds"]),
            diagnostic_look=int(document.get("diagnostic_look", 8)),
            looks=tuple(int(value) for value in document["looks"]),
            bootstrap_replicates=int(bootstrap["replicates"]),
            bootstrap_seed=int(bootstrap["seed"]),
            confidence=float(bootstrap.get("confidence", 0.95)),
            body_chunk_cells=int(body.get("chunk_cells", 512)),
            thresholds=StoppingThresholds.from_dict(document.get("thresholds")),
            contract=str(document.get("contract", "custom")),
            config_path=config_path,
            config_sha256=file_sha256(config_path),
        )
        config.validate()
        return config

    def validate(self) -> None:
        """Reject a campaign that can change meaning while it is running."""
        if not self.base_seeds or len(set(self.base_seeds)) != len(self.base_seeds):
            raise ValueError("base_seeds must be nonempty and unique")
        if any(seed < 0 for seed in self.base_seeds):
            raise ValueError("base_seeds must be nonnegative")
        if self.diagnostic_look < 2:
            raise ValueError("diagnostic_look must be at least 2")
        if len(self.looks) < 2 or tuple(sorted(set(self.looks))) != self.looks:
            raise ValueError("looks must contain at least two unique increasing values")
        if self.looks[0] <= self.diagnostic_look:
            raise ValueError("formal looks must follow the diagnostic look")
        if len(self.base_seeds) < self.looks[-1]:
            raise ValueError("base_seeds must cover the last look")
        if self.bootstrap_replicates < 100:
            raise ValueError("bootstrap.replicates must be at least 100")
        if not 0.0 < self.confidence < 1.0:
            raise ValueError("bootstrap confidence must lie between zero and one")
        if self.body_chunk_cells < 1:
            raise ValueError("body chunk count must be positive")
        self.thresholds.validate()
        if self.contract == "korenmarkt_cdf_stopping_4096_v1":
            expected = {
                "diagnostic_look": 8,
                "looks": (16, 24, 32),
                "base_seeds": tuple(range(7, 39)),
            }
            actual = {name: getattr(self, name) for name in expected}
            if actual != expected:
                raise ValueError(f"production CDF stopping contract changed: {actual} != {expected}")

    @property
    def all_looks(self) -> tuple[int, ...]:
        return (self.diagnostic_look, *self.looks)

    def scientific_config(self) -> dict[str, Any]:
        return {
            "contract": self.contract,
            "config_path": str(self.config_path),
            "config_sha256": self.config_sha256,
            "output_dir": str(self.output_dir),
            "reference": {
                "manifest": str(self.reference_manifest),
                "locations": str(self.reference_locations),
                "spectra": str(self.reference_spectra),
            },
            "base_seeds": list(self.base_seeds),
            "diagnostic_look": self.diagnostic_look,
            "looks": list(self.looks),
            "bootstrap": {
                "replicates": self.bootstrap_replicates,
                "seed": self.bootstrap_seed,
                "confidence": self.confidence,
                "unit": "one complete base-seed walk replica",
            },
            "body_peak": {
                "chunk_cells": self.body_chunk_cells,
                "bootstrap_target": "linear mean of per-replica peak absorbed power density",
                "ensemble_check": "peak recomputed from the ensemble-mean angular spectrum",
            },
            "thresholds": dataclasses.asdict(self.thresholds),
        }


def analyse_chi_replicas(
    chi: np.ndarray,
    *,
    looks: tuple[int, ...],
    formal_looks: tuple[int, ...],
    model_names: tuple[str, ...] = MODEL_NAMES,
    bootstrap_replicates: int = 10_000,
    bootstrap_seed: int = 20260805,
    confidence: float = 0.95,
    thresholds: StoppingThresholds | None = None,
) -> dict[str, Any]:
    """Apply the fixed-walk stopping rule to linear susceptibility replicas.

    ``chi`` has shape ``(replicas, standpoints, models)``.  Each bootstrap draw
    resamples the first axis and therefore keeps every standpoint and source law
    from a base-seed walk together.
    """
    values = np.asarray(chi, dtype=np.float64)
    if values.ndim != 3:
        raise ValueError("chi must have shape (replicas, standpoints, models)")
    if values.shape[2] != len(model_names):
        raise ValueError("chi model axis does not match model_names")
    if values.shape[1] < 2:
        raise ValueError("at least two standpoints are required for a route CDF")
    if np.any(values <= 0.0) or not np.all(np.isfinite(values)):
        raise ValueError("chi replicas must be finite and positive")
    if not looks or tuple(sorted(set(looks))) != looks:
        raise ValueError("looks must be unique and increasing")
    if looks[-1] > values.shape[0]:
        raise ValueError("chi does not contain every requested look")
    if not set(formal_looks).issubset(looks):
        raise ValueError("formal_looks must be included in looks")
    if bootstrap_replicates < 100:
        raise ValueError("bootstrap_replicates must be at least 100")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must lie between zero and one")
    limits = thresholds or StoppingThresholds()
    limits.validate()

    documents: list[dict[str, Any]] = []
    previous_db: np.ndarray | None = None
    consecutive = 0
    stop_at: int | None = None
    for look in looks:
        prefix = values[:look]
        rng = np.random.default_rng(np.random.SeedSequence([bootstrap_seed, look]))
        indices = rng.integers(0, look, size=(bootstrap_replicates, look))
        bootstrap_mean = np.mean(prefix[indices], axis=1, dtype=np.float64)
        estimate_linear = np.mean(prefix, axis=0, dtype=np.float64)
        estimate_db = _to_db(estimate_linear)
        bootstrap_db = _to_db(bootstrap_mean)
        point_half_width = _simultaneous_half_width(bootstrap_db, estimate_db, confidence)

        point_report = _point_report(point_half_width, model_names, limits)
        cdf_report = _cdf_report(estimate_db, bootstrap_db, model_names, confidence, limits)
        stability = _stability_report(previous_db, estimate_db, model_names, limits)
        uncertainty_pass = bool(point_report["pass"] and cdf_report["pass"])
        look_pass = bool(uncertainty_pass and stability["pass"])
        is_formal = look in formal_looks
        if is_formal:
            consecutive = consecutive + 1 if look_pass else 0
            if consecutive >= 2 and stop_at is None:
                stop_at = look
        document = {
            "replicas": look,
            "formal_look": is_formal,
            "point_estimate_db": {
                name: [float(value) for value in estimate_db[:, model]] for model, name in enumerate(model_names)
            },
            "endpoint_values_db": _endpoint_values(estimate_db, model_names),
            "point_uncertainty": point_report,
            "fixed_route_cdf": cdf_report,
            "stability_from_previous_look": stability,
            "uncertainty_pass": uncertainty_pass,
            "look_pass": look_pass,
            "consecutive_formal_passes": consecutive,
        }
        documents.append(document)
        previous_db = estimate_db

    return {
        "schema": "fixed-walk-cdf-stopping-v1",
        "independent_unit": "one complete base-seed walk replica",
        "aggregation": "arithmetic mean in linear power for each fixed standpoint, then 10 log10",
        "bootstrap": {
            "replicates": bootstrap_replicates,
            "seed": bootstrap_seed,
            "confidence": confidence,
            "resampling": "base-seed walk clusters with all standpoints and source laws kept together",
            "simultaneous_interval": "max-t band over the complete reported family",
        },
        "route_sample": {
            "standpoints": int(values.shape[1]),
            "cdf_step": float(1.0 / values.shape[1]),
            "spatial_sampling_uncertainty_included": False,
        },
        "thresholds": dataclasses.asdict(limits),
        "looks": documents,
        "stopped": stop_at is not None,
        "stop_at_replicas": stop_at,
        "cap_reached": stop_at is None and bool(formal_looks) and looks[-1] == max(formal_looks),
    }


def analyse_body_peak_replicas(
    peak_sab_w_m2: np.ndarray,
    *,
    looks: tuple[int, ...],
    bootstrap_replicates: int,
    bootstrap_seed: int,
    confidence: float,
    maximum_half_width_db: float,
) -> dict[int, dict[str, Any]]:
    """Measure seed error in the published rooftop body-peak CDF.

    The input is the peak returned by one full trace replica.  Its seed mean is
    formed in linear absorbed power before conversion to decibels.  This is a
    scalar-estimator interval.  The final campaign output also recomputes body
    exposure from the ensemble-mean angular spectrum and records the small
    difference between the two central estimators.
    """
    return analyse_body_metric_replicas(
        peak_sab_w_m2,
        looks=looks,
        bootstrap_replicates=bootstrap_replicates,
        bootstrap_seed=bootstrap_seed,
        confidence=confidence,
        maximum_half_width_db=maximum_half_width_db,
        estimator="linear mean of the per-replica peak absorbed power density",
    )


def analyse_body_metric_replicas(
    values_w_m2: np.ndarray,
    *,
    looks: tuple[int, ...],
    bootstrap_replicates: int,
    bootstrap_seed: int,
    confidence: float,
    maximum_half_width_db: float,
    estimator: str,
) -> dict[int, dict[str, Any]]:
    """Return simultaneous seed bands for one positive body-side scalar."""
    values = np.asarray(values_w_m2, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] < 2:
        raise ValueError("body metric replicas must have shape (replicas, standpoints)")
    if np.any(values <= 0.0) or not np.all(np.isfinite(values)):
        raise ValueError("body metric replicas must be finite and positive")
    out: dict[int, dict[str, Any]] = {}
    for look in looks:
        if look > values.shape[0]:
            raise ValueError("body peak replicas do not cover every look")
        prefix = values[:look]
        rng = np.random.default_rng(np.random.SeedSequence([bootstrap_seed, look, 1]))
        indices = rng.integers(0, look, size=(bootstrap_replicates, look))
        estimate_db = _to_db(np.mean(prefix, axis=0, dtype=np.float64))
        bootstrap_db = _to_db(np.mean(prefix[indices], axis=1, dtype=np.float64))
        widths = _simultaneous_half_width(bootstrap_db, estimate_db, confidence)
        ordered = np.sort(estimate_db)
        ordered_bootstrap = np.sort(bootstrap_db, axis=1)
        ordered_widths = _simultaneous_half_width(ordered_bootstrap, ordered, confidence)
        maximum = float(np.max(widths))
        out[look] = {
            "point_estimate_db": [float(value) for value in estimate_db],
            "point_simultaneous_half_width_db": [float(value) for value in widths],
            "max_half_width_db": maximum,
            "ordered_estimate_db": [float(value) for value in ordered],
            "ordered_simultaneous_half_width_db": [float(value) for value in ordered_widths],
            "pass": maximum <= maximum_half_width_db,
            "estimator": estimator,
        }
    return out


@dataclass(frozen=True)
class CampaignCheckpoint:
    """Compact complete-replica prefix and its running spectrum sum."""

    base_seeds: np.ndarray
    chi: np.ndarray
    chi_direct: np.ndarray
    body_peak_rooftop: np.ndarray
    body_mean_rooftop: np.ndarray
    trace_seconds: np.ndarray
    rho_sum: np.ndarray
    local_grid: np.ndarray
    solid_angle: float

    @property
    def replicas(self) -> int:
        return int(self.base_seeds.size)


def run_campaign(
    config: CdfConvergenceConfig,
    *,
    dry_run: bool = False,
    analyse_only: bool = False,
) -> pathlib.Path:
    """Run, resume, and analyse the sequential production campaign."""
    from semantic_twin.exposure import study
    from semantic_twin.exposure.angular_convergence import (
        AngularRunSpec,
        _prepare_shared_scene,
        _prepare_trace,
        canonical_sha256,
        code_provenance,
        load_reference,
    )

    config.output_dir.mkdir(parents=True, exist_ok=True)
    reference = load_reference(config)
    _validate_production_reference(config, reference)
    code = code_provenance(config.root)
    runner = config.root / "run_cdf_convergence.py"
    code = {
        **code,
        "runner_sha256": _file_sha256(runner) if runner.is_file() else None,
    }
    numerical_code = {
        "source_tree_sha256": code["source_tree_sha256"],
        "runner_sha256": code["runner_sha256"],
        "runtime_versions": code["runtime_versions"],
    }
    identity = canonical_sha256(
        {
            "schema": "fixed-walk-cdf-campaign-v1",
            "config": config.scientific_config(),
            "reference": reference.as_dict(),
            "source": numerical_code,
            "models": list(MODEL_NAMES),
        }
    )
    plan = {
        "schema": "fixed-walk-cdf-plan-v1",
        "created_utc": _utc_now(),
        "identity_sha256": identity,
        "scientific_config": config.scientific_config(),
        "reference": reference.as_dict(),
        "code": code,
        "identity_code_fields": numerical_code,
        "models": list(MODEL_NAMES),
        "seed_rule": "base seed + 1000 * frozen production standpoint index",
        "retention": (
            "per-replica scalar rows and one running linear-power rho sum. "
            "individual replica spectra and paths are not retained"
        ),
    }
    _write_json_atomic(config.output_dir / "plan.json", plan)
    if dry_run:
        return config.output_dir / "plan.json"

    checkpoint_path = config.output_dir / "checkpoint.npz"
    checkpoint = _load_campaign_checkpoint(checkpoint_path, identity, reference, config)
    if analyse_only and checkpoint is None:
        raise RuntimeError("no valid campaign checkpoint is available to analyse")

    if not analyse_only:
        shared = _prepare_shared_scene(config, reference)
        manifest_run = reference.manifest["run"]
        spec = AngularRunSpec(
            cells=int(manifest_run["local_cells"]),
            rays=int(manifest_run["rays"]),
            seed=int(manifest_run["seed"]),
        )
        _scene, _material, tracer, _run = _prepare_trace(spec, shared)
        coupler = study.BodyCoupler(
            study.PHANTOM,
            float(manifest_run["frequency_hz"]),
            body_mass_kg=study.PHANTOM_MASS_KG,
        )
        checkpoint = _empty_checkpoint(tracer, reference) if checkpoint is None else checkpoint
        checkpoint = _trace_until_stop(config, reference, tracer, coupler, checkpoint, checkpoint_path, identity)

    if checkpoint is None:
        raise AssertionError("campaign checkpoint was not prepared")
    analysis = _analyse_checkpoint(config, checkpoint)
    ensemble = _final_ensemble(config, reference, checkpoint, analysis, study)
    analysis["ensemble"] = ensemble
    analysis["identity_sha256"] = identity
    analysis["reference"] = reference.as_dict()
    analysis["complete_replicas"] = checkpoint.replicas
    analysis["created_utc"] = _utc_now()
    analysis_path = config.output_dir / "analysis.json"
    _write_json_atomic(analysis_path, analysis)
    _write_final_rows(config.output_dir / "ensemble_locations.jsonl", ensemble["rows"])
    _plot_convergence(analysis, config.output_dir / "cdf_convergence.png")
    manifest = _campaign_manifest(config, reference, checkpoint, identity, code, analysis_path)
    _write_json_atomic(config.output_dir / "manifest.json", manifest)
    return analysis_path


def archived_rooftop_diagnostic(config: CdfConvergenceConfig) -> pathlib.Path:
    """Validate the analysis with the archived eight-seed rooftop campaign."""
    from semantic_twin.exposure.angular_convergence import file_sha256, load_reference

    reference = load_reference(config)
    _validate_production_reference(config, reference)
    run_root = config.root / "outputs" / "angular_convergence_4096_atlas_v2" / "runs"
    seeds = tuple(range(7, 15))
    chi_rows: list[list[float]] = []
    peak_rows: list[list[float]] = []
    inputs: list[dict[str, Any]] = []
    expected_index = [int(value) for value in reference.standpoints.index]
    for seed in seeds:
        run_dir = run_root / f"cells4096_rays1600000_seed{seed}"
        manifest_path = run_dir / "manifest.json"
        metrics_path = run_dir / "metrics.json"
        manifest = json.loads(manifest_path.read_text())
        metrics = json.loads(metrics_path.read_text())
        rows = list(metrics["rows"])
        if manifest.get("complete") is not True:
            raise ValueError(f"archived rooftop seed {seed} is incomplete")
        if manifest.get("metrics_file_sha256") != file_sha256(metrics_path):
            raise ValueError(f"archived rooftop seed {seed} metrics do not match their manifest")
        if [int(row["index"]) for row in rows] != expected_index:
            raise ValueError(f"archived rooftop seed {seed} uses a different frozen route")
        chi_rows.append([float(row["chi"]) for row in rows])
        peak_rows.append([float(row["body"]["peak_sab_w_m2"]) for row in rows])
        inputs.append(
            {
                "base_seed": seed,
                "identity_sha256": manifest["identity_sha256"],
                "manifest_path": str(manifest_path),
                "manifest_sha256": file_sha256(manifest_path),
                "metrics_path": str(metrics_path),
                "metrics_sha256": file_sha256(metrics_path),
            }
        )
    chi = np.asarray(chi_rows, dtype=np.float64)[:, :, None]
    peak = np.asarray(peak_rows, dtype=np.float64)
    chi_analysis = analyse_chi_replicas(
        chi,
        looks=(8,),
        formal_looks=(8,),
        model_names=("rooftop",),
        bootstrap_replicates=config.bootstrap_replicates,
        bootstrap_seed=config.bootstrap_seed,
        confidence=config.confidence,
        thresholds=config.thresholds,
    )
    peak_analysis = analyse_body_peak_replicas(
        peak,
        looks=(8,),
        bootstrap_replicates=config.bootstrap_replicates,
        bootstrap_seed=config.bootstrap_seed,
        confidence=config.confidence,
        maximum_half_width_db=config.thresholds.body_peak_max_db,
    )[8]
    document = {
        "schema": "archived-rooftop-seed-diagnostic-v1",
        "created_utc": _utc_now(),
        "scope": (
            "rooftop only. This validates the stopping analysis but cannot replace the required three-law campaign"
        ),
        "seeds": list(seeds),
        "standpoints": int(chi.shape[1]),
        "bootstrap": {
            "replicates": config.bootstrap_replicates,
            "seed": config.bootstrap_seed,
            "confidence": config.confidence,
        },
        "analysis_source_sha256": file_sha256(pathlib.Path(__file__)),
        "reference": reference.as_dict(),
        "inputs": inputs,
        "chi_analysis": chi_analysis,
        "body_peak_analysis": peak_analysis,
    }
    path = config.output_dir / "existing_rooftop_diagnostic.json"
    _write_json_atomic(path, document)
    return path


def _validate_production_reference(config: CdfConvergenceConfig, reference: Any) -> None:
    """Pin the named production contract to the accepted final generation."""
    if config.contract != "korenmarkt_cdf_stopping_4096_v1":
        return
    identity = reference.as_dict()
    expected_hashes = {
        "mesh_sha256": "bfbdba0657a1dd4b8b819e7e611dbfd4eea919e5c08538078ff1948599957264",
        "body_sha256": "781e65ef3882f1347669e0ddca5dafa82cd6368dddd6b9e801dc49613822fe3b",
        "material_evidence_sha256": "c452c34e1d9422022d55fc758d228c22a39b80d9a770042e89e13f9110f43a76",
        "standpoint_array_sha256": "d373e65c769017c5309db17c2035adf2178641d421fc5fbbdf92356e424b6f5c",
    }
    actual_hashes = {name: identity[name] for name in expected_hashes}
    if actual_hashes != expected_hashes:
        raise ValueError(f"production CDF reference hashes changed: {actual_hashes} != {expected_hashes}")
    expected_files = {
        "manifest": "e87bd8e5db0308cfa9ad445c179a8464b19a7aaa8eaf2242fb1492c0eee75a9d",
        "locations": "66b4e5c70494dc653a8d99ab33d4551fac99d70029114995ef9523d831e34534",
        "spectra": "1186e952d4edc65046e69940a54c1024cb29c1fee6e6ae72acbe95b76f59b90b",
    }
    actual_files = {name: identity["reference_files"][name]["sha256"] for name in expected_files}
    if actual_files != expected_files:
        raise ValueError(f"production CDF output generation changed: {actual_files} != {expected_files}")
    run = reference.manifest["run"]
    expected_run = {
        "site": "korenmarkt",
        "crop_m": 250,
        "law": "band",
        "models": list(MODEL_NAMES),
        "estimator": "escape",
        "walk": "route",
        "walk_path": "links",
        "walk_stride_m": 6.0,
        "locations": 0,
        "frequency_hz": 15.0e9,
        "max_bounces": 3,
        "roulette_start": 4,
        "materials": "atlas",
        "rays": 1_600_000,
        "batch": 400_000,
        "local_cells": 4096,
        "exit_bands": 18,
        "seed": 7,
        "variant": "cuda_ad_rgb",
        "transport_kernel": "drjit",
    }
    actual_run = {name: run[name] for name in expected_run}
    if actual_run != expected_run:
        raise ValueError(f"production CDF run settings changed: {actual_run} != {expected_run}")
    point_kind = reference.standpoints.point_kind
    if point_kind.count("camera_registered") != 5 or point_kind.count("stride_interpolated") != 8:
        raise ValueError("production CDF route must contain 5 registered and 8 interpolated standpoints")
    streams = {int(base + 1000 * index) for base in config.base_seeds for index in reference.standpoints.index}
    expected_streams = len(config.base_seeds) * reference.standpoints.index.size
    if len(streams) != expected_streams:
        raise ValueError("production CDF base-seed mapping contains a random-stream collision")


def _empty_checkpoint(tracer: Any, reference: Any) -> CampaignCheckpoint:
    cells = int(np.asarray(tracer.local_grid).shape[0])
    points = int(reference.standpoints.index.size)
    return CampaignCheckpoint(
        base_seeds=np.empty(0, dtype=np.int64),
        chi=np.empty((0, points, len(MODEL_NAMES)), dtype=np.float64),
        chi_direct=np.empty((0, points, len(MODEL_NAMES)), dtype=np.float64),
        body_peak_rooftop=np.empty((0, points), dtype=np.float64),
        body_mean_rooftop=np.empty((0, points), dtype=np.float64),
        trace_seconds=np.empty((0, points), dtype=np.float64),
        rho_sum=np.zeros((points, len(MODEL_NAMES), cells), dtype=np.float64),
        local_grid=np.asarray(tracer.local_grid, dtype=np.float64),
        solid_angle=float(4.0 * np.pi / cells),
    )


def _trace_until_stop(
    config: CdfConvergenceConfig,
    reference: Any,
    tracer: Any,
    coupler: Any,
    checkpoint: CampaignCheckpoint,
    checkpoint_path: pathlib.Path,
    identity: str,
) -> CampaignCheckpoint:
    formal_targets = set(config.looks)
    if checkpoint.replicas in formal_targets and checkpoint.replicas >= config.looks[1]:
        if _analyse_checkpoint(config, checkpoint)["stopped"]:
            return checkpoint
    for base_seed in config.base_seeds[checkpoint.replicas :]:
        checkpoint = _trace_replica(config, reference, tracer, coupler, checkpoint, int(base_seed))
        _write_campaign_checkpoint(checkpoint_path, checkpoint, identity, reference)
        print(f"replica {checkpoint.replicas}/{config.looks[-1]} complete at base seed {base_seed}", flush=True)
        if checkpoint.replicas not in formal_targets:
            continue
        analysis = _analyse_checkpoint(config, checkpoint)
        partial = config.output_dir / f"analysis_look{checkpoint.replicas}.json"
        _write_json_atomic(partial, analysis)
        if analysis["stopped"]:
            return checkpoint
    return checkpoint


def _trace_replica(
    config: CdfConvergenceConfig,
    reference: Any,
    tracer: Any,
    coupler: Any,
    checkpoint: CampaignCheckpoint,
    base_seed: int,
) -> CampaignCheckpoint:
    points = int(reference.standpoints.index.size)
    cells = int(checkpoint.local_grid.shape[0])
    chi = np.empty((points, len(MODEL_NAMES)), dtype=np.float64)
    direct = np.empty_like(chi)
    peak = np.empty(points, dtype=np.float64)
    mean = np.empty(points, dtype=np.float64)
    seconds = np.empty(points, dtype=np.float64)
    rho = np.empty((points, len(MODEL_NAMES), cells), dtype=np.float64)
    models = {name: _illumination_models()[name] for name in MODEL_NAMES}
    for row, index in enumerate(reference.standpoints.index):
        result = tracer.trace(
            reference.standpoints.points[row],
            models,
            ground_z_m=float(reference.standpoints.ground_z_m[row]),
            seed=base_seed + 1000 * int(index),
        )
        if not np.array_equal(np.asarray(result.local_grid), checkpoint.local_grid):
            raise RuntimeError("angular grid changed within the CDF campaign")
        if float(result.local_solid_angle) != checkpoint.solid_angle:
            raise RuntimeError("solid angle changed within the CDF campaign")
        scalars = result.scalars()
        for model, name in enumerate(MODEL_NAMES):
            chi[row, model] = float(scalars[f"chi_{name}"])
            direct[row, model] = float(scalars[f"chi_{name}_direct"])
            rho[row, model] = np.asarray(result.rho[name], dtype=np.float64)
        exposure = coupler.couple_many(
            checkpoint.local_grid,
            rho[row, 1:2],
            checkpoint.solid_angle,
            float(reference.manifest["reference_s0_w_m2"]),
            chunk_cells=config.body_chunk_cells,
        )[0]
        peak[row] = exposure.peak_sab_w_m2
        mean[row] = exposure.mean_sab_w_m2
        seconds[row] = float(result.seconds)
        print(
            f"  [{row + 1}/{points}] seed={base_seed} index={int(index)} "
            f"chi_rooftop={chi[row, 1]:.6g} ({seconds[row]:.1f} s trace)",
            flush=True,
        )
    return CampaignCheckpoint(
        base_seeds=np.append(checkpoint.base_seeds, base_seed),
        chi=np.concatenate((checkpoint.chi, chi[None, ...]), axis=0),
        chi_direct=np.concatenate((checkpoint.chi_direct, direct[None, ...]), axis=0),
        body_peak_rooftop=np.concatenate((checkpoint.body_peak_rooftop, peak[None, ...]), axis=0),
        body_mean_rooftop=np.concatenate((checkpoint.body_mean_rooftop, mean[None, ...]), axis=0),
        trace_seconds=np.concatenate((checkpoint.trace_seconds, seconds[None, ...]), axis=0),
        rho_sum=checkpoint.rho_sum + rho,
        local_grid=checkpoint.local_grid,
        solid_angle=checkpoint.solid_angle,
    )


def _illumination_models() -> dict[str, Any]:
    from semantic_twin.exposure.study import MODELS

    return dict(MODELS)


def _analyse_checkpoint(config: CdfConvergenceConfig, checkpoint: CampaignCheckpoint) -> dict[str, Any]:
    available_looks = tuple(look for look in config.all_looks if look <= checkpoint.replicas)
    formal = tuple(look for look in config.looks if look <= checkpoint.replicas)
    if not formal:
        raise RuntimeError(f"at least {config.looks[0]} complete replicas are needed for a formal analysis")
    chi_report = analyse_chi_replicas(
        checkpoint.chi,
        looks=available_looks,
        formal_looks=formal,
        bootstrap_replicates=config.bootstrap_replicates,
        bootstrap_seed=config.bootstrap_seed,
        confidence=config.confidence,
        thresholds=config.thresholds,
    )
    direct_report = analyse_chi_replicas(
        checkpoint.chi_direct,
        looks=available_looks,
        formal_looks=formal,
        bootstrap_replicates=config.bootstrap_replicates,
        bootstrap_seed=config.bootstrap_seed + 1,
        confidence=config.confidence,
        thresholds=config.thresholds,
    )
    body = analyse_body_peak_replicas(
        checkpoint.body_peak_rooftop,
        looks=available_looks,
        bootstrap_replicates=config.bootstrap_replicates,
        bootstrap_seed=config.bootstrap_seed,
        confidence=config.confidence,
        maximum_half_width_db=config.thresholds.body_peak_max_db,
    )
    body_mean = analyse_body_metric_replicas(
        checkpoint.body_mean_rooftop,
        looks=available_looks,
        bootstrap_replicates=config.bootstrap_replicates,
        bootstrap_seed=config.bootstrap_seed,
        confidence=config.confidence,
        maximum_half_width_db=config.thresholds.body_peak_max_db,
        estimator="linear mean of the per-replica mean absorbed power density",
    )
    consecutive = 0
    stop_at: int | None = None
    for look, direct_look in zip(chi_report["looks"], direct_report["looks"], strict=True):
        replicas = int(look["replicas"])
        if replicas != int(direct_look["replicas"]):
            raise RuntimeError("total and direct susceptibility analyses use different looks")
        look["direct_susceptibility"] = {
            "point_estimate_db": direct_look["point_estimate_db"],
            "endpoint_values_db": direct_look["endpoint_values_db"],
            "point_uncertainty": direct_look["point_uncertainty"],
            "fixed_route_cdf": direct_look["fixed_route_cdf"],
            "stability_from_previous_look": direct_look["stability_from_previous_look"],
            "stopping_role": "reported diagnostic, not part of the total-susceptibility stop",
        }
        look["body_peak_rooftop"] = body[replicas]
        look["body_mean_rooftop"] = {
            **body_mean[replicas],
            "stopping_role": "reported diagnostic. Only body peak enters the stop",
        }
        look["look_pass_without_body"] = look["look_pass"]
        look["look_pass"] = bool(look["look_pass"] and body[replicas]["pass"])
        if look["formal_look"]:
            consecutive = consecutive + 1 if look["look_pass"] else 0
            if consecutive >= 2 and stop_at is None:
                stop_at = replicas
        look["consecutive_formal_passes"] = consecutive
    chi_report["body_peak_rule"] = {
        "model": "rooftop",
        "maximum_simultaneous_half_width_db": config.thresholds.body_peak_max_db,
        "central_estimator": "linear mean of per-replica peak absorbed power density",
    }
    chi_report["reported_curve_bootstraps"] = {
        "total_susceptibility_seed": config.bootstrap_seed,
        "direct_susceptibility_seed": config.bootstrap_seed + 1,
        "body_scalar_seed": config.bootstrap_seed,
        "body_seed_sequence_suffix": 1,
        "replicates": config.bootstrap_replicates,
        "confidence": config.confidence,
    }
    chi_report["stopped"] = stop_at is not None
    chi_report["stop_at_replicas"] = stop_at
    chi_report["cap_reached"] = checkpoint.replicas >= config.looks[-1] and stop_at is None
    return chi_report


def _final_ensemble(
    config: CdfConvergenceConfig,
    reference: Any,
    checkpoint: CampaignCheckpoint,
    analysis: dict[str, Any],
    study: Any,
) -> dict[str, Any]:
    count = analysis["stop_at_replicas"] or min(checkpoint.replicas, config.looks[-1])
    if count != checkpoint.replicas:
        raise RuntimeError("the compact checkpoint cannot remove replicas after the sequential stop")
    mean_rho = checkpoint.rho_sum / count
    coupler = study.BodyCoupler(
        study.PHANTOM,
        float(reference.manifest["run"]["frequency_hz"]),
        body_mass_kg=study.PHANTOM_MASS_KG,
    )
    flat = mean_rho.reshape(-1, mean_rho.shape[-1])
    exposures = coupler.couple_many(
        checkpoint.local_grid,
        flat,
        checkpoint.solid_angle,
        float(reference.manifest["reference_s0_w_m2"]),
        chunk_cells=config.body_chunk_cells,
    )
    direct = np.mean(checkpoint.chi_direct, axis=0, dtype=np.float64)
    rows: list[dict[str, Any]] = []
    for point, index in enumerate(reference.standpoints.index):
        row: dict[str, Any] = {
            "index": int(index),
            "x": float(reference.standpoints.points[point, 0]),
            "y": float(reference.standpoints.points[point, 1]),
            "z": float(reference.standpoints.points[point, 2]),
            "ground_z_m": float(reference.standpoints.ground_z_m[point]),
            "point_kind": reference.standpoints.point_kind[point],
        }
        for model, name in enumerate(MODEL_NAMES):
            exposure = exposures[point * len(MODEL_NAMES) + model]
            row[f"chi_{name}"] = exposure.susceptibility
            row[f"chi_{name}_direct"] = float(direct[point, model])
            for key, value in exposure.as_dict().items():
                row[f"{name}_{key}"] = value
        rows.append(row)
    raw_peak_mean = np.mean(checkpoint.body_peak_rooftop, axis=0, dtype=np.float64)
    ensemble_peak = np.asarray([row["rooftop_peak_sab_w_m2"] for row in rows])
    return {
        "replicas": count,
        "base_seeds": [int(value) for value in checkpoint.base_seeds],
        "rows": rows,
        "rho_sum_sha256": _array_sha256(checkpoint.rho_sum),
        "local_grid_sha256": _array_sha256(checkpoint.local_grid),
        "body_peak_central_estimator_check": {
            "seed_mean_peak_db": [float(value) for value in _to_db(raw_peak_mean)],
            "peak_of_seed_mean_spectrum_db": [float(value) for value in _to_db(ensemble_peak)],
            "difference_db": [float(value) for value in _to_db(raw_peak_mean) - _to_db(ensemble_peak)],
            "maximum_absolute_difference_db": float(np.max(np.abs(_to_db(raw_peak_mean) - _to_db(ensemble_peak)))),
        },
    }


def _write_campaign_checkpoint(
    path: pathlib.Path,
    checkpoint: CampaignCheckpoint,
    identity: str,
    reference: Any,
) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as stream:
        np.savez_compressed(
            stream,
            schema=np.asarray("fixed-walk-cdf-checkpoint-v1"),
            identity_sha256=np.asarray(identity),
            standpoint_array_sha256=np.asarray(reference.standpoints.sha256),
            base_seeds=checkpoint.base_seeds,
            chi=checkpoint.chi,
            chi_direct=checkpoint.chi_direct,
            body_peak_rooftop=checkpoint.body_peak_rooftop,
            body_mean_rooftop=checkpoint.body_mean_rooftop,
            trace_seconds=checkpoint.trace_seconds,
            rho_sum=checkpoint.rho_sum,
            local_grid=checkpoint.local_grid,
            solid_angle=np.asarray(checkpoint.solid_angle, dtype=np.float64),
            model_names=np.asarray(MODEL_NAMES),
        )
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def _load_campaign_checkpoint(
    path: pathlib.Path,
    identity: str,
    reference: Any,
    config: CdfConvergenceConfig,
) -> CampaignCheckpoint | None:
    if not path.is_file():
        return None
    try:
        with np.load(path) as artifact:
            schema = str(artifact["schema"])
            saved_identity = str(artifact["identity_sha256"])
            standpoint_hash = str(artifact["standpoint_array_sha256"])
            model_names = tuple(str(value) for value in artifact["model_names"])
            checkpoint = CampaignCheckpoint(
                base_seeds=np.asarray(artifact["base_seeds"], dtype=np.int64),
                chi=np.asarray(artifact["chi"], dtype=np.float64),
                chi_direct=np.asarray(artifact["chi_direct"], dtype=np.float64),
                body_peak_rooftop=np.asarray(artifact["body_peak_rooftop"], dtype=np.float64),
                body_mean_rooftop=np.asarray(artifact["body_mean_rooftop"], dtype=np.float64),
                trace_seconds=np.asarray(artifact["trace_seconds"], dtype=np.float64),
                rho_sum=np.asarray(artifact["rho_sum"], dtype=np.float64),
                local_grid=np.asarray(artifact["local_grid"], dtype=np.float64),
                solid_angle=float(artifact["solid_angle"]),
            )
    except (KeyError, OSError, TypeError, ValueError):
        return None
    replicas = checkpoint.replicas
    points = int(reference.standpoints.index.size)
    cells = int(reference.manifest["run"]["local_cells"])
    valid = all(
        (
            schema == "fixed-walk-cdf-checkpoint-v1",
            saved_identity == identity,
            standpoint_hash == reference.standpoints.sha256,
            model_names == MODEL_NAMES,
            np.array_equal(checkpoint.base_seeds, np.asarray(config.base_seeds[:replicas])),
            checkpoint.chi.shape == (replicas, points, len(MODEL_NAMES)),
            checkpoint.chi_direct.shape == checkpoint.chi.shape,
            checkpoint.body_peak_rooftop.shape == (replicas, points),
            checkpoint.body_mean_rooftop.shape == (replicas, points),
            checkpoint.trace_seconds.shape == (replicas, points),
            checkpoint.rho_sum.shape == (points, len(MODEL_NAMES), cells),
            checkpoint.local_grid.shape == (cells, 3),
            checkpoint.solid_angle == 4.0 * np.pi / cells,
            replicas <= config.looks[-1],
            all(
                np.all(np.isfinite(array))
                for array in (
                    checkpoint.chi,
                    checkpoint.chi_direct,
                    checkpoint.body_peak_rooftop,
                    checkpoint.body_mean_rooftop,
                    checkpoint.trace_seconds,
                    checkpoint.rho_sum,
                    checkpoint.local_grid,
                )
            ),
            np.all(checkpoint.chi > 0.0),
            np.all(checkpoint.chi_direct >= 0.0),
            np.all(checkpoint.body_peak_rooftop > 0.0),
            np.all(checkpoint.body_mean_rooftop > 0.0),
            np.all(checkpoint.rho_sum >= 0.0),
        )
    )
    return checkpoint if valid else None


def _campaign_manifest(
    config: CdfConvergenceConfig,
    reference: Any,
    checkpoint: CampaignCheckpoint,
    identity: str,
    code: dict[str, Any],
    analysis_path: pathlib.Path,
) -> dict[str, Any]:
    artifact_paths = {
        "plan": config.output_dir / "plan.json",
        "checkpoint": config.output_dir / "checkpoint.npz",
        "analysis": analysis_path,
        "ensemble_locations": config.output_dir / "ensemble_locations.jsonl",
        "figure_png": config.output_dir / "cdf_convergence.png",
        "figure_pdf": config.output_dir / "cdf_convergence.pdf",
    }
    artifact_paths.update(
        {
            f"formal_look_{path.stem.removeprefix('analysis_look')}": path
            for path in sorted(config.output_dir.glob("analysis_look*.json"))
        }
    )
    artifacts = {
        name: {
            "path": path.name,
            "sha256": _file_sha256(path),
            "bytes": path.stat().st_size,
        }
        for name, path in artifact_paths.items()
    }
    return {
        "schema": "fixed-walk-cdf-manifest-v1",
        "created_utc": _utc_now(),
        "identity_sha256": identity,
        "complete_replicas": checkpoint.replicas,
        "base_seeds": [int(value) for value in checkpoint.base_seeds],
        "reference": reference.as_dict(),
        "scientific_config": config.scientific_config(),
        "code": code,
        "runtime": {
            "host": platform.node(),
            "python": platform.python_version(),
            "trace_seconds_total": float(np.sum(checkpoint.trace_seconds)),
        },
        "artifacts": artifacts,
    }


def _write_final_rows(path: pathlib.Path, rows: list[dict[str, Any]]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text("".join(json.dumps(row, allow_nan=False) + "\n" for row in rows))
    temporary.replace(path)


def _plot_convergence(analysis: dict[str, Any], path: pathlib.Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    final = analysis["looks"][-1]
    figure, axes = plt.subplots(1, 2, figsize=(8.5, 3.5))
    colours = {"isotropic": "#1f77b4", "rooftop": "#d62728", "street_small_cell": "#2ca02c"}
    for name in MODEL_NAMES:
        cdf = final["fixed_route_cdf"]["models"][name]
        center = np.asarray(cdf["ordered_estimate_db"])
        width = np.asarray(cdf["ordered_simultaneous_half_width_db"])
        probability = np.asarray(cdf["cdf_probability"])
        axes[0].step(center, probability, where="mid", label=name.replace("_", " "), color=colours[name])
        axes[0].fill_betweenx(probability, center - width, center + width, color=colours[name], alpha=0.15)
    axes[0].set_xlabel(r"$10\log_{10}\chi$ [dB]")
    axes[0].set_ylabel("fraction of fixed route")
    axes[0].set_title(f"CDF and simultaneous 95% seed band, R={final['replicas']}")
    axes[0].legend(fontsize=7)

    formal = [look for look in analysis["looks"] if look["formal_look"]]
    for name in MODEL_NAMES:
        axes[1].plot(
            [look["replicas"] for look in formal],
            [look["point_uncertainty"]["models"][name]["max_half_width_db"] for look in formal],
            marker="o",
            label=name.replace("_", " "),
            color=colours[name],
        )
    axes[1].axhline(
        analysis["thresholds"]["point_max_db"],
        color="0.25",
        linestyle="--",
        linewidth=1.0,
        label="0.15 dB limit",
    )
    axes[1].set_xlabel("complete walk replicas")
    axes[1].set_ylabel("largest point half-width [dB]")
    axes[1].set_title("Monte Carlo error by formal look")
    axes[1].set_xticks([look["replicas"] for look in formal])
    axes[1].legend(fontsize=7)
    for axis in axes:
        axis.grid(alpha=0.25)
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    figure.savefig(path.with_suffix(".pdf"))
    plt.close(figure)


def _write_json_atomic(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    temporary.replace(path)


def _file_sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _array_sha256(array: np.ndarray) -> str:
    value = np.ascontiguousarray(array)
    digest = hashlib.sha256()
    digest.update(value.dtype.str.encode())
    digest.update(str(value.shape).encode())
    digest.update(value.tobytes())
    return digest.hexdigest()


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _to_db(values: np.ndarray) -> np.ndarray:
    if np.any(values <= 0.0):
        raise ValueError("decibel conversion requires positive values")
    return 10.0 * np.log10(values)


def _simultaneous_half_width(
    bootstrap: np.ndarray,
    estimate: np.ndarray,
    confidence: float,
) -> np.ndarray:
    """Return a max-t confidence half-width for an arbitrary statistic family."""
    if bootstrap.shape[1:] != estimate.shape:
        raise ValueError("bootstrap and estimate shapes disagree")
    flat = bootstrap.reshape(bootstrap.shape[0], -1)
    center = estimate.reshape(-1)
    scale = np.std(flat, axis=0, ddof=1)
    nonzero = scale > 0.0
    standardized = np.zeros_like(flat)
    standardized[:, nonzero] = np.abs(flat[:, nonzero] - center[nonzero]) / scale[nonzero]
    critical = float(np.quantile(np.max(standardized, axis=1), confidence))
    return (critical * scale).reshape(estimate.shape)


def _point_report(
    half_width: np.ndarray,
    model_names: tuple[str, ...],
    thresholds: StoppingThresholds,
) -> dict[str, Any]:
    by_model: dict[str, Any] = {}
    for model, name in enumerate(model_names):
        widths = half_width[:, model]
        p90 = float(np.quantile(widths, 0.9))
        maximum = float(np.max(widths))
        by_model[name] = {
            "half_width_db": [float(value) for value in widths],
            "p90_half_width_db": p90,
            "max_half_width_db": maximum,
            "pass": p90 <= thresholds.point_p90_db and maximum <= thresholds.point_max_db,
        }
    return {"models": by_model, "pass": all(value["pass"] for value in by_model.values())}


def _cdf_report(
    estimate_db: np.ndarray,
    bootstrap_db: np.ndarray,
    model_names: tuple[str, ...],
    confidence: float,
    thresholds: StoppingThresholds,
) -> dict[str, Any]:
    quantiles = np.asarray([0.0, 0.10, 0.50, 0.90, 1.0])
    estimate_stats = np.quantile(estimate_db, quantiles, axis=0)
    bootstrap_stats = np.quantile(bootstrap_db, quantiles, axis=1).transpose(1, 0, 2)
    statistic_widths = _simultaneous_half_width(bootstrap_stats, estimate_stats, confidence)

    ordered = np.sort(estimate_db, axis=0)
    bootstrap_ordered = np.sort(bootstrap_db, axis=1)
    ordered_widths = _simultaneous_half_width(bootstrap_ordered, ordered, confidence)
    by_model: dict[str, Any] = {}
    for model, name in enumerate(model_names):
        stats = {
            statistic: {
                "estimate_db": float(estimate_stats[row, model]),
                "half_width_db": float(statistic_widths[row, model]),
            }
            for row, statistic in enumerate(CDF_STATISTICS)
        }
        passed = (
            stats["q50"]["half_width_db"] <= thresholds.cdf_q50_db
            and max(stats["q10"]["half_width_db"], stats["q90"]["half_width_db"]) <= thresholds.cdf_q10_q90_db
            and max(stats["minimum"]["half_width_db"], stats["maximum"]["half_width_db"]) <= thresholds.cdf_endpoint_db
        )
        by_model[name] = {
            "statistics": stats,
            "ordered_estimate_db": [float(value) for value in ordered[:, model]],
            "ordered_simultaneous_half_width_db": [float(value) for value in ordered_widths[:, model]],
            "cdf_probability": [float((rank + 0.5) / ordered.shape[0]) for rank in range(ordered.shape[0])],
            "pass": passed,
        }
    return {"models": by_model, "pass": all(value["pass"] for value in by_model.values())}


def _endpoint_values(estimate_db: np.ndarray, model_names: tuple[str, ...]) -> dict[str, Any]:
    ordered = np.sort(estimate_db, axis=0)
    rows = (0, 1, -2, -1)
    return {
        name: {label: float(ordered[row, model]) for label, row in zip(ENDPOINT_RANKS, rows, strict=True)}
        for model, name in enumerate(model_names)
    }


def _stability_report(
    previous_db: np.ndarray | None,
    current_db: np.ndarray,
    model_names: tuple[str, ...],
    thresholds: StoppingThresholds,
) -> dict[str, Any]:
    if previous_db is None:
        return {"available": False, "models": {}, "pass": False}
    if previous_db.shape != current_db.shape:
        raise ValueError("successive look estimates have different shapes")
    quantiles = np.asarray([0.0, 0.10, 0.50, 0.90, 1.0])
    previous_stats = np.quantile(previous_db, quantiles, axis=0)
    current_stats = np.quantile(current_db, quantiles, axis=0)
    by_model: dict[str, Any] = {}
    for model, name in enumerate(model_names):
        shifts = np.abs(current_stats[:, model] - previous_stats[:, model])
        wasserstein = float(np.mean(np.abs(np.sort(current_db[:, model]) - np.sort(previous_db[:, model]))))
        statistics = {statistic: float(shifts[row]) for row, statistic in enumerate(CDF_STATISTICS)}
        passed = (
            wasserstein <= thresholds.stability_wasserstein_db
            and statistics["q50"] <= thresholds.stability_q50_db
            and max(statistics["q10"], statistics["q90"]) <= thresholds.stability_q10_q90_db
            and max(statistics["minimum"], statistics["maximum"]) <= thresholds.stability_endpoint_db
        )
        by_model[name] = {
            "wasserstein_db": wasserstein,
            "absolute_shift_db": statistics,
            "pass": passed,
        }
    return {"available": True, "models": by_model, "pass": all(value["pass"] for value in by_model.values())}
