"""Command line entry point for the city exposure study."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

from semantic_twin.exposure import study as _study
from semantic_twin.exposure.execution import ExecutionConfig, LegacyReplay
from semantic_twin.exposure.sweeps import CitySweepConfig, LadderSweepConfig
from semantic_twin.runconfig import RunConfig
from semantic_twin.transport.tracer import DEFAULT_MAX_BOUNCES

# Compatibility exports for published reproduction scripts and the immutable
# golden capture harness. New callers import semantic_twin.exposure.study.
CONFIG = _study.CONFIG
COVERAGE_LADDER = _study.COVERAGE_LADDER
CROP_BOUND_NOTE = _study.CROP_BOUND_NOTE
GROUND_DATUM_M = _study.GROUND_DATUM_M
LADDER_MODELS = _study.LADDER_MODELS
MODELS = _study.MODELS
OUTPUT = _study.OUTPUT
PHANTOM = _study.PHANTOM
PHANTOM_MASS_KG = _study.PHANTOM_MASS_KG
REFERENCE_S0_W_M2 = _study.REFERENCE_S0_W_M2
ROOT = _study.ROOT
SEMANTICS = _study.SEMANTICS
SITES = _study.SITES
SITE_SEMANTICS = _study.SITE_SEMANTICS
WALK_SEMANTIC = _study.WALK_SEMANTIC

coverage_ladder = _study.coverage_ladder
coverage_ladder_report = _study.coverage_ladder_report
coverage_report = _study.coverage_report
cross_city_report = _study.cross_city_report
fishnet_rests_on_an_admitted_pose = _study.fishnet_rests_on_an_admitted_pose
ground_datum = _study.ground_datum
ladder_key = _study.ladder_key
ladder_markdown = _study.ladder_markdown
ladder_sites = _study.ladder_sites
ladder_tag = _study.ladder_tag
measure_ground_datum = _study.measure_ground_datum
report = _study.report
site_fishnet = _study.site_fishnet
site_mesh = _study.site_mesh
site_walk_semantics = _study.site_walk_semantics
_against_baseline = _study._against_baseline
_one_value = _study._one_value
_spread = _study._spread


def _escape_config(
    locations: int,
    rays: int,
    frequency_hz: float,
    **options: Any,
) -> tuple[RunConfig, ExecutionConfig]:
    """Translate established arguments while keeping their old ``None`` rules.

    The legacy runner omitted ``roulette_start`` from ``TraceConfig`` when the
    caller passed ``None``. Its tracer default is the literal 4, even when a
    caller raises ``max_bounces``. A direct :class:`RunConfig` uses its own
    documented rule instead: ``None`` means one past that run's bounce budget.
    """
    coupler = options.pop("coupler", None)
    workers = options.pop("workers", None)
    replay = LegacyReplay(
        ground_datum_m=options.pop("ground_datum_m", None),
        walk_probe_z_m=options.pop("walk_probe_z_m", None),
    )
    roulette_start = options.pop("roulette_start", DEFAULT_MAX_BOUNCES + 1)
    if roulette_start is None:
        roulette_start = DEFAULT_MAX_BOUNCES + 1
    config = RunConfig(
        site=options.pop("site", "korenmarkt"),
        crop_m=options.pop("crop_m", 130),
        law="band",
        models=tuple(MODELS),
        estimator="escape",
        next_event=None,
        walk="grid",
        walk_radius_m=options.pop("walk_radius_m"),
        walk_spacing_m=options.pop("walk_spacing_m"),
        locations=locations,
        frequency_hz=frequency_hz,
        max_bounces=options.pop("max_bounces"),
        roulette_start=roulette_start,
        materials=options.pop("materials"),
        walk_npz=str(path) if (path := options.pop("walk_npz", None)) is not None else None,
        rays=rays,
        local_cells=options.pop("local_cells"),
        seed=options.pop("seed"),
        variant=options.pop("variant"),
        tag=options.pop("tag"),
    )
    if options:
        raise TypeError(f"unknown run options: {', '.join(sorted(options))}")
    return config, ExecutionConfig(workers=workers, coupler=coupler, replay=replay)


def run(locations: int, rays: int, frequency_hz: float, **options: Any) -> pathlib.Path:
    """Compatibility call for published scripts that predate :class:`RunConfig`."""
    config, execution = _escape_config(locations, rays, frequency_hz, **options)
    return _study.run(config, execution)


def reusable(stem: str, locations: int, rays: int, site: str, crop_m: int, seed: int, max_bounces: int) -> bool:
    """Compatibility check using the historic stem-based call."""
    tag, frequency = stem.rsplit("_", 1)
    frequency_hz = float(frequency.removesuffix("ghz")) * 1e9
    config = RunConfig(
        site=site,
        crop_m=crop_m,
        law="band",
        models=tuple(MODELS),
        estimator="escape",
        next_event=None,
        walk="grid",
        locations=locations,
        frequency_hz=frequency_hz,
        max_bounces=max_bounces,
        materials="geometric",
        rays=rays,
        seed=seed,
        tag=tag,
    )
    return _study.reusable(config)


def run_coverage_ladder(locations: int, rays: int, frequency_hz: float, **options: Any) -> pathlib.Path | None:
    seeds = options.pop("seeds")
    sites = options.pop("sites", SITES)
    tag_suffix = options.pop("tag_suffix", "")
    config, execution = _escape_config(
        locations,
        rays,
        frequency_hz,
        seed=seeds[0],
        tag="",
        materials="geometric",
        **options,
    )
    return _study.run_coverage_ladder(config, execution, LadderSweepConfig(tuple(sites), tuple(seeds), tag_suffix))


def run_all_sites(locations: int, rays: int, frequency_hz: float, **options: Any) -> None:
    sites = options.pop("sites", SITES)
    tag_suffix = options.pop("tag_suffix", "")
    config, execution = _escape_config(
        locations,
        rays,
        frequency_hz,
        tag="",
        materials="geometric",
        **options,
    )
    _study.run_all_sites(config, execution, CitySweepConfig(tuple(sites), tag_suffix))


def validate(rays: int = 400_000) -> dict[str, object]:
    """Run validation with the compatibility module's selected models."""
    return _study.validate_exposure(MODELS, CONFIG, rays)


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--locations", type=int, default=0)
    parser.add_argument("--rays", type=int, default=200_000)
    parser.add_argument("--max-bounces", type=int, default=DEFAULT_MAX_BOUNCES)
    parser.add_argument(
        "--materials",
        choices=(
            "semantic",
            "walk",
            "walk_material",
            "walk_material_mixture",
            "walk_material_over_entity",
            "walk_material_facade_only",
            "geometric",
        ),
        default="geometric",
    )
    parser.add_argument(
        "--walk-npz",
        default=None,
        help=(
            "fused walk semantics to bind materials from, for --materials walk. "
            "Defaults to the eight station set that passed the 4 degree residual gate. "
            "outputs/walk_korenmarkt/walk_semantic_conflict9.npz is the nine station set "
            "that passes the sky conflict gate of section 3.2.1 instead."
        ),
    )
    parser.add_argument("--frequency-ghz", type=float, default=15.0)
    parser.add_argument("--local-cells", type=int, default=512)
    parser.add_argument("--variant", default="llvm_ad_rgb")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="trace standpoints in a process pool. Results are bit identical to the serial sweep. "
        "One, or fewer than about four standpoints per worker, is not worth the pool startup.",
    )
    parser.add_argument("--tag", default="korenmarkt")
    parser.add_argument("--walk-radius-m", type=float, default=90.0)
    parser.add_argument("--walk-spacing-m", type=float, default=3.0)
    parser.add_argument("--site", default="korenmarkt")
    parser.add_argument("--crop-m", type=int, default=250)
    parser.add_argument(
        "--tag-suffix",
        default="",
        help="Appended to the cross site run tag, so a rerun does not land on a published run's files",
    )
    parser.add_argument("--all-sites", action="store_true")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--report", metavar="STEM", default=None)
    parser.add_argument("--cities-report", action="store_true")
    parser.add_argument("--coverage-report", action="store_true")
    parser.add_argument(
        "--coverage-ladder",
        action="store_true",
        help="trace every rung of every site's evidence ladder at --crop-m, on each of --ladder-seeds, "
        "then report the shift per site with its standard error over the seeds",
    )
    parser.add_argument(
        "--ladder-seeds",
        default="7",
        help="comma separated seeds. Each redraws the walk and the per standpoint ray streams "
        "together, so they are disjoint replicates of the whole measurement",
    )
    parser.add_argument(
        "--ladder-sites",
        default=None,
        help="comma separated sites, default every site that has a binding at --crop-m",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
    if args.cities_report:
        cross_city_report(list(SITES), args.frequency_ghz * 1e9, crop_m=args.crop_m, tag_suffix=args.tag_suffix)
    elif args.coverage_report:
        coverage_report(
            args.frequency_ghz * 1e9,
            tag_suffix=args.tag_suffix,
            site=args.site,
            crop_m=args.crop_m,
            seed=args.seed,
        )
    elif args.coverage_ladder:
        run_coverage_ladder(
            args.locations,
            args.rays,
            args.frequency_ghz * 1e9,
            variant=args.variant,
            seeds=tuple(int(value) for value in args.ladder_seeds.split(",")),
            local_cells=args.local_cells,
            walk_radius_m=args.walk_radius_m,
            walk_spacing_m=args.walk_spacing_m,
            max_bounces=args.max_bounces,
            sites=tuple(args.ladder_sites.split(",")) if args.ladder_sites else SITES,
            crop_m=args.crop_m,
            tag_suffix=args.tag_suffix,
            workers=args.workers,
        )
    elif args.all_sites:
        run_all_sites(
            args.locations,
            args.rays,
            args.frequency_ghz * 1e9,
            variant=args.variant,
            seed=args.seed,
            local_cells=args.local_cells,
            walk_radius_m=args.walk_radius_m,
            walk_spacing_m=args.walk_spacing_m,
            max_bounces=args.max_bounces,
            crop_m=args.crop_m,
            tag_suffix=args.tag_suffix,
            workers=args.workers,
        )
    elif args.report:
        report(args.report)
    elif args.validate:
        outcome = validate(args.rays)
        OUTPUT.mkdir(parents=True, exist_ok=True)
        path = OUTPUT / "exposure_validation.json"
        path.write_text(json.dumps(outcome, indent=2))
        print(json.dumps(outcome, indent=2))
        print(f"wrote {path}")
    else:
        run(
            args.locations,
            args.rays,
            args.frequency_ghz * 1e9,
            variant=args.variant,
            seed=args.seed,
            tag=args.tag,
            local_cells=args.local_cells,
            walk_radius_m=args.walk_radius_m,
            walk_spacing_m=args.walk_spacing_m,
            max_bounces=args.max_bounces,
            materials=args.materials,
            site=args.site,
            crop_m=args.crop_m,
            walk_npz=pathlib.Path(args.walk_npz) if args.walk_npz else None,
            workers=args.workers,
        )
    return 0


def __getattr__(name: str) -> Any:
    """Expose legacy study attributes while callers migrate to the package."""
    return getattr(_study, name)


if __name__ == "__main__":
    sys.exit(main())
