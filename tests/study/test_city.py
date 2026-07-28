import numpy as np
import pytest

from aegis.environment.osm_helpers import Building
from aegis.study.city import CityCache, rooftop_candidates


def test_rooftop_candidate_is_centroid_at_eave_height():
    footprint = np.array([[0, 0], [10, 0], [10, 10], [0, 10]], dtype=float)
    b = Building(way_id=1, footprint=footprint, height=20.0, roof_height=3.0)
    pts = rooftop_candidates([b])
    assert pts.shape == (1, 3)
    np.testing.assert_allclose(pts[0, :2], [5.0, 5.0])
    # Site sits at the parapet (eave height = b.height). roof_height is the
    # roof's own peak extent above the eave and is deliberately excluded:
    # rooftop antennas mount at the parapet, not the roof peak.
    assert pts[0, 2] == 20.0


def test_interior_point_inside_concave_footprint():
    # L-shaped footprint whose vertex mean falls in the notch (outside the
    # polygon). The candidate must still land inside.
    from matplotlib.path import Path as MplPath

    fp = np.array(
        [[0, 0], [10, 0], [10, 3], [3, 3], [3, 10], [0, 10]],
        dtype=float,
    )
    assert not MplPath(fp).contains_point(fp.mean(axis=0))
    b = Building(way_id=7, footprint=fp, height=12.0)
    pts = rooftop_candidates([b])
    assert pts.shape == (1, 3)
    assert MplPath(fp).contains_point(pts[0, :2])
    assert pts[0, 2] == 12.0


def test_candidate_z_snaps_to_mesh_roof():
    # The OSM tag claims 30 m but the traced mesh roof is a flat slab at 8 m:
    # the candidate must sit on the mesh (no floating masts), not the tag.
    class FakeMesh:
        vertices = np.array([[0.0, 0.0, 8.0], [10.0, 0.0, 8.0], [10.0, 10.0, 8.0], [0.0, 10.0, 8.0]])
        triangles = np.array([[0, 1, 2], [0, 2, 3]])

    fp = np.array([[0, 0], [10, 0], [10, 10], [0, 10]], dtype=float)
    b = Building(way_id=8, footprint=fp, height=30.0)
    pts = rooftop_candidates([b], mesh=FakeMesh())
    assert pts.shape == (1, 3)
    np.testing.assert_allclose(pts[0, 2], 8.0)


def test_candidate_z_falls_back_to_height_off_mesh():
    # Building outside the mesh extent: fall back to the parsed height.
    class FakeMesh:
        vertices = np.array([[100.0, 100.0, 5.0], [110.0, 100.0, 5.0], [110.0, 110.0, 5.0]])
        triangles = np.array([[0, 1, 2]])

    fp = np.array([[0, 0], [10, 0], [10, 10], [0, 10]], dtype=float)
    b = Building(way_id=9, footprint=fp, height=17.0)
    pts = rooftop_candidates([b], mesh=FakeMesh())
    np.testing.assert_allclose(pts[0, 2], 17.0)


def test_skips_degenerate_footprints():
    b = Building(way_id=2, footprint=np.zeros((2, 2)), height=10.0)
    assert rooftop_candidates([b]).shape == (0, 3)


def test_empty_building_list():
    assert rooftop_candidates([]).shape == (0, 3)


@pytest.mark.slow
def test_city_cache_build_ghent(tmp_path):
    # Network + mesh build. Small radius to keep it cheap.
    # Overpass is a shared third-party API: a 429/timeout is an infrastructure
    # condition, not a code defect, so skip rather than fail the suite.
    from aegis.environment.osm import OverpassRateLimitError, OverpassTimeoutError

    try:
        city = CityCache.build(lat=51.0536, lon=3.7253, radius_m=120.0, cache_dir=tmp_path)
    except (OverpassRateLimitError, OverpassTimeoutError) as exc:
        pytest.skip(f"Overpass API unavailable: {exc}")
    assert city.scene_xml.exists()
    assert city.candidates.shape[1] == 3
    # candidates lie within the fetch radius of the origin
    if city.candidates.shape[0]:
        r = np.linalg.norm(city.candidates[:, :2], axis=1)
        assert np.all(r <= 120.0 + 50.0)  # generous slack for footprint extent
