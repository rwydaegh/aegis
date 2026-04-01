# New Zealand adapter spec

## Source
- **Name:** RSM RRF (Radio Spectrum Management - Radiocommunications Register of Frequencies)
- **URL:** https://portal.api.business.govt.nz/api/radiospectrum-management / https://rrf.rsm.govt.nz/ui
- **Type:** REST API
- **Auth:** API key (free registration at portal.api.business.govt.nz)
- **License:** Creative Commons Attribution 4.0 New Zealand

## Fields available
| Column | Available | Notes |
|---|---|---|
| SiteCode | yes | RRF licence number |
| Latitude/Longitude | yes | NZGD2000 / WGS84, precise per licence |
| CenterHeight | yes | Antenna height above ground (m) |
| Power | yes | EIRP in dBW per licence |
| Frequency | yes | Carrier frequency in MHz |
| FrequencyBand | yes | Derivable from frequency |
| Electrical_Tilt | yes | Tilt in degrees, populated for many records |
| Mechanical_Tilt | no | Not separated |
| Azimuth | yes | Sector azimuth in degrees |
| Gain | yes | Antenna gain in dBi |
| Horizontal_Beamwidth | no | Not in RRF |
| Vertical_Beamwidth | no | Not in RRF |

## Fields missing
Horizontal_Beamwidth and Vertical_Beamwidth will be NaN. Apply 3GPP TR 38.901 defaults. Mechanical_Tilt is not separately available; treat all tilt as Electrical_Tilt.

## Extraction method

Obtain a free API key by registering at portal.api.business.govt.nz. Then query the RRF endpoint with a bbox and licence type filter:

```
GET https://api.business.govt.nz/services/v1/rsm/search/licences
    ?lat=-36.867&lon=174.770&radius=20000
    &licenceType=MOBILE
    &status=CURRENT
    &apikey=YOUR_KEY
```

The API supports radius-based queries (not bbox). Convert a bbox to a set of overlapping circles at fixed radius (e.g., 20 km), tile to cover the target area, then deduplicate by licence number.

Pagination: the response includes `totalResults` and `pageNumber`. Page size is 100. Iterate with `?page=N` until all records are retrieved.

The search UI at `rrf.rsm.govt.nz/ui` is useful for validating results by hand before building the adapter. It exposes the same API with a map interface and lets you filter by frequency band, operator, and technology.

For full-country extraction, the dataset is small (~20K active mobile licences for a country of 5M people). A single pass takes under 5 minutes.

```python
import requests

def fetch_page(lat, lon, radius_m, page=1, api_key=""):
    resp = requests.get(
        "https://api.business.govt.nz/services/v1/rsm/search/licences",
        params={
            "lat": lat, "lon": lon, "radius": radius_m,
            "licenceType": "MOBILE", "status": "CURRENT",
            "page": page, "pageSize": 100,
        },
        headers={"apikey": api_key},
    )
    resp.raise_for_status()
    return resp.json()
```

## Gotchas
- The API requires an `apikey` header, not a query parameter. Using `?apiKey=` instead of the header returns a 403.
- New Zealand uses NZGD2000 as its datum. The API returns WGS84 coordinates; no conversion needed.
- Licence records cover all spectrum services. Filter by `licenceType` and frequency band to isolate 4G/5G cellular (700/1800/2100/2600/3500 MHz). Spark, One NZ (formerly Vodafone NZ), and 2degrees are the main mobile operators.
- The search radius is in metres, not kilometres. A 20 km radius covers most of the country in a small number of circles (New Zealand is long and narrow).
- The API base URL changed from an older `api.business.govt.nz/gateway/` prefix. Monitor for URL updates.
- New Zealand is a small market. Full-country extraction is fast; no need for heavy parallelism.

## Test region
- **bbox:** [174.70, 174.85, -36.92, -36.82] (central Auckland)
- **Expected rows:** ~300-700 antennas
- **Expected time:** ~15 seconds (REST API pagination)

## Output
- **Raw file:** `data/basestations/raw/new_zealand_rsm.parquet`
- **Source tag:** `gov:new_zealand_rsm`
- **Priority:** 4 (location + azimuth + power + gain + tilt; small market, good data quality)

## Implementation
- **File:** `basestations/basestationLib/Countries/NewZealand/basestations.py`
- **Add to** `country_module_map.json`
- Constructor: `BaseStations(bbox, operator=None, technology=None, api_key=None)`
- `api_key` falls back to env var `RSM_API_KEY` if not provided.
- `extract_antennas(config)` tiles the bbox into radius-based circles, fetches all pages, deduplicates, and returns a standardized 16-column DataFrame.

## Status
Needs new adapter. No existing implementation. API key required before development.
