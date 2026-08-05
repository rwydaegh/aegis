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

import json
import os
import pathlib
from typing import Any, Sequence

from semantic_twin import paths
from semantic_twin.exposure.reuse import reusable as reusable_output
from semantic_twin.illumination import ISOTROPIC, ROOFTOP, STREET_SMALL_CELL
from semantic_twin.materials import (
    bind_fishnet,
    bind_surface_atlas,
    bind_walk_entities,
    bind_walk_materials,
    classify_faces,
    load_table,
)
from semantic_twin.paths import site_mesh
from semantic_twin.exposure import BodyCoupler, describe
from semantic_twin.exposure.validation import validate as validate_exposure
from semantic_twin.exposure.execution import ExecutionConfig, StudyEnvironment, execute
from semantic_twin.exposure.sweeps import (
    CitySweepConfig,
    LadderSweepConfig,
    SweepEnvironment,
    run_all_sites as execute_all_sites,
    run_coverage_ladder as execute_coverage_ladder,
)
from semantic_twin.propagation.geometry import MitsubaGeometry
from semantic_twin.report.coverage import (
    CoverageReportConfig,
    CoverageReportEnvironment,
    LadderReportConfig,
    LadderReportEnvironment,
    _against_baseline,
    _one_value,
    _spread,
    coverage_ladder_report as write_coverage_ladder_report,
    coverage_report as write_coverage_report,
    ladder_markdown,
    plot_cross_site_ladder,
)
from semantic_twin.report.exposure import cross_city_report as write_cross_city_report
from semantic_twin.report.exposure import report as exposure_report
from semantic_twin.sites import STUDY_ORDER
from semantic_twin.transport.tracer import (
    SbrTracer,
    TraceConfig,
    trace_standpoints,
)
from semantic_twin.runconfig import RunConfig
from semantic_twin.walk import build_walk, ground_datum, measure_ground_datum, site_walk, stratified_subset
from semantic_twin.vision.surface_atlas import load_surface_atlas

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

ROOT = paths.root()
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


def site_surface_atlas(site: str, crop_m: int) -> pathlib.Path | None:
    """The default joint barycentric atlas for one exact support mesh."""
    path = paths.joint_atlas(site, crop_m, resolution=8)
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
SITES = STUDY_ORDER


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
    return validate_exposure(MODELS, CONFIG, rays)


def run(config: RunConfig, execution: ExecutionConfig | None = None) -> pathlib.Path:
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
    return execute(config, execution or ExecutionConfig(), _execution_environment())


def _execution_environment() -> StudyEnvironment:
    return StudyEnvironment(
        output=OUTPUT,
        material_config=CONFIG,
        semantics=SEMANTICS,
        phantom=PHANTOM,
        phantom_mass_kg=PHANTOM_MASS_KG,
        reference_s0_w_m2=REFERENCE_S0_W_M2,
        frequency_note=FREQUENCY_NOTE,
        crop_bound_note=CROP_BOUND_NOTE,
        datum_cross_check_m=DATUM_CROSS_CHECK_M,
        models=MODELS,
        site_mesh=site_mesh,
        registered_ground_z=registered_ground_z,
        site_walk_semantics=site_walk_semantics,
        site_fishnet=site_fishnet,
        geometry_type=MitsubaGeometry,
        classify_faces=classify_faces,
        bind_fishnet=bind_fishnet,
        bind_walk_entities=bind_walk_entities,
        bind_walk_materials=bind_walk_materials,
        load_table=load_table,
        build_walk=build_walk,
        site_walk=site_walk,
        measure_ground_datum=measure_ground_datum,
        stratified_subset=stratified_subset,
        trace_config_type=TraceConfig,
        tracer_type=SbrTracer,
        trace_standpoints=trace_standpoints,
        body_coupler_type=BodyCoupler,
        describe_body=describe,
        report=report,
        site_surface_atlas=site_surface_atlas,
        load_surface_atlas=load_surface_atlas,
        bind_surface_atlas=bind_surface_atlas,
    )


def report(stem: str) -> pathlib.Path:
    """Regenerate the CDF figure and the numbers behind it from the JSONL."""
    return exposure_report(stem, OUTPUT)


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
    config = CoverageReportConfig(frequency_hz, tag_suffix, site, crop_m, seed)
    environment = CoverageReportEnvironment(
        output=OUTPUT,
        rungs_for=coverage_ladder,
        key_for=ladder_key,
        model_keys=LADDER_MODELS,
        compare_to_baseline=_against_baseline,
    )
    return write_coverage_report(config, environment)


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


def reusable(config: RunConfig) -> bool:
    """Whether a run already on disk is the run this sweep would produce.

    Existing and complete is not enough. Korenmarkt's three published 130 m
    stems are complete runs of 120 standpoints made under the superseded
    elevation law, and a resume that accepted them on the file names alone would
    put a different physics into one row of a cross site table and print nothing
    about it. Every field that changes the number is checked, and a rung is
    retraced whenever any of them disagrees.
    """
    return reusable_output(config, OUTPUT, MODELS)


def run_coverage_ladder(
    config: RunConfig,
    execution: ExecutionConfig,
    sweep: LadderSweepConfig,
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
    return execute_coverage_ladder(config, execution, sweep, _sweep_environment())


def coverage_ladder_report(
    sites: list[str],
    crop_m: int,
    seeds: tuple[int, ...],
    frequency_hz: float,
    **options: Any,
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
    config = LadderReportConfig(
        sites,
        crop_m,
        seeds,
        frequency_hz,
        tag_suffix=options.pop("tag_suffix", ""),
        refused=options.pop("refused", None),
        failures=options.pop("failures", None),
    )
    if options:
        raise TypeError(f"unknown coverage ladder report options: {', '.join(sorted(options))}")
    environment = LadderReportEnvironment(
        output=OUTPUT,
        key_for=ladder_key,
        model_keys=LADDER_MODELS,
        one_value=_one_value,
        spread=_spread,
        plotter=plot_cross_site_ladder,
        markdown=ladder_markdown,
    )
    return write_coverage_ladder_report(config, environment)


def run_all_sites(config: RunConfig, execution: ExecutionConfig, sweep: CitySweepConfig) -> None:
    """One geometric materials run per site, then the cross city figure.

    The material treatment is held constant across sites on purpose. Only nine
    of these sites have no panorama coverage at all, so a per site semantic
    binding is not available, and a comparison in which the materials also
    varied would confound geometry with material assignment. What varies here
    is urban form, which is the question.
    """
    execute_all_sites(config, execution, sweep, _sweep_environment())


def _sweep_environment() -> SweepEnvironment:
    return SweepEnvironment(
        output=OUTPUT,
        phantom=PHANTOM,
        phantom_mass_kg=PHANTOM_MASS_KG,
        body_coupler_type=BodyCoupler,
        site_mesh=site_mesh,
        ladder_sites=ladder_sites,
        coverage_ladder=coverage_ladder,
        reusable=reusable,
        execute=run,
        coverage_report=coverage_report,
        coverage_ladder_report=coverage_ladder_report,
        cross_city_report=cross_city_report,
    )


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
    return write_cross_city_report(
        sites,
        frequency_hz,
        crop_m=crop_m,
        tag_suffix=tag_suffix,
        sites_expected=sites_expected,
        output=OUTPUT,
        reference_s0_w_m2=REFERENCE_S0_W_M2,
        crop_bound_note=CROP_BOUND_NOTE,
    )
