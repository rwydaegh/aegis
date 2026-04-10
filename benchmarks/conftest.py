"""Shared fixtures for CodSpeed benchmarks."""

import numpy as np
import pytest

from aegis.engine import DosimetryEngine
from aegis.geometry.mesh import BodyMesh
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import SKIN_28GHZ


def _make_bench_mesh(n: int = 500) -> BodyMesh:
    """Flat mesh with n triangles, normals along +z."""
    rng = np.random.default_rng(42)
    s = np.sqrt(1e-4 * 2)
    cx = rng.uniform(0, 1.0, n)
    cy = rng.uniform(0, 1.0, n)
    z = np.zeros(n)

    vertices = np.zeros((n, 3, 3))
    vertices[:, 0, :] = np.column_stack([cx, cy, z])
    vertices[:, 1, :] = np.column_stack([cx + s, cy, z])
    vertices[:, 2, :] = np.column_stack([cx, cy + s, z])

    normals = np.tile([0, 0, 1.0], (n, 1))
    centroids = np.mean(vertices, axis=1)
    areas = 0.5 * s * s * np.ones(n)

    return BodyMesh(
        vertices=vertices,
        normals=normals,
        centroids=centroids,
        areas=areas,
        name="bench_flat",
    )


def _make_bench_paths(n: int = 50) -> PropagationPaths:
    """Random propagation paths from the upper hemisphere."""
    rng = np.random.default_rng(123)
    k_hat = rng.standard_normal((n, 3))
    k_hat[:, 2] = -np.abs(k_hat[:, 2])
    k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
    power = rng.uniform(0.1, 2.0, size=n)
    return PropagationPaths.from_powers(k_hat=k_hat, power=power)


@pytest.fixture
def bench_mesh():
    return _make_bench_mesh(500)


@pytest.fixture
def bench_paths():
    return _make_bench_paths(50)


@pytest.fixture
def bench_engine():
    return DosimetryEngine(SKIN_28GHZ)


@pytest.fixture
def bench_tissue():
    return SKIN_28GHZ


@pytest.fixture
def bench_channel_preset():
    from pathlib import Path

    from aegis.channel.presets import load_preset

    return load_preset("3GPP_38.901_UMa_LOS", Path(__file__).resolve().parents[1] / "data" / "channel_presets")
