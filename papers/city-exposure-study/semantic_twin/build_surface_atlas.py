"""Build the all-camera semantic and material atlas for one exact site mesh."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from dataclasses import dataclass
from typing import Any

import numpy as np

from semantic_twin import paths
from semantic_twin.scene.site_semantics import TRANSIENT_CLASSES, site_mesh, stations
from semantic_twin.vision.prompted import semantic_catalogue_identity
from semantic_twin.vision.provenance import AdmissionGate
from semantic_twin.vision.surface_atlas import (
    CameraSurfaceObservations,
    REQUIRED_SEMANTIC_RASTERS,
    ReducedCameraSurfaceEvidence,
    fuse_surface_observations,
    reduce_camera_observations,
    save_surface_atlas,
    semantic_artifact_reasons,
    semantic_evidence_directory,
    sha256_file,
)
from semantic_twin.vision.vocabulary import ConceptCatalog

DEFAULT_OUT = paths.outputs_dir() / "site_semantics"
REQUIRED_RASTERS = REQUIRED_SEMANTIC_RASTERS
VEGETATION_RASTERS = (
    "vegetation_form",
    "vegetation_subtype",
    "vegetation_confidence",
)


@dataclass(frozen=True)
class SurfaceAtlasBuildOptions:
    """All numerical choices that affect a site atlas."""

    crop_m: int = 250
    grid_height: int = 1536
    block_rows: int = 128
    atlas_resolution: int = 8
    max_residual_deg: float = 4.0
    max_sky_conflict: float = 0.5
    min_conflict_range_m: float = 2.0
    concepts: pathlib.Path = paths.config_dir() / "semantic_concepts.json"
    out_root: pathlib.Path = DEFAULT_OUT
    semantics_dirname: str = "semantics"

    @property
    def admission_gate(self) -> AdmissionGate:
        return AdmissionGate(
            max_residual_deg=self.max_residual_deg,
            max_sky_conflict=self.max_sky_conflict,
            min_conflict_range_m=self.min_conflict_range_m,
        )


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", required=True)
    parser.add_argument("--crop-m", type=int, default=250)
    parser.add_argument("--grid-height", type=int, default=1536)
    parser.add_argument("--block-rows", type=int, default=128)
    parser.add_argument("--atlas-resolution", type=int, default=8)
    parser.add_argument("--max-residual-deg", type=float, default=4.0)
    parser.add_argument("--max-sky-conflict", type=float, default=0.5)
    parser.add_argument("--min-conflict-range-m", type=float, default=2.0)
    parser.add_argument("--concepts", type=pathlib.Path, default=paths.config_dir() / "semantic_concepts.json")
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--semantics-dirname",
        default="semantics",
        help="relative evidence directory selected beneath every admitted panorama folder",
    )
    return parser.parse_args(argv)


def _semantics_directory(folder: pathlib.Path, dirname: str) -> pathlib.Path:
    try:
        return semantic_evidence_directory(folder, dirname)
    except ValueError as error:
        raise ValueError("--semantics-dirname must be a relative path beneath each panorama folder") from error


def build(site: str, options: SurfaceAtlasBuildOptions) -> dict[str, Any]:
    """Cast admitted hybrid panoramas and write one canonical sparse atlas."""
    import trimesh

    mesh_path = site_mesh(site, options.crop_m)
    mesh = trimesh.load(mesh_path, process=False, force="mesh")
    mesh_sha256 = sha256_file(mesh_path)
    gate = options.admission_gate
    admitted, refused = stations(
        site,
        max_residual_deg=options.max_residual_deg,
        max_sky_conflict=options.max_sky_conflict,
        min_conflict_range_m=options.min_conflict_range_m,
        semantics_dirname=None if options.semantics_dirname == "semantics" else options.semantics_dirname,
    )
    if not admitted:
        if options.semantics_dirname != "semantics" and refused:
            details = "; ".join(f"{record['station']}: {', '.join(record['refused_because'])}" for record in refused)
            raise ValueError(
                f"{site} has no admitted panorama in selected semantic evidence directory "
                f"{options.semantics_dirname}: {details}"
            )
        raise ValueError(f"{site} has no admitted panorama")

    catalog = ConceptCatalog.load(options.concepts)
    catalogue_record = _concept_catalogue_record(options.concepts)
    vocabulary: dict[str, Any] | None = None
    reduced: list[ReducedCameraSurfaceEvidence] = []
    camera_records: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for record in sorted(admitted, key=lambda value: value["station"]):
        folder = pathlib.Path(record["folder"])
        semantic_dir = _semantics_directory(folder, options.semantics_dirname)
        meta_path = semantic_dir / "semantics.json"
        semantics_path = semantic_dir / "panorama_semantics.npz"
        artifact_reasons = _semantic_artifact_reasons(meta_path, semantics_path)
        if artifact_reasons:
            skipped.append({"camera_id": record["station"], "reasons": artifact_reasons})
            continue
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        _validate_catalogue_identity(
            metadata,
            selected=catalogue_record,
            camera_id=record["station"],
        )
        current = _vocabulary(metadata, catalog)
        if vocabulary is None:
            vocabulary = current
        elif not _same_vocabulary(vocabulary, current):
            raise ValueError(f"{record['station']} carries a different semantic or material vocabulary")

        pose_path = folder / "alignment" / "pose_aligned.json"
        pose = json.loads(pose_path.read_text(encoding="utf-8"))
        panorama_path = _panorama_path(folder)
        camera_provenance = _camera_provenance(
            pose_path=pose_path,
            semantics_path=semantics_path,
            metadata_path=meta_path,
            panorama_path=panorama_path,
            metadata=metadata,
        )
        observation, counts = _cast_camera(
            mesh,
            pose,
            semantics_path,
            record["station"],
            vocabulary["transient_ids"],
            options.grid_height,
            options.block_rows,
        )
        reduced.append(
            reduce_camera_observations(
                observation,
                triangle_count=len(mesh.faces),
                atlas_resolution=options.atlas_resolution,
                entity_names=vocabulary["entity_names"],
                material_names=vocabulary["material_names"],
                concept_names=vocabulary["concept_names"],
                material_prior=vocabulary["material_prior"],
                concept_material=vocabulary["concept_material"],
                vegetation_form_names=vocabulary["vegetation_form_names"],
                vegetation_subtype_names=vocabulary["vegetation_subtype_names"],
            )
        )
        del observation
        camera_records.append(
            {
                "camera_id": record["station"],
                "folder": str(folder),
                "semantic_evidence_directory": {
                    "name": options.semantics_dirname,
                    "path": str(semantic_dir),
                },
                "position_enu_m": pose["position_enu_m"],
                "heading_deg": float(pose["heading_deg"]),
                "pitch_correction_deg": float(pose.get("pitch_correction_deg", 0.0)),
                "roll_correction_deg": float(pose.get("roll_correction_deg", 0.0)),
                "panorama": str(panorama_path) if panorama_path is not None else None,
                "semantics": str(semantics_path),
                "pose": str(pose_path),
                **camera_provenance,
                **counts,
            }
        )

    if vocabulary is None or not reduced:
        raise ValueError(f"{site} has no admitted panorama with the complete hybrid material axis")
    atlas = fuse_surface_observations(
        reduced,
        triangle_count=len(mesh.faces),
        atlas_resolution=options.atlas_resolution,
        entity_names=vocabulary["entity_names"],
        material_names=vocabulary["material_names"],
        concept_names=vocabulary["concept_names"],
        material_prior=vocabulary["material_prior"],
        concept_material=vocabulary["concept_material"],
        mesh_sha256=mesh_sha256,
        vegetation_form_names=vocabulary["vegetation_form_names"],
        vegetation_subtype_names=vocabulary["vegetation_subtype_names"],
    )

    out_dir = options.out_root / site
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"joint_atlas_{options.crop_m}m_r{options.atlas_resolution}"
    npz_path = out_dir / f"{stem}.npz"
    manifest_path = out_dir / f"{stem}.json"
    manifest_metadata = {
        "site": site,
        "crop_radius_m": options.crop_m,
        "mesh": {"path": str(mesh_path)},
        "grid": {
            "height": options.grid_height,
            "width": 2 * options.grid_height,
            "block_rows": options.block_rows,
        },
        "admission": gate.as_dict(),
        "semantic_evidence_selection": {
            "directory_name": options.semantics_dirname,
            "rule": "read this relative directory directly beneath every admitted panorama folder",
            "camera_directories": [record["semantic_evidence_directory"]["path"] for record in camera_records],
        },
        "cameras": camera_records,
        "vegetation_evidence": _vegetation_evidence_summary(camera_records),
        "stations_refused": refused,
        "admitted_without_complete_hybrid_product": skipped,
        "concept_catalogue": catalogue_record,
        "vocabularies": {"material_concept": list(vocabulary["concept_names"])},
    }
    save_surface_atlas(atlas, npz_path, metadata=manifest_metadata, manifest_path=manifest_path)
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _cast_camera(
    mesh: Any,
    pose: dict[str, Any],
    semantics_path: pathlib.Path,
    camera_id: str,
    transient_ids: frozenset[int],
    grid_height: int,
    block_rows: int,
) -> tuple[CameraSurfaceObservations, dict[str, int]]:
    from semantic_twin.pano_geometry import panorama_to_world_matrix

    height, width = grid_height, 2 * grid_height
    rasters = _sample_rasters(semantics_path, height, width)
    rotation = panorama_to_world_matrix(
        float(pose["heading_deg"]),
        pitch_deg=float(pose.get("pitch_correction_deg", 0.0)),
        roll_deg=float(pose.get("roll_correction_deg", 0.0)),
    )
    camera = np.asarray(pose["position_enu_m"], dtype=np.float64)
    columns = np.arange(width, dtype=np.float64)
    yaw = ((columns + 0.5) / width - 0.5) * 2.0 * np.pi
    sin_yaw, cos_yaw = np.sin(yaw), np.cos(yaw)
    fields: dict[str, list[np.ndarray]] = {
        name: []
        for name in (
            "triangle_id",
            "barycentric",
            *REQUIRED_RASTERS,
            "vegetation_form",
            "vegetation_subtype",
            "vegetation_confidence",
        )
    }
    hit_count = 0
    transient_count = 0
    for start in range(0, height, block_rows):
        stop = min(start + block_rows, height)
        rows = np.arange(start, stop, dtype=np.float64)
        pitch = (0.5 - (rows + 0.5) / height) * np.pi
        cos_pitch = np.cos(pitch)[:, None]
        local = np.stack(
            (
                cos_pitch * sin_yaw[None, :],
                cos_pitch * cos_yaw[None, :],
                np.broadcast_to(np.sin(pitch)[:, None], (stop - start, width)),
            ),
            axis=2,
        )
        directions = local.reshape(-1, 3) @ rotation.T
        origins = np.broadcast_to(camera, directions.shape)
        location, index_ray, index_tri = mesh.ray.intersects_location(origins, directions, multiple_hits=False)
        if not len(index_ray):
            continue
        hit_count += len(index_ray)
        entity = rasters["entity"][start:stop].reshape(-1)[index_ray]
        transient = np.isin(entity, tuple(transient_ids))
        transient_count += int(transient.sum())
        keep = ~transient
        if not np.any(keep):
            continue
        kept_triangles = index_tri[keep]
        barycentric = _barycentric(mesh.triangles[kept_triangles], location[keep])
        fields["triangle_id"].append(kept_triangles.astype(np.int32))
        fields["barycentric"].append(barycentric.astype(np.float32))
        for name in REQUIRED_RASTERS:
            fields[name].append(rasters[name][start:stop].reshape(-1)[index_ray][keep])
        for name in VEGETATION_RASTERS:
            fields[name].append(rasters[name][start:stop].reshape(-1)[index_ray][keep])

    arrays = {name: np.concatenate(parts) if parts else _empty_field(name) for name, parts in fields.items()}
    observation = CameraSurfaceObservations(
        camera_id=camera_id,
        triangle_id=arrays["triangle_id"],
        barycentric=arrays["barycentric"],
        entity=arrays["entity"],
        entity_confidence=arrays["confidence"],
        rf_material=arrays["rf_material"],
        material_prior_mass=arrays["rf_material_prior_mass"],
        material_concept=arrays["material_concept"],
        material_confidence=arrays["material_confidence"],
        material_source=arrays["material_source"],
        vegetation_form=arrays["vegetation_form"],
        vegetation_subtype=arrays["vegetation_subtype"],
        vegetation_confidence=arrays["vegetation_confidence"],
    )
    return observation, {
        "mesh_hit_observations": int(hit_count),
        "retained_observations": len(observation),
        "transient_observations": int(transient_count),
    }


def _sample_rasters(path: pathlib.Path, height: int, width: int) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as document:
        source_shape = document["entity"].shape
        rows = np.arange(height) * source_shape[0] // height
        columns = np.arange(width) * source_shape[1] // width
        result = {name: np.ascontiguousarray(document[name][np.ix_(rows, columns)]) for name in REQUIRED_RASTERS}
        for name in VEGETATION_RASTERS:
            if name in document.files:
                result[name] = np.ascontiguousarray(document[name][np.ix_(rows, columns)])
            else:
                dtype = np.float32 if name.endswith("confidence") else np.uint8
                result[name] = np.zeros((height, width), dtype=dtype)
    return result


def _vocabulary(metadata: dict[str, Any], catalog: ConceptCatalog) -> dict[str, Any]:
    entity_names = _ordered_names(metadata["entity_id2label"])
    material_names = _ordered_names(metadata["rf_material_id2label"])
    concept_names = _ordered_names(metadata["concept_id2label"])
    if material_names != tuple(catalog.taxonomy["materials"]):
        raise ValueError("panorama RF materials differ from the concept catalogue")
    if concept_names != tuple(catalog.id2label().values()):
        raise ValueError("panorama concept IDs differ from the concept catalogue")
    prior = np.zeros((len(entity_names), len(material_names)), dtype=np.float32)
    unknown = material_names.index("unknown")
    for entity_id, entity_name in enumerate(entity_names):
        distribution = metadata["vistas_material_prior"].get(entity_name)
        if not distribution:
            prior[entity_id, unknown] = 1.0
            continue
        for material, mass in distribution.items():
            prior[entity_id, material_names.index(material)] = float(mass)
    transient_ids = frozenset(index for index, name in enumerate(entity_names) if name in TRANSIENT_CLASSES)
    return {
        "entity_names": entity_names,
        "material_names": material_names,
        "concept_names": concept_names,
        "vegetation_form_names": tuple(catalog.vegetation_forms),
        "vegetation_subtype_names": tuple(catalog.vegetation_subtypes),
        "material_prior": prior,
        "concept_material": catalog.material_matrix(),
        "transient_ids": transient_ids,
    }


def _concept_catalogue_record(path: pathlib.Path) -> dict[str, Any]:
    identity = semantic_catalogue_identity(path, production=False)
    return {
        "path": str(path),
        "sha256": identity["catalogue_sha256"],
        "catalogue_semantic_sha256": identity["catalogue_semantic_sha256"],
        "matches_reviewed_production_catalogue": identity["matches_reviewed_production_catalogue"],
        "required_production_catalogue_semantic_sha256": identity["required_production_catalogue_semantic_sha256"],
    }


def _validate_catalogue_identity(
    metadata: dict[str, Any],
    *,
    selected: dict[str, Any],
    camera_id: str,
) -> None:
    """Require a semantic product built from the selected parsed catalogue."""
    vocabulary = metadata.get("concept_vocabulary")
    if not isinstance(vocabulary, dict):
        raise ValueError(f"{camera_id} does not record its semantic concept catalogue identity")
    actual = vocabulary.get("catalogue_semantic_sha256")
    if not isinstance(actual, str) or not re.fullmatch(r"[0-9a-f]{64}", actual):
        raise ValueError(f"{camera_id} does not record a valid semantic concept catalogue digest")
    expected = selected["catalogue_semantic_sha256"]
    if actual != expected:
        raise ValueError(
            f"{camera_id} was produced with semantic concept catalogue {actual}, but atlas fusion selected {expected}"
        )


def _same_vocabulary(left: dict[str, Any], right: dict[str, Any]) -> bool:
    scalar = (
        "entity_names",
        "material_names",
        "concept_names",
        "vegetation_form_names",
        "vegetation_subtype_names",
        "transient_ids",
    )
    return (
        all(left[name] == right[name] for name in scalar)
        and np.array_equal(
            left["material_prior"],
            right["material_prior"],
        )
        and np.array_equal(left["concept_material"], right["concept_material"])
    )


def _ordered_names(mapping: dict[str, str]) -> tuple[str, ...]:
    expected = [str(index) for index in range(len(mapping))]
    if list(sorted(mapping, key=int)) != expected:
        raise ValueError("semantic vocabulary IDs must be contiguous from zero")
    return tuple(str(mapping[str(index)]) for index in range(len(mapping)))


def _semantic_artifact_reasons(
    metadata_path: pathlib.Path,
    semantics_path: pathlib.Path,
) -> list[str]:
    """Compatibility name for the canonical hybrid artifact validator."""
    return semantic_artifact_reasons(metadata_path, semantics_path)


def _barycentric(triangles: np.ndarray, points: np.ndarray) -> np.ndarray:
    edge_a = triangles[:, 1] - triangles[:, 0]
    edge_b = triangles[:, 2] - triangles[:, 0]
    offset = points - triangles[:, 0]
    aa = np.einsum("ij,ij->i", edge_a, edge_a)
    ab = np.einsum("ij,ij->i", edge_a, edge_b)
    bb = np.einsum("ij,ij->i", edge_b, edge_b)
    pa = np.einsum("ij,ij->i", offset, edge_a)
    pb = np.einsum("ij,ij->i", offset, edge_b)
    denominator = aa * bb - ab * ab
    w1 = (bb * pa - ab * pb) / denominator
    w2 = (aa * pb - ab * pa) / denominator
    result = np.column_stack((1.0 - w1 - w2, w1, w2))
    result[np.abs(result) < 1e-8] = 0.0
    result = np.clip(result, 0.0, 1.0)
    return result / result.sum(axis=1, keepdims=True)


def _empty_field(name: str) -> np.ndarray:
    if name == "barycentric":
        return np.zeros((0, 3), dtype=np.float32)
    dtype = np.float32 if "confidence" in name or name == "rf_material_prior_mass" else np.int32
    return np.zeros(0, dtype=dtype)


def _panorama_path(folder: pathlib.Path) -> pathlib.Path | None:
    candidates = sorted(
        path
        for pattern in ("panorama*.jpg", "panorama*.jpeg", "panorama*.png", "panorama*.webp")
        for path in folder.glob(pattern)
        if path.is_file()
    )
    return candidates[0] if candidates else None


def _file_provenance(path: pathlib.Path | None) -> dict[str, Any]:
    if path is None or not path.is_file():
        return {"present": False, "path": str(path) if path is not None else None, "sha256": None}
    return {"present": True, "path": str(path), "sha256": sha256_file(path)}


def _camera_provenance(
    *,
    pose_path: pathlib.Path,
    semantics_path: pathlib.Path,
    metadata_path: pathlib.Path,
    panorama_path: pathlib.Path | None,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    with np.load(semantics_path, allow_pickle=False) as document:
        vegetation_rasters = {name: name in document.files for name in VEGETATION_RASTERS}
    present = [name for name, available in vegetation_rasters.items() if available]
    missing = [name for name, available in vegetation_rasters.items() if not available]
    if not present:
        vegetation_status = "absent"
        vegetation_note = (
            "No vegetation form, subtype, or confidence raster is present. Atlas vegetation categories are "
            "unresolved placeholders, not classifications."
        )
    elif missing:
        vegetation_status = "partial"
        vegetation_note = (
            "Vegetation evidence is incomplete. Missing rasters are not inferred from entity or material labels."
        )
    else:
        vegetation_status = "present"
        vegetation_note = "Vegetation form, subtype, and confidence rasters are present."

    concept_backend = metadata.get("concept_backend")
    concept_model = dict(concept_backend) if isinstance(concept_backend, dict) else None
    if concept_model is not None:
        concept_model["immutable_revision"] = _immutable_concept_revision(metadata, concept_model)
    semantic_product = {
        "backend": metadata.get("backend"),
        "entity_model": {
            "model": metadata.get("model"),
            "checkpoint": metadata.get("checkpoint"),
        },
        "concept_model": concept_model,
        "concept_cache_key": metadata.get("concept_cache_key"),
        "vegetation": {
            "status": vegetation_status,
            "rasters": vegetation_rasters,
            "missing_rasters": missing,
            "backend": metadata.get("vegetation_backend"),
            "model": metadata.get("vegetation_model"),
            "checkpoint": metadata.get("vegetation_checkpoint"),
            "note": vegetation_note,
        },
    }
    return {
        "input_files": {
            "pose_json": _file_provenance(pose_path),
            "semantic_npz": _file_provenance(semantics_path),
            "semantic_json": _file_provenance(metadata_path),
            "panorama": _file_provenance(panorama_path),
        },
        "semantic_product": semantic_product,
    }


def _immutable_concept_revision(metadata: dict[str, Any], concept_backend: dict[str, Any]) -> dict[str, Any]:
    """Extract an immutable SAM checkpoint identity without upgrading a tag to a pin."""
    candidates = (
        ("concept_backend.checkpoint_sha256", concept_backend.get("checkpoint_sha256")),
        ("concept_backend.weights_sha256", concept_backend.get("weights_sha256")),
        ("concept_backend.checkpoint_digest", concept_backend.get("checkpoint_digest")),
        ("concept_backend.checkpoint", concept_backend.get("checkpoint")),
        ("concept_backend.commit_hash", concept_backend.get("commit_hash")),
        ("concept_backend._commit_hash", concept_backend.get("_commit_hash")),
        ("concept_backend.model_revision", concept_backend.get("model_revision")),
        ("concept_backend.revision", concept_backend.get("revision")),
        ("concept_checkpoint_sha256", metadata.get("concept_checkpoint_sha256")),
        ("concept_weights_sha256", metadata.get("concept_weights_sha256")),
        ("concept_checkpoint_digest", metadata.get("concept_checkpoint_digest")),
        ("concept_checkpoint", metadata.get("concept_checkpoint")),
        ("concept_commit_hash", metadata.get("concept_commit_hash")),
        ("concept_model_revision", metadata.get("concept_model_revision")),
        ("concept_revision", metadata.get("concept_revision")),
    )
    reported: list[dict[str, str]] = []
    for field, raw_value in candidates:
        if raw_value is None:
            continue
        value = str(raw_value).strip().lower()
        reported.append({"field": field, "value": str(raw_value)})
        if re.fullmatch(r"[0-9a-f]{64}", value):
            return {"status": "resolved", "kind": "sha256", "value": value, "source_field": field}
        if re.fullmatch(r"[0-9a-f]{40}", value):
            return {"status": "resolved", "kind": "git_commit", "value": value, "source_field": field}
    return {
        "status": "unresolved",
        "kind": None,
        "value": None,
        "source_field": None,
        "reported_mutable_or_unverifiable_values": reported,
        "note": (
            "The semantic artifact does not record an immutable SAM3 weight digest or commit. "
            "The model name and cache key identify settings, not exact weights."
        ),
    }


def _vegetation_evidence_summary(camera_records: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = [record["semantic_product"]["vegetation"]["status"] for record in camera_records]
    complete = statuses.count("present")
    partial = statuses.count("partial")
    absent = statuses.count("absent")
    if complete == len(statuses):
        status = "present"
    elif absent == len(statuses):
        status = "absent"
    else:
        status = "mixed"
    return {
        "status": status,
        "camera_count": len(statuses),
        "complete_camera_count": complete,
        "partial_camera_count": partial,
        "absent_camera_count": absent,
        "note": (
            "Only explicit vegetation form, subtype, and confidence rasters count as vegetation classification "
            "evidence. Catalogue labels alone do not."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
    options = SurfaceAtlasBuildOptions(
        crop_m=args.crop_m,
        grid_height=args.grid_height,
        block_rows=args.block_rows,
        atlas_resolution=args.atlas_resolution,
        max_residual_deg=args.max_residual_deg,
        max_sky_conflict=args.max_sky_conflict,
        min_conflict_range_m=args.min_conflict_range_m,
        concepts=args.concepts,
        out_root=args.out,
        semantics_dirname=args.semantics_dirname,
    )
    manifest = build(args.site, options)
    print(
        f"wrote {manifest['atlas']['observed_triangle_count']} observed triangles from "
        f"{len(manifest['camera_ids'])} cameras to {manifest['artifact']['path']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
