"""Authenticate and replay the five sealed ray-reached evidence campaigns."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from semantic_twin import paths
from semantic_twin.exposure.ray_reached_evidence_audit import (
    AuditReplayPlan,
    AuditReplaySource,
    run_ray_reached_evidence_audit,
)
from semantic_twin.exposure.study import _execution_environment

_CAMPAIGNS = (
    "korenmarkt_provider_corridor_v1_first_material_interaction_v1_convergence_cuda_iid",
    "prague_staromestske_provider_corridor_v1_first_material_interaction_v1_convergence_cuda_iid",
    "madrid_plazamayor_provider_corridor_v1_first_material_interaction_v1_convergence_cuda_iid",
    "mexico_zocalo_provider_corridor_v1_first_material_interaction_v1_convergence_cuda_iid",
    "tokyo_hachiko_provider_corridor_v1_first_material_interaction_v1_convergence_cuda_iid",
)


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        nargs=2,
        action="append",
        metavar=("CONFIG", "SEALED_CAMPAIGN"),
        help="Original run config and authenticated campaign directory. Repeat for each site.",
    )
    parser.add_argument("--study-root", type=Path, help="Active semantic_twin package root")
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Isolated replay root (default: outputs/experiments/ray_reached_evidence_coverage_v1/replay)",
    )
    parser.add_argument("--persistent-transport-cache", type=Path, help="Optional runtime-only cache root")
    parser.add_argument("--dry-run", action="store_true", help="Authenticate and prepare without tracing")
    return parser.parse_args(argv)


def _default_sources(root: Path) -> tuple[AuditReplaySource, ...]:
    return tuple(
        AuditReplaySource(
            root / "config" / f"roofline_campaign_{name}.json",
            root / "outputs" / "roofline_campaign" / name,
        )
        for name in _CAMPAIGNS
    )


def run(args: argparse.Namespace, *, environment: object | None = None) -> int:
    root = paths.root().resolve() if args.study_root is None else args.study_root.resolve()
    if root != paths.root().resolve():
        raise ValueError(f"study root must be the active semantic_twin root: {paths.root().resolve()}")
    sources = (
        _default_sources(root)
        if not args.source
        else tuple(AuditReplaySource(Path(config), Path(campaign)) for config, campaign in args.source)
    )
    output = args.output_dir or root / "outputs" / "experiments" / "ray_reached_evidence_coverage_v1" / "replay"
    plan = AuditReplayPlan(sources, output)
    selected_environment = _execution_environment() if environment is None else environment
    result = run_ray_reached_evidence_audit(
        plan,
        selected_environment,
        persistent_cache_root=args.persistent_transport_cache,
        dry_run=args.dry_run,
    )
    if isinstance(result, Path):
        print(json.dumps({"manifest": str(result)}, indent=2), flush=True)
    else:
        print(json.dumps(result, indent=2, sort_keys=True), flush=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    return run(arguments(argv))


if __name__ == "__main__":
    raise SystemExit(main())
