"""What the source set thinning has to survive.

`measure_source_silhouette.thin` decides how base station sites are spread along
the roofline, and that choice is worth 0.2 to 0.5 dB per halving of the cell. Two
properties carry the argument in METHOD.md section 5.2, and both are checked here
on layouts small enough to count by hand.
"""

from __future__ import annotations

import numpy as np
import pytest

from measure_source_silhouette import thin
from source_support import direct_from_sites, silhouette_cloud


def wall(length_m: float, height_m: float, n: int) -> np.ndarray:
    """A vertical strip, sampled evenly in both directions."""
    y, z = np.meshgrid(np.linspace(0.0, length_m, n), np.linspace(0.0, height_m, n))
    return np.stack([np.zeros(y.size), y.ravel(), z.ravel()], axis=-1)


def roof(side_m: float, height_m: float, n: int) -> np.ndarray:
    """A horizontal patch at one height, sampled evenly in both directions."""
    x, y = np.meshgrid(np.linspace(0.0, side_m, n), np.linspace(0.0, side_m, n))
    return np.stack([x.ravel(), y.ravel(), np.full(x.size, height_m)], axis=-1)


def test_flat_cells_count_a_wall_by_its_footprint_and_a_roof_by_its_area():
    """This is why the flat grid has no useful limit.

    A wall stands over a line of ground, so halving a flat cell roughly doubles
    its site count. A roof covers a patch of ground, so halving roughly
    quadruples it. Shrink the cell and the roof takes over the set.
    """
    counts = {}
    for name, cloud in (("wall", wall(32.0, 16.0, 400)), ("roof", roof(32.0, 16.0, 400))):
        counts[name] = [thin(cloud, cell, dims=2).shape[0] for cell in (4.0, 2.0, 1.0)]

    wall_growth = np.array(counts["wall"][1:]) / np.array(counts["wall"][:-1])
    roof_growth = np.array(counts["roof"][1:]) / np.array(counts["roof"][:-1])
    assert np.all(wall_growth < 2.6), counts
    assert np.all(roof_growth > 3.3), counts


def test_solid_cells_count_both_by_area():
    """And this is why the solid grid is the default. Both grow the same way."""
    counts = {}
    for name, cloud in (("wall", wall(32.0, 16.0, 400)), ("roof", roof(32.0, 16.0, 400))):
        counts[name] = [thin(cloud, cell, dims=3).shape[0] for cell in (4.0, 2.0, 1.0)]

    wall_growth = np.array(counts["wall"][1:]) / np.array(counts["wall"][:-1])
    roof_growth = np.array(counts["roof"][1:]) / np.array(counts["roof"][:-1])
    assert np.all(wall_growth > 3.3), counts
    assert np.all(roof_growth > 3.3), counts


def test_one_site_per_occupied_cell_however_hard_the_fan_stared():
    """A fan crowds samples where it looks edge on, and thinning has to undo that.

    The same wall is sampled once evenly and once with a tenfold pile up along a
    quarter of it. The thinned sets have to match.
    """
    even = wall(20.0, 10.0, 200)
    crowded = np.concatenate([even, np.repeat(even[even[:, 1] < 5.0], 10, axis=0)])
    assert crowded.shape[0] > 3 * even.shape[0]
    assert thin(crowded, 1.0, dims=3).shape[0] == thin(even, 1.0, dims=3).shape[0]


def test_the_highest_pick_is_biased_upward_and_the_uniform_pick_is_not():
    """Why `pick` exists. The highest point in a cell is its least typical member.

    On a flat grid this wall is one line of cells, so the highest pick lands on
    the top edge every time and misses the wall's own mean by the full half
    height. The uniform pick has to be unbiased, which is a statement about its
    average and not about any one draw, so it is checked over many seeds.
    """
    cloud = wall(20.0, 10.0, 200)
    highest = thin(cloud, 4.0, dims=2)
    assert highest[:, 2].mean() == pytest.approx(10.0)

    means = [thin(cloud, 4.0, np.random.default_rng(seed), dims=2)[:, 2].mean() for seed in range(40)]
    assert np.mean(means) == pytest.approx(cloud[:, 2].mean(), abs=0.5)


def test_empty_cloud_survives_both_grids():
    empty = np.empty((0, 3))
    assert thin(empty, 1.0, dims=2).shape == (0, 3)
    assert thin(empty, 1.0, dims=3).shape == (0, 3)


class OpenSky:
    """A world with nothing in it, so every connecting ray is clear."""

    def intersect(self, origins, directions):
        n = origins.shape[0]
        return (
            np.zeros(n, dtype=bool),
            np.full(n, np.inf),
            np.zeros((n, 3)),
            np.zeros(n, dtype=np.int64),
        )


def test_the_direct_term_divides_by_every_site_not_only_the_visible_ones():
    """The mean is over the whole set, which is what makes it density free.

    Doubling the sites while halving what each stands for has to leave the answer
    alone. Here the same ring is sampled twice as finely and the term does not
    move.
    """
    origin = np.zeros((1, 3))
    for n in (16, 32):
        angle = np.arange(n) * (2.0 * np.pi / n)
        ring = np.stack([20.0 * np.cos(angle), 20.0 * np.sin(angle), np.full(n, 15.0)], axis=-1)
        direct, seen = direct_from_sites(OpenSky(), origin, ring)
        assert seen[0] == pytest.approx(1.0)
        assert direct[0] == pytest.approx(1.0 / (20.0**2 + 15.0**2), rel=1e-9)


def test_the_floor_drops_tips_by_range_from_the_standpoint_that_found_them():
    """The floor `measure_source_silhouette` grew, and what it can and cannot do."""

    def fake_silhouette(geometry, origin, *, azimuths, elevations):
        # Two azimuths, one tip close and one far, both well above the head.
        alpha = np.array([np.deg2rad(70.0), np.deg2rad(20.0)])
        horizontal = np.array([3.0, 40.0])
        return alpha, horizontal, np.array([True, True])

    origins = np.zeros((1, 3))
    kept = silhouette_cloud(None, origins, fake_silhouette, azimuths=2, elevations=2)
    cut = silhouette_cloud(None, origins, fake_silhouette, azimuths=2, elevations=2, floor_m=5.0)
    assert kept.shape[0] == 2
    assert cut.shape[0] == 1
    # The survivor is the far one, and the floor is on horizontal range, so the
    # dropped tip is 3 m out on the ground even though it is 8.8 m away in slant.
    assert np.hypot(cut[0, 0], cut[0, 1]) == pytest.approx(40.0, rel=1e-6)
    assert np.hypot(kept[0, 0], kept[0, 1]) == pytest.approx(3.0, rel=1e-6)


class OneFacePerAzimuth:
    """Geometry that answers only "which triangle did this direction hit"."""

    def __init__(self, faces: list[int]) -> None:
        self.faces = faces

    def intersect(self, origins, directions):  # noqa: ANN001, ANN201
        count = np.asarray(directions).shape[0]
        index = np.asarray(self.faces[:count], dtype=np.int64)
        return np.ones(count, bool), np.ones(count), np.zeros((count, 3)), index


def two_tips(geometry, origin, *, azimuths, elevations):  # noqa: ANN001, ANN201
    """One tip north and one east, both on a roofline, both far enough to keep."""
    return np.full(2, np.deg2rad(30.0)), np.array([40.0, 45.0]), np.array([True, True])


def test_a_tip_on_a_billboard_is_dropped_and_the_roof_beside_it_is_not():
    """The point of the mask: it separates two tips the range floor cannot."""
    origins = np.zeros((1, 3))
    clutter = np.array([True, False])
    cloud = silhouette_cloud(
        OneFacePerAzimuth([0, 1]),
        origins,
        two_tips,
        azimuths=2,
        elevations=2,
        clutter_triangles=clutter,
    )
    assert cloud.shape[0] == 1
    assert np.hypot(cloud[0, 0], cloud[0, 1]) == pytest.approx(45.0, rel=1e-6)


def test_no_mask_keeps_every_tip():
    """Every published run before the mask existed, unchanged."""
    origins = np.zeros((1, 3))
    assert silhouette_cloud(OneFacePerAzimuth([0, 1]), origins, two_tips, azimuths=2, elevations=2).shape[0] == 2


def test_a_tip_that_hits_nothing_the_mask_knows_about_is_kept():
    """A face index past the mask is a triangle the panoramas never saw, not clutter."""
    origins = np.zeros((1, 3))
    cloud = silhouette_cloud(
        OneFacePerAzimuth([-1, 900]),
        origins,
        two_tips,
        azimuths=2,
        elevations=2,
        clutter_triangles=np.array([True, True]),
    )
    assert cloud.shape[0] == 2
