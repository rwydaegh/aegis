"""Run Depth Anything V2 Metric Outdoor as an independent depth opinion.

Unlike UniDepthV2 this model has no native per-pixel uncertainty output.  Its
disagreement with UniDepth is therefore used to increase uncertainty, never as
sole authority to create a blocker.
"""

from __future__ import annotations

import json
import pathlib

import numpy as np
from PIL import Image

from semantic_twin.vision.depth_models import depth_visual, pinhole_intrinsics


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


def run_depth_anything(
    views: pathlib.Path,
    out: pathlib.Path,
    *,
    model_name: str = "depth-anything/Depth-Anything-V2-Metric-Outdoor-Large-hf",
) -> None:
    import torch
    from transformers import AutoImageProcessor, AutoModelForDepthEstimation

    if not torch.cuda.is_available():
        raise RuntimeError("Depth Anything inference is configured for CUDA, but no CUDA device is available")
    out.mkdir(parents=True, exist_ok=True)
    # The model id is a deliberate CLI input. Pinning a single commit here
    # would silently replace the model the caller selected.
    processor = AutoImageProcessor.from_pretrained(model_name)  # nosec B615
    model = AutoModelForDepthEstimation.from_pretrained(model_name).cuda().eval()  # nosec B615
    records = []
    for image_path in sorted(views.glob("*.jpg")):
        image = Image.open(image_path).convert("RGB")
        inputs = processor(images=image, return_tensors="pt").to("cuda")
        with torch.inference_mode(), torch.autocast("cuda", dtype=torch.float16):
            outputs = model(**inputs)
        postprocessed = processor.post_process_depth_estimation(outputs, target_sizes=[image.size[::-1]])[0]
        depth_z_m = postprocessed["predicted_depth"].float().cpu().numpy()
        range_m = axial_depth_to_ray_range(depth_z_m)
        np.savez_compressed(
            out / f"{image_path.stem}.npz",
            range_m=range_m.astype(np.float32),
            depth_z_m=depth_z_m.astype(np.float32),
        )
        depth_visual(range_m).save(out / f"{image_path.stem}_range.png")
        records.append(
            {
                "view": image_path.stem,
                "range_median": float(np.median(range_m)),
                "range_p05": float(np.percentile(range_m, 5.0)),
                "range_p95": float(np.percentile(range_m, 95.0)),
            }
        )
        print(f"[depth-anything] {image_path.stem}: median range {records[-1]['range_median']:.2f} m")
    (out / "manifest.json").write_text(
        json.dumps(
            {
                "model": model_name,
                "uncertainty": "none native: used only as an independent disagreement term",
                "views": records,
            },
            indent=2,
        )
    )
