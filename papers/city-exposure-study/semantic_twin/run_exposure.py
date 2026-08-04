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
    python run_exposure.py --coverage-report           # one site's evidence ladder
    python run_exposure.py --coverage-ladder --crop-m 250 --ladder-seeds 7,8,9,10
    python run_exposure.py --cities-report             # cross city CDF
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import platform
import sys
import time
from typing import Any, Sequence

import numpy as np

from semantic_twin import paths
from semantic_twin.illumination import ISOTROPIC, ROOFTOP, STREET_SMALL_CELL
from semantic_twin.materials import (
    CLASS_NAMES,
    bind_fishnet,
    bind_walk_entities,
    bind_walk_materials,
    classify_faces,
    load_table,
)
from semantic_twin.paths import site_mesh
from semantic_twin.propagation.closed_form import PEC_PERMITTIVITY, ground_plane_susceptibility
from semantic_twin.propagation.exposure import BodyCoupler, describe
from semantic_twin.propagation.geometry import MitsubaGeometry, PlaneGeometry
from semantic_twin.propagation.tracer import (
    DEFAULT_MAX_BOUNCES,
    SbrTracer,
    TraceConfig,
    trace_standpoints,
)
from semantic_twin.walk import build_walk, ground_datum, measure_ground_datum, stratified_subset

#: ``ground_datum`` lives beside the walk it feeds, in ``semantic_twin.walk``.
#: It is re-exported because the ablation and
#: payload scripts import it from this module.
__all__ = [
    "GROUND_DATUM_M",
    "MODELS",
    "SITES",
    "ground_datum",
    "measure_ground_datum",
    "run",
    "site_mesh",
    "validate",
]

ROOT = pathlib.Path(__file__).resolve().parent
MESH = ROOT / "data" / "geometry" / "korenmarkt" / "inhouse_leaf_130m_f64.ply"
CONFIG = ROOT / "config"
OUTPUT = ROOT / "outputs" / "exposure_korenmarkt"

#: Ground datum of the square in the mesh's local ENU frame, from
#: config/korenmarkt.json ``camera_ground_z_m``.
GROUND_DATUM_M = 50.83747424667166

#: How far the measured ground datum may sit from the registered panorama camera
#: ground height before the run refuses to continue. The two are independent:
#: the registered value comes from the panorama registration of section 3, the
#: measured one from the mesh alone. Eight of the eleven sites carry a registered
#: value and all eight agree to within 0.30 m, so a metre is a loud disagreement
#: rather than a tolerance anything currently uses.
DATUM_CROSS_CHECK_M = 1.0

#: Free space incident power density the external network would deliver at head
#: height with no local scene. Every absolute number below is linear in this, so
#: it is a scale factor and not a physical claim. 1 W/m^2 is chosen because it
#: is the round number nearest the ICNIRP 2020 general public whole body
#: reference level above 2 GHz (10 W/m^2), one decade below it.
REFERENCE_S0_W_M2 = 1.0

#: Duke, the adult male IT'IS phantom, standing upright. 72.4 kg from
#: aegis/data/phantoms.yaml. ``AEGIS_DATA_DIR`` is AEGIS's own documented data
#: override, so honouring it here is what lets this script run on a machine
#: where the AEGIS checkout does not sit at the same absolute path.
PHANTOM = str(pathlib.Path(os.environ.get("AEGIS_DATA_DIR", "/home/user/aegis/data")) / "duke.stl")
PHANTOM_MASS_KG = 72.4

#: The Mapillary Vistas entity to RF material prior. It is a property of the
#: segmentation vocabulary rather than of any city, and it lives in this file
#: only because Korenmarkt is where the hybrid backend ran. Every station level
#: ``semantics.json`` in the repository carries the same 65 class vocabulary,
#: checked label by label in build_site_semantics.py before the prior is used.
SEMANTICS = ROOT / "data" / "panoramas" / "korenmarkt" / "semantics" / "semantics.json"

#: Fused semantics from the eight registered Mapillary stations along the walk.
WALK_SEMANTIC = ROOT / "outputs" / "walk_korenmarkt" / "walk_semantic.npz"

#: Fused semantics from a site's own registered Street View stations, written by
#: build_site_semantics.py, one file per site and per crop radius.
SITE_SEMANTICS = ROOT / "outputs" / "site_semantics"


def site_walk_semantics(site: str, crop_m: int) -> pathlib.Path | None:
    """The fused station binding for one site at one crop radius, or None.

    ``modal_class`` is indexed by triangle with no join key, so a binding is
    only valid against the exact mesh it was cast against and the crop radius is
    part of the identity of the file. Korenmarkt keeps its Mapillary built
    130 m binding, which is what every published walk number here was measured
    on, and falls through to its Street View binding at any other radius.
    """
    if site == "korenmarkt" and crop_m == 130 and WALK_SEMANTIC.exists():
        return WALK_SEMANTIC
    path = SITE_SEMANTICS / site / f"walk_semantic_{crop_m}m.npz"
    return path if path.exists() else None


def site_fishnet(site: str) -> tuple[pathlib.Path, pathlib.Path] | None:
    """A site's fishnet directory and the single precision mesh it was cut against.

    The mesh is read from the fishnet's own manifest rather than derived from
    the crop radius of the run. ``bind`` matches each fishnet face back to a source triangle
    index, so handing it the mesh of the run rather than the mesh of the cut
    would join two different triangle numberings and would do it quietly. A
    fishnet cut at 130 m is usable in a 250 m run, which is why the mismatch is
    passed through rather than refused, but only if it is passed through
    honestly.

    ``bind`` globs ``*_fishnet.npz`` at the top of the directory it is given and
    does not recurse, so a site whose surfaces sit one level down in a folder
    per panorama has nothing to bind. That is worth saying out loud rather than
    returning None for, because the two failures need opposite fixes: build the
    surfaces, or move the ones already built.
    """
    directory = ROOT / "outputs" / f"{site}_fishnet_vistas"
    if not directory.is_dir():
        return None
    if not any(directory.glob("*_fishnet.npz")):
        nested = sorted({path.parent.name for path in directory.glob("*/*_fishnet.npz")})
        if nested:
            raise ValueError(
                f"{directory} holds its fishnet surfaces one level down, under {len(nested)} folders "
                f"beginning {nested[0]}, and bind() does not recurse. Write them at the top of the "
                f"directory with the panorama in the file name."
            )
        return None
    mesh = paths.fishnet_source_mesh(directory, site, root_dir=ROOT)
    return (directory, mesh) if mesh is not None and mesh.exists() else None


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
    "comparison at 130 m is not safe either. "
    "CORRECTION 2026-08-02: the per city dB figures above were measured under the "
    "superseded illumination law of MONOSTATIC_SBR.md section 2.7 and have not "
    "been remeasured across the nine cities. At Korenmarkt, remeasured on one set "
    "of 24 standpoints with all laws scored on one pass, the 130 m error against a "
    "340 m reference falls from 3.55 dB to 0.60 dB rooftop and from 10.36 dB to "
    "7.23 dB street. The converged radius at a 0.1 dB budget moves from 250 m to "
    "200 m for rooftop and from 300 m to 250 m for street, so the street small "
    "cell model is now the sole binding constraint on the 250 m crop and the "
    "qualitative conclusion is unchanged. Milan Duomo, the only other site with "
    "more than one mesh radius, agrees on rooftop and not on street: its 200 to "
    "250 m step is still 0.95 dB under the corrected law against Korenmarkt's "
    "0.50 dB, and it has no mesh beyond 250 m, so the 250 m requirement remains a "
    "one site measurement."
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


def registered_ground_z(site: str) -> float | None:
    """Pavement height under the panorama cameras, where a registration exists.

    Independent of the mesh statistic: it comes out of the panorama registration
    of section 3, which solved for camera pose against the skyline. Eight of the
    eleven sites have one. It is used as a cross check on the measured datum and
    never as the datum itself, because three sites do not have it and a rule that
    only works on eight sites is not a rule.
    """
    path = CONFIG / f"{site}.json"
    if not path.exists():
        return None
    value = json.loads(path.read_text()).get("camera_ground_z_m")
    return None if value is None else float(value)


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

    binding = load_table(CONFIG, 15.0e9)
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
    walk_npz: pathlib.Path | None = None,
    workers: int | None = None,
    roulette_start: int | None = None,
    ground_datum_m: float | None = None,
    walk_probe_z_m: float | None = None,
) -> pathlib.Path:
    """Trace one site's walk and stream it to disk.

    Three of these arguments exist only so that a published run can be repaired
    rather than replaced, and all three default to the current rule.

    ``roulette_start`` is here because ``TraceConfig`` derives its default from
    ``DEFAULT_MAX_BOUNCES``, and that constant changed on 3 August. Every run
    published before then recorded ``roulette_start: 3`` in its manifest and
    nothing on the command line could ask for it again, so a rerun meant to
    extend a published sweep would have traced a different chain.

    ``ground_datum_m`` and ``walk_probe_z_m`` are here for the same reason and
    matter more, because they change which standpoints get traced rather than
    how each one is traced. The datum rule became the lowest major walkable
    level and the downward probe moved from the datum plus 200 m to the sky
    probe height, both after the ``city250_corrected`` sweep. Left to the
    current defaults, a rerun of one of those sites draws a different walk and
    cannot be compared against the sites beside it.

    In every case the published manifest is the authority. Read the value out
    of it and pass it back in, rather than reconstructing the rule.
    """
    OUTPUT.mkdir(parents=True, exist_ok=True)
    stem = f"{tag}_{frequency_hz / 1e9:g}ghz"
    rows_path = OUTPUT / f"{stem}_locations.jsonl"
    spectra_path = OUTPUT / f"{stem}_spectra.npz"
    manifest_path = OUTPUT / f"{stem}_manifest.json"

    started = time.perf_counter()
    mesh = site_mesh(site, crop_m)
    geometry = MitsubaGeometry(mesh, variant=variant)
    measured = measure_ground_datum(geometry, radius_m=walk_radius_m)
    datum = measured.z_m if ground_datum_m is None else float(ground_datum_m)
    registered = registered_ground_z(site)
    datum_provenance: dict[str, Any] = dict(measured.provenance)
    datum_provenance["registered_camera_ground_z_m"] = registered
    if ground_datum_m is not None:
        datum_provenance["measured_z_m"] = measured.z_m
        datum_provenance["rule"] = (
            f"forced to {datum} m by the caller, overriding the measured "
            f"{measured.z_m} m. The measurement is kept above for comparison"
        )
    if registered is not None:
        offset = datum - registered
        datum_provenance["measured_minus_registered_m"] = offset
        if abs(offset) > DATUM_CROSS_CHECK_M:
            raise RuntimeError(
                f"{site}: the measured ground datum {datum:.3f} m disagrees with the registered "
                f"camera ground height {registered:.3f} m by {offset:+.3f} m, more than the "
                f"{DATUM_CROSS_CHECK_M:.1f} m cross check allows"
            )
    print(
        f"{site}: ground datum {datum:.3f} m from {measured.band_columns} of {measured.columns} "
        f"columns ({100 * measured.band_fraction:.1f} %)",
        flush=True,
    )
    face_class = classify_faces(geometry.vertices, geometry.faces, datum)
    areas = geometry.face_areas()
    semantic_provenance: dict[str, Any] = {"materials": materials}
    # Whether a site can be run with image evidence is a question about what is
    # on disk for that site at that crop radius, not about which site it is. The
    # guard this replaced named korenmarkt, which was true when korenmarkt held
    # the only binding and became a self fulfilling prophecy once it did not.
    walk_binding = walk_npz or site_walk_semantics(site, crop_m)
    fishnet = site_fishnet(site)
    if materials.startswith("walk") and walk_binding is None:
        raise ValueError(
            f"no fused station binding for {site} at {crop_m} m. Build one with "
            f"`build_site_semantics.py --site {site} --crop-m {crop_m}`, which needs registered "
            f"panoramas under data/panoramas/{site}, or run --materials geometric."
        )
    if materials == "semantic" and fishnet is None:
        raise ValueError(
            f"no fishnet surface set for {site} at {crop_m} m, so there is nothing to bind. "
            f"Use --materials walk if the site has a fused station binding, or --materials geometric."
        )

    if materials == "semantic":
        fishnet_dir, fishnet_mesh = fishnet
        source = MitsubaGeometry(fishnet_mesh, variant=variant)
        semantic = bind_fishnet(
            geometry.vertices,
            geometry.faces,
            areas,
            face_class,
            fishnet_dir=fishnet_dir,
            semantics_path=SEMANTICS,
            source_ply_vertices=source.vertices,
            source_ply_faces=source.faces,
        )
        face_class = semantic.face_class
        binding = load_table(
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
        semantic = bind_walk_entities(
            areas,
            face_class,
            walk_npz=walk_binding,
            semantics_path=SEMANTICS,
        )
        face_class = semantic.face_class
        binding = load_table(
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
    elif materials in (
        "walk_material",
        "walk_material_mixture",
        "walk_material_over_entity",
        "walk_material_facade_only",
    ):
        semantic = bind_walk_materials(
            areas,
            face_class,
            walk_npz=walk_binding,
            semantics_path=SEMANTICS,
            mixture=materials == "walk_material_mixture",
            over_entity=materials == "walk_material_over_entity",
            facade_only=materials == "walk_material_facade_only",
        )
        face_class = semantic.face_class
        binding = load_table(
            CONFIG,
            frequency_hz,
            class_names=semantic.class_names,
            class_binding=semantic.class_binding,
            class_rule=(
                "fused multi station walk SAM 3 material posterior where any station bound "
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
            f"walk material binding: {semantic.covered_fraction_by_face:.4f} of faces, "
            f"{semantic.covered_fraction_by_area:.4f} of area",
            flush=True,
        )
    elif materials == "geometric":
        binding = load_table(CONFIG, frequency_hz)
        semantic_provenance.update({"covered_fraction_by_face": 0.0, "covered_fraction_by_area": 0.0})
    else:
        raise ValueError(f"unknown materials mode {materials!r}")

    walk = build_walk(
        geometry,
        ground_datum_m=datum,
        radius_m=walk_radius_m,
        spacing_m=walk_spacing_m,
        seed=seed,
        **({} if walk_probe_z_m is None else {"probe_z_m": walk_probe_z_m}),
    )
    picks = stratified_subset(walk, locations)
    print(f"walk: {len(walk)} candidates, tracing {picks.size}", flush=True)

    config = TraceConfig(
        frequency_hz=frequency_hz,
        rays=rays,
        local_cells=local_cells,
        max_bounces=max_bounces,
        seed=seed,
        **({} if roulette_start is None else {"roulette_start": roulette_start}),
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
        "ground_datum_source": datum_provenance["rule"],
        "ground_datum": datum_provenance,
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
                "height_band_m": list(model.height_band_m) if model.height_band_m else None,
                "range_band_m": list(model.range_band_m) if model.range_band_m else None,
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
    standpoints = [(walk.points[i], float(walk.ground_z_m[i]), seed + 1000 * int(i)) for i in picks]
    with rows_path.open("w") as handle:
        for row_index, result in trace_standpoints(tracer, standpoints, MODELS, workers=workers):
            index = picks[row_index]
            point = walk.points[index]
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
    from semantic_twin.report import read_rows, split_half_stability, summarise
    from semantic_twin.viz.cdf import walk_cdf

    rows_path = OUTPUT / f"{stem}_locations.jsonl"
    manifest = json.loads((OUTPUT / f"{stem}_manifest.json").read_text())
    # ``read_rows`` returns the file plus what it cost to read. Only the rows go
    # on from here, because the summary this writes is pinned by a golden fixture
    # and has no field for a torn line count.
    rows = list(read_rows(rows_path, site=stem).rows)
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
    figure = walk_cdf(
        rows,
        OUTPUT / f"{stem}_cdf.png",
        reference_s0_w_m2=manifest["reference_s0_w_m2"],
        frequency_ghz=manifest["trace_config"]["frequency_hz"] / 1e9,
    )
    print(f"wrote {summary_path} and {figure}")
    return summary_path


#: The evidence coverage ladder. Same geometry, same walk, same illumination,
#: same tracer settings, three different amounts of image evidence behind the
#: material assignment. This is the published Korenmarkt tuple, kept because its
#: three stems are quoted in the paper and in half a dozen working documents and
#: are therefore a fixed point rather than a naming convention. ``coverage_ladder``
#: reproduces exactly these stems for Korenmarkt at 130 m on seed 7, and a test
#: pins that, so the generalisation cannot rename the published runs.
COVERAGE_LADDER = (
    ("korenmarkt_geometric", "orientation rule only, no image evidence"),
    ("korenmarkt_semantic", "one registered panorama"),
    ("korenmarkt_walk", "eight registered stations, fused"),
)

#: What each rung of the ladder puts behind the material assignment. The rung is
#: named by the ``--materials`` mode that produces it, so the ladder and the run
#: cannot drift apart.
LADDER_EVIDENCE: dict[str, str] = {
    "geometric": "orientation rule only, no image evidence",
    "semantic": "per view fishnet surfaces, joined onto the tracer mesh",
    "walk": "registered stations, fused",
}

#: The three illumination models the ladder is scored on. The rooftop model is
#: the one the paper leads on and the one the published ladder quoted, and the
#: other two are carried because their Monte Carlo noise differs by a factor of
#: thirty: the street model crowds its whole mass into the first thirty degrees
#: of elevation, so most rays contribute nothing to it and its shift is the
#: least resolved of the three. Reporting only the quiet model would flatter the
#: result.
LADDER_MODELS = ("chi_isotropic", "chi_rooftop", "chi_street_small_cell")


def _against_baseline(baseline: np.ndarray, values: np.ndarray) -> dict[str, float | int]:
    """How far one rung sits from the no evidence rung, paired standpoint by standpoint.

    Both rungs trace the same walk on the same per standpoint seeds, so the ray
    stream is common to the two and the difference carries no independent Monte
    Carlo noise from it. What the difference does carry is the standpoint draw,
    which is why the shift is replicated over seeds rather than quoted from one.
    """
    count = min(baseline.size, values.size)
    ratio = values[:count] / baseline[:count]
    return {
        # Median of the paired per location ratios: how far a typical location
        # moves.
        "median_ratio": float(np.median(ratio)),
        "median_shift_db": float(10.0 * np.log10(np.median(ratio))),
        # Ratio of the two distribution medians: how far the published
        # distribution moves. Larger than the paired figure at Korenmarkt, which
        # says the shift is concentrated in a minority of locations rather than
        # spread evenly.
        "distribution_median_shift_db": float(10.0 * np.log10(np.quantile(values, 0.5) / np.quantile(baseline, 0.5))),
        "spread_db_p95_over_p05": float(10.0 * np.log10(np.quantile(values, 0.95) / np.quantile(values, 0.05))),
        "p95_ratio": float(np.quantile(ratio, 0.95)),
        "max_absolute_change": float(np.max(np.abs(ratio - 1.0))),
        "locations_moved_more_than_1_db": int(np.count_nonzero(np.abs(10.0 * np.log10(ratio)) > 1.0)),
    }


#: The coverage ledger summarise_evidence_coverage.py writes, read here for the
#: one question the files on disk cannot answer: whether the cameras behind a
#: site's fishnet surfaces passed pose admission.
EVIDENCE_COVERAGE = ROOT / "outputs" / "evidence_coverage.json"


def fishnet_rests_on_an_admitted_pose(site: str) -> bool:
    """Whether a fishnet rung at this site would rest on any admitted camera.

    The rule is the ledger's ``semantic_is_bound``, applied from its cached
    output so that a ladder and a coverage table cannot disagree about which
    sites have evidence. Two single panorama sites wrote their views with no
    panorama in the name, and the ledger declines to guess which camera they
    came from rather than refusing them, so unattributed reads as bound here
    too. With no ledger on disk the answer is no, because the safe failure is
    the one that leaves a square out of the table rather than the one that puts
    an unadmitted camera into it.
    """
    if not EVIDENCE_COVERAGE.exists():
        return False
    rows = json.loads(EVIDENCE_COVERAGE.read_text())["rows"]
    entry = next((row for row in rows if row["site"] == site), None)
    if entry is None:
        return False
    coverage = entry.get("semantic_coverage")
    if coverage is None or coverage.get("covered_fraction_by_area", 0.0) <= 0.0:
        return False
    return bool(entry.get("fishnet_panoramas_admitted")) or entry.get("fishnet_panoramas") is None


def ladder_tag(site: str, crop_m: int, materials: str, seed: int = 7) -> str:
    """The run tag of one rung of one site's ladder.

    Korenmarkt at 130 m on seed 7 keeps the three bare stems the published
    ladder was written under. Every other rung is named by site, crop radius and
    seed, because all three change the number and none of them is recoverable
    from a file called ``korenmarkt_walk``.
    """
    if site == "korenmarkt" and crop_m == 130 and seed == 7:
        return f"korenmarkt_{materials}"
    return f"ladder{crop_m}_{site}_s{seed}_{materials}"


def ladder_key(site: str, crop_m: int, seed: int = 7) -> str:
    """The part of a ladder report's file name that identifies which ladder it is."""
    if site == "korenmarkt" and crop_m == 130 and seed == 7:
        return ""
    return f"_{site}_{crop_m}m_s{seed}"


def coverage_ladder(site: str, crop_m: int, seed: int = 7) -> tuple[tuple[str, str, str], ...]:
    """The rungs a site can actually climb at one crop radius, in evidence order.

    A rung is offered when the binding behind it is on disk for that site at
    that crop radius, which is the same question ``run`` asks before it refuses
    a materials mode. The list was three hard coded Korenmarkt stems while
    Korenmarkt held the only binding, and a hard coded list cannot notice that
    six more sites acquired one.

    The fishnet rung is offered on the mesh the surfaces were cut against rather
    than the mesh of the run, so a 130 m cut inside a 250 m run is a rung and not
    a silent join of two triangle numberings. A site whose surfaces sit one level
    down raises out of ``site_fishnet``; that is a build problem rather than a
    missing rung, so it is not swallowed here.

    Having surfaces on disk is not the same as having evidence. Times Square's
    eight views were cut from two cameras that the sky conflict test places
    inside the buildings they are pointed at, and neither is admitted, so the
    fishnet rung is gated on the coverage ledger's own admission rule rather
    than on the files existing.
    """
    rungs = [(ladder_tag(site, crop_m, "geometric", seed), "geometric", LADDER_EVIDENCE["geometric"])]
    if site_fishnet(site) is not None and fishnet_rests_on_an_admitted_pose(site):
        rungs.append((ladder_tag(site, crop_m, "semantic", seed), "semantic", LADDER_EVIDENCE["semantic"]))
    if site_walk_semantics(site, crop_m) is not None:
        rungs.append((ladder_tag(site, crop_m, "walk", seed), "walk", LADDER_EVIDENCE["walk"]))
    return tuple(rungs)


def coverage_report(
    frequency_hz: float,
    tag_suffix: str = "",
    *,
    site: str = "korenmarkt",
    crop_m: int = 130,
    seed: int = 7,
) -> pathlib.Path:
    """How far does the exposure distribution move as image evidence grows?

    This is the experiment that says whether the material assignment matters at
    all. Everything except the material binding is held fixed, so the only
    thing varying between the three runs is the fraction of scene area whose
    material came from an image rather than from which way the triangle points.

    ``tag_suffix`` reads a rerun of the same rungs written under suffixed
    tags, so a rerun at a different bounce budget does not overwrite the
    published ladder and can be compared against it.
    """
    from semantic_twin.report import empirical_cdf, read_rows

    entries: list[dict[str, Any]] = []
    baseline: dict[str, np.ndarray] | None = None
    for stem, _materials, description in coverage_ladder(site, crop_m, seed):
        full = f"{stem}{tag_suffix}_{frequency_hz / 1e9:g}ghz"
        rows_path = OUTPUT / f"{full}_locations.jsonl"
        manifest_path = OUTPUT / f"{full}_manifest.json"
        if not rows_path.exists() or not manifest_path.exists():
            continue
        rows = read_rows(rows_path, site=site).rows
        manifest = json.loads(manifest_path.read_text())
        binding = manifest["semantic_binding"]
        columns = {key: np.array([row[key] for row in rows]) for key in LADDER_MODELS}
        values = columns["chi_rooftop"]
        entry: dict[str, Any] = {
            "run": stem,
            # The suffixed stem, because the figure below reloads these rows and
            # rebuilding the name from ``run`` would silently read the published
            # ladder while the table above described the rerun.
            "stem": full,
            "site": site,
            "crop_radius_m": crop_m,
            "seed": seed,
            "evidence": description,
            # A bound run is a run in which this fraction of the triangle area
            # carries image evidence and the rest still falls back to the
            # orientation rule. It travels beside every shift below because a
            # shift without it is not interpretable.
            "covered_fraction_by_area": binding.get("covered_fraction_by_area", 0.0),
            "covered_fraction_by_face": binding.get("covered_fraction_by_face", 0.0),
            "stations": binding.get("stations"),
            "views": len(binding["views"]) if isinstance(binding.get("views"), list) else None,
            # Every fishnet in this study was cut against a smaller mesh than the
            # 250 m run uses, so the join from the cut mesh's triangle numbering
            # to the run's is done by centroid and normal and can drop triangles.
            # How many it kept is part of the result, not an implementation
            # detail, so it is carried rather than left inside the manifest.
            "mesh_match": binding.get("mesh_match"),
            "binding_source": binding.get("walk_npz") or binding.get("fishnet_dir"),
            "locations": len(rows),
            "chi_rooftop": {
                "p05": float(np.quantile(values, 0.05)),
                "p50": float(np.quantile(values, 0.50)),
                "p95": float(np.quantile(values, 0.95)),
                "mean": float(values.mean()),
            },
        }
        if baseline is None:
            baseline = columns
        else:
            entry["against_no_evidence"] = _against_baseline(baseline["chi_rooftop"], values)
            entry["by_model"] = {
                key: _against_baseline(baseline[key], columns[key]) for key in LADDER_MODELS if key in baseline
            }
        entries.append(entry)

    summary = {
        "question": (
            "how far does the exposure distribution move as the fraction of scene area carrying image evidence grows"
        ),
        "site": site,
        "crop_radius_m": crop_m,
        "seed": seed,
        "frequency_hz": frequency_hz,
        "ladder": entries,
    }
    path = OUTPUT / f"coverage_ladder{ladder_key(site, crop_m, seed)}{tag_suffix}_{frequency_hz / 1e9:g}ghz.json"
    path.write_text(json.dumps(summary, indent=2))

    if len(entries) >= 2:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        figure, panel = plt.subplots(figsize=(5.2, 4.0))
        for entry, colour in zip(entries, ("0.55", "tab:blue", "tab:red"), strict=False):
            rows = read_rows(OUTPUT / f"{entry['stem']}_locations.jsonl", site=site).rows
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
            f"{site}, {crop_m} m crop, {frequency_hz / 1e9:g} GHz\nexposure against image evidence coverage",
            fontsize=10,
        )
        panel.legend(fontsize=8, loc="lower right")
        panel.grid(alpha=0.25)
        figure_path = (
            OUTPUT / f"coverage_ladder{ladder_key(site, crop_m, seed)}{tag_suffix}_{frequency_hz / 1e9:g}ghz.png"
        )
        figure.tight_layout()
        figure.savefig(figure_path, dpi=170)
        figure.savefig(figure_path.with_suffix(".pdf"))
        plt.close(figure)
        print(f"wrote {figure_path}")
    print(f"wrote {path}")
    return path


def ladder_sites(sites: tuple[str, ...], crop_m: int) -> tuple[list[str], dict[str, str]]:
    """Which sites can climb a ladder at this crop, and why the rest cannot.

    A site needs a mesh at the run's radius and at least one binding beyond the
    orientation rule. Both refusals are returned rather than printed, because a
    site that cannot answer belongs in the report next to the ones that can.
    """
    admitted: list[str] = []
    refused: dict[str, str] = {}
    for site in sites:
        try:
            site_mesh(site, crop_m)
        except FileNotFoundError:
            refused[site] = f"no {crop_m} m mesh, not comparable at this radius"
            continue
        try:
            rungs = coverage_ladder(site, crop_m)
        except ValueError as error:
            refused[site] = str(error)
            continue
        if len(rungs) < 2:
            refused[site] = f"no image binding at {crop_m} m, only the orientation rule"
            continue
        admitted.append(site)
    return admitted, refused


def reusable(stem: str, locations: int, rays: int, site: str, crop_m: int, seed: int, max_bounces: int) -> bool:
    """Whether a run already on disk is the run this sweep would produce.

    Existing and complete is not enough. Korenmarkt's three published 130 m
    stems are complete runs of 120 standpoints made under the superseded
    elevation law, and a resume that accepted them on the file names alone would
    put a different physics into one row of a cross site table and print nothing
    about it. Every field that changes the number is checked, and a rung is
    retraced whenever any of them disagrees.
    """
    manifest_path = OUTPUT / f"{stem}_manifest.json"
    rows_path = OUTPUT / f"{stem}_locations.jsonl"
    if not manifest_path.exists() or not rows_path.exists():
        return False
    manifest = json.loads(manifest_path.read_text())
    with rows_path.open() as handle:
        written = sum(1 for _ in handle)
    config = manifest.get("trace_config", {})
    # The illumination law is the field that caught this: the correction of
    # MONOSTATIC_SBR.md moved the rooftop median by more than two decibels at
    # every standpoint while leaving every other manifest field identical.
    laws = {name: entry.get("law") for name, entry in manifest.get("illumination_models", {}).items()}
    return (
        manifest.get("locations_traced") == written == locations
        and manifest.get("site") == site
        and manifest.get("crop_radius_m") == crop_m
        and config.get("rays") == rays
        and config.get("seed") == seed
        and config.get("max_bounces") == max_bounces
        and laws == {name: model.law for name, model in MODELS.items()}
    )


def run_coverage_ladder(
    locations: int,
    rays: int,
    frequency_hz: float,
    *,
    variant: str,
    seeds: tuple[int, ...],
    local_cells: int,
    walk_radius_m: float,
    walk_spacing_m: float,
    max_bounces: int,
    sites: tuple[str, ...] = SITES,
    crop_m: int = 130,
    tag_suffix: str = "",
    workers: int | None = None,
) -> pathlib.Path | None:
    """Climb every site's evidence ladder, on every seed, then compare the sites.

    One seed gives one paired measurement of the shift, and the pairing removes
    the ray noise but not the standpoint draw, which is the larger term. Each
    seed here redraws the walk and the per standpoint ray streams together, so
    the seeds are disjoint replicates of the whole measurement and their spread
    is the error bar the table needs.

    A rung already on disk with the requested number of standpoints is not
    retraced, so a sweep that dies at hour three resumes where it stopped.

    The loop is seed major rather than site major. Nothing is cached between
    runs, so the order costs nothing, and it means the first replicate of every
    square lands before the second replicate of any of them. A sweep that has to
    be stopped early then holds a complete cross site answer with no error bar
    rather than an error bar on a third of the sites.
    """
    coupler = BodyCoupler(PHANTOM, frequency_hz, body_mass_kg=PHANTOM_MASS_KG)
    admitted, refused = ladder_sites(sites, crop_m)
    for site, reason in refused.items():
        print(f"[skip] {site}: {reason}", flush=True)
    failures: dict[str, str] = {}
    for seed in seeds:
        for site in admitted:
            for tag, materials, _description in coverage_ladder(site, crop_m, seed):
                stem = f"{tag}{tag_suffix}_{frequency_hz / 1e9:g}ghz"
                if reusable(stem, locations, rays, site, crop_m, seed, max_bounces):
                    print(f"[have] {stem}", flush=True)
                    continue
                if (OUTPUT / f"{stem}_manifest.json").exists():
                    # Korenmarkt at 130 m on seed 7 writes the three published
                    # stems, and those hold 120 standpoint runs made under the
                    # superseded elevation law. A resume refuses to read them,
                    # which would otherwise leave a sweep quietly overwriting
                    # the runs the paper quotes.
                    raise ValueError(
                        f"{stem} is on disk and was made at different settings. Overwriting it would "
                        f"destroy a run something else may quote. Pass --tag-suffix to write beside it."
                    )
                try:
                    run(
                        locations,
                        rays,
                        frequency_hz,
                        variant=variant,
                        seed=seed,
                        tag=f"{tag}{tag_suffix}",
                        local_cells=local_cells,
                        walk_radius_m=walk_radius_m,
                        walk_spacing_m=walk_spacing_m,
                        max_bounces=max_bounces,
                        materials=materials,
                        site=site,
                        coupler=coupler,
                        crop_m=crop_m,
                        workers=workers,
                    )
                except Exception as error:  # noqa: BLE001
                    # Named and carried into the report. A rung that failed is a
                    # row that says why, never a row filled from a neighbour.
                    failures[stem] = repr(error)
                    print(f"RUNG FAILED {stem}: {error!r}", flush=True)
            coverage_report(frequency_hz, tag_suffix, site=site, crop_m=crop_m, seed=seed)
    return coverage_ladder_report(
        admitted,
        crop_m,
        seeds,
        frequency_hz,
        tag_suffix=tag_suffix,
        refused=refused,
        failures=failures,
    )


def coverage_ladder_report(
    sites: list[str],
    crop_m: int,
    seeds: tuple[int, ...],
    frequency_hz: float,
    *,
    tag_suffix: str = "",
    refused: dict[str, str] | None = None,
    failures: dict[str, str] | None = None,
) -> pathlib.Path | None:
    """Does the single square material negative travel? One row per square.

    The shift is a mean over the seeds and its error bar is their standard
    error. The bound area fraction sits beside it in the same row and is not
    optional: a 4.6 percent bound run is a run in which 95.4 percent of the area
    still came from the orientation rule, and quoting the shift without it
    invites the reader to read it as the effect of knowing the materials.

    The bound fraction is a property of where a camera could stand rather than
    of how good the segmentation is, so the rows are ordered by site name and
    not by it.
    """
    rows: list[dict[str, Any]] = []
    for site in sites:
        per_rung: dict[str, dict[str, Any]] = {}
        for seed in seeds:
            path = (
                OUTPUT / f"coverage_ladder{ladder_key(site, crop_m, seed)}{tag_suffix}_{frequency_hz / 1e9:g}ghz.json"
            )
            if not path.exists():
                continue
            for entry in json.loads(path.read_text())["ladder"]:
                if "against_no_evidence" not in entry:
                    continue
                rung = entry["run"].rsplit("_", 1)[-1]
                record = per_rung.setdefault(
                    rung,
                    {
                        "rung": rung,
                        "evidence": entry["evidence"],
                        "covered_fraction_by_area": [],
                        "stations": entry["stations"],
                        "views": entry["views"],
                        "locations": [],
                        "seeds": [],
                        "shift_db": {key: [] for key in LADDER_MODELS},
                        "paired_median_shift_db": {key: [] for key in LADDER_MODELS},
                        "locations_moved_more_than_1_db": [],
                    },
                )
                record["covered_fraction_by_area"].append(entry["covered_fraction_by_area"])
                record["locations"].append(entry["locations"])
                record["seeds"].append(seed)
                record["locations_moved_more_than_1_db"].append(
                    entry["against_no_evidence"]["locations_moved_more_than_1_db"]
                )
                for key in LADDER_MODELS:
                    against = entry.get("by_model", {}).get(key)
                    if against is None:
                        continue
                    record["shift_db"][key].append(against["distribution_median_shift_db"])
                    record["paired_median_shift_db"][key].append(against["median_shift_db"])
        for rung in per_rung.values():
            rung["covered_fraction_by_area"] = _one_value(rung["covered_fraction_by_area"])
            rung["shift_db"] = {key: _spread(values) for key, values in rung["shift_db"].items()}
            rung["paired_median_shift_db"] = {
                key: _spread(values) for key, values in rung["paired_median_shift_db"].items()
            }
            rows.append({"site": site, **rung})
    if not rows:
        print("no ladder to report", flush=True)
        return None
    summary = {
        "question": "does the single square material negative travel to the other squares",
        "crop_radius_m": crop_m,
        "frequency_hz": frequency_hz,
        "seeds": list(seeds),
        "shift_definition": (
            "ratio of the two distribution medians in dB, the walk or fishnet rung against the "
            "geometric rung on the same standpoints, averaged over the seeds"
        ),
        "standard_error": "standard deviation over the seeds divided by the square root of their count",
        "bound_fraction_note": (
            "covered_fraction_by_area is the fraction of the crop's triangle area carrying image "
            "evidence. The rest falls back to the orientation rule. It is set by where a camera "
            "could stand against how far the crop reaches, not by segmentation quality, so it does "
            "not rank the squares by evidence quality."
        ),
        "rows": rows,
        "sites_refused": refused or {},
        "rungs_failed": failures or {},
    }
    path = OUTPUT / f"coverage_ladder_cross_site_{crop_m}m{tag_suffix}_{frequency_hz / 1e9:g}ghz.json"
    path.write_text(json.dumps(summary, indent=2))
    plot_cross_site_ladder(rows, path.with_suffix(".png"), crop_m, frequency_hz)
    print(ladder_markdown(rows), flush=True)
    print(f"wrote {path}", flush=True)
    return path


def plot_cross_site_ladder(
    rows: list[dict[str, Any]],
    path: pathlib.Path,
    crop_m: int,
    frequency_hz: float,
) -> pathlib.Path | None:
    """Shift against bound area, one point per square, with the noise floor on it.

    Plotting the shift against the bound fraction rather than against the site
    name is the whole question in one panel: if knowing the materials mattered,
    the squares that know more of them would move further, and the cloud would
    have a slope.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, panel = plt.subplots(figsize=(5.4, 4.0))
    markers = {"walk": "o", "semantic": "s"}
    for rung, marker in markers.items():
        chosen = [row for row in rows if row["rung"] == rung and isinstance(row["covered_fraction_by_area"], float)]
        if not chosen:
            continue
        x = [100.0 * row["covered_fraction_by_area"] for row in chosen]
        y = [row["shift_db"]["chi_rooftop"]["mean_db"] for row in chosen]
        error = [row["shift_db"]["chi_rooftop"]["standard_error_db"] or 0.0 for row in chosen]
        panel.errorbar(x, y, yerr=error, fmt=marker, capsize=3, label=f"{rung} rung", linewidth=1.2, markersize=5)
        for row, px, py in zip(chosen, x, y, strict=True):
            panel.annotate(row["site"].split("_")[0], (px, py), fontsize=7, xytext=(4, 3), textcoords="offset points")
    panel.axhline(0.0, color="0.4", linewidth=0.8)
    panel.set_xlabel("percent of triangle area carrying image evidence")
    panel.set_ylabel("shift of the distribution median, dB")
    panel.set_title(
        f"{crop_m} m crop, {frequency_hz / 1e9:g} GHz, rooftop model\nexposure shift against how much of the "
        "square a camera saw",
        fontsize=10,
    )
    panel.legend(fontsize=8)
    panel.grid(alpha=0.25)
    figure.tight_layout()
    figure.savefig(path, dpi=170)
    figure.savefig(path.with_suffix(".pdf"))
    plt.close(figure)
    print(f"wrote {path}", flush=True)
    return path


def _one_value(values: list[float]) -> float | list[float]:
    """A bound fraction does not depend on the seed, so a spread in it is a fault."""
    unique = sorted(set(values))
    return unique[0] if len(unique) == 1 else unique


def _spread(values: list[float]) -> dict[str, Any]:
    array = np.array(values, dtype=float)
    if array.size == 0:
        return {"replicates": 0, "mean_db": None, "sd_db": None, "standard_error_db": None, "per_seed_db": []}
    sd = float(array.std(ddof=1)) if array.size > 1 else None
    return {
        "replicates": int(array.size),
        "mean_db": float(array.mean()),
        "sd_db": sd,
        "standard_error_db": None if sd is None else sd / float(np.sqrt(array.size)),
        "per_seed_db": [float(x) for x in array],
    }


def ladder_markdown(rows: list[dict[str, Any]]) -> str:
    """The per square table, bound fraction first and never on its own."""
    header = (
        "| Site | Rung | Bound area | Stations or views | Standpoints | "
        "Rooftop shift | Isotropic shift | Street shift |"
    )
    lines = [header, "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for row in rows:
        bound = row["covered_fraction_by_area"]
        bound_cell = f"{100 * bound:.1f} %" if isinstance(bound, float) else "inconsistent across seeds"
        evidence = row["stations"] if row["stations"] is not None else row["views"]
        kind = "stations" if row["stations"] is not None else "views"
        cells = [
            row["site"],
            row["rung"],
            bound_cell,
            "not recorded" if evidence is None else f"{evidence} {kind}",
            f"{sum(row['locations'])} over {len(row['seeds'])} seeds",
        ]
        for key in ("chi_rooftop", "chi_isotropic", "chi_street_small_cell"):
            spread = row["shift_db"][key]
            if spread["mean_db"] is None:
                cells.append("n/a")
            elif spread["standard_error_db"] is None:
                cells.append(f"{spread['mean_db']:+.3f} dB, one seed")
            else:
                cells.append(f"{spread['mean_db']:+.3f} +/- {spread['standard_error_db']:.3f} dB")
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


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
    tag_suffix: str = "",
    workers: int | None = None,
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
    buildable: list[str] = []
    for site in sites:
        try:
            site_mesh(site, crop_m)
        except FileNotFoundError:
            # Not a failure. A site simply has no build at this radius, and
            # substituting a different one would confound geometry with crop.
            print(f"[skip] {site}: no {crop_m} m mesh, not comparable at this radius", flush=True)
            continue
        buildable.append(site)
        # The suffix keeps a rerun from landing on a published run's files. The
        # city250_* tags hold the results computed under the superseded
        # elevation law, and those have to stay readable next to their
        # replacements rather than be overwritten in place.
        stem = "city" if crop_m == 130 else f"city{crop_m}"
        tag = f"{stem}{tag_suffix}_{site}"
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
                workers=workers,
            )
            done.append(site)
        except Exception as error:  # noqa: BLE001
            print(f"SITE FAILED {site}: {error!r}", flush=True)
        # Written after every site so a sweep that dies at hour two still leaves
        # a readable aggregate. It therefore spends most of its life partial,
        # and used to say nothing about that: the published eleven city figure
        # was copied from one of these mid-sweep snapshots and showed a site at
        # 3 standpoints. The table now carries its own coverage and the figure is
        # only drawn from a table that passes it.
        #
        # ``buildable`` still grows inside this loop, so mid sweep it names the
        # squares reached rather than the squares intended and the two agree at
        # every step of a healthy sweep. The list is what the old counter was,
        # with names instead of a number. Hoisting the mesh check above the loop
        # would make the expectation durable and is the remaining half of this
        # fix.
        cross_city_report(done, frequency_hz, crop_m=crop_m, tag_suffix=tag_suffix, sites_expected=tuple(buildable))


def cross_city_report(
    sites: list[str],
    frequency_hz: float,
    *,
    crop_m: int = 130,
    tag_suffix: str = "",
    sites_expected: Sequence[str] | None = None,
) -> None:
    """CDF with one curve per city, plus the numbers behind it.

    The suffix has to be threaded here as well as into the per site tags. It
    was not, and the result was quiet rather than loud: a suffixed run traced
    every site, then read the unsuffixed per site files and rewrote the
    unsuffixed aggregate from them, so the new runs were simply not in the
    figure and nothing said so.

    ``sites_expected`` names the squares the sweep meant to reach. It used to be
    a count, and a count is what let a ten of eleven aggregate call itself
    complete. Names go into :class:`~semantic_twin.report.Coverage`, which will
    not hand the figure a table it cannot vouch for.
    """
    if not sites:
        return
    from semantic_twin.report import CrossCityTable, IncompleteAggregate, read_rows
    from semantic_twin.viz.cdf import cross_city_cdf

    prefix = "city" if crop_m == 130 else f"city{crop_m}"
    stems = {site: f"{prefix}{tag_suffix}_{site}_{frequency_hz / 1e9:g}ghz" for site in sites}
    rows = {}
    for site, stem in stems.items():
        path = OUTPUT / f"{stem}_locations.jsonl"
        if path.exists():
            rows[site] = read_rows(path, site=site)
    if not rows:
        return
    table = CrossCityTable.build(
        rows,
        expected=sites if sites_expected is None else sites_expected,
        frequency_hz=frequency_hz,
        reference_s0_w_m2=REFERENCE_S0_W_M2,
        crop_radius_m=float(crop_m),
        materials="geometric class prior, identical across sites",
        crop_bound_note=CROP_BOUND_NOTE,
    )
    path = OUTPUT / f"cities{crop_m}{tag_suffix}_{frequency_hz / 1e9:g}ghz_summary.json"
    path.write_text(json.dumps(table.as_dict(), indent=2))
    try:
        published = table.publish()
    except IncompleteAggregate as refusal:
        # The table is still written, because a sweep that dies at hour two should
        # leave a readable aggregate behind. The figure is not, because the figure
        # is the thing that got copied into the paper.
        print(f"[partial] {refusal}", flush=True)
        print(f"wrote {path}, no figure", flush=True)
        return
    figure = cross_city_cdf(
        published,
        OUTPUT / f"cities{crop_m}{tag_suffix}_{frequency_hz / 1e9:g}ghz_cdf.png",
        frequency_ghz=frequency_hz / 1e9,
        reference_s0_w_m2=REFERENCE_S0_W_M2,
        crop_radius_m=float(crop_m),
    )
    print(f"wrote {path} and {figure}", flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--locations", type=int, default=0)
    parser.add_argument("--rays", type=int, default=200_000)
    parser.add_argument("--max-bounces", type=int, default=DEFAULT_MAX_BOUNCES)
    parser.add_argument(
        "--materials",
        choices=(
            "semantic",
            "walk",
            "walk_material",
            "walk_material_mixture",
            "walk_material_over_entity",
            "walk_material_facade_only",
            "geometric",
        ),
        default="geometric",
    )
    parser.add_argument(
        "--walk-npz",
        default=None,
        help=(
            "fused walk semantics to bind materials from, for --materials walk. "
            "Defaults to the eight station set that passed the 4 degree residual gate. "
            "outputs/walk_korenmarkt/walk_semantic_conflict9.npz is the nine station set "
            "that passes the sky conflict gate of section 3.2.1 instead."
        ),
    )
    parser.add_argument("--frequency-ghz", type=float, default=15.0)
    parser.add_argument("--local-cells", type=int, default=512)
    parser.add_argument("--variant", default="llvm_ad_rgb")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="trace standpoints in a process pool. Results are bit identical to the serial sweep. "
        "One, or fewer than about four standpoints per worker, is not worth the pool startup.",
    )
    parser.add_argument("--tag", default="korenmarkt")
    parser.add_argument("--walk-radius-m", type=float, default=90.0)
    parser.add_argument("--walk-spacing-m", type=float, default=3.0)
    parser.add_argument("--site", default="korenmarkt")
    parser.add_argument("--crop-m", type=int, default=250)
    parser.add_argument(
        "--tag-suffix",
        default="",
        help="Appended to the cross site run tag, so a rerun does not land on a published run's files",
    )
    parser.add_argument("--all-sites", action="store_true")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--report", metavar="STEM", default=None)
    parser.add_argument("--cities-report", action="store_true")
    parser.add_argument("--coverage-report", action="store_true")
    parser.add_argument(
        "--coverage-ladder",
        action="store_true",
        help="trace every rung of every site's evidence ladder at --crop-m, on each of --ladder-seeds, "
        "then report the shift per site with its standard error over the seeds",
    )
    parser.add_argument(
        "--ladder-seeds",
        default="7",
        help="comma separated seeds. Each redraws the walk and the per standpoint ray streams "
        "together, so they are disjoint replicates of the whole measurement",
    )
    parser.add_argument(
        "--ladder-sites",
        default=None,
        help="comma separated sites, default every site that has a binding at --crop-m",
    )
    args = parser.parse_args(argv)

    if args.cities_report:
        cross_city_report(list(SITES), args.frequency_ghz * 1e9, crop_m=args.crop_m, tag_suffix=args.tag_suffix)
        return 0

    if args.coverage_report:
        coverage_report(
            args.frequency_ghz * 1e9,
            tag_suffix=args.tag_suffix,
            site=args.site,
            crop_m=args.crop_m,
            seed=args.seed,
        )
        return 0

    if args.coverage_ladder:
        run_coverage_ladder(
            args.locations,
            args.rays,
            args.frequency_ghz * 1e9,
            variant=args.variant,
            seeds=tuple(int(value) for value in args.ladder_seeds.split(",")),
            local_cells=args.local_cells,
            walk_radius_m=args.walk_radius_m,
            walk_spacing_m=args.walk_spacing_m,
            max_bounces=args.max_bounces,
            sites=tuple(args.ladder_sites.split(",")) if args.ladder_sites else SITES,
            crop_m=args.crop_m,
            tag_suffix=args.tag_suffix,
            workers=args.workers,
        )
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
            tag_suffix=args.tag_suffix,
            workers=args.workers,
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
        walk_npz=pathlib.Path(args.walk_npz) if args.walk_npz else None,
        workers=args.workers,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
