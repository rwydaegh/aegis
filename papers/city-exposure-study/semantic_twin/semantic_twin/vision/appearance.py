"""What a patch of texture looks like, in statistics that survive 14 texels.

The median triangle owns 14 texels, so there is no filter bank and no learned
embedding here. A descriptor with more degrees of freedom than that is fitting
the atlas rather than the wall.

Lab rather than raw RGB because the discriminations that survive at 19.6 cm are
lightness and hue, and Lab separates them. Facade texture baked from aerial
imagery is largely sky-lit and sits at strongly negative b*, so a space where
that shift is one coordinate rather than three matters.

:class:`MomentAccumulator` is streaming on purpose. Every statistic is a
function of running sums, a running minimum and a running maximum, so a group
can be fed in any number of chunks and end up bit identical to a single pass.
That matters twice over: an atlas is naturally processed patch by patch, and the
panorama control has to be computed on a 16384 by 8192 image that does not fit
in memory as float64. It also guarantees the control and the texture channel are
compared on literally the same descriptor rather than on two hand-copied
implementations of it.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .tiles import TileSurface, rasterize_uv_triangles, texel_geometry


_XYZ_FROM_LINEAR_RGB = np.array(
    [
        [0.4124564, 0.3575761, 0.1804375],
        [0.2126729, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041],
    ]
)
_D65_WHITE = np.array([0.95047, 1.0, 1.08883])
_SRGB_LEVELS = np.arange(256, dtype=np.float64) / 255.0
_SRGB_DECODE = np.where(_SRGB_LEVELS <= 0.04045, _SRGB_LEVELS / 12.92, ((_SRGB_LEVELS + 0.055) / 1.055) ** 2.4)


def srgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """Convert 8-bit sRGB to CIE L*a*b* under D65.

    Lab rather than raw RGB because the discriminations that survive at 19.6 cm
    are lightness and hue, and Lab separates them. Facade texture baked from
    aerial imagery is largely sky-lit and sits at strongly negative b*, so a
    space where that shift is one coordinate rather than three matters.
    """
    rgb = np.asarray(rgb)
    if rgb.dtype == np.uint8:
        # The decode has only 256 distinct inputs, so a table is exact and turns
        # the transcendental into a gather. The panorama control reads 134
        # million pixels twice and this is most of its cost.
        linear = _SRGB_DECODE[rgb]
    else:
        value = rgb.astype(np.float64) / 255.0
        linear = np.where(value <= 0.04045, value / 12.92, ((value + 0.055) / 1.055) ** 2.4)
    xyz = (linear @ _XYZ_FROM_LINEAR_RGB.T) / _D65_WHITE
    f = np.where(xyz > 0.008856, np.cbrt(np.maximum(xyz, 0.0)), 7.787 * xyz + 16.0 / 116.0)
    return np.stack(
        [116.0 * f[..., 1] - 16.0, 500.0 * (f[..., 0] - f[..., 1]), 200.0 * (f[..., 1] - f[..., 2])],
        axis=-1,
    )


TEXTURE_FEATURES: tuple[str, ...] = (
    "mean_lightness",
    "mean_green_red",
    "mean_blue_yellow",
    "std_lightness",
    "std_green_red",
    "std_blue_yellow",
    "skew_lightness",
    "relative_contrast",
    "std_gradient",
    "structure_anisotropy",
    "structure_axis_alignment",
    "mean_chroma",
    "std_chroma",
    "hue_cosine",
    "hue_sine",
    "min_lightness",
    "max_lightness",
    "lightness_range",
    "dark_texel_fraction",
    "bright_texel_fraction",
    "warm_texel_fraction",
    "sky_lit_texel_fraction",
    "green_texel_fraction",
)


@dataclass(frozen=True)
class TextureFeatures:
    """Per-triangle appearance statistics of the texels a triangle owns."""

    values: np.ndarray
    names: tuple[str, ...]
    texel_count: np.ndarray
    gsd_m: np.ndarray
    texel_anisotropy: np.ndarray

    def __post_init__(self) -> None:
        if self.values.shape != (len(self.texel_count), len(self.names)):
            raise ValueError("feature block must have one row per triangle and one column per name")


# Thresholded pixel shares. Absolute Lab cut points rather than per-face
# quantiles, because a share is only comparable between faces if the cut is the
# same everywhere. Sky-lit picks out the strongly blue cast that aerial texture
# puts on a shadowed facade, and green picks out canopy.
_LIGHTNESS_SHARES = (
    lambda lightness, green_red, blue_yellow: lightness < 15.0,
    lambda lightness, green_red, blue_yellow: lightness > 45.0,
    lambda lightness, green_red, blue_yellow: (green_red > 5.0) & (blue_yellow > 0.0),
    lambda lightness, green_red, blue_yellow: blue_yellow < -20.0,
    lambda lightness, green_red, blue_yellow: green_red < 0.0,
)


class MomentAccumulator:
    """Streaming appearance moments over a fixed set of groups.

    Every statistic in :data:`TEXTURE_FEATURES` is a function of running sums, a
    running minimum and a running maximum, so a group can be fed in any number
    of chunks and end up bit-identical to a single pass. That matters twice
    over: an atlas is naturally processed patch by patch, and the panorama
    control has to be computed on a 16384 by 8192 image that does not fit in
    memory as float64. It also guarantees the control and the texture channel
    are compared on literally the same descriptor rather than on two hand-copied
    implementations of it.
    """

    _SUMS = 14

    def __init__(self, size: int) -> None:
        if size <= 0:
            raise ValueError("size must be positive")
        self.size = int(size)
        self.count = np.zeros(size, dtype=np.float64)
        self._sums = np.zeros((self._SUMS, size), dtype=np.float64)
        self._shares = np.zeros((len(_LIGHTNESS_SHARES), size), dtype=np.float64)
        self._low = np.full(size, np.inf)
        self._high = np.full(size, -np.inf)

    def add(self, group: np.ndarray, lab: np.ndarray, gradient: np.ndarray) -> None:
        """Fold one chunk of pixels, given their group, Lab values and Lab gradient."""
        group = np.asarray(group, dtype=np.int64)
        lab = np.asarray(lab, dtype=np.float64)
        gradient = np.asarray(gradient, dtype=np.float64)
        if lab.shape != (len(group), 3) or gradient.shape != (len(group), 2):
            raise ValueError("lab must be [pixels, 3] and gradient [pixels, 2]")
        if not group.size:
            return
        if group.min() < 0 or group.max() >= self.size:
            raise IndexError("group index outside the accumulator")
        lightness, green_red, blue_yellow = lab[:, 0], lab[:, 1], lab[:, 2]
        dx, dy = gradient[:, 0], gradient[:, 1]
        magnitude = np.hypot(dx, dy)
        chroma = np.hypot(green_red, blue_yellow)
        terms = (
            lightness,
            lightness**2,
            lightness**3,
            green_red,
            green_red**2,
            blue_yellow,
            blue_yellow**2,
            magnitude,
            magnitude**2,
            dx**2,
            dy**2,
            dx * dy,
            chroma,
            chroma**2,
        )
        for index, values in enumerate(terms):
            self._sums[index] += np.bincount(group, weights=values, minlength=self.size)
        self.count += np.bincount(group, minlength=self.size)
        np.minimum.at(self._low, group, lightness)
        np.maximum.at(self._high, group, lightness)
        for index, mask in enumerate(_LIGHTNESS_SHARES):
            selected = mask(lightness, green_red, blue_yellow).astype(np.float64)
            self._shares[index] += np.bincount(group, weights=selected, minlength=self.size)

    def finish(self) -> np.ndarray:
        """Return the ``[groups, len(TEXTURE_FEATURES)]`` descriptor block."""
        safe = np.maximum(self.count, 1.0)
        shares = self._shares / safe
        (
            sum_l,
            sum_l2,
            sum_l3,
            sum_a,
            sum_a2,
            sum_b,
            sum_b2,
            sum_g,
            sum_g2,
            sum_xx,
            sum_yy,
            sum_xy,
            sum_c,
            sum_c2,
        ) = self._sums / safe
        var_l = np.maximum(sum_l2 - sum_l**2, 0.0)
        var_a = np.maximum(sum_a2 - sum_a**2, 0.0)
        var_b = np.maximum(sum_b2 - sum_b**2, 0.0)
        var_g = np.maximum(sum_g2 - sum_g**2, 0.0)
        var_c = np.maximum(sum_c2 - sum_c**2, 0.0)
        third = sum_l3 - 3.0 * sum_l * sum_l2 + 2.0 * sum_l**3
        trace = sum_xx + sum_yy
        spread = np.sqrt(np.maximum((sum_xx - sum_yy) ** 2 + 4.0 * sum_xy**2, 0.0))
        hue_norm = np.maximum(np.hypot(sum_a, sum_b), 1e-9)
        low = np.where(np.isfinite(self._low), self._low, 0.0)
        high = np.where(np.isfinite(self._high), self._high, 0.0)
        return np.stack(
            [
                sum_l,
                sum_a,
                sum_b,
                np.sqrt(var_l),
                np.sqrt(var_a),
                np.sqrt(var_b),
                third / np.maximum(var_l, 1e-6) ** 1.5,
                sum_g / np.maximum(sum_l, 1e-3),
                np.sqrt(var_g),
                spread / np.maximum(trace, 1e-9),
                np.abs(sum_xx - sum_yy) / np.maximum(spread, 1e-9),
                sum_c,
                np.sqrt(var_c),
                sum_a / hue_norm,
                sum_b / hue_norm,
                low,
                high,
                high - low,
                *shares,
            ],
            axis=1,
        )


def image_lab_and_gradient(image: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Lab image, and its lightness gradient along the column and row axes."""
    lab = srgb_to_lab(image)
    gradient_row, gradient_column = np.gradient(lab[..., 0])
    return lab, gradient_column, gradient_row


def texture_features(surface: TileSurface) -> TextureFeatures:
    """Appearance statistics, texel support and ground sample distance per triangle.

    Only statistics that survive a handful of texels are used. There is no
    filter bank and no learned embedding, because the median triangle owns 14
    texels and a descriptor with more degrees of freedom than that is fitting
    the atlas, not the wall.
    """
    count = surface.triangle_count
    accumulator = MomentAccumulator(count)
    uv_texels = surface.uv_texels()
    for index, image in enumerate(surface.patches):
        rows = np.flatnonzero(surface.patch == index)
        if not rows.size:
            continue
        height, width = image.shape[:2]
        triangle, row, column = rasterize_uv_triangles(uv_texels[rows], height, width)
        if not triangle.size:
            continue
        lab, gradient_column, gradient_row = image_lab_and_gradient(image)
        accumulator.add(
            rows[triangle],
            lab[row, column],
            np.stack([gradient_column[row, column], gradient_row[row, column]], axis=1),
        )
    gsd, anisotropy = texel_geometry(surface)
    return TextureFeatures(
        values=accumulator.finish(),
        names=TEXTURE_FEATURES,
        texel_count=accumulator.count.astype(np.int64),
        gsd_m=gsd,
        texel_anisotropy=anisotropy,
    )
