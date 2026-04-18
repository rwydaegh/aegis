import numpy as np
import pytest

from aegis.environment import EnvironmentMesh, MaterialType
from aegis.environment.export import to_binary, to_sionna_xml


@pytest.fixture
def sample_mesh():
    vertices = np.array(
        [
            [0, 0, 0],
            [10, 0, 0],
            [10, 10, 0],
            [0, 0, 0],
            [10, 10, 0],
            [0, 10, 0],
        ],
        dtype=np.float64,
    )
    triangles = np.array([[0, 1, 2], [3, 4, 5]], dtype=np.uint32)
    normals = np.array([[0, 0, 1], [0, 0, 1]], dtype=np.float64)
    materials = np.array([MaterialType.CONCRETE, MaterialType.ASPHALT], dtype=np.uint8)
    return EnvironmentMesh(
        vertices=vertices,
        triangles=triangles,
        normals=normals,
        materials=materials,
        origin_lat=51.05,
        origin_lon=3.72,
        source="test",
    )


class TestToBinary:
    def test_produces_bytes_and_meta(self, sample_mesh):
        data, meta = to_binary(sample_mesh)
        assert isinstance(data, bytes)
        assert isinstance(meta, dict)

    def test_meta_keys(self, sample_mesh):
        _, meta = to_binary(sample_mesh)
        assert "n_vertices" in meta
        assert "n_triangles" in meta
        assert "source" in meta
        assert meta["n_vertices"] == 6
        assert meta["n_triangles"] == 2

    def test_round_trip(self, sample_mesh):
        data, meta = to_binary(sample_mesh)
        n_v = meta["n_vertices"]
        n_t = meta["n_triangles"]
        offset = 0
        v_bytes = n_v * 3 * 4
        verts = np.frombuffer(data[offset : offset + v_bytes], dtype=np.float32).reshape(n_v, 3)
        offset += v_bytes
        t_bytes = n_t * 3 * 4
        tris = np.frombuffer(data[offset : offset + t_bytes], dtype=np.uint32).reshape(n_t, 3)
        offset += t_bytes
        n_bytes = n_t * 3 * 4
        norms = np.frombuffer(data[offset : offset + n_bytes], dtype=np.float32).reshape(n_t, 3)  # noqa: F841
        offset += n_bytes
        mats = np.frombuffer(data[offset : offset + n_t], dtype=np.uint8)

        # vertices are ENU->Y-up transformed, so check shape only
        assert verts.shape == (n_v, 3)
        np.testing.assert_array_equal(tris, sample_mesh.triangles)
        assert len(mats) == n_t


class TestToSionnaXml:
    def test_produces_valid_xml(self, sample_mesh, tmp_path):
        out = to_sionna_xml(sample_mesh, tmp_path / "scene.xml")
        assert out.exists()
        content = out.read_text()
        assert "<?xml" in content or "<scene" in content


class TestToDiffertScene:
    @pytest.fixture
    def _has_differt(self):
        pytest.importorskip("differt")

    @pytest.mark.usefixtures("_has_differt")
    def test_produces_triangle_scene(self, sample_mesh):
        from aegis.environment.export import to_differt_scene

        scene = to_differt_scene(sample_mesh)
        assert scene.mesh.vertices.shape[1] == 3
        assert scene.mesh.triangles.shape[1] == 3
