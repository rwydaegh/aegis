"""Bind the panorama semantic posterior to the support mesh triangles.

The fishnet surfaces in ``outputs/korenmarkt_fishnet_vistas`` carry, per face,
the Mapillary Vistas entity class the panorama assigned it and the support mesh
triangle it was cut from. That is the join key. Aggregating the fishnet faces
back onto their source triangles, area weighted, gives a per triangle class
vote, and ``vistas_material_prior`` in ``semantics.json`` maps each entity class
to a distribution over the RF material vocabulary that
``config/itu_p2040_4.json`` already grounds.

Two caveats that belong in the report and not in a footnote.

The panoramas see a small fraction of a 130 m crop. Every triangle no panorama
saw falls back to the geometric rule of :mod:`semantic_twin.propagation.scene`,
and :func:`bind` returns the covered fraction so the run can state it.

The fishnet was built against ``inhouse_leaf_130m.ply``, the single precision
export, while the tracer uses ``inhouse_leaf_130m_f64.ply``. They differ by 118
triangles out of about 158k, so the source triangle indices cannot simply be
reused. The join is done on triangle centroids with a distance ceiling, and the
matched fraction is reported rather than assumed.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from typing import Any

import numpy as np

from .scene import CLASS_BINDING, CLASS_NAMES

#: RF material vocabulary -> (ITU-R P.2040-4 row, roughness class). The ITU row
#: comes from ``material_grounding`` in ``semantics.json``. The roughness class
#: is the coarsest defensible representative of that material as a metre scale
#: outdoor patch, taken from ``config/surface_roughness.json``.
MATERIAL_BINDING: dict[str, tuple[str, str]] = {
    "brick": ("brick", "brick_wall_with_mortar_joints"),
    "concrete": ("concrete", "concrete_board_marked_or_exposed_aggregate"),
    "plasterboard": ("plasterboard", "render_plaster_painted"),
    "wood": ("wood", "wood_cladding"),
    "plywood": ("plywood", "wood_cladding"),
    "chipboard": ("chipboard", "wood_cladding"),
    "glass": ("glass", "glass_glazing_unit"),
    "metal": ("metal", "metal_cladding_panel_smooth"),
    "marble": ("marble", "stone_ashlar_dressed"),
    "asphalt_concrete": ("asphalt_concrete", "asphalt_road_dense_graded"),
    # A canopy has no interface, so giving it one is not a coarse approximation,
    # it is a different object. Leaf area index times leaf thickness over canopy
    # depth puts the canopy volume fraction at 6.4e-5, and Maxwell-Garnett then
    # gives a boundary reflectance of 1.9e-9 against the 0.029 of the P.2040
    # wood row, which is 71.8 dB of reflection that is not there. Routing
    # vegetation to the vacuum row removes that spurious reflection.
    #
    # This is better than the wood row and it is still not right. A vacuum row
    # face absorbs rather than transmits, so it removes the false glint but
    # keeps the false block, which puts it between "opaque surface" and "cut
    # out". The correct treatment is a participating medium, which needs a
    # tracer hook that is not written here.
    "vegetation_effective": ("vacuum_air", "glass_glazing_unit"),
}

#: RF materials with no ITU row, mapped to the nearest row that does have one.
#: Each substitution is a judgement, so each is listed rather than defaulted.
MATERIAL_SUBSTITUTION: dict[str, str] = {
    "ceramic": "marble",  # no P.2040 row, dense fired mineral
    "polymer": "wood",  # no P.2040 row, low permittivity dielectric
    "fabric": "wood",  # no P.2040 row, low permittivity dielectric
    "soil": "concrete",  # P.527-6 not P.2040, and not implemented here
    "water": "concrete",  # standing water is not modelled
}

#: Recorded in every manifest, because it changes how the vegetation numbers
#: should be read. Recommendation ITU-R P.833 tabulates nothing anywhere in FR2
#: and nothing at all between 12.5 and 37 GHz, so at the 15 GHz carrier this
#: study leads on, every vegetation parameter is an interpolation across a gap
#: in the recommendation rather than a value read from it.
VEGETATION_NOTE = (
    "ITU-R P.833 has no tabulated data in FR2 and nothing between 12.5 and "
    "37 GHz, so every vegetation parameter at 15 GHz is an interpolation "
    "across a gap in the recommendation. Vegetation is bound to the P.2040 "
    "vacuum row rather than to wood: a canopy volume fraction of 6.4e-5 gives "
    "a Maxwell-Garnett boundary reflectance of 1.9e-9 against the wood row's "
    "0.029, so the wood row would add 71.8 dB of reflection that is not there. "
    "A vacuum row face still absorbs rather than transmits, so this removes "
    "the false glint and keeps the false block. The correct treatment is a "
    "participating medium and is not implemented."
)


@dataclass(frozen=True)
class SemanticBinding:
    """Per triangle material class, with the fallback made explicit."""

    #: Index into the extended class table, see :attr:`class_names`.
    face_class: np.ndarray
    class_names: tuple[str, ...]
    #: Class -> (ITU row, roughness class), for every entry of ``class_names``.
    class_binding: dict[str, tuple[str, str]]
    covered_fraction_by_face: float
    covered_fraction_by_area: float
    provenance: dict[str, Any]


def _triangle_centroids(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    return vertices[faces].mean(axis=1)


def bind(
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
) -> SemanticBinding:
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

    materials = sorted(MATERIAL_BINDING)
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

    class_names = tuple(CLASS_NAMES) + tuple(f"semantic_{m}" for m in materials)
    class_binding = dict(CLASS_BINDING)
    for material in materials:
        class_binding[f"semantic_{material}"] = MATERIAL_BINDING[material]

    face_class = np.asarray(geometric_class, dtype=np.int64).copy()
    face_class[covered] = len(CLASS_NAMES) + material_index[covered]

    chosen = {
        f"semantic_{materials[i]}": int(np.count_nonzero(material_index[covered] == i)) for i in range(len(materials))
    }
    return SemanticBinding(
        face_class=face_class,
        class_names=class_names,
        class_binding=class_binding,
        covered_fraction_by_face=float(covered.mean()),
        covered_fraction_by_area=float(areas[covered].sum() / areas.sum()),
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


def bind_from_walk(
    areas: np.ndarray,
    geometric_class: np.ndarray,
    *,
    walk_npz: pathlib.Path,
    semantics_path: pathlib.Path,
    min_rays: int = 1,
) -> SemanticBinding:
    """Bind materials from the fused multi station walk semantics.

    ``walk_semantic.npz`` carries ``modal_class`` and ``clean_rays`` on the
    tracer's own mesh, one row per Mapillary station, so no centroid join is
    needed. Stations vote per face with weight equal to their transient free
    ray count, which is both an evidence weight and an implicit view quality
    weight, since a face seen edge on collects few rays.

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

    materials = sorted(MATERIAL_BINDING)
    lookup = np.zeros((max(entity_labels) + 2, len(materials)))
    for entity_id, name in entity_labels.items():
        for material_index, material in enumerate(materials):
            lookup[entity_id, material_index] = _material_weight(material_prior, name, material)

    votes = np.zeros((areas.size, len(materials)))
    for station in range(modal.shape[0]):
        seen = rays[station] >= min_rays
        classes = np.clip(modal[station], 0, lookup.shape[0] - 1)
        votes[seen] += lookup[classes[seen]] * rays[station][seen, None]

    covered = votes.sum(axis=1) > 0.0
    material_index = np.argmax(votes, axis=1)

    class_names = tuple(CLASS_NAMES) + tuple(f"semantic_{m}" for m in materials)
    class_binding = dict(CLASS_BINDING)
    for material in materials:
        class_binding[f"semantic_{material}"] = MATERIAL_BINDING[material]

    face_class = np.asarray(geometric_class, dtype=np.int64).copy()
    face_class[covered] = len(CLASS_NAMES) + material_index[covered]

    return SemanticBinding(
        face_class=face_class,
        class_names=class_names,
        class_binding=class_binding,
        covered_fraction_by_face=float(covered.mean()),
        covered_fraction_by_area=float(areas[covered].sum() / areas.sum()),
        provenance={
            "walk_npz": str(walk_npz),
            "stations": int(modal.shape[0]),
            "join": "modal_class is already indexed on the tracer mesh, no centroid match",
            "weight": "transient free ray count per station",
            "min_rays": min_rays,
            "entity_to_material": "vistas_material_prior in semantics.json",
            "substitutions": MATERIAL_SUBSTITUTION,
            "vegetation_note": VEGETATION_NOTE,
            "chosen_material_triangle_counts": {
                f"semantic_{materials[i]}": int(np.count_nonzero(material_index[covered] == i))
                for i in range(len(materials))
            },
            "fallback": "geometric orientation rule wherever no station saw the triangle",
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
