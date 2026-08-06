"""Build the all-camera semantic and material atlas for one exact site mesh."""

from __future__ import annotations

import argparse
import pathlib

from semantic_twin import paths
from semantic_twin.scene.surface_atlas_builder import DEFAULT_OUT, SurfaceAtlasBuildOptions, build


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
    raise SystemExit(main())
