"""Contract tests for the opt-in evidence-supported provider corridor."""

from __future__ import annotations

import json

import numpy as np
import pytest

from semantic_twin.walk import PROVIDER_CORRIDOR
from semantic_twin.walk import site as site_module
from semantic_twin.walk.links import LinkGraph
from semantic_twin.walk.orientation import body_yaw_hash, route_order_hash
from semantic_twin.walk.provider_corridor import (
    PROVIDER_CORRIDOR_V1,
    continuous_nearest_camera_gap_m,
    select_provider_corridor,
)

from test_route import Boxes


def _station(name: str, node: str, xy: tuple[float, float]) -> dict:
    return {"name": name, "node": node, "camera_enu_m": np.array([*xy, 2.5], dtype=np.float64)}


def _graph(positions: dict[str, tuple[float, float]], edges: tuple[tuple[str, str], ...]) -> LinkGraph:
    neighbours = {node: set() for node in positions}
    for left, right in edges:
        neighbours[left].add(right)
        neighbours[right].add(left)
    return LinkGraph(
        position={node: np.asarray(xy, dtype=np.float64) for node, xy in positions.items()},
        neighbours={node: tuple(sorted(ends)) for node, ends in neighbours.items()},
        provenance={"source": "test"},
    )


def test_continuous_gap_uses_voronoi_breakpoints_not_vertices_or_samples() -> None:
    line = np.array([[0.0, 0.0], [10.0, 0.0]])
    cameras = np.array([[0.0, 0.0], [3.0, 0.0], [10.0, 0.0]])

    # The controlling interior breakpoint is x=6.5. Neither line vertex sees it.
    assert continuous_nearest_camera_gap_m(line, cameras) == pytest.approx(3.5)


def test_selection_is_input_order_invariant_and_maximises_endpoint_span() -> None:
    graph = _graph(
        {"n0": (0.0, 0.0), "n1": (10.0, 0.0), "n2": (20.0, 0.0)},
        (("n0", "n1"), ("n1", "n2")),
    )
    stations = [_station("c", "n2", (20.0, 0.0)), _station("a", "n0", (0.0, 0.0)), _station("b", "n1", (10.0, 0.0))]

    first = select_provider_corridor(stations, graph)
    reversed_input = select_provider_corridor(list(reversed(stations)), graph)

    assert first.station_ids == ("a", "c")
    assert first.station_ids == reversed_input.station_ids
    assert first.node_path == reversed_input.node_path == ("n0", "n1", "n2")
    assert first.audit == reversed_input.audit


def test_equal_span_prefers_shorter_registered_path_then_station_ids() -> None:
    graph = _graph(
        {
            "a": (-10.0, 0.0),
            "bend": (0.0, 20.0),
            "z": (10.0, 0.0),
            "b": (0.0, -10.0),
            "c": (0.0, 10.0),
            "d": (30.0, -5.0),
            "e": (30.0, 5.0),
        },
        (("a", "bend"), ("bend", "z"), ("b", "c"), ("d", "e")),
    )
    stations = [
        _station("a", "a", (-10.0, 0.0)),
        _station("z", "z", (10.0, 0.0)),
        _station("b", "b", (0.0, -10.0)),
        _station("c", "c", (0.0, 10.0)),
        _station("d", "d", (30.0, -5.0)),
        _station("e", "e", (30.0, 5.0)),
    ]

    selected = select_provider_corridor(stations, graph, max_gap_m=100.0)

    # a-z and b-c both span 20 m. The straight b-c provider path is shorter.
    assert selected.station_ids == ("b", "c")
    assert selected.path_length_m == pytest.approx(20.0)

    tied = _graph({"a": (0.0, 0.0), "z": (10.0, 0.0), "b": (20.0, 0.0), "c": (30.0, 0.0)}, (("a", "z"), ("b", "c")))
    tied_stations = [_station(name, name, tuple(tied.position[name])) for name in ("z", "c", "b", "a")]
    assert select_provider_corridor(tied_stations, tied).station_ids == ("a", "z")


def test_disconnected_camera_cannot_supply_evidence_to_another_component() -> None:
    graph = _graph({"a": (0.0, 0.0), "b": (50.0, 0.0), "island": (25.0, 0.0)}, (("a", "b"),))
    stations = [
        _station("a", "a", (0.0, 0.0)),
        _station("b", "b", (50.0, 0.0)),
        _station("island", "island", (25.0, 0.0)),
    ]

    with pytest.raises(RuntimeError, match="no provider corridor"):
        select_provider_corridor(stations, graph, max_gap_m=20.0)


def test_refuses_when_no_pair_is_connected() -> None:
    graph = _graph({"a": (0.0, 0.0), "b": (1.0, 0.0)}, ())
    with pytest.raises(RuntimeError, match="no provider corridor"):
        select_provider_corridor([_station("a", "a", (0.0, 0.0)), _station("b", "b", (1.0, 0.0))], graph)


def test_registered_polyline_endpoints_equal_registered_cameras_exactly() -> None:
    graph = _graph({"a": (0.0, 0.0), "m": (5.0, 5.0), "b": (10.0, 0.0)}, (("a", "m"), ("m", "b")))
    stations = [_station("left", "a", (100.0, 20.0)), _station("right", "b", (110.0, 20.0))]

    selected = select_provider_corridor(stations, graph, max_gap_m=20.0)

    assert np.array_equal(selected.registered_polyline[0], stations[0]["camera_enu_m"][:2])
    assert np.array_equal(selected.registered_polyline[-1], stations[1]["camera_enu_m"][:2])


def test_report_byte_change_invalidates_the_selection_seal(tmp_path) -> None:
    graph = _graph({"a": (0.0, 0.0), "b": (10.0, 0.0)}, (("a", "b"),))
    stations = [_station("a", "a", (0.0, 0.0)), _station("b", "b", (10.0, 0.0))]
    report = tmp_path / "report.json"
    report.write_text('{"stations_admitted":[]}', encoding="utf-8")
    first = select_provider_corridor(stations, graph, admitted_report=report, root=tmp_path)
    report.write_text('{"stations_admitted":[]}\n', encoding="utf-8")
    changed = select_provider_corridor(stations, graph, admitted_report=report, root=tmp_path)

    assert first.seal["admitted_station_report"]["sha256"] != changed.seal["admitted_station_report"]["sha256"]
    assert first.seal["selection_sha256"] != changed.seal["selection_sha256"]


def test_stride_follows_selected_corridor_and_yaw_is_resealed(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    graph = _graph({"a": (0.0, 0.0), "m": (10.0, 10.0), "b": (20.0, 10.0)}, (("a", "m"), ("m", "b")))
    stations = [_station("a", "a", (100.0, 0.0)), _station("b", "b", (120.0, 10.0))]
    monkeypatch.setattr(site_module, "load_admitted_stations", lambda site, root=None: stations)
    monkeypatch.setattr(site_module, "load_link_graph", lambda site, root=None, bridge_m=0.0: graph)

    walk, provenance = site_module.site_walk(
        Boxes(ground_z=0.0),
        "test_site",
        root=tmp_path,
        path="provider_corridor",
        stride_m=6.0,
        radius_m=200.0,
    )

    corridor = np.asarray(provenance["provider_corridor"]["registered_polyline_enu_m"])
    assert walk.kind == PROVIDER_CORRIDOR
    assert provenance["provider_corridor"]["contract"] == PROVIDER_CORRIDOR_V1
    assert np.max(site_module.gap_to_path(walk.points, corridor)) < 1.0e-10
    assert np.array_equal(walk.points[[0, -1], :2], np.array([[100.0, 0.0], [120.0, 10.0]]))
    assert provenance["body_yaw_route_order_hash"] == route_order_hash(walk.points)
    assert provenance["body_yaw_hash"] == body_yaw_hash(walk.points, walk.body_yaw_deg)


def test_legacy_readiness_bytes_do_not_gain_provider_fields() -> None:
    from semantic_twin.cohort import RouteReadiness

    status = RouteReadiness("city", "street_route", True, ("report.json", "route.json"), (), (), "route.json")
    encoded = json.dumps(status.as_dict(), sort_keys=True, separators=(",", ":"))
    assert encoded == (
        '{"evidence":["report.json","route.json"],"expected_cache":"route.json",'
        '"invalid":[],"kind":"street_route","missing":[],"ready":true,"site":"city"}'
    )
