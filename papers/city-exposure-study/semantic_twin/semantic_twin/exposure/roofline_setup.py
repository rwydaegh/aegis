"""Strict preparation and preflight for production roofline body campaigns."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal

import numpy as np

from ..cohort import (
    COMPARABLE_COHORT,
    campaign_readiness,
    default_manifest_path,
    load_manifest,
    validate_study_membership,
)
from ..illumination import build_source_set, silhouette
from ..runconfig import NextEventConfig, RunConfig
from ..transport.device_tracer import DeviceEscapeTracer
from ..transport.next_event import NextEventEstimator
from ..transport.specular import DEFAULT_SPECULAR_CANDIDATE_BUDGET, OneBounceSpecularTransport
from ..transport.specular_sampling import SampledOneBounceSpecularEstimator
from ..transport.tracer import SbrTracer
from ..walk.model import PANORAMA_LINKS, STREET_ROUTE
from ..walk.route import load_admitted_stations
from .coupler import BodyCoupler
from .execution import LegacyReplay, StudyEnvironment, _bind_materials, _build_walk, _prepare_scene, _trace_config
from .roofline_campaign import (
    PreparedRooflineCampaign,
    RooflineCampaignConfig,
    campaign_identity,
    seal_coupler_provenance,
    seal_transport_provenance,
)

JSON_SUFFIX = ".json"
COHORT_MANIFEST_FILENAME = "city_cohort_manifest.json"


def _validate_positive_finite(value: float, message: str) -> None:
    if not np.isfinite(value) or value <= 0.0:
        raise ValueError(message)


def _validate_source_real_fields(source: RooflineSourcePreparation) -> None:
    _validate_positive_finite(
        source.curve_resolution_m,
        "curve_resolution_m must be positive and finite",
    )
    if not np.isfinite(source.top_edge_tolerance_m) or source.top_edge_tolerance_m < 0.0:
        raise ValueError("top_edge_tolerance_m must be finite and nonnegative")
    for name in ("crop_area_m2", "density_per_m2", "eirp_w", "expected_count"):
        value = getattr(source, name)
        if value is not None and (not np.isfinite(value) or value <= 0.0):
            raise ValueError(f"{name} must be positive and finite when supplied")


def _validate_source_candidate_fields(source: RooflineSourcePreparation) -> None:
    if any(
        not isinstance(value, int) or isinstance(value, bool) or value < 1
        for value in (source.specular_candidate_budget, source.specular_candidate_chunk)
    ):
        raise ValueError("specular candidate budget and chunk must be positive")


def _validate_source_specular_order(source: RooflineSourcePreparation) -> None:
    if source.specular_order not in (0, 1):
        raise ValueError("specular_order must be zero or one")


def _validate_source_refinement_fields(source: RooflineSourcePreparation) -> None:
    if not np.isfinite(source.specular_refinement_relative_tolerance) or not (
        0.0 < source.specular_refinement_relative_tolerance < 1.0
    ):
        raise ValueError("specular_refinement_relative_tolerance must lie strictly between zero and one")


def _validate_source_suffix_fields(source: RooflineSourcePreparation) -> None:
    if source.specular_suffix_mode not in ("exact", "sampled", "disabled"):
        raise ValueError("specular_suffix_mode must be exact, sampled, or disabled")


def _validate_source_sampled_fields(source: RooflineSourcePreparation) -> None:
    if (
        not isinstance(source.sampled_specular_samples, int)
        or isinstance(source.sampled_specular_samples, bool)
        or source.sampled_specular_samples < 1
    ):
        raise ValueError("sampled_specular_samples must be positive")
    if (
        not isinstance(source.sampled_specular_seed_offset, int)
        or isinstance(source.sampled_specular_seed_offset, bool)
        or source.sampled_specular_seed_offset < 0
    ):
        raise ValueError("sampled_specular_seed_offset must be nonnegative")


@dataclass(frozen=True)
class RooflineSourcePreparation:
    """Source and deterministic specular controls not carried by RunConfig."""

    curve_resolution_m: float = 1.0e-4
    top_edge_tolerance_m: float = 0.25
    crop_area_m2: float | None = None
    density_per_m2: float | None = None
    eirp_w: float | None = None
    expected_count: float | None = None
    specular_order: int = 1
    specular_candidate_budget: int = DEFAULT_SPECULAR_CANDIDATE_BUDGET
    specular_candidate_chunk: int = 262_144
    specular_refinement_relative_tolerance: float = 0.02
    specular_suffix_mode: Literal["exact", "sampled", "disabled"] = "exact"
    sampled_specular_samples: int = 1
    sampled_specular_seed_offset: int = 2000
    additional_input_paths: tuple[Path, ...] = ()

    def __post_init__(self) -> None:
        _validate_source_real_fields(self)
        _validate_source_specular_order(self)
        _validate_source_candidate_fields(self)
        _validate_source_refinement_fields(self)
        _validate_source_suffix_fields(self)
        _validate_source_sampled_fields(self)
        object.__setattr__(self, "additional_input_paths", tuple(Path(path) for path in self.additional_input_paths))


def _normalize_setup_paths(setup: RooflineSetupConfig) -> Path:
    root = Path(setup.study_root).resolve()
    object.__setattr__(setup, "study_root", root)
    if setup.setup_file is not None:
        object.__setattr__(setup, "setup_file", Path(setup.setup_file).resolve())
    return root


def _validate_setup_identity(setup: RooflineSetupConfig, root: Path) -> None:
    if setup.run.site != setup.campaign.site:
        raise ValueError("run and campaign site must match")
    output = setup.campaign.output_dir.resolve()
    output_root = root / "outputs"
    if output == output_root or not output.is_relative_to(output_root):
        raise ValueError("campaign output_dir must be a dedicated directory below the active study outputs root")
    if setup.run.materials != setup.campaign.material_mode:
        raise ValueError("run materials and campaign material_mode must match")


def _validate_setup_run_contract(setup: RooflineSetupConfig) -> None:
    run = setup.run
    if run.law != "roofline" or run.estimator != "next_event" or run.next_event is None:
        raise ValueError("roofline setup requires roofline/next_event RunConfig with NextEventConfig")
    if run.next_event.builders != 1 or run.next_event.held_out != 1:
        raise ValueError(
            "campaign preparation uses every declared route point; builders=held_out=1 are locked legacy sentinels"
        )
    if run.walk != "route" or run.locations != 0:
        raise ValueError("roofline setup requires the complete declared route and locations=0")
    if run.transport_kernel == "drjit" and run.variant not in ("llvm_ad_rgb", "cuda_ad_rgb"):
        raise ValueError("resident device next-event requires llvm_ad_rgb or cuda_ad_rgb")


def _validate_setup_specular_contract(setup: RooflineSetupConfig) -> None:
    source = setup.source
    campaign = setup.campaign
    run = setup.run
    if source.specular_order == 0 and campaign.specular_acceptance != "omitted_diagnostic":
        raise ValueError("specular_order=0 is only valid for an explicitly omitted-specular diagnostic")
    if source.specular_suffix_mode == "sampled" and source.specular_order != 1:
        raise ValueError("sampled specular suffix requires specular_order=1")
    if source.specular_order == 1 and campaign.specular_acceptance == "omitted_diagnostic":
        raise ValueError("omitted-specular diagnostics require specular_order=0")
    combined_policy = "adaptive_all_specular_sampled_mixed_order_1"
    if campaign.specular_acceptance == combined_policy and source.specular_suffix_mode != "sampled":
        raise ValueError("combined sampled-specular acceptance requires specular_suffix_mode=sampled")
    if campaign.specular_acceptance == combined_policy and run.max_bounces < 2:
        raise ValueError("combined sampled-specular acceptance requires max_bounces>=2")
    if campaign.specular_acceptance == "exact_complete" and source.specular_suffix_mode != "exact":
        raise ValueError("exact-complete acceptance requires specular_suffix_mode=exact")
    if run.transport_kernel == "drjit" and source.specular_order == 1 and source.specular_suffix_mode != "sampled":
        raise ValueError("resident device order-one transport requires specular_suffix_mode=sampled")


def _setup_manifest(setup: RooflineSetupConfig) -> dict[str, Any]:
    manifest_path = setup.study_root / "config" / COHORT_MANIFEST_FILENAME
    if not manifest_path.is_file():
        if setup.campaign.cohort == COMPARABLE_COHORT:
            raise FileNotFoundError(f"comparable campaign manifest is missing: {manifest_path}")
        manifest_path = default_manifest_path()
    return load_manifest(manifest_path)


def _validate_comparable_setup(setup: RooflineSetupConfig, manifest: dict[str, Any], entry: dict[str, Any]) -> None:
    contract_crop_m = int(manifest["contract"]["crop_m"])
    if setup.run.crop_m != contract_crop_m:
        raise ValueError(f"comparable cohort requires the manifest crop_m={contract_crop_m}")
    route_radius_m = float(manifest["contract"]["route_radius_m"])
    if setup.run.walk_radius_m != route_radius_m:
        raise ValueError(f"comparable cohort requires the manifest walk_radius_m={route_radius_m}")
    if setup.run.materials == "atlas":
        declared_atlas = (setup.study_root / entry["materials"]["atlas_npz"]).resolve()
        selected_atlas = declared_atlas if setup.run.atlas_npz is None else Path(setup.run.atlas_npz).resolve()
        if selected_atlas != declared_atlas:
            raise ValueError("comparable primary run must use the atlas declared by its cohort manifest")
    readiness = campaign_readiness(
        setup.run.site,
        setup.campaign.cohort,
        setup.campaign.route_contract or "",
        setup.campaign.material_mode,
        document=manifest,
        root=setup.study_root,
    )
    if not readiness.ready:
        raise ValueError(f"comparable campaign inputs are not ready: {readiness.as_dict()}")


def _validate_setup_cohort_contract(setup: RooflineSetupConfig) -> None:
    manifest = _setup_manifest(setup)
    entry = validate_study_membership(setup.run.site, setup.campaign.cohort, manifest)
    if setup.campaign.cohort == "primary_semantic_route":
        if setup.run.walk_path != "links":
            raise ValueError("legacy primary cohort requires a panorama-link route")
    elif setup.run.walk_path != "street":
        raise ValueError(f"cohort {setup.campaign.cohort!r} requires a declared street route")
    if setup.campaign.cohort == COMPARABLE_COHORT:
        _validate_comparable_setup(setup, manifest, entry)
    if setup.run.next_event.drop_clutter:
        raise ValueError(
            "drop_clutter is not silently approximated here; provide a sealed support-face clutter mask first"
        )


def _validate_setup_reference_contract(setup: RooflineSetupConfig) -> None:
    if setup.campaign.reference_mode != "physical":
        return
    if setup.source.eirp_w is None:
        raise ValueError("physical reference mode requires a positive source eirp_w")
    if setup.source.expected_count is None and setup.source.density_per_m2 is None:
        raise ValueError("physical reference mode requires expected_count or density_per_m2")


@dataclass(frozen=True)
class RooflineSetupConfig:
    """One prepared run, including the root whose inputs must be staged."""

    study_root: Path
    run: RunConfig
    campaign: RooflineCampaignConfig
    source: RooflineSourcePreparation = field(default_factory=RooflineSourcePreparation)
    setup_file: Path | None = None

    def __post_init__(self) -> None:
        root = _normalize_setup_paths(self)
        _validate_setup_identity(self, root)
        _validate_setup_run_contract(self)
        _validate_setup_specular_contract(self)
        _validate_setup_cohort_contract(self)
        _validate_setup_reference_contract(self)


@dataclass(frozen=True)
class PreparationBackend:
    """Replaceable construction seams used by deterministic preflight tests."""

    prepare_scene: Callable[[RunConfig, StudyEnvironment], Any]
    bind_materials: Callable[[RunConfig, Any, StudyEnvironment], Any]
    build_walk: Callable[[RunConfig, Any, StudyEnvironment], Any]
    trace_config: Callable[[RunConfig, StudyEnvironment], Any]
    build_sources: Callable[..., Any] = build_source_set
    silhouette: Callable[..., Any] = silhouette
    tracer_type: Any = SbrTracer
    device_tracer_type: Any = DeviceEscapeTracer
    specular_type: Any = OneBounceSpecularTransport
    estimator_type: Any = NextEventEstimator
    coupler_type: Any = BodyCoupler


def default_preparation_backend() -> PreparationBackend:
    return PreparationBackend(
        prepare_scene=lambda run, environment: _prepare_scene(run, LegacyReplay(), environment),
        bind_materials=lambda run, scene, environment: _bind_materials(run, scene, environment),
        build_walk=lambda run, scene, environment: _build_walk(run, LegacyReplay(), scene, environment),
        trace_config=_trace_config,
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _array_sha256(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(str(array.shape).encode("ascii"))
    digest.update(array.tobytes())
    return digest.hexdigest()


def _input_record(path: Path, root: Path) -> dict[str, Any]:
    resolved = path.resolve()
    try:
        name = str(resolved.relative_to(root))
    except ValueError:
        name = str(resolved)
    return {"path": name, "sha256": _sha256(resolved), "bytes": resolved.stat().st_size}


def _add_source_with_sidecar(candidates: set[Path], selected: Path | None) -> None:
    if selected is not None:
        candidates.update((Path(selected), Path(selected).with_suffix(JSON_SUFFIX)))


def _add_material_input_paths(
    setup: RooflineSetupConfig,
    environment: StudyEnvironment,
    candidates: set[Path],
) -> None:
    run = setup.run
    if run.materials == "atlas":
        selected = Path(run.atlas_npz) if run.atlas_npz else environment.site_surface_atlas(run.site, run.crop_m)
        _add_source_with_sidecar(candidates, selected)
    elif run.materials.startswith("walk"):
        candidates.add(Path(environment.semantics))
        selected = Path(run.walk_npz) if run.walk_npz else environment.site_walk_semantics(run.site, run.crop_m)
        _add_source_with_sidecar(candidates, selected)
    elif run.materials == "semantic":
        candidates.add(Path(environment.semantics))
        fishnet = environment.site_fishnet(run.site)
        if fishnet is not None:
            fishnet_root, fishnet_source = fishnet
            candidates.add(Path(fishnet_source))
            candidates.update(
                path
                for path in (
                    Path(fishnet_root) / f"fishnet_manifest{JSON_SUFFIX}",
                    Path(fishnet_root) / f"site_fishnet_manifest{JSON_SUFFIX}",
                )
                if path.is_file()
            )
            candidates.update(Path(fishnet_root).glob("*_fishnet.npz"))


def _add_route_input_paths(root: Path, run: RunConfig, candidates: set[Path]) -> None:
    site_config = root / "config" / f"{run.site}{JSON_SUFFIX}"
    if site_config.is_file():
        candidates.add(site_config)
    route_report = root / "outputs" / "site_semantics" / run.site / f"walk_semantic_{run.crop_m}m{JSON_SUFFIX}"
    if route_report.is_file():
        candidates.add(route_report)
        for station in load_admitted_stations(run.site, root=root):
            candidates.add(Path(station["metadata_path"]))
    for path in (
        root / "outputs" / "city_screening" / f"screening{JSON_SUFFIX}",
        root / "outputs" / "walk_korenmarkt_saturation" / f"walk_selection{JSON_SUFFIX}",
    ):
        if path.is_file():
            candidates.add(path)


def _add_declared_input_paths(setup: RooflineSetupConfig, root: Path, candidates: set[Path]) -> None:
    for path in setup.source.additional_input_paths:
        resolved = path if path.is_absolute() else root / path
        if not resolved.is_file():
            raise FileNotFoundError(f"declared campaign input does not exist: {resolved}")
        candidates.add(resolved)


def _automatic_input_paths(
    setup: RooflineSetupConfig,
    environment: StudyEnvironment,
    scene: Any,
) -> tuple[Path, ...]:
    root = setup.study_root
    run = setup.run
    candidates: set[Path] = {Path(scene.mesh), Path(environment.phantom)}
    if setup.setup_file is not None:
        candidates.add(setup.setup_file)
    mesh_sidecar = Path(scene.mesh).with_suffix(JSON_SUFFIX)
    if mesh_sidecar.is_file():
        candidates.add(mesh_sidecar)
    data_root = Path(environment.phantom).parent
    candidates.update(path for path in (data_root / "itis_v5.db", data_root / "phantoms.yaml") if path.is_file())
    config_root = Path(environment.material_config)
    candidates.update(
        path
        for path in (
            config_root / f"itu_p2040_4{JSON_SUFFIX}",
            config_root / f"surface_roughness{JSON_SUFFIX}",
        )
        if path.is_file()
    )
    _add_route_input_paths(root, run, candidates)
    if setup.campaign.cohort == COMPARABLE_COHORT:
        manifest_path = root / "config" / COHORT_MANIFEST_FILENAME
        readiness = campaign_readiness(
            run.site,
            setup.campaign.cohort,
            setup.campaign.route_contract or "",
            setup.campaign.material_mode,
            manifest_path=manifest_path,
            root=root,
        )
        candidates.add(manifest_path)
        candidates.update(root / relative for relative in readiness.route.evidence)
        candidates.update(root / relative for relative in readiness.materials.evidence)
    elif run.walk_path == "street":
        candidates.update((root / "data" / "street_routes").glob(f"{run.site}_*{JSON_SUFFIX}"))
    _add_material_input_paths(setup, environment, candidates)
    _add_declared_input_paths(setup, root, candidates)
    missing = sorted(str(path) for path in candidates if not path.is_file())
    if missing:
        raise FileNotFoundError(f"required campaign inputs are missing: {missing}")
    return tuple(sorted((path.resolve() for path in candidates), key=str))


def _material_provenance(run: RunConfig, material: Any) -> dict[str, Any]:
    table = material.table.as_dict() if hasattr(material.table, "as_dict") else {"class": type(material.table).__name__}
    return {
        "material_mode": run.materials,
        "binding": material.provenance,
        "surface_table": table,
        "face_class_sha256": _array_sha256(np.asarray(material.face_class)),
        "face_source_sha256": _array_sha256(np.asarray(material.face_source)),
        "atlas_material_present": material.atlas_material is not None,
    }


def prepare_roofline_campaign(
    setup: RooflineSetupConfig,
    environment: StudyEnvironment,
    *,
    backend: PreparationBackend | None = None,
) -> PreparedRooflineCampaign:
    """Build the full route, exact curve, transport, body, and sealed identity."""
    selected = default_preparation_backend() if backend is None else backend
    scene = selected.prepare_scene(setup.run, environment)
    material = selected.bind_materials(setup.run, scene, environment)
    route_key = os.environ.pop("GOOGLE_API_KEY", None) if setup.run.walk_path == "street" else None
    try:
        walk = selected.build_walk(setup.run, scene, environment)
    finally:
        if route_key is not None:
            os.environ["GOOGLE_API_KEY"] = route_key
    expected_kind = PANORAMA_LINKS if setup.campaign.cohort == "primary_semantic_route" else STREET_ROUTE
    if walk.kind != expected_kind:
        raise ValueError(f"prepared walk kind {walk.kind!r} does not match cohort route {expected_kind!r}")
    if setup.campaign.cohort == COMPARABLE_COHORT:
        readiness = campaign_readiness(
            setup.run.site,
            setup.campaign.cohort,
            setup.campaign.route_contract or "",
            setup.campaign.material_mode,
            manifest_path=setup.study_root / "config" / COHORT_MANIFEST_FILENAME,
            root=setup.study_root,
        )
        actual_cache = walk.provenance.get("street_route", {}).get("cache_file")
        if actual_cache != readiness.route.expected_cache:
            raise ValueError("prepared street route does not use the manifest's exact registered endpoint cache")
    if len(walk) == 0:
        raise ValueError("prepared route is empty")
    next_event = setup.run.next_event
    if next_event is None:
        raise AssertionError("NextEventConfig was validated before preparation")
    crop_area = setup.source.crop_area_m2
    if crop_area is None:
        crop_area = float(np.pi * setup.run.crop_m**2)
    sources = selected.build_sources(
        scene.geometry,
        np.asarray(walk.points, dtype=np.float64),
        selected.silhouette,
        azimuths=next_event.azimuths,
        elevations=next_event.elevations,
        cell_m=next_event.cell_m,
        dims=next_event.dims,
        site_lift_m=next_event.site_lift_m,
        crop_area_m2=crop_area,
        density_per_m2=setup.source.density_per_m2,
        eirp_w=setup.source.eirp_w,
        expected_count=setup.source.expected_count,
        curve_resolution_m=setup.source.curve_resolution_m,
        top_edge_tolerance_m=setup.source.top_edge_tolerance_m,
        source_measure_rule=setup.campaign.source_measure_rule,
    )
    trace_config = selected.trace_config(setup.run, environment)
    tracer_options = {} if material.atlas_material is None else {"atlas_material": material.atlas_material}
    tracer_type = selected.device_tracer_type if setup.run.transport_kernel == "drjit" else selected.tracer_type
    tracer = tracer_type(
        scene.geometry,
        material.face_class,
        material.table.permittivity,
        material.table.rms_height_m,
        trace_config,
        **tracer_options,
    )
    specular = None
    if setup.source.specular_order == 1:
        specular = selected.specular_type(
            tracer,
            candidate_chunk=setup.source.specular_candidate_chunk,
            candidate_budget=setup.source.specular_candidate_budget,
        )
    estimator = selected.estimator_type(
        tracer=tracer,
        geometry=scene.geometry,
        sources=sources,
        samples=next_event.connections,
        max_order=setup.run.max_bounces,
        specular_order=setup.source.specular_order,
        specular_candidate_budget=setup.source.specular_candidate_budget,
        specular_transport=specular,
        specular_refinement_relative_tolerance=setup.source.specular_refinement_relative_tolerance,
        specular_suffix_mode=setup.source.specular_suffix_mode,
        sampled_specular_samples=setup.source.sampled_specular_samples,
        sampled_specular_seed_offset=setup.source.sampled_specular_seed_offset,
        deterministic_cache_size=max(8, 2 * len(walk) + 4),
        diagnostic_models={},
    )
    coupler = selected.coupler_type(
        environment.phantom,
        setup.run.frequency_hz,
        level=2,
        body_mass_kg=environment.phantom_mass_kg,
    )
    input_paths = _automatic_input_paths(setup, environment, scene)
    input_records = [_input_record(path, setup.study_root) for path in input_paths]
    input_provenance = {
        "staging_contract": "explicit_runtime_data_and_run_config_files_sha256_v1",
        "code_snapshot_contract": "separate immutable staged code tree; source files are not runtime-data inputs",
        "source_standpoint_contract": {
            "rule": "every point of the full declared walk builds the fixed facade-tip curve",
            "standpoints": len(walk),
            "legacy_builders_field": next_event.builders,
            "legacy_held_out_field": next_event.held_out,
            "random_builder_evaluation_split": False,
        },
        "files": input_records,
        "file_count": len(input_records),
        "bytes": sum(record["bytes"] for record in input_records),
        "mesh": _input_record(Path(scene.mesh), setup.study_root)["path"],
        "ground_datum": scene.datum_provenance,
    }
    return PreparedRooflineCampaign(
        config=setup.campaign,
        walk=walk,
        estimator=estimator,
        coupler=coupler,
        source_provenance=sources.source_provenance(),
        material_provenance=_material_provenance(setup.run, material),
        input_provenance=input_provenance,
        transport_provenance=seal_transport_provenance(estimator),
        coupler_provenance=seal_coupler_provenance(coupler),
    )


def _preflight_specular_work(estimator: Any, tracer: Any, maximum_order: int) -> tuple[dict[str, Any], dict[str, Any]]:
    specular_transport = estimator.specular_transport
    if specular_transport is None:
        return (
            {
                "enabled": False,
                "reason": "specular_order=0 was explicitly selected",
                "support_complete": False,
            },
            {
                "enabled": False,
                "reason": "adaptive specular transport requires specular_order=1",
            },
        )
    exact_work = specular_transport.work_estimate(
        sources=len(estimator.sources),
        rays=tracer.config.rays,
        samples=estimator.samples,
        max_bounces=maximum_order,
    ).as_dict()
    face_count = int(specular_transport.surfaces.triangles.shape[0])
    source_count = len(estimator.sources)
    initial_faces = min(face_count, int(estimator.visible_face_candidates.sample_levels[0]))
    initial_sources = min(source_count, int(estimator.source_quadrature.strata_levels[0]))
    initial_work_bound = initial_faces + initial_faces * initial_sources
    adaptive_enabled = bool(
        estimator.specular_order == 1
        and getattr(estimator.sources, "curve", None) is not None
        and face_count > 0
        and source_count > 0
        and estimator.specular_candidate_budget > initial_work_bound
    )
    adaptive = {
        "enabled": adaptive_enabled,
        "reason": (
            None
            if adaptive_enabled
            else "requires curve-backed sources, nonempty finite surfaces, and budget beyond the initial screen"
        ),
        "initial_work_upper_bound": initial_work_bound,
        "candidate_budget": int(estimator.specular_candidate_budget),
        "relative_tolerance": float(estimator.specular_refinement_relative_tolerance),
        "final_gate": "every standpoint must stop at relative_tolerance_reached",
        "support_complete": False,
    }
    return exact_work, adaptive


def _preflight_sampled_suffix(
    estimator: Any,
    tracer: Any,
    maximum_order: int,
    specular_transport: Any,
) -> dict[str, Any]:
    if specular_transport is None or getattr(estimator, "specular_suffix_mode", "exact") != "sampled":
        return {
            "enabled": False,
            "reason": "requires opt-in sampled suffix mode with order-one finite surfaces",
        }
    sampled_estimator = SampledOneBounceSpecularEstimator(specular_transport, estimator.sources)
    sampled_identity = sampled_estimator.sampling_identity()
    sampled_trials_bound = (
        int(tracer.config.rays) * max(int(maximum_order) - 1, 0) * int(estimator.sampled_specular_samples)
    )
    sampled = {
        "enabled": bool(
            sampled_estimator.ready
            and sampled_identity["surface_support_complete"]
            and sampled_identity["source_support"] == sampled_identity["source_count"]
        ),
        "samples_per_diffuse_vertex": int(estimator.sampled_specular_samples),
        "seed_offset": int(estimator.sampled_specular_seed_offset),
        "proposal_identity": sampled_identity,
        "trial_upper_bound_per_standpoint": sampled_trials_bound,
        "solver_call_upper_bound_per_standpoint": int(
            np.ceil(sampled_trials_bound / max(int(specular_transport.candidate_chunk), 1))
        ),
        "uncertainty_scope": (
            "proposal standard errors are conditional on traced diffuse vertices; "
            "campaign replicas control total, body, and CDF uncertainty"
        ),
    }
    sampled["reason"] = None if sampled["enabled"] else "sampled proposal lacks complete finite support"
    return sampled


def _preflight_readiness(
    policy: str,
    estimator: Any,
    exact_work: dict[str, Any],
    adaptive: dict[str, Any],
    sampled: dict[str, Any],
) -> tuple[bool, str | None]:
    if policy == "exact_complete":
        return bool(exact_work["enabled"]), exact_work.get("reason")
    if policy == "adaptive_converged":
        return bool(adaptive["enabled"]), adaptive.get("reason")
    if policy == "adaptive_all_specular_sampled_mixed_order_1":
        ready = bool(adaptive["enabled"] and sampled["enabled"])
        return ready, adaptive.get("reason") or sampled.get("reason")
    ready = estimator.specular_order == 0
    return ready, None if ready else "omitted diagnostic requires specular_order=0"


def _checkpoint_storage_bound(
    prepared: PreparedRooflineCampaign,
    points: int,
    surfaces: int,
) -> tuple[dict[str, Any], bool, str | None]:
    config = prepared.config
    retained_field_snapshots = len(set((*config.convergence_looks, len(config.planned_seeds))))
    field_bytes = points * surfaces * np.dtype(np.float64).itemsize
    scalar_bytes = points * (len(config.planned_seeds)) * (4 + 4 * 6 + 5 + 7 + 2) * np.dtype(np.float64).itemsize
    minimum_free_bytes = max(64 * 1024**2, 2 * (field_bytes * retained_field_snapshots + scalar_bytes))
    output = Path(config.output_dir).resolve()
    existing_parent = output
    while not existing_parent.exists() and existing_parent != existing_parent.parent:
        existing_parent = existing_parent.parent
    disk = shutil.disk_usage(existing_parent)
    output_writable = os.access(existing_parent, os.W_OK | os.X_OK)
    storage_ready = output_writable and disk.free >= minimum_free_bytes
    storage_reason = None
    if not storage_ready:
        storage_reason = (
            f"output parent {existing_parent} is not writable"
            if not output_writable
            else f"free disk {disk.free} bytes is below conservative minimum {minimum_free_bytes} bytes"
        )
    bound = {
        "body_field_bytes_each": field_bytes,
        "retained_body_field_snapshots": retained_field_snapshots,
        "body_field_bytes_total_uncompressed": field_bytes * retained_field_snapshots,
        "scalar_shard_bytes_total_uncompressed": scalar_bytes,
        "minimum_free_bytes_with_headroom": minimum_free_bytes,
        "existing_output_parent": str(existing_parent),
        "output_parent_writable": output_writable,
        "free_bytes": disk.free,
        "ready": storage_ready,
        "rule": "one cumulative field at each convergence look and at the current/final prefix",
    }
    return bound, storage_ready, storage_reason


def preflight_report(prepared: PreparedRooflineCampaign) -> dict[str, Any]:
    """Return the dry-run identity, work bound, and exact staging manifest."""
    config = prepared.config
    estimator = prepared.estimator
    tracer = estimator.tracer
    maximum_order = tracer.config.max_bounces if estimator.max_order is None else estimator.max_order
    specular_transport = estimator.specular_transport
    exact_work, adaptive = _preflight_specular_work(estimator, tracer, maximum_order)
    policy = config.specular_acceptance
    sampled = _preflight_sampled_suffix(estimator, tracer, maximum_order, specular_transport)
    ready, refusal_reason = _preflight_readiness(policy, estimator, exact_work, adaptive, sampled)
    points = len(prepared.walk)
    deterministic_cache_capacity = int(getattr(estimator, "deterministic_cache_size", 8))
    surfaces = int(np.asarray(prepared.coupler.body.areas).size)
    storage_bound, storage_ready, storage_reason = _checkpoint_storage_bound(prepared, points, surfaces)
    if storage_reason is not None:
        refusal_reason = storage_reason if refusal_reason is None else f"{refusal_reason}; {storage_reason}"
    ready = ready and storage_ready
    return {
        "ready_to_trace": ready,
        "refusal_reason": refusal_reason,
        "campaign_identity": campaign_identity(prepared),
        "site": config.site,
        "cohort": config.cohort,
        "material_mode": config.material_mode,
        "material_evidence": prepared.material_provenance,
        "walk": {
            **prepared.walk.identity(),
            "point_kind_counts": dict(Counter(prepared.walk.provenance["point_kind"])),
            "route_length_m": float(np.sum(prepared.walk.step_m, dtype=np.float64)),
        },
        "sources": {
            "sites": len(estimator.sources),
            "support_length_m": estimator.sources.support_length_m,
            "crop_area_m2": estimator.sources.crop_area_m2,
            "source_hash_sha256": estimator.sources.source_hash,
        },
        "specular_readiness": {
            "acceptance_policy": policy,
            "exact_complete": exact_work,
            "adaptive_numerical": adaptive,
            "sampled_mixed_suffix_order_1": sampled,
            "omitted_diagnostic": {
                "enabled": estimator.specular_order == 0,
                "publication_total": False,
            },
        },
        "specular_work": exact_work,
        "deterministic_cache_bound": {
            "capacity_entries": deterministic_cache_capacity,
            "required_entries_for_two_terms_per_route_point_plus_margin": 2 * points + 4,
            "ready": deterministic_cache_capacity >= 2 * points + 4,
            "rule": "direct and deterministic all-specular fields only; sampled suffixes remain replica-specific",
        },
        "replica_invariant_body_cache_bound": {
            "capacity_entries": 2 * points,
            "maximum_bytes": 2 * points * (surfaces + 6) * np.dtype(np.float64).itemsize,
            "rule": "one direct and one deterministic all-specular Sab field per standpoint",
        },
        "checkpoint_storage_bound": storage_bound,
        "staged_inputs": prepared.input_provenance,
        "output_dir": str(config.output_dir),
    }


def _path(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def load_roofline_setup(path: Path, *, study_root: Path | None = None) -> RooflineSetupConfig:
    """Load one strict JSON preparation configuration."""
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    root = Path(document.get("study_root", study_root or Path(path).resolve().parents[1])).resolve()
    if study_root is not None:
        root = Path(study_root).resolve()
    run_data = dict(document["run"])
    for name in ("atlas_npz", "walk_npz"):
        if run_data.get(name) is not None:
            run_data[name] = str(_path(root, run_data[name]))
    run_data["models"] = tuple(run_data.get("models", ("isotropic",)))
    next_event_data = run_data.get("next_event")
    run_data["next_event"] = None if next_event_data is None else NextEventConfig(**next_event_data)
    run = RunConfig(**run_data)
    campaign_data = dict(document["campaign"])
    campaign_data["output_dir"] = _path(root, campaign_data["output_dir"])
    campaign_data["planned_seeds"] = tuple(campaign_data["planned_seeds"])
    campaign_data["convergence_looks"] = tuple(campaign_data.get("convergence_looks", ()))
    campaign = RooflineCampaignConfig(**campaign_data)
    source_data = dict(document.get("source", {}))
    source_data["additional_input_paths"] = tuple(
        _path(root, item) for item in source_data.get("additional_input_paths", ())
    )
    source = RooflineSourcePreparation(**source_data)
    return RooflineSetupConfig(root, run, campaign, source, setup_file=Path(path))


def write_preflight(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
