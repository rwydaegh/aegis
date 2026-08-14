"""Paired ray and angular-cell budget diagnostics for roofline campaigns."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from ..illumination.sphere import fibonacci_sphere, nearest_cell

SCHEDULE_SCHEMA = "aegis.roofline-budget-sensitivity-schedule.v1"
CAPTURE_SCHEMA = "aegis.roofline-budget-first-diffuse-capture.v1"
REQUIRED_SITES = ("madrid_plazamayor", "mexico_zocalo", "prague_staromestske")
REQUIRED_BUDGETS = (
    (25_000, 4_096),
    (50_000, 4_096),
    (100_000, 4_096),
    (200_000, 1_024),
    (200_000, 2_048),
    (200_000, 4_096),
)
BASELINE_BUDGET = (200_000, 4_096)
REQUIRED_SEEDS = tuple(range(7, 23))
COMMON_SUPPORT_CELLS = 512
CRN_CONTRACT = "drjit_counter_keyed_seed_ray_depth_dimension_prefix_v1"
MEXICO_SHADOW_POINTS = (0, 1, 3)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def budget_key(rays: int, cells: int) -> str:
    """Return the stable directory key for one numerical budget."""
    return f"rays_{rays:06d}_cells_{cells:04d}"


@dataclass(frozen=True)
class BudgetArm:
    """One paired ray and passive-output-cell budget."""

    rays: int
    cells: int

    def __post_init__(self) -> None:
        if self.rays < 1 or self.cells < 1:
            raise ValueError("budget rays and cells must be positive")

    @property
    def key(self) -> str:
        return budget_key(self.rays, self.cells)


@dataclass(frozen=True)
class RooflineBudgetSchedule:
    """Strict three-route common-random-number budget schedule."""

    path: Path
    study_root: Path
    output_dir: Path
    sites: Mapping[str, Path]
    sealed_baselines: Mapping[str, Path]
    arms: tuple[BudgetArm, ...]
    seeds: tuple[int, ...]
    baseline: BudgetArm
    common_support_cells: int
    mexico_shadow_points: tuple[int, ...]
    bootstrap_replicates: int
    bootstrap_seed: int
    confidence: float
    capture_first_diffuse: bool
    common_random_numbers: str

    @property
    def generated_config_dir(self) -> Path:
        return self.output_dir / "generated_configs"

    def campaign_dir(self, site: str, arm: BudgetArm) -> Path:
        return self.output_dir / "campaigns" / site / arm.key

    def generated_config(self, site: str, arm: BudgetArm) -> Path:
        return self.generated_config_dir / site / f"roofline_campaign_{site}_budget_{arm.key}_iid.json"

    def identity(self) -> dict[str, Any]:
        return {
            "schema": SCHEDULE_SCHEMA,
            "sites": {
                site: (
                    path.relative_to(self.study_root).as_posix() if path.is_relative_to(self.study_root) else str(path)
                )
                for site, path in sorted(self.sites.items())
            },
            "sealed_baselines": {
                site: (
                    path.relative_to(self.study_root).as_posix() if path.is_relative_to(self.study_root) else str(path)
                )
                for site, path in sorted(self.sealed_baselines.items())
            },
            "budgets": [{"rays": arm.rays, "cells": arm.cells} for arm in self.arms],
            "baseline": {"rays": self.baseline.rays, "cells": self.baseline.cells},
            "seeds": list(self.seeds),
            "common_support_cells": self.common_support_cells,
            "mexico_shadow_points": list(self.mexico_shadow_points),
            "bootstrap": {
                "replicates": self.bootstrap_replicates,
                "seed": self.bootstrap_seed,
                "confidence": self.confidence,
            },
            "capture_first_diffuse": self.capture_first_diffuse,
            "common_random_numbers": self.common_random_numbers,
        }

    @property
    def sha256(self) -> str:
        return hashlib.sha256(_canonical(self.identity())).hexdigest()


def load_budget_schedule(path: str | Path, *, study_root: str | Path | None = None) -> RooflineBudgetSchedule:
    """Load and fail closed on any departure from the registered Priority 3 design."""
    schedule_path = Path(path).resolve()
    document = json.loads(schedule_path.read_text(encoding="utf-8"))
    if document.get("schema") != SCHEDULE_SCHEMA:
        raise ValueError(f"budget schedule schema must be {SCHEDULE_SCHEMA!r}")
    if study_root is not None:
        root = Path(study_root).resolve()
    elif document.get("study_root") is not None:
        declared_root = Path(document["study_root"])
        root = (declared_root if declared_root.is_absolute() else schedule_path.parents[1] / declared_root).resolve()
    else:
        root = schedule_path.parents[1].resolve()
    output = Path(document["output_dir"])
    output = output if output.is_absolute() else root / output
    raw_sites = document.get("sites")
    if not isinstance(raw_sites, dict) or tuple(sorted(raw_sites)) != tuple(sorted(REQUIRED_SITES)):
        raise ValueError(f"budget schedule sites must be exactly {REQUIRED_SITES}")
    sites = {
        site: (Path(value) if Path(value).is_absolute() else root / value).resolve()
        for site, value in raw_sites.items()
    }
    raw_baselines = document.get("sealed_baselines")
    if not isinstance(raw_baselines, dict) or tuple(sorted(raw_baselines)) != tuple(sorted(REQUIRED_SITES)):
        raise ValueError(f"sealed_baselines sites must be exactly {REQUIRED_SITES}")
    sealed_baselines = {
        site: (Path(value) if Path(value).is_absolute() else root / value).resolve()
        for site, value in raw_baselines.items()
    }
    arms = tuple(BudgetArm(int(item["rays"]), int(item["cells"])) for item in document.get("budgets", ()))
    if tuple((arm.rays, arm.cells) for arm in arms) != REQUIRED_BUDGETS:
        raise ValueError(f"budget schedule arms must be exactly {REQUIRED_BUDGETS}")
    baseline_data = document.get("baseline", {})
    baseline = BudgetArm(int(baseline_data.get("rays", -1)), int(baseline_data.get("cells", -1)))
    if (baseline.rays, baseline.cells) != BASELINE_BUDGET:
        raise ValueError(f"baseline must be the current production contract {BASELINE_BUDGET}")
    seeds = tuple(document.get("seeds", ()))
    if seeds != REQUIRED_SEEDS:
        raise ValueError(f"paired seeds must be the exact prefix {REQUIRED_SEEDS}")
    support = int(document.get("common_support_cells", -1))
    if support != COMMON_SUPPORT_CELLS:
        raise ValueError(f"common directional support must contain {COMMON_SUPPORT_CELLS} cells")
    shadows = tuple(document.get("mexico_shadow_points", ()))
    if shadows != MEXICO_SHADOW_POINTS:
        raise ValueError(f"Mexico shadow points must be {MEXICO_SHADOW_POINTS}")
    bootstrap = document.get("bootstrap", {})
    replicates = int(bootstrap.get("replicates", 0))
    confidence = float(bootstrap.get("confidence", 0.0))
    if replicates < 100:
        raise ValueError("bootstrap replicates must be at least 100")
    if not 0.0 < confidence < 1.0:
        raise ValueError("bootstrap confidence must lie between zero and one")
    if document.get("capture_first_diffuse") is not True:
        raise ValueError("Priority 3 requires explicit first-diffuse field capture")
    if document.get("common_random_numbers") != CRN_CONTRACT:
        raise ValueError(f"common_random_numbers must be the device prefix contract {CRN_CONTRACT!r}")
    missing = [str(base) for base in sites.values() if not base.is_file()]
    if missing:
        raise FileNotFoundError("base campaign configurations are missing: " + ", ".join(missing))
    for site, config in sites.items():
        source_document = json.loads(config.read_text(encoding="utf-8"))
        declared_output = Path(source_document["campaign"]["output_dir"])
        declared_output = (declared_output if declared_output.is_absolute() else root / declared_output).resolve()
        if declared_output != sealed_baselines[site]:
            raise ValueError(f"sealed baseline for {site} does not match the source config output_dir")
    return RooflineBudgetSchedule(
        path=schedule_path,
        study_root=root,
        output_dir=output.resolve(),
        sites=sites,
        sealed_baselines=sealed_baselines,
        arms=arms,
        seeds=tuple(int(seed) for seed in seeds),
        baseline=baseline,
        common_support_cells=support,
        mexico_shadow_points=tuple(int(point) for point in shadows),
        bootstrap_replicates=replicates,
        bootstrap_seed=int(bootstrap.get("seed", 20260814)),
        confidence=confidence,
        capture_first_diffuse=True,
        common_random_numbers=CRN_CONTRACT,
    )


def _generated_document(schedule: RooflineBudgetSchedule, site: str, arm: BudgetArm) -> dict[str, Any]:
    document = json.loads(schedule.sites[site].read_text(encoding="utf-8"))
    run = document["run"]
    campaign = document["campaign"]
    run["rays"] = arm.rays
    run["local_cells"] = arm.cells
    run["launch_sampling"] = "iid"
    run["tag"] = f"roofline_budget_sensitivity_{site}_{arm.key}"
    campaign["output_dir"] = str(schedule.campaign_dir(site, arm).relative_to(schedule.study_root))
    campaign["planned_seeds"] = list(schedule.seeds)
    campaign["convergence_looks"] = [4, 8, 12, 16]
    campaign["body_chunk_cells"] = 512
    if run.get("batch", 0) < arm.rays:
        raise ValueError(f"base config batch cannot preserve a single IID prefix at {arm.rays} rays")
    if run.get("transport_kernel") != "drjit" or run.get("variant") != "cuda_ad_rgb":
        raise ValueError(f"base config for {site} does not use the counter-keyed CUDA transport")
    if run.get("max_bounces") != 1 or campaign.get("transport_topology") != "first_material_interaction_v1":
        raise ValueError(f"base config for {site} is not the current first-interaction contract")
    if campaign.get("specular_acceptance") != "first_material_interaction_exact_order_1":
        raise ValueError(f"base config for {site} does not require exact order-1 support")
    document["budget_sensitivity"] = {
        "schedule_sha256": schedule.sha256,
        "common_random_numbers": schedule.common_random_numbers,
        "ray_prefix_rule": "same point seed and ray indices 0..N-1 at every nested ray budget",
        "capture_first_diffuse": True,
        "common_support_cells": schedule.common_support_cells,
    }
    return document


def materialize_budget_configs(schedule: RooflineBudgetSchedule) -> tuple[Path, ...]:
    """Write explicit, reviewable campaign configs without touching base configs."""
    written: list[Path] = []
    for site in REQUIRED_SITES:
        for arm in schedule.arms:
            path = schedule.generated_config(site, arm)
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(_generated_document(schedule, site, arm), indent=2, sort_keys=True) + "\n"
            if path.exists() and path.read_text(encoding="utf-8") != payload:
                raise ValueError(f"generated budget config already exists with different bytes: {path}")
            temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
            temporary.write_text(payload, encoding="utf-8")
            os.replace(temporary, path)
            written.append(path)
    manifest_path = schedule.generated_config_dir / "manifest.json"
    manifest = {
        "schema": "aegis.roofline-budget-generated-configs.v1",
        "schedule_sha256": schedule.sha256,
        "source_schedule": str(schedule.path),
        "files": {
            str(path.relative_to(schedule.generated_config_dir)): {
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
            }
            for path in written
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return tuple(written)


class FirstDiffuseCapture:
    """Opt-in callback that projects first-diffuse fields onto a common support."""

    def __init__(self, root: str | Path, *, points: int, common_cells: int = COMMON_SUPPORT_CELLS) -> None:
        if points < 1 or common_cells < 1:
            raise ValueError("capture points and common cells must be positive")
        self.root = Path(root)
        if self.root.exists() and any(self.root.iterdir()):
            raise ValueError(f"first-diffuse capture directory must be new and empty: {self.root}")
        self.points = int(points)
        self.common_cells = int(common_cells)
        self.grid = fibonacci_sphere(self.common_cells)
        self._active_seed: int | None = None
        self._masses = np.zeros((self.points, self.common_cells), dtype=np.float64)
        self._raw = np.zeros(self.points, dtype=np.float64)
        self._reference = np.zeros(self.points, dtype=np.float64)
        self._point_seed = np.zeros(self.points, dtype=np.uint64)
        self._seen = np.zeros(self.points, dtype=bool)
        self._entries: list[dict[str, Any]] = []

    def __call__(self, **record: Any) -> None:
        seed = int(record["seed"])
        point = int(record["point_index"])
        if self._active_seed is None:
            self._active_seed = seed
        elif seed != self._active_seed:
            self._commit_active()
            self._active_seed = seed
        if not 0 <= point < self.points or self._seen[point]:
            raise ValueError("first-diffuse capture point is outside or duplicated")
        measures = record["measures"]
        measure = measures["first_diffuse"]
        field = record["field"]
        scale = record["scale"]
        cells = nearest_cell(np.asarray(measure.diffuse_k_hat, dtype=np.float64), self.grid)
        np.add.at(self._masses[point], cells, np.asarray(measure.diffuse_mass, dtype=np.float64))
        self._raw[point] = float(np.sum(field.bounced_mass, dtype=np.float64))
        self._reference[point] = float(scale.transfer_m_inv2)
        self._point_seed[point] = np.uint64(record["point_seed"])
        self._seen[point] = True
        reconstructed = float(np.sum(self._masses[point], dtype=np.float64) * self._reference[point])
        if not np.isclose(reconstructed, self._raw[point], rtol=2.0e-12, atol=1.0e-15):
            raise RuntimeError("common-support first-diffuse capture does not conserve transfer")
        if point == self.points - 1:
            self._commit_active()

    def _commit_active(self) -> None:
        if self._active_seed is None:
            return
        if not np.all(self._seen):
            raise RuntimeError("first-diffuse capture cannot commit an incomplete route replica")
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"seed_{self._active_seed:010d}.npz"
        temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
        with temporary.open("wb") as handle:
            np.savez_compressed(
                handle,
                common_grid=self.grid,
                first_diffuse_mass=self._masses,
                raw_first_diffuse_m_inv2=self._raw,
                reference_transfer_m_inv2=self._reference,
                point_seed=self._point_seed,
            )
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        self._entries.append(
            {"seed": self._active_seed, "path": path.name, "sha256": _sha256(path), "bytes": path.stat().st_size}
        )
        self._masses.fill(0.0)
        self._raw.fill(0.0)
        self._reference.fill(0.0)
        self._point_seed.fill(0)
        self._seen.fill(False)
        self._active_seed = None

    def finalize(self, *, campaign_identity_sha256: str, schedule_sha256: str) -> Path:
        """Seal all captures and their campaign/schedule bindings."""
        self._commit_active()
        manifest = {
            "schema": CAPTURE_SCHEMA,
            "campaign_identity_sha256": campaign_identity_sha256,
            "schedule_sha256": schedule_sha256,
            "common_support_cells": self.common_cells,
            "points": self.points,
            "entries": self._entries,
        }
        path = self.root / "manifest.json"
        path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path


__all__ = [
    "BASELINE_BUDGET",
    "CAPTURE_SCHEMA",
    "COMMON_SUPPORT_CELLS",
    "CRN_CONTRACT",
    "FirstDiffuseCapture",
    "MEXICO_SHADOW_POINTS",
    "REQUIRED_BUDGETS",
    "REQUIRED_SEEDS",
    "REQUIRED_SITES",
    "BudgetArm",
    "RooflineBudgetSchedule",
    "budget_key",
    "load_budget_schedule",
    "materialize_budget_configs",
]
