"""Next-event exposure against explicit rooftop source points."""

from __future__ import annotations

import json
import pathlib
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from semantic_twin import paths
from semantic_twin.illumination import ISOTROPIC, ROOFTOP, SITE_LIFT_M, build_source_set, silhouette
from semantic_twin.materials import FINISH_ONLY_RULE, classify_faces, clutter_triangles, load_table
from semantic_twin.paths import site_mesh
from semantic_twin.propagation.geometry import MitsubaGeometry
from semantic_twin.transport import SbrTracer, TraceConfig
from semantic_twin.transport.device_tracer import DeviceEscapeTracer
from semantic_twin.transport.next_event import NextEventEstimator
from semantic_twin.walk import build_walk, measure_ground_datum, site_walk


@dataclass(frozen=True)
class NextEventStudyConfig:
    sites: tuple[str, ...] = ("korenmarkt", "brussels_grandplace")
    crop_m: int = 250
    rays: int = 200_000
    builders: int = 128
    held_out: int = 16
    azimuths: int = 1440
    elevations: int = 600
    cell_m: float = 1.0
    dims: int = 3
    curve_resolution_m: float = 1.0e-4
    top_edge_tolerance_m: float = 0.25
    crop_area_m2: float | None = None
    density_per_m2: float | None = None
    eirp_w: float | None = None
    site_lift_m: float = SITE_LIFT_M
    connections: int = 1
    frequency_hz: float = 15.0e9
    max_bounces: int = 3
    walk_radius_m: float = 90.0
    head_height_m: float = 1.5
    walk: str = "route"
    walk_path: str = "links"
    walk_stride_m: float = 6.0
    drop_clutter: bool = False
    seed: int = 7
    variant: str = "llvm_ad_rgb"
    transport_kernel: str = "numpy"
    launch_sampling: str = "iid"
    specular_order: int = 1
    tag: str = "next_event"
    root: pathlib.Path = field(default_factory=paths.root)

    def __post_init__(self) -> None:
        if self.transport_kernel not in ("numpy", "drjit"):
            raise ValueError("transport_kernel must be 'numpy' or 'drjit'")
        if self.launch_sampling not in ("iid", "rotated_fibonacci"):
            raise ValueError("launch_sampling must be 'iid' or 'rotated_fibonacci'")
        if self.specular_order not in (0, 1):
            raise ValueError("specular_order must be zero or one")
        if self.transport_kernel == "drjit":
            if self.variant not in ("llvm_ad_rgb", "cuda_ad_rgb"):
                raise ValueError("drjit next-event transport requires llvm_ad_rgb or cuda_ad_rgb")
            if self.specular_order != 0:
                raise ValueError(
                    "drjit next-event transport supports diffuse source connections only; "
                    "set specular_order=0 explicitly"
                )


@dataclass(frozen=True)
class _SiteStudy:
    site: str
    mesh: pathlib.Path
    started: float
    geometry: Any
    datum: Any
    evaluate: np.ndarray
    sources: Any
    tracer: SbrTracer | DeviceEscapeTracer
    clutter_report: dict[str, Any]
    config: NextEventStudyConfig


def site_clutter(
    site: str,
    geometry: Any,
    config: NextEventStudyConfig,
) -> tuple[np.ndarray | None, dict[str, Any]]:
    if not config.drop_clutter:
        return None, {"used": False, "reason": "not asked for"}
    fishnet = config.root / "outputs" / f"{site}_fishnet_vistas_{config.crop_m}m"
    semantics = next((config.root / "data" / "panoramas" / site).glob("**/semantics/semantics.json"), None)
    if not fishnet.is_dir() or semantics is None:
        print(f"{site:24s} no {config.crop_m} m fishnet, every silhouette tip kept")
        return None, {"used": False, "reason": f"no fishnet at {fishnet.name}"}
    mask, report = clutter_triangles(geometry.faces.shape[0], fishnet_dir=fishnet, semantics_path=semantics)
    print(
        f"{site:24s} clutter mask {int(mask.sum())} triangles, "
        f"{report['clutter_fraction_of_seen']:.1%} of what the panoramas saw"
    )
    return mask, {"used": True, **report}


def _standpoints(
    site: str,
    geometry: Any,
    datum: Any,
    config: NextEventStudyConfig,
) -> tuple[np.ndarray, np.ndarray]:
    if config.walk == "route":
        walk, provenance = site_walk(
            geometry,
            site,
            stride_m=config.walk_stride_m,
            head_height_m=config.head_height_m,
            path=config.walk_path,
            root=config.root,
        )
        print(
            f"{site:24s} capture route, {provenance['stations']} cameras, "
            f"{provenance['standpoints']} standpoints over {provenance['road_length_m']:.0f} m"
        )
    else:
        walk = build_walk(
            geometry,
            ground_datum_m=datum.z_m,
            radius_m=config.walk_radius_m,
            head_height_m=config.head_height_m,
            seed=config.seed,
        )
    points = np.asarray(walk.points)
    held_out = config.held_out
    if points.shape[0] < config.held_out + config.builders:
        held_out = max(
            2,
            round(points.shape[0] * config.held_out / (config.held_out + config.builders)),
        )
        print(
            f"{site:24s} {points.shape[0]} standpoints is short of the "
            f"{config.held_out + config.builders} asked for, holding out {held_out}"
        )
    rng = np.random.default_rng(config.seed)
    order = rng.permutation(points.shape[0])
    evaluate = points[order[:held_out]]
    pool = points[order[held_out:]]
    index = np.linspace(0, pool.shape[0] - 1, min(config.builders, pool.shape[0])).round().astype(int)
    return evaluate, pool[index]


def _prepare_site(site: str, mesh: pathlib.Path, config: NextEventStudyConfig) -> _SiteStudy:
    started = time.perf_counter()
    geometry = MitsubaGeometry(mesh, variant=config.variant)
    datum = measure_ground_datum(geometry, radius_m=config.walk_radius_m)
    evaluate, builders = _standpoints(site, geometry, datum, config)
    clutter, clutter_report = site_clutter(site, geometry, config)
    sources = build_source_set(
        geometry,
        builders,
        silhouette,
        azimuths=config.azimuths,
        elevations=config.elevations,
        cell_m=config.cell_m,
        dims=config.dims,
        site_lift_m=config.site_lift_m,
        clutter_triangles=clutter,
        crop_area_m2=(config.crop_area_m2 if config.crop_area_m2 is not None else float(np.pi * config.crop_m**2)),
        density_per_m2=config.density_per_m2,
        eirp_w=config.eirp_w,
        curve_resolution_m=config.curve_resolution_m,
        top_edge_tolerance_m=config.top_edge_tolerance_m,
    )
    face_class = classify_faces(geometry.vertices, geometry.faces, datum.z_m)
    binding = load_table(
        config.root / "config",
        config.frequency_hz,
        roughness_rule=FINISH_ONLY_RULE,
    )
    trace_config = TraceConfig(
        frequency_hz=config.frequency_hz,
        rays=config.rays,
        max_bounces=config.max_bounces,
        seed=config.seed,
        launch_sampling=config.launch_sampling,
    )
    tracer_type = DeviceEscapeTracer if config.transport_kernel == "drjit" else SbrTracer
    tracer = tracer_type(geometry, face_class, binding.permittivity, binding.rms_height_m, trace_config)
    return _SiteStudy(
        site,
        mesh,
        started,
        geometry,
        datum,
        evaluate,
        sources,
        tracer,
        clutter_report,
        config,
    )


def _trace_points(study: _SiteStudy) -> list[dict[str, Any]]:
    models = {"isotropic": ISOTROPIC, "rooftop": ROOFTOP}
    estimator = NextEventEstimator(
        tracer=study.tracer,
        geometry=study.geometry,
        sources=study.sources,
        samples=study.config.connections,
        max_order=study.config.max_bounces,
        specular_order=getattr(study.config, "specular_order", 1),
        diagnostic_models=models,
    )
    per_point = []
    for i, origin in enumerate(study.evaluate):
        result = estimator.estimate(
            origin,
            ground_z_m=study.datum.z_m,
            seed=study.config.seed + i,
        )
        per_point.append(
            {
                "origin": [float(value) for value in origin],
                "direct": result.direct,
                "bounced": result.detail["bounced"],
                "surplus": result.surplus,
                "surplus_db": (10.0 * np.log10(result.surplus) if result.direct > 0.0 else float("nan")),
                **{name: value for name, value in result.detail.items() if name != "bounced"},
            }
        )
        if getattr(study.sources, "crop_area_m2", None) is not None and hasattr(
            study.sources, "per_density_eirp_transfer"
        ):
            per_point[-1]["per_density_eirp_transfer"] = float(study.sources.per_density_eirp_transfer(result.total))
        if (
            getattr(study.sources, "physical_expected_count", None) is not None
            and getattr(study.sources, "eirp_w", None) is not None
        ):
            per_point[-1]["physical_transfer_w_m2"] = float(study.sources.physical_transfer(result.total))
    return per_point


def _site_row(study: _SiteStudy, per_point: list[dict[str, Any]]) -> dict[str, Any]:
    surplus_db = np.array([point["surplus_db"] for point in per_point])
    escape_db = []
    for point in per_point:
        whole = point["escape_chi"]["rooftop"]
        line = point["escape_chi_direct"]["rooftop"]
        escape_db.append(10.0 * np.log10(whole / line) if line > 0.0 else float("nan"))
    escape_db = np.array(escape_db)
    print(
        f"{study.site:22s} sites {len(study.sources):6d}  visible "
        f"{np.median([point['visible_fraction'] for point in per_point]):.3f}  "
        f"surplus {np.median(surplus_db):+.2f} dB  "
        f"(5th {np.percentile(surplus_db, 5):+.2f}, 95th {np.percentile(surplus_db, 95):+.2f})  "
        f"escape surplus {np.nanmedian(escape_db):+.2f} dB  "
        f"{time.perf_counter() - study.started:.0f} s"
    )
    return {
        "site": study.site,
        "crop_radius_m": study.config.crop_m,
        "mesh": str(study.mesh.relative_to(study.config.root)),
        "sources": study.sources.source_provenance(),
        "ground_datum_m": study.datum.z_m,
        "rays": study.config.rays,
        "max_bounces": study.config.max_bounces,
        "transport_kernel": study.config.transport_kernel,
        "launch_sampling": study.config.launch_sampling,
        "variant": study.config.variant,
        "specular_order": study.config.specular_order,
        "held_out": int(study.evaluate.shape[0]),
        "clutter": study.clutter_report,
        "surplus_db_median": float(np.median(surplus_db)),
        "surplus_db_p5": float(np.percentile(surplus_db, 5)),
        "surplus_db_p95": float(np.percentile(surplus_db, 95)),
        "escape_surplus_db_median": float(np.nanmedian(escape_db)),
        "per_point": per_point,
        "seconds": time.perf_counter() - study.started,
    }


def run_next_event_study(config: NextEventStudyConfig) -> pathlib.Path:
    out_dir = config.root / "outputs" / "next_event"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for site in config.sites:
        try:
            mesh = site_mesh(site, config.crop_m, root_dir=config.root)
        except FileNotFoundError:
            print(f"{site:24s} no {config.crop_m} m mesh, skipped")
            continue

        study = _prepare_site(site, mesh, config)
        rows.append(_site_row(study, _trace_points(study)))

    payload = {
        "question": "how much more a pedestrian gets than the rooftops they can see would give on their own",
        "estimator": "next event estimation onto an explicit skyline source set",
        "normalisation": (
            "relative source weights are conditional arc-length probabilities; "
            "per-density-EIRP transfer is unit transfer * crop area / (4 pi), "
            "and physical transfer additionally multiplies density * EIRP"
        ),
        "note": "builders and evaluation standpoints are disjoint",
        "launch_sampling": config.launch_sampling,
        "rows": rows,
    }
    path = out_dir / f"{config.tag}_{config.crop_m}m.json"
    path.write_text(json.dumps(payload, indent=1))
    print(f"wrote {path.relative_to(config.root)}")
    return path
