"""Write the batch files and the exact prompt each model call is given.

Two independent draws over the same blinded image set, partitioned differently,
so that a repeat of one image is answered by a call that has not seen the first
answer. That is the only way a repeat spread means anything.

    python3 make_vlm_batches.py --out outputs/material_vlm --draws 2 --batches 6
"""

from __future__ import annotations

import json
import pathlib
import random

from semantic_twin.vision.vlm import PROMPT_VERSION, build_prompt, prompt_digest


def make_vlm_batches(out: pathlib.Path, *, draws: int = 2, batches: int = 6, seed: int = 7) -> None:
    """Write the reproducible material VLM batch plan."""
    order = json.loads((out / "blind_order.json").read_text())
    (out / "prompt.txt").write_text(build_prompt())
    (out / "raw").mkdir(parents=True, exist_ok=True)

    plan: list[dict[str, object]] = []
    for draw in range(draws):
        shuffled = order[:]
        random.Random(seed + 101 * draw).shuffle(shuffled)  # nosec B311 - reproducible study partition
        for batch in range(batches):
            names = shuffled[batch::batches]
            if not names:
                continue
            plan.append(
                {
                    "draw": draw,
                    "batch": batch,
                    "images": names,
                    "output": str(out / "raw" / f"draw{draw}_batch{batch}.jsonl"),
                }
            )
    (out / "batch_plan.json").write_text(
        json.dumps(
            {
                "prompt_version": PROMPT_VERSION,
                "prompt_digest": prompt_digest(),
                "prompt_file": str(out / "prompt.txt"),
                "image_dir": str(out / "blind"),
                "seed": seed,
                "calls": plan,
            },
            indent=2,
        )
    )
    print(f"{len(plan)} calls over {len(order)} images, prompt digest {prompt_digest()}")
