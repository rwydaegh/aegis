import numpy as np

from aegis.study.deployment import (
    build_sites,
    sectors_illuminating,
    select_rooftop_sites,
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


def test_select_rooftop_sites_respects_height_band():
    rng = np.random.default_rng(0)
    cand = np.array(
        [[0, 0, 95.0], [80, 0, 20.0], [0, 80, 15.0], [80, 80, 3.0], [-80, 0, 25.0]],
        dtype=float,
    )
    sites = select_rooftop_sites(cand, 3, rng, min_spacing_m=30.0, height_band_m=(8.0, 45.0), mount_height_m=2.0)
    # the 95 m spire and the 3 m shed are out of band; survivors get +2 m mount
    assert sites.shape[0] == 3
    assert set(np.round(sites[:, 2], 6)) <= {22.0, 17.0, 27.0}


def test_select_rooftop_sites_widens_band_when_starved():
    # All-tower core (every roof above the band): the band must widen to the
    # nearest-in-height roofs instead of returning nothing.
    rng = np.random.default_rng(0)
    cand = np.column_stack([np.linspace(-100, 100, 6), np.zeros(6), np.linspace(60.0, 300.0, 6)])
    sites = select_rooftop_sites(cand, 2, rng, min_spacing_m=30.0, height_band_m=(8.0, 45.0), mount_height_m=2.0)
    assert sites.shape[0] == 2
    # picked from the low end of the tower heights, not the supertalls
    assert np.all(sites[:, 2] <= 200.0)


def test_downtilt_points_broadside_below_horizon():
    sites = build_sites(
        np.array([[0.0, 0.0, 20.0]]),
        n_sectors=3,
        az_coverage_deg=120.0,
        max_range_m=150.0,
        freq_hz=28e9,
        array=(8, 8),
        tx_power_dbm=30.0,
        downtilt_deg=10.0,
    )
    for sector in sites[0].sectors:
        elems = np.asarray(sector.array.element_positions)
        centroid = elems.mean(axis=0)
        np.testing.assert_allclose(centroid, [0.0, 0.0, 20.0], atol=1e-9)
        # infer broadside from the element grid: normal to the panel plane
        u, s, vt = np.linalg.svd(elems - centroid)
        normal = vt[2]
        z = abs(normal[2])
        np.testing.assert_allclose(z, np.sin(np.radians(10.0)), atol=1e-9)


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
