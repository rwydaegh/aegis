"""Run the fishnet chain over every usable registered panorama of a site."""

from __future__ import annotations

import argparse

from semantic_twin.scene.site_fishnets import SITES, FishnetBuildOptions, build_sites


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", action="append", choices=SITES)
    parser.add_argument("--all-sites", action="store_true")
    parser.add_argument("--mesh", default="inhouse_leaf_130m.ply")
    parser.add_argument(
        "--out-suffix",
        default="",
        help=(
            "appended to outputs/<site>_fishnet_vistas. A build against a different mesh "
            "belongs beside the old one and not on top of it, since the two are only "
            "comparable if both survive"
        ),
    )
    parser.add_argument("--size", type=int, default=1536)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--max-sky-hit-fraction", type=float, default=0.5)
    parser.add_argument("--min-conflict-range-m", type=float, default=2.0)
    parser.add_argument("--keep-intermediates", action="store_true")
    parser.add_argument(
        "--flatten-only",
        action="store_true",
        help="move already built surface sets up to the site directory and rewrite the site manifest",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
    selected = list(SITES) if args.all_sites else list(args.site or [])
    if not selected:
        raise SystemExit("name a site with --site or run --all-sites")
    build_sites(
        selected,
        FishnetBuildOptions(
            mesh_name=args.mesh,
            out_suffix=args.out_suffix,
            size=args.size,
            workers=args.workers,
            max_sky_hit_fraction=args.max_sky_hit_fraction,
            min_conflict_range_m=args.min_conflict_range_m,
            keep_intermediates=args.keep_intermediates,
            flatten_only=args.flatten_only,
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
