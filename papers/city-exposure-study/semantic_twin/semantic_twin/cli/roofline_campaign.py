"""Prepare, preflight, and run one sealed full-walk roofline campaign."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from semantic_twin import paths
from semantic_twin.exposure.roofline_campaign import run_roofline_campaign
from semantic_twin.exposure.roofline_setup import (
    load_roofline_setup,
    preflight_report,
    prepare_roofline_campaign,
    write_preflight,
)
from semantic_twin.exposure.study import _execution_environment


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True, help="Strict roofline campaign JSON")
    parser.add_argument(
        "--study-root",
        type=Path,
        help="Override the study root recorded in the JSON. It must be this package's active root.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Prepare and preflight without tracing a replica")
    parser.add_argument("--preflight-output", type=Path, help="Preflight report path")
    parser.add_argument("--staging-manifest", type=Path, help="Exact staged-input manifest path")
    return parser.parse_args(argv)


def _failure(error: Exception, *, phase: str) -> dict[str, Any]:
    return {
        "ready_to_trace": False,
        "phase": phase,
        "refusal_reason": f"{type(error).__name__}: {error}",
    }


def _paths(args: argparse.Namespace, output_dir: Path) -> tuple[Path, Path]:
    preflight = args.preflight_output or output_dir / "preflight.json"
    staging = args.staging_manifest or output_dir / "staged_inputs.json"
    return Path(preflight), Path(staging)


def run(args: argparse.Namespace, *, environment: Any | None = None) -> int:
    """Execute the command with injectable boundaries for deterministic tests."""
    setup = load_roofline_setup(args.config, study_root=args.study_root)
    preflight_path, staging_path = _paths(args, setup.campaign.output_dir)
    active_root = paths.root().resolve()
    if setup.study_root != active_root:
        error = ValueError(
            f"configured study root {setup.study_root} does not match the active package root {active_root}; "
            "stage a coherent code-and-input tree instead of mixing checkouts"
        )
        write_preflight(preflight_path, _failure(error, phase="root_validation"))
        if args.dry_run:
            print(json.dumps(_failure(error, phase="root_validation"), indent=2), flush=True)
            return 2
        raise error

    selected_environment = _execution_environment() if environment is None else environment
    try:
        prepared = prepare_roofline_campaign(setup, selected_environment)
        report = preflight_report(prepared)
    except Exception as error:
        failure = _failure(error, phase="preparation")
        write_preflight(preflight_path, failure)
        if args.dry_run:
            print(json.dumps(failure, indent=2), flush=True)
            return 2
        raise

    write_preflight(preflight_path, report)
    staging = {
        "schema": "aegis.roofline-staged-inputs",
        "version": 1,
        "campaign_identity": report["campaign_identity"],
        **report["staged_inputs"],
    }
    write_preflight(staging_path, staging)
    print(json.dumps(report, indent=2, sort_keys=True), flush=True)
    if not report["ready_to_trace"]:
        return 2
    if args.dry_run:
        return 0
    outputs = run_roofline_campaign(prepared)
    print(json.dumps({name: str(path) for name, path in outputs.items()}, indent=2, sort_keys=True), flush=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    return run(arguments(argv))


if __name__ == "__main__":
    raise SystemExit(main())
