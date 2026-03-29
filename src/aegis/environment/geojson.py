"""GeoJSON data pipeline: parse GeoJSON FeatureCollections into environment objects.

Public API:
    parse_geojson(geojson_str, origin_lat, origin_lon) -> (buildings, roads, water, natural_features)
    build_environment_from_geojson(geojson_str, origin_lat, origin_lon, ...) -> EnvironmentMesh
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np

from aegis.environment import EnvironmentMesh
from aegis.environment.geo import transverse_mercator_forward
from aegis.environment.osm import (
    _HIGHWAY_WIDTH,
    Building,
    Road,
    WaterBody,
    _compute_face_normals,
    _parse_building_material,
    _parse_height,
    _parse_roof_shape,
    _road_to_mesh,
    _water_to_mesh,
)
from aegis.environment.roofs import generate_building

# ---------------------------------------------------------------------------
# NaturalFeature dataclass
# ---------------------------------------------------------------------------


@dataclass
class NaturalFeature:
    """A natural feature (park, forest, grass) extracted from GeoJSON."""

    way_id: int
    footprint: np.ndarray  # (N, 2) local XY coords in meters
    feature_type: str


# ---------------------------------------------------------------------------
# Projection helpers
# ---------------------------------------------------------------------------


def _project_ring(
    ring: list[list[float]],
    origin_lat: float,
    origin_lon: float,
) -> np.ndarray:
    """Project a GeoJSON coordinate ring (list of [lon, lat]) to local XY.

    GeoJSON coordinates are [lon, lat]. The closing duplicate is dropped.
    Returns (N, 2) array, or empty array if fewer than 3 unique points.
    """
    # Drop closing duplicate if present
    coords = ring[:-1] if len(ring) >= 4 and ring[0] == ring[-1] else ring
    xy = []
    for lon, lat in coords:
        x, y = transverse_mercator_forward(lat, lon, origin_lat, origin_lon)
        xy.append([x, y])
    arr = np.array(xy, dtype=np.float64)
    return arr


def _project_linestring(
    coords: list[list[float]],
    origin_lat: float,
    origin_lon: float,
) -> np.ndarray:
    """Project a GeoJSON LineString coordinate list to local XY.

    Returns (N, 2) array.
    """
    xy = []
    for lon, lat in coords:
        x, y = transverse_mercator_forward(lat, lon, origin_lat, origin_lon)
        xy.append([x, y])
    return np.array(xy, dtype=np.float64)


# ---------------------------------------------------------------------------
# Per-geometry-type feature parsers
# ---------------------------------------------------------------------------


def _parse_building_feature(
    way_id: int,
    props: dict,
    geom_type: str,
    coords: list,
    origin_lat: float,
    origin_lon: float,
) -> Building | None:
    """Parse a GeoJSON feature with a 'building' property into a Building.

    Returns None if the geometry is invalid or too small.
    """
    if geom_type != "Polygon" or not coords:
        return None
    footprint = _project_ring(coords[0], origin_lat, origin_lon)
    if len(footprint) < 3:
        return None

    building_type = props.get("building", "yes")
    height = _parse_height(props, building_type)
    roof_shape = _parse_roof_shape(props)
    roof_height_str = props.get("roof:height")
    if roof_height_str is not None:
        try:
            roof_height = float(str(roof_height_str).split()[0])
        except (ValueError, IndexError):
            roof_height = max(2.0, height * 0.25)
    else:
        roof_height = max(2.0, height * 0.25)
    material = _parse_building_material(props)
    return Building(
        way_id=way_id,
        footprint=footprint,
        height=height,
        roof_shape=roof_shape,
        roof_height=roof_height,
        material=material,
        roof_material=material,
    )


def _parse_highway_feature(
    way_id: int,
    props: dict,
    geom_type: str,
    coords: list,
    origin_lat: float,
    origin_lon: float,
) -> Road | None:
    """Parse a GeoJSON feature with a 'highway' property into a Road.

    Returns None if the geometry is invalid or too short.
    """
    if geom_type != "LineString" or not coords:
        return None
    centerline = _project_linestring(coords, origin_lat, origin_lon)
    if len(centerline) < 2:
        return None

    highway_type = props.get("highway", "unclassified")
    width = _HIGHWAY_WIDTH.get(highway_type, 6.0)
    lanes_str = props.get("lanes")
    if lanes_str is not None:
        try:
            lanes = int(lanes_str)
        except (ValueError, TypeError):
            lanes = 1
    else:
        lanes = 1
    return Road(
        way_id=way_id,
        centerline=centerline,
        highway_type=highway_type,
        width=width,
        lanes=lanes,
    )


def _parse_water_feature(
    way_id: int,
    props: dict,
    geom_type: str,
    coords: list,
    origin_lat: float,
    origin_lon: float,
) -> WaterBody | None:
    """Parse a GeoJSON feature with a water/waterway property into a WaterBody.

    Returns None if the geometry is invalid or too small.
    """
    if geom_type != "Polygon" or not coords:
        return None
    footprint = _project_ring(coords[0], origin_lat, origin_lon)
    if len(footprint) < 3:
        return None

    water_type = props.get("water", props.get("waterway", "water"))
    return WaterBody(
        way_id=way_id,
        footprint=footprint,
        water_type=water_type,
    )


def _parse_natural_feature(
    way_id: int,
    props: dict,
    geom_type: str,
    coords: list,
    origin_lat: float,
    origin_lon: float,
) -> NaturalFeature | None:
    """Parse a GeoJSON feature for natural/landuse/leisure into a NaturalFeature.

    Returns None if the geometry is invalid or too small.
    """
    if geom_type != "Polygon" or not coords:
        return None
    footprint = _project_ring(coords[0], origin_lat, origin_lon)
    if len(footprint) < 3:
        return None

    feature_type = props.get("natural") or props.get("landuse") or props.get("leisure", "natural")
    return NaturalFeature(
        way_id=way_id,
        footprint=footprint,
        feature_type=feature_type,
    )


# ---------------------------------------------------------------------------
# Origin auto-derive helper
# ---------------------------------------------------------------------------


def _derive_origin(features: list) -> tuple[float, float]:
    """Compute a centroid-based origin from a list of GeoJSON features.

    Returns (origin_lat, origin_lon) derived from all coordinate positions, or
    (0.0, 0.0) if no coordinates are found.
    """
    all_lons: list[float] = []
    all_lats: list[float] = []
    for feat in features:
        geom = feat.get("geometry") or {}
        geom_type = geom.get("type", "")
        coords = geom.get("coordinates", [])
        if geom_type == "Point":
            all_lons.append(coords[0])
            all_lats.append(coords[1])
        elif geom_type == "LineString":
            for lon, lat in coords:
                all_lons.append(lon)
                all_lats.append(lat)
        elif geom_type == "Polygon" and coords:
            for lon, lat in coords[0]:
                all_lons.append(lon)
                all_lats.append(lat)
    if not all_lons:
        return 0.0, 0.0
    return float(np.mean(all_lats)), float(np.mean(all_lons))


# ---------------------------------------------------------------------------
# Public parse function
# ---------------------------------------------------------------------------


def parse_geojson(
    geojson_str: str,
    origin_lat: float = 0.0,
    origin_lon: float = 0.0,
) -> tuple[list[Building], list[Road], list[WaterBody], list[NaturalFeature]]:
    """Parse a GeoJSON FeatureCollection string and return extracted features.

    Coordinates are projected to local XY meters relative to (origin_lat, origin_lon).
    GeoJSON coordinates are [lon, lat] (longitude first), which is handled internally.

    Args:
        geojson_str: GeoJSON FeatureCollection as a JSON string.
        origin_lat: Latitude of the local coordinate origin.
        origin_lon: Longitude of the local coordinate origin.

    Returns:
        Tuple of (buildings, roads, water_bodies, natural_features).
    """
    data = json.loads(geojson_str)
    features = data.get("features", [])

    # Auto-derive origin from feature centroids if not provided
    if origin_lat == 0.0 and origin_lon == 0.0 and features:
        origin_lat, origin_lon = _derive_origin(features)

    buildings: list[Building] = []
    roads: list[Road] = []
    water: list[WaterBody] = []
    natural_features: list[NaturalFeature] = []

    for idx, feat in enumerate(features):
        props = feat.get("properties") or {}
        geom = feat.get("geometry") or {}
        geom_type = geom.get("type", "")
        coords = geom.get("coordinates", [])
        raw_id = feat.get("id", idx)
        try:
            way_id = int(raw_id)
        except (TypeError, ValueError):
            way_id = idx

        if "building" in props:
            result = _parse_building_feature(way_id, props, geom_type, coords, origin_lat, origin_lon)
            if result is not None:
                buildings.append(result)

        elif "highway" in props:
            result = _parse_highway_feature(way_id, props, geom_type, coords, origin_lat, origin_lon)
            if result is not None:
                roads.append(result)

        elif props.get("natural") == "water" or "waterway" in props:
            result = _parse_water_feature(way_id, props, geom_type, coords, origin_lat, origin_lon)
            if result is not None:
                water.append(result)

        elif (
            props.get("natural") in ("wood", "forest")
            or props.get("landuse") in ("forest", "grass")
            or props.get("leisure") == "park"
        ):
            result = _parse_natural_feature(way_id, props, geom_type, coords, origin_lat, origin_lon)
            if result is not None:
                natural_features.append(result)

    return buildings, roads, water, natural_features


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def build_environment_from_geojson(
    geojson_str: str,
    origin_lat: float,
    origin_lon: float,
    default_building_height: float = 8.0,
    road_z: float = 0.0,
    water_z: float = -0.1,
) -> EnvironmentMesh:
    """Build an EnvironmentMesh from a GeoJSON FeatureCollection string.

    This is the main pipeline entry point:
    1. Parse GeoJSON -> Building, Road, WaterBody, NaturalFeature lists
    2. Generate geometry for each feature
    3. Combine into a single EnvironmentMesh

    Args:
        geojson_str: GeoJSON FeatureCollection as a JSON string.
        origin_lat: Latitude of the local coordinate origin.
        origin_lon: Longitude of the local coordinate origin.
        default_building_height: Fallback height when no height tag is present.
        road_z: Z coordinate for road surfaces.
        water_z: Z coordinate for water surfaces (slightly below ground).

    Returns:
        EnvironmentMesh with all features combined.
    """
    buildings, roads, water_bodies, _natural = parse_geojson(geojson_str, origin_lat, origin_lon)

    all_verts: list[np.ndarray] = []
    all_tris: list[np.ndarray] = []
    all_mats: list[np.ndarray] = []
    vert_offset = 0

    # Buildings
    for bld in buildings:
        try:
            v, t, m = generate_building(
                footprint=bld.footprint,
                height=bld.height,
                roof_shape=bld.roof_shape,
                roof_height=bld.roof_height,
                material=bld.material,
                roof_material=bld.roof_material,
            )
        except Exception:
            try:
                v, t, m = generate_building(
                    footprint=bld.footprint,
                    height=bld.height,
                    roof_shape="flat",
                    roof_height=0.0,
                    material=bld.material,
                    roof_material=bld.roof_material,
                )
            except Exception:
                continue

        if len(v) == 0 or len(t) == 0:
            continue

        all_verts.append(v)
        all_tris.append(t + vert_offset)
        all_mats.append(m)
        vert_offset += len(v)

    # Roads
    for road in roads:
        v, t, m = _road_to_mesh(road, z=road_z)
        if len(v) == 0 or len(t) == 0:
            continue
        all_verts.append(v)
        all_tris.append(t + vert_offset)
        all_mats.append(m)
        vert_offset += len(v)

    # Water bodies
    for wb in water_bodies:
        v, t, m = _water_to_mesh(wb, z=water_z)
        if len(v) == 0 or len(t) == 0:
            continue
        all_verts.append(v)
        all_tris.append(t + vert_offset)
        all_mats.append(m)
        vert_offset += len(v)

    if not all_verts:
        vertices = np.empty((0, 3), dtype=np.float64)
        triangles = np.empty((0, 3), dtype=np.uint32)
        normals = np.empty((0, 3), dtype=np.float64)
        materials = np.empty(0, dtype=np.int32)
    else:
        vertices = np.concatenate(all_verts, axis=0)
        triangles = np.concatenate(all_tris, axis=0).astype(np.uint32)
        materials = np.concatenate(all_mats, axis=0).astype(np.int32)
        normals = _compute_face_normals(vertices, triangles)

    return EnvironmentMesh(
        vertices=vertices,
        triangles=triangles,
        normals=normals,
        materials=materials,
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        source="geojson",
    )
