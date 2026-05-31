import numpy as np

from aegis.study.bodies import StaticPhantomPoser


def test_static_phantom_translates_and_yaws(duke_mesh):
    poser = StaticPhantomPoser(base_mesh=duke_mesh)
    mesh = poser.pose(position_xy=np.array([10.0, 5.0]), heading_rad=np.pi / 2, z_ground=0.0)
    # xy-centroid should sit at the requested position
    flat = mesh.vertices.reshape(-1, 3)
    c = flat.mean(axis=0)
    np.testing.assert_allclose(c[:2], [10.0, 5.0], atol=1.0)
    # feet on the ground
    assert abs(flat[:, 2].min()) < 1e-6


def test_static_phantom_yaw_changes_orientation(duke_mesh):
    poser = StaticPhantomPoser(base_mesh=duke_mesh)
    a = poser.pose([0.0, 0.0], heading_rad=0.0).vertices.reshape(-1, 3)
    b = poser.pose([0.0, 0.0], heading_rad=np.pi / 2).vertices.reshape(-1, 3)
    # rotation changes the vertex cloud (not a no-op)
    assert not np.allclose(a, b)
    # but the triangle count is preserved
    assert a.shape == b.shape
