"""Directions on the sphere: the quadrature grid, the binning search, and draws.

This is the discretisation an angular illumination law is read on. The tracer
bins every exit direction onto :func:`fibonacci_sphere` to build an angular power
spectrum, then dots that spectrum with a density from :mod:`~.bands`, so the grid
and the law are two halves of one integral and they belong together.

It sits in this package because it came out of ``propagation/directions.py`` when
the laws did, and the laws are its only structural neighbour today. When the
transport layer becomes its own package it moves there with the tracer.
"""

from __future__ import annotations

import math

import numpy as np

GOLDEN_ANGLE = np.pi * (3.0 - np.sqrt(5.0))

#: Half width of the elevation band searched by :func:`nearest_cell`, as a
#: multiple of ``sqrt(cells)``. The covering radius of a Fibonacci lattice goes
#: as ``1/sqrt(cells)`` in angle and the cell spacing in ``z`` goes as
#: ``1/cells``, so the number of cells that can hold the answer goes as
#: ``sqrt(cells)``. The constant is set from the measured miss rate rather than
#: from that argument: 1.5 leaves no misses at all from 2e6 directions on every
#: grid between 64 and 4096 cells. It is a speed knob and nothing else, because
#: a miss is caught and answered exactly.
_BAND_CONSTANT = 1.5


def fibonacci_sphere(count: int) -> np.ndarray:
    """Unit vectors spread over the sphere with near equal solid angle.

    Returns an ``(count, 3)`` array. Cell solid angle is ``4*pi/count`` to within
    a few percent, which is the accuracy the deposit weights assume.
    """
    if count < 1:
        raise ValueError("count must be positive")
    index = np.arange(count, dtype=np.float64)
    z = 1.0 - (2.0 * index + 1.0) / count
    radius = np.sqrt(np.maximum(0.0, 1.0 - z * z))
    theta = GOLDEN_ANGLE * index
    return np.stack([radius * np.cos(theta), radius * np.sin(theta), z], axis=1)


def sample_sphere(count: int, rng: np.random.Generator) -> np.ndarray:
    """Uniform directions on the sphere."""
    z = rng.uniform(-1.0, 1.0, size=count)
    phi = rng.uniform(0.0, 2.0 * np.pi, size=count)
    radius = np.sqrt(np.maximum(0.0, 1.0 - z * z))
    return np.stack([radius * np.cos(phi), radius * np.sin(phi), z], axis=1)


def _brute_nearest_cell(directions: np.ndarray, grid: np.ndarray, block: int) -> np.ndarray:
    """Dense ``argmax`` of every dot product. The definition, and the fallback."""
    out = np.empty(directions.shape[0], dtype=np.int64)
    for start in range(0, directions.shape[0], block):
        stop = min(start + block, directions.shape[0])
        out[start:stop] = np.argmax(directions[start:stop] @ grid.T, axis=1)
    return out


def _band_starts(grid: np.ndarray, query: np.ndarray, half: int, width: int) -> tuple[np.ndarray, float, bool]:
    """First cell of each query's search band, and how the heights were indexed.

    A Fibonacci grid is evenly spaced in height by construction, so the cell at a
    given height is one multiply rather than a binary search. Three binary
    searches over 400k rays cost more than the dot products do. The even spacing
    is measured, not assumed, and a grid that fails the check gets
    ``searchsorted`` instead.
    """
    height = grid[:, 2]
    cells = grid.shape[0]
    step = (height[0] - height[-1]) / (cells - 1)
    even = step > 0.0 and bool(np.max(np.abs(height - (height[0] - step * np.arange(cells)))) < 0.25 * step)
    if even:
        centre = np.clip(np.rint((height[0] - query) * (1.0 / step)).astype(np.int64), 0, cells - 1)
    else:
        # ``ascending`` is the same heights the other way round, which is what
        # ``searchsorted`` needs. Cell ``j`` is entry ``cells - 1 - j``.
        ascending = np.ascontiguousarray(height[::-1])
        centre = cells - 1 - np.clip(np.searchsorted(ascending, query), 0, cells - 1)
    return np.clip(centre - half, 0, cells - width), step, even


def _search_bands(
    directions: np.ndarray, grid: np.ndarray, first: np.ndarray, width: int
) -> tuple[np.ndarray, np.ndarray]:
    """Best cell and best dot product within each query's own band.

    One band per distinct starting cell, so every dot product is a contiguous
    ``(rays_in_band, width)`` block that stays in cache.
    """
    rays = directions.shape[0]
    out = np.empty(rays, dtype=np.int64)
    best = np.empty(rays)
    order = np.argsort(first, kind="stable")
    starts = first[order]
    unique, opens = np.unique(starts, return_index=True)
    opens = np.append(opens, rays)
    for i in range(unique.size):
        rows = order[opens[i] : opens[i + 1]]
        start = int(unique[i])
        dots = directions[rows] @ grid[start : start + width].T
        local = np.argmax(dots, axis=1)
        out[rows] = start + local
        best[rows] = dots[np.arange(local.size), local]
    return out, best


def _reach_outside_band(
    grid: np.ndarray, query: np.ndarray, best: np.ndarray, first: np.ndarray, width: int, step: float, even: bool
) -> np.ndarray:
    """Which queries could still be beaten by a cell their band did not hold.

    ``arccos`` of the best dot product is the elevation reach, and the epsilons
    only ever widen it, so a rounding error here costs a dense fallback and never
    an answer.
    """
    height = grid[:, 2]
    cells = grid.shape[0]
    reach = np.arccos(np.clip(best, -1.0, 1.0)) + 1.0e-12
    elevation = np.arcsin(np.clip(query, -1.0, 1.0))
    top = np.sin(np.clip(elevation + reach, -0.5 * np.pi, 0.5 * np.pi)) + 1.0e-12
    bottom = np.sin(np.clip(elevation - reach, -0.5 * np.pi, 0.5 * np.pi)) - 1.0e-12
    if even:
        # One cell of slack each way, which covers the quarter cell the even
        # spacing check allows the grid to wander by. Slack widens the range that
        # has to fall inside the band, so it can only cost a fallback.
        scale = 1.0 / step
        lowest = np.maximum(np.ceil((height[0] - top) * scale).astype(np.int64) - 1, 0)
        highest = np.minimum(np.floor((height[0] - bottom) * scale).astype(np.int64) + 1, cells - 1)
    else:
        ascending = np.ascontiguousarray(height[::-1])
        lowest = cells - np.searchsorted(ascending, top, side="right")
        highest = cells - 1 - np.searchsorted(ascending, bottom, side="left")
    return (lowest < first) | (highest >= first + width)


def nearest_cell(directions: np.ndarray, grid: np.ndarray, *, block: int = 65536) -> np.ndarray:
    """Index of the nearest grid direction for each row of ``directions``.

    The dense form of this is one ``(rays, cells)`` matrix of dot products, and at
    the sizes this study runs, 400k rays against 512 cells for every trace, it was
    a quarter of the trace and 1.6 GB of writes. It was also the one part of the
    estimator whose speed turned on how many BLAS threads a process happened to
    get: 0.35 s on eight, 2.05 s on one, which is the number that matters once
    standpoints run in a pool. Whether it also turned on the answer was checked
    rather than assumed, and it did not, over 2e6 directions at seven block sizes
    and two thread counts.

    The band search removes both. For a grid whose ``z`` column is sorted, the dot
    product of a query ``u`` with any cell at height ``z`` is at most
    ``cos(el_u - el_z)``, so once a candidate with dot product ``b`` is in hand,
    only cells within ``arccos(b)`` in elevation can beat it. That is a contiguous
    run of cells, a few tens wide rather than the whole grid.

    The band is searched first and the bound is then checked, not assumed. Any ray
    whose bound reaches outside the band it was given is answered by the dense
    form, so the result is the dense result for every input, including exact ties,
    where both forms return the lowest index that attains the maximum. Grids that
    are not sorted in ``z``, and grids too small for a band to save anything, take
    the dense path whole.
    """
    directions = np.asarray(directions, dtype=np.float64)
    grid = np.asarray(grid, dtype=np.float64)
    rays = directions.shape[0]
    cells = grid.shape[0]
    half = max(4, int(math.ceil(_BAND_CONSTANT * math.sqrt(cells))))
    width = 2 * half + 1
    height = grid[:, 2]
    if rays == 0 or cells < width + 2 or not np.all(height[1:] <= height[:-1]):
        return _brute_nearest_cell(directions, grid, block)

    query = directions[:, 2]
    first, step, even = _band_starts(grid, query, half, width)
    out, best = _search_bands(directions, grid, first, width)
    missed = _reach_outside_band(grid, query, best, first, width, step, even)
    if np.any(missed):
        out[missed] = _brute_nearest_cell(directions[missed], grid, block)
    return out
