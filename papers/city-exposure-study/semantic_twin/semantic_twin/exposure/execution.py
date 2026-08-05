"""Execute one configured exposure run without owning command-line policy."""

from __future__ import annotations

import json
import hashlib
import pathlib
import platform
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from importlib import metadata
from typing import Any

import numpy as np

from semantic_twin.materials import HOST_SURFACE_CLASS_RULE
from semantic_twin.runconfig import RunConfig
from semantic_twin.transport.device_tracer import DeviceEscapeTracer


@dataclass(frozen=True)
class LegacyReplay:
    """Walk settings read from an older manifest when extending that run."""

    ground_datum_m: float | None = None
    walk_probe_z_m: float | None = None


@dataclass(frozen=True)
class ExecutionConfig:
    """Machine choices and runtime objects that do not identify a run."""

    workers: int | None = None
    coupler: Any = field(default=None, compare=False, repr=False)
    replay: LegacyReplay = field(default_factory=LegacyReplay)


@dataclass(frozen=True)
class StudyEnvironment:
    """Study resources and replaceable boundaries used by the executor."""

    output: pathlib.Path
    material_config: pathlib.Path
    semantics: pathlib.Path
    phantom: str
    phantom_mass_kg: float
    reference_s0_w_m2: float
    frequency_note: str
    crop_bound_note: str
    datum_cross_check_m: float
    models: Mapping[str, Any]
    site_mesh: Callable[[str, int], pathlib.Path]
    registered_ground_z: Callable[[str], float | None]
    site_walk_semantics: Callable[[str, int], pathlib.Path | None]
    site_fishnet: Callable[[str], tuple[pathlib.Path, pathlib.Path] | None]
    geometry_type: Any
    classify_faces: Callable[..., np.ndarray]
    bind_fishnet: Callable[..., Any]
    bind_walk_entities: Callable[..., Any]
    bind_walk_materials: Callable[..., Any]
    load_table: Callable[..., Any]
    build_walk: Callable[..., Any]
    site_walk: Callable[..., Any]
    measure_ground_datum: Callable[..., Any]
    stratified_subset: Callable[..., np.ndarray]
    trace_config_type: Any
    tracer_type: Any
    trace_standpoints: Callable[..., Any]
    body_coupler_type: Any
    describe_body: Callable[[Any], dict[str, Any]]
    report: Callable[[str], pathlib.Path]


@dataclass(frozen=True)
class PreparedScene:
    mesh: pathlib.Path
    geometry: Any
    datum: float
    datum_provenance: dict[str, Any]
    face_class: np.ndarray
    areas: np.ndarray


@dataclass(frozen=True)
class MaterialBinding:
    face_class: np.ndarray
    table: Any
    provenance: dict[str, Any]


@dataclass(frozen=True)
class PreparedRun:
    run: RunConfig
    environment: StudyEnvironment
    scene: PreparedScene
    material: MaterialBinding
    walk: Any
    picks: np.ndarray
    trace_config: Any
    tracer: Any
    coupler: Any


@dataclass(frozen=True)
class OutputFiles:
    rows: pathlib.Path
    spectra: pathlib.Path
    manifest: pathlib.Path


def execute(run: RunConfig, execution: ExecutionConfig, environment: StudyEnvironment) -> pathlib.Path:
    """Trace one site's walk and stream reduced results to the fixed study output."""
    _validate_run(run, environment.models)
    _validate_execution(run, execution)
    environment.output.mkdir(parents=True, exist_ok=True)
    stem = f"{run.tag}_{run.frequency_ghz:g}ghz"
    files = OutputFiles(
        environment.output / f"{stem}_locations.jsonl",
        environment.output / f"{stem}_spectra.npz",
        environment.output / f"{stem}_manifest.json",
    )

    started = time.perf_counter()
    scene = _prepare_scene(run, execution.replay, environment)
    material = _bind_materials(run, scene, environment)
    walk = _build_walk(run, execution.replay, scene, environment)
    picks = environment.stratified_subset(walk, run.locations)
    print(f"walk: {len(walk)} candidates, tracing {picks.size}", flush=True)

    trace_config = _trace_config(run, environment)
    tracer_type = DeviceEscapeTracer if run.transport_kernel == "drjit" else environment.tracer_type
    tracer = tracer_type(
        scene.geometry,
        material.face_class,
        material.table.permittivity,
        material.table.rms_height_m,
        trace_config,
    )
    coupler = execution.coupler
    if coupler is None:
        coupler = environment.body_coupler_type(
            environment.phantom,
            run.frequency_hz,
            body_mass_kg=environment.phantom_mass_kg,
        )

    prepared = PreparedRun(run, environment, scene, material, walk, picks, trace_config, tracer, coupler)
    manifest = _manifest(prepared)
    files.manifest.write_text(json.dumps(manifest, indent=2))
    _trace_rows(prepared, execution, files)

    manifest["wall_seconds"] = time.perf_counter() - started
    files.manifest.write_text(json.dumps(manifest, indent=2))
    print(f"wrote {files.rows}")
    environment.report(stem)
    return files.rows


def _validate_run(run: RunConfig, available_models: Mapping[str, Any]) -> None:
    """Refuse states this escape executor cannot implement faithfully."""
    required = {
        "law": (run.law, "band"),
        "estimator": (run.estimator, "escape"),
        "next_event": (run.next_event, None),
    }
    unsupported = [f"{name}={actual!r}" for name, (actual, expected) in required.items() if actual != expected]
    if unsupported:
        raise ValueError(f"exposure executor requires band/escape configuration; got {', '.join(unsupported)}")
    unknown = [name for name in run.models if name not in available_models]
    if unknown:
        raise ValueError(f"unknown illumination models: {', '.join(unknown)}")
    if "rooftop" not in run.models:
        raise ValueError("exposure executor requires the rooftop model for its spectra and progress schema")


def _validate_execution(run: RunConfig, execution: ExecutionConfig) -> None:
    """Reject device states that would fork or select an unsupported backend."""
    if run.transport_kernel != "drjit":
        return
    if run.variant not in ("llvm_ad_rgb", "cuda_ad_rgb"):
        raise ValueError(
            f"drjit transport requires a Mitsuba JIT RGB variant: llvm_ad_rgb or cuda_ad_rgb, got {run.variant!r}"
        )
    if execution.workers is not None and execution.workers > 1:
        raise ValueError(
            "drjit transport runs in one process because Dr.Jit state cannot cross worker boundaries; "
            f"got workers={execution.workers}"
        )


def _prepare_scene(run: RunConfig, replay: LegacyReplay, environment: StudyEnvironment) -> PreparedScene:
    mesh = environment.site_mesh(run.site, run.crop_m)
    geometry = environment.geometry_type(mesh, variant=run.variant)
    measured = environment.measure_ground_datum(geometry, radius_m=run.walk_radius_m)
    datum = measured.z_m if replay.ground_datum_m is None else float(replay.ground_datum_m)
    registered = environment.registered_ground_z(run.site)
    provenance: dict[str, Any] = dict(measured.provenance)
    provenance["registered_camera_ground_z_m"] = registered
    if replay.ground_datum_m is not None:
        provenance["measured_z_m"] = measured.z_m
        provenance["rule"] = (
            f"forced to {datum} m by the caller, overriding the measured "
            f"{measured.z_m} m. The measurement is kept above for comparison"
        )
    if registered is not None:
        offset = datum - registered
        provenance["measured_minus_registered_m"] = offset
        if abs(offset) > environment.datum_cross_check_m:
            raise RuntimeError(
                f"{run.site}: the measured ground datum {datum:.3f} m disagrees with the registered "
                f"camera ground height {registered:.3f} m by {offset:+.3f} m, more than the "
                f"{environment.datum_cross_check_m:.1f} m cross check allows"
            )
    print(
        f"{run.site}: ground datum {datum:.3f} m from {measured.band_columns} of {measured.columns} "
        f"columns ({100 * measured.band_fraction:.1f} %)",
        flush=True,
    )
    face_class = environment.classify_faces(geometry.vertices, geometry.faces, datum)
    return PreparedScene(mesh, geometry, datum, provenance, face_class, geometry.face_areas())


def _bind_materials(run: RunConfig, scene: PreparedScene, environment: StudyEnvironment) -> MaterialBinding:
    provenance: dict[str, Any] = {"materials": run.materials}
    walk_binding = pathlib.Path(run.walk_npz) if run.walk_npz else environment.site_walk_semantics(run.site, run.crop_m)
    fishnet = environment.site_fishnet(run.site)
    _require_material_evidence(run, walk_binding, fishnet)

    if run.materials == "semantic":
        return _bind_fishnet(run, scene, fishnet, provenance, environment)
    if run.materials == "walk":
        semantic = environment.bind_walk_entities(
            scene.areas,
            scene.face_class,
            walk_npz=walk_binding,
            semantics_path=environment.semantics,
        )
        return _bound_material(
            run,
            semantic,
            provenance,
            HOST_SURFACE_CLASS_RULE,
            "walk semantic",
            environment,
        )
    if run.materials.startswith("walk_material"):
        semantic = environment.bind_walk_materials(
            scene.areas,
            scene.face_class,
            walk_npz=walk_binding,
            semantics_path=environment.semantics,
            mixture=run.materials == "walk_material_mixture",
            over_entity=run.materials == "walk_material_over_entity",
            facade_only=run.materials == "walk_material_facade_only",
        )
        return _bound_material(
            run,
            semantic,
            provenance,
            HOST_SURFACE_CLASS_RULE,
            "walk material binding",
            environment,
        )
    if run.materials == "geometric":
        table = environment.load_table(environment.material_config, run.frequency_hz)
        provenance.update({"covered_fraction_by_face": 0.0, "covered_fraction_by_area": 0.0})
        return MaterialBinding(scene.face_class, table, provenance)
    raise ValueError(f"unknown materials mode {run.materials!r}")


def _require_material_evidence(
    run: RunConfig,
    walk_binding: pathlib.Path | None,
    fishnet: tuple[pathlib.Path, pathlib.Path] | None,
) -> None:
    if run.materials.startswith("walk") and walk_binding is None:
        raise ValueError(
            f"no fused station binding for {run.site} at {run.crop_m} m. Build one with "
            f"`build_site_semantics.py --site {run.site} --crop-m {run.crop_m}`, which needs registered "
            f"panoramas under data/panoramas/{run.site}, or run --materials geometric."
        )
    if run.materials == "semantic" and fishnet is None:
        raise ValueError(
            f"no fishnet surface set for {run.site} at {run.crop_m} m, so there is nothing to bind. "
            "Use --materials walk if the site has a fused station binding, or --materials geometric."
        )


def _bind_fishnet(
    run: RunConfig,
    scene: PreparedScene,
    fishnet: tuple[pathlib.Path, pathlib.Path] | None,
    provenance: dict[str, Any],
    environment: StudyEnvironment,
) -> MaterialBinding:
    if fishnet is None:
        raise AssertionError("fishnet evidence was checked before binding")
    fishnet_dir, fishnet_mesh = fishnet
    source = environment.geometry_type(fishnet_mesh, variant=run.variant)
    semantic = environment.bind_fishnet(
        scene.geometry.vertices,
        scene.geometry.faces,
        scene.areas,
        scene.face_class,
        fishnet_dir=fishnet_dir,
        semantics_path=environment.semantics,
        source_ply_vertices=source.vertices,
        source_ply_faces=source.faces,
    )
    return _bound_material(
        run,
        semantic,
        provenance,
        HOST_SURFACE_CLASS_RULE,
        "semantic binding",
        environment,
    )


def _bound_material(
    run: RunConfig,
    semantic: Any,
    provenance: dict[str, Any],
    rule: str,
    label: str,
    environment: StudyEnvironment,
) -> MaterialBinding:
    table = environment.load_table(
        environment.material_config,
        run.frequency_hz,
        class_names=semantic.class_names,
        class_binding=semantic.class_binding,
        class_rule=rule,
    )
    provenance.update(
        {
            "covered_fraction_by_face": semantic.covered_fraction_by_face,
            "covered_fraction_by_area": semantic.covered_fraction_by_area,
            **semantic.provenance,
        }
    )
    print(
        f"{label}: {semantic.covered_fraction_by_face:.4f} of faces, {semantic.covered_fraction_by_area:.4f} of area",
        flush=True,
    )
    return MaterialBinding(semantic.face_class, table, provenance)


def _build_walk(run: RunConfig, replay: LegacyReplay, scene: PreparedScene, environment: StudyEnvironment) -> Any:
    if run.walk == "route":
        walk, _provenance = environment.site_walk(
            scene.geometry,
            run.site,
            stride_m=run.walk_stride_m,
            head_height_m=run.head_height_m,
            path=run.walk_path,
            crop_m=run.crop_m,
            ground_datum_m=scene.datum,
            radius_m=run.walk_radius_m,
            seed=run.seed,
        )
        return walk
    options = {} if replay.walk_probe_z_m is None else {"probe_z_m": replay.walk_probe_z_m}
    return environment.build_walk(
        scene.geometry,
        ground_datum_m=scene.datum,
        radius_m=run.walk_radius_m,
        spacing_m=run.walk_spacing_m,
        head_height_m=run.head_height_m,
        seed=run.seed,
        **options,
    )


def _trace_config(run: RunConfig, environment: StudyEnvironment) -> Any:
    return environment.trace_config_type(
        frequency_hz=run.frequency_hz,
        rays=run.rays,
        local_cells=run.local_cells,
        exit_bands=run.exit_bands,
        max_bounces=run.max_bounces,
        roulette_start=run.effective_roulette_start,
        roulette_floor=run.roulette_floor,
        ray_epsilon_m=run.ray_epsilon_m,
        range_weighted_escape=run.range_weighted_escape,
        seed=run.seed,
        batch=run.batch,
    )


def _manifest(prepared: PreparedRun) -> dict[str, Any]:
    run = prepared.run
    scene = prepared.scene
    material = prepared.material
    environment = prepared.environment
    return {
        "generator": "run_exposure.py",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "site": run.site,
        "mesh": str(scene.mesh),
        "mesh_sha256": _file_sha256(scene.mesh),
        "mesh_triangles": int(scene.geometry.face_count),
        "crop_radius_m": run.crop_m,
        "ground_datum_m": scene.datum,
        "ground_datum_source": scene.datum_provenance["rule"],
        "ground_datum": scene.datum_provenance,
        "reference_s0_w_m2": environment.reference_s0_w_m2,
        "trace_config": prepared.trace_config.as_dict(),
        "surface_binding": material.table.as_dict(),
        "semantic_binding": {
            **material.provenance,
            "face_class_sha256": _array_sha256(material.face_class),
        },
        "class_area_fractions": {
            name: float(scene.areas[material.face_class == i].sum() / scene.areas.sum())
            for i, name in enumerate(material.table.class_names)
        },
        "frequency_note": environment.frequency_note,
        "crop_bound_note": environment.crop_bound_note,
        "walk": _walk_provenance(run, prepared.walk),
        "locations_requested": run.locations,
        "locations_traced": int(prepared.picks.size),
        "illumination_models": {
            name: {
                "elevation_deg": [model.elevation_min_deg, model.elevation_max_deg],
                "law": model.law,
                "height_band_m": list(model.height_band_m) if model.height_band_m else None,
                "range_band_m": list(model.range_band_m) if model.range_band_m else None,
                "description": model.description,
            }
            for name, model in environment.models.items()
            if name in run.models
        },
        "body": environment.describe_body(prepared.coupler),
        "variant": run.variant,
        "transport": _transport_provenance(run),
        "python": platform.python_version(),
        "storage_policy": "paths are never written, only per location scalars and rho",
        "run_digest": run.digest(),
        "run": run.as_dict(),
    }


def _walk_provenance(run: RunConfig, walk: Any) -> dict[str, Any]:
    """Give an all-location route the same explicit candidate count as a grid."""
    if run.walk == "grid":
        return walk.provenance
    return {**walk.provenance, "candidates_after_clearance": len(walk)}


def _transport_provenance(run: RunConfig) -> dict[str, Any]:
    """Record the numerical transport implementation separately from geometry."""
    provenance: dict[str, Any] = {"kernel": run.transport_kernel}
    if run.transport_kernel == "drjit":
        provenance.update(
            {
                "floating_point": "float32",
                "rng": {"family": "counter", "algorithm": "tea32"},
                "versions": {
                    "mitsuba": _distribution_version("mitsuba"),
                    "drjit": _distribution_version("drjit"),
                },
            }
        )
    return provenance


def _array_sha256(array: np.ndarray) -> str:
    """Hash an array's exact type, shape, and bytes for payload matching."""
    value = np.ascontiguousarray(array)
    digest = hashlib.sha256()
    digest.update(value.dtype.str.encode())
    digest.update(str(value.shape).encode())
    digest.update(value.tobytes())
    return digest.hexdigest()


def _file_sha256(path: pathlib.Path) -> str:
    """Hash the exact bytes from which the production geometry was loaded."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _distribution_version(name: str) -> str:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return "unavailable"


def _trace_rows(prepared: PreparedRun, execution: ExecutionConfig, files: OutputFiles) -> None:
    run = prepared.run
    environment = prepared.environment
    walk = prepared.walk
    picks = prepared.picks
    models = {name: environment.models[name] for name in run.models}
    spectra = np.zeros((picks.size, run.local_cells))
    standpoints = [(walk.points[i], float(walk.ground_z_m[i]), run.seed + 1000 * int(i)) for i in picks]
    workers = 1 if run.transport_kernel == "drjit" else execution.workers
    with files.rows.open("w") as handle:
        results = environment.trace_standpoints(prepared.tracer, standpoints, models, workers=workers)
        for row_index, result in results:
            index = picks[row_index]
            row = _result_row(run, environment, prepared.coupler, walk, index, result, models)
            spectra[row_index] = result.rho["rooftop"]
            handle.write(json.dumps(row) + "\n")
            handle.flush()
            _print_progress(row_index, picks.size, row, result.seconds)
            np.savez_compressed(
                files.spectra,
                rho_rooftop=spectra[: row_index + 1],
                local_grid=result.local_grid,
                solid_angle=result.local_solid_angle,
                index=picks[: row_index + 1],
            )


def _result_row(
    run: RunConfig,
    environment: StudyEnvironment,
    coupler: Any,
    walk: Any,
    index: int,
    result: Any,
    models: Mapping[str, Any],
) -> dict[str, Any]:
    point = walk.points[index]
    row = {
        "index": int(index),
        "x": float(point[0]),
        "y": float(point[1]),
        "z": float(point[2]),
        "ground_z_m": float(walk.ground_z_m[index]),
        "seconds": result.seconds,
    }
    point_kind = getattr(walk, "provenance", {}).get("point_kind")
    if point_kind is not None:
        row["point_kind"] = point_kind[index]
    row.update(result.scalars())
    for name in models:
        exposure = coupler.couple(
            result.local_grid,
            result.rho[name],
            result.local_solid_angle,
            environment.reference_s0_w_m2,
        )
        for key, value in exposure.as_dict().items():
            row[f"{name}_{key}"] = value
    return row


def _print_progress(row_index: int, total: int, row: Mapping[str, Any], seconds: float) -> None:
    print(
        f"[{row_index + 1}/{total}] chi_rooftop={row['chi_rooftop']:.3f} "
        f"sky={row['sky_fraction']:.3f} "
        f"peak_sab={row['rooftop_peak_sab_w_m2']:.4f} "
        f"({seconds:.1f} s)",
        flush=True,
    )
