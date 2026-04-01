# Data extraction, new adapters, and polish

Continuation of the base station master dataset work. The infrastructure (provenance model, build pipeline, merge logic, frontend wiring) is complete. This spec covers actually running the pipeline, adding new country regions, and polishing the research report.

## Prerequisites

The previous session delivered:

- `src/aegis/basestation/provenance.py` - FieldSource, confidence scoring, dosimetric weights
- `src/aegis/basestation/parquet_io.py` - Parquet I/O with `_source` columns
- `src/aegis/basestation/merge.py` - spatial dedup, operator normalization, estimation with provenance
- `src/aegis/basestation/build.py` - CLI with extract/merge/validate/report/all subcommands
- `data/basestations/regions.yaml` - 4 regions configured (Brussels, Flanders, France, Denmark)
- `basestationLib/Countries/Denmark/basestations.py` - Mastedatabasen adapter (class-based, `BaseStations` with `extract_antennas()`)
- Frontend: confidence colors, frequency band filter, antenna detail panel with provenance dots
- 15 country adapter spec files in `docs/superpowers/specs/country-adapters/`

What's missing: `data/basestations/raw/` and `merged/` are empty. No data has been extracted.

## Existing adapters already in basestationLib

These adapters already exist and follow the class-based pattern (`BaseStations` class with `extract_antennas(config)` returning a DataFrame):

| Country | Adapter | Registered in country_module_map.json |
|---------|---------|--------------------------------------|
| Belgium (Brussels) | `Countries/Belgium/brussels/` | Yes |
| Belgium (Flanders) | `Countries/Belgium/flanders/` | Yes |
| France | `Countries/France/` | Yes |
| Netherlands | `Countries/Netherlands/` (Antenneregister WFS) | Yes |
| Austria | `Countries/Austria/` (RTR Senderkataster) | Yes |
| Switzerland | `Countries/Switzerland/` | Yes |
| Poland | `Countries/Poland/` | Yes |
| Spain | `Countries/Spain/` | Yes |
| Hungary | `Countries/Hungary/` | Yes |
| Denmark | `Countries/Denmark/` (Mastedatabasen) | Yes |
| OpenCellID | `OpenCellID/` (getInArea API, tiles bbox) | Yes (as "other") |

All adapters use the same interface: `BSClass(**init_kw).extract_antennas(config=config) -> pd.DataFrame`.

## Source tag registry

Single source of truth for naming conventions:

| Source type | Source tag | Raw filename pattern | Confidence |
|-------------|-----------|---------------------|------------|
| basestationlib (Brussels) | `gov:brussels` | `{region}_gov.parquet` | 1.0 |
| basestationlib (Flanders) | `gov:flanders` | `{region}_gov.parquet` | 0.9 |
| basestationlib (France) | `gov:anfr` | `{region}_gov.parquet` | 0.9 |
| basestationlib (Netherlands) | `gov:antenneregister` | `{region}_gov.parquet` | 0.9 |
| basestationlib (Austria) | `gov:rtr` | `{region}_gov.parquet` | 0.9 |
| mastedatabasen (Denmark) | `gov:mastedatabasen` | `{region}_mastedatabasen.parquet` | 0.9 |
| basestationlib (Australia) | `gov:acma` | `{region}_gov.parquet` | 0.9 |
| opencellid | `ocid` | `{region}_opencellid.parquet` | 0.5 |
| estimated (same dataset) | `est:tech+band` | (in merged only) | 0.3 |
| estimated (reference) | `est:ref` | (in merged only) | 0.2 |
| missing | `missing` | (in merged only) | 0.0 |

## Section 1: Wire up stubs and extract data

### 1a. Denmark extractor in build.py

The Denmark adapter already follows the basestationLib class pattern (`BaseStations` with `extract_antennas()`). The `_extract_basestationlib` function works for any adapter with this interface. Wire it up by:

- Adding a `_extract_mastedatabasen(source, region_name, force)` function in `build.py`
- It instantiates `basestationLib.Countries.Denmark.basestations.BaseStations` directly (bypassing `get_basestation_instance` since Denmark is not a standard basestationLib country)
- Passes `bounding_box=source["bbox"]` to the constructor
- Calls `extract_antennas(config)` and writes to `{region}_mastedatabasen.parquet`
- Uses the same error handling pattern as `_extract_basestationlib`

### 1b. OpenCellID extractor in build.py

The existing `basestationLib/OpenCellID/basestations.py` already handles bbox tiling, API calls, and DataFrame output. It reads the API key from a file. Wire it up:

- Add `_extract_opencellid(source, region_name, force)` function in `build.py`
- Check for API key: first `OPENCELLID_API_KEY` env var, then `basestations/basestationLib/OpenCellID/api_key.txt`
- If neither exists, log a warning and skip (not an error)
- Instantiate the OpenCellID `BaseStations` class with `bounding_box=source["bbox"]`
- Call `extract_antennas(config)` and write to `{region}_opencellid.parquet`
- OpenCellID provides location, operator (from MCC+MNC), technology (from radio type). No power, azimuth, tilt, gain, beamwidth, or height

### 1c. Run the pipeline

```bash
python -m aegis.basestation.build all
```

Fix any bugs that surface with real data. Expected output:
- `data/basestations/raw/` - one Parquet per source per region
- `data/basestations/merged/` - one merged Parquet per region with `_source` columns

## Section 2: New regions in the pipeline

Since Netherlands and Austria already have working adapters in basestationLib, adding them is just config:

### 2a. Netherlands (already has adapter)

- Adapter: `basestationLib/Countries/Netherlands/basestations.py` (Antenneregister WFS)
- Add `netherlands` region to `regions.yaml` with bbox around Amsterdam: `[4.7, 5.1, 52.2, 52.5]`
- Source type: `basestationlib`, country: `Netherlands`
- Source tag: `gov:antenneregister`

### 2b. Austria (already has adapter)

- Adapter: `basestationLib/Countries/Austria/basestations.py` (RTR Senderkataster)
- Add `austria` region to `regions.yaml` with bbox around Vienna: `[16.2, 16.6, 48.1, 48.35]`
- Source type: `basestationlib`, country: `Austria`
- Source tag: `gov:rtr`

### 2c. Germany (needs new adapter)

- No existing adapter in basestationLib
- **Source**: BNetzA EMF database (bundesnetzagentur.de)
- Research the actual API endpoint. The EMF map at emf3.bundesnetzagentur.de has a GIS backend
- Create `basestationLib/Countries/Germany/basestations.py` following the class-based pattern
- Register in `country_module_map.json`
- Add `germany` region to `regions.yaml` with bbox around Berlin: `[13.2, 13.6, 52.4, 52.6]`
- Source tag: `gov:bnetza`
- Rate limit: max 2 concurrent workers, add User-Agent header, respect rate limits

### 2d. Australia (needs new adapter)

- No existing adapter in basestationLib
- **Source**: ACMA Radiocommunications Licence Data (data.gov.au daily ZIP)
- The ZIP contains multiple CSVs that need joining (site, device_detail, licence). ~200K+ records total
- Cache the ZIP at `~/.cache/aegis/acma_rrl.zip` to avoid re-downloading. Check staleness by comparing HTTP Last-Modified header
- Filter to cellular/mobile licences only (exclude broadcasting, fixed links, etc.)
- Create `basestationLib/Countries/Australia/basestations.py`
- Register in `country_module_map.json`
- Add `australia` region to `regions.yaml` with bbox around Sydney: `[150.9, 151.4, -34.0, -33.7]`
- Source tag: `gov:acma`
- Fields available: location, frequency, EIRP, azimuth, tilt, polarisation, antenna height
- This is one of the richest public databases, so give it priority 1

### How to add a new source type (checklist)

1. Write or verify the adapter in `basestationLib/Countries/<Country>/basestations.py`
2. Register in `basestationLib/core/country_module_map.json`
3. Add extraction handling in `build.py` (or reuse `_extract_basestationlib` if it follows the standard class pattern)
4. Add region config to `data/basestations/regions.yaml`
5. Add source tag to the registry table above
6. Run `python -m aegis.basestation.build extract --region <name> --force` to test

## Section 3: Research report and polish

### 3a. MapRad research

Research MapRad.io:
- What data sources does it aggregate?
- Is there an API or only a web UI?
- Is it free or commercial?
- Could it serve as a data source for AEGIS, or is our direct-to-government approach better?

Update `docs/internal/base-station-data-sources.md` with a MapRad section. Acceptance criteria: the section should answer the four questions above in 2-3 paragraphs.

### 3b. End-to-end verification

After data extraction:
- Verify the viewer loads Parquet data (not CSV fallback) for Brussels
- Check that confidence colors appear on 3D antenna markers
- Verify frequency band filter populates
- Verify antenna detail panel shows provenance per field
- Run `python -m aegis.basestation.build report` and log the coverage table

### 3c. Bug fixes

Fix any bugs discovered during extraction or verification. Common issues:
- API response format changes (field names, pagination)
- Encoding issues in operator names
- NaN handling in merge/estimation
- Parquet schema mismatches between raw and merged

### 3d. Tests

Add smoke tests for the new extraction functions:
- Test that `_extract_mastedatabasen` handles API failure gracefully
- Test that `_extract_opencellid` skips when no API key is present
- Test that new regions in `regions.yaml` are valid config entries

## Out of scope

- Pattern library downloads (MSI, CommScope, 3GPP synthetic)
- Tier 3 adapters beyond Australia (Canada, New Zealand)
- Frontend redesign (covered by the handoff doc for a future session)
