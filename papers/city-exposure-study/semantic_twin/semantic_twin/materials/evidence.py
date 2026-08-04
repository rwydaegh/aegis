"""Photographs to triangles: three routes, one object.

Each function here answers the same question with different evidence and all
three return a :class:`~.binding.SurfaceBinding` whose ``face_source`` says
which route touched which triangle.

:func:`bind_fishnet` is the single panorama route. The fishnet surfaces carry,
per face, the Mapillary Vistas entity class the panorama assigned it and the
support mesh triangle it was cut from. That is the join key. Aggregating the
fishnet faces back onto their source triangles, area weighted, gives a per
triangle class vote, and ``vistas_material_prior`` in ``semantics.json`` maps
each entity class to a distribution over the RF material vocabulary that
``config/itu_p2040_4.json`` already grounds.

:func:`bind_walk_entities` is the fused multi station route through the same
entity raster. :func:`bind_walk_materials` is the same walk read through SAM 3's
open vocabulary material axis, which is the only one that can tell brick from
glass on one facade.

Two caveats that belong in the report and not in a footnote.

The panoramas see a small fraction of a 130 m crop. Every triangle no panorama
saw stays on the geometric rule, and the returned binding measures how much
that is rather than being told.

The fishnet was built against ``inhouse_leaf_130m.ply``, the single precision
export, while the tracer uses ``inhouse_leaf_130m_f64.ply``. They differ by 118
triangles out of about 158k, so the source triangle indices cannot simply be
reused. The join is done on triangle centroids with a distance ceiling, and the
matched fraction is reported rather than assumed.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

import numpy as np

from .binding import CLASS_NAMES, Provenance, SurfaceBinding, extend_classes
from .catalogue import IMAGE_MATERIALS, MATERIAL_SUBSTITUTION, VEGETATION_NOTE

#: Prefix every evidence class name carries in the class table.
SEMANTIC_PREFIX = "semantic_"


def _triangle_centroids(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    return vertices[faces].mean(axis=1)


def _sources(count: int, covered: np.ndarray, kind: Provenance, base: np.ndarray | None = None) -> np.ndarray:
    origin = np.zeros(count, dtype=np.int8) if base is None else base.astype(np.int8).copy()
    origin[covered] = int(kind)
    return origin


def bind_fishnet(
    vertices: np.ndarray,
    faces: np.ndarray,
    areas: np.ndarray,
    geometric_class: np.ndarray,
    *,
    fishnet_dir: pathlib.Path,
    semantics_path: pathlib.Path,
    source_ply_vertices: np.ndarray | None = None,
    source_ply_faces: np.ndarray | None = None,
    match_tolerance_m: float = 0.75,
    match_normal_cosine: float = 0.9,
) -> SurfaceBinding:
    """Aggregate the fishnet posterior onto the tracer's triangles.

    ``geometric_class`` is the orientation based assignment that fills in
    wherever no panorama saw the triangle. ``source_ply_*`` describe the mesh
    the fishnet was built against; pass ``None`` when it is the same mesh, in
    which case the source triangle indices are used directly.
    """
    document = json.loads(pathlib.Path(semantics_path).read_text())
    entity_labels = {int(k): v for k, v in document["entity_id2label"].items()}
    material_prior = document["vistas_material_prior"]

    files = sorted(pathlib.Path(fishnet_dir).glob("*_fishnet.npz"))
    if not files:
        raise FileNotFoundError(f"no fishnet npz under {fishnet_dir}")

    materials = sorted(IMAGE_MATERIALS)
    votes = np.zeros((faces.shape[0], len(materials)))
    per_view: list[dict[str, Any]] = []

    remap, match_report = _index_remap(
        vertices,
        faces,
        source_ply_vertices,
        source_ply_faces,
        match_tolerance_m,
        match_normal_cosine,
    )

    for path in files:
        data = np.load(path, allow_pickle=True)
        source = data["face_source_triangle"].astype(np.int64)
        face_area = data["face_area_m2"].astype(np.float64)
        face_class = data["face_class"].astype(np.int64)
        confidence = data["face_confidence"].astype(np.float64)
        target = source if remap is None else remap[source]
        valid = target >= 0
        unmatched = int((~valid).sum())
        for material_index, material in enumerate(materials):
            weight = np.array(
                [_material_weight(material_prior, entity_labels.get(int(c)), material) for c in face_class]
            )
            contribution = weight * face_area * confidence
            np.add.at(votes[:, material_index], target[valid], contribution[valid])
        per_view.append(
            {
                "file": path.name,
                "fishnet_faces": int(face_class.size),
                "unmatched_source_triangles": unmatched,
                "surface_area_m2": float(face_area.sum()),
            }
        )

    covered = votes.sum(axis=1) > 0.0
    material_index = np.argmax(votes, axis=1)

    class_names, spec = extend_classes(materials, SEMANTIC_PREFIX, IMAGE_MATERIALS)
    face_class = np.asarray(geometric_class, dtype=np.int64).copy()
    face_class[covered] = len(CLASS_NAMES) + material_index[covered]

    chosen = {
        f"{SEMANTIC_PREFIX}{materials[i]}": int(np.count_nonzero(material_index[covered] == i))
        for i in range(len(materials))
    }
    return SurfaceBinding(
        class_names=class_names,
        spec=spec,
        face_class=face_class,
        face_source=_sources(face_class.size, covered, Provenance.IMAGE_FISHNET),
        face_area_m2=np.asarray(areas, dtype=np.float64),
        provenance={
            "fishnet_dir": str(fishnet_dir),
            "semantics": str(semantics_path),
            "join": (
                "fishnet face_source_triangle, area and confidence weighted, "
                "mapped to the tracer mesh by triangle centroid"
            ),
            "match_tolerance_m": match_tolerance_m,
            "match_normal_cosine": match_normal_cosine,
            "mesh_match": match_report,
            "entity_to_material": "vistas_material_prior in semantics.json",
            "material_to_itu_row": "material_grounding in semantics.json",
            "substitutions": MATERIAL_SUBSTITUTION,
            "vegetation_note": VEGETATION_NOTE,
            "views": per_view,
            "chosen_material_triangle_counts": chosen,
            "fallback": "geometric orientation rule wherever no panorama saw the triangle",
        },
    )


def _station_weights(
    image_ids: list[str],
    count: int,
    station_weight: dict[str, float] | None,
) -> np.ndarray:
    """One weight per station row, defaulting to one.

    A name that no row carries is refused rather than ignored, because a typo in
    an image id would otherwise silently weight nothing.
    """
    weights = np.ones(count, dtype=np.float64)
    if not station_weight:
        return weights
    if not image_ids:
        raise ValueError("this walk file stores no image_ids, so a station cannot be named")
    unknown = sorted(set(station_weight) - set(image_ids))
    if unknown:
        raise ValueError(f"station_weight names {unknown}, which this walk file does not carry")
    for index, name in enumerate(image_ids[:count]):
        weights[index] = float(station_weight.get(name, 1.0))
    return weights


def bind_walk_entities(
    areas: np.ndarray,
    geometric_class: np.ndarray,
    *,
    walk_npz: pathlib.Path,
    semantics_path: pathlib.Path,
    min_rays: int = 1,
    station_weight: dict[str, float] | None = None,
) -> SurfaceBinding:
    """Bind materials from the fused multi station walk semantics.

    ``walk_semantic.npz`` carries ``modal_class`` and ``clean_rays`` on the
    tracer's own mesh, one row per Mapillary station, so no centroid join is
    needed. Stations vote per face with weight equal to their transient free
    ray count, which is both an evidence weight and an implicit view quality
    weight, since a face seen edge on collects few rays.

    ``station_weight`` scales or removes a station's vote, keyed on the image
    ids the file already stores. It exists because ray count says how well a
    camera saw a wall and says nothing about how well the camera itself was
    placed, and those are different failures. Of this study's 112 panoramas, 83
    have a solved pose, 18 are refused on registration residual alone, and one
    site has 14 panoramas and no usable pose at all. Pass a weight of zero to
    drop such a station.
    ``semantic_twin.vision.provenance.station_registrations`` returns the
    records these keys join to. Omitting the argument weights every station at
    one, which is what every published number ran.

    This exists to answer one question: how much does the exposure
    distribution move when the fraction of the scene carrying image evidence
    goes up. A single registered panorama binds a few percent of the surface,
    a fused walk binds several times more, and everything not bound falls back
    to the orientation rule either way.
    """
    document = json.loads(pathlib.Path(semantics_path).read_text())
    entity_labels = {int(k): v for k, v in document["entity_id2label"].items()}
    material_prior = document["vistas_material_prior"]

    data = np.load(walk_npz, allow_pickle=True)
    modal = data["modal_class"].astype(np.int64)
    rays = data["clean_rays"].astype(np.float64)
    if modal.shape[1] != areas.size:
        raise ValueError(f"walk semantics cover {modal.shape[1]} faces, the tracer mesh has {areas.size}")

    materials = sorted(IMAGE_MATERIALS)
    lookup = np.zeros((max(entity_labels) + 2, len(materials)))
    for entity_id, name in entity_labels.items():
        for material_index, material in enumerate(materials):
            lookup[entity_id, material_index] = _material_weight(material_prior, name, material)

    image_ids = [str(name) for name in data["image_ids"]] if "image_ids" in data.files else []
    weights = _station_weights(image_ids, modal.shape[0], station_weight)

    votes = np.zeros((areas.size, len(materials)))
    for station in range(modal.shape[0]):
        seen = rays[station] >= min_rays
        classes = np.clip(modal[station], 0, lookup.shape[0] - 1)
        contribution = lookup[classes[seen]] * rays[station][seen, None]
        # Left untouched at weight one, so the default path is the arithmetic
        # every published number ran, to the last bit.
        if weights[station] != 1.0:
            contribution = contribution * weights[station]
        votes[seen] += contribution

    covered = votes.sum(axis=1) > 0.0
    material_index = np.argmax(votes, axis=1)

    class_names, spec = extend_classes(materials, SEMANTIC_PREFIX, IMAGE_MATERIALS)
    face_class = np.asarray(geometric_class, dtype=np.int64).copy()
    face_class[covered] = len(CLASS_NAMES) + material_index[covered]

    return SurfaceBinding(
        class_names=class_names,
        spec=spec,
        face_class=face_class,
        face_source=_sources(face_class.size, covered, Provenance.IMAGE_WALK_ENTITY),
        face_area_m2=np.asarray(areas, dtype=np.float64),
        provenance={
            "walk_npz": str(walk_npz),
            "stations": int(modal.shape[0]),
            # The join key to vision.provenance.station_registrations, so a later
            # pass can ask how well each of these cameras was placed.
            "image_ids": image_ids,
            "join": "modal_class is already indexed on the tracer mesh, no centroid match",
            "weight": "transient free ray count per station",
            "station_weight": station_weight or "every station at one",
            "min_rays": min_rays,
            "entity_to_material": "vistas_material_prior in semantics.json",
            "substitutions": MATERIAL_SUBSTITUTION,
            "vegetation_note": VEGETATION_NOTE,
            "chosen_material_triangle_counts": {
                f"{SEMANTIC_PREFIX}{materials[i]}": int(np.count_nonzero(material_index[covered] == i))
                for i in range(len(materials))
            },
            "fallback": "geometric orientation rule wherever no station saw the triangle",
        },
    )


def bind_walk_materials(
    areas: np.ndarray,
    geometric_class: np.ndarray,
    *,
    walk_npz: pathlib.Path,
    semantics_path: pathlib.Path | None = None,
    min_rays: int = 1,
    mixture: bool = False,
    over_entity: bool = False,
    facade_only: bool = False,
) -> SurfaceBinding:
    """Bind materials from the SAM 3 material axis of the same fused walk.

    :func:`bind_walk_entities` reads the Mapillary Vistas entity raster and
    pushes it through a fixed ``p(material | entity)`` table, so every
    ``Building`` pixel resolves to one material whatever the photograph shows.
    This reads the ``rf_material`` raster instead, which SAM 3 resolved inside
    the ``Building`` class. Everything else is held identical: the same
    stations, the same rays, the same transient mask, the same ray count
    weighting and the same argmax, so a difference between the two runs is a
    difference in material discrimination and nothing else.

    ``mixture`` votes with the full per-face material histogram rather than each
    station's modal material. It is a sensitivity check on the modal reduction,
    not the primary path, because the entity binding it is compared against is
    modal.

    ``over_entity`` lays the material axis on top of the entity binding instead
    of on top of the geometric rule, which makes the covered set identical to
    :func:`bind_walk_entities`'s. Without it the two differ in coverage as well
    as in material, because ``Ego Vehicle``, the capture car filling the nadir,
    is not a transient class: the entity prior spends its non vehicle mass on
    metal and binds those faces, while the material axis resolves them to
    ``vehicle_composite``, which has no ITU row and is not substituted. That is
    a real difference between the two bindings, but it is not a difference in
    material discrimination, so the isolating comparison sets this flag and the
    coverage difference is measured separately.

    ``facade_only`` narrows that further to the faces the entity binding resolved
    to ``brick``, which is where and only where the entity axis is degenerate:
    ``Building`` and ``Wall`` are the two Vistas classes whose prior peaks on
    brick, so those faces carry one material by construction whatever the
    photograph shows. Everywhere else the entity already names the material, and
    changing those faces measures the modal reduction rather than material
    discrimination. This is the flag that answers the question the ladder could
    not: does resolving brick against glass on the same facade move exposure.
    """
    data = np.load(walk_npz, allow_pickle=True)
    if "modal_material" not in data.files:
        raise SystemExit(
            f"{walk_npz} carries no material axis. Re-run the panoramas with "
            "`semantic_twin.cli.panorama --backend hybrid` and rebuild the walk semantics."
        )
    names = [str(name) for name in data["material_names"]]
    rays = data["clean_rays"].astype(np.float64)
    materials = sorted(IMAGE_MATERIALS)

    # RF vocabulary index -> bound material index, or -1 for the labels that name
    # no surface a tracer can bind: ``unknown`` is the deliberate residual,
    # ``air`` is an aperture, and human tissue and vehicles are transients rather
    # than scene. A face whose modal material is one of those is left to the
    # geometric rule instead of being pushed onto a nearest neighbour.
    route = np.full(len(names), -1, dtype=np.int64)
    for index, name in enumerate(names):
        target = MATERIAL_SUBSTITUTION.get(name, name)
        if target in IMAGE_MATERIALS:
            route[index] = materials.index(target)

    votes = np.zeros((areas.size, len(materials)))
    if mixture:
        counts = data["material_counts"].astype(np.float64)
        if counts.shape[0] != areas.size:
            raise ValueError(f"walk semantics cover {counts.shape[0]} faces, the tracer mesh has {areas.size}")
        for index in range(len(names)):
            if route[index] >= 0:
                votes[:, route[index]] += counts[:, index]
    else:
        modal = data["modal_material"].astype(np.int64)
        if modal.shape[1] != areas.size:
            raise ValueError(f"walk semantics cover {modal.shape[1]} faces, the tracer mesh has {areas.size}")
        for station in range(modal.shape[0]):
            seen = (rays[station] >= min_rays) & (modal[station] >= 0)
            bound = route[modal[station][seen]]
            face = np.nonzero(seen)[0][bound >= 0]
            np.add.at(votes, (face, bound[bound >= 0]), rays[station][face])

    covered = votes.sum(axis=1) > 0.0
    material_index = np.argmax(votes, axis=1)

    class_names, spec = extend_classes(materials, SEMANTIC_PREFIX, IMAGE_MATERIALS)

    if over_entity or facade_only:
        if semantics_path is None:
            raise ValueError("this mode needs semantics_path, because the entity binding is the base")
        base = bind_walk_entities(
            areas, geometric_class, walk_npz=walk_npz, semantics_path=semantics_path, min_rays=min_rays
        )
        base_class = base.face_class
        base_source = base.face_source
        base_note = "entity binding of bind_walk_entities, itself falling back to the geometric orientation rule"
    else:
        base_class = np.asarray(geometric_class, dtype=np.int64)
        base_source = None
        base_note = "geometric orientation rule"

    material_set = covered
    if facade_only:
        brick_class = len(CLASS_NAMES) + materials.index("brick")
        material_set = material_set & (base_class == brick_class)
    face_class = np.asarray(base_class, dtype=np.int64).copy()
    face_class[material_set] = len(CLASS_NAMES) + material_index[material_set]

    unroutable = [name for index, name in enumerate(names) if route[index] < 0]
    return SurfaceBinding(
        class_names=class_names,
        spec=spec,
        face_class=face_class,
        face_source=_sources(face_class.size, material_set, Provenance.IMAGE_WALK_MATERIAL, base_source),
        face_area_m2=np.asarray(areas, dtype=np.float64),
        provenance={
            "walk_npz": str(walk_npz),
            "stations": int(rays.shape[0]),
            "axis": "SAM 3 rf_material, the open-vocabulary material layer of the hybrid backend",
            "join": "modal_material is already indexed on the tracer mesh, no centroid match",
            "weight": "transient free ray count per station",
            "vote": "per face material histogram" if mixture else "per station modal material",
            "base": base_note,
            "restricted_to": (
                "faces the entity binding resolved to brick, which is Building and Wall"
                if facade_only
                else "every face a routable material was bound on"
            ),
            "min_rays": min_rays,
            "concept_backed_ray_fraction": float(
                data["concept_rays"].sum() / max(data["clean_rays"].sum(), 1) if "concept_rays" in data.files else 0.0
            ),
            "unroutable_materials": unroutable,
            "unroutable_rule": (
                "left to the entity binding rather than substituted"
                if over_entity
                else "left to the geometric orientation rule rather than substituted"
            ),
            "substitutions": MATERIAL_SUBSTITUTION,
            "vegetation_note": VEGETATION_NOTE,
            "chosen_material_triangle_counts": {
                f"{SEMANTIC_PREFIX}{materials[i]}": int(np.count_nonzero(material_index[material_set] == i))
                for i in range(len(materials))
            },
            "faces_the_material_axis_set": int(material_set.sum()),
            "fallback": base_note,
        },
    )


def _material_weight(prior: dict[str, Any], entity: str | None, material: str) -> float:
    """Posterior mass a Vistas entity puts on one RF material, after substitution."""
    if entity is None:
        return 0.0
    distribution = prior.get(entity)
    if not distribution:
        return 0.0
    total = float(distribution.get(material, 0.0))
    for source, destination in MATERIAL_SUBSTITUTION.items():
        if destination == material:
            total += float(distribution.get(source, 0.0))
    return total


def _face_normals(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    a = vertices[faces[:, 0]]
    normal = np.cross(vertices[faces[:, 1]] - a, vertices[faces[:, 2]] - a)
    norms = np.linalg.norm(normal, axis=1, keepdims=True)
    return np.divide(normal, np.where(norms > 0.0, norms, 1.0))


def _index_remap(
    vertices: np.ndarray,
    faces: np.ndarray,
    source_vertices: np.ndarray | None,
    source_faces: np.ndarray | None,
    tolerance_m: float,
    normal_cosine: float,
) -> tuple[np.ndarray | None, dict[str, Any]]:
    """Source mesh triangle index -> tracer mesh triangle index, or -1.

    The single and double precision exports of the same tiles are the same
    surface placed differently: the median nearest centroid offset is about a
    quarter of a metre, which is the tile seaming the double precision read was
    written to remove. So the join needs a tolerance far above float32 epsilon,
    and a normal agreement test to stop a facade triangle matching the ground
    triangle at its foot.
    """
    if source_vertices is None or source_faces is None:
        return None, {"remap": "identity, same mesh"}
    from scipy.spatial import cKDTree

    tree = cKDTree(_triangle_centroids(vertices, faces))
    distance, index = tree.query(_triangle_centroids(source_vertices, source_faces))
    target_normal = _face_normals(vertices, faces)[index]
    source_normal = _face_normals(source_vertices, source_faces)
    aligned = np.abs(np.einsum("ij,ij->i", target_normal, source_normal)) >= normal_cosine
    accept = (distance <= tolerance_m) & aligned
    remap = np.where(accept, index, -1).astype(np.int64)
    return remap, {
        "source_triangles": int(source_faces.shape[0]),
        "matched_fraction": float(accept.mean()),
        "rejected_by_distance": float(np.mean(distance > tolerance_m)),
        "rejected_by_normal": float(np.mean(~aligned & (distance <= tolerance_m))),
        "distance_median_m": float(np.median(distance)),
        "distance_p99_m": float(np.quantile(distance, 0.99)),
    }


#: Entities that can stand against the sky and be read as a roofline, but that
#: no operator would mount a base station on. A tree, a hoarding and a lamp post
#: all put a tip on the silhouette; none of them is a site.
#:
#: Vehicles and people are absent on purpose. The fishnet already refuses them
#: as ``transient_object``, so they never reach a face class here, and listing
#: them would suggest a second line of defence that does not exist.
CLUTTER_ENTITIES = frozenset(
    {
        "Banner",
        "Bench",
        "Bike Rack",
        "Billboard",
        "CCTV Camera",
        "Fire Hydrant",
        "Guard Rail",
        "Junction Box",
        "Mailbox",
        "Phone Booth",
        "Pole",
        "Street Light",
        "Traffic Light",
        "Traffic Sign (Back)",
        "Traffic Sign (Front)",
        "Traffic Sign Frame",
        "Trash Can",
        "Utility Pole",
        "Vegetation",
    }
)


def clutter_triangles(
    face_count: int,
    *,
    fishnet_dir: pathlib.Path,
    semantics_path: pathlib.Path,
    remap: np.ndarray | None = None,
    entities: frozenset[str] = CLUTTER_ENTITIES,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Which tracer triangles the panoramas say are clutter rather than building.

    The source set is sampled off the silhouette, and the silhouette is whatever
    is highest along each azimuth. At Tokyo a third of that boundary is screens
    and signs, so a third of the sites land on things that hold no radio. This
    is the mask that lets them be dropped.

    A triangle is clutter when the clutter entities win it on area times
    confidence, so a lamp post seen edge on against a wall does not condemn the
    wall. Returns the mask and a short report, because how much of a square this
    removes is a number the study should print rather than assume.
    """
    document = json.loads(pathlib.Path(semantics_path).read_text())
    labels = {int(k): v for k, v in document["entity_id2label"].items()}
    files = sorted(pathlib.Path(fishnet_dir).glob("*_fishnet.npz"))
    if not files:
        raise FileNotFoundError(f"no fishnet npz under {fishnet_dir}")

    against = np.zeros(face_count)
    for_it = np.zeros(face_count)
    seen: dict[str, float] = {}
    for path in files:
        data = np.load(path, allow_pickle=True)
        source = data["face_source_triangle"].astype(np.int64)
        target = source if remap is None else remap[source]
        weight = data["face_area_m2"].astype(np.float64) * data["face_confidence"].astype(np.float64)
        is_clutter = np.array([labels.get(int(c)) in entities for c in data["face_class"]])
        good = (target >= 0) & (target < face_count)
        np.add.at(against, target[good & is_clutter], weight[good & is_clutter])
        np.add.at(for_it, target[good & ~is_clutter], weight[good & ~is_clutter])
        for c, w in zip(data["face_class"], weight, strict=True):
            name = labels.get(int(c))
            if name in entities:
                seen[name] = seen.get(name, 0.0) + float(w)

    mask = against > for_it
    report = {
        "fishnet_dir": str(fishnet_dir),
        "views": len(files),
        "clutter_triangles": int(mask.sum()),
        "clutter_fraction_of_seen": float(mask.sum() / max(1, int(((against + for_it) > 0.0).sum()))),
        "weight_by_entity": {k: round(v, 2) for k, v in sorted(seen.items(), key=lambda kv: -kv[1])},
        "rule": "area times confidence, clutter entities against everything else, per tracer triangle",
    }
    return mask, report
