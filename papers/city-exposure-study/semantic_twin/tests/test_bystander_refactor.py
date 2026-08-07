"""Boundary and deterministic regressions for the split bystander modules."""

from __future__ import annotations

import ast
import io
import json
import pathlib
from types import SimpleNamespace

import numpy as np
import pytest

from semantic_twin.exposure import bystander_study
from semantic_twin.exposure.bystander_study import (
    StudyRunConfig,
    _finished_locations,
)
from semantic_twin.propagation.bystander_geometry import (
    BodyLibrary,
    CrowdConfig,
    sample_crowd,
)
from semantic_twin.report.bystanders import summarise_study
from semantic_twin.transport.tracer import DEFAULT_MAX_BOUNCES


ROOT = pathlib.Path(__file__).resolve().parents[1]
DOMAIN_MODULES = (
    ROOT / "semantic_twin" / "propagation" / "bystander_geometry.py",
    ROOT / "semantic_twin" / "exposure" / "bystander_study.py",
    ROOT / "semantic_twin" / "report" / "bystanders.py",
)


class _RecordingPlane:
    def __init__(self) -> None:
        self.batch_sizes: list[int] = []

    def intersect(self, origins, directions):  # noqa: ANN001, ANN202
        self.batch_sizes.append(origins.shape[0])
        count = origins.shape[0]
        return (
            np.ones(count, dtype=bool),
            origins[:, 2],
            np.tile(np.array([0.0, 0.0, 1.0]), (count, 1)),
            np.zeros(count, dtype=np.int64),
        )


class _RecordingRows(io.StringIO):
    def __init__(self) -> None:
        super().__init__()
        self.flushes = 0

    def flush(self) -> None:
        self.flushes += 1
        super().flush()


def _library() -> BodyLibrary:
    vertices = np.array(
        [
            [-0.25, -0.15, 0.0],
            [0.25, -0.15, 0.0],
            [0.25, 0.15, 0.0],
            [-0.25, 0.15, 0.0],
            [-0.25, -0.15, 1.75],
            [0.25, -0.15, 1.75],
            [0.25, 0.15, 1.75],
            [-0.25, 0.15, 1.75],
        ]
    )
    faces = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int64)
    heights = np.array([1.6, 1.75, 1.9])
    return BodyLibrary(
        body_ids=("a", "b", "c"),
        vertices=tuple(vertices * (height / 1.75) for height in heights),
        faces=(faces, faces, faces),
        stature_m=heights,
        width_m=np.full(3, 2.0 * (0.5 + 0.3) / np.pi) * heights / 1.75,
    )


@pytest.mark.parametrize("path", DOMAIN_MODULES)
def test_split_domain_modules_have_no_command_entry_point(path: pathlib.Path) -> None:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {alias.name for node in tree.body if isinstance(node, ast.Import) for alias in node.names}
    functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    assert "argparse" not in imports
    assert "main" not in functions
    assert "__main__" not in source


def test_compatibility_module_exports_the_deliberate_surface_only() -> None:
    from semantic_twin.propagation import bystanders

    expected = (
        "BodyLibrary",
        "Crowd",
        "CrowdConfig",
        "crowd_geometry",
        "crowd_transmittance",
        "run_study",
        "noise_floor",
        "summarise_study",
        "plot_study",
        "plot_mechanism",
        "site_mesh",
        "ground_datum",
    )
    assert all(hasattr(bystanders, name) for name in expected)
    assert bystanders.DEFAULT_MAX_BOUNCES == DEFAULT_MAX_BOUNCES
    assert not hasattr(bystanders, "time")


def test_crowd_sampling_keeps_probe_count_and_random_draw_order() -> None:
    geometry = _RecordingPlane()
    crowd = sample_crowd(
        geometry,
        np.array([1.25, -2.5]),
        0.0,
        _library(),
        CrowdConfig(density_per_m2=0.04, max_radius_m=5.0, seed=23),
    )

    assert geometry.batch_sizes == [4096, 256]
    np.testing.assert_allclose(
        crowd.positions_xy,
        np.array(
            [
                [-1.2351414159785654, -5.388431398002886],
                [0.5761441395034408, -2.361764651276968],
                [-1.8871783457788194, -1.9260757650524878],
            ]
        ),
        rtol=0.0,
        atol=1.0e-15,
    )
    assert crowd.yaw_rad == pytest.approx([0.23092708414573246, 4.766030941055904, 6.027834400106871])
    assert crowd.shape_index.tolist() == [0, 2, 2]
    assert crowd.provenance["hard_core_attempts"] == 1


def test_resume_keeps_complete_locations_and_drops_partial_ones(tmp_path: pathlib.Path) -> None:
    rows = [
        {"kind": "baseline", "location": 4},
        {"kind": "crowd", "location": 4, "realisation": 0},
        {"kind": "crowd", "location": 4, "realisation": 1},
        {"kind": "baseline", "location": 9},
        {"kind": "crowd", "location": 9, "realisation": 0},
    ]
    path = tmp_path / "rows.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))

    assert _finished_locations(path, expected_crowd_rows=2) == {4}
    assert path.read_text() == "".join(json.dumps(row) + "\n" for row in rows[:3])


def test_site_mesh_uses_the_canonical_format_gate(tmp_path: pathlib.Path) -> None:
    """A newer plain build beats an adjacent but refused ``_f64`` build."""
    directory = tmp_path / "data" / "geometry" / "fixture"
    directory.mkdir(parents=True)
    f64 = directory / "inhouse_leaf_250m_f64.ply"
    plain = directory / "inhouse_leaf_250m.ply"
    f64.write_bytes(b"old f64")
    plain.write_bytes(b"format-v3")
    f64.with_suffix(".json").write_text(json.dumps({"format_version": 2}))
    plain.with_suffix(".json").write_text(json.dumps({"format_version": 3}))

    bystander_study.paths.forget_disk_reads()
    assert bystander_study.site_mesh(tmp_path, "fixture", 250) == plain


def test_study_writer_keeps_loop_seed_and_flush_order(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> None:
    events: list[tuple[object, ...]] = []
    library = _library()
    baseline = SimpleNamespace(
        susceptibility={"isotropic": 2.0},
        local_grid=np.array([[0.0, 0.0, 1.0]]),
        rho={"isotropic": np.array([2.0])},
        local_solid_angle=1.0,
        sky_fraction=0.4,
        mean_bounces=1.2,
        seconds=3.0,
    )
    traced = SimpleNamespace(
        susceptibility={"isotropic": 1.5},
        sky_fraction=0.3,
        mean_bounces=1.4,
        seconds=4.0,
    )

    class BaselineTracer:
        def trace(self, point, models, *, ground_z_m, seed):  # noqa: ANN001, ANN202
            events.append(("baseline", seed, ground_z_m, tuple(models)))
            return baseline

    class CrowdTracer:
        def __init__(self, *args):  # noqa: ANN002
            events.append(("build_tracer",))

        def trace(self, point, models, *, ground_z_m, seed):  # noqa: ANN001, ANN202
            events.append(("crowd_trace", seed, ground_z_m, tuple(models)))
            return traced

    class FakeCrowd:
        radius_m = 30.0
        provenance = {"walkable_fraction": 0.75}
        effective_density_per_m2 = 0.075
        achieved_density_per_m2 = 0.1

        def __len__(self) -> int:
            return 12

    def sample(geometry, centre, datum, selected_library, config):  # noqa: ANN001, ANN202
        events.append(("sample", config.density_per_m2, config.seed))
        assert selected_library is library
        return FakeCrowd()

    monkeypatch.setattr(bystander_study, "sample_crowd", sample)
    monkeypatch.setattr(bystander_study, "crowd_geometry", lambda config: (object(), np.zeros(1, dtype=np.int64)))
    monkeypatch.setattr(
        bystander_study,
        "crowd_transmittance",
        lambda directions, config: np.ones(directions.shape[0]),
    )
    monkeypatch.setattr("semantic_twin.transport.tracer.SbrTracer", CrowdTracer)

    points = np.zeros((6, 3))
    points[5] = [1.0, 2.0, 1.5]
    ground = np.zeros(6)
    ground[5] = 0.25
    options = StudyRunConfig(
        output_dir=tmp_path,
        bodies_dir=tmp_path,
        densities=(0.1, 0.2),
        realisations=2,
        seed=7,
    )
    context = bystander_study._StudyContext(
        options=options,
        models={"isotropic": object()},
        geometry=object(),
        datum=0.0,
        site_face_class=np.zeros(1, dtype=np.int64),
        permittivity=np.ones(1, dtype=np.complex128),
        rms_height=np.zeros(1),
        trace_config=object(),
        baseline_tracer=BaselineTracer(),
        libraries={"as_reconstructed": library, "adult": library},
        walk=SimpleNamespace(points=points, ground_z_m=ground),
        picks=np.array([5]),
        head_height_m=1.5,
        body_class_index=1,
        scratch=tmp_path,
    )
    rows = _RecordingRows()

    bystander_study._StudyWriter(context, rows).write_location(0, 5)

    written = [json.loads(line) for line in rows.getvalue().splitlines()]
    assert rows.flushes == 9
    assert [row["kind"] for row in written] == ["baseline"] + ["crowd"] * 8
    assert [row.get("stature_mode") for row in written[1:]] == [
        "as_reconstructed",
        "as_reconstructed",
        "as_reconstructed",
        "as_reconstructed",
        "adult",
        "adult",
        "adult",
        "adult",
    ]
    assert [row["density_per_m2"] for row in written[1:]] == [0.1, 0.1, 0.2, 0.2] * 2
    assert [row["realisation"] for row in written[1:]] == [0, 1, 0, 1] * 2
    assert [event for event in events if event[0] == "sample"] == [
        ("sample", 0.1, 39602),
        ("sample", 0.1, 39699),
        ("sample", 0.2, 39602),
        ("sample", 0.2, 39699),
    ] * 2
    assert [event[1] for event in events if event[0] == "crowd_trace"] == [5007] * 8


def test_summary_keeps_arm_schema_and_location_pairing(tmp_path: pathlib.Path) -> None:
    rows = []
    for location, baseline in ((1, 10.0), (2, 20.0)):
        rows.append(
            {
                "kind": "baseline",
                "location": location,
                "chi_isotropic": baseline,
                "arriving_below_5deg_isotropic": 0.25,
                "arriving_below_2deg_isotropic": 0.10,
            }
        )
        for realisation, scale in enumerate((0.5, 0.7)):
            rows.append(
                {
                    "kind": "crowd",
                    "location": location,
                    "stature_mode": "adult",
                    "density_per_m2": 0.3,
                    "realisation": realisation,
                    "bodies": 8 + location,
                    "crowd_radius_m": 30.0,
                    "walkable_fraction": 0.8,
                    "chi_full_isotropic": baseline * scale,
                    "chi_walkable_isotropic": baseline * scale,
                    "chi_nominal_isotropic": baseline * scale,
                }
            )
    path = tmp_path / "rows.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))

    summary = summarise_study(path)
    entry = summary["ladder"][0]
    expected_shift = 10.0 * np.log10(0.6)
    assert summary["models"] == ["isotropic"]
    assert summary["baseline_chi_median"] == {"isotropic": 15.0}
    assert entry["rows"] == 4
    assert entry["full_isotropic"]["paired_median_shift_db"] == pytest.approx(expected_shift)
    assert entry["walkable_minus_full_db_isotropic"] == pytest.approx(0.0)
    assert entry["nominal_minus_full_db_isotropic"] == pytest.approx(0.0)
