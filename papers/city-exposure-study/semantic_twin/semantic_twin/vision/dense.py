"""The dense segmentation backend: every pixel gets exactly one entity.

Mask2Former on Mapillary Vistas partitions a view completely into 65 street
scene classes, and at native resolution it is strong on the small infrastructure
that matters at millimetre wave: Pole, Street Light, Traffic Sign, Utility Pole,
Curb, Bike Rack. It owns the entity axis and nothing overwrites it.

What it cannot do is material. One ``Building`` class covers brick, render,
ashlar stone, glass curtain wall and metal cladding, which is why
:mod:`~semantic_twin.vision.prompted` exists and why
:mod:`~semantic_twin.vision.material` is a cascade rather than a vote.

The cache is typed. A mismatch recomputes, never warns and never partially
reuses, because an untyped cache is the reason every semantic output in this
repository once ran at the checkpoint processor's 384 without anyone noticing.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Any

import numpy as np
from PIL import Image

MODEL = "facebook/mask2former-swin-large-mapillary-vistas-semantic"
BRIDGE = "mask2former_mapillary_vistas"

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

# A dense class occupying fewer pixels than this in a view is not taken as
# evidence that the class is present, so it does not unlock its concept prompts.
# 256 pixels is 0.011 percent of a 1536 x 1536 crop, which is small enough to
# keep a distant drainpipe or a single overhead cable while still shutting off
# the facade prompts on a view that is entirely sky and pavement.
DEFAULT_GATE_MIN_PIXELS = 256


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
        self.model_name = model_name
        self.inference_size = int(inference_size)
        self.processor = AutoImageProcessor.from_pretrained(model_name)
        self.processor_saved_size = dict(getattr(self.processor, "size", {}) or {})
        self.model = Mask2FormerForUniversalSegmentation.from_pretrained(model_name, use_safetensors=True).to(device)
        self.model.eval()
        self.id2label = {int(k): str(v) for k, v in self.model.config.id2label.items()}
        # The Hub revision the weights actually came from. A model name alone
        # does not pin a checkpoint, because the same name can be re-uploaded.
        self.checkpoint_digest = getattr(self.model.config, "_commit_hash", None)

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


def file_digest(path: pathlib.Path, *, chunk: int = 1 << 22) -> str:
    """Content digest of a source file, streamed so a 22 MB panorama is cheap."""
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(chunk):
            sha.update(block)
    return sha.hexdigest()[:16]


def dense_cache_settings(backend: Any, view_size: int, panorama: pathlib.Path | None = None) -> dict[str, Any]:
    """Everything about the dense pass that makes its cached views comparable.

    The panorama digest is here because the view directory is named after the
    site, not after the capture. Two panoramas of the same square written into
    one tree would otherwise share crops and label maps.
    """
    return {
        "model": getattr(backend, "model_name", MODEL),
        "checkpoint": getattr(backend, "checkpoint_digest", None),
        "inference_size": int(getattr(backend, "inference_size", DEFAULT_INFERENCE_SIZE)),
        "view_size": int(view_size),
        "panorama": file_digest(panorama) if panorama is not None else None,
    }


def reusable_dense_cache(views_dir: pathlib.Path, settings: dict[str, Any]) -> bool:
    """Whether cached view labels were produced under exactly these settings.

    A mismatch recomputes. It never warns and never partially reuses, because
    an untyped cache is the reason every semantic output in this repository ran
    at the checkpoint processor's 384 without anyone noticing, and because a
    label map from another model or another resolution produces a plausible
    wrong number with no trace of where it came from.
    """
    stamp = views_dir / "cache_settings.json"
    if not stamp.exists():
        return False
    return json.loads(stamp.read_text()) == settings
