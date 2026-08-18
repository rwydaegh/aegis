"""Materialize, run, and report the sealed roofline budget-sensitivity schedule."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from semantic_twin.cli.roofline_campaign import arguments as campaign_arguments
from semantic_twin.cli.roofline_campaign import run as run_campaign
from semantic_twin.exposure.roofline_budget_sensitivity import (
    FirstDiffuseCapture,
    load_budget_schedule,
    materialize_budget_configs,
)
from semantic_twin.exposure.roofline_campaign import campaign_identity, run_roofline_campaign
from semantic_twin.exposure.roofline_setup import load_roofline_setup, preflight_report, prepare_roofline_campaign
from semantic_twin.exposure.study import _execution_environment
from semantic_twin.report.roofline_budget_sensitivity import write_budget_sensitivity


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schedule", type=Path, required=True)
    parser.add_argument("--study-root", type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("materialize", help="write the 18 explicit campaign configurations")
    commands.add_parser("preflight", help="preflight all generated campaigns without tracing")
    commands.add_parser("run", help="run or resume all campaigns with opt-in directional capture")
    report = commands.add_parser("report", help="authenticate completed campaigns and write artifacts")
    report.add_argument("--output", type=Path, help="artifact path prefix without extension")
    complete = commands.add_parser("all", help="materialize, run, authenticate, and report the complete sweep")
    complete.add_argument("--output", type=Path, help="artifact path prefix without extension")
    return parser


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    return _parser().parse_args(argv)


def _prepared(schedule, site, arm, *, environment):
    config = schedule.generated_config(site, arm)
    setup = load_roofline_setup(config, study_root=schedule.study_root)
    prepared = prepare_roofline_campaign(setup, environment)
    report = preflight_report(prepared)
    if not report["ready_to_trace"]:
        raise RuntimeError(f"budget arm refused preflight: {site}/{arm.key}: {report['refusal_reason']}")
    return prepared, report


def _preflight(schedule) -> int:
    environment = _execution_environment()
    reports = {}
    for site in schedule.sites:
        for arm in schedule.arms:
            parsed = campaign_arguments(
                [
                    "--config",
                    str(schedule.generated_config(site, arm)),
                    "--study-root",
                    str(schedule.study_root),
                    "--dry-run",
                ]
            )
            status = run_campaign(parsed, environment=environment)
            reports[f"{site}/{arm.key}"] = status
            if status:
                return status
    print(json.dumps(reports, indent=2, sort_keys=True), flush=True)
    return 0


def _run(schedule) -> int:
    environment = _execution_environment()
    for site in schedule.sites:
        for arm in schedule.arms:
            prepared, report = _prepared(schedule, site, arm, environment=environment)
            campaign_output = prepared.config.output_dir
            capture_root = campaign_output / "first_diffuse_common_support"
            checkpoint_index = campaign_output / "checkpoint" / "index.json"
            if checkpoint_index.exists() and not (capture_root / "manifest.json").exists():
                raise RuntimeError(
                    f"{site}/{arm.key} has campaign checkpoints but no complete directional capture. "
                    "use a fresh diagnostic output directory so paired fields cannot be silently omitted"
                )
            if (capture_root / "manifest.json").exists():
                print(
                    json.dumps({"site": site, "budget": arm.key, "status": "already_complete"}, sort_keys=True),
                    flush=True,
                )
                continue
            capture = FirstDiffuseCapture(
                capture_root,
                points=len(prepared.walk),
                common_cells=schedule.common_support_cells,
            )
            outputs = run_roofline_campaign(prepared, point_capture=capture)
            identity = campaign_identity(prepared)
            capture_manifest = capture.finalize(
                campaign_identity_sha256=identity["sha256"], schedule_sha256=schedule.sha256
            )
            print(
                json.dumps(
                    {
                        "site": site,
                        "budget": arm.key,
                        "preflight_identity": report["campaign_identity"]["sha256"],
                        "campaign_manifest": str(outputs["manifest"]),
                        "capture_manifest": str(capture_manifest),
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
    return 0


def main(argv: list[str] | None = None) -> int:
    """Execute one schedule command."""
    parsed = _parser().parse_args(argv)
    try:
        schedule = load_budget_schedule(parsed.schedule, study_root=parsed.study_root)
        if parsed.command in ("materialize", "preflight", "run", "all"):
            paths = materialize_budget_configs(schedule)
            if parsed.command == "materialize":
                print(json.dumps([str(path) for path in paths], indent=2), flush=True)
                return 0
        if parsed.command == "preflight":
            return _preflight(schedule)
        if parsed.command == "run":
            return _run(schedule)
        if parsed.command == "all":
            status = _run(schedule)
            if status:
                return status
        output = parsed.output or schedule.output_dir / "roofline_budget_sensitivity_v1"
        artifacts = write_budget_sensitivity(schedule, output)
    except (OSError, RuntimeError, ValueError) as exc:
        _parser().error(str(exc))
    print(json.dumps({name: str(path) for name, path in artifacts.__dict__.items()}, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["arguments", "main"]
