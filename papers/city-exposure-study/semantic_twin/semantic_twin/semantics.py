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

from .pano_geometry import (
    PerspectiveView,
    extract_perspective,
    inference_views,
    perspective_directions,
    view_pixel_coordinates,
)

MODEL = "facebook/mask2former-swin-large-mapillary-vistas-semantic"


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

    def __init__(self, model_name: str = MODEL, device: str = "auto") -> None:
        try:
            import torch
            from transformers import AutoImageProcessor, Mask2FormerForUniversalSegmentation
        except ImportError as exc:
            raise SystemExit("install optional dependencies with `pip install -r requirements-semantics.txt`") from exc

        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.torch = torch
        self.device = device
        self.processor = AutoImageProcessor.from_pretrained(model_name)
        self.model = Mask2FormerForUniversalSegmentation.from_pretrained(model_name, use_safetensors=True).to(device)
        self.model.eval()
        self.id2label = {int(k): str(v) for k, v in self.model.config.id2label.items()}

    def predict(self, image: Image.Image) -> tuple[np.ndarray, np.ndarray]:
        import torch.nn.functional as functional

        inputs = self.processor(images=image, return_tensors="pt")
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


def fuse_predictions(
    predictions: list[tuple[PerspectiveView, np.ndarray, np.ndarray]],
    *,
    width: int,
    height: int,
    row_chunk: int = 128,
) -> tuple[np.ndarray, np.ndarray]:
    """Fuse overlap by confidence and angular distance from each view centre."""
    labels_out = np.zeros((height, width), dtype=np.uint16)
    confidence_out = np.zeros((height, width), dtype=np.float16)
    best_out = np.full((height, width), -np.inf, dtype=np.float32)

    yaw = ((np.arange(width) + 0.5) / width - 0.5) * 2.0 * np.pi
    for y0 in range(0, height, row_chunk):
        y1 = min(y0 + row_chunk, height)
        pitch = (0.5 - (np.arange(y0, y1) + 0.5) / height) * np.pi
        yy, pp = np.meshgrid(yaw, pitch)
        cp = np.cos(pp)
        directions = np.stack([np.sin(yy) * cp, np.cos(yy) * cp, np.sin(pp)], axis=2)
        best = best_out[y0:y1]
        for view, labels, confidence in predictions:
            px, py, valid = view_pixel_coordinates(directions, view, labels.shape[1], labels.shape[0])
            sampled_conf = np.zeros_like(best)
            sampled_labels = np.zeros_like(labels_out[y0:y1])
            sampled_conf[valid] = confidence[py[valid], px[valid]].astype(np.float32)
            sampled_labels[valid] = labels[py[valid], px[valid]]
            centre = perspective_directions(view, 1, 1)[0, 0]
            angular_weight = np.clip(directions @ centre, 0.0, 1.0) ** 4
            score = sampled_conf * angular_weight
            take = valid & (score > best)
            best[take] = score[take]
            labels_out[y0:y1][take] = sampled_labels[take]
            confidence_out[y0:y1][take] = sampled_conf[take].astype(np.float16)
    return labels_out, confidence_out


def palette(n: int) -> np.ndarray:
    """Stable high-contrast colours, with class zero left black."""
    rng = np.random.default_rng(0xAE615)
    colours = rng.integers(32, 256, size=(n, 3), dtype=np.uint8)
    if n:
        colours[0] = 0
    return colours


def run(args: argparse.Namespace) -> None:
    out = args.out
    views_dir = out / "views"
    views_dir.mkdir(parents=True, exist_ok=True)
    backend = Mask2FormerBackend(args.model, args.device)
    predictions: list[tuple[PerspectiveView, np.ndarray, np.ndarray]] = []
    manifest: list[ViewPrediction] = []

    with Image.open(args.panorama) as panorama:
        for view in inference_views():
            image_path = views_dir / f"{view.name}.jpg"
            labels_path = views_dir / f"{view.name}_labels.npy"
            confidence_path = views_dir / f"{view.name}_confidence.npy"
            if not args.force and labels_path.exists() and confidence_path.exists():
                labels = np.load(labels_path)
                confidence = np.load(confidence_path)
            else:
                image = extract_perspective(panorama, view, width=args.view_size, height=args.view_size)
                image.save(image_path, quality=95)
                labels, confidence = backend.predict(image)
                np.save(labels_path, labels)
                np.save(confidence_path, confidence)
            predictions.append((view, labels, confidence))
            manifest.append(ViewPrediction(view, str(image_path), str(labels_path), str(confidence_path)))
            print(f"[semantic] {view.name}")

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
    parser.add_argument("--view-size", type=int, default=1024)
    parser.add_argument("--output-width", type=int, default=8192)
    parser.add_argument("--force", action="store_true")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
