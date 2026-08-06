"""Exposure study over alternative facade material models."""

from __future__ import annotations

import json
import pathlib
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from semantic_twin import paths
from semantic_twin.exposure import BodyCoupler, describe
from semantic_twin.illumination import ISOTROPIC, ROOFTOP, STREET_SMALL_CELL
from semantic_twin.materials import CLASS_NAMES, bind_posterior, classify_faces, load_table, realised_composition
from semantic_twin.propagation import MitsubaGeometry
from semantic_twin.transport import SbrTracer, TraceConfig
from semantic_twin.walk.grid import build_walk
from semantic_twin.walk.model import stratified_subset

GROUND_DATUM_M = 50.83747424667166
PHANTOM = paths.aegis_data_dir() / "duke.stl"
PHANTOM_MASS_KG = 72.4
MODELS = {"isotropic": ISOTROPIC, "rooftop": ROOFTOP, "street_small_cell": STREET_SMALL_CELL}


@dataclass(frozen=True)
class MaterialAblationConfig:
    out: pathlib.Path | None = None
    locations: int = 120
    rays: int = 400_000
    frequency_ghz: float = 15.0
    seed: int = 0
    material_seeds: tuple[int, ...] = (0,)
    only: tuple[str, ...] | None = None
    root: pathlib.Path = field(default_factory=paths.root)
    phantom: pathlib.Path = PHANTOM

    @property
    def output_dir(self) -> pathlib.Path:
        return self.out or self.root / "outputs" / "material_vlm"


@dataclass(frozen=True)
class _StudyContext:
    config: MaterialAblationConfig
    frequency: float
    mesh: pathlib.Path
    geometry: Any
    areas: np.ndarray
    geometric_class: np.ndarray
    walk: Any
    picks: np.ndarray
    coupler: BodyCoupler
    trace_config: TraceConfig


def pure(material: str) -> dict[str, float]:
    return {material: 1.0}


def variants(analysis: dict[str, Any]) -> dict[str, dict[str, float] | None]:
    composition = analysis["composition"]
    return {
        "brick": None,
        "pure_brick": pure("brick"),
        "prior_draw": composition["fixed_building_prior"],
        "vlm_panorama": composition["vlm_panorama"],
        "vlm_texture": composition["vlm_texture"],
        "pure_plasterboard": pure("plasterboard"),
        "pure_concrete": pure("concrete"),
        "pure_marble": pure("marble"),
        "pure_glass": pure("glass"),
        "pure_wood": pure("wood"),
        "pure_metal": pure("metal"),
    }


def _context(config: MaterialAblationConfig) -> _StudyContext:
    frequency = config.frequency_ghz * 1e9
    mesh = config.root / "data" / "geometry" / "korenmarkt" / "inhouse_leaf_130m_f64.ply"
    geometry = MitsubaGeometry(mesh)
    areas = geometry.face_areas()
    geometric_class = classify_faces(geometry.vertices, geometry.faces, GROUND_DATUM_M)
    walk = build_walk(geometry, ground_datum_m=GROUND_DATUM_M, radius_m=90.0, spacing_m=3.0, seed=config.seed)
    picks = stratified_subset(walk, config.locations)
    coupler = BodyCoupler(config.phantom, frequency, body_mass_kg=PHANTOM_MASS_KG)
    trace_config = TraceConfig(frequency_hz=frequency, rays=config.rays, seed=config.seed)
    print(f"{len(walk)} walk candidates, tracing {picks.size} per variant")
    return _StudyContext(
        config,
        frequency,
        mesh,
        geometry,
        areas,
        geometric_class,
        walk,
        picks,
        coupler,
        trace_config,
    )


def _material_binding(
    context: _StudyContext,
    posterior: dict[str, float] | None,
    material_seed: int,
) -> tuple[Any, np.ndarray, dict[str, float], float]:
    if posterior is None:
        binding = load_table(context.config.root / "config", context.frequency)
        realised = {"brick": float(context.areas[context.geometric_class == 1].sum() / context.areas.sum())}
        return binding, context.geometric_class, realised, 0.0
    drawing = bind_posterior(
        context.areas,
        context.geometric_class,
        {"facade": posterior},
        seed=1000 + material_seed,
    )
    binding = load_table(
        context.config.root / "config",
        context.frequency,
        class_names=drawing.class_names,
        class_binding=drawing.class_binding,
        class_rule="facade materials drawn per face from a posterior, other classes geometric",
    )
    return binding, drawing.face_class, realised_composition(drawing), drawing.covered_fraction_by_area


def _trace_variant(
    context: _StudyContext,
    tag: str,
    posterior: dict[str, float] | None,
    material_seed: int,
    handle: Any,
) -> tuple[dict[str, Any], list[dict[str, float]]]:
    started = time.perf_counter()
    binding, face_class, realised, drawn = _material_binding(context, posterior, material_seed)
    tracer = SbrTracer(
        context.geometry,
        face_class,
        binding.permittivity,
        binding.rms_height_m,
        context.trace_config,
    )
    scalars: list[dict[str, float]] = []
    for index in context.picks:
        point = context.walk.points[index]
        result = tracer.trace(
            point,
            MODELS,
            ground_z_m=float(context.walk.ground_z_m[index]),
            seed=context.config.seed + 1000 * index,
        )
        row = {"variant": tag, "index": int(index)}
        row.update(result.scalars())
        for model in MODELS:
            exposure = context.coupler.couple(
                result.local_grid,
                result.rho[model],
                result.local_solid_angle,
                1.0,
            )
            row[f"{model}_sar_wb_w_kg"] = float(exposure.sar_wb_w_kg)
            row[f"{model}_peak_sab_w_m2"] = float(exposure.peak_sab_w_m2)
        scalars.append(row)
        handle.write(json.dumps(row) + "\n")
    handle.flush()
    summary = _summarise_variant(tag, posterior, realised, drawn, scalars, started)
    print(
        f"{tag:24s} chi_iso {summary['chi_isotropic']['median']:.5f}  "
        f"chi_roof {summary['chi_rooftop']['median']:.5f}  "
        f"bounces {summary['mean_bounces']['median']:.2f}  {summary['seconds']:.0f} s",
        flush=True,
    )
    return summary, scalars


def _summarise_variant(
    tag: str,
    posterior: dict[str, float] | None,
    realised: dict[str, float],
    drawn: float,
    scalars: list[dict[str, float]],
    started: float,
) -> dict[str, Any]:
    summary = {
        "variant": tag,
        "posterior": posterior,
        "realised_area_composition": realised,
        "facade_area_fraction_drawn": drawn,
        "locations": len(scalars),
        "seconds": round(time.perf_counter() - started, 1),
    }
    for key in (
        "chi_isotropic",
        "chi_rooftop",
        "chi_street_small_cell",
        "mean_bounces",
        "escaped_fraction",
        "isotropic_sar_wb_w_kg",
        "rooftop_sar_wb_w_kg",
    ):
        values = np.array([row[key] for row in scalars])
        summary[key] = {
            "median": float(np.median(values)),
            "p10": float(np.quantile(values, 0.1)),
            "p90": float(np.quantile(values, 0.9)),
        }
    return summary


def _add_paired_shifts(
    results: dict[str, Any],
    per_location: dict[str, list[dict[str, float]]],
) -> None:
    reference = results.get("brick")
    if reference is None:
        return
    for tag, summary in results.items():
        summary["shift_db"] = {
            key: float(10 * np.log10(summary[key]["median"] / reference[key]["median"]))
            for key in ("chi_isotropic", "chi_rooftop", "chi_street_small_cell")
        }
        paired: dict[str, Any] = {}
        for key in ("chi_isotropic", "chi_rooftop", "chi_street_small_cell"):
            ratio = np.array([row[key] for row in per_location[tag]]) / np.array(
                [row[key] for row in per_location["brick"]]
            )
            decibels = 10 * np.log10(ratio)
            paired[key] = {
                "median_db": float(np.median(decibels)),
                "p10_db": float(np.quantile(decibels, 0.1)),
                "p90_db": float(np.quantile(decibels, 0.9)),
                "locations_over_1db": int(np.count_nonzero(np.abs(decibels) > 1.0)),
            }
        summary["paired_shift_db"] = paired


def run_material_ablation(config: MaterialAblationConfig) -> pathlib.Path:
    analysis = json.loads((config.output_dir / "analysis.json").read_text())
    plan = variants(analysis)
    if config.only:
        plan = {name: plan[name] for name in config.only}
    context = _context(config)
    results: dict[str, Any] = {}
    per_location: dict[str, list[dict[str, float]]] = {}
    rows_path = config.output_dir / "ablation_locations.jsonl"
    with rows_path.open("a") as handle:
        for name, posterior in plan.items():
            seeds = [0] if posterior is None else config.material_seeds
            for material_seed in seeds:
                tag = name if posterior is None else f"{name}_m{material_seed}"
                summary, scalars = _trace_variant(context, tag, posterior, material_seed, handle)
                results[tag] = summary
                per_location[tag] = scalars
    _add_paired_shifts(results, per_location)
    document = {
        "generator": "run_material_ablation.py",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mesh": str(context.mesh),
        "frequency_hz": context.frequency,
        "trace_config": context.trace_config.as_dict(),
        "locations": int(context.picks.size),
        "body": describe(context.coupler),
        "geometric_class_area_fractions": {
            name: float(context.areas[context.geometric_class == index].sum() / context.areas.sum())
            for index, name in enumerate(CLASS_NAMES)
        },
        "variants": results,
    }
    path = config.output_dir / "ablation.json"
    if path.exists():
        previous = json.loads(path.read_text())
        previous["variants"].update(results)
        previous["variants"] = {k: v for k, v in previous["variants"].items()}
        document["variants"] = previous["variants"]
    path.write_text(json.dumps(document, indent=2))
    print(f"\n-> {path}")
    return path
