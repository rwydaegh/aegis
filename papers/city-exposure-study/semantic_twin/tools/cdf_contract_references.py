#!/usr/bin/env python3
"""List registered production CDF configs and their sealed reference triples."""

from __future__ import annotations

import argparse

from semantic_twin.exposure.cdf_contracts import registered_body_sources, registered_reference_triples


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sync-inventory",
        action="store_true",
        help="prefix body and reference records for the GPU sync helper",
    )
    args = parser.parse_args(argv)
    if args.sync_inventory:
        for filename, sha256 in registered_body_sources():
            print("\t".join(("body", filename, sha256)))
        for config_path, reference_paths in registered_reference_triples():
            print("\t".join(("reference", config_path, *reference_paths)))
        return 0
    for config_path, reference_paths in registered_reference_triples():
        print("\t".join((config_path, *reference_paths)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
