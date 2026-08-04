"""Cut rectilinear label and confidence maps out of a fused panorama semantics file.

``build_fishnet_surface.py`` reads per-view ``h+00_YYY_labels.npy`` and
``h+00_YYY_confidence.npy`` written by the dense pass in
``semantic_twin/vision/panorama.py``.  Those per-view arrays live wherever the pass
ran, and only Korenmarkt and Milan carry them in this repository.  What every
segmented panorama does carry is the product the same pass fused out of them,
``semantics/panorama_semantics.npz``, holding the dense Mapillary Vistas entity
map and the confidence of the label that won each equirectangular pixel.

``fuse_layers`` samples each source view with nearest neighbour and keeps the
winning view's own confidence, so the fused map is a resample of exactly those
per-view arrays rather than a second estimate of them.  This cuts it back into
the crop geometry the fishnet expects, using the same ``pano_geometry`` rays the
segmenter sampled with and the ray caster casts along, so the three stages
cannot drift apart.

Both layers are sampled nearest.  A class id cannot be interpolated, and the
confidence is the score of the label that won, so a bilinear blend of two
classes' scores is the score of neither.  The RGB crop is bilinear, since it is
an image and is only read for its dimensions downstream.

``--equirect-width`` resamples the fused map before cutting.  It exists to
measure what the round trip costs: Korenmarkt carries both the native crops and
an 8192 pixel wide fused map, and narrowing that map to the 4096 pixels the
other sites carry reproduces their evidence resolution at a site where the
native answer is known.

Run from the ``semantic_twin`` directory::

    ../../../.venv/bin/python crop_fused_semantics.py \
        --semantics data/panoramas/prague_staromestske/pano_00_4CxfyuveHLZwX5MG/semantics \
        --panorama data/panoramas/prague_staromestske/pano_00_4CxfyuveHLZwX5MG/panorama_z5.jpg \
        --out outputs/prague_staromestske_fishnet_views/pano_00 --size 1536
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass

import numpy as np
from PIL import Image

from semantic_twin.pano_geometry import (
    PerspectiveView,
    directions_to_equirectangular,
    extract_perspective,
    perspective_directions,
)

Image.MAX_IMAGE_PIXELS = None


@dataclass(frozen=True)
class FusedSemanticCropConfig:
    semantics: pathlib.Path
    out: pathlib.Path
    panorama: pathlib.Path | None = None
    yaws: tuple[int, ...] = (0, 90, 180, 270)
    pitch: float = 0.0
    fov_deg: float = 90.0
    size: int = 1536
    equirect_width: int | None = None


def resample_equirectangular(layer: np.ndarray, width: int) -> np.ndarray:
    """Nearest-neighbour resample of one equirectangular layer to a new width.

    The height follows the width at the two to one aspect an equirectangular
    map has to keep.  Nearest is the only correct choice for a label map and is
    used on the confidence too, so a pixel's confidence stays the confidence of
    the class that is written next to it.
    """
    if width < 2 or width % 2:
        raise ValueError("an equirectangular width must be even and at least two")
    height = width // 2
    rows = np.minimum((np.arange(height) + 0.5) * layer.shape[0] / height, layer.shape[0] - 1).astype(np.intp)
    columns = np.minimum((np.arange(width) + 0.5) * layer.shape[1] / width, layer.shape[1] - 1).astype(np.intp)
    return layer[np.ix_(rows, columns)]


def sample_view(layer: np.ndarray, view: PerspectiveView, size: int) -> np.ndarray:
    """Nearest-neighbour sample of one equirectangular layer into a crop."""
    directions = perspective_directions(view, size, size)
    u, v = directions_to_equirectangular(directions)
    columns = np.rint(u * layer.shape[1] - 0.5).astype(np.intp) % layer.shape[1]
    rows = np.clip(np.rint(v * layer.shape[0] - 0.5), 0.0, layer.shape[0] - 1.0).astype(np.intp)
    return layer[rows, columns]


def crop_fused_semantics(config: FusedSemanticCropConfig) -> None:
    config.out.mkdir(parents=True, exist_ok=True)
    document = json.loads((config.semantics / "semantics.json").read_text())
    with np.load(config.semantics / "panorama_semantics.npz") as fused:
        entity = np.asarray(fused["entity"])
        confidence = np.asarray(fused["confidence"])
    source_shape = list(entity.shape)
    if config.equirect_width is not None:
        entity = resample_equirectangular(entity, config.equirect_width)
        confidence = resample_equirectangular(confidence, config.equirect_width)

    panorama = None
    if config.panorama is not None:
        panorama = Image.open(config.panorama)

    views = []
    for yaw in config.yaws:
        name = f"h{config.pitch:+03.0f}_{yaw:03d}"
        view = PerspectiveView(name, float(yaw), config.pitch, config.fov_deg)
        labels = sample_view(entity, view, config.size)
        scores = sample_view(confidence, view, config.size)
        np.save(config.out / f"{name}_labels.npy", labels.astype(np.uint16))
        np.save(config.out / f"{name}_confidence.npy", scores.astype(np.float16))
        if panorama is not None:
            extract_perspective(panorama, view, width=config.size, height=config.size).save(
                config.out / f"{name}.jpg", quality=95
            )
        views.append({"view": name, "shape": [config.size, config.size]})
        print(f"[crop] {name}: {config.size} x {config.size}", flush=True)
    if panorama is not None:
        panorama.close()

    (config.out / "crop_settings.json").write_text(
        json.dumps(
            {
                "source": "fused equirectangular semantics, resampled back into the inference crop geometry",
                "semantics": str(config.semantics),
                "panorama": str(config.panorama) if config.panorama else None,
                "model": document.get("model"),
                "checkpoint": document.get("checkpoint"),
                "backend": document.get("backend"),
                "native_view_size": document.get("view_size"),
                "native_inference_size": document.get("inference_size"),
                "fused_shape": source_shape,
                "cut_from_shape": list(entity.shape),
                "equirect_width": config.equirect_width,
                "size": config.size,
                "fov_deg": config.fov_deg,
                "pitch": config.pitch,
                "label_sampling": "nearest",
                "confidence_sampling": "nearest",
                "rgb_sampling": "bilinear",
                "views": views,
            },
            indent=2,
        )
    )
