import numpy as np

from aegis.study.walk import sample_trajectory


def test_constant_speed_slot_count():
    route_xy = np.array([[0.0, 0.0], [14.0, 0.0]])  # 14 m straight
    traj = sample_trajectory(route_xy, speed_mps=1.4, dt_s=1.0)
    # 14 m / 1.4 m/s = 10 s -> 11 samples (t=0..10)
    assert traj.positions.shape == (11, 2)
    np.testing.assert_allclose(traj.positions[0], [0, 0])
    np.testing.assert_allclose(traj.positions[-1], [14, 0], atol=1e-6)
    np.testing.assert_allclose(traj.headings_rad, 0.0, atol=1e-6)


def test_entry_offset_staggers_start():
    route_xy = np.array([[0.0, 0.0], [14.0, 0.0]])
    traj = sample_trajectory(route_xy, speed_mps=1.4, dt_s=1.0, entry_offset_s=3.0)
    assert traj.t0_s == 3.0


def test_corner_heading_changes():
    route_xy = np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 10.0]])
    traj = sample_trajectory(route_xy, speed_mps=1.0, dt_s=1.0)
    # first samples head east (0 rad), last samples head north (pi/2)
    assert abs(traj.headings_rad[0]) < 1e-6
    assert abs(traj.headings_rad[-1] - np.pi / 2) < 1e-6


def test_single_point_route():
    traj = sample_trajectory(np.array([[5.0, 5.0]]), speed_mps=1.4, dt_s=1.0)
    assert traj.positions.shape == (1, 2)
    np.testing.assert_allclose(traj.positions[0], [5.0, 5.0])
