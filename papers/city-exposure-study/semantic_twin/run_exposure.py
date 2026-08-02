"""Pedestrian exposure along city walks, as a CDF over observation points.

Streaming by design, per the storage rule for this study. Each location is
traced, reduced to a row of scalars plus one few hundred cell angular power
spectrum, appended to a JSONL file, and the paths are discarded. Nothing that
scales with the ray count ever reaches disk, so a run is restartable and
survives being killed.

Usage
-----
    python run_exposure.py --validate                  # closed form checks
    python run_exposure.py --locations 120 --materials walk
    python run_exposure.py --all-sites --locations 80  # the cross city sweep
    python run_exposure.py --report STEM               # replot from the JSONL
    python run_exposure.py --coverage-report           # evidence coverage ladder
    python run_exposure.py --cities-report             # cross city CDF
"""

from __future__ import annotations

import argparse
import json
import pathlib
import platform
import sys
import time
from typing import Any

import numpy as np

from semantic_twin.propagation import (
    ISOTROPIC,
    PEC_PERMITTIVITY,
    ROOFTOP,
    STREET_SMALL_CELL,
    MitsubaGeometry,
    PlaneGeometry,
    SbrTracer,
    TraceConfig,
    ground_plane_susceptibility,
)
from semantic_twin.propagation.exposure import BodyCoupler, describe
from semantic_twin.propagation.scene import CLASS_NAMES, classify_faces, load_bindings
from semantic_twin.propagation.semantic_binding import bind, bind_from_walk
from semantic_twin.propagation.walk import build_walk, stratified_subset

ROOT = pathlib.Path(__file__).resolve().parent
MESH = ROOT / "data" / "geometry" / "korenmarkt" / "inhouse_leaf_130m_f64.ply"
CONFIG = ROOT / "config"
OUTPUT = ROOT / "outputs" / "exposure_korenmarkt"

#: Ground datum of the square in the mesh's local ENU frame, from
#: config/korenmarkt.json ``camera_ground_z_m``.
GROUND_DATUM_M = 50.83747424667166

#: Free space incident power density the external network would deliver at head
#: height with no local scene. Every absolute number below is linear in this, so
#: it is a scale factor and not a physical claim. 1 W/m^2 is chosen because it
#: is the round number nearest the ICNIRP 2020 general public whole body
#: reference level above 2 GHz (10 W/m^2), one decade below it.
REFERENCE_S0_W_M2 = 1.0

#: Duke, the adult male IT'IS phantom, standing upright. 72.4 kg from
#: aegis/data/phantoms.yaml.
PHANTOM = "/home/user/aegis/data/duke.stl"
PHANTOM_MASS_KG = 72.4

#: The fishnet surfaces were cut against the single precision export of the same
#: tiles, so the semantic join runs through a centroid match. See
#: semantic_twin/propagation/semantic_binding.py.
FISHNET_MESH = ROOT / "data" / "geometry" / "korenmarkt" / "inhouse_leaf_130m.ply"
FISHNET_DIR = ROOT / "outputs" / "korenmarkt_fishnet_vistas"
SEMANTICS = ROOT / "data" / "panoramas" / "korenmarkt" / "semantics" / "semantics.json"

#: Fused semantics from the eight registered Mapillary stations along the walk.
WALK_SEMANTIC = ROOT / "outputs" / "walk_korenmarkt" / "walk_semantic.npz"

FREQUENCY_NOTE = (
    "15 GHz is the FR3 midpoint, the band this study leads on: 3GPP FR3 as "
    "scoped in Release 19 runs 7.125 to 24.25 GHz, whose geometric centre is "
    "13.1 GHz and whose arithmetic centre is 15.7 GHz. 28 GHz is carried as the "
    "upper FR2 anchor. Both sit inside the ITU-R P.2040-4 validity band of every "
    "material this scene uses, so no extrapolation flag is needed at either."
)

MODELS = {"isotropic": ISOTROPIC, "rooftop": ROOFTOP, "street_small_cell": STREET_SMALL_CELL}

#: Written into every manifest and quoted beside every rooftop number. Measured
#: by ``run_crop_convergence.py`` on an identical set of standpoints with only
#: the surroundings changing.
CROP_BOUND_NOTE = (
    "A 130 m crop is converged for the sky fraction and, at Korenmarkt, for the "
    "isotropic model. It is NOT converged for the rooftop or street small cell "
    "models, whose sources sit near the horizon where a small crop holds no "
    "geometry able to occlude them, so rays escape to sky that a real building "
    "would have blocked. A larger crop adds missing blockers, not missing "
    "scatterers, and the number goes down. Measured against a 250 m crop over "
    "nine cities, the correction is 0.05 to 4.80 dB rooftop and 0.16 to 11.39 dB "
    "street, and 0.03 to 0.96 dB even for isotropic, where tall cities move most. "
    "It is therefore NOT a constant offset: at 130 m the sites are distorted "
    "relative to each other, not merely shifted together, so a between site "
    "comparison at 130 m is not safe either."
)

#: Every site with a ``format_version: 3`` double precision support mesh. A site
#: only enters a cross city run if it has a mesh at that run's crop radius, so
#: the geometry stays comparable across the set. Milan was acquired before the
#: others and has no 130 m build, so it joins only at 250 m.
SITES: tuple[str, ...] = (
    "brussels_grandplace",
    "korenmarkt",
    "krakow_rynek",
    "london_trafalgar",
    "madrid_plazamayor",
    "mexico_zocalo",
    "newyork_timessquare",
    "prague_staromestske",
    "milan_duomo",
    "tokyo_hachiko",
    "toulouse_capitole",
)


def site_mesh(site: str, crop_m: int = 130) -> pathlib.Path:
    """The double precision export for a site, refusing the defective one.

    Korenmarkt has both a ``format_version: 2`` build, whose tile placement was
    read back through Blender in single precision and carries up to a metre of
    seaming, and a ``_f64`` rebuild that does not. The other sites were built
    after that fix, so their unsuffixed file is already the good one. Rather
    than encode which is which by name, the manifest's ``format_version`` is
    read and anything below 3 is refused.
    """
    directory = ROOT / "data" / "geometry" / site
    for candidate in (f"inhouse_leaf_{crop_m}m_f64.ply", f"inhouse_leaf_{crop_m}m.ply"):
        path = directory / candidate
        manifest = path.with_suffix(".json")
        if not path.exists() or not manifest.exists():
            continue
        if int(json.loads(manifest.read_text()).get("format_version", 0)) >= 3:
            return path
    raise FileNotFoundError(f"no double precision {crop_m} m mesh for {site}")


def ground_datum(geometry: Any, *, radius_m: float = 15.0, samples: int = 4096) -> float:
    """Median height of the surface under the centre of the crop.

    The sites have no surveyed datum in common, and their local ENU origins sit
    anywhere from -220 m to +2200 m, so the walkable height has to come from
    the mesh itself. The median over a central disc is used rather than a single
    downward ray, because a single ray at the origin lands on whatever monument
    the square was built around.
    """
    rng = np.random.default_rng(0)
    angle = rng.uniform(0.0, 2.0 * np.pi, samples)
    distance = radius_m * np.sqrt(rng.random(samples))
    xy = np.column_stack([distance * np.cos(angle), distance * np.sin(angle)])
    probe = 1.0e4
    origins = np.column_stack([xy, np.full(samples, probe)])
    directions = np.tile(np.array([0.0, 0.0, -1.0]), (samples, 1))
    hit, travel, _, _ = geometry.intersect(origins, directions)
    heights = probe - travel[hit]
    if heights.size == 0:
        raise RuntimeError("no surface under the centre of the crop")
    return float(np.median(heights))


def validate(rays: int = 400_000) -> dict[str, object]:
    """Section 11.1 and the free space identity, run rather than asserted."""
    report: dict[str, object] = {}
    config = TraceConfig(rays=rays, local_cells=256, exit_bands=18, seed=11)

    class Empty:
        def intersect(self, origins, directions):  # noqa: ANN001, ANN202
            count = origins.shape[0]
            return (
                np.zeros(count, dtype=bool),
                np.full(count, 1.0e30),
                np.zeros((count, 3)),
                np.zeros(count, dtype=np.int64),
            )

    tracer = SbrTracer(Empty(), None, np.array([PEC_PERMITTIVITY]), np.array([0.0]), config)
    free = tracer.trace(np.array([0.0, 0.0, 1.5]), MODELS)
    report["free_space"] = {
        "chi": free.susceptibility,
        "exit_profile_max_abs_error": float(np.max(np.abs(free.exit_profile - 1.0))),
    }

    tracer = SbrTracer(PlaneGeometry(0.0), None, np.array([PEC_PERMITTIVITY]), np.array([0.0]), config)
    pec = tracer.trace(np.array([0.0, 0.0, 1.5]), MODELS, ground_z_m=0.0)
    upper = pec.exit_profile[config.exit_bands // 2 :]
    lower = pec.exit_profile[: config.exit_bands // 2]
    report["pec_ground_plane"] = {
        "target_upper_hemisphere": 2.0,
        "measured_upper_mean": float(upper.mean()),
        "measured_upper_max_abs_error": float(np.max(np.abs(upper - 2.0))),
        "measured_lower_max": float(lower.max()),
        "chi": pec.susceptibility,
    }

    binding = load_bindings(CONFIG, 15.0e9)
    concrete = binding.permittivity[CLASS_NAMES.index("roof")]
    tracer = SbrTracer(PlaneGeometry(0.0), None, np.array([concrete]), np.array([0.0]), config)
    dielectric = tracer.trace(np.array([0.0, 0.0, 1.5]), MODELS, ground_z_m=0.0)
    centres = 0.5 * (dielectric.exit_sin_edges[:-1] + dielectric.exit_sin_edges[1:])
    elevation = np.degrees(np.arcsin(centres))
    target = ground_plane_susceptibility(elevation, concrete)
    above = elevation > 0.0
    report["dielectric_ground_plane"] = {
        "permittivity": [float(concrete.real), float(concrete.imag)],
        "elevation_deg": [float(x) for x in elevation[above]],
        "closed_form": [float(x) for x in target[above]],
        "measured": [float(x) for x in dielectric.exit_profile[above]],
        "max_abs_error": float(np.max(np.abs(dielectric.exit_profile[above] - target[above]))),
        "max_rel_error": float(np.max(np.abs(dielectric.exit_profile[above] / target[above] - 1.0))),
    }
    return report


def run(
    locations: int,
    rays: int,
    frequency_hz: float,
    *,
    variant: str,
    seed: int,
    tag: str,
    local_cells: int,
    walk_radius_m: float,
    walk_spacing_m: float,
    max_bounces: int,
    materials: str,
    site: str = "korenmarkt",
    coupler: Any = None,
    crop_m: int = 130,
) -> pathlib.Path:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    stem = f"{tag}_{frequency_hz / 1e9:g}ghz"
    rows_path = OUTPUT / f"{stem}_locations.jsonl"
    spectra_path = OUTPUT / f"{stem}_spectra.npz"
    manifest_path = OUTPUT / f"{stem}_manifest.json"

    started = time.perf_counter()
    mesh = site_mesh(site, crop_m)
    geometry = MitsubaGeometry(mesh, variant=variant)
    datum = GROUND_DATUM_M if site == "korenmarkt" else ground_datum(geometry)
    face_class = classify_faces(geometry.vertices, geometry.faces, datum)
    areas = geometry.face_areas()
    semantic_provenance: dict[str, Any] = {"materials": materials}
    if materials in ("semantic", "walk") and site != "korenmarkt":
        raise ValueError(f"no panorama semantics for {site}, use --materials geometric")

    if materials == "semantic":
        source = MitsubaGeometry(FISHNET_MESH, variant=variant)
        semantic = bind(
            geometry.vertices,
            geometry.faces,
            areas,
            face_class,
            fishnet_dir=FISHNET_DIR,
            semantics_path=SEMANTICS,
            source_ply_vertices=source.vertices,
            source_ply_faces=source.faces,
        )
        face_class = semantic.face_class
        binding = load_bindings(
            CONFIG,
            frequency_hz,
            class_names=semantic.class_names,
            class_binding=semantic.class_binding,
            class_rule=(
                "panorama semantic posterior where a panorama saw the triangle, "
                "geometric orientation rule everywhere else"
            ),
        )
        semantic_provenance.update(
            {
                "covered_fraction_by_face": semantic.covered_fraction_by_face,
                "covered_fraction_by_area": semantic.covered_fraction_by_area,
                **semantic.provenance,
            }
        )
        print(
            f"semantic binding: {semantic.covered_fraction_by_face:.4f} of faces, "
            f"{semantic.covered_fraction_by_area:.4f} of area",
            flush=True,
        )
    elif materials == "walk":
        semantic = bind_from_walk(
            areas,
            face_class,
            walk_npz=WALK_SEMANTIC,
            semantics_path=SEMANTICS,
        )
        face_class = semantic.face_class
        binding = load_bindings(
            CONFIG,
            frequency_hz,
            class_names=semantic.class_names,
            class_binding=semantic.class_binding,
            class_rule=(
                "fused multi station walk semantic posterior where any station saw "
                "the triangle, geometric orientation rule everywhere else"
            ),
        )
        semantic_provenance.update(
            {
                "covered_fraction_by_face": semantic.covered_fraction_by_face,
                "covered_fraction_by_area": semantic.covered_fraction_by_area,
                **semantic.provenance,
            }
        )
        print(
            f"walk semantic binding: {semantic.covered_fraction_by_face:.4f} of faces, "
            f"{semantic.covered_fraction_by_area:.4f} of area",
            flush=True,
        )
    elif materials == "geometric":
        binding = load_bindings(CONFIG, frequency_hz)
        semantic_provenance.update({"covered_fraction_by_face": 0.0, "covered_fraction_by_area": 0.0})
    else:
        raise ValueError(f"unknown materials mode {materials!r}")

    walk = build_walk(
        geometry,
        ground_datum_m=datum,
        radius_m=walk_radius_m,
        spacing_m=walk_spacing_m,
        seed=seed,
    )
    picks = stratified_subset(walk, locations)
    print(f"walk: {len(walk)} candidates, tracing {picks.size}", flush=True)

    config = TraceConfig(
        frequency_hz=frequency_hz,
        rays=rays,
        local_cells=local_cells,
        max_bounces=max_bounces,
        seed=seed,
    )
    tracer = SbrTracer(geometry, face_class, binding.permittivity, binding.rms_height_m, config)
    if coupler is None:
        coupler = BodyCoupler(PHANTOM, frequency_hz, body_mass_kg=PHANTOM_MASS_KG)

    manifest = {
        "generator": "run_exposure.py",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "site": site,
        "mesh": str(mesh),
        "mesh_triangles": int(geometry.face_count),
        "crop_radius_m": crop_m,
        "ground_datum_m": datum,
        "ground_datum_source": (
            "config/korenmarkt.json camera_ground_z_m"
            if site == "korenmarkt"
            else "median downward hit over a 15 m disc at the crop centre"
        ),
        "reference_s0_w_m2": REFERENCE_S0_W_M2,
        "trace_config": config.as_dict(),
        "surface_binding": binding.as_dict(),
        "semantic_binding": semantic_provenance,
        "class_area_fractions": {
            name: float(areas[face_class == i].sum() / areas.sum()) for i, name in enumerate(binding.class_names)
        },
        "frequency_note": FREQUENCY_NOTE,
        "crop_bound_note": CROP_BOUND_NOTE,
        "walk": walk.provenance,
        "locations_requested": locations,
        "locations_traced": int(picks.size),
        "illumination_models": {
            name: {
                "elevation_deg": [model.elevation_min_deg, model.elevation_max_deg],
                "law": model.law,
                "description": model.description,
            }
            for name, model in MODELS.items()
        },
        "body": describe(coupler),
        "variant": variant,
        "python": platform.python_version(),
        "storage_policy": "paths are never written, only per location scalars and rho",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))

    spectra = np.zeros((picks.size, local_cells))
    with rows_path.open("w") as handle:
        for row_index, index in enumerate(picks):
            point = walk.points[index]
            result = tracer.trace(point, MODELS, ground_z_m=float(walk.ground_z_m[index]), seed=seed + 1000 * index)
            row = {
                "index": int(index),
                "x": float(point[0]),
                "y": float(point[1]),
                "z": float(point[2]),
                "ground_z_m": float(walk.ground_z_m[index]),
                "seconds": result.seconds,
            }
            row.update(result.scalars())
            for name in MODELS:
                exposure = coupler.couple(
                    result.local_grid,
                    result.rho[name],
                    result.local_solid_angle,
                    REFERENCE_S0_W_M2,
                )
                for key, value in exposure.as_dict().items():
                    row[f"{name}_{key}"] = value
            spectra[row_index] = result.rho["rooftop"]
            handle.write(json.dumps(row) + "\n")
            handle.flush()
            print(
                f"[{row_index + 1}/{picks.size}] chi_rooftop={row['chi_rooftop']:.3f} "
                f"sky={row['sky_fraction']:.3f} "
                f"peak_sab={row['rooftop_peak_sab_w_m2']:.4f} "
                f"({result.seconds:.1f} s)",
                flush=True,
            )
            np.savez_compressed(
                spectra_path,
                rho_rooftop=spectra[: row_index + 1],
                local_grid=result.local_grid,
                solid_angle=result.local_solid_angle,
                index=picks[: row_index + 1],
            )

    manifest["wall_seconds"] = time.perf_counter() - started
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"wrote {rows_path}")
    report(stem)
    return rows_path


def report(stem: str) -> pathlib.Path:
    """Regenerate the CDF figure and the numbers behind it from the JSONL."""
    from semantic_twin.propagation.report import (
        load_rows,
        plot_cdf,
        split_half_stability,
        summarise,
    )

    rows_path = OUTPUT / f"{stem}_locations.jsonl"
    manifest = json.loads((OUTPUT / f"{stem}_manifest.json").read_text())
    rows = load_rows(rows_path)
    keys = [
        "chi_isotropic",
        "chi_rooftop",
        "chi_street_small_cell",
        "chi_isotropic_direct",
        "chi_rooftop_direct",
        "chi_street_small_cell_direct",
        "multipath_gain_isotropic",
        "multipath_gain_rooftop",
        "sky_fraction",
        "mean_bounces",
        "mean_excess_delay_ns",
        "truncated_throughput_share",
        "rooftop_peak_sab_w_m2",
        "rooftop_mean_sab_w_m2",
        "rooftop_absorbed_power_w",
        "rooftop_sar_wb_w_kg",
        "isotropic_peak_sab_w_m2",
        "street_small_cell_peak_sab_w_m2",
    ]
    summary = summarise(rows, keys)
    stability_keys = ["chi_rooftop", "chi_isotropic", "sky_fraction", "rooftop_peak_sab_w_m2"]
    summary["split_half_stability"] = {
        split: split_half_stability(rows, stability_keys, split=split) for split in ("interleaved", "contiguous")
    }
    summary["reference_s0_w_m2"] = manifest["reference_s0_w_m2"]
    summary["frequency_hz"] = manifest["trace_config"]["frequency_hz"]
    summary["rays_per_location"] = manifest["trace_config"]["rays"]
    summary_path = OUTPUT / f"{stem}_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    figure = plot_cdf(
        rows,
        OUTPUT / f"{stem}_cdf.png",
        reference_s0_w_m2=manifest["reference_s0_w_m2"],
        frequency_ghz=manifest["trace_config"]["frequency_hz"] / 1e9,
    )
    print(f"wrote {summary_path} and {figure}")
    return summary_path


#: The evidence coverage ladder. Same geometry, same walk, same illumination,
#: same tracer settings, three different amounts of image evidence behind the
#: material assignment.
COVERAGE_LADDER = (
    ("korenmarkt_geometric", "orientation rule only, no image evidence"),
    ("korenmarkt_semantic", "one registered panorama"),
    ("korenmarkt_walk", "eight registered stations, fused"),
)


def coverage_report(frequency_hz: float) -> pathlib.Path:
    """How far does the exposure distribution move as image evidence grows?

    This is the experiment that says whether the material assignment matters at
    all. Everything except the material binding is held fixed, so the only
    thing varying between the three runs is the fraction of scene area whose
    material came from an image rather than from which way the triangle points.
    """
    from semantic_twin.propagation.report import empirical_cdf, load_rows

    entries: list[dict[str, Any]] = []
    baseline: np.ndarray | None = None
    for stem, description in COVERAGE_LADDER:
        full = f"{stem}_{frequency_hz / 1e9:g}ghz"
        rows_path = OUTPUT / f"{full}_locations.jsonl"
        manifest_path = OUTPUT / f"{full}_manifest.json"
        if not rows_path.exists() or not manifest_path.exists():
            continue
        rows = load_rows(rows_path)
        manifest = json.loads(manifest_path.read_text())
        values = np.array([row["chi_rooftop"] for row in rows])
        entry: dict[str, Any] = {
            "run": stem,
            "evidence": description,
            "covered_fraction_by_area": manifest["semantic_binding"].get("covered_fraction_by_area", 0.0),
            "locations": len(rows),
            "chi_rooftop": {
                "p05": float(np.quantile(values, 0.05)),
                "p50": float(np.quantile(values, 0.50)),
                "p95": float(np.quantile(values, 0.95)),
                "mean": float(values.mean()),
            },
        }
        if baseline is None:
            baseline = values
        else:
            count = min(baseline.size, values.size)
            ratio = values[:count] / baseline[:count]
            entry["against_no_evidence"] = {
                # Median of the paired per location ratios: how far a typical
                # location moves.
                "median_ratio": float(np.median(ratio)),
                "median_shift_db": float(10.0 * np.log10(np.median(ratio))),
                # Ratio of the two distribution medians: how far the published
                # distribution moves. Larger than the paired figure, which says
                # the shift is concentrated in a minority of locations rather
                # than spread evenly.
                "distribution_median_shift_db": float(
                    10.0 * np.log10(np.quantile(values, 0.5) / np.quantile(baseline, 0.5))
                ),
                "spread_db_p95_over_p05": float(10.0 * np.log10(np.quantile(values, 0.95) / np.quantile(values, 0.05))),
                "p95_ratio": float(np.quantile(ratio, 0.95)),
                "max_absolute_change": float(np.max(np.abs(ratio - 1.0))),
                "locations_moved_more_than_1_db": int(np.count_nonzero(np.abs(10.0 * np.log10(ratio)) > 1.0)),
            }
        entries.append(entry)

    summary = {
        "question": (
            "how far does the exposure distribution move as the fraction of scene area carrying image evidence grows"
        ),
        "frequency_hz": frequency_hz,
        "ladder": entries,
    }
    path = OUTPUT / f"coverage_ladder_{frequency_hz / 1e9:g}ghz.json"
    path.write_text(json.dumps(summary, indent=2))

    if len(entries) >= 2:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        figure, panel = plt.subplots(figsize=(5.2, 4.0))
        for entry, colour in zip(entries, ("0.55", "tab:blue", "tab:red"), strict=False):
            full = f"{entry['run']}_{frequency_hz / 1e9:g}ghz"
            rows = load_rows(OUTPUT / f"{full}_locations.jsonl")
            ordered, probability = empirical_cdf(np.array([r["chi_rooftop"] for r in rows]))
            panel.step(
                ordered,
                probability,
                where="post",
                color=colour,
                linewidth=1.6,
                label=f"{100 * entry['covered_fraction_by_area']:.1f} % of area from images",
            )
        panel.set_xscale("log")
        panel.set_xlabel("rooftop susceptibility $\\chi_S$")
        panel.set_ylabel("fraction of walk locations")
        panel.set_title(
            f"Korenmarkt, {frequency_hz / 1e9:g} GHz\nexposure against image evidence coverage",
            fontsize=10,
        )
        panel.legend(fontsize=8, loc="lower right")
        panel.grid(alpha=0.25)
        figure.tight_layout()
        figure_path = OUTPUT / f"coverage_ladder_{frequency_hz / 1e9:g}ghz.png"
        figure.savefig(figure_path, dpi=170)
        figure.savefig(figure_path.with_suffix(".pdf"))
        plt.close(figure)
        print(f"wrote {figure_path}")
    print(f"wrote {path}")
    return path


def run_all_sites(
    locations: int,
    rays: int,
    frequency_hz: float,
    *,
    variant: str,
    seed: int,
    local_cells: int,
    walk_radius_m: float,
    walk_spacing_m: float,
    max_bounces: int,
    sites: tuple[str, ...] = SITES,
    crop_m: int = 130,
) -> None:
    """One geometric materials run per site, then the cross city figure.

    The material treatment is held constant across sites on purpose. Only nine
    of these sites have no panorama coverage at all, so a per site semantic
    binding is not available, and a comparison in which the materials also
    varied would confound geometry with material assignment. What varies here
    is urban form, which is the question.
    """
    coupler = BodyCoupler(PHANTOM, frequency_hz, body_mass_kg=PHANTOM_MASS_KG)
    done: list[str] = []
    for site in sites:
        try:
            site_mesh(site, crop_m)
        except FileNotFoundError:
            # Not a failure. A site simply has no build at this radius, and
            # substituting a different one would confound geometry with crop.
            print(f"[skip] {site}: no {crop_m} m mesh, not comparable at this radius", flush=True)
            continue
        tag = f"city_{site}" if crop_m == 130 else f"city{crop_m}_{site}"
        try:
            run(
                locations,
                rays,
                frequency_hz,
                variant=variant,
                seed=seed,
                tag=tag,
                local_cells=local_cells,
                walk_radius_m=walk_radius_m,
                walk_spacing_m=walk_spacing_m,
                max_bounces=max_bounces,
                materials="geometric",
                site=site,
                coupler=coupler,
                crop_m=crop_m,
            )
            done.append(site)
        except Exception as error:  # noqa: BLE001
            print(f"SITE FAILED {site}: {error!r}", flush=True)
        cross_city_report(done, frequency_hz, crop_m=crop_m)


def cross_city_report(sites: list[str], frequency_hz: float, *, crop_m: int = 130) -> None:
    """CDF with one curve per city, plus the numbers behind it."""
    if not sites:
        return
    from semantic_twin.propagation.report import cross_city_cdf, load_rows, summarise

    prefix = "city" if crop_m == 130 else f"city{crop_m}"
    stems = {site: f"{prefix}_{site}_{frequency_hz / 1e9:g}ghz" for site in sites}
    rows = {}
    for site, stem in stems.items():
        path = OUTPUT / f"{stem}_locations.jsonl"
        if path.exists():
            rows[site] = load_rows(path)
    if not rows:
        return
    keys = ["chi_rooftop", "chi_isotropic", "sky_fraction", "rooftop_peak_sab_w_m2"]
    summary = {
        "frequency_hz": frequency_hz,
        "reference_s0_w_m2": REFERENCE_S0_W_M2,
        "materials": "geometric class prior, identical across sites",
        "crop_radius_m": crop_m,
        "crop_bound_note": CROP_BOUND_NOTE,
        "sites": {site: summarise(values, keys) for site, values in rows.items()},
    }
    path = OUTPUT / f"cities{crop_m}_{frequency_hz / 1e9:g}ghz_summary.json"
    path.write_text(json.dumps(summary, indent=2))
    figure = cross_city_cdf(
        rows,
        OUTPUT / f"cities{crop_m}_{frequency_hz / 1e9:g}ghz_cdf.png",
        frequency_ghz=frequency_hz / 1e9,
        reference_s0_w_m2=REFERENCE_S0_W_M2,
        crop_radius_m=float(crop_m),
    )
    print(f"wrote {path} and {figure}", flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--locations", type=int, default=20)
    parser.add_argument("--rays", type=int, default=200_000)
    parser.add_argument("--max-bounces", type=int, default=6)
    parser.add_argument("--materials", choices=("semantic", "walk", "geometric"), default="semantic")
    parser.add_argument("--frequency-ghz", type=float, default=15.0)
    parser.add_argument("--local-cells", type=int, default=512)
    parser.add_argument("--variant", default="llvm_ad_rgb")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--tag", default="korenmarkt")
    parser.add_argument("--walk-radius-m", type=float, default=90.0)
    parser.add_argument("--walk-spacing-m", type=float, default=3.0)
    parser.add_argument("--site", default="korenmarkt")
    parser.add_argument("--crop-m", type=int, default=130)
    parser.add_argument("--all-sites", action="store_true")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--report", metavar="STEM", default=None)
    parser.add_argument("--cities-report", action="store_true")
    parser.add_argument("--coverage-report", action="store_true")
    args = parser.parse_args(argv)

    if args.cities_report:
        cross_city_report(list(SITES), args.frequency_ghz * 1e9, crop_m=args.crop_m)
        return 0

    if args.coverage_report:
        coverage_report(args.frequency_ghz * 1e9)
        return 0

    if args.all_sites:
        run_all_sites(
            args.locations,
            args.rays,
            args.frequency_ghz * 1e9,
            variant=args.variant,
            seed=args.seed,
            local_cells=args.local_cells,
            walk_radius_m=args.walk_radius_m,
            walk_spacing_m=args.walk_spacing_m,
            max_bounces=args.max_bounces,
            crop_m=args.crop_m,
        )
        return 0

    if args.report:
        report(args.report)
        return 0

    if args.validate:
        outcome = validate(args.rays)
        OUTPUT.mkdir(parents=True, exist_ok=True)
        path = OUTPUT / "exposure_validation.json"
        path.write_text(json.dumps(outcome, indent=2))
        print(json.dumps(outcome, indent=2))
        print(f"wrote {path}")
        return 0

    run(
        args.locations,
        args.rays,
        args.frequency_ghz * 1e9,
        variant=args.variant,
        seed=args.seed,
        tag=args.tag,
        local_cells=args.local_cells,
        walk_radius_m=args.walk_radius_m,
        walk_spacing_m=args.walk_spacing_m,
        max_bounces=args.max_bounces,
        materials=args.materials,
        site=args.site,
        crop_m=args.crop_m,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
