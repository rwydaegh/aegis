import numpy as np

from aegis.study.deployment import (
    build_sites,
    sectors_illuminating,
    thin_min_spacing,
)


def test_thinning_respects_min_spacing():
    rng = np.random.default_rng(0)
    cand = rng.uniform(-100, 100, size=(200, 3))
    cand[:, 2] = 15.0
    kept = thin_min_spacing(cand, min_spacing_m=30.0, n_target=10, rng=rng)
    assert kept.shape[0] <= 10
    for i in range(len(kept)):
        for j in range(i + 1, len(kept)):
            assert np.linalg.norm(kept[i, :2] - kept[j, :2]) >= 30.0 - 1e-6


def test_thinning_empty_pool():
    rng = np.random.default_rng(0)
    kept = thin_min_spacing(np.zeros((0, 3)), min_spacing_m=30.0, n_target=10, rng=rng)
    assert kept.shape == (0, 3)


def _one_site():
    return build_sites(
        np.array([[0.0, 0.0, 15.0]]),
        n_sectors=3,
        az_coverage_deg=120.0,
        max_range_m=150.0,
        freq_hz=28e9,
        array=(8, 8),
        tx_power_dbm=30.0,
    )[0]


def test_three_sectors_120_apart():
    sectors = _one_site().sectors
    azs = sorted(s.boresight_az_deg for s in sectors)
    assert len(sectors) == 3
    assert abs((azs[1] - azs[0]) - 120.0) < 1e-6
    assert sectors[0].m_ant == 64


def test_membership_wedge_and_range():
    site = _one_site()
    near = np.array([50.0, 0.0, 1.5])  # due east, in range
    far = np.array([300.0, 0.0, 1.5])  # due east, out of range
    assert len(sectors_illuminating(near, [site])) >= 1
    assert len(sectors_illuminating(far, [site])) == 0


def test_point_behind_panel_excluded():
    site = _one_site()
    # The sector at az=0 looks east. A point due west (az=180) is outside its
    # +/-60 deg wedge, so that sector must not illuminate it.
    west = np.array([-50.0, 0.0, 1.5])
    hit = sectors_illuminating(west, [site])
    assert all(abs(s.boresight_az_deg - 0.0) > 1e-6 for s in hit)
