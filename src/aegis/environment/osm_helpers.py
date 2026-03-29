"""Shared helpers for OSM and GeoJSON data pipelines.

Extracted from osm.py to break circular imports between osm.py and relations.py.

Public names re-exported from osm.py for backward compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from aegis.environment import MaterialType

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
    tags: dict = field(default_factory=dict)


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
# Tag parsing helpers
# ---------------------------------------------------------------------------


def _parse_tags(way_elem: object) -> dict[str, str]:
    """Extract all <tag> elements from a way into a dict."""
    return {tag.attrib["k"]: tag.attrib["v"] for tag in way_elem.findall("tag")}  # type: ignore[union-attr]


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
