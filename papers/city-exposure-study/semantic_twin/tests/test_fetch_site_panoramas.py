from __future__ import annotations

import numpy as np
import pytest

from fetch_site_panoramas import select, spread_subset


def test_farthest_point_sampling_starts_at_the_centre():
    points = np.array([[0.0, 0.0], [30.0, 0.0], [-30.0, 0.0], [2.0, 1.0]])
    assert spread_subset(points, 1) == [0]


def test_farthest_point_sampling_takes_the_extremes_before_the_middle():
    points = np.array([[0.0, 0.0], [1.0, 0.0], [40.0, 0.0], [-40.0, 0.0]])
    chosen = spread_subset(points, 3)
    assert chosen[0] == 0
    assert set(chosen[1:]) == {2, 3}


def test_farthest_point_sampling_beats_nearest_to_centre_on_spread():
    # A dense cluster at the centre and a few far cameras. Taking the four
    # nearest the centre would never leave the cluster.
    cluster = np.column_stack([np.linspace(-2.0, 2.0, 12), np.zeros(12)])
    far = np.array([[50.0, 0.0], [-50.0, 0.0], [0.0, 50.0], [0.0, -50.0]])
    points = np.vstack([cluster, far])
    chosen = spread_subset(points, 5)
    taken = points[chosen]
    assert np.linalg.norm(taken, axis=1).max() >= 50.0
    assert len({tuple(p) for p in taken} & {tuple(p) for p in far}) == 4


def test_farthest_point_sampling_cannot_ask_for_more_than_it_has():
    points = np.array([[0.0, 0.0], [10.0, 0.0]])
    assert len(spread_subset(points, 9)) == 2
    assert spread_subset(np.zeros((0, 2)), 4) == []


def test_duplicate_positions_are_not_selected_twice():
    points = np.array([[0.0, 0.0], [0.0, 0.0], [0.0, 0.0]])
    assert spread_subset(points, 3) == [0]


def row(panoramas: list[dict], walk_date: str = "2024-01") -> dict:
    return {"key": "test", "panoramas": panoramas, "walk_date": walk_date, "walk_spacing_m": 2.0}


def pano(pano_id: str, east: float, north: float, date: str = "2024-01", links: list[str] | None = None) -> dict:
    return {
        "pano_id": pano_id,
        "east_m": east,
        "north_m": north,
        "date": date,
        "links": ["x"] if links is None else links,
    }


def test_select_takes_only_the_walk_date():
    panoramas = [pano("a", 0.0, 0.0), pano("b", 30.0, 0.0), pano("old", -40.0, 0.0, date="2011-05")]
    picked, provenance = select(row(panoramas), 3)
    assert [p["pano_id"] for p in picked] == ["a", "b"]
    assert provenance["walk_panoramas"] == 2
    assert provenance["walk_date"] == "2024-01"


def test_select_drops_unlinked_photospheres():
    panoramas = [pano("a", 0.0, 0.0), pano("tourist", 20.0, 0.0, links=[])]
    picked, _ = select(row(panoramas), 4)
    assert [p["pano_id"] for p in picked] == ["a"]


def test_select_reports_the_separation_it_achieved():
    panoramas = [pano("a", 0.0, 0.0), pano("b", 30.0, 0.0), pano("c", -30.0, 0.0)]
    _, provenance = select(row(panoramas), 3)
    assert provenance["selected"] == 3
    assert provenance["minimum_separation_m"] == pytest.approx(30.0)
    assert provenance["extent_east_m"] == [-30.0, 30.0]


def test_select_of_a_single_panorama_reports_no_separation():
    _, provenance = select(row([pano("a", 0.0, 0.0)]), 12)
    assert provenance["minimum_separation_m"] is None
    assert provenance["median_separation_m"] is None


def slab(z: float, half: float = 40.0) -> tuple[np.ndarray, np.ndarray]:
    """One horizontal quad at height ``z`` spanning a square about the origin."""
    vertices = np.array(
        [[-half, -half, z], [half, -half, z], [half, half, z], [-half, half, z]],
        dtype=np.float64,
    )
    faces = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int64)
    return vertices, faces


def two_slabs(ground_z: float, roof_z: float) -> tuple[np.ndarray, np.ndarray]:
    """Ground everywhere, plus a roof over the eastern half of it."""
    ground_v, ground_f = slab(ground_z)
    roof_v = np.array(
        [[0.0, -40.0, roof_z], [40.0, -40.0, roof_z], [40.0, 40.0, roof_z], [0.0, 40.0, roof_z]],
        dtype=np.float64,
    )
    roof_f = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int64) + len(ground_v)
    return np.vstack([ground_v, roof_v]), np.vstack([ground_f, roof_f])


def test_open_sky_filter_drops_the_stations_under_the_roof():
    mesh = two_slabs(ground_z=0.0, roof_z=8.0)
    panoramas = [pano("open", -20.0, 0.0), pano("roofed", 20.0, 0.0), pano("also_open", -30.0, 10.0)]
    picked, provenance = select(row(panoramas), 4, support_mesh=mesh, ground_z_m=0.0, open_sky_m=2.5)
    assert [p["pano_id"] for p in picked] == ["open", "also_open"]
    assert provenance["walk_panoramas_dropped_as_roofed"] == 1
    assert provenance["open_sky_m"] == 2.5


def test_open_sky_filter_is_off_when_the_tolerance_is_zero():
    mesh = two_slabs(ground_z=0.0, roof_z=8.0)
    panoramas = [pano("open", -20.0, 0.0), pano("roofed", 20.0, 0.0)]
    picked, provenance = select(row(panoramas), 4, support_mesh=mesh, ground_z_m=0.0, open_sky_m=0.0)
    assert len(picked) == 2
    assert provenance["open_sky_m"] is None


def test_a_capture_that_is_entirely_indoors_is_refused_rather_than_thinned():
    # The Rynek and Capitole failure mode: every station of the largest
    # component has a roof over it, so there is nothing to select from.
    mesh = two_slabs(ground_z=0.0, roof_z=8.0)
    panoramas = [pano("a", 10.0, 0.0), pano("b", 30.0, 5.0)]
    with pytest.raises(SystemExit, match="whole capture is indoors"):
        select(row(panoramas), 4, support_mesh=mesh, ground_z_m=0.0, open_sky_m=2.5)


def test_a_station_at_the_rim_with_nothing_above_it_counts_as_open():
    mesh = two_slabs(ground_z=0.0, roof_z=8.0)
    picked, _ = select(row([pano("outside", -300.0, 0.0)]), 2, support_mesh=mesh, ground_z_m=0.0, open_sky_m=2.5)
    assert [p["pano_id"] for p in picked] == ["outside"]
