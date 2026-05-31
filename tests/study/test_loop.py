import types

import numpy as np

from aegis.study.deployment import build_sites
from aegis.study.loop import Agent, run_agent


def _straight_agent(n=6):
    positions = np.column_stack([np.linspace(10.0, 60.0, n), np.zeros(n)])
    headings = np.zeros(n)
    traj = types.SimpleNamespace(positions=positions, headings_rad=headings, t0_s=0.0)
    return Agent(trajectory=traj, is_user=False, agent_id=3)


def _one_east_sector():
    # site at origin, one panel looking east (az=0), range 150 m
    return build_sites(
        np.array([[0.0, 0.0, 15.0]]),
        n_sectors=1,
        az_coverage_deg=120.0,
        max_range_m=150.0,
        freq_hz=28e9,
        array=(2, 2),
        tx_power_dbm=30.0,
    )


def test_loop_cadence_and_summation():
    agent = _straight_agent(n=6)
    sites = _one_east_sector()

    counts = {"pose": 0, "channel": 0, "gram": 0, "refresh": 0}

    def pose_fn(pos, hdg, frame, z):
        counts["pose"] += 1
        return types.SimpleNamespace(tag="body")

    def channel_fn(sector, body, pos):
        counts["channel"] += 1
        return types.SimpleNamespace(k_hat=np.array([[0.0, 0.0, -1.0]]))

    def gram_fn(body, center_paths, sector):
        counts["gram"] += 1
        return "M"

    def refresh_fn(m_static, k_hat, delta):
        counts["refresh"] += 1
        return np.eye(2, dtype=complex)

    def beam_fn(sector, t):
        return np.ones(2, dtype=complex)

    result = run_agent(
        agent,
        sites,
        pose_period=2,
        recompute_period=2,
        pose_fn=pose_fn,
        channel_fn=channel_fn,
        gram_fn=gram_fn,
        refresh_fn=refresh_fn,
        beam_fn=beam_fn,
    )

    assert result.exposure_w.shape == (6,)
    assert result.agent_id == 3
    # Q = I, x = ones(2) -> x^H Q x = 2 every slot, one lit sector
    np.testing.assert_allclose(result.exposure_w, 2.0)
    # pose + rebuild fire at slots 0, 2, 4 (pose_period == recompute_period == 2)
    assert counts["pose"] == 3
    assert counts["channel"] == 3
    assert counts["gram"] == 3
    # Q refresh every slot for the single lit sector
    assert counts["refresh"] == 6


def test_loop_no_illumination_gives_zero():
    # agent walks far out of range -> no sector lights it -> zero exposure
    positions = np.column_stack([np.linspace(500.0, 600.0, 4), np.zeros(4)])
    traj = types.SimpleNamespace(positions=positions, headings_rad=np.zeros(4), t0_s=0.0)
    agent = Agent(trajectory=traj)
    sites = _one_east_sector()

    def pose_fn(pos, hdg, frame, z):
        return types.SimpleNamespace()

    def boom(*a, **k):
        raise AssertionError("physics must not run when no sector illuminates")

    result = run_agent(
        agent,
        sites,
        pose_period=2,
        recompute_period=2,
        pose_fn=pose_fn,
        channel_fn=boom,
        gram_fn=boom,
        refresh_fn=boom,
        beam_fn=boom,
    )
    np.testing.assert_allclose(result.exposure_w, 0.0)
