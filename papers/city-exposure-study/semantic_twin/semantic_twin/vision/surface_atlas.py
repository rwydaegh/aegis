"""Build one joint all-camera atlas on the exact support mesh.

Every observed mesh triangle owns the same barycentric grid. Cameras add soft
entity and material evidence to that shared grid. The grid belongs to the mesh,
not to a camera, so two views may disagree about a seam without either view
deciding how the support triangle is cut.

The material evidence stays a distribution. Vistas-backed pixels recover the
full ``p(material | entity)`` table from the panorama metadata. Concept-backed
pixels recover the full concept distribution from ``semantic_concepts.json``.
The ``rf_material`` raster remains a checked quicklook and never becomes a
one-hot posterior.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np

from semantic_twin.materials.atlas import (
    FALLBACK_BOUND,
    SOURCE_SAM_CONCEPT,
    SOURCE_VISTAS_PRIOR,
    JointSemanticMaterialAtlas,
)

SURFACE_ATLAS_SCHEMA = "aegis.joint_semantic_material_atlas"
SURFACE_ATLAS_MANIFEST_VERSION = 1
SEMANTIC_DENSE_RASTERS = ("entity", "confidence")
SEMANTIC_SAM_RASTERS = (
    "rf_material",
    "rf_material_prior_mass",
    "material_concept",
    "material_confidence",
    "material_source",
)
REQUIRED_SEMANTIC_RASTERS = SEMANTIC_DENSE_RASTERS + SEMANTIC_SAM_RASTERS
WEIGHTING_RULE = (
    "A camera contributes at most one confidence-weighted vote to one barycentric texel. "
    "Within each camera and texel, entity and joint entity-material weights are divided by "
    "the number of retained rays. The fused Mask2Former query score is capped at one for "
    "evidence weighting because the stored score is a nonnegative query sum and can exceed one; "
    "its uncapped mean is retained for QA. Vistas material evidence uses the full declared "
    "p(material|entity) prior and Vistas confidence. Concept material evidence uses the full "
    "declared concept posterior and the smaller of Vistas and concept confidence. Camera "
    "means are then added. Range and raw image-pixel density add no further weight."
)


@dataclass(frozen=True)
class CameraSurfaceObservations:
    """Static panorama pixels already intersected with the support mesh."""

    camera_id: str
    triangle_id: np.ndarray
    barycentric: np.ndarray
    entity: np.ndarray
    entity_confidence: np.ndarray
    rf_material: np.ndarray
    material_prior_mass: np.ndarray
    material_concept: np.ndarray
    material_confidence: np.ndarray
    material_source: np.ndarray
    vegetation_form: np.ndarray | None = None
    vegetation_subtype: np.ndarray | None = None
    vegetation_confidence: np.ndarray | None = None

    def __len__(self) -> int:
        return int(np.asarray(self.triangle_id).size)


@dataclass(frozen=True)
class ReducedCameraSurfaceEvidence:
    """One camera after bounded per-texel reduction."""

    camera_id: str
    arrays: dict[str, tuple[np.ndarray, np.ndarray]]


@dataclass(frozen=True)
class AtlasAuditMesh:
    """Compact child-face view of fused evidence for Blender and QA."""

    atlas_vertices: np.ndarray
    atlas_faces: np.ndarray
    atlas_source_triangle: np.ndarray
    atlas_sparse_cell: np.ndarray
    atlas_texel_row: np.ndarray
    atlas_texel_column: np.ndarray
    atlas_entity: np.ndarray
    atlas_material: np.ndarray
    atlas_confidence: np.ndarray
    atlas_camera_count: np.ndarray
    atlas_observation_count: np.ndarray
    atlas_entity_probabilities: np.ndarray
    atlas_material_probabilities: np.ndarray

    @property
    def atlas_entity_class(self) -> np.ndarray:
        return self.atlas_entity

    @property
    def atlas_material_class(self) -> np.ndarray:
        return self.atlas_material

    def as_arrays(self) -> dict[str, np.ndarray]:
        """Return names accepted by the Blender production payload."""
        return {
            "atlas_vertices": self.atlas_vertices,
            "atlas_faces": self.atlas_faces,
            "atlas_source_triangle": self.atlas_source_triangle,
            "atlas_sparse_cell": self.atlas_sparse_cell,
            "atlas_texel_row": self.atlas_texel_row,
            "atlas_texel_column": self.atlas_texel_column,
            "atlas_entity": self.atlas_entity,
            "atlas_material": self.atlas_material,
            "atlas_entity_class": self.atlas_entity,
            "atlas_material_class": self.atlas_material,
            "atlas_confidence": self.atlas_confidence,
            "atlas_camera_count": self.atlas_camera_count,
            "atlas_observation_count": self.atlas_observation_count,
            "atlas_entity_probabilities": self.atlas_entity_probabilities,
            "atlas_material_probabilities": self.atlas_material_probabilities,
        }


def reduce_camera_observations(
    camera: CameraSurfaceObservations,
    *,
    triangle_count: int,
    atlas_resolution: int,
    entity_names: Iterable[str],
    material_names: Iterable[str],
    concept_names: Iterable[str],
    material_prior: np.ndarray,
    concept_material: np.ndarray,
    vegetation_form_names: Iterable[str] = ("unresolved",),
    vegetation_subtype_names: Iterable[str] = ("unresolved",),
) -> ReducedCameraSurfaceEvidence:
    """Reduce one camera so full raw image hits can be released immediately."""
    entity_names = _names(entity_names, "entity")
    material_names = _names(material_names, "material")
    concept_names = _names(concept_names, "concept")
    form_names = _names(vegetation_form_names, "vegetation form")
    subtype_names = _names(vegetation_subtype_names, "vegetation subtype")
    prior = _probability_table(material_prior, (len(entity_names), len(material_names)), "material prior")
    concepts = _probability_table(
        concept_material,
        (len(concept_names), len(material_names)),
        "concept material",
    )
    arrays = _reduce_camera(
        camera,
        triangle_count=int(triangle_count),
        resolution=int(atlas_resolution),
        entity_count=len(entity_names),
        material_count=len(material_names),
        concept_count=len(concept_names),
        prior=prior,
        concepts=concepts,
        form_count=len(form_names),
        subtype_count=len(subtype_names),
    )
    return ReducedCameraSurfaceEvidence(camera.camera_id, arrays)


def fuse_surface_observations(
    cameras: Iterable[CameraSurfaceObservations | ReducedCameraSurfaceEvidence],
    *,
    triangle_count: int,
    atlas_resolution: int,
    entity_names: Iterable[str],
    material_names: Iterable[str],
    concept_names: Iterable[str],
    material_prior: np.ndarray,
    concept_material: np.ndarray,
    mesh_sha256: str,
    vegetation_form_names: Iterable[str] = ("unresolved",),
    vegetation_subtype_names: Iterable[str] = ("unresolved",),
) -> JointSemanticMaterialAtlas:
    """Fuse cameras into deterministic sparse CSR storage.

    The two material tables are part of the observation model. ``material_prior``
    has one row per entity class. ``concept_material`` has one row per concept,
    including the zero ``unlabelled`` row.
    """
    if not isinstance(triangle_count, (int, np.integer)) or triangle_count < 0:
        raise ValueError("triangle_count must be a nonnegative integer")
    if not isinstance(atlas_resolution, (int, np.integer)) or atlas_resolution < 2:
        raise ValueError("atlas_resolution must be an integer of at least two")
    entity_names = _names(entity_names, "entity")
    material_names = _names(material_names, "material")
    concept_names = _names(concept_names, "concept")
    form_names = _names(vegetation_form_names, "vegetation form")
    subtype_names = _names(vegetation_subtype_names, "vegetation subtype")
    prior = _probability_table(material_prior, (len(entity_names), len(material_names)), "material prior")
    concepts = _probability_table(
        concept_material,
        (len(concept_names), len(material_names)),
        "concept material",
    )
    _mesh_digest(mesh_sha256)

    ordered = sorted(cameras, key=lambda camera: camera.camera_id)
    camera_ids = tuple(camera.camera_id for camera in ordered)
    if not camera_ids or len(set(camera_ids)) != len(camera_ids) or any(not value for value in camera_ids):
        raise ValueError("camera IDs must be unique and nonempty")
    if len(camera_ids) > 64:
        raise ValueError("the atlas station mask supports at most 64 cameras")

    parts: dict[str, list[tuple[np.ndarray, np.ndarray]]] = {
        name: []
        for name in (
            "cell",
            "observations",
            "entity",
            "joint",
            "support",
            "prior",
            "concept",
            "mean_entity_score",
            "mean_concept_confidence",
            "vegetation_form",
            "vegetation_subtype",
        )
    }
    station_parts: list[tuple[np.ndarray, np.ndarray]] = []
    source_parts: list[tuple[np.ndarray, np.ndarray]] = []
    for camera_index, camera in enumerate(ordered):
        reduced = (
            camera.arrays
            if isinstance(camera, ReducedCameraSurfaceEvidence)
            else _reduce_camera(
                camera,
                triangle_count=int(triangle_count),
                resolution=int(atlas_resolution),
                entity_count=len(entity_names),
                material_count=len(material_names),
                concept_count=len(concept_names),
                prior=prior,
                concepts=concepts,
                form_count=len(form_names),
                subtype_count=len(subtype_names),
            )
        )
        for name in parts:
            parts[name].append(reduced[name])
        cells = reduced["cell"][0]
        station_parts.append((cells, np.full(cells.size, np.uint64(1) << np.uint64(camera_index))))
        source_parts.append(reduced["source_mask"])

    merged = {name: _merge_sparse(value) for name, value in parts.items()}
    all_cells = merged["cell"][0]
    support_on_all_cells = _aligned_values(merged["support"], all_cells)
    cells = all_cells[support_on_all_cells > 0.0]
    resolution = int(atlas_resolution)
    local_cell_count = resolution * resolution
    triangle_ids = np.unique(cells // local_cell_count).astype(np.int64)
    cell_triangle, local = np.divmod(cells, local_cell_count)
    triangle_row = np.searchsorted(triangle_ids, cell_triangle)
    texel_offsets = np.searchsorted(cell_triangle, triangle_ids, side="left")
    texel_offsets = np.r_[texel_offsets, cells.size].astype(np.int64)
    texel_row, texel_column = np.divmod(local, resolution)

    entity_offsets, entity_index, entity_weight = _posterior_csr(
        merged["entity"],
        cells,
        len(entity_names),
    )
    joint_offsets, joint_pair, joint_weight = _posterior_csr(
        merged["joint"],
        cells,
        len(entity_names) * len(material_names),
    )
    joint_entity, joint_material = np.divmod(joint_pair, len(material_names))
    entity_dense = _csr_rows(entity_offsets, entity_index, entity_weight, len(entity_names))
    material_dense = _joint_material_rows(
        joint_offsets,
        joint_material,
        joint_weight,
        len(material_names),
    )
    support = _aligned_values(merged["support"], cells)
    observations = np.rint(_aligned_values(merged["observations"], cells)).astype(np.uint32)
    camera_count = np.rint(_aligned_values(merged["cell"], cells)).astype(np.uint16)
    station_mask = _merge_or(station_parts, cells)
    source_mask = _merge_or(source_parts, cells).astype(np.uint8)
    prior_weight = _aligned_values(merged["prior"], cells).astype(np.float32)
    concept_weight = _aligned_values(merged["concept"], cells).astype(np.float32)
    mean_entity_score = _aligned_values(merged["mean_entity_score"], cells)
    mean_concept_confidence = _aligned_values(merged["mean_concept_confidence"], cells)
    mean_entity_score /= np.maximum(camera_count, 1)
    mean_concept_confidence /= np.maximum(camera_count, 1)
    form_posterior = _dense_category(merged["vegetation_form"], cells, len(form_names))
    subtype_posterior = _dense_category(merged["vegetation_subtype"], cells, len(subtype_names))

    atlas = JointSemanticMaterialAtlas(
        atlas_resolution=resolution,
        triangle_count=int(triangle_count),
        mesh_sha256=mesh_sha256.lower(),
        entity_names=np.asarray(entity_names),
        material_names=np.asarray(material_names),
        station_ids=np.asarray(camera_ids),
        station_weight=np.ones(len(camera_ids), dtype=np.float32),
        triangle_ids=triangle_ids,
        texel_offsets=texel_offsets,
        texel_row=texel_row.astype(np.uint16),
        texel_column=texel_column.astype(np.uint16),
        entity_offsets=entity_offsets,
        entity_index=entity_index.astype(np.uint16),
        entity_weight=entity_weight.astype(np.float32),
        joint_offsets=joint_offsets,
        joint_entity=joint_entity.astype(np.uint16),
        joint_material=joint_material.astype(np.uint16),
        joint_weight=joint_weight.astype(np.float32),
        support_weight=support.astype(np.float32),
        observation_count=observations,
        camera_count=camera_count,
        station_mask=station_mask,
        source_mask=source_mask,
        concept_weight=concept_weight,
        prior_weight=prior_weight,
        compatible_weight=support.astype(np.float32),
        incompatible_weight=np.zeros(cells.size, dtype=np.float32),
        fallback_state=np.full(cells.size, FALLBACK_BOUND, dtype=np.uint8),
        entity_label=entity_dense.argmax(axis=1).astype(np.int16),
        material_label=material_dense.argmax(axis=1).astype(np.int16),
        entity_confidence=entity_dense.max(axis=1).astype(np.float32),
        material_confidence=material_dense.max(axis=1).astype(np.float32),
        mean_entity_score=mean_entity_score.astype(np.float32),
        mean_concept_confidence=mean_concept_confidence.astype(np.float32),
        vegetation_form_names=np.asarray(form_names),
        vegetation_subtype_names=np.asarray(subtype_names),
        vegetation_form_posterior=form_posterior,
        vegetation_subtype_posterior=subtype_posterior,
    )
    # Keep this assignment visible. The existing field names predate the
    # evidence-only builder and do not imply agreement with a geometric host.
    del triangle_row
    return atlas


def save_surface_atlas(
    atlas: JointSemanticMaterialAtlas,
    npz_path: pathlib.Path,
    *,
    metadata: dict[str, Any],
    manifest_path: pathlib.Path | None = None,
) -> pathlib.Path:
    """Save the canonical sparse NPZ and its complete JSON provenance."""
    npz_path = pathlib.Path(npz_path)
    manifest_path = npz_path.with_suffix(".json") if manifest_path is None else pathlib.Path(manifest_path)
    atlas.save(npz_path)
    document = dict(metadata)
    document.update(
        {
            "schema": SURFACE_ATLAS_SCHEMA,
            "format_version": SURFACE_ATLAS_MANIFEST_VERSION,
            "artifact": {
                "path": npz_path.name,
                "sha256": sha256_file(npz_path),
                "content_sha256": atlas.content_digest(),
            },
            "mesh": {
                **dict(document.get("mesh", {})),
                "sha256": atlas.mesh_sha256,
                "face_count": atlas.triangle_count,
            },
            "atlas": {
                "resolution": atlas.atlas_resolution,
                "observed_triangle_count": atlas.observed_triangle_count,
                "sparse_texel_count": atlas.cell_count,
                "weighting_rule": WEIGHTING_RULE,
                "host_compatibility": (
                    "not decided here; compatible_weight mirrors evidence support and transport applies "
                    "its own structural-material gate"
                ),
            },
            "vocabularies": {
                "entity": [str(value) for value in atlas.entity_names],
                "material": [str(value) for value in atlas.material_names],
                "material_concept": list(document["vocabularies"]["material_concept"]),
                "material_source": ["vistas_prior", "concept_backend"],
                "vegetation_form": [str(value) for value in atlas.vegetation_form_names],
                "vegetation_subtype": [str(value) for value in atlas.vegetation_subtype_names],
            },
            "camera_ids": [str(value) for value in atlas.station_ids],
        }
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path


def load_surface_atlas(
    npz_path: pathlib.Path,
    manifest_path: pathlib.Path | None = None,
    *,
    expected_mesh_sha256: str | None = None,
) -> JointSemanticMaterialAtlas:
    """Load one atlas and verify its artifact, mesh, names, and camera IDs."""
    npz_path = pathlib.Path(npz_path)
    manifest_path = npz_path.with_suffix(".json") if manifest_path is None else pathlib.Path(manifest_path)
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    if document.get("schema") != SURFACE_ATLAS_SCHEMA or document.get("format_version") != 1:
        raise ValueError("unsupported surface atlas manifest")
    artifact = document.get("artifact", {})
    if artifact.get("path") != npz_path.name or artifact.get("sha256") != sha256_file(npz_path):
        raise ValueError("surface atlas artifact differs from its manifest")
    atlas = JointSemanticMaterialAtlas.load(npz_path, expected_mesh_sha256=expected_mesh_sha256)
    if artifact.get("content_sha256") != atlas.content_digest():
        raise ValueError("surface atlas content digest differs from its manifest")
    if document.get("mesh", {}).get("sha256") != atlas.mesh_sha256:
        raise ValueError("surface atlas mesh digest differs from its manifest")
    expected_vocabularies = document.get("vocabularies", {})
    if expected_vocabularies.get("entity") != [str(value) for value in atlas.entity_names] or expected_vocabularies.get(
        "material"
    ) != [str(value) for value in atlas.material_names]:
        raise ValueError("surface atlas vocabulary differs from its manifest")
    if document.get("camera_ids") != [str(value) for value in atlas.station_ids]:
        raise ValueError("surface atlas camera IDs differ from its manifest")
    return atlas


def to_surface_mesh(
    atlas: JointSemanticMaterialAtlas,
    vertices: np.ndarray,
    faces: np.ndarray,
) -> AtlasAuditMesh:
    """Triangulate fused atlas cells for Blender without legacy fishnets."""
    vertices = np.asarray(vertices, dtype=np.float64)
    faces = np.asarray(faces, dtype=np.int64)
    if vertices.ndim != 2 or vertices.shape[1:] != (3,) or not np.all(np.isfinite(vertices)):
        raise ValueError("vertices must be finite with shape (vertices, 3)")
    if faces.shape != (atlas.triangle_count, 3) or np.any(faces < 0) or np.any(faces >= len(vertices)):
        raise ValueError("faces must match the atlas support mesh")

    resolution = atlas.atlas_resolution
    cell_polygons = _texel_polygons(resolution)
    entity = atlas.entity_probability
    material = atlas.material_probability
    cameras = atlas.cell_support_dense("camera_count")
    observations = atlas.cell_support_dense("observation_count")
    output_vertices: list[np.ndarray] = []
    output_faces: list[tuple[int, int, int]] = []
    source: list[int] = []
    sparse_cell: list[int] = []
    output_texel_row: list[int] = []
    output_texel_column: list[int] = []
    entity_label: list[int] = []
    material_label: list[int] = []
    confidence: list[float] = []
    camera_count: list[int] = []
    observation_count: list[int] = []
    entity_probability: list[np.ndarray] = []
    material_probability: list[np.ndarray] = []

    for atlas_row, face_id in enumerate(np.asarray(atlas.triangle_ids, dtype=np.int64)):
        triangle = vertices[faces[face_id]]
        cache: dict[tuple[float, float], int] = {}

        def vertex_index(uv: tuple[float, float]) -> int:
            key = tuple(round(value, 14) for value in uv)
            if key not in cache:
                barycentric = np.asarray((1.0 - uv[0] - uv[1], uv[0], uv[1]), dtype=np.float64)
                cache[key] = len(output_vertices)
                output_vertices.append(barycentric @ triangle)
            return cache[key]

        start = int(atlas.texel_offsets[atlas_row])
        stop = int(atlas.texel_offsets[atlas_row + 1])
        for cell_index in range(start, stop):
            row = int(atlas.texel_row[cell_index])
            column = int(atlas.texel_column[cell_index])
            polygon = cell_polygons[(row, column)]
            entity_row = entity[atlas_row, row, column]
            material_row = material[atlas_row, row, column]
            for index in range(1, len(polygon) - 1):
                child = (polygon[0], polygon[index], polygon[index + 1])
                output_faces.append(tuple(vertex_index(value) for value in child))
                source.append(int(face_id))
                sparse_cell.append(cell_index)
                output_texel_row.append(row)
                output_texel_column.append(column)
                entity_probability.append(entity_row)
                material_probability.append(material_row)
                entity_label.append(int(entity_row.argmax()))
                material_label.append(int(material_row.argmax()))
                confidence.append(float(material_row.max()))
                camera_count.append(int(cameras[atlas_row, row, column]))
                observation_count.append(int(observations[atlas_row, row, column]))

    return AtlasAuditMesh(
        atlas_vertices=np.asarray(output_vertices, dtype=np.float32).reshape(-1, 3),
        atlas_faces=np.asarray(output_faces, dtype=np.int32).reshape(-1, 3),
        atlas_source_triangle=np.asarray(source, dtype=np.int32),
        atlas_sparse_cell=np.asarray(sparse_cell, dtype=np.int64),
        atlas_texel_row=np.asarray(output_texel_row, dtype=np.uint16),
        atlas_texel_column=np.asarray(output_texel_column, dtype=np.uint16),
        atlas_entity=np.asarray(entity_label, dtype=np.int16),
        atlas_material=np.asarray(material_label, dtype=np.int16),
        atlas_confidence=np.asarray(confidence, dtype=np.float32),
        atlas_camera_count=np.asarray(camera_count, dtype=np.uint16),
        atlas_observation_count=np.asarray(observation_count, dtype=np.uint32),
        atlas_entity_probabilities=np.asarray(entity_probability, dtype=np.float32).reshape(
            -1, len(atlas.entity_names)
        ),
        atlas_material_probabilities=np.asarray(material_probability, dtype=np.float32).reshape(
            -1,
            len(atlas.material_names),
        ),
    )


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with pathlib.Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _reduce_camera(
    camera: CameraSurfaceObservations,
    *,
    triangle_count: int,
    resolution: int,
    entity_count: int,
    material_count: int,
    concept_count: int,
    prior: np.ndarray,
    concepts: np.ndarray,
    form_count: int,
    subtype_count: int,
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    values = _validate_camera(
        camera,
        triangle_count,
        entity_count,
        material_count,
        concept_count,
        form_count,
        subtype_count,
    )
    texel_row, texel_column = _texel_indices(values["barycentric"], resolution)
    cell = values["triangle_id"] * resolution**2 + texel_row * resolution + texel_column
    order = np.lexsort(
        (
            values["material_concept"],
            values["material_source"],
            values["entity"],
            cell,
        )
    )
    cell = cell[order]
    values = {name: value[order] for name, value in values.items() if name != "barycentric"}
    raw_entity_score = values["entity_confidence"].astype(np.float64)
    entity_confidence = np.minimum(raw_entity_score, 1.0)
    material_confidence = np.where(
        values["material_source"] == 1,
        values["material_confidence"],
        entity_confidence,
    )
    joint_confidence = np.minimum(entity_confidence, material_confidence)
    retained = joint_confidence > 0.0
    cell = cell[retained]
    values = {name: value[retained] for name, value in values.items()}
    raw_entity_score = raw_entity_score[retained]
    entity_confidence = entity_confidence[retained]
    material_confidence = material_confidence[retained]
    joint_confidence = joint_confidence[retained]
    unique_cell, count = np.unique(cell, return_counts=True)
    divisor = count[np.searchsorted(unique_cell, cell)].astype(np.float64)
    selected = np.where(
        values["material_source"][:, None] == 1,
        concepts[values["material_concept"]],
        prior[values["entity"]],
    )
    _validate_quicklook(values, selected, camera.camera_id)

    joint_keys: list[np.ndarray] = []
    joint_values: list[np.ndarray] = []
    pair_base = values["entity"] * material_count
    for material in range(material_count):
        weight = selected[:, material] * joint_confidence / divisor
        positive = weight > 0.0
        if np.any(positive):
            joint_keys.append(cell[positive] * (entity_count * material_count) + pair_base[positive] + material)
            joint_values.append(weight[positive])
    if joint_keys:
        joint = _sparse_sum(np.concatenate(joint_keys), np.concatenate(joint_values))
    else:
        joint = (np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.float64))

    source_value = np.where(
        values["material_source"] == 1,
        SOURCE_SAM_CONCEPT,
        SOURCE_VISTAS_PRIOR,
    )
    source_key, first = np.unique(cell, return_index=True)
    source_mask = np.zeros(source_key.size, dtype=np.uint8)
    for source in (SOURCE_VISTAS_PRIOR, SOURCE_SAM_CONCEPT):
        source_cells = np.unique(cell[source_value == source])
        source_mask[np.searchsorted(source_key, source_cells)] |= source
    del first

    form = _category_mean(
        cell,
        values["vegetation_form"],
        values["vegetation_confidence"],
        divisor,
        form_count,
    )
    subtype = _category_mean(
        cell,
        values["vegetation_subtype"],
        values["vegetation_confidence"],
        divisor,
        subtype_count,
    )
    return {
        "cell": (unique_cell, np.ones(unique_cell.size, dtype=np.float64)),
        "observations": (unique_cell, count.astype(np.float64)),
        "entity": _category_mean(cell, values["entity"], entity_confidence, divisor, entity_count),
        "joint": joint,
        "support": _sparse_sum(cell, joint_confidence / divisor),
        "prior": _sparse_sum(cell, joint_confidence / divisor * (values["material_source"] == 0)),
        "concept": _sparse_sum(cell, joint_confidence / divisor * (values["material_source"] == 1)),
        "mean_entity_score": _sparse_sum(cell, raw_entity_score / divisor),
        "mean_concept_confidence": _sparse_sum(
            cell,
            values["material_confidence"] / divisor * (values["material_source"] == 1),
        ),
        "source_mask": (source_key, source_mask),
        "vegetation_form": form,
        "vegetation_subtype": subtype,
    }


def _validate_camera(
    camera: CameraSurfaceObservations,
    triangle_count: int,
    entity_count: int,
    material_count: int,
    concept_count: int,
    form_count: int,
    subtype_count: int,
) -> dict[str, np.ndarray]:
    count = len(camera)
    values = {
        "triangle_id": np.asarray(camera.triangle_id, dtype=np.int64),
        "barycentric": np.asarray(camera.barycentric, dtype=np.float64),
        "entity": np.asarray(camera.entity, dtype=np.int64),
        "entity_confidence": np.asarray(camera.entity_confidence, dtype=np.float64),
        "rf_material": np.asarray(camera.rf_material, dtype=np.int64),
        "material_prior_mass": np.asarray(camera.material_prior_mass, dtype=np.float64),
        "material_concept": np.asarray(camera.material_concept, dtype=np.int64),
        "material_confidence": np.asarray(camera.material_confidence, dtype=np.float64),
        "material_source": np.asarray(camera.material_source, dtype=np.int64),
        "vegetation_form": _optional(camera.vegetation_form, count, np.int64),
        "vegetation_subtype": _optional(camera.vegetation_subtype, count, np.int64),
        "vegetation_confidence": _optional(camera.vegetation_confidence, count, np.float64),
    }
    for name, value in values.items():
        shape = (count, 3) if name == "barycentric" else (count,)
        if value.shape != shape or not np.all(np.isfinite(value)):
            raise ValueError(f"{camera.camera_id} {name} must be finite with shape {shape}")
    bounds = {
        "triangle_id": triangle_count,
        "entity": entity_count,
        "rf_material": material_count,
        "material_concept": concept_count,
        "material_source": 2,
        "vegetation_form": form_count,
        "vegetation_subtype": subtype_count,
    }
    for name, upper in bounds.items():
        if np.any((values[name] < 0) | (values[name] >= upper)):
            raise ValueError(f"{camera.camera_id} {name} leaves its declared range")
    if np.any(values["entity_confidence"] < 0.0):
        raise ValueError(f"{camera.camera_id} entity_confidence must be nonnegative")
    for name in (
        "material_prior_mass",
        "material_confidence",
        "vegetation_confidence",
    ):
        if np.any((values[name] < 0.0) | (values[name] > 1.0)):
            raise ValueError(f"{camera.camera_id} {name} must lie in [0, 1]")
    barycentric = values["barycentric"]
    if np.any(barycentric < -1e-6) or not np.allclose(barycentric.sum(axis=1), 1.0, atol=1e-6):
        raise ValueError(f"{camera.camera_id} barycentric coordinates must be nonnegative and sum to one")
    return values


def _validate_quicklook(values: dict[str, np.ndarray], selected: np.ndarray, camera_id: str) -> None:
    winner = selected.argmax(axis=1)
    mass = selected.max(axis=1)
    if not np.array_equal(winner, values["rf_material"]):
        raise ValueError(f"{camera_id} rf_material does not match the reconstructed full distribution")
    if not np.allclose(mass, values["material_prior_mass"], atol=1e-3):
        raise ValueError(f"{camera_id} rf_material_prior_mass does not match the reconstructed distribution")


def _optional(value: np.ndarray | None, count: int, dtype: np.dtype) -> np.ndarray:
    return np.zeros(count, dtype=dtype) if value is None else np.asarray(value, dtype=dtype)


def _category_mean(
    cell: np.ndarray,
    category: np.ndarray,
    confidence: np.ndarray,
    divisor: np.ndarray,
    classes: int,
) -> tuple[np.ndarray, np.ndarray]:
    positive = confidence > 0.0
    return _sparse_sum(
        cell[positive] * classes + category[positive],
        np.asarray(confidence[positive], dtype=np.float64) / divisor[positive],
    )


def _posterior_csr(
    encoded: tuple[np.ndarray, np.ndarray],
    cells: np.ndarray,
    classes: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    key, weight = encoded
    owner, category = np.divmod(key, classes)
    positions = np.searchsorted(cells, owner)
    if np.any(positions >= cells.size) or np.any(cells[positions] != owner):
        raise ValueError("posterior contains a cell outside the atlas")
    support = np.bincount(positions, weights=weight, minlength=cells.size)
    normalised = weight / support[positions]
    offsets = np.searchsorted(positions, np.arange(cells.size), side="left")
    return np.r_[offsets, len(key)].astype(np.int64), category.astype(np.int64), normalised


def _csr_rows(offsets: np.ndarray, index: np.ndarray, weight: np.ndarray, classes: int) -> np.ndarray:
    rows = np.zeros((len(offsets) - 1, classes), dtype=np.float32)
    owner = np.repeat(np.arange(len(rows)), np.diff(offsets))
    np.add.at(rows, (owner, index), weight)
    return rows


def _joint_material_rows(
    offsets: np.ndarray,
    material: np.ndarray,
    weight: np.ndarray,
    classes: int,
) -> np.ndarray:
    return _csr_rows(offsets, material, weight, classes)


def _dense_category(
    encoded: tuple[np.ndarray, np.ndarray],
    cells: np.ndarray,
    classes: int,
) -> np.ndarray:
    result = np.zeros((cells.size, classes), dtype=np.float32)
    key, weight = encoded
    if not key.size:
        result[:, 0] = 1.0
        return result
    owner, category = np.divmod(key, classes)
    position = np.searchsorted(cells, owner)
    present = (position < cells.size) & (cells[np.minimum(position, cells.size - 1)] == owner)
    np.add.at(result, (position[present], category[present]), weight[present])
    total = result.sum(axis=1)
    supported = total > 0.0
    result[supported] /= total[supported, None]
    result[~supported, 0] = 1.0
    return result


def _aligned_values(values: tuple[np.ndarray, np.ndarray], cells: np.ndarray) -> np.ndarray:
    key, weight = values
    result = np.zeros(cells.size, dtype=np.float64)
    position = np.searchsorted(cells, key)
    if cells.size:
        present = (position < cells.size) & (cells[np.minimum(position, cells.size - 1)] == key)
        result[position[present]] = weight[present]
    return result


def _sparse_sum(key: np.ndarray, value: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    key = np.asarray(key, dtype=np.int64)
    value = np.asarray(value, dtype=np.float64)
    if not key.size:
        return key, value
    order = np.argsort(key, kind="stable")
    key, value = key[order], value[order]
    starts = np.flatnonzero(np.r_[True, key[1:] != key[:-1]])
    return key[starts], np.add.reduceat(value, starts)


def _merge_sparse(parts: list[tuple[np.ndarray, np.ndarray]]) -> tuple[np.ndarray, np.ndarray]:
    if not parts:
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.float64)
    return _sparse_sum(
        np.concatenate([part[0] for part in parts]),
        np.concatenate([part[1] for part in parts]),
    )


def _merge_or(parts: list[tuple[np.ndarray, np.ndarray]], cells: np.ndarray) -> np.ndarray:
    result = np.zeros(cells.size, dtype=np.uint64)
    for key, value in parts:
        position = np.searchsorted(cells, key)
        present = (position < cells.size) & (cells[np.minimum(position, cells.size - 1)] == key)
        np.bitwise_or.at(result, position[present], np.asarray(value, dtype=np.uint64)[present])
    return result


def _texel_indices(barycentric: np.ndarray, resolution: int) -> tuple[np.ndarray, np.ndarray]:
    v = np.clip(barycentric[:, 2], 0.0, 1.0)
    u = np.clip(barycentric[:, 1], 0.0, 1.0)
    rows = np.floor(v * (resolution - 1) + 0.5)
    columns = np.floor(u * (resolution - 1) + 0.5)
    row_excess = rows - v * (resolution - 1)
    column_excess = columns - u * (resolution - 1)
    outside = (rows + columns) / (resolution - 1) > 1.0 + 1e-12
    while np.any(outside):
        step_row = outside & (row_excess >= column_excess)
        step_column = outside & ~step_row
        rows[step_row] -= 1.0
        columns[step_column] -= 1.0
        row_excess[step_row] -= 1.0
        column_excess[step_column] -= 1.0
        outside = (rows + columns) / (resolution - 1) > 1.0 + 1e-12
    return rows.astype(np.int64), columns.astype(np.int64)


def _texel_polygons(resolution: int) -> dict[tuple[int, int], tuple[tuple[float, float], ...]]:
    """Return the exact nearest-lattice partition of one canonical triangle.

    Transport assigns a barycentric point to its nearest valid ``(column,
    row)`` lattice point. Clipping the support triangle by every pairwise
    perpendicular bisector gives the matching audit polygon. The table is made
    once per export, then reused for every observed support-mesh face.
    """
    divisions = resolution - 1
    sites = tuple(
        (row, column, np.asarray((column / divisions, row / divisions), dtype=np.float64))
        for row in range(resolution)
        for column in range(resolution - row)
    )
    result: dict[tuple[int, int], tuple[tuple[float, float], ...]] = {}
    for row, column, site in sites:
        polygon = [np.asarray((0.0, 0.0)), np.asarray((1.0, 0.0)), np.asarray((0.0, 1.0))]
        for other_row, other_column, other in sites:
            if other_row == row and other_column == column:
                continue
            normal = other - site
            limit = 0.5 * (float(other @ other) - float(site @ site))
            polygon = _clip_polygon(polygon, normal, limit)
            if not polygon:
                raise AssertionError("a valid atlas texel has an empty Voronoi region")
        polygon = _clean_polygon(polygon)
        result[(row, column)] = tuple((float(point[0]), float(point[1])) for point in polygon)
    return result


def _clip_polygon(points: list[np.ndarray], normal: np.ndarray, limit: float) -> list[np.ndarray]:
    """Clip one convex polygon to ``normal @ point <= limit``."""
    output: list[np.ndarray] = []
    previous = points[-1]
    previous_value = float(normal @ previous - limit)
    for current in points:
        current_value = float(normal @ current - limit)
        previous_inside = previous_value <= 1e-14
        current_inside = current_value <= 1e-14
        if previous_inside != current_inside:
            fraction = previous_value / (previous_value - current_value)
            output.append(previous + fraction * (current - previous))
        if current_inside:
            output.append(current)
        previous = current
        previous_value = current_value
    return output


def _clean_polygon(points: list[np.ndarray]) -> list[np.ndarray]:
    """Remove numerical duplicates and redundant collinear clip vertices."""
    cleaned: list[np.ndarray] = []
    for point in points:
        if not cleaned or np.linalg.norm(point - cleaned[-1]) > 1e-12:
            cleaned.append(point)
    if len(cleaned) > 1 and np.linalg.norm(cleaned[0] - cleaned[-1]) <= 1e-12:
        cleaned.pop()
    changed = True
    while changed and len(cleaned) > 3:
        changed = False
        for index in range(len(cleaned)):
            previous = cleaned[index - 1]
            current = cleaned[index]
            following = cleaned[(index + 1) % len(cleaned)]
            incoming = current - previous
            outgoing = following - current
            determinant = incoming[0] * outgoing[1] - incoming[1] * outgoing[0]
            if abs(float(determinant)) <= 1e-12:
                cleaned.pop(index)
                changed = True
                break
    return cleaned


def _probability_table(value: np.ndarray, shape: tuple[int, int], name: str) -> np.ndarray:
    table = np.asarray(value, dtype=np.float64)
    if table.shape != shape or not np.all(np.isfinite(table)) or np.any(table < 0.0):
        raise ValueError(f"{name} must be finite and nonnegative with shape {shape}")
    if not np.allclose(table.sum(axis=1), 1.0):
        raise ValueError(f"every row of {name} must sum to one")
    return table


def _names(value: Iterable[str], name: str) -> tuple[str, ...]:
    names = tuple(str(item) for item in value)
    if not names or any(not item for item in names) or len(set(names)) != len(names):
        raise ValueError(f"{name} names must be unique and nonempty")
    return names


def _mesh_digest(value: str) -> str:
    digest = str(value).lower()
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise ValueError("mesh_sha256 must be a 64-character hexadecimal digest")
    return digest
