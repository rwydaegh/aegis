"""Tests for OSM multipolygon and building-relation assembly."""

from pathlib import Path

import numpy as np
import pytest

from aegis.environment.relations import (
    RelationParseResult,
    assemble_multipolygon,
    parse_relations,
)

FIXTURE = Path(__file__).parent / "fixtures" / "osm_multipolygon.xml"


# ---------------------------------------------------------------------------
# Unit tests for assemble_multipolygon
# ---------------------------------------------------------------------------


class TestAssembleClosedWays:
    """Single closed way stays as-is (no open-way joining needed)."""

    def test_single_closed_way_returns_one_outer(self):
        # A square: nodes 0-3, closed (node 0 repeated at end)
        ways = {
            10: [0, 1, 2, 3, 0],
        }
        nodes = {
            0: (0.0, 0.0),
            1: (1.0, 0.0),
            2: (1.0, 1.0),
            3: (0.0, 1.0),
        }
        members = [{"ref": 10, "role": "outer"}]
        outers, inners = assemble_multipolygon(members, ways, nodes)
        assert len(outers) == 1
        assert len(inners) == 0
        assert outers[0].shape == (4, 2)  # closing node dropped

    def test_ring_coords_are_float64(self):
        ways = {10: [0, 1, 2, 3, 0]}
        nodes = {0: (0.0, 0.0), 1: (1.0, 0.0), 2: (1.0, 1.0), 3: (0.0, 1.0)}
        members = [{"ref": 10, "role": "outer"}]
        outers, _ = assemble_multipolygon(members, ways, nodes)
        assert outers[0].dtype == np.float64


class TestAssembleOpenWays:
    """Two open ways sharing endpoint nodes get joined into a closed ring."""

    def test_two_open_ways_joined(self):
        # Way A: 0 -> 1 -> 2, Way B: 2 -> 3 -> 0  =>  ring [0,1,2,3]
        ways = {
            10: [0, 1, 2],
            11: [2, 3, 0],
        }
        nodes = {
            0: (0.0, 0.0),
            1: (0.5, 0.0),
            2: (1.0, 0.0),
            3: (1.0, 1.0),
        }
        members = [
            {"ref": 10, "role": "outer"},
            {"ref": 11, "role": "outer"},
        ]
        outers, inners = assemble_multipolygon(members, ways, nodes)
        assert len(outers) == 1
        assert len(inners) == 0
        # 4 unique nodes (closing duplicate is dropped)
        assert outers[0].shape[0] == 4

    def test_open_ways_result_has_min_three_points(self):
        ways = {10: [0, 1, 2], 11: [2, 3, 0]}
        nodes = {0: (0.0, 0.0), 1: (0.5, 0.0), 2: (1.0, 0.0), 3: (1.0, 1.0)}
        members = [{"ref": 10, "role": "outer"}, {"ref": 11, "role": "outer"}]
        outers, _ = assemble_multipolygon(members, ways, nodes)
        assert outers[0].shape[0] >= 3


class TestAssembleWithHole:
    """Outer + inner ways produce separate ring lists."""

    def test_outer_and_inner_separated(self):
        # Outer square
        ways = {
            10: [0, 1, 2, 3, 0],
            # Inner (courtyard) square
            20: [4, 5, 6, 7, 4],
        }
        nodes = {
            0: (0.0, 0.0),
            1: (4.0, 0.0),
            2: (4.0, 4.0),
            3: (0.0, 4.0),
            4: (1.0, 1.0),
            5: (3.0, 1.0),
            6: (3.0, 3.0),
            7: (1.0, 3.0),
        }
        members = [
            {"ref": 10, "role": "outer"},
            {"ref": 20, "role": "inner"},
        ]
        outers, inners = assemble_multipolygon(members, ways, nodes)
        assert len(outers) == 1
        assert len(inners) == 1

    def test_inner_ring_has_coords(self):
        ways = {10: [0, 1, 2, 3, 0], 20: [4, 5, 6, 7, 4]}
        nodes = {
            0: (0.0, 0.0),
            1: (4.0, 0.0),
            2: (4.0, 4.0),
            3: (0.0, 4.0),
            4: (1.0, 1.0),
            5: (3.0, 1.0),
            6: (3.0, 3.0),
            7: (1.0, 3.0),
        }
        members = [{"ref": 10, "role": "outer"}, {"ref": 20, "role": "inner"}]
        _, inners = assemble_multipolygon(members, ways, nodes)
        assert inners[0].shape == (4, 2)


# ---------------------------------------------------------------------------
# Integration tests using the XML fixture
# ---------------------------------------------------------------------------


class TestParseRelationsFromXml:
    """Full XML parsing returns correct multipolygon structures."""

    def setup_method(self):
        self.xml = FIXTURE.read_text()
        # Use approximate centre of the fixture area as origin
        self.result = parse_relations(self.xml, origin_lat=51.051, origin_lon=3.721)

    def test_returns_relation_parse_result(self):
        assert isinstance(self.result, RelationParseResult)

    def test_multipolygon_with_courtyard_found(self):
        # Relation 3001: building with courtyard
        mp_ids = [m.relation_id for m in self.result.multipolygons]
        assert 3001 in mp_ids

    def test_multipolygon_has_outer_and_inner_rings(self):
        mp = next(m for m in self.result.multipolygons if m.relation_id == 3001)
        assert len(mp.outer_rings) >= 1
        assert len(mp.inner_rings) >= 1

    def test_multipolygon_height_parsed(self):
        mp = next(m for m in self.result.multipolygons if m.relation_id == 3001)
        assert mp.height == pytest.approx(15.0)

    def test_multipolygon_material_parsed(self):
        from aegis.environment import MaterialType

        mp = next(m for m in self.result.multipolygons if m.relation_id == 3001)
        assert mp.material == MaterialType.BRICK

    def test_open_way_multipolygon_assembled(self):
        # Relation 7001: two open ways joined into one ring
        mp = next(m for m in self.result.multipolygons if m.relation_id == 7001)
        assert len(mp.outer_rings) == 1
        assert mp.outer_rings[0].shape[0] >= 3

    def test_ring_coords_are_ndarray(self):
        for mp in self.result.multipolygons:
            for ring in mp.outer_rings + mp.inner_rings:
                assert isinstance(ring, np.ndarray)
                assert ring.shape[1] == 2


TOWER_XML = """<?xml version="1.0"?>
<osm version="0.6">
  <node id="1" lat="51.0500" lon="3.7200"/>
  <node id="2" lat="51.0500" lon="3.7206"/>
  <node id="3" lat="51.0504" lon="3.7206"/>
  <node id="4" lat="51.0504" lon="3.7200"/>
  <node id="5" lat="51.0504" lon="3.7206"/>
  <node id="6" lat="51.0504" lon="3.7212"/>
  <node id="7" lat="51.0508" lon="3.7212"/>
  <node id="8" lat="51.0508" lon="3.7206"/>
  <way id="10">
    <nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="4"/><nd ref="1"/>
    <tag k="building:part" v="yes"/>
    <tag k="height" v="120"/>
    <tag k="building:material" v="glass"/>
  </way>
  <way id="11">
    <nd ref="5"/><nd ref="6"/><nd ref="7"/><nd ref="8"/><nd ref="5"/>
    <tag k="building:part" v="yes"/>
    <tag k="height" v="20"/>
    <tag k="roof:shape" v="pyramidal"/>
    <tag k="roof:height" v="5"/>
  </way>
  <relation id="100">
    <member type="way" ref="10" role="part"/>
    <member type="way" ref="11" role="part"/>
    <tag k="type" v="building"/>
    <tag k="building" v="yes"/>
  </relation>
</osm>"""


class TestPartTagsParsed:
    """Relation member parts carry their own height/roof/material tags.

    Regression for the Overpass `out skel qt` defect: member ways used to
    arrive without tags, so every tower part collapsed to an 8 m flat
    concrete default.
    """

    def setup_method(self):
        self.result = parse_relations(TOWER_XML, origin_lat=51.0504, origin_lon=3.7206)
        bwp = next(b for b in self.result.building_parts if b.relation_id == 100)
        self.parts = {p.way_id: p for p in bwp.parts}

    def test_tower_part_height(self):
        assert self.parts[10].height == pytest.approx(120.0)

    def test_tower_part_material(self):
        from aegis.environment import MaterialType

        assert self.parts[10].material == MaterialType.GLASS

    def test_part_tags_carried(self):
        assert self.parts[10].tags.get("building:part") == "yes"

    def test_pyramidal_part_height_is_eave(self):
        # height=20 total, roof:height=5 -> walls to 15, peak back at 20
        p = self.parts[11]
        assert p.roof_shape == "pyramidal"
        assert p.height == pytest.approx(15.0)
        assert p.roof_height == pytest.approx(5.0)

    def test_skel_duplicate_does_not_shadow_tags(self):
        # Overpass may print the member way a second time without tags via
        # the recursion; the tagged copy must win regardless of order.
        skel = '<way id="10">\n    <nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="4"/><nd ref="1"/>\n  </way>'
        xml = TOWER_XML.replace("</osm>", skel + "\n</osm>")
        result = parse_relations(xml, origin_lat=51.0504, origin_lon=3.7206)
        bwp = next(b for b in result.building_parts if b.relation_id == 100)
        parts = {p.way_id: p for p in bwp.parts}
        assert parts[10].height == pytest.approx(120.0)


class TestMultipolygonHeightSplit:
    def test_gabled_multipolygon_height_is_eave(self):
        xml = """<?xml version="1.0"?>
        <osm version="0.6">
          <node id="1" lat="51.0500" lon="3.7200"/>
          <node id="2" lat="51.0500" lon="3.7206"/>
          <node id="3" lat="51.0504" lon="3.7206"/>
          <node id="4" lat="51.0504" lon="3.7200"/>
          <way id="10">
            <nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="4"/><nd ref="1"/>
          </way>
          <relation id="200">
            <member type="way" ref="10" role="outer"/>
            <tag k="type" v="multipolygon"/>
            <tag k="building" v="yes"/>
            <tag k="height" v="16"/>
            <tag k="roof:shape" v="gabled"/>
          </relation>
        </osm>"""
        result = parse_relations(xml, origin_lat=51.0502, origin_lon=3.7203)
        mp = next(m for m in result.multipolygons if m.relation_id == 200)
        # 16 m total, default roof span max(2, 0.25 * 16) = 4 -> eave 12
        assert mp.height == pytest.approx(12.0)
        assert mp.roof_height == pytest.approx(4.0)


class TestBuildingWithParts:
    """Building relation with outline + parts at different heights."""

    def setup_method(self):
        self.xml = FIXTURE.read_text()
        self.result = parse_relations(self.xml, origin_lat=51.051, origin_lon=3.721)

    def test_building_relation_found(self):
        part_ids = [b.relation_id for b in self.result.building_parts]
        assert 5001 in part_ids

    def test_building_has_outline(self):
        bwp = next(b for b in self.result.building_parts if b.relation_id == 5001)
        assert bwp.outline is not None
        assert bwp.outline.shape[1] == 2

    def test_building_has_two_parts(self):
        bwp = next(b for b in self.result.building_parts if b.relation_id == 5001)
        assert len(bwp.parts) == 2

    def test_parts_have_different_heights(self):
        bwp = next(b for b in self.result.building_parts if b.relation_id == 5001)
        heights = [p.height for p in bwp.parts]
        assert sorted(heights) == pytest.approx([8.0, 20.0])

    def test_parts_are_building_instances(self):
        from aegis.environment.osm import Building

        bwp = next(b for b in self.result.building_parts if b.relation_id == 5001)
        for part in bwp.parts:
            assert isinstance(part, Building)
