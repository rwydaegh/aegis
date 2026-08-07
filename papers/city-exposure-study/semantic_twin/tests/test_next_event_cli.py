from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np

from semantic_twin.cli import next_event
from semantic_twin.exposure import next_event_study
from semantic_twin.exposure.next_event_study import NextEventStudyConfig
from semantic_twin.materials import FINISH_ONLY_RULE


def test_defaults_match_the_historical_next_event_command() -> None:
    args = next_event.arguments([])
    assert vars(args) == {
        "sites": ["korenmarkt", "brussels_grandplace"],
        "crop_m": 250,
        "rays": 200_000,
        "builders": 128,
        "held_out": 16,
        "azimuths": 1440,
        "elevations": 600,
        "cell_m": 1.0,
        "dims": 3,
        "site_lift_m": 0.5,
        "connections": 1,
        "frequency_hz": 15.0e9,
        "max_bounces": 3,
        "walk_radius_m": 90.0,
        "head_height_m": 1.5,
        "walk": "route",
        "walk_path": "links",
        "walk_stride_m": 6.0,
        "drop_clutter": False,
        "seed": 7,
        "variant": "llvm_ad_rgb",
        "transport_kernel": "numpy",
        "launch_sampling": "iid",
        "specular_order": 1,
        "tag": "next_event",
    }


def test_cli_dispatches_a_typed_config(monkeypatch) -> None:
    calls: list[NextEventStudyConfig] = []
    monkeypatch.setattr(next_event, "run_next_event_study", calls.append)

    status = next_event.main(
        [
            "--sites",
            "one",
            "two",
            "--crop-m",
            "90",
            "--rays",
            "10",
            "--builders",
            "4",
            "--held-out",
            "3",
            "--azimuths",
            "20",
            "--elevations",
            "10",
            "--cell-m",
            "2",
            "--dims",
            "2",
            "--site-lift-m",
            "1.25",
            "--connections",
            "5",
            "--frequency-hz",
            "2e9",
            "--max-bounces",
            "2",
            "--walk-radius-m",
            "30",
            "--head-height-m",
            "1.7",
            "--walk",
            "grid",
            "--walk-path",
            "closest",
            "--walk-stride-m",
            "2.5",
            "--drop-clutter",
            "--seed",
            "19",
            "--variant",
            "cuda_ad_rgb",
            "--transport-kernel",
            "drjit",
            "--launch-sampling",
            "rotated_fibonacci",
            "--specular-order",
            "0",
            "--tag",
            "trial",
        ]
    )

    assert status == 0
    assert calls == [
        NextEventStudyConfig(
            sites=("one", "two"),
            crop_m=90,
            rays=10,
            builders=4,
            held_out=3,
            azimuths=20,
            elevations=10,
            cell_m=2.0,
            dims=2,
            site_lift_m=1.25,
            connections=5,
            frequency_hz=2.0e9,
            max_bounces=2,
            walk_radius_m=30.0,
            head_height_m=1.7,
            walk="grid",
            walk_path="closest",
            walk_stride_m=2.5,
            drop_clutter=True,
            seed=19,
            variant="cuda_ad_rgb",
            transport_kernel="drjit",
            launch_sampling="rotated_fibonacci",
            specular_order=0,
            tag="trial",
        )
    ]


def test_compatibility_facade_forwards_its_historical_hook(monkeypatch) -> None:
    import run_next_event

    calls: list[NextEventStudyConfig] = []
    monkeypatch.setattr(run_next_event, "run_next_event_study", calls.append)
    assert run_next_event.main(["--sites", "one"]) == 0
    assert calls and calls[0].sites == ("one",)


def test_standalone_next_event_path_selects_finish_only_and_forwards_its_rms(monkeypatch, tmp_path) -> None:
    captured = {}
    geometry = SimpleNamespace(
        vertices=np.zeros((3, 3)),
        faces=np.array([[0, 1, 2]], dtype=np.int64),
    )
    table = SimpleNamespace(
        permittivity=np.array([4.0 - 0.1j]),
        rms_height_m=np.array([0.00125]),
    )

    class Tracer:
        def __init__(self, _geometry, _face_class, permittivity, rms_height_m, _trace_config):
            captured["permittivity"] = permittivity
            captured["rms_height_m"] = rms_height_m

    monkeypatch.setattr(next_event_study, "MitsubaGeometry", lambda *_args, **_kwargs: geometry)
    monkeypatch.setattr(
        next_event_study,
        "measure_ground_datum",
        lambda *_args, **_kwargs: SimpleNamespace(z_m=0.0),
    )
    monkeypatch.setattr(
        next_event_study,
        "_standpoints",
        lambda *_args, **_kwargs: (np.array([[0.0, 0.0, 1.5]]), np.array([[1.0, 0.0, 1.5]])),
    )
    monkeypatch.setattr(next_event_study, "site_clutter", lambda *_args, **_kwargs: (None, {}))
    monkeypatch.setattr(next_event_study, "build_source_set", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(next_event_study, "classify_faces", lambda *_args, **_kwargs: np.array([0]))

    def load_table(*_args, **kwargs):
        captured["roughness_rule"] = kwargs.get("roughness_rule")
        return table

    monkeypatch.setattr(next_event_study, "load_table", load_table)
    monkeypatch.setattr(next_event_study, "SbrTracer", Tracer)

    next_event_study._prepare_site(
        "test-site",
        tmp_path / "mesh.ply",
        NextEventStudyConfig(sites=("test-site",), root=tmp_path, rays=8),
    )

    assert captured["roughness_rule"] == FINISH_ONLY_RULE
    assert np.array_equal(captured["permittivity"], table.permittivity)
    assert np.array_equal(captured["rms_height_m"], table.rms_height_m)


def test_standalone_next_event_selects_the_resident_device_tracer(monkeypatch, tmp_path) -> None:
    geometry = SimpleNamespace(
        vertices=np.zeros((3, 3)),
        faces=np.array([[0, 1, 2]], dtype=np.int64),
    )
    table = SimpleNamespace(
        permittivity=np.array([4.0 - 0.1j]),
        rms_height_m=np.array([0.00125]),
    )
    seen = {}

    class DeviceTracer:
        def __init__(self, _geometry, _face_class, _permittivity, _rms_height_m, trace_config):
            seen["trace_config"] = trace_config

    monkeypatch.setattr(next_event_study, "MitsubaGeometry", lambda *_args, **_kwargs: geometry)
    monkeypatch.setattr(
        next_event_study,
        "measure_ground_datum",
        lambda *_args, **_kwargs: SimpleNamespace(z_m=0.0),
    )
    monkeypatch.setattr(
        next_event_study,
        "_standpoints",
        lambda *_args, **_kwargs: (np.array([[0.0, 0.0, 1.5]]), np.array([[1.0, 0.0, 1.5]])),
    )
    monkeypatch.setattr(next_event_study, "site_clutter", lambda *_args, **_kwargs: (None, {}))
    monkeypatch.setattr(next_event_study, "build_source_set", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(next_event_study, "classify_faces", lambda *_args, **_kwargs: np.array([0]))
    monkeypatch.setattr(next_event_study, "load_table", lambda *_args, **_kwargs: table)
    monkeypatch.setattr(next_event_study, "DeviceEscapeTracer", DeviceTracer)

    study = next_event_study._prepare_site(
        "test-site",
        tmp_path / "mesh.ply",
        NextEventStudyConfig(
            sites=("test-site",),
            root=tmp_path,
            rays=8,
            transport_kernel="drjit",
            specular_order=0,
        ),
    )

    assert isinstance(study.tracer, DeviceTracer)
    assert seen["trace_config"].rays == 8


def test_site_row_records_the_launch_design(tmp_path) -> None:
    class Sources:
        def __len__(self) -> int:
            return 3

        def source_provenance(self) -> dict[str, object]:
            return {"count": 3}

    config = NextEventStudyConfig(
        sites=("test-site",),
        root=tmp_path,
        launch_sampling="rotated_fibonacci",
    )
    study = SimpleNamespace(
        site="test-site",
        mesh=tmp_path / "mesh.ply",
        started=0.0,
        sources=Sources(),
        datum=SimpleNamespace(z_m=4.0),
        evaluate=np.zeros((1, 3)),
        clutter_report={"used": False},
        config=config,
    )
    row = next_event_study._site_row(
        study,
        [
            {
                "surplus_db": 1.0,
                "visible_fraction": 0.5,
                "escape_chi": {"rooftop": 2.0},
                "escape_chi_direct": {"rooftop": 1.0},
            }
        ],
    )

    assert row["launch_sampling"] == "rotated_fibonacci"


def test_standalone_output_records_the_launch_design(monkeypatch, tmp_path) -> None:
    mesh = tmp_path / "mesh.ply"
    config = NextEventStudyConfig(
        sites=("test-site",),
        root=tmp_path,
        launch_sampling="rotated_fibonacci",
        tag="sampling",
    )
    monkeypatch.setattr(next_event_study, "site_mesh", lambda *_args, **_kwargs: mesh)
    monkeypatch.setattr(next_event_study, "_prepare_site", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(next_event_study, "_trace_points", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        next_event_study,
        "_site_row",
        lambda *_args, **_kwargs: {"site": "test-site", "launch_sampling": config.launch_sampling},
    )

    path = next_event_study.run_next_event_study(config)
    payload = json.loads(path.read_text())

    assert payload["launch_sampling"] == "rotated_fibonacci"
    assert payload["rows"][0]["launch_sampling"] == "rotated_fibonacci"
