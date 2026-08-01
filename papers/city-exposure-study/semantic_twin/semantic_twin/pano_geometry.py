"""Projection utilities shared by panorama segmentation and mesh labelling.

The panorama is treated as a sphere whose centre column faces the reported
heading. Perspective inference views are sampled from that sphere so segmentation
models never see the severe pole distortion of a raw equirectangular image.
"""

from __future__ import annotations

import math
import weakref
from dataclasses import dataclass

import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates

_LAST_DECODE: tuple[weakref.ReferenceType[Image.Image], np.ndarray] | None = None


@dataclass(frozen=True)
class PerspectiveView:
    name: str
    yaw_deg: float
    pitch_deg: float
    fov_deg: float = 90.0


@dataclass(frozen=True)
class ProjectionValidity:
    """Geometric support rules for projecting a rectilinear inference crop.

    The bounds are expressed on the unit viewing sphere, rather than in raw
    equirectangular pixels.  This matters because a fixed pixel band near a
    panorama pole covers a vanishingly small solid angle.  The lower elevation
    limit is also the appropriate conservative exclusion for a nadir camera
    rig.  It is *not* an object detector and cannot identify an arbitrary rig
    or stitching artefact away from the pole.
    """

    min_elevation_deg: float = -75.0
    max_elevation_deg: float = 75.0
    crop_margin_px: float = 0.0
    seam_margin_deg: float = 0.0

    def __post_init__(self) -> None:
        if not -90.0 <= self.min_elevation_deg < self.max_elevation_deg <= 90.0:
            raise ValueError("elevation limits must satisfy -90 <= min < max <= 90")
        if self.crop_margin_px < 0.0:
            raise ValueError("crop_margin_px must be non-negative")
        if not 0.0 <= self.seam_margin_deg < 180.0:
            raise ValueError("seam_margin_deg must be in [0, 180)")


def inference_views() -> list[PerspectiveView]:
    """Overlapping views that cover the sphere with seam-safe central regions."""
    views = [
        PerspectiveView(f"h{pitch:+03.0f}_{yaw:03.0f}", yaw, pitch, 90.0)
        for pitch in (-45.0, 0.0, 45.0)
        for yaw in range(0, 360, 45)
    ]
    views.extend([PerspectiveView("zenith", 0.0, 90.0, 100.0), PerspectiveView("nadir", 0.0, -90.0, 100.0)])
    return views


def view_basis(yaw_deg: float, pitch_deg: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Panorama-local right, forward and up axes of one rectilinear view."""
    yaw, pitch = np.radians([yaw_deg, pitch_deg])
    forward = np.array([math.sin(yaw) * math.cos(pitch), math.cos(yaw) * math.cos(pitch), math.sin(pitch)])
    right = np.array([math.cos(yaw), -math.sin(yaw), 0.0])
    up = np.cross(right, forward)
    return right, forward, up


def perspective_directions(view: PerspectiveView, width: int, height: int) -> np.ndarray:
    """Unit panorama-local ray for every pixel in a rectilinear view.

    The image offsets are separable, so the two axis contributions are built at
    ``(1, width, 3)`` and ``(height, 1, 3)`` and broadcast once.  Materialising a
    meshgrid and two full ``(height, width, 3)`` products instead costs four
    extra buffers of that size, which at the 1536 pixel inference crops is
    283 MB of avoidable traffic per view.  Each element still evaluates
    ``(forward + x * right) + y * up`` in that order, so the result is unchanged
    bit for bit.
    """
    right, forward, up = view_basis(view.yaw_deg, view.pitch_deg)
    aspect = width / height
    tx = math.tan(math.radians(view.fov_deg) / 2.0)
    ty = tx / aspect
    x = ((np.arange(width) + 0.5) / width * 2.0 - 1.0) * tx
    y = (1.0 - (np.arange(height) + 0.5) / height * 2.0) * ty
    directions = forward + x[None, :, None] * right + y[:, None, None] * up
    directions /= np.linalg.norm(directions, axis=2, keepdims=True)
    return directions


def perspective_direction_at(view: PerspectiveView, x: float, y: float, width: int, height: int) -> np.ndarray:
    """Unit panorama-local ray through one continuous image coordinate.

    ``x`` and ``y`` run from 0 at the leading edge of the first pixel to
    ``width`` and ``height`` at the trailing edge of the last, so a pixel corner
    is an integer and a pixel centre is a half integer. Feeding ``(i + 0.5,
    j + 0.5)`` reproduces ``perspective_directions(view, width, height)[j, i]``
    exactly. Callers that subdivide down to sub-pixel tiles need the corners,
    which the grid form cannot give them.
    """
    right, forward, up = view_basis(view.yaw_deg, view.pitch_deg)
    tx = math.tan(math.radians(view.fov_deg) / 2.0)
    ty = tx / (width / height)
    image_x = (x / width * 2.0 - 1.0) * tx
    image_y = (1.0 - y / height * 2.0) * ty
    direction = forward + image_x * right + image_y * up
    return direction / np.linalg.norm(direction)


def perspective_projection_validity_mask(
    view: PerspectiveView,
    width: int,
    height: int,
    *,
    validity: ProjectionValidity = ProjectionValidity(),
) -> np.ndarray:
    """Return geometry-only support for one rectilinear inference view.

    The input view remains an ordinary pinhole/rectilinear camera.  Pixels are
    mapped to their panorama-sphere directions, then excluded when they are
    close to either spherical pole, inside a requested panorama seam band, or
    at the crop border.  The last rule gives callers a buffer against model
    boundary effects without changing camera intrinsics.

    A False value means "do not project this prediction onto the support mesh",
    not "this pixel is known to be an occluder".  Keep dynamic-object handling
    and depth disagreement as separate evidence layers.
    """
    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive")
    if validity.crop_margin_px * 2.0 >= min(width, height):
        raise ValueError("crop margin leaves no valid pixels")

    directions = perspective_directions(view, width, height)
    elevation_deg = np.degrees(np.arcsin(np.clip(directions[:, :, 2], -1.0, 1.0)))
    valid = (elevation_deg >= validity.min_elevation_deg) & (elevation_deg <= validity.max_elevation_deg)

    if validity.seam_margin_deg:
        yaw_deg = np.degrees(np.arctan2(directions[:, :, 0], directions[:, :, 1]))
        seam_distance_deg = 180.0 - np.abs(yaw_deg)
        valid &= seam_distance_deg >= validity.seam_margin_deg

    if validity.crop_margin_px:
        x = np.arange(width, dtype=float) + 0.5
        y = np.arange(height, dtype=float) + 0.5
        xx, yy = np.meshgrid(x, y)
        margin = validity.crop_margin_px
        valid &= (xx >= margin) & (xx <= width - margin) & (yy >= margin) & (yy <= height - margin)

    return valid


def view_pixel_coordinates(
    directions: np.ndarray,
    view: PerspectiveView,
    width: int,
    height: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Project panorama-local directions into one perspective view.

    This is the inner loop of panorama fusion, so every step after the three
    projections runs in place on buffers that already exist.  The arithmetic is
    written in the same association and the same order as the expressions it
    replaces, and IEEE 754 makes addition, multiplication, division and
    comparison correctly rounded, so the returned pixels and validity mask are
    unchanged bit for bit.  Rays behind the camera are divided along with the
    rest under a suppressed error state and then reset to zero, rather than
    driving numpy's much slower masked division loop.
    """
    right, forward, up = view_basis(view.yaw_deg, view.pitch_deg)
    depth = directions @ forward
    tangent_x = np.tan(np.radians(view.fov_deg) / 2.0)
    tangent_y = tangent_x / (width / height)
    front = depth > 1e-6
    behind = ~front
    pixel_x = directions @ right
    pixel_y = directions @ up
    with np.errstate(divide="ignore", invalid="ignore"):
        pixel_x /= depth * tangent_x
        pixel_y /= depth * tangent_y
    pixel_x[behind] = 0.0
    pixel_y[behind] = 0.0
    pixel_x += 1.0
    pixel_x *= 0.5
    pixel_x *= width
    np.subtract(1.0, pixel_y, out=pixel_y)
    pixel_y *= 0.5
    pixel_y *= height
    valid = front & (pixel_x >= 0.0)
    valid &= pixel_x < width
    valid &= pixel_y >= 0.0
    valid &= pixel_y < height
    px = np.clip(pixel_x, 0.0, width - 1.0, out=pixel_x).astype(np.int32)
    py = np.clip(pixel_y, 0.0, height - 1.0, out=pixel_y).astype(np.int32)
    return px, py, valid


def directions_to_equirectangular(directions: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Unit panorama-local directions to floating u,v coordinates in [0, 1).

    The scaling runs in place on the two angle buffers. Each element is still
    evaluated as ``(yaw / 2pi + 0.5) % 1`` and ``0.5 - pitch / pi`` in that
    order, so the coordinates are unchanged bit for bit.
    """
    d = directions / np.linalg.norm(directions, axis=-1, keepdims=True)
    u = np.arctan2(d[..., 0], d[..., 1])
    u /= 2.0 * np.pi
    u += 0.5
    u %= 1.0
    v = np.arcsin(np.clip(d[..., 2], -1.0, 1.0))
    v /= np.pi
    return u, 0.5 - v


def equirectangular_directions(width: int, height: int) -> np.ndarray:
    """Unit panorama-local ray through every equirectangular pixel centre."""
    u = (np.arange(width) + 0.5) / width
    v = (np.arange(height) + 0.5) / height
    yaw = (u - 0.5) * 2.0 * np.pi
    pitch = (0.5 - v) * np.pi
    yy, pp = np.meshgrid(yaw, pitch)
    cp = np.cos(pp)
    return np.stack([np.sin(yy) * cp, np.cos(yy) * cp, np.sin(pp)], axis=2)


def decoded_panorama(panorama: Image.Image) -> np.ndarray:
    """Decoded ``(rows, columns, 3)`` RGB pixels of one panorama.

    Two costs are avoided here. A panorama that is already RGB is not converted,
    because ``Image.convert`` to the mode an image is already in only copies it,
    and at the 16384 x 8192 Street View size that copy is 403 MB. The result is
    then held against a weak reference to the image, so sampling a whole set of
    inference views decodes once instead of once per view.

    The cache is keyed on the identity of the image object and assumes panorama
    pixels are immutable, which is what the observation ledger already requires
    of them: a panorama is a record of what a camera saw, and derived evidence
    is never written back over it. Pass the array around directly if you need to
    edit pixels in place between reads.
    """
    global _LAST_DECODE
    if _LAST_DECODE is not None and _LAST_DECODE[0]() is panorama:
        return _LAST_DECODE[1]
    image = np.asarray(panorama if panorama.mode == "RGB" else panorama.convert("RGB"))
    try:
        _LAST_DECODE = (weakref.ref(panorama), image)
    except TypeError:
        _LAST_DECODE = None
    return image


def extract_perspective(
    panorama: Image.Image, view: PerspectiveView, *, width: int = 1024, height: int = 1024
) -> Image.Image:
    """Bilinearly sample one rectilinear view from an equirectangular panorama."""
    image = decoded_panorama(panorama)
    directions = perspective_directions(view, width, height)
    u, v = directions_to_equirectangular(directions)
    xs = u * image.shape[1] - 0.5
    ys = np.clip(v * image.shape[0] - 0.5, 0.0, image.shape[0] - 1.0)
    coords = np.stack([ys, xs], axis=0)
    channels = [map_coordinates(image[:, :, c], coords, order=1, mode="grid-wrap") for c in range(3)]
    return Image.fromarray(np.stack(channels, axis=2).astype(np.uint8), "RGB")


def _axis_angle(axis: np.ndarray, angle_deg: float) -> np.ndarray:
    axis = np.asarray(axis, dtype=float)
    axis /= np.linalg.norm(axis)
    x, y, z = axis
    angle = math.radians(angle_deg)
    c, s, c1 = math.cos(angle), math.sin(angle), 1.0 - math.cos(angle)
    return np.array(
        [
            [c + x * x * c1, x * y * c1 - z * s, x * z * c1 + y * s],
            [y * x * c1 + z * s, c + y * y * c1, y * z * c1 - x * s],
            [z * x * c1 - y * s, z * y * c1 + x * s, c + z * z * c1],
        ]
    )


def panorama_to_world_matrix(
    heading_deg: float,
    *,
    pitch_deg: float = 0.0,
    roll_deg: float = 0.0,
) -> np.ndarray:
    """Rotation from panorama-local (right, forward, up) to world ENU.

    ``pitch_deg`` and ``roll_deg`` are explicit corrections refined by skyline
    registration. Inhouse's ``tilt`` is retained in pose metadata as an initial
    hint but is not silently interpreted here because its sign depends on whether
    the source tiles were pre-levelled.
    """
    heading = math.radians(heading_deg)
    right = np.array([math.cos(heading), -math.sin(heading), 0.0])
    forward = np.array([math.sin(heading), math.cos(heading), 0.0])
    up = np.array([0.0, 0.0, 1.0])
    base = np.column_stack([right, forward, up])
    pitch = _axis_angle(np.array([1.0, 0.0, 0.0]), pitch_deg)
    roll = _axis_angle(np.array([0.0, 1.0, 0.0]), roll_deg)
    return base @ roll @ pitch


def streetview_orientation_prior(tilt_deg: float, roll_deg: float) -> tuple[float, float]:
    """Convert Street View metadata into panorama pitch and roll priors.

    Street View reports tilt relative to the nominal 90 degree horizon. The
    panorama tiles are not guaranteed to be levelled, so this orientation is
    applied explicitly and registration only needs to estimate a residual.
    """
    return float(tilt_deg - 90.0), float(roll_deg)


def world_directions_to_equirectangular(
    directions: np.ndarray,
    *,
    heading_deg: float,
    pitch_deg: float = 0.0,
    roll_deg: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """World ENU ray directions to panorama u,v coordinates."""
    rotation = panorama_to_world_matrix(heading_deg, pitch_deg=pitch_deg, roll_deg=roll_deg)
    local = np.asarray(directions) @ rotation
    return directions_to_equirectangular(local)
