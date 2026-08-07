"""A walk that is a route, not a blob.

``build_walk`` lays a grid over a disc and orders the survivors. This module's
subject is the other thing: a route whose standpoints are the panorama positions
themselves, ordered along the link graph the imagery provider published. Each
test below pins one property that separates the two, or one failure the route
would otherwise inherit from the walk.
"""

from __future__ import annotations

import hashlib
import itertools
import json

import numpy as np
import pytest

from semantic_twin.acquire.cache import route_key
from semantic_twin.walk import site as walk_site
from semantic_twin.walk.ground import ground_under_camera
from semantic_twin.walk.links import (
    LinkGraph,
    bridge_components,
    fragments,
    link_graph_from_screening,
    link_graph_from_sequences,
)
from semantic_twin.walk.ordering import EXACT_ORDER_LIMIT, _held_karp, _nearest_neighbour_two_opt, order_along_links
from semantic_twin.walk.route import (
    HEAD_HEIGHT_M,
    PanoramaRoute,
    admitted_route_positions,
    build_panorama_route,
    load_admitted_stations,
    panorama_walk,
    register_road_leg,
)
from semantic_twin.walk.site import densify, street_route_request
from semantic_twin.walk.grid import build_walk
from semantic_twin.walk.ground import ground_height
from semantic_twin.walk.model import Walk


class Boxes:
    """One ground plane and a set of axis aligned boxes, intersected analytically.

    Enough geometry to state a street: two long boxes with a gap between them is
    a street, one box overhead is an arcade. A mesh loader here would hide the
    layout under test and would need a file on disk.
    """

    def __init__(self, ground_z: float = 0.0, boxes: tuple = ()) -> None:
        self.ground_z = ground_z
        self.boxes = [(np.asarray(lo, float), np.asarray(hi, float)) for lo, hi in boxes]

    def intersect(self, origins, directions):  # noqa: ANN001, ANN201
        origins = np.asarray(origins, float)
        directions = np.asarray(directions, float)
        count = origins.shape[0]
        best = np.full(count, np.inf)
        normal = np.zeros((count, 3))
        index = np.full(count, -1, dtype=np.int64)

        with np.errstate(divide="ignore", invalid="ignore"):
            travel = (self.ground_z - origins[:, 2]) / directions[:, 2]
        reaches = np.isfinite(travel) & (travel > 1.0e-9)
        best = np.where(reaches, travel, best)
        normal[reaches] = np.array([0.0, 0.0, 1.0])
        index[reaches] = 0

        for slot, (low, high) in enumerate(self.boxes):
            with np.errstate(divide="ignore", invalid="ignore"):
                near = (low - origins) / directions
                far = (high - origins) / directions
            enter = np.minimum(near, far)
            leave = np.maximum(near, far)
            first = np.nanmax(np.where(np.isnan(enter), -np.inf, enter), axis=1)
            last = np.nanmin(np.where(np.isnan(leave), np.inf, leave), axis=1)
            travel = np.where(first > 1.0e-9, first, last)
            reaches = (first <= last) & (travel > 1.0e-9) & (travel < best)
            axis = np.argmax(np.where(np.isnan(enter), -np.inf, enter), axis=1)
            face = np.zeros((count, 3))
            face[np.arange(count), axis] = 1.0
            best = np.where(reaches, travel, best)
            normal[reaches] = face[reaches]
            index[reaches] = slot + 1

        hit = np.isfinite(best)
        return hit, np.where(hit, best, 1.0e30), normal, index


def straight_graph(count: int = 5, step: float = 10.0) -> LinkGraph:
    """A chain of nodes down one straight street, linked end to end."""
    position = {f"n{i}": np.array([float(i) * step, 0.0]) for i in range(count)}
    neighbours = {f"n{i}": tuple(f"n{j}" for j in (i - 1, i + 1) if 0 <= j < count) for i in range(count)}
    return LinkGraph(position=position, neighbours=neighbours, provenance={"source": "test"})


def station(name: str, node: str, xy: tuple[float, float], z: float = 2.5) -> dict:
    return {"name": name, "node": node, "camera_enu_m": np.array([xy[0], xy[1], z])}


# --- the link graph ----------------------------------------------------------


def test_road_distance_follows_the_links_and_not_the_crow():
    """An L shaped street is longer than the straight line across its corner."""
    position = {
        "a": np.array([0.0, 0.0]),
        "corner": np.array([30.0, 0.0]),
        "b": np.array([30.0, 40.0]),
    }
    graph = LinkGraph(
        position=position,
        neighbours={"a": ("corner",), "corner": ("a", "b"), "b": ("corner",)},
        provenance={},
    )
    assert graph.distances_from("a")["b"] == pytest.approx(70.0)
    assert np.linalg.norm(position["b"] - position["a"]) == pytest.approx(50.0)
    assert graph.road_between("a", "b") == ["a", "corner", "b"]


def test_a_node_across_a_block_is_unreachable_rather_than_near():
    """Two nodes ten metres apart with no link between them do not reach each other."""
    graph = LinkGraph(
        position={"a": np.array([0.0, 0.0]), "b": np.array([10.0, 0.0])},
        neighbours={"a": (), "b": ()},
        provenance={},
    )
    assert "b" not in graph.distances_from("a")
    assert graph.road_between("a", "b") == []


def test_screening_links_are_symmetrised_and_dangling_ends_dropped():
    """Street View names a neighbour one way round often enough to matter."""
    row = {
        "key": "somewhere",
        "panoramas": [
            {"pano_id": "a", "east_m": 0.0, "north_m": 0.0, "links": ["b", "off_the_edge"]},
            {"pano_id": "b", "east_m": 5.0, "north_m": 0.0, "links": []},
        ],
    }
    graph = link_graph_from_screening(row)
    assert graph.neighbours["b"] == ("a",)
    assert "off_the_edge" not in graph.position
    assert graph.edge_count == 1


def test_two_mapillary_sequences_never_link_unless_asked():
    """Consecutive frames of one drive are neighbours. Two drives are not."""
    records = [
        {"image_id": "1", "sequence_id": "s", "easting_m": 0.0, "northing_m": 0.0, "captured_at": 10},
        {"image_id": "2", "sequence_id": "s", "easting_m": 3.0, "northing_m": 0.0, "captured_at": 20},
        {"image_id": "3", "sequence_id": "t", "easting_m": 3.5, "northing_m": 0.0, "captured_at": 99},
    ]
    plain = link_graph_from_sequences(records)
    assert plain.neighbours["1"] == ("2",)
    assert "3" not in plain.distances_from("1")
    assert plain.provenance["cross_sequence_links_added"] == 0

    bridged = link_graph_from_sequences(records, bridge_m=1.0)
    assert "3" in bridged.distances_from("1")
    assert bridged.provenance["bridge_m"] == 1.0
    assert bridged.provenance["cross_sequence_links_added"] == 1


def test_sequence_order_comes_from_capture_time_not_from_input_order():
    records = [
        {"image_id": "late", "sequence_id": "s", "easting_m": 20.0, "northing_m": 0.0, "captured_at": 300},
        {"image_id": "early", "sequence_id": "s", "easting_m": 0.0, "northing_m": 0.0, "captured_at": 100},
        {"image_id": "middle", "sequence_id": "s", "easting_m": 10.0, "northing_m": 0.0, "captured_at": 200},
    ]
    graph = link_graph_from_sequences(records)
    assert graph.neighbours["middle"] == ("early", "late")
    assert graph.distances_from("early")["late"] == pytest.approx(20.0)


def test_merging_two_graphs_keeps_both_and_counts_what_it_dropped():
    left = LinkGraph(position={"a": np.zeros(2)}, neighbours={"a": ("gone",)}, provenance={"source": "left"})
    right = LinkGraph(
        position={"b": np.array([1.0, 0.0]), "c": np.array([2.0, 0.0])},
        neighbours={"b": ("c",), "c": ("b",)},
        provenance={"source": "right"},
    )
    merged = left.merge(right)
    assert set(merged.position) == {"a", "b", "c"}
    assert merged.provenance["links_dropped_without_a_position"] == 1
    assert merged.edge_count == 1


# --- ordering ----------------------------------------------------------------


def test_stations_down_one_street_come_back_in_street_order():
    graph = straight_graph(5)
    scrambled = ["n3", "n0", "n4", "n1", "n2"]
    result = order_along_links(scrambled, graph)
    assert [scrambled[i] for i in result["order"]] == ["n0", "n1", "n2", "n3", "n4"]
    assert result["road_length_m"] == pytest.approx(40.0)
    assert result["road_m"] == pytest.approx([0.0, 10.0, 10.0, 10.0, 10.0])


def test_the_route_direction_does_not_depend_on_the_input_order():
    graph = straight_graph(4)
    forward = order_along_links(["n0", "n1", "n2", "n3"], graph)
    names = ["n3", "n2", "n1", "n0"]
    backward = order_along_links(names, graph)
    assert [names[i] for i in backward["order"]] == ["n0", "n1", "n2", "n3"]
    assert forward["road_length_m"] == pytest.approx(backward["road_length_m"])


def test_street_request_is_read_only_and_keyed_by_registered_span(monkeypatch, tmp_path):
    monkeypatch.setattr(walk_site, "site_anchor", lambda *_args, **_kwargs: (51.0, 3.0))
    cameras = np.array([[-10.0, 0.0, 2.5], [0.0, 3.0, 2.5], [20.0, 0.0, 2.5]])

    chosen, waypoints, cache, optimise = street_route_request("square", cameras, root=tmp_path)

    assert chosen == [0, 2]
    assert optimise is False
    assert cache == tmp_path / "data" / "street_routes" / f"square_{route_key(waypoints, False)}.json"
    assert not cache.exists()


def test_toulouse_isolated_cohort_relocates_and_keeps_capture_identity_gates(tmp_path):
    capture_id = "4CxfyuveHLZwX5MG_full_capture"
    station = f"pano_00_{capture_id[:16]}"
    cohort = tmp_path / "data" / "panorama_cohorts" / "toulouse_capitole_2018-05" / station
    cohort.mkdir(parents=True)
    metadata = json.dumps({"panoId": capture_id, "date": "2018-05"}, separators=(",", ":")).encode()
    (cohort / "metadata.json").write_bytes(metadata)
    report = tmp_path / "outputs" / "site_semantics" / "toulouse_capitole" / "walk_semantic_250m.json"
    report.parent.mkdir(parents=True)
    report.write_text(
        json.dumps(
            {
                "stations_admitted": [
                    {
                        "station": station,
                        "folder": f"/remote/gpu/checkout/data/panorama_cohorts/toulouse_capitole_2018-05/{station}",
                        "provider": "google_streetview",
                        "pano_id": capture_id,
                        "metadata_sha256": hashlib.sha256(metadata).hexdigest(),
                        "position_enu_m": [1.0, 2.0, 2.5],
                    }
                ]
            }
        )
    )

    stations = load_admitted_stations("toulouse_capitole", root=tmp_path)

    assert len(stations) == 1
    assert stations[0]["folder"] == str(cohort)
    assert stations[0]["node"] == capture_id
    assert stations[0]["provider"] == "google_streetview"
    assert stations[0]["folder_provenance"].startswith("/remote/gpu/checkout/")

    (cohort / "metadata.json").write_text(json.dumps({"panoId": "lookalike"}))
    with pytest.raises(ValueError, match="metadata SHA-256 mismatch"):
        load_admitted_stations("toulouse_capitole", root=tmp_path)


def test_exact_route_positions_apply_live_radius_and_fragment_gates(monkeypatch, tmp_path):
    records = [
        station("near_a", "a", (0.0, 0.0)),
        station("near_b", "b", (20.0, 0.0)),
        station("far", "far", (120.0, 0.0)),
        station("orphan", "orphan", (10.0, 5.0)),
    ]
    graph = LinkGraph(
        position={record["node"]: record["camera_enu_m"][:2] for record in records},
        neighbours={"a": ("b",), "b": ("a", "far"), "far": ("b",), "orphan": ()},
        provenance={},
    )
    monkeypatch.setattr("semantic_twin.walk.route.load_admitted_stations", lambda *_args, **_kwargs: records)
    monkeypatch.setattr("semantic_twin.walk.route.load_link_graph", lambda *_args, **_kwargs: graph)

    positions = admitted_route_positions("square", root=tmp_path, radius_m=90.0)

    assert positions == pytest.approx(np.array([[0.0, 0.0, 2.5], [20.0, 0.0, 2.5]]))


def test_the_order_does_not_cut_the_corner_the_road_goes_round():
    """Two stations near each other in space but far apart along the street.

    A route ordered on straight line distance would put the two ends of the L
    next to each other. Ordered on road distance it walks the corner.
    """
    position = {
        "a": np.array([0.0, 0.0]),
        "m1": np.array([40.0, 0.0]),
        "corner": np.array([80.0, 0.0]),
        "m2": np.array([80.0, 40.0]),
        "b": np.array([10.0, 78.0]),
    }
    order = ["a", "m1", "corner", "m2", "b"]
    neighbours = {
        name: tuple(n for n in (order[i - 1] if i else None, order[i + 1] if i + 1 < len(order) else None) if n)
        for i, name in enumerate(order)
    }
    graph = LinkGraph(position=position, neighbours=neighbours, provenance={})
    assert np.linalg.norm(position["b"] - position["a"]) < 80.0
    result = order_along_links(["b", "corner", "a", "m2", "m1"], graph)
    names = ["b", "corner", "a", "m2", "m1"]
    assert [names[i] for i in result["order"]] == ["a", "m1", "corner", "m2", "b"]
    assert result["roads"][0] == ["a", "m1"]


def test_the_exact_order_matches_brute_force_on_small_graphs():
    rng = np.random.default_rng(11)
    for _ in range(20):
        count = int(rng.integers(2, 7))
        points = rng.uniform(-50.0, 50.0, size=(count, 2))
        distance = np.linalg.norm(points[:, None, :] - points[None, :, :], axis=-1)
        order, total = _held_karp(distance)
        brute = min(
            (sum(distance[p[k], p[k + 1]] for k in range(count - 1)), p) for p in itertools.permutations(range(count))
        )
        assert total == pytest.approx(brute[0])
        assert sorted(order) == list(range(count))


def test_the_search_never_beats_the_proof():
    """Two-opt is a search and sometimes loses, which is why the proof is the default.

    Over ten seven point cases it ties eight times and comes out 0.2 and 0.6
    percent long on the other two. That is small, and it is exactly why the
    exact route is what ships for every site in this study.
    """
    rng = np.random.default_rng(5)
    for _ in range(10):
        points = rng.uniform(-40.0, 40.0, size=(7, 2))
        distance = np.linalg.norm(points[:, None, :] - points[None, :, :], axis=-1)
        searched, proved = _nearest_neighbour_two_opt(distance), _held_karp(distance)
        assert searched[1] >= proved[1] - 1.0e-9
        assert sorted(searched[0]) == sorted(proved[0]) == list(range(7))


def test_the_exact_limit_is_above_every_site_in_this_study():
    """Twelve is the largest admitted station count on disk. The proof must cover it."""
    assert EXACT_ORDER_LIMIT >= 12


def test_ordering_refuses_a_set_that_does_not_reach_itself():
    graph = LinkGraph(
        position={"a": np.zeros(2), "b": np.array([1.0, 0.0])},
        neighbours={"a": (), "b": ()},
        provenance={},
    )
    with pytest.raises(ValueError, match="do not all reach each other"):
        order_along_links(["a", "b"], graph)


def test_bridging_joins_two_drives_that_pass_close():
    """Two sequences that share a street but not a link, which is the Korenmarkt case."""
    records = [
        {"image_id": "a0", "sequence_id": "a", "easting_m": 0.0, "northing_m": 0.0, "captured_at": 1},
        {"image_id": "a1", "sequence_id": "a", "easting_m": 10.0, "northing_m": 0.0, "captured_at": 2},
        {"image_id": "b0", "sequence_id": "b", "easting_m": 13.0, "northing_m": 0.0, "captured_at": 9},
        {"image_id": "b1", "sequence_id": "b", "easting_m": 23.0, "northing_m": 0.0, "captured_at": 10},
    ]
    plain = link_graph_from_sequences(records)
    assert len(fragments(["a0", "b1"], plain)) == 2

    joined = bridge_components(plain, 5.0)
    assert len(fragments(["a0", "b1"], joined)) == 1
    assert joined.distances_from("a0")["b1"] == pytest.approx(23.0)
    assert joined.provenance["bridges_added"] == 1
    assert joined.provenance["bridged_within_m"] == 5.0


def test_bridging_never_adds_a_chord_inside_one_drive():
    """A proximity join would cut corners off a dense drive. This one cannot.

    Every link it adds joins two parts that did not reach each other, so the
    number of links it can add is one less than the number of parts, and the
    road along an existing chain is left exactly as the provider recorded it.
    """
    records = [
        {"image_id": f"f{i}", "sequence_id": "s", "easting_m": 0.0, "northing_m": float(i), "captured_at": i}
        for i in range(6)
    ]
    graph = link_graph_from_sequences(records)
    joined = bridge_components(graph, 5.0)
    assert joined.provenance["bridges_added"] == 0
    assert joined.neighbours == graph.neighbours
    assert joined.distances_from("f0")["f5"] == pytest.approx(5.0)


def test_bridging_is_off_at_zero_and_leaves_the_graph_alone():
    graph = straight_graph(3)
    assert bridge_components(graph, 0.0) is graph


def test_bridging_joins_at_every_close_pair_and_not_at_one_of_them():
    """Two drives down the same street have to share the street, not one node.

    Joining them at their closest pair alone leaves the road from one to the
    other running out to that pair and back. At Korenmarkt that rule turned a
    5.5 m step into 88 m of road.
    """
    left = [
        {"image_id": f"l{i}", "sequence_id": "l", "easting_m": float(i) * 10.0, "northing_m": 0.0, "captured_at": i}
        for i in range(4)
    ]
    right = [
        {"image_id": f"r{i}", "sequence_id": "r", "easting_m": float(i) * 10.0, "northing_m": 2.0, "captured_at": i}
        for i in range(4)
    ]
    graph = link_graph_from_sequences([*left, *right])
    joined = bridge_components(graph, 3.0)

    assert joined.provenance["bridges_added"] == 4
    assert joined.provenance["parts_before_bridging"] == 2
    assert joined.distances_from("l3")["r3"] == pytest.approx(2.0)
    assert joined.distances_from("l0")["r0"] == pytest.approx(2.0)


def test_fragments_come_back_largest_first():
    position = {n: np.array([float(i), 0.0]) for i, n in enumerate("abcd")}
    graph = LinkGraph(
        position=position,
        neighbours={"a": ("b",), "b": ("a", "c"), "c": ("b",), "d": ()},
        provenance={},
    )
    groups = fragments(list("dabc"), graph)
    assert [len(g) for g in groups] == [3, 1]
    assert set(groups[0]) == {"a", "b", "c"}


# --- the ground under a camera ----------------------------------------------


def test_the_sky_probe_puts_a_head_on_the_arcade_and_the_camera_probe_does_not():
    """The repair that six of the 52 admitted stations in this study need.

    A photogrammetric mesh bridges an arcade over as solid roof. A downward ray
    from above the scene stops on that roof, so the walk's own ground rule would
    place a pedestrian eight metres in the air. Starting the probe under the
    camera, which is known to be outdoors because it passed the sky conflict
    gate, reports the pavement instead.
    """
    arcade = ((-4.0, -4.0, 8.0), (4.0, 4.0, 9.0))
    geometry = Boxes(ground_z=0.0, boxes=(arcade,))
    xy = np.array([[0.0, 0.0]])
    camera_z = np.array([2.5])

    from_sky, _ = ground_height(geometry, xy)
    from_camera, up = ground_under_camera(geometry, xy, camera_z)

    assert from_sky[0] == pytest.approx(9.0)
    assert from_camera[0] == pytest.approx(0.0)
    assert up[0] == pytest.approx(1.0)


def test_the_two_probes_agree_where_nothing_is_overhead():
    geometry = Boxes(ground_z=12.0)
    xy = np.array([[3.0, -7.0], [0.0, 0.0]])
    from_sky, _ = ground_height(geometry, xy)
    from_camera, _ = ground_under_camera(geometry, xy, np.array([14.5, 14.5]))
    assert from_camera == pytest.approx(from_sky)


# --- the route ---------------------------------------------------------------


def test_registered_road_leg_matches_both_cameras_and_keeps_the_provider_bend():
    raw = np.array([[0.0, 0.0], [3.0, 0.0], [3.0, 4.0]])
    corrected = register_road_leg(raw, np.array([10.0, 2.0]), np.array([17.0, 9.0]))

    assert corrected[0] == pytest.approx([10.0, 2.0])
    assert corrected[-1] == pytest.approx([17.0, 9.0])
    assert corrected[1] == pytest.approx([3.0 + 10.0 + 12.0 / 7.0, 2.0 + 9.0 / 7.0])


def test_route_road_uses_registered_endpoints_instead_of_raw_graph_endpoints():
    graph = LinkGraph(
        position={"a": np.array([0.0, 0.0]), "bend": np.array([5.0, 2.0]), "b": np.array([10.0, 0.0])},
        neighbours={"a": ("bend",), "bend": ("a", "b"), "b": ("bend",)},
        provenance={},
    )
    cameras = [station("a", "a", (100.0, 50.0)), station("b", "b", (110.0, 50.0))]
    route = build_panorama_route(Boxes(), cameras, graph, clearance_samples=16)

    assert route.road_polyline[0][0] == pytest.approx(cameras[0]["camera_enu_m"][:2])
    assert route.road_polyline[0][-1] == pytest.approx(cameras[1]["camera_enu_m"][:2])
    assert route.road_polyline[0][1] == pytest.approx([105.0, 52.0])
    assert route.provenance["raw_link_graph_length_m"] == pytest.approx(2.0 * np.hypot(5.0, 2.0))
    assert route.provenance["point_kind"] == ["camera_registered", "camera_registered"]


def test_two_registered_cameras_on_one_provider_node_keep_their_own_leg():
    graph = LinkGraph(
        position={"a": np.array([0.0, 0.0]), "b": np.array([10.0, 0.0])},
        neighbours={"a": ("b",), "b": ("a",)},
        provenance={},
    )
    cameras = [
        station("a1", "a", (100.0, 0.0)),
        station("a2", "a", (101.0, 0.0)),
        station("b", "b", (110.0, 0.0)),
    ]
    route = build_panorama_route(Boxes(), cameras, graph, clearance_samples=16)

    assert len(route.road_polyline) == 2
    assert route.road_m == pytest.approx([0.0, 1.0, 9.0])
    for leg, line in enumerate(route.road_polyline):
        assert line[0] == pytest.approx(route.walk.points[leg, :2])
        assert line[-1] == pytest.approx(route.walk.points[leg + 1, :2])


def open_street_case():
    """Five cameras down one street, with facades either side."""
    walls = (
        ((-10.0, 6.0, 0.0), (50.0, 8.0, 18.0)),
        ((-10.0, -8.0, 0.0), (50.0, -6.0, 18.0)),
    )
    geometry = Boxes(ground_z=0.0, boxes=walls)
    graph = straight_graph(5, step=10.0)
    stations = [station(f"pano_{i}", f"n{i}", (float(i) * 10.0, 0.0)) for i in range(5)]
    return geometry, graph, stations


def test_every_standpoint_stands_where_a_camera_stood():
    """The property the whole module exists for."""
    geometry, graph, stations = open_street_case()
    route = build_panorama_route(geometry, stations, graph, clearance_samples=32)
    assert len(route) == len(stations)
    camera_xy = {(round(float(s["camera_enu_m"][0]), 6), round(float(s["camera_enu_m"][1]), 6)) for s in stations}
    for point in route.walk.points:
        assert (round(float(point[0]), 6), round(float(point[1]), 6)) in camera_xy


def test_the_head_sits_at_pedestrian_height_and_not_at_the_camera():
    geometry, graph, stations = open_street_case()
    route = build_panorama_route(geometry, stations, graph, clearance_samples=32)
    assert route.walk.points[:, 2] == pytest.approx(HEAD_HEIGHT_M)
    assert route.walk.ground_z_m == pytest.approx(0.0)
    for entry in route.stations:
        assert entry.detail["camera_above_measured_ground_m"] == pytest.approx(2.5)


def test_the_route_runs_from_one_end_of_the_street_to_the_other():
    geometry, graph, stations = open_street_case()
    scrambled = [stations[i] for i in (3, 0, 4, 1, 2)]
    route = build_panorama_route(geometry, scrambled, graph, clearance_samples=32)
    assert [s.name for s in route.stations] == ["pano_0", "pano_1", "pano_2", "pano_3", "pano_4"]
    assert route.road_length_m == pytest.approx(40.0)
    assert route.end_to_end_m == pytest.approx(40.0)
    assert route.detour_ratio == pytest.approx(1.0)
    assert route.walk.step_m == pytest.approx([0.0, 10.0, 10.0, 10.0, 10.0])


def test_a_route_round_a_corner_is_longer_than_the_hops_between_its_stations():
    position = {
        "a": np.array([0.0, 0.0]),
        "corner": np.array([30.0, 0.0]),
        "b": np.array([30.0, 30.0]),
    }
    graph = LinkGraph(
        position=position,
        neighbours={"a": ("corner",), "corner": ("a", "b"), "b": ("corner",)},
        provenance={},
    )
    geometry = Boxes(ground_z=0.0)
    stations = [station("a", "a", (0.0, 0.0)), station("b", "b", (30.0, 30.0))]
    route = build_panorama_route(geometry, stations, graph, clearance_samples=16)
    assert route.road_length_m == pytest.approx(60.0)
    assert route.straight_length_m == pytest.approx(np.hypot(30.0, 30.0))
    assert route.detour_ratio > 1.4
    assert len(route.road_polyline) == 1
    assert route.road_polyline[0].shape == (3, 2)


def test_a_station_on_another_fragment_is_dropped_and_says_why():
    geometry, graph, stations = open_street_case()
    orphan = station("pano_orphan", "island", (200.0, 0.0))
    graph = LinkGraph(
        position={**graph.position, "island": np.array([200.0, 0.0])},
        neighbours={**graph.neighbours, "island": ()},
        provenance=graph.provenance,
    )
    route = build_panorama_route(geometry, [*stations, orphan], graph, clearance_samples=16)
    assert [s.name for s in route.stations] == ["pano_0", "pano_1", "pano_2", "pano_3", "pano_4"]
    assert len(route.dropped) == 1
    assert route.dropped[0]["station"] == "pano_orphan"
    assert "fragment" in route.dropped[0]["because"]
    assert route.provenance["fragment_sizes"] == [5, 1]


def test_the_second_fragment_can_be_walked_on_purpose():
    geometry, graph, stations = open_street_case()
    graph = LinkGraph(
        position={**graph.position, "i0": np.array([200.0, 0.0]), "i1": np.array([210.0, 0.0])},
        neighbours={**graph.neighbours, "i0": ("i1",), "i1": ("i0",)},
        provenance=graph.provenance,
    )
    extra = [station("far_0", "i0", (200.0, 0.0)), station("far_1", "i1", (210.0, 0.0))]
    route = build_panorama_route(geometry, [*stations, *extra], graph, fragment=1, clearance_samples=16)
    assert [s.name for s in route.stations] == ["far_0", "far_1"]
    with pytest.raises(IndexError, match="fragments"):
        build_panorama_route(geometry, [*stations, *extra], graph, fragment=2, clearance_samples=16)


def test_a_camera_off_the_link_graph_is_dropped_and_says_why():
    geometry, graph, stations = open_street_case()
    route = build_panorama_route(
        geometry, [*stations, station("nameless", "not_a_node", (5.0, 0.0))], graph, clearance_samples=16
    )
    assert len(route) == 5
    assert route.dropped[0]["because"] == "the camera is not in the link graph"


def test_a_station_whose_metadata_never_landed_is_dropped_separately():
    """A station directory with no metadata.json has no provider identifier.

    That is a different failure from a camera the link graph does not hold, and
    saying so is the difference between a missing download and a torn graph.
    """
    geometry, graph, stations = open_street_case()
    nameless = {"name": "no_metadata", "node": None, "camera_enu_m": np.array([5.0, 0.0, 2.5])}
    route = build_panorama_route(geometry, [*stations, nameless], graph, clearance_samples=16)
    assert len(route) == 5
    assert route.dropped[0]["because"] == "this station carries no provider identifier"


def test_a_camera_beyond_the_crop_is_dropped():
    geometry, graph, stations = open_street_case()
    route = build_panorama_route(geometry, stations, graph, radius_m=25.0, clearance_samples=16)
    assert [s.name for s in route.stations] == ["pano_0", "pano_1", "pano_2"]
    assert {d["station"] for d in route.dropped} == {"pano_3", "pano_4"}


def test_a_tight_standpoint_survives_by_default_and_is_measured_anyway():
    """A station is a place a camera stood, so the route does not second guess it.

    ``build_walk`` refuses a grid point with less than 2 m of clearance, which is
    right for a point that has nothing behind it. Refusing a station here would
    break the one property this route holds, so both numbers are reported and
    neither is a gate until the caller asks for one.
    """
    alley = (
        ((-10.0, 0.7, 0.0), (50.0, 4.0, 18.0)),
        ((-10.0, -4.0, 0.0), (50.0, -0.7, 18.0)),
    )
    geometry = Boxes(ground_z=0.0, boxes=alley)
    graph = straight_graph(3, step=10.0)
    stations = [station(f"pano_{i}", f"n{i}", (float(i) * 10.0, 0.0)) for i in range(3)]

    kept = build_panorama_route(geometry, stations, graph, clearance_samples=256)
    assert len(kept) == 3
    assert max(s.clearance_m for s in kept.stations) < 2.0

    with pytest.raises(RuntimeError, match="failed the clearance or sky gate"):
        build_panorama_route(geometry, stations, graph, clearance_samples=256, min_clearance_m=2.0)


def test_a_standpoint_far_from_the_datum_is_counted_rather_than_moved():
    geometry, graph, stations = open_street_case()
    route = build_panorama_route(geometry, stations, graph, ground_datum_m=40.0, clearance_samples=16)
    assert route.provenance["standpoints_off_the_ground_datum"] == [s["name"] for s in stations]
    assert route.walk.ground_z_m == pytest.approx(0.0)


def test_the_provenance_records_the_route_it_actually_walked():
    geometry, graph, stations = open_street_case()
    route = build_panorama_route(geometry, stations, graph, clearance_samples=16)
    record = route.provenance
    assert record["stations"] == [s.name for s in route.stations]
    assert record["road_step_m"] == pytest.approx([0.0, 10.0, 10.0, 10.0, 10.0])
    assert record["probe_from"] == "camera"
    assert "Held-Karp" in record["ordering"]
    assert record["link_graph"]["source"] == "test"
    assert record["head_height_m"] == HEAD_HEIGHT_M


def test_it_refuses_a_site_with_nothing_to_walk():
    geometry, graph, _ = open_street_case()
    with pytest.raises(RuntimeError, match="cannot supply a panorama route"):
        build_panorama_route(geometry, [station("lonely", "elsewhere", (0.0, 0.0))], graph)


def test_one_station_is_a_route_of_one():
    geometry, graph, stations = open_street_case()
    route = build_panorama_route(geometry, stations[:1], graph, clearance_samples=16)
    assert len(route) == 1
    assert route.road_length_m == 0.0
    assert route.detour_ratio == 1.0
    assert route.end_to_end_m == 0.0
    assert route.provenance["ordering"] == "single station"


# --- next to the walk it does not replace ------------------------------------


def test_panorama_walk_returns_the_same_type_build_walk_does():
    geometry, graph, stations = open_street_case()
    walk = panorama_walk(geometry, stations, graph, clearance_samples=16)
    assert isinstance(walk, Walk)
    assert walk.points.shape == (5, 3)
    assert walk.ground_z_m.shape == (5,)
    assert walk.step_m.shape == (5,)
    assert len(walk) == 5


def test_the_route_is_not_a_grid_and_the_grid_is_not_a_route():
    """The two builders disagree about what a standpoint is, which is the point.

    ``build_walk`` fills the disc: on this street it returns dozens of points
    almost none of which coincide with a camera. The route returns five, all of
    them cameras. Both still run, because every published number rests on the
    first one.
    """
    geometry, graph, stations = open_street_case()
    grid = build_walk(geometry, ground_datum_m=0.0, radius_m=40.0, spacing_m=3.0, clearance_samples=16)
    route = build_panorama_route(geometry, stations, graph, clearance_samples=16)

    assert len(grid) > 4 * len(route)
    camera_xy = {(round(float(s["camera_enu_m"][0]), 3), round(float(s["camera_enu_m"][1]), 3)) for s in stations}
    on_a_camera = sum(1 for p in grid.points if (round(float(p[0]), 3), round(float(p[1]), 3)) in camera_xy)
    assert on_a_camera < len(route)
    assert all((round(float(p[0]), 3), round(float(p[1]), 3)) in camera_xy for p in route.walk.points)


def test_build_walk_is_untouched_by_the_route_module():
    """A regression guard, because reproducing published numbers depends on it."""
    geometry = Boxes(ground_z=0.0, boxes=(((-10.0, 6.0, 0.0), (50.0, 8.0, 18.0)),))
    first = build_walk(geometry, ground_datum_m=0.0, radius_m=20.0, spacing_m=4.0, clearance_samples=16, seed=3)
    second = build_walk(geometry, ground_datum_m=0.0, radius_m=20.0, spacing_m=4.0, clearance_samples=16, seed=3)
    assert first.points == pytest.approx(second.points)
    assert first.provenance["head_height_m"] == 1.5
    assert "stations" not in first.provenance


def test_the_route_is_reproducible():
    geometry, graph, stations = open_street_case()
    first = build_panorama_route(geometry, stations, graph, clearance_samples=32, seed=7)
    second = build_panorama_route(geometry, list(reversed(stations)), graph, clearance_samples=32, seed=7)
    assert [s.name for s in first.stations] == [s.name for s in second.stations]
    assert first.walk.points == pytest.approx(second.walk.points)
    assert isinstance(first, PanoramaRoute)


# --- the stride along the road -----------------------------------------------


def test_the_stride_puts_points_along_the_road_and_keeps_both_ends():
    leg = np.array([[0.0, 0.0], [10.0, 0.0]])
    dense = densify([leg], stride_m=2.5)
    assert dense == pytest.approx(np.array([[0.0, 0.0], [2.5, 0.0], [5.0, 0.0], [7.5, 0.0], [10.0, 0.0]]))


def test_the_stride_follows_a_corner_rather_than_cutting_it():
    corner = np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 10.0]])
    dense = densify([corner], stride_m=5.0)
    assert len(dense) == 5
    assert dense[3] == pytest.approx([10.0, 5.0])


def test_the_stride_gives_nothing_back_when_there_is_no_road():
    assert densify([], stride_m=3.0).shape == (0, 2)
    assert densify([np.array([[1.0, 2.0]])], stride_m=3.0).shape == (0, 2)


def test_a_stride_joins_legs_end_to_end():
    legs = [np.array([[0.0, 0.0], [6.0, 0.0]]), np.array([[6.0, 0.0], [6.0, 6.0]])]
    dense = densify(legs, stride_m=3.0)
    assert len(dense) == 5
    assert dense[-1] == pytest.approx([6.0, 6.0])
