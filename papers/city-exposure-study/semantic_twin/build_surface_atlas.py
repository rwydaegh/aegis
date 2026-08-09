"""Build the all-camera semantic and material atlas for one exact site mesh."""

from __future__ import annotations

import sys
from typing import Any

from semantic_twin import paths  # noqa: F401
from semantic_twin.cli.surface_atlas import arguments
from semantic_twin.scene import surface_atlas_builder as _builder
from semantic_twin.scene.site_semantics import site_mesh, stations
from semantic_twin.vision.surface_atlas import sha256_file

from semantic_twin.scene.surface_atlas_builder import (  # noqa: F401
    CameraSurfaceObservations,
    ConceptCatalog,
    DEFAULT_OUT,
    REQUIRED_RASTERS,
    ReducedCameraSurfaceEvidence,
    VEGETATION_RASTERS,
    SurfaceAtlasBuildOptions,
    _barycentric,
    _camera_provenance,
    _concept_catalogue_record,
    _empty_field,
    _file_provenance,
    _immutable_concept_revision,
    _ordered_names,
    _panorama_path,
    _sample_rasters,
    _same_vocabulary,
    _semantic_artifact_reasons,
    _semantics_directory,
    _validate_catalogue_identity,
    _vegetation_evidence_summary,
    _vocabulary,
)


def __getattr__(name: str) -> Any:
    return getattr(_builder, name)


def build(site: str, options: SurfaceAtlasBuildOptions) -> dict[str, Any]:
    """Build an atlas, honoring dependencies patched on this compatibility module."""
    return _builder.build(
        site,
        options,
        site_mesh_fn=site_mesh,
        stations_fn=stations,
        sha256_file_fn=sha256_file,
    )


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
        cohort_dir=args.cohort_dir,
    )
    manifest = build(args.site, options)
    print(
        f"wrote {manifest['atlas']['observed_triangle_count']} observed triangles from "
        f"{len(manifest['camera_ids'])} cameras to {manifest['artifact']['path']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
