"""The estimator's numbers, to the last bit.

Everything here compares bits, not tolerances. That is the point: the tracer is
fast because of a band search, a memo and a process pool, and each of those is
only allowed to exist if it leaves every published number exactly where it was.
A tolerance would let a real change through as long as it was small, and a
change that is small on one standpoint is not small on a distribution over
eight hundred and eighty of them.

The recorded constants below were produced on two machines that share no
version of anything relevant, Python 3.10 with NumPy 2.2.6 and Python 3.12 with
NumPy 2.4.6, and they agreed on every bit. PERFORMANCE.md records what does not
carry across a machine, which is the two elevation weighted susceptibilities,
by one or two units in the last place, because they go through ``arcsin`` and
libm is not standardised. The isotropic model does not, so it is what is
pinned here.
"""

from __future__ import annotations

import hashlib
import pathlib

import numpy as np
import pytest

from semantic_twin.propagation import (
    ISOTROPIC,
    MODELS,
    PEC_PERMITTIVITY,
    PlaneGeometry,
    SbrTracer,
    TraceConfig,
    fibonacci_sphere,
)
from semantic_twin.illumination import ROOFTOP, STREET_SMALL_CELL
from semantic_twin.illumination.sphere import _brute_nearest_cell, nearest_cell
from semantic_twin.transport.tracer import trace_standpoints

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONCRETE = complex(5.24, -0.46055233310470917)

#: Every field of the configuration, written out. A default that moves must
#: not be able to move these numbers quietly, and one already has: the bounce
#: budget and the roulette start both changed while this file was being
#: written, which is exactly the kind of drift a pinned config catches.
PINNED = dict(
    frequency_hz=15.0e9,
    rays=20_000,
    local_cells=128,
    exit_bands=18,
    max_bounces=4,
    roulette_start=3,
    roulette_floor=0.05,
    ray_epsilon_m=1.0e-3,
    seed=20260803,
    batch=20_000,
)

#: ``(chi as a hex float, sha256 of rho, sky fraction, escaped fraction, mean bounces)``
#: for the isotropic model under :data:`PINNED`.
RECORDED = {
    "plane_pec": (
        "0x1.ffff2115eb714p-1",
        "d02eb802fbc83b140d9d126f0542771e55bdf8ea57fdee1ce3e90144aa51f3f9",
        0.49955,
        1.0,
        0.50045,
    ),
    "plane_concrete_rough": (
        "0x1.496db7cb825d8p-1",
        "33febc0cfded12606184d2da9c4cbdef0ef5d6c13b05014287ccc4a93ea21c4c",
        0.49955,
        1.0,
        0.50045,
    ),
}


def _pinned_tracer(permittivity: complex, rms_height_m: float) -> SbrTracer:
    return SbrTracer(
        PlaneGeometry(0.0),
        None,
        np.array([permittivity]),
        np.array([rms_height_m]),
        TraceConfig(**PINNED),
    )


@pytest.mark.parametrize(
    ("case", "permittivity", "rms_height_m"),
    [("plane_pec", PEC_PERMITTIVITY, 0.0), ("plane_concrete_rough", CONCRETE, 0.002)],
)
def test_the_pinned_trace_returns_the_recorded_bits(case: str, permittivity: complex, rms_height_m: float) -> None:
    tracer = _pinned_tracer(permittivity, rms_height_m)
    result = tracer.trace(np.array([0.0, 0.0, 1.5]), {"isotropic": ISOTROPIC}, ground_z_m=0.0, seed=PINNED["seed"])
    chi, rho_sha, sky, escaped, bounces = RECORDED[case]
    assert float(result.susceptibility["isotropic"]).hex() == chi
    assert hashlib.sha256(result.rho["isotropic"].tobytes()).hexdigest() == rho_sha
    assert result.sky_fraction == sky
    assert result.escaped_fraction == escaped
    assert result.mean_bounces == bounces


def test_the_same_seed_twice_is_the_same_trace() -> None:
    tracer = _pinned_tracer(CONCRETE, 0.002)
    first = tracer.trace(np.array([0.0, 0.0, 1.5]), MODELS, ground_z_m=0.0, seed=7)
    second = tracer.trace(np.array([0.0, 0.0, 1.5]), MODELS, ground_z_m=0.0, seed=7)
    for name in MODELS:
        assert first.susceptibility[name] == second.susceptibility[name]
        assert np.array_equal(first.rho[name], second.rho[name])


def _digest(result) -> tuple:
    return (
        tuple(float(v).hex() for v in result.susceptibility.values()),
        tuple(float(v).hex() for v in result.susceptibility_direct.values()),
        tuple(hashlib.sha256(v.tobytes()).hexdigest() for v in result.rho.values()),
        hashlib.sha256(result.exit_profile.tobytes()).hexdigest(),
        result.sky_fraction,
        result.escaped_fraction,
        result.mean_bounces,
        result.mean_excess_delay_ns,
    )


def _standpoints(count: int) -> list:
    rng = np.random.default_rng(4)
    return [
        (np.array([float(x), float(y), 1.5]), 0.0, 1000 * i)
        for i, (x, y) in enumerate(rng.uniform(-20.0, 20.0, size=(count, 2)))
    ]


def test_a_worker_pool_reproduces_the_serial_sweep() -> None:
    """Which process runs a standpoint must not be able to reach its numbers."""
    tracer = _pinned_tracer(CONCRETE, 0.002)
    points = _standpoints(5)
    serial = [(row, _digest(r)) for row, r in trace_standpoints(tracer, points, MODELS, workers=1)]
    pooled = [(row, _digest(r)) for row, r in trace_standpoints(tracer, points, MODELS, workers=3)]
    assert [row for row, _ in pooled] == list(range(len(points))), "the pool must yield in sweep order"
    assert pooled == serial


@pytest.mark.parametrize("cells", [1, 4, 16, 64, 128, 512, 1024, 2048])
def test_the_band_search_is_the_dense_argmax(cells: int) -> None:
    """The band is a shortcut to the dense answer, never a different answer."""
    rng = np.random.default_rng(cells)
    height = rng.uniform(-1.0, 1.0, 50_000)
    azimuth = rng.uniform(0.0, 2.0 * np.pi, 50_000)
    radius = np.sqrt(np.maximum(0.0, 1.0 - height * height))
    directions = np.stack([radius * np.cos(azimuth), radius * np.sin(azimuth), height], axis=1)
    grid = fibonacci_sphere(cells)
    assert np.array_equal(nearest_cell(directions, grid), _brute_nearest_cell(directions, grid, 65536))


def test_the_band_search_handles_grids_it_cannot_band() -> None:
    """A grid that is not sorted in height, and one that is sorted but uneven."""
    rng = np.random.default_rng(11)
    directions = rng.normal(size=(20_000, 3))
    directions /= np.linalg.norm(directions, axis=1, keepdims=True)
    scrambled = rng.normal(size=(300, 3))
    scrambled /= np.linalg.norm(scrambled, axis=1, keepdims=True)
    for grid in (scrambled, scrambled[np.argsort(-scrambled[:, 2])]):
        assert np.array_equal(nearest_cell(directions, grid), _brute_nearest_cell(directions, grid, 65536))


def test_the_band_search_handles_the_grid_directions_themselves() -> None:
    """Where two cells tie, both forms take the lower index."""
    grid = fibonacci_sphere(512)
    directions = np.vstack([grid, -grid, np.array([[0.0, 0.0, 1.0], [0.0, 0.0, -1.0], [1.0, 0.0, 0.0]])])
    assert np.array_equal(nearest_cell(directions, grid), _brute_nearest_cell(directions, grid, 65536))


@pytest.mark.parametrize("block", [256, 4096, 65536])
def test_the_dense_block_size_does_not_reach_the_answer(block: int) -> None:
    rng = np.random.default_rng(3)
    directions = rng.normal(size=(120_000, 3))
    directions /= np.linalg.norm(directions, axis=1, keepdims=True)
    grid = fibonacci_sphere(512)
    assert np.array_equal(_brute_nearest_cell(directions, grid, block), nearest_cell(directions, grid))


@pytest.mark.parametrize("model", [ISOTROPIC, ROOFTOP, STREET_SMALL_CELL])
def test_the_normalisation_memo_returns_the_quadrature(model) -> None:
    """The kept value is the value the quadrature returns, to the bit."""
    fresh = model.integrate(200_001)
    assert model.normalisation() == fresh
    assert model.normalisation() == fresh
    assert model.normalisation(50_001) == model.integrate(50_001)
    assert model.normalisation() == fresh, "a second quadrature must not evict the first answer"


def _site_mesh() -> pathlib.Path | None:
    directory = ROOT / "data" / "geometry" / "korenmarkt"
    for candidate in ("inhouse_leaf_130m_f64.ply", "inhouse_leaf_130m.ply"):
        if (directory / candidate).exists():
            return directory / candidate
    return None


@pytest.mark.skipif(_site_mesh() is None, reason="no Korenmarkt mesh on this checkout")
def test_a_worker_pool_reproduces_the_serial_sweep_on_a_real_mesh() -> None:
    """The same again with a mesh, a Mitsuba scene and a per triangle class."""
    pytest.importorskip("mitsuba")
    from semantic_twin.propagation import MitsubaGeometry
    from semantic_twin.materials import classify_faces, load_table

    geometry = MitsubaGeometry(_site_mesh())
    datum = float(np.median(geometry.vertices[:, 2]))
    face_class = classify_faces(geometry.vertices, geometry.faces, datum)
    binding = load_table(ROOT / "config", 15.0e9)
    config = TraceConfig(**{**PINNED, "rays": 20_000, "batch": 20_000, "local_cells": 512})
    tracer = SbrTracer(geometry, face_class, binding.permittivity, binding.rms_height_m, config)
    centre = geometry.vertices.mean(axis=0)
    points = [(np.array([centre[0] + 2.0 * i, centre[1], datum + 1.5]), datum, 1000 * i) for i in range(4)]
    serial = [_digest(r) for _, r in trace_standpoints(tracer, points, MODELS, workers=1)]
    pooled = [_digest(r) for _, r in trace_standpoints(tracer, points, MODELS, workers=3)]
    assert pooled == serial
