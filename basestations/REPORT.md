# basestationLib: feature report

Report generated 2026-03-27 by extracting real data from multiple European countries.

## What it does

basestationLib extracts mobile base station (cell tower) antenna data from government and community databases across Europe. It standardizes everything into a common 16-column CSV schema, regardless of the source country or API format.

The core pipeline: **query data source -> parse -> filter -> deduplicate -> estimate missing values -> export CSV**.

## Supported countries

| Country | Data source | API type | Speed |
|---|---|---|---|
| Belgium (Brussels) | environnement.brussels | REST + HTML | ~2 min |
| Belgium (Flanders) | Flemish SPARQL endpoint | SPARQL | ~3 min |
| Netherlands | Antenneregister (WFS) | OGC WFS | ~5 sec |
| France | CartoRadio (ANFR) | REST API | ~2 sec |
| Hungary | OpenCellID community | Static GeoJSON | ~1 sec |
| Austria | SenderKataster | REST API | ~2 min |
| Spain | VCTEL InfoAntenas | GeoJSON tiles | slow (millions of tiles) |
| Switzerland | BAKOM/geo.admin | Static GeoJSON | fast (but 403 as of 2026-03) |
| Poland | BTSearch | Web scraping | ~20 min |
| Any country | OpenCellID (fallback) | REST API (needs key) | varies |

## Standardized output schema

Every country produces CSVs with these 16 columns:

| Column | Description | Unit |
|---|---|---|
| SiteCode | Site identifier | e.g. `SITE(15261)` |
| AntennaLabel | Antenna panel identifier | e.g. `ANT(82265455321)` |
| Operator | Mobile network operator | string |
| Technology | Generation(s) served | `2G`, `3G`, `4G`, `5G`, or combos like `4G/5G` |
| Latitude | WGS84 latitude | degrees |
| Longitude | WGS84 longitude | degrees |
| CenterHeight | Antenna height above ground | meters |
| Power | Transmit power | dBm (or watts, source-dependent) |
| Frequency | Center frequency | MHz |
| FrequencyBand | 3GPP band designation | e.g. `Band3600MHz` |
| Electrical\_Tilt | Electronic downtilt | degrees |
| Mechanical\_Tilt | Mechanical downtilt | degrees |
| Azimuth | Pointing direction | 0-359 degrees, or `isotropic` |
| Gain | Antenna gain | dBi |
| Horizontal\_Beamwidth | Horizontal 3 dB beamwidth | degrees |
| Vertical\_Beamwidth | Vertical 3 dB beamwidth | degrees |

Missing values are `NaN`.

## Data richness by country

Tested with small bounding boxes around city centers. Column population rates:

| Column | Brussels | Netherlands | France | Hungary |
|---|---|---|---|---|
| SiteCode | 100% | 100% | 100% | 100% |
| Operator | 100% | 100% | 100% | 100% |
| Technology | 100% | 100% | 100% | 100% |
| Lat/Lon | 100% | 100% | 100% | 100% |
| CenterHeight | **100%** | **100%** | **100%** | 0% |
| Power | **100%** | **100%** | 0% | 0% |
| Frequency | 100% | 100% | 100% | 100% |
| FrequencyBand | 100% | 100% | 100% | 100% |
| Electrical\_Tilt | **100%** | 0% | 0% | 0% |
| Mechanical\_Tilt | **100%** | 0% | 0% | 0% |
| Azimuth | **100%** | **92%** | **98%** | 0% |
| Gain | **100%** | 0% | 0% | 0% |
| Horizontal\_Beamwidth | **100%** | 0% | 0% | 0% |
| Vertical\_Beamwidth | **100%** | 0% | 0% | 0% |

Brussels is the richest source (100% on all 16 columns). Hungary is the sparsest (community-sourced, location + frequency only).

## Real extraction results

### Netherlands: Amsterdam center (bbox 4.89-4.91, 52.37-52.38)

- **624 antennas** from 66 sites, extracted in ~5 seconds
- Operators: KPN, Odido, Vodafone, Tampnet
- Technologies: 2G, 3G, 4G, 5G (and combos like `4G/5G`)
- Bands: 700, 800, 900, 1500, 1800, 2100, 2600, 3600 MHz

Sample rows:

```
Operator  Tech   Band          Power  Height  Azimuth
Odido     5G     Band3600MHz   46.0   26.3    210
Tampnet   5G     Band700MHz    28.4   24.2    330
Vodafone  4G/5G  Band1800MHz   32.4   24.2    210
Vodafone  4G     Band2100MHz   32.4   24.2    210
Vodafone  2G     Band900MHz    24.8   24.2    210
```

### France: Paris center (bbox 2.345-2.355, 48.858-48.863)

- **220 antennas** from 21 sites, extracted in ~2 seconds
- Operators: Bouygues Telecom, Free Mobile, Orange, SFR
- Technologies: 2G/3G, 3G, 3G/4G, 4G, 4G/5G, 5G
- Bands: 700, 800, 900, 1800, 2100, 2600, 3600 MHz

Sample rows:

```
Operator  Tech   Band          Height  Azimuth
ORANGE    5G     Band3600MHz   31.4    15
ORANGE    4G     Band1800MHz   31.9    15
ORANGE    4G/5G  Band700MHz    31.9    15
SFR       5G     Band3600MHz   27.1    40
FREE      4G     Band1800MHz   20.0    80
```

### Belgium Brussels (bbox 4.35-4.37, 50.845-50.855)

- **626 antennas**, the richest dataset
- Operators: Proximus, Orange, Telenet, Citymesh Mobile (Insky)
- All columns populated at 100%

Sample rows:

```
Operator   Tech    Band          Power  Height  Azimuth  Gain   E_tilt  HBW   VBW
Proximus   4G/5G   Band1800MHz   40.8   7.93    297      6.15   0       168   100
Proximus   4G/5G   Band800MHz    40.8   7.93    297      6.15   0       158   90
Proximus   2G/3G   Band900MHz    40.8   7.93    297      6.15   0       158   90
Orange     4G      Band800MHz    42.4   8.51    210      6.15   0       158   90
```

### Hungary: Budapest center (bbox 19.04-19.06, 47.50-47.51)

- **356 antennas**, sparse community data
- Operators: One, Telekom, Yettel, UNKNOWN
- Technologies include rare combos: `3G/4G/5G`, `2G/3G/4G`
- No power, height, gain, azimuth, tilts, or beamwidth

## Features

### Filtering

All filters can be combined. Supported filters:

- **Bounding box**: `[min_lon, max_lon, min_lat, max_lat]` - spatial crop
- **Operator**: token-based matching (e.g. `"Proximus"`)
- **Technology**: regex match (e.g. `"5G"`, `"4G"`)
- **Frequency range**: numeric bounds in Hz (e.g. `[3400000000, 3800000000]`)
- **Frequency band**: string match (e.g. `"Band3600MHz"`)
- **Date**: temporal cutoff, keeps only antennas active before that date

### Smart deduplication

When multiple antenna panels at the same site share the same operator, location, azimuth, and frequency band, they are merged into a single physical antenna record. Technologies get combined (e.g. separate `4G` and `5G` entries become one `4G/5G` row). Frequencies are averaged.

### Missing data estimation

Multi-stage fallback estimation for numeric columns (power, gain, tilts, beamwidths):

1. Match by (Technology + FrequencyBand) within extracted data
2. Match by Technology only within extracted data
3. Match by FrequencyBand only within extracted data
4. Same stages using external reference CSVs (if provided)

Fills NaN values with median from matching groups.

### Antenna radiation patterns (Belgium only)

Both Brussels and Flanders can export full 2D antenna radiation patterns:

- **Format**: MATLAB `.mat` files
- **Resolution**: 181 x 360 matrix per antenna (1-degree steps in elevation and azimuth)
- **Scale**: the Brussels cache contains **22,443 patterns**
- **Use case**: RF planning, exposure assessment, beamforming analysis

### Caching

Raw API responses are cached as pickle files (`all.pkl`) per country. On subsequent runs, cached data is loaded instead of re-querying the API, unless filters change. Cache files can be deleted to force a refresh.

### Parallel extraction

Configurable thread pool (`max_workers`) for concurrent API fetching. Includes:

- Exponential backoff retry (3 retries default)
- Rate limiting (2 req/sec default)
- Connection pooling (64 connections)
- Progress bars (tqdm)

## Usage

### Config-driven (YAML)

```yaml
locationinfo:
  country: "Netherlands"
  bbox: [4.89, 4.91, 52.37, 52.38]

antennafilters:
  technology: "5G"
  operator: "KPN"

computation:
  max_workers: 8
  estimations:
    estimate_missing_data_based_on_existing: true

output:
  folder: "output/nl"
```

```bash
python main.py  # reads config.yaml
```

### Programmatic

```python
from basestationLib import get_basestation_instance

BS = get_basestation_instance("Netherlands")
inst = BS(
    output_folder="output/nl/",
    bounding_box=[4.89, 4.91, 52.37, 52.38],
    technology="5G",
    max_workers=8,
)
df = inst.extract_antennas(config={...})
# df is a pandas DataFrame with 16 standardized columns
```

### Belgium (requires region)

```python
BS = get_basestation_instance("Belgium", region_city="brussels")
# or region_city="flanders"
```

## Output files

| File type | Location | Description |
|---|---|---|
| `*_antennas.csv` | `output/{country}/` | Standardized 16-column antenna data |
| `all.pkl` | `basestationLib/Countries/{country}/` | Raw data cache (pickle) |
| `patterns.mat` | Belgium only | 2D antenna radiation patterns (MATLAB) |

Filename convention: `{bbox_or_filters}_{date}_antennas.csv`

Example: `4.89-4.91-52.37-52.38_2026-03-27_antennas.csv`

## Limitations observed during testing

- **Switzerland**: secondary data source returning 403 errors (March 2026), primary BAKOM source still works for site locations but not detailed per-operator data
- **Spain**: tiles the bounding box very finely (~1M tiles for a small area), making extraction extremely slow
- **Austria**: API occasionally returns empty responses causing JSON parse errors
- **Hungary**: community-sourced, very sparse metadata (no power, height, gain, or azimuth)
- **tkinter dependency**: the estimation module opens a GUI file dialog when no reference CSVs are configured, which fails on headless systems (patched in this fork to skip gracefully)
- **Power units**: not consistent across countries (some dBm, some watts)
