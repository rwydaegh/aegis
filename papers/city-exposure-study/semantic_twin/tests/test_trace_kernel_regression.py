"""Exact lock for the trace kernel's state transitions and observers."""

from __future__ import annotations

import hashlib

import numpy as np
import pytest

from semantic_twin.illumination import ISOTROPIC
from semantic_twin.transport import BounceEvidenceTally, PathRecorder, SbrTracer, TraceConfig
from semantic_twin.transport import tracer as tracer_module


class LeakySphere:
    """An analytic cavity with a directional opening and two face classes."""

    vertices = np.array(
        [
            [8.0, 0.0, 0.0],
            [-8.0, 0.0, 0.0],
            [0.0, 8.0, 0.0],
            [0.0, -8.0, 0.0],
            [0.0, 0.0, 8.0],
            [0.0, 0.0, -8.0],
        ]
    )

    def intersect(
        self, origins: np.ndarray, directions: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        b = np.einsum("ij,ij->i", origins, directions)
        c = np.einsum("ij,ij->i", origins, origins) - 64.0
        discriminant = b * b - c
        root = np.sqrt(np.maximum(discriminant, 0.0))
        distance = -b + root
        hit = (discriminant > 0.0) & (distance > 0.0) & (directions[:, 2] < 0.35)
        distance = np.where(hit, distance, np.inf)
        point = origins + np.where(hit, distance, 0.0)[:, None] * directions
        normal = -point
        norm = np.linalg.norm(normal, axis=1, keepdims=True)
        normal = np.divide(normal, np.where(norm > 0.0, norm, 1.0))
        face = (point[:, 0] >= 0.0).astype(np.int64)
        return hit, distance, normal, face


class TiltedLaw:
    """A portable second model whose density uses only basic arithmetic."""

    name = "tilted"
    law = "test"
    family = ""

    def normalisation(self, quadrature: int = 200_001) -> float:
        del quadrature
        return 1.0

    def density(self, directions: np.ndarray, normalisation: float | None = None) -> np.ndarray:
        del normalisation
        return (1.0 + 0.25 * directions[:, 2]) / (4.0 * np.pi)


class OpenGeometry:
    def intersect(
        self, origins: np.ndarray, directions: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        count = origins.shape[0]
        return (
            np.zeros(count, dtype=bool),
            np.full(count, np.inf),
            np.zeros_like(directions),
            np.zeros(count, dtype=np.int64),
        )


class RecordingGather:
    def __init__(self) -> None:
        self.batch_sizes: list[int] = []
        self.rows: list[tuple[np.ndarray | None, ...]] = []

    def begin(self, origin: np.ndarray, count: int) -> None:
        del origin
        self.batch_sizes.append(count)

    def vertex(self, *args: np.ndarray | None) -> None:
        self.rows.append(tuple(None if arg is None else np.asarray(arg).copy() for arg in args))


def _sha(array: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(array).tobytes()).hexdigest()


def test_trace_kernel_keeps_the_recorded_bits_and_callback_order() -> None:
    """Exercise batching, both reflections, roulette, deposits, and all observers."""
    config = TraceConfig(
        frequency_hz=15.0e9,
        rays=257,
        local_cells=31,
        exit_bands=7,
        max_bounces=4,
        roulette_start=1,
        roulette_floor=0.15,
        ray_epsilon_m=1.0e-3,
        range_weighted_escape=True,
        seed=12345,
        batch=73,
    )
    tracer = SbrTracer(
        LeakySphere(),
        np.array([0, 1]),
        np.array([complex(5.24, -0.46055233310470917), complex(3.1, -0.2)]),
        np.array([0.002, 0.007]),
        config,
    )
    recorder = PathRecorder(capacity=37, sky_distance_m=22.0)
    tally = BounceEvidenceTally(
        {"left": np.array([True, False]), "right": np.array([False, True])},
        max_depth=4,
    )
    gather = RecordingGather()

    result = tracer.trace(
        np.array([0.25, -0.5, 0.75]),
        {"tilted": TiltedLaw(), "iso": ISOTROPIC},
        ground_z_m=-8.0,
        recorder=recorder,
        tally=tally,
        gather=gather,
    )
    paths = recorder.result()

    assert tuple(result.susceptibility) == ("tilted", "iso")
    assert tuple(value.hex() for value in result.susceptibility.values()) == (
        "0x1.abb21d0fd4678p-8",
        "0x1.6d6b006c0db41p-8",
    )
    assert tuple(value.hex() for value in result.susceptibility_direct.values()) == (
        "0x1.a4ee95d593f7cp-8",
        "0x1.679d353c2a9c6p-8",
    )
    assert {name: _sha(value) for name, value in result.rho.items()} == {
        "tilted": "d506754b32c76cab544005dd0fc8de3c3dcbfecb86dff98ca37414cd972dc880",
        "iso": "0456000af1afb7be888bcaef00786cbce3d7c85dec5a98f33f3b913fcf7ede23",
    }
    assert _sha(result.exit_profile) == "764d0078390b4ed83d85039a953f5b4e939063872244f22c88252fe38482cf17"
    assert (
        result.sky_fraction.hex(),
        result.escaped_fraction.hex(),
        result.mean_bounces.hex(),
        result.mean_excess_delay_ns.hex(),
    ) == (
        "0x1.2ed12ed12ed13p-2",
        "0x1.56a956a956a95p-2",
        "0x1.3594d653594d6p-3",
        "0x1.64aa42876b5e6p+2",
    )

    observed = {
        "vertices": _sha(paths.vertices),
        "offsets": _sha(paths.offsets),
        "throughput": _sha(paths.throughput),
        "class": _sha(paths.face_class),
        "exit": _sha(paths.exit_direction),
        "bounces": _sha(paths.bounces),
        "termination": _sha(paths.termination),
        "tally_hits": _sha(tally.hits),
        "tally_throughput": _sha(tally.throughput),
    }
    assert observed == {
        "vertices": "3584eb231f5e0e28cec4223213eff9c488cbc52e91c4f7d24255d562f67b35ac",
        "offsets": "010d4f33ed7cabc69fae3abcae76d1584b6d9f06b7cd50abc826d773dd355e2b",
        "throughput": "fa4464858cf72ac201a72e52dc5e91be330d03287a1781ffb37e9a93ffb20b3b",
        "class": "e9b45648f54fb568711f50da0e89f34a359c2c1cc65c0df137a663d4eb62e2fc",
        "exit": "b2956b596c5949493dd111b9a89d2a7582996c463b01e71cc9852dd6d76544aa",
        "bounces": "bfb5378e0147c9058cf2039c6215ce97434cfa4413be86ea5397ba7a6a7a4de2",
        "termination": "9fb23c6cdb48a7f90c8e4c5579bcb8140975df681c51d96f58cfbb4caeb80279",
        "tally_hits": "5eb3b90dc74c81866ed34ea53387ae9fdb3ac40081bd913ea654efc9bbed54a8",
        "tally_throughput": "284a8b01fa1823c4b10c68e5355f332651a86b081c1a01045cd0c1451f6041f6",
    }
    assert gather.batch_sizes == [73, 73, 73, 38]
    assert len(gather.rows) == 10
    assert [
        _sha(np.concatenate([row[column] for row in gather.rows if row[column] is not None], axis=0))
        for column in range(9)
    ] == [
        "819adfff90cf42afd34f02786cbf69185e2de2204bc0863b3b16c41e5b243b98",
        "53363f3471ec412916829b4f87c959e2a92bf0b6c05fd9d9ae1de8daa6eb5f6a",
        "59e121a7a24288888c85da97a06cc4e812b5cdbb0acd7a1b7f36802aa620f5f3",
        "14ee867b68c5f2ca3bae3640b93d6cfe1ae5309ee0ea09562d60cad85042090b",
        "79d1db270f45e051ca417353029d7abdda043c4be0cc4ec363cdd8eaea31e87f",
        "722654627723af31bc1119c009607b5e74cd16ffcd181236896847b74a8f5eff",
        "6df81342358cbd95ef677256a336fb3719831ac8b1651ff6ab1e461b00299e54",
        "eed260b53567d973511b540fa38a66f2bec9a0c247bc9b443ee7e9a97c995ff4",
        "b5ee4090e41195fac886a223d99baf8f509e554ae56ea692becc84d2cbd804ae",
    ]


def test_range_weighting_keeps_the_tracer_override_hook() -> None:
    calls: list[int] = []

    class RangeHookTracer(SbrTracer):
        def _range_to_the_source_shell(
            self,
            last_vertex: np.ndarray,
            exit_direction: np.ndarray,
            path_length: np.ndarray,
        ) -> np.ndarray:
            del last_vertex, path_length
            calls.append(exit_direction.shape[0])
            return np.full(exit_direction.shape[0], 2.0)

    config = TraceConfig(rays=31, local_cells=8, exit_bands=4, batch=13, range_weighted_escape=True)
    tracer = RangeHookTracer(OpenGeometry(), None, np.array([1.0 + 0.0j]), np.array([0.0]), config)
    result = tracer.trace(np.zeros(3), {"iso": ISOTROPIC})

    assert calls == [13, 13, 5]
    assert result.susceptibility["iso"] == pytest.approx(0.25)


def test_trace_resolves_the_public_surface_functions_at_call_time(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"fresnel": 0, "share": 0}
    original_fresnel = tracer_module.fresnel_power_reflectance
    original_share = tracer_module.specular_share

    def watched_fresnel(cos_incidence: np.ndarray, permittivity: np.ndarray) -> np.ndarray:
        calls["fresnel"] += 1
        return original_fresnel(cos_incidence, permittivity)

    def watched_share(
        rms_height_m: np.ndarray,
        cos_incidence: np.ndarray,
        wavelength_m: float,
    ) -> np.ndarray:
        calls["share"] += 1
        return original_share(rms_height_m, cos_incidence, wavelength_m)

    monkeypatch.setattr(tracer_module, "fresnel_power_reflectance", watched_fresnel)
    monkeypatch.setattr(tracer_module, "specular_share", watched_share)
    config = TraceConfig(rays=31, local_cells=8, exit_bands=4, max_bounces=2, batch=13)
    tracer = SbrTracer(
        LeakySphere(),
        np.array([0, 1]),
        np.array([complex(5.24, -0.46), complex(3.1, -0.2)]),
        np.array([0.002, 0.007]),
        config,
    )

    tracer.trace(np.zeros(3), {"iso": ISOTROPIC})

    assert calls["fresnel"] > 0
    assert calls["share"] == calls["fresnel"]


def test_harvest_tracer_still_observes_batches_and_deposits() -> None:
    from semantic_twin.illumination.sensitivity_study import HarvestTracer

    config = TraceConfig(rays=31, local_cells=8, exit_bands=4, max_bounces=2, batch=13, seed=91)
    parameters = (
        LeakySphere(),
        np.array([0, 1]),
        np.array([complex(5.24, -0.46), complex(3.1, -0.2)]),
        np.array([0.002, 0.007]),
        config,
    )
    reference = SbrTracer(*parameters).trace(np.zeros(3), {"iso": ISOTROPIC})
    harvester = HarvestTracer(*parameters, crop_radius_m=8.0)
    observed = harvester.trace(np.zeros(3), {"iso": ISOTROPIC})
    harvest = harvester.harvest()

    assert observed.susceptibility == reference.susceptibility
    assert np.array_equal(observed.rho["iso"], reference.rho["iso"])
    assert int(np.count_nonzero(harvest["fine"])) > 0
    assert float(harvest["fine"].sum()) > float(harvest["direct"].sum())
