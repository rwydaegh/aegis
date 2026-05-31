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


def test_skips_degenerate_footprints():
    b = Building(way_id=2, footprint=np.zeros((2, 2)), height=10.0)
    assert rooftop_candidates([b]).shape == (0, 3)


def test_empty_building_list():
    assert rooftop_candidates([]).shape == (0, 3)


@pytest.mark.slow
def test_city_cache_build_ghent(tmp_path):
    # Network + mesh build. Small radius to keep it cheap.
    city = CityCache.build(lat=51.0536, lon=3.7253, radius_m=120.0, cache_dir=tmp_path)
    assert city.scene_xml.exists()
    assert city.candidates.shape[1] == 3
    # candidates lie within the fetch radius of the origin
    if city.candidates.shape[0]:
        r = np.linalg.norm(city.candidates[:, :2], axis=1)
        assert np.all(r <= 120.0 + 50.0)  # generous slack for footprint extent
