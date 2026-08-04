"""Pixel-faithful adaptive tiles for projecting dense semantics into 3D."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SemanticTile:
    """A half-open image rectangle containing one semantic class."""

    x0: int
    y0: int
    x1: int
    y1: int
    class_id: int

    @property
    def width(self) -> int:
        return self.x1 - self.x0

    @property
    def height(self) -> int:
        return self.y1 - self.y0


def adaptive_semantic_tiles(labels: np.ndarray, valid: np.ndarray) -> list[SemanticTile]:
    """Exactly encode valid labelled pixels with adaptively merged rectangles.

    Uniform regions collapse to large tiles. Mixed or partially invalid regions
    recursively split down to individual source pixels, so semantic boundaries
    never become coarser than the input label map.
    """
    labels = np.asarray(labels)
    valid = np.asarray(valid, dtype=bool)
    if labels.ndim != 2 or valid.shape != labels.shape:
        raise ValueError("labels and valid must be equally shaped 2D arrays")

    height, width = labels.shape
    result: list[SemanticTile] = []
    pending = [(0, 0, width, height)]
    while pending:
        x0, y0, x1, y1 = pending.pop()
        tile_valid = valid[y0:y1, x0:x1]
        if not tile_valid.any():
            continue
        tile_labels = labels[y0:y1, x0:x1]
        if tile_valid.all() and np.all(tile_labels == tile_labels[0, 0]):
            result.append(SemanticTile(x0, y0, x1, y1, int(tile_labels[0, 0])))
            continue
        if x1 - x0 == 1 and y1 - y0 == 1:
            result.append(SemanticTile(x0, y0, x1, y1, int(tile_labels[0, 0])))
            continue

        xm = (x0 + x1) // 2
        ym = (y0 + y1) // 2
        children = (
            (x0, y0, xm, ym),
            (xm, y0, x1, ym),
            (x0, ym, xm, y1),
            (xm, ym, x1, y1),
        )
        pending.extend(child for child in children if child[0] < child[2] and child[1] < child[3])
    return result


def rasterize_tiles(tiles: list[SemanticTile], shape: tuple[int, int], *, fill: int = -1) -> np.ndarray:
    """Rasterize tiles for validation and diagnostics."""
    output = np.full(shape, fill, dtype=np.int64)
    for tile in tiles:
        output[tile.y0 : tile.y1, tile.x0 : tile.x1] = tile.class_id
    return output


def plane_fit_error(points: np.ndarray) -> tuple[float, np.ndarray]:
    """Return maximum orthogonal residual and normal of a best-fit plane."""
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or points.shape[0] < 3 or points.shape[1] != 3:
        raise ValueError("points must have shape (n, 3) with n >= 3")
    centred = points - points.mean(axis=0)
    _u, _singular, axes = np.linalg.svd(centred, full_matrices=False)
    normal = axes[-1]
    residual = np.abs(centred @ normal)
    return float(residual.max()), normal


def edge_aware_smooth_depth(
    depth: np.ndarray,
    valid: np.ndarray,
    *,
    iterations: int = 3,
    edge_sigma_m: float = 0.75,
) -> np.ndarray:
    """Regularize a ray-cast depth grid while preserving blockers and holes."""
    values = np.asarray(depth, dtype=float)
    mask = np.asarray(valid, dtype=bool)
    if values.ndim != 2 or mask.shape != values.shape:
        raise ValueError("depth and valid must have matching 2D shapes")
    if iterations < 0 or edge_sigma_m <= 0.0:
        raise ValueError("iterations must be non-negative and edge_sigma_m positive")
    result = values.copy()
    result[~mask] = np.nan
    for _ in range(iterations):
        numerator = np.where(mask, result, 0.0)
        denominator = mask.astype(float)
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            shifted = np.roll(result, (dy, dx), axis=(0, 1))
            shifted_mask = np.roll(mask, (dy, dx), axis=(0, 1))
            valid_pair = mask & shifted_mask
            weight = valid_pair * np.exp(-np.abs(shifted - result) / edge_sigma_m)
            weight = np.nan_to_num(weight, nan=0.0)
            numerator += weight * np.nan_to_num(shifted, nan=0.0)
            denominator += weight
        result[mask] = numerator[mask] / np.maximum(denominator[mask], 1e-12)
    return result
