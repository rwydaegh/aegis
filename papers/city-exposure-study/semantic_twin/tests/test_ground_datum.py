"""What the ground datum has to survive, on synthetic layouts and on the crops.

The estimator this pins replaced one that put the pedestrian on the roof of the
Sukiennice at Krakow and on the Capitole at Toulouse. Each synthetic case below
is one of the layouts that broke it, or one that would break an obvious
alternative to it. GROUND_DATUM.md carries the measurements.
"""

from __future__ import annotations

import json
import pathlib

import numpy as np
import pytest

from semantic_twin.propagation.walk import (
    SKY_PROBE,
    build_walk,
    ground_datum,
    ground_height,
    measure_ground_datum,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
GEOMETRY = ROOT / "data" / "geometry"
CONFIG = ROOT / "config"

#: config/korenmarkt.json camera_ground_z_m, solved by the panorama registration
#: and independent of every mesh statistic.
KORENMARKT_REGISTERED_Z_M = 50.83747424667166


class Slabs:
    """Horizontal rectangular patches, intersected analytically.

    Enough geometry to state a layout: a patch is a height and an xy rectangle,
    and a downward ray reports the highest patch below its origin. Walls are
    absent on purpose, because the datum only ever looks at what is under a
    column, and a mesh loader in a unit test would hide the layout being tested.
    """

    def __init__(self, patches: list[tuple[float, tuple[float, float, float, float]]]) -> None:
        self.patches = patches

    def intersect(self, origins, directions):  # noqa: ANN001, ANN201
        count = origins.shape[0]
        best = np.full(count, -np.inf)
        for z, (x0, x1, y0, y1) in self.patches:
            inside = (origins[:, 0] >= x0) & (origins[:, 0] <= x1) & (origins[:, 1] >= y0) & (origins[:, 1] <= y1)
            below = inside & (z <= origins[:, 2]) & (directions[:, 2] < 0.0)
            best = np.where(below & (z > best), z, best)
        hit = np.isfinite(best)
        distance = np.where(hit, origins[:, 2] - best, 1.0e30)
        normal = np.tile(np.array([0.0, 0.0, 1.0]), (count, 1))
        return hit, distance, normal, np.zeros(count, dtype=np.int64)


WIDE = (-500.0, 500.0, -500.0, 500.0)


def test_a_flat_square_returns_its_own_height() -> None:
    datum = ground_datum(Slabs([(7.25, WIDE)]), radius_m=60.0)
    assert datum == pytest.approx(7.25, abs=0.05)


def test_a_monument_at_the_centre_does_not_become_the_datum() -> None:
    """Krakow. A 15 m disc at the origin sees only the Sukiennice roof."""
    layout = Slabs([(0.0, WIDE), (18.5, (-55.0, 55.0, -18.0, 18.0))])
    assert ground_datum(layout, radius_m=15.0) == pytest.approx(18.5, abs=0.05), "the failure being fixed"
    assert ground_datum(layout, radius_m=90.0) == pytest.approx(0.0, abs=0.05)


def test_a_basement_below_the_whole_crop_is_invisible_to_the_datum() -> None:
    """The tile provider leaves car park shells under the street.

    A minimum or a low quantile over the mesh would land on the slab at -9 m.
    A downward first hit never reaches it, because the pavement is in the way.
    """
    layout = Slabs([(0.0, WIDE), (-9.0, WIDE)])
    assert ground_datum(layout, radius_m=60.0) == pytest.approx(0.0, abs=0.05)


def test_the_ground_wins_even_where_roofs_outnumber_it() -> None:
    """The Zocalo between 50 and 70 m: more roof in the disc than pavement.

    Pedestrians are on the lowest major surface and never on the second one, so
    a roof that merely outnumbers the ground must not take the datum.
    """
    layout = Slabs([(0.0, WIDE), (9.0, (-90.0, 10.0, -90.0, 90.0))])
    measured = measure_ground_datum(layout, radius_m=90.0)
    assert measured.busiest_z_m == pytest.approx(9.0, abs=0.05), "the roof is genuinely the busier level"
    assert measured.z_m == pytest.approx(0.0, abs=0.05)


def test_a_minor_lower_street_does_not_pull_the_datum_off_the_square() -> None:
    """Madrid. Cava de San Miguel runs five metres below the plaza floor.

    The plaza is the walkable surface of the site and the lower street is a
    sliver of the crop, so the datum has to stay on the plaza. This is the case
    that stops the rule from being "the lowest surface anywhere".
    """
    layout = Slabs([(0.0, WIDE), (-5.0, (-500.0, -75.0, -500.0, 500.0))])
    measured = measure_ground_datum(layout, radius_m=90.0)
    assert measured.z_m == pytest.approx(0.0, abs=0.05)


def test_the_answer_does_not_move_with_the_disc_radius() -> None:
    layout = Slabs([(3.0, WIDE), (21.0, (-45.0, 45.0, -20.0, 20.0)), (-6.0, WIDE)])
    found = [ground_datum(layout, radius_m=float(r)) for r in (40, 60, 90, 120)]
    assert max(found) - min(found) < 0.1
    assert found[0] == pytest.approx(3.0, abs=0.05)


def test_the_majority_ratio_only_bites_when_a_roof_outnumbers_the_ground() -> None:
    """Where the ground is the busiest level, which is the operating case, the ratio is inert.

    Where a roof outnumbers the ground the ratio is the whole rule, and at 1.0 it
    switches off and hands the datum to the roof. So the value is a real choice,
    and the case that fixes it is the Zocalo rather than a preference.
    """
    ordinary = Slabs([(0.0, WIDE), (14.0, (-40.0, 40.0, -40.0, 40.0))])
    found = [ground_datum(ordinary, radius_m=90.0, major_level_ratio=r) for r in (0.2, 0.5, 0.9, 1.0)]
    assert max(found) - min(found) < 1.0e-6

    roof_heavy = Slabs([(0.0, WIDE), (14.0, (-70.0, 20.0, -90.0, 90.0))])
    assert ground_datum(roof_heavy, radius_m=90.0, major_level_ratio=0.5) == pytest.approx(0.0, abs=0.05)
    assert ground_datum(roof_heavy, radius_m=90.0, major_level_ratio=1.0) == pytest.approx(14.0, abs=0.05)


def test_a_sloping_surface_settles_on_its_median() -> None:
    class Ramp:
        def intersect(self, origins, directions):  # noqa: ANN001, ANN201
            count = origins.shape[0]
            z = 0.02 * origins[:, 0]
            return (
                np.ones(count, dtype=bool),
                origins[:, 2] - z,
                np.tile(np.array([0.0, 0.0, 1.0]), (count, 1)),
                np.zeros(count, dtype=np.int64),
            )

    assert ground_datum(Ramp(), radius_m=60.0) == pytest.approx(0.0, abs=0.05)


def test_a_crop_with_no_dominant_surface_is_refused_rather_than_guessed() -> None:
    """Nineteen terraces, none of them a majority. There is no pedestrian level here."""
    steps = [(12.0 * k, (-500.0, 500.0, 10.0 * k - 2.0, 10.0 * k + 2.0)) for k in range(-9, 10)]
    with pytest.raises(RuntimeError, match="no dominant walkable surface"):
        measure_ground_datum(Slabs(steps), radius_m=90.0)


def test_an_empty_crop_is_an_error_and_not_a_number() -> None:
    with pytest.raises(RuntimeError, match="no near horizontal surface"):
        measure_ground_datum(Slabs([]), radius_m=30.0)


def test_the_arguments_are_checked() -> None:
    with pytest.raises(ValueError, match="radius_m"):
        measure_ground_datum(Slabs([(0.0, WIDE)]), radius_m=0.0)
    with pytest.raises(ValueError, match="major_level_ratio"):
        measure_ground_datum(Slabs([(0.0, WIDE)]), major_level_ratio=1.5)


def test_the_downward_probe_starts_above_the_tallest_tower() -> None:
    """Times Square rises 343 m above its pavement, Shibuya 230 m.

    The probe used to start 200 m above the datum, which is inside both. A ray
    that starts inside a shell reports a surface of that shell rather than its
    roof, and at street level that is indistinguishable from pavement.
    """
    layout = Slabs([(0.0, WIDE), (343.0, (-30.0, 30.0, -30.0, 30.0))])
    z, up = ground_height(layout, np.array([[0.0, 0.0], [100.0, 0.0]]))
    assert z[0] == pytest.approx(343.0)
    assert z[1] == pytest.approx(0.0)
    assert np.all(up == 1.0)
    assert SKY_PROBE > 343.0


def test_the_old_probe_height_can_still_be_asked_for_and_is_recorded() -> None:
    """Repairing a published run means selecting the standpoints it selected.

    Every run written before the probe moved cast from the ground datum plus
    200 m, which sits inside a 343 m tower and reports a wall of its shell as if
    it were pavement. Those runs are on disk and two of them had to be repaired,
    so the old rule has to remain reachable, and a walk has to say which rule
    built it rather than leaving it to be inferred from a timestamp.
    """
    layout = Slabs([(0.0, WIDE), (343.0, (-30.0, 30.0, -30.0, 30.0))])
    datum = ground_datum(layout, radius_m=90.0)
    old = build_walk(layout, ground_datum_m=datum, radius_m=90.0, spacing_m=6.0, probe_z_m=datum + 200.0)
    new = build_walk(layout, ground_datum_m=datum, radius_m=90.0, spacing_m=6.0)

    assert old.provenance["probe_z_m"] == pytest.approx(datum + 200.0)
    assert new.provenance["probe_z_m"] == SKY_PROBE
    # The tower footprint is walkable under the old probe and is not under the
    # new one, which is the whole difference between the two standpoint sets.
    under_the_tower = (np.abs(old.points[:, 0]) <= 30.0) & (np.abs(old.points[:, 1]) <= 30.0)
    assert np.any(under_the_tower)
    assert not np.any((np.abs(new.points[:, 0]) <= 30.0) & (np.abs(new.points[:, 1]) <= 30.0))


def test_the_walk_stays_off_the_roof_the_old_datum_put_it_on() -> None:
    layout = Slabs([(0.0, WIDE), (18.5, (-55.0, 55.0, -18.0, 18.0))])
    walk = build_walk(layout, ground_datum_m=ground_datum(layout, radius_m=90.0), radius_m=90.0, spacing_m=6.0)
    assert len(walk) > 0
    assert np.all(walk.ground_z_m == pytest.approx(0.0, abs=0.05))
    on_the_block = (np.abs(walk.points[:, 0]) <= 55.0) & (np.abs(walk.points[:, 1]) <= 18.0)
    assert not np.any(on_the_block), "no standpoint may sit over the monument footprint"


def mesh_path(site: str, crop_m: int = 250) -> pathlib.Path | None:
    for name in (f"inhouse_leaf_{crop_m}m_f64.ply", f"inhouse_leaf_{crop_m}m.ply"):
        path = GEOMETRY / site / name
        manifest = path.with_suffix(".json")
        if path.exists() and manifest.exists():
            if int(json.loads(manifest.read_text()).get("format_version", 0)) >= 3:
                return path
    return None


def site_geometry(site: str):  # noqa: ANN201
    path = mesh_path(site)
    if path is None:
        pytest.skip(f"no double precision 250 m mesh for {site}")
    pytest.importorskip("mitsuba")
    from semantic_twin.propagation import MitsubaGeometry

    return MitsubaGeometry(path)


def test_korenmarkt_reproduces_the_registered_pavement_height() -> None:
    """The no regression check. Ghent is the site with an independent answer.

    The registration of section 3 solved the camera pose against the skyline and
    reported the pavement under the cameras. The estimator never sees it.
    """
    measured = measure_ground_datum(site_geometry("korenmarkt"), radius_m=90.0)
    assert measured.z_m == pytest.approx(KORENMARKT_REGISTERED_Z_M, abs=0.25)


@pytest.mark.parametrize(
    ("site", "roof_z_m"),
    [("krakow_rynek", 269.124), ("toulouse_capitole", 205.169)],
)
def test_the_two_broken_sites_no_longer_sit_on_a_roof(site: str, roof_z_m: float) -> None:
    measured = measure_ground_datum(site_geometry(site), radius_m=90.0)
    assert measured.z_m < roof_z_m - 10.0
    assert measured.band_fraction > 0.4


def test_no_crop_needs_the_majority_ratio_at_the_walk_radius() -> None:
    """On the real crops at 90 m the ground is the busiest level everywhere.

    Which is what makes the ratio a margin rather than a fitted parameter: turn it
    off entirely and not one of the eleven datums moves.
    """
    checked = 0
    for site in sorted(p.name for p in GEOMETRY.iterdir() if p.is_dir()):
        if mesh_path(site) is None:
            continue
        geometry = site_geometry(site)
        found = [measure_ground_datum(geometry, radius_m=90.0, major_level_ratio=r).z_m for r in (0.2, 0.5, 1.0)]
        assert max(found) - min(found) < 1.0e-6, site
        checked += 1
    assert checked >= 10, f"expected the eleven crops, saw {checked}"


def test_every_registered_site_agrees_with_its_registration() -> None:
    """Eight of the eleven crops carry a registered pavement height. All eight agree.

    This is the cross check the run refuses on, so it is asserted on the whole
    set rather than on the one site the study leads with.
    """
    checked = 0
    for path in sorted(CONFIG.glob("*.json")):
        site = path.stem
        registered = json.loads(path.read_text()).get("camera_ground_z_m")
        if registered is None or mesh_path(site) is None:
            continue
        measured = measure_ground_datum(site_geometry(site), radius_m=90.0)
        assert measured.z_m == pytest.approx(float(registered), abs=1.0), site
        checked += 1
    assert checked >= 7, f"expected the registered sites to be exercised, saw {checked}"
