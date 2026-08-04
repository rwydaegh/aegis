"""The exact commands the golden lock covers, and how to reduce their output.

Both `capture.py` and `../test_golden_regression.py` import this table, so the
command that wrote a fixture and the command that checks it cannot drift apart.

Every case names its own ``--tag``, so nothing here can overwrite a published
run. The tags all begin with ``golden_``.

Sizing rule for the cases: each one must be cheap enough to run on a four vCPU
box with no GPU, and must still move if the physics moves. The smallest real
physics effect measured while these were chosen is the material binding, which
shifts ``chi_rooftop`` by 0.34 % at the least affected standpoint and by 12.7 %
at the most affected one. Every tolerance below sits many orders of magnitude
under that.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
from dataclasses import dataclass, field
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
GOLDEN_DIR = pathlib.Path(__file__).resolve().parent

#: Where `run_exposure.py` writes. Named for one city and holds all eleven,
#: which TANGLE.md knot 8 records. Read, never written to by anything here
#: outside the ``golden_`` tags.
EXPOSURE_OUT = ROOT / "outputs" / "exposure_korenmarkt"
NEXT_EVENT_OUT = ROOT / "outputs" / "next_event"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class Case:
    """One command, its tier, and the reduction that turns its output into a fixture."""

    ident: str
    driver: str
    argv: tuple[str, ...]
    tier: str
    what_it_locks: str
    #: Files the driver writes for this case, relative to the study root. Used
    #: only to report what a rerun overwrites.
    writes: tuple[str, ...] = field(default_factory=tuple)
    #: Which reduction reads this case's output. Defaults to the one implied by
    #: the driver.
    kind: str = ""
    #: Case idents that must have run first. ``--cities-report`` reads the per
    #: site rows off disk and traces nothing, so on its own it would compare an
    #: aggregate of whatever happened to be there.
    prerequisites: tuple[str, ...] = field(default_factory=tuple)
    #: Globs under ``outputs/`` to delete before the command runs, so that a
    #: driver which resumes from disk traces instead of reading. Every pattern
    #: has to name the ``golden`` tag; ``clear()`` refuses anything else.
    clears: tuple[str, ...] = field(default_factory=tuple)

    @property
    def fixture(self) -> pathlib.Path:
        return GOLDEN_DIR / f"{self.ident}.json"

    def command(self) -> list[str]:
        return [self.driver, *self.argv]

    def clear(self) -> list[str]:
        """Delete this case's own previous output. Returns what went.

        ``--coverage-ladder`` resumes: ``run_exposure.reusable()`` accepts a rung
        already on disk whose settings match, and prints ``[have]``. That is
        right for a sweep and wrong for a golden test, which took 1.7 s and
        re-read three runs instead of making them. Only paths carrying the
        golden tag are ever removed, so a published stem cannot be caught by a
        careless pattern.
        """
        gone: list[str] = []
        for pattern in self.clears:
            for path in sorted((ROOT / "outputs").glob(pattern)):
                if "golden" not in path.name:
                    raise ValueError(f"{self.ident} would delete {path}, which is not a golden run")
                path.unlink()
                gone.append(str(path.relative_to(ROOT)))
        return gone

    def reduce(self) -> dict[str, Any]:
        which = self.kind or ("exposure" if self.driver == "run_exposure.py" else "next_event")
        if which == "exposure":
            return reduce_exposure(self)
        if which == "next_event":
            return reduce_next_event(self)
        if which == "all_sites":
            return reduce_all_sites(self)
        if which == "cities_summary":
            return reduce_all_sites(self, rows=False)
        if which == "coverage_ladder":
            return reduce_coverage_ladder(self)
        raise ValueError(f"no reduction called {which!r}")


def _arg(case: Case, flag: str, default: str | None = None) -> str:
    argv = list(case.argv)
    if flag in argv:
        return argv[argv.index(flag) + 1]
    if default is None:
        raise KeyError(f"{case.ident} has no {flag} and no default")
    return default


def reduce_exposure(case: Case) -> dict[str, Any]:
    """Per standpoint rows, the manifest fields that decide them, and the spectra.

    The rows are kept whole rather than sampled. Sixteen standpoints times forty
    scalars is thirty kilobytes of JSON, and a sample would leave most of the
    published quantities unlocked for no saving worth having.

    ``rho_rooftop`` is the angular power spectrum, five hundred and twelve cells
    per standpoint. That is too large to keep, so it is locked by a hash of the
    whole array plus three reductions per standpoint. The hash catches any change
    at all. The reductions say something useful when a machine reproduces the
    physics but not the last bit.
    """
    import numpy as np

    tag = _arg(case, "--tag")
    ghz = float(_arg(case, "--frequency-ghz", "15.0"))
    stem = f"{tag}_{ghz:g}ghz"
    rows_path = EXPOSURE_OUT / f"{stem}_locations.jsonl"
    manifest = json.loads((EXPOSURE_OUT / f"{stem}_manifest.json").read_text())
    rows = [json.loads(line) for line in rows_path.read_text().splitlines() if line.strip()]
    for row in rows:
        row.pop("seconds", None)

    spectra = np.load(EXPOSURE_OUT / f"{stem}_spectra.npz")
    rho = np.asarray(spectra["rho_rooftop"], dtype=np.float64)
    grid = np.asarray(spectra["local_grid"], dtype=np.float64)
    solid = np.asarray(spectra["solid_angle"], dtype=np.float64)

    return {
        "kind": "exposure",
        "scene": {
            "site": manifest["site"],
            "mesh": pathlib.Path(manifest["mesh"]).name,
            "mesh_triangles": manifest["mesh_triangles"],
            "crop_radius_m": manifest["crop_radius_m"],
            "ground_datum_m": manifest["ground_datum_m"],
            "ground_datum_rule": manifest["ground_datum_source"],
            "ground_datum_band_fraction": manifest["ground_datum"].get("band_fraction"),
            "reference_s0_w_m2": manifest["reference_s0_w_m2"],
            "class_area_fractions": manifest["class_area_fractions"],
            "semantic_covered_fraction_by_face": manifest["semantic_binding"].get("covered_fraction_by_face"),
            "semantic_covered_fraction_by_area": manifest["semantic_binding"].get("covered_fraction_by_area"),
            # How the fishnet faces were matched back onto the tracer mesh. This
            # is the provenance the SurfaceBinding wave is meant to make
            # mandatory, and it is the field that says whether a run joined two
            # different meshes. Korenmarkt does: its fishnet was cut against
            # inhouse_leaf_130m.ply and the trace reads the f64 rebuild, so the
            # match keeps 86.65 % of the source triangles at a median centroid
            # distance of 0.249 m. Prague cuts and traces the same file and
            # matches 100 % at zero distance.
            "semantic_mesh_match": manifest["semantic_binding"].get("mesh_match"),
            # Triangles per material class, as integers. The area fractions above
            # can be reproduced by an accident of arithmetic; a count of 3,271
            # triangles at Korenmarkt and 38,222 at Prague, split across eleven
            # classes, cannot.
            "chosen_material_triangle_counts": manifest["semantic_binding"].get("chosen_material_triangle_counts"),
            "materials": manifest["semantic_binding"]["materials"],
            "surface_binding_classes": manifest["surface_binding"]["classes"],
            "walk_candidates": manifest["walk"].get("count"),
            "walk_provenance": manifest["walk"],
            "locations_traced": manifest["locations_traced"],
            "trace_config": manifest["trace_config"],
            "illumination_models": manifest["illumination_models"],
            "body": manifest["body"],
        },
        "rows": rows,
        "spectra": {
            "shape": list(rho.shape),
            "sha256": _sha256(rho.tobytes()),
            "grid_sha256": _sha256(grid.tobytes()),
            "solid_angle_sha256": _sha256(solid.tobytes()),
            "solid_angle_total": float(solid.sum()),
            "per_location": [{"sum": float(r.sum()), "max": float(r.max()), "argmax": int(r.argmax())} for r in rho],
        },
    }


#: Below this many held out standpoints, a median is not a distribution. The
#: number is not a threshold anything acts on, only the point at which the
#: fixture starts saying so out loud.
THIN_HELD_OUT = 8


def reduce_next_event(case: Case) -> dict[str, Any]:
    """The whole payload minus wall times, with a warning on the thin rows.

    The warning is written into the fixture rather than left in a note, because
    the fixture is what a later reader will open. At Korenmarkt the driver's own
    defaults hold out two standpoints, so the median it prints is a median of
    two, and the fifth and ninety fifth percentiles either side of it are those
    same two points. That is a real property of the run and it is locked as one,
    but nobody should read it as a stable statistic.
    """
    tag = _arg(case, "--tag")
    crop = _arg(case, "--crop-m", "250")
    payload = json.loads((NEXT_EVENT_OUT / f"{tag}_{crop}m.json").read_text())
    for row in payload["rows"]:
        row.pop("seconds", None)
        if row["held_out"] < THIN_HELD_OUT:
            row["held_out_warning"] = (
                f"{row['held_out']} standpoints. surplus_db_median is a median of "
                f"{row['held_out']}, and surplus_db_p5 and surplus_db_p95 are drawn from the "
                f"same {row['held_out']} points. The capture route at this site is shorter "
                f"than the split rule assumes, so the rule shrinks the held out set. Locked "
                f"as the behaviour that exists, NOT as a converged number."
            )
    return {"kind": "next_event", "payload": payload}


def _rows_of(stem: str) -> list[dict[str, Any]]:
    rows = [
        json.loads(line) for line in (EXPOSURE_OUT / f"{stem}_locations.jsonl").read_text().splitlines() if line.strip()
    ]
    for row in rows:
        row.pop("seconds", None)
    return rows


def reduce_all_sites(case: Case, *, rows: bool = True) -> dict[str, Any]:
    """Every site's standpoints, and the cross city table built from them.

    Two things are locked here and they fail in different ways. The per site
    rows catch a geometry regression at a square nobody else samples. The
    ``cities`` summary catches a change in the reduction that turns those rows
    into the published table, which is a separate piece of arithmetic and a
    prime refactor target.

    ``sites_present``, ``sites_expected``, ``complete`` and ``ragged_locations``
    are kept deliberately. A partial sweep once became a published figure, and
    those four fields are the driver's own answer to that. If a refactor drops
    them the fixture says so.

    ``rows=False`` keeps only the table. It is what the report only case uses,
    since the standpoints under it are already locked by the sweep and there is
    no reason to hold two copies of two hundred kilobytes.
    """
    crop = int(_arg(case, "--crop-m", "130"))
    suffix = _arg(case, "--tag-suffix", "")
    ghz = float(_arg(case, "--frequency-ghz", "15.0"))
    prefix = "city" if crop == 130 else f"city{crop}"

    summary_path = EXPOSURE_OUT / f"cities{crop}{suffix}_{ghz:g}ghz_summary.json"
    summary = json.loads(summary_path.read_text())

    if not rows:
        return {"kind": "cities_summary", "cities_summary": summary}

    per_site: dict[str, Any] = {}
    for site in sorted(summary["sites"]):
        stem = f"{prefix}{suffix}_{site}_{ghz:g}ghz"
        manifest = json.loads((EXPOSURE_OUT / f"{stem}_manifest.json").read_text())
        per_site[site] = {
            "mesh": pathlib.Path(manifest["mesh"]).name,
            "mesh_triangles": manifest["mesh_triangles"],
            "ground_datum_m": manifest["ground_datum_m"],
            "ground_datum_rule": manifest["ground_datum_source"],
            "class_area_fractions": manifest["class_area_fractions"],
            "walk_candidates": manifest["walk"].get("candidates_after_clearance"),
            "locations_traced": manifest["locations_traced"],
            "rows": _rows_of(stem),
        }
    return {"kind": "all_sites", "cities_summary": summary, "per_site": per_site}


def reduce_coverage_ladder(case: Case) -> dict[str, Any]:
    """The evidence ladder: one run per rung, and the two reports over them.

    The rungs are geometric, then the per view fishnet surfaces, then the fused
    stations. The whole point of the experiment is that only the material
    binding changes between them, so the per rung coverage fractions are locked
    beside the numbers they moved.
    """
    crop = int(_arg(case, "--crop-m", "130"))
    suffix = _arg(case, "--tag-suffix", "")
    ghz = float(_arg(case, "--frequency-ghz", "15.0"))
    seeds = [int(s) for s in _arg(case, "--ladder-seeds", "7").split(",")]
    sites = _arg(case, "--ladder-sites").split(",")

    import run_exposure  # the tag rule is the driver's, not a copy of it

    ladders: dict[str, Any] = {}
    rungs: dict[str, Any] = {}
    for site in sites:
        for seed in seeds:
            key = run_exposure.ladder_key(site, crop, seed)
            report = EXPOSURE_OUT / f"coverage_ladder{key}{suffix}_{ghz:g}ghz.json"
            ladders[f"{site}_s{seed}"] = json.loads(report.read_text())
            for tag, materials, _description in run_exposure.coverage_ladder(site, crop, seed):
                stem = f"{tag}{suffix}_{ghz:g}ghz"
                manifest = json.loads((EXPOSURE_OUT / f"{stem}_manifest.json").read_text())
                rungs[stem] = {
                    "materials": materials,
                    "covered_fraction_by_face": manifest["semantic_binding"].get("covered_fraction_by_face"),
                    "covered_fraction_by_area": manifest["semantic_binding"].get("covered_fraction_by_area"),
                    "mesh_match": manifest["semantic_binding"].get("mesh_match"),
                    "chosen_material_triangle_counts": manifest["semantic_binding"].get(
                        "chosen_material_triangle_counts"
                    ),
                    "class_area_fractions": manifest["class_area_fractions"],
                    "surface_binding_classes": manifest["surface_binding"]["classes"],
                    "rows": _rows_of(stem),
                }
    cross = EXPOSURE_OUT / f"coverage_ladder_cross_site_{crop}m{suffix}_{ghz:g}ghz.json"
    return {
        "kind": "coverage_ladder",
        "cross_site": json.loads(cross.read_text()) if cross.exists() else None,
        "per_site_ladder": ladders,
        "rungs": rungs,
    }


#: Fast tier. Runs in well under a minute on four vCPUs and still traces a real
#: city mesh with real Fresnel coefficients against a real phantom.
#:
#: Slow tier. The configurations closest to what the study publishes. About
#: three minutes for the four of them together.
CASES: tuple[Case, ...] = (
    Case(
        ident="exposure_korenmarkt_130m_geometric_fast",
        driver="run_exposure.py",
        argv=(
            "--site",
            "korenmarkt",
            "--crop-m",
            "130",
            "--locations",
            "8",
            "--rays",
            "50000",
            "--local-cells",
            "512",
            "--frequency-ghz",
            "15.0",
            "--materials",
            "geometric",
            "--seed",
            "7",
            "--workers",
            "1",
            "--tag",
            "golden_km130_geo_fast",
        ),
        tier="fast",
        what_it_locks=(
            "The escape estimator end to end on the Korenmarkt 130 m mesh: ground datum, "
            "walkable grid, triangle orientation materials, three illumination laws, and "
            "the Duke phantom coupling."
        ),
        writes=("outputs/exposure_korenmarkt/golden_km130_geo_fast_15ghz_*",),
    ),
    Case(
        ident="next_event_korenmarkt_130m_fast",
        driver="run_next_event.py",
        argv=(
            "--sites",
            "korenmarkt",
            "--crop-m",
            "130",
            "--rays",
            "50000",
            "--builders",
            "32",
            "--held-out",
            "16",
            "--azimuths",
            "720",
            "--elevations",
            "300",
            "--cell-m",
            "1.0",
            "--dims",
            "3",
            "--connections",
            "1",
            "--frequency-hz",
            "15000000000.0",
            "--max-bounces",
            "3",
            "--walk",
            "route",
            "--walk-path",
            "links",
            "--walk-stride-m",
            "6.0",
            "--seed",
            "7",
            "--tag",
            "golden_ne_km130_fast",
        ),
        tier="fast",
        what_it_locks=(
            "The second estimator: skyline extraction, the explicit source set on facade "
            "tips, the exact line of sight term, and next event connection at every path "
            "vertex. Also carries the escape estimator's own surplus for the same points, "
            "so the factor of three gap between the two is locked as a number."
        ),
        writes=("outputs/next_event/golden_ne_km130_fast_130m.json",),
    ),
    Case(
        ident="exposure_korenmarkt_130m_geometric",
        driver="run_exposure.py",
        argv=(
            "--site",
            "korenmarkt",
            "--crop-m",
            "130",
            "--locations",
            "16",
            "--rays",
            "200000",
            "--local-cells",
            "512",
            "--frequency-ghz",
            "15.0",
            "--materials",
            "geometric",
            "--seed",
            "7",
            "--workers",
            "2",
            "--tag",
            "golden_km130_geo",
        ),
        tier="slow",
        what_it_locks="The fast case at the published ray count, 200 000 per standpoint.",
        writes=("outputs/exposure_korenmarkt/golden_km130_geo_15ghz_*",),
    ),
    Case(
        ident="exposure_korenmarkt_130m_walk",
        driver="run_exposure.py",
        argv=(
            "--site",
            "korenmarkt",
            "--crop-m",
            "130",
            "--locations",
            "8",
            "--rays",
            "200000",
            "--local-cells",
            "512",
            "--frequency-ghz",
            "15.0",
            "--materials",
            "walk",
            "--seed",
            "7",
            "--workers",
            "2",
            "--tag",
            "golden_km130_walk",
        ),
        tier="slow",
        what_it_locks=(
            "The image evidence arm. Korenmarkt at 130 m is the only place the fused "
            "Mapillary station binding reaches the mesh, 6.88 % of faces and 10.57 % of "
            "area. Against the geometric case at the same eight standpoints it moves "
            "chi_rooftop between +0.00 % and +12.69 %, so this fixture is what stops a "
            "refactor from silently disconnecting the materials."
        ),
        writes=("outputs/exposure_korenmarkt/golden_km130_walk_15ghz_*",),
    ),
    Case(
        ident="exposure_brussels_250m_geometric",
        driver="run_exposure.py",
        argv=(
            "--site",
            "brussels_grandplace",
            "--crop-m",
            "250",
            "--locations",
            "16",
            "--rays",
            "200000",
            "--local-cells",
            "512",
            "--frequency-ghz",
            "15.0",
            "--materials",
            "geometric",
            "--seed",
            "7",
            "--workers",
            "2",
            "--tag",
            "golden_bru250_geo",
        ),
        tier="slow",
        what_it_locks=(
            "A second city at the published 250 m crop radius. Catches anything that is "
            "accidentally specific to Korenmarkt, which is the site every hardcoded path "
            "in the driver names."
        ),
        writes=("outputs/exposure_korenmarkt/golden_bru250_geo_15ghz_*",),
    ),
    Case(
        ident="next_event_250m_default",
        driver="run_next_event.py",
        argv=(
            "--sites",
            "korenmarkt",
            "brussels_grandplace",
            "--crop-m",
            "250",
            "--rays",
            "200000",
            "--builders",
            "128",
            "--held-out",
            "16",
            "--azimuths",
            "1440",
            "--elevations",
            "600",
            "--cell-m",
            "1.0",
            "--dims",
            "3",
            "--connections",
            "1",
            "--frequency-hz",
            "15000000000.0",
            "--max-bounces",
            "3",
            "--walk",
            "route",
            "--walk-path",
            "links",
            "--walk-stride-m",
            "6.0",
            "--seed",
            "7",
            "--tag",
            "golden_ne_250m",
        ),
        tier="slow",
        what_it_locks=(
            "run_next_event.py on every one of its own defaults, at both pilot squares. "
            "This is the configuration behind the +0.30 to +0.57 dB multipath surplus."
        ),
        writes=("outputs/next_event/golden_ne_250m_250m.json",),
    ),
    Case(
        ident="exposure_korenmarkt_130m_semantic",
        driver="run_exposure.py",
        argv=(
            "--site",
            "korenmarkt",
            "--crop-m",
            "130",
            "--locations",
            "8",
            "--rays",
            "200000",
            "--local-cells",
            "512",
            "--frequency-ghz",
            "15.0",
            "--materials",
            "semantic",
            "--seed",
            "7",
            "--workers",
            "2",
            "--tag",
            "golden_km130_semantic",
        ),
        tier="slow",
        what_it_locks=(
            "The fishnet binding route through bind(), which is the one physics path that "
            "had no lock at all. Korenmarkt is the site: outputs/korenmarkt_fishnet_vistas "
            "holds four per view surface sets cut against inhouse_leaf_130m.ply, and the "
            "run traces the f64 rebuild, so this also locks the cross mesh join that "
            "site_fishnet() passes through: 86.65 % of source triangles matched, 13.32 % "
            "refused on the normal test, median centroid distance 0.249 m. It reaches "
            "2.07 % of faces and 3.13 % of area and adds eleven semantic_* material "
            "classes, so class_area_fractions and the 3,271 triangle chosen counts are a "
            "fingerprint of bind() itself. Waves 2 and 3 restructure this into "
            "SurfaceBinding with mandatory provenance, and mesh_match is that provenance."
        ),
        writes=("outputs/exposure_korenmarkt/golden_km130_semantic_15ghz_*",),
    ),
    Case(
        ident="exposure_prague_130m_semantic",
        driver="run_exposure.py",
        argv=(
            "--site",
            "prague_staromestske",
            "--crop-m",
            "130",
            "--locations",
            "8",
            "--rays",
            "200000",
            "--local-cells",
            "512",
            "--frequency-ghz",
            "15.0",
            "--materials",
            "semantic",
            "--seed",
            "7",
            "--workers",
            "2",
            "--tag",
            "golden_prague130_semantic",
        ),
        tier="slow",
        what_it_locks=(
            "The fishnet binding again, where it actually reaches the mesh. Korenmarkt "
            "binds 3.13 % of area and Prague binds 32.95 %, from 52 per view surface sets, "
            "so this is the case in which a broken bind() shows up as a large number "
            "rather than a small one. Measured against the same run with geometric "
            "materials, the binding moves chi_rooftop here by +2.2 % to +59.1 % per "
            "standpoint and +0.45 dB on the median. "
            "It is also the clean half of the mesh join. Prague cuts and traces the same "
            "file, inhouse_leaf_130m.ply, and matches 100 % of source triangles at zero "
            "distance. Korenmarkt cuts against inhouse_leaf_130m.ply and traces the f64 "
            "rebuild, so it matches 86.65 % at a median centroid distance of 0.249 m. "
            "Holding both sides means a refactor that breaks the join fails in a way that "
            "says which half broke."
        ),
        writes=("outputs/exposure_korenmarkt/golden_prague130_semantic_15ghz_*",),
    ),
    Case(
        ident="cities_250m_all_sites",
        driver="run_exposure.py",
        argv=(
            "--all-sites",
            "--crop-m",
            "250",
            "--locations",
            "8",
            "--rays",
            "200000",
            "--local-cells",
            "512",
            "--frequency-ghz",
            "15.0",
            "--seed",
            "7",
            "--workers",
            "2",
            "--tag-suffix",
            "_golden",
        ),
        tier="slow",
        what_it_locks=(
            "All eleven squares at the published 250 m crop, and the cross city table built "
            "from them. Two different failures: the per site rows catch a geometry "
            "regression at a square nothing else samples, and cities250_golden_15ghz_summary "
            "catches a change in the reduction from rows to table. The completeness fields "
            "are locked too, because a partial sweep once became a published figure."
        ),
        writes=(
            "outputs/exposure_korenmarkt/city250_golden_<site>_15ghz_*",
            "outputs/exposure_korenmarkt/cities250_golden_15ghz_summary.json",
        ),
        kind="all_sites",
    ),
    Case(
        ident="cities_250m_report_only",
        driver="run_exposure.py",
        argv=(
            "--cities-report",
            "--crop-m",
            "250",
            "--frequency-ghz",
            "15.0",
            "--tag-suffix",
            "_golden",
        ),
        tier="slow",
        what_it_locks=(
            "The aggregation on its own, with no tracing at all. It reads the eleven per "
            "site row files the case above wrote and rebuilds the table, so a refactor that "
            "changes only the reduction fails here in seconds rather than after a nine "
            "minute sweep."
        ),
        writes=("outputs/exposure_korenmarkt/cities250_golden_15ghz_summary.json",),
        kind="cities_summary",
        prerequisites=("cities_250m_all_sites",),
    ),
    Case(
        ident="coverage_ladder_korenmarkt_130m",
        driver="run_exposure.py",
        argv=(
            "--coverage-ladder",
            "--ladder-sites",
            "korenmarkt",
            "--ladder-seeds",
            "7",
            "--crop-m",
            "130",
            "--locations",
            "8",
            "--rays",
            "200000",
            "--local-cells",
            "512",
            "--frequency-ghz",
            "15.0",
            "--workers",
            "2",
            "--tag-suffix",
            "_golden",
        ),
        tier="slow",
        what_it_locks=(
            "The evidence ladder, which is the experiment that says whether the material "
            "assignment matters. Three rungs at one site and one seed: orientation rule, "
            "fishnet surfaces, fused stations, with everything but the binding held fixed. "
            "It locks the three runs, the per site ladder report and the cross site report. "
            "The tag suffix is mandatory here and the driver enforces it: without one the "
            "sweep would overwrite the published korenmarkt_geometric, korenmarkt_semantic "
            "and korenmarkt_walk stems, which hold 120 standpoint runs made under the "
            "superseded illumination law."
        ),
        writes=(
            "outputs/exposure_korenmarkt/korenmarkt_{geometric,semantic,walk}_golden_15ghz_*",
            "outputs/exposure_korenmarkt/coverage_ladder_golden_15ghz.json",
            "outputs/exposure_korenmarkt/coverage_ladder_cross_site_130m_golden_15ghz.json",
        ),
        kind="coverage_ladder",
        clears=(
            "exposure_korenmarkt/korenmarkt_geometric_golden_15ghz*",
            "exposure_korenmarkt/korenmarkt_semantic_golden_15ghz*",
            "exposure_korenmarkt/korenmarkt_walk_golden_15ghz*",
        ),
    ),
)

CASES_BY_ID = {case.ident: case for case in CASES}

#: Relative tolerance for the scalar comparison.
#:
#: Chosen from measurement, not from taste. On this box the drivers reproduce
#: bit for bit across repeat runs and across worker counts, so the honest
#: tolerance for a same seed rerun is zero. It is set to 1e-12 instead to leave
#: room for the one drift the suite already documents: tests/test_determinism.py
#: records that the two elevation weighted susceptibilities move by one or two
#: units in the last place across machines, because they go through arcsin and
#: libm is not standardised. 1e-12 is about four thousand units in the last
#: place, and it is nine orders of magnitude below the smallest physics effect
#: any of these cases carries.
RTOL = 1.0e-12

#: Absolute floor, for quantities that legitimately pass through zero.
ATOL = 1.0e-300

#: What a real change looks like, so a failure can be read. Measured over five
#: seeds of ``exposure_korenmarkt_130m_geometric``, written into MANIFEST.json
#: by capture.py under ``seed_spread``. A deviation above this is not a rounding
#: question.
PHYSICS_SCALE_HINT = "see MANIFEST.json -> seed_spread"
