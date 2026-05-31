import numpy as np

from aegis.environment.osm import parse_osm_xml
from aegis.study.geo import enu_to_latlon, latlon_to_enu


def test_round_trip():
    lat0, lon0 = 51.0536, 3.7253  # Ghent
    lat, lon = 51.0550, 3.7280
    x, y = latlon_to_enu(lat, lon, lat0, lon0)
    lat2, lon2 = enu_to_latlon(x, y, lat0, lon0)
    assert abs(lat2 - lat) < 1e-7
    assert abs(lon2 - lon) < 1e-7


def test_origin_maps_to_zero():
    x, y = latlon_to_enu(51.0536, 3.7253, 51.0536, 3.7253)
    assert abs(x) < 1e-6
    assert abs(y) < 1e-6


def test_east_is_positive_x():
    x, _ = latlon_to_enu(51.0536, 3.7300, 51.0536, 3.7253)
    assert x > 0


def test_frame_matches_parse_osm_xml():
    """The study projection must place a node at the exact XY parse_osm_xml does."""
    lat0, lon0 = 51.0536, 3.7253
    nodes = [
        (1, 51.0540, 3.7260),
        (2, 51.0540, 3.7265),
        (3, 51.0545, 3.7265),
        (4, 51.0545, 3.7260),
    ]
    node_xml = "".join(f'<node id="{nid}" lat="{lat}" lon="{lon}"/>' for nid, lat, lon in nodes)
    refs = "".join(f'<nd ref="{nid}"/>' for nid, _, _ in nodes)
    refs += '<nd ref="1"/>'  # close the ring
    xml = f'<osm version="0.6">{node_xml}<way id="100">{refs}<tag k="building" v="yes"/></way></osm>'

    buildings, _, _ = parse_osm_xml(xml, origin_lat=lat0, origin_lon=lon0)
    assert len(buildings) == 1
    footprint = buildings[0].footprint

    expected = np.array([latlon_to_enu(lat, lon, lat0, lon0) for _, lat, lon in nodes])
    # parse_osm_xml may drop the duplicate closing vertex; compare the unique ring.
    np.testing.assert_allclose(footprint[: len(nodes)], expected, atol=1e-6)
