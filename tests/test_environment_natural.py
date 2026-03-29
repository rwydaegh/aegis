"""Tests for natural feature geometry: forests, parks, hedges."""

import numpy as np

from aegis.environment import MaterialType
from aegis.environment.natural import (
    NaturalFeature,
    generate_forest_canopy,
    generate_ground_plane,
    generate_hedge,
)


def test_forest_canopy_volume():
    fp = np.array([[0, 0], [20, 0], [20, 20], [0, 20]], dtype=np.float64)
    verts, tris, mats = generate_forest_canopy(fp, canopy_height=8.0, canopy_base=5.0)
    assert verts.shape[0] > 0
    assert tris.shape[0] > 0
    assert np.all(mats == int(MaterialType.VEGETATION_DENSE))
    z_vals = verts[:, 2]
    assert z_vals.min() < 6.0  # has canopy_base vertices
    assert z_vals.max() > 7.0  # has canopy_height vertices


def test_ground_plane():
    fp = np.array([[0, 0], [10, 0], [10, 10], [0, 10]], dtype=np.float64)
    verts, tris, mats = generate_ground_plane(fp, z=0.0, material=MaterialType.VEGETATION)
    assert verts.shape[0] >= 3
    assert np.all(mats == int(MaterialType.VEGETATION))


def test_hedge_wall():
    centerline = np.array([[0, 0], [10, 0]], dtype=np.float64)
    verts, tris, mats = generate_hedge(centerline, height=2.0, width=0.5)
    assert verts.shape[0] > 0
    assert np.all(mats == int(MaterialType.VEGETATION_DENSE))


def test_natural_feature_dataclass():
    nf = NaturalFeature(
        way_id=1,
        footprint=np.array([[0, 0], [1, 0], [1, 1]]),
        feature_type="forest",
    )
    assert nf.feature_type == "forest"
