# Realistic exposure modeling, antenna pattern library, and CloudRF integration

**Date**: 2026-04-01
**Status**: Approved
**Scope**: Three-pillar feature expansion: (1) unified antenna pattern library from 156k local MSI files + CloudRF API, (2) realistic exposure modes with TDD duty cycles, beam decomposition, and sidelobe modeling, (3) CloudRF API integration for coverage validation and scenario templates.
**Depends on**: 2026-03-29-basestation-antenna-upgrade-design.md (classification, panel rendering, MIMO compute)

## Problem

AEGIS computes theoretical maximum exposure only. Real 5G networks operate at roughly 32% of theoretical maximum due to TDD duty cycles, beam sweeping overhead, and traffic loading (IEC 62232:2022, Table C.2). This makes AEGIS predictions 3-5x conservative, which undermines credibility for compliance consulting and monograph validation.

The synthetic Gaussian antenna pattern has no sidelobes (rolls to zero), which is unrealistic. Real sector antennas have a sidelobe floor 15-20 dB below peak. And AEGIS has no way to use real measured antenna patterns from manufacturers, despite having 156k MSI files on disk and access to CloudRF's 1,241-pattern API database.

## Goals

1. Unified antenna pattern library: searchable catalog spanning local MSI files, CloudRF API, and synthetic generation. User picks a pattern, gets an `AntennaPattern(181, 360)`.
2. Three exposure modes: theoretical max (current), actual max (TDD + PRF), typical (+ traffic load). Exposed in the viewer with clear labeling.
3. mMIMO broadcast/traffic beam decomposition for non-served user exposure assessment.
4. Sidelobe floor on synthetic patterns.
5. CloudRF thin client for coverage underlays, S_inc validation, and pattern search.
6. Scenario presets derived from CloudRF's 32 real-world radio templates.

## Non-goals

- Full CloudRF client library or downloading their entire database.
- Using CloudRF as a propagation backend (it does not expose per-ray data).
- Full 3D theta x phi antenna patterns (neither MSI nor CloudRF provides them; the separable H x V reconstruction is industry standard).
- Per-element mMIMO patterns from external sources (synthetic broadcast + traffic model is more physically accurate than vendor envelope patterns for dosimetry purposes).
- Replacing DiffeRT as the ray tracer.

---

## Design

### 1. Antenna pattern library

#### Architecture

```
AntennaPatternLibrary
  ├── LocalIndex        (SQLite, built from MSI zips, ~156k entries)
  ├── CloudRFProvider   (REST API, 1,241 entries, live search)
  └── SyntheticProvider (existing pattern.py, enhanced with sidelobe floor)
```

All three providers return the same type: `AntennaPattern(181, 360)` from `basestation/antenna.py`.

#### MSI parser

New file: `src/aegis/basestation/msi.py`

MSI format is a text file with a header block followed by two 360-row data sections (HORIZONTAL and VERTICAL). Each row is `angle attenuation_dB` where attenuation is relative to peak (0 = peak, positive values = loss below peak).

```python
@dataclass(frozen=True)
class MSIMetadata:
    name: str
    manufacturer: str          # inferred from zip directory structure
    frequency_mhz: float
    gain_dbi: float
    tilt_deg: float
    source_zip: str            # e.g. "Kathrein.zip"
    source_path: str           # e.g. "Kathrein/1800MHz/731620X7.MSI"

def parse_msi(text: str) -> tuple[MSIMetadata, np.ndarray, np.ndarray]:
    """Parse MSI text into metadata + H-plane (360,) + V-plane (360,) attenuation arrays."""

def msi_to_antenna_pattern(
    h_atten: np.ndarray,
    v_atten: np.ndarray,
    gain_dbi: float,
) -> AntennaPattern:
    """Reconstruct 2D pattern from H/V cuts using the separable assumption.
    
    gain_2d[elev, azim] = gain_dbi - h_atten[azim] - v_atten[elev_mapped]
    
    MSI vertical plane convention: 0 degrees = boresight (horizontal forward),
    90 = zenith, 180 = back, 270 = nadir. This is NOT the same as AntennaPattern
    elevation which uses -90 (nadir) to +90 (zenith).
    
    Remapping: MSI V-plane index i (0..359) maps to angle (i) degrees from boresight.
    Convert to elevation: elevation = 90 - msi_angle (for 0..180), wrapping for 180..360.
    Specifically: elevation[i] = 90 - i for i in 0..180, elevation[i] = 90 - (i-360) for i in 181..359.
    Then resample to the 181-point grid covering -90..+90.
    """
```

The separable reconstruction (`gain = peak - h_loss - v_loss`) is the 3GPP TR 38.901 Section 7.3 standard. It works well for passive sector antennas. It breaks down for antennas with strong cross-coupling between planes, but those are active antennas that should use the synthetic beam model anyway.

**Convention detection:** Some MSI files use 0 = horizontal boresight (most common, matches the convention above). Others use 0 = north/zenith. The parser detects the convention by checking if the V-plane attenuation at index 0 is 0.0 dB (boresight convention) or if the minimum attenuation appears at index 90 (zenith-origin convention). A flag `vertical_convention: "boresight" | "zenith"` in `MSIMetadata` records which was detected.

#### Local index (SQLite)

New file: `src/aegis/basestation/library.py`

```python
class AntennaPatternLibrary:
    """Unified antenna pattern search across local MSI files and CloudRF API."""
    
    def __init__(self, data_dir: str, cloudrf_api_key: str | None = None):
        self._db_path = Path(data_dir) / "antenna_patterns" / "index.sqlite"
        self._msi_dir = Path(data_dir) / "antenna_patterns" / "msi_raw"
        self._cloudrf = CloudRFPatternProvider(cloudrf_api_key) if cloudrf_api_key else None
    
    def build_index(self) -> int:
        """Scan all MSI zips, parse headers (not full patterns), write SQLite index.
        Returns number of indexed patterns. Idempotent: drops and rebuilds."""
    
    def search(
        self,
        query: str = "",                    # free text: matches manufacturer or model
        manufacturer: str | None = None,
        freq_min_mhz: float | None = None,
        freq_max_mhz: float | None = None,
        gain_min_dbi: float | None = None,
        gain_max_dbi: float | None = None,
        source: str = "all",                # "local", "cloudrf", "all"
        limit: int = 50,
    ) -> list[PatternSearchResult]:
        """Search local index, optionally also CloudRF. Local results first."""
    
    def load_pattern(self, source: str, pattern_id: str) -> AntennaPattern:
        """Load full pattern by source and ID.
        source="local": extract MSI from zip, parse, reconstruct 2D.
        source="cloudrf": fetch via API, convert H/V to 2D.
        source="synthetic": generate from beamwidth params in pattern_id.
        """
```

SQLite schema:
```sql
CREATE TABLE patterns (
    id TEXT PRIMARY KEY,           -- "{zip_stem}/{internal_path}" e.g. "Kathrein/1800MHz/731620X7"
    manufacturer TEXT NOT NULL,
    model TEXT NOT NULL,           -- filename stem e.g. "731620X7"
    frequency_mhz REAL,
    gain_dbi REAL,
    tilt_deg REAL,
    source_zip TEXT NOT NULL,
    source_path TEXT NOT NULL,
    UNIQUE(source_zip, source_path)
);
CREATE INDEX idx_manufacturer ON patterns(manufacturer);
CREATE INDEX idx_freq ON patterns(frequency_mhz);
CREATE INDEX idx_model ON patterns(model);
```

Build command: `python -m aegis.basestation.library build` (or auto-builds on first search if index missing).

Expected: ~156k entries, ~5 MB database file, builds in under 30 seconds. Scanning zips with `zipfile.ZipFile` and reading only the first 10 lines of each MSI file for header parsing. No full pattern extraction during indexing.

#### CloudRF pattern provider

New file: `src/aegis/integration/cloudrf.py`

```python
class CloudRFClient:
    """Thin CloudRF API client. Only the endpoints AEGIS actually uses."""
    
    BASE_URL = "https://api.cloudrf.com"
    
    def __init__(self, api_key: str):
        self._key = api_key
        self._session = requests.Session()
        self._session.headers["key"] = api_key
    
    # Pattern search
    def search_antennas(
        self, manufacturer: str = "", model: str = "",
        freq_lower: float = 0, freq_upper: float = 100000,
        gain_lower: float = -10, gain_upper: float = 50,
        page: int = 1,
    ) -> list[dict]: ...
    
    def fetch_antenna(self, antenna_id: int) -> dict:
        """Returns full antenna detail including pattern_data with horizontal/vertical arrays."""
    
    def antenna_to_pattern(self, antenna_data: dict) -> AntennaPattern:
        """Convert CloudRF H/V arrays to AntennaPattern(181, 360).
        CloudRF returns gain in dBd (relative to dipole). Convert: dBi = dBd + 2.15.
        Reconstruction same as MSI: separable assumption."""
    
    # Coverage (for underlay and validation)
    def area(
        self, lat: float, lon: float, alt: float, freq_mhz: float,
        power_w: float, gain_dbi: float, azimuth: float, tilt: float,
        hbw: float, vbw: float, radius_km: float = 2, res_m: int = 10,
        propagation_model: int = 1,  # ITM by default
    ) -> bytes:
        """Returns GeoTIFF bytes of coverage heatmap."""
    
    def path(
        self, tx_lat: float, tx_lon: float, tx_alt: float,
        rx_lat: float, rx_lon: float, rx_alt: float,
        freq_mhz: float, power_w: float, gain_dbi: float,
    ) -> dict:
        """Point-to-point link budget. Returns signal_power_dbm, path_loss_db, etc."""
    
    def list_manufacturers(self) -> list[dict]: ...
```

The `area()` and `path()` methods use CloudRF JSON templates as a base, overriding the transmitter/receiver/antenna/output fields. Propagation model defaults to ITM (Longley-Rice, `pm=1`), the FCC standard.

#### API endpoints

New route file: `src/aegis/viewer/routes/patterns.py`

```
GET  /api/patterns/search?q=kathrein&freq_min=1700&freq_max=1900&source=all&limit=50
GET  /api/patterns/{source}/{id}          # source: "local" or "cloudrf"; id uses Flask <path:id> to handle slashes in local IDs
GET  /api/patterns/manufacturers
POST /api/patterns/build-index            # trigger index rebuild
```

Response format for search:
```json
{
  "results": [
    {
      "id": "Kathrein/1800MHz/731620X7",
      "source": "local",
      "manufacturer": "Kathrein",
      "model": "731620X7",
      "frequency_mhz": 1767.5,
      "gain_dbi": 8.15,
      "tilt_deg": 0.0
    },
    {
      "id": "447",
      "source": "cloudrf",
      "manufacturer": "Ericsson",
      "model": "AIR6468",
      "frequency_mhz": 3500.0,
      "gain_dbi": 28.0,
      "tilt_deg": null
    }
  ],
  "total_local": 156000,
  "total_cloudrf": 1241
}
```

Response format for pattern fetch (binary):
```
Content-Type: application/octet-stream
X-Meta: {"manufacturer": "Kathrein", "model": "731620X7", "gain_dbi": 8.15, ...}
Body: float32 array (181 * 360 = 65160 values) in row-major order
```

#### Frontend: pattern browser

New component: `aegis-web/src/components/panels/PatternBrowserPanel.tsx`

Located in the sidebar as a new accordion section "Antenna patterns". Contains:

- Search input with 300ms debounce
- Source filter: tabs for "All", "Local", "CloudRF", "Synthetic"
- Results table: manufacturer, model, freq (MHz), gain (dBi)
- Scroll-to-load pagination (50 results per page)
- Click row to preview: shows H-plane and V-plane polar plot (SVG, client-side rendered from the 360-point arrays)
- "Apply to antenna" button: sets the pattern on the current single-antenna or selected base station
- "Auto-match" button (base stations mode): for each loaded station, searches local index by model substring, assigns first match

New store additions in `simulation.ts`:
```typescript
selectedPattern: {
  source: 'local' | 'cloudrf' | 'synthetic'
  id: string
  metadata: PatternMetadata
} | null
```

### 2. Realistic exposure model

#### ExposureConfig (separate from BaseStation)

`BaseStation` is a frozen dataclass representing pure antenna metadata from the cell tower database. Exposure policy parameters do not belong on it because they are mode-dependent, not intrinsic to the hardware. A separate `ExposureConfig` is produced during classification.

New dataclass in `src/aegis/basestation/antenna.py`:

```python
@dataclass(frozen=True)
class ExposureConfig:
    """Exposure reduction parameters for realistic modeling."""
    duplex_mode: str = "fdd"              # "fdd" or "tdd"
    tdd_dl_ratio: float = 1.0            # DL fraction: 1.0 for FDD, 0.75 for TDD (DDDSU)
    power_reduction_factor: float = 1.0   # IEC 62232 PRF: 1.0 for sector, 0.32 for mMIMO traffic
    traffic_load_factor: float = 0.5      # Average cell utilization, must be > 0
```

`classify_basestation()` returns `ExposureConfig` alongside the existing classification dict. `BaseStation` itself is unchanged. The viewer route stores exposure configs in a parallel list indexed by station index.

Default values by archetype (populated during classification):

| Field | sector | mmimo | small_cell |
|-------|--------|-------|------------|
| duplex_mode | "fdd" | "tdd" | "fdd" |
| tdd_dl_ratio | 1.0 | 0.75 | 1.0 |
| power_reduction_factor | 1.0 | 0.32 | 1.0 |
| traffic_load_factor | 0.5 | 0.5 | 0.3 |

These defaults are overridable in config JSON under `basestations.exposure_defaults`.

Technology-based duplex inference: if `freq_mhz >= 2500` and technology contains "5G", set `duplex_mode = "tdd"` and `tdd_dl_ratio = 0.75`. This catches the common case (3.5 GHz TDD NR). FDD bands (700, 800, 900, 1800, 2100) keep ratio 1.0.

#### Exposure modes

New enum and logic in `src/aegis/basestation/power.py`:

```python
class ExposureMode(str, Enum):
    THEORETICAL = "theoretical"   # Full EIRP, no reduction
    ACTUAL_MAX = "actual_max"     # TDD + PRF applied
    TYPICAL = "typical"           # TDD + PRF + traffic load

def effective_eirp_dbm(
    bs: BaseStation,
    exposure: ExposureConfig,
    mode: ExposureMode,
) -> float:
    """Compute effective EIRP accounting for exposure mode.
    
    Takes BaseStation (hardware metadata) and ExposureConfig (policy) separately.
    Factor is clamped to >= 1e-10 to avoid log10(0) when traffic_load_factor is near zero.
    """
    factor = 1.0
    if mode in (ExposureMode.ACTUAL_MAX, ExposureMode.TYPICAL):
        factor *= exposure.tdd_dl_ratio
        factor *= exposure.power_reduction_factor
    if mode == ExposureMode.TYPICAL:
        factor *= exposure.traffic_load_factor
    factor = max(factor, 1e-10)
    return bs.eirp_dbm + 10 * math.log10(factor)
```

Integration point: `paths_from_basestation()` in `adapter.py` gains `exposure_mode` and `exposure_config` parameters. It calls `effective_eirp_dbm(bs, exposure, mode)` instead of using `bs.eirp_dbm` directly. `paths_from_basestations()` (plural) also gains these parameters and passes them through, looking up the per-station `ExposureConfig` from a parallel list. The route handler in `basestations.py` receives `exposure_mode` from the request JSON, retrieves per-station `ExposureConfig` objects from the classification cache, and passes both to the adapter. The `_bs_summary()` function in `basestations.py` is extended to include `exposure_config` fields (duplex_mode, tdd_dl_ratio, power_reduction_factor, traffic_load_factor) in its JSON response so the frontend can display effective power.

For mMIMO antennas in `actual_max` or `typical` mode, the beam decomposition logic (broadcast + traffic) replaces the normal single-path computation within `paths_from_basestation()`. The function checks the archetype from `ExposureConfig` context and dispatches accordingly. In `theoretical` mode or for non-mMIMO antennas, the existing single-path logic is unchanged.

#### mMIMO beam decomposition

New dataclass in `src/aegis/basestation/antenna.py`:

```python
@dataclass(frozen=True)
class BeamConfig:
    """mMIMO broadcast/traffic beam separation for realistic exposure."""
    broadcast_gain_dbi: float = 18.0      # SSB/PBCH wide beam
    broadcast_hbw_deg: float = 65.0
    broadcast_vbw_deg: float = 10.0
    traffic_gain_dbi: float = 25.0        # Narrow traffic beam
    traffic_hbw_deg: float = 12.0
    traffic_vbw_deg: float = 8.0
    sweep_h_range_deg: float = 60.0       # Traffic beam sweep: +/- from boresight
    sweep_v_range_deg: float = 15.0
```

Beam decomposition logic in `adapter.py`:

For mMIMO antennas in `actual_max` or `typical` mode, exposure at a point is the **maximum** of broadcast and traffic contributions:

1. Compute broadcast power: always-on, uses broadcast beam pattern (wide synthetic from `broadcast_hbw/vbw`), power = `eirp * tdd_dl_ratio` (broadcast is always active during DL).

2. Compute traffic power: only if the body is within the sweep range (`|azimuth_local| < sweep_h_range` AND `|elevation_local| < sweep_v_range`). Uses traffic beam pattern (narrow synthetic from `traffic_hbw/vbw`), power = `eirp * tdd_dl_ratio * prf`. In typical mode, multiply by `traffic_load_factor`.

3. Combine beams depending on mode:
   - **actual_max**: `power = max(broadcast_power, traffic_power)`. This is the conservative upper bound, appropriate for compliance assessment. Not time-averaged, but the worst-case instantaneous exposure at any point.
   - **typical**: `power = broadcast_power + traffic_power * traffic_load_factor`. This is a time-weighted sum reflecting actual average exposure. The broadcast beam runs continuously during DL time, while the traffic beam visits this direction only a fraction of the time proportional to cell load.

For `theoretical` mode: existing behavior unchanged (full EIRP, single pattern).

`classify_basestation()` gains a `beam_config` field in its return dict, populated from config defaults with the option to override per antenna.

#### Sidelobe floor

Modify `src/aegis/basestation/pattern.py`:

```python
def synthetic_pattern_from_beamwidth(
    hpbw_h_deg: float,
    hpbw_v_deg: float,
    gain_dbi: float,
    sidelobe_suppression_db: float = 15.0,   # NEW parameter
) -> AntennaPattern:
```

Implementation: after computing the Gaussian gain matrix, apply a floor:

```python
floor_dbi = gain_dbi - sidelobe_suppression_db
gain_matrix = np.maximum(gain_matrix, floor_dbi)
```

This gives a flat sidelobe level 15 dB below peak in all directions beyond the main lobe. Real antennas have structured sidelobes, but a flat floor is conservative and matches the ITU-R F.1336-5 recommendation for cases where sidelobe data is unavailable.

The parameter is exposed in config under `basestations.exposure.sidelobe_suppression_db` and defaults to 15.0.

### 3. CloudRF integration

#### Coverage underlay

New route in `src/aegis/viewer/routes/environment.py`:

```
POST /api/environment/coverage
```

Request:
```json
{
  "stations": [
    {
      "lat": 50.853, "lon": 4.359, "alt": 29.67,
      "freq_mhz": 3750, "power_w": 2.0, "gain_dbi": 24.8,
      "azimuth": 150, "tilt": 6,
      "hbw": 65, "vbw": 10
    }
  ],
  "radius_km": 1.0,
  "resolution_m": 10,
  "propagation_model": 1
}
```

Flow:
1. For each station, call `CloudRFClient.area()` with appropriate parameters.
2. Download GeoTIFF (WGS84 projection).
3. If multiple stations, call CloudRF `/mesh` to merge into best-server composite.
4. Convert GeoTIFF to PNG with geo bounds for frontend overlay.
5. Cache result keyed by hash of station parameters + radius.

Response:
```
Content-Type: image/png
X-Bounds: {"north": 50.86, "south": 50.84, "east": 4.37, "west": 4.35}
X-Color-Key: [{"label": "-60dBm", "r": 0, "g": 0, "b": 255}, ...]
```

Rate limiting: CloudRF free tier allows 50 requests/month. The route checks a counter file and warns (HTTP 429) if approaching the limit. Cached results do not count.

Frontend: new `CoverageOverlay.tsx` scene component. Renders a textured plane at ground level, positioned and scaled using the geo bounds. Toggle in the base stations panel: "Show coverage map" checkbox.

#### S_inc validation

New route in `src/aegis/viewer/routes/compute.py`:

```
POST /api/validate/sinc
```

Request:
```json
{
  "tx_lat": 50.853, "tx_lon": 4.359, "tx_alt": 29.67,
  "rx_lat": 50.854, "rx_lon": 4.360, "rx_alt": 1.5,
  "freq_mhz": 3750, "power_w": 2.0, "gain_dbi": 24.8
}
```

Response:
```json
{
  "aegis_sinc_wm2": 0.0023,
  "aegis_sinc_dbm": -26.4,
  "cloudrf_sinc_dbm": -28.1,
  "delta_db": 1.7,
  "cloudrf_model": "ITM (Longley-Rice)",
  "cloudrf_path_loss_db": 98.2,
  "distance_m": 142.3
}
```

This is a development/validation tool, not user-facing. Useful for monograph validation tables.

#### Scenario templates

New file: `src/aegis/integration/cloudrf_templates.py`

Converter that reads CloudRF JSON templates from `/home/user/CloudRF-API-clients/templates/` and produces AEGIS scenario configs.

```python
def cloudrf_template_to_scenario(template_path: str) -> dict:
    """Convert a CloudRF JSON template to an AEGIS scenario dict.
    
    Maps:
      transmitter.frq (MHz) -> webState.freqGhz
      transmitter.txw (W) -> webState.powerDbm (via w_to_dbm + gain)
      antenna.txg, antenna.hbw, antenna.vbw -> pattern params
      template.name -> scenario label
    """
```

Run once to generate `configs/presets/cloudrf/` directory with scenario JSON files. These appear in the viewer scenario dropdown under a "Real-world radios" group. Templates to convert (most useful):

- 5G-CBand-sector (3500 MHz, 12 dBi sector)
- LTE-eNodeB-B3-RSRP (1800 MHz, eNB)
- LoRa-GW-EU (868 MHz, IoT gateway)
- WiFi-2.4G-AP-Omni (2400 MHz, indoor AP)
- PMR446-Mobile (446 MHz, handheld)
- MOTO-DMR-470M (470 MHz, DMR repeater)
- Starlink_12GHz_UE (12 GHz, satellite terminal)

### 4. Frontend changes

#### Exposure mode selector

In `ParametersPanel.tsx`, below the power input, add a three-way toggle:

```
[Theoretical] [Actual max] [Typical]
```

- Only visible when base stations are loaded (single-antenna mode always uses theoretical).
- When mode changes, the "effective power" display updates to show the reduced value.
- Tooltip on each button explains what it means.

New store field in `simulation.ts`:
```typescript
exposureMode: 'theoretical' | 'actual_max' | 'typical'  // default: 'theoretical'
```

Passed to `/api/basestations/compute` as `exposure_mode` parameter.

#### Pattern browser

New accordion panel "Antenna patterns" in sidebar. See section 1 for full specification.

#### Coverage overlay toggle

New checkbox "Show coverage map (CloudRF)" in the base stations panel, below the compute button. Disabled if no CloudRF API key configured. Grayed out with tooltip "Configure CLOUDRF_API_KEY" when key is missing.

#### Scenario dropdown expansion

The scenario dropdown groups scenarios:

```
AEGIS scenarios
  Open ground (28 GHz)
  mmWave close (60 GHz)
  Urban Ghent

Real-world radios (CloudRF)
  5G C-Band macro (3.5 GHz)
  LTE eNodeB B3 (1.8 GHz)
  LoRa EU gateway (868 MHz)
  WiFi 2.4 GHz AP
  PMR446 handheld
  ...
```

The "Real-world radios" section sets frequency, power, and optionally a matched antenna pattern from the library.

### 5. Config additions

Under `basestations` in DEFAULTS:

```python
"exposure": {
    "default_mode": "theoretical",
    "defaults_by_archetype": {
        "sector": {
            "duplex_mode": "fdd",
            "tdd_dl_ratio": 1.0,
            "power_reduction_factor": 1.0,
            "traffic_load_factor": 0.5
        },
        "mmimo": {
            "duplex_mode": "tdd",
            "tdd_dl_ratio": 0.75,
            "power_reduction_factor": 0.32,
            "traffic_load_factor": 0.5
        },
        "small_cell": {
            "duplex_mode": "fdd",
            "tdd_dl_ratio": 1.0,
            "power_reduction_factor": 1.0,
            "traffic_load_factor": 0.3
        }
    },
    "sidelobe_suppression_db": 15.0,
    "beam_config": {
        "broadcast_gain_dbi": 18.0,
        "broadcast_hbw_deg": 65.0,
        "broadcast_vbw_deg": 10.0,
        "traffic_gain_dbi": 25.0,
        "traffic_hbw_deg": 12.0,
        "traffic_vbw_deg": 8.0,
        "sweep_h_range_deg": 60.0,
        "sweep_v_range_deg": 15.0
    }
},
"pattern_library": {
    "cloudrf_api_key_env": "CLOUDRF_API_KEY",
    "auto_build_index": true
}
```

### 6. Testing

**Unit tests:**

- `tests/test_msi_parser.py`: Parse known Kathrein MSI file, verify header fields, verify H/V array shapes and values. Verify 2D reconstruction produces correct gain at boresight, at -3 dB points, and at back lobe. Explicit test for V-plane elevation remapping: boresight (elevation 0) must map to peak gain, zenith (elevation +90) and nadir (elevation -90) must map to attenuated values. Test convention detection on both boresight-origin and zenith-origin MSI files.
- `tests/test_pattern_library.py`: Build index from test fixtures (small zip with 5 MSI files), verify search by manufacturer/model/freq/gain, verify pattern loading and shape.
- `tests/test_exposure_modes.py`: Verify `effective_eirp_dbm()` for all three modes against hand-calculated values. Verify beam decomposition: broadcast vs traffic power at various angles relative to boresight and sweep range boundaries.
- `tests/test_sidelobe.py`: Verify synthetic pattern with sidelobe floor has minimum gain = `peak - suppression_db` everywhere.
- `tests/test_cloudrf_client.py`: Mock HTTP responses, verify template conversion, verify pattern format conversion (dBd to dBi, H/V to 2D).

**Integration tests (marked slow):**

- Load Brussels base stations, classify, verify exposure mode power scaling matches IEC 62232 reference values.
- Build real MSI index from actual zip files, search for "Kathrein 742", verify results returned.
- End-to-end: load station, assign MSI pattern, compute dosimetry in actual_max mode, verify SAB is lower than theoretical mode.

### 7. File change summary

| File | Change |
|---|---|
| `src/aegis/basestation/msi.py` | New: MSI parser |
| `src/aegis/basestation/library.py` | New: AntennaPatternLibrary with SQLite index |
| `src/aegis/basestation/antenna.py` | Add ExposureConfig and BeamConfig dataclasses (BaseStation unchanged) |
| `src/aegis/basestation/pattern.py` | Add sidelobe_suppression_db parameter |
| `src/aegis/basestation/power.py` | Add ExposureMode enum, effective_eirp_dbm() |
| `src/aegis/basestation/adapter.py` | Add exposure_mode + exposure_config parameters to path functions, beam decomposition logic |
| `src/aegis/basestation/classify.py` | Return ExposureConfig and BeamConfig from classification |
| `src/aegis/integration/cloudrf.py` | New: CloudRFClient (patterns, area, path) |
| `src/aegis/integration/cloudrf_templates.py` | New: template-to-scenario converter |
| `src/aegis/viewer/routes/patterns.py` | New: pattern search/fetch API |
| `src/aegis/viewer/routes/environment.py` | Add /api/environment/coverage route |
| `src/aegis/viewer/routes/compute.py` | Add /api/validate/sinc route |
| `src/aegis/viewer/routes/basestations.py` | Add exposure_mode to compute, ExposureConfig to cache and _bs_summary |
| `src/aegis/viewer/config.py` | Add exposure and pattern_library config blocks |
| `aegis-web/src/components/panels/PatternBrowserPanel.tsx` | New: pattern search UI |
| `aegis-web/src/components/panels/ParametersPanel.tsx` | Add exposure mode toggle |
| `aegis-web/src/components/panels/BaseStationsPanel.tsx` | Add coverage overlay toggle |
| `aegis-web/src/components/scene/CoverageOverlay.tsx` | New: ground-plane coverage texture |
| `aegis-web/src/components/hud/ScenarioDropdown.tsx` | Add "Real-world radios" group |
| `aegis-web/src/stores/simulation.ts` | Add exposureMode, selectedPattern |
| `aegis-web/src/api/patterns.ts` | New: pattern search/fetch API client |
| `configs/presets/cloudrf/*.json` | New: converted CloudRF scenario configs |
| `tests/test_msi_parser.py` | New |
| `tests/test_pattern_library.py` | New |
| `tests/test_exposure_modes.py` | New |
| `tests/test_sidelobe.py` | New |
| `tests/test_cloudrf_client.py` | New |

### 8. Dependencies

- `requests` (already in deps, used by CloudRF client)
- `Pillow` (PIL) for GeoTIFF-to-PNG conversion in the coverage underlay route. CloudRF returns standard TIFF files that PIL can read. If CRS metadata parsing is needed, `rasterio` is the fallback, but initial implementation uses PIL only. Added to `[viewer]` extra.
- SQLite is stdlib. MSI parsing is pure string manipulation.
- Frontend: no new npm packages. Pattern polar plots rendered with SVG path elements.

### 9. Phasing

The three pillars are largely independent and can be built in parallel:

**Phase A (pattern library):** MSI parser, SQLite index, library class, API routes, frontend browser. No CloudRF dependency.

**Phase B (realistic exposure):** New BaseStation fields, ExposureMode, beam decomposition, sidelobe floor, frontend toggle. No pattern library dependency.

**Phase C (CloudRF integration):** Client, pattern provider, coverage underlay, S_inc validation, scenario templates. Depends on API key availability.

Phase A and B can ship together. Phase C can follow independently.
