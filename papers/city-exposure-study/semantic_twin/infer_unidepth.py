"""Infer metric range and uncertainty for perspective panorama crops.

UniDepthV2 operates on normal perspective cameras.  The Street View panorama is
therefore never passed to the model directly: ``semantics.py`` has already
created 90-degree crops with known pinhole intrinsics.  The produced ``range_m``
is the Euclidean distance along each image ray, which is the quantity needed to
compare a model prediction with the first hit in the support mesh.

Example (on the GPU host)::

    python infer_unidepth.py --views views --out unidepth --model unidepth-v2-vitl14
"""

from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np
from PIL import Image


def pinhole_intrinsics(width: int, height: int, horizontal_fov_deg: float = 90.0) -> np.ndarray:
    """Return the known intrinsics of one panorama perspective crop."""
    focal = width / (2.0 * np.tan(np.deg2rad(horizontal_fov_deg) / 2.0))
    return np.array([[focal, 0.0, width / 2.0], [0.0, focal, height / 2.0], [0.0, 0.0, 1.0]], dtype=np.float32)


def uncertainty_visual(uncertainty: np.ndarray) -> Image.Image:
    """Render relative log-depth error: dark is more certain, bright is less."""
    low, high = np.nanpercentile(uncertainty, (2.0, 98.0))
    scaled = np.clip((uncertainty - low) / max(high - low, 1e-6), 0.0, 1.0)
    return Image.fromarray(np.round(scaled * 255.0).astype(np.uint8), mode="L")


def depth_visual(range_m: np.ndarray) -> Image.Image:
    """Render log range with near surfaces warm and far surfaces cool."""
    finite = np.isfinite(range_m) & (range_m > 0.0)
    low, high = np.percentile(np.log(range_m[finite]), (1.0, 99.0))
    scaled = np.clip((np.log(np.maximum(range_m, 1e-6)) - low) / max(high - low, 1e-6), 0.0, 1.0)
    # A compact perceptual ramp, with red close and blue distant.
    red = np.clip(1.5 - 2.0 * scaled, 0.0, 1.0)
    green = np.clip(1.0 - np.abs(2.0 * scaled - 1.0), 0.0, 1.0)
    blue = np.clip(2.0 * scaled - 0.5, 0.0, 1.0)
    return Image.fromarray(np.round(np.stack((red, green, blue), axis=-1) * 255.0).astype(np.uint8), mode="RGB")


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--views", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--model", default="unidepth-v2-vitl14")
    parser.add_argument("--resolution-level", type=float, default=7.0)
    parser.add_argument("--limit", type=int)
    return parser.parse_args()


def main() -> None:
    args = arguments()
    import torch
    from unidepth.models import UniDepthV2

    if not torch.cuda.is_available():
        raise RuntimeError("UniDepth inference is configured for CUDA, but no CUDA device is available")
    args.out.mkdir(parents=True, exist_ok=True)
    image_paths = sorted(args.views.glob("*.jpg"))
    if args.limit is not None:
        image_paths = image_paths[: args.limit]
    if not image_paths:
        raise FileNotFoundError(f"no JPEG views in {args.views}")

    model = UniDepthV2.from_pretrained(f"lpiccinelli/{args.model}").cuda().eval()
    model.resolution_level = args.resolution_level
    manifest: list[dict[str, object]] = []
    for image_path in image_paths:
        rgb = np.asarray(Image.open(image_path).convert("RGB"), dtype=np.uint8)
        height, width = rgb.shape[:2]
        intrinsics = pinhole_intrinsics(width, height)
        tensor = torch.from_numpy(rgb.copy()).permute(2, 0, 1)
        with torch.inference_mode():
            prediction = model.infer(tensor, torch.from_numpy(intrinsics))
        range_m = prediction["radius"][0, 0].float().cpu().numpy()
        depth_z_m = prediction["depth"][0, 0].float().cpu().numpy()
        log_error = prediction["confidence"][0, 0].float().cpu().numpy()
        output = args.out / f"{image_path.stem}.npz"
        np.savez_compressed(
            output,
            range_m=range_m.astype(np.float32),
            depth_z_m=depth_z_m.astype(np.float32),
            log_error=log_error.astype(np.float32),
            intrinsics=intrinsics,
        )
        depth_visual(range_m).save(args.out / f"{image_path.stem}_range.png")
        uncertainty_visual(log_error).save(args.out / f"{image_path.stem}_uncertainty.png")
        manifest.append(
            {
                "view": image_path.stem,
                "shape": [height, width],
                "range_median": float(np.median(range_m)),
                "range_p05": float(np.percentile(range_m, 5.0)),
                "range_p95": float(np.percentile(range_m, 95.0)),
                "relative_log_error_median": float(np.median(log_error)),
            }
        )
        print(f"[unidepth] {image_path.stem}: median range {manifest[-1]['range_median']:.2f} m")
    (args.out / "manifest.json").write_text(
        json.dumps(
            {
                "model": f"lpiccinelli/{args.model}",
                "source": str(args.views),
                "camera": "known 90-degree pinhole intrinsics per perspective crop",
                "uncertainty": "UniDepthV2 estimated scale-invariant log error, relative within each crop",
                "views": manifest,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
