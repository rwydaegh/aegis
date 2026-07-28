"""The multi-city driver runs each city, overlays the CDFs, and survives a city
that fails (one bad city must not sink the batch)."""

import json
import types

import numpy as np

from aegis.study import run_cities as rc
from aegis.study.config import StudyConfig
from aegis.study.deployment import build_sites
from aegis.study.loop import Agent


class FakeKernel:
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

    # no sab_fn -> getattr(..., None) -> headline falls back to scalar exposure


def _agents(n, n_slots):
    agents = []
    for i in range(n):
        positions = np.column_stack([np.linspace(10.0, 40.0, n_slots), np.zeros(n_slots)])
        traj = types.SimpleNamespace(positions=positions, headings_rad=np.zeros(n_slots), t0_s=0.0)
        agents.append(Agent(trajectory=traj, is_user=(i == 0), agent_id=i))
    return agents


def _fake_build(cfg, out_dir, seed, agent_start, agent_count, city_latlon=(0.0, 0.0)):
    sites = build_sites(
        np.array([[0.0, 0.0, 15.0]]),
        n_sectors=1,
        az_coverage_deg=120.0,
        max_range_m=150.0,
        freq_hz=28e9,
        array=(2, 2),
        tx_power_dbm=30.0,
    )
    return _agents(3, 4), sites, FakeKernel(), 28e9, None


def _cfg_two_cities():
    cfg = StudyConfig()
    object.__setattr__(
        cfg.cities,
        "specs",
        [{"name": "alpha", "lat": 1.0, "lon": 2.0}, {"name": "beta", "lat": 3.0, "lon": 4.0}],
    )
    return cfg


def test_run_cities_overlays_all(tmp_path, monkeypatch):
    monkeypatch.setattr(rc, "_build_real", _fake_build)
    combined = rc.run_cities(_cfg_two_cities(), tmp_path, seed=0)

    assert combined["n_cities_requested"] == 2
    assert combined["n_cities_succeeded"] == 2
    assert {c["name"] for c in combined["cities"]} == {"alpha", "beta"}
    assert (tmp_path / "cities_summary.json").exists()
    assert (tmp_path / "cities_cdf.png").exists()
    assert (tmp_path / "cities_cdf.pdf").exists()
    # each city wrote its own outputs
    assert (tmp_path / "alpha" / "summary.json").exists()


def test_run_cities_skips_failures(tmp_path, monkeypatch):
    def flaky(cfg, out_dir, seed, agent_start, agent_count, city_latlon=(0.0, 0.0)):
        if city_latlon == (3.0, 4.0):
            raise RuntimeError("no illuminated receiver")
        return _fake_build(cfg, out_dir, seed, agent_start, agent_count, city_latlon)

    monkeypatch.setattr(rc, "_build_real", flaky)
    combined = rc.run_cities(_cfg_two_cities(), tmp_path, seed=0)

    assert combined["n_cities_requested"] == 2
    assert combined["n_cities_succeeded"] == 1
    assert combined["cities"][0]["name"] == "alpha"
    # the figure still gets written from the one survivor
    assert (tmp_path / "cities_cdf.png").exists()


def test_default_cities_selected_by_count():
    cfg = StudyConfig()
    object.__setattr__(cfg.cities, "count", 3)
    names = [c["name"] for c in rc._cities(cfg)]
    assert names == ["ghent", "manhattan", "barcelona"]
    cdict = json.loads(json.dumps(rc.DEFAULT_CITIES))  # plain JSON-serialisable
    assert len(cdict) == 10
