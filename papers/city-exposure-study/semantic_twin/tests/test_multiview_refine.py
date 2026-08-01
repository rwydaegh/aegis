from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from semantic_twin.multiview_refine import (
    LabelResolver,
    correspondence_static_mask,
    parse_args,
    static_label_mask,
)


def _manifest(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "entity_id2label": {
                    "0": "Sky",
                    "1": "Building",
                    "2": "Person",
                    "3": "Truck",
                    "4": "Cobblestone paving",
                }
            }
        )
    )
    return path


def test_label_resolver_excludes_sky_and_dynamic_names_from_manifest(tmp_path: Path) -> None:
    resolver = LabelResolver.from_manifest(_manifest(tmp_path / "semantics.json"))
    labels = np.array([[0, 1, 2], [3, 4, 99]], dtype=np.uint16)

    assert resolver.names_for(labels)[0, 1] == "building"
    assert static_label_mask(labels, resolver).tolist() == [[False, True, False], [False, True, True]]
    assert resolver.excluded_ids() == {0, 2, 3}


def test_static_correspondence_sampling_rejects_dynamic_and_out_of_bounds() -> None:
    labels = np.array([[1, 1, 2], [0, 1, 1]], dtype=np.uint16)
    resolver = LabelResolver({0: "sky", 1: "building", 2: "person"})
    static = static_label_mask(labels, resolver)
    keep = correspondence_static_mask(
        np.array([[1.1, 0.1], [2.0, 0.0], [-0.6, 0.0]]),
        np.array([[1.0, 1.0], [1.0, 0.0], [0.0, 0.0]]),
        labels,
        labels,
        static,
        static,
    )
    assert keep.tolist() == [True, False, False]


def test_cli_validation_happens_without_opencv(tmp_path: Path) -> None:
    image_a, image_b = tmp_path / "a.jpg", tmp_path / "b.jpg"
    labels_a, labels_b = tmp_path / "a.npy", tmp_path / "b.npy"
    for image in (image_a, image_b):
        image.write_bytes(b"placeholder")
    np.save(labels_a, np.zeros((2, 2), dtype=np.uint16))
    np.save(labels_b, np.zeros((2, 2), dtype=np.uint16))
    common = [
        "--image-a",
        str(image_a),
        "--image-b",
        str(image_b),
        "--labels-a",
        str(labels_a),
        "--labels-b",
        str(labels_b),
        "--fx-a",
        "400",
        "--fy-a",
        "400",
        "--cx-a",
        "1",
        "--cy-a",
        "1",
        "--fx-b",
        "401",
        "--fy-b",
        "401",
        "--cx-b",
        "1",
        "--cy-b",
        "1",
        "--baseline-m",
        "12.5",
        "--out",
        str(tmp_path / "evidence.json"),
    ]
    parsed = parse_args(common)
    assert parsed.intrinsics_a.fx == 400.0
    assert parsed.baseline_m == 12.5
    with pytest.raises(ValueError, match="--baseline-m"):
        parse_args([*common[:-2], "--baseline-m", "0", "--out", str(tmp_path / "bad.json")])
