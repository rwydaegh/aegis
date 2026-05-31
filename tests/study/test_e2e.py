"""Tiny end-to-end run of the real deterministic pipeline.

Drives the real RealKernel (DiffeRT ray trace + coherent Sab + reduction +
output) over a synthetic ground-plane scene and the duke phantom, avoiding the
network and the Directions API. Skips if DiffeRT or mesh data is unavailable.
"""

from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("sionna.rt")

import tempfile  # noqa: E402

from aegis.engine import DosimetryEngine  # noqa: E402
from aegis.environment import EnvironmentMesh, MaterialType  # noqa: E402
from aegis.geometry.mesh import BodyMesh  # noqa: E402
from aegis.study.bodies import StaticPhantomPoser  # noqa: E402
from aegis.study.config import StudyConfig, TemporalConfig  # noqa: E402
from aegis.study.deployment import build_sites  # noqa: E402
from aegis.study.loop import Agent  # noqa: E402
from aegis.study.run import RealKernel, run_study  # noqa: E402
from aegis.study.walk import sample_trajectory  # noqa: E402
from aegis.tissue.dielectric import TissueModel  # noqa: E402

_DUKE = Path(__file__).parents[2] / "data" / "duke.stl"


def _ground_scene():
    """Synthetic ground-plane Sionna RT scene (radio materials, loaded on CPU)."""
    import sionna.rt as srt

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
        source="e2e_ground",
    )
    xml = mesh.to_sionna_xml(Path(tempfile.mkdtemp()) / "scene.xml", radio_materials=True)
    return srt.load_scene(str(xml))


@pytest.mark.slow
def test_tiny_end_to_end(tmp_path):
    if not _DUKE.exists():
        pytest.skip("duke.stl phantom not available")

    freq = 28e9
    scene = _ground_scene()
    sites = build_sites(
        np.array([[0.0, 0.0, 15.0]]),
        n_sectors=1,
        az_coverage_deg=120.0,
        max_range_m=150.0,
        freq_hz=freq,
        array=(4, 4),
        tx_power_dbm=30.0,
    )

    n_slots = 4
    agents = []
    for i in range(2):
        route = np.array([[20.0, 5.0 * i], [44.0, 5.0 * i]])  # east of the site, in wedge
        traj = sample_trajectory(route, speed_mps=8.0, dt_s=1.0)  # 24 m / 8 = 3 s -> 4 slots
        agents.append(Agent(trajectory=traj, is_user=(i == 0), agent_id=i, z_ground=0.0))
    assert all(len(a.trajectory.positions) == n_slots for a in agents)

    poser = StaticPhantomPoser(BodyMesh.load(_DUKE, name="duke"))
    engine = DosimetryEngine(TissueModel.from_database("Skin", freq))
    kernel = RealKernel(
        scene,
        engine,
        poser,
        sites,
        freq,
        level=7,
        user_agents=[a for a in agents if a.is_user],
        recompute_period=4,
    )

    cfg = StudyConfig(temporal=TemporalConfig(dt_s=1.0, pose_period=4, recompute_period=4))
    summary = run_study(cfg, agents, sites, kernel, tmp_path, freq_hz=freq)

    assert summary["n_agents"] == 2
    assert (tmp_path / "exposure.npz").exists()
    assert (tmp_path / "summary.json").exists()

    data = np.load(tmp_path / "exposure.npz")
    assert data["p_abs_w"].shape == (2,)
    assert np.all(np.isfinite(data["p_abs_w"]))
    assert np.all(data["p_abs_w"] >= 0)
    assert np.all(np.isfinite(data["icnirp_fraction"]))
    assert np.all(data["icnirp_fraction"] >= 0)
