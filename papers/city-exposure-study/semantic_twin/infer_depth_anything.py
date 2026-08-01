"""Run Depth Anything V2 Metric Outdoor as an independent depth opinion.

Unlike UniDepthV2 this model has no native per-pixel uncertainty output.  Its
disagreement with UniDepth is therefore used to increase uncertainty, never as
sole authority to create a blocker.
"""

from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np
from PIL import Image

from infer_unidepth import depth_visual, pinhole_intrinsics


def axial_depth_to_ray_range(depth_z_m: np.ndarray) -> np.ndarray:
    """Convert pinhole axial depth to Euclidean distance along each pixel ray."""
    height, width = depth_z_m.shape
    intrinsics = pinhole_intrinsics(width, height)
    x, y = np.meshgrid(np.arange(width, dtype=np.float32), np.arange(height, dtype=np.float32))
    ray_norm = np.sqrt(
        1.0
        + np.square((x + 0.5 - intrinsics[0, 2]) / intrinsics[0, 0])
        + np.square((y + 0.5 - intrinsics[1, 2]) / intrinsics[1, 1])
    )
    return depth_z_m * ray_norm


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--views", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--model", default="depth-anything/Depth-Anything-V2-Metric-Outdoor-Large-hf")
    return parser.parse_args()


def main() -> None:
    args = arguments()
    import torch
    from transformers import AutoImageProcessor, AutoModelForDepthEstimation

    if not torch.cuda.is_available():
        raise RuntimeError("Depth Anything inference is configured for CUDA, but no CUDA device is available")
    args.out.mkdir(parents=True, exist_ok=True)
    processor = AutoImageProcessor.from_pretrained(args.model)
    model = AutoModelForDepthEstimation.from_pretrained(args.model).cuda().eval()
    records = []
    for image_path in sorted(args.views.glob("*.jpg")):
        image = Image.open(image_path).convert("RGB")
        inputs = processor(images=image, return_tensors="pt").to("cuda")
        with torch.inference_mode(), torch.autocast("cuda", dtype=torch.float16):
            outputs = model(**inputs)
        postprocessed = processor.post_process_depth_estimation(outputs, target_sizes=[image.size[::-1]])[0]
        depth_z_m = postprocessed["predicted_depth"].float().cpu().numpy()
        range_m = axial_depth_to_ray_range(depth_z_m)
        np.savez_compressed(
            args.out / f"{image_path.stem}.npz",
            range_m=range_m.astype(np.float32),
            depth_z_m=depth_z_m.astype(np.float32),
        )
        depth_visual(range_m).save(args.out / f"{image_path.stem}_range.png")
        records.append(
            {
                "view": image_path.stem,
                "range_median": float(np.median(range_m)),
                "range_p05": float(np.percentile(range_m, 5.0)),
                "range_p95": float(np.percentile(range_m, 95.0)),
            }
        )
        print(f"[depth-anything] {image_path.stem}: median range {records[-1]['range_median']:.2f} m")
    (args.out / "manifest.json").write_text(
        json.dumps(
            {
                "model": args.model,
                "uncertainty": "none native: used only as an independent disagreement term",
                "views": records,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
