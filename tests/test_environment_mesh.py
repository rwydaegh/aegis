import numpy as np
import pytest

from aegis.environment import (
    MATERIAL_EM_PROPERTIES,
    EnvironmentMesh,
    MaterialType,
)


class TestMaterialType:
    def test_all_values_are_sequential(self):
        values = [m.value for m in MaterialType]
        assert values == list(range(len(MaterialType)))

    def test_every_material_has_em_properties(self):
        for mat in MaterialType:
            assert mat in MATERIAL_EM_PROPERTIES
            props = MATERIAL_EM_PROPERTIES[mat]
            assert "eps_r" in props
            assert "sigma" in props
            assert props["eps_r"] > 0

    def test_concrete_values_match_itu_p2040(self):
        props = MATERIAL_EM_PROPERTIES[MaterialType.CONCRETE]
        assert props["eps_r"] == pytest.approx(5.31)
        assert props["sigma"] == pytest.approx(0.0326)


class TestEnvironmentMesh:
    @pytest.fixture
    def simple_mesh(self):
        """A single triangle at origin."""
        vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float64)
        triangles = np.array([[0, 1, 2]], dtype=np.uint32)
        normals = np.array([[0, 0, 1]], dtype=np.float64)
        materials = np.array([MaterialType.CONCRETE], dtype=np.uint8)
        return EnvironmentMesh(
            vertices=vertices,
            triangles=triangles,
            normals=normals,
            materials=materials,
            origin_lat=51.05,
            origin_lon=3.72,
            source="test",
        )

    def test_creation(self, simple_mesh):
        assert simple_mesh.vertices.shape == (3, 3)
        assert simple_mesh.triangles.shape == (1, 3)
        assert simple_mesh.normals.shape == (1, 3)
        assert simple_mesh.materials.shape == (1,)
        assert simple_mesh.source == "test"

    def test_combine_same_origin(self, simple_mesh):
        combined = EnvironmentMesh.combine(simple_mesh, simple_mesh)
        assert combined.vertices.shape == (6, 3)
        assert combined.triangles.shape == (2, 3)
        assert combined.source == "combined"
        assert combined.triangles[1, 0] == 3

    def test_combine_different_origin_raises(self, simple_mesh):
        other = EnvironmentMesh(
            vertices=simple_mesh.vertices,
            triangles=simple_mesh.triangles,
            normals=simple_mesh.normals,
            materials=simple_mesh.materials,
            origin_lat=52.0,
            origin_lon=3.72,
            source="test",
        )
        with pytest.raises(ValueError, match="origin"):
            EnvironmentMesh.combine(simple_mesh, other)

    def test_combine_empty(self):
        with pytest.raises(ValueError):
            EnvironmentMesh.combine()
