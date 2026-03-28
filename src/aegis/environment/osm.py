"""OSM data pipeline: fetch, parse, and convert to EnvironmentMesh.

Public API:
    fetch_osm(lat, lon, radius_m) -> str
    parse_osm_xml(xml_str, origin_lat, origin_lon) -> (buildings, roads, water)
    build_environment_from_osm(xml_str, origin_lat, origin_lon, ...) -> EnvironmentMesh
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass

import numpy as np

from aegis.environment import EnvironmentMesh, MaterialType
from aegis.environment.geo import transverse_mercator_forward
from aegis.environment.roofs import generate_building, triangulate_polygon

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class OverpassRateLimitError(RuntimeError):
    """Overpass API returned HTTP 429 or indicated rate limiting."""


class OverpassTimeoutError(RuntimeError):
    """Overpass API query timed out."""


class OverpassResponseTooLarge(RuntimeError):
    """Overpass API response exceeded size limit."""


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Building:
    """A building extracted from OSM."""

    way_id: int
    footprint: np.ndarray  # (N, 2) local XY coords in meters
    height: float = 8.0
    roof_shape: str = "flat"
    roof_height: float = 2.0
    material: MaterialType = MaterialType.CONCRETE
    roof_material: MaterialType = MaterialType.CONCRETE


@dataclass
class Road:
    """A road (highway) extracted from OSM."""

    way_id: int
    centerline: np.ndarray  # (N, 2) local XY coords in meters
    highway_type: str = "residential"
    width: float = 6.0  # meters
    lanes: int = 1


@dataclass
class WaterBody:
    """A water polygon extracted from OSM."""

    way_id: int
    footprint: np.ndarray  # (N, 2) local XY coords in meters
    water_type: str = "water"


# ---------------------------------------------------------------------------
# Material tag mappings
# ---------------------------------------------------------------------------

_BUILDING_MATERIAL_MAP: dict[str, MaterialType] = {
    "brick": MaterialType.BRICK,
    "bricks": MaterialType.BRICK,
    "concrete": MaterialType.CONCRETE,
    "glass": MaterialType.GLASS,
    "metal": MaterialType.METAL,
    "steel": MaterialType.METAL,
    "wood": MaterialType.WOOD,
    "timber": MaterialType.WOOD,
}

_HIGHWAY_WIDTH: dict[str, float] = {
    "motorway": 14.0,
    "trunk": 12.0,
    "primary": 10.0,
    "secondary": 8.0,
    "tertiary": 7.0,
    "residential": 6.0,
    "service": 4.0,
    "footway": 2.0,
    "cycleway": 2.0,
    "path": 1.5,
    "track": 3.0,
    "unclassified": 6.0,
}

# Default building heights by type when no explicit height tag is present
_BUILDING_TYPE_HEIGHT: dict[str, float] = {
    "house": 7.0,
    "detached": 7.0,
    "residential": 9.0,
    "apartments": 15.0,
    "office": 20.0,
    "commercial": 10.0,
    "retail": 5.0,
    "industrial": 8.0,
    "warehouse": 8.0,
    "garage": 3.0,
    "yes": 8.0,
}

# ---------------------------------------------------------------------------
# Overpass API fetch
# ---------------------------------------------------------------------------

_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
_MAX_RESPONSE_BYTES = 50 * 1024 * 1024  # 50 MB


def fetch_osm(
    lat: float,
    lon: float,
    radius_m: float = 500.0,
    timeout: int = 30,
) -> str:
    """Fetch OSM data from Overpass API for a circular area.

    Args:
        lat: Center latitude in degrees.
        lon: Center longitude in degrees.
        radius_m: Radius in meters.
        timeout: HTTP request timeout in seconds.

    Returns:
        OSM XML string.

    Raises:
        OverpassRateLimitError: If the API returns 429 or indicates rate limiting.
        OverpassTimeoutError: If the query times out.
        OverpassResponseTooLarge: If the response exceeds the size limit.
    """
    import requests

    query = (
        f"[out:xml][timeout:{timeout}];"
        f"("
        f"  way['building'](around:{radius_m},{lat},{lon});"
        f"  way['highway'](around:{radius_m},{lat},{lon});"
        f"  way['natural'='water'](around:{radius_m},{lat},{lon});"
        f"  way['waterway'](around:{radius_m},{lat},{lon});"
        f");"
        f"(._;>;);"
        f"out body;"
    )
    try:
        resp = requests.post(
            _OVERPASS_URL,
            data={"data": query},
            timeout=timeout,
        )
    except requests.exceptions.Timeout as exc:
        raise OverpassTimeoutError(f"Overpass request timed out after {timeout}s") from exc

    if resp.status_code == 429:
        raise OverpassRateLimitError("Overpass rate limit exceeded (HTTP 429)")
    if resp.status_code == 504:
        raise OverpassTimeoutError("Overpass gateway timeout (HTTP 504)")
    resp.raise_for_status()

    content = resp.content
    if len(content) > _MAX_RESPONSE_BYTES:
        raise OverpassResponseTooLarge(
            f"Response size {len(content) / 1e6:.1f} MB exceeds limit {_MAX_RESPONSE_BYTES / 1e6:.0f} MB"
        )

    return resp.text


# ---------------------------------------------------------------------------
# XML parsing helpers
# ---------------------------------------------------------------------------


def _parse_tags(way_elem: ET.Element) -> dict[str, str]:
    """Extract all <tag> elements from a way into a dict."""
    return {tag.attrib["k"]: tag.attrib["v"] for tag in way_elem.findall("tag")}


def _node_refs(way_elem: ET.Element) -> list[int]:
    """Extract ordered list of node IDs referenced by a way."""
    return [int(nd.attrib["ref"]) for nd in way_elem.findall("nd")]


def _project_nodes(
    node_ids: list[int],
    nodes: dict[int, tuple[float, float]],
    origin_lat: float,
    origin_lon: float,
) -> np.ndarray:
    """Project a list of node IDs to local XY (meters).

    Returns (N, 2) array. Skips unknown node IDs.
    """
    coords = []
    for nid in node_ids:
        if nid not in nodes:
            continue
        lat, lon = nodes[nid]
        x, y = transverse_mercator_forward(lat, lon, origin_lat, origin_lon)
        coords.append([x, y])
    return np.array(coords, dtype=np.float64)


def _is_closed_way(node_ids: list[int]) -> bool:
    """Check if a way is closed (first node == last node)."""
    return len(node_ids) >= 4 and node_ids[0] == node_ids[-1]


def _footprint_from_way(
    way_elem: ET.Element,
    nodes: dict[int, tuple[float, float]],
    origin_lat: float,
    origin_lon: float,
) -> np.ndarray | None:
    """Return (N, 2) footprint for a closed way, or None if invalid."""
    node_ids = _node_refs(way_elem)
    if not _is_closed_way(node_ids):
        return None
    # Drop closing duplicate node
    coords = _project_nodes(node_ids[:-1], nodes, origin_lat, origin_lon)
    if len(coords) < 3:
        return None
    return coords


def _parse_height(tags: dict[str, str], building_type: str) -> float:
    """Parse height from OSM tags, with fallback to building type defaults."""
    if "height" in tags:
        try:
            return float(tags["height"].split()[0])
        except (ValueError, IndexError):
            pass
    if "building:levels" in tags:
        try:
            return float(tags["building:levels"]) * 3.0
        except ValueError:
            pass
    return _BUILDING_TYPE_HEIGHT.get(building_type, 8.0)


def _parse_roof_shape(tags: dict[str, str]) -> str:
    """Parse roof:shape tag to a supported shape string."""
    shape = tags.get("roof:shape", "flat").lower()
    supported = {
        "flat",
        "gabled",
        "hipped",
        "pyramidal",
        "skillion",
        "half_hipped",
        "gambrel",
        "saltbox",
        "mansard",
        "dome",
        "onion",
        "round",
    }
    if shape in supported:
        return shape
    # Map common aliases
    aliases = {
        "hip": "hipped",
        "pyramid": "pyramidal",
        "shed": "skillion",
    }
    return aliases.get(shape, "flat")


def _parse_building_material(tags: dict[str, str]) -> MaterialType:
    """Parse building:material tag to MaterialType."""
    mat_str = tags.get("building:material", "").lower()
    return _BUILDING_MATERIAL_MAP.get(mat_str, MaterialType.CONCRETE)


# ---------------------------------------------------------------------------
# Public parse function
# ---------------------------------------------------------------------------


def parse_osm_xml(
    xml_str: str,
    origin_lat: float = 0.0,
    origin_lon: float = 0.0,
) -> tuple[list[Building], list[Road], list[WaterBody]]:
    """Parse OSM XML string and return extracted features.

    Coordinates are projected to local XY meters relative to (origin_lat, origin_lon).
    If origin is (0, 0), coordinates are still projected but relative to the null island.
    Callers should pass the actual origin for meaningful metric coordinates.

    Args:
        xml_str: OSM XML string (from Overpass or file).
        origin_lat: Latitude of the local coordinate origin.
        origin_lon: Longitude of the local coordinate origin.

    Returns:
        Tuple of (buildings, roads, water_bodies).
    """
    root = ET.fromstring(xml_str)

    # Build node lookup: id -> (lat, lon)
    nodes: dict[int, tuple[float, float]] = {}
    for node_elem in root.findall("node"):
        nid = int(node_elem.attrib["id"])
        lat = float(node_elem.attrib["lat"])
        lon = float(node_elem.attrib["lon"])
        nodes[nid] = (lat, lon)

    # If no origin provided, use centroid of all nodes to avoid huge coordinates
    if origin_lat == 0.0 and origin_lon == 0.0 and nodes:
        lats = [v[0] for v in nodes.values()]
        lons = [v[1] for v in nodes.values()]
        origin_lat = float(np.mean(lats))
        origin_lon = float(np.mean(lons))

    buildings: list[Building] = []
    roads: list[Road] = []
    water: list[WaterBody] = []

    for way_elem in root.findall("way"):
        way_id = int(way_elem.attrib["id"])
        tags = _parse_tags(way_elem)

        if "building" in tags:
            footprint = _footprint_from_way(way_elem, nodes, origin_lat, origin_lon)
            if footprint is None:
                continue
            building_type = tags.get("building", "yes")
            height = _parse_height(tags, building_type)
            roof_shape = _parse_roof_shape(tags)
            roof_height_str = tags.get("roof:height", None)
            if roof_height_str is not None:
                try:
                    roof_height = float(roof_height_str.split()[0])
                except (ValueError, IndexError):
                    roof_height = max(2.0, height * 0.25)
            else:
                roof_height = max(2.0, height * 0.25)

            material = _parse_building_material(tags)
            roof_material = material  # use same material for roof by default

            buildings.append(
                Building(
                    way_id=way_id,
                    footprint=footprint,
                    height=height,
                    roof_shape=roof_shape,
                    roof_height=roof_height,
                    material=material,
                    roof_material=roof_material,
                )
            )

        elif "highway" in tags:
            node_ids = _node_refs(way_elem)
            centerline = _project_nodes(node_ids, nodes, origin_lat, origin_lon)
            if len(centerline) < 2:
                continue
            highway_type = tags.get("highway", "unclassified")
            width = _HIGHWAY_WIDTH.get(highway_type, 6.0)
            lanes_str = tags.get("lanes", None)
            if lanes_str is not None:
                try:
                    lanes = int(lanes_str)
                except ValueError:
                    lanes = 1
            else:
                lanes = 1
            roads.append(
                Road(
                    way_id=way_id,
                    centerline=centerline,
                    highway_type=highway_type,
                    width=width,
                    lanes=lanes,
                )
            )

        elif "natural" in tags and tags["natural"] == "water":
            footprint = _footprint_from_way(way_elem, nodes, origin_lat, origin_lon)
            if footprint is None:
                continue
            water.append(
                WaterBody(
                    way_id=way_id,
                    footprint=footprint,
                    water_type=tags.get("water", "water"),
                )
            )

        elif "waterway" in tags:
            # Waterway as polygon (reservoir, etc.)
            node_ids = _node_refs(way_elem)
            if _is_closed_way(node_ids):
                footprint = _footprint_from_way(way_elem, nodes, origin_lat, origin_lon)
                if footprint is not None:
                    water.append(
                        WaterBody(
                            way_id=way_id,
                            footprint=footprint,
                            water_type=tags.get("waterway", "waterway"),
                        )
                    )

    return buildings, roads, water


# ---------------------------------------------------------------------------
# Road and water mesh helpers
# ---------------------------------------------------------------------------


def _road_to_mesh(
    road: Road,
    z: float = 0.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Convert a road centerline to a quad-strip mesh.

    Returns (vertices (V,3), triangles (T,3), materials (T,)).
    """
    pts = road.centerline
    n = len(pts)
    half_w = road.width * 0.5

    verts = []
    tris = []

    for i in range(n):
        # Compute perpendicular direction at each point
        if i == 0:
            seg = pts[1] - pts[0]
        elif i == n - 1:
            seg = pts[-1] - pts[-2]
        else:
            seg = pts[i + 1] - pts[i - 1]

        seg_len = np.linalg.norm(seg)
        if seg_len < 1e-10:
            seg_len = 1.0
        perp = np.array([-seg[1], seg[0]]) / seg_len

        left = pts[i] + half_w * perp
        right = pts[i] - half_w * perp
        verts.append([left[0], left[1], z])
        verts.append([right[0], right[1], z])

    # Build quad strips
    for i in range(n - 1):
        li = i * 2
        ri = li + 1
        ln = li + 2
        rn = li + 3
        tris.append([li, ri, rn])
        tris.append([li, rn, ln])

    if not verts:
        return (
            np.empty((0, 3), dtype=np.float64),
            np.empty((0, 3), dtype=np.uint32),
            np.empty(0, dtype=np.int32),
        )

    v = np.array(verts, dtype=np.float64)
    t = np.array(tris, dtype=np.uint32)
    m = np.full(len(t), int(MaterialType.ASPHALT), dtype=np.int32)
    return v, t, m


def _water_to_mesh(
    wb: WaterBody,
    z: float = -0.1,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Convert a water body footprint to a flat triangulated mesh.

    Returns (vertices (V,3), triangles (T,3), materials (T,)).
    """
    fp = wb.footprint
    tris_2d = triangulate_polygon(fp)
    if len(tris_2d) == 0:
        return (
            np.empty((0, 3), dtype=np.float64),
            np.empty((0, 3), dtype=np.uint32),
            np.empty(0, dtype=np.int32),
        )
    n = len(fp)
    verts = np.zeros((n, 3), dtype=np.float64)
    verts[:, :2] = fp
    verts[:, 2] = z
    mats = np.full(len(tris_2d), int(MaterialType.WATER), dtype=np.int32)
    return verts, tris_2d, mats


# ---------------------------------------------------------------------------
# Face normals
# ---------------------------------------------------------------------------


def _compute_face_normals(
    vertices: np.ndarray,
    triangles: np.ndarray,
) -> np.ndarray:
    """Compute per-face unit normals.

    Args:
        vertices: (V, 3) float64 array.
        triangles: (T, 3) uint32 array.

    Returns:
        (T, 3) float64 array of unit normals.
    """
    v0 = vertices[triangles[:, 0]]
    v1 = vertices[triangles[:, 1]]
    v2 = vertices[triangles[:, 2]]
    e1 = v1 - v0
    e2 = v2 - v0
    normals = np.cross(e1, e2)
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    # Avoid division by zero for degenerate triangles
    lengths = np.where(lengths < 1e-12, 1.0, lengths)
    return normals / lengths


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def build_environment_from_osm(
    xml_str: str,
    origin_lat: float,
    origin_lon: float,
    default_building_height: float = 8.0,
    road_z: float = 0.0,
    water_z: float = -0.1,
) -> EnvironmentMesh:
    """Build an EnvironmentMesh from an OSM XML string.

    This is the main pipeline entry point:
    1. Parse XML -> Building, Road, WaterBody lists
    2. Generate geometry for each feature
    3. Combine into a single EnvironmentMesh

    Args:
        xml_str: OSM XML string.
        origin_lat: Latitude of the local coordinate origin.
        origin_lon: Longitude of the local coordinate origin.
        default_building_height: Fallback height when no height tag is present.
        road_z: Z coordinate for road surfaces.
        water_z: Z coordinate for water surfaces (slightly below ground).

    Returns:
        EnvironmentMesh with all features combined.
    """
    buildings, roads, water_bodies = parse_osm_xml(xml_str, origin_lat, origin_lon)

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
            # Fallback: flat roof if roof generation fails
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
        # Return empty mesh if no geometry was generated
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
        source="osm",
    )
