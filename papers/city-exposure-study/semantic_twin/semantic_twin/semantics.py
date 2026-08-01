"""Dense panorama semantics with interchangeable segmentation backends.

The built-in baseline is Mask2Former trained on Mapillary Vistas. It supplies a
dense street-scene map, including small infrastructure classes. SAM 3.1 concept
masks can be added as a second backend without changing panorama geometry or mesh
projection. Entity labels and RF-material hints are kept as separate layers.

Run after :mod:`semantic_twin.panorama`::

    ../../../.venv/bin/python -m semantic_twin.semantics \
        --panorama data/panoramas/korenmarkt/panorama_z5.jpg \
        --out data/panoramas/korenmarkt/semantics
"""

from __future__ import annotations

import argparse
import json
import pathlib
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates

from .pano_geometry import (
    PerspectiveView,
    directions_to_equirectangular,
    inference_views,
    perspective_directions,
    view_pixel_coordinates,
)

MODEL = "facebook/mask2former-swin-large-mapillary-vistas-semantic"

# The processor saved with the Mapillary Vistas checkpoint carries
# ``{"height": 384, "width": 384}`` with ``do_resize`` on, so an unmodified
# processor downsamples every crop to 384 x 384 and returns 96 x 96 mask logits
# no matter how large the crop was.  The inference resolution is therefore set
# explicitly here instead of being inherited from the checkpoint.  Measured on
# one real Korenmarkt crop on an RTX A6000, distinct Vistas classes recovered
# against wall-clock cost per crop:
#
#     384 -> 96 x 96 logits,   15 classes,   97 ms
#    1024 -> 256 x 256,        26 classes,  348 ms
#    1536 -> 384 x 384,        32 classes,  666 ms
#    2048 -> 512 x 512,        31 classes, 1240 ms, 97.0 percent agreement with 1536
#
# 1536 is where the small mmWave clutter appears: Pole, Street Light, Utility
# Pole, Traffic Light, Traffic Sign front and back, Bike Rack, Mailbox, Curb,
# On Rails, Parking and Other Rider are only recovered there.  2048 costs 1.9x
# more and 5.3 GiB of device memory for no additional class, so the default
# stops at 1536.  Crops are extracted at the same size so the model sees native
# pixels: on a 1024 crop, upsampling to 1536 recovered no extra class.
DEFAULT_INFERENCE_SIZE = 1536
DEFAULT_VIEW_SIZE = 1536


@dataclass(frozen=True)
class ViewPrediction:
    view: PerspectiveView
    image_file: str
    labels_file: str
    confidence_file: str


MATERIAL_HINTS = {
    "sky": "none",
    "person": "human_tissue",
    "bicyclist": "human_tissue",
    "motorcyclist": "human_tissue",
    "bird": "animal_tissue",
    "ground animal": "animal_tissue",
    "vegetation": "vegetation",
    "water": "water",
    "road": "asphalt",
    "lane marking - general": "road_paint",
    "lane marking - crosswalk": "road_paint",
    "sidewalk": "concrete",
    "curb": "concrete",
    "terrain": "soil",
    "sand": "soil",
    "snow": "snow",
    "building": "unknown_building",
    "wall": "unknown_wall",
    "bridge": "concrete",
    "tunnel": "concrete",
    "pole": "metal",
    "utility pole": "metal",
    "traffic light": "metal",
    "traffic sign (front)": "metal",
    "traffic sign (back)": "metal",
    "street light": "metal",
    "fire hydrant": "metal",
    "bench": "unknown_furniture",
    "bike rack": "metal",
    "bollard": "metal",
    "trash can": "metal",
    "car": "vehicle_composite",
    "truck": "vehicle_composite",
    "bus": "vehicle_composite",
    "motorcycle": "vehicle_composite",
    "bicycle": "vehicle_composite",
    "boat": "vehicle_composite",
    "caravan": "vehicle_composite",
    "trailer": "vehicle_composite",
}


def material_hints(id2label: dict[int, str]) -> tuple[np.ndarray, list[str]]:
    """Map an entity vocabulary to a compact, explicitly provisional RF layer."""
    names = ["unknown"]
    per_entity = np.zeros(max(id2label, default=-1) + 1, dtype=np.uint16)
    for class_id, label in id2label.items():
        hint = MATERIAL_HINTS.get(label.casefold(), "unknown")
        if hint not in names:
            names.append(hint)
        per_entity[class_id] = names.index(hint)
    return per_entity, names


class Mask2FormerBackend:
    """CPU/GPU semantic baseline with the Mapillary Vistas vocabulary."""

    def __init__(
        self,
        model_name: str = MODEL,
        device: str = "auto",
        *,
        inference_size: int = DEFAULT_INFERENCE_SIZE,
    ) -> None:
        try:
            import torch
            from transformers import AutoImageProcessor, Mask2FormerForUniversalSegmentation
        except ImportError as exc:
            raise SystemExit("install optional dependencies with `pip install -r requirements-semantics.txt`") from exc

        if inference_size < 32:
            raise ValueError("inference_size must be at least 32 pixels")
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.torch = torch
        self.device = device
        self.inference_size = int(inference_size)
        self.processor = AutoImageProcessor.from_pretrained(model_name)
        self.processor_saved_size = dict(getattr(self.processor, "size", {}) or {})
        self.model = Mask2FormerForUniversalSegmentation.from_pretrained(model_name, use_safetensors=True).to(device)
        self.model.eval()
        self.id2label = {int(k): str(v) for k, v in self.model.config.id2label.items()}

    def predict(self, image: Image.Image) -> tuple[np.ndarray, np.ndarray]:
        import torch.nn.functional as functional

        inputs = self.processor(
            images=image,
            return_tensors="pt",
            size={"height": self.inference_size, "width": self.inference_size},
        )
        inputs = {name: tensor.to(self.device) for name, tensor in inputs.items()}
        with self.torch.inference_mode():
            outputs = self.model(**inputs)
        class_probability = outputs.class_queries_logits.softmax(dim=-1)[..., :-1]
        mask_probability = outputs.masks_queries_logits.sigmoid()
        mask_probability = functional.interpolate(
            mask_probability,
            size=image.size[::-1],
            mode="bilinear",
            align_corners=False,
        )
        semantic_probability = self.torch.einsum("bqc,bqhw->bchw", class_probability, mask_probability)[0]
        scores, labels = semantic_probability.max(dim=0)
        return (
            labels.detach().cpu().numpy().astype(np.uint16),
            scores.detach().cpu().numpy().astype(np.float16),
        )


def perspective_crop(panorama_rgb: np.ndarray, view: PerspectiveView, *, width: int, height: int) -> Image.Image:
    """Sample one rectilinear view from an already decoded panorama array.

    This is :func:`pano_geometry.extract_perspective` with the decode hoisted
    out. That function re-materialises the panorama on every call, which on the
    16384 x 8192 Korenmarkt image is 403 MB per view: 1.54 s per view against
    0.61 s here, so 40 s against 16 s over the 26 inference views.
    """
    if panorama_rgb.ndim != 3 or panorama_rgb.shape[2] != 3:
        raise ValueError("panorama_rgb must be a decoded (rows, columns, 3) RGB array")
    directions = perspective_directions(view, width, height)
    u, v = directions_to_equirectangular(directions)
    xs = u * panorama_rgb.shape[1] - 0.5
    ys = np.clip(v * panorama_rgb.shape[0] - 0.5, 0.0, panorama_rgb.shape[0] - 1.0)
    coords = np.stack([ys, xs], axis=0)
    channels = [map_coordinates(panorama_rgb[:, :, c], coords, order=1, mode="grid-wrap") for c in range(3)]
    return Image.fromarray(np.stack(channels, axis=2).astype(np.uint8), "RGB")


@dataclass(frozen=True)
class _ViewFootprint:
    """Where on the equirectangular output one perspective view can land.

    The frustum maps to a geodesically convex region, so its latitude extent and
    its longitude extent inside any latitude band are both attained on its
    border. Sampling the border once therefore bounds the region exactly enough
    to skip the output rows and columns a view cannot reach. A view that
    strictly contains a pole wraps every longitude, and is not culled in yaw.
    """

    centre: np.ndarray
    centre_yaw_deg: float
    yaw_offset_deg: np.ndarray
    pitch_deg: np.ndarray
    minimum_pitch_deg: float
    maximum_pitch_deg: float
    contains_pole: bool
    margin_deg: float
    width: int

    def column_spans(self, pitch_low_deg: float, pitch_high_deg: float) -> tuple[tuple[int, int], ...]:
        """Output column ranges this view can touch inside one latitude band."""
        if pitch_high_deg < self.minimum_pitch_deg - self.margin_deg:
            return ()
        if pitch_low_deg > self.maximum_pitch_deg + self.margin_deg:
            return ()
        if self.contains_pole:
            return ((0, self.width),)
        in_band = (self.pitch_deg >= pitch_low_deg - self.margin_deg) & (
            self.pitch_deg <= pitch_high_deg + self.margin_deg
        )
        if not np.any(in_band):
            return ()
        offsets = self.yaw_offset_deg[in_band]
        return _column_spans(
            self.centre_yaw_deg,
            float(offsets.min()) - self.margin_deg,
            float(offsets.max()) + self.margin_deg,
            self.width,
        )


def _column_spans(centre_yaw_deg: float, low_offset_deg: float, high_offset_deg: float, width: int) -> tuple:
    if high_offset_deg - low_offset_deg >= 360.0:
        return ((0, width),)
    start = int(np.floor(((centre_yaw_deg + low_offset_deg) / 360.0 + 0.5) * width - 0.5))
    stop = int(np.ceil(((centre_yaw_deg + high_offset_deg) / 360.0 + 0.5) * width - 0.5)) + 1
    span = stop - start
    if span >= width:
        return ((0, width),)
    start %= width
    if start + span <= width:
        return ((start, start + span),)
    return ((start, width), (0, start + span - width))


def _view_footprint(
    view: PerspectiveView,
    view_width: int,
    view_height: int,
    output_width: int,
    output_height: int,
    *,
    samples: int = 256,
) -> _ViewFootprint:
    grid = perspective_directions(view, samples, samples)
    border = np.concatenate((grid[0], grid[-1], grid[1:-1, 0], grid[1:-1, -1]))
    yaw_deg = np.degrees(np.arctan2(border[:, 0], border[:, 1]))
    pitch_deg = np.degrees(np.arcsin(np.clip(border[:, 2], -1.0, 1.0)))
    centre_yaw_deg = float(np.degrees(np.arctan2(*perspective_directions(view, 1, 1)[0, 0, :2])))
    offsets = (yaw_deg - centre_yaw_deg + 180.0) % 360.0 - 180.0
    # The border grid samples pixel centres, so it sits half a cell inside the
    # true frustum edge. One whole cell, plus one output pixel, covers that.
    margin_deg = view.fov_deg / samples + max(360.0 / output_width, 180.0 / output_height)
    north = _contains_pole(view, view_width, view_height, 1.0)
    south = _contains_pole(view, view_width, view_height, -1.0)
    return _ViewFootprint(
        centre=perspective_directions(view, 1, 1)[0, 0],
        centre_yaw_deg=centre_yaw_deg,
        yaw_offset_deg=offsets,
        pitch_deg=pitch_deg,
        minimum_pitch_deg=-90.0 if south else float(pitch_deg.min()),
        maximum_pitch_deg=90.0 if north else float(pitch_deg.max()),
        contains_pole=north or south,
        margin_deg=margin_deg,
        width=output_width,
    )


def _contains_pole(view: PerspectiveView, view_width: int, view_height: int, sign: float) -> bool:
    pole = np.array([[[0.0, 0.0, sign]]])
    px, py, valid = view_pixel_coordinates(pole, view, view_width, view_height)
    if not bool(valid[0, 0]):
        return False
    # A pole sitting exactly on the frustum edge, as it does for a 90 degree
    # view centred at 45 degrees elevation, does not sweep every longitude.
    return 0 < int(px[0, 0]) < view_width - 1 and 0 < int(py[0, 0]) < view_height - 1


def fuse_predictions(
    predictions: list[tuple[PerspectiveView, np.ndarray, np.ndarray]],
    *,
    width: int,
    height: int,
    row_chunk: int = 128,
) -> tuple[np.ndarray, np.ndarray]:
    """Fuse overlap by confidence and angular distance from each view centre.

    Every view is bounded to its equirectangular footprint first, so a view is
    only evaluated on the rows and columns it can actually reach. The previous
    pass ran all 26 views over all output pixels, which is roughly 73 s for one
    panorama at the default 8192 pixel output width.
    """
    labels_out = np.zeros((height, width), dtype=np.uint16)
    confidence_out = np.zeros((height, width), dtype=np.float16)
    best_out = np.full((height, width), -np.inf, dtype=np.float32)
    footprints = [
        _view_footprint(view, labels.shape[1], labels.shape[0], width, height)
        for view, labels, _confidence in predictions
    ]

    yaw = ((np.arange(width) + 0.5) / width - 0.5) * 2.0 * np.pi
    sin_yaw, cos_yaw = np.sin(yaw), np.cos(yaw)
    for y0 in range(0, height, row_chunk):
        y1 = min(y0 + row_chunk, height)
        pitch = (0.5 - (np.arange(y0, y1) + 0.5) / height) * np.pi
        directions = np.empty((y1 - y0, width, 3), dtype=np.float64)
        directions[..., 0] = sin_yaw[None, :] * np.cos(pitch)[:, None]
        directions[..., 1] = cos_yaw[None, :] * np.cos(pitch)[:, None]
        directions[..., 2] = np.sin(pitch)[:, None]
        pitch_low = float(np.degrees(pitch[-1]))
        pitch_high = float(np.degrees(pitch[0]))
        for (view, labels, confidence), footprint in zip(predictions, footprints):
            flat_labels = labels.reshape(-1)
            flat_confidence = confidence.reshape(-1)
            for x0, x1 in footprint.column_spans(pitch_low, pitch_high):
                block = directions[:, x0:x1]
                px, py, valid = view_pixel_coordinates(block, view, labels.shape[1], labels.shape[0])
                if not np.any(valid):
                    continue
                flat = py.astype(np.intp) * labels.shape[1] + px
                sampled_confidence = flat_confidence[flat].astype(np.float32)
                score = sampled_confidence * np.clip(block @ footprint.centre, 0.0, 1.0) ** 4
                best = best_out[y0:y1, x0:x1]
                take = valid & (score > best)
                best[take] = score[take]
                labels_out[y0:y1, x0:x1][take] = flat_labels[flat][take]
                confidence_out[y0:y1, x0:x1][take] = sampled_confidence[take].astype(np.float16)
    return labels_out, confidence_out


def palette(n: int) -> np.ndarray:
    """Stable high-contrast colours, with class zero left black."""
    rng = np.random.default_rng(0xAE615)
    colours = rng.integers(32, 256, size=(n, 3), dtype=np.uint8)
    if n:
        colours[0] = 0
    return colours


def predict_views(
    panorama: Image.Image,
    backend: Any,
    views_dir: pathlib.Path,
    *,
    view_size: int,
    force: bool = False,
) -> tuple[list[tuple[PerspectiveView, np.ndarray, np.ndarray]], list[ViewPrediction]]:
    """Segment every inference view, decoding the panorama exactly once."""
    panorama_rgb = np.asarray(panorama.convert("RGB"))
    predictions: list[tuple[PerspectiveView, np.ndarray, np.ndarray]] = []
    manifest: list[ViewPrediction] = []
    for view in inference_views():
        image_path = views_dir / f"{view.name}.jpg"
        labels_path = views_dir / f"{view.name}_labels.npy"
        confidence_path = views_dir / f"{view.name}_confidence.npy"
        if not force and labels_path.exists() and confidence_path.exists():
            labels = np.load(labels_path)
            confidence = np.load(confidence_path)
        else:
            image = perspective_crop(panorama_rgb, view, width=view_size, height=view_size)
            image.save(image_path, quality=95)
            labels, confidence = backend.predict(image)
            np.save(labels_path, labels)
            np.save(confidence_path, confidence)
        predictions.append((view, labels, confidence))
        manifest.append(ViewPrediction(view, str(image_path), str(labels_path), str(confidence_path)))
        print(f"[semantic] {view.name}")
    return predictions, manifest


def run(args: argparse.Namespace) -> None:
    out = args.out
    views_dir = out / "views"
    views_dir.mkdir(parents=True, exist_ok=True)
    backend = Mask2FormerBackend(args.model, args.device, inference_size=args.inference_size)

    with Image.open(args.panorama) as panorama:
        predictions, manifest = predict_views(
            panorama,
            backend,
            views_dir,
            view_size=args.view_size,
            force=args.force,
        )

    output_width = args.output_width
    output_height = output_width // 2
    labels, confidence = fuse_predictions(predictions, width=output_width, height=output_height)
    entity_to_material, material_names = material_hints(backend.id2label)
    material = entity_to_material[labels]
    np.savez_compressed(
        out / "panorama_semantics.npz",
        entity=labels,
        material_hint=material,
        confidence=confidence,
    )
    colours = palette(max(backend.id2label, default=0) + 1)
    Image.fromarray(colours[labels], "RGB").save(out / "panorama_entities.png")
    material_colours = palette(len(material_names))
    Image.fromarray(material_colours[material], "RGB").save(out / "panorama_material_hints.png")
    document: dict[str, Any] = {
        "backend": "mask2former",
        "model": args.model,
        "entity_id2label": backend.id2label,
        "material_id2label": dict(enumerate(material_names)),
        "material_status": "provisional hints, refine with concept/material backend",
        "view_size": args.view_size,
        "inference_size": backend.inference_size,
        "processor_saved_size": backend.processor_saved_size,
        "inference_size_status": "set explicitly, not inherited from the checkpoint processor",
        "shape": [output_height, output_width],
        "views": [asdict(record) for record in manifest],
    }
    (out / "semantics.json").write_text(json.dumps(document, indent=2))
    print(f"[semantic] -> {out / 'panorama_semantics.npz'}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panorama", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--view-size", type=int, default=DEFAULT_VIEW_SIZE)
    parser.add_argument(
        "--inference-size",
        type=int,
        default=DEFAULT_INFERENCE_SIZE,
        help="Square input the segmenter actually sees, instead of the checkpoint processor's 384.",
    )
    parser.add_argument("--output-width", type=int, default=8192)
    parser.add_argument("--force", action="store_true")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
