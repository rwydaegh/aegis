"""The illumination protocol, and what every law that claims it has to do.

Five things get checked here and none of them restates the code.

**A law integrates to a value you can write down without it.** The band law's
normalisation is a quadrature in elevation, but the quantity it computes is the
volume of an annular shell, so ``pi (d_max^2 - d_min^2)(h_max - h_min)`` is the
answer and the quadrature has to land on it. The fixed height law has a closed
form too. That is a stronger statement than integrating the same law twice.

**A band accepts a direction just inside and refuses one just outside.** Both
sides of both edges, at 1e-9 degrees, because a support that leaks is a law that
credits rays from a place it says holds no sites.

**A model can name the law that made it.** That is the whole reason the protocol
exists: `LAW_CHANGE.md` is 270 lines of which-numbers-survive tables written by
hand because no result on disk said which law wrote it.

**A registered law is a class, and a class with no fixture here fails.** So a
declared law that nobody ever built cannot happen again.

**One class is a law.** :class:`GrazingCutoffLaw` is defined at the bottom of
this file, registered, and picked up by every contract test above without a line
being added to any of them.

Everything here is closed form or a stub geometry. No mesh, so the whole file
runs in CI.
"""

from __future__ import annotations

import math
from typing import Any, ClassVar

import numpy as np
import pytest
from scipy.integrate import quad, dblquad

from semantic_twin import illumination as ill
from semantic_twin.illumination import (
    LAW_REGISTRY,
    BandLaw,
    ElevationLaw,
    FixedHeightLaw,
    SourceSet,
    credited_by,
    register_law,
)
from semantic_twin.illumination.model import AngularIllumination, IlluminationModel, PlacedIllumination
from semantic_twin.illumination.sphere import _brute_nearest_cell, fibonacci_sphere, nearest_cell, sample_sphere
from semantic_twin.runconfig import ESTIMATORS, LAWS
from semantic_twin.transport.next_event import NextEventGather

# ---------------------------------------------------------------------------
# A third law, written here and nowhere else, to prove one class is enough
# ---------------------------------------------------------------------------


class GrazingCutoffLaw(ElevationLaw):
    """Sites spread uniformly over a spherical cap, cut off below the horizon.

    Not a law the study uses, and not registered at import either, because a test
    that leaves an entry in a global registry changes what every other test file
    sees. :func:`test_a_new_law_is_one_class_and_a_decorator` registers it and
    takes it back out again.

    It is here so the contract tests run against a law written after they were,
    and it is a cap because a constant density over one integrates to the cap's
    own solid angle, ``2 pi (1 - sin(el_min))``, which no code in the package
    computes.
    """

    law: ClassVar[str] = "test_grazing_cutoff"
    family: ClassVar[str] = ""

    def profile(self, elevation: np.ndarray) -> np.ndarray:
        return np.ones_like(elevation)


# ---------------------------------------------------------------------------
# One fixture per registered law. A law with none fails the suite.
# ---------------------------------------------------------------------------


def _fixture(cls: type) -> ElevationLaw:
    """A representative instance of one law class."""
    if issubclass(cls, BandLaw):
        return cls(name=f"fixture_{cls.law}", height_band_m=(9.0, 31.0), range_band_m=(15.0, 190.0))
    if issubclass(cls, FixedHeightLaw):
        return cls(name=f"fixture_{cls.law}", elevation_min_deg=4.0, elevation_max_deg=55.0)
    if issubclass(cls, GrazingCutoffLaw):
        return cls(name=f"fixture_{cls.law}", elevation_min_deg=12.0, elevation_max_deg=90.0)
    return cls(name=f"fixture_{cls.law}")


#: One per law the package registers. The guard below holds this equal to the
#: registry, so a law nobody instantiates cannot exist.
SHIPPED_FIXTURES: dict[str, ElevationLaw] = {law: _fixture(cls) for law, cls in LAW_REGISTRY.items()}

#: What the contract tests run over. The extra entry is the law defined in this
#: file, which is the point: it inherits every contract below without any of them
#: being edited.
FIXTURES: dict[str, ElevationLaw] = {**SHIPPED_FIXTURES, GrazingCutoffLaw.law: _fixture(GrazingCutoffLaw)}
LAW_TAGS = sorted(FIXTURES)
SHIPPED = sorted(ill.VARIANTS)


def test_every_registered_law_has_a_fixture_here() -> None:
    """The check that closes the hole ``uniform_sites_pathloss`` sat in.

    That tag was declared as a law for two days and no instance of it ever
    existed, so nothing integrated it and nothing could. A law is a class now, so
    the tag cannot exist without an implementation, and this makes sure the
    implementation cannot exist without something exercising it.
    """
    assert set(SHIPPED_FIXTURES) == set(LAW_REGISTRY)
    assert set(LAW_REGISTRY) == set(ill.LAWS)


def test_the_law_a_class_registers_under_is_the_one_it_reports() -> None:
    for law, cls in LAW_REGISTRY.items():
        assert cls.law == law
        assert _fixture(cls).law == law


def test_a_new_law_is_one_class_and_a_decorator() -> None:
    """Adding a law touches no other file, and the tag becomes reversible at once."""
    assert GrazingCutoffLaw.law not in LAW_REGISTRY
    try:
        assert register_law(GrazingCutoffLaw) is GrazingCutoffLaw
        assert LAW_REGISTRY[GrazingCutoffLaw.law] is GrazingCutoffLaw
        model = FIXTURES[GrazingCutoffLaw.law]
        assert LAW_REGISTRY[model.describe()["law"]] is GrazingCutoffLaw
        assert credited_by(model) == ("escape",)
    finally:
        LAW_REGISTRY.pop(GrazingCutoffLaw.law, None)


def test_a_second_class_cannot_claim_a_tag_that_is_taken() -> None:
    """Two classes on one tag makes an old manifest ambiguous about what ran."""

    class Impostor(ElevationLaw):
        law: ClassVar[str] = "uniform_sites_band"

    with pytest.raises(ValueError, match="already held"):
        register_law(Impostor)
    assert LAW_REGISTRY["uniform_sites_band"] is BandLaw


def test_a_law_with_no_tag_cannot_register() -> None:
    class Nameless(ElevationLaw):
        pass

    with pytest.raises(ValueError, match="no law tag"):
        register_law(Nameless)


# ---------------------------------------------------------------------------
# The contract: what every angular law has to satisfy
# ---------------------------------------------------------------------------


def sphere_integral(model: AngularIllumination) -> float:
    """``integral density dOmega`` over 4 pi, by adaptive quadrature.

    Azimuthally symmetric, so the azimuth integral is the factor 2 pi. Shares no
    code with the trapezoid the package normalises with, and the branch knots go
    in as break points.
    """

    def integrand(elevation: float) -> float:
        direction = np.array([[math.cos(elevation), 0.0, math.sin(elevation)]])
        return float(model.density(direction)[0] * math.cos(elevation))

    low = math.radians(model.elevation_min_deg)
    high = math.radians(model.elevation_max_deg)
    breaks = sorted(k for k in model.knots() if low < k < high)
    total, _ = quad(integrand, low, high, points=breaks or None, limit=400, epsabs=1e-13, epsrel=1e-13)
    return 2.0 * math.pi * total


@pytest.mark.parametrize("law", LAW_TAGS)
def test_a_law_is_a_probability_density_on_the_sphere(law: str) -> None:
    """The one contract everything downstream rests on.

    `chi` equals one in free space only because this holds, and because the study
    only ever compares sites scored under the same law, a density that integrates
    to something else would rescale every number and nothing would complain.
    """
    assert sphere_integral(FIXTURES[law]) == pytest.approx(1.0, rel=2.0e-6)


@pytest.mark.parametrize("law", LAW_TAGS)
def test_a_law_accepts_just_inside_its_window_and_refuses_just_outside(law: str) -> None:
    """Both edges, from both sides, a nanodegree apart.

    A window that leaks credits a ray arriving from an elevation the law says
    holds no sites. A window that is closed too far throws away the grazing
    directions where the band laws keep most of their measure.
    """
    model = FIXTURES[law]
    for edge, inward in ((model.elevation_min_deg, +1.0), (model.elevation_max_deg, -1.0)):
        if abs(edge) >= 90.0:
            continue  # the sphere has no outside there
        inside = np.radians(edge + inward * 1.0e-9)
        outside = np.radians(edge - inward * 1.0e-9)
        at = np.column_stack([np.cos([inside, outside]), np.zeros(2), np.sin([inside, outside])])
        value = model.weight(at)
        assert value[0] > 0.0, f"{law} refuses a direction inside its own window at {edge}"
        assert value[1] == 0.0, f"{law} credits a direction outside its window at {edge}"


@pytest.mark.parametrize("law", LAW_TAGS)
def test_a_law_is_finite_and_never_negative_anywhere_on_the_sphere(law: str) -> None:
    """Sampled on a grid that lands cells inside, on both edges, and well outside.

    The band laws are differences of slant range caps. An ordering slip in
    ``max(far - near, 0)`` shows up here as negative measure and nowhere else.
    """
    density = FIXTURES[law].density(fibonacci_sphere(8192))
    assert np.all(np.isfinite(density))
    assert np.all(density >= 0.0)


@pytest.mark.parametrize("law", LAW_TAGS)
def test_narrowing_the_window_never_adds_measure(law: str) -> None:
    """``over`` moves the window and leaves the profile alone.

    Read over half its window a law keeps the same unnormalised weight at every
    direction the narrower window still holds, and zero at the rest. It is the
    move the band by band reference integrals need, and it used to be done by
    writing through a frozen dataclass from outside it.
    """
    model = FIXTURES[law]
    low, high = model.elevation_min_deg, model.elevation_max_deg
    middle = 0.5 * (low + high)
    piece = model.over(low, middle)
    assert piece.knots() == model.knots()
    elevation = np.radians(np.linspace(low, high, 501))
    at = np.column_stack([np.cos(elevation), np.zeros_like(elevation), np.sin(elevation)])
    # The split itself is skipped. ``weight`` re-derives the elevation from the
    # direction, so which side of the cut a sample sitting exactly on it lands is
    # a last bit question and not a statement about the law.
    degrees = np.degrees(elevation)
    kept = degrees < middle - 1.0e-9
    dropped = degrees > middle + 1.0e-9
    assert np.array_equal(piece.weight(at)[kept], model.weight(at)[kept])
    assert np.all(piece.weight(at)[dropped] == 0.0)


# ---------------------------------------------------------------------------
# Closed forms. A quadrature that has to land on a number computed another way.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["rooftop", "street_small_cell"])
def test_the_band_law_integral_is_the_volume_of_its_own_shell(name: str) -> None:
    """``pi (d1^2 - d0^2)(h1 - h0)``, and there is no quadrature in that.

    The band law counts sites of uniform volumetric density, so ``(far^3 -
    near^3)/3`` is the radial integral of ``r^2 dr`` and the whole normalisation
    is the volume of the region ``{d in [d0, d1], h in [h0, h1]}`` in cylindrical
    coordinates. That region is an annular slab and its volume is elementary.

    This pins three separate things at once: the profile, the derived elevation
    window, and the ``cos(el)`` Jacobian. Get any of them wrong and the volume
    comes out somewhere else.
    """
    model = ill.VARIANTS[name]
    low_h, high_h = model.height_band_m
    low_d, high_d = model.range_band_m
    volume = math.pi * (high_d**2 - low_d**2) * (high_h - low_h)
    assert model.normalisation() == pytest.approx(volume, rel=1.0e-8)


@pytest.mark.parametrize("name", ["rooftop_pathloss", "street_small_cell_pathloss"])
def test_the_path_loss_band_integral_matches_a_two_dimensional_quadrature(name: str) -> None:
    """The same population integrated in ``(range, height)`` instead of elevation.

    Every site weighted by ``1/r^2`` with ``r^2 = d^2 + h^2``, integrated over the
    band rectangle with the areal element ``2 pi d dd dh``. That never converts to
    elevation at all, so it checks the change of variables the shipped form does
    rather than repeating it.
    """
    model = ill.VARIANTS[name]
    low_h, high_h = model.height_band_m
    low_d, high_d = model.range_band_m
    value, _ = dblquad(
        lambda d, h: 2.0 * math.pi * d / (d * d + h * h),
        low_h,
        high_h,
        low_d,
        high_d,
        epsabs=1e-11,
        epsrel=1e-11,
    )
    assert model.normalisation() == pytest.approx(value, rel=1.0e-8)


def test_the_fixed_height_law_integral_matches_its_antiderivative() -> None:
    """``pi (1/sin^2 a - 1/sin^2 b)``, which is what ``1/sin^3`` integrates to.

    Looser than the band laws by an order of magnitude, and the reason is the law
    rather than the test. ``1/sin^3`` is convex and steep, and the street window
    opens at 0.95 degrees, so a uniform trapezoid over 200001 points overshoots by
    1.4e-8 relative. That is the shipped quadrature error and it is in every
    number this law produced.
    """
    for name in ("rooftop_fixed_height", "street_small_cell_fixed_height"):
        model = ill.VARIANTS[name]
        a = math.radians(model.elevation_min_deg)
        b = math.radians(model.elevation_max_deg)
        closed = math.pi * (1.0 / math.sin(a) ** 2 - 1.0 / math.sin(b) ** 2)
        assert model.normalisation() == pytest.approx(closed, rel=1.0e-7)
        assert model.normalisation() > closed, "the trapezoid on a convex law reads high"


def test_a_cap_law_integrates_to_the_solid_angle_of_its_cap() -> None:
    """``2 pi (1 - sin(el_min))``. The law added at the bottom of this file."""
    for cut in (0.0, 12.0, 45.0, 80.0):
        model = GrazingCutoffLaw(name="cap", elevation_min_deg=cut, elevation_max_deg=90.0)
        assert model.integrate() == pytest.approx(ill.solid_angle_of_band(cut, 90.0), rel=1.0e-9)


def test_the_isotropic_normalisation_is_the_trapezoid_and_not_four_pi() -> None:
    """A gotcha worth pinning, because it is a constant every number divides by.

    ``4 pi`` is the exact answer and 12.566370614100787 is what a 200001 point
    trapezoid over ``cos(el)`` returns. The difference is 2.1e-11 relative and it
    is in every published isotropic susceptibility. Replacing the quadrature with
    the closed form would be a correction, not a refactor.
    """
    assert ill.ISOTROPIC.normalisation() == 12.566370614100787
    assert ill.ISOTROPIC.normalisation() != 4.0 * math.pi
    assert ill.ISOTROPIC.normalisation() == pytest.approx(4.0 * math.pi, rel=1.0e-10)


def test_the_band_clamp_is_load_bearing_at_the_window_edge() -> None:
    """It looks unreachable and it is not, because the window round trips degrees.

    Inside the window ``far >= near`` holds exactly, since the window is where the
    two caps cross. The window is stored in degrees though, and
    ``radians(degrees(atan2(h, d)))`` is not ``atan2(h, d)``, so at the edge the
    caps miss each other by about 1e-16 relative. On street_small_cell that is
    -6.2e-10 in the profile, and the clamp is the only thing keeping the density
    non-negative at its own edge.
    """
    model = ill.STREET_SMALL_CELL
    edge = math.radians(model.elevation_min_deg)
    near, far = model.slant_range_bounds(np.array([edge]))
    assert far[0] - near[0] < 0.0, "the round trip no longer bites, re-read the clamp comment"
    at = np.array([[math.cos(edge), 0.0, math.sin(edge)]])
    assert model.weight(at)[0] == 0.0
    assert model.profile(np.array([edge]))[0] == 0.0


# ---------------------------------------------------------------------------
# Provenance. The question LAW_CHANGE.md was written to answer by hand.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", SHIPPED)
def test_a_shipped_model_can_name_the_law_that_made_it(name: str) -> None:
    record = ill.VARIANTS[name].describe()
    assert record["name"] == name
    assert record["law"] in LAW_REGISTRY
    assert record["kind"] == "angular"
    assert record["family"] in ("", *LAWS)
    assert record["elevation_deg"] == [ill.VARIANTS[name].elevation_min_deg, ill.VARIANTS[name].elevation_max_deg]


@pytest.mark.parametrize("name", SHIPPED)
def test_a_description_is_json_and_rebuilds_the_class_that_wrote_it(name: str) -> None:
    """A manifest carries the tag, and the tag has to be reversible.

    Reading back is what turns the survives-or-not table into a query: a result
    file says ``uniform_sites_band`` and this is what says which class that was.
    """
    import json

    record = json.loads(json.dumps(ill.VARIANTS[name].describe()))
    rebuilt = LAW_REGISTRY[record["law"]]
    assert isinstance(ill.VARIANTS[name], rebuilt)


def test_the_family_of_every_law_agrees_with_the_provenance_reader() -> None:
    """``viz/provenance.py`` maps tags to families by hand. The classes now say it.

    Two copies of one fact is how ``LAW_CHANGE.md`` got long. This is the join
    that keeps them equal.
    """
    from semantic_twin.viz.provenance import LAW_FAMILY

    for law, cls in LAW_REGISTRY.items():
        if law in LAW_FAMILY:
            assert cls.family == LAW_FAMILY[law], law
    assert ill.SourceSet.family == LAW_FAMILY[ill.FACADE_TIP_LAW]
    assert ill.Roofline.law == ill.FACADE_TIP_LAW


def test_a_placed_law_records_the_law_without_disturbing_what_is_on_disk() -> None:
    """``describe`` names the law. ``as_dict`` stays the seven keys payloads carry.

    Every shipped next event payload records the build resolutions and not the
    law, which is exactly the gap the protocol closes. Widening ``as_dict`` would
    have closed it by changing files the golden lock pins, so the law went on a
    new method instead.
    """
    sources = SourceSet(positions=np.zeros((5, 3)), cell_m=1.0, dims=3, azimuths=1440, builders=12)
    assert set(sources.as_dict()) == {"sites", "cell_m", "dims", "azimuths", "builders", "floor_m", "site_lift_m"}
    record = sources.describe()
    assert record["law"] == ill.FACADE_TIP_LAW
    assert record["kind"] == "placed"
    assert record["sites"] == 5


# ---------------------------------------------------------------------------
# Which estimator can consume which law
# ---------------------------------------------------------------------------


def test_the_two_laws_satisfy_the_root_protocol_and_nothing_more_in_common() -> None:
    """The finding the package layout rests on, asserted rather than asserted in prose.

    The band law is a density on direction. The facade tip law is a set of points
    whose sources occupy no solid angle, so it has no density to give and reading
    one at an exit direction returns nothing. They share an identity and a
    provenance record, and that is the honest extent of it.
    """
    band = ill.ROOFTOP
    placed = SourceSet(positions=np.zeros((3, 3)), cell_m=1.0, dims=3, azimuths=720, builders=4)
    for model in (band, placed):
        assert isinstance(model, IlluminationModel)
    assert isinstance(band, AngularIllumination)
    assert not isinstance(band, PlacedIllumination)
    assert isinstance(placed, PlacedIllumination)
    assert not isinstance(placed, AngularIllumination)


def test_each_law_names_the_estimators_that_can_score_it() -> None:
    assert credited_by(ill.ROOFTOP) == ("escape",)
    assert credited_by(SourceSet(positions=np.zeros((1, 3)), cell_m=1.0, dims=3, azimuths=1, builders=1)) == (
        "next_event",
    )
    for law in LAW_TAGS:
        found = credited_by(FIXTURES[law])
        assert found, f"{law} is a population no estimator can score"
        assert set(found) <= set(ESTIMATORS)


def test_the_gather_only_takes_a_law_that_keeps_its_sites() -> None:
    """Next event needs points to connect to, so the type it takes is the placed one."""
    sources = SourceSet(positions=np.array([[0.0, 0.0, 40.0]]), cell_m=1.0, dims=3, azimuths=1, builders=1)
    gather = NextEventGather(geometry=None, sources=sources, rng=np.random.default_rng(0))
    assert isinstance(gather.sources, PlacedIllumination)
    assert gather.chi_bounce() == 0.0


# ---------------------------------------------------------------------------
# The direction grid the density is read on
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("count", [64, 512, 4096])
def test_the_grid_cells_carry_equal_solid_angle_and_no_net_direction(count: int) -> None:
    """A biased grid biases every deposit, since each cell is credited ``4 pi / n``.

    The heights are evenly spaced by construction, so the cell solid angle is
    exactly ``4 pi / n`` in the band sense. What is worth checking is that the
    directions do not pile up anywhere: the vector mean of a set covering the
    sphere is zero, and this holds it to a few parts in ``n``.
    """
    grid = fibonacci_sphere(count)
    assert np.allclose(np.linalg.norm(grid, axis=1), 1.0)
    spacing = np.diff(grid[:, 2])
    assert np.allclose(spacing, spacing[0], rtol=1.0e-12)
    assert np.linalg.norm(grid.mean(axis=0)) < 4.0 / count


@pytest.mark.parametrize("cells", [16, 512, 4096])
def test_the_band_search_returns_the_dense_answer_for_every_input(cells: int) -> None:
    """The fast path is an optimisation, so it has to be an identity.

    Grid points themselves are the hard case, because a query sitting exactly on
    a cell ties with itself and both forms have to break the tie the same way.
    """
    grid = fibonacci_sphere(cells)
    for query in (
        grid,
        sample_sphere(50_000, np.random.default_rng(3)),
        np.repeat(grid[:1], 17, axis=0),
        np.empty((0, 3)),
    ):
        assert np.array_equal(nearest_cell(query, grid), _brute_nearest_cell(query, grid, 65536))


def test_an_unsorted_grid_falls_back_rather_than_answering_wrongly() -> None:
    """The band search needs heights descending. A grid that is not takes the dense path."""
    grid = fibonacci_sphere(512)
    shuffled = grid[np.random.default_rng(1).permutation(512)]
    query = sample_sphere(20_000, np.random.default_rng(2))
    assert np.array_equal(nearest_cell(query, shuffled), _brute_nearest_cell(query, shuffled, 65536))


# ---------------------------------------------------------------------------
# The placed law, on a geometry with an answer you can write down
# ---------------------------------------------------------------------------


class OpenSky:
    """Nothing to hit. Every connection is clear and every range is exact."""

    def intersect(self, origins: np.ndarray, directions: np.ndarray) -> tuple[Any, ...]:
        count = np.asarray(origins).shape[0]
        return (
            np.zeros(count, dtype=bool),
            np.full(count, 1.0e30),
            np.zeros((count, 3)),
            np.zeros(count, dtype=np.int64),
        )


def test_the_direct_term_is_the_mean_inverse_square_range_over_the_whole_set() -> None:
    """A ring of sites at one slant range, so the answer is ``1/r^2`` and nothing else.

    Averaging over every site rather than over the visible ones is what makes the
    number independent of how densely the set was sampled, which is the assumption
    the cross city comparison rests on. Doubling the ring has to change nothing.
    """
    radius, height = 60.0, 25.0
    slant_squared = radius**2 + height**2
    for count in (12, 24, 720):
        angle = np.linspace(0.0, 2.0 * np.pi, count, endpoint=False)
        ring = np.column_stack([radius * np.cos(angle), radius * np.sin(angle), np.full(count, height)])
        direct, seen = ill.sources.direct_from_sites(OpenSky(), np.zeros((1, 3)), ring)
        assert direct[0] == pytest.approx(1.0 / slant_squared, rel=1.0e-12)
        assert seen[0] == 1.0


def test_the_gather_reproduces_the_lambertian_connection_it_stands_for() -> None:
    """One vertex, one site, open sky, so the deposit is arithmetic you can do by hand.

    The connection is ``throughput (1 - share) / pi * cos(out) / r^2`` and
    ``chi_bounce`` scales it by ``4 pi / rays``. Nothing here is sampled, because
    a single site makes the draw deterministic.
    """
    site = np.array([[0.0, 0.0, 40.0]])
    sources = SourceSet(positions=site, cell_m=1.0, dims=3, azimuths=1, builders=1)
    gather = NextEventGather(geometry=OpenSky(), sources=sources, rng=np.random.default_rng(0), max_order=3)
    position = np.array([[0.0, 30.0, 0.0]])
    normal = np.array([[0.0, 0.0, 1.0]])
    throughput, share = np.array([0.4]), np.array([0.25])
    gather.begin(np.zeros(3), 1_000)
    gather.vertex(
        index=np.array([0]),
        position=position,
        incoming=normal,
        normal=normal,
        throughput=throughput,
        share=share,
        order=np.array([1]),
        path_length=np.array([30.0]),
    )
    to_site = site[0] - position[0]
    distance = float(np.linalg.norm(to_site))
    expected = 0.4 * 0.75 / math.pi * (to_site[2] / distance) / distance**2
    assert gather.total == pytest.approx(expected, rel=1.0e-12)
    assert gather.chi_bounce() == pytest.approx(4.0 * math.pi * expected / 1_000, rel=1.0e-12)
    assert gather.chi_by_order()[1] == pytest.approx(gather.chi_bounce(), rel=1.0e-12)


def test_a_site_behind_the_surface_is_never_connected_to() -> None:
    """``cos_out > 0`` is the whole of it, and a leak here would credit through a wall."""
    sources = SourceSet(positions=np.array([[0.0, 0.0, -40.0]]), cell_m=1.0, dims=3, azimuths=1, builders=1)
    gather = NextEventGather(geometry=OpenSky(), sources=sources, rng=np.random.default_rng(0))
    gather.begin(np.zeros(3), 10)
    gather.vertex(
        index=np.array([0]),
        position=np.zeros((1, 3)),
        incoming=np.array([[0.0, 0.0, 1.0]]),
        normal=np.array([[0.0, 0.0, 1.0]]),
        throughput=np.array([1.0]),
        share=np.array([0.0]),
        order=np.array([1]),
        path_length=np.array([1.0]),
    )
    assert gather.connections == 0
    assert gather.cleared == 0
    assert gather.total == 0.0


def test_thinning_converges_on_a_solid_grid_and_runs_away_on_a_flat_one() -> None:
    """The reason ``dims=3`` is the default, measured rather than asserted.

    A wall occupies a line of flat cells and gains sites as ``1/cell``, a roof
    occupies a patch and gains as ``1/cell^2``, so a flat grid keeps shifting
    weight onto horizontal surface as the cell shrinks. On a solid grid both gain
    as ``1/cell^2`` and the share stops moving.
    """
    span = np.linspace(-20.0, 20.0, 240)
    rise = np.linspace(0.0, 20.0, 240)
    # A flat roof and a wall that stands clear of it, so neither hides the other
    # when the survivor of a shared cell is picked.
    roof = np.column_stack([np.repeat(span, 240), np.tile(span, 240), np.full(240 * 240, 20.0)])
    wall = np.column_stack([np.full(240 * 240, 25.0), np.tile(span, 240), np.repeat(rise, 240)])
    cloud = np.vstack([roof, wall])

    def roof_share(dims: int, cell: float) -> float:
        kept = ill.thin(cloud, cell, dims=dims)
        return float((kept[:, 0] < 24.0).mean())

    flat = [roof_share(2, cell) for cell in (4.0, 2.0, 1.0)]
    solid = [roof_share(3, cell) for cell in (4.0, 2.0, 1.0)]
    assert flat[0] < flat[1] < flat[2], f"the flat grid stopped shifting weight onto the roof: {flat}"
    assert flat[2] > 0.95, f"the flat grid should be nearly all roof by 1 m: {flat}"
    assert max(solid) - min(solid) < 0.02, f"the solid grid should hold its share: {solid}"
