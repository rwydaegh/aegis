"""Optional SAM 3 concept/instance pass over cached panorama views.

This is the high-detail backend for small clutter and RF material concepts. It is
kept separate from the CPU Mapillary baseline because SAM 3 requires a CUDA GPU
and gated Hugging Face weights. Install Meta's ``sam3`` package in its documented
environment, authenticate with Hugging Face, then run::

    python -m semantic_twin.sam3_concepts \
      --views data/panoramas/korenmarkt/semantics/views \
      --concepts config/semantic_concepts.json \
      --out data/panoramas/korenmarkt/sam3

Masks are bit-packed per view. Surface concepts can refine the RF-material map;
object concepts remain independent instances for proxy fitting or reconstruction.
"""

from __future__ import annotations

import argparse
from contextlib import nullcontext
import json
import pathlib

import numpy as np
from PIL import Image

from .concepts import ConceptCatalog


def _numpy(value):
    if hasattr(value, "detach"):
        value = value.detach().float().cpu().numpy()
    return np.asarray(value)


def _inference_context(torch):
    """Match Meta's CUDA inference path while keeping CPU imports testable."""
    if torch.cuda.is_available():
        return torch.autocast("cuda", dtype=torch.bfloat16)
    return nullcontext()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--views", type=pathlib.Path, required=True)
    parser.add_argument("--concepts", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--threshold", type=float, default=0.35)
    parser.add_argument("--limit-views", type=int)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    try:
        import torch
        from sam3.model.sam3_image_processor import Sam3Processor
        from sam3.model_builder import build_sam3_image_model
    except ImportError as exc:
        raise SystemExit(
            "SAM 3 is not installed. Follow https://github.com/facebookresearch/sam3 "
            "in a CUDA 12.6+ environment and authenticate with Hugging Face."
        ) from exc
    if not torch.cuda.is_available():
        raise SystemExit("SAM 3 requires a CUDA GPU; no CUDA device is visible")

    catalog = ConceptCatalog.load(args.concepts)
    concepts = [(concept.kind, concept.prompt) for concept in catalog.concepts]
    args.out.mkdir(parents=True, exist_ok=True)
    with _inference_context(torch):
        model = build_sam3_image_model()
    processor = Sam3Processor(model, confidence_threshold=args.threshold)

    image_paths = [path for path in sorted(args.views.glob("*.jpg")) if not path.stem.endswith("_key")]
    if args.limit_views is not None:
        if args.limit_views < 1:
            raise SystemExit("--limit-views must be positive")
        image_paths = image_paths[: args.limit_views]
    for image_path in image_paths:
        destination = args.out / f"{image_path.stem}.npz"
        if destination.exists() and not args.force:
            print(f"[sam3] {image_path.name}: cached")
            continue
        with Image.open(image_path) as source:
            image = source.convert("RGB")
        with _inference_context(torch):
            state = processor.set_image(image)
            masks, scores, boxes, labels, kinds = [], [], [], [], []
            for kind, prompt in concepts:
                output = processor.set_text_prompt(state=state, prompt=prompt)
                concept_masks = _numpy(output["masks"]).astype(bool)
                concept_scores = _numpy(output["scores"]).reshape(-1)
                concept_boxes = _numpy(output["boxes"]).reshape(-1, 4)
                keep = concept_scores >= args.threshold
                masks.extend(concept_masks[keep])
                scores.extend(concept_scores[keep].tolist())
                boxes.extend(concept_boxes[keep].tolist())
                labels.extend([prompt] * int(keep.sum()))
                kinds.extend([kind] * int(keep.sum()))
        if masks:
            mask_array = np.stack(masks).astype(np.uint8)
            packed = np.packbits(mask_array.reshape(len(masks), -1), axis=1)
        else:
            packed = np.empty((0, 0), dtype=np.uint8)
        np.savez_compressed(
            destination,
            packed_masks=packed,
            mask_shape=np.asarray([image.height, image.width]),
            scores=np.asarray(scores, dtype=np.float32),
            boxes=np.asarray(boxes, dtype=np.float32).reshape(-1, 4),
            labels=np.asarray(labels),
            kinds=np.asarray(kinds),
        )
        print(f"[sam3] {image_path.name}: {len(masks)} instances")

    manifest = {
        "model": "facebook/sam3",
        "model_role": "open-vocabulary promptable concept segmentation for independent panorama views",
        "sam3_1_note": "SAM 3.1 Object Multiplex is a video tracker and is not applied to discontinuous perspective views.",
        "threshold": args.threshold,
        "taxonomy": catalog.taxonomy,
        "concepts": [concept.prompt for concept in catalog.concepts],
    }
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
