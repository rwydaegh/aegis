"""Sequential Monte Carlo stopping for a frozen production walk CDF.

One complete frozen walk is one Monte Carlo replica.  The points within a
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
from collections import Counter
from dataclasses import dataclass
from typing import Any

import numpy as np

from semantic_twin.exposure.cdf_contracts import (
    CdfProductionContract,
    production_contract as resolve_production_contract,
)

MODEL_NAMES = ("isotropic", "rooftop", "street_small_cell")
CDF_STATISTICS = ("minimum", "q10", "q50", "q90", "maximum")
ENDPOINT_RANKS = ("minimum", "second_lowest", "second_highest", "maximum")


@dataclass(frozen=True)
class StoppingThresholds:
    """Maximum allowed confidence half-widths and look shifts."""

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
    bootstrap_alpha_allocation: str
    body_chunk_cells: int
    body_peak_selection_min_fraction: float
    body_model: str
    body_source: str
    body_mass_kg: float
    seed_stream_stride: int
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
        body_source = document["body_source"]
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
            bootstrap_alpha_allocation=str(bootstrap.get("alpha_allocation", "custom allocation")),
            body_chunk_cells=int(body.get("chunk_cells", 512)),
            body_peak_selection_min_fraction=float(body.get("selection_stability_min_fraction", 0.95)),
            body_model=str(document["body_model"]),
            body_source=str(body_source["phantom"]),
            body_mass_kg=float(body_source["mass_kg"]),
            seed_stream_stride=int(document["seed_stream_stride"]),
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
        if not 0.0 < self.body_peak_selection_min_fraction <= 1.0:
            raise ValueError("body peak selection stability fraction must lie in (0, 1]")
        if self.body_model not in MODEL_NAMES:
            raise ValueError(f"body_model must be one of {', '.join(MODEL_NAMES)}")
        if not self.body_source:
            raise ValueError("body_source.phantom must be nonempty")
        if self.body_mass_kg <= 0.0:
            raise ValueError("body_source.mass_kg must be positive")
        if self.seed_stream_stride < 1:
            raise ValueError("seed_stream_stride must be positive")
        self.thresholds.validate()
        contract = self.production_contract
        if contract is not None:
            self._validate_production_config(contract)

    @property
    def production_contract(self) -> CdfProductionContract | None:
        return resolve_production_contract(self.contract)

    @property
    def body_path(self) -> pathlib.Path:
        data_dir = pathlib.Path(os.environ.get("AEGIS_DATA_DIR", "/home/user/aegis/data"))
        return data_dir / f"{self.body_source}.stl"

    def _validate_production_config(self, contract: CdfProductionContract) -> None:
        def relative(path: pathlib.Path) -> str:
            try:
                return path.relative_to(self.root).as_posix()
            except ValueError:
                return str(path)

        expected = {
            "output_dir": contract.output_dir,
            "reference_manifest": contract.reference.manifest,
            "reference_locations": contract.reference.locations,
            "reference_spectra": contract.reference.spectra,
            "diagnostic_look": contract.diagnostic_look,
            "looks": contract.looks,
            "base_seeds": contract.base_seeds,
            "bootstrap_replicates": contract.bootstrap_replicates,
            "bootstrap_seed": contract.bootstrap_seed,
            "confidence": contract.confidence,
            "bootstrap_alpha_allocation": contract.bootstrap_alpha_allocation,
            "body_chunk_cells": contract.body_chunk_cells,
            "body_peak_selection_min_fraction": contract.body_peak_selection_min_fraction,
            "body_model": contract.body.model,
            "body_source": contract.body.phantom,
            "body_mass_kg": contract.body.mass_kg,
            "seed_stream_stride": contract.seed_stream_stride,
            "thresholds": contract.threshold_values(),
            "model_names": contract.run.models,
        }
        actual = {
            "output_dir": relative(self.output_dir),
            "reference_manifest": relative(self.reference_manifest),
            "reference_locations": relative(self.reference_locations),
            "reference_spectra": relative(self.reference_spectra),
            "diagnostic_look": self.diagnostic_look,
            "looks": self.looks,
            "base_seeds": self.base_seeds,
            "bootstrap_replicates": self.bootstrap_replicates,
            "bootstrap_seed": self.bootstrap_seed,
            "confidence": self.confidence,
            "bootstrap_alpha_allocation": self.bootstrap_alpha_allocation,
            "body_chunk_cells": self.body_chunk_cells,
            "body_peak_selection_min_fraction": self.body_peak_selection_min_fraction,
            "body_model": self.body_model,
            "body_source": self.body_source,
            "body_mass_kg": self.body_mass_kg,
            "seed_stream_stride": self.seed_stream_stride,
            "thresholds": dataclasses.asdict(self.thresholds),
            "model_names": MODEL_NAMES,
        }
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
                "planned_familywise_confidence": self.confidence,
                "formal_look_alpha": (1.0 - self.confidence) / len(self.looks),
                "formal_look_confidence": 1.0 - (1.0 - self.confidence) / len(self.looks),
                "alpha_allocation": self.bootstrap_alpha_allocation,
                "unit": "one complete base-seed walk replica",
            },
            "body_peak": {
                "model": self.body_model,
                "chunk_cells": self.body_chunk_cells,
                "bootstrap_target": "peak absorbed density of the ensemble-mean angular spectrum",
                "retained_replica_field": f"complete {self.body_model} level-2 surface absorbed density",
                "selection_stability_min_fraction": self.body_peak_selection_min_fraction,
            },
            "body_source": {
                "phantom": self.body_source,
                "mass_kg": self.body_mass_kg,
                "path": str(self.body_path),
            },
            "seed_stream_stride": self.seed_stream_stride,
            "contract_pinning": {
                "production": self.production_contract is not None,
                "status": "pinned production contract"
                if self.production_contract is not None
                else "unpinned custom campaign",
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
    formal_alpha = (1.0 - confidence) / len(formal_looks) if formal_looks else 1.0 - confidence
    formal_confidence = 1.0 - formal_alpha
    for look in looks:
        prefix = values[:look]
        rng = np.random.default_rng(np.random.SeedSequence([bootstrap_seed, look]))
        indices = rng.integers(0, look, size=(bootstrap_replicates, look))
        bootstrap_mean = np.mean(prefix[indices], axis=1, dtype=np.float64)
        estimate_linear = np.mean(prefix, axis=0, dtype=np.float64)
        estimate_db = _to_db(estimate_linear)
        bootstrap_db = _to_db(bootstrap_mean)
        is_formal = look in formal_looks
        per_look_confidence = formal_confidence if is_formal else confidence
        components = _confidence_components("total", estimate_db, bootstrap_db)
        widths, critical = _joint_simultaneous_half_widths(components, per_look_confidence)
        point_report = _point_report(widths["total.point"], model_names, limits)
        cdf_report = _cdf_report_from_joint(
            estimate_db,
            widths["total.statistics"],
            widths["total.ordered"],
            model_names,
            limits,
        )
        stability = _stability_report(previous_db, estimate_db, model_names, limits)
        uncertainty_pass = bool(point_report["pass"] and cdf_report["pass"])
        look_pass = bool(is_formal and uncertainty_pass and stability["pass"])
        if is_formal:
            consecutive = consecutive + 1 if look_pass else 0
            if consecutive >= 2 and stop_at is None:
                stop_at = look
        document = {
            "replicas": look,
            "formal_look": is_formal,
            "coverage": {
                "role": ("formal alpha-spent look" if is_formal else "diagnostic only, excluded from formal coverage"),
                "per_look_confidence_nominal": per_look_confidence,
                "per_look_alpha": 1.0 - per_look_confidence,
                "joint_max_t_critical_value": critical,
            },
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
            "simultaneous_interval": "one max-t band over points, CDF ranks, and CDF summaries",
        },
        "planned_look_coverage": {
            "familywise_confidence_nominal": confidence,
            "planned_formal_looks": list(formal_looks),
            "alpha_per_formal_look": formal_alpha,
            "confidence_per_formal_look": formal_confidence,
            "finite_sample_exact": False,
            "caveat": "nonparametric max-t bootstrap coverage is approximate at finite replica count",
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


@dataclass(frozen=True)
class CampaignCheckpoint:
    """Compact complete-replica prefix and its running spectrum sum."""

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


def analyse_joint_replicas(
    chi: np.ndarray,
    chi_direct: np.ndarray,
    body_sab: np.ndarray,
    body_mean: np.ndarray,
    *,
    looks: tuple[int, ...],
    planned_formal_looks: tuple[int, ...],
    model_names: tuple[str, ...] = MODEL_NAMES,
    body_model: str = "rooftop",
    bootstrap_replicates: int = 10_000,
    bootstrap_seed: int = 20260805,
    familywise_confidence: float = 0.95,
    body_peak_selection_min_fraction: float = 0.95,
    thresholds: StoppingThresholds | None = None,
) -> dict[str, Any]:
    """Analyse every confidence-bounded curve with one planned-look family.

    One bootstrap draw resamples complete walk replicas and is shared by total
    susceptibility, body peak, and body mean.  One max-t critical value covers
    every reported point, CDF rank, and CDF summary in that look.  The formal
    look alpha is ``(1 - familywise_confidence) / len(planned_formal_looks)``.
    Bonferroni then controls selection over the predeclared formal looks.

    The max-t bands have nominal bootstrap coverage.  They are not exact
    finite-sample confidence sequences.  The familywise statement is valid if
    each per-look bootstrap band attains its nominal coverage.
    """
    total = np.asarray(chi, dtype=np.float64)
    direct = np.asarray(chi_direct, dtype=np.float64)
    sab = np.asarray(body_sab, dtype=np.float64)
    mean = np.asarray(body_mean, dtype=np.float64)
    if total.ndim != 3 or total.shape[2] != len(model_names):
        raise ValueError("chi must have shape (replicas, standpoints, models)")
    if body_model not in model_names:
        raise ValueError("body_model must name one of the source laws")
    if direct.shape != total.shape:
        raise ValueError("direct susceptibility must match total susceptibility")
    if sab.ndim != 3 or sab.shape[:2] != total.shape[:2] or sab.shape[2] < 2:
        raise ValueError("body Sab must have shape (replicas, standpoints, surface elements)")
    if mean.shape != total.shape[:2]:
        raise ValueError("body mean must have shape (replicas, standpoints)")
    if total.shape[1] < 2:
        raise ValueError("at least two standpoints are required for a route CDF")
    if np.any(total <= 0.0) or not np.all(np.isfinite(total)):
        raise ValueError("total susceptibility must be finite and positive")
    if np.any(direct < 0.0) or not np.all(np.isfinite(direct)):
        raise ValueError("direct susceptibility must be finite and nonnegative")
    if np.any(sab < 0.0) or not np.all(np.isfinite(sab)) or np.any(np.max(sab, axis=2) <= 0.0):
        raise ValueError("body Sab must be finite, nonnegative, and positive at its peak")
    if np.any(mean <= 0.0) or not np.all(np.isfinite(mean)):
        raise ValueError("body mean must be finite and positive")
    if not looks or tuple(sorted(set(looks))) != looks or looks[-1] > total.shape[0]:
        raise ValueError("looks must be unique, increasing, and covered by the replicas")
    if not planned_formal_looks or tuple(sorted(set(planned_formal_looks))) != planned_formal_looks:
        raise ValueError("planned formal looks must be nonempty, unique, and increasing")
    if bootstrap_replicates < 100:
        raise ValueError("bootstrap_replicates must be at least 100")
    if not 0.0 < familywise_confidence < 1.0:
        raise ValueError("familywise_confidence must lie between zero and one")
    if not 0.0 < body_peak_selection_min_fraction <= 1.0:
        raise ValueError("body_peak_selection_min_fraction must lie in (0, 1]")
    limits = thresholds or StoppingThresholds()
    limits.validate()

    formal_alpha = (1.0 - familywise_confidence) / len(planned_formal_looks)
    formal_confidence = 1.0 - formal_alpha
    previous_db: np.ndarray | None = None
    documents: list[dict[str, Any]] = []
    consecutive = 0
    stop_at: int | None = None
    for look in looks:
        is_formal = look in planned_formal_looks
        per_look_confidence = formal_confidence if is_formal else familywise_confidence
        rng = np.random.default_rng(np.random.SeedSequence([bootstrap_seed, look, 37]))
        indices = rng.integers(0, look, size=(bootstrap_replicates, look))

        total_estimate_db = _to_db(np.mean(total[:look], axis=0, dtype=np.float64))
        total_bootstrap_db = _to_db(np.mean(total[:look][indices], axis=1, dtype=np.float64))
        peak_estimate, peak_face_band, peak_selection = _bootstrap_peak_of_mean_sab(
            sab[:look],
            indices,
            minimum_stable_fraction=body_peak_selection_min_fraction,
        )
        peak_estimate_db = _to_db(peak_estimate)
        mean_estimate_db = _to_db(np.mean(mean[:look], axis=0, dtype=np.float64))
        mean_bootstrap_db = _to_db(np.mean(mean[:look][indices], axis=1, dtype=np.float64))

        components = {
            **_confidence_components("total", total_estimate_db, total_bootstrap_db),
            **_confidence_components("body_mean", mean_estimate_db, mean_bootstrap_db),
        }
        widths, critical = _joint_simultaneous_half_widths(
            components,
            per_look_confidence,
            extra_standardized_max=peak_face_band["standardized_max"],
        )
        point_report = _point_report(widths["total.point"], model_names, limits)
        cdf_report = _cdf_report_from_joint(
            total_estimate_db,
            widths["total.statistics"],
            widths["total.ordered"],
            model_names,
            limits,
        )
        peak_report = _body_peak_face_band_report(
            peak_estimate_db,
            peak_face_band["estimate_surface"],
            peak_face_band["scale_surface"],
            critical,
            maximum_half_width_db=limits.body_peak_max_db,
            estimator=(
                "maximum surface absorbed density of the linear mean across per-replica Sab fields, "
                "equal to max Sab(mean rho) at level 2"
            ),
            stopping_role="enters the formal stop",
            selection_stability=peak_selection,
        )
        mean_report = _body_report_from_joint(
            mean_estimate_db,
            widths["body_mean.point"],
            widths["body_mean.statistics"],
            widths["body_mean.ordered"],
            maximum_half_width_db=None,
            estimator="linear mean of per-replica mean absorbed power density",
            stopping_role="reported in the joint family but does not enter the stop",
        )
        stability = _stability_report(previous_db, total_estimate_db, model_names, limits)
        uncertainty_pass = bool(point_report["pass"] and cdf_report["pass"] and peak_report["pass"])
        look_pass = bool(is_formal and uncertainty_pass and stability["pass"])
        if is_formal:
            consecutive = consecutive + 1 if look_pass else 0
            if consecutive >= 2 and stop_at is None:
                stop_at = look
        document = {
            "replicas": look,
            "formal_look": is_formal,
            "coverage": {
                "role": ("formal alpha-spent look" if is_formal else "diagnostic only, excluded from formal coverage"),
                "per_look_confidence_nominal": per_look_confidence,
                "per_look_alpha": 1.0 - per_look_confidence,
                "joint_max_t_critical_value": critical,
                "joint_family_statistics": int(
                    sum(estimate.size for _bootstrap, estimate in components.values())
                    + peak_face_band["estimate_surface"].size
                ),
            },
            "point_estimate_db": {
                name: [float(value) for value in total_estimate_db[:, model]] for model, name in enumerate(model_names)
            },
            "endpoint_values_db": _endpoint_values(total_estimate_db, model_names),
            "point_uncertainty": point_report,
            "fixed_route_cdf": cdf_report,
            f"body_peak_{body_model}": peak_report,
            f"body_mean_{body_model}": mean_report,
            "direct_susceptibility": _direct_zero_report(direct[:look], model_names),
            "stability_from_previous_look": stability,
            "uncertainty_pass": uncertainty_pass,
            "look_pass": look_pass,
            "consecutive_formal_passes": consecutive,
        }
        documents.append(document)
        previous_db = total_estimate_db

    return {
        "schema": "fixed-walk-cdf-stopping-v3",
        "independent_unit": "one complete base-seed walk replica",
        "aggregation": "arithmetic mean in linear power for each fixed standpoint, then 10 log10",
        "bootstrap": {
            "replicates": bootstrap_replicates,
            "seed": bootstrap_seed,
            "resampling": "base-seed walk clusters with every standpoint and confidence-bounded metric kept together",
            "simultaneous_interval": "one max-t band over total susceptibility and both body metrics",
            "body_peak_resampling": (
                "tie-robust simultaneous band over every retained level-2 surface Sab mean, projected through max"
            ),
        },
        "planned_look_coverage": {
            "familywise_confidence_nominal": familywise_confidence,
            "familywise_alpha": 1.0 - familywise_confidence,
            "planned_formal_looks": list(planned_formal_looks),
            "alpha_allocation": "equal Bonferroni allocation",
            "alpha_per_formal_look": formal_alpha,
            "confidence_per_formal_look": formal_confidence,
            "production_exact_values": (
                {
                    "familywise_alpha": "1/20",
                    "alpha_per_formal_look": "1/60",
                    "confidence_per_formal_look": "59/60",
                }
                if familywise_confidence == 0.95 and len(planned_formal_looks) == 3
                else None
            ),
            "coverage_statement": (
                "Bonferroni limits formal-look familywise error to 0.05 if each 59/60 "
                "max-t bootstrap band attains its nominal coverage"
                if familywise_confidence == 0.95 and len(planned_formal_looks) == 3
                else "Bonferroni limits familywise error to the declared alpha if each per-look band attains its nominal coverage"
            ),
            "finite_sample_exact": False,
            "caveat": "nonparametric max-t bootstrap coverage is approximate at finite replica count",
        },
        "confidence_family": {
            "included": [
                "total susceptibility at every standpoint and source law",
                "total susceptibility fixed-route CDF ranks and minimum, q10, q50, q90, maximum",
                f"every {body_model} surface Sab mean, whose band is projected to the peak of the ensemble-mean spectrum and CDF",
                f"linear mean of per-replica {body_model} mean absorbed density at every standpoint and its fixed-route CDF",
            ],
            "excluded": [
                "direct susceptibility, whose physical zero is reported as an atom at zero without a dB confidence interval",
                f"linear mean of per-replica {body_model} peaks, which is retained only as a Jensen-gap diagnostic",
            ],
        },
        "route_sample": {
            "standpoints": int(total.shape[1]),
            "cdf_step": float(1.0 / total.shape[1]),
            "spatial_sampling_uncertainty_included": False,
        },
        "thresholds": dataclasses.asdict(limits),
        "looks": documents,
        "stopped": stop_at is not None,
        "stop_at_replicas": stop_at,
        "cap_reached": total.shape[0] >= planned_formal_looks[-1] and stop_at is None,
    }


def _confidence_components(
    prefix: str,
    estimate_db: np.ndarray,
    bootstrap_db: np.ndarray,
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    quantiles = np.asarray([0.0, 0.10, 0.50, 0.90, 1.0])
    estimate_statistics = np.quantile(estimate_db, quantiles, axis=0)
    bootstrap_statistics = np.quantile(bootstrap_db, quantiles, axis=1).transpose((1, 0, *range(2, bootstrap_db.ndim)))
    return {
        f"{prefix}.point": (bootstrap_db, estimate_db),
        f"{prefix}.statistics": (bootstrap_statistics, estimate_statistics),
        f"{prefix}.ordered": (np.sort(bootstrap_db, axis=1), np.sort(estimate_db, axis=0)),
    }


def _bootstrap_peak_of_mean_sab(
    sab: np.ndarray,
    bootstrap_indices: np.ndarray,
    *,
    minimum_stable_fraction: float,
    bootstrap_batch: int = 16,
) -> tuple[np.ndarray, dict[str, np.ndarray], dict[str, Any]]:
    """Evaluate bootstrap peaks and a tie-robust band over all surface means."""
    fields = np.asarray(sab, dtype=np.float64)
    indices = np.asarray(bootstrap_indices, dtype=np.int64)
    replicas, points, surface_elements = fields.shape
    if indices.ndim != 2 or indices.shape[1] != replicas:
        raise ValueError("bootstrap indices must resample every retained body replica")
    if np.any(indices < 0) or np.any(indices >= replicas):
        raise ValueError("bootstrap indices are outside the retained replica prefix")
    if bootstrap_batch < 1:
        raise ValueError("body bootstrap batch must be positive")

    bootstrap_replicates = indices.shape[0]
    weights = np.zeros((bootstrap_replicates, replicas), dtype=np.float64)
    rows = np.repeat(np.arange(bootstrap_replicates), replicas)
    np.add.at(weights, (rows, indices.reshape(-1)), 1.0 / replicas)

    flat = fields.reshape(replicas, points * surface_elements)
    surface_sum = np.sum(fields, axis=0, dtype=np.float64)
    estimate_surface = surface_sum / replicas
    estimate_winner = np.argmax(estimate_surface, axis=1)
    estimate = np.max(estimate_surface, axis=1)
    scale_surface = np.std(fields, axis=0, ddof=0) / np.sqrt(replicas)
    safe_scale = np.where(scale_surface > 0.0, scale_surface, np.inf)
    bootstrap_peak = np.empty((bootstrap_replicates, points), dtype=np.float64)
    bootstrap_winner = np.empty((bootstrap_replicates, points), dtype=np.int64)
    standardized_max = np.empty(bootstrap_replicates, dtype=np.float64)
    for start in range(0, bootstrap_replicates, bootstrap_batch):
        stop = min(start + bootstrap_batch, bootstrap_replicates)
        weighted = (weights[start:stop] @ flat).reshape(stop - start, points, surface_elements)
        bootstrap_peak[start:stop] = np.max(weighted, axis=2)
        bootstrap_winner[start:stop] = np.argmax(weighted, axis=2)
        weighted -= estimate_surface
        np.abs(weighted, out=weighted)
        weighted /= safe_scale
        standardized_max[start:stop] = np.max(weighted, axis=(1, 2))

    leave_one_out_winner = np.empty((replicas, points), dtype=np.int64)
    for replica in range(replicas):
        leave_one_out = (surface_sum - fields[replica]) / (replicas - 1)
        leave_one_out_winner[replica] = np.argmax(leave_one_out, axis=1)

    seed_mean_peak = np.mean(np.max(fields, axis=2), axis=0, dtype=np.float64)
    bootstrap_peak_db = _to_db(bootstrap_peak)
    by_point: list[dict[str, Any]] = []
    for point in range(points):
        winner = int(estimate_winner[point])
        reference_profile = fields[:, point, winner]
        equivalent = np.all(
            np.isclose(
                fields[:, point, :],
                reference_profile[:, None],
                rtol=1.0e-12,
                atol=1.0e-15,
            ),
            axis=0,
        )
        bootstrap_fraction = float(np.mean(equivalent[bootstrap_winner[:, point]]))
        leave_one_out_stable = bool(np.all(equivalent[leave_one_out_winner[:, point]]))
        passed = bootstrap_fraction >= minimum_stable_fraction and leave_one_out_stable
        by_point.append(
            {
                "surface_element": winner,
                "equivalent_surface_elements": int(np.count_nonzero(equivalent)),
                "bootstrap_equivalent_winner_fraction": bootstrap_fraction,
                "leave_one_out_equivalent_winner": leave_one_out_stable,
                "seed_mean_peak_minus_physical_peak_db": float(
                    10.0 * np.log10(seed_mean_peak[point] / estimate[point])
                ),
                "pass": passed,
            }
        )
    return (
        estimate,
        {
            "estimate_surface": estimate_surface,
            "scale_surface": scale_surface,
            "standardized_max": standardized_max,
        },
        {
            "criterion": (
                "the full-sample peak response class wins at least the declared fraction of bootstrap resamples "
                "and every leave-one-replica-out ensemble"
            ),
            "minimum_bootstrap_equivalent_winner_fraction": minimum_stable_fraction,
            "surface_elements": surface_elements,
            "ordinary_peak_bootstrap_quantiles_db": {
                name: [float(value) for value in np.quantile(bootstrap_peak_db, quantile, axis=0)]
                for name, quantile in (("q025", 0.025), ("q50", 0.5), ("q975", 0.975))
            },
            "stopping_role": (
                "regularity diagnostic only. The tie-robust projected surface band remains the formal interval"
            ),
            "points": by_point,
            "pass": all(point["pass"] for point in by_point),
        },
    )


def _joint_simultaneous_half_widths(
    components: dict[str, tuple[np.ndarray, np.ndarray]],
    confidence: float,
    *,
    extra_standardized_max: np.ndarray | None = None,
) -> tuple[dict[str, np.ndarray], float]:
    """Use one studentized maximum over every component in a reported family."""
    if not components:
        raise ValueError("a joint confidence family cannot be empty")
    bootstrap_count = {bootstrap.shape[0] for bootstrap, _estimate in components.values()}
    if len(bootstrap_count) != 1:
        raise ValueError("joint confidence components use different bootstrap counts")
    standardized: list[np.ndarray] = []
    scales: dict[str, np.ndarray] = {}
    for name, (bootstrap, estimate) in components.items():
        if bootstrap.shape[1:] != estimate.shape:
            raise ValueError(f"joint confidence component {name} has mismatched shapes")
        flat = bootstrap.reshape(bootstrap.shape[0], -1)
        center = estimate.reshape(-1)
        scale = np.std(flat, axis=0, ddof=1)
        nonzero = scale > 0.0
        value = np.zeros_like(flat)
        value[:, nonzero] = np.abs(flat[:, nonzero] - center[nonzero]) / scale[nonzero]
        standardized.append(value)
        scales[name] = scale.reshape(estimate.shape)
    maximum = np.max(np.concatenate(standardized, axis=1), axis=1)
    if extra_standardized_max is not None:
        extra = np.asarray(extra_standardized_max, dtype=np.float64)
        if extra.shape != maximum.shape or not np.all(np.isfinite(extra)):
            raise ValueError("extra standardized maximum must be finite and match the bootstrap count")
        maximum = np.maximum(maximum, extra)
    critical = float(np.quantile(maximum, confidence))
    return {name: critical * scale for name, scale in scales.items()}, critical


def _cdf_report_from_joint(
    estimate_db: np.ndarray,
    statistic_widths: np.ndarray,
    ordered_widths: np.ndarray,
    model_names: tuple[str, ...],
    thresholds: StoppingThresholds,
) -> dict[str, Any]:
    quantiles = np.asarray([0.0, 0.10, 0.50, 0.90, 1.0])
    statistics = np.quantile(estimate_db, quantiles, axis=0)
    ordered = np.sort(estimate_db, axis=0)
    by_model: dict[str, Any] = {}
    for model, name in enumerate(model_names):
        stats = {
            statistic: {
                "estimate_db": float(statistics[row, model]),
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


def _body_peak_face_band_report(
    estimate_db: np.ndarray,
    estimate_surface: np.ndarray,
    scale_surface: np.ndarray,
    critical: float,
    *,
    maximum_half_width_db: float,
    estimator: str,
    stopping_role: str,
    selection_stability: dict[str, Any],
) -> dict[str, Any]:
    """Project a simultaneous surface-mean band through the peak functional."""
    lower_peak = np.max(estimate_surface - critical * scale_surface, axis=1)
    upper_peak = np.max(estimate_surface + critical * scale_surface, axis=1)
    finite_lower = bool(np.all(lower_peak > 0.0))
    upper_db = _to_db(upper_peak)
    if finite_lower:
        lower_db = _to_db(lower_peak)
        point_width = np.maximum(estimate_db - lower_db, upper_db - estimate_db)
        ordered_estimate = np.sort(estimate_db)
        ordered_lower = np.sort(lower_db)
        ordered_upper = np.sort(upper_db)
        ordered_width = np.maximum(ordered_estimate - ordered_lower, ordered_upper - ordered_estimate)
        quantiles = np.asarray([0.0, 0.10, 0.50, 0.90, 1.0])
        estimate_statistics = np.quantile(estimate_db, quantiles)
        lower_statistics = np.quantile(lower_db, quantiles)
        upper_statistics = np.quantile(upper_db, quantiles)
        statistic_width = np.maximum(
            estimate_statistics - lower_statistics,
            upper_statistics - estimate_statistics,
        )
        maximum = float(np.max(point_width))
        statistics = {
            name: {
                "estimate_db": float(estimate_statistics[row]),
                "lower_db": float(lower_statistics[row]),
                "upper_db": float(upper_statistics[row]),
                "half_width_db": float(statistic_width[row]),
            }
            for row, name in enumerate(CDF_STATISTICS)
        }
        lower_values: list[float | None] = [float(value) for value in lower_db]
        point_width_values: list[float | None] = [float(value) for value in point_width]
        ordered_lower_values: list[float | None] = [float(value) for value in ordered_lower]
        ordered_width_values: list[float | None] = [float(value) for value in ordered_width]
    else:
        maximum = float("inf")
        ordered_estimate = np.sort(estimate_db)
        ordered_upper = np.sort(upper_db)
        statistics = {}
        lower_values = [None] * estimate_db.size
        point_width_values = [None] * estimate_db.size
        ordered_lower_values = [None] * estimate_db.size
        ordered_width_values = [None] * estimate_db.size
    passed = finite_lower and maximum <= maximum_half_width_db
    return {
        "point_estimate_db": [float(value) for value in estimate_db],
        "point_lower_db": lower_values,
        "point_upper_db": [float(value) for value in upper_db],
        "point_simultaneous_half_width_db": point_width_values,
        "max_half_width_db": maximum if np.isfinite(maximum) else None,
        "finite_lower_bound": finite_lower,
        "fixed_route_cdf": {
            "statistics": statistics,
            "ordered_estimate_db": [float(value) for value in ordered_estimate],
            "ordered_lower_db": ordered_lower_values,
            "ordered_upper_db": [float(value) for value in ordered_upper],
            "ordered_simultaneous_half_width_db": ordered_width_values,
            "cdf_probability": [float((rank + 0.5) / ordered_estimate.size) for rank in range(ordered_estimate.size)],
        },
        "pass": passed,
        "maximum_half_width_threshold_db": maximum_half_width_db,
        "estimator": estimator,
        "interval_method": (
            "one joint max-t band over every surface Sab mean, projected as max(lower) and max(upper). "
            "This remains valid for tied peak surfaces whenever the joint face band covers"
        ),
        "face_mean_family_statistics": int(estimate_surface.size),
        "stopping_role": stopping_role,
        "peak_selection_stability": selection_stability,
    }


def _body_report_from_joint(
    estimate_db: np.ndarray,
    point_widths: np.ndarray,
    statistic_widths: np.ndarray,
    ordered_widths: np.ndarray,
    *,
    maximum_half_width_db: float | None,
    estimator: str,
    stopping_role: str,
    selection_stability: dict[str, Any] | None = None,
) -> dict[str, Any]:
    quantiles = np.asarray([0.0, 0.10, 0.50, 0.90, 1.0])
    statistics = np.quantile(estimate_db, quantiles)
    ordered = np.sort(estimate_db)
    maximum = float(np.max(point_widths))
    return {
        "point_estimate_db": [float(value) for value in estimate_db],
        "point_simultaneous_half_width_db": [float(value) for value in point_widths],
        "max_half_width_db": maximum,
        "fixed_route_cdf": {
            "statistics": {
                statistic: {
                    "estimate_db": float(statistics[row]),
                    "half_width_db": float(statistic_widths[row]),
                }
                for row, statistic in enumerate(CDF_STATISTICS)
            },
            "ordered_estimate_db": [float(value) for value in ordered],
            "ordered_simultaneous_half_width_db": [float(value) for value in ordered_widths],
            "cdf_probability": [float((rank + 0.5) / ordered.size) for rank in range(ordered.size)],
        },
        "pass": maximum_half_width_db is None or maximum <= maximum_half_width_db,
        "maximum_half_width_threshold_db": maximum_half_width_db,
        "estimator": estimator,
        "stopping_role": stopping_role,
        **({"peak_selection_stability": selection_stability} if selection_stability is not None else {}),
    }


def _direct_zero_report(values: np.ndarray, model_names: tuple[str, ...]) -> dict[str, Any]:
    """Keep physical direct-path zeros exact instead of inventing a dB floor."""
    estimate = np.mean(values, axis=0, dtype=np.float64)
    zero_counts = np.count_nonzero(values == 0.0, axis=0)
    by_model: dict[str, Any] = {}
    for model, name in enumerate(model_names):
        model_estimate = estimate[:, model]
        positive = model_estimate > 0.0
        point_db: list[float | None] = [
            float(10.0 * np.log10(value)) if value > 0.0 else None for value in model_estimate
        ]
        by_model[name] = {
            "point_estimate_linear": [float(value) for value in model_estimate],
            "point_estimate_db": point_db,
            "zero_replica_count_by_standpoint": [int(value) for value in zero_counts[:, model]],
            "zero_estimate_standpoints": int(np.count_nonzero(~positive)),
            "cdf_atom_at_zero": float(np.count_nonzero(~positive) / model_estimate.size),
            "positive_ordered_estimate_db": [float(value) for value in np.sort(_to_db(model_estimate[positive]))],
        }
    return {
        "models": by_model,
        "uncertainty_role": "point estimates only. Direct susceptibility is outside the simultaneous confidence family and stop",
        "zero_policy": (
            "exact zero remains a probability atom at zero. No logarithmic floor, pseudo-count, or dB confidence interval is used"
        ),
    }


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
    reference = load_reference(config, body_path=config.body_path)
    _validate_production_reference(config, reference)
    tissue_database = _tissue_database_identity()
    _validate_production_tissue_database(config, tissue_database)
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
            "schema": "fixed-walk-cdf-campaign-v3",
            "config": config.scientific_config(),
            "reference": reference.as_dict(),
            "tissue_database": {
                "sha256": tissue_database["sha256"],
                "bytes": tissue_database["bytes"],
            },
            "source": numerical_code,
            "models": list(MODEL_NAMES),
        }
    )
    plan = {
        "schema": "fixed-walk-cdf-plan-v3",
        "created_utc": _utc_now(),
        "identity_sha256": identity,
        "scientific_config": config.scientific_config(),
        "reference": reference.as_dict(),
        "tissue_database": tissue_database,
        "code": code,
        "identity_code_fields": numerical_code,
        "models": list(MODEL_NAMES),
        "seed_rule": (
            config.production_contract.seed_stream_rule
            if config.production_contract is not None
            else f"base seed + {config.seed_stream_stride} * frozen standpoint index"
        ),
        "retention": (
            f"per-replica scalar rows, complete {config.body_model} level-2 surface Sab fields, and one running "
            "linear-power "
            "rho sum. Individual replica spectra and paths are not retained"
        ),
    }
    _quarantine_stale_generation(config.output_dir, identity)
    plan_path = _prepare_campaign_plan(config.output_dir, identity, plan, dry_run=dry_run)
    if dry_run:
        return plan_path

    checkpoint_path = config.output_dir / "checkpoint.npz"
    checkpoint = _load_campaign_checkpoint(
        checkpoint_path,
        identity,
        reference,
        config,
        tissue_database["sha256"],
    )
    if analyse_only and checkpoint is None:
        raise RuntimeError("no valid campaign checkpoint is available to analyse")

    trace_analysis: dict[str, Any] | None = None
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
            str(config.body_path),
            float(manifest_run["frequency_hz"]),
            body_mass_kg=config.body_mass_kg,
        )
        checkpoint = _empty_checkpoint(tracer, coupler, reference) if checkpoint is None else checkpoint
        checkpoint, trace_analysis = _trace_until_stop(
            config,
            reference,
            tracer,
            coupler,
            checkpoint,
            checkpoint_path,
            identity,
            tissue_database["sha256"],
        )

    if checkpoint is None:
        raise AssertionError("campaign checkpoint was not prepared")
    analysis = trace_analysis or _write_reached_formal_analyses(config, checkpoint, identity)
    if analysis is None:
        raise RuntimeError(f"at least {config.looks[0]} complete replicas are needed for a formal analysis")
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
    manifest = _campaign_manifest(
        config,
        reference,
        checkpoint,
        identity,
        code,
        tissue_database,
        analysis_path,
    )
    _write_json_atomic(config.output_dir / "manifest.json", manifest)
    return analysis_path


def _quarantine_stale_generation(output_dir: pathlib.Path, identity: str) -> pathlib.Path | None:
    """Move an incomplete or different output generation aside before reuse."""
    managed = [
        output_dir / "plan.json",
        output_dir / "checkpoint.npz",
        output_dir / "analysis.json",
        output_dir / "ensemble_locations.jsonl",
        output_dir / "cdf_convergence.png",
        output_dir / "cdf_convergence.pdf",
        output_dir / "manifest.json",
        *sorted(output_dir.glob("analysis_look*.json")),
    ]
    existing = [path for path in managed if path.exists()]
    if not existing:
        return None

    identity_paths = [
        path
        for path in existing
        if path.name in {"plan.json", "checkpoint.npz", "analysis.json", "manifest.json"}
        or path.name.startswith("analysis_look")
    ]
    found: dict[str, str | None] = {}
    for path in identity_paths:
        try:
            if path.suffix == ".npz":
                with np.load(path) as artifact:
                    found[path.name] = str(artifact["identity_sha256"])
            else:
                found[path.name] = str(json.loads(path.read_text())["identity_sha256"])
        except (KeyError, OSError, TypeError, ValueError):
            found[path.name] = None
    if found and all(value == identity for value in found.values()):
        return None

    labels = sorted({value for value in found.values() if value})
    old_label = labels[0][:12] if len(labels) == 1 else "mixed-or-unreadable"
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    destination = output_dir / "quarantine" / f"{stamp}-{time.time_ns() % 1_000_000_000:09d}-{old_label}"
    destination.mkdir(parents=True, exist_ok=False)
    moved: list[str] = []
    for path in existing:
        os.replace(path, destination / path.name)
        moved.append(path.name)
    _write_json_atomic(
        destination / "quarantine_record.json",
        {
            "schema": "fixed-walk-cdf-quarantine-v1",
            "created_utc": _utc_now(),
            "replacement_identity_sha256": identity,
            "found_identity_by_file": found,
            "moved_files": moved,
            "reason": "managed outputs did not all carry the replacement campaign identity",
        },
    )
    return destination


def _prepare_campaign_plan(
    output_dir: pathlib.Path,
    identity: str,
    plan: dict[str, Any],
    *,
    dry_run: bool,
) -> pathlib.Path:
    """Verify any final seal before preserving or creating a campaign plan."""
    path = output_dir / "plan.json"
    manifest_path = output_dir / "manifest.json"
    if manifest_path.is_file():
        _verify_sealed_generation(output_dir, identity)
    if path.is_file():
        try:
            saved_identity = json.loads(path.read_text())["identity_sha256"]
        except (KeyError, OSError, TypeError, ValueError) as error:
            raise RuntimeError("campaign plan is unreadable after generation quarantine") from error
        if saved_identity != identity:
            raise RuntimeError("campaign plan has a different identity after generation quarantine")
        return path
    _write_json_atomic(path, plan)
    return path


def _verify_sealed_generation(output_dir: pathlib.Path, identity: str) -> None:
    """Verify every artifact sealed by a same-identity final manifest."""
    manifest_path = output_dir / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text())
        if manifest["identity_sha256"] != identity:
            raise RuntimeError("sealed manifest belongs to a different campaign identity")
        artifacts = manifest["artifacts"]
        if not isinstance(artifacts, dict) or "plan" not in artifacts:
            raise RuntimeError("sealed campaign manifest does not include the campaign plan")
    except (KeyError, OSError, TypeError, ValueError) as error:
        raise RuntimeError("sealed campaign manifest is unreadable") from error
    for name, metadata in artifacts.items():
        path = output_dir / str(metadata["path"])
        if path.parent.resolve() != output_dir.resolve():
            raise RuntimeError(f"sealed artifact {name} escapes the campaign output directory")
        if not path.is_file():
            raise RuntimeError(f"sealed artifact {name} is missing")
        if path.stat().st_size != int(metadata["bytes"]) or _file_sha256(path) != metadata["sha256"]:
            raise RuntimeError(f"sealed artifact {name} does not match its manifest")


def archived_rooftop_diagnostic(config: CdfConvergenceConfig) -> pathlib.Path:
    """Validate the analysis with the archived eight-seed rooftop campaign."""
    from semantic_twin.exposure.angular_convergence import file_sha256, load_reference
    from semantic_twin.exposure.coupler import BodyCoupler

    contract = config.production_contract
    if contract is None or contract.archived_rooftop_run_dir is None:
        raise ValueError("the archived rooftop diagnostic is available only for the Korenmarkt production contract")
    reference = load_reference(config, body_path=config.body_path)
    _validate_production_reference(config, reference)
    run_root = config.root / contract.archived_rooftop_run_dir
    seeds = tuple(range(7, 15))
    chi_rows: list[list[float]] = []
    direct_rows: list[list[float]] = []
    peak_rows: list[list[float]] = []
    mean_rows: list[list[float]] = []
    rho_rows: list[np.ndarray] = []
    common_grid: np.ndarray | None = None
    common_solid_angle: float | None = None
    inputs: list[dict[str, Any]] = []
    expected_index = [int(value) for value in reference.standpoints.index]
    for seed in seeds:
        run_dir = run_root / f"cells4096_rays1600000_seed{seed}"
        manifest_path = run_dir / "manifest.json"
        metrics_path = run_dir / "metrics.json"
        spectra_path = run_dir / "spectra.npz"
        manifest = json.loads(manifest_path.read_text())
        metrics = json.loads(metrics_path.read_text())
        rows = list(metrics["rows"])
        if manifest.get("complete") is not True:
            raise ValueError(f"archived rooftop seed {seed} is incomplete")
        if manifest.get("metrics_file_sha256") != file_sha256(metrics_path):
            raise ValueError(f"archived rooftop seed {seed} metrics do not match their manifest")
        if manifest.get("spectra_file_sha256") != file_sha256(spectra_path):
            raise ValueError(f"archived rooftop seed {seed} spectra do not match their manifest")
        if [int(row["index"]) for row in rows] != expected_index:
            raise ValueError(f"archived rooftop seed {seed} uses a different frozen route")
        chi_rows.append([float(row["chi"]) for row in rows])
        direct_rows.append([float(row["trace"]["chi_rooftop_direct"]) for row in rows])
        peak_rows.append([float(row["body"]["peak_sab_w_m2"]) for row in rows])
        mean_rows.append([float(row["body"]["mean_sab_w_m2"]) for row in rows])
        with np.load(spectra_path) as spectra:
            if not np.array_equal(np.asarray(spectra["index"], dtype=np.int64), reference.standpoints.index):
                raise ValueError(f"archived rooftop seed {seed} spectra use a different frozen route")
            grid = np.asarray(spectra["local_grid"], dtype=np.float64)
            solid_angle = float(spectra["solid_angle"])
            if common_grid is None:
                common_grid = grid
                common_solid_angle = solid_angle
            elif not np.array_equal(grid, common_grid) or solid_angle != common_solid_angle:
                raise ValueError("archived rooftop spectra use different angular grids")
            rho_rows.append(np.asarray(spectra["rho_rooftop"], dtype=np.float64))
        inputs.append(
            {
                "base_seed": seed,
                "identity_sha256": manifest["identity_sha256"],
                "manifest_path": str(manifest_path),
                "manifest_sha256": file_sha256(manifest_path),
                "metrics_path": str(metrics_path),
                "metrics_sha256": file_sha256(metrics_path),
                "spectra_path": str(spectra_path),
                "spectra_sha256": file_sha256(spectra_path),
            }
        )
    chi = np.asarray(chi_rows, dtype=np.float64)[:, :, None]
    direct = np.asarray(direct_rows, dtype=np.float64)[:, :, None]
    archived_peak = np.asarray(peak_rows, dtype=np.float64)
    mean = np.asarray(mean_rows, dtype=np.float64)
    if common_grid is None or common_solid_angle is None:
        raise AssertionError("archived rooftop angular grid was not loaded")
    rho = np.asarray(rho_rows, dtype=np.float64)
    coupler = BodyCoupler(
        str(config.body_path),
        float(reference.manifest["run"]["frequency_hz"]),
        body_mass_kg=config.body_mass_kg,
    )
    exposures, flat_sab = coupler.couple_many_with_sab(
        common_grid,
        rho.reshape(-1, rho.shape[-1]),
        common_solid_angle,
        float(reference.manifest["reference_s0_w_m2"]),
        chunk_cells=config.body_chunk_cells,
    )
    body_sab = flat_sab.reshape(len(seeds), chi.shape[1], -1)
    computed_peak = np.asarray([exposure.peak_sab_w_m2 for exposure in exposures]).reshape(archived_peak.shape)
    computed_mean = np.asarray([exposure.mean_sab_w_m2 for exposure in exposures]).reshape(mean.shape)
    if not np.allclose(computed_peak, archived_peak, rtol=2.0e-14, atol=1.0e-15):
        raise ValueError("recomputed archived body peaks disagree with their metrics")
    if not np.allclose(computed_mean, mean, rtol=2.0e-14, atol=1.0e-15):
        raise ValueError("recomputed archived body means disagree with their metrics")
    joint_analysis = analyse_joint_replicas(
        chi,
        direct,
        body_sab,
        mean,
        looks=(8,),
        planned_formal_looks=config.looks,
        model_names=("rooftop",),
        bootstrap_replicates=config.bootstrap_replicates,
        bootstrap_seed=config.bootstrap_seed,
        familywise_confidence=config.confidence,
        body_peak_selection_min_fraction=config.body_peak_selection_min_fraction,
        thresholds=config.thresholds,
    )
    document = {
        "schema": "archived-rooftop-seed-diagnostic-v3",
        "created_utc": _utc_now(),
        "scope": (
            "one-look rooftop diagnostic with one joint confidence family for total susceptibility and both body metrics. "
            "It cannot replace the required three-law planned-look campaign"
        ),
        "seeds": list(seeds),
        "standpoints": int(chi.shape[1]),
        "bootstrap": {
            "replicates": config.bootstrap_replicates,
            "seed": config.bootstrap_seed,
            "confidence": config.confidence,
        },
        "analysis_source_sha256": file_sha256(pathlib.Path(__file__)),
        "body_coupler_source_sha256": file_sha256(pathlib.Path(__file__).with_name("coupler.py")),
        "reference": reference.as_dict(),
        "inputs": inputs,
        "joint_analysis": joint_analysis,
    }
    path = config.output_dir / "existing_rooftop_diagnostic.json"
    _write_json_atomic(path, document)
    return path


def _validate_production_reference(config: CdfConvergenceConfig, reference: Any) -> None:
    """Pin the named production contract to the accepted final generation."""
    streams = {
        int(base + config.seed_stream_stride * index)
        for base in config.base_seeds
        for index in reference.standpoints.index
    }
    expected_streams = len(config.base_seeds) * reference.standpoints.index.size
    if len(streams) != expected_streams:
        raise ValueError("CDF base-seed mapping contains a random-stream collision")
    contract = config.production_contract
    if contract is None:
        return
    identity = reference.as_dict()
    expected_hashes = {
        **contract.reference_identity_values(),
        "body_sha256": contract.body.sha256,
    }
    actual_hashes = _pinned_values(identity, expected_hashes, "reference identity")
    if actual_hashes != expected_hashes:
        raise ValueError(f"production CDF reference identity changed: {actual_hashes} != {expected_hashes}")
    expected_files = contract.reference.hashes()
    reference_files = identity.get("reference_files") if isinstance(identity, dict) else None
    if not isinstance(reference_files, dict):
        raise ValueError("production CDF output generation changed: reference files are missing")
    actual_files: dict[str, Any] = {}
    for name in expected_files:
        record = reference_files.get(name)
        actual_files[name] = record.get("sha256") if isinstance(record, dict) else None
    if actual_files != expected_files:
        raise ValueError(f"production CDF output generation changed: {actual_files} != {expected_files}")
    manifest = reference.manifest if isinstance(reference.manifest, dict) else {}
    run = manifest.get("run")
    expected_run = contract.run_setting_values()
    actual_run = _pinned_values(run, expected_run, "run settings")
    if actual_run != expected_run:
        raise ValueError(f"production CDF run settings changed: {actual_run} != {expected_run}")
    expected_body = contract.body.manifest_fields()
    actual_body = _pinned_values(manifest.get("body"), expected_body, "body source")
    if actual_body != expected_body:
        raise ValueError(f"production CDF body source changed: {actual_body} != {expected_body}")
    expected_point_kinds = contract.point_kind_count_values()
    actual_point_kinds = dict(Counter(reference.standpoints.point_kind))
    if actual_point_kinds != expected_point_kinds:
        raise ValueError(f"production CDF point kinds changed: {actual_point_kinds} != {expected_point_kinds}")


def _pinned_values(document: Any, expected: dict[str, Any], label: str) -> dict[str, Any]:
    """Read every required field while turning omissions into a closed failure."""
    if not isinstance(document, dict):
        raise ValueError(f"production CDF {label} changed: expected an object")
    missing = set(expected) - set(document)
    if missing:
        raise ValueError(f"production CDF {label} changed: missing {', '.join(sorted(missing))}")
    return {name: document[name] for name in expected}


def _tissue_database_identity() -> dict[str, Any]:
    """Hash the exact IT'IS SQLite file selected by AEGIS."""
    from aegis.tissue.database import find_database

    path = find_database().resolve()
    return {
        "path": str(path),
        "sha256": _file_sha256(path),
        "bytes": path.stat().st_size,
    }


def _validate_production_tissue_database(
    config: CdfConvergenceConfig,
    tissue_database: dict[str, Any],
) -> None:
    contract = config.production_contract
    if contract is None:
        return
    expected = dataclasses.asdict(contract.tissue_database)
    actual = {name: tissue_database[name] for name in expected}
    if actual != expected:
        raise ValueError(f"production IT'IS tissue database changed: {actual} != {expected}")


def _empty_checkpoint(tracer: Any, coupler: Any, reference: Any) -> CampaignCheckpoint:
    from semantic_twin.illumination import fibonacci_sphere

    cells = int(np.asarray(tracer.local_grid).shape[0])
    points = int(reference.standpoints.index.size)
    surface_elements = int(coupler.body.n_triangles)
    if surface_elements != int(reference.manifest["body"]["triangles"]):
        raise RuntimeError("body surface count differs from the frozen reference")
    local_grid = np.asarray(tracer.local_grid, dtype=np.float64)
    expected_grid = fibonacci_sphere(cells)
    if not np.array_equal(local_grid, expected_grid):
        raise RuntimeError("device tracer local grid differs from the exact deterministic Fibonacci grid")
    return CampaignCheckpoint(
        base_seeds=np.empty(0, dtype=np.int64),
        chi=np.empty((0, points, len(MODEL_NAMES)), dtype=np.float64),
        chi_direct=np.empty((0, points, len(MODEL_NAMES)), dtype=np.float64),
        body_peak_rooftop=np.empty((0, points), dtype=np.float64),
        body_mean_rooftop=np.empty((0, points), dtype=np.float64),
        body_sab_rooftop=np.empty((0, points, surface_elements), dtype=np.float64),
        trace_seconds=np.empty((0, points), dtype=np.float64),
        rho_sum=np.zeros((points, len(MODEL_NAMES), cells), dtype=np.float64),
        local_grid=local_grid,
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
    tissue_database_sha256: str,
) -> tuple[CampaignCheckpoint, dict[str, Any] | None]:
    formal_targets = set(config.looks)
    analysis = _write_reached_formal_analyses(config, checkpoint, identity)
    if analysis is not None and analysis["stopped"]:
        return checkpoint, analysis
    for base_seed in config.base_seeds[checkpoint.replicas :]:
        checkpoint = _trace_replica(config, reference, tracer, coupler, checkpoint, int(base_seed))
        _write_campaign_checkpoint(
            checkpoint_path,
            checkpoint,
            identity,
            reference,
            tissue_database_sha256,
        )
        print(f"replica {checkpoint.replicas}/{config.looks[-1]} complete at base seed {base_seed}", flush=True)
        if checkpoint.replicas not in formal_targets:
            continue
        analysis = _write_reached_formal_analyses(config, checkpoint, identity)
        if analysis is None:
            raise AssertionError("a formal target did not produce an analysis")
        if analysis["stopped"]:
            return checkpoint, analysis
    return checkpoint, analysis


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
    sab = np.empty((points, checkpoint.body_sab_rooftop.shape[2]), dtype=np.float64)
    seconds = np.empty(points, dtype=np.float64)
    rho = np.empty((points, len(MODEL_NAMES), cells), dtype=np.float64)
    models = {name: _illumination_models()[name] for name in MODEL_NAMES}
    body_model_index = MODEL_NAMES.index(config.body_model)
    for row, index in enumerate(reference.standpoints.index):
        result = tracer.trace(
            reference.standpoints.points[row],
            models,
            ground_z_m=float(reference.standpoints.ground_z_m[row]),
            seed=base_seed + config.seed_stream_stride * int(index),
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
        exposures, surface_sab = coupler.couple_many_with_sab(
            checkpoint.local_grid,
            rho[row, body_model_index : body_model_index + 1],
            checkpoint.solid_angle,
            float(reference.manifest["reference_s0_w_m2"]),
            chunk_cells=config.body_chunk_cells,
        )
        exposure = exposures[0]
        peak[row] = exposure.peak_sab_w_m2
        mean[row] = exposure.mean_sab_w_m2
        sab[row] = surface_sab[0]
        seconds[row] = float(result.seconds)
        print(
            f"  [{row + 1}/{points}] seed={base_seed} index={int(index)} "
            f"chi_{config.body_model}={chi[row, body_model_index]:.6g} ({seconds[row]:.1f} s trace)",
            flush=True,
        )
    return CampaignCheckpoint(
        base_seeds=np.append(checkpoint.base_seeds, base_seed),
        chi=np.concatenate((checkpoint.chi, chi[None, ...]), axis=0),
        chi_direct=np.concatenate((checkpoint.chi_direct, direct[None, ...]), axis=0),
        body_peak_rooftop=np.concatenate((checkpoint.body_peak_rooftop, peak[None, ...]), axis=0),
        body_mean_rooftop=np.concatenate((checkpoint.body_mean_rooftop, mean[None, ...]), axis=0),
        body_sab_rooftop=np.concatenate((checkpoint.body_sab_rooftop, sab[None, ...]), axis=0),
        trace_seconds=np.concatenate((checkpoint.trace_seconds, seconds[None, ...]), axis=0),
        rho_sum=checkpoint.rho_sum + rho,
        local_grid=checkpoint.local_grid,
        solid_angle=checkpoint.solid_angle,
    )


def _illumination_models() -> dict[str, Any]:
    from semantic_twin.exposure.study import MODELS

    return dict(MODELS)


def _analyse_checkpoint(
    config: CdfConvergenceConfig,
    checkpoint: CampaignCheckpoint,
    identity: str | None = None,
) -> dict[str, Any]:
    available_looks = tuple(look for look in config.all_looks if look <= checkpoint.replicas)
    if not set(available_looks).intersection(config.looks):
        raise RuntimeError(f"at least {config.looks[0]} complete replicas are needed for a formal analysis")
    report = analyse_joint_replicas(
        checkpoint.chi,
        checkpoint.chi_direct,
        checkpoint.body_sab_rooftop,
        checkpoint.body_mean_rooftop,
        looks=available_looks,
        planned_formal_looks=config.looks,
        body_model=config.body_model,
        bootstrap_replicates=config.bootstrap_replicates,
        bootstrap_seed=config.bootstrap_seed,
        familywise_confidence=config.confidence,
        body_peak_selection_min_fraction=config.body_peak_selection_min_fraction,
        thresholds=config.thresholds,
    )
    if identity is not None:
        report["identity_sha256"] = identity
    return report


def _write_reached_formal_analyses(
    config: CdfConvergenceConfig,
    checkpoint: CampaignCheckpoint,
    identity: str,
) -> dict[str, Any] | None:
    """Regenerate every reached formal-look file from the checkpoint prefix."""
    if checkpoint.replicas < config.looks[0]:
        return None
    report = _analyse_checkpoint(config, checkpoint, identity)
    for look in config.looks:
        if look > checkpoint.replicas:
            continue
        stopped_at = report["stop_at_replicas"]
        partial_stop = stopped_at if stopped_at is not None and stopped_at <= look else None
        partial = {
            **report,
            "looks": [document for document in report["looks"] if int(document["replicas"]) <= look],
            "stopped": partial_stop is not None,
            "stop_at_replicas": partial_stop,
            "cap_reached": look >= config.looks[-1] and partial_stop is None,
        }
        _write_json_atomic(config.output_dir / f"analysis_look{look}.json", partial)
    return report


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
        str(config.body_path),
        float(reference.manifest["run"]["frequency_hz"]),
        body_mass_kg=config.body_mass_kg,
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
    seed_mean_peak = np.mean(checkpoint.body_peak_rooftop, axis=0, dtype=np.float64)
    retained_peak_of_mean = np.max(
        np.mean(checkpoint.body_sab_rooftop, axis=0, dtype=np.float64),
        axis=1,
    )
    raw_body_mean = np.mean(checkpoint.body_mean_rooftop, axis=0, dtype=np.float64)
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
            if name == config.body_model:
                row[f"{config.body_model}_seed_mean_peak_sab_w_m2"] = float(seed_mean_peak[point])
        rows.append(row)
    physical_peak = np.asarray([row[f"{config.body_model}_peak_sab_w_m2"] for row in rows])
    plugin_mean = np.asarray([row[f"{config.body_model}_mean_sab_w_m2"] for row in rows])
    return {
        "replicas": count,
        "base_seeds": [int(value) for value in checkpoint.base_seeds],
        "rows": rows,
        "rho_sum_sha256": _array_sha256(checkpoint.rho_sum),
        "local_grid_sha256": _array_sha256(checkpoint.local_grid),
        "published_body_peak": {
            "field": f"{config.body_model}_peak_sab_w_m2",
            "estimator": "maximum absorbed density of the ensemble-mean angular spectrum",
            "confidence_family": "joint planned-look max-t family",
        },
        "body_peak_retained_field_check": {
            "retained_surface_estimator_db": [float(value) for value in _to_db(retained_peak_of_mean)],
            "recomputed_mean_spectrum_estimator_db": [float(value) for value in _to_db(physical_peak)],
            "maximum_absolute_difference_db": float(
                np.max(np.abs(_to_db(retained_peak_of_mean) - _to_db(physical_peak)))
            ),
        },
        "body_peak_jensen_diagnostic": {
            "field": f"{config.body_model}_seed_mean_peak_sab_w_m2",
            "estimator": "linear mean of per-replica peak absorbed density",
            "confidence_bounded": False,
            "seed_mean_peak_minus_physical_peak_db": [
                float(value) for value in _to_db(seed_mean_peak) - _to_db(physical_peak)
            ],
        },
        "body_mean_linearity_check": {
            "seed_mean_db": [float(value) for value in _to_db(raw_body_mean)],
            "mean_spectrum_db": [float(value) for value in _to_db(plugin_mean)],
            "maximum_absolute_difference_db": float(np.max(np.abs(_to_db(plugin_mean) - _to_db(raw_body_mean)))),
        },
    }


def _write_campaign_checkpoint(
    path: pathlib.Path,
    checkpoint: CampaignCheckpoint,
    identity: str,
    reference: Any,
    tissue_database_sha256: str,
) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as stream:
        np.savez_compressed(
            stream,
            schema=np.asarray("fixed-walk-cdf-checkpoint-v3"),
            identity_sha256=np.asarray(identity),
            standpoint_array_sha256=np.asarray(reference.standpoints.sha256),
            tissue_database_sha256=np.asarray(tissue_database_sha256),
            base_seeds=checkpoint.base_seeds,
            chi=checkpoint.chi,
            chi_direct=checkpoint.chi_direct,
            body_peak_rooftop=checkpoint.body_peak_rooftop,
            body_mean_rooftop=checkpoint.body_mean_rooftop,
            body_sab_rooftop=checkpoint.body_sab_rooftop,
            body_sab_sha256=np.asarray(_array_sha256(checkpoint.body_sab_rooftop)),
            trace_seconds=checkpoint.trace_seconds,
            rho_sum=checkpoint.rho_sum,
            local_grid=checkpoint.local_grid,
            local_grid_sha256=np.asarray(_array_sha256(checkpoint.local_grid)),
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
    tissue_database_sha256: str,
) -> CampaignCheckpoint | None:
    if not path.is_file():
        return None
    try:
        with np.load(path) as artifact:
            schema = str(artifact["schema"])
            saved_identity = str(artifact["identity_sha256"])
            standpoint_hash = str(artifact["standpoint_array_sha256"])
            saved_tissue_hash = str(artifact["tissue_database_sha256"])
            saved_grid_hash = str(artifact["local_grid_sha256"])
            saved_body_sab_hash = str(artifact["body_sab_sha256"])
            model_names = tuple(str(value) for value in artifact["model_names"])
            checkpoint = CampaignCheckpoint(
                base_seeds=np.asarray(artifact["base_seeds"], dtype=np.int64),
                chi=np.asarray(artifact["chi"], dtype=np.float64),
                chi_direct=np.asarray(artifact["chi_direct"], dtype=np.float64),
                body_peak_rooftop=np.asarray(artifact["body_peak_rooftop"], dtype=np.float64),
                body_mean_rooftop=np.asarray(artifact["body_mean_rooftop"], dtype=np.float64),
                body_sab_rooftop=np.asarray(artifact["body_sab_rooftop"], dtype=np.float64),
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
    from semantic_twin.illumination import fibonacci_sphere

    expected_grid = fibonacci_sphere(cells)
    valid = all(
        (
            schema == "fixed-walk-cdf-checkpoint-v3",
            saved_identity == identity,
            standpoint_hash == reference.standpoints.sha256,
            saved_tissue_hash == tissue_database_sha256,
            model_names == MODEL_NAMES,
            np.array_equal(checkpoint.base_seeds, np.asarray(config.base_seeds[:replicas])),
            checkpoint.chi.shape == (replicas, points, len(MODEL_NAMES)),
            checkpoint.chi_direct.shape == checkpoint.chi.shape,
            checkpoint.body_peak_rooftop.shape == (replicas, points),
            checkpoint.body_mean_rooftop.shape == (replicas, points),
            checkpoint.body_sab_rooftop.shape == (replicas, points, int(reference.manifest["body"]["triangles"])),
            saved_body_sab_hash == _array_sha256(checkpoint.body_sab_rooftop),
            checkpoint.trace_seconds.shape == (replicas, points),
            checkpoint.rho_sum.shape == (points, len(MODEL_NAMES), cells),
            checkpoint.local_grid.shape == (cells, 3),
            saved_grid_hash == _array_sha256(checkpoint.local_grid),
            np.array_equal(checkpoint.local_grid, expected_grid),
            checkpoint.solid_angle == 4.0 * np.pi / cells,
            replicas <= config.looks[-1],
            all(
                np.all(np.isfinite(array))
                for array in (
                    checkpoint.chi,
                    checkpoint.chi_direct,
                    checkpoint.body_peak_rooftop,
                    checkpoint.body_mean_rooftop,
                    checkpoint.body_sab_rooftop,
                    checkpoint.trace_seconds,
                    checkpoint.rho_sum,
                    checkpoint.local_grid,
                )
            ),
            np.all(checkpoint.chi > 0.0),
            np.all(checkpoint.chi_direct >= 0.0),
            np.all(checkpoint.body_peak_rooftop > 0.0),
            np.all(checkpoint.body_mean_rooftop > 0.0),
            np.all(checkpoint.body_sab_rooftop >= 0.0),
            np.array_equal(np.max(checkpoint.body_sab_rooftop, axis=2), checkpoint.body_peak_rooftop),
            np.array_equal(np.mean(checkpoint.body_sab_rooftop, axis=2), checkpoint.body_mean_rooftop),
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
    tissue_database: dict[str, Any],
    analysis_path: pathlib.Path,
) -> dict[str, Any]:
    for label, path in {
        "plan": config.output_dir / "plan.json",
        "analysis": analysis_path,
    }.items():
        document = json.loads(path.read_text())
        if document.get("identity_sha256") != identity:
            raise RuntimeError(f"{label} belongs to a different campaign identity")
    artifact_paths = {
        "plan": config.output_dir / "plan.json",
        "checkpoint": config.output_dir / "checkpoint.npz",
        "analysis": analysis_path,
        "ensemble_locations": config.output_dir / "ensemble_locations.jsonl",
        "figure_png": config.output_dir / "cdf_convergence.png",
        "figure_pdf": config.output_dir / "cdf_convergence.pdf",
    }
    for look in config.looks:
        if look > checkpoint.replicas:
            continue
        path = config.output_dir / f"analysis_look{look}.json"
        if not path.is_file():
            raise RuntimeError(f"formal look {look} analysis is missing")
        document = json.loads(path.read_text())
        if document.get("identity_sha256") != identity:
            raise RuntimeError(f"formal look {look} analysis belongs to a different campaign identity")
        artifact_paths[f"formal_look_{look}"] = path
    artifacts = {
        name: {
            "path": path.name,
            "sha256": _file_sha256(path),
            "bytes": path.stat().st_size,
        }
        for name, path in artifact_paths.items()
    }
    return {
        "schema": "fixed-walk-cdf-manifest-v3",
        "created_utc": _utc_now(),
        "identity_sha256": identity,
        "complete_replicas": checkpoint.replicas,
        "base_seeds": [int(value) for value in checkpoint.base_seeds],
        "reference": reference.as_dict(),
        "tissue_database": tissue_database,
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
    per_look = 100.0 * float(final["coverage"]["per_look_confidence_nominal"])
    familywise = 100.0 * float(analysis["planned_look_coverage"]["familywise_confidence_nominal"])
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
    axes[0].set_title(
        f"CDF and joint {per_look:.2f}% look band, R={final['replicas']}\n"
        f"planned-look familywise confidence {familywise:.0f}%"
    )
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
