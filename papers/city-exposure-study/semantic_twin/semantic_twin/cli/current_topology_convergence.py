"""Report five-site current-topology convergence through 64 replicas."""

from __future__ import annotations

import argparse
from pathlib import Path

from semantic_twin.report.current_topology_convergence import (
    EXPECTED_SITES,
    CurrentTopologyConvergenceError,
    write_current_topology_convergence,
)


def _site_path(value: str) -> tuple[str, Path]:
    site, separator, path = value.partition("=")
    if not separator or site not in EXPECTED_SITES or not path:
        raise argparse.ArgumentTypeError(f"expected SITE=PATH where SITE is one of: {', '.join(EXPECTED_SITES)}")
    return site, Path(path)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--extended",
        action="append",
        required=True,
        type=_site_path,
        metavar="SITE=PATH",
        help="One completed 64-replica current-topology campaign per site",
    )
    parser.add_argument(
        "--sealed",
        action="append",
        required=True,
        type=_site_path,
        metavar="SITE=PATH",
        help="One sealed 16-replica current-topology campaign per site",
    )
    parser.add_argument("--output", type=Path, required=True, help="Dedicated report output directory")
    parser.add_argument("--bootstrap-replicates", type=int, default=2000)
    parser.add_argument("--bootstrap-seed", type=int, default=20260814)
    return parser


def _mapping(values: list[tuple[str, Path]], parser: argparse.ArgumentParser, label: str) -> dict[str, Path]:
    result = dict(values)
    if len(result) != len(values):
        parser.error(f"duplicate site in {label} campaign arguments")
    missing = sorted(set(EXPECTED_SITES).difference(result))
    extra = sorted(set(result).difference(EXPECTED_SITES))
    if missing or extra:
        parser.error(
            f"{label} campaigns must contain every expected site exactly once"
            + (f". Missing: {', '.join(missing)}" if missing else "")
            + (f". Extra: {', '.join(extra)}" if extra else "")
        )
    return result


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse and validate command-line arguments."""
    parser = _parser()
    parsed = parser.parse_args(argv)
    parsed.extended = _mapping(parsed.extended, parser, "extended")
    parsed.sealed = _mapping(parsed.sealed, parser, "sealed")
    return parsed


def main(argv: list[str] | None = None) -> int:
    """Authenticate all campaigns and write the convergence artifacts."""
    parser = _parser()
    parsed = parser.parse_args(argv)
    extended = _mapping(parsed.extended, parser, "extended")
    sealed = _mapping(parsed.sealed, parser, "sealed")
    try:
        artifacts = write_current_topology_convergence(
            extended,
            sealed,
            parsed.output,
            bootstrap_replicates=parsed.bootstrap_replicates,
            bootstrap_seed=parsed.bootstrap_seed,
        )
    except CurrentTopologyConvergenceError as exc:
        parser.error(str(exc))
    print(
        "wrote "
        + ", ".join(
            str(path) for path in (artifacts.json, artifacts.csv, artifacts.pdf, artifacts.png, artifacts.manifest)
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["arguments", "main"]
