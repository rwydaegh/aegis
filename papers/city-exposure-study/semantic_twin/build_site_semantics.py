"""Fuse a site's registered panoramas into a per-triangle semantic posterior.

`run_exposure.py --materials walk` reads one file, `walk_semantic.npz`, holding
`modal_class` and `clean_rays` with one row per station and one column per
triangle of the mesh the tracer will use. Exactly one such file existed, built
by `build_walk_twin.py` from twelve Mapillary stations at Korenmarkt against
the 130 m mesh, which is why `--materials walk` refused every other site and
why every site in the eleven city table ran with a covered area fraction of
0.000.

Nothing about that file is Mapillary-specific. Eight sites already carry
registered panoramas with segmented imagery beside them, 83 poses in total, and
71 of the 83 were feeding no published result. This builds the same product
from them.

Three things are not inherited from the Mapillary path and are stated here.

**The mesh is the tracer's, not the scene's.** `modal_class` is indexed by
triangle with no join key, so it is only meaningful against the exact mesh it
was cast against. A binding is therefore built per site *and per crop radius*,
and `bind_walk_entities` will refuse a mismatch on the column count. A 130 m
binding is not valid for a 250 m run.

**Admission is on two tests, not one.** `build_walk_twin.py` admits a station
on its skyline residual alone. The residual is blind to the failure mode that
actually matters: a pose whose camera has been driven inside the geometry
scores a low residual because the silhouette it is matching is the inside of a
wall. The second test is the sky conflict already recorded in every
`pose_aligned.json`, the fraction of directions the segmentation calls sky for
which the support mesh returns a first hit. A healthy pose sits near zero with
its few conflicts tens of metres away. A pose at 1.0 with a median conflict
range under a metre is inside a building. Of the 83 poses in this repository 26
fail that test and 6 of those pass the residual gate, so the two tests are not
redundant and the residual is not sufficient.

**The material prior is a table, not a site measurement.** `vistas_material_prior`
maps a Mapillary Vistas entity class to a distribution over the RF material
vocabulary. It is a property of the vocabulary and not of the city, and it was
written only into the twelve `semantics.json` files the hybrid backend produced,
eleven of them at Korenmarkt. All 83 station level files carry one and the same
65 class Vistas vocabulary from the same mask2former checkpoint, verified label
by label before use, so the same table applies and is passed through rather than
recomputed. What the other sites do not carry is the SAM 3 material axis, so
`bind_walk_materials` is unavailable at them and only the entity axis
binding is built here.

**Ray density is not free and is not converged at the cheap settings.** The
covered area fraction rises with the ray grid, because a triangle no ray landed
on is a triangle no station saw. At Plaza Mayor over the 130 m crop, the same
six admitted stations bind 18.04 percent of the area at `--grid-height 384` and
19.43 percent at 768, so a 4x cheaper grid costs about 7 percent of the answer,
relative. The default is 1536, which is what the Korenmarkt walk binding was
built at, and it is held fixed across sites because the covered fraction is
compared between them.

Run from the `semantic_twin` directory::

    ../../../.venv/bin/python build_site_semantics.py --site prague_staromestske --crop-m 250
    ../../../.venv/bin/python build_site_semantics.py --all-sites --crop-m 250 --workers 2
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from concurrent.futures import ProcessPoolExecutor
from typing import Any

import numpy as np

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from semantic_twin.vision.provenance import AdmissionGate, Registration  # noqa: E402

#: Copied rather than imported from ``build_walk_twin.py``, which is under
#: concurrent edit. The list is the Mapillary Vistas classes that describe
#: something in front of the facade rather than the facade.
TRANSIENT_CLASSES = (
    "Person",
    "Bicyclist",
    "Motorcyclist",
    "Other Rider",
    "Bicycle",
    "Boat",
    "Bus",
    "Car",
    "Caravan",
    "Motorcycle",
    "Other Vehicle",
    "Trailer",
    "Truck",
    "Wheeled Slow",
)

#: The panorama whose ``semantics.json`` supplies ``vistas_material_prior``.
#: Eleven others carry an identical copy, all of them at Korenmarkt, and any of
#: them would do. This one is named so the provenance of every site's prior is a
#: single path rather than whichever file happened to be read first.
PRIOR_SEMANTICS = SCRIPT_DIR / "data" / "panoramas" / "korenmarkt" / "semantics" / "semantics.json"

DEFAULT_OUT = SCRIPT_DIR / "outputs" / "site_semantics"

#: Sites whose panoramas were acquired in more than one campaign, and where the
#: second campaign lives under its own directory. Korenmarkt's twelve Mapillary
#: stations are the evidence every published walk number in this study rests on,
#: and they are registered against the same mesh in the same frame, so a
#: Korenmarkt binding that read only the single Street View panorama at the top
#: of ``data/panoramas/korenmarkt`` would be thinner than the study it belongs
#: to. Station names carry their campaign prefix, so the two never collide.
COMPANION_DIRECTORIES: dict[str, tuple[str, ...]] = {"korenmarkt": ("korenmarkt_walk",)}

#: Directory name prefixes that hold an acquired panorama. ``indoor_`` is
#: deliberately absent: those are the sky fraction probe of a capture the
#: screener rejected, and they are kept on disk as the evidence for rejecting it.
STATION_PREFIXES = ("pano_", "walk_")

#: Every site with a double precision support mesh, the same tuple
#: ``run_exposure.py`` sweeps.
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


def _relative(path: pathlib.Path) -> str:
    try:
        return str(path.relative_to(SCRIPT_DIR))
    except ValueError:
        return str(path)


def site_mesh(site: str, crop_m: int) -> pathlib.Path:
    """The mesh ``run_exposure.py`` would trace, resolved by the same rule.

    Duplicated from ``run_exposure.py`` rather than imported, because importing
    it pulls in the whole propagation stack and that module is under concurrent
    edit. The rule is one line and refusing a ``format_version`` below 3 is the
    part that matters.
    """
    directory = SCRIPT_DIR / "data" / "geometry" / site
    for candidate in (f"inhouse_leaf_{crop_m}m_f64.ply", f"inhouse_leaf_{crop_m}m.ply"):
        path = directory / candidate
        manifest = path.with_suffix(".json")
        if not path.exists() or not manifest.exists():
            continue
        if int(json.loads(manifest.read_text()).get("format_version", 0)) >= 3:
            return path
    raise FileNotFoundError(f"no double precision {crop_m} m mesh for {site}")


def station_verdict(
    pose: dict[str, Any],
    *,
    max_residual_deg: float,
    max_sky_conflict: float,
    min_conflict_range_m: float,
) -> dict[str, Any]:
    """Admit or refuse one registered pose, and say which test decided.

    The two tests and the gate they compare against now live in
    :class:`~semantic_twin.vision.provenance.Registration` and
    :class:`~semantic_twin.vision.provenance.AdmissionGate`, so that anything
    else asking how good a pose is gets the same answer as the admission does.
    This function stays because it names the keys the site report writes, and it
    was checked against the previous inline version on all 83 poses in the
    repository before the two were merged.

    ``sky_conflict`` may be absent on a pose registered before the diagnostic
    existed, or carry ``unavailable`` where the raycast extra was missing. That
    is recorded as unknown rather than silently treated as a pass, because the
    whole point of the second test is that the first one cannot see this.
    """
    registration = Registration.from_pose(pose)
    gate = AdmissionGate(
        max_residual_deg=max_residual_deg,
        max_sky_conflict=max_sky_conflict,
        min_conflict_range_m=min_conflict_range_m,
    )
    verdict = registration.verdict(gate)
    return {
        # An unregistered pose reports 99 degrees rather than nothing, because
        # this key feeds a sort in the site report.
        "residual_deg": 99.0 if registration.residual_deg is None else registration.residual_deg,
        "sky_with_mesh_hit_fraction": registration.sky_conflict,
        "conflict_median_range_m": registration.conflict_median_range_m,
        "sky_conflict_state": verdict.sky_conflict_state,
        "dz_at_bound": registration.dz_at_bound,
        "position_sigma_m": registration.position_sigma_m,
        "admitted": verdict.admitted,
        "refused_because": list(verdict.reasons),
    }


def stations(
    site: str,
    *,
    max_residual_deg: float,
    max_sky_conflict: float,
    min_conflict_range_m: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Every panorama directory of a site, split into admitted and refused."""
    found = []
    for name in (site, *COMPANION_DIRECTORIES.get(site, ())):
        root = SCRIPT_DIR / "data" / "panoramas" / name
        if not root.exists():
            continue
        numbered = sorted(f for prefix in STATION_PREFIXES for f in root.glob(f"{prefix}*") if f.is_dir())
        # Korenmarkt and Milan hold one panorama at the top of the site directory
        # instead of a numbered set, from before the multi camera acquisition.
        if not numbered and (root / "alignment" / "pose_aligned.json").exists():
            numbered = [root]
        found.extend(numbered)
    admitted, refused = [], []
    for folder in found:
        aligned = folder / "alignment" / "pose_aligned.json"
        semantics = folder / "semantics" / "panorama_semantics.npz"
        meta = folder / "semantics" / "semantics.json"
        if not (aligned.exists() and semantics.exists() and meta.exists()):
            refused.append(
                {"station": folder.name, "admitted": False, "refused_because": ["no registration or no semantics"]}
            )
            continue
        pose = json.loads(aligned.read_text())
        verdict = station_verdict(
            pose,
            max_residual_deg=max_residual_deg,
            max_sky_conflict=max_sky_conflict,
            min_conflict_range_m=min_conflict_range_m,
        )
        verdict["station"] = folder.name
        verdict["folder"] = str(folder)
        verdict["position_enu_m"] = pose["position_enu_m"]
        (admitted if verdict["admitted"] else refused).append(verdict)
    return admitted, refused


def _modal_class(face: np.ndarray, label: np.ndarray, face_count: int, classes: int) -> np.ndarray:
    """Most common class per face, without ever building a face by class table.

    The obvious implementation allocates ``(faces, classes)`` int32, which is
    260 MB for a 250 m crop at one million triangles and is what killed the
    first run of this script on a loaded box. This groups the hits instead: a
    single key per hit, unique with counts, then a lexsort that puts the
    winning class last within each face.
    """
    modal = np.full(face_count, -1, dtype=np.int16)
    if not face.size:
        return modal
    key = face.astype(np.int64) * classes + label.astype(np.int64)
    unique, count = np.unique(key, return_counts=True)
    del key
    owner, chosen = np.divmod(unique, classes)
    # Sorted by face, then by count ascending, then by class descending, so the
    # last entry of each face is its most common class and a tie goes to the
    # lowest class index. That last part is not cosmetic: it is what argmax on
    # the dense table did, and the two have to agree.
    order = np.lexsort((-chosen, count, owner))
    owner, chosen = owner[order], chosen[order]
    last = np.ones(owner.size, dtype=bool)
    last[:-1] = owner[1:] != owner[:-1]
    modal[owner[last]] = chosen[last].astype(np.int16)
    return modal


def _cast(job: tuple) -> dict[str, Any]:
    """Bind every panorama pixel to a mesh triangle through the aligned pose.

    The ray grid is walked in row blocks and only the hit indices are kept, not
    the hit locations, because a 1536 by 3072 grid is 4.7 million rays and the
    locations alone are 113 MB of float64 this never reads.
    """
    import trimesh

    from semantic_twin.pano_geometry import equirectangular_directions, panorama_to_world_matrix

    mesh_path, pose, semantics_path, transient_ids, grid_height, station, block_rows = job
    mesh = trimesh.load(mesh_path, process=False)
    height, width = grid_height, 2 * grid_height
    rotation = panorama_to_world_matrix(
        float(pose["heading_deg"]),
        pitch_deg=float(pose.get("pitch_correction_deg", 0.0)),
        roll_deg=float(pose.get("roll_correction_deg", 0.0)),
    )
    camera = np.asarray(pose["position_enu_m"], dtype=np.float64)

    with np.load(semantics_path) as document:
        entity = document["entity"]
        rows = np.arange(height) * entity.shape[0] // height
        columns = np.arange(width) * entity.shape[1] // width
        labels = np.ascontiguousarray(entity[np.ix_(rows, columns)])
    classes = int(labels.max()) + 1
    transient_lookup = np.zeros(classes, dtype=bool)
    for identifier in transient_ids:
        if 0 <= identifier < classes:
            transient_lookup[identifier] = True

    grid = equirectangular_directions(width, height)
    face_count = len(mesh.faces)
    total = np.zeros(face_count, dtype=np.int64)
    blocked = np.zeros(face_count, dtype=np.int64)
    clean_count = np.zeros(face_count, dtype=np.int64)
    hit_faces, hit_labels, rays_cast, transient_rays = [], [], 0, 0
    for start in range(0, height, block_rows):
        stop = min(start + block_rows, height)
        directions = grid[start:stop].reshape(-1, 3) @ rotation.T
        origins = np.broadcast_to(camera, directions.shape)
        index_tri, index_ray = mesh.ray.intersects_id(origins, directions, multiple_hits=False)
        del directions, origins
        if not len(index_ray):
            continue
        block_labels = labels[start:stop].reshape(-1)[index_ray]
        transient = transient_lookup[block_labels]
        total += np.bincount(index_tri, minlength=face_count)
        blocked += np.bincount(index_tri[transient], minlength=face_count)
        keep = ~transient
        clean_count += np.bincount(index_tri[keep], minlength=face_count)
        hit_faces.append(index_tri[keep].astype(np.int32))
        hit_labels.append(block_labels[keep].astype(np.int16))
        rays_cast += len(index_ray)
        transient_rays += int(transient.sum())
        del index_tri, index_ray, block_labels, transient, keep

    face = np.concatenate(hit_faces) if hit_faces else np.zeros(0, dtype=np.int32)
    label = np.concatenate(hit_labels) if hit_labels else np.zeros(0, dtype=np.int16)
    return {
        "station": station,
        "rays": total.astype(np.int32),
        "transient_rays": blocked.astype(np.int32),
        "modal_class": _modal_class(face, label, face_count, classes),
        "clean_rays": clean_count.astype(np.int32),
        "view_transient_fraction": float(transient_rays / rays_cast) if rays_cast else 0.0,
        "view_mesh_rays": int(rays_cast),
    }


def vocabulary_matches(meta_path: pathlib.Path, prior: dict[str, Any]) -> bool:
    document = json.loads(meta_path.read_text())
    return document["entity_id2label"] == prior["entity_id2label"]


def build(
    site: str,
    *,
    crop_m: int,
    grid_height: int,
    block_rows: int,
    workers: int,
    max_residual_deg: float,
    max_sky_conflict: float,
    min_conflict_range_m: float,
    out_root: pathlib.Path,
) -> dict[str, Any] | None:
    import trimesh

    mesh_path = site_mesh(site, crop_m)
    admitted, refused = stations(
        site,
        max_residual_deg=max_residual_deg,
        max_sky_conflict=max_sky_conflict,
        min_conflict_range_m=min_conflict_range_m,
    )
    prior = json.loads(PRIOR_SEMANTICS.read_text())
    report: dict[str, Any] = {
        "site": site,
        "crop_radius_m": crop_m,
        "mesh": mesh_path.name,
        "grid_height": grid_height,
        "admission": {
            "max_residual_deg": max_residual_deg,
            "max_sky_conflict": max_sky_conflict,
            "min_conflict_range_m": min_conflict_range_m,
            "rule": (
                "a station is admitted when its skyline residual is inside the gate AND its sky "
                "conflict does not say the camera is inside the geometry. The second test is not "
                "implied by the first: a pose driven inside a wall matches the inside of that wall "
                "and scores well."
            ),
        },
        "stations_admitted": admitted,
        "stations_refused": refused,
        "material_prior": _relative(PRIOR_SEMANTICS),
    }
    if not admitted:
        report["result"] = "no admitted station, nothing written"
        return report

    jobs, mismatched = [], []
    for station in admitted:
        folder = pathlib.Path(station["folder"])
        meta_path = folder / "semantics" / "semantics.json"
        if not vocabulary_matches(meta_path, prior):
            mismatched.append(station["station"])
            continue
        meta = json.loads(meta_path.read_text())
        transient = {int(k) for k, v in meta["entity_id2label"].items() if v in TRANSIENT_CLASSES}
        jobs.append(
            (
                str(mesh_path),
                json.loads((folder / "alignment" / "pose_aligned.json").read_text()),
                str(folder / "semantics" / "panorama_semantics.npz"),
                transient,
                grid_height,
                station["station"],
                block_rows,
            )
        )
    report["stations_with_a_different_vocabulary"] = mismatched
    if not jobs:
        report["result"] = "every admitted station carries a vocabulary the prior does not cover"
        return report

    if workers > 1 and len(jobs) > 1:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(_cast, jobs))
    else:
        results = [_cast(job) for job in jobs]

    rays = np.stack([r["rays"] for r in results])
    blocked = np.stack([r["transient_rays"] for r in results])
    modal = np.stack([r["modal_class"] for r in results])
    clean = np.stack([r["clean_rays"] for r in results])

    area = np.asarray(trimesh.load(mesh_path, process=False).area_faces, dtype=float)
    seen = clean > 0
    union = seen.any(axis=0)

    out_dir = out_root / site
    out_dir.mkdir(parents=True, exist_ok=True)
    npz = out_dir / f"walk_semantic_{crop_m}m.npz"
    np.savez_compressed(
        npz,
        image_ids=np.asarray([r["station"] for r in results]),
        rays=rays,
        transient_rays=blocked,
        modal_class=modal,
        clean_rays=clean,
    )
    report.update(
        {
            "result": "written",
            "walk_npz": _relative(npz),
            "stations_cast": [r["station"] for r in results],
            "faces": int(area.size),
            "coverage": {
                "faces_seen_by_any_station": int(union.sum()),
                "covered_fraction_by_face": float(union.mean()),
                "covered_fraction_by_area": float(area[union].sum() / area.sum()),
                "faces_seen_by_one_station_only": int((seen.sum(axis=0) == 1).sum()),
                "median_stations_per_seen_face": float(np.median(seen.sum(axis=0)[union])),
            },
            "per_view_transient_pixel_fraction": {
                "median": float(np.median([r["view_transient_fraction"] for r in results])),
                "max": float(np.max([r["view_transient_fraction"] for r in results])),
            },
        }
    )
    (out_dir / f"walk_semantic_{crop_m}m.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", nargs="+")
    parser.add_argument("--all-sites", action="store_true")
    parser.add_argument("--crop-m", type=int, default=250)
    parser.add_argument("--grid-height", type=int, default=1536)
    parser.add_argument(
        "--block-rows",
        type=int,
        default=128,
        help="rows of the equirectangular grid cast at once, which sets the peak memory of a worker",
    )
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--max-residual-deg", type=float, default=4.0)
    parser.add_argument("--max-sky-conflict", type=float, default=0.5)
    parser.add_argument("--min-conflict-range-m", type=float, default=2.0)
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
    sites = SITES if args.all_sites else tuple(args.site or ())
    if not sites:
        raise SystemExit("name --site or pass --all-sites")
    for site in sites:
        try:
            report = build(
                site,
                crop_m=args.crop_m,
                grid_height=args.grid_height,
                block_rows=args.block_rows,
                workers=args.workers,
                max_residual_deg=args.max_residual_deg,
                max_sky_conflict=args.max_sky_conflict,
                min_conflict_range_m=args.min_conflict_range_m,
                out_root=args.out,
            )
        except FileNotFoundError as exc:
            print(f"[skip] {site}: {exc}", flush=True)
            continue
        if report is None or report.get("result") != "written":
            print(
                f"[none] {site}: {report.get('result') if report else 'nothing'}, "
                f"{len(report['stations_admitted']) if report else 0} admitted of "
                f"{len(report['stations_admitted']) + len(report['stations_refused']) if report else 0}",
                flush=True,
            )
            continue
        coverage = report["coverage"]
        print(
            f"[bound] {site} at {args.crop_m} m: {len(report['stations_cast'])} stations of "
            f"{len(report['stations_admitted']) + len(report['stations_refused'])}, "
            f"{coverage['covered_fraction_by_face']:.4f} of faces, "
            f"{coverage['covered_fraction_by_area']:.4f} of area -> {report['walk_npz']}",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
