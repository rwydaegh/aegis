from __future__ import annotations

import json

import numpy as np

from run_sam3_surface_probe import _circle, _inventory_prompts, _slug


def test_slug_makes_prompt_safe_for_artifact_name() -> None:
    assert _slug("Pale stone / window surround!") == "pale_stone_window_surround"


def test_circle_marks_exact_pixel_and_radius_one_neighbors() -> None:
    point = _circle(7, 9, 4, 3, 0)
    disk = _circle(7, 9, 4, 3, 1)

    assert point.sum() == 1
    assert point[3, 4]
    assert disk.sum() == 5
    assert np.all(disk[2:5, 4])


def test_inventory_prompts_omits_unresolved_class(tmp_path) -> None:
    path = tmp_path / "inventory.json"
    path.write_text(
        json.dumps(
            {
                "classes": [
                    {"sam3_prompt": "red brick wall", "scene_role": "static_support"},
                    {"sam3_prompt": "remaining ambiguity", "scene_role": "unresolved"},
                ]
            }
        )
    )

    assert _inventory_prompts(path) == ["red brick wall"]
