"""Cross-site and evidence-ladder exposure sweeps."""

from __future__ import annotations

import pathlib
import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from semantic_twin.exposure.execution import ExecutionConfig
from semantic_twin.runconfig import RunConfig


@dataclass(frozen=True)
class LadderSweepConfig:
    """The sites, replicates, and output label of one ladder sweep."""

    sites: tuple[str, ...]
    seeds: tuple[int, ...]
    tag_suffix: str = ""


@dataclass(frozen=True)
class CitySweepConfig:
    """The sites and output label of one cross-city sweep."""

    sites: tuple[str, ...]
    tag_suffix: str = ""


@dataclass(frozen=True)
class SweepEnvironment:
    """Study operations used by the generic sweep loops."""

    output: pathlib.Path
    phantom: str
    phantom_mass_kg: float
    body_coupler_type: Any
    site_mesh: Callable[[str, int], pathlib.Path]
    ladder_sites: Callable[[tuple[str, ...], int], tuple[list[str], dict[str, str]]]
    coverage_ladder: Callable[[str, int, int], tuple[tuple[str, str, str], ...]]
    reusable: Callable[..., bool]
    execute: Callable[[RunConfig, ExecutionConfig], pathlib.Path]
    coverage_report: Callable[..., pathlib.Path]
    coverage_ladder_report: Callable[..., pathlib.Path | None]
    cross_city_report: Callable[..., None]


@dataclass(frozen=True)
class LadderTask:
    run: RunConfig
    execution: ExecutionConfig
    sweep: LadderSweepConfig
    environment: SweepEnvironment
    coupler: Any
    failures: dict[str, str]


def run_coverage_ladder(
    run: RunConfig,
    execution: ExecutionConfig,
    sweep: LadderSweepConfig,
    environment: SweepEnvironment,
) -> pathlib.Path | None:
    """Climb every admitted site's evidence ladder in seed-major order."""
    coupler = environment.body_coupler_type(
        environment.phantom,
        run.frequency_hz,
        body_mass_kg=environment.phantom_mass_kg,
    )
    admitted, refused = environment.ladder_sites(sweep.sites, run.crop_m)
    for site, reason in refused.items():
        print(f"[skip] {site}: {reason}", flush=True)
    failures: dict[str, str] = {}
    task = LadderTask(run, execution, sweep, environment, coupler, failures)
    for seed in sweep.seeds:
        for site in admitted:
            _run_site_ladder(task, seed, site)
            environment.coverage_report(
                run.frequency_hz,
                sweep.tag_suffix,
                site=site,
                crop_m=run.crop_m,
                seed=seed,
            )
    return environment.coverage_ladder_report(
        admitted,
        run.crop_m,
        sweep.seeds,
        run.frequency_hz,
        tag_suffix=sweep.tag_suffix,
        refused=refused,
        failures=failures,
    )


def _run_site_ladder(task: LadderTask, seed: int, site: str) -> None:
    for tag, materials, _description in task.environment.coverage_ladder(site, task.run.crop_m, seed):
        tagged = f"{tag}{task.sweep.tag_suffix}"
        rung = task.run.replace(site=site, seed=seed, tag=tagged, materials=materials)
        stem = f"{tagged}_{task.run.frequency_ghz:g}ghz"
        if _reusable(task.environment, rung, task.execution.output_profile):
            print(f"[have] {stem}", flush=True)
            continue
        if (task.environment.output / f"{stem}_manifest.json").exists():
            raise ValueError(
                f"{stem} is on disk and was made at different settings. Overwriting it would "
                "destroy a run something else may quote. Pass --tag-suffix to write beside it."
            )
        try:
            task.environment.execute(
                rung,
                ExecutionConfig(
                    workers=task.execution.workers,
                    coupler=task.coupler,
                    output_profile=task.execution.output_profile,
                ),
            )
        except Exception as error:  # noqa: BLE001
            task.failures[stem] = repr(error)
            print(f"RUNG FAILED {stem}: {error!r}", flush=True)


def run_all_sites(
    run: RunConfig,
    execution: ExecutionConfig,
    sweep: CitySweepConfig,
    environment: SweepEnvironment,
) -> None:
    """Run the geometric control at each site, then update the aggregate."""
    coupler = environment.body_coupler_type(
        environment.phantom,
        run.frequency_hz,
        body_mass_kg=environment.phantom_mass_kg,
    )
    done: list[str] = []
    buildable: list[str] = []
    for site in sweep.sites:
        if not _has_comparable_mesh(site, run.crop_m, environment):
            continue
        buildable.append(site)
        stem = "city" if run.crop_m == 130 else f"city{run.crop_m}"
        site_run = run.replace(
            site=site,
            tag=f"{stem}{sweep.tag_suffix}_{site}",
            materials="geometric",
            walk_npz=None,
        )
        try:
            environment.execute(
                site_run,
                ExecutionConfig(
                    workers=execution.workers,
                    coupler=coupler,
                    output_profile=execution.output_profile,
                ),
            )
            done.append(site)
        except Exception as error:  # noqa: BLE001
            print(f"SITE FAILED {site}: {error!r}", flush=True)
        environment.cross_city_report(
            done,
            run.frequency_hz,
            crop_m=run.crop_m,
            tag_suffix=sweep.tag_suffix,
            sites_expected=tuple(buildable),
        )


def _has_comparable_mesh(site: str, crop_m: int, environment: SweepEnvironment) -> bool:
    try:
        environment.site_mesh(site, crop_m)
    except FileNotFoundError:
        print(f"[skip] {site}: no {crop_m} m mesh, not comparable at this radius", flush=True)
        return False
    return True


def _reusable(environment: SweepEnvironment, run: RunConfig, profile: Any) -> bool:
    """Call old one-argument and new profile-aware reuse adapters safely."""
    callback = environment.reusable
    try:
        signature = inspect.signature(callback)
    except (TypeError, ValueError):
        return callback(run, profile)
    try:
        signature.bind(run, profile)
    except TypeError:
        return callback(run)
    return callback(run, profile)
