import tempfile
from pathlib import Path

import numpy as np
import pytest

from aegis.environment import EnvironmentMesh, MaterialType  # noqa: E402
from aegis.paths import PropagationPaths  # noqa: E402
from aegis.study.channel_det import _cap_paths, center_paths, sector_paths  # noqa: E402
from aegis.study.deployment import build_sites  # noqa: E402


def test_cap_paths_keeps_strongest_by_power():
    n = 6
    rng = np.random.default_rng(0)
    psi = np.zeros((n, 3), dtype=complex)
    # path i has power i^2, so the top-3 by power are paths 3, 4, 5
    for i in range(n):
        psi[i, 0] = float(i)
    k = rng.standard_normal((n, 3))
    k /= np.linalg.norm(k, axis=1, keepdims=True)
    paths = PropagationPaths(
        k_hat=k,
        psi=psi,
        element_index=np.zeros(n, dtype=np.intp),
        delay=np.arange(n, dtype=float),
        is_los=np.zeros(n, dtype=bool),
    )
    capped = _cap_paths(paths, 3)
    assert capped.k_hat.shape[0] == 3
    # kept the three strongest (delays 3, 4, 5), in original order
    np.testing.assert_array_equal(capped.delay, np.array([3.0, 4.0, 5.0]))
    # at-or-below count and None are no-ops (same object back)
    assert _cap_paths(paths, 10) is paths
    assert _cap_paths(paths, None) is paths


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


def test_samples_per_src_converged_default_threads_to_sionna(monkeypatch):
    # The default must be the convergence-study value, and it must reach the
    # solver. A regression to the 1M bridge default would silently halve the
    # discovered paths at 28 GHz.
    import aegis.integration.sionna as sio
    from aegis.study.channel_det import SAMPLES_PER_SRC

    assert SAMPLES_PER_SRC == 30_000_000

    captured = {}

    def fake(scene, **kw):
        captured.update(kw)
        return object()

    monkeypatch.setattr(sio, "paths_from_sionna_scene", fake)

    sector_paths(object(), _sector(), [10.0, 0.0, 1.5], 28e9, engine="sionna")
    assert captured["samples_per_src"] == SAMPLES_PER_SRC
    # diffraction is on by default (rooftop-edge diffraction carries ~2.2x the
    # specular-only power for near-ground receivers); a regression to off would
    # silently underestimate exposure.
    assert captured["diffraction"] is True
    assert captured["edge_diffraction"] is True

    center_paths(object(), _sector(), [10.0, 0.0, 1.5], 28e9, engine="sionna", samples_per_src=12345)
    assert captured["samples_per_src"] == 12345

    center_paths(object(), _sector(), [10.0, 0.0, 1.5], 28e9, engine="sionna", diffraction=False)
    assert captured["diffraction"] is False
