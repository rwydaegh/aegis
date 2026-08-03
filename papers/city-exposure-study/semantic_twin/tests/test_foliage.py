"""Tests for the vegetation participating medium.

There are no vegetation measurements in this project and there will not be, so
every test here is either a transcription check against Recommendation
ITU-R P.833-10, a closed form limit, or an internal identity the recommendation
itself asserts. The delta-M test is the load bearing one: it shows the Monte
Carlo transport solver satisfies the same scaling equations (13) and (14) of the
recommendation use, which is what licenses reading the RET tables into a volume
renderer at all.
"""

import numpy as np
import pytest

from semantic_twin.foliage import (
    LEAF_THICKNESS_M,
    TABULATED_FREQUENCIES_GHZ,
    CanopyCanyonGeometry,
    FoliageMedium,
    FoliageTracer,
    canopy_boundary_reflectance,
    canopy_volume_fraction,
    delta_m_scaling,
    figure2_specific_attenuation_db_per_m,
    leaf_reflectance_ratio_db,
    ret_parameter_envelope,
    ret_parameters,
    sample_phase_function,
    slab_transmission,
)
from semantic_twin.propagation import PEC_PERMITTIVITY, PlaneGeometry, SbrTracer, TraceConfig
from semantic_twin.propagation.directions import MODELS

FIFTEEN_GHZ = 15.0e9


def test_tabulated_frequencies_are_the_two_disjoint_campaigns():
    assert TABULATED_FREQUENCIES_GHZ == (1.3, 1.5, 2.0, 2.2, 2.5, 3.5, 4.5, 5.5, 11.0, 12.5, 37.0, 61.5)


def test_no_table_row_exists_anywhere_in_fr2():
    """The gap the report has to state rather than paper over."""
    in_fr2 = [f for f in TABULATED_FREQUENCIES_GHZ if 24.25 <= f <= 29.5]
    assert in_fr2 == []
    in_upper_fr3 = [f for f in TABULATED_FREQUENCIES_GHZ if 14.8 <= f <= 15.35]
    assert in_upper_fr3 == []


def test_a_known_cell_transcribes_exactly():
    """London plane in leaf at 37 GHz, the only column above 12.5 GHz."""
    p = ret_parameters(37.0e9, species="london_plane", leaf_state="in_leaf")
    assert p.in_table
    assert p.alpha == pytest.approx(0.95)
    assert p.phase_beamwidth_deg == pytest.approx(18.0)
    assert p.albedo == pytest.approx(0.95)
    assert p.sigma_tau_per_m == pytest.approx(0.441)


def test_nearest_row_reports_its_own_distance():
    p = ret_parameters(28.0e9, species="london_plane", leaf_state="in_leaf")
    assert not p.in_table
    assert p.tabulated_frequency_ghz == 37.0
    assert p.frequency_gap_octaves == pytest.approx(np.log2(37.0 / 28.0), rel=1e-9)
    assert "nearest tabulated frequency" in p.provenance()["status"]


def test_nearest_is_taken_in_log_frequency_not_linear():
    """At 22 GHz the two metrics disagree, and the ratio metric is the right one.

    Linear in hertz, 11 GHz is 11 GHz away and 37 GHz is 15 GHz away, so a
    linear nearest neighbour would pick 11. By ratio, 37 GHz is 0.75 octaves
    away and 11 GHz is a full octave, so log picks 37. Dielectric and
    scattering behaviour move with the ratio, not the difference, so log is
    what this module uses.
    """
    p = ret_parameters(22.0e9, species="london_plane", leaf_state="in_leaf")
    assert p.tabulated_frequency_ghz == 37.0
    assert abs(37.0 - 22.0) > abs(22.0 - 11.0)


def test_sigma_tau_reads_as_nepers_per_metre():
    p = ret_parameters(11.0e9, species="london_plane", leaf_state="in_leaf")
    assert p.specific_attenuation_db_per_m == pytest.approx(0.750 * 8.6858896, rel=1e-6)


def test_the_recommendation_disagrees_with_itself_at_eleven_gigahertz():
    """Two P.833-10 models, one recommendation, a factor of three apart.

    Table 8 read as nepers per metre gives 6.5 dB/m for London plane in leaf at
    11 GHz. Figure 2, the recommendation's own specific attenuation curve for
    woodland, gives about 2.2 dB/m at the same frequency. Neither is wrong
    against the other because they were never reconciled, and that gap is the
    reason this study sweeps optical depth rather than quoting one.
    """
    table = ret_parameters(11.0e9, species="london_plane", leaf_state="in_leaf").specific_attenuation_db_per_m
    figure = float(figure2_specific_attenuation_db_per_m(11.0e9))
    assert table / figure > 2.5
    assert table / figure < 3.5


def test_parameter_envelope_spans_the_whole_species_disagreement():
    envelope = ret_parameter_envelope(FIFTEEN_GHZ)
    low, high = envelope["sigma_tau_per_m"]
    assert high / low > 5.0
    assert envelope["albedo"][0] < 0.5
    assert envelope["albedo"][1] > 0.95


# Delta-M, the identity of Recommendation ITU-R P.833-10 equations (13) and (14).


def test_delta_m_scaling_matches_the_recommendation_algebra():
    scale, reduced_albedo = delta_m_scaling(0.7, 0.95)
    assert scale == pytest.approx(1.0 - 0.7 * 0.95)
    assert reduced_albedo == pytest.approx(0.3 * 0.95 / (1.0 - 0.7 * 0.95))


def test_delta_m_conserves_the_absorption_optical_depth():
    """``tau_hat (1 - W_hat)`` must equal ``tau (1 - W)``.

    Forward scattering does not absorb, so removing it from the transport must
    leave the absorption optical depth untouched. This is the algebraic check
    that the recommendation's two scalings are consistent with each other.
    """
    for alpha in (0.0, 0.25, 0.7, 0.95):
        for albedo in (0.1, 0.5, 0.9, 0.99):
            scale, reduced = delta_m_scaling(alpha, albedo)
            assert scale * (1.0 - reduced) == pytest.approx(1.0 - albedo, rel=1e-12)


def test_medium_reduced_agrees_with_the_scaling_function():
    medium = FoliageMedium(extinction_per_m=0.5, albedo=0.9, forward_fraction=0.8, phase_beamwidth_deg=20.0)
    scale, reduced_albedo = delta_m_scaling(0.8, 0.9)
    got = medium.reduced()
    assert got.extinction_per_m == pytest.approx(0.5 * scale)
    assert got.albedo == pytest.approx(reduced_albedo)
    assert got.forward_fraction == 0.0


@pytest.mark.parametrize("beamwidth", [2.0, 8.0])
def test_monte_carlo_obeys_the_delta_m_identity(beamwidth):
    """The narrow forward lobe and its delta-M equivalent give the same answer.

    This is the strongest validation available without measurements. The
    recommendation exposes ``alpha`` and ``beta`` but never writes the phase
    function down, so the Gaussian lobe used in :func:`sample_phase_function` is
    an interpolation. If the escaping power is invariant under the scaling the
    recommendation itself applies, the choice of lobe shape does not matter and
    the interpolation is safe.
    """
    geometry = CanopyCanyonGeometry(
        street_width_m=60.0,
        street_length_m=200.0,
        facade_height_m=6.0,
        canopy_half_width_m=8.0,
        canopy_base_m=4.0,
        canopy_depth_m=6.0,
    )
    permittivity = np.array([complex(3.66, -0.09)] * 4)
    rms = np.full(4, 4.5e-4)
    medium = FoliageMedium(extinction_per_m=0.6, albedo=0.9, forward_fraction=0.85, phase_beamwidth_deg=beamwidth)
    models = {"isotropic": MODELS["isotropic"]}
    origin = np.array([0.0, 0.0, 1.5])

    full = FoliageTracer(
        geometry,
        permittivity=permittivity,
        rms_height_m=rms,
        frequency_hz=FIFTEEN_GHZ,
        medium=medium,
        rays=120_000,
        seed=5,
    ).trace(origin, models)
    scaled = FoliageTracer(
        geometry,
        permittivity=permittivity,
        rms_height_m=rms,
        frequency_hz=FIFTEEN_GHZ,
        medium=medium.reduced(),
        rays=120_000,
        seed=11,
    ).trace(origin, models)
    assert full.susceptibility["isotropic"] == pytest.approx(scaled.susceptibility["isotropic"], rel=0.03)


# Closed form limits of the transport.


def _slab_scene(canopy_depth_m: float) -> CanopyCanyonGeometry:
    """A canopy slab covering the whole sky and nothing else in the scene.

    The street is made a micron wide so its ground has no area, the facades are
    given zero height, and the canopy box is made ten kilometres across. What
    is left is one horizontal absorbing slab over an otherwise empty sphere,
    which has a closed form.
    """
    return CanopyCanyonGeometry(
        street_width_m=1.0e-6,
        street_length_m=1.0e5,
        facade_height_m=0.0,
        canopy_half_width_m=1.0e5,
        canopy_base_m=4.0,
        canopy_depth_m=canopy_depth_m,
    )


def _slab_susceptibility(medium: FoliageMedium | None, depth_m: float, *, rays: int = 400_000, seed: int = 2) -> float:
    return (
        FoliageTracer(
            _slab_scene(depth_m),
            permittivity=np.array([PEC_PERMITTIVITY] * 4),
            rms_height_m=np.zeros(4),
            frequency_hz=FIFTEEN_GHZ,
            medium=medium,
            rays=rays,
            seed=seed,
        )
        .trace(np.array([0.0, 0.0, 1.5]), {"isotropic": MODELS["isotropic"]})
        .susceptibility["isotropic"]
    )


@pytest.mark.parametrize("tau", [0.25, 1.0, 3.0])
def test_absorbing_slab_reproduces_the_exponential_integral(tau):
    """The exact Beer-Lambert answer for an absorbing slab over an empty sphere.

    Directions sampled uniformly on the sphere have ``mu = cos(theta)`` uniform
    on ``(0, 1]`` in the upper hemisphere, and the chord through a horizontal
    slab of depth ``d`` is ``d / mu``, so with zero albedo

        ``chi = 1/2 + 1/2 * integral_0^1 exp(-tau / mu) dmu = 1/2 + 1/2 E_2(tau)``

    with ``E_2`` the second exponential integral. That is a non trivial angle
    dependent target, and it fails if the chord length, the boundary crossing
    or the free flight sampling is wrong in any way. Beer-Lambert on a single
    normal ray would pass all three broken.
    """
    from scipy.special import expn

    depth = 6.0
    medium = FoliageMedium(extinction_per_m=tau / depth, albedo=0.0, forward_fraction=0.0, phase_beamwidth_deg=180.0)
    expected = 0.5 + 0.5 * float(expn(2, tau))
    assert _slab_susceptibility(medium, depth) == pytest.approx(expected, rel=0.01)


def test_slab_transmission_is_the_beer_lambert_helper():
    for tau in (0.5, 1.0, 2.0):
        medium = FoliageMedium(extinction_per_m=tau / 6.0, albedo=0.0, forward_fraction=0.0, phase_beamwidth_deg=180.0)
        assert slab_transmission(medium, 6.0) == pytest.approx(np.exp(-tau))


def test_transparent_medium_is_invisible():
    """Zero extinction must leave the scene exactly as if the canopy were cut.

    This is the test that catches a spurious reflection at the canopy hull, and
    it is the property that distinguishes a medium boundary from a surface.
    """
    clear = FoliageMedium(extinction_per_m=0.0, albedo=0.9, forward_fraction=0.8, phase_beamwidth_deg=30.0)
    assert _slab_susceptibility(clear, 6.0) == pytest.approx(1.0, rel=1e-6)


def test_black_canopy_removes_exactly_the_solid_angle_it_covers():
    """A fully absorbing finite canopy costs the isotropic susceptibility its share.

    With albedo zero and a large optical depth every ray entering the canopy
    dies, so the isotropic susceptibility of an otherwise empty scene must fall
    by the canopy solid angle fraction and nothing else. This catches a
    boundary crossing bug, a double counted face, or a sign error in the inside
    flag, none of which the delta-M test can see.
    """
    permittivity = np.array([PEC_PERMITTIVITY] * 4)
    rms = np.zeros(4)
    models = {"isotropic": MODELS["isotropic"]}
    origin = np.array([0.0, 0.0, 1.5])
    empty = CanopyCanyonGeometry(
        street_width_m=1.0e-6, street_length_m=1.0e3, facade_height_m=0.0, canopy_half_width_m=0.0
    )
    shaded_scene = CanopyCanyonGeometry(
        street_width_m=1.0e-6,
        street_length_m=1.0e3,
        facade_height_m=0.0,
        canopy_half_width_m=6.0,
        canopy_base_m=4.0,
        canopy_depth_m=6.0,
    )
    black = FoliageMedium(extinction_per_m=8.0, albedo=0.0, forward_fraction=0.0, phase_beamwidth_deg=180.0)
    reference = FoliageTracer(
        empty, permittivity=permittivity, rms_height_m=rms, frequency_hz=FIFTEEN_GHZ, rays=200_000, seed=3
    ).trace(origin, models)
    shaded = FoliageTracer(
        shaded_scene,
        permittivity=permittivity,
        rms_height_m=rms,
        frequency_hz=FIFTEEN_GHZ,
        medium=black,
        rays=200_000,
        seed=3,
    ).trace(origin, models)
    assert reference.susceptibility["isotropic"] == pytest.approx(1.0, rel=1e-6)
    lost = reference.susceptibility["isotropic"] - shaded.susceptibility["isotropic"]
    assert lost == pytest.approx(shaded.canopy_solid_angle_fraction, rel=0.03)


def test_estimator_reproduces_the_ground_plane_closed_form():
    """PEC ground under a rooftop illumination must give exactly two.

    Same target as MONOSTATIC_SBR.md section 11.1. This module runs its own
    estimator rather than editing the shared tracer, so the shared tracer's
    validation has to be re-earned here rather than assumed.
    """
    geometry = CanopyCanyonGeometry(
        street_width_m=1.0e7, street_length_m=1.0e7, facade_height_m=0.0, canopy_half_width_m=0.0
    )
    result = FoliageTracer(
        geometry,
        permittivity=np.array([PEC_PERMITTIVITY] * 4),
        rms_height_m=np.zeros(4),
        frequency_hz=FIFTEEN_GHZ,
        rays=200_000,
        seed=7,
    ).trace(np.array([0.0, 0.0, 1.5]), {"rooftop": MODELS["rooftop"]})
    assert result.susceptibility["rooftop"] == pytest.approx(2.0, rel=0.02)


def test_estimator_agrees_with_the_shared_sbr_tracer():
    """Two independent estimators, one dielectric ground plane, same number."""
    permittivity = complex(5.24, -0.30)
    geometry = CanopyCanyonGeometry(
        street_width_m=1.0e7, street_length_m=1.0e7, facade_height_m=0.0, canopy_half_width_m=0.0
    )
    mine = FoliageTracer(
        geometry,
        permittivity=np.array([permittivity] * 4),
        rms_height_m=np.zeros(4),
        frequency_hz=FIFTEEN_GHZ,
        rays=200_000,
        seed=3,
    ).trace(np.array([0.0, 0.0, 1.5]), {"rooftop": MODELS["rooftop"]})
    theirs = SbrTracer(
        PlaneGeometry(0.0),
        None,
        np.array([permittivity]),
        np.zeros(1),
        TraceConfig(frequency_hz=FIFTEEN_GHZ, rays=200_000, seed=3),
    ).trace(np.array([0.0, 0.0, 1.5]), {"rooftop": MODELS["rooftop"]})
    assert mine.susceptibility["rooftop"] == pytest.approx(theirs.susceptibility["rooftop"], rel=0.02)


def test_free_space_susceptibility_is_one():
    geometry = CanopyCanyonGeometry(
        street_width_m=1.0e6, street_length_m=1.0e-6, facade_height_m=0.0, canopy_half_width_m=0.0
    )
    result = FoliageTracer(
        geometry,
        permittivity=np.array([PEC_PERMITTIVITY] * 4),
        rms_height_m=np.zeros(4),
        frequency_hz=FIFTEEN_GHZ,
        rays=60_000,
        seed=1,
    ).trace(np.array([0.0, 0.0, 1.5]), {"isotropic": MODELS["isotropic"]})
    assert result.susceptibility["isotropic"] == pytest.approx(1.0, rel=1e-6)


# The two derived facts that decide the treatment.


def test_phase_function_forward_lobe_is_narrow_and_the_rest_is_isotropic():
    rng = np.random.default_rng(0)
    incoming = np.tile(np.array([0.0, 0.0, 1.0]), (200_000, 1))
    medium = FoliageMedium(extinction_per_m=1.0, albedo=0.9, forward_fraction=0.8, phase_beamwidth_deg=20.0)
    out = sample_phase_function(incoming, medium, rng)
    cosine = out[:, 2]
    # The isotropic 20% is uniform in cosine, so the backward hemisphere holds
    # half of it and nothing else.
    assert np.mean(cosine < 0.0) == pytest.approx(0.5 * 0.2, abs=0.01)
    # The forward lobe keeps its power within a few beamwidths.
    assert np.mean(cosine > np.cos(np.radians(30.0))) > 0.75


def test_canopy_has_no_dielectric_boundary():
    """Maxwell Garnett on the leaf volume fraction the recommendation implies.

    LAI and leaf thickness both come from Recommendation ITU-R P.833-10, Tables
    4 and 9, so the volume fraction is derived and not fitted. The interface
    reflectance that follows is around 1e-9, which is why the medium treatment
    puts no Fresnel surface on the canopy hull and why the wood substitution
    the pipeline uses today is the single largest error in the surface
    treatment.
    """
    result = canopy_boundary_reflectance(1.93, 6.0)
    assert result["volume_fraction"] < 1.0e-3
    assert result["normal_incidence_reflectance"] < 1.0e-7
    assert result["excess_of_wood_substitution_db"] > 60.0


def test_canopy_volume_fraction_is_lai_times_thickness_over_depth():
    assert canopy_volume_fraction(2.0, 5.0, 0.0002) == pytest.approx(2.0 * 0.0002 / 5.0)
    with pytest.raises(ValueError):
        canopy_volume_fraction(2.0, 0.0)


@pytest.mark.parametrize("frequency_hz", [7.0e9, 15.0e9, 28.0e9])
def test_a_leaf_is_not_a_half_space(frequency_hz):
    """A half space Fresnel model over-reflects a 0.2 mm leaf.

    This is the quantitative reason explicit procedural leaf geometry would be
    worse than the blob, not better: the tracer's only surface response is a
    half space reflectance, and applying it to leaf sized facets over-reports
    the reflected power while costing far more rays than a canopy can afford.
    """
    result = leaf_reflectance_ratio_db(frequency_hz, np.array([0.0, 30.0, 60.0, 80.0]))
    assert np.all(result["electrical_thickness_rad"] < 0.5)
    assert np.all(result["slab_reflectance"] < result["half_space_reflectance"])
    assert np.max(result["excess_db"]) > 3.0


def test_leaf_slab_approaches_the_half_space_when_it_is_thick():
    """Sanity on the slab formula: many wavelengths thick and the excess vanishes."""
    thick = leaf_reflectance_ratio_db(15.0e9, 40.0, thickness_m=0.5)
    assert float(thick["excess_db"]) == pytest.approx(0.0, abs=0.5)
    thin = leaf_reflectance_ratio_db(15.0e9, 40.0, thickness_m=LEAF_THICKNESS_M)
    assert float(thin["excess_db"]) > float(thick["excess_db"])


def test_figure_two_curve_matches_the_published_twenty_eight_gigahertz_readback():
    """Zhang et al. 2019 quote gamma of about 6 dB/m at 28 GHz from P.833-9.

    IEEE Wireless Communications Letters, DOI 10.1109/LWC.2019.2899299,
    section III-B. That is an independent digitisation of the same figure, so
    it bounds how wrong the fit used here can be.
    """
    assert float(figure2_specific_attenuation_db_per_m(28.0e9)) == pytest.approx(6.0, rel=0.15)


def test_medium_rejects_impossible_parameters():
    with pytest.raises(ValueError):
        FoliageMedium(extinction_per_m=-1.0, albedo=0.5, forward_fraction=0.5, phase_beamwidth_deg=10.0)
    with pytest.raises(ValueError):
        FoliageMedium(extinction_per_m=1.0, albedo=1.5, forward_fraction=0.5, phase_beamwidth_deg=10.0)
    with pytest.raises(ValueError):
        FoliageMedium(extinction_per_m=1.0, albedo=0.5, forward_fraction=0.5, phase_beamwidth_deg=0.0)
    with pytest.raises(ValueError):
        delta_m_scaling(1.0, 1.0)


def test_a_canopy_cannot_be_a_medium_and_a_surface_at_once():
    geometry = CanopyCanyonGeometry(canopy_half_width_m=2.0)
    with pytest.raises(ValueError):
        FoliageTracer(
            geometry,
            permittivity=np.array([complex(2.0, -0.1)] * 4),
            rms_height_m=np.zeros(4),
            frequency_hz=FIFTEEN_GHZ,
            medium=FoliageMedium(extinction_per_m=0.5, albedo=0.9, forward_fraction=0.5, phase_beamwidth_deg=30.0),
            canopy_is_surface=True,
        )
