"""OSM multipolygon and building-relation assembly.

Public API:
    assemble_multipolygon(members, ways, nodes) -> (outer_rings, inner_rings)
    parse_relations(xml_str, origin_lat, origin_lon) -> RelationParseResult
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

import numpy as np

# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class MultipolygonBuilding:
    """A building parsed from an OSM multipolygon relation."""

    relation_id: int
    outer_rings: list[np.ndarray]  # each (N, 2) float64
    inner_rings: list[np.ndarray]  # each (N, 2) float64
    height: float = 8.0
    roof_shape: str = "flat"
    material: object = None  # MaterialType, resolved lazily
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class BuildingWithParts:
    """A building parsed from an OSM building relation (outline + parts)."""

    relation_id: int
    outline: np.ndarray | None  # (N, 2) float64, or None
    parts: list  # list of Building instances
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class RelationParseResult:
    """Result of parsing OSM relations from an XML string."""

    multipolygons: list[MultipolygonBuilding] = field(default_factory=list)
    building_parts: list[BuildingWithParts] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Ring assembly
# ---------------------------------------------------------------------------


def _ring_from_closed_way(node_ids: list[int], nodes: dict) -> np.ndarray | None:
    """Build an (N, 2) ring from a closed way.  Returns None if invalid."""
    # Drop closing duplicate
    ids = node_ids[:-1]
    coords = [[nodes[nid][0], nodes[nid][1]] for nid in ids if nid in nodes]
    if len(coords) < 3:
        return None
    return np.array(coords, dtype=np.float64)


def _ways_to_rings(
    way_node_lists: list[list[int]],
    nodes: dict,
) -> list[np.ndarray]:
    """Convert a list of ways (each a list of node IDs) into closed rings.

    Closed ways are returned directly.  Open ways are chained at shared
    endpoints until a closed ring is formed.
    """
    closed: list[list[int]] = []
    open_segs: list[list[int]] = []

    for nids in way_node_lists:
        if len(nids) >= 4 and nids[0] == nids[-1]:
            closed.append(nids)
        else:
            open_segs.append(list(nids))

    rings: list[np.ndarray] = []

    # Convert already-closed ways
    for nids in closed:
        ring = _ring_from_closed_way(nids, nodes)
        if ring is not None:
            rings.append(ring)

    # Chain open segments into closed rings
    remaining = [list(s) for s in open_segs]
    while remaining:
        chain = remaining.pop(0)
        changed = True
        while changed:
            changed = False
            for i, seg in enumerate(remaining):
                if chain[-1] == seg[0]:
                    chain = chain + seg[1:]
                    remaining.pop(i)
                    changed = True
                    break
                if chain[-1] == seg[-1]:
                    chain = chain + seg[-2::-1]
                    remaining.pop(i)
                    changed = True
                    break
                if chain[0] == seg[-1]:
                    chain = seg[:-1] + chain
                    remaining.pop(i)
                    changed = True
                    break
                if chain[0] == seg[0]:
                    chain = seg[::-1][:-1] + chain
                    remaining.pop(i)
                    changed = True
                    break
            # Check if chain closed itself
            if chain[0] == chain[-1]:
                break

        if chain[0] == chain[-1] and len(chain) >= 4:
            ring = _ring_from_closed_way(chain, nodes)
            if ring is not None:
                rings.append(ring)
        # If chain never closed, skip (malformed data)

    return rings


def assemble_multipolygon(
    members: list[dict],
    ways: dict[int, list[int]],
    nodes: dict[int, tuple[float, float]],
) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """Assemble outer and inner rings for a multipolygon relation.

    Args:
        members: List of dicts with keys ``ref`` (int) and ``role`` (str).
        ways: Mapping from way ID to ordered list of node IDs.
        nodes: Mapping from node ID to (x, y) coordinates (any 2-D space;
               callers may pass projected meters or raw lat/lon).

    Returns:
        ``(outer_rings, inner_rings)`` where each ring is an ``(N, 2)``
        float64 array with the closing node already removed.
    """
    outer_way_ids: list[int] = []
    inner_way_ids: list[int] = []

    for m in members:
        ref = int(m["ref"])
        role = m.get("role", "outer")
        if role == "outer":
            outer_way_ids.append(ref)
        elif role == "inner":
            inner_way_ids.append(ref)

    outer_node_lists = [ways[wid] for wid in outer_way_ids if wid in ways]
    inner_node_lists = [ways[wid] for wid in inner_way_ids if wid in ways]

    outer_rings = _ways_to_rings(outer_node_lists, nodes)
    inner_rings = _ways_to_rings(inner_node_lists, nodes)

    return outer_rings, inner_rings


# ---------------------------------------------------------------------------
# XML parsing
# ---------------------------------------------------------------------------


def _parse_tags_from_elem(elem: ET.Element) -> dict[str, str]:
    return {t.attrib["k"]: t.attrib["v"] for t in elem.findall("tag")}


def _node_refs_from_way(way_elem: ET.Element) -> list[int]:
    return [int(nd.attrib["ref"]) for nd in way_elem.findall("nd")]


def parse_relations(
    xml_str: str,
    origin_lat: float = 0.0,
    origin_lon: float = 0.0,
) -> RelationParseResult:
    """Parse OSM XML and extract multipolygon and building relations.

    Coordinates are projected to local XY metres via Transverse Mercator
    relative to ``(origin_lat, origin_lon)``.

    Args:
        xml_str: Raw OSM XML string.
        origin_lat: Latitude of the local coordinate origin.
        origin_lon: Longitude of the local coordinate origin.

    Returns:
        :class:`RelationParseResult` with ``.multipolygons`` and
        ``.building_parts`` lists.
    """
    # Lazy imports to avoid circular dependency (osm.py will later import us)
    from aegis.environment.geo import transverse_mercator_forward
    from aegis.environment.osm import (
        Building,
        _parse_building_material,
        _parse_height,
        _parse_roof_shape,
    )

    root = ET.fromstring(xml_str)

    # Build node lookup: id -> (lat, lon)
    raw_nodes: dict[int, tuple[float, float]] = {}
    for node_elem in root.findall("node"):
        nid = int(node_elem.attrib["id"])
        lat = float(node_elem.attrib["lat"])
        lon = float(node_elem.attrib["lon"])
        raw_nodes[nid] = (lat, lon)

    # Auto-origin from centroid if not provided
    if origin_lat == 0.0 and origin_lon == 0.0 and raw_nodes:
        lats = [v[0] for v in raw_nodes.values()]
        lons = [v[1] for v in raw_nodes.values()]
        origin_lat = float(np.mean(lats))
        origin_lon = float(np.mean(lons))

    # Project all nodes to local XY metres
    proj_nodes: dict[int, tuple[float, float]] = {}
    for nid, (lat, lon) in raw_nodes.items():
        x, y = transverse_mercator_forward(lat, lon, origin_lat, origin_lon)
        proj_nodes[nid] = (x, y)

    # Build way lookup: id -> [node_ids]
    ways: dict[int, list[int]] = {}
    way_elems: dict[int, ET.Element] = {}
    for way_elem in root.findall("way"):
        wid = int(way_elem.attrib["id"])
        ways[wid] = _node_refs_from_way(way_elem)
        way_elems[wid] = way_elem

    result = RelationParseResult()

    for rel_elem in root.findall("relation"):
        rel_id = int(rel_elem.attrib["id"])
        tags = _parse_tags_from_elem(rel_elem)
        rel_type = tags.get("type", "")

        members = [
            {
                "ref": int(m.attrib["ref"]),
                "role": m.attrib.get("role", "outer"),
                "type": m.attrib.get("type", "way"),
            }
            for m in rel_elem.findall("member")
        ]

        if rel_type == "multipolygon":
            outer_rings, inner_rings = assemble_multipolygon(members, ways, proj_nodes)
            if not outer_rings:
                continue

            building_type = tags.get("building", "yes")
            height = _parse_height(tags, building_type)
            roof_shape = _parse_roof_shape(tags)
            material = _parse_building_material(tags)

            result.multipolygons.append(
                MultipolygonBuilding(
                    relation_id=rel_id,
                    outer_rings=outer_rings,
                    inner_rings=inner_rings,
                    height=height,
                    roof_shape=roof_shape,
                    material=material,
                    tags=tags,
                )
            )

        elif rel_type == "building":
            # Separate outline from parts
            outline_fp: np.ndarray | None = None
            parts: list[Building] = []

            for m in members:
                if m["type"] != "way":
                    continue
                wid = m["ref"]
                role = m["role"]

                if wid not in ways:
                    continue

                node_ids = ways[wid]
                is_closed = len(node_ids) >= 4 and node_ids[0] == node_ids[-1]

                if role == "outline" and is_closed:
                    coords = [list(proj_nodes[nid]) for nid in node_ids[:-1] if nid in proj_nodes]
                    if len(coords) >= 3:
                        outline_fp = np.array(coords, dtype=np.float64)

                elif role == "part" and is_closed and wid in way_elems:
                    part_elem = way_elems[wid]
                    part_tags = _parse_tags_from_elem(part_elem)
                    part_type = part_tags.get("building:part", "yes")
                    # Fallback to relation-level building type for height heuristic
                    part_building_type = part_tags.get("building", part_type)
                    part_height = _parse_height(part_tags, part_building_type)
                    part_roof = _parse_roof_shape(part_tags)
                    part_mat = _parse_building_material(part_tags)

                    coords = [list(proj_nodes[nid]) for nid in node_ids[:-1] if nid in proj_nodes]
                    if len(coords) >= 3:
                        fp = np.array(coords, dtype=np.float64)
                        parts.append(
                            Building(
                                way_id=wid,
                                footprint=fp,
                                height=part_height,
                                roof_shape=part_roof,
                                material=part_mat,
                            )
                        )

            result.building_parts.append(
                BuildingWithParts(
                    relation_id=rel_id,
                    outline=outline_fp,
                    parts=parts,
                    tags=tags,
                )
            )

    return result
