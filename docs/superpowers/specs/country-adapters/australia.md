# Australia adapter spec

## Source
- **Name:** ACMA RRL (Register of Radiocommunications Licences)
- **URL:** https://www.acma.gov.au/radiocomms-licence-data / https://web.acma.gov.au/rrl/
- **Type:** Daily ZIP download (static files) + Web API
- **Auth:** None (public)
- **License:** Creative Commons Attribution 3.0 Australia

## Fields available
| Column | Available | Notes |
|---|---|---|
| SiteCode | yes | Licence number as site identifier |
| Latitude/Longitude | yes | WGS84, precise tower coordinates |
| CenterHeight | yes | Antenna height above ground (m) |
| Power | yes | EIRP in dBW per licence record |
| Frequency | yes | Carrier frequency in MHz |
| FrequencyBand | yes | Derivable from frequency |
| Electrical_Tilt | yes | Tilt in degrees per licence |
| Mechanical_Tilt | no | Not separated from total tilt |
| Azimuth | yes | Bearing in degrees |
| Gain | yes | Antenna gain in dBi |
| Horizontal_Beamwidth | no | Not in RRL |
| Vertical_Beamwidth | no | Not in RRL |

## Fields missing
Horizontal_Beamwidth and Vertical_Beamwidth will be NaN. Apply 3GPP TR 38.901 defaults for beamwidth. Mechanical_Tilt is not separated from electrical tilt; assign all tilt to Electrical_Tilt.

## Extraction method

Download the daily ZIP from the ACMA data portal:

```bash
wget https://www.acma.gov.au/sites/default/files/2023-01/spectra_rrl.zip
unzip spectra_rrl.zip
```

The ZIP contains pipe-delimited CSV files organised by service type. The relevant files for cellular are `site.csv`, `antenna.csv`, `licence.csv`, and `device_details.csv`. Join on `licence_no` to assemble the full record per antenna.

Key join logic:
1. `licence.csv` - licensee, service type, status (only keep ACTIVE licences)
2. `site.csv` - lat/lon, site ID, elevation
3. `antenna.csv` - antenna ID, gain, azimuth, tilt, polarisation, height
4. `device_details.csv` - frequency, bandwidth, EIRP

Filter `licence_type` to `APPARATUS` and `client_type` to mobile carriers (Telstra, Optus, TPG/Vodafone, etc.) using MCC/MNC-mapped ABN numbers. Alternatively filter on `service_type` containing `MOBILE` or frequency ranges (700/850/1800/2100/2600/3500 MHz bands).

The Web API at `web.acma.gov.au/rrl/` supports bbox and keyword queries but the static ZIP is faster for full-country extraction. Use the API only for targeted queries or incremental updates.

```python
import pandas as pd

site = pd.read_csv("site.csv", delimiter="|")
antenna = pd.read_csv("antenna.csv", delimiter="|")
licence = pd.read_csv("licence.csv", delimiter="|")
device = pd.read_csv("device_details.csv", delimiter="|")

active = licence[licence["licence_status"] == "ACTIVE"]
merged = (active
    .merge(site, on="site_id")
    .merge(antenna, on="licence_no")
    .merge(device, on="licence_no"))
```

Expect ~200K-400K antenna records total; mobile cellular is a subset. Full join takes under a minute on a modern laptop.

## Gotchas
- The ZIP is updated daily but the file layout has changed over time. Pin column names by index, not by header string, or add a schema check on load.
- EIRP is in dBW; many downstream tools expect dBm. Convert: `dBm = dBW + 30`.
- Some licences have multiple `device_details` rows (multiple channels). Deduplicate by keeping the primary carrier frequency per sector.
- 5G mmWave licences (26/28 GHz) appear in the same ZIP. Dosimetry at mmWave requires different tissue parameters; flag these separately.
- The `antenna.csv` tilt column is labelled `antenna_tilt` and is the combined electrical + mechanical tilt. Treat as Electrical_Tilt.
- Polarisation is included (V, H, +-45) and is useful for MIMO path modelling but is not in the standard 16-column schema.

## Test region
- **bbox:** [150.90, 151.30, -34.05, -33.75] (central Sydney)
- **Expected rows:** ~3,000-6,000 antennas after filtering to mobile cellular
- **Expected time:** < 2 seconds (filter from pre-loaded DataFrame)

## Output
- **Raw file:** `data/basestations/raw/australia_acma.parquet`
- **Source tag:** `gov:australia_acma`
- **Priority:** 5 (location + azimuth + power + gain + tilt; one of the richest public databases globally)

## Implementation
- **File:** `basestations/basestationLib/Countries/Australia/basestations.py`
- **Add to** `country_module_map.json`
- Constructor: `BaseStations(bbox, operator=None, technology=None, zip_path=None)`
- `extract_antennas(config)` loads the four CSV files (downloading the ZIP if not cached), joins and filters, then returns a standardized 16-column DataFrame.
- Cache the ZIP at `~/.cache/aegis/acma_rrl.zip` and re-download if older than 24 hours.

## Status
Needs new adapter. No existing implementation.
