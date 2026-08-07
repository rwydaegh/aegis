"""Three rules for where a pedestrian stands, held to one interface.

``tests/test_route.py`` pins what the capture route does and ``tests/test_ground_datum.py``
pins the datum under it. This module's subject is the thing neither of them can
see: that the study has three answers to one question, that they are genuinely
different answers, and that a walk now says which of them produced it.

No mesh, no phantom, no network. The geometry is the analytic box caster from
``tests/test_route.py``, so every case here runs in CI.
"""

from __future__ import annotations

import numpy as np
import pytest

from semantic_twin.walk import (
    GRID,
    NEAREST_OF,
    PANORAMA_LINKS,
    STREET_ROUTE,
    UNRECORDED,
    GridWalk,
    NearestCameraWalk,
    PanoramaLinkWalk,
    StreetRouteWalk,
    Walk,
    WalkBuilder,
    body_yaw_array_hash,
    body_yaw_hash,
    route_order_hash,
)
from semantic_twin.walk import site as site_module
from semantic_twin.walk.model import KIND_RULE

from test_route import Boxes, station, straight_graph

BUILDERS = (GridWalk, PanoramaLinkWalk, StreetRouteWalk, NearestCameraWalk)


def open_square() -> Boxes:
    """Flat ground with facades north and south, wide enough for a 40 m disc."""
    return Boxes(
        ground_z=0.0,
        boxes=(
            ((-60.0, 8.0, 0.0), (60.0, 12.0, 18.0)),
            ((-60.0, -12.0, 0.0), (60.0, -8.0, 18.0)),
        ),
    )


def five_cameras() -> list[dict]:
    return [station(f"pano_{i}", f"n{i}", (float(i) * 10.0 - 20.0, 0.0)) for i in range(5)]


# --- the protocol -------------------------------------------------------------


@pytest.mark.parametrize("builder", BUILDERS, ids=lambda b: b.__name__)
def test_every_builder_satisfies_the_protocol(builder: type) -> None:
    """A new rule inherits this file rather than needing its own."""
    made = builder() if builder is GridWalk else builder("somewhere")
    assert isinstance(made, WalkBuilder)
    assert made.kind in KIND_RULE
    assert callable(made.build)


def test_the_kind_vocabulary_has_no_unnamed_members() -> None:
    """A label with no sentence beside it is a label a report cannot print."""
    assert set(KIND_RULE) == {GRID, PANORAMA_LINKS, STREET_ROUTE, NEAREST_OF, UNRECORDED}
    assert all(rule and rule[0].islower() for rule in KIND_RULE.values())


def test_a_contest_is_a_builder_kind_and_never_a_walk_kind() -> None:
    """``nearest_of`` describes how a walk was picked, not how its points were chosen.

    A number produced by the contest came from one of the other two rules, so
    stamping the result ``nearest_of`` would hide exactly the thing the stamp is
    for.
    """
    assert NearestCameraWalk("somewhere").kind == NEAREST_OF
    assert NEAREST_OF not in {GRID, PANORAMA_LINKS, STREET_ROUTE}


# --- identity -----------------------------------------------------------------


def test_a_grid_walk_says_it_is_a_grid_and_says_where() -> None:
    walk = GridWalk(site="korenmarkt", ground_datum_m=0.0, radius_m=20.0, spacing_m=5.0).build(open_square())
    assert walk.kind == GRID
    assert walk.site == "korenmarkt"
    assert walk.identity() == {
        "walk_kind": GRID,
        "walk_site": "korenmarkt",
        "walk_rule": KIND_RULE[GRID],
        "standpoints": len(walk),
    }
    assert "korenmarkt" in walk.describe()


def test_a_walk_nobody_stamped_says_so_rather_than_claiming_a_rule() -> None:
    """An unstamped walk is the state every published manifest is in today.

    Reporting it as unrecorded is the point. A default of ``grid`` would be a
    guess that happens to be right for the published runs and wrong for anything
    built after them.
    """
    bare = Walk(points=np.zeros((2, 3)), ground_z_m=np.zeros(2), step_m=np.zeros(2), provenance={})
    assert bare.kind == UNRECORDED
    assert bare.site is None
    assert bare.identity()["walk_rule"] == "unrecorded"


def test_the_function_stamps_the_walk_not_only_the_builder() -> None:
    """The two drivers still call the functions, so the identity cannot live in the class."""
    from semantic_twin.walk.grid import build_walk

    walk = build_walk(open_square(), ground_datum_m=0.0, radius_m=15.0, spacing_m=5.0, clearance_samples=16)
    assert walk.kind == GRID


# --- the three rules disagree, and they disagree in a specific direction -------


def test_the_grid_and_the_capture_route_are_not_the_same_sample() -> None:
    """Not "they differ" but by how much, in the quantity the method rests on.

    The whole argument for standing at the cameras is BOUNCE_BUDGET.md: the
    first interaction lands on photographed surface with probability 0.99 within
    ten metres of a panorama and about 0.1 past forty. So the number that
    separates these two walks is the distance from a standpoint to the nearest
    camera, and at Korenmarkt the real figures are 44.3 m for the grid and 2.8 m
    for the route. This layout reproduces the shape of that gap.
    """
    from semantic_twin.walk.route import build_panorama_route

    geometry, cameras = open_square(), five_cameras()
    grid = GridWalk(ground_datum_m=0.0, radius_m=40.0, spacing_m=3.0, options={"clearance_samples": 16}).build(geometry)
    route = build_panorama_route(geometry, cameras, straight_graph(5, step=10.0), clearance_samples=16)

    camera_xy = np.array([c["camera_enu_m"][:2] for c in cameras])

    def mean_gap(points: np.ndarray) -> float:
        return float(np.linalg.norm(points[:, None, :2] - camera_xy[None], axis=2).min(axis=1).mean())

    assert len(grid) > 10 * len(route)
    assert mean_gap(route.walk.points) == pytest.approx(0.0, abs=1e-9)
    assert mean_gap(grid.points) > 10.0


def test_two_walks_over_one_square_cover_different_surface() -> None:
    """Coverage is a property of the walk, which is why a coverage number needs its walk.

    Korenmarkt reads 0.032 of surface area by the fishnet route and 0.106 by the
    fused walk, and only the second circulates. The mechanism is here in
    miniature: two rules over one square reach different sets of standpoints, so
    any quantity accumulated over standpoints differs between them.
    """
    from semantic_twin.walk.route import build_panorama_route

    geometry = open_square()
    grid = GridWalk(ground_datum_m=0.0, radius_m=40.0, spacing_m=3.0, options={"clearance_samples": 16}).build(geometry)
    route = build_panorama_route(geometry, five_cameras(), straight_graph(5, step=10.0), clearance_samples=16)

    grid_cells = {(round(float(x) / 6.0), round(float(y) / 6.0)) for x, y, _ in grid.points}
    route_cells = {(round(float(x) / 6.0), round(float(y) / 6.0)) for x, y, _ in route.walk.points}
    assert route_cells - grid_cells or grid_cells - route_cells
    assert len(grid_cells) > 3 * len(route_cells)


def test_the_grid_wanders_off_the_street_and_the_route_cannot() -> None:
    """The route's one guarantee, stated as a bound the grid provably breaks.

    Every route standpoint is a camera position or a point on the road between
    two of them. The grid has no such constraint: on this layout it fills the
    whole 40 m disc including the ends of the square no camera ever reached.
    """
    from semantic_twin.walk.route import build_panorama_route

    geometry = open_square()
    grid = GridWalk(ground_datum_m=0.0, radius_m=40.0, spacing_m=3.0, options={"clearance_samples": 16}).build(geometry)
    route = build_panorama_route(geometry, five_cameras(), straight_graph(5, step=10.0), clearance_samples=16)

    span = (-20.0, 20.0)
    assert np.all(route.walk.points[:, 0] >= span[0] - 1e-9)
    assert np.all(route.walk.points[:, 0] <= span[1] + 1e-9)
    assert np.any(grid.points[:, 0] < span[0] - 5.0)
    assert np.any(grid.points[:, 0] > span[1] + 5.0)


# --- what each walk must never do --------------------------------------------


def test_the_grid_stays_on_walkable_ground() -> None:
    """Every standpoint is a head height above ground that passed the datum test.

    A grid square whose ground is a roof, a plinth or the top of a market stall
    is not somewhere a pedestrian is, and admitting one puts a head in the air
    with a completely different view of the sky.
    """
    plinth = ((-5.0, -5.0, 0.0), (5.0, 5.0, 4.0))
    geometry = Boxes(ground_z=0.0, boxes=(plinth,))
    walk = GridWalk(ground_datum_m=0.0, radius_m=25.0, spacing_m=2.5, options={"clearance_samples": 16}).build(geometry)

    assert len(walk) > 0
    assert walk.ground_z_m == pytest.approx(0.0)
    assert walk.points[:, 2] == pytest.approx(1.5)
    on_the_plinth = (np.abs(walk.points[:, 0]) < 5.0) & (np.abs(walk.points[:, 1]) < 5.0)
    assert not on_the_plinth.any()


def test_the_capture_route_stays_connected() -> None:
    """A route through a graph that does not join up is not a route.

    Two cameras on separate fragments cannot be walked between, so the builder
    keeps one fragment and says which. Silently ordering them anyway would put a
    step across a block into the walk and call it a stride.
    """
    from semantic_twin.walk.route import build_panorama_route

    geometry = open_square()
    graph = straight_graph(3, step=10.0)
    graph.position["island"] = np.array([500.0, 0.0])
    graph.neighbours["island"] = ()
    cameras = [station(f"pano_{i}", f"n{i}", (float(i) * 10.0, 0.0)) for i in range(3)]
    cameras.append(station("orphan", "island", (500.0, 0.0)))

    route = build_panorama_route(geometry, cameras, graph, clearance_samples=16)
    assert [s.name for s in route.stations] == ["pano_0", "pano_1", "pano_2"]
    assert route.provenance["fragment_sizes"] == [3, 1]
    steps = np.linalg.norm(np.diff(route.walk.points[:, :2], axis=0), axis=1)
    assert float(steps.max()) < 20.0


def test_densified_route_is_returned_in_path_order(monkeypatch: pytest.MonkeyPatch) -> None:
    """Camera points and stride points form one walk, not two concatenated lists."""
    graph = straight_graph(5, step=10.0)
    cameras = [station(f"pano_{i}", f"n{i}", (float(i) * 10.0, 0.0)) for i in range(5)]
    monkeypatch.setattr(site_module, "load_admitted_stations", lambda site, root=None: cameras)
    monkeypatch.setattr(site_module, "load_link_graph", lambda site, root=None, bridge_m=0.0: graph)

    walk, provenance = site_module.site_walk(
        open_square(),
        "nowhere",
        stride_m=6.0,
        path="links",
        clearance_samples=16,
    )

    assert walk.points[:, 0] == pytest.approx([0.0, 6.0, 10.0, 12.0, 18.0, 20.0, 24.0, 30.0, 36.0, 40.0])
    assert walk.points[:, 1] == pytest.approx(0.0)
    assert walk.step_m.max() == pytest.approx(6.0)
    assert provenance["standpoint_ordering"] == "increasing distance travelled along the selected path"
    assert walk.body_yaw_deg == pytest.approx(np.full(len(walk), 90.0))
    assert len(provenance["body_yaw_deg"]) == len(walk)


def test_densified_route_stays_in_the_registered_frame_and_labels_every_point(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    graph = straight_graph(3, step=10.0)
    cameras = [station(f"pano_{i}", f"n{i}", (100.0 + float(i) * 10.0, 0.0)) for i in range(3)]
    monkeypatch.setattr(site_module, "load_admitted_stations", lambda site, root=None: cameras)
    monkeypatch.setattr(site_module, "load_link_graph", lambda site, root=None, bridge_m=0.0: graph)

    walk, provenance = site_module.site_walk(
        open_square(),
        "nowhere",
        stride_m=6.0,
        path="links",
        clearance_samples=16,
    )

    assert walk.points[:, 0] == pytest.approx([100.0, 106.0, 110.0, 112.0, 118.0, 120.0])
    assert walk.step_m.max() <= 6.0 + 1.0e-12
    assert np.all(np.diff(walk.points[:, 0]) > 0.0)
    assert not np.isin(walk.points[:, 0], [0.0, 10.0, 20.0]).any()
    assert provenance["point_kind"] == [
        "camera_registered",
        "stride_interpolated",
        "camera_registered",
        "stride_interpolated",
        "stride_interpolated",
        "camera_registered",
    ]
    assert walk.provenance["point_kind"] == provenance["point_kind"]


def test_street_filter_reorients_the_kept_route_and_reseals_yaw(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Filtering an oriented route must not leave a stale yaw seal behind."""
    graph = straight_graph(3, step=10.0)
    cameras = [station(f"pano_{i}", f"n{i}", (float(i) * 10.0, 0.0)) for i in range(3)]
    line = np.array([[0.0, 0.0], [10.0, 0.0]])
    monkeypatch.setattr(site_module, "load_admitted_stations", lambda site, root=None: cameras)
    monkeypatch.setattr(site_module, "load_link_graph", lambda site, root=None, bridge_m=0.0: graph)
    monkeypatch.setattr(
        site_module,
        "street_path",
        lambda site, route, **kwargs: ((line,), {"polyline_enu": line.tolist()}),
    )

    walk, provenance = site_module.site_walk(
        open_square(),
        "nowhere",
        stride_m=0.0,
        path="street",
        clearance_samples=16,
    )

    assert walk.points[:, 0] == pytest.approx([0.0, 10.0])
    assert walk.body_yaw_deg == pytest.approx([90.0, 90.0])
    assert provenance["body_yaw_deg"] == pytest.approx([90.0, 90.0])
    assert provenance["body_yaw_route_order_hash"] == route_order_hash(walk.points)
    assert provenance["body_yaw_hash"] == body_yaw_hash(walk.points, walk.body_yaw_deg)
    assert provenance["body_yaw_array_hash"] == body_yaw_array_hash(walk.body_yaw_deg)


def test_the_grid_ordering_is_fixed_by_the_geometry_and_not_by_the_seed() -> None:
    """Standpoint selection order is what the golden lock is most sensitive to.

    Reordering the candidates changes which of them a stratified pilot traces,
    so a walk that came back in a different order under a different seed would
    move every published number without touching any physics. The seed drives
    the clearance and sky rays only.
    """
    geometry = open_square()
    kwargs = {"ground_datum_m": 0.0, "radius_m": 20.0, "spacing_m": 4.0, "options": {"clearance_samples": 64}}
    first = GridWalk(seed=3, **kwargs).build(geometry)
    again = GridWalk(seed=3, **kwargs).build(geometry)
    other = GridWalk(seed=11, **kwargs).build(geometry)

    assert first.points == pytest.approx(again.points)
    assert first.points == pytest.approx(other.points)
    assert first.step_m == pytest.approx(again.step_m)


def test_the_route_ordering_does_not_depend_on_the_order_the_stations_arrive() -> None:
    from semantic_twin.walk.route import build_panorama_route

    geometry, cameras = open_square(), five_cameras()
    forward = build_panorama_route(geometry, cameras, straight_graph(5, step=10.0), clearance_samples=32, seed=7)
    reverse = build_panorama_route(
        geometry, list(reversed(cameras)), straight_graph(5, step=10.0), clearance_samples=32, seed=7
    )
    assert [s.name for s in forward.stations] == [s.name for s in reverse.stations]
    assert forward.walk.points == pytest.approx(reverse.walk.points)


# --- the contest --------------------------------------------------------------


def test_the_contest_keeps_the_walk_that_stands_nearer_a_camera(monkeypatch: pytest.MonkeyPatch) -> None:
    """And the result carries the winner's kind, not the contest's.

    This is the case that makes the identity worth having. A manifest written by
    ``--walk-path closest`` at one square and by the same flag at another can
    hold walks built by two different rules, and only the stamp says so.
    """
    cameras = [{"camera_enu_m": np.array([0.0, 0.0, 2.5])}, {"camera_enu_m": np.array([40.0, 0.0, 2.5])}]
    built = {
        "links": Walk(
            points=np.array([[0.0, 9.0, 1.5], [40.0, 9.0, 1.5]]),
            ground_z_m=np.zeros(2),
            step_m=np.zeros(2),
            provenance={},
            kind=PANORAMA_LINKS,
            site="nowhere",
        ),
        "street": Walk(
            points=np.array([[0.0, 2.0, 1.5], [40.0, 2.0, 1.5]]),
            ground_z_m=np.zeros(2),
            step_m=np.zeros(2),
            provenance={},
            kind=STREET_ROUTE,
            site="nowhere",
        ),
    }
    real = site_module.site_walk

    def stub(geometry, site, *, path="links", **kwargs):
        if path == "closest":
            return real(geometry, site, path=path, **kwargs)
        return built[path], {"path": path}

    monkeypatch.setattr(site_module, "site_walk", stub)
    monkeypatch.setattr(site_module, "load_admitted_stations", lambda site, root=None: cameras)

    walk = NearestCameraWalk("nowhere").build(None)
    assert walk.kind == STREET_ROUTE
    assert walk.identity()["walk_rule"] == KIND_RULE[STREET_ROUTE]


def test_the_contest_records_the_walk_it_did_not_keep(monkeypatch: pytest.MonkeyPatch) -> None:
    """A run should say what it rejected, so the choice can be argued with."""
    cameras = [{"camera_enu_m": np.array([0.0, 0.0, 2.5])}]
    built = {
        "links": Walk(np.array([[0.0, 1.0, 1.5]]), np.zeros(1), np.zeros(1), {}, PANORAMA_LINKS, "nowhere"),
        "street": Walk(np.array([[0.0, 20.0, 1.5]]), np.zeros(1), np.zeros(1), {}, STREET_ROUTE, "nowhere"),
    }
    real = site_module.site_walk

    def stub(geometry, site, *, path="links", **kwargs):
        return real(geometry, site, path=path, **kwargs) if path == "closest" else (built[path], {"path": path})

    monkeypatch.setattr(site_module, "site_walk", stub)
    monkeypatch.setattr(site_module, "load_admitted_stations", lambda site, root=None: cameras)

    walk, record = real(None, "nowhere", path="closest")
    assert walk.kind == PANORAMA_LINKS
    assert record["path_candidates_m"] == {"links": 1.0, "street": 20.0}
    assert "nearest camera" in record["path_chosen_by"]


# --- the pilot subset ---------------------------------------------------------


def test_a_pilot_covers_the_whole_walk_rather_than_its_head() -> None:
    """Both drivers trace a subset, so how the subset is drawn is a method choice.

    Evenly spaced along the ordering, so a pilot at one tenth of the standpoints
    still reaches both ends of the square. Taking the first n would sample one
    corner of the grid and one end of the route.
    """
    from semantic_twin.walk.model import stratified_subset

    walk = GridWalk(ground_datum_m=0.0, radius_m=30.0, spacing_m=3.0, options={"clearance_samples": 16}).build(
        open_square()
    )
    picks = stratified_subset(walk, 8)
    assert picks[0] == 0
    assert picks[-1] == len(walk) - 1
    assert len(picks) <= 8
    assert stratified_subset(walk, 0).tolist() == list(range(len(walk)))
    assert stratified_subset(walk, len(walk) + 5).tolist() == list(range(len(walk)))


@pytest.mark.filterwarnings("error")
def test_a_walk_with_no_standpoints_cannot_win_the_contest(monkeypatch: pytest.MonkeyPatch) -> None:
    """An empty candidate should lose on the measurement, not slip past it.

    `_nearest_of` scores a candidate by the mean distance from a standpoint to
    the nearest camera. An empty candidate has no such measurement and receives
    an infinite score, so it cannot win or introduce a NaN into the manifest.

    Not hypothetical. At Mexico City's Zocalo no camera lies within 5 m of the
    routed walking path, so at a stride of zero the street candidate really is
    empty. See finding 11.
    """
    cameras = [{"camera_enu_m": np.array([0.0, 0.0, 2.5])}]
    empty = np.zeros((0, 3))
    built = {
        "links": Walk(np.array([[0.0, 40.0, 1.5]]), np.zeros(1), np.zeros(1), {}, PANORAMA_LINKS, "nowhere"),
        "street": Walk(empty, np.zeros(0), np.zeros(0), {}, STREET_ROUTE, "nowhere"),
    }
    real = site_module.site_walk

    def stub(geometry, site, *, path="links", **kwargs):
        return real(geometry, site, path=path, **kwargs) if path == "closest" else (built[path], {"path": path})

    monkeypatch.setattr(site_module, "site_walk", stub)
    monkeypatch.setattr(site_module, "load_admitted_stations", lambda site, root=None: cameras)

    walk, record = real(None, "nowhere", path="closest")
    assert len(walk) == 1
    assert record["path_candidates_m"] == {"links": 40.0, "street": float("inf")}


@pytest.mark.xfail(strict=True, reason="finding 11 in docs/BUGS.md, not fixed in the move")
def test_a_walk_trimmed_to_nothing_is_not_returned_as_a_walk(monkeypatch: pytest.MonkeyPatch) -> None:
    """`site_walk` says it raises rather than quietly falling back. Here it does neither.

    Every camera further from the routed path than the tolerance is dropped. When
    that leaves none, the caller gets a Walk holding zero standpoints and only a
    note in the provenance to say so. No caller reads the note. See finding 11.
    """
    graph = straight_graph(5, step=10.0)
    stations = [station(f"pano_{i}", f"n{i}", (float(i) * 10.0 - 20.0, 0.0)) for i in range(5)]
    line = np.array([[-20.0, 60.0], [20.0, 60.0]])
    monkeypatch.setattr(site_module, "load_admitted_stations", lambda site, root=None: [dict(s) for s in stations])
    monkeypatch.setattr(site_module, "load_link_graph", lambda site, root=None, bridge_m=0.0: graph)
    monkeypatch.setattr(
        site_module,
        "street_path",
        lambda site, route, **kwargs: ((line,), {"polyline_enu": [[float(x), float(y)] for x, y in line]}),
    )

    walk, _ = site_module.site_walk(open_square(), "nowhere", stride_m=0.0, path="street", clearance_samples=32)
    assert len(walk) > 0, "a walk with no standpoints reached the caller without raising"
