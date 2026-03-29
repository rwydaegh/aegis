"""Tests for the GeoJSON environment parser."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from aegis.environment import EnvironmentMesh
from aegis.environment.geojson import NaturalFeature, build_environment_from_geojson, parse_geojson

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "geojson_sample.json"
ORIGIN_LAT = 51.050
ORIGIN_LON = 3.720


@pytest.fixture
def sample_geojson() -> str:
    return FIXTURE_PATH.read_text()


def test_parse_geojson_buildings(sample_geojson: str) -> None:
    buildings, roads, water, natural = parse_geojson(sample_geojson, ORIGIN_LAT, ORIGIN_LON)

    assert len(buildings) == 1
    bld = buildings[0]

    # Height tag "10" should parse to 10.0
    assert bld.height == pytest.approx(10.0)

    # Roof shape "gabled" should be preserved
    assert bld.roof_shape == "gabled"

    # Footprint should be a 2D array with at least 3 points
    assert isinstance(bld.footprint, np.ndarray)
    assert bld.footprint.ndim == 2
    assert bld.footprint.shape[1] == 2
    assert len(bld.footprint) >= 3


def test_parse_geojson_roads(sample_geojson: str) -> None:
    buildings, roads, water, natural = parse_geojson(sample_geojson, ORIGIN_LAT, ORIGIN_LON)

    assert len(roads) == 1
    road = roads[0]

    assert road.highway_type == "residential"
    assert road.width == pytest.approx(6.0)

    # Centerline should be a 2D array with at least 2 points
    assert isinstance(road.centerline, np.ndarray)
    assert road.centerline.ndim == 2
    assert road.centerline.shape[1] == 2
    assert len(road.centerline) >= 2


def test_parse_geojson_water(sample_geojson: str) -> None:
    buildings, roads, water, natural = parse_geojson(sample_geojson, ORIGIN_LAT, ORIGIN_LON)

    assert len(water) == 1
    wb = water[0]

    # Footprint should be a 2D array with at least 3 points
    assert isinstance(wb.footprint, np.ndarray)
    assert wb.footprint.ndim == 2
    assert wb.footprint.shape[1] == 2
    assert len(wb.footprint) >= 3


def test_build_environment_from_geojson(sample_geojson: str) -> None:
    mesh = build_environment_from_geojson(sample_geojson, ORIGIN_LAT, ORIGIN_LON)

    assert isinstance(mesh, EnvironmentMesh)
    assert mesh.source == "geojson"
    assert mesh.origin_lat == pytest.approx(ORIGIN_LAT)
    assert mesh.origin_lon == pytest.approx(ORIGIN_LON)

    # Should have generated geometry from at least the building and road
    assert len(mesh.vertices) > 0
    assert len(mesh.triangles) > 0
    assert len(mesh.normals) == len(mesh.triangles)
    assert len(mesh.materials) == len(mesh.triangles)

    # Vertices should be finite
    assert np.all(np.isfinite(mesh.vertices))


def test_parse_geojson_natural_features() -> None:
    """Natural features (park, forest, grass) are parsed into NaturalFeature objects."""
    geojson = json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"leisure": "park"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [3.720, 51.050],
                                [3.721, 51.050],
                                [3.721, 51.051],
                                [3.720, 51.050],
                            ]
                        ],
                    },
                },
                {
                    "type": "Feature",
                    "properties": {"natural": "forest"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [3.722, 51.050],
                                [3.723, 51.050],
                                [3.723, 51.051],
                                [3.722, 51.050],
                            ]
                        ],
                    },
                },
            ],
        }
    )
    buildings, roads, water, natural = parse_geojson(geojson, ORIGIN_LAT, ORIGIN_LON)

    assert len(natural) == 2
    types = {nf.feature_type for nf in natural}
    assert "park" in types
    assert "forest" in types
    for nf in natural:
        assert isinstance(nf, NaturalFeature)
        assert nf.footprint.shape[1] == 2
