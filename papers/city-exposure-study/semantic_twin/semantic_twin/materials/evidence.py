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
import hashlib
import pathlib
from dataclasses import dataclass
from typing import Any

import numpy as np

from .binding import CLASS_NAMES, Provenance, SurfaceBinding, extend_classes
from .catalogue import IMAGE_MATERIALS, MATERIAL_SUBSTITUTION, VEGETATION_NOTE, load_table
from .support import (
    SUPPORT_COMPATIBILITY_VERSION,
    SupportKind,
    entity_supports_atlas_cell,
    entity_support_kind,
    entity_supports_geometric_class,
)

#: Prefix every evidence class name carries in the class table.
SEMANTIC_PREFIX = "semantic_"
VEGETATION_FORM_NAMES = ("unresolved", "ground_vegetation", "woody_canopy")
VEGETATION_SUBTYPE_NAMES = ("unresolved", "grass", "shrub", "tree", "forest")


@dataclass(frozen=True)
class VegetationBinding:
    """Per-face vegetation form kept apart from surface material classes.

    A canopy is a volume and grass is ground cover. Neither belongs in the
    interface-only class index of :class:`SurfaceBinding`. Zero is unresolved
    on both axes, including faces seen only by the dense Vegetation class.
    """

    form_names: tuple[str, ...]
    subtype_names: tuple[str, ...]
    face_form: np.ndarray
    face_subtype: np.ndarray
    face_weight: np.ndarray
    face_area_m2: np.ndarray
    provenance: dict[str, Any]

    def __post_init__(self) -> None:
        count = self.face_form.shape[0]
        shapes = (self.face_subtype.shape, self.face_weight.shape, self.face_area_m2.shape)
        if any(shape != (count,) for shape in shapes):
            raise ValueError(f"{count} vegetation forms but incompatible subtype, weight, or area arrays")
        _validate_vegetation_axis(self.form_names, self.face_form, "form")
        _validate_vegetation_axis(self.subtype_names, self.face_subtype, "subtype")
        if np.any((self.face_subtype > 0) & (self.face_form == 0)):
            raise ValueError("a vegetation subtype cannot resolve where vegetation form is unresolved")
        if np.any(self.face_weight < 0.0):
            raise ValueError("vegetation evidence weight cannot be negative")
        if not self.provenance:
            raise ValueError("a vegetation binding must record how its forms were decided")

    @property
    def resolved(self) -> np.ndarray:
        return self.face_form > 0

    @property
    def covered_fraction_by_face(self) -> float:
        return float(self.resolved.mean()) if self.face_form.size else 0.0

    @property
    def covered_fraction_by_area(self) -> float:
        total = float(self.face_area_m2.sum())
        return float(self.face_area_m2[self.resolved].sum() / total) if total else 0.0


JOINT_ATLAS_FALLBACK_NAMES = (
    "bound",
    "unobserved",
    "conflict_or_tie",
    "compatible_but_unroutable",
)


@dataclass(frozen=True)
class JointAtlasMaterialEvidence:
    """Safe material evidence for every observed cell of a joint atlas.

    The three posterior arrays deliberately answer different questions.
    ``raw_material_posterior`` is the material marginal of every stored joint
    observation. ``host_material_posterior`` keeps only entries whose entity
    can live on the geometric support surface. ``transport_posterior`` also
    applies the declared entity-to-material vocabulary and is normalised over
    the material mass that the tracer can route. Keeping all three prevents an
    object material from disappearing merely because it was refused.

    ``transport_label`` is a deterministic convenience label. It uses the
    lowest material index on an exact tie and is ``-1`` wherever the geometric
    fallback must remain in force. Scientific uncertainty consumers should use
    ``transport_posterior`` rather than this reduction.
    """

    triangle_id: np.ndarray
    texel_row: np.ndarray
    texel_column: np.ndarray
    input_material_names: tuple[str, ...]
    transport_material_names: tuple[str, ...]
    raw_material_posterior: np.ndarray
    host_material_posterior: np.ndarray
    transport_posterior: np.ndarray
    observed_weight: np.ndarray
    host_compatible_weight: np.ndarray
    host_incompatible_weight: np.ndarray
    routable_weight: np.ndarray
    unroutable_weight: np.ndarray
    fallback_state: np.ndarray
    transport_label: np.ndarray
    provenance: dict[str, Any]

    def __post_init__(self) -> None:
        cells = self.triangle_id.size
        vectors = (
            self.texel_row,
            self.texel_column,
            self.observed_weight,
            self.host_compatible_weight,
            self.host_incompatible_weight,
            self.routable_weight,
            self.unroutable_weight,
            self.fallback_state,
            self.transport_label,
        )
        if any(np.asarray(value).shape != (cells,) for value in vectors):
            raise ValueError("joint atlas material evidence arrays disagree on cell count")
        if self.raw_material_posterior.shape != (cells, len(self.input_material_names)):
            raise ValueError("raw material posterior does not match the atlas material vocabulary")
        if self.host_material_posterior.shape != self.raw_material_posterior.shape:
            raise ValueError("host material posterior must preserve the full input vocabulary")
        if self.transport_posterior.shape != (cells, len(self.transport_material_names)):
            raise ValueError("transport posterior does not match the routable material vocabulary")
        if cells and (self.fallback_state.min() < 0 or self.fallback_state.max() >= len(JOINT_ATLAS_FALLBACK_NAMES)):
            raise ValueError("joint atlas fallback state is outside its declared vocabulary")
        if cells and (
            self.transport_label.min() < -1 or self.transport_label.max() >= len(self.transport_material_names)
        ):
            raise ValueError("joint atlas transport label is outside its declared vocabulary")
        if np.any(self.transport_posterior < 0.0) or np.any(self.raw_material_posterior < 0.0):
            raise ValueError("joint atlas material posterior cannot be negative")
        bound = self.fallback_state == JOINT_ATLAS_FALLBACK_NAMES.index("bound")
        if np.any(self.transport_label[bound] < 0) or np.any(self.transport_label[~bound] != -1):
            raise ValueError("only bound atlas cells may carry a transport label")
        if not self.provenance:
            raise ValueError("joint atlas material evidence must retain provenance")

    @property
    def bound(self) -> np.ndarray:
        """Cells whose paired entity and material evidence passed every gate."""
        return self.fallback_state == JOINT_ATLAS_FALLBACK_NAMES.index("bound")

    def class_names_and_spec(self) -> tuple[tuple[str, ...], dict[str, Any]]:
        """Return the stable tracer class namespace for the central labels."""
        return extend_classes(list(self.transport_material_names), SEMANTIC_PREFIX, IMAGE_MATERIALS)

    @property
    def class_names(self) -> tuple[str, ...]:
        """Tracer namespace indexed by :attr:`tracer_posterior`."""
        return self.class_names_and_spec()[0]

    @property
    def tracer_posterior(self) -> np.ndarray:
        """Cell posterior padded into the tracer's complete class namespace."""
        posterior = np.zeros((self.triangle_id.size, len(self.class_names)), dtype=np.float64)
        posterior[:, len(CLASS_NAMES) :] = self.transport_posterior
        return posterior

    @property
    def support_weight(self) -> np.ndarray:
        """Absolute fused image support carried by each atlas cell."""
        return self.observed_weight

    @property
    def confidence(self) -> np.ndarray:
        """Largest safe transport posterior mass, zero on fallback cells."""
        confidence = np.zeros(self.triangle_id.size, dtype=np.float64)
        if self.transport_posterior.shape[1]:
            confidence[self.bound] = self.transport_posterior[self.bound].max(axis=1)
        return confidence

    def central_cells(self, resolution: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
        """Return the cell nearest the barycentre of each observed triangle.

        Distance is measured in canonical barycentric UV. Equal distances use
        the lowest row, then the lowest column. This label exists for compact
        summaries only. The complete cell posterior remains the transport and
        subdivision input.
        """
        height, width = (int(resolution[0]), int(resolution[1]))
        if height < 2 or width < 2:
            raise ValueError("atlas resolution must be at least 2 by 2")
        if not self.triangle_id.size:
            return np.empty(0, dtype=np.int64), np.empty(0, dtype=np.int64)
        distance = np.square(self.texel_row / (height - 1) - 1.0 / 3.0) + np.square(
            self.texel_column / (width - 1) - 1.0 / 3.0
        )
        index = np.arange(self.triangle_id.size, dtype=np.int64)
        order = np.lexsort((index, self.texel_column, self.texel_row, distance, self.triangle_id))
        ordered_triangle = self.triangle_id[order]
        first = np.concatenate(([True], ordered_triangle[1:] != ordered_triangle[:-1]))
        return ordered_triangle[first], order[first]


@dataclass(frozen=True, kw_only=True)
class JointAtlasSurfaceBinding(SurfaceBinding):
    """A normal surface binding plus the mixture behind every emitted face."""

    posterior_names: tuple[str, ...]
    face_material_posterior: np.ndarray
    face_atlas_cell: np.ndarray
    face_parent_triangle: np.ndarray
    face_fallback_state: np.ndarray

    def __post_init__(self) -> None:
        super().__post_init__()
        count = self.face_class.size
        if self.face_material_posterior.shape != (count, len(self.posterior_names)):
            raise ValueError("face material posterior does not match the emitted surface")
        if any(
            np.asarray(value).shape != (count,)
            for value in (self.face_atlas_cell, self.face_parent_triangle, self.face_fallback_state)
        ):
            raise ValueError("joint atlas face mapping does not match the emitted surface")
        if np.any(self.face_material_posterior < 0.0):
            raise ValueError("face material posterior cannot be negative")


def _vegetation_names(data: Any, key: str, fallback: tuple[str, ...]) -> tuple[str, ...]:
    if key not in data.files:
        return fallback
    names = tuple(str(name) for name in data[key])
    if not names or names[0] != "unresolved":
        raise ValueError(f"{key} must start with unresolved")
    return names


def _validate_vegetation_axis(names: tuple[str, ...], values: np.ndarray, axis: str) -> None:
    if not names or names[0] != "unresolved":
        raise ValueError(f"vegetation {axis}s must start with unresolved")
    if values.size and (values.min() < 0 or values.max() >= len(names)):
        raise ValueError(f"face_{axis} leaves the vegetation {axis}s it names")


def _legacy_vegetation_binding(
    areas: np.ndarray,
    walk_npz: pathlib.Path,
    form_names: tuple[str, ...],
    subtype_names: tuple[str, ...],
) -> VegetationBinding:
    zeros = np.zeros(areas.size, dtype=np.uint8)
    return VegetationBinding(
        form_names=form_names,
        subtype_names=subtype_names,
        face_form=zeros,
        face_subtype=zeros.copy(),
        face_weight=np.zeros(areas.size, dtype=np.float64),
        face_area_m2=areas,
        provenance={
            "walk_npz": str(walk_npz),
            "status": "legacy walk file with no vegetation-form axis",
            "dense_vegetation": "unresolved",
        },
    )


def _validate_walk_vegetation(
    modal_form: np.ndarray,
    modal_subtype: np.ndarray,
    rays: np.ndarray,
    areas: np.ndarray,
    form_names: tuple[str, ...],
    subtype_names: tuple[str, ...],
) -> None:
    if modal_form.shape != modal_subtype.shape or modal_form.shape != rays.shape:
        raise ValueError("walk vegetation form, subtype, and ray arrays have different shapes")
    if modal_form.ndim != 2 or modal_form.shape[1] != areas.size:
        faces = modal_form.shape[1] if modal_form.ndim == 2 else "an invalid rank"
        raise ValueError(f"walk vegetation covers {faces} faces, the tracer mesh has {areas.size}")
    _validate_vegetation_axis(form_names, modal_form, "form")
    _validate_vegetation_axis(subtype_names, modal_subtype, "subtype")


def _vegetation_votes(
    labels: np.ndarray,
    rays: np.ndarray,
    weights: np.ndarray,
    order: np.ndarray,
    classes: int,
    min_rays: int,
    allowed_form: np.ndarray | None = None,
) -> np.ndarray:
    votes = np.zeros((rays.shape[1], classes), dtype=np.float64)
    for station in order:
        eligible = (rays[station] >= min_rays) & (labels[station] > 0)
        if allowed_form is not None:
            eligible &= allowed_form[station] > 0
        face = np.flatnonzero(eligible)
        contribution = rays[station, face] * weights[station]
        np.add.at(votes, (face, labels[station, face]), contribution)
    return votes


def bind_walk_vegetation(
    areas: np.ndarray,
    *,
    walk_npz: pathlib.Path,
    min_rays: int = 1,
    station_weight: dict[str, float] | None = None,
) -> VegetationBinding:
    """Bind ground vegetation and woody canopy without making either a surface.

    New walk files carry one vegetation form per station and face, voted with
    the rays that hit a vegetation-specific concept mask. Old walk files carry
    no such axis. They load as fully unresolved, which preserves their legacy
    meaning instead of treating dense ``Vegetation`` as canopy.
    """
    areas = np.asarray(areas, dtype=np.float64)
    with np.load(walk_npz, allow_pickle=True) as data:
        form_names = _vegetation_names(data, "vegetation_form_names", VEGETATION_FORM_NAMES)
        subtype_names = _vegetation_names(data, "vegetation_subtype_names", VEGETATION_SUBTYPE_NAMES)
        required = {"modal_vegetation_form", "modal_vegetation_subtype", "vegetation_rays"}
        present = required & set(data.files)
        if not present:
            return _legacy_vegetation_binding(areas, walk_npz, form_names, subtype_names)
        if present != required:
            missing = sorted(required - present)
            raise ValueError(f"walk vegetation schema is incomplete; missing {missing}")
        modal_form = data["modal_vegetation_form"].astype(np.int64)
        modal_subtype = data["modal_vegetation_subtype"].astype(np.int64)
        rays = data["vegetation_rays"].astype(np.float64)
        has_image_ids = "image_ids" in data.files
        image_ids = [str(name) for name in data["image_ids"]] if has_image_ids else []

    _validate_walk_vegetation(modal_form, modal_subtype, rays, areas, form_names, subtype_names)
    if has_image_ids and len(image_ids) != modal_form.shape[0]:
        raise ValueError(f"walk vegetation has {modal_form.shape[0]} station rows but {len(image_ids)} image_ids")

    weights = _station_weights(image_ids, modal_form.shape[0], station_weight)
    # Canonical station order makes a weighted floating-point vote invariant to
    # row order when image ids are present. Unweighted integer ray counts are
    # exact in either order.
    order = np.argsort(np.asarray(image_ids), kind="stable") if image_ids else np.arange(modal_form.shape[0])
    form_votes = _vegetation_votes(modal_form, rays, weights, order, len(form_names), min_rays)

    face_form = form_votes.argmax(axis=1).astype(np.uint8)
    face_weight = form_votes.sum(axis=1)
    face_form[np.isclose(face_weight, 0.0)] = 0
    matching_form = np.where(modal_form == face_form, modal_form, 0)
    subtype_votes = _vegetation_votes(
        modal_subtype,
        rays,
        weights,
        order,
        len(subtype_names),
        min_rays,
        matching_form,
    )
    face_subtype = subtype_votes.argmax(axis=1).astype(np.uint8)
    face_subtype[np.isclose(subtype_votes.sum(axis=1), 0.0)] = 0
    return VegetationBinding(
        form_names=form_names,
        subtype_names=subtype_names,
        face_form=face_form,
        face_subtype=face_subtype,
        face_weight=face_weight,
        face_area_m2=areas,
        provenance={
            "walk_npz": str(walk_npz),
            "stations": int(modal_form.shape[0]),
            "image_ids": image_ids,
            "weight": "vegetation-specific rays per station",
            "station_weight": station_weight or "every station at one",
            "min_rays": min_rays,
            "dense_vegetation": "unresolved and contributes no vote",
            "tie_break": "lowest vocabulary index",
        },
    )


def _triangle_centroids(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    return vertices[faces].mean(axis=1)


def _sources(count: int, covered: np.ndarray, kind: Provenance, base: np.ndarray | None = None) -> np.ndarray:
    origin = np.zeros(count, dtype=np.int8) if base is None else base.astype(np.int8).copy()
    origin[covered] = int(kind)
    return origin


@dataclass
class _SupportEvidence:
    """Material votes and the structural evidence that licenses them."""

    material_votes: np.ndarray
    compatible_weight: np.ndarray
    incompatible_weight: np.ndarray
    observed_weight: np.ndarray
    weight_by_kind: dict[str, float]
    embedded: dict[str, dict[str, Any]]


def _empty_support_evidence(face_count: int, material_count: int) -> _SupportEvidence:
    return _SupportEvidence(
        material_votes=np.zeros((face_count, material_count), dtype=np.float64),
        compatible_weight=np.zeros(face_count, dtype=np.float64),
        incompatible_weight=np.zeros(face_count, dtype=np.float64),
        observed_weight=np.zeros(face_count, dtype=np.float64),
        weight_by_kind={kind.value: 0.0 for kind in SupportKind},
        embedded={},
    )


def _record_support(
    evidence: _SupportEvidence,
    face: np.ndarray,
    entity: np.ndarray,
    weight: np.ndarray,
    geometric_class: np.ndarray,
    labels: dict[int, str],
    material_lookup: np.ndarray,
) -> None:
    """Add one deterministic block of entity observations to a face tally."""
    if not (face.shape == entity.shape == weight.shape):
        raise ValueError("support face, entity, and weight arrays have different shapes")
    positive = np.isfinite(weight) & (weight > 0.0)
    face = np.asarray(face[positive], dtype=np.int64)
    entity = np.asarray(entity[positive], dtype=np.int64)
    weight = np.asarray(weight[positive], dtype=np.float64)
    if not face.size:
        return

    names = np.asarray([labels.get(int(identifier)) for identifier in entity], dtype=object)
    kinds = np.asarray([entity_support_kind(name).value for name in names], dtype=object)
    compatible = np.fromiter(
        (
            entity_supports_geometric_class(name, int(geometric_class[target]))
            for name, target in zip(names, face, strict=True)
        ),
        dtype=bool,
        count=face.size,
    )
    np.add.at(evidence.observed_weight, face, weight)
    np.add.at(evidence.compatible_weight, face[compatible], weight[compatible])
    np.add.at(evidence.incompatible_weight, face[~compatible], weight[~compatible])

    valid_entity = (entity >= 0) & (entity < material_lookup.shape[0])
    vote = compatible & valid_entity
    if np.any(vote):
        contribution = material_lookup[entity[vote]] * weight[vote, None]
        np.add.at(evidence.material_votes, face[vote], contribution)

    for kind in SupportKind:
        selected = kinds == kind.value
        evidence.weight_by_kind[kind.value] += float(weight[selected].sum())

    embedded = kinds == SupportKind.EMBEDDED_SUBFACE.value
    for name in sorted({str(item) for item in names[embedded]}):
        selected = embedded & (names == name)
        faces = np.unique(face[selected])
        entry = evidence.embedded.setdefault(
            name,
            {"observations": 0, "evidence_weight": 0.0, "target_faces": set()},
        )
        entry["observations"] += int(np.count_nonzero(selected))
        entry["evidence_weight"] += float(weight[selected].sum())
        entry["target_faces"].update(int(index) for index in faces)


def _support_decision(
    evidence: _SupportEvidence,
    areas: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Accept only a strict host-surface majority with routable material mass."""
    accepted = evidence.compatible_weight > evidence.incompatible_weight
    routable = evidence.material_votes.sum(axis=1) > 0.0
    covered = accepted & routable
    observed = evidence.observed_weight > 0.0
    conflict = observed & ~accepted
    compatible_unbound = accepted & ~routable
    unobserved = ~observed
    partitions = {
        "unobserved": unobserved,
        "observed_conflict_or_tie": conflict,
        "compatible_but_unroutable": compatible_unbound,
        "bound": covered,
    }
    total_area = float(np.asarray(areas, dtype=np.float64).sum())
    structural_agreement = np.divide(
        evidence.compatible_weight,
        evidence.observed_weight,
        out=np.zeros_like(evidence.compatible_weight),
        where=evidence.observed_weight > 0.0,
    )
    winner_share = np.divide(
        evidence.material_votes.max(axis=1),
        evidence.material_votes.sum(axis=1),
        out=np.zeros(evidence.material_votes.shape[0], dtype=np.float64),
        where=evidence.material_votes.sum(axis=1) > 0.0,
    )
    embedded = {
        name: {
            "observations": int(entry["observations"]),
            "evidence_weight": float(entry["evidence_weight"]),
            "target_faces": len(entry["target_faces"]),
        }
        for name, entry in sorted(evidence.embedded.items())
    }
    return (
        accepted,
        covered,
        {
            "version": SUPPORT_COMPATIBILITY_VERSION,
            "rule": (
                "geometry keeps the structural class; compatible host-surface evidence must carry "
                "strictly more weight than all incompatible, object, vegetation, void, and embedded-subface evidence"
            ),
            "tie": "geometric fallback",
            "weight_by_kind": {name: float(value) for name, value in evidence.weight_by_kind.items()},
            "face_partition": {name: int(mask.sum()) for name, mask in partitions.items()},
            "area_fraction_partition": {
                name: float(np.asarray(areas)[mask].sum() / total_area) if total_area else 0.0
                for name, mask in partitions.items()
            },
            "structural_agreement_on_bound_faces": _finite_summary(structural_agreement[covered]),
            "material_winner_share_on_bound_faces": _finite_summary(winner_share[covered]),
            "embedded_subface_evidence": {
                "policy": (
                    "retained as evidence but excluded from host material votes until physical within-triangle "
                    "coverage can be represented"
                ),
                "entities": embedded,
            },
        },
    )


def _finite_summary(values: np.ndarray) -> dict[str, float | int]:
    values = np.asarray(values, dtype=np.float64)
    values = values[np.isfinite(values)]
    if not values.size:
        return {"count": 0}
    return {
        "count": int(values.size),
        "minimum": float(values.min()),
        "median": float(np.median(values)),
        "maximum": float(values.max()),
    }


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
    lookup = np.zeros((max(entity_labels) + 2, len(materials)), dtype=np.float64)
    for entity_id, name in entity_labels.items():
        for material_index, material in enumerate(materials):
            lookup[entity_id, material_index] = _material_weight(material_prior, name, material)
    evidence = _empty_support_evidence(faces.shape[0], len(materials))
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
        support_weight = face_area * confidence
        selected = np.flatnonzero(valid)
        selected = selected[np.lexsort((support_weight[selected], face_class[selected], target[selected]))]
        _record_support(
            evidence,
            target[selected],
            face_class[selected],
            support_weight[selected],
            np.asarray(geometric_class, dtype=np.int64),
            entity_labels,
            lookup,
        )
        per_view.append(
            {
                "file": path.name,
                "fishnet_faces": int(face_class.size),
                "unmatched_source_triangles": unmatched,
                "surface_area_m2": float(face_area.sum()),
            }
        )

    _accepted, covered, support_report = _support_decision(evidence, areas)
    material_index = np.argmax(evidence.material_votes, axis=1)

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
            "support_compatibility": support_report,
            "fallback": "geometric orientation rule wherever compatible host-surface evidence did not win",
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


def _canonical_station_order(image_ids: list[str], modal: np.ndarray, rays: np.ndarray) -> np.ndarray:
    """Stable station order, including legacy files with no station names."""
    if image_ids:
        if len(image_ids) != modal.shape[0]:
            raise ValueError(f"walk has {modal.shape[0]} station rows but {len(image_ids)} image_ids")
        if len(set(image_ids)) != len(image_ids):
            raise ValueError("walk image_ids must be unique for order-invariant evidence fusion")
        return np.argsort(np.asarray(image_ids), kind="stable")
    digest = []
    for station in range(modal.shape[0]):
        checksum = hashlib.sha256()
        checksum.update(np.ascontiguousarray(modal[station]).tobytes())
        checksum.update(np.ascontiguousarray(rays[station]).tobytes())
        digest.append(checksum.hexdigest())
    return np.argsort(np.asarray(digest), kind="stable")


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

    evidence = _empty_support_evidence(areas.size, len(materials))
    order = _canonical_station_order(image_ids, modal, rays)
    for station in order:
        seen = rays[station] >= min_rays
        face = np.flatnonzero(seen)
        _record_support(
            evidence,
            face,
            modal[station, face],
            rays[station, face] * weights[station],
            np.asarray(geometric_class, dtype=np.int64),
            entity_labels,
            lookup,
        )

    _accepted, covered, support_report = _support_decision(evidence, areas)
    material_index = np.argmax(evidence.material_votes, axis=1)

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
            "support_compatibility": support_report,
            "fallback": "geometric orientation rule wherever compatible host-surface evidence did not win",
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
    """Refuse SAM material binding until entity and material evidence is joint.

    Existing walk files store independent per-face modes and marginal material
    counts. They cannot prove that a material pixel belongs to the compatible
    host entity on the same face. Binding either reduction would let object
    material repaint structural geometry, so all four material modes stop here
    until the walk schema carries joint entity-by-material evidence.
    """
    data = np.load(walk_npz, allow_pickle=True)
    if "modal_material" not in data.files:
        raise SystemExit(
            f"{walk_npz} carries no material axis. Re-run the panoramas with "
            "`semantic_twin.cli.panorama --backend hybrid` and rebuild the walk semantics."
        )
    modes = [
        name
        for name, enabled in (("mixture", mixture), ("over_entity", over_entity), ("facade_only", facade_only))
        if enabled
    ]
    mode = ", ".join(modes) if modes else "modal"
    raise ValueError(
        f"walk material mode {mode} is unsafe: {walk_npz} stores independent entity and material reductions, "
        f"not joint entity-by-material evidence; requested for {np.asarray(areas).size} faces with geometric "
        f"shape {np.asarray(geometric_class).shape}, semantics {semantics_path}, and min_rays={min_rays}"
    )


_JOINT_ATLAS_KEYS = frozenset(
    {
        "resolution",
        "triangle_count",
        "entity_names",
        "material_names",
        "triangle_ids",
        "texel_offsets",
        "texel_row",
        "texel_column",
        "joint_offsets",
        "joint_entity",
        "joint_material",
        "joint_weight",
        "support_weight",
    }
)


def _routed_material(name: str) -> str | None:
    routed = MATERIAL_SUBSTITUTION.get(name, name)
    return routed if routed in IMAGE_MATERIALS else None


def material_table_for_names(
    names: tuple[str, ...] | list[str] | np.ndarray,
    config_dir: pathlib.Path,
    frequency_hz: float,
) -> tuple[Any, np.ndarray]:
    """Build the canonical tracer table and map raw material names into it.

    Unknown names map to ``-1``. Substituted names map to the declared target
    in :data:`MATERIAL_SUBSTITUTION`. The table always uses the same sorted RF
    material namespace, so a refined mesh sidecar cannot change class indices
    by omitting a material that happened not to appear in one scene.

    Structural compatibility still needs a paired entity and geometric host.
    It is applied by :func:`bind_joint_atlas_materials`, before this material
    mapping is allowed to decide a face class.
    """
    raw_names = tuple(str(name) for name in names)
    materials = tuple(sorted(IMAGE_MATERIALS))
    class_names, spec = extend_classes(list(materials), SEMANTIC_PREFIX, IMAGE_MATERIALS)
    table = load_table(
        pathlib.Path(config_dir),
        float(frequency_hz),
        class_names=class_names,
        class_binding=spec,
        class_rule="joint semantic-material atlas with host-surface compatibility",
    )
    index = {name: len(CLASS_NAMES) + position for position, name in enumerate(materials)}
    raw_to_table = np.asarray(
        [index.get(_routed_material(name), -1) for name in raw_names],
        dtype=np.int64,
    )
    return table, raw_to_table


def bind_joint_atlas_materials(
    geometric_class: np.ndarray,
    *,
    atlas_npz: pathlib.Path,
    semantics_path: pathlib.Path,
) -> JointAtlasMaterialEvidence:
    """Reduce only proven joint entity-material atlas entries for transport.

    Every joint entry is checked while its entity and material are still
    paired. The entity first has to agree with the geometric host. The material
    must then be a routable material that the declared Vistas prior permits for
    that entity. A strict majority of all joint mass must pass both gates. This
    makes ``Road + asphalt_concrete`` eligible on ground while ``Road + metal``
    remains visible in the raw posterior and leaves the geometric fallback.

    The return value is cell-level evidence. It deliberately does not collapse
    the atlas back to one material per source triangle. A subdivision stage can
    map each emitted child face to ``triangle_id``, ``texel_row`` and
    ``texel_column``, then freeze the selected class and complete posterior in
    its refined-surface sidecar.
    """
    geometric = np.asarray(geometric_class, dtype=np.int64)
    if geometric.ndim != 1:
        raise ValueError("geometric_class must be one-dimensional")
    if geometric.size and (geometric.min() < 0 or geometric.max() >= len(CLASS_NAMES)):
        raise ValueError("geometric_class leaves the structural class vocabulary")

    document = json.loads(pathlib.Path(semantics_path).read_text())
    material_prior = document.get("vistas_material_prior")
    if not isinstance(material_prior, dict):
        raise ValueError("semantics file carries no vistas_material_prior for joint pair licensing")

    with np.load(atlas_npz, allow_pickle=False) as data:
        missing = sorted(_JOINT_ATLAS_KEYS - set(data.files))
        if missing:
            raise ValueError(f"joint atlas schema is incomplete; missing {missing}")
        if "format" in data.files:
            atlas_format = str(np.asarray(data["format"]).item())
            if "joint" not in atlas_format or "v1" not in atlas_format:
                raise ValueError(f"unsupported joint atlas format {atlas_format!r}")
        else:
            raise ValueError("joint atlas carries no explicit format identifier")

        resolution_value = np.asarray(data["resolution"], dtype=np.int64).reshape(-1)
        if resolution_value.size == 1:
            resolution = (int(resolution_value[0]), int(resolution_value[0]))
        elif resolution_value.size == 2:
            resolution = (int(resolution_value[0]), int(resolution_value[1]))
        else:
            raise ValueError("joint atlas resolution must be a scalar or (height, width)")
        triangle_count = int(np.asarray(data["triangle_count"]).item())
        entity_names = tuple(str(name) for name in data["entity_names"])
        input_material_names = tuple(str(name) for name in data["material_names"])
        triangle_ids = data["triangle_ids"].astype(np.int64)
        texel_offsets = data["texel_offsets"].astype(np.int64)
        texel_row = data["texel_row"].astype(np.int64)
        texel_column = data["texel_column"].astype(np.int64)
        joint_offsets = data["joint_offsets"].astype(np.int64)
        joint_entity = data["joint_entity"].astype(np.int64)
        joint_material = data["joint_material"].astype(np.int64)
        joint_weight = data["joint_weight"].astype(np.float64)
        support_weight = data["support_weight"].astype(np.float64)

    if triangle_count != geometric.size:
        raise ValueError(f"joint atlas names {triangle_count} support triangles, geometric_class has {geometric.size}")
    if triangle_ids.ndim != 1 or np.any(np.diff(triangle_ids) <= 0):
        raise ValueError("joint atlas triangle_ids must be strictly increasing")
    if np.any((triangle_ids < 0) | (triangle_ids >= triangle_count)):
        raise ValueError("joint atlas triangle_ids leave the declared support mesh")
    if texel_offsets.shape != (triangle_ids.size + 1,) or texel_offsets[0] != 0:
        raise ValueError("joint atlas texel_offsets do not index triangle_ids")
    if np.any(np.diff(texel_offsets) < 0) or texel_offsets[-1] != texel_row.size:
        raise ValueError("joint atlas texel_offsets do not cover its cells")
    cells = texel_row.size
    if texel_column.shape != (cells,) or support_weight.shape != (cells,):
        raise ValueError("joint atlas cell arrays disagree on cell count")
    if np.any((texel_row < 0) | (texel_row >= resolution[0])) or np.any(
        (texel_column < 0) | (texel_column >= resolution[1])
    ):
        raise ValueError("joint atlas cell coordinates leave its resolution")
    if joint_offsets.shape != (cells + 1,) or joint_offsets[0] != 0:
        raise ValueError("joint atlas joint_offsets do not index its cells")
    if np.any(np.diff(joint_offsets) < 0) or joint_offsets[-1] != joint_weight.size:
        raise ValueError("joint atlas joint_offsets do not cover joint entries")
    joints = joint_weight.size
    if joint_entity.shape != (joints,) or joint_material.shape != (joints,):
        raise ValueError("joint atlas entry arrays disagree on joint count")
    if np.any((joint_entity < 0) | (joint_entity >= len(entity_names))):
        raise ValueError("joint atlas entity index leaves entity_names")
    if np.any((joint_material < 0) | (joint_material >= len(input_material_names))):
        raise ValueError("joint atlas material index leaves material_names")
    if not np.all(np.isfinite(joint_weight)) or np.any(joint_weight < 0.0):
        raise ValueError("joint atlas weights must be finite and nonnegative")
    if not np.all(np.isfinite(support_weight)) or np.any(support_weight < 0.0):
        raise ValueError("joint atlas support weights must be finite and nonnegative")

    cell_triangle = np.repeat(triangle_ids, np.diff(texel_offsets))
    cell_index = np.repeat(np.arange(cells, dtype=np.int64), np.diff(joint_offsets))
    joint_sum = np.zeros(cells, dtype=np.float64)
    np.add.at(joint_sum, cell_index, joint_weight)
    observed = support_weight > 0.0
    if np.any(observed & ~np.isclose(joint_sum, 1.0, atol=2e-6, rtol=2e-6)):
        raise ValueError("each observed joint atlas cell posterior must sum to one")
    if np.any(~observed & (joint_sum > 0.0)):
        raise ValueError("an unobserved joint atlas cell cannot carry posterior mass")

    raw = np.zeros((cells, len(input_material_names)), dtype=np.float64)
    if joints:
        np.add.at(raw, (cell_index, joint_material), joint_weight)

    entity_name = np.asarray([entity_names[index] for index in joint_entity], dtype=object)
    host = np.fromiter(
        (
            entity_supports_atlas_cell(str(name), int(geometric[cell_triangle[cell]]))
            for name, cell in zip(entity_name, cell_index, strict=True)
        ),
        dtype=bool,
        count=joints,
    )
    host_raw = np.zeros_like(raw)
    if np.any(host):
        np.add.at(host_raw, (cell_index[host], joint_material[host]), joint_weight[host])

    transport_names = tuple(sorted(IMAGE_MATERIALS))
    transport_index = {name: index for index, name in enumerate(transport_names)}
    routed_name = np.asarray([_routed_material(name) for name in input_material_names], dtype=object)
    routed_index = np.asarray(
        [transport_index.get(name, -1) if name is not None else -1 for name in routed_name],
        dtype=np.int64,
    )
    joint_route = routed_index[joint_material]
    pair_licensed = np.fromiter(
        (
            route >= 0 and _material_weight(material_prior, str(name), transport_names[route]) > 0.0
            for name, route in zip(entity_name, joint_route, strict=True)
        ),
        dtype=bool,
        count=joints,
    )
    routable_joint = host & pair_licensed
    transport_mass = np.zeros((cells, len(transport_names)), dtype=np.float64)
    if np.any(routable_joint):
        np.add.at(
            transport_mass,
            (cell_index[routable_joint], joint_route[routable_joint]),
            joint_weight[routable_joint],
        )

    host_mass = host_raw.sum(axis=1)
    routed_mass = transport_mass.sum(axis=1)
    host_posterior = np.divide(
        host_raw,
        host_mass[:, None],
        out=np.zeros_like(host_raw),
        where=host_mass[:, None] > 0.0,
    )
    transport_posterior = np.divide(
        transport_mass,
        routed_mass[:, None],
        out=np.zeros_like(transport_mass),
        where=routed_mass[:, None] > 0.0,
    )

    fallback = np.full(cells, JOINT_ATLAS_FALLBACK_NAMES.index("unobserved"), dtype=np.uint8)
    host_majority = host_mass > 0.5
    pair_majority = routed_mass > 0.5
    conflict = observed & ~host_majority
    compatible_unroutable = observed & host_majority & ~pair_majority
    bound = observed & host_majority & pair_majority
    fallback[conflict] = JOINT_ATLAS_FALLBACK_NAMES.index("conflict_or_tie")
    fallback[compatible_unroutable] = JOINT_ATLAS_FALLBACK_NAMES.index("compatible_but_unroutable")
    fallback[bound] = JOINT_ATLAS_FALLBACK_NAMES.index("bound")
    label = np.full(cells, -1, dtype=np.int64)
    if np.any(bound):
        label[bound] = np.argmax(transport_posterior[bound], axis=1)

    semantic_hash = hashlib.sha256(pathlib.Path(semantics_path).read_bytes()).hexdigest()
    return JointAtlasMaterialEvidence(
        triangle_id=cell_triangle,
        texel_row=texel_row,
        texel_column=texel_column,
        input_material_names=input_material_names,
        transport_material_names=transport_names,
        raw_material_posterior=raw,
        host_material_posterior=host_posterior,
        transport_posterior=transport_posterior,
        observed_weight=support_weight,
        host_compatible_weight=support_weight * host_mass,
        host_incompatible_weight=support_weight * (joint_sum - host_mass),
        routable_weight=support_weight * routed_mass,
        unroutable_weight=support_weight * (joint_sum - routed_mass),
        fallback_state=fallback,
        transport_label=label,
        provenance={
            "atlas_npz": str(atlas_npz),
            "semantics": str(semantics_path),
            "semantics_sha256": semantic_hash,
            "resolution": list(resolution),
            "triangle_count": triangle_count,
            "cells": cells,
            "joint_entries": joints,
            "support_compatibility_version": SUPPORT_COMPATIBILITY_VERSION,
            "host_rule": "paired entity must support the source triangle's geometric class",
            "pair_rule": (
                "paired material must route to IMAGE_MATERIALS and have positive mass in the declared "
                "vistas_material_prior for that same entity"
            ),
            "acceptance_rule": "routable paired joint mass must be a strict majority of all cell mass",
            "tie": "geometric fallback; material argmax ties use the lowest canonical material index",
            "fallback_names": list(JOINT_ATLAS_FALLBACK_NAMES),
            "material_substitution": dict(MATERIAL_SUBSTITUTION),
            "posterior_policy": (
                "raw, host-compatible, and routed posteriors are all retained; transport uses the routed "
                "posterior only after pair acceptance"
            ),
        },
    )


def bind_refined_atlas_faces(
    areas: np.ndarray,
    geometric_class: np.ndarray,
    evidence: JointAtlasMaterialEvidence,
    *,
    face_atlas_cell: np.ndarray,
    face_parent_triangle: np.ndarray,
) -> JointAtlasSurfaceBinding:
    """Freeze safe joint-atlas evidence onto emitted propagation faces.

    ``face_atlas_cell`` is the exact sparse cell selected from each child face's
    centroid. ``-1`` means that the atlas had no evidence at that point. The
    explicit map keeps binding independent of floating-point point-in-triangle
    reconstruction during later exposure runs.
    """
    areas = np.asarray(areas, dtype=np.float64)
    geometric = np.asarray(geometric_class, dtype=np.int64)
    cell = np.asarray(face_atlas_cell, dtype=np.int64)
    parent = np.asarray(face_parent_triangle, dtype=np.int64)
    count = areas.size
    if any(value.shape != (count,) for value in (geometric, cell, parent)):
        raise ValueError("refined face areas, classes, cells, and parents must have the same length")
    if count and (geometric.min() < 0 or geometric.max() >= len(CLASS_NAMES)):
        raise ValueError("refined geometric class leaves the structural vocabulary")
    if np.any((cell < -1) | (cell >= evidence.triangle_id.size)):
        raise ValueError("refined face atlas cell leaves the joint material evidence")
    mapped = cell >= 0
    if np.any(evidence.triangle_id[cell[mapped]] != parent[mapped]):
        raise ValueError("refined face parent does not match its selected atlas cell")

    class_names, spec = evidence.class_names_and_spec()
    face_class = geometric.copy()
    fallback = np.full(
        count,
        JOINT_ATLAS_FALLBACK_NAMES.index("unobserved"),
        dtype=np.uint8,
    )
    posterior = np.zeros((count, len(class_names)), dtype=np.float64)
    if np.any(mapped):
        fallback[mapped] = evidence.fallback_state[cell[mapped]]
        posterior[mapped] = evidence.tracer_posterior[cell[mapped]]
    bound = mapped & (fallback == JOINT_ATLAS_FALLBACK_NAMES.index("bound"))
    face_class[bound] = len(CLASS_NAMES) + evidence.transport_label[cell[bound]]
    source = _sources(count, bound, Provenance.IMAGE_WALK_MATERIAL)
    return JointAtlasSurfaceBinding(
        class_names=class_names,
        spec=spec,
        face_class=face_class,
        face_source=source,
        face_area_m2=areas,
        provenance={
            "class_rule": "joint semantic-material atlas bound after physical support subdivision",
            "joint_atlas": evidence.provenance,
            "face_mapping": "explicit child face to sparse atlas cell and source support triangle",
            "face_count": count,
            "bound_faces": int(bound.sum()),
            "fallback_faces": int((~bound).sum()),
            "fallback_face_counts": {
                name: int(np.count_nonzero(fallback == index)) for index, name in enumerate(JOINT_ATLAS_FALLBACK_NAMES)
            },
            "fallback": "child geometric class wherever paired evidence does not pass a strict majority",
            "posterior": "complete routed material mixture retained per child face",
        },
        posterior_names=class_names,
        face_material_posterior=posterior,
        face_atlas_cell=cell,
        face_parent_triangle=parent,
        face_fallback_state=fallback,
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
