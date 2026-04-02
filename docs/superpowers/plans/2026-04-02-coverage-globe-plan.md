# Coverage globe implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a 3D globe view with tiered LOD rendering of ~800K base station antennas across 13 regions, accessible as a 4th scenario card from the welcome screen.

**Architecture:** A new backend endpoint pre-computes coverage data at three tiers (regions, clusters, sites) from merged Parquet files. A new frontend component renders the appropriate tier based on camera altitude inside the existing `Environment3DTiles` globe wrapper. A new scenario entry and Zustand store orchestrate the flow.

**Tech Stack:** Python/Flask backend, React/Three.js/R3F frontend, Zustand state, `3d-tiles-renderer` for globe, `@react-three/drei` for labels/lines, existing Parquet pipeline.

**Spec:** `docs/superpowers/specs/2026-04-02-coverage-globe-design.md`

---

## File structure

### New files

| File | Responsibility |
|---|---|
| `src/aegis/viewer/routes/coverage.py` | Backend endpoint: reads Parquet, computes 3 tiers, caches, returns JSON+base64 |
| `tests/test_coverage_endpoint.py` | Backend tests for tier computation, binary encoding, caching |
| `aegis-web/src/lib/geo.ts` | Shared `latLonToECEF`, `ecefToLatLon`, `WGS84_A` constants |
| `aegis-web/src/stores/coverage.ts` | Zustand store: coverage state, fetch, tier switching |
| `aegis-web/src/api/coverage.ts` | API client: `fetchCoverage()` with response parsing |
| `aegis-web/src/components/scene/CoverageGlobe.tsx` | Scene component: tier-based LOD rendering (regions, clusters, sites) |
| `aegis-web/src/components/hud/CoverageHud.tsx` | HUD overlay: legend, "Set up scene here", "Back to globe" buttons |

### Modified files

| File | Change |
|---|---|
| `src/aegis/viewer/config.py` | Add `coverage_globe` scenario to DEFAULTS |
| `src/aegis/viewer/server.py` | Import and register coverage routes |
| `aegis-web/src/components/scene/Environment3DTiles.tsx` | Import `latLonToECEF` from `@/lib/geo` instead of local definition |
| `aegis-web/src/components/hud/WelcomeOverlay.tsx` | Add `Globe` icon, adjust grid to 4 columns |
| `aegis-web/src/hooks/useScenario.ts` | Add coverage_globe case in `loadScenario` |
| `aegis-web/src/components/scene/SceneRoot.tsx` | Mount `<CoverageGlobe />` |
| `aegis-web/src/components/layout/HudOverlay.tsx` | Mount `<CoverageHud />` |
| `aegis-web/src/api/types.ts` | Add coverage TypeScript interfaces |

---

### Task 1: Backend coverage endpoint

**Files:**
- Create: `src/aegis/viewer/routes/coverage.py`
- Modify: `src/aegis/viewer/server.py:543-566`
- Test: `tests/test_coverage_endpoint.py`

This task builds the `GET /api/basestations/coverage` endpoint that reads all merged Parquet files and returns three tiers of data: region summaries (JSON), spatial clusters (JSON), and deduplicated site positions (base64-encoded binary).

**Reference files to read first:**
- `src/aegis/viewer/routes/basestations.py` (lines 1-30) for the route file pattern (`register(app, cache, cache_lock)`)
- `data/basestations/regions.yaml` for region definitions and bbox format `[min_lon, max_lon, min_lat, max_lat]`
- `data/basestations/merged/` directory listing for available Parquet files
- `docs/superpowers/specs/2026-04-02-coverage-globe-design.md` sections "Backend: coverage data endpoint" and "Error handling"

- [ ] **Step 1: Write the failing test for tier 1 (region summaries)**

```python
# tests/test_coverage_endpoint.py
"""Tests for the coverage endpoint tier computation."""
import struct
import base64
import numpy as np
import pandas as pd
import pytest
from pathlib import Path


def _make_test_parquet(tmp_path: Path, region: str, n: int = 100) -> Path:
    """Create a minimal merged parquet with n antennas."""
    merged_dir = tmp_path / "merged"
    merged_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        "SiteCode": [f"SITE({i})" for i in range(n)],
        "Operator": rng.choice(["OpA", "OpB"], n),
        "Technology": rng.choice(["LTE", "5G"], n),
        "Latitude": rng.uniform(50.0, 51.0, n),
        "Longitude": rng.uniform(3.0, 4.0, n),
        "Power": rng.choice([30.0, np.nan], n),
        "Azimuth": rng.choice([90.0, np.nan], n),
        "CenterHeight": rng.choice([25.0, np.nan], n),
        "Frequency": rng.choice([1800.0, np.nan], n),
        "Gain": rng.choice([18.0, np.nan], n),
    })
    out = merged_dir / f"{region}.parquet"
    df.to_parquet(str(out))
    return out


def _make_test_regions_yaml(tmp_path: Path, regions: dict) -> Path:
    """Create a test regions.yaml."""
    import yaml
    yaml_path = tmp_path / "regions.yaml"
    yaml_path.write_text(yaml.dump({"regions": regions}))
    return yaml_path


def test_compute_regions_from_parquet(tmp_path):
    """Tier 1: region summaries are computed correctly from parquet data."""
    from aegis.viewer.routes.coverage import _compute_coverage

    _make_test_parquet(tmp_path, "testregion", n=50)
    regions_cfg = {
        "testregion": {
            "sources": [{"bbox": [3.0, 4.0, 50.0, 51.0]}]
        }
    }
    yaml_path = _make_test_regions_yaml(tmp_path, regions_cfg)

    result = _compute_coverage(
        merged_dir=tmp_path / "merged",
        regions_yaml=yaml_path,
    )

    assert len(result["regions"]) == 1
    r = result["regions"][0]
    assert r["name"] == "testregion"
    assert r["count"] == 50
    assert r["bbox"] == [3.0, 4.0, 50.0, 51.0]
    assert 0.0 <= r["completeness"] <= 1.0


def test_compute_regions_bbox_from_data(tmp_path):
    """Regions without bbox in yaml get bbox computed from data."""
    from aegis.viewer.routes.coverage import _compute_coverage

    _make_test_parquet(tmp_path, "nobbox", n=20)
    regions_cfg = {
        "nobbox": {"sources": [{"type": "basestationlib"}]}
    }
    yaml_path = _make_test_regions_yaml(tmp_path, regions_cfg)

    result = _compute_coverage(
        merged_dir=tmp_path / "merged",
        regions_yaml=yaml_path,
    )

    r = result["regions"][0]
    assert r["bbox"] is not None
    assert len(r["bbox"]) == 4
    # bbox should contain the data range with padding
    min_lon, max_lon, min_lat, max_lat = r["bbox"]
    assert min_lon < 4.0  # data is 3.0-4.0
    assert max_lon > 3.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/user/aegis && .venv/bin/python -m pytest tests/test_coverage_endpoint.py -v -x`
Expected: FAIL with `ModuleNotFoundError: No module named 'aegis.viewer.routes.coverage'`

- [ ] **Step 3: Implement `_compute_coverage` and the route**

Create `src/aegis/viewer/routes/coverage.py`:

```python
"""Coverage endpoint: pre-computed global base station overview."""

from __future__ import annotations

import base64
import logging
import struct
import threading
from math import floor
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from flask import Flask, jsonify

logger = logging.getLogger(__name__)

_COMPLETENESS_COLS = ["Power", "Azimuth", "CenterHeight", "Frequency", "Gain"]


def _compute_coverage(
    merged_dir: Path,
    regions_yaml: Path,
) -> dict:
    """Build the three-tier coverage response from parquet files."""
    with open(regions_yaml) as f:
        cfg = yaml.safe_load(f)

    regions_cfg = cfg.get("regions", {})
    all_dfs: list[pd.DataFrame] = []
    regions_out: list[dict] = []

    for name, rcfg in sorted(regions_cfg.items()):
        pq = merged_dir / f"{name}.parquet"
        if not pq.exists():
            continue
        try:
            df = pd.read_parquet(str(pq))
        except Exception:
            logger.warning("Corrupt parquet %s, skipping", pq)
            continue

        # Bbox: read from first source, or compute from data
        bbox = None
        for src in rcfg.get("sources", []):
            if "bbox" in src:
                bbox = src["bbox"]
                break
        if bbox is None and "Latitude" in df.columns and "Longitude" in df.columns:
            pad = 0.01
            bbox = [
                float(df["Longitude"].min() - pad),
                float(df["Longitude"].max() + pad),
                float(df["Latitude"].min() - pad),
                float(df["Latitude"].max() + pad),
            ]

        # Completeness: fraction of non-null values in key columns
        present_cols = [c for c in _COMPLETENESS_COLS if c in df.columns]
        if present_cols:
            completeness = float(df[present_cols].notna().mean().mean())
        else:
            completeness = 0.0

        label = name.replace("_", " ").title()
        regions_out.append({
            "name": name,
            "label": label,
            "bbox": bbox,
            "count": len(df),
            "completeness": round(completeness, 2),
        })
        all_dfs.append(df)

    if not all_dfs:
        return {
            "regions": [],
            "clusters": [],
            "sites_meta": {"count": 0, "operators": [], "technologies": []},
            "sites_b64": "",
        }

    combined = pd.concat(all_dfs, ignore_index=True)

    # Tier 2: clusters (0.1-degree grid)
    combined["_cell_lat"] = np.floor(combined["Latitude"] / 0.1) * 0.1 + 0.05
    combined["_cell_lon"] = np.floor(combined["Longitude"] / 0.1) * 0.1 + 0.05
    grouped = combined.groupby(["_cell_lat", "_cell_lon"])
    clusters = []
    for (clat, clon), grp in grouped:
        op_mode = grp["Operator"].mode()
        tech_mode = grp["Technology"].mode()
        clusters.append({
            "lat": round(float(clat), 2),
            "lon": round(float(clon), 2),
            "count": len(grp),
            "operator": str(op_mode.iloc[0]) if len(op_mode) > 0 else "",
            "technology": str(tech_mode.iloc[0]) if len(tech_mode) > 0 else "",
        })

    # Tier 3: sites (deduplicated by SiteCode)
    if "SiteCode" in combined.columns:
        sites = combined.drop_duplicates(subset="SiteCode", keep="first")
    else:
        sites = combined.drop_duplicates(subset=["Latitude", "Longitude"], keep="first")

    op_col = sites["Operator"].fillna("Unknown")
    tech_col = sites["Technology"].fillna("Unknown")
    operators = sorted(op_col.unique().tolist())
    technologies = sorted(tech_col.unique().tolist())
    op_map = {o: i for i, o in enumerate(operators)}
    tech_map = {t: i for i, t in enumerate(technologies)}

    # Pack binary: float32 lat, float32 lon, uint8 op_idx, uint8 tech_idx
    buf = bytearray()
    for _, row in sites.iterrows():
        buf.extend(struct.pack("<ff", float(row["Latitude"]), float(row["Longitude"])))
        buf.append(op_map.get(str(row.get("Operator", "Unknown")), 0))
        buf.append(tech_map.get(str(row.get("Technology", "Unknown")), 0))

    return {
        "regions": regions_out,
        "clusters": clusters,
        "sites_meta": {
            "count": len(sites),
            "operators": operators,
            "technologies": technologies,
        },
        "sites_b64": base64.b64encode(bytes(buf)).decode("ascii"),
    }


def register(app: Flask, cache: dict, cache_lock: threading.RLock) -> None:
    """Register coverage routes."""

    @app.route("/api/basestations/coverage")
    def api_coverage():
        with cache_lock:
            if "coverage_response" in cache:
                return jsonify(cache["coverage_response"])

        data_dir = cache.get("data_dir", "data")
        merged_dir = Path(data_dir) / "basestations" / "merged"
        regions_yaml = Path(data_dir) / "basestations" / "regions.yaml"

        if not regions_yaml.exists():
            return jsonify({"error": "regions.yaml not found"}), 500

        result = _compute_coverage(merged_dir, regions_yaml)

        with cache_lock:
            cache["coverage_response"] = result

        return jsonify(result)
```

- [ ] **Step 4: Write tests for tier 2 (clusters) and tier 3 (sites binary)**

Add to `tests/test_coverage_endpoint.py`:

```python
def test_compute_clusters(tmp_path):
    """Tier 2: antennas are spatially binned into 0.1-degree cells."""
    from aegis.viewer.routes.coverage import _compute_coverage

    _make_test_parquet(tmp_path, "clustered", n=200)
    regions_cfg = {"clustered": {"sources": [{"bbox": [3.0, 4.0, 50.0, 51.0]}]}}
    yaml_path = _make_test_regions_yaml(tmp_path, regions_cfg)

    result = _compute_coverage(tmp_path / "merged", yaml_path)
    clusters = result["clusters"]

    assert len(clusters) > 0
    total = sum(c["count"] for c in clusters)
    assert total == 200
    for c in clusters:
        assert "lat" in c
        assert "lon" in c
        assert "count" in c
        assert c["count"] > 0


def test_compute_sites_binary(tmp_path):
    """Tier 3: sites are encoded as base64 binary with correct format."""
    from aegis.viewer.routes.coverage import _compute_coverage

    _make_test_parquet(tmp_path, "binary", n=30)
    regions_cfg = {"binary": {"sources": [{"bbox": [3.0, 4.0, 50.0, 51.0]}]}}
    yaml_path = _make_test_regions_yaml(tmp_path, regions_cfg)

    result = _compute_coverage(tmp_path / "merged", yaml_path)
    meta = result["sites_meta"]
    raw = base64.b64decode(result["sites_b64"])

    assert meta["count"] > 0
    assert len(raw) == meta["count"] * 10  # 10 bytes per record
    assert len(meta["operators"]) > 0
    assert len(meta["technologies"]) > 0

    # Parse first record
    lat, lon = struct.unpack_from("<ff", raw, 0)
    op_idx = raw[8]
    tech_idx = raw[9]
    assert 49.0 < lat < 52.0
    assert 2.0 < lon < 5.0
    assert op_idx < len(meta["operators"])
    assert tech_idx < len(meta["technologies"])


def test_empty_merged_dir(tmp_path):
    """Empty merged dir returns empty response, not error."""
    from aegis.viewer.routes.coverage import _compute_coverage

    (tmp_path / "merged").mkdir()
    regions_cfg = {"missing": {"sources": [{"bbox": [0, 1, 0, 1]}]}}
    yaml_path = _make_test_regions_yaml(tmp_path, regions_cfg)

    result = _compute_coverage(tmp_path / "merged", yaml_path)
    assert result["regions"] == []
    assert result["clusters"] == []
    assert result["sites_meta"]["count"] == 0
```

- [ ] **Step 5: Run all tests**

Run: `cd /home/user/aegis && .venv/bin/python -m pytest tests/test_coverage_endpoint.py -v`
Expected: All PASS

- [ ] **Step 6: Create feature branch**

This is a large change (5+ files), so use the PR workflow per `.claude/rules/git-workflow.md`:

```bash
git checkout -b feature/coverage-globe
```

- [ ] **Step 7: Register the route in server.py**

Modify `src/aegis/viewer/server.py`. In the import block (around line 543), add:

```python
from aegis.viewer.routes import (
    ...
    coverage,  # add this line
    ...
)
```

And in the registration block (around line 558), add:

```python
coverage.register(app, _cache, _cache_lock)
```

- [ ] **Step 8: Commit**

```bash
git add src/aegis/viewer/routes/coverage.py tests/test_coverage_endpoint.py src/aegis/viewer/server.py
git commit -m "feat: add coverage endpoint with 3-tier pre-computation"
```

---

### Task 2: Scenario config and welcome overlay

**Files:**
- Modify: `src/aegis/viewer/config.py:494-561`
- Modify: `aegis-web/src/components/hud/WelcomeOverlay.tsx`

This task adds the `coverage_globe` scenario entry and the 4th welcome card. No new components yet, just the config plumbing.

**Reference files to read first:**
- `src/aegis/viewer/config.py` lines 494-561 for the scenarios dict format
- `aegis-web/src/components/hud/WelcomeOverlay.tsx` for ICON_MAP and grid layout
- `aegis-web/src/api/types.ts` lines 100-123 for ScenarioWebState

- [ ] **Step 1: Add the scenario to config.py**

Add after the `"empty"` scenario entry in `config.py` DEFAULTS (around line 561):

```python
"coverage_globe": {
    "description": "Browse base station coverage worldwide",
    "launch": {},
    "label": "Coverage globe",
    "icon": "globe",
    "instant": True,
    "autoCompute": False,
    "webState": {
        "antennaPos": None,
        "environment": {
            "source": "3dtiles",
            "lat": 0,
            "lon": 0,
        },
    },
},
```

- [ ] **Step 2: Add Globe icon to WelcomeOverlay**

In `aegis-web/src/components/hud/WelcomeOverlay.tsx`:

Add import (around line 2):
```typescript
import { Radio, Zap, Building2, Globe } from 'lucide-react'
```

Update ICON_MAP (around line 7):
```typescript
const ICON_MAP: Record<string, React.FC<{ size?: number; className?: string }>> = {
  radio: Radio,
  zap: Zap,
  building: Building2,
  globe: Globe,
}
```

Update grid layout (around line 59), change:
```
grid grid-cols-1 sm:grid-cols-3 gap-3 w-full
```
to:
```
grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 w-full
```

- [ ] **Step 3: Verify visually**

Run the dev server: `cd aegis-web && npm run dev`
Open the app. The welcome screen should show 4 cards. The "Coverage globe" card should appear with a globe icon. Clicking it should activate 3D tiles (if Google API key is configured) but no coverage data overlay yet.

- [ ] **Step 4: Commit**

```bash
git add src/aegis/viewer/config.py aegis-web/src/components/hud/WelcomeOverlay.tsx
git commit -m "feat: add coverage_globe scenario card to welcome screen"
```

---

### Task 3: Extract shared geo utilities

**Files:**
- Create: `aegis-web/src/lib/geo.ts`
- Modify: `aegis-web/src/components/scene/Environment3DTiles.tsx:1-28`

This task extracts `latLonToECEF` and `WGS84_A` from `Environment3DTiles.tsx` into a shared utility so both the 3D tiles component and the coverage store can use them.

**Reference files to read first:**
- `aegis-web/src/components/scene/Environment3DTiles.tsx` lines 1-28 for the existing function

- [ ] **Step 1: Create the shared geo utility**

Create `aegis-web/src/lib/geo.ts`:

```typescript
import * as THREE from 'three'

/** WGS84 semi-major axis in meters. */
export const WGS84_A = 6378137.0

/** Convert lat/lon (degrees) + altitude (meters) to ECEF position. */
export function latLonToECEF(latDeg: number, lonDeg: number, altitude: number): THREE.Vector3 {
  const latRad = (latDeg * Math.PI) / 180
  const lonRad = (lonDeg * Math.PI) / 180
  const r = WGS84_A + altitude
  const cosLat = Math.cos(latRad)
  return new THREE.Vector3(
    r * cosLat * Math.cos(lonRad),
    r * cosLat * Math.sin(lonRad),
    r * Math.sin(latRad),
  )
}

/** Convert lat/lon (radians) + altitude (meters) to ECEF position. */
export function latLonRadToECEF(latRad: number, lonRad: number, altitude: number): THREE.Vector3 {
  const r = WGS84_A + altitude
  const cosLat = Math.cos(latRad)
  return new THREE.Vector3(
    r * cosLat * Math.cos(lonRad),
    r * cosLat * Math.sin(lonRad),
    r * Math.sin(latRad),
  )
}

/** Extract lat/lon (degrees) from an ECEF position. */
export function ecefToLatLon(pos: THREE.Vector3): { lat: number; lon: number } {
  const lon = Math.atan2(pos.y, pos.x) * (180 / Math.PI)
  const lat = Math.atan2(pos.z, Math.sqrt(pos.x * pos.x + pos.y * pos.y)) * (180 / Math.PI)
  return { lat, lon }
}
```

- [ ] **Step 2: Update Environment3DTiles.tsx to import from shared utility**

In `aegis-web/src/components/scene/Environment3DTiles.tsx`:

Remove the local `WGS84_A` constant and `latLonToECEF` function (lines 17-28). Replace with:

```typescript
import { latLonRadToECEF } from '@/lib/geo'
```

Update `GlobeCameraInit` and `GlobeCameraRecenter` to use `latLonRadToECEF` instead of the local function. The call sites pass radians, so use the radian variant. Example in `GlobeCameraInit`:

```typescript
const surfacePos = latLonRadToECEF(latRad, lonRad, 0)
const cameraPos = latLonRadToECEF(latRad, lonRad, 800)
```

- [ ] **Step 3: Verify the existing 3D tiles view still works**

Run: `cd aegis-web && npm run dev`
Load the "Urban Ghent" scenario. Verify the 3D tiles globe renders correctly with the same camera positioning.

- [ ] **Step 4: Commit**

```bash
git add aegis-web/src/lib/geo.ts aegis-web/src/components/scene/Environment3DTiles.tsx
git commit -m "refactor: extract latLonToECEF to shared geo utility"
```

---

### Task 4: Coverage API client and TypeScript types

**Files:**
- Create: `aegis-web/src/api/coverage.ts`
- Modify: `aegis-web/src/api/types.ts`

This task adds the TypeScript interfaces for coverage data and the API client function.

**Reference files to read first:**
- `aegis-web/src/api/client.ts` for `fetchWithRetry` pattern
- `aegis-web/src/api/types.ts` for existing interface patterns
- `docs/superpowers/specs/2026-04-02-coverage-globe-design.md` for the response JSON schema

- [ ] **Step 1: Add TypeScript interfaces to types.ts**

Add to `aegis-web/src/api/types.ts` (at the end of the file):

```typescript
// Coverage globe types

export interface RegionSummary {
  name: string
  label: string
  bbox: [number, number, number, number]  // [min_lon, max_lon, min_lat, max_lat]
  count: number
  completeness: number
}

export interface ClusterPoint {
  lat: number
  lon: number
  count: number
  operator: string
  technology: string
}

export interface CoverageSitesMeta {
  count: number
  operators: string[]
  technologies: string[]
}

export interface CoverageResponse {
  regions: RegionSummary[]
  clusters: ClusterPoint[]
  sites_meta: CoverageSitesMeta
  sites_b64: string
}
```

- [ ] **Step 2: Create the API client**

Create `aegis-web/src/api/coverage.ts`:

```typescript
import type { CoverageResponse } from './types'

export async function fetchCoverage(): Promise<CoverageResponse> {
  const resp = await fetch('/api/basestations/coverage')
  if (!resp.ok) {
    throw new Error(`Coverage fetch failed: ${resp.status}`)
  }
  return resp.json()
}

/** Decode base64 sites binary into typed arrays. */
export function decodeSitesBinary(
  b64: string,
  count: number,
): { latitudes: Float32Array; longitudes: Float32Array; opIndices: Uint8Array; techIndices: Uint8Array } {
  const raw = Uint8Array.from(atob(b64), c => c.charCodeAt(0))
  const latitudes = new Float32Array(count)
  const longitudes = new Float32Array(count)
  const opIndices = new Uint8Array(count)
  const techIndices = new Uint8Array(count)

  const view = new DataView(raw.buffer)
  for (let i = 0; i < count; i++) {
    const offset = i * 10
    latitudes[i] = view.getFloat32(offset, true)      // little-endian
    longitudes[i] = view.getFloat32(offset + 4, true)
    opIndices[i] = raw[offset + 8]
    techIndices[i] = raw[offset + 9]
  }

  return { latitudes, longitudes, opIndices, techIndices }
}
```

- [ ] **Step 3: Commit**

```bash
git add aegis-web/src/api/coverage.ts aegis-web/src/api/types.ts
git commit -m "feat: add coverage API client and TypeScript types"
```

---

### Task 5: Coverage Zustand store

**Files:**
- Create: `aegis-web/src/stores/coverage.ts`

This task creates the Zustand store that fetches coverage data, converts lat/lon to ECEF, and manages tier state.

**Reference files to read first:**
- `aegis-web/src/stores/basestations.ts` for existing Zustand store patterns
- `aegis-web/src/lib/geo.ts` for `latLonToECEF`
- `aegis-web/src/api/coverage.ts` for `fetchCoverage` and `decodeSitesBinary`

- [ ] **Step 1: Create the coverage store**

Create `aegis-web/src/stores/coverage.ts`:

```typescript
import { create } from 'zustand'
import { fetchCoverage, decodeSitesBinary } from '@/api/coverage'
import { latLonToECEF } from '@/lib/geo'
import type { RegionSummary, ClusterPoint } from '@/api/types'

// Operator colors: consistent palette for up to 16 operators
const OPERATOR_COLORS: [number, number, number][] = [
  [0.23, 0.51, 0.96],  // blue
  [0.96, 0.51, 0.11],  // orange
  [0.18, 0.76, 0.49],  // green
  [0.66, 0.33, 0.83],  // purple
  [0.91, 0.30, 0.24],  // red
  [0.10, 0.74, 0.81],  // cyan
  [0.98, 0.75, 0.18],  // yellow
  [0.55, 0.34, 0.16],  // brown
  [0.44, 0.50, 0.56],  // gray
  [0.84, 0.37, 0.65],  // pink
  [0.40, 0.65, 0.12],  // lime
  [0.70, 0.20, 0.36],  // maroon
  [0.30, 0.30, 0.80],  // indigo
  [0.80, 0.60, 0.40],  // tan
  [0.50, 0.80, 0.80],  // teal
  [0.60, 0.60, 0.20],  // olive
]

interface CoverageState {
  enabled: boolean
  loaded: boolean
  loading: boolean
  regions: RegionSummary[]
  clusters: ClusterPoint[]
  sitePositions: Float32Array | null
  siteColors: Float32Array | null
  siteCount: number
  operatorNames: string[]
  technologyNames: string[]
  activeTier: 1 | 2 | 3
  cameraLatLon: { lat: number; lon: number } | null
  cameraAltitude: number
  hoveredRegion: string | null

  fetch: () => Promise<void>
  setEnabled: (v: boolean) => void
  setActiveTier: (t: 1 | 2 | 3) => void
  setCameraLatLon: (ll: { lat: number; lon: number }) => void
  setCameraAltitude: (alt: number) => void
  setHoveredRegion: (r: string | null) => void
}

export const useCoverageStore = create<CoverageState>((set, get) => ({
  enabled: false,
  loaded: false,
  loading: false,
  regions: [],
  clusters: [],
  sitePositions: null,
  siteColors: null,
  siteCount: 0,
  operatorNames: [],
  technologyNames: [],
  activeTier: 1,
  cameraLatLon: null,
  cameraAltitude: Infinity,
  hoveredRegion: null,

  fetch: async () => {
    if (get().loaded || get().loading) return
    set({ loading: true })
    try {
      const data = await fetchCoverage()

      // Decode binary sites
      const { latitudes, longitudes, opIndices } = decodeSitesBinary(
        data.sites_b64,
        data.sites_meta.count,
      )

      // Convert to ECEF positions (500m above surface to avoid z-fighting)
      const positions = new Float32Array(data.sites_meta.count * 3)
      const colors = new Float32Array(data.sites_meta.count * 3)
      for (let i = 0; i < data.sites_meta.count; i++) {
        const ecef = latLonToECEF(latitudes[i], longitudes[i], 500)
        positions[i * 3] = ecef.x
        positions[i * 3 + 1] = ecef.y
        positions[i * 3 + 2] = ecef.z

        const color = OPERATOR_COLORS[opIndices[i] % OPERATOR_COLORS.length]
        colors[i * 3] = color[0]
        colors[i * 3 + 1] = color[1]
        colors[i * 3 + 2] = color[2]
      }

      set({
        regions: data.regions,
        clusters: data.clusters,
        sitePositions: positions,
        siteColors: colors,
        siteCount: data.sites_meta.count,
        operatorNames: data.sites_meta.operators,
        technologyNames: data.sites_meta.technologies,
        loaded: true,
        loading: false,
      })
    } catch (err) {
      console.error('Failed to fetch coverage data:', err)
      set({ loading: false })
    }
  },

  setEnabled: (v) => set({ enabled: v }),
  setActiveTier: (t) => set({ activeTier: t }),
  setCameraLatLon: (ll) => set({ cameraLatLon: ll }),
  setCameraAltitude: (alt) => set({ cameraAltitude: alt }),
  setHoveredRegion: (r) => set({ hoveredRegion: r }),
}))
```

- [ ] **Step 2: Commit**

```bash
git add aegis-web/src/stores/coverage.ts
git commit -m "feat: add coverage Zustand store with ECEF conversion"
```

---

### Task 6: useScenario integration

**Files:**
- Modify: `aegis-web/src/hooks/useScenario.ts`

This task wires the coverage store into the scenario loading flow.

**Reference files to read first:**
- `aegis-web/src/hooks/useScenario.ts` (full file)
- `aegis-web/src/stores/coverage.ts` for store API

- [ ] **Step 1: Add coverage store integration to loadScenario**

In `aegis-web/src/hooks/useScenario.ts`:

Add import at top:
```typescript
import { useCoverageStore } from '@/stores/coverage'
```

Inside `loadScenario`, after the `ui.setActiveScenario(name)` line (around line 44), add:

```typescript
// Coverage globe: enable overlay and fetch data
if (name === 'coverage_globe') {
  useCoverageStore.getState().setEnabled(true)
  useCoverageStore.getState().fetch()
} else {
  useCoverageStore.getState().setEnabled(false)
}
```

- [ ] **Step 2: Verify**

Run: `cd aegis-web && npm run dev`
Click "Coverage globe" card. Open browser devtools Network tab. Verify `GET /api/basestations/coverage` is called.

- [ ] **Step 3: Commit**

```bash
git add aegis-web/src/hooks/useScenario.ts
git commit -m "feat: wire coverage store into scenario loading"
```

---

### Task 7: CoverageGlobe scene component

**Files:**
- Create: `aegis-web/src/components/scene/CoverageGlobe.tsx`
- Modify: `aegis-web/src/components/scene/SceneRoot.tsx`

This is the main rendering component. It reads camera altitude each frame and renders the appropriate tier: region boundaries (tier 1), instanced cluster markers (tier 2), or site point cloud (tier 3).

**Reference files to read first:**
- `aegis-web/src/components/scene/Environment3DTiles.tsx` for ECEF coordinate patterns
- `aegis-web/src/stores/coverage.ts` for store shape
- `aegis-web/src/lib/geo.ts` for `latLonToECEF`, `WGS84_A`

- [ ] **Step 1: Create the CoverageGlobe component**

Create `aegis-web/src/components/scene/CoverageGlobe.tsx`:

```typescript
import { useRef, useMemo, useEffect } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import { Html, Line } from '@react-three/drei'
import * as THREE from 'three'
import { useCoverageStore } from '@/stores/coverage'
import { latLonToECEF, ecefToLatLon, WGS84_A } from '@/lib/geo'

const TIER1_ALTITUDE_M = 2_000_000
const TIER2_ALTITUDE_M = 200_000
const TRANSITION_ALTITUDE_M = 5_000

const COMPLETENESS_COLORS: Record<string, string> = {
  high: '#22c55e',
  medium: '#f59e0b',
  low: '#ef4444',
}

function completenessColor(c: number): string {
  if (c > 0.8) return COMPLETENESS_COLORS.high
  if (c > 0.4) return COMPLETENESS_COLORS.medium
  return COMPLETENESS_COLORS.low
}

/** Tier 1: region boundary rectangles and floating labels. */
function RegionBoundaries() {
  const regions = useCoverageStore(s => s.regions)

  return (
    <>
      {regions.map(r => {
        if (!r.bbox) return null
        const [minLon, maxLon, minLat, maxLat] = r.bbox
        const alt = 1000 // slightly above surface
        const corners = [
          latLonToECEF(minLat, minLon, alt),
          latLonToECEF(minLat, maxLon, alt),
          latLonToECEF(maxLat, maxLon, alt),
          latLonToECEF(maxLat, minLon, alt),
          latLonToECEF(minLat, minLon, alt), // close
        ]
        const points = corners.map(v => [v.x, v.y, v.z] as [number, number, number])
        const center = latLonToECEF(
          (minLat + maxLat) / 2,
          (minLon + maxLon) / 2,
          alt + 5000,
        )

        return (
          <group key={r.name}>
            <Line
              points={points}
              color={completenessColor(r.completeness)}
              lineWidth={2}
            />
            <Html position={[center.x, center.y, center.z]} center distanceFactor={1_000_000}>
              <div className="pointer-events-auto whitespace-nowrap rounded bg-zinc-900/90 px-2 py-1 text-xs text-white shadow-lg border border-zinc-700">
                <div className="font-medium">{r.label}</div>
                <div className="text-zinc-400">{r.count.toLocaleString()} antennas</div>
              </div>
            </Html>
          </group>
        )
      })}
    </>
  )
}

/** Tier 2: instanced cluster markers. */
function ClusterMarkers() {
  const clusters = useCoverageStore(s => s.clusters)
  const operatorNames = useCoverageStore(s => s.operatorNames)
  const meshRef = useRef<THREE.InstancedMesh>(null)

  const OPERATOR_COLORS: [number, number, number][] = useMemo(() => [
    [0.23, 0.51, 0.96], [0.96, 0.51, 0.11], [0.18, 0.76, 0.49],
    [0.66, 0.33, 0.83], [0.91, 0.30, 0.24], [0.10, 0.74, 0.81],
    [0.98, 0.75, 0.18], [0.55, 0.34, 0.16], [0.44, 0.50, 0.56],
    [0.84, 0.37, 0.65], [0.40, 0.65, 0.12], [0.70, 0.20, 0.36],
  ], [])

  useEffect(() => {
    const mesh = meshRef.current
    if (!mesh || clusters.length === 0) return

    const dummy = new THREE.Object3D()
    const color = new THREE.Color()
    const up = new THREE.Vector3()
    const quat = new THREE.Quaternion()
    const defaultUp = new THREE.Vector3(0, 0, 1)

    for (let i = 0; i < clusters.length; i++) {
      const c = clusters[i]
      const pos = latLonToECEF(c.lat, c.lon, 500)
      const scale = Math.max(1, Math.log2(c.count)) * 5000

      dummy.position.copy(pos)
      // Orient circle tangent to globe surface
      up.copy(pos).normalize()
      quat.setFromUnitVectors(defaultUp, up)
      dummy.quaternion.copy(quat)
      dummy.scale.set(scale, scale, 1)
      dummy.updateMatrix()
      mesh.setMatrixAt(i, dummy.matrix)

      const opIdx = operatorNames.indexOf(c.operator)
      const rgb = OPERATOR_COLORS[Math.max(0, opIdx) % OPERATOR_COLORS.length]
      color.setRGB(rgb[0], rgb[1], rgb[2])
      mesh.setColorAt(i, color)
    }

    mesh.instanceMatrix.needsUpdate = true
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true
  }, [clusters, operatorNames, OPERATOR_COLORS])

  if (clusters.length === 0) return null

  return (
    <instancedMesh ref={meshRef} args={[undefined, undefined, clusters.length]}>
      <circleGeometry args={[1, 16]} />
      <meshBasicMaterial transparent opacity={0.7} side={THREE.DoubleSide} />
    </instancedMesh>
  )
}

/** Tier 3: site point cloud. */
function SitePoints() {
  const positions = useCoverageStore(s => s.sitePositions)
  const colors = useCoverageStore(s => s.siteColors)

  if (!positions || !colors) return null

  return (
    <points>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" array={positions} count={positions.length / 3} itemSize={3} />
        <bufferAttribute attach="attributes-color" array={colors} count={colors.length / 3} itemSize={3} />
      </bufferGeometry>
      <pointsMaterial size={3000} sizeAttenuation vertexColors transparent opacity={0.8} />
    </points>
  )
}

/** Camera-controlled initial position for coverage globe. */
function CoverageCamera() {
  const { camera } = useThree()
  const initialized = useRef(false)

  useFrame(() => {
    if (initialized.current) return
    initialized.current = true
    // Position camera high above equator for full-Earth view
    const pos = latLonToECEF(20, 10, 20_000_000)
    camera.position.set(pos.x, pos.y, pos.z)
    camera.lookAt(0, 0, 0)
    camera.updateProjectionMatrix()
  })

  return null
}

export function CoverageGlobe() {
  const enabled = useCoverageStore(s => s.enabled)
  const loaded = useCoverageStore(s => s.loaded)
  const activeTier = useCoverageStore(s => s.activeTier)
  const { camera } = useThree()

  // Update active tier and camera lat/lon each frame
  useFrame(() => {
    if (!enabled) return
    const store = useCoverageStore.getState()
    const altitude = camera.position.length() - WGS84_A

    let tier: 1 | 2 | 3
    if (altitude > TIER1_ALTITUDE_M) tier = 1
    else if (altitude > TIER2_ALTITUDE_M) tier = 2
    else tier = 3
    if (tier !== store.activeTier) store.setActiveTier(tier)

    // Write camera altitude and lat/lon to store for HUD to read
    store.setCameraAltitude(altitude)
    if (altitude < TIER2_ALTITUDE_M) {
      const ll = ecefToLatLon(camera.position)
      store.setCameraLatLon(ll)
    }
  })

  if (!enabled || !loaded) return null

  return (
    <group>
      <CoverageCamera />
      {/* Region boundaries visible at tier 1 and 2 */}
      <group visible={activeTier <= 2}>
        <RegionBoundaries />
      </group>
      <group visible={activeTier === 2}>
        <ClusterMarkers />
      </group>
      <group visible={activeTier === 3}>
        <SitePoints />
      </group>
    </group>
  )
}
```

- [ ] **Step 2: Mount in SceneRoot**

In `aegis-web/src/components/scene/SceneRoot.tsx`:

Add import:
```typescript
import { CoverageGlobe } from './CoverageGlobe'
```

Add `<CoverageGlobe />` inside `sceneContent`, right after `<BaseStationMarkers />` (around line 392):
```typescript
<BaseStationMarkers />
<CoverageGlobe />
```

- [ ] **Step 3: Verify visually**

Run: `cd aegis-web && npm run dev`
Click "Coverage globe" card. Verify:
- Globe renders with Google 3D Tiles
- Region boundaries appear as colored rectangles
- Zooming in transitions through tiers (check console for tier changes)
- Site dots appear at close zoom

- [ ] **Step 4: Commit**

```bash
git add aegis-web/src/components/scene/CoverageGlobe.tsx aegis-web/src/components/scene/SceneRoot.tsx
git commit -m "feat: add CoverageGlobe component with 3-tier LOD rendering"
```

---

### Task 8: Coverage HUD overlay

**Files:**
- Create: `aegis-web/src/components/hud/CoverageHud.tsx`
- Modify: `aegis-web/src/components/layout/HudOverlay.tsx`

This task adds the floating HUD with the completeness legend, "Set up scene here" button, and "Back to globe" button.

**Reference files to read first:**
- `aegis-web/src/components/layout/HudOverlay.tsx` for the HUD composition pattern
- `aegis-web/src/stores/coverage.ts` for store API
- `aegis-web/src/api/basestations.ts` for `loadBasestations`
- `aegis-web/src/stores/environment.ts` for `setLocation`
- `aegis-web/src/stores/ui.ts` for `activeScenario`

- [ ] **Step 1: Create the CoverageHud component**

Create `aegis-web/src/components/hud/CoverageHud.tsx`:

```typescript
import { useCoverageStore } from '@/stores/coverage'
import { useUIStore } from '@/stores/ui'
import { useEnvironmentStore } from '@/stores/environment'
import { useBaseStationsStore } from '@/stores/basestations'
import { loadBasestations } from '@/api/basestations'
import { Globe, MapPin, ArrowLeft } from 'lucide-react'

const TRANSITION_ALTITUDE_M = 5_000

function CoverageHudInner() {
  const enabled = useCoverageStore(s => s.enabled)
  const activeScenario = useUIStore(s => s.activeScenario)
  const cameraAltitude = useCoverageStore(s => s.cameraAltitude)
  const cameraLatLon = useCoverageStore(s => s.cameraLatLon)
  const regions = useCoverageStore(s => s.regions)

  const isCoverageScenario = activeScenario === 'coverage_globe'
  if (!isCoverageScenario) return null

  const showTransitionButton = enabled && cameraAltitude < TRANSITION_ALTITUDE_M && cameraLatLon

  const handleSetupScene = () => {
    // Read camera lat/lon from coverage store (written by CoverageGlobe each frame)
    const ll = useCoverageStore.getState().cameraLatLon
    if (!ll) return

    useCoverageStore.getState().setEnabled(false)
    // Update environment store location for the local scene
    useEnvironmentStore.getState().setLocation(ll.lat, ll.lon)
    // Load base stations at current camera location
    loadBasestations({ lat: ll.lat, lon: ll.lon, radius_m: 500 }).then(resp => {
      useBaseStationsStore.getState().setBasestations(resp.basestations, ll)
    })
  }

  const handleBackToGlobe = () => {
    useCoverageStore.getState().setEnabled(true)
    useBaseStationsStore.getState().clear()
  }

  return (
    <div className="absolute bottom-16 left-4 pointer-events-auto flex flex-col gap-2 z-20">
      {enabled && (
        <div className="rounded-lg bg-zinc-900/90 border border-zinc-700 p-3 text-xs text-white shadow-lg">
          <div className="flex items-center gap-2 mb-2 font-medium">
            <Globe size={14} />
            Coverage
          </div>
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: '#22c55e' }} />
              <span className="text-zinc-300">Rich data (&gt;80%)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: '#f59e0b' }} />
              <span className="text-zinc-300">Partial (40-80%)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: '#ef4444' }} />
              <span className="text-zinc-300">Location only (&lt;40%)</span>
            </div>
          </div>
          <div className="mt-2 text-zinc-400">
            {regions.length} regions, {regions.reduce((s, r) => s + r.count, 0).toLocaleString()} antennas
          </div>
        </div>
      )}

      {showTransitionButton && (
        <button
          onClick={handleSetupScene}
          className="flex items-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-500 px-3 py-2 text-sm text-white font-medium shadow-lg transition-colors"
        >
          <MapPin size={14} />
          Set up scene here
        </button>
      )}

      {!enabled && isCoverageScenario && (
        <button
          onClick={handleBackToGlobe}
          className="flex items-center gap-2 rounded-lg bg-zinc-700 hover:bg-zinc-600 px-3 py-2 text-sm text-white font-medium shadow-lg transition-colors"
        >
          <ArrowLeft size={14} />
          Back to globe
        </button>
      )}
    </div>
  )
}

export function CoverageHud() {
  const isCoverageScenario = useUIStore(s => s.activeScenario) === 'coverage_globe'
  if (!isCoverageScenario) return null
  return <CoverageHudInner />
}
```

The "Set up scene here" button reads camera lat/lon from the coverage store, which is written by the `CoverageGlobe` scene component each frame via `ecefToLatLon`. This avoids using R3F hooks (`useThree`) in the HUD, which lives outside the Canvas tree. The button only appears when camera altitude is below 5 km (the `TRANSITION_ALTITUDE_M` threshold), not at the full tier 3 range of 200 km.

- [ ] **Step 2: Mount in HudOverlay**

In `aegis-web/src/components/layout/HudOverlay.tsx`:

Add import:
```typescript
import { CoverageHud } from '@/components/hud/CoverageHud'
```

Add `<CoverageHud />` inside the outer div, after `<AntennaHint />`:
```typescript
<AntennaHint />
<CoverageHud />
```

- [ ] **Step 3: Verify**

Run: `cd aegis-web && npm run dev`
Click "Coverage globe". Verify:
- Legend appears in bottom-left with color coding
- "Set up scene here" button appears when zoomed in to tier 3
- Clicking it hides the overlay and shows "Back to globe" button

- [ ] **Step 4: Commit**

```bash
git add aegis-web/src/components/hud/CoverageHud.tsx aegis-web/src/components/layout/HudOverlay.tsx
git commit -m "feat: add coverage HUD with legend and transition buttons"
```

---

### Task 9: Integration testing and polish

**Files:**
- Multiple files may need adjustments

This task is for end-to-end testing and fixing any integration issues discovered during the visual smoke test.

- [ ] **Step 1: Run backend tests**

Run: `cd /home/user/aegis && .venv/bin/python -m pytest tests/test_coverage_endpoint.py -v`
Expected: All PASS

- [ ] **Step 2: Run lint**

Run: `cd /home/user/aegis && .venv/bin/python -m ruff check src/aegis/viewer/routes/coverage.py tests/test_coverage_endpoint.py`
Fix any issues.

- [ ] **Step 3: Run frontend build**

Run: `cd aegis-web && npm run build`
Expected: Build succeeds with no TypeScript errors

- [ ] **Step 4: Full visual smoke test**

Run: `cd aegis-web && npm run dev` (and Flask backend in another terminal)

Test the full flow:
1. Welcome screen shows 4 cards including "Coverage globe"
2. Click "Coverage globe" - globe appears, coverage data loads
3. Zoom out - region boundaries with labels visible
4. Zoom in to Europe - cluster markers appear, sized by count
5. Zoom into Brussels - individual site dots appear
6. "Set up scene here" button appears at close zoom
7. Click it - coverage overlay disappears, base stations load
8. "Back to globe" button appears
9. Click it - returns to globe with coverage overlay
10. Try other scenarios (Open ground, Urban Ghent) - coverage overlay does not appear

- [ ] **Step 5: Fix any issues found**

Address any rendering glitches, z-fighting, label sizing, tier threshold adjustments, or button positioning issues.

- [ ] **Step 6: Final commit**

Stage specific files that were modified during polish (do not use `git add -A`):

```bash
git add <specific files that were fixed>
git commit -m "fix: integration polish for coverage globe"
```

- [ ] **Step 7: Push and create PR**

```bash
git push -u origin feature/coverage-globe
gh pr create --title "Add coverage globe for global base station overview" \
  --body "## Summary
- Adds a 4th scenario card: Coverage Globe
- Backend endpoint pre-computes 3 tiers from merged Parquet files
- 3-tier LOD rendering on the 3D tiles globe (regions, clusters, sites)
- Transition flow to enter local dosimetry scene from globe

## Test plan
- [ ] Backend: pytest tests/test_coverage_endpoint.py passes
- [ ] Frontend: npm run build succeeds
- [ ] Visual: all 4 scenario cards visible on welcome screen
- [ ] Visual: zoom through tiers 1-2-3 without glitches
- [ ] Transition: Set up scene here -> base stations load
- [ ] Transition: Back to globe -> returns to coverage view
- [ ] Other scenarios still work independently" \
  --base master
```
