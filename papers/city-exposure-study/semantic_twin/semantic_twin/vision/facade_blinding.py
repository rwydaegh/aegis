"""Blind the crop set before it is shown to a model, and keep the key.

A file called ``..._texture.png`` tells the model which source it is looking at,
and the whole point of the comparison is that the model should not know. The
blinded names are a keyed digest of the crop id and the source, so the mapping is
reproducible from the key without storing a lookup the reader has to trust.

    python3 blind_facade_crops.py --out outputs/material_vlm
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import shutil

KEY = "material-vlm-blind-v1"


def blind_name(crop_id: str, source: str) -> str:
    digest = hashlib.sha256(f"{KEY}:{crop_id}:{source}".encode()).hexdigest()[:10]
    return f"patch_{digest}"


def blind_facade_crops(out: pathlib.Path) -> None:
    """Copy facade crops under deterministic source-blind names."""
    manifest = json.loads((out / "crops.json").read_text())
    blind_dir = out / "blind"
    blind_dir.mkdir(parents=True, exist_ok=True)

    key: dict[str, dict[str, str]] = {}
    for record in manifest["crops"]:
        for source in ("panorama", "texture"):
            name = blind_name(record["crop_id"], source)
            shutil.copyfile(out / "crops" / f"{record['crop_id']}_{source}.png", blind_dir / f"{name}.png")
            key[name] = {
                "crop_id": record["crop_id"],
                "source": source,
                "patch": record["patch"],
                "wall_group": record["wall_group"],
            }
    (out / "blind_key.json").write_text(json.dumps({"key_string": KEY, "map": key}, indent=2, sort_keys=True))
    order = sorted(key)
    (out / "blind_order.json").write_text(json.dumps(order, indent=2))
    print(f"{len(order)} blinded images -> {blind_dir}")
