import tempfile
from pathlib import Path

import numpy as np
import pytest

from aegis.environment import EnvironmentMesh, MaterialType  # noqa: E402
from aegis.study.channel_det import center_paths, sector_paths  # noqa: E402
from aegis.study.deployment import build_sites  # noqa: E402


def _ground_mesh():
    s = 200.0
    verts = np.array([[-s, -s, 0.0], [s, -s, 0.0], [s, s, 0.0], [-s, s, 0.0]], dtype=float)
    tris = np.array([[0, 1, 2], [0, 2, 3]])
    normals = np.tile([0.0, 0.0, 1.0], (2, 1))
    materials = np.array([MaterialType.GROUND, MaterialType.GROUND])
    return EnvironmentMesh(
        vertices=verts,
        triangles=tris,
        normals=normals,
        materials=materials,
        origin_lat=51.0,
        origin_lon=3.7,
        source="test_ground",
    )


def _sector(array=(4, 4)):
    return build_sites(
        np.array([[0.0, 0.0, 12.0]]),
        n_sectors=1,
        az_coverage_deg=120.0,
        max_range_m=150.0,
        freq_hz=28e9,
        array=array,
        tx_power_dbm=30.0,
    )[0].sectors[0]


@pytest.mark.slow
def test_sionna_sector_and_center_paths():
    pytest.importorskip("sionna.rt")
    import sionna.rt as srt

    d = Path(tempfile.mkdtemp())
    xml = _ground_mesh().to_sionna_xml(d / "scene.xml", radio_materials=True)
    scene = srt.load_scene(str(xml))
    sector = _sector()

    per_elem = sector_paths(scene, sector, [30.0, 0.0, 1.5], 28e9, engine="sionna")
    assert sector.m_ant == 16
    assert np.iscomplexobj(per_elem.psi)
    assert per_elem.element_index.min() >= 0
    assert per_elem.element_index.max() < 16
    assert per_elem.total_power > 0

    center = center_paths(scene, sector, [30.0, 0.0, 1.5], 28e9, engine="sionna")
    assert center.n_elements == 1  # single virtual tx at the array center


@pytest.mark.slow
def test_differt_engine_still_works():
    pytest.importorskip("differt")
    scene = _ground_mesh().to_differt_scene()
    sector = _sector()
    per_elem = sector_paths(scene, sector, [30.0, 0.0, 1.5], 28e9, engine="differt")
    assert per_elem.element_index.max() < sector.m_ant
    assert per_elem.total_power > 0


def test_unknown_engine_raises():
    with pytest.raises(ValueError, match="unknown ray-tracing engine"):
        sector_paths(object(), _sector(), [0, 0, 1.5], 28e9, engine="bogus")
