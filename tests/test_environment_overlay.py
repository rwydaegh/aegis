"""Tests for satellite overlay tile math."""

import numpy as np

from aegis.environment.overlay import (
    OverlayImage,
    meters_per_pixel,
    stitch_bounds,
    tile_coords,
    tile_url,
)


def test_tile_coords():
    tx, ty = tile_coords(51.05, 3.72, zoom=15)
    assert isinstance(tx, int)
    assert isinstance(ty, int)
    assert tx > 0
    assert ty > 0


def test_tile_url_osm():
    url = tile_url(1234, 5678, 15, template="https://tile.openstreetmap.org/{z}/{x}/{y}.png")
    assert "1234" in url
    assert "5678" in url
    assert "15" in url


def test_stitch_bounds():
    bounds = stitch_bounds(lat=51.05, lon=3.72, radius_m=200, zoom=15)
    assert bounds.width > 0
    assert bounds.height > 0
    assert len(bounds.tile_grid) > 0


def test_overlay_image_structure():
    oi = OverlayImage(
        image=np.zeros((256, 256, 3), dtype=np.uint8),
        uv_min=np.array([0.0, 0.0]),
        uv_max=np.array([1.0, 1.0]),
        origin_lat=51.05,
        origin_lon=3.72,
    )
    assert oi.image.shape[2] == 3


def test_tile_coords_known_value():
    # Ghent city centre at zoom 15 should be in a specific tile range
    tx, ty = tile_coords(51.05, 3.72, zoom=15)
    # At zoom 15, valid range is 0..32767; Ghent is in Western Europe
    assert 16000 < tx < 18000
    assert 10000 < ty < 12000


def test_tile_url_default_template():
    url = tile_url(100, 200, 10)
    assert url == "https://tile.openstreetmap.org/10/100/200.png"


def test_meters_per_pixel_equator():
    mpp = meters_per_pixel(lat=0.0, zoom=0)
    # At zoom 0, the whole world is 256px wide: ~156543 m/px at equator
    assert abs(mpp - 156_543.0) < 1.0


def test_meters_per_pixel_decreases_with_zoom():
    mpp_z10 = meters_per_pixel(lat=51.0, zoom=10)
    mpp_z15 = meters_per_pixel(lat=51.0, zoom=15)
    assert mpp_z15 < mpp_z10


def test_stitch_bounds_tile_grid_consistency():
    bounds = stitch_bounds(lat=51.05, lon=3.72, radius_m=500, zoom=14)
    cols = bounds.x_max - bounds.x_min + 1
    rows = bounds.y_max - bounds.y_min + 1
    assert bounds.width == cols * 256
    assert bounds.height == rows * 256
    assert len(bounds.tile_grid) == cols * rows
