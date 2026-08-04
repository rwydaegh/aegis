"""Write the batch files and the exact prompt each model call is given.

Two independent draws over the same blinded image set, partitioned differently,
so that a repeat of one image is answered by a call that has not seen the first
answer. That is the only way a repeat spread means anything.

    python3 make_vlm_batches.py --out outputs/material_vlm --draws 2 --batches 6
"""

from __future__ import annotations

import argparse
import json
import pathlib
import random

from semantic_twin.vision.vlm import PROMPT_VERSION, build_prompt, prompt_digest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=pathlib.Path, default=pathlib.Path("outputs/material_vlm"))
    parser.add_argument("--draws", type=int, default=2)
    parser.add_argument("--batches", type=int, default=6)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    order = json.loads((args.out / "blind_order.json").read_text())
    (args.out / "prompt.txt").write_text(build_prompt())
    (args.out / "raw").mkdir(parents=True, exist_ok=True)

    plan: list[dict[str, object]] = []
    for draw in range(args.draws):
        shuffled = order[:]
        random.Random(args.seed + 101 * draw).shuffle(shuffled)
        for batch in range(args.batches):
            names = shuffled[batch :: args.batches]
            if not names:
                continue
            plan.append(
                {
                    "draw": draw,
                    "batch": batch,
                    "images": names,
                    "output": str(args.out / "raw" / f"draw{draw}_batch{batch}.jsonl"),
                }
            )
    (args.out / "batch_plan.json").write_text(
        json.dumps(
            {
                "prompt_version": PROMPT_VERSION,
                "prompt_digest": prompt_digest(),
                "prompt_file": str(args.out / "prompt.txt"),
                "image_dir": str(args.out / "blind"),
                "seed": args.seed,
                "calls": plan,
            },
            indent=2,
        )
    )
    print(f"{len(plan)} calls over {len(order)} images, prompt digest {prompt_digest()}")


if __name__ == "__main__":
    main()
