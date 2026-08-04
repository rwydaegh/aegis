"""Where the material evidence runs out, and what a three bounce budget costs.

Two questions, one set of standpoints.

**Where does the evidence run out.** The trace is adjoint: rays leave the
observation point and the estimator reads them backwards, so the first surface
interaction is the one that scatters energy into the observer. A panorama
standing at that observation point looks at exactly those surfaces. The claim
this script tests is that the first bounce, and to a large extent the second,
land on triangles a registered panorama actually observed, and that the third is
the first that routinely does not. That is a measurement, not a slogan, and it
can come out the other way.

The evidence mask is the per triangle transient free ray count from the fused
station binding, indexed on the tracer's own mesh with no join. A triangle is
observed when at least one admitted station collected at least one clean ray on
it, which is exactly the set that ``bind_walk_entities`` gives a measured material
to. Everything else falls back to the geometric orientation rule, so a bounce
landing outside the mask is a bounce landing on a guessed material.

**What does the budget cost.** The same standpoints are traced at several
budgets from one script so the comparison carries no difference in geometry,
datum or walk. Reported per illumination model as a distribution over
standpoints, together with the truncated throughput share, which is the share of
the power still travelling when the budget ran out and is therefore the size of
the low bias the truncation introduces.

Russian roulette is carried as its own axis. It fires when
``depth + 1 >= roulette_start``, so at a three bounce budget with the shipped
``roulette_start`` of 3 it can only kill rays one iteration before the hard cap
drops them anyway. Roulette is unbiased by construction, it divides the survivor
throughput by the survival probability, so switching it off does not move the
expectation. What it moves is the variance, and at a short budget it buys almost
no work in exchange for that variance. The run measures both.

Usage
-----
    python measure_bounce_evidence.py --site korenmarkt --crop-m 130 250
    python measure_bounce_evidence.py --crop-m 250 --locations 40 --rays 200000
"""

from __future__ import annotations

import json
import pathlib
import time
from dataclasses import dataclass
from itertools import pairwise
from typing import Any

import numpy as np

from semantic_twin import paths
from semantic_twin.exposure.study import (
    MODELS,
    SEMANTICS,
    measure_ground_datum,
    site_fishnet,
    site_mesh,
    site_walk_semantics,
)
from semantic_twin.materials import (
    CLASS_NAMES,
    bind_fishnet,
    bind_walk_entities,
    classify_faces,
    load_table,
)
from semantic_twin.propagation import (
    DEFAULT_MAX_BOUNCES,
    BounceEvidenceTally,
    MitsubaGeometry,
    SbrTracer,
    TraceConfig,
)
from semantic_twin.walk.grid import build_walk
from semantic_twin.walk.model import stratified_subset

SCRIPT_DIR = paths.root()
CONFIG = paths.config_dir()
OUTPUT = paths.output("bounce_budget")

#: Budgets to score, as ``(max_bounces, roulette_start)``. 4 is what the
#: published eleven city run ``city250_corrected`` used, 6 is what most other
#: manifests in ``outputs/exposure_korenmarkt`` used, and 3 is the new default.
#: A ``roulette_start`` above the budget switches roulette off entirely.
BUDGETS: tuple[tuple[int, int], ...] = (
    (3, 3),
    (3, 99),
    (4, 3),
    (6, 3),
    (8, 99),
)

#: The reference the costs are quoted against: the longest budget, roulette off.
REFERENCE = (8, 99)


@dataclass(frozen=True)
class BounceEvidenceConfig:
    sites: tuple[str, ...] = ("korenmarkt",)
    crops_m: tuple[int, ...] = (130, 250)
    locations: int = 24
    rays: int = 200_000
    local_cells: int = 512
    walk_radius_m: float = 90.0
    walk_spacing_m: float = 3.0
    frequency_hz: float = 15.0e9
    variant: str = "llvm_ad_rgb"
    seed: int = 7
    variance_seeds: int = 8
    variance_standpoints: int = 4
    tag: str = ""
    out: pathlib.Path = OUTPUT


@dataclass(frozen=True)
class _Measurement:
    site: str
    crop_m: int
    geometry: Any
    face_class: np.ndarray
    binding: Any
    masks: dict[str, dict[str, Any]]
    points: np.ndarray
    datums: np.ndarray
    datum: float
    config: BounceEvidenceConfig


@dataclass(frozen=True)
class _ProbeSet:
    points: list[np.ndarray]
    grounds: list[float]
    kind: list[str]
    gap_m: np.ndarray
    stations: np.ndarray


def evidence_masks(
    site: str,
    crop_m: int,
    geometry: Any,
    areas: np.ndarray,
    face_class: np.ndarray,
) -> dict[str, dict[str, Any]]:
    """Per triangle boolean masks of what image evidence covers, by definition.

    Four nested definitions, because "a panorama saw it" and "a panorama gave it
    a material" are not the same set and the difference between them is the
    diagnosis when the first interaction turns out not to be fully covered.

    ``seen_by_the_ray_grid`` is every triangle the station's equirectangular cast
    landed on at all. ``survived_transient_rejection`` is the subset whose rays
    were not thrown away as a person, a vehicle or a piece of clutter in front.
    ``walk`` is the subset that came out of that with a material, which is the
    set ``bind_walk_entities`` actually binds and therefore the only one that changes
    a number. ``fishnet`` is the stricter cut surface set, which exists only
    where a fishnet was built and joins on triangle centroids rather than on
    index.
    """
    masks: dict[str, dict[str, Any]] = {}

    walk_npz = site_walk_semantics(site, crop_m)
    if walk_npz is not None:
        data = np.load(walk_npz, allow_pickle=True)
        masks["seen_by_the_ray_grid"] = {
            "mask": data["rays"].sum(axis=0) > 0,
            "source": str(walk_npz.relative_to(SCRIPT_DIR)),
            "definition": "the station equirectangular cast landed at least one ray on the triangle",
        }
        masks["survived_transient_rejection"] = {
            "mask": data["clean_rays"].sum(axis=0) > 0,
            "source": str(walk_npz.relative_to(SCRIPT_DIR)),
            "definition": "at least one of those rays was not rejected as a transient or as clutter in front",
        }
        binding = bind_walk_entities(areas, face_class, walk_npz=walk_npz, semantics_path=SEMANTICS)
        covered = binding.face_class >= len(CLASS_NAMES)
        masks["walk"] = {
            "mask": covered,
            "source": str(walk_npz.relative_to(SCRIPT_DIR)),
            "stations": int(binding.provenance["stations"]),
            "definition": "and the entity class it collected carries a material in vistas_material_prior",
            "covered_fraction_by_face": binding.covered_fraction_by_face,
            "covered_fraction_by_area": binding.covered_fraction_by_area,
        }
        for name in ("seen_by_the_ray_grid", "survived_transient_rejection"):
            mask = masks[name]["mask"]
            masks[name]["covered_fraction_by_face"] = float(mask.mean())
            masks[name]["covered_fraction_by_area"] = float(areas[mask].sum() / areas.sum())

    fishnet = site_fishnet(site)
    if fishnet is not None:
        directory, mesh_path = fishnet
        source = MitsubaGeometry(mesh_path)
        binding = bind_fishnet(
            geometry.vertices,
            geometry.faces,
            areas,
            face_class,
            fishnet_dir=directory,
            semantics_path=SEMANTICS,
            source_ply_vertices=source.vertices,
            source_ply_faces=source.faces,
        )
        covered = binding.face_class >= len(CLASS_NAMES)
        masks["fishnet"] = {
            "mask": covered,
            "source": str(directory.relative_to(SCRIPT_DIR)),
            "views": len(sorted(directory.glob("*_fishnet.npz"))),
            "covered_fraction_by_face": binding.covered_fraction_by_face,
            "covered_fraction_by_area": binding.covered_fraction_by_area,
        }
    return masks


def station_positions(site: str, crop_m: int) -> np.ndarray:
    """Registered camera positions of the stations that built the binding, in ENU.

    Two shapes on disk. ``build_site_semantics.py`` writes the pose beside the
    admission verdict, so its sidecar carries positions directly. The older
    Korenmarkt Mapillary product does not, and its poses have to be joined by
    image id to ``walk_download.json``. Returns an empty array where neither is
    available, in which case the distance axis is simply absent rather than
    guessed.
    """
    npz = site_walk_semantics(site, crop_m)
    if npz is None:
        return np.zeros((0, 3))
    sidecar = npz.with_suffix(".json")
    if not sidecar.exists():
        return np.zeros((0, 3))
    document = json.loads(sidecar.read_text())

    admitted = document.get("stations_admitted")
    if admitted and all("position_enu_m" in entry for entry in admitted):
        return np.asarray([entry["position_enu_m"] for entry in admitted], dtype=np.float64)

    used = document.get("stations_used")
    download = npz.parent / "walk_download.json"
    if used and download.exists():
        pose = {
            entry["image_id"]: entry["pose"]["position_enu_m"] for entry in json.loads(download.read_text())["stations"]
        }
        found = [pose[entry["image_id"]] for entry in used if entry["image_id"] in pose]
        if found:
            return np.asarray(found, dtype=np.float64)
    return np.zeros((0, 3))


def joint(tally: BounceEvidenceTally, launched: int) -> dict[str, Any]:
    """The tally, plus the joint of coverage and power rather than the marginals.

    A depth that is ninety percent unobserved but carries two percent of the
    power is not a problem, and a reader cannot tell the two apart from the
    coverage fraction alone. ``launched`` is the total number of rays fired
    across the standpoints pooled here, and every ray leaves with unit
    throughput, so dividing the incident throughput by it puts both quantities
    on one scale: the share of all launched power that arrives at a surface at
    that depth, and the share that arrives at a surface with no image evidence
    behind its material.
    """
    out = tally.as_dict()
    incident = np.asarray(tally.throughput) / max(launched, 1)
    out["share_of_launched_power_incident"] = incident.tolist()
    out["share_of_launched_power_incident_cumulative"] = np.cumsum(incident).tolist()
    for name in tally.names:
        unobserved = (np.asarray(tally.throughput) - np.asarray(tally.throughput_observed[name])) / max(launched, 1)
        out[name]["share_of_launched_power_on_unobserved_material"] = unobserved.tolist()
        out[name]["share_of_launched_power_on_unobserved_material_cumulative"] = np.cumsum(unobserved).tolist()
    return out


def quantiles(values: np.ndarray) -> dict[str, float]:
    finite = np.asarray(values, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return {}
    q = np.percentile(finite, [0, 10, 25, 50, 75, 90, 100])
    return {
        "min": float(q[0]),
        "p10": float(q[1]),
        "p25": float(q[2]),
        "median": float(q[3]),
        "p75": float(q[4]),
        "p90": float(q[5]),
        "max": float(q[6]),
        "mean": float(finite.mean()),
        "n": int(finite.size),
    }


def _probe_set(measurement: _Measurement) -> _ProbeSet:
    stations = station_positions(measurement.site, measurement.crop_m)
    points = list(measurement.points)
    grounds = list(measurement.datums)
    kind = ["walk"] * len(measurement.points)
    for position in stations:
        points.append(np.asarray(position, dtype=np.float64))
        grounds.append(measurement.datum)
        kind.append("station")
    combined = np.asarray(points, dtype=np.float64)
    gap = (
        np.linalg.norm(combined[:, None, :2] - stations[None, :, :2], axis=2).min(axis=1)
        if stations.size
        else np.full(len(points), np.nan)
    )
    return _ProbeSet(points, grounds, kind, gap, stations)


def _trace_probe(
    measurement: _Measurement,
    probes: _ProbeSet,
    tracer: SbrTracer,
    plain: dict[str, np.ndarray],
    probe_bounces: int,
) -> tuple[BounceEvidenceTally, BounceEvidenceTally, BounceEvidenceTally, list[dict[str, Any]], float]:
    pooled_all = BounceEvidenceTally(plain, probe_bounces)
    pooled_walk = BounceEvidenceTally(plain, probe_bounces)
    pooled_station = BounceEvidenceTally(plain, probe_bounces)
    per_standpoint: list[dict[str, Any]] = []
    started = time.perf_counter()
    for index, (point, ground) in enumerate(zip(probes.points, probes.grounds, strict=True)):
        local = BounceEvidenceTally(plain, probe_bounces)
        tracer.trace(point, MODELS, ground_z_m=float(ground), seed=measurement.config.seed + index, tally=local)
        pooled_all.add(local)
        (pooled_station if probes.kind[index] == "station" else pooled_walk).add(local)
        row: dict[str, Any] = {
            "kind": probes.kind[index],
            "metres_to_nearest_station": (None if not np.isfinite(probes.gap_m[index]) else float(probes.gap_m[index])),
        }
        for name in plain:
            _, by_power = local.fractions(name)
            row[name] = [None if np.isnan(value) else float(value) for value in by_power]
        per_standpoint.append(row)
        if (index + 1) % 10 == 0:
            print(f"  probe {index + 1}/{len(probes.points)}", flush=True)
    return pooled_all, pooled_walk, pooled_station, per_standpoint, started


def _distance_coverage(
    plain: dict[str, np.ndarray], per_standpoint: list[dict[str, Any]], gap_m: np.ndarray, probe_bounces: int
) -> dict[str, Any]:
    edges = [0.0, 5.0, 10.0, 20.0, 40.0, 80.0, np.inf]
    binned: dict[str, Any] = {}
    for name in plain:
        table = np.array([[np.nan if value is None else value for value in row[name]] for row in per_standpoint])
        rows = []
        for low, high in pairwise(edges):
            select = (gap_m >= low) & (gap_m < high)
            if not np.any(select):
                continue
            rows.append(
                {
                    "metres_from_nearest_station": [low, None if np.isinf(high) else high],
                    "standpoints": int(np.count_nonzero(select)),
                    "median_covered_fraction_by_power": {
                        f"bounce_{depth + 1}": float(np.nanmedian(table[select, depth]))
                        for depth in range(probe_bounces)
                    },
                }
            )
        binned[name] = rows
    return binned


def _evidence_probe(measurement: _Measurement) -> dict[str, Any]:
    config = measurement.config
    probe_bounces, probe_roulette = REFERENCE
    trace_config = TraceConfig(
        frequency_hz=config.frequency_hz,
        rays=config.rays,
        local_cells=config.local_cells,
        max_bounces=probe_bounces,
        roulette_start=probe_roulette,
        seed=config.seed,
    )
    tracer = SbrTracer(
        measurement.geometry,
        measurement.face_class,
        measurement.binding.permittivity,
        measurement.binding.rms_height_m,
        trace_config,
    )
    plain = {name: entry["mask"] for name, entry in measurement.masks.items()}
    probes = _probe_set(measurement)
    pooled_all, pooled_walk, pooled_station, per_standpoint, started = _trace_probe(
        measurement, probes, tracer, plain, probe_bounces
    )
    evidence = {
        "pooled": joint(pooled_all, config.rays * len(probes.points)),
        "pooled_walk_standpoints_only": joint(pooled_walk, config.rays * len(measurement.points)),
        "per_standpoint": per_standpoint,
        "against_distance_from_nearest_station": _distance_coverage(plain, per_standpoint, probes.gap_m, probe_bounces),
    }
    if probes.stations.size:
        evidence["pooled_at_station_positions"] = joint(pooled_station, config.rays * int(probes.stations.shape[0]))
    return {
        "bounce_evidence": evidence,
        "bounce_evidence_probe": {
            "max_bounces": probe_bounces,
            "roulette_start": probe_roulette,
            "walk_standpoints": int(measurement.points.shape[0]),
            "station_standpoints": int(probes.stations.shape[0]) if probes.stations.size else 0,
            "weight": "throughput incident on the surface, before that interaction's reflectance",
            "seconds": time.perf_counter() - started,
        },
    }


def _budget_cost(measurement: _Measurement) -> dict[str, Any]:
    config = measurement.config
    keys = ("chi_isotropic", "chi_rooftop", "chi_street_small_cell")
    by_budget: dict[str, dict[str, np.ndarray]] = {}
    for max_bounces, roulette_start in BUDGETS:
        label = f"L{max_bounces}_roulette{roulette_start}"
        trace_config = TraceConfig(
            frequency_hz=config.frequency_hz,
            rays=config.rays,
            local_cells=config.local_cells,
            max_bounces=max_bounces,
            roulette_start=roulette_start,
            seed=config.seed,
        )
        tracer = SbrTracer(
            measurement.geometry,
            measurement.face_class,
            measurement.binding.permittivity,
            measurement.binding.rms_height_m,
            trace_config,
        )
        rows = []
        started = time.perf_counter()
        for index, (point, ground) in enumerate(zip(measurement.points, measurement.datums, strict=True)):
            result = tracer.trace(point, MODELS, ground_z_m=float(ground), seed=config.seed + index)
            rows.append(result.scalars())
        columns = {
            key: np.array([row.get(key, np.nan) for row in rows]) for key in {key for row in rows for key in row}
        }
        columns["seconds"] = np.array([time.perf_counter() - started])
        by_budget[label] = columns
        print(
            f"  {label}: median chi_rooftop {np.median(columns['chi_rooftop']):.6f}, "
            f"truncated share median {np.median(columns['truncated_throughput_share']):.5f}, "
            f"{time.perf_counter() - started:.1f} s",
            flush=True,
        )

    reference_label = f"L{REFERENCE[0]}_roulette{REFERENCE[1]}"
    budgets: dict[str, Any] = {}
    for label, columns in by_budget.items():
        entry: dict[str, Any] = {
            "seconds": float(columns["seconds"][0]),
            "truncated_throughput_share": quantiles(columns["truncated_throughput_share"]),
            "sky_fraction": quantiles(columns["sky_fraction"]),
            "mean_bounces": quantiles(columns["mean_bounces"]),
        }
        for key in keys:
            here = columns[key]
            there = by_budget[reference_label][key]
            with np.errstate(divide="ignore", invalid="ignore"):
                shift = 10.0 * np.log10(np.where(there > 0.0, here / np.maximum(there, 1e-300), np.nan))
            entry[key] = {
                "value": quantiles(here),
                "against_reference_db": quantiles(shift),
                "standpoints_over_0p5_db": int(np.count_nonzero(np.abs(shift[np.isfinite(shift)]) > 0.5)),
                "standpoints_over_1_db": int(np.count_nonzero(np.abs(shift[np.isfinite(shift)]) > 1.0)),
            }
        budgets[label] = entry
    return {"budgets": budgets, "cost_reference": reference_label}


def measure(site: str, crop_m: int, config: BounceEvidenceConfig) -> dict[str, Any]:
    mesh = site_mesh(site, crop_m)
    geometry = MitsubaGeometry(mesh, variant=config.variant)
    datum = measure_ground_datum(geometry, radius_m=config.walk_radius_m).z_m
    face_class = classify_faces(geometry.vertices, geometry.faces, datum)
    areas = geometry.face_areas()
    binding = load_table(CONFIG, config.frequency_hz)

    masks = evidence_masks(site, crop_m, geometry, areas, face_class)
    if not masks:
        raise RuntimeError(f"no image evidence on disk for {site} at {crop_m} m, nothing to measure against")
    print(
        f"{site} {crop_m} m: {geometry.faces.shape[0]} triangles, evidence masks "
        + ", ".join(f"{k} {v['covered_fraction_by_face']:.4f} of faces" for k, v in masks.items()),
        flush=True,
    )

    walk = build_walk(
        geometry,
        ground_datum_m=datum,
        radius_m=config.walk_radius_m,
        spacing_m=config.walk_spacing_m,
        seed=config.seed,
    )
    picks = stratified_subset(walk, config.locations)
    points, datums = walk.points[picks], walk.ground_z_m[picks]
    print(f"walk: {len(walk)} candidates, tracing {picks.size} at {len(BUDGETS)} budgets", flush=True)

    report: dict[str, Any] = {
        "site": site,
        "crop_radius_m": crop_m,
        "mesh": str(mesh.relative_to(SCRIPT_DIR)),
        "mesh_triangles": int(geometry.faces.shape[0]),
        "ground_datum_m": float(datum),
        "locations": int(picks.size),
        "rays": config.rays,
        "frequency_hz": config.frequency_hz,
        "seed": config.seed,
        "materials": "geometric, so the binding is identical at every budget and only the budget moves",
        "evidence": {name: {k: v for k, v in entry.items() if k != "mask"} for name, entry in masks.items()},
    }

    measurement = _Measurement(
        site=site,
        crop_m=crop_m,
        geometry=geometry,
        face_class=face_class,
        binding=binding,
        masks=masks,
        points=points,
        datums=datums,
        datum=datum,
        config=config,
    )
    report.update(_evidence_probe(measurement))
    report.update(_budget_cost(measurement))

    # --- does roulette still pay at a three bounce budget -------------------
    # Roulette is unbiased whatever the budget, so the question is not bias, it
    # is whether the variance it injects buys any work back. That is a repeated
    # seed measurement and nothing else answers it: the same standpoint traced
    # under many independent streams, with and without roulette, scored on the
    # relative standard deviation of chi and on the wall clock.
    report["roulette_at_three_bounces"] = roulette_variance(
        geometry, face_class, binding, points[: config.variance_standpoints], datums, config
    )
    return report


def roulette_variance(
    geometry: Any,
    face_class: np.ndarray,
    binding: Any,
    points: np.ndarray,
    datums: np.ndarray,
    config: BounceEvidenceConfig,
) -> dict[str, Any]:
    """Relative spread of ``chi`` over independent seeds, roulette on and off."""
    out: dict[str, Any] = {
        "seeds": config.variance_seeds,
        "standpoints": len(points),
        "note": (
            "roulette divides the surviving throughput by the survival probability, so it does not "
            "move the expectation at any budget. What is compared here is the spread over seeds and "
            "the wall clock, which is the only thing it can trade."
        ),
    }
    for roulette_start in (DEFAULT_MAX_BOUNCES, 99):
        trace_config = TraceConfig(
            frequency_hz=config.frequency_hz,
            rays=config.rays,
            local_cells=config.local_cells,
            max_bounces=DEFAULT_MAX_BOUNCES,
            roulette_start=roulette_start,
            seed=config.seed,
        )
        tracer = SbrTracer(geometry, face_class, binding.permittivity, binding.rms_height_m, trace_config)
        spread: dict[str, list[float]] = {key: [] for key in ("chi_isotropic", "chi_rooftop", "chi_street_small_cell")}
        started = time.perf_counter()
        for index, (point, ground) in enumerate(zip(points, datums[: len(points)], strict=True)):
            draws = [
                tracer.trace(point, MODELS, ground_z_m=float(ground), seed=10_000 * (index + 1) + repeat).scalars()
                for repeat in range(config.variance_seeds)
            ]
            for key, relative_spread in spread.items():
                values = np.array([draw[key] for draw in draws])
                relative_spread.append(float(values.std(ddof=1) / values.mean()) if values.mean() > 0.0 else np.nan)
        label = "off" if roulette_start > DEFAULT_MAX_BOUNCES else f"from bounce {roulette_start}"
        out[f"roulette_{label.replace(' ', '_')}"] = {
            "seconds": time.perf_counter() - started,
            **{key: quantiles(np.array(values)) for key, values in spread.items()},
        }
        print(f"  roulette {label}: {time.perf_counter() - started:.1f} s", flush=True)
    return out


def execute(config: BounceEvidenceConfig) -> int:
    config.out.mkdir(parents=True, exist_ok=True)
    for site in config.sites:
        for crop_m in config.crops_m:
            try:
                report = measure(site, crop_m, config)
            except (FileNotFoundError, RuntimeError, ValueError) as error:
                # A site with no mesh or no binding at this radius is not a
                # failure of the measurement, it is the absence of the evidence
                # the measurement is about, and saying so is part of the answer.
                print(f"[skip] {site} at {crop_m} m: {error}", flush=True)
                continue
            report["default_max_bounces"] = DEFAULT_MAX_BOUNCES
            path = config.out / f"{site}_{crop_m}m{config.tag}_bounce_evidence.json"
            path.write_text(json.dumps(report, indent=2))
            print(f"wrote {path}", flush=True)
    return 0
