# HPC study: deterministic single-city exposure spine (Plan 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a headless `aegis.study` module that walks a small synchronized crowd through one real city core, illuminates them with a sectored mmWave deployment, computes each person's coherent absorbed-power exposure by ray tracing, and writes a population exposure CDF.

**Architecture:** A new config-driven module under `src/aegis/study/`, no Flask. The deterministic arm only. It composes production AEGIS physics (OSM mesh, DiffeRT ray tracer, coherent Sab kernel, UPA array, MRT precoder, the coherent Q translation phasor) into a per-agent serial time loop with three independent cadence knobs (`dt`, `pose_period`, `recompute_period`). Parallelism is over agents via a scheduler job array; this plan builds the single-process kernel. The three precursor repos (`plaza_run`, `pedestrian_flow_ABM`, `hybrid-QuaDRiGa-FDTD`) are inspiration only, not imported and not copied.

**Tech Stack:** Python 3.12, NumPy/SciPy, JAX (engine + coherent kernel), DiffeRT (`aegis[rt]`), SMPL-X via `smplx`/`torch` (`aegis[body]`), Google Directions API for routing, GHSL raster for population sampling, PyYAML for config, matplotlib/scienceplots for the CDF.

**Design spec:** `docs/superpowers/specs/2026-05-31-hpc-city-exposure-study-design.md`. Read it before starting.

---

## Plan series (this plan is #1 of 5)

The design spec's build order decomposes into five plans. Each produces working, testable software on its own. This document is Plan 1. The others are written after Plan 1 lands so they can build on its real interfaces.

1. **Deterministic single-city spine (this plan).** Scaffold + cost-discovery spike + a deterministic-only, coherent, fixed-MRT-beam run on one small Ghent core that writes a per-person exposure CDF. Covers build-order steps 1 and 2, plus a simple v1 deployment good enough to run (a fuller generator is Plan 3).
2. **Coherent 38.901 stochastic channel.** The native coherent cluster channel (`generate_coherent_channel`: steering phases + XPR) and `P_LOS(d)`, validated against a reference on a fixed link. Build-order step 3.
3. **Stochastic arm + deployment generator + K-marginalization.** Wire the stochastic channel into the loop with the `P_LOS`-weighted blend, add the paired det-vs-stoch comparison, replace the v1 deployment with the Ginibre generator and K realizations. Build-order steps 4 and 5.
4. **Multi-city orchestration + covariate analysis.** Build-order step 6.
5. **Internal R3F HPC tab.** Build-order step 7.

Do not implement anything from Plans 2-5 in this plan. The hard gate for those is a working Plan 1.

---

## Decisions deferred to the implementer (flag, do not invent)

These are real design points the spec leaves open. Each has a dedicated task that makes the decision explicit, picks a documented default, and tests it. Do not silently paper over them.

- **Per-element user channel `h` for MRT.** `Precoder.mrt(h, P)` needs an `(M_ant,)` complex channel vector at the served user. The ray tracer gives per-element *paths*, not a single vector. Task 12 defines the reduction (sum each element's paths, project polarization) and tests it. Confirm against how `JSAC/code/experiments/plaza_run/phy.py` builds its channel matrix `H` before finalizing.
- **OSM building candidates and the local frame.** Walks, buildings, and the mesh must share one ENU origin. Task 2 reuses AEGIS's existing lat/lon-to-local conversion (the one `parse_osm_xml` uses) rather than rolling a new one. If no shared helper exists, the task implements equirectangular projection and verifies it reproduces a known building's coordinates.
- **ICNIRP reference level.** The headline metric is exposure as a fraction of the ICNIRP limit. Task 16 pulls the limit from `src/aegis/compliance/` rather than hardcoding `plaza_run`'s `reference_level_vpm`.

---

## File structure

All new code under `src/aegis/study/`. Tests under `tests/study/`.

- `src/aegis/study/__init__.py` - public exports.
- `src/aegis/study/config.py` - `StudyConfig` dataclasses + YAML loader. Mirrors the spec's config block.
- `src/aegis/study/geo.py` - lat/lon to local ENU projection, sharing the mesh origin.
- `src/aegis/study/city.py` - city mesh build/cache, Sionna XML export, building rooftop candidates.
- `src/aegis/study/mobility.py` - GHSL population sampling, Google Directions routing, polyline decode, route cache.
- `src/aegis/study/walk.py` - route to time-sampled trajectory at `dt`, with heading.
- `src/aegis/study/bodies.py` - SMPL-X walking body along a trajectory; static-phantom fallback.
- `src/aegis/study/deployment.py` - v1 site set (simple repulsive thinning), equipment, sectoring, site/sector dataclasses, user-to-sector assignment.
- `src/aegis/study/channel_det.py` - deterministic arm: per-sector ray-traced per-element paths.
- `src/aegis/study/precoding.py` - user channel vector `h`, MRT precoder per sector.
- `src/aegis/study/exposure.py` - coherent dosimetry: static path Gram, per-slot `q_translate` scalar exposure, per-triangle Sab map at recompute cadence, power-sum across sectors.
- `src/aegis/study/loop.py` - per-agent serial time loop tying the cadences together.
- `src/aegis/study/reduce.py` - per-person summary, population CDF, ICNIRP fraction.
- `src/aegis/study/run.py` - headless entry: one config to one run, job-array friendly (`--agent-start`/`--agent-count`).
- `src/aegis/study/spike.py` - cost-discovery timing harness (build-order step 1).
- `tests/study/test_*.py` - one test module per source module.
- `configs/study/ghent_core_v1.yaml` - the v1 config.

---

## Task 0: Module scaffold and config

**Files:**
- Create: `src/aegis/study/__init__.py`
- Create: `src/aegis/study/config.py`
- Create: `configs/study/ghent_core_v1.yaml`
- Test: `tests/study/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/study/test_config.py
from pathlib import Path

from aegis.study.config import StudyConfig


def test_loads_v1_yaml(tmp_path):
    yaml_text = (Path(__file__).parents[2] / "configs/study/ghent_core_v1.yaml").read_text()
    cfg_file = tmp_path / "c.yaml"
    cfg_file.write_text(yaml_text)

    cfg = StudyConfig.from_yaml(cfg_file)

    assert cfg.cities.count == 1
    assert cfg.cities.radius_m == 200.0
    assert cfg.mobility.n_agents == 50
    assert cfg.mobility.walk_speed_mps == 1.4
    assert cfg.deployment.sectoring.sectors == 3
    assert cfg.deployment.sectoring.az_coverage_deg == 120.0
    assert cfg.deployment.equipment.array == (8, 8)
    assert cfg.deployment.equipment.freq_hz == 28.0e9
    assert cfg.dosimetry.level == 7
    assert cfg.channel.seed == 42


def test_defaults_round_trip():
    cfg = StudyConfig()  # all defaults from the spec
    assert cfg.deployment.realizations_K == 1
    assert cfg.deployment.precoder == "mrt"
    assert cfg.temporal.dt_s is None  # TBD until the spike sets it
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/study/test_config.py -v -n 0`
Expected: FAIL with `ModuleNotFoundError: No module named 'aegis.study'`.

- [ ] **Step 3: Write `config.py`**

Frozen dataclasses mirroring the spec config block, with a `from_yaml` classmethod. Use only stdlib + PyYAML (`pyyaml>=6.0.3` is a direct core dependency in `pyproject.toml`, so `import yaml` always works). `temporal` cadences default to `None` (TBD until the spike). `array` parsed to a tuple.

```python
# src/aegis/study/config.py
from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import get_type_hints

import yaml


@dataclass(frozen=True)
class CitiesConfig:
    count: int = 1
    radius_m: float = 200.0


@dataclass(frozen=True)
class MobilityConfig:
    n_agents: int = 50
    window_s: float = 60.0
    walk_speed_mps: float = 1.4
    user_fraction: float = 0.5


@dataclass(frozen=True)
class SectoringConfig:
    sectors: int = 3
    az_coverage_deg: float = 120.0
    max_range_m: float = 150.0


@dataclass(frozen=True)
class EquipmentConfig:
    name: str = "mmwave_mamimo_28ghz"
    array: tuple[int, int] = (8, 8)
    tx_power_dbm: float = 30.0
    height_class: str = "rooftop"
    freq_hz: float = 28.0e9


@dataclass(frozen=True)
class DeploymentConfig:
    process: str = "ginibre"
    density_source: str = "dataset"
    densification: float = 1.0
    realizations_K: int = 1
    sectoring: SectoringConfig = field(default_factory=SectoringConfig)
    equipment: EquipmentConfig = field(default_factory=EquipmentConfig)
    precoder: str = "mrt"


@dataclass(frozen=True)
class ChannelConfig:
    stochastic: str = "coherent_38901"
    los_blend: str = "p_los"
    seed: int = 42


@dataclass(frozen=True)
class DosimetryConfig:
    level: int = 7


@dataclass(frozen=True)
class TemporalConfig:
    dt_s: float | None = None
    pose_period: int | None = None
    recompute_period: int | None = None


@dataclass(frozen=True)
class StudyConfig:
    cities: CitiesConfig = field(default_factory=CitiesConfig)
    mobility: MobilityConfig = field(default_factory=MobilityConfig)
    deployment: DeploymentConfig = field(default_factory=DeploymentConfig)
    channel: ChannelConfig = field(default_factory=ChannelConfig)
    dosimetry: DosimetryConfig = field(default_factory=DosimetryConfig)
    temporal: TemporalConfig = field(default_factory=TemporalConfig)

    @classmethod
    def from_yaml(cls, path: str | Path) -> StudyConfig:
        raw = yaml.safe_load(Path(path).read_text()) or {}
        return _build(cls, raw)


def _build(cls, raw: dict):
    if not is_dataclass(cls):
        return raw
    # `from __future__ import annotations` stringizes f.type, so resolve the
    # real classes via get_type_hints before checking is_dataclass.
    hints = get_type_hints(cls)
    kwargs = {}
    for f in fields(cls):
        if f.name not in raw:
            continue
        val = raw[f.name]
        ftype = hints[f.name]
        if is_dataclass(ftype):
            kwargs[f.name] = _build(ftype, val)
        elif f.name == "array" and isinstance(val, list):
            kwargs[f.name] = tuple(val)
        else:
            kwargs[f.name] = val
    return cls(**kwargs)
```

- [ ] **Step 4: Write `configs/study/ghent_core_v1.yaml`**

Copy the spec config block verbatim (the YAML in the spec's "Configuration and defaults" section). Keep the `TBD` cadences as null.

- [ ] **Step 5: Write `__init__.py`** exporting `StudyConfig`.

- [ ] **Step 6: Run to verify pass**

Run: `python -m pytest tests/study/test_config.py -v -n 0`
Expected: PASS.

- [ ] **Step 7: Lint and commit**

```bash
python -m ruff check src/aegis/study tests/study
python -m ruff format src/aegis/study tests/study
git add src/aegis/study/__init__.py src/aegis/study/config.py configs/study/ghent_core_v1.yaml tests/study/test_config.py
git commit -m "Add aegis.study scaffold and config"
```

---

## Task 1: Branch setup

**Files:** none (git only).

- [ ] **Step 1: Create the feature branch**

This is a multi-file new module, so it uses the PR workflow per `.claude/rules/git-workflow.md`.

```bash
git checkout -b feature/hpc-study-deterministic-spine
```

All subsequent task commits land on this branch. The branch is opened as a PR and squash-merged at the end of the plan.

---

## Task 2: Local ENU projection (geo)

**Files:**
- Create: `src/aegis/study/geo.py`
- Test: `tests/study/test_geo.py`

The mesh, the buildings, and the walks must share one origin. The mesh frame uses **Transverse Mercator** (not equirectangular). AEGIS already exposes the exact pair `parse_osm_xml` uses, so this task re-exports them rather than rolling a new projection.

- [ ] **Step 1: Re-export the shared projection**

`src/aegis/environment/geo.py` exposes `transverse_mercator_forward(lat, lon, origin_lat, origin_lon) -> (x, y)` and `transverse_mercator_inverse(x, y, origin_lat, origin_lon) -> (lat, lon)`, which `parse_osm_xml` uses via `_project_nodes`. These match the intended `latlon_to_enu`/`enu_to_latlon` API directly. Re-export them so the study frame is identical to the mesh frame:

```python
# src/aegis/study/geo.py
from aegis.environment.geo import (
    transverse_mercator_forward as latlon_to_enu,
    transverse_mercator_inverse as enu_to_latlon,
)

__all__ = ["latlon_to_enu", "enu_to_latlon"]
```

Do not implement a new equirectangular projection. (Equirectangular agrees with TM to sub-cm at 200 m, but using it would silently diverge from the mesh frame, defeating the point of this task.)

- [ ] **Step 2: Write the test**

```python
# tests/study/test_geo.py
import numpy as np

from aegis.study.geo import latlon_to_enu, enu_to_latlon


def test_round_trip():
    lat0, lon0 = 51.0536, 3.7253  # Ghent
    lat, lon = 51.0550, 3.7280
    x, y = latlon_to_enu(lat, lon, lat0, lon0)
    lat2, lon2 = enu_to_latlon(x, y, lat0, lon0)
    assert abs(lat2 - lat) < 1e-7
    assert abs(lon2 - lon) < 1e-7


def test_origin_maps_to_zero():
    x, y = latlon_to_enu(51.0536, 3.7253, 51.0536, 3.7253)
    assert abs(x) < 1e-6 and abs(y) < 1e-6


def test_east_is_positive_x():
    x, _ = latlon_to_enu(51.0536, 3.7300, 51.0536, 3.7253)
    assert x > 0
```

- [ ] **Step 3: Add a frame-match assertion**

Beyond the round-trip, add a test that the re-exported projection reproduces a known building vertex from `parse_osm_xml` for a fixed OSM fixture (same origin in, same XY out), proving the study frame is byte-identical to the mesh frame. The implementation is just the Step 1 re-export; there is no projection math to write.

- [ ] **Step 4: Run, lint, commit**

```bash
python -m pytest tests/study/test_geo.py -v -n 0
python -m ruff check src/aegis/study/geo.py tests/study/test_geo.py
git add src/aegis/study/geo.py tests/study/test_geo.py
git commit -m "Add local ENU projection for study frame"
```

---

## Task 3: City mesh + rooftop candidates (city)

**Files:**
- Create: `src/aegis/study/city.py`
- Test: `tests/study/test_city.py`

Wraps `EnvironmentMesh.from_osm`, caches the mesh and the Sionna XML, and extracts rooftop candidate points (centroid raised to roof height) from the parsed buildings. Marked `@slow` where it touches the network or mesh data.

- [ ] **Step 1: Confirm the building access path**

`EnvironmentMesh.from_osm(lat, lon, radius_m)` builds the mesh but does not expose `Building` objects. `parse_osm_xml(xml_str, origin_lat, origin_lon)` returns `(list[Building], list[Road], list[WaterBody])` but needs the raw OSM XML. Find how `from_osm` fetches that XML (`grep -n "overpass\|requests.get\|fetch" src/aegis/environment/*.py`). Reuse the same fetch so the mesh and the candidates come from one download. Expose a small helper `_fetch_osm_xml(lat, lon, radius_m) -> str` if one is not already public.

- [ ] **Step 2: Write the test (fast part only)**

```python
# tests/study/test_city.py
import numpy as np

from aegis.study.city import rooftop_candidates
from aegis.environment.osm_helpers import Building


def test_rooftop_candidate_is_centroid_at_eave_height():
    footprint = np.array([[0, 0], [10, 0], [10, 10], [0, 10]], dtype=float)
    b = Building(way_id=1, footprint=footprint, height=20.0, roof_height=3.0)
    pts = rooftop_candidates([b])
    assert pts.shape == (1, 3)
    np.testing.assert_allclose(pts[0, :2], [5.0, 5.0])
    # Site sits at the parapet (eave height = b.height). roof_height is the
    # roof's own peak extent above the eave and is deliberately excluded:
    # rooftop antennas mount at the parapet, not the roof peak.
    assert pts[0, 2] == 20.0


def test_skips_degenerate_footprints():
    b = Building(way_id=2, footprint=np.zeros((2, 2)), height=10.0)
    assert rooftop_candidates([b]).shape == (0, 3)
```

Height convention (confirmed against `osm_helpers.Building`): `height` is the eave/parapet height, `roof_height` is the roof peak's extra extent above it. The site z is the eave height (`b.height`), the parapet where antennas mount, so `roof_height` is intentionally excluded.

- [ ] **Step 3: Implement `rooftop_candidates` and `CityCache`**

```python
# src/aegis/study/city.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from aegis.environment import EnvironmentMesh


def rooftop_candidates(buildings) -> np.ndarray:
    """(K, 3) candidate site points: footprint centroid at building top."""
    pts = []
    for b in buildings:
        fp = np.asarray(b.footprint, dtype=float)
        if fp.shape[0] < 3:
            continue
        centroid = fp.mean(axis=0)
        # b.height is eave/parapet height (OSM `height` tag or levels*3).
        # b.roof_height is the roof peak's extra extent on top; excluded here
        # because the antenna mounts at the parapet.
        z = float(b.height)
        pts.append([centroid[0], centroid[1], z])
    if not pts:
        return np.zeros((0, 3))
    return np.asarray(pts)


@dataclass
class CityCache:
    mesh: EnvironmentMesh
    scene_xml: Path
    candidates: np.ndarray
    origin_lat: float
    origin_lon: float

    @classmethod
    def build(cls, lat, lon, radius_m, cache_dir: Path) -> "CityCache":
        cache_dir.mkdir(parents=True, exist_ok=True)
        mesh = EnvironmentMesh.from_osm(lat=lat, lon=lon, radius_m=radius_m)
        scene_xml = cache_dir / "scene.xml"
        if not scene_xml.exists():
            mesh.to_sionna_xml(scene_xml)
        # buildings via the same OSM fetch parse_osm_xml uses (see Step 1)
        buildings = _buildings_for(lat, lon, radius_m)
        return cls(
            mesh=mesh,
            scene_xml=scene_xml,
            candidates=rooftop_candidates(buildings),
            origin_lat=mesh.origin_lat,
            origin_lon=mesh.origin_lon,
        )
```

Implement `_buildings_for` using the fetch found in Step 1 and `parse_osm_xml`, passing `mesh.origin_lat`/`mesh.origin_lon` as the origin so candidate XY matches the mesh frame.

- [ ] **Step 4: Add a slow integration test** (network/mesh) for `CityCache.build` on the Ghent origin, marked `@pytest.mark.slow`, asserting `candidates.shape[1] == 3`, `scene_xml.exists()`, and that candidates lie within `radius_m` of the origin.

- [ ] **Step 5: Run fast tests, lint, commit**

```bash
python -m pytest tests/study/test_city.py -v -n 0 -m "not slow"
python -m ruff check src/aegis/study/city.py tests/study/test_city.py
git add src/aegis/study/city.py tests/study/test_city.py
git commit -m "Add city mesh cache and rooftop candidates"
```

---

## Task 4: Deployment v1 (simple repulsive thinning + sectoring)

**Files:**
- Create: `src/aegis/study/deployment.py`
- Test: `tests/study/test_deployment.py`

v1 deployment is a minimum-spacing thinning of the rooftop candidates (a placeholder for Plan 3's Ginibre generator), plus the sectoring model. Site count is anchored to a scalar target (config: `density_source` reads a count; for v1 accept an explicit `n_sites` argument and defer the dataset read to Plan 3).

- [ ] **Step 1: Write the test**

```python
# tests/study/test_deployment.py
import numpy as np

from aegis.study.deployment import thin_min_spacing, Sector, build_sites, sectors_illuminating


def test_thinning_respects_min_spacing():
    rng = np.random.default_rng(0)
    cand = rng.uniform(-100, 100, size=(200, 3))
    cand[:, 2] = 15.0
    kept = thin_min_spacing(cand, min_spacing_m=30.0, n_target=10, rng=rng)
    assert kept.shape[0] <= 10
    for i in range(len(kept)):
        for j in range(i + 1, len(kept)):
            assert np.linalg.norm(kept[i, :2] - kept[j, :2]) >= 30.0 - 1e-6


def test_three_sectors_120_apart():
    site = np.array([0.0, 0.0, 15.0])
    sectors = build_sites(site[None, :], n_sectors=3, az_coverage_deg=120.0,
                          max_range_m=150.0, freq_hz=28e9, array=(8, 8),
                          tx_power_dbm=30.0)[0].sectors
    azs = sorted(s.boresight_az_deg for s in sectors)
    assert len(sectors) == 3
    assert abs((azs[1] - azs[0]) - 120.0) < 1e-6


def test_membership_wedge_and_range():
    site = build_sites(np.array([[0.0, 0.0, 15.0]]), n_sectors=3,
                       az_coverage_deg=120.0, max_range_m=150.0,
                       freq_hz=28e9, array=(8, 8), tx_power_dbm=30.0)[0]
    # point due east, in range
    near = np.array([50.0, 0.0, 1.5])
    far = np.array([300.0, 0.0, 1.5])
    assert len(sectors_illuminating(near, [site])) >= 1
    assert len(sectors_illuminating(far, [site])) == 0
```

- [ ] **Step 2: Implement**

`thin_min_spacing` greedily accepts candidates in random order, rejecting any within `min_spacing_m` (XY) of an accepted one, stopping at `n_target`. `Sector` is a frozen dataclass holding `array: AntennaArray` (built via `AntennaArray.upa` with the panel boresight as `broadside`), `boresight_az_deg`, `az_coverage_deg`, `max_range_m`, `position`. `build_sites` places `n_sectors` panels evenly in azimuth per site, each an `(n_h, n_v)` UPA at the site position. `sectors_illuminating(point, sites)` returns sectors whose horizontal range to the point is `<= max_range_m` and whose azimuth-to-point is within `±az_coverage_deg/2` of boresight.

Use `AntennaArray.upa(n_h, n_v, d_h=lam/2, d_v=lam/2, center=site_pos, broadside=unit_az_vector, element_pattern="patch")` with `lam = C_0 / freq_hz`. Import `C_0` from wherever the codebase defines it (`grep -rn "C_0\s*=" src/aegis`).

- [ ] **Step 3: Run, lint, commit**

```bash
python -m pytest tests/study/test_deployment.py -v -n 0
python -m ruff check src/aegis/study/deployment.py tests/study/test_deployment.py
git add src/aegis/study/deployment.py tests/study/test_deployment.py
git commit -m "Add v1 deployment thinning and sectoring"
```

---

## Task 5: Route to trajectory (walk)

**Files:**
- Create: `src/aegis/study/walk.py`
- Test: `tests/study/test_walk.py`

Turns a decoded lat/lon route (already in local ENU XY) into a time-sampled trajectory at slot interval `dt`, walking at constant speed, with heading set to the path tangent. Pure geometry, no network.

- [ ] **Step 1: Write the test**

```python
# tests/study/test_walk.py
import numpy as np

from aegis.study.walk import sample_trajectory


def test_constant_speed_slot_count():
    route_xy = np.array([[0.0, 0.0], [14.0, 0.0]])  # 14 m straight
    traj = sample_trajectory(route_xy, speed_mps=1.4, dt_s=1.0)
    # 14 m / 1.4 m/s = 10 s -> 11 samples (t=0..10)
    assert traj.positions.shape == (11, 2)
    np.testing.assert_allclose(traj.positions[0], [0, 0])
    np.testing.assert_allclose(traj.positions[-1], [14, 0], atol=1e-6)
    np.testing.assert_allclose(traj.headings_rad, 0.0, atol=1e-6)


def test_entry_offset_staggers_start():
    route_xy = np.array([[0.0, 0.0], [14.0, 0.0]])
    traj = sample_trajectory(route_xy, speed_mps=1.4, dt_s=1.0, entry_offset_s=3.0)
    assert traj.t0_s == 3.0
```

- [ ] **Step 2: Implement** `sample_trajectory(route_xy, speed_mps, dt_s, entry_offset_s=0.0) -> Trajectory` where `Trajectory` is a frozen dataclass `(positions (T,2), headings_rad (T,), t0_s)`. Resample the polyline by arc length at `speed_mps * dt_s` spacing; heading is `atan2(dy, dx)` of the local tangent (carry the last heading at the final point).

- [ ] **Step 3: Run, lint, commit**

```bash
python -m pytest tests/study/test_walk.py -v -n 0
python -m ruff check src/aegis/study/walk.py tests/study/test_walk.py
git add src/aegis/study/walk.py tests/study/test_walk.py
git commit -m "Add route-to-trajectory sampling"
```

---

## Task 6: Mobility - GHSL sampling + Directions routing (mobility)

**Files:**
- Create: `src/aegis/study/mobility.py`
- Test: `tests/study/test_mobility.py`

Samples origin/destination lat-lon weighted by GHSL population density, routes them with Google Directions (walking), decodes the polyline, and projects to local ENU. Routing is cached on disk keyed by rounded endpoints because the API is billed per call. The Google call is isolated behind a function so the test can inject a fake.

- [ ] **Step 1: Write the test (no network)**

```python
# tests/study/test_mobility.py
import numpy as np

from aegis.study.mobility import decode_polyline, sample_population_xy


def test_decode_polyline_known_value():
    # Google's documented example
    pts = decode_polyline("_p~iF~ps|U_ulLnnqC_mqNvxq`@")
    assert len(pts) == 3
    np.testing.assert_allclose(pts[0], [38.5, -120.2], atol=1e-4)


def test_population_sampling_prefers_dense_cells():
    # 2x2 density raster, all mass in one cell
    density = np.array([[0.0, 0.0], [0.0, 100.0]])
    rng = np.random.default_rng(0)
    lats, lons = sample_population_xy(density, bounds=(50.0, 51.0, 3.0, 4.0),
                                      n=500, rng=rng)
    # the hot cell is the lower-right -> high lon, low lat
    assert np.mean(lons) > 3.5
    assert np.mean(lats) < 50.5
```

- [ ] **Step 2: Implement** `decode_polyline` (standard Google algorithm), `sample_population_xy(density, bounds, n, rng)` (flatten, sample cells by weight, jitter within cell to lat/lon), and `route_walk(orig, dest, api_key, cache_dir)` which checks the cache, else calls Directions, decodes, and caches. Keep the actual HTTP call in a thin `_call_directions(...)` so it is trivially mockable. Read the API key from `GOOGLE_DIRECTIONS_API_KEY` env. If the key is absent, raise a clear error naming the env var (do not silently fall back to straight-line routing; that would be a quality downgrade).

- [ ] **Step 3: Add a slow, key-gated integration test** for one real route, skipped if `GOOGLE_DIRECTIONS_API_KEY` is unset, marked `@pytest.mark.slow`.

- [ ] **Step 4: Run fast tests, lint, commit**

```bash
python -m pytest tests/study/test_mobility.py -v -n 0 -m "not slow"
python -m ruff check src/aegis/study/mobility.py tests/study/test_mobility.py
git add src/aegis/study/mobility.py tests/study/test_mobility.py
git commit -m "Add GHSL sampling and Directions routing with cache"
```

Note: GHSL raster loading (reading the actual population GeoTIFF and clipping to the city bounds) is the one piece here that touches a large external file. Implement `load_ghsl_density(path, bounds)` returning the clipped raster + bounds, and gate its test on the file being present (`@pytest.mark.slow`, skip if absent), exactly as the mesh tests do.

---

## Task 7: Walking bodies + static-phantom fallback (bodies)

**Files:**
- Create: `src/aegis/study/bodies.py`
- Test: `tests/study/test_bodies.py`

Produces a `BodyMesh` at a given trajectory sample. Two backends: SMPL-X (production, via `PoseStream` + `ParametricBody`) and a static STL phantom translated/yaw-rotated (cheap, for the spike and for nodes without `smplx`/`torch`/AMASS).

- [ ] **Step 1: Write the test (static backend, no heavy deps)**

```python
# tests/study/test_bodies.py
import numpy as np

from aegis.study.bodies import StaticPhantomPoser


def test_static_phantom_translates_and_yaws(duke_mesh):
    poser = StaticPhantomPoser(base_mesh=duke_mesh)
    mesh = poser.pose(position_xy=np.array([10.0, 5.0]), heading_rad=np.pi / 2, z_ground=0.0)
    # centroid x,y should sit near the requested position
    c = mesh.vertices.mean(axis=0)
    np.testing.assert_allclose(c[:2], [10.0, 5.0], atol=1.0)
```

Provide a `duke_mesh` fixture in `tests/study/conftest.py` that loads the `duke` phantom and is skipped (`pytest.skip`) if mesh data is absent, matching the existing slow-mesh pattern.

- [ ] **Step 2: Implement** `StaticPhantomPoser.pose(...)` (rotate vertices by `heading_rad` about z, translate to `position_xy` at `z_ground`) and `SmplxWalkPoser` wrapping `PoseStream.load(clip)` + `ParametricBody.load("smplx")`, exposing the same `pose(position_xy, heading_rad, z_ground, frame_idx)` that calls `stream.posed_body(frame_idx, body, apply_translation=False)` then applies the world rotate+translate. Both return `BodyMesh`. Select backend by config/availability.

- [ ] **Step 3: Run (skips if no mesh data), lint, commit**

```bash
python -m pytest tests/study/test_bodies.py -v -n 0
python -m ruff check src/aegis/study/bodies.py tests/study/test_bodies.py
git add src/aegis/study/bodies.py tests/study/test_bodies.py tests/study/conftest.py
git commit -m "Add walking-body posers (SMPL-X + static fallback)"
```

---

## Task 8: Deterministic channel arm (channel_det)

**Files:**
- Create: `src/aegis/study/channel_det.py`
- Test: `tests/study/test_channel_det.py`

Thin wrapper over `paths_from_differt_scene`: given a sector (its `AntennaArray.element_positions` as `tx_positions`) and an rx point, return the coherent per-element `PropagationPaths`. This is the deterministic body channel source.

- [ ] **Step 1: Write the test** (a tiny synthetic scene, or skip-if-no-rt). Assert the returned paths carry `element_index` in `[0, M_ant)` and `psi` is complex, and that `paths.n_elements == M_ant`. Mark `@pytest.mark.slow` and skip if DiffeRT is not installed (`pytest.importorskip("differt")`).

- [ ] **Step 2: Implement**

```python
# src/aegis/study/channel_det.py
from __future__ import annotations

import numpy as np

from aegis.integration.differt import paths_from_differt_scene


def sector_paths_det(scene_xml, sector, rx_position, freq_hz,
                     max_bounces=3, tx_power_dbm=30.0):
    return paths_from_differt_scene(
        scene_path=scene_xml,
        tx_positions=np.asarray(sector.array.element_positions),
        rx_position=np.asarray(rx_position),
        freq_hz=freq_hz,
        max_bounces=max_bounces,
        tx_power_dbm=tx_power_dbm,
        initial_polarisation="vertical",
    )
```

Do not call `expand_paths_to_array` on this output; it already carries per-element phase (spec, Architecture).

- [ ] **Step 3: Run, lint, commit**

```bash
python -m pytest tests/study/test_channel_det.py -v -n 0
python -m ruff check src/aegis/study/channel_det.py tests/study/test_channel_det.py
git add src/aegis/study/channel_det.py tests/study/test_channel_det.py
git commit -m "Add deterministic per-sector ray-traced channel"
```

---

## Task 9: User channel vector + MRT precoder (precoding)

**Files:**
- Create: `src/aegis/study/precoding.py`
- Test: `tests/study/test_precoding.py`

**Decision task (flagged above).** Reduce a sector's per-element user paths to an `(M_ant,)` channel vector `h`, then build the fixed MRT precoder. The reduction: for each element index, coherently sum that element's path contributions into one complex scalar (project the vector `psi` onto the dominant copolar axis, then sum with phase). Confirm against `plaza_run/phy.py`'s `H` construction before locking the projection.

- [ ] **Step 1: Write the test**

```python
# tests/study/test_precoding.py
import numpy as np

from aegis.paths import PropagationPaths
from aegis.study.precoding import user_channel_vector, mrt_for_user


def test_channel_vector_length_is_m_ant():
    M = 4
    N = 3 * M
    rng = np.random.default_rng(0)
    k_hat = rng.standard_normal((N, 3)); k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
    psi = rng.standard_normal((N, 3)) + 1j * rng.standard_normal((N, 3))
    elem = np.repeat(np.arange(M), 3)
    paths = PropagationPaths(k_hat=k_hat, psi=psi, element_index=elem,
                             delay=np.zeros(N), is_los=np.ones(N, bool))
    h = user_channel_vector(paths, m_ant=M)
    assert h.shape == (M,)
    assert np.iscomplexobj(h)


def test_mrt_points_at_user():
    h = np.array([1 + 0j, 0 + 1j, -1 + 0j, 0 - 1j])
    pre = mrt_for_user(h, power_w=1.0)
    # MRT: x proportional to conj(h); check alignment
    align = np.abs(np.vdot(pre.x, np.conj(h))) / (np.linalg.norm(pre.x) * np.linalg.norm(h))
    assert align > 0.999
```

- [ ] **Step 2: Implement** `user_channel_vector(paths, m_ant, copol_axis=None)` (group `psi` by `element_index`, project onto `copol_axis` or the largest-singular-value polarization direction, sum within element) and `mrt_for_user(h, power_w)` returning `Precoder.mrt(h, P=power_w)`.

- [ ] **Step 3: Run, lint, commit**

```bash
python -m pytest tests/study/test_precoding.py -v -n 0
python -m ruff check src/aegis/study/precoding.py tests/study/test_precoding.py
git add src/aegis/study/precoding.py tests/study/test_precoding.py
git commit -m "Add user channel reduction and MRT precoder"
```

---

## Task 10: Coherent exposure (exposure)

**Files:**
- Create: `src/aegis/study/exposure.py`
- Test: `tests/study/test_exposure.py`

The dosimetry core. Two cadences:
- **Per slot (cheap):** refresh the exposure operator `Q` under the body's bulk translation with `q_translate(M_static, translation_phasor(...))`, giving the scalar absorbed power `x^H Q x` per served sector. This is the headline metric path.
- **At `recompute_period` (expensive):** call `engine.compute(body, paths, level=7, precoder=...)` for the full per-triangle Sab map (for validation and the future viz tab) and rebuild `M_static`.

Distinct sectors/sites are uncorrelated transmitters and sum in power.

- [ ] **Step 1: Write the test (engine path, free-space sanity)**

```python
# tests/study/test_exposure.py
import numpy as np

from aegis.study.exposure import scalar_exposure_w


def test_scalar_exposure_nonneg_and_hermitian_form():
    M = 4
    rng = np.random.default_rng(0)
    A = rng.standard_normal((M, M)) + 1j * rng.standard_normal((M, M))
    Q = A.conj().T @ A  # Hermitian PSD
    x = rng.standard_normal(M) + 1j * rng.standard_normal(M)
    p = scalar_exposure_w(Q, x)
    assert p >= 0
    assert abs(p.imag) < 1e-9 if np.iscomplexobj(p) else True
```

- [ ] **Step 2: Implement**
  - `scalar_exposure_w(Q, x) -> float`: `np.real(x.conj() @ Q @ x)`.
  - `build_static_gram(body, paths, array, ...)`: wrap `coherent.translation.compute_static_path_gram` with the arguments shown in the signature report (normals, centroids, areas, center_k_hat, center_psi, array_offsets, n_tilde, sigma, freq_hz). Pull `n_tilde`/`sigma` (tissue refractive index, conductivity) from the same source the engine uses; `grep` the coherent kernel for how it computes them.
  - `refresh_Q(M_static, k_hat, delta_t, freq_hz)`: `q_translate(M_static, translation_phasor(k_hat, delta_t, freq_hz))`.
  - `per_triangle_sab(engine, body, paths, precoder, level)`: `engine.compute(body, paths, level=level, precoder=precoder).sab`.
  - `combine_sites_power(per_site_watts) -> float`: sum (incoherent across sites).

- [ ] **Step 3: Add a slow cross-check test** that the per-triangle Sab integrated to absorbed power agrees with the `x^H Q x` scalar for the same body/paths/precoder at a recompute frame (they are two routes to the same number). Mark `@slow`, skip if no mesh/rt.

- [ ] **Step 4: Run fast tests, lint, commit**

```bash
python -m pytest tests/study/test_exposure.py -v -n 0 -m "not slow"
python -m ruff check src/aegis/study/exposure.py tests/study/test_exposure.py
git add src/aegis/study/exposure.py tests/study/test_exposure.py
git commit -m "Add coherent exposure (Q-phasor scalar + per-triangle map)"
```

---

## Task 11: Per-agent time loop (loop)

**Files:**
- Create: `src/aegis/study/loop.py`
- Test: `tests/study/test_loop.py`

Ties the cadences together for one agent: walk the trajectory at `dt`; re-pose every `pose_period`; for each served sector recompute the channel + `M_static` + per-triangle map every `recompute_period`, and refresh `Q` (scalar exposure) every slot via the phasor; sum sectors in power; emit a per-slot exposure series. Serial, single agent. Cadence knobs come from `TemporalConfig`.

- [ ] **Step 1: Write the test with fakes**

Inject fake posers/channel/exposure callables so the loop logic (cadence counters, sector summation, output shape) is tested without physics. Assert: number of slots equals `len(trajectory)`; the channel recompute fires exactly `ceil(T / recompute_period)` times; the per-slot Q refresh fires every slot; output is `(T,)` exposure in watts.

- [ ] **Step 2: Implement** `run_agent(agent, sites, city, engine, cfg, posers, channel_fn, exposure_fns) -> AgentResult` where `AgentResult` holds the per-slot exposure series and metadata (is_user, served-sector ids). Keep all physics behind injected callables so the loop stays pure control flow (this is what makes Step 1 possible and keeps the loop testable). Honor `sectors_illuminating` per slot so a body only interacts with nearby panels.

- [ ] **Step 3: Run, lint, commit**

```bash
python -m pytest tests/study/test_loop.py -v -n 0
python -m ruff check src/aegis/study/loop.py tests/study/test_loop.py
git add src/aegis/study/loop.py tests/study/test_loop.py
git commit -m "Add per-agent time loop with cadence knobs"
```

---

## Task 12: Exposure reduction + CDF (reduce)

**Files:**
- Create: `src/aegis/study/reduce.py`
- Test: `tests/study/test_reduce.py`

Per-person time-averaged exposure over the walk, expressed as a fraction of the ICNIRP limit, plus the population CDF and the retained per-timestep distribution.

- [ ] **Step 1: Use the confirmed ICNIRP reference**

The limit lives in `src/aegis/compliance`: `from aegis.compliance import icnirp_limits, ExposureScenario`, then `icnirp_limits(scenario=ExposureScenario.GENERAL_PUBLIC, freq_hz=28e9)` returns an `ICNIRPLimits` whose `.sab_4cm2` (W/m^2) is the headline absorbed-power-density limit above 6 GHz (`.sab_1cm2` applies above 30 GHz). At 28 GHz use `.sab_4cm2`. Do not hardcode `plaza_run`'s `reference_level_vpm`.

- [ ] **Step 2: Write the test**

```python
# tests/study/test_reduce.py
import numpy as np

from aegis.study.reduce import time_average, population_cdf


def test_time_average_is_mean_power():
    series = np.array([1.0, 3.0, 2.0, 2.0])
    assert time_average(series) == 2.0


def test_cdf_is_monotone_in_zero_one():
    samples = np.array([0.1, 0.2, 0.05, 0.4])
    x, f = population_cdf(samples)
    assert np.all(np.diff(f) >= 0)
    assert f[0] >= 0 and f[-1] <= 1.0 + 1e-9
    assert x[0] <= x[-1]
```

- [ ] **Step 3: Implement** `time_average(series)`, `as_icnirp_fraction(power_w, ...)` (using the Step 1 limit), and `population_cdf(samples)` returning the sorted samples and empirical CDF.

- [ ] **Step 4: Run, lint, commit**

```bash
python -m pytest tests/study/test_reduce.py -v -n 0
python -m ruff check src/aegis/study/reduce.py tests/study/test_reduce.py
git add src/aegis/study/reduce.py tests/study/test_reduce.py
git commit -m "Add exposure reduction and population CDF"
```

---

## Task 13: Cost-discovery spike (spike) - build-order step 1

**Files:**
- Create: `src/aegis/study/spike.py`
- Test: `tests/study/test_spike.py`

A timing harness that measures wall-clock per slot for the deterministic ray trace and the coherent dosimetry on a real city mesh with one static phantom, plus GPU memory if available. Its output sets the `temporal` cadences. This is the first thing run on real hardware.

- [ ] **Step 1: Write the test (smoke, fast)** asserting `spike.measure(...)` returns a dict with keys `raytrace_s`, `dosimetry_s`, `q_refresh_s`, and that all are positive, using fakes for the heavy calls so the test is fast.

- [ ] **Step 2: Implement** `measure(city, sector, body, engine, n_reps)` timing `sector_paths_det`, `per_triangle_sab`, and `refresh_Q` separately, and a `recommend_cadences(timings, budget_s_per_agent)` that proposes `dt_s`, `pose_period`, `recompute_period`. Add a `__main__` so it runs as `python -m aegis.study.spike --config configs/study/ghent_core_v1.yaml`. Use the static phantom backend to isolate ray-trace cost from posing.

- [ ] **Step 3: Run fast test, lint, commit**

```bash
python -m pytest tests/study/test_spike.py -v -n 0
python -m ruff check src/aegis/study/spike.py tests/study/test_spike.py
git add src/aegis/study/spike.py tests/study/test_spike.py
git commit -m "Add cost-discovery spike harness"
```

- [ ] **Step 4: Run the spike on real hardware (manual, documented)**

This step needs the city mesh, DiffeRT, and ideally a GPU. If unavailable in this environment, STOP and hand off to Robin per `CLAUDE.md` ("When you're stuck, ask Robin") with a copy-paste command. Record the measured cadences into `configs/study/ghent_core_v1.yaml` (replacing the `TBD` nulls) and commit that as a separate change.

---

## Task 14: Headless run entry (run) - build-order step 2

**Files:**
- Create: `src/aegis/study/run.py`
- Test: `tests/study/test_run.py`

The orchestrator: load config, build the city cache, sample the crowd, build the deployment, run each agent through the loop, reduce to per-person exposure, write results (NPZ + JSON + a CDF figure). Job-array friendly via `--agent-start`/`--agent-count`.

- [ ] **Step 1: Write the test (tiny, fakes for physics)**

A 3-agent, 4-slot run with injected fake channel/exposure, asserting the output NPZ exists, holds 3 per-person samples, and a CDF JSON is written. No network, no mesh, no rt.

- [ ] **Step 2: Implement** `main(argv)` parsing `--config`, `--out`, `--seed`, `--agent-start`, `--agent-count`, mirroring the `plaza_run/run.py` config-plus-flags idiom. Compose Tasks 3-12. Write `results/<run-id>/exposure.npz`, `summary.json`, and `cdf.png` (matplotlib + scienceplots, IEEE single-column style per `feedback_figure_style`). Add a `[project.scripts]` entry (peer of the existing `aegis` and `aegis-run`): `aegis-study = "aegis.study.run:main"` in `pyproject.toml`.

- [ ] **Step 3: Run fast test, lint, commit**

```bash
python -m pytest tests/study/test_run.py -v -n 0
python -m ruff check src/aegis/study/run.py tests/study/test_run.py
git add src/aegis/study/run.py tests/study/test_run.py pyproject.toml
git commit -m "Add headless study run entry"
```

---

## Task 15: Tiny end-to-end integration test

**Files:**
- Test: `tests/study/test_e2e.py`

- [ ] **Step 1: Write a `@pytest.mark.slow` test** that runs the real pipeline on a minimal config (radius ~100 m, 3 agents, 8 slots, 1 site/3 sectors, static phantom, deterministic only) end to end and asserts a CDF file is written with 3 finite, non-negative samples. Skip if mesh data or DiffeRT is absent.

- [ ] **Step 2: Run it if the environment allows**

Run: `python -m pytest tests/study/test_e2e.py -v -n 0`
If skipped for missing data/rt, note that in the PR description and hand the real run to Robin.

- [ ] **Step 3: Commit**

```bash
git add tests/study/test_e2e.py
git commit -m "Add tiny end-to-end study integration test"
```

---

## Task 16: Full lint, test sweep, docs note, PR

**Files:**
- Modify: a short note in `docs/` developer guide pointing at the new module (optional, follow `docs-style.md`).

- [ ] **Step 1: Full fast suite**

```bash
python -m ruff check src/aegis/study tests/study
python -m ruff format --check src/aegis/study tests/study
python -m pytest tests/study -m "not slow" -n 0
```
Expected: all pass. The Mie regression test (the CI canary) is untouched by this module; confirm it still passes: `python -m pytest tests/ -k mie -n 0`.

- [ ] **Step 2: Push and open the PR**

```bash
git push -u origin feature/hpc-study-deterministic-spine
gh pr create --title "Add HPC study deterministic single-city exposure spine" \
  --body "## Summary
- New headless aegis.study module: walks a synchronized crowd through one OSM city core under a sectored mmWave deployment and writes a population exposure CDF
- Deterministic arm only (coherent Sab, fixed MRT beam), per the design spec build-order steps 1-2
- Cost-discovery spike harness sets the temporal cadences
- Stochastic arm, Ginibre generator, K-marginalization, multi-city, and the R3F tab are Plans 2-5

## Notes
- SMPL-X / AMASS / DiffeRT / GHSL / Directions-key dependent paths are gated and skip cleanly when absent
- Three open design points (user channel reduction, OSM frame reuse, ICNIRP reference) are resolved in Tasks 9, 2, 12 respectively

## Test plan
- Fast unit suite green: pytest tests/study -m 'not slow'
- Slow/integration tests require mesh data + DiffeRT + a GPU; run on the cluster" \
  --base master
gh pr merge --squash --delete-branch
git checkout master && git pull origin master
```

- [ ] **Step 3: Update the project memory**

After merge, update `project_ten_cities_study.md`: Plan 1 landed, link to the merged PR, note that the spike's measured cadences are now in the config, and that Plan 2 (coherent 38.901) is next.

---

## Notes on discipline

- **TDD throughout.** Every task writes the failing test first. The loop, run, and spike tasks inject fakes for physics so control flow is tested fast and the slow physics paths are exercised separately under `@slow`.
- **No silent quality downgrades.** Missing Directions key, missing mesh data, missing DiffeRT, missing SMPL-X all raise or skip with a clear message. None fall back to a worse method silently (per `CLAUDE.md` and `feedback_ask_for_help`).
- **Frequent commits**, one per task, on the feature branch. Squash-merge at the end.
- **Do not weaken any existing assertion** to make a test pass. The Mie canary stays green.
