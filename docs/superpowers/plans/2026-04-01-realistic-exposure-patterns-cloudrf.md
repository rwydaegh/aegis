# Realistic exposure, pattern library, and CloudRF implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three capabilities to AEGIS: (1) a unified antenna pattern library backed by 156k local MSI files and CloudRF's 1,241-pattern API, (2) realistic exposure modes (theoretical/actual_max/typical) with TDD duty cycles, beam decomposition, and sidelobe modeling, (3) CloudRF API integration for coverage underlays, S_inc validation, and real-world scenario presets.

**Architecture:** Phase A (pattern library) creates `msi.py` (parser) and `library.py` (SQLite index + unified search) in the basestation module, plus a CloudRF client in integration/. Phase B (realistic exposure) adds `ExposureConfig`/`BeamConfig` dataclasses and an `ExposureMode` enum, wired through the adapter and viewer routes. Phase C (CloudRF features) adds coverage underlays and validation endpoints. All phases share the `AntennaPattern(181, 360)` type as the universal output format.

**Tech Stack:** Python 3.12 (numpy, sqlite3, zipfile, requests, Pillow), TypeScript/React (Zustand), Flask REST API

**Spec:** `docs/superpowers/specs/2026-04-01-realistic-exposure-and-pattern-library-design.md`

**Supersedes:** `docs/superpowers/plans/2026-04-01-realistic-exposure.md` (older plan that put exposure fields on BaseStation directly)

---

## File structure

| File | Action | Responsibility |
|---|---|---|
| `src/aegis/basestation/msi.py` | Create | MSI file parser, metadata extraction, H/V to 2D reconstruction |
| `src/aegis/basestation/library.py` | Create | AntennaPatternLibrary: SQLite index build, unified search, pattern loading |
| `src/aegis/basestation/antenna.py` | Modify (lines 1-10) | Add ExposureConfig and BeamConfig frozen dataclasses. BaseStation unchanged. |
| `src/aegis/basestation/pattern.py` | Modify (line 10-37) | Add sidelobe_suppression_db param to synthetic_pattern_from_beamwidth |
| `src/aegis/basestation/power.py` | Modify (lines 8-31) | Add ExposureMode enum and effective_eirp_dbm() |
| `src/aegis/basestation/classify.py` | Modify (lines 102-149) | Return ExposureConfig and BeamConfig from classify_basestation() |
| `src/aegis/basestation/adapter.py` | Modify (lines 223-333) | Add exposure_mode/exposure_config params, beam decomposition |
| `src/aegis/basestation/__init__.py` | Modify (lines 1-16) | Export new public types |
| `src/aegis/integration/cloudrf.py` | Create | CloudRFClient: antenna search, pattern fetch, area coverage, path validation |
| `src/aegis/integration/cloudrf_templates.py` | Create | CloudRF JSON template to AEGIS scenario converter |
| `src/aegis/viewer/routes/patterns.py` | Create | /api/patterns/search, /api/patterns/{source}/{id}, /api/patterns/manufacturers |
| `src/aegis/viewer/routes/basestations.py` | Modify (lines 188-322, 542-571) | exposure_mode in compute, ExposureConfig in _bs_summary |
| `src/aegis/viewer/routes/environment.py` | Modify | Add /api/environment/coverage CloudRF route |
| `src/aegis/viewer/routes/compute.py` | Modify | Add /api/validate/sinc route |
| `src/aegis/viewer/config.py` | Modify (lines 436-477) | Add exposure + pattern_library config blocks |
| `aegis-web/src/api/patterns.ts` | Create | Pattern search/fetch API client |
| `aegis-web/src/stores/simulation.ts` | Modify | Add exposureMode, selectedPattern |
| `aegis-web/src/components/panels/PatternBrowserPanel.tsx` | Create | Pattern search UI with polar plot preview |
| `aegis-web/src/components/panels/ParametersPanel.tsx` | Modify | Exposure mode toggle |
| `aegis-web/src/components/panels/BaseStationsPanel.tsx` | Modify | Coverage overlay toggle |
| `aegis-web/src/components/scene/CoverageOverlay.tsx` | Create | Ground-plane coverage texture from CloudRF |
| `aegis-web/src/components/hud/ScenarioDropdown.tsx` | Modify | "Real-world radios" group |
| `configs/presets/cloudrf/*.json` | Create | Converted CloudRF scenario configs |
| `tests/test_msi_parser.py` | Create | MSI parsing, elevation remapping, convention detection |
| `tests/test_pattern_library.py` | Create | Index build, search, pattern loading |
| `tests/test_exposure_modes.py` | Create | ExposureMode, effective_eirp_dbm, beam decomposition |
| `tests/test_sidelobe.py` | Create | Sidelobe floor on synthetic patterns |
| `tests/test_cloudrf_client.py` | Create | Mocked CloudRF API, pattern conversion |
| `pyproject.toml` | Modify | Add Pillow to [viewer] extra |

---

## Phase A: Antenna pattern library

### Task 1: MSI parser

**Files:**
- Create: `src/aegis/basestation/msi.py`
- Create: `tests/test_msi_parser.py`
- Create: `tests/fixtures/test_antenna.msi` (small test fixture)

- [ ] **Step 1: Create a test fixture MSI file**

Create `tests/fixtures/test_antenna.msi` with known values. Use the real Kathrein format observed in the codebase:

```
TestAntenna 900MHz
FREQUENCY 900
GAIN (dBi) 12.0
TILT 
COMMENT test fixture
HORIZONTAL 360
0.0 0.0
1.0 0.1
2.0 0.2
...  (360 rows, angle then attenuation in dB relative to peak)
VERTICAL 360
0.0 0.0
1.0 0.3
...  (360 rows)
```

Generate programmatically: H-plane has a Gaussian-like pattern centered at 0 with known -3dB points. V-plane likewise. This gives known ground truth for reconstruction verification.

- [ ] **Step 2: Write failing tests for parse_msi**

```python
# tests/test_msi_parser.py
import numpy as np
import pytest
from pathlib import Path

def test_parse_msi_header():
    """parse_msi extracts name, frequency, gain from MSI text."""
    from aegis.basestation.msi import parse_msi
    text = Path("tests/fixtures/test_antenna.msi").read_text()
    meta, h_atten, v_atten = parse_msi(text, manufacturer="TestMfg", source_zip="test.zip", source_path="test.msi")
    assert meta.name == "TestAntenna 900MHz"
    assert meta.frequency_mhz == 900.0
    assert meta.gain_dbi == 12.0
    assert meta.manufacturer == "TestMfg"

def test_parse_msi_shapes():
    """H and V attenuation arrays are (360,) float64."""
    from aegis.basestation.msi import parse_msi
    text = Path("tests/fixtures/test_antenna.msi").read_text()
    _, h, v = parse_msi(text, manufacturer="TestMfg", source_zip="test.zip", source_path="test.msi")
    assert h.shape == (360,)
    assert v.shape == (360,)
    assert h[0] == 0.0  # peak at boresight
    assert h[180] > 0.0  # attenuated at back

def test_parse_msi_boresight_convention():
    """V-plane index 0 = boresight (0 dB attenuation)."""
    from aegis.basestation.msi import parse_msi
    text = Path("tests/fixtures/test_antenna.msi").read_text()
    meta, _, v = parse_msi(text, manufacturer="TestMfg", source_zip="test.zip", source_path="test.msi")
    assert meta.vertical_convention == "boresight"
    assert v[0] == 0.0
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python3.12 -m pytest tests/test_msi_parser.py -x -v`
Expected: ImportError (module does not exist yet)

- [ ] **Step 4: Implement parse_msi**

Create `src/aegis/basestation/msi.py` with:
- `MSIMetadata` frozen dataclass (name, manufacturer, frequency_mhz, gain_dbi, tilt_deg, source_zip, source_path, vertical_convention)
- `parse_msi(text, manufacturer, source_zip, source_path)` that:
  1. Reads first line as name
  2. Scans header lines for FREQUENCY, GAIN, TILT keywords
  3. Finds HORIZONTAL 360 marker, reads next 360 lines as angle+attenuation pairs
  4. Finds VERTICAL 360 marker, reads next 360 lines
  5. Detects vertical convention: if v_atten[0] == 0.0, it is "boresight"; if min attenuation is at index 90, it is "zenith"
  6. Returns (MSIMetadata, h_atten_360, v_atten_360)

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3.12 -m pytest tests/test_msi_parser.py -x -v`
Expected: All 3 PASS

- [ ] **Step 6: Write failing tests for msi_to_antenna_pattern**

```python
def test_msi_to_pattern_shape():
    """Reconstructed pattern is (181, 360) AntennaPattern."""
    from aegis.basestation.msi import parse_msi, msi_to_antenna_pattern
    text = Path("tests/fixtures/test_antenna.msi").read_text()
    meta, h, v = parse_msi(text, manufacturer="X", source_zip="x.zip", source_path="x.msi")
    pattern = msi_to_antenna_pattern(h, v, meta.gain_dbi)
    assert pattern.gain_dbi.shape == (181, 360)
    assert pattern.max_gain_dbi == pytest.approx(12.0, abs=0.1)

def test_msi_to_pattern_boresight():
    """Peak gain at boresight (elevation=0, azimuth=0)."""
    from aegis.basestation.msi import parse_msi, msi_to_antenna_pattern
    text = Path("tests/fixtures/test_antenna.msi").read_text()
    _, h, v = parse_msi(text, manufacturer="X", source_zip="x.zip", source_path="x.msi")
    pattern = msi_to_antenna_pattern(h, v, 12.0)
    # elevation 0 = row 90 (index 90 maps to 0 deg), azimuth 0 = col 180 (index 180 maps to 0 deg)
    boresight_gain = pattern.gain_dbi[90, 180]
    assert boresight_gain == pytest.approx(12.0, abs=0.01)

def test_msi_to_pattern_elevation_mapping():
    """V-plane boresight maps to elevation=0, zenith to +90, nadir to -90."""
    from aegis.basestation.msi import parse_msi, msi_to_antenna_pattern
    text = Path("tests/fixtures/test_antenna.msi").read_text()
    _, h, v = parse_msi(text, manufacturer="X", source_zip="x.zip", source_path="x.msi")
    pattern = msi_to_antenna_pattern(h, v, 12.0)
    # Elevation +90 (zenith) = row 180. Should be attenuated.
    # Elevation -90 (nadir) = row 0. Should be attenuated.
    assert pattern.gain_dbi[180, 180] < 12.0  # zenith
    assert pattern.gain_dbi[0, 180] < 12.0    # nadir
    assert pattern.gain_dbi[90, 180] > pattern.gain_dbi[0, 180]  # boresight > nadir
```

- [ ] **Step 7: Implement msi_to_antenna_pattern**

Add to `src/aegis/basestation/msi.py`:
- `msi_to_antenna_pattern(h_atten, v_atten, gain_dbi, vertical_convention="boresight")` that:
  1. Creates 181-point elevation attenuation by remapping V-plane:
     - Boresight convention: MSI index 0 = forward = elevation 0. Index 90 = up = elevation +90. Index 270 = down = elevation -90.
     - Extract: for elevation -90..+90 (181 points), map to MSI index via `msi_idx = (90 - elev) % 360`
  2. Creates the 2D gain matrix: `gain_2d[elev_i, azim_j] = gain_dbi - v_atten_181[elev_i] - h_atten[azim_j]`
  3. Clamps to floor of -200 dBi (effectively zero)
  4. Returns `AntennaPattern(gain_dbi=gain_2d, max_gain_dbi=gain_dbi)`

- [ ] **Step 8: Run all tests**

Run: `python3.12 -m pytest tests/test_msi_parser.py -x -v`
Expected: All 6 PASS

- [ ] **Step 9: Lint and commit**

```bash
python3.12 -m ruff check src/aegis/basestation/msi.py tests/test_msi_parser.py
python3.12 -m ruff format src/aegis/basestation/msi.py tests/test_msi_parser.py
git add src/aegis/basestation/msi.py tests/test_msi_parser.py tests/fixtures/test_antenna.msi
git commit -m "Add MSI antenna pattern parser with elevation remapping"
```

---

### Task 2: Sidelobe floor on synthetic patterns

**Files:**
- Modify: `src/aegis/basestation/pattern.py` (lines 10-37)
- Create: `tests/test_sidelobe.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_sidelobe.py
import numpy as np
import pytest

def test_sidelobe_floor_applied():
    """Synthetic pattern with sidelobe floor has minimum gain = peak - suppression."""
    from aegis.basestation.pattern import synthetic_pattern_from_beamwidth
    pattern = synthetic_pattern_from_beamwidth(65.0, 10.0, 17.0, sidelobe_suppression_db=15.0)
    assert pattern.gain_dbi.min() >= 17.0 - 15.0 - 0.01  # 2.0 dBi floor

def test_sidelobe_floor_default():
    """Default sidelobe floor is 15 dB."""
    from aegis.basestation.pattern import synthetic_pattern_from_beamwidth
    pattern = synthetic_pattern_from_beamwidth(65.0, 10.0, 17.0)
    # With default 15 dB suppression, minimum should be ~2 dBi
    assert pattern.gain_dbi.min() >= 17.0 - 15.0 - 0.01

def test_no_sidelobe_floor():
    """Setting suppression to None disables the floor."""
    from aegis.basestation.pattern import synthetic_pattern_from_beamwidth
    pattern = synthetic_pattern_from_beamwidth(65.0, 10.0, 17.0, sidelobe_suppression_db=None)
    # Pure Gaussian rolls off to very low values at back
    assert pattern.gain_dbi[90, 0] < 17.0 - 30.0  # back lobe, well below 15 dB suppression
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3.12 -m pytest tests/test_sidelobe.py -x -v`
Expected: FAIL (no sidelobe_suppression_db parameter yet)

- [ ] **Step 3: Modify synthetic_pattern_from_beamwidth**

In `src/aegis/basestation/pattern.py`, add `sidelobe_suppression_db: float | None = 15.0` parameter. After computing the Gaussian gain matrix, add:

```python
if sidelobe_suppression_db is not None:
    floor_dbi = gain_dbi - sidelobe_suppression_db
    gain_matrix = np.maximum(gain_matrix, floor_dbi)
```

- [ ] **Step 4: Run tests**

Run: `python3.12 -m pytest tests/test_sidelobe.py tests/test_basestation.py -x -v`
Expected: All PASS (including existing basestation tests, since default 15dB floor should not break -3dB validation)

- [ ] **Step 5: Lint and commit**

```bash
python3.12 -m ruff check src/aegis/basestation/pattern.py tests/test_sidelobe.py
python3.12 -m ruff format src/aegis/basestation/pattern.py tests/test_sidelobe.py
git add src/aegis/basestation/pattern.py tests/test_sidelobe.py
git commit -m "Add sidelobe floor to synthetic antenna patterns"
```

---

### Task 3: SQLite pattern index and library

**Files:**
- Create: `src/aegis/basestation/library.py`
- Create: `tests/test_pattern_library.py`
- Create: `tests/fixtures/test_patterns.zip` (small zip with 3 MSI files)

- [ ] **Step 1: Create test fixture zip**

Write a script or inline code that creates `tests/fixtures/test_patterns.zip` containing:
```
TestMfg/900MHz/Model_A.MSI
TestMfg/1800MHz/Model_B.MSI
TestMfg/2100MHz/Model_C.MSI
```
Each with valid MSI content (use the fixture generator from Task 1). Different frequencies and gains.

- [ ] **Step 2: Write failing tests**

```python
# tests/test_pattern_library.py
import pytest
from pathlib import Path

@pytest.fixture
def library(tmp_path):
    """Create a library with test fixture zip."""
    from aegis.basestation.library import AntennaPatternLibrary
    import shutil
    msi_dir = tmp_path / "antenna_patterns" / "msi_raw"
    msi_dir.mkdir(parents=True)
    shutil.copy(Path(__file__).parent / "fixtures" / "test_patterns.zip", msi_dir / "TestMfg.zip")
    lib = AntennaPatternLibrary(data_dir=str(tmp_path))
    return lib

def test_build_index(library):
    count = library.build_index()
    assert count == 3

def test_search_by_manufacturer(library):
    library.build_index()
    results = library.search(manufacturer="TestMfg")
    assert len(results) == 3

def test_search_by_query(library):
    library.build_index()
    results = library.search(query="Model_A")
    assert len(results) == 1
    assert results[0].model == "Model_A"

def test_search_by_freq_range(library):
    library.build_index()
    results = library.search(freq_min_mhz=1700, freq_max_mhz=1900)
    assert len(results) == 1
    assert results[0].frequency_mhz == 1800.0

def test_load_pattern(library):
    library.build_index()
    results = library.search(query="Model_A")
    pattern = library.load_pattern(source="local", pattern_id=results[0].id)
    assert pattern.gain_dbi.shape == (181, 360)

def test_auto_build_on_first_search(tmp_path):
    """Index is auto-built on first search if missing."""
    from aegis.basestation.library import AntennaPatternLibrary
    import shutil
    msi_dir = tmp_path / "antenna_patterns" / "msi_raw"
    msi_dir.mkdir(parents=True)
    shutil.copy(Path(__file__).parent / "fixtures" / "test_patterns.zip", msi_dir / "TestMfg.zip")
    lib = AntennaPatternLibrary(data_dir=str(tmp_path))
    # No explicit build_index call
    results = lib.search(query="Model_A")
    assert len(results) == 1
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python3.12 -m pytest tests/test_pattern_library.py -x -v`
Expected: ImportError

- [ ] **Step 4: Implement AntennaPatternLibrary**

Create `src/aegis/basestation/library.py` with:
- `PatternSearchResult` dataclass (id, source, manufacturer, model, frequency_mhz, gain_dbi, tilt_deg)
- `AntennaPatternLibrary` class:
  - `__init__(data_dir, cloudrf_api_key=None)`: sets paths, lazy CloudRF client
  - `build_index()`: scan zips with `zipfile.ZipFile`, for each `.MSI`/`.msi` file read first 10 lines for header, insert into SQLite. Drop+recreate on each call.
  - `search(query, manufacturer, freq_min_mhz, freq_max_mhz, gain_min_dbi, gain_max_dbi, source, limit)`: query SQLite with LIKE for text, range for numeric. If source="all" and cloudrf client available, also query CloudRF and merge.
  - `load_pattern(source, pattern_id)`: for "local", open zip, extract file, parse_msi, msi_to_antenna_pattern. For "cloudrf", delegate to CloudRF client.
  - Auto-build: `search()` checks if index.sqlite exists, calls `build_index()` if not.

- [ ] **Step 5: Run tests**

Run: `python3.12 -m pytest tests/test_pattern_library.py -x -v`
Expected: All 6 PASS

- [ ] **Step 6: Lint and commit**

```bash
python3.12 -m ruff check src/aegis/basestation/library.py tests/test_pattern_library.py
python3.12 -m ruff format src/aegis/basestation/library.py tests/test_pattern_library.py
git add src/aegis/basestation/library.py tests/test_pattern_library.py tests/fixtures/test_patterns.zip
git commit -m "Add antenna pattern library with SQLite index over MSI files"
```

---

### Task 4: Pattern API routes

**Files:**
- Create: `src/aegis/viewer/routes/patterns.py`
- Modify: `src/aegis/viewer/server.py` (register blueprint)
- Modify: `src/aegis/viewer/config.py` (add pattern_library config)

- [ ] **Step 1: Add config defaults**

In `src/aegis/viewer/config.py`, inside the `"basestations"` dict (around line 477), add:

```python
"pattern_library": {
    "cloudrf_api_key_env": "CLOUDRF_API_KEY",
    "auto_build_index": True,
},
```

- [ ] **Step 2: Create route blueprint**

Create `src/aegis/viewer/routes/patterns.py` with Flask blueprint `patterns_bp`:

- `GET /api/patterns/search`: query params `q`, `manufacturer`, `freq_min`, `freq_max`, `gain_min`, `gain_max`, `source`, `limit`. Returns JSON with `results` array of PatternSearchResult dicts.
- `GET /api/patterns/<source>/<path:pattern_id>`: returns binary float32 array (181*360 values) with `X-Meta` header containing JSON metadata.
- `GET /api/patterns/manufacturers`: returns sorted list of unique manufacturers from local index.
- `POST /api/patterns/build-index`: triggers index rebuild, returns count.

The route creates/caches an `AntennaPatternLibrary` instance on first request using `_cache["config"]` for data_dir and CloudRF key lookup.

- [ ] **Step 3: Register blueprint in server.py**

In `src/aegis/viewer/server.py`, import and register `patterns_bp` alongside existing blueprints.

- [ ] **Step 4: Test manually or write a quick integration test**

Run: `python3.12 -m pytest tests/test_msi_parser.py tests/test_pattern_library.py tests/test_sidelobe.py -x -v`
Expected: All PASS

- [ ] **Step 5: Lint and commit**

```bash
python3.12 -m ruff check src/aegis/viewer/routes/patterns.py src/aegis/viewer/config.py
python3.12 -m ruff format src/aegis/viewer/routes/patterns.py src/aegis/viewer/config.py
git add src/aegis/viewer/routes/patterns.py src/aegis/viewer/server.py src/aegis/viewer/config.py
git commit -m "Add pattern search API routes backed by antenna library"
```

---

## Phase B: Realistic exposure model

### Task 5: ExposureConfig, BeamConfig, ExposureMode

**Files:**
- Modify: `src/aegis/basestation/antenna.py` (add dataclasses after line 9)
- Modify: `src/aegis/basestation/power.py` (add enum + function after line 31)
- Create: `tests/test_exposure_modes.py`

- [ ] **Step 1: Write failing tests for ExposureMode and effective_eirp_dbm**

```python
# tests/test_exposure_modes.py
import math
import pytest

def test_theoretical_mode_no_reduction():
    from aegis.basestation.antenna import ExposureConfig
    from aegis.basestation.power import ExposureMode, effective_eirp_dbm
    from aegis.basestation import BaseStation
    bs = BaseStation(site_code="T", antenna_label="A", operator="Op", technology="5G",
                     latitude=0, longitude=0, height_m=10, eirp_dbm=50.0, gain_dbi=25.0,
                     freq_mhz=3500, azimuth_deg=0, electrical_tilt_deg=0, mechanical_tilt_deg=0,
                     horizontal_beamwidth_deg=65, vertical_beamwidth_deg=10)
    exp = ExposureConfig(duplex_mode="tdd", tdd_dl_ratio=0.75, power_reduction_factor=0.32, traffic_load_factor=0.5)
    result = effective_eirp_dbm(bs, exp, ExposureMode.THEORETICAL)
    assert result == pytest.approx(50.0)

def test_actual_max_applies_tdd_and_prf():
    from aegis.basestation.antenna import ExposureConfig
    from aegis.basestation.power import ExposureMode, effective_eirp_dbm
    from aegis.basestation import BaseStation
    bs = BaseStation(site_code="T", antenna_label="A", operator="Op", technology="5G",
                     latitude=0, longitude=0, height_m=10, eirp_dbm=50.0, gain_dbi=25.0,
                     freq_mhz=3500, azimuth_deg=0, electrical_tilt_deg=0, mechanical_tilt_deg=0,
                     horizontal_beamwidth_deg=65, vertical_beamwidth_deg=10)
    exp = ExposureConfig(duplex_mode="tdd", tdd_dl_ratio=0.75, power_reduction_factor=0.32, traffic_load_factor=0.5)
    result = effective_eirp_dbm(bs, exp, ExposureMode.ACTUAL_MAX)
    expected = 50.0 + 10 * math.log10(0.75 * 0.32)  # 50 + 10*log10(0.24) = 50 - 6.20 = 43.80
    assert result == pytest.approx(expected, abs=0.01)

def test_typical_applies_all_factors():
    from aegis.basestation.antenna import ExposureConfig
    from aegis.basestation.power import ExposureMode, effective_eirp_dbm
    from aegis.basestation import BaseStation
    bs = BaseStation(site_code="T", antenna_label="A", operator="Op", technology="5G",
                     latitude=0, longitude=0, height_m=10, eirp_dbm=50.0, gain_dbi=25.0,
                     freq_mhz=3500, azimuth_deg=0, electrical_tilt_deg=0, mechanical_tilt_deg=0,
                     horizontal_beamwidth_deg=65, vertical_beamwidth_deg=10)
    exp = ExposureConfig(duplex_mode="tdd", tdd_dl_ratio=0.75, power_reduction_factor=0.32, traffic_load_factor=0.5)
    result = effective_eirp_dbm(bs, exp, ExposureMode.TYPICAL)
    expected = 50.0 + 10 * math.log10(0.75 * 0.32 * 0.5)  # 50 + 10*log10(0.12) = 50 - 9.21 = 40.79
    assert result == pytest.approx(expected, abs=0.01)

def test_near_zero_traffic_load_clamped():
    """traffic_load_factor near zero should not produce -inf."""
    from aegis.basestation.antenna import ExposureConfig
    from aegis.basestation.power import ExposureMode, effective_eirp_dbm
    from aegis.basestation import BaseStation
    bs = BaseStation(site_code="T", antenna_label="A", operator="Op", technology="5G",
                     latitude=0, longitude=0, height_m=10, eirp_dbm=50.0, gain_dbi=25.0,
                     freq_mhz=3500, azimuth_deg=0, electrical_tilt_deg=0, mechanical_tilt_deg=0,
                     horizontal_beamwidth_deg=65, vertical_beamwidth_deg=10)
    exp = ExposureConfig(tdd_dl_ratio=0.75, power_reduction_factor=0.32, traffic_load_factor=0.0)
    result = effective_eirp_dbm(bs, exp, ExposureMode.TYPICAL)
    assert math.isfinite(result)
    assert result < -50  # very low but not -inf
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3.12 -m pytest tests/test_exposure_modes.py -x -v`
Expected: ImportError

- [ ] **Step 3: Add ExposureConfig and BeamConfig to antenna.py**

At the top of `src/aegis/basestation/antenna.py`, after the existing imports, add:

```python
@dataclass(frozen=True)
class ExposureConfig:
    """Exposure reduction parameters for realistic modeling."""
    duplex_mode: str = "fdd"
    tdd_dl_ratio: float = 1.0
    power_reduction_factor: float = 1.0
    traffic_load_factor: float = 0.5

@dataclass(frozen=True)
class BeamConfig:
    """mMIMO broadcast/traffic beam separation for realistic exposure."""
    broadcast_gain_dbi: float = 18.0
    broadcast_hbw_deg: float = 65.0
    broadcast_vbw_deg: float = 10.0
    traffic_gain_dbi: float = 25.0
    traffic_hbw_deg: float = 12.0
    traffic_vbw_deg: float = 8.0
    sweep_h_range_deg: float = 60.0
    sweep_v_range_deg: float = 15.0
```

- [ ] **Step 4: Add ExposureMode and effective_eirp_dbm to power.py**

At the bottom of `src/aegis/basestation/power.py`, add:

```python
import math
from enum import Enum

class ExposureMode(str, Enum):
    THEORETICAL = "theoretical"
    ACTUAL_MAX = "actual_max"
    TYPICAL = "typical"

def effective_eirp_dbm(bs, exposure, mode):
    """Compute effective EIRP accounting for exposure mode."""
    factor = 1.0
    if mode in (ExposureMode.ACTUAL_MAX, ExposureMode.TYPICAL):
        factor *= exposure.tdd_dl_ratio
        factor *= exposure.power_reduction_factor
    if mode == ExposureMode.TYPICAL:
        factor *= exposure.traffic_load_factor
    factor = max(factor, 1e-10)
    return bs.eirp_dbm + 10 * math.log10(factor)
```

- [ ] **Step 5: Update __init__.py exports**

Add `ExposureConfig`, `BeamConfig`, `ExposureMode`, `effective_eirp_dbm` to exports in `src/aegis/basestation/__init__.py`.

- [ ] **Step 6: Run tests**

Run: `python3.12 -m pytest tests/test_exposure_modes.py -x -v`
Expected: All 4 PASS

- [ ] **Step 7: Lint and commit**

```bash
python3.12 -m ruff check src/aegis/basestation/antenna.py src/aegis/basestation/power.py src/aegis/basestation/__init__.py tests/test_exposure_modes.py
python3.12 -m ruff format src/aegis/basestation/antenna.py src/aegis/basestation/power.py src/aegis/basestation/__init__.py tests/test_exposure_modes.py
git add src/aegis/basestation/antenna.py src/aegis/basestation/power.py src/aegis/basestation/__init__.py tests/test_exposure_modes.py
git commit -m "Add ExposureConfig, BeamConfig, ExposureMode with power reduction"
```

---

### Task 6: Classification returns ExposureConfig and BeamConfig

**Files:**
- Modify: `src/aegis/basestation/classify.py` (lines 102-149)
- Modify: `tests/test_classify_antenna.py` (add tests)

- [ ] **Step 1: Write failing tests**

```python
# Add to existing tests/test_classify_antenna.py
def test_classify_returns_exposure_config():
    from aegis.basestation.classify import classify_basestation
    result = classify_basestation(gain_dbi=24.8, technology="5G", freq_mhz=3500)
    assert "exposure_config" in result
    exp = result["exposure_config"]
    assert exp.duplex_mode == "tdd"
    assert exp.tdd_dl_ratio == 0.75
    assert exp.power_reduction_factor == 0.32

def test_classify_sector_fdd():
    from aegis.basestation.classify import classify_basestation
    result = classify_basestation(gain_dbi=15.0, technology="4G", freq_mhz=1800)
    exp = result["exposure_config"]
    assert exp.duplex_mode == "fdd"
    assert exp.tdd_dl_ratio == 1.0

def test_classify_returns_beam_config_for_mmimo():
    from aegis.basestation.classify import classify_basestation
    result = classify_basestation(gain_dbi=24.8, technology="5G", freq_mhz=3500)
    assert "beam_config" in result
    bc = result["beam_config"]
    assert bc.broadcast_gain_dbi == 18.0
    assert bc.traffic_hbw_deg == 12.0

def test_classify_5g_sector_tdd():
    """5G sector at 3.5 GHz gets TDD ratio but no PRF reduction (PRF applies to mMIMO only)."""
    from aegis.basestation.classify import classify_basestation
    result = classify_basestation(gain_dbi=15.0, technology="5G", freq_mhz=3500)
    assert result["archetype"] == "sector"
    exp = result["exposure_config"]
    assert exp.duplex_mode == "tdd"
    assert exp.tdd_dl_ratio == 0.75
    assert exp.power_reduction_factor == 1.0  # sector, not mMIMO

def test_classify_no_beam_config_for_sector():
    from aegis.basestation.classify import classify_basestation
    result = classify_basestation(gain_dbi=15.0, technology="4G", freq_mhz=1800)
    assert result["beam_config"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3.12 -m pytest tests/test_classify_antenna.py -x -v -k "exposure_config or beam_config"`
Expected: FAIL (no exposure_config key in return dict)

- [ ] **Step 3: Modify classify_basestation**

In `src/aegis/basestation/classify.py`, import `ExposureConfig` and `BeamConfig` from `antenna.py`. At the end of `classify_basestation()`, before the return dict:

```python
# Infer exposure config from archetype + technology + frequency
if archetype == "mmimo":
    is_tdd = freq_mhz >= 2500 and technology and "5G" in technology.upper()
    exposure_config = ExposureConfig(
        duplex_mode="tdd" if is_tdd else "fdd",
        tdd_dl_ratio=0.75 if is_tdd else 1.0,
        power_reduction_factor=0.32,
        traffic_load_factor=0.5,
    )
    beam_config = BeamConfig()  # all defaults
elif archetype == "small_cell":
    exposure_config = ExposureConfig(traffic_load_factor=0.3)
    beam_config = None
else:  # sector
    is_tdd = freq_mhz >= 2500 and technology and "5G" in technology.upper()
    exposure_config = ExposureConfig(
        duplex_mode="tdd" if is_tdd else "fdd",
        tdd_dl_ratio=0.75 if is_tdd else 1.0,
    )
    beam_config = None
```

Add `"exposure_config": exposure_config, "beam_config": beam_config` to the return dict.

- [ ] **Step 4: Run all classification tests**

Run: `python3.12 -m pytest tests/test_classify_antenna.py -x -v`
Expected: All PASS

- [ ] **Step 5: Lint and commit**

```bash
python3.12 -m ruff check src/aegis/basestation/classify.py tests/test_classify_antenna.py
python3.12 -m ruff format src/aegis/basestation/classify.py tests/test_classify_antenna.py
git add src/aegis/basestation/classify.py tests/test_classify_antenna.py
git commit -m "Return ExposureConfig and BeamConfig from antenna classification"
```

---

### Task 7: Wire exposure mode through adapter and viewer routes

**Files:**
- Modify: `src/aegis/basestation/adapter.py` (lines 223-333)
- Modify: `src/aegis/viewer/routes/basestations.py` (lines 188-322, 542-571)
- Modify: `src/aegis/viewer/config.py` (lines 436-477)
- Add tests to `tests/test_exposure_modes.py`

- [ ] **Step 1: Write failing test for adapter**

```python
# Add to tests/test_exposure_modes.py
def test_paths_from_basestation_actual_max_reduces_power():
    """actual_max mode produces lower power than theoretical."""
    import numpy as np
    from aegis.basestation.adapter import paths_from_basestation
    from aegis.basestation.antenna import ExposureConfig
    from aegis.basestation.power import ExposureMode
    from aegis.basestation import BaseStation

    bs = BaseStation(site_code="T", antenna_label="A", operator="Op", technology="5G",
                     latitude=50.85, longitude=4.35, height_m=30, eirp_dbm=50.0, gain_dbi=25.0,
                     freq_mhz=3500, azimuth_deg=0, electrical_tilt_deg=6, mechanical_tilt_deg=0,
                     horizontal_beamwidth_deg=65, vertical_beamwidth_deg=10)
    body = np.array([0.0, 100.0, 1.5])  # 100m north, human height
    origin = (50.85, 4.35)
    exp = ExposureConfig(tdd_dl_ratio=0.75, power_reduction_factor=0.32, traffic_load_factor=0.5)

    paths_theo = paths_from_basestation(bs, body, origin)
    paths_actual = paths_from_basestation(bs, body, origin, exposure_mode=ExposureMode.ACTUAL_MAX, exposure_config=exp)

    assert paths_actual.total_power < paths_theo.total_power
```

- [ ] **Step 2: Run to verify failure**

Run: `python3.12 -m pytest tests/test_exposure_modes.py::test_paths_from_basestation_actual_max_reduces_power -x -v`
Expected: TypeError (unexpected keyword argument)

- [ ] **Step 3: Modify paths_from_basestation**

In `src/aegis/basestation/adapter.py`, add parameters to `paths_from_basestation()`:

```python
def paths_from_basestation(
    bs: BaseStation,
    body_center: np.ndarray,
    scene_origin: tuple[float, float],
    ground_height: float = 0.0,
    exposure_mode: ExposureMode | None = None,
    exposure_config: ExposureConfig | None = None,
    beam_config: BeamConfig | None = None,
    archetype: str | None = None,
) -> PropagationPaths:
```

In the function body, replace the EIRP usage:
- If `exposure_mode` and `exposure_config` are provided, use `effective_eirp_dbm(bs, exposure_config, exposure_mode)` to get the effective EIRP.
- Otherwise, use `bs.eirp_dbm` (backward compatible).

- [ ] **Step 4: Modify paths_from_basestations**

Add parallel parameters:

```python
def paths_from_basestations(
    basestations: list[BaseStation],
    body_center: np.ndarray,
    scene_origin: tuple[float, float],
    max_distance_m: float = 2000.0,
    exposure_mode: ExposureMode | None = None,
    exposure_configs: list[ExposureConfig] | None = None,
) -> PropagationPaths:
```

Pass per-station config through: `exposure_configs[i]` for station `i`.

- [ ] **Step 5: Add exposure config to _bs_summary and config.py**

In `basestations.py` `_bs_summary()`, add exposure_config fields to the return dict from classification result.

In `config.py`, add the `"exposure"` block inside `"basestations"` as specified in the spec.

- [ ] **Step 6: Add exposure_mode parameter to compute route**

In `_handle_basestations_compute`, read `exposure_mode` from request JSON (default "theoretical"), look up ExposureConfig from cached classification, pass both to `paths_from_basestations`.

- [ ] **Step 7: Run all tests**

Run: `python3.12 -m pytest tests/test_exposure_modes.py tests/test_basestation.py -x -v`
Expected: All PASS

- [ ] **Step 8: Lint and commit**

```bash
python3.12 -m ruff check src/aegis/basestation/adapter.py src/aegis/viewer/routes/basestations.py src/aegis/viewer/config.py
python3.12 -m ruff format src/aegis/basestation/adapter.py src/aegis/viewer/routes/basestations.py src/aegis/viewer/config.py
git add src/aegis/basestation/adapter.py src/aegis/viewer/routes/basestations.py src/aegis/viewer/config.py tests/test_exposure_modes.py
git commit -m "Wire exposure mode through adapter and viewer routes"
```

---

### Task 8: mMIMO beam decomposition in adapter

**Files:**
- Modify: `src/aegis/basestation/adapter.py`
- Add tests to `tests/test_exposure_modes.py`

- [ ] **Step 1: Write failing tests for beam decomposition**

```python
def test_beam_decomposition_actual_max_uses_max():
    """actual_max takes max(broadcast, traffic) for mMIMO in sweep range."""
    import numpy as np
    from aegis.basestation.adapter import paths_from_basestation
    from aegis.basestation.antenna import ExposureConfig, BeamConfig
    from aegis.basestation.power import ExposureMode
    from aegis.basestation import BaseStation

    bs = BaseStation(site_code="T", antenna_label="A", operator="Op", technology="5G",
                     latitude=50.85, longitude=4.35, height_m=30, eirp_dbm=50.0, gain_dbi=25.0,
                     freq_mhz=3500, azimuth_deg=0, electrical_tilt_deg=6, mechanical_tilt_deg=0,
                     horizontal_beamwidth_deg=65, vertical_beamwidth_deg=10)
    body = np.array([0.0, 50.0, 1.5])  # on boresight, within sweep range
    origin = (50.85, 4.35)
    exp = ExposureConfig(duplex_mode="tdd", tdd_dl_ratio=0.75, power_reduction_factor=0.32)
    beam = BeamConfig()

    paths = paths_from_basestation(
        bs, body, origin,
        exposure_mode=ExposureMode.ACTUAL_MAX,
        exposure_config=exp,
        beam_config=beam,
        archetype="mmimo",
    )
    # Should produce paths (power > 0)
    assert paths.total_power > 0

def test_beam_decomposition_outside_sweep_broadcast_only():
    """Outside sweep range, only broadcast beam contributes."""
    import numpy as np
    from aegis.basestation.adapter import paths_from_basestation
    from aegis.basestation.antenna import ExposureConfig, BeamConfig
    from aegis.basestation.power import ExposureMode
    from aegis.basestation import BaseStation

    bs = BaseStation(site_code="T", antenna_label="A", operator="Op", technology="5G",
                     latitude=50.85, longitude=4.35, height_m=30, eirp_dbm=50.0, gain_dbi=25.0,
                     freq_mhz=3500, azimuth_deg=0, electrical_tilt_deg=6, mechanical_tilt_deg=0,
                     horizontal_beamwidth_deg=65, vertical_beamwidth_deg=10)
    # Body at 90 degrees azimuth from boresight -- outside ±60 sweep
    body = np.array([200.0, 0.0, 1.5])
    origin = (50.85, 4.35)
    exp = ExposureConfig(duplex_mode="tdd", tdd_dl_ratio=0.75, power_reduction_factor=0.32)
    beam = BeamConfig(sweep_h_range_deg=60.0)

    paths = paths_from_basestation(
        bs, body, origin,
        exposure_mode=ExposureMode.ACTUAL_MAX,
        exposure_config=exp,
        beam_config=beam,
        archetype="mmimo",
    )
    # Broadcast only -- lower gain than traffic beam on boresight
    assert paths.total_power > 0
```

- [ ] **Step 2: Implement beam decomposition**

In `paths_from_basestation()`, when `archetype == "mmimo"` and `exposure_mode` is not THEORETICAL and `beam_config` is provided:

1. Compute antenna-local angles to body (using existing `departure_to_antenna_local`)
2. Generate broadcast pattern: `synthetic_pattern_from_beamwidth(beam.broadcast_hbw_deg, beam.broadcast_vbw_deg, beam.broadcast_gain_dbi)`
3. Compute broadcast power: `s_broadcast = tx_power * broadcast_gain / (4*pi*d^2)` where tx_power uses `eirp * tdd_dl_ratio`
4. Check sweep range: if `|azim_local| < sweep_h` and `|elev_local| < sweep_v`:
   - Generate traffic pattern: `synthetic_pattern_from_beamwidth(beam.traffic_hbw_deg, beam.traffic_vbw_deg, beam.traffic_gain_dbi)`
   - Compute traffic power: `s_traffic = tx_power * traffic_gain / (4*pi*d^2)` where tx_power uses `eirp * tdd_dl_ratio * prf`
   - For typical mode: multiply traffic power by `traffic_load_factor`
5. Combine: actual_max uses `max(broadcast, traffic)`, typical uses `broadcast + traffic`
6. Return single path with the combined power

- [ ] **Step 3: Run tests**

Run: `python3.12 -m pytest tests/test_exposure_modes.py -x -v`
Expected: All PASS

- [ ] **Step 4: Lint and commit**

```bash
python3.12 -m ruff check src/aegis/basestation/adapter.py tests/test_exposure_modes.py
python3.12 -m ruff format src/aegis/basestation/adapter.py tests/test_exposure_modes.py
git add src/aegis/basestation/adapter.py tests/test_exposure_modes.py
git commit -m "Add mMIMO broadcast/traffic beam decomposition for realistic exposure"
```

---

## Phase C: CloudRF integration

### Task 9: CloudRF client

**Files:**
- Create: `src/aegis/integration/cloudrf.py`
- Create: `tests/test_cloudrf_client.py`

- [ ] **Step 1: Write failing tests with mocked HTTP**

```python
# tests/test_cloudrf_client.py
import pytest
from unittest.mock import patch, MagicMock

def test_search_antennas_returns_list():
    from aegis.integration.cloudrf import CloudRFClient
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "rows": [{"id": 1, "manufacturer": "Ericsson", "model": "AIR6468", "frequency_mhz": 3500, "gain_dbi": 28.0}],
        "pages": 1
    }
    mock_response.status_code = 200
    with patch("requests.Session.post", return_value=mock_response):
        client = CloudRFClient(api_key="test-key")
        results = client.search_antennas(manufacturer="Ericsson")
        assert len(results) == 1
        assert results[0]["model"] == "AIR6468"

def test_antenna_to_pattern_shape():
    from aegis.integration.cloudrf import CloudRFClient
    import numpy as np
    client = CloudRFClient(api_key="test-key")
    # Simulate CloudRF antenna data with H/V arrays
    antenna_data = {
        "gain_dbd": 10.0,  # CloudRF reports gain in dBd
        "pattern_data": {
            "horizontal": [list(range(360)), [0.0] * 360],  # angles, relative gains in dBd
            "vertical": [list(range(360)), [0.0] * 360],
        }
    }
    pattern = client.antenna_to_pattern(antenna_data)
    assert pattern.gain_dbi.shape == (181, 360)
    # dBd + 2.15 = dBi, so 10.0 dBd peak -> 12.15 dBi
    assert pattern.max_gain_dbi == pytest.approx(12.15, abs=0.5)

def test_path_returns_signal_power():
    from aegis.integration.cloudrf import CloudRFClient
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "Signal power at receiver dBm": -65.3,
        "Computed path loss dB": 98.2,
    }
    mock_response.status_code = 200
    with patch("requests.Session.post", return_value=mock_response):
        client = CloudRFClient(api_key="test-key")
        result = client.path(50.85, 4.35, 30, 50.86, 4.36, 1.5, 3500, 2.0, 25.0)
        assert "Signal power at receiver dBm" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3.12 -m pytest tests/test_cloudrf_client.py -x -v`
Expected: ImportError

- [ ] **Step 3: Implement CloudRFClient**

Create `src/aegis/integration/cloudrf.py` with the class as specified in the spec. Key methods: `search_antennas`, `fetch_antenna`, `antenna_to_pattern`, `area`, `path`, `list_manufacturers`. The `area()` method builds a JSON request body from a base template (5G-CBand-sector.json structure) with overridden fields.

- [ ] **Step 4: Run tests**

Run: `python3.12 -m pytest tests/test_cloudrf_client.py -x -v`
Expected: All 3 PASS

- [ ] **Step 5: Lint and commit**

```bash
python3.12 -m ruff check src/aegis/integration/cloudrf.py tests/test_cloudrf_client.py
python3.12 -m ruff format src/aegis/integration/cloudrf.py tests/test_cloudrf_client.py
git add src/aegis/integration/cloudrf.py tests/test_cloudrf_client.py
git commit -m "Add CloudRF API client for pattern search and coverage"
```

---

### Task 10: CloudRF scenario template converter

**Files:**
- Create: `src/aegis/integration/cloudrf_templates.py`
- Create: `configs/presets/cloudrf/` (generated JSON files)

- [ ] **Step 1: Implement the converter**

Create `src/aegis/integration/cloudrf_templates.py` with `cloudrf_template_to_scenario(template_path)` that reads a CloudRF JSON template and returns an AEGIS scenario dict:

```python
def cloudrf_template_to_scenario(template_path: str) -> dict:
    with open(template_path) as f:
        t = json.load(f)
    freq_ghz = t["transmitter"]["frq"] / 1000
    power_w = t["transmitter"]["txw"]
    gain = t["antenna"]["txg"]
    power_dbm = 10 * math.log10(power_w * 1000) + gain  # EIRP
    name = t["template"]["name"]
    return {
        "description": f"{name} ({t['transmitter']['frq']} MHz, {gain} dBi)",
        "label": name.replace("-", " ").replace("_", " "),
        "icon": "radio",
        "instant": True,
        "autoCompute": True,
        "hidden": False,
        "webState": {
            "freqGhz": freq_ghz,
            "powerDbm": round(power_dbm, 1),
            "mode": "spatial",
        },
    }
```

Also add a `generate_all_presets()` function that scans the templates directory and writes AEGIS scenario configs to `configs/presets/cloudrf/`.

- [ ] **Step 2: Run the converter**

```bash
python3.12 -c "from aegis.integration.cloudrf_templates import generate_all_presets; generate_all_presets('/home/user/CloudRF-API-clients/templates', 'configs/presets/cloudrf')"
```

- [ ] **Step 3: Verify generated files**

Check that `configs/presets/cloudrf/` contains JSON files for the 7 key templates.

- [ ] **Step 4: Lint and commit**

```bash
python3.12 -m ruff check src/aegis/integration/cloudrf_templates.py
python3.12 -m ruff format src/aegis/integration/cloudrf_templates.py
git add src/aegis/integration/cloudrf_templates.py configs/presets/cloudrf/
git commit -m "Add CloudRF template converter and real-world scenario presets"
```

---

### Task 11: Coverage underlay and S_inc validation routes

**Files:**
- Modify: `src/aegis/viewer/routes/environment.py`
- Modify: `src/aegis/viewer/routes/compute.py`

- [ ] **Step 0: Add Pillow dependency**

In `pyproject.toml`, add `"Pillow"` to the `[project.optional-dependencies]` `viewer` list. This is needed for GeoTIFF-to-PNG conversion.

- [ ] **Step 1: Add /api/environment/coverage route**

In `environment.py`, add a route that:
1. Reads station list from request JSON
2. For each station, calls `CloudRFClient.area()` with station params
3. Converts TIFF response to PNG using PIL (`Image.open(BytesIO(tiff_bytes))`)
4. Returns PNG with `X-Bounds` and `X-Color-Key` headers
5. Caches by hash of station params

Guard the route: if `CLOUDRF_API_KEY` env var not set, return 501 with helpful error message.

- [ ] **Step 2: Add /api/validate/sinc route**

In `compute.py`, add a route that:
1. Computes AEGIS S_inc via free-space path loss (same as `paths_from_basestation`)
2. Calls `CloudRFClient.path()` for the same link
3. Returns comparison JSON

- [ ] **Step 3: Test coverage route manually (requires API key)**

This is an integration test that hits the real CloudRF API. Test with:
```bash
curl -X POST http://localhost:5000/api/environment/coverage -H "Content-Type: application/json" -d '{"stations": [{"lat": 50.853, "lon": 4.359, "alt": 30, "freq_mhz": 3500, "power_w": 2, "gain_dbi": 12, "azimuth": 0, "tilt": 6, "hbw": 65, "vbw": 10}], "radius_km": 0.5}'
```

- [ ] **Step 4: Lint and commit**

```bash
python3.12 -m ruff check src/aegis/viewer/routes/environment.py src/aegis/viewer/routes/compute.py
python3.12 -m ruff format src/aegis/viewer/routes/environment.py src/aegis/viewer/routes/compute.py
git add src/aegis/viewer/routes/environment.py src/aegis/viewer/routes/compute.py
git commit -m "Add CloudRF coverage underlay and S_inc validation routes"
```

---

## Phase D: Frontend

### Task 12: Exposure mode selector in ParametersPanel

**Files:**
- Modify: `aegis-web/src/stores/simulation.ts`
- Modify: `aegis-web/src/components/panels/ParametersPanel.tsx`
- Modify: `aegis-web/src/api/basestations.ts`

- [ ] **Step 1: Add exposureMode to simulation store**

In `simulation.ts`, add:
```typescript
exposureMode: 'theoretical' | 'actual_max' | 'typical'
setExposureMode: (mode: 'theoretical' | 'actual_max' | 'typical') => void
```
Default: `'theoretical'`. The setter updates state.

- [ ] **Step 2: Add toggle to ParametersPanel**

Below the power input, add a three-button group (similar to the existing mode selector pattern):
- "Theoretical", "Actual max", "Typical"
- Only rendered when `useBaseStationsStore.basestations.length > 0`
- Each button calls `setExposureMode()`

- [ ] **Step 3: Pass exposure_mode in compute request**

In `basestations.ts` API client, add `exposure_mode` to the compute request body from the simulation store.

- [ ] **Step 4: Build and verify**

```bash
cd aegis-web && npm run build
```
Expected: No TypeScript errors

- [ ] **Step 5: Commit**

```bash
git add aegis-web/src/stores/simulation.ts aegis-web/src/components/panels/ParametersPanel.tsx aegis-web/src/api/basestations.ts
git commit -m "Add exposure mode selector to viewer frontend"
```

---

### Task 13: Pattern browser panel

**Files:**
- Create: `aegis-web/src/api/patterns.ts`
- Create: `aegis-web/src/components/panels/PatternBrowserPanel.tsx`
- Modify: `aegis-web/src/components/layout/Sidebar.tsx` (add accordion section)
- Modify: `aegis-web/src/stores/simulation.ts` (add selectedPattern)

- [ ] **Step 1: Create patterns API client**

```typescript
// aegis-web/src/api/patterns.ts
export interface PatternSearchResult {
  id: string
  source: 'local' | 'cloudrf'
  manufacturer: string
  model: string
  frequency_mhz: number
  gain_dbi: number
  tilt_deg: number | null
}

export async function searchPatterns(params: {
  q?: string; manufacturer?: string; freq_min?: number; freq_max?: number;
  source?: string; limit?: number;
}): Promise<{ results: PatternSearchResult[] }> {
  const qs = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v != null) qs.set(k, String(v))
  }
  const res = await fetch(`/api/patterns/search?${qs}`)
  return res.json()
}

export async function loadPattern(source: string, id: string): Promise<Float32Array> {
  const res = await fetch(`/api/patterns/${source}/${id}`)
  const buf = await res.arrayBuffer()
  return new Float32Array(buf)
}
```

- [ ] **Step 2: Add selectedPattern to store**

In `simulation.ts`:
```typescript
selectedPattern: { source: string; id: string; metadata: PatternSearchResult } | null
setSelectedPattern: (p: { source: string; id: string; metadata: PatternSearchResult } | null) => void
```

- [ ] **Step 3: Create PatternBrowserPanel**

Create the panel with:
- Search input (debounced 300ms)
- Source tabs (All / Local / CloudRF)
- Scrollable results list showing manufacturer, model, freq, gain
- Click to select, "Apply" button to set `selectedPattern`
- Keep it simple for V1: no polar plot preview yet (add in follow-up)

- [ ] **Step 4: Add to sidebar**

In `Sidebar.tsx`, add `PatternBrowserPanel` as a new accordion item after the existing panels.

- [ ] **Step 5: Build and verify**

```bash
cd aegis-web && npm run build
```

- [ ] **Step 6: Commit**

```bash
git add aegis-web/src/api/patterns.ts aegis-web/src/components/panels/PatternBrowserPanel.tsx aegis-web/src/components/layout/Sidebar.tsx aegis-web/src/stores/simulation.ts
git commit -m "Add antenna pattern browser panel to viewer"
```

---

### Task 14: Coverage overlay and scenario presets

**Files:**
- Create: `aegis-web/src/components/scene/CoverageOverlay.tsx`
- Modify: `aegis-web/src/components/panels/BaseStationsPanel.tsx`
- Modify: `aegis-web/src/components/hud/ScenarioDropdown.tsx`

- [ ] **Step 1: Create CoverageOverlay component**

A Three.js `<mesh>` component:
- Renders a horizontal plane at y=0.01 (just above ground)
- Texture from `POST /api/environment/coverage` response (PNG as data URL)
- Positioned and scaled using X-Bounds header (converted from lat/lon to local ENU)
- Only rendered when `showCoverage` flag is true in basestations store

- [ ] **Step 2: Add toggle to BaseStationsPanel**

Checkbox: "Show coverage map (CloudRF)". Disabled with tooltip if CLOUDRF_API_KEY not configured (check via `/api/viewer-config` response).

- [ ] **Step 3: Add "Real-world radios" group to ScenarioDropdown**

Load CloudRF preset scenarios from config. Group them under a separate heading in the dropdown.

- [ ] **Step 4: Build and verify**

```bash
cd aegis-web && npm run build
```

- [ ] **Step 5: Commit**

```bash
git add aegis-web/src/components/scene/CoverageOverlay.tsx aegis-web/src/components/panels/BaseStationsPanel.tsx aegis-web/src/components/hud/ScenarioDropdown.tsx
git commit -m "Add CloudRF coverage overlay and real-world scenario presets"
```

---

## Final: Integration test and release

### Task 15: End-to-end integration test and cleanup

**Files:**
- Run full test suite
- Update exports
- Tag release

- [ ] **Step 1: Run full test suite**

```bash
python3.12 -m ruff check src/ tests/
python3.12 -m ruff format --check src/ tests/
python3.12 -m pytest tests/ -m "not slow" -x -v
```

- [ ] **Step 2: Run frontend build**

```bash
cd aegis-web && npm run build
```

- [ ] **Step 3: Update integration/__init__.py if needed**

Add CloudRF client to exports if appropriate.

- [ ] **Step 4: Final commit and push**

```bash
git push origin master
```

- [ ] **Step 5: Tag release**

This is a minor release (new features: pattern library, exposure modes, CloudRF integration).

```bash
git tag v0.9.0
git push origin master --tags
```
