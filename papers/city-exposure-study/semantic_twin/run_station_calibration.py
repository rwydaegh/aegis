"""Exposure and first bounce evidence at the panorama standpoints themselves.

The study's licence for reading material off photographs is geometric. The
trace is adjoint, so the first surface interaction is a surface a camera
standing at the observation point can see. That argument is exact at a
standpoint a camera occupied and only statistical anywhere else, and
BOUNCE_BUDGET.md measures how fast it decays: essentially total coverage inside
ten metres of a station, essentially none past forty.

Every published material comparison is nevertheless measured over an 80
standpoint walk spread across a 90 m disc, where the first interaction lands on
photographed geometry between 54 and 80 percent of the time. This script runs
the comparison where the guarantee holds instead: at the admitted station
positions, with nothing else changed.

Two questions, one set of standpoints, both at the published operating point of
a 250 m crop, 15 GHz, three interactions and roulette off.

**Is the evidence actually exact here.** The same ``BounceEvidenceTally`` that
BOUNCE_BUDGET.md uses, attached to a trace launched from each station, scored on
the ``walk`` mask that ``bind_from_walk`` actually binds. If the first
interaction is not near 1.0 at a station, the premise of the whole experiment
fails there and that is the result.

**What do image derived materials do here.** The coverage ladder's rungs,
geometric against walk against fishnet, traced at the stations rather than at
the walk. Both reductions are reported for every shift, because they disagree by
up to a factor of five over the walk and one square changes sign between them:
the median of the paired per standpoint decibel difference, which is what the
paper uses, and the decibel ratio of the two distribution medians, which is what
COVERAGE_LADDER.md quotes.

Two standpoint conventions are carried, because a camera is not a pedestrian.

``pose``: the registered camera position exactly as admitted, which is where the
first bounce guarantee is a statement about that camera's own view. Its height
above the walkable ground is whatever the vehicle or the photographer had, and
across this set that runs from below the datum to nearly five metres above it.

``pedestrian``: the same horizontal position at the walk's own head height above
the ground under it, which is the standpoint a pedestrian would occupy and is
directly comparable to the published walk. Where the two agree, camera height is
not carrying the result.

Usage
-----
    python run_station_calibration.py --stage evidence
    python run_station_calibration.py --stage exposure --seeds 7,8,9,10 --workers 4
    python run_station_calibration.py --stage report
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from typing import Any

import numpy as np

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_exposure import (  # noqa: E402
    CONFIG,
    MODELS,
    SEMANTICS,
    fishnet_rests_on_an_admitted_pose,
    measure_ground_datum,
    site_fishnet,
    site_mesh,
    site_walk_semantics,
)
from semantic_twin.propagation import (  # noqa: E402
    BounceEvidenceTally,
    MitsubaGeometry,
    SbrTracer,
    TraceConfig,
    trace_standpoints,
)
from semantic_twin.propagation.scene import CLASS_NAMES, classify_faces, load_bindings  # noqa: E402
from semantic_twin.propagation.semantic_binding import bind, bind_from_walk, bind_from_walk_material  # noqa: E402
from semantic_twin.propagation.walk import ground_height  # noqa: E402

OUTPUT = SCRIPT_DIR / "outputs" / "station_calibration"

#: The sites with a fused station binding at 250 m, in the order their station
#: counts fall. Krakow, London, Times Square and Toulouse have no admitted
#: station at all and cannot answer.
SITES: tuple[str, ...] = (
    "prague_staromestske",
    "mexico_zocalo",
    "korenmarkt",
    "brussels_grandplace",
    "madrid_plazamayor",
    "tokyo_hachiko",
    "milan_duomo",
)

#: The three illumination models the ladder is scored on, same as run_exposure.
MODEL_KEYS = ("chi_isotropic", "chi_rooftop", "chi_street_small_cell")

#: The walk's own head height, so a pedestrian convention standpoint at a
#: station sits exactly where ``build_walk`` would have put one.
HEAD_HEIGHT_M = 1.5


def safe_fishnet(site: str) -> tuple[pathlib.Path, pathlib.Path] | None:
    """``site_fishnet`` without the raise for surfaces written one level down.

    A site whose fishnets sit in a folder per panorama has nothing this script
    can bind, and that is a build problem belonging to the fishnet stage rather
    than a reason for a station calibration to stop.
    """
    try:
        return site_fishnet(site)
    except ValueError as error:
        print(f"[note] {site} fishnet unusable: {error}", flush=True)
        return None


def admitted_stations(site: str, crop_m: int) -> list[dict[str, Any]]:
    """The stations that built this site's binding, with their registered poses.

    Read from the sidecar ``build_site_semantics.py`` writes beside the binding
    rather than from the download manifest, because admission is a property of
    the binding and a station refused at 250 m may still be present in the
    download.

    The older Korenmarkt Mapillary product predates that sidecar shape and lists
    the stations it used without their poses, so those are joined back to
    ``walk_download.json`` by image id. Same join
    ``measure_bounce_evidence.station_positions`` makes, and it matters that it
    is the same one: BOUNCE_BUDGET.md shows one of these eight poses is stale
    and fails the first interaction test, and a calibration that quietly used
    the re-registered 250 m pose instead would report a cleaner set than the
    130 m binding actually rests on.
    """
    npz = site_walk_semantics(site, crop_m)
    if npz is None:
        raise FileNotFoundError(f"no fused station binding for {site} at {crop_m} m")
    sidecar = npz.with_suffix(".json")
    if not sidecar.exists():
        raise FileNotFoundError(f"{npz} has no sidecar, so its station poses are not recoverable")
    document = json.loads(sidecar.read_text())
    entries = [entry for entry in document.get("stations_admitted", []) if "position_enu_m" in entry]
    if entries:
        return entries

    used = document.get("stations_used")
    download = npz.parent / "walk_download.json"
    if used and download.exists():
        pose = {
            entry["image_id"]: entry["pose"]["position_enu_m"] for entry in json.loads(download.read_text())["stations"]
        }
        joined = [
            {
                "station": entry["image_id"],
                "residual_deg": entry.get("skyline_residual_deg"),
                "position_enu_m": pose[entry["image_id"]],
                "pose_source": "walk_download.json, joined by image id",
            }
            for entry in used
            if entry["image_id"] in pose
        ]
        if joined:
            return joined
    raise RuntimeError(f"{sidecar} admits no station carrying a position")


def standpoint_set(
    geometry: Any,
    entries: list[dict[str, Any]],
    datum: float,
    convention: str,
) -> tuple[np.ndarray, np.ndarray, list[dict[str, Any]]]:
    """Trace origins and their ground reference under one standpoint convention.

    Returns the origins, the per standpoint ground height handed to the tracer,
    and a per station record carrying both so the choice is auditable rather
    than implied.
    """
    positions = np.asarray([entry["position_enu_m"] for entry in entries], dtype=np.float64)
    under, up = ground_height(geometry, positions[:, :2])
    records: list[dict[str, Any]] = []
    origins = np.array(positions, dtype=np.float64)
    grounds = np.full(positions.shape[0], float(datum))

    for index, entry in enumerate(entries):
        local = float(under[index]) if np.isfinite(under[index]) else float("nan")
        record = {
            "station": entry.get("station"),
            "residual_deg": entry.get("residual_deg"),
            "position_enu_m": [float(v) for v in positions[index]],
            "ground_under_station_m": None if not np.isfinite(local) else local,
            "ground_up_cosine": float(up[index]),
            "camera_height_above_local_ground_m": None
            if not np.isfinite(local)
            else float(positions[index, 2] - local),
            "camera_height_above_datum_m": float(positions[index, 2] - datum),
        }
        if convention == "pedestrian":
            base = local if np.isfinite(local) else datum
            origins[index, 2] = base + HEAD_HEIGHT_M
            grounds[index] = base
            record["ground_probe_used"] = (
                "local ray cast" if np.isfinite(local) else "site datum, no ground under the station"
            )
        record["origin_m"] = [float(v) for v in origins[index]]
        record["ground_z_m"] = float(grounds[index])
        records.append(record)
    return origins, grounds, records


def evidence_masks(site: str, crop_m: int, geometry: Any, areas: np.ndarray, face_class: np.ndarray) -> dict[str, Any]:
    """Per triangle boolean masks of what image evidence covers, by definition.

    The same four nested definitions ``measure_bounce_evidence.py`` carries, so
    a coverage number here is the same quantity as one there and the two can be
    compared without a caveat. ``walk`` is the set ``bind_from_walk`` binds and
    is therefore the only one that changes an exposure number.
    """
    masks: dict[str, Any] = {}
    walk_npz = site_walk_semantics(site, crop_m)
    if walk_npz is not None:
        data = np.load(walk_npz, allow_pickle=True)
        masks["seen_by_the_ray_grid"] = {
            "mask": data["rays"].sum(axis=0) > 0,
            "definition": "the station equirectangular cast landed at least one ray on the triangle",
        }
        masks["survived_transient_rejection"] = {
            "mask": data["clean_rays"].sum(axis=0) > 0,
            "definition": "at least one of those rays was not rejected as a transient or as clutter in front",
        }
        binding = bind_from_walk(areas, face_class, walk_npz=walk_npz, semantics_path=SEMANTICS)
        masks["walk"] = {
            "mask": binding.face_class >= len(CLASS_NAMES),
            "definition": "and the entity class it collected carries a material in vistas_material_prior",
            "stations": int(binding.provenance["stations"]),
            "covered_fraction_by_area": binding.covered_fraction_by_area,
        }
    fishnet = safe_fishnet(site)
    if fishnet is not None:
        directory, mesh_path = fishnet
        source = MitsubaGeometry(mesh_path)
        binding = bind(
            geometry.vertices,
            geometry.faces,
            areas,
            face_class,
            fishnet_dir=directory,
            semantics_path=SEMANTICS,
            source_ply_vertices=source.vertices,
            source_ply_faces=source.faces,
        )
        masks["fishnet"] = {
            "mask": binding.face_class >= len(CLASS_NAMES),
            "definition": "the per view fishnet cut surfaces, joined on triangle centroids",
            "covered_fraction_by_area": binding.covered_fraction_by_area,
        }
    for entry in masks.values():
        mask = entry["mask"]
        entry.setdefault("covered_fraction_by_area", float(areas[mask].sum() / areas.sum()))
        entry["covered_fraction_by_face"] = float(mask.mean())
    return masks


def bind_materials(
    materials: str,
    site: str,
    crop_m: int,
    geometry: Any,
    areas: np.ndarray,
    face_class: np.ndarray,
    frequency_hz: float,
    variant: str,
) -> tuple[np.ndarray, Any, dict[str, Any]]:
    """The face classes and surface binding one materials mode produces.

    A transcription of what ``run_exposure.run`` does for the same mode, kept
    here rather than imported because ``run`` traces a walk it builds itself and
    there is no seam in it to hand a standpoint set to.
    """
    if materials == "geometric":
        return face_class, load_bindings(CONFIG, frequency_hz), {"covered_fraction_by_area": 0.0}
    if materials == "walk":
        semantic = bind_from_walk(
            areas,
            face_class,
            walk_npz=site_walk_semantics(site, crop_m),
            semantics_path=SEMANTICS,
        )
        rule = (
            "fused multi station walk semantic posterior where any station saw the triangle, "
            "geometric orientation rule everywhere else"
        )
    elif materials == "semantic":
        fishnet = safe_fishnet(site)
        if fishnet is None:
            raise ValueError(f"no fishnet surface set for {site}")
        directory, mesh_path = fishnet
        source = MitsubaGeometry(mesh_path, variant=variant)
        semantic = bind(
            geometry.vertices,
            geometry.faces,
            areas,
            face_class,
            fishnet_dir=directory,
            semantics_path=SEMANTICS,
            source_ply_vertices=source.vertices,
            source_ply_faces=source.faces,
        )
        rule = (
            "panorama semantic posterior where a panorama saw the triangle, geometric orientation rule everywhere else"
        )
    elif materials in (
        "walk_material",
        "walk_material_mixture",
        "walk_material_over_entity",
        "walk_material_facade_only",
    ):
        semantic = bind_from_walk_material(
            areas,
            face_class,
            walk_npz=site_walk_semantics(site, crop_m),
            semantics_path=SEMANTICS,
            mixture=materials == "walk_material_mixture",
            over_entity=materials == "walk_material_over_entity",
            facade_only=materials == "walk_material_facade_only",
        )
        rule = (
            "fused multi station walk SAM 3 material posterior where any station bound the triangle, "
            "geometric orientation rule everywhere else"
        )
    else:
        raise ValueError(f"unknown materials mode {materials!r}")
    binding = load_bindings(
        CONFIG,
        frequency_hz,
        class_names=semantic.class_names,
        class_binding=semantic.class_binding,
        class_rule=rule,
    )
    provenance = {
        "covered_fraction_by_area": semantic.covered_fraction_by_area,
        "covered_fraction_by_face": semantic.covered_fraction_by_face,
        **{k: v for k, v in semantic.provenance.items() if k != "views"},
    }
    return semantic.face_class, binding, provenance


def scene(site: str, crop_m: int, args: argparse.Namespace) -> dict[str, Any]:
    """Everything a site's traces share: mesh, datum, classes, areas, stations."""
    mesh = site_mesh(site, crop_m)
    geometry = MitsubaGeometry(mesh, variant=args.variant)
    measured = measure_ground_datum(geometry, radius_m=args.walk_radius_m)
    face_class = classify_faces(geometry.vertices, geometry.faces, measured.z_m)
    return {
        "site": site,
        "crop_radius_m": crop_m,
        "mesh": str(mesh.relative_to(SCRIPT_DIR)),
        "mesh_triangles": int(geometry.faces.shape[0]),
        "geometry": geometry,
        "ground_datum_m": float(measured.z_m),
        "face_class": face_class,
        "areas": geometry.face_areas(),
        "entries": admitted_stations(site, crop_m),
    }


def stage_evidence(site: str, crop_m: int, args: argparse.Namespace) -> dict[str, Any]:
    """First interaction coverage at the stations, per station and pooled.

    Traced under the geometric binding at the operating budget, matching
    ``measure_bounce_evidence.py``. The first interaction's coverage cannot
    depend on the material binding at all, since no reflectance has been applied
    when it is recorded, and the later depths depend on it only through the
    throughput weight.
    """
    common = scene(site, crop_m, args)
    geometry, areas, face_class = common["geometry"], common["areas"], common["face_class"]
    masks = evidence_masks(site, crop_m, geometry, areas, face_class)
    if "walk" not in masks:
        raise RuntimeError(f"{site} has no fused station binding at {crop_m} m")
    plain = {name: entry["mask"] for name, entry in masks.items()}

    binding = load_bindings(CONFIG, args.frequency_hz)
    config = TraceConfig(
        frequency_hz=args.frequency_hz,
        rays=args.rays,
        local_cells=args.local_cells,
        max_bounces=args.max_bounces,
        roulette_start=args.max_bounces + 1,
        seed=args.seeds[0],
    )
    tracer = SbrTracer(geometry, face_class, binding.permittivity, binding.rms_height_m, config)

    report: dict[str, Any] = {
        **{k: v for k, v in common.items() if k not in ("geometry", "face_class", "areas", "entries")},
        "rays": args.rays,
        "frequency_hz": args.frequency_hz,
        "max_bounces": args.max_bounces,
        "roulette_start": args.max_bounces + 1,
        "evidence_masks": {name: {k: v for k, v in entry.items() if k != "mask"} for name, entry in masks.items()},
        "conventions": {},
    }
    for convention in args.conventions:
        origins, grounds, records = standpoint_set(geometry, common["entries"], common["ground_datum_m"], convention)
        pooled = BounceEvidenceTally(plain, args.max_bounces)
        started = time.perf_counter()
        for index, (origin, ground) in enumerate(zip(origins, grounds, strict=True)):
            local = BounceEvidenceTally(plain, args.max_bounces)
            result = tracer.trace(
                origin,
                MODELS,
                ground_z_m=float(ground),
                seed=args.seeds[0] + 1000 * index,
                tally=local,
            )
            pooled.add(local)
            records[index]["sky_fraction"] = float(result.sky_fraction)
            records[index]["mean_bounces"] = float(result.mean_bounces)
            # The geometric rung of the exposure stage traces this same
            # standpoint with this same config on this same seed, so these three
            # have to come back bit identical there. Carrying them makes the two
            # stages checkable against each other rather than assumed consistent.
            for key in MODEL_KEYS:
                records[index][key] = float(result.scalars()[key])
            for name in plain:
                _, by_power = local.fractions(name)
                records[index][f"covered_by_power_{name}"] = [None if np.isnan(v) else float(v) for v in by_power]
            print(
                f"  {site} {convention} station {index + 1}/{len(origins)} "
                f"bounce1 walk coverage {records[index]['covered_by_power_walk'][0]:.4f}",
                flush=True,
            )
        report["conventions"][convention] = {
            "stations": records,
            "pooled": pooled.as_dict(),
            "seconds": time.perf_counter() - started,
        }
    return report


def stage_exposure(site: str, crop_m: int, args: argparse.Namespace) -> dict[str, Any]:
    """Chi at the stations under every materials rung this site can climb."""
    common = scene(site, crop_m, args)
    geometry, areas, face_class = common["geometry"], common["areas"], common["face_class"]

    rungs = [args.baseline]
    for materials in args.rungs:
        if materials == args.baseline:
            continue
        # Same gate the coverage ladder applies: surfaces cut from cameras that
        # failed pose admission are files on disk rather than evidence.
        if materials == "semantic" and not (safe_fishnet(site) is not None and fishnet_rests_on_an_admitted_pose(site)):
            continue
        rungs.append(materials)

    report: dict[str, Any] = {
        **{k: v for k, v in common.items() if k not in ("geometry", "face_class", "areas", "entries")},
        "rays": args.rays,
        "frequency_hz": args.frequency_hz,
        "max_bounces": args.max_bounces,
        "roulette_start": args.max_bounces + 1,
        "seeds": list(args.seeds),
        "seed_note": (
            "the standpoint set is fixed by the data here, so redrawing a seed redraws only the ray "
            "streams. The spread over seeds is Monte Carlo ray noise and not the standpoint sampling "
            "uncertainty the walk's four seed error bar carries."
        ),
        "baseline": args.baseline,
        "rungs": {},
        "conventions": {},
    }

    for convention in args.conventions:
        origins, grounds, records = standpoint_set(geometry, common["entries"], common["ground_datum_m"], convention)
        report["conventions"][convention] = records
        per_rung: dict[str, Any] = {}
        for materials in rungs:
            bound_class, binding, provenance = bind_materials(
                materials, site, crop_m, geometry, areas, face_class, args.frequency_hz, args.variant
            )
            rows: dict[str, list[list[float]]] = {key: [] for key in MODEL_KEYS}
            extras: dict[str, list[list[float]]] = {key: [] for key in ("sky_fraction", "truncated_throughput_share")}
            for seed in args.seeds:
                config = TraceConfig(
                    frequency_hz=args.frequency_hz,
                    rays=args.rays,
                    local_cells=args.local_cells,
                    max_bounces=args.max_bounces,
                    roulette_start=args.max_bounces + 1,
                    seed=seed,
                )
                tracer = SbrTracer(geometry, bound_class, binding.permittivity, binding.rms_height_m, config)
                standpoints = [(origins[i], float(grounds[i]), seed + 1000 * i) for i in range(origins.shape[0])]
                collected: dict[int, dict[str, float]] = {}
                started = time.perf_counter()
                for row, result in trace_standpoints(tracer, standpoints, MODELS, workers=args.workers):
                    collected[row] = result.scalars()
                order = [collected[i] for i in range(len(standpoints))]
                for key in MODEL_KEYS:
                    rows[key].append([float(entry[key]) for entry in order])
                for key in extras:
                    extras[key].append([float(entry[key]) for entry in order])
                print(
                    f"  {site} {convention} {materials} seed {seed}: median chi_rooftop "
                    f"{np.median(rows['chi_rooftop'][-1]):.6f} ({time.perf_counter() - started:.1f} s)",
                    flush=True,
                )
            per_rung[materials] = {
                "covered_fraction_by_area": provenance.get("covered_fraction_by_area"),
                "provenance": provenance,
                "per_seed": {key: rows[key] for key in MODEL_KEYS},
                "diagnostics": extras,
            }
        report["rungs"][convention] = per_rung
    return report


def reductions(baseline: np.ndarray, values: np.ndarray) -> dict[str, float]:
    """Both reductions of one shift, named so neither can be quoted as the other.

    ``paired_median_shift_db`` is the median over standpoints of the per
    standpoint decibel difference, which is what paper.tex uses throughout.
    ``distribution_median_shift_db`` is the decibel ratio of the two
    distribution medians, which is what COVERAGE_LADDER.md quotes. They coincide
    only when the shift is uniform across standpoints.
    """
    ratio = values / baseline
    return {
        "paired_median_shift_db": float(np.median(10.0 * np.log10(ratio))),
        "distribution_median_shift_db": float(10.0 * np.log10(np.median(values) / np.median(baseline))),
        "paired_mean_shift_db": float(np.mean(10.0 * np.log10(ratio))),
        "paired_min_shift_db": float(np.min(10.0 * np.log10(ratio))),
        "paired_max_shift_db": float(np.max(10.0 * np.log10(ratio))),
        "standpoints": int(values.size),
    }


def spread(values: list[float]) -> dict[str, Any]:
    array = np.asarray(values, dtype=float)
    if array.size == 0:
        return {"replicates": 0, "mean_db": None, "sd_db": None, "standard_error_db": None, "per_seed_db": []}
    sd = float(array.std(ddof=1)) if array.size > 1 else None
    return {
        "replicates": int(array.size),
        "mean_db": float(array.mean()),
        "sd_db": sd,
        "standard_error_db": None if sd is None else sd / float(np.sqrt(array.size)),
        "per_seed_db": [float(v) for v in array],
    }


def summarise(exposure: dict[str, Any], baseline: str = "geometric") -> dict[str, Any]:
    """Per seed shifts under both reductions, then their mean and standard error.

    Every rung is scored against the run's own baseline, and additionally
    against the ``walk`` entity rung where one was traced. Those are two
    different questions and SPINE.md R3 is the second one: what a photograph
    buys over the orientation rule is not what reading a material off it buys
    over reading an entity class off it, and the sizes differ by an order of
    magnitude.
    """
    out: dict[str, Any] = {}
    baseline = exposure.get("baseline", baseline)
    for convention, per_rung in exposure["rungs"].items():
        entry: dict[str, Any] = {}
        for reference in dict.fromkeys([baseline, "walk"]):
            if reference not in per_rung:
                continue
            base = per_rung[reference]["per_seed"]
            against: dict[str, Any] = {}
            for materials, record in per_rung.items():
                if materials == reference:
                    continue
                by_model: dict[str, Any] = {}
                for key in MODEL_KEYS:
                    paired: list[float] = []
                    distribution: list[float] = []
                    detail: list[dict[str, float]] = []
                    for seed_index in range(len(base[key])):
                        reduced = reductions(
                            np.asarray(base[key][seed_index]), np.asarray(record["per_seed"][key][seed_index])
                        )
                        paired.append(reduced["paired_median_shift_db"])
                        distribution.append(reduced["distribution_median_shift_db"])
                        detail.append(reduced)
                    by_model[key] = {
                        "paired_median_shift_db": spread(paired),
                        "distribution_median_shift_db": spread(distribution),
                        "per_seed_detail": detail,
                    }
                against[materials] = {
                    "covered_fraction_by_area": record["covered_fraction_by_area"],
                    "by_model": by_model,
                }
            if reference == baseline:
                entry.update(against)
            entry[f"against_{reference}"] = against
        out[convention] = entry
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", nargs="+", default=list(SITES))
    parser.add_argument("--crop-m", type=int, default=250)
    parser.add_argument("--stage", default="both", choices=("evidence", "exposure", "both", "report"))
    parser.add_argument("--rays", type=int, default=200_000)
    parser.add_argument("--local-cells", type=int, default=512)
    parser.add_argument("--walk-radius-m", type=float, default=90.0)
    parser.add_argument("--frequency-hz", type=float, default=15.0e9)
    parser.add_argument("--max-bounces", type=int, default=3)
    parser.add_argument("--variant", default="llvm_ad_rgb")
    parser.add_argument("--seeds", default="7,8,9,10")
    parser.add_argument("--conventions", nargs="+", default=["pose", "pedestrian"])
    parser.add_argument("--rungs", nargs="+", default=["walk", "semantic"])
    # The evidence ladder is scored against the orientation rule. The SAM 3
    # material axis of SPINE.md R3 is scored against the entity binding instead,
    # because both of its sides are image derived and the question it asks is
    # narrower. Naming the baseline keeps the two from being quoted as one.
    parser.add_argument("--baseline", default="geometric")
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--tag", default="")
    parser.add_argument("--out", type=pathlib.Path, default=OUTPUT)
    args = parser.parse_args(argv)
    args.seeds = tuple(int(value) for value in args.seeds.split(","))
    args.out.mkdir(parents=True, exist_ok=True)

    for site in args.site:
        if args.stage in ("evidence", "both"):
            path = args.out / f"{site}_{args.crop_m}m{args.tag}_station_evidence.json"
            try:
                report = stage_evidence(site, args.crop_m, args)
            except (FileNotFoundError, RuntimeError, ValueError) as error:
                print(f"[skip] evidence {site}: {error}", flush=True)
            else:
                path.write_text(json.dumps(report, indent=2))
                print(f"wrote {path}", flush=True)
        if args.stage in ("exposure", "both"):
            path = args.out / f"{site}_{args.crop_m}m{args.tag}_station_exposure.json"
            try:
                report = stage_exposure(site, args.crop_m, args)
            except (FileNotFoundError, RuntimeError, ValueError) as error:
                print(f"[skip] exposure {site}: {error}", flush=True)
            else:
                report["summary"] = summarise(report)
                path.write_text(json.dumps(report, indent=2))
                print(f"wrote {path}", flush=True)
        if args.stage == "report":
            path = args.out / f"{site}_{args.crop_m}m{args.tag}_station_exposure.json"
            if not path.exists():
                print(f"[skip] report {site}: no exposure run on disk", flush=True)
                continue
            report = json.loads(path.read_text())
            report["summary"] = summarise(report)
            path.write_text(json.dumps(report, indent=2))
            print(f"rewrote {path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
