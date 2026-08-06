"""What a label is worth, and whether it can refuse to say.

The failure this layer already had was silence rather than error. A material
read off a camera driven inside a building and a material read off the
orientation of a triangle arrived downstream looking the same, so most of what
is pinned here is a refusal: evidence that will not exist without naming what
saw it, a pose that scores zero rather than small, an unrecorded diagnostic that
reads unknown rather than clean.

The real data half runs on the 83 ``pose_aligned.json`` files in the repository.
It needs no mesh and no network.
"""

from __future__ import annotations

import numpy as np
import pytest

from semantic_twin import sites
from semantic_twin.vision.evidence import EvidenceAccumulator, ObservationQuality, SoftAssociation
from semantic_twin.vision.provenance import (
    ADAPTIVE_TILES,
    FACE_CENTROID,
    NO_IMAGE,
    NO_PROJECTION,
    PANORAMA_ENTITY,
    PANORAMA_MATERIAL,
    TILE_TEXTURE,
    AdmissionGate,
    EvidenceOrigin,
    Registration,
    ViewProvenance,
    station_registrations,
    survey,
    survey_site,
)

GATE = AdmissionGate()


def pose(
    residual: float = 1.0,
    *,
    sky_hit: float | None = 0.0,
    conflict_range: float | None = 40.0,
    sigma: float = 0.2,
    dz_at_bound: bool | None = False,
) -> dict:
    """A ``pose_aligned.json`` document with the four fields that decide a verdict."""
    document: dict = {
        "skyline_score_mean_deg": residual,
        "pose_uncertainty": {"covariance": np.diag([sigma**2 / 2, sigma**2 / 2, 0.1, 0.1, 0.1, 0.1]).tolist()},
    }
    if dz_at_bound is not None:
        document["skyline_dz_at_bound"] = dz_at_bound
    if sky_hit is not None:
        document["sky_conflict"] = {
            "sky_with_mesh_hit_fraction": sky_hit,
            "conflict_median_range_m": conflict_range,
        }
    return document


def look(residual: float = 1.0, **kwargs) -> ViewProvenance:
    return ViewProvenance(
        site="korenmarkt",
        station="493993666",
        provider=sites.MAPILLARY,
        registration=Registration.from_pose(pose(residual, **kwargs)),
    )


# Evidence that refuses to exist without provenance.


def test_camera_evidence_cannot_exist_without_naming_a_look() -> None:
    with pytest.raises(ValueError, match="must name at least one look"):
        EvidenceOrigin(channel=PANORAMA_ENTITY, projection=ADAPTIVE_TILES)
    with pytest.raises(ValueError, match="must name at least one look"):
        EvidenceOrigin(channel=PANORAMA_MATERIAL, projection=FACE_CENTROID, views=())


def test_evidence_cannot_invent_a_channel_or_a_projection_rule() -> None:
    with pytest.raises(ValueError, match="unknown evidence channel"):
        EvidenceOrigin(channel="vibes", projection=ADAPTIVE_TILES, views=(look(),))
    with pytest.raises(ValueError, match="unknown projection rule"):
        EvidenceOrigin(channel=PANORAMA_ENTITY, projection="somehow", views=(look(),))


def test_a_surface_no_photograph_reached_says_so_instead_of_going_missing() -> None:
    """The eleven city headline is entirely this case, so it needs a name."""
    origin = EvidenceOrigin.none()
    assert origin.channel == NO_IMAGE
    assert origin.projection == NO_PROJECTION
    assert origin.views == ()
    assert origin.worst_registration(GATE) == 0.0


def test_evidence_from_no_image_cannot_claim_a_look_or_a_projection() -> None:
    with pytest.raises(ValueError, match="cannot name a look"):
        EvidenceOrigin(channel=NO_IMAGE, projection=NO_PROJECTION, views=(look(),))
    with pytest.raises(ValueError, match="never projected"):
        EvidenceOrigin(channel=NO_IMAGE, projection=ADAPTIVE_TILES)


def test_the_tile_texture_channel_needs_no_camera_but_still_needs_a_rule() -> None:
    """Tile texture is baked into the photogrammetry, so it has no pose."""
    origin = EvidenceOrigin(channel=TILE_TEXTURE, projection="tile_uv")
    assert origin.views == ()
    with pytest.raises(ValueError, match="unknown projection rule"):
        EvidenceOrigin(channel=TILE_TEXTURE, projection="uv")


def test_a_look_must_name_a_provider_the_study_actually_used() -> None:
    with pytest.raises(ValueError, match="unknown imagery provider"):
        ViewProvenance(site="korenmarkt", station="1", provider="bing", registration=Registration.unregistered())
    with pytest.raises(ValueError, match="site and the camera"):
        ViewProvenance(site="", station="1", provider=sites.MAPILLARY, registration=Registration.unregistered())


# What a pose is worth.


def test_a_pose_inside_a_building_is_worth_nothing_rather_than_a_little() -> None:
    """A camera in a wall is not weak evidence about the wall. It is evidence about nothing."""
    inside = Registration.from_pose(pose(0.4, sky_hit=0.97, conflict_range=0.6))
    verdict = inside.verdict(GATE)
    assert not verdict.admitted
    assert verdict.inside_geometry
    assert inside.quality(GATE) == 0.0
    # The residual alone would have called this the best pose in the study.
    assert inside.residual_deg < Registration.from_pose(pose(1.0)).residual_deg


def test_the_sky_test_refuses_a_pose_the_residual_admits() -> None:
    """The two admission tests are not redundant, which is the whole reason for the second."""
    residual_only = Registration.from_pose(pose(0.4, sky_hit=0.0))
    both = Registration.from_pose(pose(0.4, sky_hit=0.97, conflict_range=0.6))
    assert residual_only.verdict(GATE).admitted
    assert not both.verdict(GATE).admitted
    assert "inside a building" in " ".join(both.verdict(GATE).reasons)


def test_a_distant_sky_conflict_is_not_a_camera_inside_a_building() -> None:
    """Sky seen through an arcade hits the mesh far away and is not a fault."""
    far = Registration.from_pose(pose(1.0, sky_hit=0.9, conflict_range=60.0))
    assert far.verdict(GATE).sky_conflict_state == "large sky-mesh mismatch"
    assert far.verdict(GATE).admitted
    assert far.quality(GATE) > 0.0


def test_an_unrecorded_sky_conflict_fails_closed() -> None:
    silent = Registration.from_pose(pose(0.0, sky_hit=None))
    clean = Registration.from_pose(pose(0.0, sky_hit=0.0))
    assert silent.sky_conflict is None
    assert silent.verdict(GATE).sky_conflict_state == "unknown"
    assert clean.verdict(GATE).sky_conflict_state == "clear"
    assert not silent.verdict(GATE).admitted
    assert silent.quality(GATE) < clean.quality(GATE)


@pytest.mark.parametrize(
    ("fraction", "distance", "state", "admitted"),
    [
        (0.5, 1.999, "clear", True),
        (0.500001, 1.999, "inside the geometry", False),
        (0.500001, 2.0, "large sky-mesh mismatch", True),
        (0.9, 60.0, "large sky-mesh mismatch", True),
        (0.9997, 4.95, "large sky-mesh mismatch", True),
    ],
)
def test_paired_sky_rule_truth_table(
    fraction: float,
    distance: float,
    state: str,
    admitted: bool,
) -> None:
    verdict = Registration.from_pose(pose(sky_hit=fraction, conflict_range=distance)).verdict(GATE)
    assert verdict.sky_conflict_state == state
    assert verdict.admitted is admitted


def test_a_good_residual_at_the_vertical_bound_is_refused() -> None:
    registration = Registration.from_pose(pose(0.2, dz_at_bound=True))
    verdict = registration.verdict(GATE)
    assert not verdict.admitted
    assert "altitude search bound" in " ".join(verdict.reasons)


def test_missing_boundary_status_fails_closed() -> None:
    verdict = Registration.from_pose(pose(dz_at_bound=None)).verdict(GATE)
    assert not verdict.admitted
    assert "missing skyline_dz_at_bound" in " ".join(verdict.reasons)


def test_gate_policy_is_versioned_in_full() -> None:
    assert GATE.as_dict() == {
        "version": "registration-admission-v2",
        "max_residual_deg": 4.0,
        "max_sky_conflict": 0.5,
        "min_conflict_range_m": 2.0,
        "require_complete_sky_diagnostics": True,
        "require_interior_optimum": True,
        "inside_geometry_rule": (
            "sky_with_mesh_hit_fraction > max_sky_conflict AND conflict_median_range_m < min_conflict_range_m"
        ),
    }


def test_legacy_gate_is_named_and_keeps_sealed_v1_boundary_policy() -> None:
    registration = Registration.from_pose(pose(0.2, dz_at_bound=True))
    gate = AdmissionGate.legacy_v1()
    assert gate.version == "registration-admission-v1"
    assert registration.verdict(gate).admitted
    assert not gate.require_complete_sky_diagnostics
    assert not gate.require_interior_optimum


def test_quality_falls_off_with_the_residual_inside_the_gate() -> None:
    ladder = [Registration.from_pose(pose(r)).quality(GATE) for r in (0.5, 1.5, 3.0, 3.9)]
    assert ladder == sorted(ladder, reverse=True)
    assert all(0.0 < value <= 1.0 for value in ladder)


def test_an_unregistered_look_is_not_the_same_as_a_badly_registered_one() -> None:
    blank = Registration.unregistered()
    assert blank.residual_deg is None
    assert blank.sky_conflict is None
    assert not blank.verdict(GATE).admitted


def test_a_registration_refuses_numbers_that_cannot_be_measurements() -> None:
    with pytest.raises(ValueError, match="fraction of directions"):
        Registration(sky_conflict=1.4)
    with pytest.raises(ValueError, match="finite non-negative"):
        Registration(residual_deg=-1.0)
    with pytest.raises(ValueError, match="finite non-negative"):
        Registration(position_sigma_m=float("nan"))


def test_a_gate_has_to_be_a_gate() -> None:
    with pytest.raises(ValueError):
        AdmissionGate(max_residual_deg=0.0)
    with pytest.raises(ValueError):
        AdmissionGate(max_sky_conflict=1.5)


# Fusion has to prefer the better registered view, and say why.


def test_a_fused_label_inherits_its_worst_pose_and_names_it() -> None:
    good = look(0.4)
    bad = look(0.4, sky_hit=0.97, conflict_range=0.6)
    origin = EvidenceOrigin(channel=PANORAMA_MATERIAL, projection=ADAPTIVE_TILES, views=(good, bad))
    quality = origin.registration_quality(GATE)
    assert quality[0] > 0.0
    assert quality[1] == 0.0
    assert origin.worst_registration(GATE) == 0.0
    # Saying why is the point. The bad look is identifiable, not just counted.
    worst = origin.views[int(np.argmin(quality))]
    assert worst.registration.verdict(GATE).inside_geometry
    assert worst.identifier in origin.as_dict()["looks"][1]["site"] + "/" + origin.as_dict()["looks"][1]["station"]


def test_the_accumulator_follows_the_better_registered_of_two_disagreeing_views() -> None:
    """``ObservationQuality.registration`` is the slot ``Registration.quality`` fills.

    Two cameras see the same triangle and disagree. One is admitted, one sits
    inside a building. Feeding the pose quality into the slot that has existed
    since the accumulator was written makes the posterior follow the good camera
    instead of splitting the difference.
    """
    good = Registration.from_pose(pose(0.2))
    bad = Registration.from_pose(pose(0.2, sky_hit=0.97, conflict_range=0.6))
    registration = np.array([good.quality(GATE), bad.quality(GATE)], dtype=np.float64)
    assert registration[0] > 0.0 and registration[1] == 0.0

    accumulator = EvidenceAccumulator(1, ["brick", "glass"], ["masonry"], ["wet"])
    ones = np.ones(2, dtype=np.float64)
    accumulator.update(
        SoftAssociation(np.zeros((2, 1), dtype=np.int64), np.ones((2, 1))),
        ObservationQuality(registration, ones, ones, ones, ones, ones),
        entity_probability=np.array([[1.0, 0.0], [0.0, 1.0]]),
        material_probability=np.ones((2, 1)),
        attribute_probability=np.array([[1.0], [0.0]]),
    )
    posterior = accumulator.entity_posterior()[0]
    assert posterior[0] > posterior[1]
    # With both cameras trusted equally the same batch says nothing at all.
    even = EvidenceAccumulator(1, ["brick", "glass"], ["masonry"], ["wet"])
    even.update(
        SoftAssociation(np.zeros((2, 1), dtype=np.int64), np.ones((2, 1))),
        ObservationQuality(ones, ones, ones, ones, ones, ones),
        entity_probability=np.array([[1.0, 0.0], [0.0, 1.0]]),
        material_probability=np.ones((2, 1)),
        attribute_probability=np.array([[1.0], [0.0]]),
    )
    assert even.entity_posterior()[0] == pytest.approx([0.5, 0.5])


# The 83 poses on disk.


@pytest.mark.local_data
def test_every_pose_in_the_repository_reads_as_a_registration() -> None:
    survey_all = survey(gate=GATE)
    assert sum(report.registered for report in survey_all.values()) == 83


@pytest.mark.local_data
def test_the_survey_counts_the_cameras_that_are_actually_usable() -> None:
    """Three numbers, and the study's evidence lists were written against the middle one."""
    reports = survey(gate=GATE).values()
    on_disk = sum(report.stations for report in reports)
    posed = sum(report.registered for report in reports)
    admitted = sum(report.admitted for report in reports)
    assert (on_disk, posed, admitted) == (112, 83, 39)
    assert admitted < posed < on_disk


def test_the_two_refusal_reasons_partition_the_refused_poses() -> None:
    for report in survey(gate=GATE).values():
        refused = report.registered - report.admitted
        assert refused == report.inside_geometry + report.refused_on_residual


@pytest.mark.local_data
def test_a_site_with_photographs_and_no_pose_at_all_is_visible() -> None:
    """London has 14 panoramas on disk and not one of them is registered."""
    london = survey_site(sites.Site.get("london_trafalgar"), gate=GATE)
    assert london.stations == 14
    assert london.registered == 0
    assert london.admitted == 0
    assert london.usable_fraction == 0.0


@pytest.mark.local_data
def test_a_stricter_gate_never_admits_more_cameras() -> None:
    loose = survey(gate=AdmissionGate(max_residual_deg=8.0))
    strict = survey(gate=AdmissionGate(max_residual_deg=2.0))
    for name, report in strict.items():
        assert report.admitted <= loose[name].admitted
    assert sum(r.admitted for r in strict.values()) < sum(r.admitted for r in loose.values())


def test_no_pose_on_disk_carries_an_unrecorded_sky_conflict() -> None:
    """Every registered pose has been backfilled, so unknown is a live state with no live case."""
    assert sum(report.unknown_conflict for report in survey(gate=GATE).values()) == 0


@pytest.mark.local_data
def test_korenmarkt_v1_to_v2_camera_delta_is_only_the_boundary_gate() -> None:
    registrations = station_registrations(sites.Site.get("korenmarkt"), roles=("stations", "walk"))
    v1 = {
        name for name, registration in registrations.items() if registration.verdict(AdmissionGate.legacy_v1()).admitted
    }
    v2 = {name for name, registration in registrations.items() if registration.verdict(GATE).admitted}

    assert v1 == {
        "korenmarkt",
        "walk_00_986493819697753",
        "walk_01_1304023184185511",
        "walk_02_582445657694750",
        "walk_03_706535575184668",
        "walk_05_1084407470281938",
        "walk_06_1419513849204492",
        "walk_08_1019442960256615",
        "walk_10_3367014310197013",
    }
    assert v2 == {
        "walk_00_986493819697753",
        "walk_01_1304023184185511",
        "walk_02_582445657694750",
        "walk_05_1084407470281938",
    }
    removed = v1 - v2
    assert all(registrations[name].dz_at_bound for name in removed)
