"""Tests for the OSM data pipeline."""

from pathlib import Path

import numpy as np
import pytest

from aegis.environment import EnvironmentMesh, MaterialType
from aegis.environment.osm import build_environment_from_osm, fetch_osm, parse_osm_xml

FIXTURE = Path(__file__).parent / "fixtures" / "osm_sample.xml"
MULTIPOLYGON_FIXTURE = Path(__file__).parent / "fixtures" / "osm_multipolygon.xml"


class TestParseOsmXml:
    def test_extracts_buildings(self):
        buildings, roads, water = parse_osm_xml(FIXTURE.read_text())
        assert len(buildings) >= 2

    def test_building_has_footprint(self):
        buildings, _, _ = parse_osm_xml(FIXTURE.read_text())
        for b in buildings:
            assert b.footprint.shape[1] == 2
            assert len(b.footprint) >= 3

    def test_building_material_tag(self):
        buildings, _, _ = parse_osm_xml(FIXTURE.read_text())
        brick_buildings = [b for b in buildings if b.material == MaterialType.BRICK]
        assert len(brick_buildings) >= 1

    def test_extracts_roads(self):
        _, roads, _ = parse_osm_xml(FIXTURE.read_text())
        assert len(roads) >= 1

    def test_extracts_water(self):
        _, _, water = parse_osm_xml(FIXTURE.read_text())
        assert len(water) >= 1

    def test_building_height_parsed(self):
        buildings, _, _ = parse_osm_xml(FIXTURE.read_text())
        heights = [b.height for b in buildings]
        assert any(h > 0 for h in heights)

    def test_roof_shape_parsed(self):
        buildings, _, _ = parse_osm_xml(FIXTURE.read_text())
        shapes = [b.roof_shape for b in buildings]
        assert "gabled" in shapes

    def test_road_has_coordinates(self):
        _, roads, _ = parse_osm_xml(FIXTURE.read_text())
        for r in roads:
            assert r.centerline.shape[1] == 2
            assert len(r.centerline) >= 2

    def test_water_has_footprint(self):
        _, _, water = parse_osm_xml(FIXTURE.read_text())
        for w in water:
            assert w.footprint.shape[1] == 2
            assert len(w.footprint) >= 3


class TestBuildEnvironment:
    def test_produces_environment_mesh(self):
        xml = FIXTURE.read_text()
        mesh = build_environment_from_osm(xml, origin_lat=51.05, origin_lon=3.72)
        assert isinstance(mesh, EnvironmentMesh)
        assert mesh.vertices.shape[1] == 3
        assert mesh.triangles.shape[1] == 3
        assert len(mesh.materials) == len(mesh.triangles)
        assert mesh.source == "osm"

    def test_contains_multiple_materials(self):
        xml = FIXTURE.read_text()
        mesh = build_environment_from_osm(xml, origin_lat=51.05, origin_lon=3.72)
        unique_mats = set(mesh.materials.tolist())
        assert len(unique_mats) >= 2

    def test_origin_stored(self):
        xml = FIXTURE.read_text()
        mesh = build_environment_from_osm(xml, origin_lat=51.05, origin_lon=3.72)
        assert abs(mesh.origin_lat - 51.05) < 1e-6
        assert abs(mesh.origin_lon - 3.72) < 1e-6

    def test_normals_shape(self):
        xml = FIXTURE.read_text()
        mesh = build_environment_from_osm(xml, origin_lat=51.05, origin_lon=3.72)
        assert mesh.normals.shape == mesh.triangles.shape

    def test_normals_unit_length(self):
        xml = FIXTURE.read_text()
        mesh = build_environment_from_osm(xml, origin_lat=51.05, origin_lon=3.72)
        norms = np.linalg.norm(mesh.normals, axis=1)
        assert np.allclose(norms, 1.0, atol=1e-6)

    def test_no_degenerate_triangles(self):
        xml = FIXTURE.read_text()
        mesh = build_environment_from_osm(xml, origin_lat=51.05, origin_lon=3.72)
        v = mesh.vertices
        t = mesh.triangles
        for tri in t:
            a, b, c = v[tri[0]], v[tri[1]], v[tri[2]]
            area = 0.5 * np.linalg.norm(np.cross(b - a, c - a))
            assert area > 1e-12, f"Degenerate triangle: area={area}"

    def test_water_material_present(self):
        xml = FIXTURE.read_text()
        mesh = build_environment_from_osm(xml, origin_lat=51.05, origin_lon=3.72)
        assert int(MaterialType.WATER) in mesh.materials.tolist()


class TestDetailFlag:
    def test_build_osm_with_detail_flag(self):
        """detail=True should produce more triangles than detail=False."""
        xml = FIXTURE.read_text()
        mesh_simple = build_environment_from_osm(xml, 51.05, 3.72, detail=False)
        mesh_detail = build_environment_from_osm(xml, 51.05, 3.72, detail=True)
        assert mesh_detail.triangles.shape[0] > mesh_simple.triangles.shape[0]


class TestRelationsIntegration:
    def test_parse_osm_with_multipolygon_building(self):
        """Buildings from multipolygon relations should appear in output."""
        xml = MULTIPOLYGON_FIXTURE.read_text()
        mesh = build_environment_from_osm(xml, origin_lat=51.05, origin_lon=3.72)
        assert mesh.triangles.shape[0] > 0  # should have geometry from relations

    def test_building_parts_in_mesh(self):
        """Building parts with different heights produce distinct geometry."""
        xml = MULTIPOLYGON_FIXTURE.read_text()
        mesh = build_environment_from_osm(xml, origin_lat=51.05, origin_lon=3.72)
        z_max = mesh.vertices[:, 2].max()
        assert z_max > 10  # tallest part is 15m + roof


class TestFetchOsmMirrorFailover:
    """Unit tests for the mirror failover logic in fetch_osm.

    These avoid hitting the network by mocking requests.post.
    """

    def _fake_response(self, status_code: int, text: str = ""):
        from unittest.mock import MagicMock

        resp = MagicMock()
        resp.status_code = status_code
        resp.ok = 200 <= status_code < 300
        resp.text = text
        resp.content = text.encode() if text else b""
        return resp

    def test_http_error_on_all_mirrors_raises_overpass_http_error(self):
        """A non-(429/5xx/403) HTTP error on every mirror raises OverpassHTTPError, not HTTPError."""
        from unittest.mock import patch

        from aegis.environment.osm import OverpassHTTPError

        with (
            patch(
                "requests.post",
                return_value=self._fake_response(400, "bad query"),
            ),
            pytest.raises(OverpassHTTPError),
        ):
            fetch_osm(51.05, 3.72, radius_m=100, timeout=1, retries=0)

    def test_http_error_on_first_mirror_falls_back_to_next(self):
        """A bad status on the first mirror should let the second mirror succeed."""
        from unittest.mock import patch

        xml_body = "<osm></osm>"
        responses = [
            self._fake_response(400, "bad"),  # first mirror: bad request
            self._fake_response(200, xml_body),  # second mirror: success
        ]

        with patch("requests.post", side_effect=responses):
            result = fetch_osm(51.05, 3.72, radius_m=100, timeout=1, retries=0)
            assert result == xml_body


class TestHeightSemantics:
    """OSM height tag is total ground-to-peak: stored height is the eave."""

    def setup_method(self):
        self.buildings, _, _ = parse_osm_xml(FIXTURE.read_text())
        self.by_id = {b.way_id: b for b in self.buildings}

    def test_gabled_height_split_into_eave_and_roof(self):
        # height=10, roof:height=3 -> walls to 7, roof spans [7, 10]
        b = self.by_id[1001]
        assert b.height == pytest.approx(7.0)
        assert b.roof_height == pytest.approx(3.0)

    def test_hipped_height_split(self):
        # height=20, roof:height=4 -> walls to 16, peak at 20
        b = self.by_id[1003]
        assert b.height == pytest.approx(16.0)
        assert b.roof_height == pytest.approx(4.0)

    def test_flat_roof_unchanged(self):
        b = self.by_id[1002]
        assert b.height == pytest.approx(12.0)

    def test_peak_lands_at_tagged_height(self):
        for b in self.buildings:
            tagged = float(b.tags["height"])
            peak = b.height if b.roof_shape == "flat" else b.height + b.roof_height
            assert peak == pytest.approx(tagged)

    def test_mesh_peak_equals_tallest_tagged_height(self):
        # Tallest building is the hipped office at 20 m total. Before the
        # eave split its mesh peaked at 24 m (height + roof:height).
        mesh = build_environment_from_osm(FIXTURE.read_text(), origin_lat=51.05, origin_lon=3.72)
        assert mesh.vertices[:, 2].max() == pytest.approx(20.0)

    def test_low_building_keeps_positive_walls(self):
        # height=3 with roof:height=2.5 would leave 0.5 m walls: the eave is
        # floored at min(2, height/2) = 1.5 and the roof shrinks to match.
        xml = """<?xml version="1.0"?>
        <osm version="0.6">
          <node id="1" lat="51.0500" lon="3.7200"/>
          <node id="2" lat="51.0500" lon="3.7202"/>
          <node id="3" lat="51.0501" lon="3.7202"/>
          <node id="4" lat="51.0501" lon="3.7200"/>
          <way id="10">
            <nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="4"/><nd ref="1"/>
            <tag k="building" v="yes"/>
            <tag k="roof:shape" v="gabled"/>
            <tag k="height" v="3"/>
            <tag k="roof:height" v="2.5"/>
          </way>
        </osm>"""
        buildings, _, _ = parse_osm_xml(xml)
        b = buildings[0]
        assert b.height == pytest.approx(1.5)
        assert b.roof_height == pytest.approx(1.5)


class TestSplitHeight:
    def test_flat_passthrough(self):
        from aegis.environment.osm_helpers import _split_height

        assert _split_height(12.0, "flat", 3.0) == (12.0, 3.0)

    def test_non_flat_split(self):
        from aegis.environment.osm_helpers import _split_height

        eave, roof = _split_height(95.0, "pyramidal", 24.0)
        assert eave == pytest.approx(71.0)
        assert roof == pytest.approx(24.0)
        assert eave + roof == pytest.approx(95.0)

    def test_large_explicit_roof_height_respected(self):
        from aegis.environment.osm_helpers import _split_height

        # A spire taller than the walls is legal as long as walls stay sane
        eave, roof = _split_height(90.0, "pyramidal", 60.0)
        assert eave == pytest.approx(30.0)
        assert roof == pytest.approx(60.0)

    def test_floor_keeps_roof_positive(self):
        from aegis.environment.osm_helpers import _split_height

        eave, roof = _split_height(3.0, "gabled", 5.0)
        assert 0.0 < eave < 3.0
        assert roof > 0.0
        assert eave + roof == pytest.approx(3.0)


class TestDuplicateWays:
    """Overpass prints an element once per out statement: dedupe by id."""

    XML_TAGGED_FIRST = """<?xml version="1.0"?>
    <osm version="0.6">
      <node id="1" lat="51.0500" lon="3.7200"/>
      <node id="2" lat="51.0500" lon="3.7205"/>
      <node id="3" lat="51.0503" lon="3.7205"/>
      <node id="4" lat="51.0503" lon="3.7200"/>
      <way id="10">
        <nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="4"/><nd ref="1"/>
        <tag k="building" v="yes"/>
        <tag k="height" v="30"/>
      </way>
      <way id="10">
        <nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="4"/><nd ref="1"/>
      </way>
    </osm>"""

    XML_SKEL_FIRST = """<?xml version="1.0"?>
    <osm version="0.6">
      <node id="1" lat="51.0500" lon="3.7200"/>
      <node id="2" lat="51.0500" lon="3.7205"/>
      <node id="3" lat="51.0503" lon="3.7205"/>
      <node id="4" lat="51.0503" lon="3.7200"/>
      <way id="10">
        <nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="4"/><nd ref="1"/>
      </way>
      <way id="10">
        <nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="4"/><nd ref="1"/>
        <tag k="building" v="yes"/>
        <tag k="height" v="30"/>
      </way>
    </osm>"""

    @pytest.mark.parametrize("xml", [XML_TAGGED_FIRST, XML_SKEL_FIRST])
    def test_way_parsed_once_with_tags(self, xml):
        buildings, _, _ = parse_osm_xml(xml)
        assert len(buildings) == 1
        assert buildings[0].height == pytest.approx(30.0)


class TestStandaloneBuildingParts:
    """Simple 3D Buildings tower parts without a type=building relation."""

    PART_XML = """<?xml version="1.0"?>
    <osm version="0.6">
      <node id="1" lat="51.0500" lon="3.7200"/>
      <node id="2" lat="51.0500" lon="3.7205"/>
      <node id="3" lat="51.0503" lon="3.7205"/>
      <node id="4" lat="51.0503" lon="3.7200"/>
      <way id="10">
        <nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="4"/><nd ref="1"/>
        <tag k="building:part" v="yes"/>
        <tag k="height" v="227"/>
      </way>
    </osm>"""

    def test_standalone_part_becomes_building(self):
        buildings, _, _ = parse_osm_xml(self.PART_XML)
        assert len(buildings) == 1
        assert buildings[0].height == pytest.approx(227.0)

    def test_part_no_is_ignored(self):
        xml = self.PART_XML.replace('v="yes"', 'v="no"')
        buildings, _, _ = parse_osm_xml(xml)
        assert len(buildings) == 0

    def test_relation_member_part_not_emitted_twice(self):
        xml = """<?xml version="1.0"?>
        <osm version="0.6">
          <node id="1" lat="51.0500" lon="3.7200"/>
          <node id="2" lat="51.0500" lon="3.7205"/>
          <node id="3" lat="51.0503" lon="3.7205"/>
          <node id="4" lat="51.0503" lon="3.7200"/>
          <way id="10">
            <nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="4"/><nd ref="1"/>
            <tag k="building:part" v="yes"/>
            <tag k="height" v="20"/>
          </way>
          <relation id="100">
            <member type="way" ref="10" role="part"/>
            <tag k="type" v="building"/>
            <tag k="building" v="yes"/>
          </relation>
        </osm>"""
        mesh = build_environment_from_osm(xml, origin_lat=51.05015, origin_lon=3.72025)
        # One flat-roofed quad building: 8 wall triangles + 2 roof triangles.
        # A double emission (standalone way + relation part) would give 20.
        assert mesh.triangles.shape[0] == 10


class TestFetchQuery:
    """The Overpass query must return relation member ways with tags."""

    def _capture_query(self):
        from unittest.mock import MagicMock, patch

        resp = MagicMock()
        resp.status_code = 200
        resp.ok = True
        resp.text = "<osm></osm>"
        resp.content = b"<osm></osm>"
        captured = {}

        def fake_post(url, data=None, headers=None, timeout=None):
            captured["query"] = data["data"]
            return resp

        with patch("requests.post", side_effect=fake_post):
            fetch_osm(51.05, 3.72, radius_m=100, timeout=1, retries=0)
        return captured["query"]

    def test_building_part_ways_matched(self):
        # `way["building"]` does not match building:part ways, and the skel
        # recursion strips their tags, so without a direct match every tower
        # part would parse as an 8 m flat default box.
        query = self._capture_query()
        assert 'way["building:part"]' in query

    def test_matched_ways_printed_with_tags(self):
        # The union prints bodies (tags included); only the node/geometry
        # recursion is skel. Recursing bodies instead would leak tagged member
        # ways of relations that extend far outside the fetch radius.
        query = self._capture_query()
        assert query.index("out body;") < query.index(">;") < query.index("out skel qt;")


class TestGroundPlane:
    def test_off_by_default(self):
        xml = FIXTURE.read_text()
        mesh = build_environment_from_osm(xml, origin_lat=51.05, origin_lon=3.72)
        assert int(MaterialType.GROUND) not in mesh.materials.tolist()

    def test_ground_disk_added(self):
        xml = FIXTURE.read_text()
        mesh = build_environment_from_osm(xml, origin_lat=51.05, origin_lon=3.72, ground_radius_m=120.0)
        ground_faces = np.flatnonzero(mesh.materials == int(MaterialType.GROUND))
        assert len(ground_faces) > 0
        ground_verts = mesh.vertices[np.unique(mesh.triangles[ground_faces].ravel())]
        # 1 cm below the roads (road_z defaults to 0) to avoid coincident surfaces
        np.testing.assert_allclose(ground_verts[:, 2], -0.01)
        radii = np.linalg.norm(ground_verts[:, :2], axis=1)
        assert radii.max() == pytest.approx(120.0)

    def test_ground_normals_point_up(self):
        xml = FIXTURE.read_text()
        mesh = build_environment_from_osm(xml, origin_lat=51.05, origin_lon=3.72, ground_radius_m=50.0)
        ground_faces = np.flatnonzero(mesh.materials == int(MaterialType.GROUND))
        assert np.all(mesh.normals[ground_faces, 2] > 0.99)

    def test_ground_follows_road_z(self):
        xml = FIXTURE.read_text()
        mesh = build_environment_from_osm(xml, origin_lat=51.05, origin_lon=3.72, road_z=0.5, ground_radius_m=50.0)
        ground_faces = np.flatnonzero(mesh.materials == int(MaterialType.GROUND))
        ground_verts = mesh.vertices[np.unique(mesh.triangles[ground_faces].ravel())]
        np.testing.assert_allclose(ground_verts[:, 2], 0.49)

    def test_ground_material_exports_to_sionna(self, tmp_path):
        xml = FIXTURE.read_text()
        mesh = build_environment_from_osm(xml, origin_lat=51.05, origin_lon=3.72, ground_radius_m=50.0)
        out = mesh.to_sionna_xml(tmp_path / "scene.xml", radio_materials=True)
        content = out.read_text()
        # GROUND maps to itu_concrete: the ITU P.2040 ground models are
        # undefined above 10 GHz and Sionna raises at the study's 28 GHz.
        assert 'id="mat-itu_concrete"' in content


def _polygon_area(fp: np.ndarray) -> float:
    x, y = fp[:, 0], fp[:, 1]
    return 0.5 * abs(float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)))


class TestPedestrianAreas:
    """Closed pedestrian squares become filled polygons, not ribbon rings."""

    SQUARE_XML = """<?xml version="1.0"?>
    <osm version="0.6">
      <node id="1" lat="51.0500" lon="3.7200"/>
      <node id="2" lat="51.0500" lon="3.7207"/>
      <node id="3" lat="51.0504" lon="3.7207"/>
      <node id="4" lat="51.0504" lon="3.7200"/>
      <way id="10">
        <nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="4"/><nd ref="1"/>
        <tag k="highway" v="pedestrian"/>
        <tag k="area" v="yes"/>
      </way>
    </osm>"""

    def test_parsed_as_area(self):
        _, roads, _ = parse_osm_xml(self.SQUARE_XML)
        assert len(roads) == 1
        assert roads[0].is_area
        assert roads[0].centerline.shape == (4, 2)

    def test_meshed_as_filled_polygon(self):
        _, roads, _ = parse_osm_xml(self.SQUARE_XML)
        mesh = build_environment_from_osm(self.SQUARE_XML, origin_lat=51.0502, origin_lon=3.72035)
        asphalt = np.flatnonzero(mesh.materials == int(MaterialType.ASPHALT))
        tri = mesh.vertices[mesh.triangles[asphalt]]
        mesh_area = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1).sum()
        fp_area = _polygon_area(roads[0].centerline)
        # The fill covers the polygon; a 6 m ribbon ring would cover far less
        assert mesh_area == pytest.approx(fp_area, rel=0.01)

    def test_closed_pedestrian_without_area_tag_stays_ribbon(self):
        xml = self.SQUARE_XML.replace('<tag k="area" v="yes"/>', "")
        _, roads, _ = parse_osm_xml(xml)
        assert len(roads) == 1
        assert not roads[0].is_area

    def test_area_highway_polygon(self):
        xml = self.SQUARE_XML.replace(
            '<tag k="highway" v="pedestrian"/>\n        <tag k="area" v="yes"/>',
            '<tag k="area:highway" v="pedestrian"/>',
        )
        _, roads, _ = parse_osm_xml(xml)
        assert len(roads) == 1
        assert roads[0].is_area

    def test_open_area_highway_fragment_skipped(self):
        xml = """<?xml version="1.0"?>
        <osm version="0.6">
          <node id="1" lat="51.0500" lon="3.7200"/>
          <node id="2" lat="51.0500" lon="3.7207"/>
          <way id="10">
            <nd ref="1"/><nd ref="2"/>
            <tag k="area:highway" v="pedestrian"/>
          </way>
        </osm>"""
        _, roads, _ = parse_osm_xml(xml)
        assert len(roads) == 0


@pytest.mark.slow
def test_fetch_osm_includes_relations():
    """Real Overpass fetch should include relation elements."""
    pytest.importorskip("requests", reason="requests not installed")

    from aegis.environment.osm import OverpassRateLimitError, OverpassTimeoutError

    try:
        xml = fetch_osm(51.0544, 3.7237, radius_m=100, timeout=60)
    except (OverpassTimeoutError, OverpassRateLimitError):
        pytest.skip("Overpass API unavailable (timeout/rate limit)")
    assert "<node" in xml
    assert "<way" in xml
    # Relations may or may not exist in this area, but query should not error
    assert "<?xml" in xml or "<osm" in xml
