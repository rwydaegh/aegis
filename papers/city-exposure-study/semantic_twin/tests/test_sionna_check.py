"""Tests for the external cross validation harness.

These do not test the estimator, `test_propagation.py` does that. They test the
translation between the estimator and Sionna RT, which is where a cross
validation goes wrong quietly: a comparison that has silently changed the
question is worse than no comparison, because it reports a number.

Two of them shell out to a subprocess. Importing `sionna.rt` sets the Mitsuba
variant to `llvm_ad_mono_polarized` for the whole process, and the rest of the
suite builds geometry under `llvm_ad_rgb`, so keeping Sionna out of the shared
interpreter is deliberate rather than fussy.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap

import numpy as np
import pytest

import semantic_twin.transport.sionna_check as sionna_check
from semantic_twin.propagation.closed_form import PEC_PERMITTIVITY
from semantic_twin.illumination import ISOTROPIC, ROOFTOP, STREET_SMALL_CELL
from semantic_twin.propagation.geometry import PlaneGeometry
from semantic_twin.transport.sionna_check import (
    CompareOptions,
    FULLY_DIFFUSE_RMS_HEIGHT_M,
    MODES,
    SLAB_THICKNESS_M,
    SPEED_OF_LIGHT_M_S,
    VACUUM_PERMITTIVITY_F_M,
    band_transfer,
    conductivity_from_permittivity,
    free_space_reference,
    matched_scattering_coefficient,
    median_change_db,
    mode_materials,
    rayleigh_specular_share,
    recorded_susceptibility,
    sample_sky,
    smallest_converged,
    split_mesh_by_class,
    susceptibility,
    write_ply,
)
from semantic_twin.transport.tracer import (
    PathRecorder,
    SbrTracer,
    TraceConfig,
    fresnel_power_reflectance,
    specular_share,
)

MODELS = {"isotropic": ISOTROPIC, "rooftop": ROOFTOP, "street_small_cell": STREET_SMALL_CELL}
FREQUENCY_HZ = 15.0e9
WAVELENGTH_M = SPEED_OF_LIGHT_M_S / FREQUENCY_HZ

#: The four geometric classes at 15 GHz, from config/itu_p2040_4.json through
#: scene.load_bindings. Written out rather than loaded so a change to the
#: config file cannot silently change what this file claims to have checked.
CLASS_PERMITTIVITY = (
    complex(4.83, -0.56885825),
    complex(3.91, -0.04399973),
    complex(5.24, -0.46055233),
    complex(5.24, -0.46055233),
)
CLASS_RMS_HEIGHT_M = (0.00378594, 0.00115509, 0.0006, 0.00015)


def test_site_mesh_uses_the_canonical_provenance_resolver(monkeypatch: pytest.MonkeyPatch) -> None:
    """The Sionna harness must not reimplement mesh filename/version policy."""
    calls: list[tuple[str, int, object]] = []
    expected = sionna_check.ROOT / "data" / "geometry" / "fixture" / "mesh.ply"

    def resolve(site: str, crop_m: int, *, root_dir=None):  # noqa: ANN001
        calls.append((site, crop_m, root_dir))
        return expected

    monkeypatch.setattr(sionna_check.paths, "site_mesh", resolve)

    assert sionna_check.site_mesh("fixture", 250) == expected
    assert calls == [("fixture", 250, sionna_check.ROOT)]


def test_compare_preserves_historical_keyword_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    expected = sionna_check.ROOT / "outputs" / "comparison.json"
    seen: dict[str, object] = {}

    def fake_compare(site: str, options: CompareOptions):
        seen["site"] = site
        seen["options"] = options
        return expected

    monkeypatch.setattr(sionna_check, "_compare", fake_compare)

    assert sionna_check.compare("fixture", locations=3, local=True) == expected
    assert seen == {"site": "fixture", "options": CompareOptions(locations=3, local=True)}


def test_compare_rejects_unknown_configuration() -> None:
    with pytest.raises(TypeError, match="unexpected keyword"):
        CompareOptions.from_kwargs({"not_a_compare_option": 1})


def _subprocess_json(body: str) -> dict:
    """Run a snippet in a fresh interpreter and read its single JSON line."""
    source = textwrap.dedent(body)
    finished = subprocess.run(
        [sys.executable, "-c", source],
        capture_output=True,
        text=True,
        timeout=900,
        # Dr.Jit writes a kernel cache under HOME and aborts the process if it
        # cannot, so the environment is inherited and narrowed rather than
        # replaced. Two threads because this box is shared.
        env={**os.environ, "DRJIT_NUM_THREADS": "2"},
    )
    if finished.returncode != 0:
        pytest.skip(f"Sionna unavailable in a subprocess: {finished.stderr.strip()[-400:]}")
    return json.loads(finished.stdout.strip().splitlines()[-1])


# ---------------------------------------------------------------------------
# The dielectric has to be the same dielectric
# ---------------------------------------------------------------------------


def test_conductivity_round_trips_to_the_imaginary_permittivity() -> None:
    permittivity = np.array(CLASS_PERMITTIVITY)
    conductivity = conductivity_from_permittivity(permittivity, FREQUENCY_HZ)
    recovered = conductivity / (2.0 * np.pi * FREQUENCY_HZ * VACUUM_PERMITTIVITY_F_M)
    assert np.allclose(recovered, -permittivity.imag, rtol=1e-12)
    assert np.all(conductivity > 0.0)


def test_slab_thickness_is_a_half_space() -> None:
    """At ``SLAB_THICKNESS_M`` Sionna's slab is the estimator's half space.

    The failing half of this test is the point of it. Sionna's default 0.1 m
    thickness puts a slab resonance on the brick facade worth about 3 dB, which
    would have entered the comparison as a disagreement about propagation.
    """
    body = f"""
        import json
        import numpy as np
        import mitsuba as mi
        import sionna.rt  # noqa: F401
        from sionna.rt.utils import itu_coefficients_single_layer_slab

        wavelength = {WAVELENGTH_M!r}
        cosines = np.cos(np.radians(np.array([0.0, 20.0, 40.0, 60.0, 80.0, 87.0])))
        out = {{}}
        for thickness in ({SLAB_THICKNESS_M!r}, 0.1):
            rows = []
            for real, imaginary in {[(p.real, p.imag) for p in CLASS_PERMITTIVITY]!r}:
                eta = mi.Complex2f(mi.Float(real), mi.Float(imaginary))
                r_te, r_tm, _, _ = itu_coefficients_single_layer_slab(
                    mi.Float(np.asarray(cosines, dtype=np.float32)),
                    eta,
                    mi.Float(thickness),
                    mi.Float(wavelength),
                )
                te = np.asarray(r_te.real) + 1j * np.asarray(r_te.imag)
                tm = np.asarray(r_tm.real) + 1j * np.asarray(r_tm.imag)
                rows.append((0.5 * (np.abs(te) ** 2 + np.abs(tm) ** 2)).tolist())
            out[str(thickness)] = rows
        print(json.dumps(out))
    """
    answer = _subprocess_json(body)
    cosines = np.cos(np.radians(np.array([0.0, 20.0, 40.0, 60.0, 80.0, 87.0])))
    ours = np.array([fresnel_power_reflectance(cosines, np.full(cosines.shape, p)) for p in CLASS_PERMITTIVITY])
    matched = np.array(answer[str(SLAB_THICKNESS_M)])
    default = np.array(answer["0.1"])
    assert np.max(np.abs(10.0 * np.log10(matched / ours))) < 0.01
    assert np.max(np.abs(10.0 * np.log10(default / ours))) > 1.0


def test_free_space_reference_matches_friis() -> None:
    assert free_space_reference(1000.0, 0.02) == pytest.approx((0.02 / (4.0 * np.pi * 1000.0)) ** 2)


# ---------------------------------------------------------------------------
# The scattering split has to be the same split
# ---------------------------------------------------------------------------


def test_rayleigh_share_closed_form_matches_quadrature() -> None:
    """``(1 - exp(-a^2)) / a^2`` is the flux weighted mean of the tracer's share."""
    for rms in CLASS_RMS_HEIGHT_M:
        cosine = np.linspace(0.0, 1.0, 200_001)
        share = specular_share(np.full(cosine.shape, rms), cosine, WAVELENGTH_M)
        quadrature = 2.0 * np.trapezoid(share * cosine, cosine)
        assert rayleigh_specular_share(np.array([rms]), WAVELENGTH_M)[0] == pytest.approx(quadrature, rel=1e-6)


def test_the_two_exact_modes_are_exact() -> None:
    """`specular` and `diffuse` leave the tracer and Sionna implementing one model."""
    rms = np.array(CLASS_RMS_HEIGHT_M)
    tracer_rms, scattering = mode_materials("specular", rms, WAVELENGTH_M)
    assert np.all(tracer_rms == 0.0)
    assert np.all(scattering == 0.0)
    cosine = np.linspace(0.0, 1.0, 21)
    assert np.all(specular_share(np.zeros_like(cosine), cosine, WAVELENGTH_M) == 1.0)

    tracer_rms, scattering = mode_materials("diffuse", rms, WAVELENGTH_M)
    assert np.all(scattering == 1.0)
    assert tracer_rms[0] == FULLY_DIFFUSE_RMS_HEIGHT_M
    # Everything within 89 degrees of the normal is fully diffuse, which is all
    # the measure the cosine lobe of a bounce can reach in practice.
    cosine = np.cos(np.radians(np.linspace(0.0, 89.0, 90)))
    saturated = np.full(cosine.shape, FULLY_DIFFUSE_RMS_HEIGHT_M)
    assert np.max(specular_share(saturated, cosine, WAVELENGTH_M)) < 1e-20

    tracer_rms, scattering = mode_materials("production", rms, WAVELENGTH_M)
    assert np.allclose(tracer_rms, rms)
    assert np.allclose(scattering, matched_scattering_coefficient(rms, WAVELENGTH_M))
    # Facades are the specular class and paving the diffuse one, and the shipped
    # roughness has to keep them on opposite sides of the split.
    assert scattering[1] < 0.7
    assert scattering[0] > 0.85


def test_unknown_mode_is_refused() -> None:
    with pytest.raises(ValueError):
        mode_materials("microfacet", np.array(CLASS_RMS_HEIGHT_M), WAVELENGTH_M)
    assert MODES == ("specular", "diffuse", "production")


# ---------------------------------------------------------------------------
# The triangles have to be the same triangles
# ---------------------------------------------------------------------------


def test_write_ply_round_trips_through_mitsuba(tmp_path) -> None:
    rng = np.random.default_rng(0)
    vertices = rng.normal(size=(64, 3)) * 10.0
    faces = rng.integers(0, 64, size=(40, 3))
    faces = faces[(faces[:, 0] != faces[:, 1]) & (faces[:, 1] != faces[:, 2]) & (faces[:, 0] != faces[:, 2])]
    path = tmp_path / "mesh.ply"
    path.write_bytes(write_ply(vertices, faces))

    from semantic_twin.propagation.geometry import MitsubaGeometry

    loaded = MitsubaGeometry(path, variant="llvm_ad_rgb")
    assert loaded.faces.shape == faces.shape
    assert np.allclose(loaded.vertices, vertices.astype(np.float32), atol=0.0)
    assert np.array_equal(loaded.faces, faces)


def test_split_mesh_by_class_keeps_every_triangle() -> None:
    rng = np.random.default_rng(1)
    vertices = rng.normal(size=(200, 3))
    faces = np.stack([rng.permutation(200)[:3] for _ in range(120)])
    face_class = rng.integers(0, 4, size=120)
    names = ("ground", "facade", "roof", "soffit")
    blobs = split_mesh_by_class(vertices, faces, face_class, names)
    assert set(blobs) <= set(names)
    header_counts = 0
    for blob in blobs.values():
        header = blob[: blob.index(b"end_header")].decode("ascii")
        header_counts += int([line for line in header.splitlines() if line.startswith("element face")][0].split()[-1])
    assert header_counts == faces.shape[0]


# ---------------------------------------------------------------------------
# The sky integral has to be the same integral
# ---------------------------------------------------------------------------


def test_mixture_proposal_bounds_every_importance_weight() -> None:
    """No source direction can dominate, which is what makes a few hundred enough."""
    sky = sample_sky(MODELS, 4000, np.random.default_rng(3))
    for name in MODELS:
        weight = sky.weight(name)
        assert np.all(weight >= 0.0)
        assert np.max(weight) <= len(MODELS) + 1e-9


def test_free_space_transfer_integrates_to_one_under_every_model() -> None:
    """The parameter free identity, on the oracle side of the comparison.

    `T = 1` everywhere is free space, and `Q` is normalised to integrate to one
    over the sphere, so every model has to come back at one. This exercises the
    elevation inverse transform sampling, the mixture density and the estimator
    together, and it is the Sionna side's answer to section 8.1.
    """
    sky = sample_sky(MODELS, 20_000, np.random.default_rng(5))
    for name, (value, error) in susceptibility(np.ones(len(sky)), sky).items():
        assert abs(value - 1.0) < 4.0 * error + 1e-9, name
        assert abs(value - 1.0) < 0.05, name


def test_band_transfer_is_flat_in_free_space() -> None:
    sky = sample_sky(MODELS, 20_000, np.random.default_rng(11))
    edges = np.linspace(-1.0, 1.0, 19)
    profile, error = band_transfer(np.ones(len(sky)), sky, edges)
    assert np.all(np.abs(profile - 1.0) < 4.0 * error + 0.02)


def test_sky_sample_respects_each_support() -> None:
    sky = sample_sky(MODELS, 3000, np.random.default_rng(7))
    elevation = np.degrees(np.arcsin(np.clip(sky.directions[:, 2], -1.0, 1.0)))
    for name, model in MODELS.items():
        inside = sky.density[name] > 0.0
        assert np.all(elevation[inside] >= model.elevation_min_deg - 1e-6)
        assert np.all(elevation[inside] <= model.elevation_max_deg + 1e-6)
    assert np.any(elevation < 0.0)


# ---------------------------------------------------------------------------
# The convergence curves have to measure the production estimator
# ---------------------------------------------------------------------------


def _plane_trace(rays: int = 20_000, max_bounces: int = 4):
    config = TraceConfig(
        frequency_hz=FREQUENCY_HZ,
        rays=rays,
        local_cells=256,
        max_bounces=max_bounces,
        roulette_start=max_bounces + 1,
        seed=1,
        batch=rays,
    )
    tracer = SbrTracer(
        PlaneGeometry(0.0),
        None,
        np.array([complex(5.24, -0.46055233)]),
        np.array([0.002]),
        config,
    )
    recorder = PathRecorder(capacity=rays)
    result = tracer.trace(np.array([0.0, 0.0, 1.5]), MODELS, recorder=recorder, seed=1)
    return tracer, result, recorder.result()


def test_recorded_susceptibility_reproduces_the_production_estimator() -> None:
    """The rebuild is the same arithmetic, not an equivalent one.

    If this drifts the dynamic range curve stops describing the shipped
    estimator, so the tolerance is exact equality up to float64 summation order.
    """
    tracer, result, record = _plane_trace()
    rebuilt = recorded_susceptibility(record, MODELS, tracer.local_grid)
    for name in MODELS:
        assert rebuilt[name] == pytest.approx(result.susceptibility[name], rel=1e-12)


def test_throughput_floor_is_monotone_and_saturates() -> None:
    """More dynamic range can only retain more, and enough retains everything."""
    tracer, result, record = _plane_trace()
    values = [
        recorded_susceptibility(record, MODELS, tracer.local_grid, throughput_floor=10.0 ** (-d / 10.0))["isotropic"]
        for d in (2.0, 5.0, 10.0, 20.0, 40.0)
    ]
    assert np.all(np.diff(values) >= -1e-15)
    assert values[0] < result.susceptibility["isotropic"]
    assert values[-1] == pytest.approx(result.susceptibility["isotropic"], rel=1e-12)


def test_the_floor_is_a_post_hoc_filter_only_without_roulette() -> None:
    """Monotone throughput is the whole justification, so check the premise.

    Russian roulette divides the throughput by the survival probability, which
    can raise it, and once it can rise the surviving set is no longer the set
    that never fell below the floor. This asserts the premise rather than
    trusting the docstring for it.
    """
    _, _, record = _plane_trace()
    offsets = np.asarray(record.offsets)
    throughput = np.asarray(record.throughput)
    for start, stop in zip(offsets[:-1], offsets[1:], strict=True):
        assert np.all(np.diff(throughput[start:stop]) <= 1e-15)


def test_median_change_and_the_convergence_rule() -> None:
    values = np.array([[1.0, 1.5, 1.52, 1.521], [2.0, 3.0, 3.04, 3.042]])
    change = median_change_db(values)
    assert change[0] == pytest.approx(10.0 * np.log10(1.5), rel=1e-9)
    assert change[-1] < 0.5
    assert smallest_converged(change, first=1) == 2
    assert smallest_converged(np.array([1.0, 1.0]), first=1) is None


# ---------------------------------------------------------------------------
# The oracle has to reproduce a closed form before it is allowed near a city
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not os.environ.get("SIONNA_ORACLE_TESTS"),
    reason="minutes of CPU ray tracing, set SIONNA_ORACLE_TESTS=1 to run",
)
def test_oracle_reproduces_the_ground_plane_closed_forms() -> None:
    """Both exactly matched modes, against analytic targets, through Sionna.

    Specular is `1 + R(theta)`. Fully diffuse is `1 + 2 sin(alpha) <R>`, where
    the average is uniform in `cos(theta)` because the adjoint departure
    hemisphere is uniform in solid angle and a cosine lobe leaves at elevation
    `alpha` with density `sin(alpha)/pi`.
    """
    permittivity = complex(4.83, -0.56885825)
    elevation = np.array([5.0, 10.0, 20.0, 30.0, 45.0, 60.0, 80.0])
    cosine = np.linspace(0.0, 1.0, 20_001)
    mean_reflectance = float(
        np.trapezoid(fresnel_power_reflectance(cosine, np.full(cosine.shape, permittivity)), cosine)
    )
    body = f"""
        import json
        import numpy as np
        import sys
        sys.path.insert(0, {str(__file__).rsplit("/tests/", 1)[0]!r})
        from semantic_twin.transport.sionna_check import build_payload, run_payload, write_ply

        half = 3.0e3
        vertices = np.array([[-half, -half, 0.0], [half, -half, 0.0], [half, half, 0.0], [-half, half, 0.0]])
        faces = np.array([[0, 1, 2], [0, 2, 3]])
        elevation = np.array({elevation.tolist()!r})
        directions = np.column_stack(
            [np.cos(np.radians(elevation)), np.zeros_like(elevation), np.sin(np.radians(elevation))]
        )
        out = {{}}
        for mode, scattering in (("specular", 0.0), ("diffuse", 1.0)):
            payload = build_payload(
                {{"ground": write_ply(vertices, faces)}},
                {{"ground": complex({permittivity.real!r}, {permittivity.imag!r})}},
                {{"ground": scattering}},
                {FREQUENCY_HZ!r},
                np.array([[0.0, 0.0, 1.5]]),
                directions,
                max_depth=1,
                samples_per_src=200_000,
                target_chunk=int(directions.shape[0]),
                diffuse=mode != "specular",
                seed=3,
            )
            answer = run_payload(payload)
            out[mode] = {{"total": np.asarray(answer["total"])[0].tolist(),
                          "saturated": answer["paths_high_water"] >= answer["max_num_paths_per_src"]}}
        print(json.dumps(out))
    """
    answer = _subprocess_json(body)
    targets = {
        "specular": 1.0
        + fresnel_power_reflectance(np.sin(np.radians(elevation)), np.full(elevation.shape, permittivity)),
        "diffuse": 1.0 + 2.0 * np.sin(np.radians(elevation)) * mean_reflectance,
    }
    for mode, target in targets.items():
        assert not answer[mode]["saturated"], f"{mode} overflowed the path buffer"
        residual = 10.0 * np.log10(np.array(answer[mode]["total"]) / target)
        assert np.max(np.abs(residual)) < 0.05, f"{mode}: {residual}"


def test_pec_reference_is_available_for_the_report() -> None:
    """A sanity guard on the constant the closed forms lean on."""
    assert abs(PEC_PERMITTIVITY.imag) > 1e6
