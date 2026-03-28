# Environment module implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate blosm (OSM + Google 3D Tiles) into AEGIS as `src/aegis/environment/`, producing `EnvironmentMesh` objects that feed the existing ray tracing and dosimetry pipeline, with frontend visualization via 3DTilesRendererJS and OSM mesh rendering.

**Architecture:** New `src/aegis/environment/` package with 7 modules. All environment sources (OSM, 3D Tiles, voxels) produce an `EnvironmentMesh` dataclass. Downstream pipeline unchanged: `EnvironmentMesh.to_differt_scene()` feeds DiffeRT. Frontend gets new 3DTilesRendererJS component, OSM mesh renderer, environment panel, and globe camera mode. All legacy code stays untouched.

**Tech Stack:** Python 3.12, numpy, requests, Flask, DiffeRT, React 19, Three.js, R3F, Zustand, 3d-tiles-renderer (npm), TypeScript.

**Spec:** `docs/superpowers/specs/2026-03-28-environment-module-design.md`

---

## File map

### Python: new files

| File | Responsibility |
|---|---|
| `src/aegis/environment/__init__.py` | `EnvironmentMesh` dataclass, `MaterialType` enum, `MATERIAL_EM_PROPERTIES` dict |
| `src/aegis/environment/geo.py` | WGS84/ECEF/ENU coordinate transforms, bounding volume intersection tests |
| `src/aegis/environment/materials.py` | `get_em_properties()`, `classify_color()` for vertex-color material classification |
| `src/aegis/environment/roofs.py` | `generate_building()`, all 12+ roof types, `triangulate_polygon()`, `extrude_walls()` |
| `src/aegis/environment/skeleton.py` | Pure-numpy straight skeleton (replaces bpyeuclid.py + wraps bpypolyskel.py) |
| `src/aegis/environment/osm.py` | `fetch_osm()`, OSM XML parsing via blosm, building/road/water extraction |
| `src/aegis/environment/tiles.py` | `TileTraverser` class, 3D Tiles recursive fetch + GLB mesh extraction |
| `src/aegis/environment/export.py` | `to_differt_scene()`, `to_sionna_xml()`, `to_binary()` |
| `src/aegis/viewer/routes/environment.py` | Flask routes for `/api/environment/*` |

### Python: modified files

| File | Change |
|---|---|
| `src/aegis/viewer/server.py` | Add `environment.register(app, _cache, _cache_lock)` call |
| `src/aegis/viewer/config.py` | Add `"environment"` key to `DEFAULTS` dict |
| `pyproject.toml` | Add `requests` to `viewer` extra |

### Python: test files

| File | Scope |
|---|---|
| `tests/test_environment_geo.py` | Coordinate transform round-trips, intersection tests |
| `tests/test_environment_materials.py` | MaterialType enum, EM property lookup, color classification |
| `tests/test_environment_roofs.py` | Each roof type produces valid mesh |
| `tests/test_environment_skeleton.py` | Straight skeleton on known polygons |
| `tests/test_environment_mesh.py` | EnvironmentMesh creation, combine, binary round-trip |
| `tests/test_environment_osm.py` | OSM parsing with fixture XML, building extraction |
| `tests/test_environment_export.py` | DiffeRT scene export, Sionna XML well-formedness |

### Frontend: new files

| File | Responsibility |
|---|---|
| `aegis-web/src/stores/environment.ts` | Zustand store for environment source, location, mesh data |
| `aegis-web/src/components/scene/Environment3DTiles.tsx` | 3DTilesRendererJS wrapper with Google auth + attribution |
| `aegis-web/src/components/scene/EnvironmentOSM.tsx` | Renders OSM mesh from backend binary data |
| `aegis-web/src/components/panels/EnvironmentPanel.tsx` | Sidebar panel: source selector, location, options, RT export |
| `aegis-web/public/google-maps-logo.png` | Bundled Google Maps logo for ToS compliance |

### Frontend: modified files

| File | Change |
|---|---|
| `aegis-web/src/stores/ui.ts` | Add `'globe'` to `CameraMode` type |
| `aegis-web/src/components/scene/SceneRoot.tsx` | Conditional environment rendering, globe controls |
| `aegis-web/src/components/layout/Toolbar.tsx` | Globe camera toggle button |
| `aegis-web/src/components/layout/Sidebar.tsx` | Add EnvironmentPanel accordion section |
| `aegis-web/src/hooks/useConfig.ts` | Hydrate environment store from config |
| `aegis-web/package.json` | Add `3d-tiles-renderer` dependency |

---

## Task 1: EnvironmentMesh dataclass and MaterialType enum

**Files:**
- Create: `src/aegis/environment/__init__.py`
- Test: `tests/test_environment_mesh.py`

This is the foundation. Every other task depends on this dataclass.

- [ ] **Step 1: Write test for MaterialType enum and EM properties**

```python
# tests/test_environment_mesh.py
import numpy as np
import pytest

from aegis.environment import (
    EnvironmentMesh,
    MaterialType,
    MATERIAL_EM_PROPERTIES,
)


class TestMaterialType:
    def test_all_values_are_sequential(self):
        values = [m.value for m in MaterialType]
        assert values == list(range(len(MaterialType)))

    def test_every_material_has_em_properties(self):
        for mat in MaterialType:
            assert mat in MATERIAL_EM_PROPERTIES
            props = MATERIAL_EM_PROPERTIES[mat]
            assert "eps_r" in props
            assert "sigma" in props
            assert props["eps_r"] > 0

    def test_concrete_values_match_itu_p2040(self):
        props = MATERIAL_EM_PROPERTIES[MaterialType.CONCRETE]
        assert props["eps_r"] == pytest.approx(5.31)
        assert props["sigma"] == pytest.approx(0.0326)
```

- [ ] **Step 2: Write test for EnvironmentMesh creation and combine**

```python
# append to tests/test_environment_mesh.py

class TestEnvironmentMesh:
    @pytest.fixture
    def simple_mesh(self):
        """A single triangle at origin."""
        vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float64)
        triangles = np.array([[0, 1, 2]], dtype=np.uint32)
        normals = np.array([[0, 0, 1]], dtype=np.float64)
        materials = np.array([MaterialType.CONCRETE], dtype=np.uint8)
        return EnvironmentMesh(
            vertices=vertices,
            triangles=triangles,
            normals=normals,
            materials=materials,
            origin_lat=51.05,
            origin_lon=3.72,
            source="test",
        )

    def test_creation(self, simple_mesh):
        assert simple_mesh.vertices.shape == (3, 3)
        assert simple_mesh.triangles.shape == (1, 3)
        assert simple_mesh.normals.shape == (1, 3)
        assert simple_mesh.materials.shape == (1,)
        assert simple_mesh.source == "test"

    def test_combine_same_origin(self, simple_mesh):
        combined = EnvironmentMesh.combine(simple_mesh, simple_mesh)
        assert combined.vertices.shape == (6, 3)
        assert combined.triangles.shape == (2, 3)
        assert combined.source == "combined"
        # second mesh triangles should be offset by 3
        assert combined.triangles[1, 0] == 3

    def test_combine_different_origin_raises(self, simple_mesh):
        other = EnvironmentMesh(
            vertices=simple_mesh.vertices,
            triangles=simple_mesh.triangles,
            normals=simple_mesh.normals,
            materials=simple_mesh.materials,
            origin_lat=52.0,  # different
            origin_lon=3.72,
            source="test",
        )
        with pytest.raises(ValueError, match="origin"):
            EnvironmentMesh.combine(simple_mesh, other)

    def test_combine_empty(self):
        with pytest.raises(ValueError):
            EnvironmentMesh.combine()
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_environment_mesh.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'aegis.environment'`

- [ ] **Step 4: Implement EnvironmentMesh and MaterialType**

```python
# src/aegis/environment/__init__.py
"""Unified environment mesh for AEGIS ray tracing and visualization."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

import numpy as np


class MaterialType(IntEnum):
    CONCRETE = 0
    BRICK = 1
    GLASS = 2
    METAL = 3
    ASPHALT = 4
    VEGETATION = 5
    WATER = 6
    WOOD = 7
    GROUND = 8
    UNKNOWN = 9


MATERIAL_EM_PROPERTIES: dict[MaterialType, dict[str, float]] = {
    MaterialType.CONCRETE:   {"eps_r": 5.31, "sigma": 0.0326},
    MaterialType.BRICK:      {"eps_r": 3.75, "sigma": 0.038},
    MaterialType.GLASS:      {"eps_r": 6.27, "sigma": 0.0043},
    MaterialType.METAL:      {"eps_r": 1.0,  "sigma": 1e7},
    MaterialType.ASPHALT:    {"eps_r": 3.18, "sigma": 0.0},
    MaterialType.VEGETATION: {"eps_r": 1.0,  "sigma": 0.0},
    MaterialType.WATER:      {"eps_r": 81.0, "sigma": 0.01},
    MaterialType.WOOD:       {"eps_r": 1.99, "sigma": 0.0047},
    MaterialType.GROUND:     {"eps_r": 15.0, "sigma": 0.035},
    MaterialType.UNKNOWN:    {"eps_r": 5.31, "sigma": 0.0326},
}


@dataclass
class EnvironmentMesh:
    vertices: np.ndarray
    triangles: np.ndarray
    normals: np.ndarray
    materials: np.ndarray
    origin_lat: float
    origin_lon: float
    source: str

    @classmethod
    def combine(cls, *meshes: EnvironmentMesh) -> EnvironmentMesh:
        if not meshes:
            raise ValueError("At least one mesh required")
        origin_lat = meshes[0].origin_lat
        origin_lon = meshes[0].origin_lon
        for m in meshes[1:]:
            if abs(m.origin_lat - origin_lat) > 1e-6 or abs(m.origin_lon - origin_lon) > 1e-6:
                raise ValueError(
                    f"All meshes must share the same origin. "
                    f"Got ({origin_lat}, {origin_lon}) and ({m.origin_lat}, {m.origin_lon})"
                )
        vert_offset = 0
        all_verts, all_tris, all_normals, all_mats = [], [], [], []
        for m in meshes:
            all_verts.append(m.vertices)
            all_tris.append(m.triangles + vert_offset)
            all_normals.append(m.normals)
            all_mats.append(m.materials)
            vert_offset += len(m.vertices)
        return cls(
            vertices=np.concatenate(all_verts),
            triangles=np.concatenate(all_tris),
            normals=np.concatenate(all_normals),
            materials=np.concatenate(all_mats),
            origin_lat=origin_lat,
            origin_lon=origin_lon,
            source="combined",
        )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_environment_mesh.py -v`
Expected: all PASS

- [ ] **Step 6: Lint and commit**

```bash
python -m ruff check src/aegis/environment/ tests/test_environment_mesh.py
python -m ruff format src/aegis/environment/ tests/test_environment_mesh.py
git add src/aegis/environment/__init__.py tests/test_environment_mesh.py
git commit -m "Add EnvironmentMesh dataclass and MaterialType enum"
```

---

## Task 2: Coordinate transforms (geo.py)

**Files:**
- Create: `src/aegis/environment/geo.py`
- Test: `tests/test_environment_geo.py`
- Reference: `blosm/threed_tiles/manager.py` (lines 62-93 for `fromGeographic`), `blosm/util/transverse_mercator.py`

All coordinate math for the environment module. Other tasks (osm.py, tiles.py, export.py) depend on this.

- [ ] **Step 1: Write tests for WGS84-ECEF-ENU round-trip**

```python
# tests/test_environment_geo.py
import numpy as np
import pytest

from aegis.environment.geo import (
    wgs84_to_ecef,
    ecef_to_enu,
    enu_to_yup,
    rotation_ecef_to_enu,
    transverse_mercator_forward,
    transverse_mercator_inverse,
)


class TestWgs84Ecef:
    def test_equator_prime_meridian(self):
        """(0, 0, 0) should be on the equator at the prime meridian."""
        ecef = wgs84_to_ecef(0.0, 0.0, 0.0)
        assert ecef[0] == pytest.approx(6378137.0, abs=1)  # WGS84 semi-major axis
        assert ecef[1] == pytest.approx(0.0, abs=1)
        assert ecef[2] == pytest.approx(0.0, abs=1)

    def test_north_pole(self):
        ecef = wgs84_to_ecef(90.0, 0.0, 0.0)
        assert ecef[0] == pytest.approx(0.0, abs=1)
        assert ecef[1] == pytest.approx(0.0, abs=1)
        assert ecef[2] == pytest.approx(6356752.314, abs=1)  # semi-minor axis

    def test_ghent(self):
        """Known point: Ghent, Belgium (51.05 N, 3.72 E)."""
        ecef = wgs84_to_ecef(51.05, 3.72, 0.0)
        # approximate ECEF for Ghent (verified via pyproj)
        assert ecef[0] == pytest.approx(4009241, abs=100)
        assert ecef[1] == pytest.approx(260671, abs=100)
        assert ecef[2] == pytest.approx(4937043, abs=100)


class TestEcefEnu:
    def test_origin_is_zero(self):
        """Point at the origin should map to ENU (0,0,0)."""
        origin_lat, origin_lon = 51.05, 3.72
        origin_ecef = wgs84_to_ecef(origin_lat, origin_lon, 0.0)
        enu = ecef_to_enu(origin_ecef, origin_ecef, origin_lat, origin_lon)
        np.testing.assert_allclose(enu, [0, 0, 0], atol=1e-6)

    def test_east_is_positive_x(self):
        """A point slightly east should have positive E component."""
        origin_lat, origin_lon = 51.05, 3.72
        origin_ecef = wgs84_to_ecef(origin_lat, origin_lon, 0.0)
        east_ecef = wgs84_to_ecef(origin_lat, origin_lon + 0.001, 0.0)
        enu = ecef_to_enu(east_ecef, origin_ecef, origin_lat, origin_lon)
        assert enu[0] > 0  # east
        assert abs(enu[1]) < abs(enu[0])  # mostly east, not north
        assert abs(enu[2]) < 1  # near ground

    def test_north_is_positive_y(self):
        origin_lat, origin_lon = 51.05, 3.72
        origin_ecef = wgs84_to_ecef(origin_lat, origin_lon, 0.0)
        north_ecef = wgs84_to_ecef(origin_lat + 0.001, origin_lon, 0.0)
        enu = ecef_to_enu(north_ecef, origin_ecef, origin_lat, origin_lon)
        assert enu[1] > 0  # north
        assert abs(enu[0]) < abs(enu[1])  # mostly north

    def test_up_is_positive_z(self):
        origin_lat, origin_lon = 51.05, 3.72
        origin_ecef = wgs84_to_ecef(origin_lat, origin_lon, 0.0)
        up_ecef = wgs84_to_ecef(origin_lat, origin_lon, 100.0)
        enu = ecef_to_enu(up_ecef, origin_ecef, origin_lat, origin_lon)
        assert enu[2] == pytest.approx(100.0, abs=1)


class TestEnuToYup:
    def test_conversion(self):
        """ENU [east, north, up] -> Y-up [east, up, -north]."""
        enu = np.array([10.0, 20.0, 30.0])
        yup = enu_to_yup(enu)
        np.testing.assert_allclose(yup, [10.0, 30.0, -20.0])

    def test_batch(self):
        enu = np.array([[1, 2, 3], [4, 5, 6]])
        yup = enu_to_yup(enu)
        expected = np.array([[1, 3, -2], [4, 6, -5]])
        np.testing.assert_allclose(yup, expected)


class TestTransverseMercator:
    def test_origin_is_zero(self):
        x, y = transverse_mercator_forward(51.05, 3.72, 51.05, 3.72)
        assert x == pytest.approx(0.0, abs=1e-6)
        assert y == pytest.approx(0.0, abs=1e-6)

    def test_round_trip(self):
        lat, lon = 51.06, 3.73
        x, y = transverse_mercator_forward(lat, lon, 51.05, 3.72)
        lat2, lon2 = transverse_mercator_inverse(x, y, 51.05, 3.72)
        assert lat2 == pytest.approx(lat, abs=1e-8)
        assert lon2 == pytest.approx(lon, abs=1e-8)

    def test_scale_roughly_correct(self):
        """1 degree latitude ~ 111km at mid-latitudes."""
        x, y = transverse_mercator_forward(52.05, 3.72, 51.05, 3.72)
        assert abs(y) == pytest.approx(111_000, rel=0.01)
```

- [ ] **Step 2: Write tests for bounding volume intersection**

```python
# append to tests/test_environment_geo.py
from aegis.environment.geo import (
    box_sphere_intersect,
    sphere_aabb_intersect,
    obb_aabb_intersect,
)


class TestSphereAabbIntersect:
    def test_sphere_inside_box(self):
        assert sphere_aabb_intersect(
            center=np.array([0, 0, 0]),
            radius=1.0,
            aabb_min=np.array([-5, -5, -5]),
            aabb_max=np.array([5, 5, 5]),
        )

    def test_sphere_outside_box(self):
        assert not sphere_aabb_intersect(
            center=np.array([100, 100, 100]),
            radius=1.0,
            aabb_min=np.array([-5, -5, -5]),
            aabb_max=np.array([5, 5, 5]),
        )

    def test_sphere_touching_face(self):
        assert sphere_aabb_intersect(
            center=np.array([6, 0, 0]),
            radius=1.5,
            aabb_min=np.array([-5, -5, -5]),
            aabb_max=np.array([5, 5, 5]),
        )

    def test_sphere_touching_edge(self):
        assert sphere_aabb_intersect(
            center=np.array([6, 6, 0]),
            radius=2.0,
            aabb_min=np.array([-5, -5, -5]),
            aabb_max=np.array([5, 5, 5]),
        )


class TestObbAabbIntersect:
    def test_axis_aligned_overlap(self):
        assert obb_aabb_intersect(
            obb_center=np.array([0, 0, 0]),
            obb_half_axes=np.eye(3) * 5,
            aabb_min=np.array([-3, -3, -3]),
            aabb_max=np.array([3, 3, 3]),
        )

    def test_axis_aligned_no_overlap(self):
        assert not obb_aabb_intersect(
            obb_center=np.array([20, 0, 0]),
            obb_half_axes=np.eye(3) * 5,
            aabb_min=np.array([-3, -3, -3]),
            aabb_max=np.array([3, 3, 3]),
        )

    def test_rotated_overlap(self):
        """45-degree rotated box should still overlap centered AABB."""
        c45 = np.cos(np.pi / 4)
        s45 = np.sin(np.pi / 4)
        # rotate 45 degrees around Z
        half_axes = np.array([
            [c45 * 5, s45 * 5, 0],
            [-s45 * 5, c45 * 5, 0],
            [0, 0, 5],
        ])
        assert obb_aabb_intersect(
            obb_center=np.array([0, 0, 0]),
            obb_half_axes=half_axes,
            aabb_min=np.array([-1, -1, -1]),
            aabb_max=np.array([1, 1, 1]),
        )
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_environment_geo.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 4: Implement geo.py**

```python
# src/aegis/environment/geo.py
"""Coordinate transforms and bounding volume intersection tests.

All functions use numpy arrays. No mathutils dependency.
Reference: blosm/threed_tiles/manager.py, blosm/util/transverse_mercator.py
"""

from __future__ import annotations

import numpy as np

# WGS-84 ellipsoid parameters
_A = 6378137.0  # semi-major axis (meters)
_F = 1.0 / 298.257223563  # flattening
_B = _A * (1 - _F)  # semi-minor axis
_E2 = 2 * _F - _F**2  # first eccentricity squared


def wgs84_to_ecef(
    lat: float, lon: float, alt: float = 0.0
) -> np.ndarray:
    """Convert WGS-84 geodetic coordinates (degrees) to ECEF (meters)."""
    lat_r = np.radians(lat)
    lon_r = np.radians(lon)
    sin_lat = np.sin(lat_r)
    cos_lat = np.cos(lat_r)
    sin_lon = np.sin(lon_r)
    cos_lon = np.cos(lon_r)
    N = _A / np.sqrt(1 - _E2 * sin_lat**2)
    x = (N + alt) * cos_lat * cos_lon
    y = (N + alt) * cos_lat * sin_lon
    z = (N * (1 - _E2) + alt) * sin_lat
    return np.array([x, y, z], dtype=np.float64)


def rotation_ecef_to_enu(lat: float, lon: float) -> np.ndarray:
    """3x3 rotation matrix from ECEF to local ENU frame (lat/lon in degrees)."""
    lat_r = np.radians(lat)
    lon_r = np.radians(lon)
    sin_lat = np.sin(lat_r)
    cos_lat = np.cos(lat_r)
    sin_lon = np.sin(lon_r)
    cos_lon = np.cos(lon_r)
    return np.array([
        [-sin_lon,           cos_lon,          0],
        [-sin_lat * cos_lon, -sin_lat * sin_lon, cos_lat],
        [cos_lat * cos_lon,  cos_lat * sin_lon,  sin_lat],
    ], dtype=np.float64)


def ecef_to_enu(
    ecef: np.ndarray,
    origin_ecef: np.ndarray,
    origin_lat: float,
    origin_lon: float,
) -> np.ndarray:
    """Convert ECEF coordinates to local ENU relative to origin (lat/lon in degrees).

    Works for single points (3,) or batches (N, 3).
    """
    R = rotation_ecef_to_enu(origin_lat, origin_lon)
    diff = ecef - origin_ecef
    if diff.ndim == 1:
        return R @ diff
    return (R @ diff.T).T


def enu_to_yup(enu: np.ndarray) -> np.ndarray:
    """Convert ENU [east, north, up] to Three.js Y-up [east, up, -north].

    Works for single points (3,) or batches (N, 3).
    """
    if enu.ndim == 1:
        return np.array([enu[0], enu[2], -enu[1]])
    return np.column_stack([enu[:, 0], enu[:, 2], -enu[:, 1]])


def transverse_mercator_forward(
    lat: float, lon: float, origin_lat: float, origin_lon: float
) -> tuple[float, float]:
    """Project WGS-84 (degrees) to local XY meters via Transverse Mercator.

    Adapted from blosm/util/transverse_mercator.py.
    """
    lat_r = np.radians(lat)
    lon_offset = np.radians(lon - origin_lon)
    origin_lat_r = np.radians(origin_lat)
    B = np.sin(lon_offset) * np.cos(lat_r)
    x = 0.5 * _A * np.log((1 + B) / (1 - B))
    y = _A * (np.arctan(np.tan(lat_r) / np.cos(lon_offset)) - origin_lat_r)
    return float(x), float(y)


def transverse_mercator_inverse(
    x: float, y: float, origin_lat: float, origin_lon: float
) -> tuple[float, float]:
    """Inverse Transverse Mercator: local XY meters to WGS-84 degrees."""
    origin_lat_r = np.radians(origin_lat)
    origin_lon_r = np.radians(origin_lon)
    x_n = x / _A
    y_n = y / _A
    D = y_n + origin_lat_r
    lon = np.arctan(np.sinh(x_n) / np.cos(D)) + origin_lon_r
    lat = np.arcsin(np.sin(D) / np.cosh(x_n))
    return float(np.degrees(lat)), float(np.degrees(lon))


def sphere_aabb_intersect(
    center: np.ndarray,
    radius: float,
    aabb_min: np.ndarray,
    aabb_max: np.ndarray,
) -> bool:
    """Test sphere-AABB intersection (Arvo's algorithm)."""
    clamped = np.clip(center, aabb_min, aabb_max)
    dist_sq = float(np.sum((center - clamped) ** 2))
    return dist_sq <= radius * radius


def obb_aabb_intersect(
    obb_center: np.ndarray,
    obb_half_axes: np.ndarray,
    aabb_min: np.ndarray,
    aabb_max: np.ndarray,
) -> bool:
    """Test OBB-AABB intersection via separating axis theorem.

    obb_half_axes: (3, 3) array where each row is a half-extent vector
    (direction * half-length). The OBB axes are the row directions.
    """
    aabb_center = 0.5 * (aabb_min + aabb_max)
    aabb_half = 0.5 * (aabb_max - aabb_min)
    t = obb_center - aabb_center

    # normalize OBB axes and get half-lengths
    obb_axes = np.zeros((3, 3))
    obb_extents = np.zeros(3)
    for i in range(3):
        length = np.linalg.norm(obb_half_axes[i])
        if length < 1e-12:
            obb_axes[i] = 0
            obb_extents[i] = 0
        else:
            obb_axes[i] = obb_half_axes[i] / length
            obb_extents[i] = length

    aabb_axes = np.eye(3)

    # test 3 AABB face normals + 3 OBB face normals + 9 cross products = 15 axes
    for axis in _sat_axes(aabb_axes, obb_axes):
        norm = np.linalg.norm(axis)
        if norm < 1e-12:
            continue
        axis = axis / norm
        proj_t = abs(np.dot(t, axis))
        proj_aabb = sum(aabb_half[i] * abs(np.dot(aabb_axes[i], axis)) for i in range(3))
        proj_obb = sum(obb_extents[i] * abs(np.dot(obb_axes[i], axis)) for i in range(3))
        if proj_t > proj_aabb + proj_obb:
            return False
    return True


def box_sphere_intersect(
    box_center: np.ndarray,
    box_half: np.ndarray,
    sphere_center: np.ndarray,
    sphere_radius: float,
) -> bool:
    """Test axis-aligned box vs sphere intersection."""
    return sphere_aabb_intersect(
        center=sphere_center,
        radius=sphere_radius,
        aabb_min=box_center - box_half,
        aabb_max=box_center + box_half,
    )


def _sat_axes(a_axes: np.ndarray, b_axes: np.ndarray):
    """Yield the 15 separating axes for two sets of 3 axes."""
    for i in range(3):
        yield a_axes[i]
    for i in range(3):
        yield b_axes[i]
    for i in range(3):
        for j in range(3):
            yield np.cross(a_axes[i], b_axes[j])
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_environment_geo.py -v`
Expected: all PASS

- [ ] **Step 6: Lint and commit**

```bash
python -m ruff check src/aegis/environment/geo.py tests/test_environment_geo.py
python -m ruff format src/aegis/environment/geo.py tests/test_environment_geo.py
git add src/aegis/environment/geo.py tests/test_environment_geo.py
git commit -m "Add coordinate transforms and bounding volume tests (geo.py)"
```

---

## Task 3: Materials module

**Files:**
- Create: `src/aegis/environment/materials.py`
- Test: `tests/test_environment_materials.py`

- [ ] **Step 1: Write tests**

```python
# tests/test_environment_materials.py
import pytest

from aegis.environment import MaterialType, MATERIAL_EM_PROPERTIES
from aegis.environment.materials import get_em_properties, classify_color


class TestGetEmProperties:
    def test_default_concrete(self):
        eps_r, sigma = get_em_properties(MaterialType.CONCRETE)
        assert eps_r == pytest.approx(5.31)
        assert sigma == pytest.approx(0.0326)

    def test_override(self):
        eps_r, sigma = get_em_properties(
            MaterialType.CONCRETE,
            overrides={"concrete": {"eps_r": 6.0, "sigma": 0.05}},
        )
        assert eps_r == pytest.approx(6.0)
        assert sigma == pytest.approx(0.05)

    def test_unknown_defaults_to_concrete(self):
        eps_r, sigma = get_em_properties(MaterialType.UNKNOWN)
        concrete = MATERIAL_EM_PROPERTIES[MaterialType.CONCRETE]
        assert eps_r == pytest.approx(concrete["eps_r"])


class TestClassifyColor:
    def test_gray_is_concrete(self):
        assert classify_color(128, 128, 128) == MaterialType.CONCRETE

    def test_green_is_vegetation(self):
        assert classify_color(50, 150, 50) == MaterialType.VEGETATION

    def test_blue_is_water(self):
        assert classify_color(30, 30, 200) == MaterialType.WATER

    def test_dark_gray_is_asphalt(self):
        assert classify_color(60, 60, 60) == MaterialType.ASPHALT

    def test_brown_is_brick(self):
        assert classify_color(160, 82, 45) == MaterialType.BRICK
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_environment_materials.py -v`

- [ ] **Step 3: Implement materials.py**

```python
# src/aegis/environment/materials.py
"""EM material properties (ITU-R P.2040) and vertex-color classification."""

from __future__ import annotations

import colorsys

from aegis.environment import MaterialType, MATERIAL_EM_PROPERTIES


def get_em_properties(
    material: MaterialType,
    freq_hz: float = 28e9,
    overrides: dict | None = None,
) -> tuple[float, float]:
    """Return (eps_r, sigma) for a material at given frequency.

    If overrides contains a key matching the material name (lowercase),
    those values are used instead of the defaults.
    """
    name = material.name.lower()
    if overrides and name in overrides:
        props = overrides[name]
        return props["eps_r"], props["sigma"]
    props = MATERIAL_EM_PROPERTIES[material]
    return props["eps_r"], props["sigma"]


def classify_color(r: int, g: int, b: int) -> MaterialType:
    """Classify an RGB vertex color (0-255) into a MaterialType.

    Uses HSV-based heuristics similar to scene_data.classify_material().
    """
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    h360 = h * 360

    # very dark -> asphalt
    if v < 0.30:
        return MaterialType.ASPHALT

    # low saturation -> concrete or asphalt
    if s < 0.15:
        if v < 0.45:
            return MaterialType.ASPHALT
        return MaterialType.CONCRETE

    # blue -> water
    if 190 < h360 < 260 and s > 0.3:
        return MaterialType.WATER

    # green -> vegetation
    if 80 < h360 < 170 and s > 0.2:
        return MaterialType.VEGETATION

    # orange-brown -> brick
    if 10 < h360 < 45 and s > 0.3:
        return MaterialType.BRICK

    # yellow-ish -> wood
    if 35 < h360 < 65 and s > 0.2:
        return MaterialType.WOOD

    # high value, low saturation metallic
    if v > 0.7 and s < 0.1:
        return MaterialType.METAL

    return MaterialType.CONCRETE
```

- [ ] **Step 4: Run tests, lint, commit**

```bash
python -m pytest tests/test_environment_materials.py -v
python -m ruff check src/aegis/environment/materials.py tests/test_environment_materials.py
python -m ruff format src/aegis/environment/materials.py tests/test_environment_materials.py
git add src/aegis/environment/materials.py tests/test_environment_materials.py
git commit -m "Add EM material properties and color classification"
```

---

## Task 4: Geometry utilities (triangulation and wall extrusion)

**Files:**
- Create: `src/aegis/environment/roofs.py` (start with utilities only, roof types in Task 6)
- Test: `tests/test_environment_roofs.py`

- [ ] **Step 1: Write tests for triangulate_polygon and extrude_walls**

```python
# tests/test_environment_roofs.py
import numpy as np
import pytest

from aegis.environment.roofs import triangulate_polygon, extrude_walls


class TestTriangulatePolygon:
    def test_triangle_returns_itself(self):
        poly = np.array([[0, 0], [1, 0], [0, 1]], dtype=np.float64)
        tris = triangulate_polygon(poly)
        assert tris.shape == (1, 3)
        np.testing.assert_array_equal(tris[0], [0, 1, 2])

    def test_square(self):
        poly = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=np.float64)
        tris = triangulate_polygon(poly)
        assert tris.shape == (2, 3)
        # all indices should be in [0, 3]
        assert tris.min() >= 0
        assert tris.max() <= 3

    def test_pentagon(self):
        angles = np.linspace(0, 2 * np.pi, 6)[:-1]
        poly = np.column_stack([np.cos(angles), np.sin(angles)])
        tris = triangulate_polygon(poly)
        assert tris.shape == (3, 3)  # n-2 triangles

    def test_ccw_winding(self):
        """All output triangles should have CCW winding (positive signed area)."""
        poly = np.array([[0, 0], [2, 0], [2, 1], [1, 2], [0, 1]], dtype=np.float64)
        tris = triangulate_polygon(poly)
        for tri in tris:
            a, b, c = poly[tri[0]], poly[tri[1]], poly[tri[2]]
            cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            assert cross > 0, f"Triangle {tri} has CW winding"


class TestExtrudeWalls:
    def test_square_building_walls(self):
        footprint = np.array([[0, 0], [10, 0], [10, 10], [0, 10]], dtype=np.float64)
        verts, tris = extrude_walls(footprint, base_height=0.0, top_height=5.0)
        # 4 walls, each wall = 4 vertices + 2 triangles
        assert verts.shape[0] == 16  # 4 walls * 4 verts
        assert verts.shape[1] == 3   # 3D
        assert tris.shape[0] == 8    # 4 walls * 2 tris
        # z values should be 0 or 5
        z_vals = np.unique(verts[:, 2])
        np.testing.assert_allclose(sorted(z_vals), [0.0, 5.0])

    def test_triangle_building_walls(self):
        footprint = np.array([[0, 0], [5, 0], [2.5, 4]], dtype=np.float64)
        verts, tris = extrude_walls(footprint, base_height=0.0, top_height=3.0)
        assert verts.shape[0] == 12  # 3 walls * 4 verts
        assert tris.shape[0] == 6   # 3 walls * 2 tris
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_environment_roofs.py::TestTriangulatePolygon tests/test_environment_roofs.py::TestExtrudeWalls -v`

- [ ] **Step 3: Implement triangulate_polygon and extrude_walls**

```python
# src/aegis/environment/roofs.py
"""Building geometry: wall extrusion and roof algorithms.

All functions output numpy arrays. No Blender/bmesh dependency.
Reference: blosm/building/roof/, blosm/action/volume/
"""

from __future__ import annotations

import numpy as np

from aegis.environment import MaterialType


def triangulate_polygon(polygon: np.ndarray) -> np.ndarray:
    """Triangulate a 2D polygon using ear clipping.

    Args:
        polygon: (N, 2) array of 2D vertices in CCW order.

    Returns:
        (N-2, 3) uint32 array of triangle indices.
    """
    n = len(polygon)
    if n < 3:
        return np.empty((0, 3), dtype=np.uint32)
    if n == 3:
        return np.array([[0, 1, 2]], dtype=np.uint32)

    # ensure CCW winding
    signed_area = _signed_area_2d(polygon)
    indices = list(range(n))
    if signed_area < 0:
        indices = indices[::-1]

    triangles = []
    remaining = list(indices)

    max_iter = n * n  # safety valve
    iteration = 0
    while len(remaining) > 3 and iteration < max_iter:
        iteration += 1
        ear_found = False
        for i in range(len(remaining)):
            prev_i = (i - 1) % len(remaining)
            next_i = (i + 1) % len(remaining)
            a = polygon[remaining[prev_i]]
            b = polygon[remaining[i]]
            c = polygon[remaining[next_i]]
            # check convex
            cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            if cross <= 0:
                continue
            # check no other vertex inside triangle
            is_ear = True
            for j in range(len(remaining)):
                if j in (prev_i, i, next_i):
                    continue
                if _point_in_triangle(polygon[remaining[j]], a, b, c):
                    is_ear = False
                    break
            if is_ear:
                triangles.append([remaining[prev_i], remaining[i], remaining[next_i]])
                remaining.pop(i)
                ear_found = True
                break
        if not ear_found:
            break  # degenerate polygon

    if len(remaining) == 3:
        triangles.append(remaining)

    return np.array(triangles, dtype=np.uint32) if triangles else np.empty((0, 3), dtype=np.uint32)


def extrude_walls(
    footprint: np.ndarray,
    base_height: float,
    top_height: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Extrude vertical walls from a 2D footprint polygon.

    Args:
        footprint: (N, 2) array of 2D footprint vertices.
        base_height: Z coordinate of the bottom edge.
        top_height: Z coordinate of the top edge.

    Returns:
        (vertices, triangles) where vertices is (N*4, 3) float64
        and triangles is (N*2, 3) uint32.
    """
    n = len(footprint)
    vertices = []
    triangles = []
    for i in range(n):
        j = (i + 1) % n
        p0 = footprint[i]
        p1 = footprint[j]
        base_idx = len(vertices)
        # quad: bottom-left, bottom-right, top-right, top-left
        vertices.append([p0[0], p0[1], base_height])
        vertices.append([p1[0], p1[1], base_height])
        vertices.append([p1[0], p1[1], top_height])
        vertices.append([p0[0], p0[1], top_height])
        # two triangles per quad
        triangles.append([base_idx, base_idx + 1, base_idx + 2])
        triangles.append([base_idx, base_idx + 2, base_idx + 3])

    return (
        np.array(vertices, dtype=np.float64),
        np.array(triangles, dtype=np.uint32),
    )


def _signed_area_2d(polygon: np.ndarray) -> float:
    """Signed area of a 2D polygon (positive = CCW)."""
    x = polygon[:, 0]
    y = polygon[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def _point_in_triangle(
    p: np.ndarray, a: np.ndarray, b: np.ndarray, c: np.ndarray
) -> bool:
    """Test if 2D point p is inside triangle abc."""
    d1 = (p[0] - c[0]) * (a[1] - c[1]) - (a[0] - c[0]) * (p[1] - c[1])
    d2 = (p[0] - a[0]) * (b[1] - a[1]) - (b[0] - a[0]) * (p[1] - a[1])
    d3 = (p[0] - b[0]) * (c[1] - b[1]) - (c[0] - b[0]) * (p[1] - b[1])
    has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
    has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
    return not (has_neg and has_pos)
```

- [ ] **Step 4: Run tests, lint, commit**

```bash
python -m pytest tests/test_environment_roofs.py -v
python -m ruff check src/aegis/environment/roofs.py tests/test_environment_roofs.py
python -m ruff format src/aegis/environment/roofs.py tests/test_environment_roofs.py
git add src/aegis/environment/roofs.py tests/test_environment_roofs.py
git commit -m "Add polygon triangulation and wall extrusion utilities"
```

---

## Task 5: Straight skeleton (numpy bpyeuclid replacement)

**Files:**
- Create: `src/aegis/environment/skeleton.py`
- Test: `tests/test_environment_skeleton.py`
- Reference: `blosm/lib/bpypolyskel/bpyeuclid.py` (109 lines), `blosm/lib/bpypolyskel/bpypolyskel.py` (1177 lines)

This task replaces `bpyeuclid.py` with pure numpy, then adapts `bpypolyskel.py` to use it. The straight skeleton is needed for hipped, half-hipped, and mansard roofs.

- [ ] **Step 1: Write tests for skeleton on known polygons**

```python
# tests/test_environment_skeleton.py
import numpy as np
import pytest

from aegis.environment.skeleton import skeletonize, polygonize


class TestSkeletonize:
    def test_square(self):
        """Square skeleton should produce a single apex at center."""
        verts = np.array([[0, 0], [10, 0], [10, 10], [0, 10]], dtype=np.float64)
        arcs = skeletonize([verts])
        assert len(arcs) > 0
        # all arc sources should be at or near the center
        for arc in arcs:
            assert 0 <= arc.source[0] <= 10
            assert 0 <= arc.source[1] <= 10

    def test_rectangle(self):
        """Rectangle skeleton should produce a ridge line along the long axis."""
        verts = np.array([[0, 0], [20, 0], [20, 10], [0, 10]], dtype=np.float64)
        arcs = skeletonize([verts])
        assert len(arcs) > 0

    def test_triangle(self):
        """Triangle skeleton should produce a single apex."""
        verts = np.array([[0, 0], [10, 0], [5, 8]], dtype=np.float64)
        arcs = skeletonize([verts])
        assert len(arcs) > 0
        # should have exactly one subtree (peak event)
        sources = [arc.source for arc in arcs]
        assert len(sources) >= 1


class TestPolygonize:
    def test_square_produces_faces(self):
        """Polygonize a square at height 5 should produce triangular roof faces."""
        verts_list = []  # will be populated by polygonize
        footprint = np.array([[0, 0], [10, 0], [10, 10], [0, 10]], dtype=np.float64)
        faces = polygonize(verts_list, footprint, height=5.0)
        assert len(faces) > 0
        # each face should be a list of vertex indices
        for face in faces:
            assert len(face) >= 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_environment_skeleton.py -v`

- [ ] **Step 3: Implement skeleton.py**

This is the largest single implementation task. The file must:
1. Reimplement `bpyeuclid.py` geometry primitives (`Edge2`, `Ray2`, `Line2`, `_intersect_line2_line2`, `fitCircle3Points`) using numpy instead of `mathutils.Vector`.
2. Adapt `bpypolyskel.py`'s `skeletonize()` and `polygonize()` to use the numpy primitives.
3. Adapt `poly2FacesGraph.py` for the face extraction step.

Key numpy replacements:
- `mathutils.Vector((x, y))` -> `np.array([x, y])`
- `v.normalize()` -> `v /= np.linalg.norm(v)` (in-place) or `v / np.linalg.norm(v)`
- `v.magnitude` / `v.length` -> `np.linalg.norm(v)`
- `v.length_squared` -> `np.dot(v, v)`
- `a.dot(b)` -> `np.dot(a, b)`
- `a.cross(b)` (2D, returns scalar) -> `np.cross(a, b)`
- `v.normalized()` -> `v / np.linalg.norm(v)`
- `v.xy` -> `v[:2]`
- `mathutils.geometry.intersect_point_line(pt, p1, p2)` -> manual projection: `t = np.dot(pt - p1, v) / np.dot(v, v); nearest = p1 + t * v`

The implementation should be written as a single `skeleton.py` file, porting the algorithms from the three blosm source files. Consult:
- `blosm/lib/bpypolyskel/bpyeuclid.py` for geometry primitives
- `blosm/lib/bpypolyskel/bpypolyskel.py` for the main algorithm
- `blosm/lib/bpypolyskel/poly2FacesGraph.py` for face extraction

The module should export:
- `skeletonize(edge_contours: list[np.ndarray]) -> list[Subtree]` where `Subtree = namedtuple("Subtree", ["source", "height", "sinks"])` and `source`/`sinks` are numpy arrays.
- `polygonize(verts_out: list, footprint: np.ndarray, height: float, ...) -> list[list[int]]`

- [ ] **Step 4: Run tests, lint, commit**

```bash
python -m pytest tests/test_environment_skeleton.py -v
python -m ruff check src/aegis/environment/skeleton.py tests/test_environment_skeleton.py
python -m ruff format src/aegis/environment/skeleton.py tests/test_environment_skeleton.py
git add src/aegis/environment/skeleton.py tests/test_environment_skeleton.py
git commit -m "Add pure-numpy straight skeleton algorithm"
```

---

## Task 6: Roof type algorithms

**Files:**
- Modify: `src/aegis/environment/roofs.py` (add `generate_building` and all roof types)
- Modify: `tests/test_environment_roofs.py` (add roof type tests)
- Reference: `blosm/building/roof/`, `blosm/action/volume/roof_*.py`

Depends on: Task 4 (triangulate_polygon, extrude_walls), Task 5 (skeleton for hipped roofs).

- [ ] **Step 1: Write tests for generate_building with each roof type**

```python
# append to tests/test_environment_roofs.py
from aegis.environment import MaterialType
from aegis.environment.roofs import generate_building

SQUARE = np.array([[0, 0], [10, 0], [10, 10], [0, 10]], dtype=np.float64)
RECTANGLE = np.array([[0, 0], [20, 0], [20, 10], [0, 10]], dtype=np.float64)
ROOF_TYPES = [
    "flat", "gabled", "hipped", "pyramidal", "skillion",
    "half_hipped", "gambrel", "saltbox", "mansard",
    "dome", "onion", "round",
]


class TestGenerateBuilding:
    @pytest.mark.parametrize("roof_shape", ROOF_TYPES)
    def test_produces_valid_mesh(self, roof_shape):
        footprint = RECTANGLE if roof_shape in ("gabled", "saltbox", "round") else SQUARE
        verts, tris, mats = generate_building(
            footprint=footprint,
            height=10.0,
            roof_shape=roof_shape,
            roof_height=3.0,
        )
        assert verts.ndim == 2 and verts.shape[1] == 3
        assert tris.ndim == 2 and tris.shape[1] == 3
        assert mats.ndim == 1
        assert len(mats) == len(tris)
        # all triangle indices should be valid
        assert tris.max() < len(verts)
        assert tris.min() >= 0

    @pytest.mark.parametrize("roof_shape", ROOF_TYPES)
    def test_normals_nonzero(self, roof_shape):
        footprint = RECTANGLE if roof_shape in ("gabled", "saltbox", "round") else SQUARE
        verts, tris, mats = generate_building(
            footprint=footprint,
            height=10.0,
            roof_shape=roof_shape,
        )
        # compute face normals from vertex positions
        v0 = verts[tris[:, 0]]
        v1 = verts[tris[:, 1]]
        v2 = verts[tris[:, 2]]
        normals = np.cross(v1 - v0, v2 - v0)
        areas = np.linalg.norm(normals, axis=1)
        # no degenerate triangles (area > 0)
        assert np.all(areas > 1e-10), f"Degenerate triangles in {roof_shape}"

    def test_flat_roof_height(self):
        verts, tris, mats = generate_building(
            footprint=SQUARE, height=10.0, roof_shape="flat",
        )
        # max z should be exactly the building height
        assert verts[:, 2].max() == pytest.approx(10.0)

    def test_gabled_roof_ridge_above_eave(self):
        verts, tris, mats = generate_building(
            footprint=RECTANGLE, height=10.0, roof_shape="gabled", roof_height=3.0,
        )
        assert verts[:, 2].max() == pytest.approx(13.0, abs=0.5)

    def test_material_assignment(self):
        verts, tris, mats = generate_building(
            footprint=SQUARE, height=10.0, roof_shape="flat",
            material=MaterialType.BRICK, roof_material=MaterialType.CONCRETE,
        )
        # should have both wall material and roof material
        assert MaterialType.BRICK in mats
        assert MaterialType.CONCRETE in mats
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_environment_roofs.py::TestGenerateBuilding -v`

- [ ] **Step 3: Implement generate_building and all roof types**

Add to `src/aegis/environment/roofs.py`:
- `generate_building(footprint, height, roof_shape, ...)` - dispatcher
- `_roof_flat(footprint, height)` - fan triangulation of top polygon
- `_roof_gabled(footprint, height, roof_height)` - ridge along longest axis
- `_roof_hipped(footprint, height, roof_height)` - straight skeleton from `skeleton.py`
- `_roof_pyramidal(footprint, height, roof_height)` - single apex at centroid
- `_roof_skillion(footprint, height, roof_height)` - single slope plane
- `_roof_half_hipped(footprint, height, roof_height)` - hybrid gabled+hipped
- `_roof_gambrel(footprint, height, roof_height)` - double-slope profile
- `_roof_saltbox(footprint, height, roof_height)` - asymmetric gabled
- `_roof_mansard(footprint, height, roof_height)` - four-sided double-slope
- `_roof_dome(footprint, height, roof_height)` - parametric hemisphere
- `_roof_onion(footprint, height, roof_height)` - parametric onion curve
- `_roof_round(footprint, height, roof_height)` - barrel vault

Each roof function returns `(vertices, triangles)` as numpy arrays. `generate_building` combines walls + roof and assigns materials.

Reference algorithms in detail:
- **flat**: `triangulate_polygon(footprint)` at `height`, lift z coordinates
- **gabled**: find longest edge pair, compute ridge line midway between them at `height + roof_height`, create 4 slope faces + 2 gable triangles
- **hipped**: call `skeleton.polygonize()` to get face loops, lift skeleton nodes by height proportional to their distance from edges
- **pyramidal**: centroid of footprint at `height + roof_height`, connect to each edge
- **skillion**: tilt one edge up by `roof_height`, keep opposite edge at `height`
- **half_hipped**: gabled with the gable triangles replaced by small hip planes
- **gambrel**: two-segment profile on each side (steep lower, shallow upper)
- **saltbox**: asymmetric gabled with ridge offset toward one side
- **mansard**: inset footprint at lower break, then inset again for upper break
- **dome**: parametric hemisphere using lat/lon subdivision (8 segments, 6 rings typical)
- **onion**: parametric curve `r(t) = R * sin(t) * (1 + 0.3 * sin(3t))` revolved
- **round**: barrel vault: semicircular cross-section extruded along ridge

- [ ] **Step 4: Run tests, lint, commit**

```bash
python -m pytest tests/test_environment_roofs.py -v
python -m ruff check src/aegis/environment/roofs.py tests/test_environment_roofs.py
python -m ruff format src/aegis/environment/roofs.py tests/test_environment_roofs.py
git add src/aegis/environment/roofs.py tests/test_environment_roofs.py
git commit -m "Add all 12 roof type algorithms"
```

---

## Task 7: OSM pipeline

**Files:**
- Create: `src/aegis/environment/osm.py`
- Test: `tests/test_environment_osm.py`
- Test fixture: `tests/fixtures/osm_sample.xml` (small OSM XML for unit testing)
- Reference: `blosm/parse/osm/__init__.py`

Depends on: Task 2 (geo.py), Task 4+6 (roofs.py).

- [ ] **Step 1: Create OSM XML test fixture**

Create `tests/fixtures/osm_sample.xml` with a small sample containing:
- 2-3 buildings (one with `roof:shape=gabled`, one with `building:material=brick`)
- 1 road segment
- 1 water polygon
- Centered around a known lat/lon (e.g. 51.05, 3.72)

- [ ] **Step 2: Write tests**

```python
# tests/test_environment_osm.py
from pathlib import Path

import numpy as np
import pytest

from aegis.environment import EnvironmentMesh, MaterialType
from aegis.environment.osm import parse_osm_xml, build_environment_from_osm

FIXTURE = Path(__file__).parent / "fixtures" / "osm_sample.xml"


class TestParseOsmXml:
    def test_extracts_buildings(self):
        buildings, roads, water = parse_osm_xml(FIXTURE.read_text())
        assert len(buildings) >= 2

    def test_building_has_footprint(self):
        buildings, _, _ = parse_osm_xml(FIXTURE.read_text())
        for b in buildings:
            assert b.footprint.shape[1] == 2
            assert len(b.footprint) >= 3

    def test_building_material_tag(self):
        buildings, _, _ = parse_osm_xml(FIXTURE.read_text())
        brick_buildings = [b for b in buildings if b.material == MaterialType.BRICK]
        assert len(brick_buildings) >= 1

    def test_extracts_roads(self):
        _, roads, _ = parse_osm_xml(FIXTURE.read_text())
        assert len(roads) >= 1

    def test_extracts_water(self):
        _, _, water = parse_osm_xml(FIXTURE.read_text())
        assert len(water) >= 1


class TestBuildEnvironment:
    def test_produces_environment_mesh(self):
        xml = FIXTURE.read_text()
        mesh = build_environment_from_osm(xml, origin_lat=51.05, origin_lon=3.72)
        assert isinstance(mesh, EnvironmentMesh)
        assert mesh.vertices.shape[1] == 3
        assert mesh.triangles.shape[1] == 3
        assert len(mesh.materials) == len(mesh.triangles)
        assert mesh.source == "osm"

    def test_contains_multiple_materials(self):
        xml = FIXTURE.read_text()
        mesh = build_environment_from_osm(xml, origin_lat=51.05, origin_lon=3.72)
        unique_mats = set(mesh.materials.tolist())
        assert len(unique_mats) >= 2  # at least walls + roads
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_environment_osm.py -v`

- [ ] **Step 4: Implement osm.py**

```python
# src/aegis/environment/osm.py
"""OpenStreetMap data fetching and mesh generation.

Fetches OSM data via Overpass API, parses XML, generates 3D building
geometry with roofs, roads, and water bodies.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

import numpy as np
import requests

from aegis.environment import EnvironmentMesh, MaterialType
from aegis.environment.geo import transverse_mercator_forward
from aegis.environment.roofs import generate_building, triangulate_polygon

_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
_TIMEOUT = 60
_MAX_RESPONSE_BYTES = 50 * 1024 * 1024  # 50 MB

_MATERIAL_TAG_MAP = {
    "brick": MaterialType.BRICK,
    "stone": MaterialType.CONCRETE,
    "concrete": MaterialType.CONCRETE,
    "wood": MaterialType.WOOD,
    "glass": MaterialType.GLASS,
    "metal": MaterialType.METAL,
    "steel": MaterialType.METAL,
}


@dataclass
class Building:
    footprint: np.ndarray  # (N, 2) in local meters
    height: float = 10.0
    roof_shape: str = "flat"
    roof_height: float | None = None
    material: MaterialType = MaterialType.CONCRETE
    roof_material: MaterialType = MaterialType.CONCRETE


@dataclass
class Road:
    centerline: np.ndarray  # (N, 2) in local meters
    width: float = 6.0


@dataclass
class WaterBody:
    polygon: np.ndarray  # (N, 2) in local meters


def fetch_osm(lat: float, lon: float, radius_m: float) -> str:
    """Fetch OSM data from Overpass API. Returns raw XML string."""
    # bounding box from center + radius
    dlat = radius_m / 111_000
    dlon = radius_m / (111_000 * np.cos(np.radians(lat)))
    bbox = f"{lat - dlat},{lon - dlon},{lat + dlat},{lon + dlon}"

    query = f"""
    [out:xml][timeout:{_TIMEOUT}];
    (
      way["building"]({bbox});
      way["highway"]({bbox});
      way["natural"="water"]({bbox});
      way["waterway"]({bbox});
      relation["natural"="water"]({bbox});
    );
    (._;>;);
    out body;
    """

    try:
        resp = requests.post(
            _OVERPASS_URL,
            data={"data": query},
            timeout=_TIMEOUT,
        )
    except requests.exceptions.Timeout:
        raise OverpassTimeoutError("Overpass API timed out, try a smaller radius")

    if resp.status_code == 429:
        raise OverpassRateLimitError("Rate limited by Overpass API")
    if resp.status_code == 504:
        raise OverpassTimeoutError("Overpass API timed out, try a smaller radius")
    resp.raise_for_status()

    # cap response size
    content = resp.content
    if len(content) > _MAX_RESPONSE_BYTES:
        raise OverpassResponseTooLarge(
            f"Response is {len(content) / 1e6:.0f} MB, max is {_MAX_RESPONSE_BYTES / 1e6:.0f} MB"
        )
    return content.decode("utf-8")


class OverpassRateLimitError(Exception):
    pass


class OverpassTimeoutError(Exception):
    pass


class OverpassResponseTooLarge(Exception):
    pass


def parse_osm_xml(
    xml_str: str,
    origin_lat: float = 0.0,
    origin_lon: float = 0.0,
    default_building_height: float = 10.0,
    level_height: float = 3.0,
) -> tuple[list[Building], list[Road], list[WaterBody]]:
    """Parse OSM XML into building, road, and water objects.

    Coordinates are projected to local XY meters via Transverse Mercator
    centered on (origin_lat, origin_lon).
    """
    root = ET.fromstring(xml_str)

    # build node lookup: id -> (lat, lon)
    nodes: dict[str, tuple[float, float]] = {}
    for node in root.iter("node"):
        nid = node.get("id")
        lat = float(node.get("lat"))
        lon = float(node.get("lon"))
        nodes[nid] = (lat, lon)

    # if no origin provided, use center of bounds or first node
    if origin_lat == 0.0 and origin_lon == 0.0:
        bounds = root.find("bounds")
        if bounds is not None:
            origin_lat = (float(bounds.get("minlat")) + float(bounds.get("maxlat"))) / 2
            origin_lon = (float(bounds.get("minlon")) + float(bounds.get("maxlon"))) / 2
        elif nodes:
            first = next(iter(nodes.values()))
            origin_lat, origin_lon = first

    def project(lat: float, lon: float) -> tuple[float, float]:
        return transverse_mercator_forward(lat, lon, origin_lat, origin_lon)

    buildings = []
    roads = []
    water = []

    for way in root.iter("way"):
        tags = {tag.get("k"): tag.get("v") for tag in way.iter("tag")}
        nd_refs = [nd.get("ref") for nd in way.iter("nd")]

        # skip if nodes are missing
        if not all(ref in nodes for ref in nd_refs):
            continue

        coords = np.array([project(*nodes[ref]) for ref in nd_refs], dtype=np.float64)

        if "building" in tags:
            # determine height
            height = default_building_height
            if "height" in tags:
                try:
                    height = float(tags["height"])
                except ValueError:
                    pass
            elif "building:levels" in tags:
                try:
                    height = float(tags["building:levels"]) * level_height
                except ValueError:
                    pass

            # roof shape
            roof_shape = tags.get("roof:shape", "flat")

            # roof height
            roof_height = None
            if "roof:height" in tags:
                try:
                    roof_height = float(tags["roof:height"])
                except ValueError:
                    pass

            # material
            mat_tag = tags.get("building:material", tags.get("building:facade:material", ""))
            material = _MATERIAL_TAG_MAP.get(mat_tag.lower(), MaterialType.CONCRETE)

            roof_mat_tag = tags.get("roof:material", "")
            roof_material = _MATERIAL_TAG_MAP.get(roof_mat_tag.lower(), MaterialType.CONCRETE)

            # close the polygon if needed
            footprint = coords[:-1] if np.allclose(coords[0], coords[-1]) else coords

            if len(footprint) >= 3:
                buildings.append(Building(
                    footprint=footprint,
                    height=height,
                    roof_shape=roof_shape,
                    roof_height=roof_height,
                    material=material,
                    roof_material=roof_material,
                ))

        elif "highway" in tags:
            width = 6.0
            if "lanes" in tags:
                try:
                    width = float(tags["lanes"]) * 3.5
                except ValueError:
                    pass
            roads.append(Road(centerline=coords, width=width))

        elif tags.get("natural") == "water" or "waterway" in tags:
            footprint = coords[:-1] if np.allclose(coords[0], coords[-1]) else coords
            if len(footprint) >= 3:
                water.append(WaterBody(polygon=footprint))

    return buildings, roads, water


def build_environment_from_osm(
    xml_str: str,
    origin_lat: float,
    origin_lon: float,
    default_building_height: float = 10.0,
    level_height: float = 3.0,
    buildings_enabled: bool = True,
    roads_enabled: bool = True,
    water_enabled: bool = True,
) -> EnvironmentMesh:
    """Parse OSM XML and generate a complete EnvironmentMesh."""
    buildings, roads, water_bodies = parse_osm_xml(
        xml_str, origin_lat, origin_lon, default_building_height, level_height,
    )

    all_verts = []
    all_tris = []
    all_mats = []
    vert_offset = 0

    if buildings_enabled:
        for b in buildings:
            try:
                verts, tris, mats = generate_building(
                    footprint=b.footprint,
                    height=b.height,
                    roof_shape=b.roof_shape,
                    roof_height=b.roof_height,
                    material=b.material,
                    roof_material=b.roof_material,
                )
                all_verts.append(verts)
                all_tris.append(tris + vert_offset)
                all_mats.append(mats)
                vert_offset += len(verts)
            except Exception:
                continue  # skip malformed buildings

    if roads_enabled:
        for road in roads:
            verts, tris = _road_to_mesh(road)
            mats = np.full(len(tris), MaterialType.ASPHALT, dtype=np.uint8)
            all_verts.append(verts)
            all_tris.append(tris + vert_offset)
            all_mats.append(mats)
            vert_offset += len(verts)

    if water_enabled:
        for wb in water_bodies:
            verts, tris = _water_to_mesh(wb)
            mats = np.full(len(tris), MaterialType.WATER, dtype=np.uint8)
            all_verts.append(verts)
            all_tris.append(tris + vert_offset)
            all_mats.append(mats)
            vert_offset += len(verts)

    if not all_verts:
        return EnvironmentMesh(
            vertices=np.empty((0, 3), dtype=np.float64),
            triangles=np.empty((0, 3), dtype=np.uint32),
            normals=np.empty((0, 3), dtype=np.float64),
            materials=np.empty(0, dtype=np.uint8),
            origin_lat=origin_lat,
            origin_lon=origin_lon,
            source="osm",
        )

    vertices = np.concatenate(all_verts)
    triangles = np.concatenate(all_tris)
    materials = np.concatenate(all_mats)
    normals = _compute_face_normals(vertices, triangles)

    return EnvironmentMesh(
        vertices=vertices,
        triangles=triangles,
        normals=normals,
        materials=materials,
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        source="osm",
    )


def _road_to_mesh(road: Road) -> tuple[np.ndarray, np.ndarray]:
    """Convert a road centerline to a flat quad strip at ground level."""
    pts = road.centerline
    half_w = road.width / 2
    verts = []
    tris = []

    for i in range(len(pts) - 1):
        d = pts[i + 1] - pts[i]
        perp = np.array([-d[1], d[0]])
        perp_len = np.linalg.norm(perp)
        if perp_len < 1e-10:
            continue
        perp = perp / perp_len * half_w

        base = len(verts)
        verts.append([pts[i][0] + perp[0], pts[i][1] + perp[1], 0.0])
        verts.append([pts[i][0] - perp[0], pts[i][1] - perp[1], 0.0])
        verts.append([pts[i + 1][0] - perp[0], pts[i + 1][1] - perp[1], 0.0])
        verts.append([pts[i + 1][0] + perp[0], pts[i + 1][1] + perp[1], 0.0])
        tris.append([base, base + 1, base + 2])
        tris.append([base, base + 2, base + 3])

    if not verts:
        return np.empty((0, 3), dtype=np.float64), np.empty((0, 3), dtype=np.uint32)
    return np.array(verts, dtype=np.float64), np.array(tris, dtype=np.uint32)


def _water_to_mesh(wb: WaterBody) -> tuple[np.ndarray, np.ndarray]:
    """Convert a water polygon to a flat mesh at ground level."""
    tris_2d = triangulate_polygon(wb.polygon)
    verts_3d = np.column_stack([wb.polygon, np.zeros(len(wb.polygon))])
    return verts_3d.astype(np.float64), tris_2d


def _compute_face_normals(
    vertices: np.ndarray, triangles: np.ndarray
) -> np.ndarray:
    """Compute per-face normals from vertices and triangle indices."""
    v0 = vertices[triangles[:, 0]]
    v1 = vertices[triangles[:, 1]]
    v2 = vertices[triangles[:, 2]]
    normals = np.cross(v1 - v0, v2 - v0)
    norms = np.linalg.norm(normals, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-10)
    return normals / norms
```

- [ ] **Step 5: Run tests, lint, commit**

```bash
python -m pytest tests/test_environment_osm.py -v
python -m ruff check src/aegis/environment/osm.py tests/test_environment_osm.py
python -m ruff format src/aegis/environment/osm.py tests/test_environment_osm.py
git add src/aegis/environment/osm.py tests/test_environment_osm.py tests/fixtures/osm_sample.xml
git commit -m "Add OSM pipeline: Overpass fetch, XML parse, mesh generation"
```

---

## Task 8: 3D Tiles server-side pipeline

**Files:**
- Create: `src/aegis/environment/tiles.py`
- Test: `tests/test_environment_tiles.py` (unit tests with mocked HTTP)
- Reference: `blosm/threed_tiles/manager.py`, `blosm/threed_tiles/py3dtiles/`

Depends on: Task 2 (geo.py), Task 3 (materials.py).

- [ ] **Step 1: Write tests with mocked tile responses**

```python
# tests/test_environment_tiles.py
import json
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from aegis.environment.tiles import TileTraverser


class TestTileTraverser:
    def test_init_with_api_key(self):
        t = TileTraverser(
            root_url="https://tile.googleapis.com/v1/3dtiles/root.json",
            api_key="test-key",
            geometric_error=30.0,
        )
        assert t.geometric_error == 30.0

    def test_init_without_api_key(self):
        t = TileTraverser(
            root_url="https://example.com/tileset.json",
            geometric_error=60.0,
        )
        assert t.api_key is None

    @patch("aegis.environment.tiles.requests.Session")
    def test_traverse_empty_tileset(self, mock_session_cls):
        """A tileset with no content should return an empty mesh."""
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        tileset = {
            "root": {
                "boundingVolume": {
                    "sphere": [0, 0, 0, 1000]
                },
                "geometricError": 1000,
            },
            "geometricError": 1000,
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = tileset
        mock_resp.status_code = 200
        mock_session.get.return_value = mock_resp

        t = TileTraverser.__new__(TileTraverser)
        t.root_url = "https://example.com/tileset.json"
        t.api_key = None
        t.geometric_error = 30.0
        t.session = mock_session

        mesh = t.traverse(lat=51.05, lon=3.72, radius_m=200)
        assert mesh.vertices.shape[1] == 3
        assert mesh.source == "3dtiles"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_environment_tiles.py -v`

- [ ] **Step 3: Implement tiles.py**

The module should implement `TileTraverser` with:
- `__init__(root_url, api_key, geometric_error)` - sets up requests.Session with Google auth headers if api_key provided
- `traverse(lat, lon, radius_m)` - fetches root tileset.json, recurses through tile tree
- `_traverse_node(node, query_ecef, query_radius, origin_ecef, origin_lat, origin_lon)` - recursive traversal
- `_check_intersection(bounding_volume, query_ecef, query_radius)` - dispatches to sphere/box/region tests from geo.py
- `_fetch_tile_content(content_uri)` - fetches B3DM or GLB binary content
- `_parse_glb(data)` - uses blosm's py3dtiles to extract vertices, indices, vertex colors from binary glTF
- `_parse_b3dm(data)` - extracts glTF from B3DM wrapper via py3dtiles

Import blosm's py3dtiles using importlib to bypass `blosm/__init__.py`:
```python
import importlib.util
import sys
from pathlib import Path

_BLOSM_ROOT = Path(__file__).resolve().parents[3] / "blosm"
_PY3DTILES = _BLOSM_ROOT / "threed_tiles" / "py3dtiles"

def _import_py3dtiles():
    """Import py3dtiles without triggering blosm/__init__.py."""
    if "py3dtiles_blosm" not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            "py3dtiles_blosm",
            _PY3DTILES / "__init__.py",
            submodule_search_locations=[str(_PY3DTILES)],
        )
        mod = importlib.util.module_from_spec(spec)
        sys.modules["py3dtiles_blosm"] = mod
        spec.loader.exec_module(mod)
    return sys.modules["py3dtiles_blosm"]
```

- [ ] **Step 4: Run tests, lint, commit**

```bash
python -m pytest tests/test_environment_tiles.py -v
python -m ruff check src/aegis/environment/tiles.py tests/test_environment_tiles.py
python -m ruff format src/aegis/environment/tiles.py tests/test_environment_tiles.py
git add src/aegis/environment/tiles.py tests/test_environment_tiles.py
git commit -m "Add 3D Tiles server-side traversal and mesh extraction"
```

---

## Task 9: Export module (DiffeRT, Sionna, binary)

**Files:**
- Create: `src/aegis/environment/export.py`
- Test: `tests/test_environment_export.py`
- Reference: `src/aegis/viewer/raytracer.py` (lines 459-556 for DiffeRT TriangleScene construction pattern)

Depends on: Task 1 (EnvironmentMesh), Task 2 (geo.py for enu_to_yup).

- [ ] **Step 1: Write tests**

```python
# tests/test_environment_export.py
import json
from pathlib import Path

import numpy as np
import pytest

from aegis.environment import EnvironmentMesh, MaterialType
from aegis.environment.export import to_binary, to_sionna_xml


@pytest.fixture
def sample_mesh():
    """Two-triangle mesh for testing exports."""
    vertices = np.array([
        [0, 0, 0], [10, 0, 0], [10, 10, 0],
        [0, 0, 0], [10, 10, 0], [0, 10, 0],
    ], dtype=np.float64)
    triangles = np.array([[0, 1, 2], [3, 4, 5]], dtype=np.uint32)
    normals = np.array([[0, 0, 1], [0, 0, 1]], dtype=np.float64)
    materials = np.array([MaterialType.CONCRETE, MaterialType.ASPHALT], dtype=np.uint8)
    return EnvironmentMesh(
        vertices=vertices, triangles=triangles, normals=normals,
        materials=materials, origin_lat=51.05, origin_lon=3.72, source="test",
    )


class TestToBinary:
    def test_produces_bytes_and_meta(self, sample_mesh):
        data, meta = to_binary(sample_mesh)
        assert isinstance(data, bytes)
        assert isinstance(meta, dict)

    def test_meta_keys(self, sample_mesh):
        _, meta = to_binary(sample_mesh)
        assert "n_vertices" in meta
        assert "n_triangles" in meta
        assert "source" in meta
        assert meta["n_vertices"] == 6
        assert meta["n_triangles"] == 2

    def test_round_trip(self, sample_mesh):
        """Binary data should be parseable back to arrays."""
        data, meta = to_binary(sample_mesh)
        n_v = meta["n_vertices"]
        n_t = meta["n_triangles"]
        offset = 0
        # vertices: float32 (n_v * 3)
        v_bytes = n_v * 3 * 4
        verts = np.frombuffer(data[offset:offset + v_bytes], dtype=np.float32).reshape(n_v, 3)
        offset += v_bytes
        # triangles: uint32 (n_t * 3)
        t_bytes = n_t * 3 * 4
        tris = np.frombuffer(data[offset:offset + t_bytes], dtype=np.uint32).reshape(n_t, 3)
        offset += t_bytes
        # normals: float32 (n_t * 3)
        n_bytes = n_t * 3 * 4
        norms = np.frombuffer(data[offset:offset + n_bytes], dtype=np.float32).reshape(n_t, 3)
        offset += n_bytes
        # materials: uint8 (n_t)
        mats = np.frombuffer(data[offset:offset + n_t], dtype=np.uint8)

        np.testing.assert_allclose(verts, sample_mesh.vertices.astype(np.float32), atol=1e-5)
        np.testing.assert_array_equal(tris, sample_mesh.triangles)
        assert len(mats) == n_t


class TestToSionnaXml:
    def test_produces_valid_xml(self, sample_mesh, tmp_path):
        out = to_sionna_xml(sample_mesh, tmp_path / "scene.xml")
        assert out.exists()
        content = out.read_text()
        assert "<?xml" in content or "<scene" in content


# DiffeRT export test: only run if differt is installed
class TestToDiffertScene:
    @pytest.fixture
    def _has_differt(self):
        pytest.importorskip("differt")

    def test_produces_triangle_scene(self, _has_differt, sample_mesh):
        from aegis.environment.export import to_differt_scene

        scene = to_differt_scene(sample_mesh)
        assert scene.mesh.vertices.shape[1] == 3
        assert scene.mesh.triangles.shape[1] == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_environment_export.py -v`

- [ ] **Step 3: Implement export.py**

```python
# src/aegis/environment/export.py
"""Export EnvironmentMesh to DiffeRT, Sionna XML, and binary wire format."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from aegis.environment import EnvironmentMesh, MaterialType, MATERIAL_EM_PROPERTIES
from aegis.environment.geo import enu_to_yup

# material display colors for DiffeRT scene (RGB 0-1)
_MATERIAL_COLORS: dict[MaterialType, tuple[float, float, float]] = {
    MaterialType.CONCRETE:   (0.7, 0.7, 0.7),
    MaterialType.BRICK:      (0.7, 0.3, 0.2),
    MaterialType.GLASS:      (0.6, 0.8, 0.9),
    MaterialType.METAL:      (0.8, 0.8, 0.85),
    MaterialType.ASPHALT:    (0.3, 0.3, 0.3),
    MaterialType.VEGETATION: (0.3, 0.6, 0.2),
    MaterialType.WATER:      (0.2, 0.4, 0.8),
    MaterialType.WOOD:       (0.6, 0.4, 0.2),
    MaterialType.GROUND:     (0.5, 0.45, 0.35),
    MaterialType.UNKNOWN:    (0.5, 0.5, 0.5),
}


def to_binary(mesh: EnvironmentMesh) -> tuple[bytes, dict]:
    """Serialize EnvironmentMesh for frontend consumption.

    Binary layout (little-endian):
        float32 vertices (N*3) | uint32 triangles (M*3) |
        float32 normals (M*3) | uint8 materials (M)

    Returns (binary_data, metadata_dict).
    """
    # convert ENU to Y-up for frontend
    verts_yup = enu_to_yup(mesh.vertices).astype(np.float32)

    parts = [
        verts_yup.tobytes(),
        mesh.triangles.astype(np.uint32).tobytes(),
        mesh.normals.astype(np.float32).tobytes(),
        mesh.materials.astype(np.uint8).tobytes(),
    ]

    meta = {
        "n_vertices": len(mesh.vertices),
        "n_triangles": len(mesh.triangles),
        "source": mesh.source,
        "origin_lat": mesh.origin_lat,
        "origin_lon": mesh.origin_lon,
        "materials": sorted(set(
            MaterialType(m).name.lower() for m in mesh.materials
        )),
    }
    return b"".join(parts), meta


def to_differt_scene(mesh: EnvironmentMesh):
    """Convert EnvironmentMesh to a DiffeRT TriangleScene.

    ENU coordinates [e, n, u] map directly to DiffeRT Z-up [x, y, z]
    since ENU is already a Z-up frame.
    """
    import jax.numpy as jnp
    from differt.geometry import TriangleMesh
    from differt.scene import TriangleScene

    # per-face colors from material type
    face_colors = np.array(
        [_MATERIAL_COLORS.get(MaterialType(m), (0.5, 0.5, 0.5)) for m in mesh.materials],
        dtype=np.float32,
    )

    # per-face material indices and names
    unique_mats = sorted(set(mesh.materials.tolist()))
    mat_name_map = {m: i for i, m in enumerate(unique_mats)}
    face_materials = np.array(
        [mat_name_map[m] for m in mesh.materials], dtype=np.int32
    )
    material_names = tuple(MaterialType(m).name.lower() for m in unique_mats)

    triangle_mesh = TriangleMesh(
        vertices=jnp.array(mesh.vertices, dtype=jnp.float32),
        triangles=jnp.array(mesh.triangles, dtype=jnp.int32),
        face_colors=jnp.array(face_colors),
        face_materials=jnp.array(face_materials),
        material_names=material_names,
        object_bounds=jnp.array([[0, len(mesh.triangles)]], dtype=jnp.int32),
    )

    return TriangleScene(
        transmitters=jnp.zeros((0, 3)),
        receivers=jnp.zeros((0, 3)),
        mesh=triangle_mesh,
    )


def to_sionna_xml(mesh: EnvironmentMesh, path: Path) -> Path:
    """Write EnvironmentMesh as a Sionna-compatible XML scene file."""
    path = Path(path)

    lines = ['<?xml version="1.0" encoding="utf-8"?>']
    lines.append('<scene version="2.1.0">')

    # materials
    for mat in MaterialType:
        if mat.value not in mesh.materials:
            continue
        props = MATERIAL_EM_PROPERTIES[mat]
        name = mat.name.lower()
        r, g, b = _MATERIAL_COLORS.get(mat, (0.5, 0.5, 0.5))
        lines.append(f'  <bsdf type="diffuse" id="{name}">')
        lines.append(f'    <rgb name="reflectance" value="{r} {g} {b}"/>')
        lines.append(f'  </bsdf>')

    # geometry: one shape per material group
    for mat_val in sorted(set(mesh.materials.tolist())):
        mask = mesh.materials == mat_val
        mat_tris = mesh.triangles[mask]
        mat_name = MaterialType(mat_val).name.lower()

        lines.append(f'  <shape type="ply" id="env_{mat_name}">')
        lines.append(f'    <ref id="{mat_name}" name="bsdf"/>')

        # inline vertex/face data as a simple OBJ-like format
        # Sionna expects PLY files, so we write a PLY to a sibling file
        ply_path = path.parent / f"env_{mat_name}.ply"
        _write_ply(mesh.vertices, mat_tris, ply_path)
        lines.append(f'    <string name="filename" value="{ply_path.name}"/>')
        lines.append(f'  </shape>')

    lines.append('</scene>')

    path.write_text("\n".join(lines))
    return path


def _write_ply(vertices: np.ndarray, triangles: np.ndarray, path: Path):
    """Write a minimal binary PLY file."""
    n_verts = len(vertices)
    n_faces = len(triangles)
    header = (
        "ply\n"
        "format binary_little_endian 1.0\n"
        f"element vertex {n_verts}\n"
        "property float x\n"
        "property float y\n"
        "property float z\n"
        f"element face {n_faces}\n"
        "property list uchar int vertex_indices\n"
        "end_header\n"
    )
    with open(path, "wb") as f:
        f.write(header.encode("ascii"))
        f.write(vertices.astype(np.float32).tobytes())
        for tri in triangles:
            f.write(np.uint8(3).tobytes())
            f.write(tri.astype(np.int32).tobytes())
```

- [ ] **Step 4: Wire up convenience methods on EnvironmentMesh**

Add to `src/aegis/environment/__init__.py`:
```python
    def to_differt_scene(self):
        from aegis.environment.export import to_differt_scene
        return to_differt_scene(self)

    def to_sionna_xml(self, path):
        from aegis.environment.export import to_sionna_xml
        return to_sionna_xml(self, path)

    def to_binary(self) -> tuple[bytes, dict]:
        from aegis.environment.export import to_binary
        return to_binary(self)
```

- [ ] **Step 5: Run tests, lint, commit**

```bash
python -m pytest tests/test_environment_export.py -v
python -m ruff check src/aegis/environment/export.py tests/test_environment_export.py
python -m ruff format src/aegis/environment/export.py tests/test_environment_export.py
git add src/aegis/environment/export.py src/aegis/environment/__init__.py tests/test_environment_export.py
git commit -m "Add export module: DiffeRT, Sionna XML, binary serialization"
```

---

## Task 10: Config integration and `requests` dependency

**Files:**
- Modify: `src/aegis/viewer/config.py` (add `"environment"` key to DEFAULTS)
- Modify: `pyproject.toml` (add `requests` to viewer extra)

- [ ] **Step 1: Add environment config to DEFAULTS**

In `src/aegis/viewer/config.py`, add the `"environment"` key to the `DEFAULTS` dict. Place it after the existing `"location"` key (around line 315). The exact content is specified in the design spec under "Config changes".

- [ ] **Step 2: Add requests to viewer extra**

In `pyproject.toml`, add `"requests>=2.31"` to the `viewer` optional extra list (around line 39).

- [ ] **Step 3: Lint and commit**

```bash
python -m ruff check src/aegis/viewer/config.py
git add src/aegis/viewer/config.py pyproject.toml
git commit -m "Add environment config defaults and requests dependency"
```

---

## Task 11: Backend routes

**Files:**
- Create: `src/aegis/viewer/routes/environment.py`
- Modify: `src/aegis/viewer/server.py` (register the new route module)

Depends on: Task 1 (EnvironmentMesh), Task 7 (osm.py), Task 8 (tiles.py), Task 9 (export.py), Task 10 (config).

- [ ] **Step 1: Implement routes/environment.py**

Follow the exact pattern from `routes/data.py`: a `register(app, cache, cache_lock)` function with nested route closures.

```python
# src/aegis/viewer/routes/environment.py
"""Environment mesh generation and export routes."""

from __future__ import annotations

import json
import os

import numpy as np
from flask import Flask, Response, jsonify, request

from aegis.environment import EnvironmentMesh, MaterialType, MATERIAL_EM_PROPERTIES
from aegis.environment.export import to_binary
from aegis.environment.osm import (
    OverpassRateLimitError,
    OverpassResponseTooLarge,
    OverpassTimeoutError,
    build_environment_from_osm,
    fetch_osm,
)


def register(app: Flask, cache: dict, cache_lock) -> None:
    """Attach environment routes to *app*."""

    @app.route("/api/environment/osm", methods=["POST"])
    def api_environment_osm():
        body = request.get_json(force=True)
        lat = body["lat"]
        lon = body["lon"]
        radius = body.get("radius", 200)
        options = body.get("options", {})

        try:
            xml = fetch_osm(lat, lon, radius)
        except OverpassRateLimitError:
            resp = jsonify({"error": "Overpass API rate limited"})
            resp.status_code = 503
            resp.headers["Retry-After"] = "60"
            return resp
        except OverpassTimeoutError:
            return jsonify({"error": "Overpass API timed out, try smaller radius"}), 504
        except OverpassResponseTooLarge as e:
            return jsonify({"error": str(e)}), 413

        cfg = cache.get("config", {}).get("environment", {}).get("osm", {})
        mesh = build_environment_from_osm(
            xml,
            origin_lat=lat,
            origin_lon=lon,
            default_building_height=options.get(
                "default_building_height", cfg.get("default_building_height", 10)
            ),
            level_height=options.get("level_height", cfg.get("level_height", 3.0)),
            buildings_enabled=options.get("buildings", cfg.get("buildings", True)),
            roads_enabled=options.get("roads", cfg.get("roads", True)),
            water_enabled=options.get("water", cfg.get("water", True)),
        )

        with cache_lock:
            cache["environment_mesh_osm"] = mesh

        data, meta = to_binary(mesh)
        resp = Response(data, mimetype="application/octet-stream")
        resp.headers["X-Meta"] = json.dumps(meta)
        return resp

    @app.route("/api/environment/3dtiles", methods=["POST"])
    def api_environment_3dtiles():
        body = request.get_json(force=True)
        lat = body["lat"]
        lon = body["lon"]
        radius = body.get("radius", 200)
        geometric_error = body.get("geometric_error", 30.0)
        api_key = os.environ.get("GOOGLE_MAPS_API_KEY")

        if not api_key:
            return jsonify({"error": "GOOGLE_MAPS_API_KEY not set"}), 400

        from aegis.environment.tiles import TileTraverser

        traverser = TileTraverser(
            root_url="https://tile.googleapis.com/v1/3dtiles/root.json",
            api_key=api_key,
            geometric_error=geometric_error,
        )
        mesh = traverser.traverse(lat, lon, radius)

        with cache_lock:
            cache["environment_mesh_tiles"] = mesh

        data, meta = to_binary(mesh)
        resp = Response(data, mimetype="application/octet-stream")
        resp.headers["X-Meta"] = json.dumps(meta)
        return resp

    @app.route("/api/environment/from-voxels", methods=["POST"])
    def api_environment_from_voxels():
        positions = cache.get("voxel_positions")
        if positions is None:
            return jsonify({"error": "No voxels loaded"}), 404

        from aegis.environment import EnvironmentMesh

        materials = cache.get("voxel_materials", [])
        voxel_sizes = cache.get("voxel_sizes")
        voxel_size = float(np.median(voxel_sizes)) if voxel_sizes is not None else 1.0

        mesh = EnvironmentMesh.from_voxels(
            positions=positions,
            materials=materials,
            voxel_size=voxel_size,
        )

        with cache_lock:
            cache["environment_mesh_voxels"] = mesh

        data, meta = to_binary(mesh)
        resp = Response(data, mimetype="application/octet-stream")
        resp.headers["X-Meta"] = json.dumps(meta)
        return resp

    @app.route("/api/environment/combine", methods=["POST"])
    def api_environment_combine():
        body = request.get_json(force=True)
        sources = body.get("sources", [])
        source_key_map = {
            "osm": "environment_mesh_osm",
            "3dtiles": "environment_mesh_tiles",
            "voxels": "environment_mesh_voxels",
        }
        meshes = []
        for src in sources:
            key = source_key_map.get(src)
            if key and cache.get(key) is not None:
                meshes.append(cache[key])
        if not meshes:
            return jsonify({"error": "No cached meshes for requested sources"}), 404

        mesh = EnvironmentMesh.combine(*meshes)
        with cache_lock:
            cache["environment_mesh_combined"] = mesh

        data, meta = to_binary(mesh)
        resp = Response(data, mimetype="application/octet-stream")
        resp.headers["X-Meta"] = json.dumps(meta)
        return resp

    @app.route("/api/environment/mesh", methods=["GET"])
    def api_environment_mesh():
        # return the most recently generated mesh from any source
        for key in ("environment_mesh_combined", "environment_mesh_osm",
                     "environment_mesh_tiles", "environment_mesh_voxels"):
            mesh = cache.get(key)
            if mesh is not None:
                data, meta = to_binary(mesh)
                resp = Response(data, mimetype="application/octet-stream")
                resp.headers["X-Meta"] = json.dumps(meta)
                return resp
        return jsonify({"error": "No environment mesh generated"}), 404

    @app.route("/api/environment/export-scene", methods=["POST"])
    def api_environment_export_scene():
        body = request.get_json(force=True)
        fmt = body.get("format", "differt")

        mesh = None
        for key in ("environment_mesh_combined", "environment_mesh_osm",
                     "environment_mesh_tiles", "environment_mesh_voxels"):
            mesh = cache.get(key)
            if mesh is not None:
                break

        if mesh is None:
            return jsonify({"error": "No environment mesh to export"}), 404

        cache_dir = cache.get("cache_dir", "/tmp")

        if fmt == "sionna":
            from aegis.environment.export import to_sionna_xml
            from pathlib import Path

            scene_path = to_sionna_xml(mesh, Path(cache_dir) / "environment_scene.xml")
            with cache_lock:
                cache["environment_scene_path"] = str(scene_path)
            return jsonify({"scene_path": str(scene_path)})

        else:  # differt
            from aegis.environment.export import to_differt_scene

            scene = to_differt_scene(mesh)
            with cache_lock:
                cache["environment_differt_scene"] = scene
                cache["environment_scene_path"] = "__environment__"
            return jsonify({"scene_path": "__environment__"})

    @app.route("/api/environment/materials", methods=["GET"])
    def api_environment_materials():
        catalog = {}
        for mat in MaterialType:
            props = MATERIAL_EM_PROPERTIES[mat]
            catalog[mat.name.lower()] = {
                "value": mat.value,
                "eps_r": props["eps_r"],
                "sigma": props["sigma"],
            }
        return jsonify(catalog)
```

- [ ] **Step 2: Register in server.py**

In `src/aegis/viewer/server.py`, add the import and registration call alongside the existing route modules (around line 452-458):

```python
from aegis.viewer.routes import analysis, compute, data, environment, location, mimo
# ...
environment.register(app, _cache, _cache_lock)
```

- [ ] **Step 3: Lint and commit**

```bash
python -m ruff check src/aegis/viewer/routes/environment.py src/aegis/viewer/server.py
python -m ruff format src/aegis/viewer/routes/environment.py src/aegis/viewer/server.py
git add src/aegis/viewer/routes/environment.py src/aegis/viewer/server.py
git commit -m "Add environment API routes and register in server"
```

---

## Task 12: Frontend environment store

**Files:**
- Create: `aegis-web/src/stores/environment.ts`
- Reference: `aegis-web/src/stores/scene.ts` (Zustand pattern), `aegis-web/src/api/client.ts` (fetch patterns)

- [ ] **Step 1: Implement environment store**

```typescript
// aegis-web/src/stores/environment.ts
import { create } from 'zustand'

export type EnvironmentSource = 'none' | 'voxels' | 'osm' | '3dtiles'

interface OsmOptions {
  defaultBuildingHeight: number
  levelHeight: number
  buildings: boolean
  roads: boolean
  water: boolean
}

interface EnvironmentMeshData {
  positions: Float32Array
  indices: Uint32Array
  normals: Float32Array
  materials: Uint8Array
  meta: Record<string, unknown>
}

interface EnvironmentState {
  source: EnvironmentSource
  location: { lat: number; lon: number } | null
  radius: number
  geometricError: number
  osmMeshData: EnvironmentMeshData | null
  loading: boolean
  error: string | null
  googleApiKey: string
  osmOptions: OsmOptions

  setSource: (s: EnvironmentSource) => void
  setLocation: (lat: number, lon: number) => void
  setRadius: (r: number) => void
  setGeometricError: (ge: number) => void
  setGoogleApiKey: (key: string) => void
  setOsmOptions: (opts: Partial<OsmOptions>) => void
  fetchOSM: () => Promise<void>
  fetchTilesForRT: () => Promise<void>
  exportForRT: (format: 'differt' | 'sionna') => Promise<string>
}

export const useEnvironmentStore = create<EnvironmentState>((set, get) => ({
  source: 'none',
  location: null,
  radius: 200,
  geometricError: 30,
  osmMeshData: null,
  loading: false,
  error: null,
  googleApiKey: '',
  osmOptions: {
    defaultBuildingHeight: 10,
    levelHeight: 3.0,
    buildings: true,
    roads: true,
    water: true,
  },

  setSource: (source) => set({ source }),
  setLocation: (lat, lon) => set({ location: { lat, lon } }),
  setRadius: (radius) => set({ radius }),
  setGeometricError: (geometricError) => set({ geometricError }),
  setGoogleApiKey: (googleApiKey) => set({ googleApiKey }),
  setOsmOptions: (opts) => set((s) => ({
    osmOptions: { ...s.osmOptions, ...opts },
  })),

  fetchOSM: async () => {
    const { location, radius, osmOptions } = get()
    if (!location) return
    set({ loading: true, error: null })
    try {
      const resp = await fetch('/api/environment/osm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lat: location.lat,
          lon: location.lon,
          radius,
          options: {
            default_building_height: osmOptions.defaultBuildingHeight,
            level_height: osmOptions.levelHeight,
            buildings: osmOptions.buildings,
            roads: osmOptions.roads,
            water: osmOptions.water,
          },
        }),
      })
      if (!resp.ok) {
        const err = await resp.json()
        throw new Error(err.error || `HTTP ${resp.status}`)
      }
      const meta = JSON.parse(resp.headers.get('X-Meta') || '{}')
      const buf = await resp.arrayBuffer()
      const meshData = parseEnvironmentBinary(buf, meta)
      set({ osmMeshData: meshData, loading: false })
    } catch (e) {
      set({ error: (e as Error).message, loading: false })
    }
  },

  fetchTilesForRT: async () => {
    const { location, radius, geometricError } = get()
    if (!location) return
    set({ loading: true, error: null })
    try {
      const resp = await fetch('/api/environment/3dtiles', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lat: location.lat,
          lon: location.lon,
          radius,
          geometric_error: geometricError,
        }),
      })
      if (!resp.ok) {
        const err = await resp.json()
        throw new Error(err.error || `HTTP ${resp.status}`)
      }
      set({ loading: false })
    } catch (e) {
      set({ error: (e as Error).message, loading: false })
    }
  },

  exportForRT: async (format) => {
    const resp = await fetch('/api/environment/export-scene', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ format }),
    })
    if (!resp.ok) {
      const err = await resp.json()
      throw new Error(err.error || `HTTP ${resp.status}`)
    }
    const data = await resp.json()
    return data.scene_path
  },
}))

function parseEnvironmentBinary(
  buf: ArrayBuffer,
  meta: Record<string, unknown>,
): EnvironmentMeshData {
  const nV = meta.n_vertices as number
  const nT = meta.n_triangles as number
  let offset = 0

  const positions = new Float32Array(buf, offset, nV * 3)
  offset += nV * 3 * 4

  const indices = new Uint32Array(buf, offset, nT * 3)
  offset += nT * 3 * 4

  const normals = new Float32Array(buf, offset, nT * 3)
  offset += nT * 3 * 4

  const materials = new Uint8Array(buf, offset, nT)

  return { positions, indices, normals, materials, meta }
}
```

- [ ] **Step 2: Commit**

```bash
git add aegis-web/src/stores/environment.ts
git commit -m "Add frontend environment Zustand store"
```

---

## Task 13: EnvironmentOSM component

**Files:**
- Create: `aegis-web/src/components/scene/EnvironmentOSM.tsx`

Depends on: Task 12 (environment store).

- [ ] **Step 1: Implement EnvironmentOSM.tsx**

```tsx
// aegis-web/src/components/scene/EnvironmentOSM.tsx
import { useMemo } from 'react'
import * as THREE from 'three'
import { useEnvironmentStore } from '@/stores/environment'
// material type index -> display color (RGB 0-1)
const MATERIAL_COLORS: Record<number, [number, number, number]> = {
  0: [0.7, 0.7, 0.7],    // concrete
  1: [0.7, 0.3, 0.2],    // brick
  2: [0.6, 0.8, 0.9],    // glass
  3: [0.8, 0.8, 0.85],   // metal
  4: [0.3, 0.3, 0.3],    // asphalt
  5: [0.3, 0.6, 0.2],    // vegetation
  6: [0.2, 0.4, 0.8],    // water
  7: [0.6, 0.4, 0.2],    // wood
  8: [0.5, 0.45, 0.35],  // ground
  9: [0.5, 0.5, 0.5],    // unknown
}

export function EnvironmentOSM() {
  const meshData = useEnvironmentStore((s) => s.osmMeshData)

  const geometry = useMemo(() => {
    if (!meshData) return null

    // de-index geometry to avoid shared-vertex color conflicts across materials
    const nTris = meshData.indices.length / 3
    const positions = new Float32Array(nTris * 9)
    const colors = new Float32Array(nTris * 9)

    for (let t = 0; t < nTris; t++) {
      const mat = meshData.materials[t]
      const color = MATERIAL_COLORS[mat] || MATERIAL_COLORS[9]
      for (let v = 0; v < 3; v++) {
        const srcIdx = meshData.indices[t * 3 + v]
        const dstIdx = t * 9 + v * 3
        positions[dstIdx] = meshData.positions[srcIdx * 3]
        positions[dstIdx + 1] = meshData.positions[srcIdx * 3 + 1]
        positions[dstIdx + 2] = meshData.positions[srcIdx * 3 + 2]
        colors[dstIdx] = color[0]
        colors[dstIdx + 1] = color[1]
        colors[dstIdx + 2] = color[2]
      }
    }

    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3))
    geo.computeVertexNormals()

    return geo
  }, [meshData])

  if (!geometry) return null

  return (
    <mesh geometry={geometry} receiveShadow castShadow>
      <meshStandardMaterial vertexColors side={THREE.DoubleSide} />
    </mesh>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add aegis-web/src/components/scene/EnvironmentOSM.tsx
git commit -m "Add EnvironmentOSM scene component"
```

---

## Task 14: Environment3DTiles component

**Files:**
- Create: `aegis-web/src/components/scene/Environment3DTiles.tsx`
- Create: `aegis-web/public/google-maps-logo.png` (download from Google)
- Modify: `aegis-web/package.json` (add `3d-tiles-renderer` dependency)

- [ ] **Step 1: Install 3d-tiles-renderer**

```bash
cd aegis-web && npm install 3d-tiles-renderer
```

- [ ] **Step 2: Download Google Maps logo**

Download the outlined Google Maps logo from Google's Map Tiles API policies page and save to `aegis-web/public/google-maps-logo.png`. This is required for ToS compliance.

- [ ] **Step 3: Implement Environment3DTiles.tsx**

```tsx
// aegis-web/src/components/scene/Environment3DTiles.tsx
import { useMemo, type ReactNode } from 'react'
import {
  TilesRenderer,
  TilesPlugin,
  EastNorthUpFrame,
  TilesAttributionOverlay,
  GlobeControls,
} from '3d-tiles-renderer/r3f'
import { GoogleCloudAuthPlugin } from '3d-tiles-renderer/plugins'
import { useEnvironmentStore } from '@/stores/environment'
import { useUIStore } from '@/stores/ui'

interface Props {
  children: ReactNode
}

export function Environment3DTiles({ children }: Props) {
  const location = useEnvironmentStore((s) => s.location)
  const apiKey = useEnvironmentStore((s) => s.googleApiKey)
  const cameraMode = useUIStore((s) => s.cameraMode)

  const pluginArgs = useMemo(
    () => ({
      apiToken: apiKey,
      logoUrl: '/google-maps-logo.png',
    }),
    [apiKey],
  )

  if (!location || !apiKey) return <>{children}</>

  return (
    <TilesRenderer>
      <TilesPlugin plugin={GoogleCloudAuthPlugin} args={pluginArgs} />
      <TilesAttributionOverlay
        style={{ position: 'absolute', right: 10, bottom: 10, left: 'auto' }}
      />
      {cameraMode === 'globe' && <GlobeControls />}
      <EastNorthUpFrame
        lat={location.lat * Math.PI / 180}
        lon={location.lon * Math.PI / 180}
      >
        {children}
      </EastNorthUpFrame>
    </TilesRenderer>
  )
}
```

- [ ] **Step 4: Commit**

```bash
git add aegis-web/src/components/scene/Environment3DTiles.tsx aegis-web/public/google-maps-logo.png aegis-web/package.json aegis-web/package-lock.json
git commit -m "Add 3DTilesRendererJS integration with Google auth and attribution"
```

---

## Task 15: Globe camera mode and SceneRoot integration

**Files:**
- Modify: `aegis-web/src/stores/ui.ts` (add `'globe'` to CameraMode)
- Modify: `aegis-web/src/components/scene/SceneRoot.tsx` (conditional environment rendering + globe controls)
- Modify: `aegis-web/src/components/layout/Toolbar.tsx` (globe toggle button)

- [ ] **Step 1: Update CameraMode type in ui.ts**

Change line 4 in `aegis-web/src/stores/ui.ts`:
```typescript
export type CameraMode = 'orbit' | 'follow' | 'globe'
```

No other changes needed. The `setCameraMode` action already accepts `CameraMode`.

- [ ] **Step 2: Add globe button to Toolbar.tsx**

Import `Globe` from `lucide-react`. Add a globe toggle button after the existing follow-mode toggle in the camera preset row. On click: `setCameraMode(cameraMode === 'globe' ? 'orbit' : 'globe')`. Active state uses the same `bg-primary/15 text-primary` styling. When any camera preset button is clicked, reset to `setCameraMode('orbit')` first.

- [ ] **Step 3: Update SceneRoot.tsx**

Import `Environment3DTiles`, `EnvironmentOSM`, `useEnvironmentStore`.

Conditional rendering logic:
```tsx
const envSource = useEnvironmentStore((s) => s.source)
const cameraMode = useUIStore((s) => s.cameraMode)

// environment layer
{envSource === 'voxels' && (
  <>
    <VoxelField />
    <Environment />
  </>
)}
{envSource === 'osm' && <EnvironmentOSM />}

// 3dtiles wraps the entire scene
// for non-3dtiles, render scene directly
```

For 3D Tiles mode, the `<Environment3DTiles>` component wraps the scene children to provide the `TilesRenderer` context and `EastNorthUpFrame`.

Camera controls:
```tsx
{cameraMode === 'orbit' && <OrbitControls ... />}
{/* GlobeControls rendered inside Environment3DTiles when cameraMode === 'globe' */}
{/* FollowCamera already checks cameraMode === 'follow' internally */}
```

When `envSource === 'none'`, render `<VoxelField />` and `<Environment />` as before (backwards-compatible default).

- [ ] **Step 4: Lint and commit**

```bash
cd aegis-web && npx tsc --noEmit
git add aegis-web/src/stores/ui.ts aegis-web/src/components/scene/SceneRoot.tsx aegis-web/src/components/layout/Toolbar.tsx
git commit -m "Add globe camera mode and environment source switching in SceneRoot"
```

---

## Task 16: EnvironmentPanel and Sidebar integration

**Files:**
- Create: `aegis-web/src/components/panels/EnvironmentPanel.tsx`
- Modify: `aegis-web/src/components/layout/Sidebar.tsx` (add accordion section)

Depends on: Task 12 (environment store).

- [ ] **Step 1: Implement EnvironmentPanel.tsx**

Panel sections:
1. **Source selector**: radio group (None / Voxels / OpenStreetMap / Google 3D Tiles) mapped to `useEnvironmentStore.setSource()`
2. **Location**: lat/lon number inputs with step 0.001 + text geocoding input (fetch from Nominatim on enter)
3. **Radius**: slider 50-500, step 10
4. **OSM options** (shown when source='osm'): default building height input, level height input, buildings/roads/water toggles
5. **3D Tiles options** (shown when source='3dtiles'): LOD preset dropdown (preview/medium/high/ultra), geometric error slider 1-200, API key password input
6. **Fetch/Generate button**: calls `fetchOSM()` or `fetchTilesForRT()` depending on source. Shows loading spinner.
7. **"Export for Ray Tracing" button**: calls `exportForRT('differt')`, shows scene path on success
8. **Error display**: shows `error` from store

Use the same styling patterns as existing panels (`ParametersPanel.tsx`, `ScenePanel.tsx`): Tailwind classes, `text-sm`, `text-muted-foreground` labels, inline inputs.

- [ ] **Step 2: Add to Sidebar.tsx**

Add an `<AccordionItem value="environment">` section in `Sidebar.tsx`. Place it before the existing `"scene"` section. Follow the exact accordion pattern:

```tsx
<AccordionItem value="environment" className="border-b border-border px-3">
  <AccordionTrigger className="text-sm font-medium py-3">Environment</AccordionTrigger>
  <AccordionContent>
    <div className="py-2">
      <EnvironmentPanel />
    </div>
  </AccordionContent>
</AccordionItem>
```

- [ ] **Step 3: Lint and commit**

```bash
cd aegis-web && npx tsc --noEmit
git add aegis-web/src/components/panels/EnvironmentPanel.tsx aegis-web/src/components/layout/Sidebar.tsx
git commit -m "Add EnvironmentPanel sidebar with source selector and options"
```

---

## Task 17: Config hydration

**Files:**
- Modify: `aegis-web/src/hooks/useConfig.ts` (hydrate environment store from config)

- [ ] **Step 1: Add environment store hydration**

In `useConfig.ts`, after the existing store hydration calls (around line 50-60), add:

```typescript
import { useEnvironmentStore } from '@/stores/environment'

// inside the useEffect, after other store hydrations:
if (viewerConfig.environment) {
  const env = viewerConfig.environment
  useEnvironmentStore.setState({
    source: env.source || 'none',
    location: env.location || null,
    radius: env.radius || 200,
    geometricError: env.tiles?.geometric_error || 30,
    osmOptions: {
      defaultBuildingHeight: env.osm?.default_building_height || 10,
      levelHeight: env.osm?.level_height || 3.0,
      buildings: env.osm?.buildings ?? true,
      roads: env.osm?.roads ?? true,
      water: env.osm?.water ?? true,
    },
  })
}
```

- [ ] **Step 2: Lint and commit**

```bash
cd aegis-web && npx tsc --noEmit
git add aegis-web/src/hooks/useConfig.ts
git commit -m "Hydrate environment store from viewer config on load"
```

---

## Task 18: EnvironmentMesh.from_voxels and from_osm/from_3dtiles class methods

**Files:**
- Modify: `src/aegis/environment/__init__.py` (add factory classmethods)
- Modify: `tests/test_environment_mesh.py` (add factory tests)

Wire up the convenience factory classmethods on EnvironmentMesh that delegate to `osm.py`, `tiles.py`, and the voxel conversion.

- [ ] **Step 1: Add from_voxels implementation**

```python
@classmethod
def from_voxels(cls, positions, materials, voxel_size):
    """Convert voxel data to EnvironmentMesh by generating cube faces."""
    from aegis.environment.osm import _compute_face_normals

    # Generate 12 triangles (6 faces, 2 tris each) per voxel
    n = len(positions)
    half = voxel_size / 2
    # cube template: 8 corners
    offsets = np.array([
        [-1,-1,-1],[-1,-1,1],[-1,1,-1],[-1,1,1],
        [1,-1,-1],[1,-1,1],[1,1,-1],[1,1,1],
    ], dtype=np.float64) * half
    # 12 triangles from 6 faces
    cube_tris = np.array([
        [0,2,6],[0,6,4],[1,5,7],[1,7,3],  # -x, +x
        [0,1,3],[0,3,2],[4,6,7],[4,7,5],  # -y, +y
        [0,4,5],[0,5,1],[2,3,7],[2,7,6],  # -z, +z
    ], dtype=np.uint32)

    all_verts = np.repeat(positions, 8, axis=0).reshape(n, 8, 3) + offsets
    all_verts = all_verts.reshape(-1, 3)
    all_tris = np.tile(cube_tris, (n, 1, 1))
    for i in range(n):
        all_tris[i] += i * 8
    all_tris = all_tris.reshape(-1, 3)

    # material per face: 12 tris per voxel
    mat_array = np.repeat(
        np.array(materials, dtype=np.uint8), 12
    ) if len(materials) == n else np.full(n * 12, MaterialType.CONCRETE, dtype=np.uint8)

    normals = _compute_face_normals(all_verts, all_tris)

    return cls(
        vertices=all_verts,
        triangles=all_tris,
        normals=normals,
        materials=mat_array,
        origin_lat=0.0,
        origin_lon=0.0,
        source="voxels",
    )
```

- [ ] **Step 2: Add from_osm and from_3dtiles as thin wrappers**

```python
@classmethod
def from_osm(cls, lat, lon, radius_m, **kwargs):
    from aegis.environment.osm import fetch_osm, build_environment_from_osm
    xml = fetch_osm(lat, lon, radius_m)
    return build_environment_from_osm(xml, origin_lat=lat, origin_lon=lon, **kwargs)

@classmethod
def from_3dtiles(cls, lat, lon, radius_m, geometric_error=30., api_key=None):
    from aegis.environment.tiles import TileTraverser
    import os
    key = api_key or os.environ.get("GOOGLE_MAPS_API_KEY")
    traverser = TileTraverser(
        root_url="https://tile.googleapis.com/v1/3dtiles/root.json",
        api_key=key,
        geometric_error=geometric_error,
    )
    return traverser.traverse(lat, lon, radius_m)
```

- [ ] **Step 3: Add tests, lint, commit**

```bash
python -m pytest tests/test_environment_mesh.py -v
python -m ruff check src/aegis/environment/__init__.py
git add src/aegis/environment/__init__.py tests/test_environment_mesh.py
git commit -m "Wire up EnvironmentMesh factory classmethods"
```

---

## Task 19: Final integration test and PR

- [ ] **Step 1: Run full test suite**

```bash
python -m ruff check src/aegis/environment/ tests/test_environment_*.py
python -m ruff format --check src/aegis/environment/ tests/test_environment_*.py
python -m pytest tests/test_environment_*.py -v
```

- [ ] **Step 2: Run frontend type check and build**

```bash
cd aegis-web && npx tsc --noEmit && npm run build
```

- [ ] **Step 3: Run existing tests to verify no regressions**

```bash
python -m pytest tests/ -m "not slow" -x
```

- [ ] **Step 4: Create PR**

```bash
git push -u origin wt/blosm
gh pr create --title "Add environment module: OSM + 3D Tiles integration" \
  --body "$(cat <<'EOF'
## Summary
- New `src/aegis/environment/` package with EnvironmentMesh dataclass
- OSM pipeline: Overpass API fetch, 12+ roof types, roads, water
- 3D Tiles server-side mesh extraction for ray tracing
- Frontend 3DTilesRendererJS streaming visualization
- Globe camera mode (GlobeControls toggle in toolbar)
- EnvironmentPanel sidebar with source/location/options controls
- ITU-R P.2040 material mapping for EM properties
- All legacy code (voxels, GLB tiles, Sionna scenes) untouched

## Test plan
- [ ] `pytest tests/test_environment_*.py -v` passes
- [ ] `cd aegis-web && npx tsc --noEmit && npm run build` passes
- [ ] `pytest tests/ -m "not slow" -x` passes (no regressions)
- [ ] Manual: load OSM for a known location, verify buildings render
- [ ] Manual: toggle globe mode, verify zoom-out works
- [ ] Manual: existing voxel/scene workflows still function
EOF
)" --base master
```
