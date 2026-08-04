"""Public boundaries of the transport package."""

from __future__ import annotations

import math

import numpy as np
import pytest

import semantic_twin.propagation as propagation
import semantic_twin.transport as transport
from semantic_twin.illumination import ISOTROPIC
from semantic_twin.illumination.sources import SourceSet


def test_surplus_reports_the_shared_ratio() -> None:
    result = transport.Surplus(estimator="escape", law="bands", direct=2.0, total=5.0)

    assert result.bounced == 3.0
    assert result.surplus == 2.5
    assert result.surplus_db == pytest.approx(10.0 * math.log10(2.5))
    assert result.as_dict()["total"] == 5.0


def test_surplus_is_undefined_without_a_direct_term() -> None:
    result = transport.Surplus(estimator="escape", law="bands", direct=0.0, total=1.0)

    assert math.isnan(result.surplus)
    assert math.isnan(result.surplus_db)


def test_each_illumination_shape_is_accepted_by_its_estimator() -> None:
    sources = SourceSet(
        positions=np.empty((0, 3)),
        cell_m=1.0,
        dims=3,
        azimuths=0,
        builders=0,
    )

    transport.require_credit("escape", ISOTROPIC)
    transport.require_credit("next_event", sources)
    with pytest.raises(TypeError, match="next_event"):
        transport.require_credit("next_event", ISOTROPIC)
    with pytest.raises(TypeError, match="escape"):
        transport.require_credit("escape", sources)


def test_multi_gather_calls_each_observer() -> None:
    calls: list[tuple[str, int]] = []

    class Observer:
        def __init__(self, name: str) -> None:
            self.name = name

        def begin(self, origin: np.ndarray, count: int) -> None:
            del origin
            calls.append((f"begin_{self.name}", count))

        def vertex(self, *args: object, **kwargs: object) -> None:
            del args, kwargs
            calls.append((f"vertex_{self.name}", 0))

    gather = transport.MultiGather((Observer("first"), Observer("second")))
    gather.begin(np.zeros(3), 7)
    gather.vertex(np.zeros(1))

    assert calls == [
        ("begin_first", 7),
        ("begin_second", 7),
        ("vertex_first", 0),
        ("vertex_second", 0),
    ]


def test_propagation_facade_keeps_the_frozen_golden_api() -> None:
    assert propagation.SbrTracer is transport.SbrTracer
    assert propagation.TraceConfig is transport.TraceConfig
    assert propagation.PathRecorder is transport.PathRecorder
    assert propagation.BounceEvidenceTally is transport.BounceEvidenceTally
