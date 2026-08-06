"""Audit propagation blend files against their code and source data."""

import argparse
import pathlib

from semantic_twin.viz.blender.audit import run_audit


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", action="append", default=[])
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--scratch", type=pathlib.Path, default=pathlib.Path("/tmp/blend_qa"))
    return parser.parse_args()


def main() -> None:
    run_audit(arguments())


if __name__ == "__main__":
    main()
