from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pytest

import run_exposure
from semantic_twin.exposure.execution import (
    ExecutionConfig,
    MaterialBinding,
    OutputFiles,
    PreparedRun,
    PreparedScene,
    _build_walk,
    _manifest,
    _transport_provenance,
    _trace_config,
    _trace_rows,
    _validate_run,
    execute,
)
from semantic_twin.exposure.sweeps import LadderSweepConfig, SweepEnvironment, run_coverage_ladder
from semantic_twin.runconfig import RunConfig
from semantic_twin.transport.tracer import TraceConfig


def escape_config(**changes) -> RunConfig:
    config = RunConfig(
        site="korenmarkt",
        law="band",
        models=("isotropic", "rooftop", "street_small_cell"),
        estimator="escape",
        next_event=None,
        walk="grid",
        materials="geometric",
        tag="trial",
    )
    return config.replace(**changes)


def test_the_legacy_driver_builds_the_live_run_config_without_changing_its_defaults():
    config, execution = run_exposure._escape_config(
        0,
        200_000,
        15.0e9,
        variant="llvm_ad_rgb",
        seed=7,
        tag="korenmarkt",
        local_cells=512,
        walk_radius_m=90.0,
        walk_spacing_m=3.0,
        max_bounces=6,
        materials="geometric",
        site="korenmarkt",
        crop_m=250,
    )

    assert config.locations == 0
    assert config.models == tuple(run_exposure.MODELS)
    assert config.estimator == "escape"
    assert config.walk == "grid"
    assert config.crop_m == 250
    assert config.max_bounces == 6
    assert config.roulette_start == 4
    assert config.transport_kernel == "numpy"
    assert config.head_height_m == 1.5
    assert execution == ExecutionConfig()


def test_explicit_none_keeps_the_legacy_tracer_default_at_a_larger_bounce_budget():
    options = {
        "variant": "llvm_ad_rgb",
        "seed": 7,
        "tag": "korenmarkt",
        "local_cells": 512,
        "walk_radius_m": 90.0,
        "walk_spacing_m": 3.0,
        "max_bounces": 6,
        "materials": "geometric",
        "roulette_start": None,
    }

    config, _execution = run_exposure._escape_config(1, 100, 15.0e9, **options)

    assert config.roulette_start == 4
    assert RunConfig(site="korenmarkt", max_bounces=6).effective_roulette_start == 7


@pytest.mark.parametrize(
    ("config", "message"),
    [
        (RunConfig(site="korenmarkt"), "band/escape/grid"),
        (escape_config(models=("isotropic",)), "requires the rooftop model"),
        (escape_config(models=("rooftop", "invented")), "unknown illumination models: invented"),
    ],
)
def test_executor_rejects_unsupported_configs_before_it_creates_output(tmp_path, config, message):
    output = tmp_path / "output"
    environment = SimpleNamespace(
        output=output,
        models={"isotropic": object(), "rooftop": object(), "street_small_cell": object()},
    )

    with pytest.raises(ValueError, match=message):
        execute(config, ExecutionConfig(), environment)

    assert not output.exists()


@pytest.mark.parametrize(
    ("config", "execution", "message"),
    [
        (
            escape_config(transport_kernel="drjit", variant="scalar_rgb"),
            ExecutionConfig(),
            "drjit transport requires a Mitsuba JIT RGB variant",
        ),
        (
            escape_config(transport_kernel="drjit", variant="cuda_ad_rgb"),
            ExecutionConfig(workers=2),
            "Dr.Jit state cannot cross worker boundaries",
        ),
    ],
)
def test_device_executor_rejects_invalid_execution_before_it_creates_output(tmp_path, config, execution, message):
    output = tmp_path / "output"
    environment = SimpleNamespace(
        output=output,
        models={"isotropic": object(), "rooftop": object(), "street_small_cell": object()},
    )

    with pytest.raises(ValueError, match=message):
        execute(config, execution, environment)

    assert not output.exists()


@pytest.mark.parametrize("models", [("rooftop",), ("isotropic", "rooftop")])
def test_executor_accepts_supported_model_subsets(models):
    available = {"isotropic": object(), "rooftop": object(), "street_small_cell": object()}
    _validate_run(escape_config(models=models), available)


def test_every_trace_field_in_run_config_reaches_the_tracer():
    run = escape_config(
        frequency_hz=28.0e9,
        rays=123,
        local_cells=32,
        exit_bands=7,
        max_bounces=6,
        roulette_start=3,
        roulette_floor=0.2,
        ray_epsilon_m=0.004,
        range_weighted_escape=True,
        seed=19,
        batch=41,
    )

    traced = _trace_config(run, SimpleNamespace(trace_config_type=TraceConfig))

    assert traced.as_dict() == {
        "frequency_hz": 28.0e9,
        "rays": 123,
        "local_cells": 32,
        "exit_bands": 7,
        "max_bounces": 6,
        "roulette_start": 3,
        "roulette_floor": 0.2,
        "ray_epsilon_m": 0.004,
        "range_weighted_escape": True,
        "seed": 19,
        "batch": 41,
    }


def test_head_height_in_run_config_reaches_walk_construction():
    received = {}

    def build_walk(geometry, **options):
        received.update(options)
        return object()

    run = escape_config(head_height_m=1.72)
    replay = SimpleNamespace(walk_probe_z_m=None)
    scene = SimpleNamespace(geometry=object(), datum=5.0)

    _build_walk(run, replay, scene, SimpleNamespace(build_walk=build_walk))

    assert received == {
        "ground_datum_m": 5.0,
        "radius_m": 90.0,
        "spacing_m": 3.0,
        "head_height_m": 1.72,
        "seed": 7,
    }


def test_standpoint_seed_row_and_spectrum_order_are_kept(tmp_path):
    captured = {}

    class Result:
        local_grid = np.array([0.0])
        local_solid_angle = 0.5
        seconds = 1.0

        def __init__(self, value):
            self.rho = {"rooftop": np.array([value, value + 1.0])}

        def scalars(self):
            return {"chi_rooftop": 2.0, "sky_fraction": 0.25}

    def trace_standpoints(tracer, standpoints, models, workers):
        captured["standpoints"] = standpoints
        captured["models"] = tuple(models)
        captured["workers"] = workers
        return iter(((0, Result(10.0)), (1, Result(20.0))))

    class Coupler:
        def couple(self, *args):
            return SimpleNamespace(as_dict=lambda: {"peak_sab_w_m2": 0.1})

    walk = SimpleNamespace(
        points=np.array([[1.0, 0.0, 0.0], [2.0, 0.0, 0.0], [3.0, 0.0, 0.0]]),
        ground_z_m=np.array([5.0, 6.0, 7.0]),
    )
    run = escape_config(seed=7, local_cells=2, models=("rooftop",))
    environment = SimpleNamespace(
        models={"rooftop": object()},
        trace_standpoints=trace_standpoints,
        reference_s0_w_m2=1.0,
    )
    prepared = PreparedRun(
        run,
        environment,
        None,
        None,
        walk,
        np.array([2, 0]),
        None,
        object(),
        Coupler(),
    )
    files = OutputFiles(tmp_path / "rows.jsonl", tmp_path / "spectra.npz", tmp_path / "manifest.json")

    _trace_rows(prepared, ExecutionConfig(workers=3), files)

    assert [seed for _point, _ground, seed in captured["standpoints"]] == [2007, 7]
    assert captured["models"] == ("rooftop",)
    assert captured["workers"] == 3
    assert [json.loads(line)["index"] for line in files.rows.read_text().splitlines()] == [2, 0]
    saved = np.load(files.spectra)
    assert saved["index"].tolist() == [2, 0]
    assert saved["rho_rooftop"].tolist() == [[10.0, 11.0], [20.0, 21.0]]


def test_device_execute_selects_resident_tracer_and_keeps_output_contract(tmp_path, monkeypatch):
    captured = {}

    class Model:
        elevation_min_deg = 0.0
        elevation_max_deg = 90.0
        law = "band"
        height_band_m = (20.0, 40.0)
        range_band_m = (10.0, 100.0)
        description = "rooftop"

    class Geometry:
        face_count = 1
        vertices = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
        faces = np.array([[0, 1, 2]])

        def face_areas(self):
            return np.array([0.5])

    class Table:
        class_names = ("facade",)
        permittivity = np.array([4.0 - 0.1j])
        rms_height_m = np.array([0.002])

        def as_dict(self):
            return {"classes": ["facade"]}

    class DeviceTracer:
        def __init__(self, geometry, face_class, permittivity, rms_height_m, config):
            captured["tracer_args"] = (geometry, face_class, permittivity, rms_height_m, config)

    class Result:
        local_grid = np.array([[1.0, 0.0, 0.0], [-1.0, 0.0, 0.0]])
        local_solid_angle = 2.0 * np.pi
        seconds = 0.01

        def __init__(self, value):
            self.rho = {"rooftop": np.array([value, value + 1.0])}

        def scalars(self):
            return {"chi_rooftop": 0.4, "sky_fraction": 0.3}

    class Coupler:
        def couple(self, *_args):
            return SimpleNamespace(as_dict=lambda: {"peak_sab_w_m2": 0.2})

    class Walk:
        points = np.array([[1.0, 0.0, 1.5], [2.0, 0.0, 1.5], [3.0, 0.0, 1.5]])
        ground_z_m = np.zeros(3)
        provenance = {"rule": "test walk"}

        def __len__(self):
            return len(self.points)

    walk = Walk()

    def trace_standpoints(tracer, standpoints, models, workers):
        captured["tracer"] = tracer
        captured["standpoints"] = standpoints
        captured["models"] = tuple(models)
        captured["workers"] = workers
        return iter(((0, Result(10.0)), (1, Result(20.0))))

    environment = SimpleNamespace(
        output=tmp_path / "output",
        material_config=tmp_path / "materials.json",
        semantics=tmp_path / "semantics.json",
        phantom="phantom.stl",
        phantom_mass_kg=70.0,
        reference_s0_w_m2=1.0,
        frequency_note="frequency",
        crop_bound_note="crop",
        datum_cross_check_m=0.5,
        models={"rooftop": Model()},
        site_mesh=lambda _site, _crop: tmp_path / "mesh.ply",
        registered_ground_z=lambda _site: None,
        site_walk_semantics=lambda _site, _crop: None,
        site_fishnet=lambda _site: None,
        geometry_type=lambda _mesh, variant: Geometry(),
        classify_faces=lambda *_args: np.array([0]),
        bind_fishnet=None,
        bind_walk_entities=None,
        bind_walk_materials=None,
        load_table=lambda *_args, **_kwargs: Table(),
        build_walk=lambda *_args, **_kwargs: walk,
        measure_ground_datum=lambda *_args, **_kwargs: SimpleNamespace(
            z_m=0.0,
            provenance={"rule": "measured"},
            band_columns=1,
            columns=1,
            band_fraction=1.0,
        ),
        stratified_subset=lambda _walk, _locations: np.array([2, 0]),
        trace_config_type=TraceConfig,
        tracer_type=lambda *_args: pytest.fail("NumPy tracer was selected for a Dr.Jit run"),
        trace_standpoints=trace_standpoints,
        body_coupler_type=lambda *_args, **_kwargs: Coupler(),
        describe_body=lambda _coupler: {"phantom": "test"},
        report=lambda stem: tmp_path / f"{stem}.json",
    )
    monkeypatch.setattr("semantic_twin.exposure.execution.DeviceEscapeTracer", DeviceTracer)
    run = escape_config(
        transport_kernel="drjit",
        variant="cuda_ad_rgb",
        models=("rooftop",),
        local_cells=2,
        seed=11,
        locations=2,
    )

    rows = execute(run, ExecutionConfig(workers=None), environment)

    assert isinstance(captured["tracer"], DeviceTracer)
    geometry, face_class, permittivity, rms_height_m, trace_config = captured["tracer_args"]
    assert isinstance(geometry, Geometry)
    assert np.array_equal(face_class, [0])
    assert np.array_equal(permittivity, [4.0 - 0.1j])
    assert np.array_equal(rms_height_m, [0.002])
    assert trace_config.rays == run.rays
    assert captured["workers"] == 1
    assert captured["models"] == ("rooftop",)
    assert [seed for _point, _ground, seed in captured["standpoints"]] == [2011, 11]
    documents = [json.loads(line) for line in rows.read_text().splitlines()]
    assert [document["index"] for document in documents] == [2, 0]
    assert all("rooftop_peak_sab_w_m2" in document for document in documents)
    saved = np.load(environment.output / "trial_15ghz_spectra.npz")
    assert saved["rho_rooftop"].tolist() == [[10.0, 11.0], [20.0, 21.0]]
    assert saved["index"].tolist() == [2, 0]
    manifest = json.loads((environment.output / "trial_15ghz_manifest.json").read_text())
    assert manifest["transport"]["kernel"] == "drjit"


def test_llvm_device_trace_writes_one_production_location(tmp_path):
    pytest.importorskip("mitsuba")
    from semantic_twin.illumination import MODELS
    from semantic_twin.propagation.geometry import MitsubaGeometry
    from semantic_twin.transport.device_tracer import DeviceEscapeTracer
    from semantic_twin.transport.tracer import trace_standpoints

    mesh = tmp_path / "plane.ply"
    mesh.write_text(
        """ply
format ascii 1.0
element vertex 4
property float x
property float y
property float z
element face 2
property list uchar int vertex_indices
end_header
-100 -100 0
100 -100 0
100 100 0
-100 100 0
3 0 1 2
3 0 2 3
"""
    )
    run = escape_config(
        transport_kernel="drjit",
        variant="llvm_ad_rgb",
        models=("rooftop",),
        locations=1,
        rays=4_000,
        batch=1_501,
        local_cells=64,
        max_bounces=1,
        roulette_start=2,
    )
    geometry = MitsubaGeometry(mesh, variant=run.variant)
    trace_config = _trace_config(run, SimpleNamespace(trace_config_type=TraceConfig))
    tracer = DeviceEscapeTracer(
        geometry,
        np.zeros(geometry.face_count, dtype=np.int64),
        np.array([4.2 - 0.15j]),
        np.array([0.0]),
        trace_config,
    )

    class Coupler:
        def couple(self, *_args):
            return SimpleNamespace(as_dict=lambda: {"peak_sab_w_m2": 0.1})

    walk = SimpleNamespace(points=np.array([[0.0, 0.0, 1.0]]), ground_z_m=np.array([0.0]))
    environment = SimpleNamespace(
        models={"rooftop": MODELS["rooftop"]},
        trace_standpoints=trace_standpoints,
        reference_s0_w_m2=1.0,
    )
    prepared = PreparedRun(
        run,
        environment,
        None,
        None,
        walk,
        np.array([0]),
        trace_config,
        tracer,
        Coupler(),
    )
    files = OutputFiles(tmp_path / "rows.jsonl", tmp_path / "spectra.npz", tmp_path / "manifest.json")

    _trace_rows(prepared, ExecutionConfig(), files)

    row = json.loads(files.rows.read_text())
    assert row["index"] == 0
    assert row["chi_rooftop"] > 0.0
    assert row["rooftop_peak_sab_w_m2"] == 0.1
    saved = np.load(files.spectra)
    assert saved["rho_rooftop"].shape == (1, run.local_cells)
    assert saved["local_grid"].shape == (run.local_cells, 3)
    assert saved["index"].tolist() == [0]


def test_manifest_keys_keep_the_published_insertion_order(tmp_path):
    class Model:
        elevation_min_deg = 0.0
        elevation_max_deg = 90.0
        law = "law"
        height_band_m = (10.0, 20.0)
        range_band_m = None
        description = "model"

    table = SimpleNamespace(class_names=("facade",), as_dict=lambda: {"classes": ["facade"]})
    scene = PreparedScene(
        tmp_path / "mesh.ply",
        SimpleNamespace(face_count=1),
        5.0,
        {"rule": "measured"},
        np.array([0]),
        np.array([2.0]),
    )
    environment = SimpleNamespace(
        reference_s0_w_m2=1.0,
        frequency_note="frequency",
        crop_bound_note="crop",
        models={"isotropic": Model(), "rooftop": Model(), "street_small_cell": Model()},
        describe_body=lambda coupler: {"phantom": "duke"},
    )
    prepared = PreparedRun(
        escape_config(locations=1),
        environment,
        scene,
        MaterialBinding(np.array([0]), table, {"materials": "geometric"}),
        SimpleNamespace(provenance={"rule": "grid"}),
        np.array([0]),
        TraceConfig(),
        object(),
        object(),
    )

    manifest = _manifest(prepared)

    assert list(manifest) == [
        "generator",
        "created_utc",
        "site",
        "mesh",
        "mesh_triangles",
        "crop_radius_m",
        "ground_datum_m",
        "ground_datum_source",
        "ground_datum",
        "reference_s0_w_m2",
        "trace_config",
        "surface_binding",
        "semantic_binding",
        "class_area_fractions",
        "frequency_note",
        "crop_bound_note",
        "walk",
        "locations_requested",
        "locations_traced",
        "illumination_models",
        "body",
        "variant",
        "transport",
        "python",
        "storage_policy",
        "run_digest",
        "run",
    ]
    assert list(manifest["illumination_models"]) == ["isotropic", "rooftop", "street_small_cell"]
    assert manifest["run"] == prepared.run.as_dict()
    assert manifest["run_digest"] == prepared.run.digest()
    assert manifest["transport"] == {"kernel": "numpy"}


def test_device_transport_provenance_names_its_arithmetic_rng_and_versions(monkeypatch):
    monkeypatch.setattr(
        "semantic_twin.exposure.execution._distribution_version",
        lambda name: {"mitsuba": "3.8.0", "drjit": "1.3.1"}[name],
    )

    assert _transport_provenance(escape_config(transport_kernel="drjit")) == {
        "kernel": "drjit",
        "floating_point": "float32",
        "rng": {"family": "counter", "algorithm": "tea32"},
        "versions": {"mitsuba": "3.8.0", "drjit": "1.3.1"},
    }


def test_ladder_sweep_remains_seed_major_and_reuses_one_body(tmp_path):
    calls = []
    bodies = []

    def body(*args, **kwargs):
        value = object()
        bodies.append(value)
        return value

    def execute(run, execution):
        calls.append((run.seed, run.site, run.materials, execution.coupler))
        return tmp_path / "rows.jsonl"

    environment = SweepEnvironment(
        output=tmp_path,
        phantom="phantom.stl",
        phantom_mass_kg=72.4,
        body_coupler_type=body,
        site_mesh=lambda site, crop: tmp_path / "mesh.ply",
        ladder_sites=lambda sites, crop: (list(sites), {}),
        coverage_ladder=lambda site, crop, seed: (
            (f"{site}_{seed}_geometric", "geometric", "none"),
            (f"{site}_{seed}_walk", "walk", "images"),
        ),
        reusable=lambda run: False,
        execute=execute,
        coverage_report=lambda *args, **kwargs: tmp_path / "coverage.json",
        coverage_ladder_report=lambda *args, **kwargs: tmp_path / "summary.json",
        cross_city_report=lambda *args, **kwargs: None,
    )

    result = run_coverage_ladder(
        escape_config(locations=8),
        ExecutionConfig(workers=2),
        LadderSweepConfig(("alpha", "beta"), (7, 9)),
        environment,
    )

    assert result == tmp_path / "summary.json"
    assert [(seed, site, material) for seed, site, material, _body in calls] == [
        (7, "alpha", "geometric"),
        (7, "alpha", "walk"),
        (7, "beta", "geometric"),
        (7, "beta", "walk"),
        (9, "alpha", "geometric"),
        (9, "alpha", "walk"),
        (9, "beta", "geometric"),
        (9, "beta", "walk"),
    ]
    assert len(bodies) == 1
    assert all(used is bodies[0] for *_run, used in calls)
