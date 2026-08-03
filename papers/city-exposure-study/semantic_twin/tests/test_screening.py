from __future__ import annotations

import math

import numpy as np
import pytest

from screen_cities import CANDIDATES, markdown_table
from semantic_twin.screening import (
    EARTH_RADIUS_M,
    azimuth_spread,
    Candidate,
    Panorama,
    connected_components,
    link_lengths_m,
    nearest_neighbour_distances,
    offsets_m,
    panorama_from_metadata,
    probe_points,
    rank,
    screen,
    traverse,
)

CENTRE_LAT = 51.055
CENTRE_LON = 3.722


def at(east_m: float, north_m: float) -> tuple[float, float]:
    """Latitude and longitude of a local offset from the test centre."""
    lat = CENTRE_LAT + math.degrees(north_m / EARTH_RADIUS_M)
    lon = CENTRE_LON + math.degrees(east_m / (EARTH_RADIUS_M * math.cos(math.radians(CENTRE_LAT))))
    return lat, lon


class FakeSource:
    """A metadata endpoint backed by a dictionary of panoramas."""

    def __init__(self, panoramas: dict[str, dict]) -> None:
        self.panoramas = panoramas
        self.pano_id_calls: list[str] = []
        self.location_calls: list[tuple[float, float]] = []

    def by_pano_id(self, pano_id: str) -> dict:
        self.pano_id_calls.append(pano_id)
        return self.panoramas.get(pano_id, {})

    def by_location(self, lat: float, lon: float, radius_m: float) -> dict:
        self.location_calls.append((lat, lon))
        best, best_distance = None, math.inf
        for metadata in self.panoramas.values():
            east = math.radians(metadata["lng"] - lon) * EARTH_RADIUS_M * math.cos(math.radians(lat))
            north = math.radians(metadata["lat"] - lat) * EARTH_RADIUS_M
            distance = math.hypot(east, north)
            if distance < best_distance:
                best, best_distance = metadata, distance
        return best if best is not None and best_distance <= radius_m else {}


def make_metadata(pano_id: str, east_m: float, north_m: float, links: list[str], date: str = "2023-05") -> dict:
    lat, lon = at(east_m, north_m)
    return {
        "panoId": pano_id,
        "lat": lat,
        "lng": lon,
        "date": date,
        "copyright": "From the Owner, Photo by: Inhouse",
        "links": [{"panoId": link, "heading": 0.0} for link in links],
        "tilt": 91.2,
        "roll": 0.4,
    }


def chain(count: int, spacing_m: float, prefix: str = "p", date: str = "2023-05") -> dict[str, dict]:
    """A straight line of linked panoramas through the centre, running east."""
    ids = [f"{prefix}{index}" for index in range(count)]
    panoramas = {}
    for index, pano_id in enumerate(ids):
        links = [ids[j] for j in (index - 1, index + 1) if 0 <= j < count]
        east = (index - (count - 1) / 2.0) * spacing_m
        panoramas[pano_id] = make_metadata(pano_id, east, 0.0, links, date=date)
    return panoramas


def grid(spacing_m: float, reach_m: float, prefix: str = "g", date: str = "2023-05") -> dict[str, dict]:
    """A square grid of panoramas linked to their four neighbours.

    A straight chain is not enough to exercise coverage: it can hold every
    panorama in one component and still leave half the square unvisited, which is
    exactly the case the coverage measure exists to catch.
    """
    steps = int(reach_m // spacing_m)
    cells = [(i, j) for i in range(-steps, steps + 1) for j in range(-steps, steps + 1)]
    present = {cell for cell in cells if math.hypot(cell[0] * spacing_m, cell[1] * spacing_m) <= reach_m}
    panoramas = {}
    for i, j in sorted(present):
        neighbours = [
            f"{prefix}_{i + di}_{j + dj}"
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1))
            if (i + di, j + dj) in present
        ]
        panoramas[f"{prefix}_{i}_{j}"] = make_metadata(
            f"{prefix}_{i}_{j}", i * spacing_m, j * spacing_m, neighbours, date=date
        )
    return panoramas


CANDIDATE = Candidate("test", "Test square", "Nowhere", CENTRE_LAT, CENTRE_LON, "test")


def test_offsets_recover_the_metres_they_were_built_from():
    panorama = panorama_from_metadata(make_metadata("a", 30.0, -40.0, []))
    offsets = offsets_m(CENTRE_LAT, CENTRE_LON, [panorama])
    assert offsets.shape == (1, 2)
    assert offsets[0] == pytest.approx([30.0, -40.0], abs=1e-3)


def test_offsets_of_an_empty_set_are_empty():
    assert offsets_m(CENTRE_LAT, CENTRE_LON, []).shape == (0, 2)


def test_panorama_from_metadata_returns_none_when_nothing_was_found():
    assert panorama_from_metadata({}) is None
    assert panorama_from_metadata({"panoId": ""}) is None


def test_links_without_a_pano_id_are_dropped():
    metadata = make_metadata("a", 0.0, 0.0, [])
    metadata["links"] = [{"heading": 12.0}, {"panoId": "b"}, "not a link"]
    panorama = panorama_from_metadata(metadata)
    assert panorama is not None
    assert panorama.links == ("b",)


def test_a_level_camera_with_no_pose_solution_is_flagged():
    degenerate = panorama_from_metadata(
        {"panoId": "a", "lat": CENTRE_LAT, "lng": CENTRE_LON, "tilt": 90.0, "roll": 0.0}
    )
    measured = panorama_from_metadata({"panoId": "b", "lat": CENTRE_LAT, "lng": CENTRE_LON, "tilt": 102.3, "roll": 4.2})
    absent = panorama_from_metadata({"panoId": "c", "lat": CENTRE_LAT, "lng": CENTRE_LON})
    assert degenerate is not None and not degenerate.has_orientation
    assert measured is not None and measured.has_orientation
    assert absent is not None and not absent.has_orientation


def test_nearest_neighbour_distances_on_a_known_spacing():
    points = np.array([[0.0, 0.0], [3.0, 0.0], [7.0, 0.0]])
    assert nearest_neighbour_distances(points) == pytest.approx([3.0, 3.0, 4.0])


def test_nearest_neighbour_distances_need_two_points():
    assert nearest_neighbour_distances(np.zeros((1, 2))).size == 0
    assert nearest_neighbour_distances(np.zeros((0, 2))).size == 0


def test_link_lengths_count_each_undirected_edge_once():
    panoramas = [panorama_from_metadata(m) for m in chain(3, 5.0).values()]
    positions = offsets_m(CENTRE_LAT, CENTRE_LON, panoramas)
    lengths = link_lengths_m(panoramas, positions)
    assert lengths.size == 2
    assert lengths == pytest.approx([5.0, 5.0], abs=1e-3)


def test_links_pointing_outside_the_set_are_not_measured():
    panoramas = [panorama_from_metadata(make_metadata("a", 0.0, 0.0, ["somewhere_else"]))]
    positions = offsets_m(CENTRE_LAT, CENTRE_LON, panoramas)
    assert link_lengths_m(panoramas, positions).size == 0


def test_connected_components_splits_two_unlinked_chains():
    panoramas = [panorama_from_metadata(m) for m in (chain(4, 5.0, "a") | chain(3, 5.0, "b")).values()]
    components = connected_components(panoramas)
    assert [len(component) for component in components] == [4, 3]


def test_a_single_chain_is_one_component():
    panoramas = [panorama_from_metadata(m) for m in chain(5, 5.0).values()]
    assert len(connected_components(panoramas)) == 1


def test_probe_points_land_on_their_rings():
    points = probe_points(CENTRE_LAT, CENTRE_LON, 60.0, (0.5,), 4)
    assert len(points) == 5
    panoramas = [Panorama("x", lat, lon, "", "") for lat, lon in points[1:]]
    radii = np.linalg.norm(offsets_m(CENTRE_LAT, CENTRE_LON, panoramas), axis=1)
    assert radii == pytest.approx(np.full(4, 30.0), abs=1e-3)


def test_traversal_expands_the_interior_and_stops_at_the_boundary():
    # Eleven panoramas 20 m apart, so five of them sit outside the 60 m disc.
    source = FakeSource(chain(11, 20.0))
    traversal = traverse(source, CANDIDATE, radius_m=60.0, workers=2)
    inside = {
        pano_id
        for pano_id, metadata in source.panoramas.items()
        if abs(offsets_m(CENTRE_LAT, CENTRE_LON, [panorama_from_metadata(metadata)])[0][0]) <= 60.0
    }
    assert inside <= set(traversal.panoramas)
    # The walk reaches one ring beyond the disc to learn where the disc ends and
    # then stops, so it never leaks down the street network.
    assert len(traversal.panoramas) == len(inside) + 2
    assert not traversal.truncated


def test_traversal_stops_at_the_panorama_cap():
    source = FakeSource(chain(60, 1.5))
    traversal = traverse(source, CANDIDATE, radius_m=60.0, max_panoramas=10, workers=2)
    assert traversal.truncated
    assert len(traversal.panoramas) <= 10


def test_traversal_of_a_site_with_no_coverage_is_empty():
    source = FakeSource({})
    traversal = traverse(source, CANDIDATE, radius_m=60.0, workers=2)
    assert traversal.panoramas == {}
    assert traversal.seed is None
    assert traversal.requests == 1


def test_screen_reproduces_a_known_spacing_and_calls_the_endpoint_once_per_panorama():
    panoramas = grid(10.0, 60.0)
    source = FakeSource(panoramas)
    row = screen(source, CANDIDATE, radius_m=60.0, workers=2)
    assert row["panorama_count"] == len(panoramas)
    assert row["median_spacing_m"] == pytest.approx(10.0, abs=1e-3)
    assert row["median_link_length_m"] == pytest.approx(10.0, abs=1e-3)
    assert row["distinct_dates"] == 1
    assert row["connected"] is True
    assert row["walk_coverage"] == pytest.approx(1.0)
    assert row["walk_azimuth_spread"] == pytest.approx(1.0)
    assert row["walk_count"] == len(panoramas)
    assert row["requests"] == len(source.pano_id_calls) + len(source.location_calls)
    assert len(row["panoramas"]) == len(panoramas)


def test_a_walk_along_one_edge_of_the_square_does_not_pass_as_a_walk_of_the_square():
    # A dense line down the middle, and a sparser earlier capture that covers the
    # whole square. The line is the biggest single-date walk and every one of its
    # panoramas is in one component, so counting components alone would call it
    # connected, but it only ever sees the facades at two ends.
    source = FakeSource(chain(55, 2.0, "line", date="2024-03") | grid(15.0, 60.0, "old", date="2019-08"))
    row = screen(source, CANDIDATE, radius_m=60.0, workers=2)
    assert row["walk_date"] == "2024-03"
    assert row["walk_count"] == 55
    assert row["walk_fraction_of_date"] == 1.0
    assert row["walk_azimuth_spread"] < 0.6
    assert row["connected"] is False


def test_screen_reports_a_second_component_the_walk_could_not_reach():
    # Two parallel chains that never link to each other. The walk starts in one
    # of them, so only the probes can discover the other.
    far = {key: dict(value) for key, value in chain(9, 6.0, "b").items()}
    for metadata in far.values():
        metadata["lat"] = at(0.0, 40.0)[0]
    source = FakeSource(chain(9, 6.0, "a") | far)
    row = screen(source, CANDIDATE, radius_m=60.0, workers=2)
    assert row["connected"] is False
    assert row["linked_panoramas_the_walk_missed"]
    assert len(row["components"]) == 2
    assert row["reachable_from_centre"] == 9


def test_screen_counts_distinct_dates():
    panoramas = chain(5, 6.0, "a", date="2019-06") | chain(7, 6.0, "b", date="2024-09")
    for pano_id, metadata in panoramas.items():
        if pano_id.startswith("b"):
            metadata["lat"] = at(0.0, 12.0)[0]
    source = FakeSource(panoramas)
    row = screen(source, CANDIDATE, radius_m=60.0, workers=2)
    assert row["distinct_dates"] == 2
    assert row["dates"] == ["2019-06", "2024-09"]
    # The walk is one capture date, not the union of two that never link.
    assert row["walk_date"] == "2024-09"
    assert row["walk_count"] == 7
    assert [epoch["date"] for epoch in row["epochs"]] == ["2024-09", "2019-06"]


def test_an_unlinked_photosphere_is_not_a_broken_link_graph():
    panoramas = grid(10.0, 60.0)
    lat, lon = at(0.0, 33.0)  # exactly on a probe point, so a probe finds it
    panoramas["tourist"] = {
        "panoId": "tourist",
        "lat": lat,
        "lng": lon,
        "date": "2021-07",
        "copyright": "(c) Some Visitor",
        "links": [],
        "tilt": 90.0,
        "roll": 0.0,
    }
    source = FakeSource(panoramas)
    row = screen(source, CANDIDATE, radius_m=60.0, workers=2)
    assert row["unlinked_panoramas"] == 1
    assert row["panoramas_without_orientation"] == 1
    assert row["linked_panoramas_the_walk_missed"] == []
    assert row["connected"] is True


def test_the_largest_recent_walk_is_reported_beside_the_largest_walk():
    # The biggest walk is fourteen years old and the mesh is current, so the
    # newer and smaller walk has to stay visible in the row.
    panoramas = grid(10.0, 60.0, "old", date="2011-05") | grid(20.0, 60.0, "new", date="2024-08")
    # One link across the two captures, which is how a walk finds the other
    # epoch at all: the endpoint links neighbours, not the same place at a
    # different date.
    panoramas["old_0_0"]["links"].append({"panoId": "new_1_0", "heading": 90.0})
    source = FakeSource(panoramas)
    row = screen(source, CANDIDATE, radius_m=60.0, workers=2)
    assert row["walk_date"] == "2011-05"
    assert row["walk_year"] == 2011
    assert row["walk_age_years"] >= 14
    assert row["recent_walk"] is not None
    assert row["recent_walk"]["date"] == "2024-08"
    assert row["recent_walk"]["walk_count"] < row["walk_count"]


def test_a_site_with_only_old_captures_reports_no_recent_walk():
    source = FakeSource(grid(10.0, 60.0, "old", date="2011-05"))
    row = screen(source, CANDIDATE, radius_m=60.0, workers=2)
    assert row["recent_walk"] is None


def test_a_line_through_the_centre_fills_only_two_azimuth_sectors():
    line = np.column_stack([np.linspace(-50.0, 50.0, 41), np.zeros(41)])
    assert azimuth_spread(line) == pytest.approx(2.0 / 16.0)


def test_a_ring_about_the_centre_fills_every_azimuth_sector():
    angles = np.linspace(0.0, 2.0 * math.pi, 64, endpoint=False)
    ring = np.column_stack([40.0 * np.sin(angles), 40.0 * np.cos(angles)])
    assert azimuth_spread(ring) == pytest.approx(1.0)


def test_a_cluster_at_the_centre_has_no_azimuth_spread():
    cluster = np.column_stack([np.linspace(-1.0, 1.0, 20), np.linspace(-1.0, 1.0, 20)])
    assert azimuth_spread(cluster) == 0.0
    assert azimuth_spread(np.zeros((0, 2))) == 0.0


def test_provider_is_read_from_the_copyright_string():
    from semantic_twin.screening import provider_of

    linked = panorama_from_metadata(make_metadata("a", 0.0, 0.0, []))
    assert linked is not None and provider_of(linked) == "Inhouse"
    tourist = Panorama("b", CENTRE_LAT, CENTRE_LON, "2021-07", "(c) Some Visitor")
    assert provider_of(tourist) == "Some Visitor"
    assert provider_of(Panorama("c", CENTRE_LAT, CENTRE_LON, "", "")) == "unknown"


def test_screen_of_a_site_with_no_coverage_says_so_without_crashing():
    source = FakeSource({})
    row = screen(source, CANDIDATE, radius_m=60.0, workers=2)
    assert row["panorama_count"] == 0
    assert row["median_spacing_m"] is None
    assert row["connected"] is False


def test_rank_gates_on_connectivity_before_it_looks_at_the_walk():
    rows = [
        {"key": "dense_but_broken", "connected": False, "walk_count": 90, "walk_spacing_m": 1.0},
        {"key": "short_and_whole", "connected": True, "walk_count": 25, "walk_spacing_m": 1.5},
        {"key": "long_and_whole", "connected": True, "walk_count": 60, "walk_spacing_m": 3.0},
    ]
    ordered = [row["key"] for row in rank(rows)]
    assert ordered == ["long_and_whole", "short_and_whole", "dense_but_broken"]


def test_rank_pushes_a_connected_site_with_too_short_a_walk_down():
    rows = [
        {"key": "tiny", "connected": True, "walk_count": 3, "walk_spacing_m": 1.0},
        {"key": "real", "connected": True, "walk_count": 40, "walk_spacing_m": 9.0},
    ]
    assert [row["key"] for row in rank(rows)] == ["real", "tiny"]


def test_rank_breaks_a_tie_on_spacing_and_tolerates_a_missing_one():
    rows = [
        {"key": "empty", "connected": True, "walk_count": 30, "walk_spacing_m": None},
        {"key": "measured", "connected": True, "walk_count": 30, "walk_spacing_m": 8.0},
    ]
    assert [row["key"] for row in rank(rows)] == ["measured", "empty"]


def test_candidate_rejects_an_impossible_position():
    with pytest.raises(ValueError):
        Candidate("bad", "Bad", "Nowhere", 91.0, 0.0, "test")
    with pytest.raises(ValueError):
        Candidate("bad", "Bad", "Nowhere", 0.0, 181.0, "test")
    with pytest.raises(ValueError):
        Candidate("", "Bad", "Nowhere", 0.0, 0.0, "test")


def test_candidate_keys_are_unique_and_positions_are_valid():
    keys = [candidate.key for candidate in CANDIDATES]
    assert len(keys) == len(set(keys))
    assert {"korenmarkt", "milan_duomo"} <= set(keys)


def test_markdown_table_renders_a_missing_spacing_without_formatting_none():
    table = markdown_table(
        [
            {
                "rank": 1,
                "name": "Nowhere",
                "country": "Nowhere",
                "panorama_count": 0,
                "distinct_dates": 0,
                "walk_date": None,
                "walk_count": 0,
                "walk_spacing_m": None,
                "walk_span_m": 0.0,
                "walk_coverage": 0.0,
                "walk_azimuth_spread": 0.0,
                "recent_walk": None,
                "connected": False,
                "requests": 17,
            }
        ]
    )
    assert "n/a" in table
    assert "None" not in table
