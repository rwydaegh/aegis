# OpenCellID global adapter spec

## Source
- **Name:** OpenCellID (Unwired Labs)
- **URL:** https://opencellid.org
- **Type:** Bulk CSV download (country-level files) + bbox REST API
- **Auth:** API key (free, requires account registration)
- **License:** CC-BY-SA 4.0

## Fields available
| Column | Available | Notes |
|---|---|---|
| SiteCode | partial | Cell ID (not physical tower ID) |
| Latitude/Longitude | yes | Centroid-of-measurements; may be offset from actual tower |
| CenterHeight | no | |
| Power | no | |
| Frequency | partial | Radio type (GSM/LTE/NR) and EARFCN (encodes frequency band) but not exact carrier frequency |
| FrequencyBand | partial | Derivable from EARFCN |
| Electrical_Tilt | no | |
| Mechanical_Tilt | no | |
| Azimuth | no | |
| Gain | no | |
| Horizontal_Beamwidth | no | |
| Vertical_Beamwidth | no | |

## Fields missing
CenterHeight, Power, Electrical_Tilt, Mechanical_Tilt, Azimuth, Gain, Horizontal_Beamwidth, Vertical_Beamwidth will all be NaN. No fallback from reference distribution is reliable because cell ID records do not correspond 1:1 to physical antennas. Use this source only when no government registry is available.

## Extraction method

### Bulk download (preferred)

Bulk CSVs are available per country code (MCC) at:

```
https://opencellid.org/ocid/downloads?token=YOUR_KEY&type=mcc&file=<MCC>.csv.gz
```

Common MCCs: 206 (Belgium), 204 (Netherlands), 208 (France), 228 (Switzerland), etc. A full-world export (`cell_towers.csv.gz`) is also available but exceeds 4 GB compressed.

Each row in the CSV contains: `radio`, `mcc`, `net`, `area`, `cell`, `unit`, `lon`, `lat`, `range`, `samples`, `changeable`, `created`, `updated`, `averageSignal`.

```python
import pandas as pd

df = pd.read_csv("206.csv.gz", compression="gzip", low_memory=False)
df = df[df["radio"].isin(["LTE", "NR"])]  # 4G/5G only
```

The `range` column is a coverage radius estimate in metres (highly unreliable, based on measurement spread, not actual coverage).

### Bbox API (small areas only)

```
GET https://opencellid.org/cell/getInArea
    ?apiKey=KEY
    &BBOX=latmin,lonmin,latmax,lonmax
    &radio=LTE
    &format=json
```

Hard cap of 50 cells per request. Each cell returned costs 1 API credit. Free tier: 1,000 credits/day. Not practical for city-scale extraction; use bulk download instead.

The API also enforces a data contribution requirement: you must contribute at least 1/10th the data you download in a rolling 15-day window.

## Gotchas
- OpenCellID maps by cell ID, not physical tower. A 3-sector tower generates 3 separate cell IDs, each with an independently estimated position that drifts toward where measurements were collected. Do not aggregate these as if they were co-located.
- Centroid accuracy degrades for towers with asymmetric measurement coverage (one-sided roads, rural highways). Expect up to several hundred metres of error in typical cases.
- About one third of entries may be attributed to the wrong operator (MNC mismatch), based on community testing. Cross-validate against government data where available.
- The bulk download only covers the last 18 months of observations. Historical records are dropped.
- The EARFCN encodes band and carrier frequency but parsing it requires a carrier frequency lookup table per radio access technology (E-UTRA for LTE, NR-ARFCN for 5G NR). Use the `pyearfcn` library or a similar tool.
- CC-BY-SA 4.0 is copyleft. Derived databases must also be shared under CC-BY-SA. This is compatible with academic publication but may constrain commercial redistribution.

## When to use

Use OpenCellID as a fallback when no government registry covers the target country. Priority hierarchy:

1. Government registry (Belgium, Netherlands, France, Australia, Canada, etc.)
2. OpenCellID bulk download (location + frequency band only)
3. No data (return empty DataFrame with correct schema)

Do not mix OpenCellID records with government records for the same country. Government data takes precedence and is more accurate.

## Test region
- **MCC filter:** `mcc == 206` (Belgium)
- **bbox:** [4.30, 4.45, 50.82, 50.92] (central Brussels)
- **Expected rows:** ~2,000-5,000 cell records (vs ~800 physical antennas in Brussels government data)
- **Expected rows after dedup by lat/lon cluster:** significantly fewer, but dedup logic is heuristic

## Output
- **Raw file:** `data/basestations/raw/opencellid_<mcc>.parquet`
- **Source tag:** `crowd:opencellid`
- **Priority:** 1 (location only; lowest quality, no RF parameters)

## Implementation
- **File:** `basestations/basestationLib/Global/OpenCellID/basestations.py`
- **Add to** `country_module_map.json` as global fallback
- Constructor: `BaseStations(bbox, mcc, api_key=None, radio=None)`
- `api_key` falls back to env var `OPENCELLID_API_KEY`.
- `extract_antennas(config)` loads the bulk CSV for the given MCC (downloading if not cached), filters to the bbox, and returns a standardized 16-column DataFrame with RF parameters set to `pd.NA`.
- Cache bulk CSVs at `~/.cache/aegis/opencellid/<mcc>.csv.gz`.

## Status
Needs new adapter. No existing implementation. Use as fallback only; do not prioritise over government sources.
