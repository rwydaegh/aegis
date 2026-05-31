import numpy as np
import pytest

pytest.importorskip("differt")

from aegis.environment import EnvironmentMesh, MaterialType  # noqa: E402
from aegis.study.channel_det import sector_paths_det  # noqa: E402
from aegis.study.deployment import build_sites  # noqa: E402


def _ground_scene():
    """A single large ground quad at z=0 as an in-memory DiffeRT scene."""
    s = 200.0
    verts = np.array([[-s, -s, 0.0], [s, -s, 0.0], [s, s, 0.0], [-s, s, 0.0]], dtype=float)
    tris = np.array([[0, 1, 2], [0, 2, 3]])
    normals = np.tile([0.0, 0.0, 1.0], (2, 1))
    materials = np.array([MaterialType.GROUND, MaterialType.GROUND])
    mesh = EnvironmentMesh(
        vertices=verts,
        triangles=tris,
        normals=normals,
        materials=materials,
        origin_lat=51.0,
        origin_lon=3.7,
        source="test_ground",
    )
    return mesh.to_differt_scene()


@pytest.mark.slow
def test_sector_paths_per_element():
    scene = _ground_scene()
    site = build_sites(
        np.array([[0.0, 0.0, 12.0]]),
        n_sectors=1,
        az_coverage_deg=120.0,
        max_range_m=150.0,
        freq_hz=28e9,
        array=(4, 4),
        tx_power_dbm=30.0,
    )[0]
    sector = site.sectors[0]

    paths = sector_paths_det(scene, sector, rx_position=[30.0, 0.0, 1.5], freq_hz=28e9)

    m_ant = sector.m_ant
    assert m_ant == 16
    assert np.iscomplexobj(paths.psi)
    assert paths.element_index.min() >= 0
    assert paths.element_index.max() < m_ant
    assert paths.total_power > 0
