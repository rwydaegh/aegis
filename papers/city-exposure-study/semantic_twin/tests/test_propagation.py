"""Closed form and invariant tests for the adjoint SBR estimator.

MONOSTATIC_SBR.md section 11 orders these from "cannot be argued with" to
"agrees with another tool". Everything here is in the first category: an exact
analytic target, run against the same estimator that produces the published
numbers.
"""

from __future__ import annotations

import pathlib

import numpy as np
import pytest

from semantic_twin.propagation import (
    ISOTROPIC,
    PEC_PERMITTIVITY,
    ROOFTOP,
    STREET_SMALL_CELL,
    PlaneGeometry,
    SbrTracer,
    SphereGeometry,
    TraceConfig,
    fibonacci_sphere,
    ground_plane_susceptibility,
)
from semantic_twin.propagation.closed_form import (
    ground_plane_band_average,
    ground_plane_susceptibility_te_only,
)
from semantic_twin.propagation.directions import sample_sphere
from semantic_twin.propagation.scene import CLASS_NAMES, classify_faces
from semantic_twin.propagation.tracer import fresnel_power_reflectance, specular_share

MODELS = {"isotropic": ISOTROPIC, "rooftop": ROOFTOP, "street_small_cell": STREET_SMALL_CELL}
CONCRETE = complex(5.24, -0.46055233310470917)


class EmptyGeometry:
    """No geometry at all. Every ray escapes on the zero bounce."""

    def intersect(self, origins, directions):  # noqa: ANN001, ANN201
        count = origins.shape[0]
        return (
            np.zeros(count, dtype=bool),
            np.full(count, 1.0e30),
            np.zeros((count, 3)),
            np.zeros(count, dtype=np.int64),
        )


def make_tracer(geometry, permittivity, rms, **kwargs):  # noqa: ANN001, ANN201
    config = TraceConfig(local_cells=256, exit_bands=18, **kwargs)
    return SbrTracer(geometry, None, np.array([permittivity]), np.array([rms]), config)


def test_fibonacci_sphere_is_near_equal_solid_angle() -> None:
    grid = fibonacci_sphere(4096)
    assert np.allclose(np.linalg.norm(grid, axis=1), 1.0)
    # The z marginal of an equal area sphere grid is uniform on [-1, 1].
    counts, _ = np.histogram(grid[:, 2], bins=16, range=(-1.0, 1.0))
    assert counts.max() / counts.min() < 1.02


def test_illumination_models_integrate_to_one() -> None:
    rng = np.random.default_rng(0)
    directions = sample_sphere(2_000_000, rng)
    for model in MODELS.values():
        total = 4.0 * np.pi * model.density(directions).mean()
        assert total == pytest.approx(1.0, abs=0.02)


def test_free_space_identity() -> None:
    """Section 11.3. With no geometry T_S is the transverse projector and K_S is 1."""
    tracer = make_tracer(EmptyGeometry(), PEC_PERMITTIVITY, 0.0, rays=200_000, seed=1)
    result = tracer.trace(np.array([0.0, 0.0, 1.5]), MODELS)
    assert result.sky_fraction == 1.0
    assert result.susceptibility["isotropic"] == pytest.approx(1.0, abs=1.0e-6)
    assert np.max(np.abs(result.exit_profile - 1.0)) < 0.03
    for name in MODELS:
        assert result.susceptibility[name] == pytest.approx(1.0, abs=0.05)


def test_pec_ground_plane_gives_exactly_two() -> None:
    """Section 11.1. The angle independent closed form target is 2, not 1.

    A naive amplitude accumulating estimator returns 1.0 here with no visible
    noise, which is how section 2.8 of the design document was found. What this
    case cannot do is discriminate polarisation handling, since both Fresnel
    coefficients have unit magnitude at every angle. That job belongs to the
    dielectric test below. The target is 2 to about 1e-5 rather than to machine
    precision, because ``PEC_PERMITTIVITY`` is a large finite stand in for
    infinite conductivity.
    """
    tracer = make_tracer(PlaneGeometry(0.0), PEC_PERMITTIVITY, 0.0, rays=400_000, seed=2)
    result = tracer.trace(np.array([0.0, 0.0, 1.5]), MODELS, ground_z_m=0.0)
    half = result.exit_profile.size // 2
    upper = result.exit_profile[half:]
    lower = result.exit_profile[:half]
    assert np.max(np.abs(upper - 2.0)) < 0.03
    assert np.max(lower) == 0.0
    # Illumination confined above the horizon sees the same factor of two.
    assert result.susceptibility["rooftop"] == pytest.approx(2.0, rel=0.03)


def test_dielectric_ground_plane_matches_closed_form() -> None:
    """Section 11.1, dielectric case. This is the test with teeth.

    The perfect conductor case cannot discriminate anything about polarisation
    or material handling: both Fresnel coefficients have unit magnitude at
    every angle, so K is 2 whether the estimator averages TE and TM, uses one
    of them, or takes the larger. Concrete near its pseudo Brewster angle
    separates them by nearly three orders of magnitude, so the correct answer
    and the TE only answer differ by about 0.9 dB.
    """
    tracer = make_tracer(PlaneGeometry(0.0), CONCRETE, 0.0, rays=800_000, seed=3)
    result = tracer.trace(np.array([0.0, 0.0, 1.5]), MODELS, ground_z_m=0.0)
    target = ground_plane_band_average(result.exit_sin_edges, CONCRETE)
    centres = 0.5 * (result.exit_sin_edges[:-1] + result.exit_sin_edges[1:])
    above = centres > 0.0
    measured = result.exit_profile[above]
    assert np.max(np.abs(measured / target[above] - 1.0)) < 0.02

    # And the wrong answer has to be rejected, at every band where the two
    # differ by more than the Monte Carlo error.
    elevation = np.degrees(np.arcsin(centres[above]))
    wrong = ground_plane_susceptibility_te_only(elevation, CONCRETE)
    right = ground_plane_susceptibility(elevation, CONCRETE)
    separated = np.abs(wrong / right - 1.0) > 0.05
    assert separated.sum() >= 5
    assert np.all(np.abs(measured[separated] / wrong[separated] - 1.0) > 0.04)

    # The band nearest the pseudo Brewster angle. TM has all but vanished there,
    # so the two candidate answers sit about 0.9 dB apart and the trace has to
    # land on the lower one.
    sharpest = int(np.argmin(np.abs(elevation - 24.4)))
    assert elevation[sharpest] == pytest.approx(22.9, abs=1.0)
    assert right[sharpest] == pytest.approx(1.23, abs=0.02)
    separation_db = 10.0 * np.log10(wrong[sharpest] / right[sharpest])
    assert separation_db == pytest.approx(0.78, abs=0.05)
    assert measured[sharpest] == pytest.approx(right[sharpest], rel=0.02)


def test_fresnel_limits() -> None:
    cosine = np.linspace(0.0, 1.0, 21)
    perfect = fresnel_power_reflectance(cosine, np.asarray(PEC_PERMITTIVITY))
    # PEC_PERMITTIVITY is a large finite stand in for infinite conductivity, so
    # the reflectance falls short of 1 by order 1/sqrt(|eps|).
    assert np.allclose(perfect, 1.0, atol=1.0e-4)
    # Exact grazing on a vacuum interface is 0/0, which is degenerate rather
    # than wrong, so it is excluded rather than papered over.
    vacuum = fresnel_power_reflectance(cosine[1:], np.asarray(complex(1.0, 0.0)))
    assert np.allclose(vacuum, 0.0, atol=1.0e-12)
    concrete = fresnel_power_reflectance(cosine, np.asarray(CONCRETE))
    assert np.all((concrete >= 0.0) & (concrete <= 1.0))
    # Grazing incidence reflects everything, normal incidence does not.
    assert concrete[0] == pytest.approx(1.0, abs=1.0e-6)
    assert concrete[-1] < 0.2


def test_specular_share_is_a_fraction() -> None:
    cosine = np.linspace(0.0, 1.0, 11)
    share = specular_share(np.full_like(cosine, 0.004), cosine, 0.02)
    assert np.all((share >= 0.0) & (share <= 1.0))
    assert share[0] == pytest.approx(1.0)
    assert share[-1] < share[0]
    smooth = specular_share(np.zeros_like(cosine), cosine, 0.02)
    assert np.allclose(smooth, 1.0)


def test_closed_lossless_cavity_conserves_energy() -> None:
    """Section 11.3 white furnace. Nothing escapes a closed perfect reflector."""
    tracer = make_tracer(SphereGeometry(10.0), PEC_PERMITTIVITY, 0.0, rays=20_000, seed=4, max_bounces=8)
    result = tracer.trace(np.array([0.0, 0.0, 0.0]), {"isotropic": ISOTROPIC})
    assert result.escaped_fraction == 0.0
    assert result.susceptibility["isotropic"] == 0.0
    assert result.diagnostics["truncated_rays"] == 20_000


def test_susceptibility_is_non_negative_and_bounded_by_the_reflector() -> None:
    """A lossy ground can only remove power relative to the perfect one."""
    lossy = make_tracer(PlaneGeometry(0.0), CONCRETE, 0.0, rays=200_000, seed=5)
    perfect = make_tracer(PlaneGeometry(0.0), PEC_PERMITTIVITY, 0.0, rays=200_000, seed=5)
    a = lossy.trace(np.array([0.0, 0.0, 1.5]), MODELS).susceptibility["rooftop"]
    b = perfect.trace(np.array([0.0, 0.0, 1.5]), MODELS).susceptibility["rooftop"]
    assert 1.0 <= a <= b


def test_zero_bounce_susceptibility_equals_the_sky_fraction() -> None:
    """Section 2.7. `K_iso^(0)` is the sky fraction, exactly and by definition.

    This is the strongest cheap check in the suite and it costs nothing. The
    zero bounce transfer tensor is the identity in sky visible directions and
    zero in blocked ones, so its isotropic average is the sky solid angle
    fraction. Getting it right requires the direction binning, the per cell
    solid angle weight, the occlusion test and the illumination normalisation
    to all be correct at once, and unlike the ground plane cases it holds for
    any geometry whatever, so it is asserted here on a plane, on a sphere and
    on nothing at all.

    It is an identity of the estimator rather than an independent measurement,
    so it cannot detect a systematically wrong ray distribution. What it does
    detect is any inconsistency between the two ways this code counts the same
    directions.

    It holds to Monte Carlo precision and not exactly, and the reason is worth
    recording because the near miss looks like a bug and is not one. The sky
    fraction is a ratio of sums over all rays, while ``chi_iso_direct`` sums a
    per cell mean, so the two differ by the covariance between a cell's escape
    rate and its ray count. Both are unbiased for the same limit and they
    converge to each other, which is what the scaling test below asserts.
    """
    for geometry, expected in ((EmptyGeometry(), 1.0), (PlaneGeometry(0.0), 0.5)):
        tracer = make_tracer(geometry, CONCRETE, 0.0, rays=200_000, seed=6)
        result = tracer.trace(np.array([0.0, 0.0, 1.5]), MODELS, ground_z_m=0.0)
        assert result.sky_fraction == pytest.approx(expected, abs=0.01)
        assert result.susceptibility_direct["isotropic"] == pytest.approx(
            result.sky_fraction, rel=0.01
        )


def test_sky_fraction_identity_converges_as_the_ray_count_grows() -> None:
    """The residual in the identity is Monte Carlo noise, so it must shrink.

    A constant offset would mean a genuine normalisation error. A residual that
    falls roughly as one over the square root of the ray count is the ratio
    estimator behaving as it should.
    """
    geometry = SphereGeometry(20.0, (0.0, 0.0, -19.0))
    residuals = []
    for rays in (25_000, 400_000):
        tracer = make_tracer(geometry, CONCRETE, 0.0, rays=rays, seed=9)
        result = tracer.trace(np.array([0.0, 0.0, 1.5]), MODELS)
        assert 0.0 < result.sky_fraction < 1.0
        residuals.append(
            abs(result.susceptibility_direct["isotropic"] / result.sky_fraction - 1.0)
        )
    # Sixteen times the rays should buy about four times the agreement. Allow a
    # wide margin, since a single realisation of a noise level is itself noisy.
    assert residuals[1] < residuals[0] / 2.0
    assert residuals[1] < 3.0e-3


def test_lambertian_ground_plane_matches_one_plus_two_sine() -> None:
    """Closed form for the diffuse branch, which the specular tests never touch.

    Make the plane a perfect reflector and rough enough that the Rayleigh
    coherent fraction vanishes, so every bounce is cosine scattered. Half the
    rays leave upward and escape, contributing 1. The other half hit the plane
    and re-emit with density ``cos(theta)/pi = sin(el)/pi``, so their
    contribution to ``K_tot`` is ``4*pi*(1/2)*sin(el)/pi = 2*sin(el)``. Hence

        K_tot(el) = 1 + 2*sin(el)

    exactly, running from 1 at the horizon to 3 at the zenith. This tests the
    cosine hemisphere sampler and the diffuse throughput weight together, and a
    wrong power of the cosine in either shows up immediately as a slope error.
    """
    tracer = make_tracer(PlaneGeometry(0.0), PEC_PERMITTIVITY, 0.5, rays=800_000, seed=7, max_bounces=1)
    result = tracer.trace(np.array([0.0, 0.0, 1.5]), MODELS, ground_z_m=0.0)
    edges = result.exit_sin_edges
    above = 0.5 * (edges[:-1] + edges[1:]) > 0.0
    # Band average of 1 + 2*sin(el) over equal solid angle bands in sin(el).
    target = 1.0 + 2.0 * 0.5 * (edges[:-1] + edges[1:])
    measured = result.exit_profile
    assert np.max(np.abs(measured[above] - target[above])) < 0.06
    assert np.max(measured[~above]) == 0.0
    assert measured[above].mean() == pytest.approx(2.0, rel=0.01)


def test_rayleigh_criterion_is_angle_dependent_at_grazing() -> None:
    """The same plane is rough at the zenith and smooth at the horizon.

    ``g = 4*pi*s*cos(theta)/lam`` uses the incidence cosine, which for a ground
    plane is ``sin(el)``, so a surface that fully diffuses a steep ray still
    reflects a grazing one specularly. Against the pure Lambertian closed form
    of the previous test, that shows up as an excess in the lowest elevation
    band and nowhere else.
    """
    tracer = make_tracer(PlaneGeometry(0.0), PEC_PERMITTIVITY, 0.05, rays=800_000, seed=7, max_bounces=1)
    result = tracer.trace(np.array([0.0, 0.0, 1.5]), MODELS, ground_z_m=0.0)
    edges = result.exit_sin_edges
    lambertian = 1.0 + 2.0 * 0.5 * (edges[:-1] + edges[1:])
    excess = result.exit_profile - lambertian
    half = excess.size // 2
    assert excess[half] > 0.15
    assert np.max(np.abs(excess[half + 1 :])) < 0.08


def test_roughness_conserves_power_and_flattens_the_specular_lobe() -> None:
    smooth = make_tracer(PlaneGeometry(0.0), PEC_PERMITTIVITY, 0.0, rays=200_000, seed=7)
    rough = make_tracer(PlaneGeometry(0.0), PEC_PERMITTIVITY, 0.05, rays=200_000, seed=7)
    fine = smooth.trace(np.array([0.0, 0.0, 1.5]), MODELS).exit_profile
    coarse = rough.trace(np.array([0.0, 0.0, 1.5]), MODELS).exit_profile
    # A perfect reflector conserves power whatever the roughness, so the total
    # over the exit bands is unchanged, only its distribution moves.
    assert coarse.sum() == pytest.approx(fine.sum(), rel=0.02)
    half = fine.size // 2
    # Specular reflection off a plane maps elevation to elevation, so the smooth
    # profile is flat. Diffuse scattering is not, and tilts toward the zenith.
    assert np.max(np.abs(fine[half:] - 2.0)) < 0.05
    assert np.max(np.abs(coarse[half:] - 2.0)) > 0.5
    assert coarse[-1] > coarse[half]


def test_absorbed_power_density_obeys_the_relu_bound() -> None:
    """`Sab = Sinc*T0*ReLU[n.(-k)]` can never exceed `Sinc*T0`, for any spectrum.

    This is the monograph's own bound applied to whatever the tracer produces,
    and it is the check that catches a solid angle weight or a sign error in the
    handover from the environment side to the body side. It is run against real
    traced spectra in the study, and here against three extreme ones.
    """
    pytest.importorskip("aegis")
    from semantic_twin.propagation.exposure import BodyCoupler

    phantom = pathlib.Path("/home/user/aegis/data/duke.stl")
    if not phantom.exists():
        pytest.skip("phantom mesh not available")
    coupler = BodyCoupler(str(phantom), 15.0e9, body_mass_kg=72.4)
    grid = fibonacci_sphere(256)
    solid_angle = 4.0 * np.pi / 256
    rng = np.random.default_rng(0)
    spectra = {
        "isotropic": np.full(256, 1.0 / (4.0 * np.pi)),
        "single direction": np.eye(256)[0] / solid_angle,
        "random": np.abs(rng.normal(size=256)),
    }
    for name, rho in spectra.items():
        exposure = coupler.couple(grid, rho, solid_angle, 1.0)
        bound = exposure.arriving_power_density_w_m2 * coupler.engine.T0
        assert exposure.peak_sab_w_m2 <= bound * (1.0 + 1.0e-9), name
        assert exposure.mean_sab_w_m2 <= exposure.peak_sab_w_m2 + 1.0e-12
        assert exposure.absorbed_power_w >= 0.0
    # A single plane wave all but saturates the bound. It falls short by the
    # angle between the arrival direction and the best aligned facet normal,
    # which on a 56k triangle phantom is small but not zero, so the bound is
    # approached from below rather than met exactly.
    single = coupler.couple(grid, spectra["single direction"], solid_angle, 1.0)
    assert single.peak_sab_w_m2 <= coupler.engine.T0
    assert single.peak_sab_w_m2 > 0.999 * coupler.engine.T0
    # Isotropic illumination puts the mean at exactly a quarter of it, because
    # the average of ReLU(cos) over the sphere is 1/4.
    isotropic = coupler.couple(grid, spectra["isotropic"], solid_angle, 1.0)
    assert isotropic.mean_sab_w_m2 == pytest.approx(coupler.engine.T0 / 4.0, rel=0.02)


def test_classify_faces_separates_ground_facade_and_roof() -> None:
    vertices = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 20.0],
            [1.0, 0.0, 20.0],
            [0.0, 1.0, 20.0],
            [0.0, 0.0, 10.0],
            [0.0, 1.0, 10.0],
        ]
    )
    faces = np.array([[0, 1, 2], [3, 4, 5], [0, 2, 6], [3, 5, 4]])
    index = classify_faces(vertices, faces, 0.0)
    assert CLASS_NAMES[index[0]] == "ground"
    assert CLASS_NAMES[index[1]] == "roof"
    assert CLASS_NAMES[index[2]] == "facade"
    assert vertices[7][2] == 10.0


def test_excess_delay_matches_image_theory_on_a_ground_plane() -> None:
    """Section 2.4. `Delta = l_K - u_e.(x_K - S)` must equal `2*h*sin(el)`."""
    height = 1.5
    tracer = make_tracer(PlaneGeometry(0.0), PEC_PERMITTIVITY, 0.0, rays=400_000, seed=8)
    result = tracer.trace(np.array([0.0, 0.0, height]), MODELS, ground_z_m=0.0)
    # Half the rays go straight up with zero excess path, half reflect. The
    # throughput weighted mean excess path is therefore half the mean of
    # 2*h*sin(el) over the downward hemisphere, which is 2*h*(1/2)/2 = h/2.
    expected_ns = 0.5 * height / 299_792_458.0 * 1e9
    assert result.mean_excess_delay_ns == pytest.approx(expected_ns, rel=0.02)
