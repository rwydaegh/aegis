"""Concrete estimators preserve the two study loops they replace."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from semantic_twin.exposure.next_event_study import _trace_points
from semantic_twin.illumination import ISOTROPIC, ROOFTOP
from semantic_twin.illumination import surplus_spread_study
from semantic_twin.illumination.sources import SourceSet
from semantic_twin.transport import EscapeEstimator, Estimator, NextEventEstimator
from semantic_twin.transport.next_event import NextEventGather


class ClearGeometry:
    def intersect(self, origins: np.ndarray, directions: np.ndarray):
        del directions
        count = origins.shape[0]
        return (
            np.zeros(count, dtype=bool),
            np.full(count, np.inf),
            np.zeros((count, 3)),
            np.full(count, -1, dtype=np.int64),
        )


class RecordingTracer:
    def __init__(self, *, seed: int = 4, max_bounces: int = 3) -> None:
        self.config = SimpleNamespace(seed=seed, max_bounces=max_bounces)
        self.calls: list[dict[str, Any]] = []

    def trace(
        self,
        origin: np.ndarray,
        models: dict[str, Any],
        *,
        ground_z_m: float = 0.0,
        seed: int | None = None,
        gather: Any = None,
    ) -> Any:
        self.calls.append(
            {
                "origin": np.asarray(origin).copy(),
                "models": tuple(models),
                "ground_z_m": ground_z_m,
                "seed": seed,
            }
        )
        if gather is not None:
            count = 2
            gather.begin(origin, count)
            gather.vertex(
                np.arange(count),
                np.zeros((count, 3)),
                np.tile((-1.0, 0.0, 0.0), (count, 1)),
                np.tile((1.0, 0.0, 0.0), (count, 1)),
                np.ones(count),
                np.zeros(count),
                np.ones(count, dtype=np.int64),
                np.ones(count),
            )
        susceptibility = {name: 1.25 + i for i, name in enumerate(models)}
        susceptibility_direct = {name: 0.75 + i for i, name in enumerate(models)}
        rho = {name: np.array([0.25 + i, 0.5 + i]) for i, name in enumerate(models)}
        return SimpleNamespace(
            susceptibility=susceptibility,
            susceptibility_direct=susceptibility_direct,
            rho=rho,
            sky_fraction=0.375,
            mean_bounces=1.625,
            escaped_fraction=0.875,
        )


class ProtocolSourceSet:
    """Placed illumination with no SourceSet implementation details."""

    name = "protocol_sites"
    law = "protocol_sites"
    family = "roofline"

    def __init__(self, sites: np.ndarray) -> None:
        self._sites = sites

    def sites(self) -> np.ndarray:
        return self._sites

    def __len__(self) -> int:
        return int(self._sites.shape[0])

    def describe(self) -> dict[str, Any]:
        return {"name": self.name, "law": self.law, "family": self.family}


def source_set(*positions: tuple[float, float, float]) -> SourceSet:
    return SourceSet(
        positions=np.asarray(positions, dtype=np.float64).reshape((-1, 3)),
        cell_m=1.0,
        dims=3,
        azimuths=12,
        builders=2,
    )


def legacy_next_event(
    tracer: RecordingTracer,
    geometry: ClearGeometry,
    sources: SourceSet,
    origin: np.ndarray,
    *,
    seed: int,
) -> dict[str, Any]:
    """The former body of ``next_event_study._trace_points``."""
    models = {"isotropic": ISOTROPIC, "rooftop": ROOFTOP}
    direct, seen = sources.direct(geometry, np.atleast_2d(origin))
    gather = NextEventGather(
        geometry=geometry,
        sources=sources,
        rng=np.random.default_rng(seed + 1000),
        samples=1,
        max_order=3,
    )
    point = tracer.trace(origin, models, ground_z_m=-2.0, seed=seed, gather=gather)
    bounced = gather.chi_bounce()
    total = float(direct[0]) + bounced
    return {
        "direct": float(direct[0]),
        "bounced": bounced,
        "surplus": total / direct[0] if direct[0] > 0.0 else float("nan"),
        "surplus_db": 10.0 * np.log10(total / direct[0]) if direct[0] > 0.0 else float("nan"),
        "by_order": [float(value) for value in gather.chi_by_order()],
        "visible_fraction": float(seen[0]),
        "sky_fraction": point.sky_fraction,
        "mean_bounces": point.mean_bounces,
        "escape_chi": {name: point.susceptibility[name] for name in models},
        "escape_chi_direct": {name: point.susceptibility_direct[name] for name in models},
        "connections": gather.connections,
        "clear_fraction": gather.cleared / max(gather.connections, 1),
    }


def test_both_concrete_estimators_satisfy_the_runtime_protocol() -> None:
    geometry = ClearGeometry()
    tracer = RecordingTracer()

    escape = EscapeEstimator(tracer, ISOTROPIC)
    next_event = NextEventEstimator(tracer, geometry, source_set((2.0, 0.0, 0.0)))

    assert isinstance(escape, Estimator)
    assert isinstance(next_event, Estimator)
    assert escape.illumination() is ISOTROPIC
    assert next_event.illumination() is next_event.sources


def test_escape_estimator_passes_one_law_and_exposes_the_angular_trace() -> None:
    tracer = RecordingTracer()
    estimator = EscapeEstimator(tracer, ISOTROPIC)

    point = estimator.trace(np.array((1.0, 2.0, 3.0)), ground_z_m=-4.0, seed=19)
    result = estimator.estimate(np.array((1.0, 2.0, 3.0)), ground_z_m=-4.0, seed=19)

    assert len(tracer.calls) == 2
    assert np.array_equal(tracer.calls[0]["origin"], np.array((1.0, 2.0, 3.0)))
    assert tracer.calls[0]["models"] == ("isotropic",)
    assert tracer.calls[0]["ground_z_m"] == -4.0
    assert tracer.calls[0]["seed"] == 19
    assert result.estimator == "escape"
    assert result.law == ISOTROPIC.law
    assert result.direct == 0.75
    assert result.total == 1.25
    assert np.array_equal(point.rho["isotropic"], np.array((0.25, 0.5)))
    assert "rho" not in result.detail


def test_next_event_estimator_is_exactly_the_former_study_loop() -> None:
    geometry = ClearGeometry()
    sources = source_set((2.0, 0.0, 0.0), (4.0, 0.0, 0.0))
    origin = np.array((0.0, 0.0, 1.0))
    expected = legacy_next_event(RecordingTracer(), geometry, sources, origin, seed=12)
    tracer = RecordingTracer()
    estimator = NextEventEstimator(
        tracer,
        geometry,
        sources,
        samples=1,
        max_order=3,
        diagnostic_models={"isotropic": ISOTROPIC, "rooftop": ROOFTOP},
    )

    result = estimator.estimate(origin, ground_z_m=-2.0, seed=12)
    actual = {
        "direct": result.direct,
        "bounced": result.detail["bounced"],
        "surplus": result.surplus,
        "surplus_db": 10.0 * np.log10(result.surplus),
        **{name: value for name, value in result.detail.items() if name != "bounced"},
    }

    assert actual == expected
    assert tracer.calls[0]["models"] == ("isotropic", "rooftop")
    assert tracer.calls[0]["seed"] == 12


def test_next_event_uses_only_the_placed_illumination_protocol() -> None:
    geometry = ClearGeometry()
    sources = ProtocolSourceSet(np.array(((2.0, 0.0, 0.0), (4.0, 0.0, 0.0))))
    assert not hasattr(sources, "positions")
    estimator = NextEventEstimator(RecordingTracer(), geometry, sources)

    result = estimator.estimate(np.array((0.0, 0.0, 1.0)), seed=12)

    assert result.law == sources.law
    assert result.direct > 0.0
    assert result.total > result.direct


def test_next_event_study_keeps_its_per_point_schema_and_seed_order() -> None:
    geometry = ClearGeometry()
    tracer = RecordingTracer(seed=7)
    study = SimpleNamespace(
        tracer=tracer,
        geometry=geometry,
        sources=source_set((2.0, 0.0, 0.0), (4.0, 0.0, 0.0)),
        evaluate=np.array(((0.0, 0.0, 1.0), (0.0, 0.0, 2.0))),
        datum=SimpleNamespace(z_m=-3.0),
        config=SimpleNamespace(connections=1, max_bounces=3, seed=7),
    )

    rows = _trace_points(study)

    assert tuple(rows[0]) == (
        "origin",
        "direct",
        "bounced",
        "surplus",
        "surplus_db",
        "by_order",
        "visible_fraction",
        "sky_fraction",
        "mean_bounces",
        "escape_chi",
        "escape_chi_direct",
        "connections",
        "clear_fraction",
    )
    assert [call["seed"] for call in tracer.calls] == [7, 8]
    assert [call["ground_z_m"] for call in tracer.calls] == [-3.0, -3.0]


def test_surplus_spread_one_seed_is_exactly_the_former_study_loop(monkeypatch) -> None:
    points = np.array([(float(index), float(index % 2), 1.5 + 0.1 * index) for index in range(8)])
    geometry = ClearGeometry()
    geometry.vertices = np.zeros((3, 3))
    geometry.faces = np.array(((0, 1, 2),))
    sources = source_set((10.0, 1.0, 8.0), (14.0, -2.0, 12.0))
    built_from: list[np.ndarray] = []
    actual_tracers: list[RecordingTracer] = []

    monkeypatch.setattr(surplus_spread_study.paths, "site_mesh", lambda site, crop: (site, crop))
    monkeypatch.setattr(surplus_spread_study, "MitsubaGeometry", lambda mesh, variant: geometry)
    monkeypatch.setattr(
        surplus_spread_study,
        "measure_ground_datum",
        lambda scene, radius_m: SimpleNamespace(z_m=-1.25),
    )
    monkeypatch.setattr(
        surplus_spread_study,
        "site_walk",
        lambda scene, site, stride_m: (SimpleNamespace(points=points), None),
    )
    monkeypatch.setattr(
        surplus_spread_study,
        "build_source_set",
        lambda scene, builders, silhouette_fn, **kwargs: built_from.append(builders.copy()) or sources,
    )
    monkeypatch.setattr(
        surplus_spread_study,
        "classify_faces",
        lambda vertices, faces, ground_z_m: np.zeros(faces.shape[0], dtype=np.int64),
    )
    monkeypatch.setattr(
        surplus_spread_study,
        "load_table",
        lambda config, frequency_hz: SimpleNamespace(
            permittivity=np.array((1.0 + 0.0j,)),
            rms_height_m=np.array((0.0,)),
        ),
    )

    def make_tracer(scene, face_class, permittivity, rms_height_m, config):
        del scene, face_class, permittivity, rms_height_m
        tracer = RecordingTracer(seed=config.seed, max_bounces=config.max_bounces)
        actual_tracers.append(tracer)
        return tracer

    monkeypatch.setattr(surplus_spread_study, "SbrTracer", make_tracer)
    args = SimpleNamespace(
        crop_m=130.0,
        variant="scalar_rgb",
        walk_radius_m=100.0,
        walk_stride_m=2.0,
        held_out_fraction=0.375,
        builders=2,
        azimuths=24,
        elevations=12,
        cell_m=1.0,
        site_lift_m=0.2,
        frequency_hz=15.0e9,
        rays=64,
        max_bounces=3,
        connections=1,
    )
    seed = 17

    actual = surplus_spread_study.one_seed("test_square", seed, args)

    order = np.random.default_rng(0).permutation(points.shape[0])
    held = max(2, round(points.shape[0] * args.held_out_fraction))
    evaluate, pool = points[order[:held]], points[order[held:]]
    builder_index = np.linspace(0, pool.shape[0] - 1, min(args.builders, pool.shape[0])).round().astype(int)
    expected_tracer = RecordingTracer(seed=seed, max_bounces=args.max_bounces)
    expected_rows = [
        legacy_next_event(expected_tracer, geometry, sources, origin, seed=seed + index)
        for index, origin in enumerate(evaluate)
    ]
    expected = float(np.nanmedian([row["surplus_db"] for row in expected_rows]))

    assert actual == expected
    assert len(actual_tracers) == 1
    assert np.array_equal(built_from[0], pool[builder_index])
    assert [call["seed"] for call in actual_tracers[0].calls] == [seed, seed + 1, seed + 2]
    assert all(
        np.array_equal(call["origin"], origin) for call, origin in zip(actual_tracers[0].calls, evaluate, strict=True)
    )


@pytest.mark.xfail(
    strict=True,
    reason="known defect: direct accepts a source inside the gather's 0.5 m floor",
)
def test_near_source_uses_the_same_floor_for_direct_and_bounced_terms() -> None:
    geometry = ClearGeometry()
    estimator = NextEventEstimator(
        RecordingTracer(),
        geometry,
        source_set((0.25, 0.0, 0.0)),
    )

    result = estimator.estimate(np.zeros(3), seed=2)

    assert result.direct == 0.0
