"""Infer metric range and uncertainty for perspective panorama crops.

UniDepthV2 operates on normal perspective cameras.  The Street View panorama is
therefore never passed to the model directly: ``semantic_twin/vision/views.py``
has already created 90-degree crops with known pinhole intrinsics.  The produced ``range_m``
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

from semantic_twin.vision.bodies import pinhole_intrinsics as body_intrinsics

# What UniDepthV2's ``confidence`` output actually is, settled from the source
# rather than from the key name.  ``unidepth/models/unidepthv2/decoder.py``
# returns ``exp(logconfidence)``, and ``unidepthv2.py`` trains ``logconfidence``
# with the ``Confidence`` loss, which regresses it against the magnitude of the
# depth error of the median-rescaled prediction.  The upstream V2 notes agree:
# "the model outputs confidence as the estimated scale-invariant log error, i.e.
# the confidence is a ranking and relative within one input".  A corruption
# probe on a real Korenmarkt crop confirms the direction: the median field value
# rises from 0.583 on the original image to 0.849 under heavy pixel noise and
# 0.741 on a flat grey frame.  The field is an error ranking that grows where
# the prediction is worse.  It is not a confidence, and its absolute magnitude
# is not a log-depth standard deviation.
UNCERTAINTY_FIELD = "UniDepthV2 confidence output, an error ranking relative within one crop"

# Anchor for turning that ranking into a usable log-depth sigma.  UniDepthV2
# reports roughly 10-20 percent absolute relative depth error on outdoor
# benchmarks, so pinning the median pixel at 0.15 in log-depth is an engineering
# prior of the same kind as the mesh prior in ``compare_mesh_depth.py``.  It is
# deliberately a stated, recorded choice rather than raw model units.
DEFAULT_REFERENCE_LOG_SIGMA = 0.15


def relative_error_to_log_sigma(
    relative_error: np.ndarray,
    *,
    reference_log_sigma: float = DEFAULT_REFERENCE_LOG_SIGMA,
) -> np.ndarray:
    """Anchor UniDepth's relative error ranking onto a log-depth sigma.

    The raw field carries no metric units, so consuming it directly as a
    standard deviation invents an absolute scale.  The median pixel of a crop is
    pinned to ``reference_log_sigma`` and every other pixel keeps its relative
    order, which makes the absolute scale an explicit calibration instead of an
    accident of the checkpoint.
    """
    field = np.asarray(relative_error, dtype=np.float64)
    if reference_log_sigma <= 0.0:
        raise ValueError("reference_log_sigma must be positive")
    finite = np.isfinite(field) & (field > 0.0)
    if not np.any(finite):
        raise ValueError("the relative error field has no positive finite values to anchor")
    return (reference_log_sigma * np.abs(field) / np.median(field[finite])).astype(np.float32)


def pinhole_intrinsics(width: int, height: int, horizontal_fov_deg: float = 90.0) -> np.ndarray:
    """Intrinsics of one panorama perspective crop, in the single precision UniDepth wants.

    The arithmetic is :func:`semantic_twin.vision.bodies.pinhole_intrinsics`,
    which the body reconstruction already needed and which validates its inputs.
    Narrowing its float64 result rounds each element exactly once, so this is bit
    identical to the copy that used to live here.
    """
    return body_intrinsics(width, height, horizontal_fov_deg).astype(np.float32)


def uncertainty_visual(uncertainty: np.ndarray) -> Image.Image:
    """Render the relative error ranking: dark is more reliable, bright is less."""
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
    parser.add_argument("--reference-log-sigma", type=float, default=DEFAULT_REFERENCE_LOG_SIGMA)
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
        relative_error = prediction["confidence"][0, 0].float().cpu().numpy()
        log_sigma = relative_error_to_log_sigma(relative_error, reference_log_sigma=args.reference_log_sigma)
        output = args.out / f"{image_path.stem}.npz"
        np.savez_compressed(
            output,
            range_m=range_m.astype(np.float32),
            depth_z_m=depth_z_m.astype(np.float32),
            relative_error=relative_error.astype(np.float32),
            log_sigma=log_sigma,
            intrinsics=intrinsics,
        )
        depth_visual(range_m).save(args.out / f"{image_path.stem}_range.png")
        uncertainty_visual(relative_error).save(args.out / f"{image_path.stem}_uncertainty.png")
        manifest.append(
            {
                "view": image_path.stem,
                "shape": [height, width],
                "range_median": float(np.median(range_m)),
                "range_p05": float(np.percentile(range_m, 5.0)),
                "range_p95": float(np.percentile(range_m, 95.0)),
                "relative_error_median": float(np.median(relative_error)),
                "log_sigma_median": float(np.median(log_sigma)),
            }
        )
        print(f"[unidepth] {image_path.stem}: median range {manifest[-1]['range_median']:.2f} m")
    (args.out / "manifest.json").write_text(
        json.dumps(
            {
                "model": f"lpiccinelli/{args.model}",
                "source": str(args.views),
                "camera": "known 90-degree pinhole intrinsics per perspective crop",
                "uncertainty_field": UNCERTAINTY_FIELD,
                "uncertainty_anchor": "median pixel pinned to reference_log_sigma, ordering preserved",
                "reference_log_sigma": args.reference_log_sigma,
                "views": manifest,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
