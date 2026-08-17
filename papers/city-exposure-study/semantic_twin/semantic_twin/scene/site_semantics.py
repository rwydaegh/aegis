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

**Admission uses one shared versioned gate.** `build_walk_twin.py` admitted a
station on its skyline residual alone. The residual is blind to the failure
mode that actually matters: a pose whose camera has been driven inside the
geometry scores a low residual because the silhouette it is matching is the
inside of a wall. The second test is the sky conflict already recorded in every
`pose_aligned.json`, the fraction of directions the segmentation calls sky for
which the support mesh returns a first hit. A healthy pose sits near zero with
its few conflicts tens of metres away. A pose at 1.0 with a median conflict
range under a metre is inside a building. Of the 83 poses in this repository 26
fail that paired test and 6 of those pass the residual gate. Production v2 also
requires complete sky diagnostics and a vertical optimum inside the search
interval.

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

import hashlib
import json
import pathlib
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from typing import Any

import numpy as np

from semantic_twin import paths
from semantic_twin.sites import ImagerySet, Site
from semantic_twin.vision.provenance import AdmissionGate, Registration
from semantic_twin.vision.surface_atlas import semantic_artifact_reasons, semantic_evidence_directory

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

DEFAULT_OUT = paths.outputs_dir() / "site_semantics"

#: Sites whose panoramas were acquired in more than one campaign, and where the
#: second campaign lives under its own directory. Korenmarkt's twelve Mapillary
#: stations are the evidence every published walk number in this study rests on,
#: and they are registered against the same mesh in the same frame, so a
#: Korenmarkt binding that read only the single Street View panorama at the top
#: of ``data/panoramas/korenmarkt`` would be thinner than the study it belongs
#: to. Station names carry their campaign prefix, so the two never collide.
COMPANION_DIRECTORIES: dict[str, tuple[str, ...]] = {
    site.name: tuple(entry.directory for entry in site.imagery_by_role("walk"))
    for site in Site.all()
    if site.imagery_by_role("walk")
}

#: Directory name prefixes that hold an acquired panorama. ``indoor_`` is
#: deliberately absent: those are the sky fraction probe of a capture the
#: screener rejected, and they are kept on disk as the evidence for rejecting it.
STATION_PREFIXES = ("pano_", "walk_")

#: Every site with a double precision support mesh, the same tuple
#: ``run_exposure.py`` sweeps.
SITES: tuple[str, ...] = Site.names()


@dataclass(frozen=True)
class SemanticBuildOptions:
    """Settings shared by every site in one semantic binding build."""

    crop_m: int = 250
    grid_height: int = 1536
    block_rows: int = 128
    workers: int = 2
    max_residual_deg: float = 4.0
    max_sky_conflict: float = 0.5
    min_conflict_range_m: float = 2.0
    out_root: pathlib.Path = DEFAULT_OUT
    cohort_dir: pathlib.Path | None = None
    semantics_dirname: str = "semantics"

    @property
    def admission_gate(self) -> AdmissionGate:
        return AdmissionGate(
            max_residual_deg=self.max_residual_deg,
            max_sky_conflict=self.max_sky_conflict,
            min_conflict_range_m=self.min_conflict_range_m,
        )


def _relative(path: pathlib.Path) -> str:
    try:
        return str(path.relative_to(paths.root()))
    except ValueError:
        return str(path)


def _prior_semantics() -> pathlib.Path:
    """The Korenmarkt panorama that supplies ``vistas_material_prior``.

    Eleven other panorama files carry the same prior. Resolving the chosen one
    here keeps module import independent of the ignored panorama data while
    preserving the original source when that data is present.
    """
    stations = Site.get("korenmarkt").stations()
    if not stations:
        raise FileNotFoundError("no Korenmarkt station is available to supply the material prior")
    return paths.panorama_semantics(stations[0])


def site_mesh(site: str, crop_m: int) -> pathlib.Path:
    """The mesh ``run_exposure.py`` would trace, resolved by the same rule.

    Duplicated from ``run_exposure.py`` rather than imported, because importing
    it pulls in the whole propagation stack and that module is under concurrent
    edit. The rule is one line and refusing a ``format_version`` below 3 is the
    part that matters.
    """
    return paths.site_mesh(site, crop_m)


def station_verdict(
    pose: dict[str, Any],
    *,
    max_residual_deg: float,
    max_sky_conflict: float,
    min_conflict_range_m: float,
) -> dict[str, Any]:
    """Admit or refuse one registered pose, and say which test decided.

    The tests and the gate they compare against now live in
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
        "admission_gate_version": gate.version,
    }


def stations(
    site: str,
    *,
    max_residual_deg: float,
    max_sky_conflict: float,
    min_conflict_range_m: float,
    root: pathlib.Path | None = None,
    semantics_dirname: str | None = None,
    cohort_dir: pathlib.Path | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Every panorama directory of a site, split into admitted and refused.

    The default keeps the legacy entity-only station contract. An explicit
    directory selects one exact hybrid product and validates it before pose
    admission. No artifact is borrowed from the legacy ``semantics`` folder.
    """
    admitted, refused = [], []
    for folder in _station_directories(site, root, semantics_dirname, cohort_dir):
        accepted, record = _station_record(
            folder,
            max_residual_deg=max_residual_deg,
            max_sky_conflict=max_sky_conflict,
            min_conflict_range_m=min_conflict_range_m,
            semantics_dirname=semantics_dirname,
        )
        (admitted if accepted else refused).append(record)
    return admitted, refused


def _station_directories(
    site: str,
    root: pathlib.Path | None,
    semantics_dirname: str | None,
    cohort_dir: pathlib.Path | None = None,
) -> list[pathlib.Path]:
    """Camera directories for the site and its walk campaigns."""
    if cohort_dir is not None:
        return _cohort_station_directories(cohort_dir, root)
    found: list[pathlib.Path] = []
    selected = Site.get(site)
    for role in ("stations", "walk"):
        for entry in selected.imagery_by_role(role):
            found.extend(_imagery_stations(entry, root, semantics_dirname))
    return found


def _cohort_station_directories(
    cohort_dir: pathlib.Path,
    root: pathlib.Path | None,
) -> list[pathlib.Path]:
    """Resolve an isolated cohort and enumerate its explicit ``pano_*`` folders.

    A cohort is intentionally not treated like a declared :class:`ImagerySet`.
    It is a one-run override for a dated capture, so reading the site's canonical
    directory or accepting a flat single-camera layout here would make it easy
    to mix campaigns without noticing.  The resolved directory must stay
    physically beneath the study root, including when a symlink is supplied.
    """
    study_root = (root or paths.root()).expanduser().resolve()
    requested = pathlib.Path(cohort_dir).expanduser()
    candidate = requested if requested.is_absolute() else study_root / requested
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise FileNotFoundError(f"cohort directory does not exist: {candidate}") from error
    if not resolved.is_dir():
        raise FileNotFoundError(f"cohort directory is not a directory: {candidate}")
    try:
        resolved.relative_to(study_root)
    except ValueError as error:
        raise ValueError(f"cohort directory must remain beneath study root: {candidate}") from error
    return sorted(folder for folder in resolved.glob("pano_*") if folder.is_dir())


def _imagery_stations(
    entry: ImagerySet,
    root: pathlib.Path | None,
    semantics_dirname: str | None,
) -> list[pathlib.Path]:
    """Resolve one declared imagery set, with a fixture-root override for tests."""
    if root is None and semantics_dirname is None:
        return list(paths.panorama_stations(entry.directory, entry.station_prefix))
    directory = paths.panorama_set(entry.directory) if root is None else root / "data" / "panoramas" / entry.directory
    if not directory.is_dir():
        return []
    if entry.station_prefix:
        return sorted(path for path in directory.glob(f"{entry.station_prefix}*") if path.is_dir())
    numbered = sorted(path for prefix in STATION_PREFIXES for path in directory.glob(f"{prefix}*") if path.is_dir())
    if numbered:
        return numbered
    if semantics_dirname is not None:
        return [directory]
    selected = semantics_dirname or "semantics"
    return [directory] if semantic_evidence_directory(directory, selected).is_dir() else []


def _station_record(
    folder: pathlib.Path,
    *,
    max_residual_deg: float,
    max_sky_conflict: float,
    min_conflict_range_m: float,
    semantics_dirname: str | None,
) -> tuple[bool, dict[str, Any]]:
    """Read and score one station, returning its admission and report row."""
    capture = _capture_identity(folder)
    aligned = paths.panorama_pose(folder)
    selected_name = semantics_dirname or "semantics"
    selected_directory = semantic_evidence_directory(folder, selected_name)
    semantics = selected_directory / "panorama_semantics.npz"
    meta = selected_directory / "semantics.json"
    missing: list[str] = []
    if not aligned.exists():
        missing.append("missing pose artifact: alignment/pose_aligned.json")
    if semantics_dirname is None:
        if not semantics.exists():
            missing.append("missing dense semantic artifact: semantics/panorama_semantics.npz")
        if not meta.exists():
            missing.append("missing semantic metadata artifact: semantics/semantics.json")
    else:
        missing.extend(semantic_artifact_reasons(meta, semantics))
    if missing:
        record: dict[str, Any] = {
            "station": folder.name,
            "admitted": False,
            "refused_because": missing,
            "admission_gate_version": AdmissionGate().version,
            **capture,
        }
        if semantics_dirname is not None:
            record["semantic_evidence_directory"] = str(selected_directory)
        return False, record
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
    verdict.update(capture)
    if semantics_dirname is not None:
        verdict["semantic_evidence_directory"] = str(selected_directory)
    return bool(verdict["admitted"]), verdict


def _capture_identity(folder: pathlib.Path) -> dict[str, str]:
    """Freeze provider metadata and its complete capture identifier when present."""
    metadata_path = folder / "metadata.json"
    if not metadata_path.is_file():
        return {}
    payload = metadata_path.read_bytes()
    document = json.loads(payload)
    if not isinstance(document, dict):
        raise TypeError(f"{metadata_path} must contain a metadata object")
    has_google = document.get("panoId") is not None
    has_mapillary = document.get("id") is not None
    if has_google == has_mapillary:
        raise ValueError(f"{metadata_path} does not identify exactly one supported panorama provider")
    identity = {
        "metadata_sha256": hashlib.sha256(payload).hexdigest(),
        "provider": "google_streetview" if has_google else "mapillary",
    }
    identity["pano_id" if has_google else "image_id"] = str(document["panoId" if has_google else "id"])
    return identity


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

    (
        mesh_path,
        pose,
        semantics_path,
        transient_ids,
        grid_height,
        station,
        block_rows,
        vegetation_form_count,
        vegetation_subtype_count,
    ) = job
    mesh = trimesh.load(mesh_path, process=False)
    height, width = grid_height, 2 * grid_height
    rotation = panorama_to_world_matrix(
        float(pose["heading_deg"]),
        pitch_deg=float(pose.get("pitch_correction_deg", 0.0)),
        roll_deg=float(pose.get("roll_correction_deg", 0.0)),
    )
    camera = np.asarray(pose["position_enu_m"], dtype=np.float64)

    labels, forms, subtypes = _load_site_semantic_rasters(
        pathlib.Path(semantics_path),
        height,
        width,
        vegetation_form_count,
        vegetation_subtype_count,
        station,
    )
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
    vegetation_faces, vegetation_forms, vegetation_subtypes = [], [], []
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
        vegetation_face, vegetation_form, vegetation_subtype = _vegetation_block(
            forms,
            subtypes,
            start,
            stop,
            index_ray,
            index_tri,
            keep,
        )
        vegetation_faces.append(vegetation_face)
        vegetation_forms.append(vegetation_form)
        vegetation_subtypes.append(vegetation_subtype)
        rays_cast += len(index_ray)
        transient_rays += int(transient.sum())
        del index_tri, index_ray, block_labels, transient, keep

    face = np.concatenate(hit_faces) if hit_faces else np.zeros(0, dtype=np.int32)
    label = np.concatenate(hit_labels) if hit_labels else np.zeros(0, dtype=np.int16)
    record = {
        "station": station,
        "rays": total.astype(np.int32),
        "transient_rays": blocked.astype(np.int32),
        "modal_class": _modal_class(face, label, face_count, classes),
        "clean_rays": clean_count.astype(np.int32),
        "view_transient_fraction": float(transient_rays / rays_cast) if rays_cast else 0.0,
        "view_mesh_rays": int(rays_cast),
    }
    record.update(
        _vegetation_record(
            vegetation_faces,
            vegetation_forms,
            vegetation_subtypes,
            face_count,
            vegetation_form_count,
            vegetation_subtype_count,
        )
    )
    return record


def _load_site_semantic_rasters(
    path: pathlib.Path,
    height: int,
    width: int,
    form_count: int,
    subtype_count: int,
    station: str,
) -> tuple[np.ndarray, np.ndarray | None, np.ndarray | None]:
    """Load one station only when its JSON vocabulary and NPZ axes agree."""
    expects_vegetation = bool(form_count or subtype_count)
    if bool(form_count) != bool(subtype_count):
        raise ValueError(f"{station} metadata carries only half of the vegetation vocabulary")
    with np.load(path) as document:
        entity = document["entity"]
        has_form = _validate_vegetation_axes(document.files, expects_vegetation, station)
        rows = np.arange(height) * entity.shape[0] // height
        columns = np.arange(width) * entity.shape[1] // width
        labels = np.ascontiguousarray(entity[np.ix_(rows, columns)])
        if not has_form:
            return labels, None, None
        vegetation_form = document["vegetation_form"]
        vegetation_subtype = document["vegetation_subtype"]
        _validate_vegetation_shapes(vegetation_form, vegetation_subtype, entity.shape, station)
        _validate_vegetation_range(vegetation_form, form_count, "form", station)
        _validate_vegetation_range(vegetation_subtype, subtype_count, "subtype", station)
        forms = np.ascontiguousarray(vegetation_form[np.ix_(rows, columns)])
        subtypes = np.ascontiguousarray(vegetation_subtype[np.ix_(rows, columns)])
    return labels, forms, subtypes


def _validate_vegetation_axes(files: list[str], expects_vegetation: bool, station: str) -> bool:
    has_form = "vegetation_form" in files
    has_subtype = "vegetation_subtype" in files
    if has_form != has_subtype:
        raise ValueError(f"{station} NPZ carries only half of the vegetation axis")
    if expects_vegetation != has_form:
        metadata = "declares" if expects_vegetation else "does not declare"
        arrays = "contains" if has_form else "does not contain"
        raise ValueError(f"{station} metadata {metadata} vegetation but its NPZ {arrays} the arrays")
    return has_form


def _validate_vegetation_shapes(
    vegetation_form: np.ndarray,
    vegetation_subtype: np.ndarray,
    entity_shape: tuple[int, ...],
    station: str,
) -> None:
    if vegetation_form.shape != entity_shape or vegetation_subtype.shape != entity_shape:
        raise ValueError(f"{station} vegetation rasters do not match its entity raster")


def _validate_vegetation_range(
    values: np.ndarray,
    vocabulary_size: int,
    axis: str,
    station: str,
) -> None:
    if values.size and (int(values.min()) < 0 or int(values.max()) >= vocabulary_size):
        raise ValueError(f"{station} vegetation {axis} leaves its declared vocabulary")


def _vegetation_block(
    forms: np.ndarray | None,
    subtypes: np.ndarray | None,
    start: int,
    stop: int,
    index_ray: np.ndarray,
    index_tri: np.ndarray,
    keep: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if forms is None or subtypes is None:
        return np.zeros(0, dtype=np.int32), np.zeros(0, dtype=np.uint8), np.zeros(0, dtype=np.uint8)
    block_forms = forms[start:stop].reshape(-1)[index_ray]
    resolved = keep & (block_forms > 0)
    block_subtypes = subtypes[start:stop].reshape(-1)[index_ray]
    return (
        index_tri[resolved].astype(np.int32),
        block_forms[resolved].astype(np.uint8),
        block_subtypes[resolved].astype(np.uint8),
    )


def _vegetation_record(
    faces: list[np.ndarray],
    forms: list[np.ndarray],
    subtypes: list[np.ndarray],
    face_count: int,
    form_count: int,
    subtype_count: int,
) -> dict[str, np.ndarray]:
    if not form_count:
        return {}
    face = np.concatenate(faces) if faces else np.zeros(0, dtype=np.int32)
    form = np.concatenate(forms) if forms else np.zeros(0, dtype=np.uint8)
    subtype = np.concatenate(subtypes) if subtypes else np.zeros(0, dtype=np.uint8)
    modal_form = _modal_class(face, form, face_count, form_count).clip(min=0).astype(np.uint8)
    diagnostic = (subtype > 0) & (form == modal_form[face])
    return {
        "modal_vegetation_form": modal_form,
        "modal_vegetation_subtype": _modal_class(
            face[diagnostic],
            subtype[diagnostic],
            face_count,
            subtype_count,
        )
        .clip(min=0)
        .astype(np.uint8),
        "vegetation_rays": np.bincount(face, minlength=face_count).astype(np.int32),
    }


def _site_vegetation_vocabularies(
    document: dict[str, Any],
    current_form: list[str] | None,
    current_subtype: list[str] | None,
) -> tuple[list[str] | None, list[str] | None, bool]:
    form_vocabulary = document.get("vegetation_form_id2label")
    subtype_vocabulary = document.get("vegetation_subtype_id2label")
    if form_vocabulary is None and subtype_vocabulary is None:
        return current_form, current_subtype, True
    if form_vocabulary is None or subtype_vocabulary is None:
        return current_form, current_subtype, False
    form = [form_vocabulary[str(index)] for index in range(len(form_vocabulary))]
    subtype = [subtype_vocabulary[str(index)] for index in range(len(subtype_vocabulary))]
    compatible = (current_form is None or form == current_form) and (
        current_subtype is None or subtype == current_subtype
    )
    return (form, subtype, True) if compatible else (current_form, current_subtype, False)


def vocabulary_matches(meta_path: pathlib.Path, prior: dict[str, Any]) -> bool:
    document = json.loads(meta_path.read_text())
    return document["entity_id2label"] == prior["entity_id2label"]


def _station_jobs(
    admitted: list[dict[str, Any]],
    prior: dict[str, Any],
    mesh_path: pathlib.Path,
    options: SemanticBuildOptions,
) -> tuple[list[tuple], list[str], list[str] | None, list[str] | None]:
    jobs: list[tuple] = []
    mismatched: list[str] = []
    vegetation_form_names: list[str] | None = None
    vegetation_subtype_names: list[str] | None = None
    for station in admitted:
        folder = pathlib.Path(station["folder"])
        semantic_dir = semantic_evidence_directory(folder, options.semantics_dirname)
        meta_path = semantic_dir / "semantics.json"
        if not vocabulary_matches(meta_path, prior):
            mismatched.append(station["station"])
            continue
        meta = json.loads(meta_path.read_text())
        vegetation_form_names, vegetation_subtype_names, compatible = _site_vegetation_vocabularies(
            meta,
            vegetation_form_names,
            vegetation_subtype_names,
        )
        if not compatible:
            mismatched.append(station["station"])
            continue
        form_vocabulary = meta.get("vegetation_form_id2label")
        subtype_vocabulary = meta.get("vegetation_subtype_id2label")
        transient = {int(k) for k, v in meta["entity_id2label"].items() if v in TRANSIENT_CLASSES}
        jobs.append(
            (
                str(mesh_path),
                json.loads((folder / "alignment" / "pose_aligned.json").read_text()),
                str(semantic_dir / "panorama_semantics.npz"),
                transient,
                options.grid_height,
                station["station"],
                options.block_rows,
                0 if form_vocabulary is None else len(form_vocabulary),
                0 if subtype_vocabulary is None else len(subtype_vocabulary),
            )
        )
    return jobs, mismatched, vegetation_form_names, vegetation_subtype_names


def build(site: str, options: SemanticBuildOptions) -> dict[str, Any] | None:
    import trimesh

    mesh_path = site_mesh(site, options.crop_m)
    gate = options.admission_gate
    admitted, refused = stations(
        site,
        max_residual_deg=options.max_residual_deg,
        max_sky_conflict=options.max_sky_conflict,
        min_conflict_range_m=options.min_conflict_range_m,
        cohort_dir=options.cohort_dir,
        semantics_dirname=None if options.semantics_dirname == "semantics" else options.semantics_dirname,
    )
    prior_semantics = _prior_semantics()
    prior = json.loads(prior_semantics.read_text())
    report: dict[str, Any] = {
        "site": site,
        "crop_radius_m": options.crop_m,
        "mesh": mesh_path.name,
        "grid_height": options.grid_height,
        "admission": {
            **gate.as_dict(),
            "rule": (
                "A station needs a complete diagnostic record, a skyline residual at or below the "
                "gate, an interior vertical optimum, and no paired inside-geometry signature. The "
                "inside signature is a sky-hit fraction above the threshold AND a median conflict "
                "range below the range threshold."
            ),
        },
        "stations_admitted": admitted,
        "stations_refused": refused,
        "material_prior": _relative(prior_semantics),
    }
    if not admitted:
        report["result"] = "no admitted station, nothing written"
        return report

    jobs, mismatched, vegetation_form_names, vegetation_subtype_names = _station_jobs(
        admitted,
        prior,
        mesh_path,
        options,
    )
    report["stations_with_a_different_vocabulary"] = mismatched
    if not jobs:
        report["result"] = "every admitted station carries a vocabulary the prior does not cover"
        return report

    if options.workers > 1 and len(jobs) > 1:
        with ProcessPoolExecutor(max_workers=options.workers) as pool:
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

    out_dir = options.out_root / site
    out_dir.mkdir(parents=True, exist_ok=True)
    npz = out_dir / f"walk_semantic_{options.crop_m}m.npz"
    arrays: dict[str, np.ndarray] = {
        "image_ids": np.asarray([r["station"] for r in results]),
        "rays": rays,
        "transient_rays": blocked,
        "modal_class": modal,
        "clean_rays": clean,
    }
    vegetation_arrays, vegetation_report = _site_vegetation_arrays(
        results,
        vegetation_form_names,
        vegetation_subtype_names,
    )
    arrays.update(vegetation_arrays)
    if vegetation_report is not None:
        report["vegetation"] = vegetation_report
    np.savez_compressed(npz, **arrays)
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
    (out_dir / f"walk_semantic_{options.crop_m}m.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def _site_vegetation_arrays(
    results: list[dict[str, Any]],
    form_names: list[str] | None,
    subtype_names: list[str] | None,
) -> tuple[dict[str, np.ndarray], dict[str, Any] | None]:
    if form_names is None or subtype_names is None:
        return {}, None
    if not all("modal_vegetation_form" in result for result in results):
        return {}, {"status": "mixed semantic files, refusing a vegetation axis only some stations carry"}
    return (
        {
            "modal_vegetation_form": np.stack([result["modal_vegetation_form"] for result in results]),
            "modal_vegetation_subtype": np.stack([result["modal_vegetation_subtype"] for result in results]),
            "vegetation_rays": np.stack([result["vegetation_rays"] for result in results]),
            "vegetation_form_names": np.asarray(form_names),
            "vegetation_subtype_names": np.asarray(subtype_names),
        },
        {
            "form_vocabulary": form_names,
            "diagnostic_subtype_vocabulary": subtype_names,
            "dense_vegetation": "unresolved and contributes no form vote",
        },
    )
