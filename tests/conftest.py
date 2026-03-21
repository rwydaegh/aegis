"""Shared test fixtures for AEGIS."""

# ruff: noqa: E402
# test_viewer_e2e.py is a manual script (requires a running server, requests,
# and playwright). Exclude it from pytest collection.
collect_ignore = ["test_viewer_e2e.py"]

import os
from pathlib import Path

import numpy as np
import pytest

from aegis.engine import DosimetryEngine
from aegis.geometry.mesh import BodyMesh
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import SKIN_28GHZ


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "slow: tests that need mesh data or take >10s")


@pytest.fixture
def data_dir():
    """Path to the data directory containing mesh files and databases."""
    env_path = os.environ.get("AEGIS_DATA_DIR")
    if env_path:
        return Path(env_path)
    # Default: aegis/data/ (repo-local)
    default = Path(__file__).parent.parent / "data"
    return default


@pytest.fixture
def has_data(data_dir):
    """Whether the data directory exists and contains mesh files."""
    return data_dir.exists() and any(data_dir.glob("*.stl"))


# ---------------------------------------------------------------------------
# Synthetic mesh helpers (importable by test modules)
# ---------------------------------------------------------------------------


def make_flat_mesh(n: int = 100) -> BodyMesh:
    """Create a flat square mesh in the xy-plane, normals pointing +z.

    Each triangle has area ~1e-4 m^2.
    """
    rng = np.random.default_rng(42)
    side = np.sqrt(n * 1e-4)
    vertices = np.zeros((n, 3, 3))
    s = np.sqrt(1e-4 * 2)  # triangle side for area ~1e-4
    for i in range(n):
        cx = rng.uniform(0, side)
        cy = rng.uniform(0, side)
        vertices[i, 0] = [cx, cy, 0]
        vertices[i, 1] = [cx + s, cy, 0]
        vertices[i, 2] = [cx, cy + s, 0]

    normals = np.tile([0, 0, 1.0], (n, 1))
    centroids = np.mean(vertices, axis=1)
    areas = 0.5 * s * s * np.ones(n)

    return BodyMesh(vertices=vertices, normals=normals, centroids=centroids, areas=areas, name="flat_plane")


def make_icosahedron() -> BodyMesh:
    """Create an icosahedron mesh (20 triangles) centered at origin."""
    phi = (1 + np.sqrt(5)) / 2
    verts_raw = np.array(
        [
            [-1, phi, 0],
            [1, phi, 0],
            [-1, -phi, 0],
            [1, -phi, 0],
            [0, -1, phi],
            [0, 1, phi],
            [0, -1, -phi],
            [0, 1, -phi],
            [phi, 0, -1],
            [phi, 0, 1],
            [-phi, 0, -1],
            [-phi, 0, 1],
        ],
        dtype=float,
    )
    # Normalize to unit sphere
    verts_raw /= np.linalg.norm(verts_raw[0])
    # Scale to ~10cm radius
    verts_raw *= 0.1

    faces = [
        (0, 11, 5),
        (0, 5, 1),
        (0, 1, 7),
        (0, 7, 10),
        (0, 10, 11),
        (1, 5, 9),
        (5, 11, 4),
        (11, 10, 2),
        (10, 7, 6),
        (7, 1, 8),
        (3, 9, 4),
        (3, 4, 2),
        (3, 2, 6),
        (3, 6, 8),
        (3, 8, 9),
        (4, 9, 5),
        (2, 4, 11),
        (6, 2, 10),
        (8, 6, 7),
        (9, 8, 1),
    ]

    n = len(faces)
    vertices = np.zeros((n, 3, 3))
    for i, (a, b, c) in enumerate(faces):
        vertices[i] = [verts_raw[a], verts_raw[b], verts_raw[c]]

    # Compute normals from cross product
    v0 = vertices[:, 0]
    v1 = vertices[:, 1]
    v2 = vertices[:, 2]
    cross = np.cross(v1 - v0, v2 - v0)
    norms = np.linalg.norm(cross, axis=1, keepdims=True)
    normals = cross / norms

    # Ensure outward-pointing (away from origin)
    centroids = np.mean(vertices, axis=1)
    flip = np.sum(normals * centroids, axis=1) < 0
    normals[flip] *= -1

    areas = 0.5 * norms[:, 0]

    return BodyMesh(vertices=vertices, normals=normals, centroids=centroids, areas=areas, name="icosahedron")


def make_cube_mesh() -> BodyMesh:
    """Unit cube centered at origin, 12 triangles (2 per face)."""
    from aegis.geometry.mesh import triangle_areas

    v = np.array(
        [
            [-0.5, -0.5, -0.5],
            [0.5, -0.5, -0.5],
            [0.5, 0.5, -0.5],
            [-0.5, 0.5, -0.5],
            [-0.5, -0.5, 0.5],
            [0.5, -0.5, 0.5],
            [0.5, 0.5, 0.5],
            [-0.5, 0.5, 0.5],
        ]
    )
    faces = [
        (0, 2, 1),
        (0, 3, 2),
        (4, 5, 6),
        (4, 6, 7),
        (0, 1, 5),
        (0, 5, 4),
        (2, 3, 7),
        (2, 7, 6),
        (0, 4, 7),
        (0, 7, 3),
        (1, 2, 6),
        (1, 6, 5),
    ]
    vertices = np.array([[v[i] for i in f] for f in faces], dtype=np.float64)
    areas = triangle_areas(vertices)
    v0, v1, v2 = vertices[:, 0], vertices[:, 1], vertices[:, 2]
    cross = np.cross(v1 - v0, v2 - v0)
    norms = np.linalg.norm(cross, axis=1, keepdims=True)
    normals = cross / norms
    centroids = np.mean(vertices, axis=1)
    return BodyMesh(vertices=vertices, normals=normals, centroids=centroids, areas=areas, name="cube")


def make_single_triangle() -> BodyMesh:
    """Single right triangle in the XY plane, normal along +Z."""
    from aegis.geometry.mesh import triangle_areas

    vertices = np.array([[[0, 0, 0], [1, 0, 0], [0, 1, 0]]], dtype=np.float64)
    areas = triangle_areas(vertices)
    normals = np.array([[0, 0, 1]], dtype=np.float64)
    centroids = np.mean(vertices, axis=1)
    return BodyMesh(vertices=vertices, normals=normals, centroids=centroids, areas=areas, name="tri")


# ---------------------------------------------------------------------------
# Shared pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def flat_mesh():
    return make_flat_mesh()


@pytest.fixture
def ico_mesh():
    return make_icosahedron()


@pytest.fixture
def cube_mesh():
    return make_cube_mesh()


@pytest.fixture
def engine():
    return DosimetryEngine(SKIN_28GHZ)


@pytest.fixture
def single_path_down():
    """Single plane wave from +z (downward)."""
    return PropagationPaths.from_powers(
        k_hat=np.array([[0, 0, -1.0]]),
        power=np.array([1.0]),
    )


@pytest.fixture
def multi_path():
    """Multiple paths from different directions."""
    rng = np.random.default_rng(123)
    N = 50
    k_hat = rng.standard_normal((N, 3))
    k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
    power = rng.uniform(0.1, 2.0, size=N)
    return PropagationPaths.from_powers(k_hat=k_hat, power=power)
