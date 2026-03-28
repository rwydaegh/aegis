import numpy as np
import pytest

from aegis.environment.geo import (
    ecef_to_enu,
    enu_to_yup,
    obb_aabb_intersect,
    sphere_aabb_intersect,
    transverse_mercator_forward,
    transverse_mercator_inverse,
    wgs84_to_ecef,
)


class TestWgs84Ecef:
    def test_equator_prime_meridian(self):
        ecef = wgs84_to_ecef(0.0, 0.0, 0.0)
        assert ecef[0] == pytest.approx(6378137.0, abs=1)
        assert ecef[1] == pytest.approx(0.0, abs=1)
        assert ecef[2] == pytest.approx(0.0, abs=1)

    def test_north_pole(self):
        ecef = wgs84_to_ecef(90.0, 0.0, 0.0)
        assert ecef[0] == pytest.approx(0.0, abs=1)
        assert ecef[1] == pytest.approx(0.0, abs=1)
        assert ecef[2] == pytest.approx(6356752.314, abs=1)

    def test_ghent(self):
        ecef = wgs84_to_ecef(51.05, 3.72, 0.0)
        assert ecef[0] == pytest.approx(4009241, abs=100)
        assert ecef[1] == pytest.approx(260671, abs=100)
        assert ecef[2] == pytest.approx(4937043, abs=100)


class TestEcefEnu:
    def test_origin_is_zero(self):
        origin_lat, origin_lon = 51.05, 3.72
        origin_ecef = wgs84_to_ecef(origin_lat, origin_lon, 0.0)
        enu = ecef_to_enu(origin_ecef, origin_ecef, origin_lat, origin_lon)
        np.testing.assert_allclose(enu, [0, 0, 0], atol=1e-6)

    def test_east_is_positive_x(self):
        origin_lat, origin_lon = 51.05, 3.72
        origin_ecef = wgs84_to_ecef(origin_lat, origin_lon, 0.0)
        east_ecef = wgs84_to_ecef(origin_lat, origin_lon + 0.001, 0.0)
        enu = ecef_to_enu(east_ecef, origin_ecef, origin_lat, origin_lon)
        assert enu[0] > 0
        assert abs(enu[1]) < abs(enu[0])
        assert abs(enu[2]) < 1

    def test_north_is_positive_y(self):
        origin_lat, origin_lon = 51.05, 3.72
        origin_ecef = wgs84_to_ecef(origin_lat, origin_lon, 0.0)
        north_ecef = wgs84_to_ecef(origin_lat + 0.001, origin_lon, 0.0)
        enu = ecef_to_enu(north_ecef, origin_ecef, origin_lat, origin_lon)
        assert enu[1] > 0
        assert abs(enu[0]) < abs(enu[1])

    def test_up_is_positive_z(self):
        origin_lat, origin_lon = 51.05, 3.72
        origin_ecef = wgs84_to_ecef(origin_lat, origin_lon, 0.0)
        up_ecef = wgs84_to_ecef(origin_lat, origin_lon, 100.0)
        enu = ecef_to_enu(up_ecef, origin_ecef, origin_lat, origin_lon)
        assert enu[2] == pytest.approx(100.0, abs=1)


class TestEnuToYup:
    def test_conversion(self):
        enu = np.array([10.0, 20.0, 30.0])
        yup = enu_to_yup(enu)
        np.testing.assert_allclose(yup, [10.0, 30.0, -20.0])

    def test_batch(self):
        enu = np.array([[1, 2, 3], [4, 5, 6]])
        yup = enu_to_yup(enu)
        expected = np.array([[1, 3, -2], [4, 6, -5]])
        np.testing.assert_allclose(yup, expected)


class TestTransverseMercator:
    def test_origin_is_zero(self):
        x, y = transverse_mercator_forward(51.05, 3.72, 51.05, 3.72)
        assert x == pytest.approx(0.0, abs=1e-6)
        assert y == pytest.approx(0.0, abs=1e-6)

    def test_round_trip(self):
        lat, lon = 51.06, 3.73
        x, y = transverse_mercator_forward(lat, lon, 51.05, 3.72)
        lat2, lon2 = transverse_mercator_inverse(x, y, 51.05, 3.72)
        assert lat2 == pytest.approx(lat, abs=1e-8)
        assert lon2 == pytest.approx(lon, abs=1e-8)

    def test_scale_roughly_correct(self):
        x, y = transverse_mercator_forward(52.05, 3.72, 51.05, 3.72)
        assert abs(y) == pytest.approx(111_000, rel=0.01)


class TestSphereAabbIntersect:
    def test_sphere_inside_box(self):
        assert sphere_aabb_intersect(
            center=np.array([0, 0, 0]),
            radius=1.0,
            aabb_min=np.array([-5, -5, -5]),
            aabb_max=np.array([5, 5, 5]),
        )

    def test_sphere_outside_box(self):
        assert not sphere_aabb_intersect(
            center=np.array([100, 100, 100]),
            radius=1.0,
            aabb_min=np.array([-5, -5, -5]),
            aabb_max=np.array([5, 5, 5]),
        )

    def test_sphere_touching_face(self):
        assert sphere_aabb_intersect(
            center=np.array([6, 0, 0]),
            radius=1.5,
            aabb_min=np.array([-5, -5, -5]),
            aabb_max=np.array([5, 5, 5]),
        )

    def test_sphere_touching_edge(self):
        assert sphere_aabb_intersect(
            center=np.array([6, 6, 0]),
            radius=2.0,
            aabb_min=np.array([-5, -5, -5]),
            aabb_max=np.array([5, 5, 5]),
        )


class TestObbAabbIntersect:
    def test_axis_aligned_overlap(self):
        assert obb_aabb_intersect(
            obb_center=np.array([0, 0, 0]),
            obb_half_axes=np.eye(3) * 5,
            aabb_min=np.array([-3, -3, -3]),
            aabb_max=np.array([3, 3, 3]),
        )

    def test_axis_aligned_no_overlap(self):
        assert not obb_aabb_intersect(
            obb_center=np.array([20, 0, 0]),
            obb_half_axes=np.eye(3) * 5,
            aabb_min=np.array([-3, -3, -3]),
            aabb_max=np.array([3, 3, 3]),
        )

    def test_rotated_overlap(self):
        c45 = np.cos(np.pi / 4)
        s45 = np.sin(np.pi / 4)
        half_axes = np.array(
            [
                [c45 * 5, s45 * 5, 0],
                [-s45 * 5, c45 * 5, 0],
                [0, 0, 5],
            ]
        )
        assert obb_aabb_intersect(
            obb_center=np.array([0, 0, 0]),
            obb_half_axes=half_axes,
            aabb_min=np.array([-1, -1, -1]),
            aabb_max=np.array([1, 1, 1]),
        )
