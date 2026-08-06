from __future__ import annotations

from pathlib import Path

from semantic_twin.exposure.execution import ExecutionConfig
from semantic_twin.exposure.output_policy import OutputProfile
from semantic_twin.exposure.sweeps import (
    CitySweepConfig,
    LadderSweepConfig,
    LadderTask,
    SweepEnvironment,
    _run_site_ladder,
    run_all_sites,
)
from semantic_twin.runconfig import RunConfig


def _run_config() -> RunConfig:
    return RunConfig.escape_grid(site="korenmarkt", locations=1, rays=10, tag="trial")


def _environment(
    tmp_path: Path,
    execute,
    coverage_ladder=lambda _site, _crop, _seed: (),
    reusable=lambda _run: False,
) -> SweepEnvironment:
    return SweepEnvironment(
        output=tmp_path,
        phantom="phantom.stl",
        phantom_mass_kg=70.0,
        body_coupler_type=lambda *_args, **_kwargs: object(),
        site_mesh=lambda _site, _crop: tmp_path / "mesh.ply",
        ladder_sites=lambda sites, _crop: (list(sites), {}),
        coverage_ladder=coverage_ladder,
        reusable=reusable,
        execute=execute,
        coverage_report=lambda *_args, **_kwargs: None,
        coverage_ladder_report=lambda *_args, **_kwargs: None,
        cross_city_report=lambda *_args, **_kwargs: None,
    )


def test_ladder_rebuild_preserves_output_profile(tmp_path):
    captured = []
    run = _run_config()
    execution = ExecutionConfig(workers=2, output_profile=OutputProfile.MINIMAL)
    sweep = LadderSweepConfig(("korenmarkt",), (7,))
    environment = _environment(
        tmp_path,
        lambda _run, config: captured.append(config),
        coverage_ladder=lambda _site, _crop, _seed: (("rung", "geometric", ""),),
    )
    task = LadderTask(run, execution, sweep, environment, object(), {})

    _run_site_ladder(task, 7, "korenmarkt")

    assert captured[0].output_profile is OutputProfile.MINIMAL


def test_city_sweep_rebuild_preserves_output_profile(tmp_path):
    captured = []
    execution = ExecutionConfig(output_profile="full")
    environment = _environment(tmp_path, lambda _run, config: captured.append(config))

    run_all_sites(_run_config(), execution, CitySweepConfig(("korenmarkt",)), environment)

    assert captured[0].output_profile is OutputProfile.FULL


def test_ladder_reuse_receives_the_requested_output_profile(tmp_path):
    requested = []
    run = _run_config()
    execution = ExecutionConfig(output_profile=OutputProfile.MINIMAL)
    sweep = LadderSweepConfig(("korenmarkt",), (7,))
    environment = _environment(
        tmp_path,
        lambda _run, _config: None,
        coverage_ladder=lambda _site, _crop, _seed: (("rung", "geometric", ""),),
        reusable=lambda _run, profile: requested.append(profile) or True,
    )
    task = LadderTask(run, execution, sweep, environment, object(), {})

    _run_site_ladder(task, 7, "korenmarkt")

    assert requested == [OutputProfile.MINIMAL]
