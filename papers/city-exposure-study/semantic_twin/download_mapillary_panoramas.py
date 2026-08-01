"""Persist selected Mapillary spherical panoramas for multi-view reconstruction."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from semantic_twin.mapillary import persist_selected_panorama  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", type=pathlib.Path, required=True)
    parser.add_argument("--scene", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    args = parser.parse_args()
    records = json.loads(args.metadata.read_text())
    if not isinstance(records, list):
        raise ValueError("metadata must be a JSON list of Mapillary image records")
    for index, record in enumerate(records):
        out_dir = args.out / f"view_{index:02d}_{record['id']}"
        result = persist_selected_panorama(record, args.scene, out_dir)
        print(f"[mapillary] {record['id']} -> {result}")


if __name__ == "__main__":
    main()
