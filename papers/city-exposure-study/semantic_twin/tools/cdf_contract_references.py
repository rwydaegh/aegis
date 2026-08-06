#!/usr/bin/env python3
"""List registered production CDF configs and their sealed reference triples."""

from __future__ import annotations

from semantic_twin.exposure.cdf_contracts import registered_reference_triples


def main() -> int:
    for config_path, reference_paths in registered_reference_triples():
        print("\t".join((config_path, *reference_paths)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
