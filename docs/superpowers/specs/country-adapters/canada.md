# Canada adapter spec

## Source
- **Name:** ISED SMS (Spectrum Management System)
- **URL:** https://ised-isde.canada.ca/site/spectrum-management-system/en/download-sms-data
- **Type:** ZIP download (static files) + ArcGIS REST API
- **Auth:** None (public)
- **License:** Open Government Licence - Canada

## Fields available
| Column | Available | Notes |
|---|---|---|
| SiteCode | yes | SMS site ID |
| Latitude/Longitude | yes | NAD83, sub-meter precision for licensed sites |
| CenterHeight | yes | Antenna height above ground (m) |
| Power | yes | Transmit power in dBW (ERP or EIRP depending on service) |
| Frequency | yes | Assigned frequency in MHz |
| FrequencyBand | yes | Derivable from frequency |
| Electrical_Tilt | no | Included for some services, missing for others |
| Mechanical_Tilt | no | Not consistently populated |
| Azimuth | yes | Tx azimuth in degrees |
| Gain | no | Antenna gain missing for most cellular records |
| Horizontal_Beamwidth | no | |
| Vertical_Beamwidth | no | |

## Fields missing
Electrical_Tilt, Mechanical_Tilt, Gain, Horizontal_Beamwidth, Vertical_Beamwidth will be NaN for most records. Apply 3GPP TR 38.901 defaults for gain and beamwidth. Tilt is not reliably populated; default to 0 degrees.

## Extraction method

Download the ZIP from the ISED download page. The dataset contains multiple pipe-delimited tables. The primary files for cellular are `site_data.csv` and `transmitter_data.csv`.

```bash
wget https://ised-isde.canada.ca/ised/site/spectrum-management-system/files/sms_data.zip
unzip sms_data.zip
```

The ZIP contains ~54 fields per site. Key columns:

- `LATITUDE`, `LONGITUDE` - WGS84 coordinates
- `ANTENNA_HEIGHT_M` - height above ground
- `AZIMUTH_OF_MAIN_LOBE` - sector azimuth
- `TX_POWER_DBW` - transmit power (ERP)
- `FREQUENCY_MHZ` - assigned frequency
- `LICENSE_TYPE_CODE` - use to filter to mobile cellular (codes: `CL`, `PCS`, `AWS`, `700`, `2500`)
- `STATUS_CODE` - keep `ACTIVE` only

Alternatively, use the ArcGIS REST API for bbox queries:

```
GET https://services1.arcgis.com/v6OKGagFNlXn4OTL/arcgis/rest/services/SMS_Public/FeatureServer/0/query
    ?geometry={"xmin":-79.6,"ymin":43.6,"xmax":-79.3,"ymax":43.8}
    &geometryType=esriGeometryEnvelope
    &outFields=*
    &f=geojson
```

The ArcGIS service supports pagination with `resultOffset` and `resultRecordCount` (max 2000 per page). For full-country extraction, the ZIP download is faster.

Third-party explorer tools (tafl.jonathanmorgan.net, tafl.mckie.ca) can help validate results and explore the dataset interactively before building the adapter.

## Gotchas
- Power units vary by service type: some fields are ERP (referenced to a dipole), others are EIRP. Check the `POWER_TYPE` column and convert ERP to EIRP by adding 2.15 dB.
- The SMS dataset covers all spectrum services, not just cellular. Filter aggressively by `LICENSE_TYPE_CODE` and frequency band to avoid including fixed microwave, broadcast, and amateur radio records.
- Azimuth is only populated for directional antennas. Omnidirectional sites have `AZIMUTH_OF_MAIN_LOBE` = NaN; expand these to three 120-degree sectors if dosimetry requires sector-level modelling.
- Rogers, Bell, and Telstra-derived MVNO operators appear under subsidiary company names. Normalise to canonical operator names using MCC/MNC (302-720 = Rogers, 302-610 = Bell, 302-220 = Telemark/Telus).
- The ArcGIS layer has a 2000-record cap per request. Tile the bbox and paginate for dense urban areas.
- Column names in the ZIP have changed between dataset versions. Add a schema validation step.

## Test region
- **bbox:** [-79.55, -79.30, 43.60, 43.80] (central Toronto)
- **Expected rows:** ~1,500-3,000 antennas
- **Expected time:** < 5 seconds (filter from pre-loaded DataFrame)

## Output
- **Raw file:** `data/basestations/raw/canada_ised.parquet`
- **Source tag:** `gov:canada_ised`
- **Priority:** 4 (location + azimuth + power; tilt and gain missing)

## Implementation
- **File:** `basestations/basestationLib/Countries/Canada/basestations.py`
- **Add to** `country_module_map.json`
- Constructor: `BaseStations(bbox, operator=None, technology=None, zip_path=None)`
- `extract_antennas(config)` loads the SMS CSV files (downloading if not cached), filters by service type and status, joins transmitter and site tables, and returns a standardized 16-column DataFrame.
- Cache the ZIP at `~/.cache/aegis/canada_ised.zip` and re-download if older than 7 days (data is updated weekly).

## Status
Needs new adapter. No existing implementation.
