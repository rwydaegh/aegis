"""Covariates: morphology + deployment statistics per city, and the geometric
LOS fraction against the traced mesh."""

import types

import numpy as np

from aegis.study.covariates import city_covariates, phantom_mass_kg
from aegis.study.deployment import build_sites
from aegis.study.loop import Agent


def _wall_mesh():
    """A single vertical wall at x=10 spanning y in [-20, 20], z in [0, 30]."""
    v = np.array(
        [
            [10.0, -20.0, 0.0],
            [10.0, 20.0, 0.0],
            [10.0, 20.0, 30.0],
            [10.0, -20.0, 30.0],
        ]
    )
    t = np.array([[0, 1, 2], [0, 2, 3]])
    return types.SimpleNamespace(vertices=v, triangles=t)


def _city(candidates):
    return types.SimpleNamespace(mesh=_wall_mesh(), candidates=np.asarray(candidates, dtype=float))


def _agent(x, y, agent_id=0):
    traj = types.SimpleNamespace(positions=np.array([[x, y]] * 3, dtype=float), headings_rad=np.zeros(3), t0_s=0.0)
    return Agent(trajectory=traj, is_user=False, agent_id=agent_id)


def _sites_at(positions):
    return build_sites(
        np.asarray(positions, dtype=float),
        n_sectors=3,
        az_coverage_deg=120.0,
        max_range_m=150.0,
        freq_hz=28e9,
        array=(2, 2),
        tx_power_dbm=30.0,
    )


def test_wall_blocks_los_and_open_side_does_not():
    city = _city([[0, 0, 12.0], [40, 0, 20.0]])
    sites = _sites_at([[0.0, 0.0, 15.0]])
    # agent behind the wall (x=25): blocked. Agent on the site side (x=-25): LOS.
    cov = city_covariates(city, sites, [_agent(25.0, 0.0), _agent(-25.0, 0.0, 1)], radius_m=100.0)
    assert cov["los_fraction"] == 0.5
    assert cov["n_sites"] == 1
    assert cov["n_buildings"] == 2
    np.testing.assert_allclose(cov["roof_height_mean_m"], 16.0)
    assert cov["serving_distance_mean_m"] > 25.0


def test_isd_is_nearest_neighbor_mean():
    city = _city([[0, 0, 12.0]])
    sites = _sites_at([[0.0, 100.0, 15.0], [0.0, -100.0, 15.0], [30.0, 100.0, 15.0]])
    cov = city_covariates(city, sites, [], radius_m=100.0)
    # nearest neighbours: 30, 200, 30 -> mean 86.67
    np.testing.assert_allclose(cov["isd_mean_m"], (30.0 + 200.0 + 30.0) / 3.0)
    assert cov["los_fraction"] is None


def test_phantom_mass_lookup():
    assert phantom_mass_kg("duke") == 72.4
    assert phantom_mass_kg("nonexistent_phantom") is None
