"""Fuse a site's registered panoramas into a per-triangle semantic posterior."""

from __future__ import annotations

import argparse
import pathlib
import sys

from semantic_twin.scene.site_semantics import (
    COMPANION_DIRECTORIES as COMPANION_DIRECTORIES,
    DEFAULT_OUT,
    SITES as SITES,
    SemanticBuildOptions,
    STATION_PREFIXES as STATION_PREFIXES,
    build as _build,
    station_verdict as station_verdict,
)


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
    parser.add_argument(
        "--cohort-dir",
        type=pathlib.Path,
        help="explicit dated panorama cohort beneath the study root; never mixed with canonical cameras",
    )
    parser.add_argument(
        "--semantics-dirname",
        default="semantics",
        help="relative evidence directory selected beneath every admitted panorama folder",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
    selected = _selected_sites(args)
    options = _build_options(args)
    for site in selected:
        _run_site(site, args, options)
    return 0


def _selected_sites(args: argparse.Namespace) -> tuple[str, ...]:
    selected = SITES if args.all_sites else tuple(args.site or ())
    if not selected:
        raise SystemExit("name --site or pass --all-sites")
    return selected


def _build_options(args: argparse.Namespace) -> SemanticBuildOptions:
    return SemanticBuildOptions(
        crop_m=args.crop_m,
        grid_height=args.grid_height,
        block_rows=args.block_rows,
        workers=args.workers,
        max_residual_deg=args.max_residual_deg,
        max_sky_conflict=args.max_sky_conflict,
        min_conflict_range_m=args.min_conflict_range_m,
        out_root=args.out,
        cohort_dir=args.cohort_dir,
        semantics_dirname=args.semantics_dirname,
    )


def _run_site(site: str, args: argparse.Namespace, options: SemanticBuildOptions) -> None:
    try:
        report = _build(site, options)
    except FileNotFoundError as exc:
        print(f"[skip] {site}: {exc}", flush=True)
        return
    if report is None or report.get("result") != "written":
        _print_empty_site(site, report)
        return
    _print_site_bound(site, args.crop_m, report)


def _print_empty_site(site: str, report: dict | None) -> None:
    admitted = len(report["stations_admitted"]) if report else 0
    total = admitted + len(report["stations_refused"]) if report else 0
    result = report.get("result") if report else "nothing"
    print(f"[none] {site}: {result}, {admitted} admitted of {total}", flush=True)


def _print_site_bound(site: str, crop_m: int, report: dict) -> None:
    coverage = report["coverage"]
    station_count = len(report["stations_cast"])
    total = len(report["stations_admitted"]) + len(report["stations_refused"])
    print(
        f"[bound] {site} at {crop_m} m: {station_count} stations of {total}, "
        f"{coverage['covered_fraction_by_face']:.4f} of faces, "
        f"{coverage['covered_fraction_by_area']:.4f} of area -> {report['walk_npz']}",
        flush=True,
    )


if __name__ == "__main__":
    sys.exit(main())
