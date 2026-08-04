"""One table saying what image evidence each of the eleven sites actually has.

The eleven city table in `REPORT.md` was produced with `--materials geometric`
at every site, so its covered area fraction is 0.000 everywhere and no number
in it depends on a photograph. That is not visible from the table itself, and
the pieces needed to see it are scattered across `data/panoramas`,
`outputs/site_semantics`, `outputs/*_fishnet_vistas` and the pose files. This
collects them into one row per site.

The column that matters most is not the panorama count. It is the number of
poses that survive both admission tests. `summarise_site_panoramas.py` already
reports the skyline residual, which is the gate the acquisition shipped
against, and the residual is blind to the failure mode that decides whether a
pose is usable: a camera driven inside the geometry matches the inside of a
wall and scores well doing it. The second test is the sky conflict recorded in
each `pose_aligned.json`, the fraction of directions the segmentation calls sky
for which the support mesh returns a first hit, together with how far away the
conflicting surface is. Both are reported here, separately, so the disagreement
between them is on the page rather than in a footnote.

Run from the `semantic_twin` directory::

    ../../../.venv/bin/python summarise_evidence_coverage.py
    ../../../.venv/bin/python summarise_evidence_coverage.py --crop-m 130 250
"""

from __future__ import annotations

import json
import pathlib
import statistics
from dataclasses import dataclass
from typing import Any

import numpy as np

from semantic_twin import paths
from semantic_twin.scene.site_semantics import COMPANION_DIRECTORIES, SITES, STATION_PREFIXES, station_verdict

SCRIPT_DIR = paths.root()


def panorama_dirs(site: str) -> list[pathlib.Path]:
    """Directories holding a stitched panorama, not merely a reserved name.

    A run that stopped part way through leaves a directory with metadata and a
    handful of tiles in it. Counting those as panoramas would overstate what the
    site has, so the image on disk is the test. Companion campaigns are included
    on the same terms `build_site_semantics.py` includes them, so the count in
    this table and the station count in a binding are the same population.
    """
    found = []
    for name in (site, *COMPANION_DIRECTORIES.get(site, ())):
        root = paths.panorama_set(name)
        if not root.exists():
            continue
        numbered = sorted(f for prefix in STATION_PREFIXES for f in root.glob(f"{prefix}*") if f.is_dir())
        stitched = [folder for folder in numbered if any(folder.glob("panorama*.jpg"))]
        if not stitched and any(root.glob("panorama*.jpg")):
            stitched = [root]
        found.extend(stitched)
    return found


def fishnet(site: str) -> dict[str, Any]:
    """What was cut, and whether `bind` can reach it.

    Surfaces written one level down, in a folder per panorama, are counted here
    because they exist, and flagged because `bind` globs the top of the
    directory and does not recurse, so they cannot be bound where they sit.
    """
    directory = paths.output(f"{site}_fishnet_vistas")
    if not directory.is_dir():
        return {"views": 0, "faces": 0, "surface_area_m2": 0.0, "layout": "none"}
    files = sorted(directory.glob("*_fishnet.npz"))
    layout = "flat" if files else "none"
    if not files:
        files = sorted(directory.glob("*/*_fishnet.npz"))
        layout = "nested, unreachable by bind" if files else "none"
    faces, area = 0, 0.0
    for path in files:
        with np.load(path, allow_pickle=True) as document:
            faces += int(document["face_class"].size)
            area += float(document["face_area_m2"].sum())
    return {"views": len(files), "faces": faces, "surface_area_m2": area, "layout": layout}


#: Cached beside the fishnet it describes, because measuring it loads the
#: support mesh and binds every view, which is far too slow to do on every
#: report. Refreshed with `--measure-semantic`.
SEMANTIC_COVERAGE = "semantic_coverage.json"


def semantic_coverage(site: str) -> dict[str, Any] | None:
    """What fraction of the mesh the fishnet views cover, if it has been measured."""
    path = paths.output(f"{site}_fishnet_vistas", SEMANTIC_COVERAGE)
    return json.loads(path.read_text()) if path.exists() else None


def measure_semantic_coverage(site: str, *, variant: str = "llvm_ad_rgb") -> dict[str, Any] | None:
    """Bind a site's fishnet onto the mesh it was cut against and cache the answer.

    This is the `--materials semantic` path exactly as `run_exposure.py` runs
    it, against the fishnet's own source mesh, so the number it caches is the
    coverage that run would report rather than an estimate of it.
    """
    # Mitsuba is slow to import and is not needed to read the cache, so the
    # dependency is taken only when a measurement is actually asked for.
    from semantic_twin.exposure import study as run_exposure
    from semantic_twin.materials import bind_fishnet
    from semantic_twin.propagation import MitsubaGeometry

    resolved = run_exposure.site_fishnet(site)
    if resolved is None:
        return None
    directory, mesh = resolved
    geometry = MitsubaGeometry(mesh, variant=variant)
    areas = geometry.face_areas()
    # The geometric classes are the fallback `bind` fills in around the covered
    # triangles. They do not affect the covered fraction, so the datum they are
    # cut at does not either.
    classes = run_exposure.classify_faces(geometry.vertices, geometry.faces, 0.0)
    bound = bind_fishnet(
        geometry.vertices,
        geometry.faces,
        areas,
        classes,
        fishnet_dir=directory,
        semantics_path=run_exposure.SEMANTICS,
        source_ply_vertices=geometry.vertices,
        source_ply_faces=geometry.faces,
    )
    measured = {
        "mesh": mesh.name,
        "views": len(bound.provenance["views"]),
        "covered_fraction_by_face": bound.covered_fraction_by_face,
        "covered_fraction_by_area": bound.covered_fraction_by_area,
    }
    (directory / SEMANTIC_COVERAGE).write_text(json.dumps(measured, indent=2))
    return measured


def fishnet_panoramas(site: str) -> list[str] | None:
    """Which panoramas the fishnet views were cut from, when the names say so.

    Views built per panorama carry the panorama in the file name or in the
    folder holding them. The two single panorama sites carry neither, because
    there was only ever one camera to attribute them to, and inventing an
    attribution for those is worse than returning None.
    """
    directory = paths.output(f"{site}_fishnet_vistas")
    if not directory.is_dir():
        return None
    names = {folder.name for folder in panorama_dirs(site)}
    attributed = set()
    for path in sorted(directory.glob("*_fishnet.npz")) + sorted(directory.glob("*/*_fishnet.npz")):
        stem = path.parent.name if path.parent != directory else path.name
        match = [name for name in names if stem.startswith(name)]
        if match:
            attributed.add(max(match, key=len))
    return sorted(attributed) or None


def binding(site: str, crop_m: int) -> dict[str, Any] | None:
    path = paths.site_semantics(site, crop_m, suffix=".json")
    if path.exists():
        report = json.loads(path.read_text())
        if report.get("result") == "written":
            return {
                "stations": len(report["stations_cast"]),
                "covered_fraction_by_area": report["coverage"]["covered_fraction_by_area"],
                "covered_fraction_by_face": report["coverage"]["covered_fraction_by_face"],
                "source": "street view stations, build_site_semantics.py",
            }
    # Korenmarkt's published 130 m walk binding predates that script.
    legacy = paths.output("walk_korenmarkt", "walk_semantic.json")
    if site == "korenmarkt" and crop_m == 130 and legacy.exists():
        report = json.loads(legacy.read_text())
        return {
            "stations": len(report.get("stations_used", [])),
            "covered_fraction_by_area": None,
            "covered_fraction_by_face": None,
            "source": "mapillary stations, build_walk_twin.py",
        }
    return None


def row(site: str, crops: tuple[int, ...], **gate: float) -> dict[str, Any]:
    folders = panorama_dirs(site)
    poses, backends, material_axis = [], set(), 0
    for folder in folders:
        aligned = folder / "alignment" / "pose_aligned.json"
        meta = folder / "semantics" / "semantics.json"
        if meta.exists():
            document = json.loads(meta.read_text())
            backends.add(str(document.get("backend")))
            # Only the hybrid backend writes the SAM 3 `rf_material` axis. The
            # entity axis is present either way, so the backend is the test.
            material_axis += int(document.get("backend") == "hybrid")
        if not aligned.exists():
            continue
        pose = json.loads(aligned.read_text())
        verdict = station_verdict(pose, **gate)
        verdict["station"] = folder.name
        poses.append(verdict)

    residuals = [p["residual_deg"] for p in poses]
    sigmas = [p["position_sigma_m"] for p in poses if p["position_sigma_m"] is not None]
    admitted = [p for p in poses if p["admitted"]]
    inside = [p for p in poses if p["sky_conflict_state"] == "inside the geometry"]
    sources = fishnet_panoramas(site)
    return {
        "site": site,
        "panoramas": len(folders),
        "registered": len(poses),
        "residual_deg": {
            "median": round(statistics.median(residuals), 3) if residuals else None,
            "max": round(max(residuals), 3) if residuals else None,
        },
        "position_sigma_m": {
            "median": round(statistics.median(sigmas), 3) if sigmas else None,
            "max": round(max(sigmas), 3) if sigmas else None,
        },
        "poses_at_altitude_bound": sum(1 for p in poses if p["dz_at_bound"]),
        "poses_inside_the_geometry": len(inside),
        "poses_inside_and_passing_the_residual_gate": sum(
            1 for p in inside if p["residual_deg"] <= gate["max_residual_deg"]
        ),
        "poses_admitted": len(admitted),
        "semantics_backend": sorted(backends),
        "sam3_material_axis": "hybrid" in backends,
        "panoramas_with_sam3_material_axis": material_axis,
        "fishnet": fishnet(site),
        "semantic_coverage": semantic_coverage(site),
        "fishnet_panoramas": sources,
        # A fishnet cut from a camera that sits inside a wall inherits that
        # camera's error, so a semantic run is only materially bound if the
        # views behind it came from poses that passed both admission tests.
        "fishnet_panoramas_admitted": (
            None if sources is None else sorted(set(sources) & {p["station"] for p in admitted})
        ),
        "bindings": {f"{crop}m": binding(site, crop) for crop in crops},
        "materially_bound_run_possible": {f"{crop}m": binding(site, crop) is not None for crop in crops},
    }


def fishnet_cell(entry: dict[str, Any]) -> str:
    if not entry["faces"]:
        return "none"
    if entry["layout"].startswith("nested"):
        return f"{entry['faces']} nested"
    return str(entry["faces"])


def semantic_cell(r: dict[str, Any]) -> str:
    """Coverage, and how much of it rests on a pose that passed admission."""
    entry = r["semantic_coverage"]
    if entry is None:
        return "not measured"
    cell = f"{100 * entry['covered_fraction_by_area']:.1f}% ({entry['views']} views)"
    sources = r["fishnet_panoramas"]
    if sources is None:
        return f"{cell}, poses unattributed"
    return f"{cell} from {len(r['fishnet_panoramas_admitted'])} of {len(sources)} admitted poses"


def semantic_is_bound(r: dict[str, Any]) -> bool:
    """Whether a semantic run at this site would rest on any admitted pose.

    Times Square has fishnets and no admitted pose, so it has surfaces cut from
    cameras the sky conflict test places inside the buildings they are looking
    at. Calling that materially bound would be the same overclaim this table
    was written to expose.
    """
    entry = r["semantic_coverage"]
    if entry is None or entry["covered_fraction_by_area"] <= 0.0:
        return False
    return bool(r["fishnet_panoramas_admitted"]) or r["fishnet_panoramas"] is None


def bound_run_cell(r: dict[str, Any], crops: tuple[int, ...]) -> str:
    """The routes to a materially bound run, which are not the same route.

    The walk binding fuses whole stations onto the tracer triangles and is
    reported per crop radius. The fishnet binding aggregates per view surfaces
    onto the mesh they were cut against, so it is reported at that mesh.
    """
    routes = [f"walk at {crop} m" for crop in crops if r["materially_bound_run_possible"][f"{crop}m"]]
    if semantic_is_bound(r):
        routes.append(f"semantic at {r['semantic_coverage']['mesh'].split('_')[-1].removesuffix('.ply')}")
    return ", ".join(routes) if routes else "no"


def _walk_binding_cell(r: dict[str, Any], crop: int) -> str:
    bound = r["bindings"][f"{crop}m"]
    if bound is None:
        return "none"
    if bound["covered_fraction_by_area"] is None:
        return f"{bound['stations']} stations, area not recorded"
    return f"{100 * bound['covered_fraction_by_area']:.1f}% ({bound['stations']} stations)"


def markdown(rows: list[dict[str, Any]], crops: tuple[int, ...]) -> str:
    header = (
        "| Site | Panoramas | Registered | Median residual | Worst residual | Median pose sigma | "
        "At altitude bound | Inside the geometry | Admitted | SAM 3 material axis | Fishnet faces | "
        "Fishnet bound area | "
        + " | ".join(f"Walk bound area at {crop} m" for crop in crops)
        + " | Materially bound run |\n"
    )
    header += "| --- " * (13 + len(crops)) + "|\n"
    lines = []
    for r in rows:
        cells = [
            r["site"],
            str(r["panoramas"]),
            str(r["registered"]),
            "n/a" if r["residual_deg"]["median"] is None else f"{r['residual_deg']['median']:.2f} deg",
            "n/a" if r["residual_deg"]["max"] is None else f"{r['residual_deg']['max']:.2f} deg",
            "n/a" if r["position_sigma_m"]["median"] is None else f"{r['position_sigma_m']['median']:.2f} m",
            str(r["poses_at_altitude_bound"]),
            str(r["poses_inside_the_geometry"]),
            str(r["poses_admitted"]),
            f"{r['panoramas_with_sam3_material_axis']} of {r['panoramas']}" if r["panoramas"] else "none",
            fishnet_cell(r["fishnet"]),
            semantic_cell(r),
        ]
        cells.extend(_walk_binding_cell(r, crop) for crop in crops)
        cells.append(bound_run_cell(r, crops))
        lines.append("| " + " | ".join(cells) + " |")
    return header + "\n".join(lines) + "\n"


MARKER = "<!-- COVERAGE_TABLE -->"
END = "<!-- END_COVERAGE_TABLE -->"


@dataclass(frozen=True)
class EvidenceCoverageConfig:
    crops_m: tuple[int, ...] = (130, 250)
    max_residual_deg: float = 4.0
    max_sky_conflict: float = 0.5
    min_conflict_range_m: float = 2.0
    out: pathlib.Path = paths.outputs_dir() / "evidence_coverage.json"
    into: pathlib.Path = SCRIPT_DIR / "docs" / "COVERAGE.md"
    write: bool = True
    measure_semantic: bool = False


def splice(document: str, table: str) -> str:
    """Replace whatever sits between the two markers, or insert after the first."""
    if MARKER not in document:
        raise SystemExit(f"no {MARKER} marker to write into")
    head, rest = document.split(MARKER, 1)
    tail = rest.split(END, 1)[1] if END in rest else rest
    return f"{head}{MARKER}\n\n{table.strip()}\n\n{END}{tail}"


def execute(config: EvidenceCoverageConfig) -> int:
    crops = config.crops_m
    if config.measure_semantic:
        for site in SITES:
            measured = measure_semantic_coverage(site)
            if measured is not None:
                print(
                    f"[semantic] {site}: {measured['views']} views on {measured['mesh']}, "
                    f"{100 * measured['covered_fraction_by_area']:.1f}% of area",
                    flush=True,
                )
    rows = [
        row(
            site,
            crops,
            max_residual_deg=config.max_residual_deg,
            max_sky_conflict=config.max_sky_conflict,
            min_conflict_range_m=config.min_conflict_range_m,
        )
        for site in SITES
    ]
    table = markdown(rows, crops)
    if config.write:
        config.out.parent.mkdir(parents=True, exist_ok=True)
        gate = {
            "crop_m": list(config.crops_m),
            "max_residual_deg": config.max_residual_deg,
            "max_sky_conflict": config.max_sky_conflict,
            "min_conflict_range_m": config.min_conflict_range_m,
            "out": str(config.out),
            "into": config.into,
            "no_write": not config.write,
            "measure_semantic": config.measure_semantic,
        }
        config.out.write_text(json.dumps({"gate": gate, "rows": rows}, indent=2, default=str))
        if config.into.exists():
            config.into.write_text(splice(config.into.read_text(), table))
            print(f"[coverage] {config.into.name} updated", flush=True)
    print(table)
    total = {
        "panoramas": sum(r["panoramas"] for r in rows),
        "registered": sum(r["registered"] for r in rows),
        "admitted": sum(r["poses_admitted"] for r in rows),
        "inside_the_geometry": sum(r["poses_inside_the_geometry"] for r in rows),
        "inside_and_passing_the_residual_gate": sum(r["poses_inside_and_passing_the_residual_gate"] for r in rows),
    }
    print(json.dumps(total, indent=2))
    return 0
