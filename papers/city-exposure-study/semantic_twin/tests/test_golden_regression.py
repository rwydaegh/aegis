"""The golden lock: the numbers this directory produced before it was refactored.

Three tiers, cheapest first.

The numeric tier needs no mesh and no phantom. It checks the closed form
references in ``propagation/closed_form.py`` and the quadrature identity every
illumination model has to satisfy, which is that its density integrates to 1
over 4 pi. It runs in about a second and it catches most of the damage a
refactor can do to the weights, because a law that has been moved, renamed or
rewritten and no longer normalises will fail here before any ray is cast.

The fast golden tier runs the two drivers end to end on the Korenmarkt 130 m
mesh at a reduced ray count. About a minute.

The slow golden tier runs the configurations closest to what the study
publishes. It covers all three material routes, both estimators, all eleven
squares at the published crop radius, the cross city table built from them, and
the evidence ladder. Roughly a quarter of an hour.

What the slow tier covers, and why each one is there:

- ``exposure_korenmarkt_130m_geometric`` the escape estimator at the published
  ray count.
- ``exposure_korenmarkt_130m_semantic`` the fishnet route through ``bind()``.
- ``exposure_korenmarkt_130m_walk`` the fused station route.
- ``exposure_brussels_250m_geometric`` a second city at the published crop.
- ``next_event_250m_default`` the second estimator on its own defaults.
- ``cities_250m_all_sites`` every square, plus the cross city table.
- ``cities_250m_report_only`` that table again with no tracing, so a change in
  the reduction alone fails in seconds.
- ``coverage_ladder_korenmarkt_130m`` the three rung evidence ladder and the two
  reports over it.

Why the tolerance is what it is
-------------------------------
On the machine these fixtures were captured on, both drivers reproduce bit for
bit: repeat runs at the same seed agree on every field, and so do runs at one
worker and at four. So the honest tolerance for a same seed rerun is zero. It is
set to 1e-12 rather than zero to leave room for the one drift already documented
in ``tests/test_determinism.py``, where the two elevation weighted
susceptibilities move by one or two units in the last place across machines
because they go through ``arcsin``.

For scale: the Monte Carlo noise at one standpoint and 200 000 rays is 0.09 %
on the isotropic model, 0.7 % on rooftop and 2.4 % on street small cell. The
seed to seed spread of the median over sixteen standpoints is 1.05 dB on
rooftop. The tolerance here is ten orders of magnitude below either of those, so
nothing it flags is noise.
"""

from __future__ import annotations

import json
import math
import pathlib
import subprocess
import sys
from typing import Any, Iterator

import numpy as np
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from golden.cases import ATOL, CASES, CASES_BY_ID, RTOL, ROOT, Case  # noqa: E402

from semantic_twin.propagation import (  # noqa: E402
    MODELS,
    PEC_PERMITTIVITY,
    VARIANTS,
    IlluminationModel,
    elevation_band_measure,
    fibonacci_sphere,
    measure_below,
)
from semantic_twin.propagation.closed_form import (  # noqa: E402
    ground_plane_band_average,
    ground_plane_susceptibility,
    ground_plane_susceptibility_te_only,
)

#: ITU-R P.2040-4 concrete at 15 GHz, the row the ground class binds to.
CONCRETE = complex(5.24, -0.46055233310470917)


# ---------------------------------------------------------------------------
# Numeric tier. No mesh, no phantom, about a second.
# ---------------------------------------------------------------------------


def _independent_sphere_integral(model: IlluminationModel) -> float:
    """Integrate ``density`` over 4 pi with a scheme the package does not use.

    ``IlluminationModel.normalisation`` is a 200 001 point trapezoid, and
    ``density`` divides by it, so integrating with the same trapezoid would
    prove nothing. This is adaptive Gauss-Kronrod from SciPy, with the band
    laws' two interior knots handed over as break points.
    """
    from scipy.integrate import quad

    low = math.radians(model.elevation_min_deg)
    high = math.radians(model.elevation_max_deg)

    def integrand(elevation: float) -> float:
        direction = np.array([[math.cos(elevation), 0.0, math.sin(elevation)]])
        return float(model.density(direction)[0]) * math.cos(elevation)

    points = [knot for knot in model.knots() if low < knot < high]
    value, _ = quad(integrand, low, high, points=points or None, limit=400)
    return 2.0 * math.pi * value


@pytest.mark.parametrize("name", sorted(VARIANTS))
def test_every_illumination_density_integrates_to_one(name: str) -> None:
    """`Q_S` is a probability density on the sphere. Everything downstream assumes it."""
    total = _independent_sphere_integral(VARIANTS[name])
    assert total == pytest.approx(1.0, abs=1.0e-7), f"{name} integrates to {total!r} over 4 pi"


@pytest.mark.parametrize("name", sorted(VARIANTS))
def test_elevation_bands_covering_the_support_partition_the_measure(name: str) -> None:
    """The band measure is what the figures and the sweeps read. Bands over the
    whole support must sum to one, at one band and at forty."""
    model = VARIANTS[name]
    for count in (1, 7, 40):
        edges = np.linspace(model.elevation_min_deg, model.elevation_max_deg, count + 1)
        total = float(elevation_band_measure(model, edges).sum())
        assert total == pytest.approx(1.0, abs=1.0e-5), f"{name} with {count} bands sums to {total!r}"


@pytest.mark.parametrize("name", sorted(VARIANTS))
def test_measure_below_runs_from_zero_to_one_and_never_decreases(name: str) -> None:
    model = VARIANTS[name]
    assert measure_below(model, model.elevation_min_deg) == pytest.approx(0.0, abs=1.0e-9)
    assert measure_below(model, model.elevation_max_deg) == pytest.approx(1.0, abs=1.0e-5)
    cuts = np.linspace(model.elevation_min_deg, model.elevation_max_deg, 25)
    values = np.array([measure_below(model, float(cut)) for cut in cuts])
    assert np.all(np.diff(values) >= -1.0e-12), f"{name} measure_below is not monotone"


#: The seven models, their laws, and the derived elevation support of each, as
#: captured. A refactor that renames a law, drops a model or changes a band edge
#: has to change this table on purpose.
PINNED_MODELS = {
    "isotropic": ("isotropic", -90.0, 90.0, None, None),
    "rooftop": ("uniform_sites_band", 3.090970003540502, 60.113473059575966, (13.5, 43.5), (25.0, 250.0)),
    "street_small_cell": (
        "uniform_sites_band",
        0.9548412538721887,
        33.02386755579665,
        (2.5, 6.5),
        (10.0, 150.0),
    ),
    "rooftop_pathloss": (
        "uniform_sites_band_pathloss",
        3.090970003540502,
        60.113473059575966,
        (13.5, 43.5),
        (25.0, 250.0),
    ),
    "street_small_cell_pathloss": (
        "uniform_sites_band_pathloss",
        0.9548412538721887,
        33.02386755579665,
        (2.5, 6.5),
        (10.0, 150.0),
    ),
    "rooftop_fixed_height": ("uniform_sites", 3.1, 60.1, None, None),
    "street_small_cell_fixed_height": ("uniform_sites", 0.95, 33.0, None, None),
}

#: ``normalisation()`` at the default 200 001 point quadrature. These are the
#: constants every susceptibility in the study is divided by.
PINNED_NORMALISATION = {
    "isotropic": 12.566370614100787,
    "rooftop": 5831581.360687153,
    "street_small_cell": 281486.7012513481,
    "rooftop_pathloss": 357.2817326972599,
    "street_small_cell_pathloss": 65.66294172725507,
    "rooftop_fixed_height": 1070.045413760976,
    "street_small_cell_fixed_height": 11417.869618970028,
}


def test_the_model_registry_is_the_one_that_was_captured() -> None:
    assert set(VARIANTS) == set(PINNED_MODELS)
    assert list(MODELS) == ["isotropic", "rooftop", "street_small_cell"]
    for name, (law, low, high, height, ranges) in PINNED_MODELS.items():
        model = VARIANTS[name]
        assert model.law == law
        assert model.elevation_min_deg == pytest.approx(low, rel=1e-15)
        assert model.elevation_max_deg == pytest.approx(high, rel=1e-15)
        assert model.height_band_m == height
        assert model.range_band_m == ranges


@pytest.mark.parametrize("name", sorted(PINNED_NORMALISATION))
def test_normalisation_constants_are_unchanged(name: str) -> None:
    assert VARIANTS[name].normalisation() == pytest.approx(PINNED_NORMALISATION[name], rel=RTOL)


def test_band_law_support_is_derived_from_the_bands_not_written_beside_them() -> None:
    """The defect MONOSTATIC_SBR.md section 2.7 records, checked rather than trusted."""
    for name in ("rooftop", "street_small_cell", "rooftop_pathloss", "street_small_cell_pathloss"):
        model = VARIANTS[name]
        low_h, high_h = model.height_band_m  # type: ignore[misc]
        low_d, high_d = model.range_band_m  # type: ignore[misc]
        assert model.elevation_min_deg == pytest.approx(math.degrees(math.atan2(low_h, high_d)), rel=1e-15)
        assert model.elevation_max_deg == pytest.approx(math.degrees(math.atan2(high_h, low_d)), rel=1e-15)


def test_fibonacci_sphere_is_unit_length_and_near_equal_area() -> None:
    for count in (128, 512, 4096):
        grid = fibonacci_sphere(count)
        assert grid.shape == (count, 3)
        assert np.allclose(np.linalg.norm(grid, axis=1), 1.0, atol=1e-12)
        # The z column is what nearest_cell's band search assumes is sorted and
        # evenly spaced. Both are load bearing and neither is asserted anywhere
        # else in the suite.
        assert np.all(np.diff(grid[:, 2]) < 0.0)
        step = np.diff(grid[:, 2])
        assert np.max(np.abs(step - step.mean())) < 1e-12


#: The closed form ground plane susceptibility at seven elevations, as captured.
#: MONOSTATIC_SBR.md section 11.1.
PINNED_GROUND_PLANE_ELEVATIONS_DEG = [1.0, 5.0, 10.0, 24.0, 45.0, 60.0, 89.0]
PINNED_GROUND_PLANE_CONCRETE = [
    1.901950555154233,
    1.6254190228626793,
    1.4329826928463574,
    1.2290042592682209,
    1.164717176201048,
    1.1563423122929546,
    1.1547181481952016,
]
PINNED_GROUND_PLANE_CONCRETE_TE_ONLY = [
    1.9668098589380696,
    1.8449192937796146,
    1.7150131225491796,
    1.4576242961127597,
    1.2612058541564797,
    1.1959630016369267,
    1.1547592103765,
]


def test_perfect_conductor_ground_plane_is_two_at_every_elevation() -> None:
    """The angle independent target section 11.1 asks for.

    ``PEC_PERMITTIVITY`` is large but finite, so the residual is a real and
    measurable thing rather than rounding. It is worst at grazing, 1.6e-4 at
    half a degree, and falls to 2.8e-6 by 89 degrees. Both ends are asserted,
    because a residual that vanishes would mean the constant had been replaced
    by something infinite and the test would have stopped testing the Fresnel
    path at all.
    """
    elevation = np.linspace(0.5, 89.5, 400)
    value = ground_plane_susceptibility(elevation, PEC_PERMITTIVITY)
    deviation = np.abs(value - 2.0)
    assert deviation.max() < 2.0e-4
    assert deviation[elevation >= 5.0].max() < 2.0e-5
    assert deviation.min() > 1.0e-9, "PEC_PERMITTIVITY has become effectively infinite"


def test_dielectric_ground_plane_matches_the_captured_values() -> None:
    value = ground_plane_susceptibility(np.array(PINNED_GROUND_PLANE_ELEVATIONS_DEG), CONCRETE)
    np.testing.assert_allclose(value, PINNED_GROUND_PLANE_CONCRETE, rtol=RTOL, atol=0.0)


def test_the_te_only_answer_stays_the_wrong_answer() -> None:
    """Kept because it is the specific mistake the dielectric test rejects. If
    these two ever agree, the test has stopped discriminating."""
    elevation = np.array(PINNED_GROUND_PLANE_ELEVATIONS_DEG)
    te = ground_plane_susceptibility_te_only(elevation, CONCRETE)
    np.testing.assert_allclose(te, PINNED_GROUND_PLANE_CONCRETE_TE_ONLY, rtol=RTOL, atol=0.0)
    both = ground_plane_susceptibility(elevation, CONCRETE)
    gap_db = 10.0 * np.log10(te / both)
    assert gap_db.max() > 0.7, "TE only is no longer separated from the two polarisation answer"


def test_band_average_is_the_pointwise_value_when_the_band_is_narrow() -> None:
    edges = np.array([0.40, 0.4001, 0.70, 0.7001])
    banded = ground_plane_band_average(edges, CONCRETE)
    centres = np.degrees(np.arcsin(np.array([0.40005, 0.70005])))
    pointwise = ground_plane_susceptibility(centres, CONCRETE)
    np.testing.assert_allclose(banded[[0, 2]], pointwise, rtol=1.0e-8)


def test_band_average_over_the_whole_upper_hemisphere_is_two_for_a_conductor() -> None:
    edges = np.linspace(0.0, 1.0, 9)
    value = ground_plane_band_average(edges, PEC_PERMITTIVITY)
    assert np.max(np.abs(value - 2.0)) < 1.0e-3


#: ``run_exposure.py --validate`` at its own default ray count, under the laws
#: that are current today. Four seconds, no mesh, and it is the one part of the
#: driver that has a target it can be wrong against rather than only a previous
#: value.
#:
#: One of these is expected to move. docs/BUGS.md item 8 records that the gate
#: scores a band average against the value at the band centre, and that the
#: mismatch in the lowest band is 0.0158 against a reported dielectric
#: max_abs_error of 0.0122. When that is fixed the dielectric errors here get
#: smaller and this test fails on purpose. Recapture it then; do not widen it.
PINNED_VALIDATE_400K = {
    "free_space.chi.isotropic": 1.0000000000205487,
    "free_space.chi.rooftop": 0.9982039419693284,
    "free_space.chi.street_small_cell": 1.011829654602254,
    "free_space.exit_profile_max_abs_error": 0.011735000000000051,
    "pec.upper_mean": 1.9999823008055355,
    "pec.upper_max_abs_error": 0.011497122652717628,
    "pec.lower_max": 0.0,
    "pec.chi.isotropic": 0.999991158460922,
    "pec.chi.rooftop": 1.9979068619427198,
    "pec.chi.street_small_cell": 2.008493810660388,
    "dielectric.max_abs_error": 0.012245497180557896,
    "dielectric.max_rel_error": 0.010236766748666248,
}


def _validate_leaves(report: dict[str, Any]) -> dict[str, float]:
    free = report["free_space"]
    pec = report["pec_ground_plane"]
    die = report["dielectric_ground_plane"]
    return {
        "free_space.chi.isotropic": free["chi"]["isotropic"],
        "free_space.chi.rooftop": free["chi"]["rooftop"],
        "free_space.chi.street_small_cell": free["chi"]["street_small_cell"],
        "free_space.exit_profile_max_abs_error": free["exit_profile_max_abs_error"],
        "pec.upper_mean": pec["measured_upper_mean"],
        "pec.upper_max_abs_error": pec["measured_upper_max_abs_error"],
        "pec.lower_max": pec["measured_lower_max"],
        "pec.chi.isotropic": pec["chi"]["isotropic"],
        "pec.chi.rooftop": pec["chi"]["rooftop"],
        "pec.chi.street_small_cell": pec["chi"]["street_small_cell"],
        "dielectric.max_abs_error": die["max_abs_error"],
        "dielectric.max_rel_error": die["max_rel_error"],
    }


def test_the_drivers_own_closed_form_gate_is_unchanged() -> None:
    """``run_exposure.py --validate``, called as a function so nothing is written."""
    import run_exposure

    leaves = _validate_leaves(run_exposure.validate(400_000))
    for key, want in PINNED_VALIDATE_400K.items():
        assert leaves[key] == pytest.approx(want, rel=RTOL, abs=1e-300), key
    # The physics targets themselves, not only the previous numbers.
    assert leaves["free_space.chi.isotropic"] == pytest.approx(1.0, abs=1e-9)
    assert leaves["pec.chi.isotropic"] == pytest.approx(1.0, abs=1e-4)
    assert leaves["pec.upper_mean"] == pytest.approx(2.0, abs=1e-4)
    assert leaves["pec.lower_max"] == 0.0
    assert leaves["dielectric.max_rel_error"] < 0.02


def test_the_published_validation_file_is_a_record_of_the_superseded_law() -> None:
    """A finding, pinned so it cannot be mistaken for a regression later.

    ``outputs/exposure_korenmarkt/exposure_validation.json`` was written on
    2026-08-01 and does not reproduce under the code as it stands. Exactly four
    of its forty two leaves differ, and all four are the two directional
    susceptibilities. Everything isotropic, every exit profile and every
    dielectric number still matches to the last bit.

    The cause is not drift. Swap the two directional models for the uncorrected
    fixed height pair that ``directions.py`` keeps for exactly this purpose, and
    the whole file comes back identical. The band law correction landed on
    2026-08-02, the file predates it by a day, and it was never regenerated. So
    the file is a correct record of a superseded run, which is the same status
    LAW_CHANGE.md gives the rest of the old numbers.
    """
    import run_exposure
    from semantic_twin.illumination import (
        ISOTROPIC,
        ROOFTOP_FIXED_HEIGHT,
        STREET_SMALL_CELL_FIXED_HEIGHT,
    )

    published_path = ROOT / "outputs" / "exposure_korenmarkt" / "exposure_validation.json"
    if not published_path.exists():
        pytest.skip("the published validation file is not in this checkout")
    published = json.loads(published_path.read_text())

    current = _validate_leaves(run_exposure.validate(400_000))
    old_law = {
        "isotropic": ISOTROPIC,
        "rooftop": ROOFTOP_FIXED_HEIGHT,
        "street_small_cell": STREET_SMALL_CELL_FIXED_HEIGHT,
    }
    saved = run_exposure.MODELS
    try:
        run_exposure.MODELS = old_law
        replayed = _validate_leaves(run_exposure.validate(400_000))
    finally:
        run_exposure.MODELS = saved

    want = _validate_leaves(published)
    directional = [key for key in want if key.endswith(("rooftop", "street_small_cell"))]
    for key in want:
        assert replayed[key] == pytest.approx(want[key], rel=RTOL, abs=1e-300), (
            f"{key} no longer replays under the uncorrected fixed height law"
        )
    for key in want:
        if key in directional:
            assert current[key] != pytest.approx(want[key], rel=1.0e-6), (
                f"{key} now agrees with the superseded file. Either the law was reverted or the "
                f"file was regenerated. Both are real events and this test has to be rewritten."
            )
        else:
            assert current[key] == pytest.approx(want[key], rel=RTOL, abs=1e-300), key


# ---------------------------------------------------------------------------
# Golden tier. Re-run the drivers and compare against the captured fixtures.
# ---------------------------------------------------------------------------


def _flatten(value: Any, prefix: str = "") -> Iterator[tuple[str, Any]]:
    if isinstance(value, dict):
        for key in sorted(value):
            yield from _flatten(value[key], f"{prefix}.{key}" if prefix else str(key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _flatten(item, f"{prefix}[{index}]")
    else:
        yield prefix or "<root>", value


def _relative(fresh: float, want: float) -> float:
    if want == fresh:
        return 0.0
    scale = max(abs(want), abs(fresh))
    return abs(fresh - want) / scale if scale > 0.0 else abs(fresh - want)


def compare(fresh: dict[str, Any], want: dict[str, Any]) -> list[str]:
    """Every leaf of both structures, compared. Returns the complaints."""
    left = dict(_flatten(fresh))
    right = dict(_flatten(want))
    problems: list[str] = []
    for path in sorted(set(right) - set(left)):
        problems.append(f"missing from the rerun: {path} (was {right[path]!r})")
    for path in sorted(set(left) - set(right)):
        problems.append(f"new in the rerun: {path} (is {left[path]!r})")

    worst = (0.0, "")
    for path in sorted(set(left) & set(right)):
        got, expected = left[path], right[path]
        if isinstance(expected, bool) or expected is None or isinstance(expected, str):
            if got != expected:
                problems.append(f"{path}: {got!r} != {expected!r}")
            continue
        if isinstance(expected, int) and not isinstance(got, float):
            if got != expected:
                problems.append(f"{path}: {got!r} != {expected!r}")
            continue
        got_f, expected_f = float(got), float(expected)
        if math.isnan(expected_f) or math.isnan(got_f):
            if not (math.isnan(expected_f) and math.isnan(got_f)):
                problems.append(f"{path}: {got_f!r} != {expected_f!r}")
            continue
        relative = _relative(got_f, expected_f)
        if relative > worst[0]:
            worst = (relative, path)
        if not math.isclose(got_f, expected_f, rel_tol=RTOL, abs_tol=ATOL):
            problems.append(f"{path}: {got_f!r} != {expected_f!r} (relative {relative:.3e})")

    if problems:
        problems.append(
            f"worst relative deviation {worst[0]:.3e} at {worst[1]}. For scale: Monte Carlo noise "
            f"at 200 000 rays is 9e-4 isotropic, 7e-3 rooftop, 2.4e-2 street small cell, and the "
            f"seed to seed spread of the median over sixteen standpoints is 2.4e-1 on rooftop. "
            f"A deviation near or above those is physics, not arithmetic."
        )
    return problems


def _invoke(case: Case) -> None:
    case.clear()
    command = [sys.executable, *case.command()]
    proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        raise AssertionError(
            f"{case.ident} exited {proc.returncode}\n$ {' '.join(command)}\n"
            f"{proc.stdout[-3000:]}\n{proc.stderr[-3000:]}"
        )


#: Cases already run in this pytest process. The eleven city sweep takes four
#: minutes and is both a case of its own and the prerequisite of the report only
#: case, so without this it runs twice.
_INVOKED: set[str] = set()


def _run(case: Case) -> dict[str, Any]:
    """Run the case, after anything it depends on.

    ``--cities-report`` traces nothing. It reads the per site row files off disk
    and rebuilds the table from them, so running it alone would compare an
    aggregate of whatever was left in ``outputs/`` by the last thing to write
    there. Its prerequisite is run first unless this process already ran it, so
    the test is meaningful under ``-k`` selection and under xdist too, where each
    worker keeps its own set.
    """
    for name in case.prerequisites:
        if name in _INVOKED:
            continue
        _invoke(CASES_BY_ID[name])
        _INVOKED.add(name)
    _invoke(case)
    _INVOKED.add(case.ident)
    return case.reduce()


def _ids(cases: tuple[Case, ...]) -> list[str]:
    return [case.ident for case in cases]


FAST = tuple(case for case in CASES if case.tier == "fast")
SLOW = tuple(case for case in CASES if case.tier == "slow")


@pytest.mark.slow
@pytest.mark.parametrize("case", FAST, ids=_ids(FAST))
def test_golden_fast(case: Case) -> None:
    """The cheap end to end lock. Real mesh, real Fresnel, real phantom."""
    if not case.fixture.exists():
        pytest.fail(f"no fixture at {case.fixture}. Capture it with tests/golden/capture.py")
    want = json.loads(case.fixture.read_text())
    problems = compare(_run(case), want)
    assert not problems, "\n".join([f"{case.ident} moved:", *problems[:40]])


@pytest.mark.slow
@pytest.mark.parametrize("case", SLOW, ids=_ids(SLOW))
def test_golden_slow(case: Case) -> None:
    """The configurations closest to what the study publishes."""
    if not case.fixture.exists():
        pytest.fail(f"no fixture at {case.fixture}. Capture it with tests/golden/capture.py")
    want = json.loads(case.fixture.read_text())
    problems = compare(_run(case), want)
    assert not problems, "\n".join([f"{case.ident} moved:", *problems[:40]])


def test_the_thin_korenmarkt_median_is_labelled_as_thin() -> None:
    """Escalated as a paper question, so the code is unchanged and the label is the fix.

    ``run_next_event.py`` at its own defaults holds out two standpoints at
    Korenmarkt. The capture route is 49 m long and yields fourteen, and the
    split rule turns sixteen of a hundred and forty four into two. The median it
    prints is a median of two points and the two percentiles either side are
    drawn from the same two. That is locked as the behaviour that exists. This
    test is what stops the label being dropped while the number stays.
    """
    fixture = CASES_BY_ID["next_event_250m_default"].fixture
    if not fixture.exists():
        pytest.fail(f"no fixture at {fixture}")
    rows = {row["site"]: row for row in json.loads(fixture.read_text())["payload"]["rows"]}
    korenmarkt = rows["korenmarkt"]
    assert korenmarkt["held_out"] == 2, (
        f"Korenmarkt now holds out {korenmarkt['held_out']} standpoints, not 2. If the split "
        f"rule was changed on purpose, recapture and rewrite this test. If it moved by "
        f"accident, that is the regression."
    )
    assert "held_out_warning" in korenmarkt
    assert "NOT as a converged number" in korenmarkt["held_out_warning"]

    manifest_path = pathlib.Path(__file__).resolve().parent / "golden" / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text())
    assert "next_event_250m_default:korenmarkt" in manifest["thin_statistics"]


#: The eleven squares, in the order ``run_exposure.SITES`` lists them. Written
#: out here rather than imported so that a site quietly dropped from the driver
#: fails a test instead of shrinking the sweep it is compared against.
EXPECTED_SITES: tuple[str, ...] = (
    "brussels_grandplace",
    "korenmarkt",
    "krakow_rynek",
    "london_trafalgar",
    "madrid_plazamayor",
    "mexico_zocalo",
    "newyork_timessquare",
    "prague_staromestske",
    "milan_duomo",
    "tokyo_hachiko",
    "toulouse_capitole",
)


def test_the_site_list_is_the_one_that_was_captured() -> None:
    """A site added or removed changes the published cross city table."""
    import run_exposure

    assert tuple(run_exposure.SITES) == EXPECTED_SITES


@pytest.mark.parametrize("site", EXPECTED_SITES)
def test_every_site_is_locked_by_the_sweep(site: str) -> None:
    """One assertion per square, so a geometry regression cannot hide in the aggregate.

    ``cities_250m_all_sites`` traces every site through the same ``run()`` the
    single site cases use, at the published 250 m crop with the geometric class
    prior, and its fixture keeps all eight standpoint rows per site. Separate
    ``--site`` cases for the other ten would re-trace identical physics under a
    different tag, so this test names the site instead. It reads the fixture and
    runs in milliseconds; the tracing that fills it is the slow tier case.
    """
    case = CASES_BY_ID["cities_250m_all_sites"]
    if not case.fixture.exists():
        pytest.fail(f"no fixture at {case.fixture}")
    fixture = json.loads(case.fixture.read_text())

    assert site in fixture["per_site"], f"{site} is not in the sweep fixture"
    entry = fixture["per_site"][site]
    assert entry["mesh_triangles"] > 0
    assert entry["locations_traced"] == 8
    assert len(entry["rows"]) == 8, f"{site} has {len(entry['rows'])} rows, not 8"
    for row in entry["rows"]:
        for key in ("chi_isotropic", "chi_rooftop", "chi_street_small_cell", "sky_fraction"):
            value = row[key]
            assert math.isfinite(value) and value > 0.0, f"{site} row {row['index']}: {key} is {value}"

    summary = fixture["cities_summary"]
    assert site in summary["sites"]
    assert summary["locations_by_site"][site] == 8
    assert summary["sites_present"] == summary["sites_expected"] == len(EXPECTED_SITES)
    assert summary["complete"] is True
    assert summary["ragged_locations"] is False


def test_the_deliberate_holes_are_written_down() -> None:
    """A hole nobody recorded reads later as a hole nobody noticed."""
    manifest_path = pathlib.Path(__file__).resolve().parent / "golden" / "MANIFEST.json"
    holes = json.loads(manifest_path.read_text())["deliberate_holes"]
    for name in (
        "next_event_walk_paths",
        "cross_machine_bit_equality",
        "clean_checkout",
        "coverage_ladder_breadth",
        "coverage_ladder_resumes",
        "materials_walk_variants",
        "per_site_single_runs",
    ):
        assert name in holes and len(holes[name]) > 40


def test_every_case_has_a_fixture_and_a_manifest_entry() -> None:
    """Cheap, and it is the check that notices a case captured on one machine and
    never captured on another."""
    manifest_path = pathlib.Path(__file__).resolve().parent / "golden" / "MANIFEST.json"
    assert manifest_path.exists(), "tests/golden/MANIFEST.json is missing"
    manifest = json.loads(manifest_path.read_text())
    provenance_fields = {"captured_utc", "git_sha", "git_dirty"}
    legacy_provenance = provenance_fields <= manifest.keys()
    for case in CASES:
        assert case.fixture.exists(), f"{case.ident} has no fixture"
        assert case.ident in manifest["cases"], f"{case.ident} is not in the manifest"
        entry = manifest["cases"][case.ident]
        recorded = entry["argv"]
        assert recorded == list(case.argv), (
            f"{case.ident}: the fixture was captured with a different command.\n"
            f"  captured: {recorded}\n  now:      {list(case.argv)}"
        )
        present = provenance_fields & entry.keys()
        assert present in (set(), provenance_fields), f"{case.ident}: partial per-case provenance {sorted(present)}"
        if not present:
            assert legacy_provenance, f"{case.ident}: no per-case provenance and no complete legacy provenance"
        else:
            assert isinstance(entry["captured_utc"], str) and entry["captured_utc"].endswith("Z")
            assert isinstance(entry["git_sha"], str) and entry["git_sha"]
            assert isinstance(entry["git_dirty"], bool)
