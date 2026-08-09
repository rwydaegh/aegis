"""Run the paired traced and analytic bystander exposure study."""

from __future__ import annotations

import gc
import json
import pathlib
import time
from dataclasses import dataclass
from typing import Any

import numpy as np

from .. import paths
from ..propagation.bystander_geometry import (
    ABSORBER_PERMITTIVITY,
    CLOTHING_RMS_HEIGHT_M,
    DENSITY_LADDER,
    EXCLUSION_RADIUS_M,
    MIN_SEPARATION_M,
    BodyLibrary,
    CrowdConfig,
    CrowdGeometryConfig,
    TransmittanceConfig,
    blocked_susceptibility,
    crowd_geometry,
    crowd_transmittance,
    load_body_library,
    near_horizon_share,
    sample_crowd,
    skin_permittivity,
)
from ..propagation.geometry import MitsubaGeometry
from ..transport.tracer import DEFAULT_MAX_BOUNCES

#: Standing stature of the adult population the bystanders stand in for, both
#: sexes pooled. This is a declared modelling parameter and not a measurement of
#: anyone on Korenmarkt, and nothing downstream needs it to be exact: the
#: blocking depth of the law below is linear in ``h_body - h_observer``, so a
#: reader who prefers a different population can rescale every number in the
#: cheap arm by hand. The traced arm is run at this value and at the
#: reconstructions' own statures, which brackets it.
ADULT_STATURE_MEAN_M = 1.73
ADULT_STATURE_SD_M = 0.09

STATURE_MODES = ("as_reconstructed", "adult")

#: The three estimates every row carries. ``full`` re-traced the scene with the
#: bodies in it, ``walkable`` and ``nominal`` are the Beer-Lambert post-multiply
#: read at the crowd's true areal intensity and at the square's nominal
#: pedestrian density.
ARMS = ("full", "walkable", "nominal")


def stature_library(library: BodyLibrary, mode: str, seed: int = 0) -> BodyLibrary:
    """The body library at reconstructed statures or at adult statures.

    The reconstructions run 1.39 to 1.71 m with a median of 1.55 m, which is
    short for adults and is a property of the monocular reconstruction rather
    than of Korenmarkt. The observation point stands at 1.5 m, so the difference
    between a 1.55 m bystander and a 1.73 m one is the difference between 0.05 m
    and 0.23 m of blocking height, a factor of four in how deep a crowd of the
    same density is. Both are therefore run.
    """
    if mode == "as_reconstructed":
        return library
    if mode != "adult":
        raise ValueError(f"unknown stature mode {mode!r}")
    rng = np.random.default_rng(seed)
    targets = np.clip(rng.normal(ADULT_STATURE_MEAN_M, ADULT_STATURE_SD_M, len(library)), 1.45, 2.05)
    return library.rescaled(targets)


def _finished_locations(rows_path: pathlib.Path, expected_crowd_rows: int) -> set[int]:
    """Standpoints already fully traced, and drop the partial ones in place.

    A shared machine kills a long run eventually, so the runner has to be
    restartable without silently mixing a half traced standpoint into the
    medians. Complete standpoints are kept, incomplete ones are deleted from the
    file, and the run picks up from there.
    """
    rows_path = pathlib.Path(rows_path)
    if not rows_path.exists():
        return set()
    rows = [json.loads(line) for line in rows_path.read_text().splitlines() if line.strip()]
    counted: dict[int, int] = {}
    seen_baseline: set[int] = set()
    for row in rows:
        if row["kind"] == "baseline":
            seen_baseline.add(int(row["location"]))
        else:
            counted[int(row["location"])] = counted.get(int(row["location"]), 0) + 1
    done = {loc for loc in seen_baseline if counted.get(loc, 0) >= expected_crowd_rows}
    kept = [row for row in rows if int(row["location"]) in done]
    if len(kept) != len(rows):
        rows_path.write_text("".join(json.dumps(row) + "\n" for row in kept))
    return done


def site_mesh(root: pathlib.Path, site: str, crop_m: int) -> pathlib.Path:
    """Resolve a traceable support mesh through the canonical study resolver.

    This compatibility entry point retains the historical ``root`` argument
    used by the bystander runner and :mod:`semantic_twin.propagation.bystanders`.
    Mesh selection and format provenance are owned by :func:`semantic_twin.paths.site_mesh`.
    """
    return paths.site_mesh(site, crop_m, root_dir=pathlib.Path(root))


def ground_datum(root: pathlib.Path, site: str, geometry: Any, *, radius_m: float = 15.0, samples: int = 4096) -> float:
    """Walkable height of the square, from the site config or from the mesh."""
    config = pathlib.Path(root) / "config" / f"{site}.json"
    if config.exists():
        recorded = json.loads(config.read_text()).get("camera_ground_z_m")
        if recorded is not None:
            return float(recorded)
    rng = np.random.default_rng(0)
    angle = rng.uniform(0.0, 2.0 * np.pi, samples)
    distance = radius_m * np.sqrt(rng.random(samples))
    probe = 1.0e4
    hit, travel, _, _ = geometry.intersect(
        np.column_stack([distance * np.cos(angle), distance * np.sin(angle), np.full(samples, probe)]),
        np.tile(np.array([0.0, 0.0, -1.0]), (samples, 1)),
    )
    heights = probe - travel[hit]
    if heights.size == 0:
        raise RuntimeError("no surface under the centre of the crop")
    return float(np.median(heights))


def _shift_db(value: float, reference: float) -> float:
    if value <= 0.0 or reference <= 0.0:
        return float("nan")
    return float(10.0 * np.log10(value / reference))


@dataclass(frozen=True)
class StudyRunConfig:
    """Inputs for one full bystander study run."""

    output_dir: pathlib.Path
    bodies_dir: pathlib.Path
    site: str = "korenmarkt"
    crop_m: int = 250
    frequency_hz: float = 15.0e9
    locations: int = 12
    densities: tuple[float, ...] = DENSITY_LADDER
    realisations: int = 3
    rays: int = 200_000
    local_cells: int = 512
    max_bounces: int = DEFAULT_MAX_BOUNCES
    seed: int = 7
    stature_modes: tuple[str, ...] = STATURE_MODES
    target_faces: int = 600
    max_radius_m: float = 30.0
    mean_free_paths: float = float("inf")
    clothing_rms_height_m: float = CLOTHING_RMS_HEIGHT_M
    body_absorber: bool = False
    variant: str = "llvm_ad_rgb"
    tag: str = "korenmarkt"
    scratch: pathlib.Path | None = None
    resume: bool = False


@dataclass(frozen=True)
class _StudyContext:
    options: StudyRunConfig
    models: dict[str, Any]
    geometry: Any
    datum: float
    site_face_class: np.ndarray
    permittivity: np.ndarray
    rms_height: np.ndarray
    trace_config: Any
    baseline_tracer: Any
    libraries: dict[str, BodyLibrary]
    walk: Any
    picks: np.ndarray
    head_height_m: float
    body_class_index: int
    scratch: pathlib.Path


@dataclass(frozen=True)
class _LocationTrace:
    order: int
    index: int
    point: np.ndarray
    ground_z: float
    baseline: Any


@dataclass
class _StudyWriter:
    context: _StudyContext
    handle: Any

    def write_location(self, order: int, index: int) -> None:
        point = self.context.walk.points[index]
        ground_z = float(self.context.walk.ground_z_m[index])
        seed = self.context.options.seed + 1000 * index
        baseline = self.context.baseline_tracer.trace(
            point,
            self.context.models,
            ground_z_m=ground_z,
            seed=seed,
        )
        self._write_baseline(index, point, baseline)
        location = _LocationTrace(order, index, point, ground_z, baseline)
        for mode, library in self.context.libraries.items():
            for density in self.context.options.densities:
                self._write_density(location, mode, library, density)

    def _write_baseline(self, index: int, point: np.ndarray, baseline: Any) -> None:
        row = {
            "kind": "baseline",
            "location": index,
            "x": float(point[0]),
            "y": float(point[1]),
            "z": float(point[2]),
            "sky_fraction": baseline.sky_fraction,
            "mean_bounces": baseline.mean_bounces,
            "seconds": baseline.seconds,
        }
        for name in self.context.models:
            row[f"chi_{name}"] = baseline.susceptibility[name]
            row[f"arriving_below_5deg_{name}"] = near_horizon_share(
                baseline.local_grid,
                baseline.rho[name],
                baseline.local_solid_angle,
                5.0,
            )
            row[f"arriving_below_2deg_{name}"] = near_horizon_share(
                baseline.local_grid,
                baseline.rho[name],
                baseline.local_solid_angle,
                2.0,
            )
        self.handle.write(json.dumps(row) + "\n")
        self.handle.flush()

    def _write_density(
        self,
        location: _LocationTrace,
        mode: str,
        library: BodyLibrary,
        density: float,
    ) -> None:
        placed = 0
        built_radius = 0.0
        row: dict[str, Any] = {}
        for realisation in range(self.context.options.realisations):
            row, placed, built_radius = self._write_realisation(
                location,
                mode,
                library,
                density,
                realisation,
            )
        print(
            f"[{location.order + 1}/{self.context.picks.size}] {mode} lambda={density:g} "
            f"bodies={placed} R={built_radius:.0f} m "
            + " ".join(
                f"{name}={row[f'shift_full_db_{name}']:+.2f}/{row[f'shift_nominal_db_{name}']:+.2f} dB"
                for name in self.context.models
            ),
            flush=True,
        )

    def _write_realisation(
        self,
        location: _LocationTrace,
        mode: str,
        library: BodyLibrary,
        density: float,
        realisation: int,
    ) -> tuple[dict[str, Any], int, float]:
        from ..transport.tracer import SbrTracer

        options = self.context.options
        crowd = sample_crowd(
            self.context.geometry,
            location.point[:2],
            self.context.datum,
            library,
            CrowdConfig(
                density_per_m2=float(density),
                max_radius_m=options.max_radius_m,
                mean_free_paths=options.mean_free_paths,
                seed=options.seed + 97 * realisation + 7919 * location.index,
            ),
        )
        composite, face_class = crowd_geometry(
            CrowdGeometryConfig(
                site=self.context.geometry,
                crowd=crowd,
                library=library,
                site_face_class=self.context.site_face_class,
                body_class_index=self.context.body_class_index,
                variant=options.variant,
                scratch=self.context.scratch,
            )
        )
        traced = SbrTracer(
            composite,
            face_class,
            self.context.permittivity,
            self.context.rms_height,
            self.context.trace_config,
        ).trace(
            location.point,
            self.context.models,
            ground_z_m=location.ground_z,
            seed=options.seed + 1000 * location.index,
        )
        transmittance = self._transmittance(location.baseline, crowd, library, density)
        row = self._crowd_row(location, mode, density, realisation, crowd, traced, transmittance)
        self.handle.write(json.dumps(row) + "\n")
        self.handle.flush()
        placed, built_radius = len(crowd), crowd.radius_m
        del composite, face_class, traced, crowd, transmittance
        gc.collect()
        return row, placed, built_radius

    def _transmittance(
        self,
        baseline: Any,
        crowd: Any,
        library: BodyLibrary,
        density: float,
    ) -> dict[str, np.ndarray]:
        shared = {
            "width_m": library.width_m,
            "body_height_m": library.stature_m,
            "observer_height_m": self.context.head_height_m,
            "radius_m": crowd.radius_m,
            "cells": self.context.options.local_cells,
        }
        return {
            "walkable": crowd_transmittance(
                baseline.local_grid,
                TransmittanceConfig(density_per_m2=crowd.effective_density_per_m2, **shared),
            ),
            "nominal": crowd_transmittance(
                baseline.local_grid,
                TransmittanceConfig(density_per_m2=float(density), **shared),
            ),
        }

    def _crowd_row(
        self,
        location: _LocationTrace,
        mode: str,
        density: float,
        realisation: int,
        crowd: Any,
        traced: Any,
        transmittance: dict[str, np.ndarray],
    ) -> dict[str, Any]:
        row = {
            "kind": "crowd",
            "location": location.index,
            "stature_mode": mode,
            "density_per_m2": float(density),
            "realisation": realisation,
            "bodies": len(crowd),
            "crowd_radius_m": crowd.radius_m,
            "walkable_fraction": crowd.provenance["walkable_fraction"],
            "effective_density_per_m2": crowd.effective_density_per_m2,
            "achieved_density_per_m2": crowd.achieved_density_per_m2,
            "sky_fraction": traced.sky_fraction,
            "mean_bounces": traced.mean_bounces,
            "seconds": traced.seconds,
        }
        for name in self.context.models:
            row[f"chi_full_{name}"] = traced.susceptibility[name]
            row[f"shift_full_db_{name}"] = _shift_db(
                traced.susceptibility[name],
                location.baseline.susceptibility[name],
            )
            for arm, factor in transmittance.items():
                cheap = blocked_susceptibility(
                    location.baseline.rho[name],
                    factor,
                    location.baseline.local_solid_angle,
                )
                row[f"chi_{arm}_{name}"] = cheap
                row[f"shift_{arm}_db_{name}"] = _shift_db(
                    cheap,
                    location.baseline.susceptibility[name],
                )
        return row


def run_study(options: StudyRunConfig) -> pathlib.Path:
    """Trace the same standpoints with and without a crowd, at every density.

    Streaming, like every other runner here: one row per standpoint, density,
    realisation and stature mode is appended to a JSONL and nothing that scales
    with the ray count reaches disk. The baseline trace of a standpoint is done
    once and reused by every density, which is what makes the paired ratio a
    paired ratio.
    """
    from ..illumination import MODELS as models
    from ..materials import classify_faces, load_table
    from ..transport.tracer import SbrTracer, TraceConfig
    from ..walk.grid import build_walk
    from ..walk.model import stratified_subset

    output_dir = options.output_dir
    bodies_dir = options.bodies_dir
    site = options.site
    crop_m = options.crop_m
    frequency_hz = options.frequency_hz
    locations = options.locations
    densities = options.densities
    realisations = options.realisations
    rays = options.rays
    local_cells = options.local_cells
    max_bounces = options.max_bounces
    seed = options.seed
    stature_modes = options.stature_modes
    target_faces = options.target_faces
    max_radius_m = options.max_radius_m
    mean_free_paths = options.mean_free_paths
    clothing_rms_height_m = options.clothing_rms_height_m
    body_absorber = options.body_absorber
    variant = options.variant
    tag = options.tag
    resume = options.resume

    root = pathlib.Path(__file__).resolve().parents[2]
    output_dir = pathlib.Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    scratch = pathlib.Path(options.scratch or output_dir / "scratch")
    stem = f"{tag}_{frequency_hz / 1e9:g}ghz"
    rows_path = output_dir / f"{stem}_rows.jsonl"
    manifest_path = output_dir / f"{stem}_manifest.json"

    started = time.perf_counter()
    mesh = site_mesh(root, site, crop_m)
    geometry = MitsubaGeometry(mesh, variant=variant)
    datum = ground_datum(root, site, geometry)
    site_face_class = classify_faces(geometry.vertices, geometry.faces, datum)
    binding = load_table(root / "config", frequency_hz)

    body_permittivity = ABSORBER_PERMITTIVITY if body_absorber else skin_permittivity(frequency_hz)
    permittivity = np.append(binding.permittivity, body_permittivity)
    rms_height = np.append(binding.rms_height_m, 0.0 if body_absorber else float(clothing_rms_height_m))
    body_class_index = len(binding.class_names)

    base_library = load_body_library(bodies_dir, target_faces=target_faces)
    libraries = {mode: stature_library(base_library, mode, seed=seed) for mode in stature_modes}

    walk = build_walk(geometry, ground_datum_m=datum, radius_m=90.0, spacing_m=3.0, seed=seed)
    picks = stratified_subset(walk, locations)
    head_height_m = float(walk.provenance["head_height_m"])

    config = TraceConfig(
        frequency_hz=frequency_hz, rays=rays, local_cells=local_cells, max_bounces=max_bounces, seed=seed
    )
    baseline_tracer = SbrTracer(geometry, site_face_class, permittivity, rms_height, config)

    manifest: dict[str, Any] = {
        "generator": "semantic_twin.propagation.bystanders",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "question": (
            "how far does the pedestrian exposure distribution move when the square holds other "
            "people, per illumination model and per crowd density"
        ),
        "prediction": (
            "bystanders stand at the observation point's own height, so they can only take away "
            "the near horizon band. The corrected illumination laws put 87.9 percent of the street "
            "small cell measure and 9.4 percent of the rooftop measure below 5 degrees, so the "
            "street column should lose much more than the rooftop column."
        ),
        "site": site,
        "mesh": str(mesh),
        "mesh_triangles": int(geometry.face_count),
        "crop_radius_m": crop_m,
        "ground_datum_m": datum,
        "head_height_m": head_height_m,
        "trace_config": config.as_dict(),
        "surface_binding": binding.as_dict(),
        "body_material": {
            "class_index": body_class_index,
            "relative_permittivity": [float(permittivity[-1].real), float(permittivity[-1].imag)],
            "source": (
                "index matched absorber, a control that removes re-illumination"
                if body_absorber
                else "IT'IS skin through aegis.tissue.TissueModel.from_database"
            ),
            "rms_height_m": float(rms_height[-1]),
            "rms_height_source": "prior for clothing weave and drape, see CLOTHING_RMS_HEIGHT_M",
        },
        "body_library": base_library.provenance,
        "stature_modes": {
            mode: {
                "min": float(np.min(lib.stature_m)),
                "median": float(np.median(lib.stature_m)),
                "max": float(np.max(lib.stature_m)),
                "mean_width_m": float(np.mean(lib.width_m)),
            }
            for mode, lib in libraries.items()
        },
        "densities_per_m2": list(densities),
        "density_source": (
            "Fruin, Designing for pedestrians: a level-of-service concept, Highway Research Record "
            "355 (1971), pp. 1-15. Walkway level of service is stated as a pedestrian area module "
            "in square feet per pedestrian: A above 35, B 25 to 35, C 15 to 25, D 10 to 15, E 5 to "
            "10, F below 5. Inverted and converted at 1 sq ft = 0.09290304 m2 those boundaries are "
            "0.31, 0.43, 0.72, 1.08 and 2.15 people per square metre."
        ),
        "crowd": {
            "max_radius_m": max_radius_m,
            "mean_free_paths": mean_free_paths,
            "exclusion_radius_m": EXCLUSION_RADIUS_M,
            "min_separation_m": MIN_SEPARATION_M,
            "realisations": realisations,
            "density_is": "people per square metre of walkable ground, not of total disc area",
        },
        "walk": walk.provenance,
        "locations_traced": int(picks.size),
        "illumination_models": sorted(models),
        "storage_policy": "paths are never written, only per row scalars",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))

    expected_rows = len(libraries) * len(densities) * realisations
    finished = _finished_locations(rows_path, expected_rows) if resume else set()
    if finished:
        print(f"resuming, {len(finished)} standpoints already complete", flush=True)
    context = _StudyContext(
        options=options,
        models=models,
        geometry=geometry,
        datum=datum,
        site_face_class=site_face_class,
        permittivity=permittivity,
        rms_height=rms_height,
        trace_config=config,
        baseline_tracer=baseline_tracer,
        libraries=libraries,
        walk=walk,
        picks=picks,
        head_height_m=head_height_m,
        body_class_index=body_class_index,
        scratch=scratch,
    )
    with rows_path.open("a" if finished else "w") as handle:
        writer = _StudyWriter(context, handle)
        for order, index in enumerate(picks):
            if int(index) in finished:
                continue
            writer.write_location(order, int(index))

    manifest["wall_seconds"] = time.perf_counter() - started
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"wrote {rows_path}", flush=True)
    return rows_path


@dataclass(frozen=True)
class NoiseFloorConfig:
    """Inputs for the empty-square estimator variance run."""

    output_dir: pathlib.Path
    site: str = "korenmarkt"
    crop_m: int = 250
    frequency_hz: float = 15.0e9
    locations: int = 12
    rays: int = 120_000
    local_cells: int = 512
    max_bounces: int = DEFAULT_MAX_BOUNCES
    seed: int = 7
    seeds: int = 3
    variant: str = "llvm_ad_rgb"
    tag: str = "korenmarkt"


def noise_floor(options: NoiseFloorConfig) -> pathlib.Path:
    """How large a dB shift the estimator's own Monte Carlo error can fake.

    Without this the results table cannot be read. The street small cell weight
    is concentrated in the first few degrees above the horizon, so only a small
    fraction of the rays carries almost all of that model's ``chi``, and its
    estimator variance is much larger than the isotropic one's. Any crowd
    induced shift smaller than the number this writes is not a measurement of a
    crowd.

    Same standpoints, same everything, empty square, only the trace seed moves.
    """
    from ..illumination import MODELS as models
    from ..materials import classify_faces, load_table
    from ..transport.tracer import SbrTracer, TraceConfig
    from ..walk.grid import build_walk
    from ..walk.model import stratified_subset

    output_dir = options.output_dir
    site = options.site
    crop_m = options.crop_m
    frequency_hz = options.frequency_hz
    locations = options.locations
    rays = options.rays
    local_cells = options.local_cells
    max_bounces = options.max_bounces
    seed = options.seed
    seeds = options.seeds
    variant = options.variant
    tag = options.tag

    root = pathlib.Path(__file__).resolve().parents[2]
    output_dir = pathlib.Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    geometry = MitsubaGeometry(site_mesh(root, site, crop_m), variant=variant)
    datum = ground_datum(root, site, geometry)
    face_class = classify_faces(geometry.vertices, geometry.faces, datum)
    binding = load_table(root / "config", frequency_hz)
    walk = build_walk(geometry, ground_datum_m=datum, radius_m=90.0, spacing_m=3.0, seed=seed)
    picks = stratified_subset(walk, locations)
    config = TraceConfig(
        frequency_hz=frequency_hz, rays=rays, local_cells=local_cells, max_bounces=max_bounces, seed=seed
    )
    tracer = SbrTracer(geometry, face_class, binding.permittivity, binding.rms_height_m, config)

    shifts: dict[str, list[float]] = {name: [] for name in models}
    for index in picks:
        point = walk.points[index]
        ground_z = float(walk.ground_z_m[index])
        reference = tracer.trace(point, models, ground_z_m=ground_z, seed=seed + 1000 * int(index))
        for repeat in range(1, seeds):
            other = tracer.trace(point, models, ground_z_m=ground_z, seed=seed + 1000 * int(index) + 131 * repeat)
            for name in models:
                shifts[name].append(_shift_db(other.susceptibility[name], reference.susceptibility[name]))
        print(f"noise floor: {int(index)} done", flush=True)

    summary = {
        "what": "dB shift between two independent ray sets at the same standpoint, empty square",
        "locations": int(picks.size),
        "seeds_per_location": seeds,
        "rays": rays,
        "per_model": {
            name: {
                "median_abs_db": float(np.median(np.abs(values))),
                "p95_abs_db": float(np.quantile(np.abs(values), 0.95)),
                "max_abs_db": float(np.max(np.abs(values))),
            }
            for name, values in shifts.items()
        },
    }
    path = output_dir / f"{tag}_{frequency_hz / 1e9:g}ghz_noise_floor.json"
    path.write_text(json.dumps(summary, indent=2))
    print(f"wrote {path}", flush=True)
    return path


@dataclass(frozen=True)
class BystanderStudyConfig:
    """Inputs for the two-arm bystander study command."""

    locations: int
    realisations: int
    rays: int
    max_bounces: int
    local_cells: int
    frequency_ghz: float
    crop_m: int
    site: str
    seed: int
    tag: str
    target_faces: int
    max_radius_m: float
    mean_free_paths: float
    clothing_rms_mm: float
    body_absorber: bool
    densities: list[float]
    stature_modes: list[str]
    bodies: str
    output: str
    variant: str
    report: str | None
    resume: bool
    noise_floor: bool


def run_bystander_study(config: BystanderStudyConfig) -> None:
    """Run or summarise the bystander study from validated command inputs."""
    output_dir = pathlib.Path(config.output)
    stem = config.report or f"{config.tag}_{config.frequency_ghz:g}ghz"
    if config.noise_floor:
        noise_floor(
            NoiseFloorConfig(
                output_dir=output_dir,
                site=config.site,
                crop_m=config.crop_m,
                frequency_hz=config.frequency_ghz * 1e9,
                locations=config.locations,
                rays=config.rays,
                local_cells=config.local_cells,
                max_bounces=config.max_bounces,
                seed=config.seed,
                variant=config.variant,
                tag=config.tag,
            )
        )
        return
    if config.report is None:
        run_study(
            StudyRunConfig(
                output_dir=output_dir,
                bodies_dir=pathlib.Path(config.bodies),
                site=config.site,
                crop_m=config.crop_m,
                frequency_hz=config.frequency_ghz * 1e9,
                locations=config.locations,
                densities=tuple(config.densities),
                realisations=config.realisations,
                rays=config.rays,
                local_cells=config.local_cells,
                max_bounces=config.max_bounces,
                seed=config.seed,
                stature_modes=tuple(config.stature_modes),
                target_faces=config.target_faces,
                max_radius_m=config.max_radius_m,
                mean_free_paths=config.mean_free_paths,
                clothing_rms_height_m=config.clothing_rms_mm * 1e-3,
                body_absorber=config.body_absorber,
                variant=config.variant,
                tag=config.tag,
                resume=config.resume,
            )
        )
    from ..report.bystanders import plot_mechanism, plot_study, summarise_study

    summary = summarise_study(output_dir / f"{stem}_rows.jsonl")
    summary_path = output_dir / f"{stem}_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    figure = plot_study(summary, output_dir / f"{stem}_shift.png")
    mechanism = plot_mechanism(
        output_dir / f"{stem}_mechanism.png",
        library=load_body_library(pathlib.Path(config.bodies), target_faces=config.target_faces),
        summary=summary,
    )
    print(f"wrote {summary_path}, {figure} and {mechanism}")
