from pathlib import Path

import numpy as np
import pytest

from aegis.environment import EnvironmentMesh

_FIXTURES = Path(__file__).parent / "fixtures"


class TestOSMDetailPipeline:
    def test_simple_pipeline(self):
        """OSM XML -> mesh -> binary export."""
        from aegis.environment.osm import build_environment_from_osm

        xml = (_FIXTURES / "osm_sample.xml").read_text()
        mesh = build_environment_from_osm(xml, origin_lat=51.05, origin_lon=3.72)
        assert mesh.triangles.shape[0] > 0
        blob, meta = mesh.to_binary()
        assert len(blob) > 0
        assert meta["n_triangles"] == mesh.triangles.shape[0]

    def test_detail_pipeline(self):
        """OSM with detail=True produces more geometry."""
        from aegis.environment.osm import build_environment_from_osm

        xml = (_FIXTURES / "osm_sample.xml").read_text()
        mesh_simple = build_environment_from_osm(xml, 51.05, 3.72, detail=False)
        mesh_detail = build_environment_from_osm(xml, 51.05, 3.72, detail=True)
        assert mesh_detail.triangles.shape[0] > mesh_simple.triangles.shape[0]

    def test_multipolygon_pipeline(self):
        """OSM with multipolygon relations produces valid mesh."""
        from aegis.environment.osm import build_environment_from_osm

        xml = (_FIXTURES / "osm_multipolygon.xml").read_text()
        mesh = build_environment_from_osm(xml, origin_lat=51.05, origin_lon=3.72)
        assert mesh.triangles.shape[0] > 50

    def test_source_tag(self):
        """Mesh built from OSM has source='osm'."""
        from aegis.environment.osm import build_environment_from_osm

        xml = (_FIXTURES / "osm_sample.xml").read_text()
        mesh = build_environment_from_osm(xml, 51.05, 3.72)
        assert mesh.source == "osm"

    def test_origin_preserved(self):
        """Origin lat/lon are preserved in the returned mesh."""
        from aegis.environment.osm import build_environment_from_osm

        xml = (_FIXTURES / "osm_sample.xml").read_text()
        mesh = build_environment_from_osm(xml, 51.05, 3.72)
        assert mesh.origin_lat == pytest.approx(51.05)
        assert mesh.origin_lon == pytest.approx(3.72)


class TestGeoJSONPipeline:
    def test_geojson_to_mesh(self):
        """GeoJSON -> mesh -> binary."""
        from aegis.environment.geojson import build_environment_from_geojson

        geojson = (_FIXTURES / "geojson_sample.json").read_text()
        mesh = build_environment_from_geojson(geojson, origin_lat=51.05, origin_lon=3.72)
        assert mesh.source == "geojson"
        assert mesh.triangles.shape[0] > 0
        blob, meta = mesh.to_binary()
        assert len(blob) > 0
        assert meta["n_triangles"] == mesh.triangles.shape[0]

    def test_geojson_origin_preserved(self):
        """GeoJSON mesh carries the requested origin."""
        from aegis.environment.geojson import build_environment_from_geojson

        geojson = (_FIXTURES / "geojson_sample.json").read_text()
        mesh = build_environment_from_geojson(geojson, origin_lat=51.05, origin_lon=3.72)
        assert mesh.origin_lat == pytest.approx(51.05)
        assert mesh.origin_lon == pytest.approx(3.72)


class TestCombinePipeline:
    def test_combine_osm_and_geojson(self):
        """Combine meshes from different sources."""
        from aegis.environment.geojson import build_environment_from_geojson
        from aegis.environment.osm import build_environment_from_osm

        xml = (_FIXTURES / "osm_sample.xml").read_text()
        m1 = build_environment_from_osm(xml, origin_lat=51.05, origin_lon=3.72)
        geojson = (_FIXTURES / "geojson_sample.json").read_text()
        m2 = build_environment_from_geojson(geojson, origin_lat=51.05, origin_lon=3.72)
        combined = EnvironmentMesh.combine(m1, m2)
        assert combined.source == "combined"
        assert combined.triangles.shape[0] >= m1.triangles.shape[0]

    def test_combine_triangle_count_additive(self):
        """Combined mesh has exactly m1 + m2 triangles."""
        from aegis.environment.geojson import build_environment_from_geojson
        from aegis.environment.osm import build_environment_from_osm

        xml = (_FIXTURES / "osm_sample.xml").read_text()
        m1 = build_environment_from_osm(xml, origin_lat=51.05, origin_lon=3.72)
        geojson = (_FIXTURES / "geojson_sample.json").read_text()
        m2 = build_environment_from_geojson(geojson, origin_lat=51.05, origin_lon=3.72)
        combined = EnvironmentMesh.combine(m1, m2)
        assert combined.triangles.shape[0] == m1.triangles.shape[0] + m2.triangles.shape[0]

    def test_combine_origin_mismatch_raises(self):
        """Combining meshes with different origins raises ValueError."""
        from aegis.environment.osm import build_environment_from_osm

        xml = (_FIXTURES / "osm_sample.xml").read_text()
        m1 = build_environment_from_osm(xml, origin_lat=51.05, origin_lon=3.72)
        m2 = build_environment_from_osm(xml, origin_lat=52.00, origin_lon=4.00)
        with pytest.raises(ValueError, match="origin"):
            EnvironmentMesh.combine(m1, m2)


class TestMeshIntegrity:
    def test_all_indices_valid(self):
        """All triangle indices must reference existing vertices."""
        from aegis.environment.osm import build_environment_from_osm

        xml = (_FIXTURES / "osm_sample.xml").read_text()
        mesh = build_environment_from_osm(xml, 51.05, 3.72, detail=True)
        assert mesh.triangles.max() < len(mesh.vertices)
        assert mesh.triangles.min() >= 0

    def test_normals_finite(self):
        """All face normals must be finite (no NaN or Inf)."""
        from aegis.environment.osm import build_environment_from_osm

        xml = (_FIXTURES / "osm_sample.xml").read_text()
        mesh = build_environment_from_osm(xml, 51.05, 3.72)
        assert np.all(np.isfinite(mesh.normals))

    def test_materials_valid(self):
        """Material indices must be in a reasonable range."""
        from aegis.environment.osm import build_environment_from_osm

        xml = (_FIXTURES / "osm_sample.xml").read_text()
        mesh = build_environment_from_osm(xml, 51.05, 3.72, detail=True)
        assert np.all(mesh.materials >= 0)
        assert np.all(mesh.materials < 20)

    def test_triangle_count_matches_materials(self):
        """One material entry per triangle."""
        from aegis.environment.osm import build_environment_from_osm

        xml = (_FIXTURES / "osm_sample.xml").read_text()
        mesh = build_environment_from_osm(xml, 51.05, 3.72)
        assert len(mesh.materials) == mesh.triangles.shape[0]

    def test_triangle_count_matches_normals(self):
        """One normal per triangle."""
        from aegis.environment.osm import build_environment_from_osm

        xml = (_FIXTURES / "osm_sample.xml").read_text()
        mesh = build_environment_from_osm(xml, 51.05, 3.72)
        assert mesh.normals.shape[0] == mesh.triangles.shape[0]

    def test_multipolygon_indices_valid(self):
        """Multipolygon mesh indices must reference existing vertices."""
        from aegis.environment.osm import build_environment_from_osm

        xml = (_FIXTURES / "osm_multipolygon.xml").read_text()
        mesh = build_environment_from_osm(xml, 51.05, 3.72)
        assert mesh.triangles.max() < len(mesh.vertices)
        assert mesh.triangles.min() >= 0

    def test_geojson_normals_finite(self):
        """GeoJSON-derived normals must be finite."""
        from aegis.environment.geojson import build_environment_from_geojson

        geojson = (_FIXTURES / "geojson_sample.json").read_text()
        mesh = build_environment_from_geojson(geojson, 51.05, 3.72)
        assert np.all(np.isfinite(mesh.normals))
