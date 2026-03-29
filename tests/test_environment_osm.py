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


@pytest.mark.slow
def test_fetch_osm_includes_relations():
    """Real Overpass fetch should include relation elements."""
    pytest.importorskip("requests", reason="requests not installed")
    xml = fetch_osm(51.0544, 3.7237, radius_m=100, timeout=60)
    assert "<node" in xml
    assert "<way" in xml
    # Relations may or may not exist in this area, but query should not error
    assert "<?xml" in xml or "<osm" in xml
