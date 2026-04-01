# Base station master dataset

Design for a build-time pipeline that stacks multiple data sources per region, fills gaps with statistical estimation, and tracks per-field provenance through to the frontend.

## Context

AEGIS computes absorbed power density on human bodies from real base station deployments. The `basestations/` library (basestationLib) extracts antenna data from 8 European government APIs into a standardized 16-column CSV. The viewer loads these CSVs and runs dosimetry.

The problem: Brussels provides 100% of all 16 fields including radiation patterns. France gives location, height, frequency, and azimuth but no power, tilt, gain, or beamwidth. Hungary gives only location and frequency. The existing estimation module fills gaps with (Technology + FrequencyBand) medians, but there is no tracking of which values are measured vs estimated.

The goal: a master dataset that stacks government data, crowdsourced data (OpenCellID), and statistical estimation, tracking provenance per field, and communicating data quality to the user in the frontend.

## Research

Full source research in `docs/internal/base-station-data-sources.md`. Key findings:

- Brussels environnement.brussels is the richest public antenna database globally (100% on all 16 columns + 22K radiation patterns)
- Denmark Mastedatabasen has the best open API in Europe (JSON:API with bbox queries)
- Australia ACMA RRL and Canada ISED SMS have per-site RF parameters (unlike US FCC)
- CellMapper is most accurate but TOS blocks academic use
- OpenCellID provides location-only fallback (no power, azimuth, tilt, gain)
- The US is a dead end for per-site cellular data due to geographic area licensing
- MSI antenna pattern libraries (400K files free at wireless-planning.com, CommScope BSAPatternsWeb) can supplement radiation patterns

## Data model

### BaseStation dataclass changes

Add two fields to the existing frozen dataclass in `src/aegis/basestation/antenna.py`:

```python
@dataclass(frozen=True)
class FieldSource:
    origin: str        # "gov:brussels", "gov:anfr", "opencellid", "est:tech+band", "est:ref", "missing"
    confidence: float  # 0.0-1.0, always field-level (not aggregate)

@dataclass(frozen=True)
class BaseStation:
    # ... existing 15 scalar fields + pattern ...
    frequency_band: str                             # NEW: e.g. "Band3600MHz"
    provenance: tuple[tuple[str, FieldSource], ...]  # NEW: tuple of (field_name, source) pairs
    pattern_source: str = ""                         # NEW: "gov:brussels", "msi:kathrein_742215", "3gpp:tr38901", "synthetic:gaussian", ""
```

Using `tuple[tuple[str, FieldSource], ...]` instead of `dict` because `BaseStation` is frozen. A helper property can provide dict-like access:

```python
@property
def provenance_dict(self) -> dict[str, FieldSource]:
    return dict(self.provenance)
```

Note: existing tests that compare `BaseStation` with `==` need updating since provenance is now part of equality. Construct test fixtures with `provenance=()` to maintain old behavior.

### Confidence scoring

Per-field confidence (stored in `FieldSource.confidence`):
- Government source, direct measurement: 1.0
- Government source, operator self-report: 0.8
- Crowdsourced (OpenCellID): 0.5
- Estimated from same-dataset (Technology + Band) median: 0.3
- Estimated from reference dataset: 0.2
- Missing (NaN): 0.0

Per-antenna aggregate confidence is computed on the fly in `_bs_summary()` (not stored on `BaseStation`). Weighted average of per-field scores using these weights, keyed by `BaseStation` field name:

| BaseStation field | Weight | Rationale |
|---|---|---|
| `eirp_dbm` | 5 | Directly scales Sab |
| `azimuth_deg` | 4 | Determines beam direction |
| `height_m` | 3 | Affects distance and elevation angle |
| `freq_mhz` | 3 | Determines tissue properties and wavelength |
| `gain_dbi` | 2 | Scales beam intensity |
| `electrical_tilt_deg` | 1 | Typical range 0-10 deg, moderate impact at close range |
| `mechanical_tilt_deg` | 1 | Same as electrical tilt |
| `horizontal_beamwidth_deg` | 1 | Shapes envelope |
| `vertical_beamwidth_deg` | 1 | Shapes envelope |

Pattern source is not included in the numeric confidence score but is exposed separately in the API response via `pattern_source`.

### Parquet schema

Merged Parquet files use the 16 standard columns plus `_source` suffix columns for all numeric fields:

```
SiteCode, AntennaLabel, Operator, Technology, Latitude, Longitude,
CenterHeight, Power, Frequency, FrequencyBand, Electrical_Tilt,
Mechanical_Tilt, Azimuth, Gain, Horizontal_Beamwidth, Vertical_Beamwidth,
CenterHeight_source, Power_source, Frequency_source, FrequencyBand_source,
Electrical_Tilt_source, Mechanical_Tilt_source, Azimuth_source, Gain_source,
Horizontal_Beamwidth_source, Vertical_Beamwidth_source, Pattern_source
```

Column name mapping to `BaseStation` fields (for the implementing agent):
- `Power` (DataFrame) = `eirp_dbm` (BaseStation), unit is dBm EIRP
- `CenterHeight` = `height_m`
- `Frequency` = `freq_mhz` (MHz)
- `Azimuth` = `azimuth_deg`
- `Electrical_Tilt` = `electrical_tilt_deg`
- `Mechanical_Tilt` = `mechanical_tilt_deg`
- `Gain` = `gain_dbi`
- `Horizontal_Beamwidth` = `horizontal_beamwidth_deg`
- `Vertical_Beamwidth` = `vertical_beamwidth_deg`

Source values are short strings: `"gov:brussels"`, `"gov:anfr"`, `"gov:mastedatabasen"`, `"est:tech+band"`, `"est:ref"`, `"ocid"`, `"missing"`. Location and operator always come from the primary source and don't need provenance columns.

## Build pipeline

### Directory layout

```
data/basestations/
  raw/                          # One Parquet per source extraction
    brussels_gov.parquet
    flanders_gov.parquet
    denmark_mastedatabasen.parquet
    france_anfr.parquet
    opencellid_be.parquet
  merged/                       # One Parquet per region, ready for viewer
    brussels.parquet
    flanders.parquet
    denmark.parquet
    france.parquet
  patterns/                     # Radiation patterns
    brussels.mat
    flanders.mat
  regions.yaml                  # Build configuration
```

Reference datasets for cross-region estimation are specified by path in `regions.yaml`, not symlinks (avoids Windows compatibility issues).

### Build script: `src/aegis/basestation/build.py`

CLI with three stages:

**Stage 1: Extract** - Calls basestationLib adapters, writes raw Parquet. No estimation. Skips if raw file exists and is fresh (mtime check or `--force`).

```bash
python -m aegis.basestation.build extract --region brussels
python -m aegis.basestation.build extract --region france --bbox 2.0,2.6,48.7,49.0
```

**Stage 2: Merge** - Loads all raw files for a region, stacks with priority ordering, deduplicates spatially, picks best value per field, runs estimation, writes provenance.

```bash
python -m aegis.basestation.build merge --region brussels
```

Spatial deduplication rules:
1. Group antennas by operator (normalized: lowercase, stripped, known aliases mapped, e.g. "BE:PROXIMUS" -> "proximus")
2. Within an operator group, cluster by spatial proximity: antennas within 50m of each other belong to the same physical site
3. Within a site cluster, match sectors by frequency band. Two rows with same operator + same site + same FrequencyBand = same physical antenna panel from different sources
4. For matched panels: take each field from the highest-priority source that has a non-NaN value. The output is one row per matched panel with the best available value per column
5. Unmatched panels (only in one source): keep as-is with that source's provenance

Field priority for a matched antenna:
1. Government source with non-NaN value (priority 1)
2. Second government source, e.g. border areas (priority 2)
3. Crowdsourced source with non-NaN value (priority 3)
4. Estimate from merged dataset (Technology + FrequencyBand median), tagged `est:tech+band`
5. Estimate from reference dataset (Brussels as gold standard), tagged `est:ref`
6. Still NaN: tagged `missing`

**Stage 3: Validate** - Sanity checks (power 0-80 dBm, azimuth 0-360, lat/lon in bbox). Prints coverage report showing % of fields filled and source distribution.

```bash
python -m aegis.basestation.build validate --region brussels
python -m aegis.basestation.build report
python -m aegis.basestation.build all     # extract + merge + validate for all regions
```

### Region configuration

```yaml
# data/basestations/regions.yaml
# bbox format: [min_lon, max_lon, min_lat, max_lat] (lon-first, matching basestationLib convention)
regions:
  brussels:
    sources:
      - type: basestationlib
        country: Belgium
        region: brussels
        priority: 1
    reference: data/basestations/raw/brussels_gov.parquet

  france:
    sources:
      - type: basestationlib
        country: France
        bbox: [1.5, 3.0, 48.5, 49.2]  # [min_lon, max_lon, min_lat, max_lat]
        priority: 1
      - type: opencellid
        country_code: 208
        bbox: [1.5, 3.0, 48.5, 49.2]
        priority: 3
    reference: data/basestations/raw/brussels_gov.parquet

  denmark:
    sources:
      - type: mastedatabasen
        priority: 1
      - type: opencellid
        country_code: 238
        priority: 3
    reference: data/basestations/raw/brussels_gov.parquet
```

## Adapter and viewer changes

### Bug fixes (5 issues from code audit)

1. **FrequencyBand dropped at adapter boundary**: Add `frequency_band: str` to `BaseStation`, pass through `_bs_summary()`.
2. **Only brussels.csv exists**: Replaced by build pipeline. Viewer checks Parquet first, CSV fallback.
3. **Brussels patterns.mat not loaded from CSV path**: Auto-discover `patterns/{region}.mat` in data directory.
4. **No Wallonia adapter**: Covered by OpenCellID fallback with Brussels reference estimation. Region config makes this explicit.
5. **Pattern key mismatch**: Unify `sanitize_label` in `src/aegis/basestation/`, used by both adapter and pattern loader.

### New: `load_basestations_from_parquet`

```python
def load_basestations_from_parquet(
    path: str,
    bbox: list[float] | None = None,
    operator: str | None = None,
    technology: str | None = None,
    frequency_band: str | None = None,
) -> list[BaseStation]:
```

Reads merged Parquet, builds `BaseStation` objects with `provenance` populated from `_source` columns. Auto-loads patterns from co-located `patterns/` directory.

### Viewer route resolution order

1. `data/basestations/merged/{region}.parquet` (new, preferred)
2. `data/basestations/{region}.csv` (existing, backwards compat)
3. Live basestationLib extraction (existing fallback)

Update `_list_available_regions()` to also scan for `.parquet` files in `merged/`, not just `.csv` files.

Note: the CSV fallback path does not support `frequency_band` filtering (that's bug fix #1). If a region only has a CSV file, the `frequency_band` filter from the frontend is silently ignored. This is acceptable as a transitional state since all regions will eventually migrate to Parquet.

### API response changes

`_bs_summary()` adds:

```json
{
  "frequency_band": "Band3600MHz",
  "confidence": 0.85,
  "pattern_source": "gov:brussels",
  "provenance": {
    "eirp_dbm": {"origin": "gov:brussels", "confidence": 1.0},
    "azimuth_deg": {"origin": "gov:brussels", "confidence": 1.0},
    "gain_dbi": {"origin": "est:tech+band", "confidence": 0.3}
  }
}
```

The `confidence` field is the aggregate weighted score, computed on the fly. The `provenance` dict uses `BaseStation` field names (not DataFrame column names) for frontend consistency.

### Frontend (minimal pass)

- Antenna icons colored by confidence score (green > 0.7, yellow > 0.4, orange > 0.2, red <= 0.2)
- Detail panel shows provenance per field as colored dots next to values
- Small legend in base stations sidebar explaining colors
- `frequency_band` filter added to sidebar
- A frontend context handoff doc written after changes, for a future "beautiful frontend" brainstorming session

## New Denmark adapter

Mastedatabasen has a marketing site at mastedatabasen.dk and exposes a third-party JSON:API at `dk-api.mastdatabase.co.uk` (operated separately, well-documented).

Endpoints:
- `GET /sites?filter[bounds]=lat1,lon1,lat2,lon2` - bbox query
- `GET /sites?filter[operator]=...&filter[technology]=...`
- Pagination up to 5000 results/page

Fields available: location, operator, technology (GSM/LTE/5G-NR), frequency band, service type.
Fields missing: power, azimuth, tilt, gain, beamwidth, height (all estimated from Brussels reference).

Implementation: new file `basestations/basestationLib/Countries/Denmark/basestations.py` following the existing adapter pattern.

## Country adapter specs for future agents

Each country gets a standalone spec in `docs/superpowers/specs/country-adapters/`. Contains: source URL, API type, authentication, fields available, fields missing, extraction method with exact API calls, pagination and rate limits, known gotchas, a test region (small bbox with expected row count), output filename convention, and priority in the merge hierarchy.

### Tier 2: European government sources
- Germany (BNetzA, scraping, 82K sites, has azimuth + height)
- Netherlands (WFS, adapter exists, needs Parquet migration)
- Austria (REST, adapter exists, intermittent API)
- Spain (GeoJSON tiles, adapter exists, very slow)
- Switzerland (BAKOM, adapter exists, currently 403)
- Poland (scraping, adapter exists, slow)
- Ireland (ComReg Siteviewer, needs scraping)
- Italy Lombardy (CASTEL, needs scraping)

### Tier 3: Non-European government sources
- Australia (ACMA RRL, daily ZIP, has EIRP/azimuth/tilt/polarisation)
- Canada (ISED SMS, ZIP + ArcGIS, 54 fields per site)
- New Zealand (RSM RRF, REST API)

### Tier 4: Crowdsourced fallback
- OpenCellID global (bulk CSV download, location-only, CC-BY-SA)

### Tier 5: Antenna patterns
- CommScope BSAPatternsWeb (free, 25 export formats)
- wireless-planning.com MSI library (400K files, 50+ manufacturers)
- 3GPP TR 38.901 parametric model (mathematical, no measured data)

## Session scope

### Code
1. `src/aegis/basestation/provenance.py` - FieldSource, confidence scoring, dosimetric weights
2. `src/aegis/basestation/build.py` - CLI build pipeline (extract, merge, validate, report)
3. `src/aegis/basestation/merge.py` - Source stacking, spatial dedup, field-level priority, provenance tagging
4. `src/aegis/basestation/parquet_io.py` - Parquet read/write with provenance columns
5. Updated `antenna.py` - frequency_band, provenance (tuple), pattern_source fields
6. Updated `adapter.py` - Parquet loader, pattern auto-discovery, unified sanitize_label
7. Updated viewer route - Parquet-first resolution, provenance in API, frequency_band filter, updated _list_available_regions
8. Updated frontend - Confidence-colored icons, provenance dots in detail panel, frequency_band filter, legend
9. Denmark adapter in basestationLib
10. 5 bug fixes listed above

### Data
11. Raw Parquet for Brussels, Flanders, Denmark, France
12. Merged Parquet with provenance for same regions
13. `regions.yaml` build configuration

### Specs
14. This design doc
15. ~18 country adapter specs in `docs/superpowers/specs/country-adapters/` (tiers 2-5)
16. Frontend context handoff doc for future "beautiful frontend" session

### Not in scope
- Dosimetry engine changes (already consumes BaseStation objects)
- CloudRF integration (another agent is exploring that)
- Full frontend redesign (separate brainstorming session)
- Wallonia government data (no government API exists)
