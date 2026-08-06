"""Execute one configured exposure run without owning command-line policy."""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import platform
import time
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from importlib import metadata
from typing import Any

import numpy as np

from semantic_twin.materials import HOST_SURFACE_CLASS_RULE, Provenance
from semantic_twin.exposure.output_policy import OutputProfile, coerce_profile, profile as profile_spec
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
    output_profile: OutputProfile = OutputProfile.STANDARD

    def __post_init__(self) -> None:
        """Normalize the profile at the execution boundary.

        Output retention is a runtime choice, not part of the physical run
        identity.  Accepting the string form keeps JSON/CLI adapters simple,
        while storing the enum makes accidental profile typos fail before any
        scene work begins.
        """
        object.__setattr__(self, "output_profile", coerce_profile(self.output_profile))


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
    site_surface_atlas: Callable[[str, int], pathlib.Path | None]
    load_surface_atlas: Callable[..., Any]
    bind_surface_atlas: Callable[..., tuple[Any, Any]]


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
    face_source: np.ndarray
    table: Any
    provenance: dict[str, Any]
    atlas_material: Any = field(default=None, compare=False, repr=False)

    def __post_init__(self) -> None:
        if self.face_source.shape != self.face_class.shape:
            raise ValueError(
                f"face_class shape {self.face_class.shape} does not match face_source shape {self.face_source.shape}"
            )
        known = {int(source) for source in Provenance}
        unknown = sorted(set(np.unique(self.face_source).tolist()) - known)
        if unknown:
            raise ValueError(f"face_source carries values {unknown} that name no Provenance member")


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
    """Trace one site's walk and publish one sealed output generation."""
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
    stage_seconds: dict[str, float] = {}
    stage_started = started
    scene = _prepare_scene(run, execution.replay, environment)
    stage_seconds["scene_preparation_seconds"] = time.perf_counter() - stage_started
    stage_started = time.perf_counter()
    material = _bind_materials(run, scene, environment)
    stage_seconds["material_binding_seconds"] = time.perf_counter() - stage_started
    stage_started = time.perf_counter()
    walk = _build_walk(run, execution.replay, scene, environment)
    picks = environment.stratified_subset(walk, run.locations)
    stage_seconds["walk_and_pick_seconds"] = time.perf_counter() - stage_started
    print(f"walk: {len(walk)} candidates, tracing {picks.size}", flush=True)

    stage_started = time.perf_counter()
    trace_config = _trace_config(run, environment)
    tracer_type = DeviceEscapeTracer if run.transport_kernel == "drjit" else environment.tracer_type
    tracer_options = {} if material.atlas_material is None else {"atlas_material": material.atlas_material}
    tracer = tracer_type(
        scene.geometry,
        material.face_class,
        material.table.permittivity,
        material.table.rms_height_m,
        trace_config,
        **tracer_options,
    )
    coupler = execution.coupler
    if coupler is None:
        coupler = environment.body_coupler_type(
            environment.phantom,
            run.frequency_hz,
            body_mass_kg=environment.phantom_mass_kg,
        )

    prepared = PreparedRun(run, environment, scene, material, walk, picks, trace_config, tracer, coupler)
    stage_seconds["tracer_coupler_setup_seconds"] = time.perf_counter() - stage_started
    generation_id = uuid.uuid4().hex
    staged = _staging_files(files, generation_id)
    manifest = _manifest(prepared, execution.output_profile)
    try:
        trace_metrics = _trace_rows(prepared, execution, staged)
        stage_seconds.update(trace_metrics)
        manifest["wall_seconds"] = time.perf_counter() - started
        validation_started = time.perf_counter()
        manifest["output_generation"] = _output_generation(
            generation_id,
            staged,
            files,
            profile=execution.output_profile,
        )
        _write_json(staged.manifest, manifest)
        _validate_generation(manifest, run, staged, profile=execution.output_profile)
        stage_seconds["output_validation_publication_seconds"] = time.perf_counter() - validation_started
        # Rewrite the staged commit record once with the measured validation
        # phase before the final atomic publication.  The numerical artifact
        # seals are independent of this diagnostic ledger.
        manifest["stage_seconds"] = _stage_seconds(stage_seconds, started)
        _write_json(staged.manifest, manifest)
        _publish_generation(staged, files, profile=execution.output_profile)
    finally:
        _remove_staging_files(staged)
    print(f"wrote {files.rows}")
    environment.report(stem)
    return files.rows


def _validate_run(run: RunConfig, available_models: Mapping[str, Any]) -> None:
    """Refuse states this executor cannot implement faithfully.

    The roofline/next-event method has a separate driver and result shape.  Keep
    accepting it as a valid :class:`RunConfig`, but fail before any output
    directory is created when it is handed to this escape-only executor.
    Likewise, reject mixed law/estimator pairs instead of letting a later
    attribute error decide which scientific path happened to run.
    """
    if run.law == "roofline" and run.estimator == "next_event" and run.next_event is not None:
        raise ValueError(
            "exposure executor requires band/escape configuration; got roofline/next_event. "
            "Use run_next_event.py for the next_event_roofline profile"
        )

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
    atlas_path = None
    if run.materials == "atlas":
        atlas_path = (
            pathlib.Path(run.atlas_npz) if run.atlas_npz else environment.site_surface_atlas(run.site, run.crop_m)
        )
    _require_material_evidence(run, walk_binding, fishnet, atlas_path)

    if run.materials == "atlas":
        return _bind_atlas(run, scene, provenance, atlas_path, environment)

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
        face_source = np.full(scene.face_class.shape, int(Provenance.GEOMETRIC), dtype=np.int8)
        return MaterialBinding(scene.face_class, face_source, table, provenance)
    raise ValueError(f"unknown materials mode {run.materials!r}")


def _bind_atlas(
    run: RunConfig,
    scene: PreparedScene,
    provenance: dict[str, Any],
    atlas_path: pathlib.Path | None,
    environment: StudyEnvironment,
) -> MaterialBinding:
    """Validate the canonical atlas pair and bind it to the traced mesh."""
    if atlas_path is None:
        raise AssertionError("surface atlas was checked before binding")
    atlas_manifest = atlas_path.with_suffix(".json")
    if not atlas_manifest.is_file():
        raise ValueError(f"surface atlas has no canonical JSON sidecar: {atlas_manifest}")
    mesh_sha256 = _file_sha256(scene.mesh)
    try:
        atlas = environment.load_surface_atlas(
            atlas_path,
            atlas_manifest,
            expected_mesh_sha256=mesh_sha256,
        )
    except (KeyError, OSError, TypeError, ValueError) as error:
        raise ValueError(f"surface atlas failed canonical provenance validation: {error}") from error
    atlas_mesh_sha256 = getattr(atlas, "mesh_sha256", None)
    if atlas_mesh_sha256 is None:
        raise ValueError("surface atlas does not record the exact support-mesh SHA-256")
    if str(atlas_mesh_sha256).lower() != mesh_sha256:
        raise ValueError("surface atlas belongs to a different support mesh")
    table, atlas_material = environment.bind_surface_atlas(
        atlas,
        environment.material_config,
        run.frequency_hz,
        geometric_class=scene.face_class,
        source_npz=atlas_path,
        source_manifest=atlas_manifest,
    )
    provenance.update(atlas_material.provenance)
    face_source = np.full(scene.face_class.shape, int(Provenance.GEOMETRIC), dtype=np.int8)
    print(
        f"surface atlas: {atlas_material.provenance['observed_faces']} observed faces, "
        f"{atlas_material.provenance['supported_texels']} supported texels",
        flush=True,
    )
    return MaterialBinding(scene.face_class, face_source, table, provenance, atlas_material=atlas_material)


def _require_material_evidence(
    run: RunConfig,
    walk_binding: pathlib.Path | None,
    fishnet: tuple[pathlib.Path, pathlib.Path] | None,
    atlas_path: pathlib.Path | None,
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
    if run.materials == "atlas" and atlas_path is None:
        raise ValueError(
            f"no joint surface atlas for {run.site} at {run.crop_m} m. Build one with "
            f"`build_surface_atlas.py --site {run.site} --crop-m {run.crop_m}`, or provide --atlas-npz."
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
    return MaterialBinding(semantic.face_class, semantic.face_source, table, provenance)


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


def _manifest(prepared: PreparedRun, output_profile: OutputProfile | str = OutputProfile.STANDARD) -> dict[str, Any]:
    run = prepared.run
    scene = prepared.scene
    material = prepared.material
    environment = prepared.environment
    selected_profile = coerce_profile(output_profile)
    document = {
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
            "face_source_sha256": _array_sha256(material.face_source),
            "face_source_labels": {str(int(source)): source.name for source in Provenance},
            "face_source_area_fractions": _face_source_area_fractions(
                material.face_source,
                scene.areas,
            ),
        },
        "class_area_fractions": {
            name: float(scene.areas[material.face_class == i].sum() / scene.areas.sum())
            for i, name in enumerate(material.table.class_names)
        },
        "class_area_fraction_basis": (
            "geometric fallback face classes; atlas transport uses hit-position material posteriors"
            if material.atlas_material is not None
            else "area-weighted material class assigned to each complete support-mesh face"
        ),
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
        "storage_policy": _storage_policy(selected_profile),
        "run_digest": run.digest(),
        "run": run.as_dict(),
    }
    return document


def _storage_policy(output_profile: OutputProfile | str) -> dict[str, Any]:
    """Describe retained artifacts without implying that audit data is automatic."""
    selected = coerce_profile(output_profile)
    requested = profile_spec(selected)
    # The profile catalogue also describes the CDF checkpoint and audit tracks.
    # This generic one-walk executor emits only its manifest, scalar rows, and
    # (for standard/full) the per-model angular spectra.  Keeping the actual
    # emitted set here prevents a manifest from claiming a restart index,
    # stopping record, or Blender payload that another command owns.
    retained = ["sealed_provenance", "standpoint_scalars"]
    if selected in (OutputProfile.STANDARD, OutputProfile.FULL):
        retained.extend(("angular_spectra", "source_law_facts", "body_coupling_inputs"))
    deferred = [name for name in requested.artifact_names if name not in retained]
    spectra = profile_spec(selected).includes("angular_spectra")
    emitted = {
        "sealed_provenance": "<stem>_manifest.json",
        "standpoint_scalars": "<stem>_locations.jsonl",
    }
    if spectra:
        emitted.update(
            {
                "angular_spectra": "<stem>_spectra.npz",
                "source_law_facts": "<stem>_manifest.json:trace_config,illumination_models",
                "body_coupling_inputs": "<stem>_manifest.json + <stem>_spectra.npz",
            }
        )
    return {
        "schema": "aegis.exposure.storage-policy",
        "version": 1,
        "profile": selected.value,
        "retained_artifacts": retained,
        "deferred_artifacts": deferred,
        "emitted_artifacts": emitted,
        "spectra": {
            "retained": spectra,
            "artifact": "angular_spectra" if spectra else None,
            "publication": "<stem>_spectra.npz" if spectra else None,
        },
        "paths": "separate explicit path/evidence exporters; no paths are written by this executor",
        "blender": "separate explicit Blender exporter; this executor never invokes Blender",
        "restart": "single-walk execution restarts from the beginning; CDF checkpointing is a separate command",
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


def _face_source_area_fractions(
    face_source: np.ndarray,
    areas: np.ndarray,
) -> dict[str, float]:
    """Area share decided by each per-face material source."""
    source = np.asarray(face_source)
    area = np.asarray(areas, dtype=np.float64)
    if source.shape != area.shape:
        raise ValueError(f"face_source shape {source.shape} does not match face areas {area.shape}")
    total = float(area.sum())
    if not np.isfinite(total) or total <= 0.0:
        raise ValueError("face areas must have a finite positive total")
    return {Provenance(int(value)).name: float(area[source == value].sum() / total) for value in np.unique(source)}


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


def _trace_rows(prepared: PreparedRun, execution: ExecutionConfig, files: OutputFiles) -> dict[str, float]:
    run = prepared.run
    environment = prepared.environment
    walk = prepared.walk
    picks = prepared.picks
    models = {name: environment.models[name] for name in run.models}
    retain_spectra = profile_spec(execution.output_profile).includes("angular_spectra")
    spectra = {name: np.zeros((picks.size, run.local_cells)) for name in run.models} if retain_spectra else None
    trace_reported_seconds = 0.0
    row_body_serialization_seconds = 0.0
    spectra_write_seconds = 0.0
    standpoints = [(walk.points[i], float(walk.ground_z_m[i]), run.seed + 1000 * int(i)) for i in picks]
    workers = 1 if run.transport_kernel == "drjit" else execution.workers
    with files.rows.open("w") as handle:
        results = environment.trace_standpoints(prepared.tracer, standpoints, models, workers=workers)
        for row_index, result in results:
            row_started = time.perf_counter()
            index = picks[row_index]
            row = _result_row(environment, prepared.coupler, walk, index, result, models)
            if spectra is not None:
                for name in run.models:
                    spectra[name][row_index] = result.rho[name]
            handle.write(json.dumps(row) + "\n")
            handle.flush()
            _print_progress(row_index, picks.size, row, result.seconds)
            row_body_serialization_seconds += time.perf_counter() - row_started
            trace_reported_seconds += float(result.seconds)
        if retain_spectra:
            # The rows are staged and discarded on interruption, so there is
            # no benefit in repeatedly recompressing a growing NPZ.  Keep the
            # exact in-memory order and publish one final archive after all
            # standpoints have completed.
            if picks.size == 0:
                raise RuntimeError("cannot write spectra for an empty standpoint selection")
            if spectra is None:
                raise RuntimeError("spectra retention is enabled but no spectrum buffers were allocated")
            spectra_started = time.perf_counter()
            spectrum_arrays: dict[str, Any] = {
                "index": picks,
                "local_grid": result.local_grid,
                "solid_angle": result.local_solid_angle,
            }
            spectrum_arrays.update({f"rho_{name}": values for name, values in spectra.items()})
            np.savez_compressed(
                files.spectra,
                **spectrum_arrays,
            )
            spectra_write_seconds = time.perf_counter() - spectra_started
    return {
        "trace_reported_seconds": trace_reported_seconds,
        "row_body_serialization_seconds": row_body_serialization_seconds,
        "spectra_write_seconds": spectra_write_seconds,
    }


def _stage_seconds(measured: Mapping[str, float], started: float) -> dict[str, Any]:
    """Return a stable, machine-readable runtime ledger.

    The output-validation/publication phase is filled immediately before the
    manifest is sealed.  ``total_wall_seconds`` covers execution through the
    validation phase.  The final filesystem replace is deliberately kept as
    the manifest commit point, so its tiny syscall interval is not counted in
    the sealed ledger.  These values are diagnostics only and never enter
    :class:`RunConfig` identity or reuse matching.
    """
    names = (
        "scene_preparation_seconds",
        "material_binding_seconds",
        "walk_and_pick_seconds",
        "tracer_coupler_setup_seconds",
        "trace_reported_seconds",
        "row_body_serialization_seconds",
        "spectra_write_seconds",
        "output_validation_publication_seconds",
    )
    ledger = {"schema": "aegis.exposure.stage-seconds", "version": 1}
    ledger.update({name: float(measured.get(name, 0.0)) for name in names})
    ledger["total_wall_seconds"] = float(time.perf_counter() - started)
    return ledger


def _staging_files(files: OutputFiles, generation_id: str) -> OutputFiles:
    """Give one in-progress generation private names in the output directory."""

    def staged(path: pathlib.Path) -> pathlib.Path:
        return path.with_name(f".{path.stem}.{generation_id}{path.suffix}")

    return OutputFiles(staged(files.rows), staged(files.spectra), staged(files.manifest))


def _output_generation(
    generation_id: str,
    staged: OutputFiles,
    published: OutputFiles,
    *,
    profile: OutputProfile | str = OutputProfile.STANDARD,
) -> dict[str, Any]:
    """Seal the numerical artifacts retained by one manifest commit."""
    selected = coerce_profile(profile)
    artifacts = {"locations": _artifact_record(staged.rows, published.rows)}
    if profile_spec(selected).includes("angular_spectra"):
        artifacts["spectra"] = _artifact_record(staged.spectra, published.spectra)
    retained_names = "locations and spectra" if "spectra" in artifacts else "locations"
    return {
        "format_version": 1,
        "id": generation_id,
        "artifacts": artifacts,
        "publication_rule": (
            f"{retained_names} are written under private names, validated, and replaced before this "
            "manifest is replaced as the generation commit record"
        ),
    }


def _artifact_record(staged: pathlib.Path, published: pathlib.Path) -> dict[str, Any]:
    stat = staged.stat()
    return {
        "path": published.name,
        "sha256": _file_sha256(staged),
        "bytes": stat.st_size,
    }


def _write_json(path: pathlib.Path, document: Mapping[str, Any]) -> None:
    """Write and sync a JSON commit record before it becomes visible."""
    with path.open("w", encoding="utf-8") as stream:
        json.dump(document, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _validate_generation(
    manifest: dict[str, Any],
    run: RunConfig,
    staged: OutputFiles,
    *,
    profile: OutputProfile | str = OutputProfile.STANDARD,
) -> None:
    """Refuse to publish a generation whose staged files disagree."""
    from semantic_twin.exposure.reuse import complete_output, same_output_generation

    if not complete_output(manifest, run, staged.rows, staged.spectra, profile=profile):
        raise RuntimeError("staged exposure generation is incomplete or internally inconsistent")
    if not same_output_generation(
        manifest,
        staged.rows,
        staged.spectra,
        require_published_names=False,
        profile=profile,
    ):
        raise RuntimeError("staged exposure generation differs from its artifact seal")


def _publish_generation(
    staged: OutputFiles,
    published: OutputFiles,
    *,
    profile: OutputProfile | str = OutputProfile.STANDARD,
) -> None:
    """Publish data first and the manifest commit record last."""
    selected = coerce_profile(profile)
    os.replace(staged.rows, published.rows)
    if profile_spec(selected).includes("angular_spectra"):
        os.replace(staged.spectra, published.spectra)
    else:
        # A minimal rerun must not leave a spectrum from a previous standard
        # generation under the same stem.  The new manifest also omits the
        # artifact, so a stale file would be misleading to users inspecting
        # the output directory.
        published.spectra.unlink(missing_ok=True)
    os.replace(staged.manifest, published.manifest)
    try:
        directory = os.open(published.manifest.parent, os.O_RDONLY)
    except OSError:
        return
    try:
        try:
            os.fsync(directory)
        except OSError:
            pass
    finally:
        os.close(directory)


def _remove_staging_files(files: OutputFiles) -> None:
    for path in (files.rows, files.spectra, files.manifest):
        path.unlink(missing_ok=True)


def _result_row(
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
    names = tuple(models)
    couple_many = getattr(coupler, "couple_many", None)
    if callable(couple_many):
        exposures = couple_many(
            result.local_grid,
            np.stack([result.rho[name] for name in names]),
            result.local_solid_angle,
            environment.reference_s0_w_m2,
        )
    else:
        exposures = tuple(
            coupler.couple(
                result.local_grid,
                result.rho[name],
                result.local_solid_angle,
                environment.reference_s0_w_m2,
            )
            for name in names
        )
    if len(exposures) != len(names):
        raise RuntimeError(f"body coupler returned {len(exposures)} results for {len(names)} illumination models")
    for name, exposure in zip(names, exposures, strict=True):
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
