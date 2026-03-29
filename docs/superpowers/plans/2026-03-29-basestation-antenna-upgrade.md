# Base station antenna upgrade implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace sphere markers with classified panel antennas, add geocoded location input, and integrate MRT beamforming for 5G mMIMO base stations.

**Architecture:** Three-layer approach. A Python classifier (`classify.py`) assigns archetypes and infers element grids during loading. The viewer routes expose classification data and a new MIMO compute endpoint. A shared React `PanelAntenna` component renders oriented panel models, reused by both `BaseStationMarkers` and `AntennaArray`.

**Tech Stack:** Python (geopy, scipy, numpy), TypeScript/React (Three.js, R3F, Zustand), Flask REST API

**Spec:** `docs/superpowers/specs/2026-03-29-basestation-antenna-upgrade-design.md`

---

## File structure

| File | Action | Responsibility |
|---|---|---|
| `src/aegis/basestation/classify.py` | Create | Archetype classifier + element grid inference |
| `src/aegis/basestation/adapter.py` | No change | Classification happens in routes `_bs_summary()`, not adapter |
| `src/aegis/viewer/config.py` | Modify | Add basestations block to DEFAULTS dict |
| `src/aegis/viewer/routes/basestations.py` | Modify | Geocoding, archetype in response, MIMO compute route |
| `configs/default.json` | Modify | Add `basestations` config block |
| `pyproject.toml` | Modify | Add geopy to `[viewer]` extra |
| `aegis-web/src/utils/classifyAntenna.ts` | Create | TypeScript mirror of Python classifier |
| `aegis-web/src/api/basestations.ts` | Modify | Add archetype fields to types, location-based loading, MIMO compute |
| `aegis-web/src/stores/basestations.ts` | Modify | Add selected antenna state, archetype info |
| `aegis-web/src/components/scene/PanelAntenna.tsx` | Create | Shared panel antenna 3D component |
| `aegis-web/src/components/scene/BaseStationMarkers.tsx` | Rewrite | Use PanelAntenna, site grouping, click selection |
| `aegis-web/src/components/scene/AntennaArray.tsx` | Modify | Extract panel rendering to PanelAntenna |
| `aegis-web/src/components/panels/BaseStationsPanel.tsx` | Modify | Text location input, MIMO compute for selected |
| `aegis-web/src/components/panels/ScenePanel.tsx` | Modify | "Also load base stations" checkbox |
| `tests/test_classify_antenna.py` | Create | Classifier unit tests |

---

## Task 1: Python archetype classifier

**Files:**
- Create: `src/aegis/basestation/classify.py`
- Create: `tests/test_classify_antenna.py`

- [ ] **Step 1: Write failing tests for classifier**

```python
# tests/test_classify_antenna.py
"""Tests for base station archetype classification."""
import pytest
from aegis.basestation.classify import classify_antenna, infer_element_grid


class TestClassifyAntenna:
    """Archetype assignment from antenna metadata."""

    def test_mmimo_high_gain_5g(self):
        result = classify_antenna(
            gain_dbi=24.8, technology="5G", freq_mhz=3750.0,
            h_bw=126, v_bw=34,
        )
        assert result == "mmimo"

    def test_mmimo_mixed_4g5g(self):
        result = classify_antenna(
            gain_dbi=22.0, technology="4G/5G", freq_mhz=3750.0,
            h_bw=100, v_bw=20,
        )
        assert result == "mmimo"

    def test_sector_typical_4g(self):
        result = classify_antenna(
            gain_dbi=16.8, technology="4G", freq_mhz=1800.0,
            h_bw=65, v_bw=10,
        )
        assert result == "sector"

    def test_sector_high_gain_non_5g(self):
        """High gain but not 5G should NOT be mmimo."""
        result = classify_antenna(
            gain_dbi=22.0, technology="4G", freq_mhz=2600.0,
            h_bw=65, v_bw=7,
        )
        assert result == "sector"

    def test_small_cell_low_gain(self):
        result = classify_antenna(
            gain_dbi=2.1, technology="2G", freq_mhz=800.0,
            h_bw=168, v_bw=100,
        )
        assert result == "small_cell"

    def test_null_technology_not_mmimo(self):
        """Unknown tech should never classify as mmimo."""
        result = classify_antenna(
            gain_dbi=24.0, technology=None, freq_mhz=3750.0,
            h_bw=126, v_bw=34,
        )
        assert result != "mmimo"

    def test_empty_technology_not_mmimo(self):
        result = classify_antenna(
            gain_dbi=24.0, technology="", freq_mhz=3750.0,
            h_bw=126, v_bw=34,
        )
        assert result != "mmimo"


class TestInferElementGrid:
    """Element count inference and grid snapping."""

    def test_mmimo_snaps_to_standard_grid(self):
        n_h, n_v = infer_element_grid(
            archetype="mmimo", gain_dbi=24.8,
            element_gain_dbi=5.0,
        )
        assert n_h * n_v in (64, 128)
        assert n_v >= n_h  # tall panels

    def test_sector_dual_column(self):
        n_h, n_v = infer_element_grid(
            archetype="sector", gain_dbi=16.0,
            element_gain_dbi=5.0,
        )
        assert n_h in (1, 2)
        assert n_v >= 2

    def test_small_cell_minimal(self):
        n_h, n_v = infer_element_grid(
            archetype="small_cell", gain_dbi=2.1,
            element_gain_dbi=5.0,
        )
        assert n_h == 1
        assert n_v == 1

    def test_small_cell_moderate_gain(self):
        n_h, n_v = infer_element_grid(
            archetype="small_cell", gain_dbi=8.0,
            element_gain_dbi=5.0,
        )
        assert n_h * n_v in (1, 4)

    def test_custom_element_gain(self):
        n_h_5, n_v_5 = infer_element_grid(
            archetype="mmimo", gain_dbi=24.8,
            element_gain_dbi=5.0,
        )
        n_h_7, n_v_7 = infer_element_grid(
            archetype="mmimo", gain_dbi=24.8,
            element_gain_dbi=7.0,
        )
        # Higher element gain means fewer inferred elements
        assert n_h_7 * n_v_7 <= n_h_5 * n_v_5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_classify_antenna.py -v -n0`
Expected: ImportError, classify.py does not exist

- [ ] **Step 3: Implement the classifier**

```python
# src/aegis/basestation/classify.py
"""Archetype classification and element grid inference for base stations.

Three archetypes:
- mmimo: high-gain 5G panels with digital beamforming (e.g. Ericsson AIR 4518)
- sector: conventional sector panels with fixed patterns
- small_cell: low-gain omnidirectional or small box antennas
"""
from __future__ import annotations

import math

# Default standard grids [n_h, n_v] per archetype. Configurable via config.
DEFAULT_GRIDS: dict[str, list[tuple[int, int]]] = {
    "mmimo": [(4, 4), (4, 8), (8, 8), (8, 16)],
    "sector": [(1, 2), (1, 4), (2, 4), (2, 8)],
    "small_cell": [(1, 1), (2, 2)],
}

DEFAULT_ELEMENT_GAIN_DBI = 5.0
DEFAULT_MMIMO_THRESHOLD = 20.0
DEFAULT_SMALL_CELL_THRESHOLD = 10.0


def classify_antenna(
    gain_dbi: float,
    technology: str | None,
    freq_mhz: float = 0.0,
    h_bw: float = 0.0,
    v_bw: float = 0.0,
    *,
    mmimo_threshold: float = DEFAULT_MMIMO_THRESHOLD,
    small_cell_threshold: float = DEFAULT_SMALL_CELL_THRESHOLD,
) -> str:
    """Classify a base station antenna into an archetype.

    Returns one of: "mmimo", "sector", "small_cell".
    """
    tech = (technology or "").upper()
    is_5g = "5G" in tech

    if gain_dbi >= mmimo_threshold and is_5g:
        return "mmimo"
    if gain_dbi < small_cell_threshold:
        return "small_cell"
    return "sector"


def infer_element_grid(
    archetype: str,
    gain_dbi: float,
    element_gain_dbi: float = DEFAULT_ELEMENT_GAIN_DBI,
    *,
    standard_grids: dict[str, list[tuple[int, int]]] | None = None,
) -> tuple[int, int]:
    """Infer antenna element grid (n_h, n_v) from gain and archetype.

    Computes raw element count from array gain, then snaps to the nearest
    standard grid for the archetype. For mmimo, n_v >= n_h (tall panels).
    For sector, n_h is 1 or 2 (cross-pol columns).
    """
    grids = standard_grids or DEFAULT_GRIDS
    candidates = grids.get(archetype, [(1, 1)])

    array_gain_db = gain_dbi - element_gain_dbi
    if array_gain_db <= 0:
        return candidates[0]

    n_raw = 10 ** (array_gain_db / 10)

    best = candidates[0]
    best_dist = float("inf")
    for grid in candidates:
        n_total = grid[0] * grid[1]
        dist = abs(n_total - n_raw)
        if dist < best_dist:
            best_dist = dist
            best = grid
    return best


def compute_panel_dimensions(
    n_h: int,
    n_v: int,
    freq_mhz: float,
    *,
    margin: float = 0.02,
    default_freq_mhz: float = 2100.0,
) -> tuple[float, float]:
    """Compute physical panel dimensions from element grid and frequency.

    Uses half-wavelength spacing. Returns (width_m, height_m).
    """
    freq = freq_mhz if freq_mhz > 0 else default_freq_mhz
    c = 299_792_458.0
    wavelength = c / (freq * 1e6)
    spacing = wavelength / 2

    width = max((n_h - 1) * spacing + margin, margin * 2)
    height = max((n_v - 1) * spacing + margin, margin * 2)
    return width, height


def classify_basestation(
    gain_dbi: float,
    technology: str | None,
    freq_mhz: float = 0.0,
    h_bw: float = 0.0,
    v_bw: float = 0.0,
    *,
    mmimo_threshold: float = DEFAULT_MMIMO_THRESHOLD,
    small_cell_threshold: float = DEFAULT_SMALL_CELL_THRESHOLD,
    element_gain_dbi: float = DEFAULT_ELEMENT_GAIN_DBI,
    standard_grids: dict[str, list[tuple[int, int]]] | None = None,
    margin: float = 0.02,
    default_freq_mhz: float = 2100.0,
) -> dict:
    """Full classification: archetype + grid + panel dimensions.

    Returns dict with keys: archetype, n_h, n_v, panel_width_m, panel_height_m.
    """
    archetype = classify_antenna(
        gain_dbi, technology, freq_mhz, h_bw, v_bw,
        mmimo_threshold=mmimo_threshold,
        small_cell_threshold=small_cell_threshold,
    )
    n_h, n_v = infer_element_grid(
        archetype, gain_dbi, element_gain_dbi,
        standard_grids=standard_grids,
    )
    width, height = compute_panel_dimensions(
        n_h, n_v, freq_mhz,
        margin=margin, default_freq_mhz=default_freq_mhz,
    )
    return {
        "archetype": archetype,
        "n_h": n_h,
        "n_v": n_v,
        "panel_width_m": round(width, 4),
        "panel_height_m": round(height, 4),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_classify_antenna.py -v -n0`
Expected: All 12 tests PASS

- [ ] **Step 5: Lint**

Run: `python -m ruff check src/aegis/basestation/classify.py tests/test_classify_antenna.py && python -m ruff format --check src/aegis/basestation/classify.py tests/test_classify_antenna.py`

- [ ] **Step 6: Commit**

```bash
git add src/aegis/basestation/classify.py tests/test_classify_antenna.py
git commit -m "Add base station archetype classifier with element grid inference"
```

---

## Task 2: Integrate classifier into Python adapter and routes

**Files:**
- Modify: `src/aegis/basestation/adapter.py` (lines 35-99 for loading, add classification)
- Modify: `src/aegis/viewer/routes/basestations.py` (lines 237-255 for `_bs_summary`)
- Modify: `pyproject.toml` (add geopy to viewer extra)

- [ ] **Step 1: Add geopy dependency**

In `pyproject.toml`, find the `viewer` optional dependency list and add `geopy`:

```toml
# Find the line: viewer = [
# Add geopy to the list:
viewer = [
    "flask>=3.0",
    # ... existing deps ...
    "geopy>=2.4",
]
```

Run: `pip install -e ".[viewer]"` to install.

- [ ] **Step 2: Add classification to `_bs_summary()` in routes**

In `src/aegis/viewer/routes/basestations.py`, import the classifier at the top:

```python
from aegis.basestation.classify import classify_basestation
```

Modify `_bs_summary()` (currently lines 237-255) to add classification fields:

```python
def _bs_summary(bs) -> dict:
    """Serialize a BaseStation to a JSON-safe dict with classification."""
    classification = classify_basestation(
        gain_dbi=bs.gain_dbi,
        technology=bs.technology,
        freq_mhz=bs.freq_mhz,
        h_bw=bs.horizontal_beamwidth_deg or 0,
        v_bw=bs.vertical_beamwidth_deg or 0,
    )
    return {
        "site_code": bs.site_code,
        "antenna_label": bs.antenna_label,
        "operator": bs.operator,
        "technology": bs.technology,
        "latitude": bs.latitude,
        "longitude": bs.longitude,
        "height_m": bs.height_m,
        "eirp_dbm": bs.eirp_dbm,
        "gain_dbi": bs.gain_dbi,
        "freq_mhz": bs.freq_mhz,
        "azimuth_deg": bs.azimuth_deg,
        "total_tilt_deg": bs.total_tilt_deg,
        "has_pattern": bs.pattern is not None,
        "horizontal_beamwidth_deg": bs.horizontal_beamwidth_deg,
        "vertical_beamwidth_deg": bs.vertical_beamwidth_deg,
        **classification,
    }
```

- [ ] **Step 3: Add geocoding to the load route**

Add a `geocode_location()` function near the top of `basestations.py`:

```python
import re

def geocode_location(location: str) -> tuple[float, float]:
    """Geocode a location string to (latitude, longitude).

    Tries parsing as "lat, lon" first, falls back to geopy Nominatim.
    Raises ValueError on failure.
    """
    # Try raw coordinate parsing: "50.85, 4.35" or "50.85 4.35"
    match = re.match(
        r"^\s*(-?\d+\.?\d*)\s*[,\s]\s*(-?\d+\.?\d*)\s*$", location,
    )
    if match:
        return float(match.group(1)), float(match.group(2))

    from geopy.geocoders import Nominatim
    from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

    geolocator = Nominatim(user_agent="aegis-viewer", timeout=10)
    try:
        result = geolocator.geocode(location)
    except (GeocoderTimedOut, GeocoderUnavailable) as e:
        raise ValueError(f"Geocoding service unavailable: {e}") from e

    if result is None:
        raise ValueError(f"Could not geocode location: {location!r}")
    return result.latitude, result.longitude
```

Modify the `/api/basestations/load` route to accept `location`:

In the POST handler (around line 23), after extracting the JSON body, add location handling before the existing bbox/lat/lon logic:

```python
data = request.get_json(force=True)
location_str = data.get("location")

if location_str and not data.get("bbox") and not data.get("lat"):
    try:
        lat, lon = geocode_location(location_str)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    data["lat"] = lat
    data["lon"] = lon
```

The rest of the existing lat/lon -> bbox conversion logic stays unchanged.

- [ ] **Step 4: Write geocoding tests**

Add to `tests/test_classify_antenna.py`:

```python
from unittest.mock import patch, MagicMock
from aegis.viewer.routes.basestations import geocode_location


class TestGeocodeLocation:
    def test_raw_coordinates_comma(self):
        lat, lon = geocode_location("50.85, 4.35")
        assert abs(lat - 50.85) < 0.001
        assert abs(lon - 4.35) < 0.001

    def test_raw_coordinates_space(self):
        lat, lon = geocode_location("50.85 4.35")
        assert abs(lat - 50.85) < 0.001
        assert abs(lon - 4.35) < 0.001

    def test_negative_coordinates(self):
        lat, lon = geocode_location("-33.87, 151.21")
        assert abs(lat - (-33.87)) < 0.001

    def test_nominatim_fallback(self):
        mock_location = MagicMock()
        mock_location.latitude = 50.85
        mock_location.longitude = 4.35
        with patch("aegis.viewer.routes.basestations.Nominatim") as mock_nom:
            mock_nom.return_value.geocode.return_value = mock_location
            lat, lon = geocode_location("Brussels, Belgium")
            assert abs(lat - 50.85) < 0.01

    def test_unknown_location_raises(self):
        with patch("aegis.viewer.routes.basestations.Nominatim") as mock_nom:
            mock_nom.return_value.geocode.return_value = None
            import pytest
            with pytest.raises(ValueError, match="Could not geocode"):
                geocode_location("xyznonexistent12345")
```

Note: The geocode_location function needs to be importable. Move the `Nominatim` import to module-level with a lazy guard, or adjust the mock path to match the actual import location.

- [ ] **Step 5: Run the test suite**

Run: `python -m pytest tests/test_classify_antenna.py -v -n0`
Expected: All tests pass

- [ ] **Step 6: Lint**

Run: `python -m ruff check src/aegis/basestation/ src/aegis/viewer/routes/basestations.py tests/test_classify_antenna.py && python -m ruff format --check src/aegis/basestation/ src/aegis/viewer/routes/basestations.py tests/test_classify_antenna.py`

- [ ] **Step 7: Regenerate uv.lock**

Run: `uv lock` (to pick up the new geopy dependency)

- [ ] **Step 8: Commit**

```bash
git add src/aegis/viewer/routes/basestations.py pyproject.toml uv.lock tests/test_classify_antenna.py
git commit -m "Integrate classifier into base station routes, add geocoding via geopy"
```

---

## Task 3: Add basestations config block to default.json

**Files:**
- Modify: `configs/default.json` (add after existing sections, before closing `}`)

- [ ] **Step 1: Add the basestations config block**

Add the following JSON block to `configs/default.json`. Insert it as a new top-level key after the last existing section (around line 498):

```json
  "basestations": {
    "classification": {
      "element_gain_dbi": 5.0,
      "mmimo_gain_threshold": 20.0,
      "small_cell_gain_threshold": 10.0,
      "default_freq_mhz": 2100,
      "standard_grids": {
        "mmimo": [[4,4],[4,8],[8,8],[8,16]],
        "sector": [[1,2],[1,4],[2,4],[2,8]],
        "small_cell": [[1,1],[2,2]]
      }
    },
    "panel": {
      "depth": 0.05,
      "pole_radius": 0.04,
      "element_dot_radius": 0.008,
      "show_elements": true,
      "margin": 0.02
    },
    "mmimo": {
      "default_panel_width": 0.7,
      "default_panel_height": 0.4,
      "show_pattern": true,
      "ico_detail": 6,
      "pattern_opacity": 0.85,
      "dynamic_range_db": 36
    },
    "sector": {
      "default_panel_width": 0.3,
      "default_panel_height": 1.0,
      "show_pattern": false
    },
    "small_cell": {
      "default_panel_width": 0.15,
      "default_panel_height": 0.15,
      "show_pattern": false
    },
    "auto_load_with_scene": false,
    "default_radius_m": 500,
    "max_distance_m": 2000,
    "site_vertical_gap": 0.1
  }
```

- [ ] **Step 2: Validate JSON**

Run: `python -c "import json; json.load(open('configs/default.json'))"`
Expected: No error

- [ ] **Step 3: Commit**

```bash
git add configs/default.json
git commit -m "Add basestations config block with classification thresholds and panel defaults"
```

---

## Task 3b: Add basestations to config.py DEFAULTS

**Files:**
- Modify: `src/aegis/viewer/config.py` (add basestations block to DEFAULTS dict, before the closing `}` around line 444)

The viewer's `config.py` DEFAULTS dict is the source of truth for all default values. `configs/default.json` is generated from it. Both must stay in sync.

- [ ] **Step 1: Add basestations block to DEFAULTS**

In `src/aegis/viewer/config.py`, add the basestations dict as a new key in the DEFAULTS dict, before the `"default_scenario"` key (around line 434):

```python
    "basestations": {
        "classification": {
            "element_gain_dbi": 5.0,
            "mmimo_gain_threshold": 20.0,
            "small_cell_gain_threshold": 10.0,
            "default_freq_mhz": 2100,
            "standard_grids": {
                "mmimo": [[4, 4], [4, 8], [8, 8], [8, 16]],
                "sector": [[1, 2], [1, 4], [2, 4], [2, 8]],
                "small_cell": [[1, 1], [2, 2]],
            },
        },
        "panel": {
            "depth": 0.05,
            "pole_radius": 0.04,
            "element_dot_radius": 0.008,
            "show_elements": True,
            "margin": 0.02,
        },
        "mmimo": {
            "default_panel_width": 0.7,
            "default_panel_height": 0.4,
            "show_pattern": True,
            "ico_detail": 6,
            "pattern_opacity": 0.85,
            "dynamic_range_db": 36,
        },
        "sector": {
            "default_panel_width": 0.3,
            "default_panel_height": 1.0,
            "show_pattern": False,
        },
        "small_cell": {
            "default_panel_width": 0.15,
            "default_panel_height": 0.15,
            "show_pattern": False,
        },
        "auto_load_with_scene": False,
        "default_radius_m": 500,
        "max_distance_m": 2000,
        "site_vertical_gap": 0.1,
    },
```

- [ ] **Step 2: Verify config loads**

Run: `python -c "from aegis.viewer.config import DEFAULTS; assert 'basestations' in DEFAULTS; print('OK')"`

- [ ] **Step 3: Commit**

```bash
git add src/aegis/viewer/config.py
git commit -m "Add basestations defaults to viewer config.py DEFAULTS"
```

---

## Task 4: TypeScript classifier utility

**Files:**
- Create: `aegis-web/src/utils/classifyAntenna.ts`

- [ ] **Step 1: Create the TypeScript classifier**

This mirrors the Python classifier exactly. Both must produce the same results.

```typescript
// aegis-web/src/utils/classifyAntenna.ts

export type Archetype = 'mmimo' | 'sector' | 'small_cell'

export interface ClassificationConfig {
  element_gain_dbi: number
  mmimo_gain_threshold: number
  small_cell_gain_threshold: number
  standard_grids: Record<Archetype, [number, number][]>
  default_freq_mhz: number
}

export const DEFAULT_CLASSIFICATION_CONFIG: ClassificationConfig = {
  element_gain_dbi: 5.0,
  mmimo_gain_threshold: 20.0,
  small_cell_gain_threshold: 10.0,
  standard_grids: {
    mmimo: [[4, 4], [4, 8], [8, 8], [8, 16]],
    sector: [[1, 2], [1, 4], [2, 4], [2, 8]],
    small_cell: [[1, 1], [2, 2]],
  },
  default_freq_mhz: 2100,
}

export function classifyAntenna(
  gainDbi: number,
  technology: string | null | undefined,
  config: ClassificationConfig = DEFAULT_CLASSIFICATION_CONFIG,
): Archetype {
  const tech = (technology ?? '').toUpperCase()
  const is5G = tech.includes('5G')

  if (gainDbi >= config.mmimo_gain_threshold && is5G) return 'mmimo'
  if (gainDbi < config.small_cell_gain_threshold) return 'small_cell'
  return 'sector'
}

export function inferElementGrid(
  archetype: Archetype,
  gainDbi: number,
  config: ClassificationConfig = DEFAULT_CLASSIFICATION_CONFIG,
): [number, number] {
  const candidates = config.standard_grids[archetype] ?? [[1, 1]]
  const arrayGainDb = gainDbi - config.element_gain_dbi
  if (arrayGainDb <= 0) return candidates[0]

  const nRaw = 10 ** (arrayGainDb / 10)

  let best = candidates[0]
  let bestDist = Infinity
  for (const grid of candidates) {
    const nTotal = grid[0] * grid[1]
    const dist = Math.abs(nTotal - nRaw)
    if (dist < bestDist) {
      bestDist = dist
      best = grid
    }
  }
  return best
}

export function computePanelDimensions(
  nH: number,
  nV: number,
  freqMhz: number,
  margin = 0.02,
  defaultFreqMhz = 2100,
): { width: number; height: number } {
  const freq = freqMhz > 0 ? freqMhz : defaultFreqMhz
  const c = 299_792_458
  const wavelength = c / (freq * 1e6)
  const spacing = wavelength / 2

  const width = Math.max((nH - 1) * spacing + margin, margin * 2)
  const height = Math.max((nV - 1) * spacing + margin, margin * 2)
  return { width, height }
}
```

- [ ] **Step 2: Verify it compiles**

Run: `cd aegis-web && npx tsc --noEmit src/utils/classifyAntenna.ts 2>&1 || echo "Check for errors"`

- [ ] **Step 3: Commit**

```bash
git add aegis-web/src/utils/classifyAntenna.ts
git commit -m "Add TypeScript antenna classifier mirroring Python classify.py"
```

---

## Task 5: Update TypeScript types and API client

**Files:**
- Modify: `aegis-web/src/api/basestations.ts` (add archetype fields, location loading, MIMO compute)

- [ ] **Step 1: Update BaseStationData interface and API functions**

Replace the contents of `aegis-web/src/api/basestations.ts`:

```typescript
import { postJson } from './client'
import type { DosimetryStats } from './types'
import type { Archetype } from '@/utils/classifyAntenna'

export interface BaseStationData {
  site_code: string
  antenna_label: string
  operator: string
  technology: string
  latitude: number
  longitude: number
  height_m: number
  eirp_dbm: number
  gain_dbi: number
  freq_mhz: number
  azimuth_deg: number
  total_tilt_deg: number
  has_pattern: boolean
  horizontal_beamwidth_deg: number
  vertical_beamwidth_deg: number
  // Classification fields from backend
  archetype: Archetype
  n_h: number
  n_v: number
  panel_width_m: number
  panel_height_m: number
}

interface LoadResponse {
  count: number
  basestations: BaseStationData[]
}

interface LoadParams {
  location?: string
  lat?: number
  lon?: number
  radius_m?: number
  operator?: string
  technology?: string
}

export async function loadBasestations(params: LoadParams): Promise<LoadResponse> {
  return postJson<LoadResponse>('/api/basestations/load', params)
}

export async function listBasestations(): Promise<LoadResponse> {
  const res = await fetch('/api/basestations/list')
  if (!res.ok) throw new Error(`GET /api/basestations/list failed: ${res.status} ${res.statusText}`)
  return res.json() as Promise<LoadResponse>
}

interface ComputeParams {
  indices?: number[]
  mode?: string
  body_offset?: [number, number, number]
  body_rotation_y?: number
  quantities?: string[]
  skin_model?: string
  freq_hz?: number
  use_beamforming?: boolean | 'auto'
}

export interface ComputeResult {
  sab: Float32Array
  stats: DosimetryStats
  arrays: Record<string, Float32Array>
}

export async function computeBasestations(
  params: ComputeParams,
  signal?: AbortSignal,
): Promise<ComputeResult> {
  const res = await fetch('/api/basestations/compute', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
    signal,
  })
  if (!res.ok) throw new Error(`POST /api/basestations/compute failed: ${res.status} ${res.statusText}`)

  const statsHeader = res.headers.get('X-Stats')
  if (!statsHeader) throw new Error('POST /api/basestations/compute: missing X-Stats header')
  const stats: DosimetryStats = JSON.parse(statsHeader)

  const buffer = await res.arrayBuffer()

  const arrays: Record<string, Float32Array> = {}
  if (stats.arrays && stats.arrays.length > 0) {
    for (const meta of stats.arrays) {
      const byteOffset = meta.offset
      const byteLength = meta.length * 4
      arrays[meta.key] = new Float32Array(buffer.slice(byteOffset, byteOffset + byteLength))
    }
  } else {
    arrays['sab'] = new Float32Array(buffer)
  }

  return { sab: arrays['sab'] ?? new Float32Array(buffer), stats, arrays }
}
```

- [ ] **Step 2: Verify it compiles**

Run: `cd aegis-web && npx tsc --noEmit`

- [ ] **Step 3: Commit**

```bash
git add aegis-web/src/api/basestations.ts
git commit -m "Add archetype fields and location param to base station API types"
```

---

## Task 6: Update Zustand store with selection state

**Files:**
- Modify: `aegis-web/src/stores/basestations.ts`

- [ ] **Step 1: Add selected antenna state to the store**

Add to the `BaseStationsState` interface (around line 4):

```typescript
selectedIndex: number | null
selectAntenna: (index: number | null) => void
```

Add to the initial state in `create()`:

```typescript
selectedIndex: null,
selectAntenna: (index) => set({ selectedIndex: index }),
```

Update the `clear()` method to also reset `selectedIndex: null`.

Note: The `computeForSelected()` dispatch and frontend MIMO interaction (beam pattern rendering on selected mMIMO antenna, triggering MIMO compute) are deferred to a follow-up task after the core visual + backend infrastructure is working. The click selection + route infrastructure in this plan provide the foundation.

- [ ] **Step 2: Verify it compiles**

Run: `cd aegis-web && npx tsc --noEmit`

- [ ] **Step 3: Commit**

```bash
git add aegis-web/src/stores/basestations.ts
git commit -m "Add selected antenna state to base stations store"
```

---

## Task 7: PanelAntenna shared component

**Files:**
- Create: `aegis-web/src/components/scene/PanelAntenna.tsx`

This is the core visual component. It renders an oriented rectangular antenna panel with element dots, support pole, and optional radiation pattern mesh.

- [ ] **Step 1: Create PanelAntenna component**

```typescript
// aegis-web/src/components/scene/PanelAntenna.tsx
import { useMemo, useRef } from 'react'
import * as THREE from 'three'
import type { Archetype } from '@/utils/classifyAntenna'

interface PanelAntennaProps {
  nH: number
  nV: number
  panelWidth: number
  panelHeight: number
  depth?: number
  azimuthDeg: number
  tiltDeg: number
  position: [number, number, number]
  color?: string
  showElements?: boolean
  elementDotRadius?: number
  poleRadius?: number
  selected?: boolean
  onClick?: () => void
}

const DEFAULT_DEPTH = 0.05
const DEFAULT_POLE_RADIUS = 0.04
const DEFAULT_DOT_RADIUS = 0.008
const DEFAULT_COLOR = '#888888'

export default function PanelAntenna({
  nH,
  nV,
  panelWidth,
  panelHeight,
  depth = DEFAULT_DEPTH,
  azimuthDeg,
  tiltDeg,
  position,
  color = DEFAULT_COLOR,
  showElements = true,
  elementDotRadius = DEFAULT_DOT_RADIUS,
  poleRadius = DEFAULT_POLE_RADIUS,
  selected = false,
  onClick,
}: PanelAntennaProps) {
  const groupRef = useRef<THREE.Group>(null)

  // Compute panel orientation quaternion from azimuth and tilt
  const quaternion = useMemo(() => {
    const q = new THREE.Quaternion()
    // Azimuth: rotate around Y axis (compass bearing, 0=North=+Z, 90=East=+X)
    // In Three.js Y-up: North is -Z, so azimuth 0 faces -Z
    const azRad = THREE.MathUtils.degToRad(azimuthDeg)
    const tiltRad = THREE.MathUtils.degToRad(tiltDeg)
    const euler = new THREE.Euler(tiltRad, -azRad, 0, 'YXZ')
    q.setFromEuler(euler)
    return q
  }, [azimuthDeg, tiltDeg])

  // Compute element positions on the panel face (local coords)
  const elementPositions = useMemo(() => {
    if (!showElements || nH <= 0 || nV <= 0) return []
    const positions: [number, number, number][] = []
    const spacingH = nH > 1 ? panelWidth / (nH + 1) : 0
    const spacingV = nV > 1 ? panelHeight / (nV + 1) : 0
    const startH = nH > 1 ? -panelWidth / 2 + spacingH : 0
    const startV = nV > 1 ? -panelHeight / 2 + spacingV : 0
    for (let i = 0; i < nH; i++) {
      for (let j = 0; j < nV; j++) {
        const x = nH > 1 ? startH + i * spacingH : 0
        const y = nV > 1 ? startV + j * spacingV : 0
        positions.push([x, y, depth / 2 + 0.001])
      }
    }
    return positions
  }, [nH, nV, panelWidth, panelHeight, depth, showElements])

  const [px, py, pz] = position
  const poleHeight = py

  const panelColor = selected ? '#ffaa00' : color
  const emissive = selected ? '#664400' : '#000000'

  return (
    <group ref={groupRef}>
      {/* Support pole from ground to panel center */}
      {poleHeight > 0.1 && (
        <mesh position={[px, poleHeight / 2, pz]}>
          <cylinderGeometry args={[poleRadius, poleRadius, poleHeight, 8]} />
          <meshStandardMaterial color="#404040" metalness={0.6} roughness={0.4} />
        </mesh>
      )}

      {/* Panel body - oriented by azimuth and tilt */}
      <group position={[px, py, pz]} quaternion={quaternion}>
        <mesh onClick={onClick}>
          <boxGeometry args={[panelWidth, panelHeight, depth]} />
          <meshStandardMaterial
            color={panelColor}
            emissive={emissive}
            metalness={0.5}
            roughness={0.3}
          />
        </mesh>

        {/* Element dots on the front face */}
        {showElements && elementPositions.map((pos, i) => (
          <mesh key={i} position={pos}>
            <circleGeometry args={[elementDotRadius, 12]} />
            <meshBasicMaterial color="#cccccc" side={THREE.FrontSide} />
          </mesh>
        ))}
      </group>
    </group>
  )
}
```

- [ ] **Step 2: Verify it compiles**

Run: `cd aegis-web && npx tsc --noEmit`

- [ ] **Step 3: Commit**

```bash
git add aegis-web/src/components/scene/PanelAntenna.tsx
git commit -m "Add PanelAntenna shared 3D component for antenna panel rendering"
```

---

## Task 8: Rewrite BaseStationMarkers to use PanelAntenna

**Files:**
- Rewrite: `aegis-web/src/components/scene/BaseStationMarkers.tsx`

- [ ] **Step 1: Rewrite the component**

Replace the entire file. The new version groups antennas by site, renders one pole per site, and a `PanelAntenna` per antenna. Read the current file first to preserve the `bsToScenePos()` function and `OPERATOR_COLORS` map.

Key changes from the current implementation:
- Remove the two `InstancedMesh` refs (poles, spheres)
- Remove the `useEffect` that rebuilds instanced geometry
- Instead: iterate over filtered base stations, group by `site_code`, render `PanelAntenna` for each
- Add click handler that calls `selectAntenna(index)` on the store
- Vertical stacking: within a site, antennas at the same azimuth offset vertically by `site_vertical_gap` (from config, default 0.1m)

The new structure:

```typescript
import { useMemo } from 'react'
import { useBaseStationsStore } from '@/stores/basestations'
import type { BaseStationData } from '@/api/basestations'
import PanelAntenna from './PanelAntenna'

const OPERATOR_COLORS: Record<string, string> = {
  Proximus: '#4488ff',
  Orange: '#f97316',
  Telenet: '#22c55e',
  'Citymesh Mobile (Insky)': '#e879f9',
}
const DEFAULT_COLOR = '#a855f7'
const R = 6_371_000

function bsToScenePos(
  bs: BaseStationData,
  origin: { lat: number; lon: number },
): [number, number, number] {
  const dLat = ((bs.latitude - origin.lat) * Math.PI) / 180
  const dLon = ((bs.longitude - origin.lon) * Math.PI) / 180
  const cosLat = Math.cos((origin.lat * Math.PI) / 180)
  const east = R * dLon * cosLat
  const north = R * dLat
  return [east, bs.height_m, -north]
}

interface SiteGroup {
  siteCode: string
  antennas: { bs: BaseStationData; index: number }[]
  maxHeight: number
  position: [number, number, number] // use first antenna's position
}

export default function BaseStationMarkers() {
  const basestations = useBaseStationsStore(s => s.basestations)
  const origin = useBaseStationsStore(s => s.origin)
  const enabledOperators = useBaseStationsStore(s => s.enabledOperators)
  const enabledTechnologies = useBaseStationsStore(s => s.enabledTechnologies)
  const selectedIndex = useBaseStationsStore(s => s.selectedIndex)
  const selectAntenna = useBaseStationsStore(s => s.selectAntenna)

  // Group by site and filter
  const siteGroups = useMemo(() => {
    if (!origin || basestations.length === 0) return []

    const groups = new Map<string, SiteGroup>()

    basestations.forEach((bs, index) => {
      if (!enabledOperators.has(bs.operator)) return
      if (!enabledTechnologies.has(bs.technology)) return

      const key = bs.site_code
      if (!groups.has(key)) {
        groups.set(key, {
          siteCode: key,
          antennas: [],
          maxHeight: 0,
          position: bsToScenePos(bs, origin),
        })
      }
      const group = groups.get(key)!
      group.antennas.push({ bs, index })
      group.maxHeight = Math.max(group.maxHeight, bs.height_m)
    })

    // Sort antennas within each site by azimuth then frequency
    for (const group of groups.values()) {
      group.antennas.sort((a, b) => {
        const azDiff = a.bs.azimuth_deg - b.bs.azimuth_deg
        if (azDiff !== 0) return azDiff
        return a.bs.freq_mhz - b.bs.freq_mhz
      })
    }

    return Array.from(groups.values())
  }, [basestations, origin, enabledOperators, enabledTechnologies])

  if (!origin) return null

  const VERTICAL_GAP = 0.1

  return (
    <group>
      {siteGroups.map(site => {
        // Track vertical offset per azimuth
        const azimuthOffsets = new Map<number, number>()

        return (
          <group key={site.siteCode}>
            {site.antennas.map(({ bs, index }) => {
              const pos = bsToScenePos(bs, origin)
              const azKey = bs.azimuth_deg
              const offset = azimuthOffsets.get(azKey) ?? 0
              azimuthOffsets.set(azKey, offset + 1)
              const verticalShift = offset * (bs.panel_height_m + VERTICAL_GAP)

              return (
                <PanelAntenna
                  key={index}
                  nH={bs.n_h}
                  nV={bs.n_v}
                  panelWidth={bs.panel_width_m}
                  panelHeight={bs.panel_height_m}
                  azimuthDeg={bs.azimuth_deg}
                  tiltDeg={bs.total_tilt_deg}
                  position={[pos[0], pos[1] - verticalShift, pos[2]]}
                  color={OPERATOR_COLORS[bs.operator] ?? DEFAULT_COLOR}
                  selected={selectedIndex === index}
                  onClick={() => selectAntenna(
                    selectedIndex === index ? null : index,
                  )}
                />
              )
            })}
          </group>
        )
      })}
    </group>
  )
}
```

- [ ] **Step 2: Verify it compiles**

Run: `cd aegis-web && npx tsc --noEmit`

- [ ] **Step 3: Commit**

```bash
git add aegis-web/src/components/scene/BaseStationMarkers.tsx
git commit -m "Rewrite BaseStationMarkers with PanelAntenna and site grouping"
```

---

## Task 9: Update BaseStationsPanel with text location input

**Files:**
- Modify: `aegis-web/src/components/panels/BaseStationsPanel.tsx`

- [ ] **Step 1: Replace lat/lon inputs with location text input**

Key changes:
- Replace `lat`/`lon` state with single `location` string state (default: `"Brussels, Belgium"`)
- Update `handleLoad()` to pass `{ location, radius_m }` instead of `{ lat, lon, radius_m }`
- Replace the two number inputs with one text input

In the component state (lines 8-10):

```typescript
// Replace these three lines:
const [lat, setLat] = useState(50.8503)
const [lon, setLon] = useState(4.3517)
const [radius, setRadius] = useState(500)

// With:
const [location, setLocation] = useState('Brussels, Belgium')
const [radius, setRadius] = useState(500)
```

In `handleLoad()` (line 36):

```typescript
// Replace:
const res = await loadBasestations({ lat, lon, radius_m: radius })
setBasestations(res.basestations, { lat, lon })

// With:
const res = await loadBasestations({ location, radius_m: radius })
if (res.basestations.length > 0) {
  const first = res.basestations[0]
  setBasestations(res.basestations, { lat: first.latitude, lon: first.longitude })
}
```

In the JSX (lines 54-70), replace the Latitude and Longitude inputs with:

```tsx
<label className={labelClass}>Location</label>
<input
  type="text"
  className={inputClass}
  value={location}
  onChange={e => setLocation(e.target.value)}
  placeholder="e.g. Brussels, Belgium or 50.85, 4.35"
  onKeyDown={e => e.key === 'Enter' && !isLoading && handleLoad()}
/>
```

- [ ] **Step 2: Verify it compiles**

Run: `cd aegis-web && npx tsc --noEmit`

- [ ] **Step 3: Commit**

```bash
git add aegis-web/src/components/panels/BaseStationsPanel.tsx
git commit -m "Replace lat/lon inputs with text location input in BaseStationsPanel"
```

---

## Task 10: Add "Also load base stations" checkbox to ScenePanel

**Files:**
- Modify: `aegis-web/src/components/panels/ScenePanel.tsx`

- [ ] **Step 1: Add checkbox state and auto-load logic**

In `ScenePanel()`, add state (around line 69):

```typescript
const [alsoLoadBS, setAlsoLoadBS] = useState(false)
```

Add an import at the top:

```typescript
import { loadBasestations } from '@/api/basestations'
import { useBaseStationsStore } from '@/stores/basestations'
```

In the 'done' event handler (around line 96-100), after the existing `fetchCapabilities()` call, add:

```typescript
if (alsoLoadBS) {
  try {
    const bsRes = await loadBasestations({ location, radius_m: radius })
    if (bsRes.basestations.length > 0) {
      const first = bsRes.basestations[0]
      useBaseStationsStore.getState().setBasestations(
        bsRes.basestations,
        { lat: first.latitude, lon: first.longitude },
      )
    }
  } catch (err) {
    console.warn('Auto-load base stations failed:', err)
  }
}
```

In the JSX, add a checkbox below the existing location input controls (before the Load button):

```tsx
<label className="flex items-center gap-2 text-xs cursor-pointer select-none mt-2">
  <input
    type="checkbox"
    className="rounded border-border accent-primary h-3.5 w-3.5"
    checked={alsoLoadBS}
    onChange={e => setAlsoLoadBS(e.target.checked)}
  />
  <span className="text-foreground/70">Also load base stations</span>
</label>
```

- [ ] **Step 2: Verify it compiles**

Run: `cd aegis-web && npx tsc --noEmit`

- [ ] **Step 3: Commit**

```bash
git add aegis-web/src/components/panels/ScenePanel.tsx
git commit -m "Add 'Also load base stations' checkbox to ScenePanel"
```

---

## Task 11: Build and visual verification

**Files:** None new. This is integration testing.

- [ ] **Step 1: Build the frontend**

Run: `cd aegis-web && npm run build`
Expected: Build succeeds with no errors

- [ ] **Step 2: Copy build to Flask static**

Run: `cd aegis-web && npm run build:copy`

- [ ] **Step 3: Run the full test suite**

Run: `python -m pytest tests/ -m "not slow" -x -n0`
Expected: All tests pass

- [ ] **Step 4: Lint everything**

Run: `python -m ruff check src/ tests/ && python -m ruff format --check src/ tests/`
Expected: Clean

- [ ] **Step 5: Commit any fixes**

If anything needed fixing, commit with descriptive message.

---

## Task 12: MIMO compute route for mMIMO base stations

**Files:**
- Modify: `src/aegis/viewer/routes/basestations.py`

This route builds an `AntennaArray` from the inferred grid, computes MRT precoder weights toward the body, and runs coherent dosimetry. It follows the same pattern as `src/aegis/viewer/routes/mimo.py`.

**Key references to read first:**
- `src/aegis/viewer/routes/mimo.py` lines 23-87: `_build_scene()` for AntennaArray.upa() construction
- `src/aegis/mimo/array.py`: `AntennaArray.upa()` constructor signature
- `src/aegis/mimo/compute.py`: `compute_mimo_scene_with_bodies()` for the full computation pipeline
- `src/aegis/basestation/coords.py`: `wgs84_to_enu()` for coordinate conversion

- [ ] **Step 1: Read MIMO infrastructure**

Read the files listed above to understand the exact interfaces. Key things to learn:
- `AntennaArray.upa(n_h, n_v, d_h, d_v, center, broadside, element_pattern)` constructs the array
- `compute_mimo_scene_with_bodies(scene, bodies, level, precoder_type)` runs the computation
- `MIMOScene(array, users, freq_hz, total_power)` wraps everything
- `UserConfig/UserState` represent the body

- [ ] **Step 2: Add MIMO compute route**

In `src/aegis/viewer/routes/basestations.py`, add imports at the top of the `register()` function scope (lazy, following existing pattern):

```python
@app.route("/api/basestations/compute_mimo", methods=["POST"])
def basestations_compute_mimo():
    """Compute coherent beamformed dosimetry for a mMIMO base station."""
    import json as _json

    import numpy as np

    from aegis.basestation.classify import classify_basestation
    from aegis.basestation.coords import wgs84_to_enu
    from aegis.constants import C_0
    from aegis.mimo.array import AntennaArray
    from aegis.mimo.compute import compute_mimo_scene_with_bodies
    from aegis.mimo.scene import MIMOScene
    from aegis.mimo.user import UserConfig, UserState

    data = request.get_json(force=True)
    index = data.get("index")

    with cache_lock:
        bss = list(cache.get("basestations", []))
        origin = cache.get("basestations_origin")
        bodies = {name: entry["body"] for name, entry in cache.get("bodies", {}).items()}
        default_body = cache.get("default_body", "thelonious")

    if index is None or index < 0 or index >= len(bss):
        return jsonify({"error": f"Invalid base station index: {index}"}), 400
    if not origin:
        return jsonify({"error": "No base station origin set"}), 400

    bs = bss[index]
    cls = classify_basestation(
        bs.gain_dbi, bs.technology, bs.freq_mhz,
        bs.horizontal_beamwidth_deg or 0,
        bs.vertical_beamwidth_deg or 0,
    )
    if cls["archetype"] != "mmimo":
        return jsonify({"error": "Base station is not mMIMO classified"}), 400

    # Convert BS position to scene ENU
    bs_enu = wgs84_to_enu(
        bs.latitude, bs.longitude, bs.height_m,
        origin[0], origin[1], 0.0,
    )
    center = np.array(bs_enu, dtype=np.float64)

    # Compute broadside from azimuth and tilt
    az_rad = np.radians(bs.azimuth_deg)
    tilt_rad = np.radians(bs.total_tilt_deg)
    broadside = np.array([
        np.sin(az_rad) * np.cos(tilt_rad),
        np.cos(az_rad) * np.cos(tilt_rad),
        -np.sin(tilt_rad),
    ], dtype=np.float64)

    # Build array
    freq_hz = bs.freq_mhz * 1e6
    wavelength = C_0 / freq_hz
    d = 0.5 * wavelength

    array = AntennaArray.upa(
        n_h=cls["n_h"],
        n_v=cls["n_v"],
        d_h=d,
        d_v=d,
        center=center,
        broadside=broadside,
        element_pattern="patch",
    )

    # Body position
    body_offset = np.array(data.get("body_offset", [0.0, 0.0, 0.0]), dtype=np.float64)
    body_rotation_y = float(data.get("body_rotation_y", 0.0))
    phantom = data.get("phantom", default_body)

    if phantom not in bodies:
        return jsonify({"error": f"Unknown phantom: {phantom!r}"}), 404

    user_cfg = UserConfig(
        user_id="bs_user",
        phantom_name=phantom,
        position=body_offset,
        device_position=body_offset + np.array([0.25, 0.0, 1.4]),
        device_orientation=np.array([0.0, 0.0, 1.0]),
        orientation=body_rotation_y,
    )

    eirp_w = 10 ** ((bs.eirp_dbm - 30) / 10)

    scene = MIMOScene(
        array=array,
        users=[UserState(config=user_cfg)],
        freq_hz=freq_hz,
        total_power=eirp_w,
    )

    level = int(data.get("level", 7))
    precoder_type = str(data.get("precoder_type", "mrt"))

    try:
        summary = compute_mimo_scene_with_bodies(
            scene, bodies, level=level, precoder_type=precoder_type,
        )
    except Exception as exc:
        logger.exception("MIMO base station compute failed")
        return jsonify({"error": str(exc)}), 500

    # Serialize result as binary + X-Stats header (same as /api/basestations/compute)
    user = scene.users[0]
    if user._sab_raw is not None:
        sab = user._sab_raw.astype(np.float32)
        data_bytes = sab.tobytes()
        stats = {
            "p_abs": float(user.result.p_abs) if user.result else 0.0,
            "peak_sab": float(user.result.peak_sab) if user.result else 0.0,
            "n_basestations": 1,
            "freq_hz": freq_hz,
            "precoder_type": precoder_type,
            "archetype": "mmimo",
            "n_h": cls["n_h"],
            "n_v": cls["n_v"],
            "arrays": [{"key": "sab", "offset": 0, "length": len(sab)}],
        }
    else:
        data_bytes = b""
        stats = {"error": "No SAB result"}

    resp = Response(data_bytes, mimetype="application/octet-stream")
    resp.headers["X-Stats"] = _json.dumps(stats)
    resp.headers["Access-Control-Expose-Headers"] = "X-Stats"
    return resp
```

- [ ] **Step 3: Run tests**

Run: `python -m pytest tests/ -m "not slow" -x -n0`
Expected: All tests pass (this is a new route, not breaking existing ones)

- [ ] **Step 4: Lint**

Run: `python -m ruff check src/aegis/viewer/routes/basestations.py && python -m ruff format --check src/aegis/viewer/routes/basestations.py`

- [ ] **Step 5: Commit**

```bash
git add src/aegis/viewer/routes/basestations.py
git commit -m "Add MIMO compute route for mMIMO base stations"
```

---

## Task 13: Refactor AntennaArray to use PanelAntenna

**Files:**
- Modify: `aegis-web/src/components/scene/AntennaArray.tsx`

- [ ] **Step 1: Read the current AntennaArray component**

Read `aegis-web/src/components/scene/AntennaArray.tsx` fully to understand the backplane, element, and pole rendering sections.

- [ ] **Step 2: Extract panel rendering to use PanelAntenna**

Replace the backplane panel (lines ~219-222), instanced element mesh (lines ~225-227), and support pole (lines ~230-235) with a single `<PanelAntenna>` component. Keep the array factor computation and radiation pattern mesh in AntennaArray.

The implementing agent should:
1. Import `PanelAntenna` from `./PanelAntenna`
2. Compute the equivalent `azimuthDeg` and `tiltDeg` from the existing broadside direction
3. Replace the three rendering blocks with one `<PanelAntenna>` call
4. Keep the `patternGeo` memoization and pattern mesh rendering as-is (these stay in AntennaArray because they depend on precoder weights)

- [ ] **Step 3: Verify visual parity**

Run: `cd aegis-web && npm run build`
Expected: Build succeeds. Visual appearance of MIMO antenna should remain the same.

- [ ] **Step 4: Commit**

```bash
git add aegis-web/src/components/scene/AntennaArray.tsx
git commit -m "Refactor AntennaArray to use shared PanelAntenna component"
```

---

## Task 14: Final integration and push

- [ ] **Step 1: Full build**

Run: `cd aegis-web && npm run build && npm run build:copy`

- [ ] **Step 2: Full test suite**

Run: `python -m pytest tests/ -m "not slow" -x -n0`

- [ ] **Step 3: Lint**

Run: `python -m ruff check src/ tests/ && python -m ruff format --check src/ tests/`

- [ ] **Step 4: Push**

```bash
git push origin master
```
