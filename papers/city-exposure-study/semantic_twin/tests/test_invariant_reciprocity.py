"""The two estimators answer the same question, so they must give one answer.

On real cities the escape estimator and the next event estimator disagree by a
factor of three to five, and nobody can presently say how much of that is
geometry and how much is a defect. This file removes the geometry from the
argument. The scene is a finite disc of ground under a head, which has a closed
form, and the source population is put on a distant shell so both estimators
see the same physics.

Two properties are pinned.

Reciprocity. The escape estimator integrates an assumed angular density over
exit directions. The next event estimator connects each path vertex to an
explicit site. Under an isotropic sky those are the same integral, so the two
have to land on the same number and on the closed form.

Roughness invariance. An isotropic sky does not care whether a reflection left
the surface as a mirror or as a Lambertian lobe, because the same power ends up
spread over the same sphere of sources. So neither estimator's answer may move
when the surface roughness is changed with everything else held fixed. That is
what the specular share is: a redistribution, not a loss.

The geometry is deliberately lopsided. The direct term is 0.598 and the bounced
term is 0.085, a seven to one split, so an estimator that is wrong by a constant
on one of the two cannot pass by cancelling against the other.
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy.integrate import quad

from semantic_twin.illumination import ISOTROPIC, fibonacci_sphere
from semantic_twin.illumination.sources import NextEventGather, SourceSet
from semantic_twin.propagation.tracer import (
    SbrTracer,
    TraceConfig,
    fresnel_power_reflectance,
    specular_share,
)

#: Concrete at 15 GHz, so the reflectance is angle dependent and nowhere near 1.
PERMITTIVITY = complex(5.31, -0.90)
FREQUENCY_HZ = 15.0e9
WAVELENGTH_M = 299_792_458.0 / FREQUENCY_HZ

DISC_RADIUS_M = 50.0
HEAD_HEIGHT_M = 10.0
#: Far enough that a bounce vertex anywhere on the disc is at the same range
#: from every site to within 0.3 percent, which is what makes the two estimators
#: comparable at all.
SHELL_RADIUS_M = 20_000.0
RAYS = 200_000

#: Fully rough at a two centimetre wavelength, so the coherent share is zero and
#: every reflection is Lambertian. This is the regime the existing suite tests.
ROUGH_M = 1.0
#: Two millimetres of relief, which puts the coherent share around 0.6 at the
#: incidences that matter. This is the regime a real facade is in and the one no
#: existing test visits.
PARTLY_SPECULAR_M = 0.002

INFINITY = 1.0e30


class DiscGeometry:
    """A disc of ground at ``z = 0``, and nothing else.

    An infinite plane will not do here. Its bounce vertices run out to
    kilometres, so a source shell of any finite radius stops being far field for
    the grazing rays and the comparison becomes a test of the shell radius. A
    disc bounds the vertices, and its subtended solid angle is still a closed
    form.
    """

    def __init__(self, radius_m: float, plane_z: float = 0.0) -> None:
        self.radius_m = float(radius_m)
        self.plane_z = float(plane_z)

    def intersect(self, origins, directions):
        dz = directions[:, 2]
        with np.errstate(divide="ignore", invalid="ignore"):
            distance = -(origins[:, 2] - self.plane_z) / dz
        forward = np.isfinite(distance) & (distance > 0.0)
        point = origins + np.where(forward, distance, 0.0)[:, None] * directions
        hit = forward & (point[:, 0] ** 2 + point[:, 1] ** 2 <= self.radius_m**2)
        normal = np.tile(np.array([0.0, 0.0, 1.0]), (origins.shape[0], 1))
        face = np.zeros(origins.shape[0], dtype=np.int64)
        return hit, np.where(hit, distance, INFINITY), normal, face


def _reflectance(mu: float) -> float:
    return float(fresnel_power_reflectance(np.array([mu]), np.asarray(PERMITTIVITY))[0])


def _share(mu: float, rms_height_m: float) -> float:
    return float(specular_share(np.array([rms_height_m]), np.array([mu]), WAVELENGTH_M)[0])


#: Cosine of incidence below which a downward ray misses the disc entirely.
MU_MIN = HEAD_HEIGHT_M / np.sqrt(DISC_RADIUS_M**2 + HEAD_HEIGHT_M**2)


def closed_form() -> tuple[float, float]:
    """``(direct, bounced)`` susceptibility for the disc, under an isotropic sky.

    Rays leave the head uniformly on the sphere, so the cosine of incidence on
    the disc is uniform on ``[0, 1]`` over the downward half. A ray hits the disc
    when that cosine exceeds ``MU_MIN``, reflects with the unpolarised Fresnel
    power reflectance, and then leaves for good, because a lobe off a flat disc
    never comes back. Everything else escapes unattenuated.
    """
    direct = 1.0 - 0.5 * (1.0 - MU_MIN)
    bounced = 0.5 * quad(_reflectance, MU_MIN, 1.0, limit=200)[0]
    return direct, bounced


def diffuse_only_bounce(rms_height_m: float) -> float:
    """The bounced term with the coherent share of every reflection removed.

    Not a physical quantity. It is what an estimator computes if it connects only
    the diffuse lobe to a source and never rejoins the specular one, and it is
    here so the size of that omission can be stated rather than guessed at.
    """
    return 0.5 * quad(lambda mu: _reflectance(mu) * (1.0 - _share(mu, rms_height_m)), MU_MIN, 1.0, limit=200)[0]


_CACHE: dict[float, tuple[float, float, float, float]] = {}


def measure(rms_height_m: float) -> tuple[float, float, float, float]:
    """``(escape chi, escape direct, next event direct, next event bounced)``.

    Both estimators run off one trace, which is the point: same rays, same
    scene, same seed, so any difference between them is the estimator and
    nothing else. The next event numbers are multiplied by the shell radius
    squared, which is the free space value of the direct term and therefore the
    scale that makes the two comparable.
    """
    if rms_height_m in _CACHE:
        return _CACHE[rms_height_m]
    disc = DiscGeometry(DISC_RADIUS_M)
    head = np.array([0.0, 0.0, HEAD_HEIGHT_M])
    # An equal solid angle shell, so the visible fraction is the geometric one
    # rather than a binomial draw around it.
    sources = SourceSet(
        positions=head + SHELL_RADIUS_M * fibonacci_sphere(8192),
        cell_m=1.0,
        dims=3,
        azimuths=0,
        builders=0,
    )
    config = TraceConfig(frequency_hz=FREQUENCY_HZ, rays=RAYS, max_bounces=2, seed=11, local_cells=512)
    tracer = SbrTracer(disc, None, np.array([PERMITTIVITY]), np.array([rms_height_m]), config)
    gather = NextEventGather(
        geometry=disc,
        sources=sources,
        rng=np.random.default_rng(23),
        samples=1,
        max_order=2,
    )
    result = tracer.trace(head, {"isotropic": ISOTROPIC}, ground_z_m=0.0, seed=11, gather=gather)
    direct, _ = sources.direct(disc, head)
    out = (
        result.susceptibility["isotropic"],
        result.susceptibility_direct["isotropic"],
        float(direct[0]) * SHELL_RADIUS_M**2,
        gather.chi_bounce() * SHELL_RADIUS_M**2,
    )
    _CACHE[rms_height_m] = out
    return out


def test_the_geometry_is_not_a_degenerate_case():
    """Guard on the setup itself.

    Every assertion below would still pass on a scene where the bounced term is
    negligible or where it is half the answer. Neither is interesting. This
    fixes the split at roughly seven to one and fails loudly if a later edit
    flattens it.
    """
    direct, bounced = closed_form()
    assert 0.55 < direct < 0.65
    assert 0.07 < bounced < 0.10
    ratio = direct / bounced
    assert 5.0 < ratio < 10.0


def test_the_escape_estimator_lands_on_the_closed_form():
    """Energy over a whole trace, not just at one interface.

    Every ray leaves with unit weight and comes back credited at whatever the
    scene left of it, so this is the end to end statement that nothing is
    created or lost between the head and the sky.
    """
    direct, bounced = closed_form()
    chi, chi_direct, _, _ = measure(ROUGH_M)
    assert chi_direct == pytest.approx(direct, rel=0.01)
    assert chi - chi_direct == pytest.approx(bounced, rel=0.02)
    assert chi == pytest.approx(direct + bounced, rel=0.01)


def test_the_next_event_estimator_lands_on_the_same_closed_form():
    """The other estimator, on the same trace, against the same target."""
    direct, bounced = closed_form()
    _, _, ne_direct, ne_bounced = measure(ROUGH_M)
    assert ne_direct == pytest.approx(direct, rel=0.01)
    assert ne_bounced == pytest.approx(bounced, rel=0.02)


def test_the_two_estimators_agree_on_a_lambertian_scene():
    """Reciprocity, stated as the equality it is.

    This is the anchor. It says the comparison is meaningful, the shell is far
    enough away, the disc is small enough, and the two normalisations line up.
    Without it, the failure below could be blamed on the harness.
    """
    chi, _, ne_direct, ne_bounced = measure(ROUGH_M)
    assert ne_direct + ne_bounced == pytest.approx(chi, rel=0.01)


def test_the_escape_answer_does_not_move_with_surface_roughness():
    """A mirror and a Lambertian put the same power into the same sky.

    Under an isotropic source density the two are indistinguishable, so the
    susceptibility may not depend on the roughness at all. It does not, which is
    what makes the same statement about the other estimator a fair test rather
    than a wish.
    """
    values = np.array([measure(rms)[0] for rms in (ROUGH_M, 0.005, PARTLY_SPECULAR_M)])
    assert values.max() / values.min() == pytest.approx(1.0, abs=0.005)


@pytest.mark.xfail(
    strict=True,
    reason="docs/BUGS.md finding 1: sources.py:382 credits only throughput*(1-share)/pi, "
    "so the coherent lobe is never routed to a source and never rejoined",
)
def test_the_next_event_answer_does_not_move_with_surface_roughness():
    """The same invariant, on the estimator that fails it.

    At two millimetres of relief the coherent share is about 0.6 over the
    incidences that matter, and the bounced term falls from 0.0845 to 0.0313,
    which is the diffuse part of the reflection and nothing else. The total
    drops 8 percent. Roughness is a free parameter of the study, so an estimator
    whose answer tracks it is reporting the parameter and not the scene.
    """
    totals = []
    for rms in (ROUGH_M, 0.005, PARTLY_SPECULAR_M):
        _, _, ne_direct, ne_bounced = measure(rms)
        totals.append(ne_direct + ne_bounced)
    assert max(totals) / min(totals) == pytest.approx(1.0, abs=0.02)


@pytest.mark.xfail(
    strict=True,
    reason="docs/BUGS.md finding 1: the specular share is discarded, so the two estimators "
    "cannot agree on any surface that is not fully rough",
)
def test_the_two_estimators_agree_on_a_partly_specular_scene():
    """Reciprocity again, with the one thing changed that should not matter.

    Nothing about the scene, the sources or the sky has moved. Only the split
    between the coherent and diffuse lobes of the same total reflectance. The
    escape estimator is unmoved. The next event estimator is 8 percent low, and
    its bounced term sits on :func:`diffuse_only_bounce` to within the Monte
    Carlo noise, 0.0313 against 0.0313, which names the omission rather than
    merely detecting it.
    """
    chi, _, ne_direct, ne_bounced = measure(PARTLY_SPECULAR_M)
    assert ne_direct + ne_bounced == pytest.approx(chi, rel=0.01)


def test_the_bounced_term_is_bracketed_by_its_two_lobes():
    """A bracket that holds whichever way finding 1 is settled.

    The bounced term cannot be less than the diffuse lobe alone, and cannot be
    more than the whole reflection. Today it sits on the lower edge, which is
    the defect. A fix moves it to the upper edge. Either way this stays green,
    so it is the one statement about the partly specular case that does not have
    to be rewritten when the code changes.
    """
    _, _, _, ne_bounced = measure(PARTLY_SPECULAR_M)
    _, bounced = closed_form()
    floor = diffuse_only_bounce(PARTLY_SPECULAR_M)
    assert floor > 0.0
    assert floor / bounced < 0.5  # the two edges are far apart, so the bracket bites
    assert floor * 0.97 <= ne_bounced <= bounced * 1.03
