import json
import types

import numpy as np

from aegis.study.config import StudyConfig
from aegis.study.deployment import build_sites
from aegis.study.loop import Agent
from aegis.study.run import run_study


class FakeKernel:
    """Minimal physics stand-in: constant Q, constant beam, constant density."""

    def pose_fn(self, pos, hdg, frame, z):
        return types.SimpleNamespace()

    def channel_fn(self, sector, body, pos):
        return types.SimpleNamespace(k_hat=np.array([[0.0, 0.0, -1.0]]))

    def gram_fn(self, body, center_paths, sector):
        return "M"

    def refresh_fn(self, m_static, k_hat, delta):
        return np.eye(2, dtype=complex)

    def beam_fn(self, sector, t):
        return np.ones(2, dtype=complex)

    def sab_fn(self, body, sector, x, center_paths):
        return 4.0  # W/m^2 -> 0.2 of the 20 W/m^2 general-public limit at 28 GHz


def _agents(n, n_slots):
    agents = []
    for i in range(n):
        positions = np.column_stack([np.linspace(10.0, 40.0, n_slots), np.zeros(n_slots)])
        traj = types.SimpleNamespace(positions=positions, headings_rad=np.zeros(n_slots), t0_s=0.0)
        agents.append(Agent(trajectory=traj, is_user=(i == 0), agent_id=i))
    return agents


def test_run_study_writes_outputs(tmp_path):
    cfg = StudyConfig()
    sites = build_sites(
        np.array([[0.0, 0.0, 15.0]]),
        n_sectors=1,
        az_coverage_deg=120.0,
        max_range_m=150.0,
        freq_hz=28e9,
        array=(2, 2),
        tx_power_dbm=30.0,
    )
    agents = _agents(3, 4)

    summary = run_study(cfg, agents, sites, FakeKernel(), tmp_path, freq_hz=28e9)

    assert summary["n_agents"] == 3
    assert summary["headline"] == "icnirp_fraction"
    assert (tmp_path / "exposure.npz").exists()
    assert (tmp_path / "summary.json").exists()

    data = np.load(tmp_path / "exposure.npz")
    assert data["p_abs_w"].shape == (3,)
    assert data["icnirp_fraction"].shape == (3,)
    # 4 W/m^2 / 20 W/m^2 = 0.2
    np.testing.assert_allclose(data["icnirp_fraction"], 0.2, atol=1e-9)

    written = json.loads((tmp_path / "summary.json").read_text())
    assert len(written["cdf_x"]) == 3
    assert written["median"] is not None


def test_run_study_no_density_falls_back_to_power(tmp_path):
    cfg = StudyConfig()
    sites = build_sites(
        np.array([[0.0, 0.0, 15.0]]),
        n_sectors=1,
        az_coverage_deg=120.0,
        max_range_m=150.0,
        freq_hz=28e9,
        array=(2, 2),
        tx_power_dbm=30.0,
    )
    agents = _agents(2, 4)

    kernel = FakeKernel()
    kernel.sab_fn = None  # no density -> headline is absorbed power

    summary = run_study(cfg, agents, sites, kernel, tmp_path, freq_hz=28e9)
    assert summary["headline"] == "p_abs_w"
