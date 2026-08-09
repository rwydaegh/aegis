"""Run SAM3 text segmentation and select the instance covering an RF hit."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import time
from typing import Any

import numpy as np
from PIL import Image, ImageDraw


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _inventory_prompts(path: pathlib.Path) -> list[str]:
    document = json.loads(path.read_text())
    return [
        str(record["sam3_prompt"])
        for record in document["classes"]
        if record.get("scene_role") != "unresolved" and record.get("sam3_prompt")
    ]


def _circle(height: int, width: int, x: int, y: int, radius: int) -> np.ndarray:
    yy, xx = np.ogrid[:height, :width]
    return (xx - x) ** 2 + (yy - y) ** 2 <= radius**2


def _overlay(image: Image.Image, mask: np.ndarray, *, x: int, y: int, radius: int) -> Image.Image:
    base = np.asarray(image.convert("RGB"), dtype=np.float32)
    color = np.array([0.0, 235.0, 125.0], dtype=np.float32)
    base[mask] = 0.55 * base[mask] + 0.45 * color
    rendered = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    draw = ImageDraw.Draw(rendered)
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), outline=(255, 220, 0), width=2)
    arm, gap = max(radius + 6, 10), 2
    for line in (
        (x - arm, y, x - gap, y),
        (x + gap, y, x + arm, y),
        (x, y - arm, x, y - gap),
        (x, y + gap, x, y + arm),
    ):
        draw.line(line, fill=(255, 40, 40), width=2)
    return rendered


def run_probe(args: argparse.Namespace) -> dict[str, Any]:
    import torch
    from sam3.model.sam3_image_processor import Sam3Processor
    from sam3.model_builder import build_sam3_image_model

    started = time.perf_counter()
    model = build_sam3_image_model(
        checkpoint_path=str(args.checkpoint),
        load_from_HF=False,
        device="cuda",
    )
    processor = Sam3Processor(model, confidence_threshold=args.threshold)
    model_load_s = time.perf_counter() - started
    results: dict[str, Any] = {
        "checkpoint": str(args.checkpoint),
        "threshold": args.threshold,
        "model_load_s": model_load_s,
        "device": torch.cuda.get_device_name(0),
        "images": [],
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)

    for image_path in args.images:
        image = Image.open(image_path).convert("RGB")
        width, height = image.size
        x = args.hit_x if args.hit_x is not None else width // 2
        y = args.hit_y if args.hit_y is not None else height // 2
        if not 0 <= x < width or not 0 <= y < height:
            raise ValueError(f"hit ({x}, {y}) outside {width}x{height} image")
        footprint = _circle(height, width, x, y, args.footprint_radius_px)
        encoded_at = time.perf_counter()
        with torch.autocast("cuda", dtype=torch.bfloat16):
            state = processor.set_image(image)
        image_result: dict[str, Any] = {
            "image": str(image_path),
            "size": [width, height],
            "hit": [x, y],
            "footprint_radius_px": args.footprint_radius_px,
            "encode_s": time.perf_counter() - encoded_at,
            "prompts": [],
        }

        for prompt in args.prompt:
            prompted_at = time.perf_counter()
            with torch.autocast("cuda", dtype=torch.bfloat16):
                output = processor.set_text_prompt(state=state, prompt=prompt)
            masks_tensor = output["masks"]
            if masks_tensor.ndim == 4:
                masks_tensor = masks_tensor[:, 0]
            masks = masks_tensor.detach().cpu().numpy().astype(bool)
            scores = output["scores"].detach().cpu().tolist()
            boxes = output["boxes"].detach().cpu().tolist()
            coverages = [float(mask[footprint].mean()) for mask in masks]
            hit_flags = [bool(mask[y, x]) for mask in masks]
            if len(masks):
                selected = max(range(len(masks)), key=lambda index: (coverages[index], scores[index]))
                union = np.logical_or.reduce(masks)
                selected_mask = masks[selected]
            else:
                selected = None
                union = np.zeros((height, width), dtype=bool)
                selected_mask = union

            stem = f"{image_path.stem}__{_slug(prompt)}"
            union_path = args.output_dir / f"{stem}__union.png"
            union_mask_path = args.output_dir / f"{stem}__union_mask.png"
            selected_path = args.output_dir / f"{stem}__selected.png"
            mask_path = args.output_dir / f"{stem}__mask.png"
            _overlay(image, union, x=x, y=y, radius=args.footprint_radius_px).save(union_path)
            Image.fromarray(union.astype(np.uint8) * 255).save(union_mask_path)
            _overlay(image, selected_mask, x=x, y=y, radius=args.footprint_radius_px).save(selected_path)
            Image.fromarray(selected_mask.astype(np.uint8) * 255).save(mask_path)
            image_result["prompts"].append(
                {
                    "prompt": prompt,
                    "inference_s": time.perf_counter() - prompted_at,
                    "instances": len(masks),
                    "scores": scores,
                    "boxes_xyxy": boxes,
                    "hit_flags": hit_flags,
                    "footprint_coverages": coverages,
                    "selected_instance": selected,
                    "selected_hit": bool(selected_mask[y, x]),
                    "selected_footprint_coverage": float(selected_mask[footprint].mean()),
                    "selected_area_fraction": float(selected_mask.mean()),
                    "union_overlay": str(union_path),
                    "union_mask": str(union_mask_path),
                    "selected_overlay": str(selected_path),
                    "selected_mask": str(mask_path),
                }
            )
        results["images"].append(image_result)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", type=pathlib.Path, nargs="+")
    parser.add_argument("--checkpoint", type=pathlib.Path, required=True)
    parser.add_argument("--output-dir", type=pathlib.Path, required=True)
    parser.add_argument("--prompt", action="append", default=[])
    parser.add_argument("--inventory-json", type=pathlib.Path)
    parser.add_argument("--threshold", type=float, default=0.3)
    parser.add_argument("--hit-x", type=int)
    parser.add_argument("--hit-y", type=int)
    parser.add_argument("--footprint-radius-px", type=int, default=4)
    parser.add_argument("--json", type=pathlib.Path)
    args = parser.parse_args()
    if args.inventory_json is not None:
        args.prompt.extend(_inventory_prompts(args.inventory_json))
    if not args.prompt:
        parser.error("at least one --prompt or --inventory-json is required")
    result = run_probe(args)
    encoded = json.dumps(result, indent=2)
    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(encoded + "\n")
    print(encoded)


if __name__ == "__main__":
    main()
