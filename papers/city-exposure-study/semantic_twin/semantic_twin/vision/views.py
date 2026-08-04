"""How a panorama becomes rectilinear views, and where each one lands back.

Segmentation models are trained on ordinary photographs, so the equirectangular
sphere is never shown to one directly. It is cut into 26 overlapping 90 degree
crops by :func:`~semantic_twin.pano_geometry.inference_views`, each model runs
per crop, and the answers are stitched back onto the sphere afterwards.

The stitching is what makes this module more than a crop. Each view can only
reach part of the output, and :class:`_ViewFootprint` bounds that part exactly
enough to skip the rows and columns it cannot touch. That cull is what took one
panorama from roughly 73 s to 17 s at the default 8192 pixel output width, and
:mod:`~semantic_twin.vision.fuse` is its only consumer.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates

from ..pano_geometry import (
    PerspectiveView,
    directions_to_equirectangular,
    perspective_directions,
    view_pixel_coordinates,
)

# The processor saved with the Mapillary Vistas checkpoint carries
# ``{"height": 384, "width": 384}`` with ``do_resize`` on, so an unmodified
# processor downsamples every crop to 384 x 384. The crop size is therefore set
# explicitly rather than inherited from the checkpoint. See
# :mod:`~semantic_twin.vision.dense` for the measurements behind 1536.
DEFAULT_VIEW_SIZE = 1536


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


def present_classes(labels: np.ndarray, id2label: dict[int, str], *, minimum_pixels: int) -> frozenset[str]:
    """Dense classes with enough area in one view to be taken as present."""
    values, counts = np.unique(labels, return_counts=True)
    return frozenset(
        id2label[int(value)]
        for value, count in zip(values, counts, strict=True)
        if count >= minimum_pixels and int(value) in id2label
    )
