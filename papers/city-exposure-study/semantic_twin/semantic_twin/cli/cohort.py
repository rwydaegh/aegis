"""Validate and report the ten-city cohort route contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from semantic_twin.cohort import CohortManifestError, route_readiness


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--root", type=Path, default=None, help="study root containing data/ and outputs/")
    parser.add_argument("--json", action="store_true", dest="as_json", help="emit machine-readable readiness JSON")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
    try:
        statuses = route_readiness(manifest_path=args.manifest, root=args.root)
    except (CohortManifestError, OSError, json.JSONDecodeError) as error:
        print(f"cohort manifest error: {error}")
        return 2
    if args.as_json:
        print(json.dumps([status.as_dict() for status in statuses], indent=2))
    else:
        for status in statuses:
            state = "ready" if status.ready else "blocked"
            print(f"{status.site:24} {status.kind:16} {state}")
            for missing in status.missing:
                print(f"  missing: {missing}")
            for invalid in status.invalid:
                print(f"  invalid: {invalid}")
    return 0 if all(status.ready for status in statuses) else 1


if __name__ == "__main__":
    raise SystemExit(main())
