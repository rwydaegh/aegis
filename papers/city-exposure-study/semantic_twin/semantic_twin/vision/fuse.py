"""Many views into one sphere.

Every backend answers per rectilinear view, and a pixel of the output sphere is
usually visible in more than one of them. :func:`fuse_layers` resolves that
overlap by confidence times angular distance from the view centre, so a label
seen at the edge of one crop loses to the same label seen at the centre of its
neighbour.

Several co-registered layers are fused in one geometric pass on purpose. The
projection, the footprint spans and the direction block depend only on the view
and not on what is painted in it, so four concept layers cost one traversal
rather than four.

``require_nonzero`` is the switch between the two kinds of layer this study
has. A dense partition treats label zero as a real class and any valid sample
beats no sample. A sparse layer treats zero as "nothing here", so only a
positive score can claim a pixel.
"""

from __future__ import annotations

import numpy as np

from ..pano_geometry import PerspectiveView, view_pixel_coordinates
from .views import _view_footprint


def fuse_layers(
    views: list[PerspectiveView],
    layers: dict[str, list[tuple[np.ndarray, np.ndarray]]],
    *,
    width: int,
    height: int,
    row_chunk: int = 128,
    require_nonzero: bool = False,
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Fuse several co-registered layers over the sphere in one geometric pass.

    Overlap is resolved by confidence times angular distance from the view
    centre, independently per layer. Every view is bounded to its
    equirectangular footprint first, so a view is only evaluated on the rows and
    columns it can actually reach. That cull is what took one panorama from
    roughly 73 s to 17 s at the default 8192 pixel output width.

    Fusing the layers together rather than one call each shares the expensive
    half of the work. The projection, the footprint spans and the direction
    block depend only on the view, not on what is painted in it, so the four
    concept layers cost one traversal instead of four.

    ``require_nonzero`` switches from a dense partition, where label zero is a
    real class and any valid sample beats no sample, to a sparse layer where
    zero means "nothing here" and only a positive score can claim a pixel.
    """
    if not layers:
        raise ValueError("fuse_layers needs at least one layer")
    counts = {len(items) for items in layers.values()} | {len(views)}
    if len(counts) != 1:
        raise ValueError("every layer must supply one raster pair per view")
    shapes = [next(iter(layers.values()))[index][0].shape for index in range(len(views))]
    for name, per_view in layers.items():
        for index, (raster, confidence) in enumerate(per_view):
            if raster.shape != shapes[index] or confidence.shape != shapes[index]:
                raise ValueError(f"layer {name} disagrees with the others on the raster shape of view {index}")
    outputs = {
        name: (
            np.zeros((height, width), dtype=np.uint16),
            np.zeros((height, width), dtype=np.float16),
            np.full((height, width), 0.0 if require_nonzero else -np.inf, dtype=np.float32),
        )
        for name in layers
    }
    footprints = [
        _view_footprint(view, shape[1], shape[0], width, height) for view, shape in zip(views, shapes, strict=True)
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
        for index, (view, footprint, shape) in enumerate(zip(views, footprints, shapes, strict=True)):
            for x0, x1 in footprint.column_spans(pitch_low, pitch_high):
                block = directions[:, x0:x1]
                px, py, valid = view_pixel_coordinates(block, view, shape[1], shape[0])
                if not np.any(valid):
                    continue
                flat = py.astype(np.intp) * shape[1] + px
                angular = np.clip(block @ footprint.centre, 0.0, 1.0) ** 4
                for name, per_view in layers.items():
                    labels, confidence = per_view[index]
                    flat_labels = labels.reshape(-1)[flat]
                    sampled_confidence = confidence.reshape(-1)[flat].astype(np.float32)
                    score = sampled_confidence * angular
                    labels_out, confidence_out, best_out = outputs[name]
                    best = best_out[y0:y1, x0:x1]
                    take = valid & (score > best)
                    if require_nonzero:
                        take &= flat_labels > 0
                    best[take] = score[take]
                    labels_out[y0:y1, x0:x1][take] = flat_labels[take]
                    confidence_out[y0:y1, x0:x1][take] = sampled_confidence[take].astype(np.float16)
    return {name: (labels, confidence) for name, (labels, confidence, _best) in outputs.items()}


def fuse_predictions(
    predictions: list[tuple[PerspectiveView, np.ndarray, np.ndarray]],
    *,
    width: int,
    height: int,
    row_chunk: int = 128,
    require_nonzero: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    """Fuse one layer over the sphere. See :func:`fuse_layers`."""
    fused = fuse_layers(
        [view for view, _labels, _confidence in predictions],
        {"layer": [(labels, confidence) for _view, labels, confidence in predictions]},
        width=width,
        height=height,
        row_chunk=row_chunk,
        require_nonzero=require_nonzero,
    )
    return fused["layer"]


def palette(n: int) -> np.ndarray:
    """Stable high-contrast colours, with class zero left black."""
    rng = np.random.default_rng(0xAE615)
    colours = rng.integers(32, 256, size=(n, 3), dtype=np.uint8)
    if n:
        colours[0] = 0
    return colours
