# Data extraction, new adapters, and polish

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract real base station data from existing adapters, add Netherlands/Austria/Germany/Australia regions, and polish the research report.

**Architecture:** The build pipeline (`src/aegis/basestation/build.py`) orchestrates extract/merge/validate/report. Each region in `data/basestations/regions.yaml` declares sources (basestationlib, mastedatabasen, opencellid). Extractors call basestationLib adapters, write raw Parquet to `data/basestations/raw/`, then merge/estimate and write to `data/basestations/merged/`. The viewer loads merged Parquet files with provenance columns.

**Tech Stack:** Python 3.12, pandas, pyarrow, basestationLib adapters, requests, xml.etree.ElementTree

---

### Task 1: Wire up Denmark (Mastedatabasen) extractor in build.py

**Files:**
- Modify: `src/aegis/basestation/build.py:62-72`
- Test: `tests/test_build.py`

The Denmark adapter at `basestations/basestationLib/Countries/Denmark/basestations.py` already has a `BaseStations` class with `extract_antennas(config)`. The build pipeline just needs to instantiate it.

- [ ] **Step 1: Write test for mastedatabasen extraction function**

Add to `tests/test_build.py`:

```python
def test_extract_mastedatabasen_function_exists():
    """Verify _extract_mastedatabasen is callable."""
    from aegis.basestation.build import _extract_mastedatabasen
    assert callable(_extract_mastedatabasen)
```

- [ ] **Step 2: Run test, verify it fails**

```bash
python -m pytest tests/test_build.py::test_extract_mastedatabasen_function_exists -v
```

Expected: FAIL with `ImportError: cannot import name '_extract_mastedatabasen'`

- [ ] **Step 3: Implement `_extract_mastedatabasen` in build.py**

Replace the stub in `_extract_region` and add the extraction function. In `build.py`, add after `_extract_basestationlib`:

```python
def _extract_mastedatabasen(source: dict, region_name: str, force: bool = False) -> pd.DataFrame | None:
    outdir = Path("data/basestations/raw")
    outdir.mkdir(parents=True, exist_ok=True)
    outfile = outdir / f"{region_name}_mastedatabasen.parquet"
    if outfile.exists() and not force:
        logger.info("Raw file %s exists, skipping (use --force to re-extract)", outfile)
        return pd.read_parquet(str(outfile))
    try:
        from basestationLib.Countries.Denmark.basestations import BaseStations
    except ImportError:
        logger.error("Denmark adapter not available. pip install -e basestations/")
        return None
    bbox = source.get("bbox")
    init_kw: dict = {"output_folder": f"/tmp/aegis_build/{region_name}/"}
    if bbox:
        init_kw["bounding_box"] = bbox
    instance = BaseStations(**init_kw)
    config = {
        "computation": {
            "max_workers": 4,
            "estimations": {"estimate_missing_data_based_on_existing": False},
        }
    }
    try:
        df = instance.extract_antennas(config=config)
    except Exception as exc:
        logger.error("Mastedatabasen extraction failed: %s", exc)
        return None
    if df is None or len(df) == 0:
        logger.warning("No antennas extracted from Mastedatabasen for %s", region_name)
        return None
    write_raw_parquet(df, str(outfile))
    return df
```

Update `_extract_region` to call it:

```python
elif src_type == "mastedatabasen":
    _extract_mastedatabasen(source, region_name, force=force)
```

- [ ] **Step 4: Run test, verify it passes**

```bash
python -m pytest tests/test_build.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/aegis/basestation/build.py tests/test_build.py
git commit -m "Wire up Mastedatabasen extractor in build pipeline"
```

---

### Task 2: Wire up OpenCellID extractor in build.py

**Files:**
- Modify: `src/aegis/basestation/build.py`
- Test: `tests/test_build.py`

The OpenCellID adapter at `basestations/basestationLib/OpenCellID/basestations.py` has a `BaseStations` class. It requires an API key file. The extractor should check for the key and skip gracefully if absent.

- [ ] **Step 1: Write test for opencellid extraction graceful skip**

Add to `tests/test_build.py`:

```python
def test_extract_opencellid_skips_without_key(tmp_path, monkeypatch):
    """OpenCellID extraction should skip gracefully when no API key is available."""
    from aegis.basestation.build import _extract_opencellid
    monkeypatch.delenv("OPENCELLID_API_KEY", raising=False)
    # Also ensure the fallback key file does not exist
    monkeypatch.setattr("aegis.basestation.build.Path", lambda p: tmp_path / "nonexistent" if "opencellid" in str(p).lower() else Path(p))
    source = {"bbox": [3.7, 3.8, 51.0, 51.1], "country_code": 206}
    result = _extract_opencellid(source, "test_ocid", force=True)
    assert result is None
```

- [ ] **Step 2: Run test, verify it fails**

```bash
python -m pytest tests/test_build.py::test_extract_opencellid_skips_without_key -v
```

- [ ] **Step 3: Implement `_extract_opencellid` in build.py**

Add after `_extract_mastedatabasen`:

```python
def _extract_opencellid(source: dict, region_name: str, force: bool = False) -> pd.DataFrame | None:
    outdir = Path("data/basestations/raw")
    outdir.mkdir(parents=True, exist_ok=True)
    outfile = outdir / f"{region_name}_opencellid.parquet"
    if outfile.exists() and not force:
        logger.info("Raw file %s exists, skipping (use --force to re-extract)", outfile)
        return pd.read_parquet(str(outfile))
    # Check for API key: env var first, then file
    api_key = os.environ.get("OPENCELLID_API_KEY", "")
    api_key_path = Path("basestations/basestationLib/OpenCellID/opencellid_api_key.txt")
    if not api_key and not api_key_path.exists():
        logger.warning("No OpenCellID API key found (set OPENCELLID_API_KEY or create %s), skipping", api_key_path)
        return None
    try:
        from basestationLib.OpenCellID.basestations import BaseStations
    except ImportError:
        logger.error("OpenCellID adapter not available. pip install -e basestations/")
        return None
    bbox = source.get("bbox")
    if not bbox:
        logger.warning("No bbox for OpenCellID extraction of %s, skipping", region_name)
        return None
    init_kw: dict = {
        "bounding_box": bbox,
        "output_folder": f"/tmp/aegis_build/{region_name}/",
        "max_workers": 1,
    }
    if api_key:
        # Write temp key file for the adapter
        tmp_key = Path(f"/tmp/aegis_build/{region_name}/ocid_key.txt")
        tmp_key.parent.mkdir(parents=True, exist_ok=True)
        tmp_key.write_text(api_key)
        init_kw["api_key_path"] = str(tmp_key)
    else:
        init_kw["api_key_path"] = str(api_key_path)
    try:
        instance = BaseStations(**init_kw)
        df = instance.extract_antennas(config={})
    except Exception as exc:
        logger.error("OpenCellID extraction failed: %s", exc)
        return None
    if df is None or len(df) == 0:
        logger.warning("No antennas from OpenCellID for %s", region_name)
        return None
    write_raw_parquet(df, str(outfile))
    return df
```

Update `_extract_region`:

```python
elif src_type == "opencellid":
    _extract_opencellid(source, region_name, force=force)
```

- [ ] **Step 4: Run test, verify it passes**

```bash
python -m pytest tests/test_build.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/aegis/basestation/build.py tests/test_build.py
git commit -m "Wire up OpenCellID extractor in build pipeline"
```

---

### Task 3: Add Netherlands and Austria regions to pipeline

**Files:**
- Modify: `data/basestations/regions.yaml`
- Test: `tests/test_build.py`

Both adapters already exist in basestationLib and are registered in `country_module_map.json`. This task only adds region config entries and verifies the pipeline can load them.

- [ ] **Step 1: Write test for new regions in config**

Add to `tests/test_build.py`:

```python
def test_regions_yaml_has_new_regions():
    """Verify Netherlands and Austria are configured in regions.yaml."""
    import yaml
    with open("data/basestations/regions.yaml") as f:
        cfg = yaml.safe_load(f)
    regions = cfg.get("regions", {})
    assert "netherlands" in regions
    assert "austria" in regions
    # Verify they have basestationlib sources
    for name in ["netherlands", "austria"]:
        sources = regions[name].get("sources", [])
        assert any(s.get("type") == "basestationlib" for s in sources), f"{name} missing basestationlib source"
```

- [ ] **Step 2: Run test, verify it fails**

```bash
python -m pytest tests/test_build.py::test_regions_yaml_has_new_regions -v
```

- [ ] **Step 3: Add regions to regions.yaml**

Append to `data/basestations/regions.yaml`:

```yaml
  netherlands:
    sources:
      - type: basestationlib
        country: Netherlands
        bbox: [4.7, 5.1, 52.2, 52.5]
        priority: 1
        source_tag: gov:antenneregister
    reference: data/basestations/raw/brussels_gov.parquet

  austria:
    sources:
      - type: basestationlib
        country: Austria
        bbox: [16.2, 16.6, 48.1, 48.35]
        priority: 1
        source_tag: gov:rtr
    reference: data/basestations/raw/brussels_gov.parquet
```

- [ ] **Step 4: Run test, verify it passes**

```bash
python -m pytest tests/test_build.py -v
```

- [ ] **Step 5: Commit**

```bash
git add data/basestations/regions.yaml tests/test_build.py
git commit -m "Add Netherlands and Austria regions to build pipeline"
```

---

### Task 4: Create Germany (BNetzA) adapter

**Files:**
- Create: `basestations/basestationLib/Countries/Germany/__init__.py`
- Create: `basestations/basestationLib/Countries/Germany/basestations.py`
- Modify: `basestations/basestationLib/core/country_module_map.json`
- Modify: `data/basestations/regions.yaml`
- Test: `tests/test_build.py`

The BNetzA EMF database exposes site data via a POST endpoint at `emf3.bundesnetzagentur.de`. Sites have location, height, operator, and per-antenna azimuth. No frequency or power data is publicly available.

Reference scraper: https://github.com/stefanw/bnetza-emf-scraper

- [ ] **Step 1: Research the actual BNetzA API endpoint**

Before writing code, verify the API endpoint is accessible and understand the response format. Use WebSearch or WebFetch to check if `emf3.bundesnetzagentur.de/Standortservice.asmx/GetStandorte` is still the correct endpoint. Also check the reference scraper repo for any recent changes.

If the endpoint has changed or is inaccessible, document what was found and adjust the implementation accordingly.

- [ ] **Step 2: Write test for Germany adapter import**

Add to `tests/test_build.py`:

```python
def test_germany_adapter_importable():
    """Verify Germany adapter can be imported."""
    from basestationLib.Countries.Germany.basestations import BaseStations
    bs = BaseStations(bounding_box=[13.38, 13.42, 52.50, 52.52])
    assert hasattr(bs, "extract_antennas")
```

- [ ] **Step 3: Run test, verify it fails**

```bash
python -m pytest tests/test_build.py::test_germany_adapter_importable -v
```

- [ ] **Step 4: Create Germany adapter**

Create `basestations/basestationLib/Countries/Germany/__init__.py` (empty).

Create `basestations/basestationLib/Countries/Germany/basestations.py`:

```python
"""Germany adapter: BNetzA EMF-Datenbank (bundesnetzagentur.de)."""

from __future__ import annotations

import logging
import math
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
import requests

logger = logging.getLogger(__name__)

API_URL = "https://emf3.bundesnetzagentur.de/Standortservice.asmx/GetStandorte"
TILE_SIZE = 0.1  # degrees


class BaseStations:
    """Extract antenna data from BNetzA EMF database."""

    def __init__(
        self,
        output_folder: str = "output/germany/",
        bounding_box: list[float] | None = None,
        operator: str | None = None,
        technology: str | None = None,
        max_workers: int = 2,
        **kwargs,
    ):
        self.output_folder = output_folder
        self.bounding_box = bounding_box
        self.operator = operator
        self.technology = technology
        self.max_workers = max_workers

    def extract_antennas(self, config: dict | None = None) -> pd.DataFrame:
        """Extract antenna data from BNetzA API.

        Fields available: location, height, operator, azimuth.
        Fields missing: power, frequency, tilt, gain, beamwidth.
        """
        if not self.bounding_box:
            logger.error("bounding_box is required for Germany extraction")
            return pd.DataFrame()

        tiles = self._tile_bbox()
        all_rows = []
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "AEGIS-Dosimetry-Research/1.0",
        })

        for i, tile in enumerate(tiles):
            try:
                rows = self._fetch_tile(session, tile)
                all_rows.extend(rows)
                if (i + 1) % 10 == 0:
                    logger.info("Fetched %d/%d tiles (%d antennas so far)", i + 1, len(tiles), len(all_rows))
            except Exception as exc:
                logger.warning("Failed to fetch tile %s: %s", tile, exc)

        if not all_rows:
            logger.warning("No antennas extracted from BNetzA")
            return pd.DataFrame()

        df = pd.DataFrame(all_rows)

        if self.operator:
            df = df[df["Operator"].str.contains(self.operator, case=False, na=False)]

        logger.info("Extracted %d antennas from BNetzA", len(df))

        from basestationLib.utils.create_output_df import create_output_df
        return create_output_df(df, config or {}, {})

    def _tile_bbox(self) -> list[tuple[float, float, float, float]]:
        """Split bbox into tiles of TILE_SIZE degrees."""
        min_lon, max_lon, min_lat, max_lat = self.bounding_box
        tiles = []
        lat = min_lat
        while lat < max_lat:
            lon = min_lon
            while lon < max_lon:
                tiles.append((
                    lat,
                    lon,
                    min(lat + TILE_SIZE, max_lat),
                    min(lon + TILE_SIZE, max_lon),
                ))
                lon += TILE_SIZE
            lat += TILE_SIZE
        return tiles

    def _fetch_tile(self, session: requests.Session, tile: tuple[float, float, float, float]) -> list[dict]:
        """Fetch sites for one tile from the BNetzA API."""
        min_lat, min_lon, max_lat, max_lon = tile
        data = {
            "minLat": str(min_lat),
            "maxLat": str(max_lat),
            "minLon": str(min_lon),
            "maxLon": str(max_lon),
        }
        resp = session.post(API_URL, data=data, timeout=30)
        resp.raise_for_status()
        return self._parse_xml(resp.text)

    def _parse_xml(self, xml_text: str) -> list[dict]:
        """Parse BNetzA XML response into rows."""
        rows = []
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            logger.warning("XML parse error: %s", exc)
            return rows

        # Handle XML namespaces
        ns = ""
        if root.tag.startswith("{"):
            ns = root.tag.split("}")[0] + "}"

        for site in root.iter(f"{ns}Standort"):
            site_id = self._text(site, f"{ns}Standortnr") or self._text(site, f"{ns}StandortId") or ""
            lat = self._float(site, f"{ns}Breitengrad") or self._float(site, f"{ns}Latitude")
            lon = self._float(site, f"{ns}Laengengrad") or self._float(site, f"{ns}Longitude")
            height = self._float(site, f"{ns}Masthoe") or self._float(site, f"{ns}Hoehe")
            operator = self._text(site, f"{ns}Betreiber") or self._text(site, f"{ns}Operator") or ""

            if lat is None or lon is None:
                continue

            # Look for individual antennas
            antennas = list(site.iter(f"{ns}Antenne"))
            if not antennas:
                # No sub-elements, create one row for the site
                rows.append(self._make_row(site_id, operator, lat, lon, height, None))
            else:
                for ant in antennas:
                    azimuth = self._float(ant, f"{ns}Richtung") or self._float(ant, f"{ns}Azimut")
                    rows.append(self._make_row(site_id, operator, lat, lon, height, azimuth))

        return rows

    @staticmethod
    def _make_row(site_id: str, operator: str, lat: float, lon: float, height: float | None, azimuth: float | None) -> dict:
        return {
            "SiteCode": f"DE_{site_id}",
            "AntennaLabel": f"DE_{site_id}_{int(azimuth or 0)}",
            "Operator": operator,
            "Technology": "",
            "Latitude": lat,
            "Longitude": lon,
            "CenterHeight": height,
            "Power": None,
            "Frequency": None,
            "FrequencyBand": None,
            "Electrical_Tilt": None,
            "Mechanical_Tilt": None,
            "Azimuth": azimuth,
            "Gain": None,
            "Horizontal_Beamwidth": None,
            "Vertical_Beamwidth": None,
        }

    @staticmethod
    def _text(elem, tag: str) -> str | None:
        child = elem.find(tag)
        return child.text.strip() if child is not None and child.text else None

    @staticmethod
    def _float(elem, tag: str) -> float | None:
        text = BaseStations._text(elem, tag)
        if text is None:
            return None
        try:
            return float(text.replace(",", "."))
        except ValueError:
            return None
```

- [ ] **Step 5: Register in country_module_map.json**

Add `"germany": "basestationLib.Countries.Germany.basestations"` to the JSON.

- [ ] **Step 6: Add germany region to regions.yaml**

```yaml
  germany:
    sources:
      - type: basestationlib
        country: Germany
        bbox: [13.2, 13.6, 52.4, 52.6]
        priority: 1
    reference: data/basestations/raw/brussels_gov.parquet
```

- [ ] **Step 7: Run test, verify it passes**

```bash
python -m pytest tests/test_build.py::test_germany_adapter_importable -v
```

- [ ] **Step 8: Commit**

```bash
git add basestations/basestationLib/Countries/Germany/ basestations/basestationLib/core/country_module_map.json data/basestations/regions.yaml tests/test_build.py
git commit -m "Add Germany (BNetzA) adapter"
```

---

### Task 5: Create Australia (ACMA RRL) adapter

**Files:**
- Create: `basestations/basestationLib/Countries/Australia/__init__.py`
- Create: `basestations/basestationLib/Countries/Australia/basestations.py`
- Modify: `basestations/basestationLib/core/country_module_map.json`
- Modify: `data/basestations/regions.yaml`
- Test: `tests/test_build.py`

ACMA distributes a daily ZIP with pipe-delimited CSVs. Join site + antenna + device_details + licence tables. Cache the ZIP at `~/.cache/aegis/acma_rrl.zip`.

- [ ] **Step 1: Research the ACMA download URL**

Verify the current download URL for `spectra_rrl.zip` (or equivalent) from acma.gov.au. The URL has changed over time. Check data.gov.au as an alternative source.

- [ ] **Step 2: Write test for Australia adapter import**

Add to `tests/test_build.py`:

```python
def test_australia_adapter_importable():
    """Verify Australia adapter can be imported."""
    from basestationLib.Countries.Australia.basestations import BaseStations
    bs = BaseStations(bounding_box=[150.9, 151.4, -34.0, -33.7])
    assert hasattr(bs, "extract_antennas")
```

- [ ] **Step 3: Run test, verify it fails**

```bash
python -m pytest tests/test_build.py::test_australia_adapter_importable -v
```

- [ ] **Step 4: Create Australia adapter**

Create `basestations/basestationLib/Countries/Australia/__init__.py` (empty).

Create `basestations/basestationLib/Countries/Australia/basestations.py`:

```python
"""Australia adapter: ACMA Register of Radiocommunications Licences."""

from __future__ import annotations

import io
import logging
import os
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests

logger = logging.getLogger(__name__)

# ACMA RRL download URL (daily ZIP)
DOWNLOAD_URL = "https://www.acma.gov.au/sites/default/files/spectra_rrl.zip"
CACHE_DIR = Path.home() / ".cache" / "aegis"
CACHE_FILE = CACHE_DIR / "acma_rrl.zip"

# Mobile carrier-related service types
MOBILE_SERVICE_TYPES = {"MOBILE", "LAND MOBILE", "RADIODETERMINATION"}
# Common Australian mobile bands (MHz)
MOBILE_BANDS_MHZ = {700, 850, 900, 1800, 2100, 2600, 3500, 3600, 26000, 28000}


class BaseStations:
    """Extract antenna data from ACMA RRL."""

    def __init__(
        self,
        output_folder: str = "output/australia/",
        bounding_box: list[float] | None = None,
        operator: str | None = None,
        technology: str | None = None,
        zip_path: str | None = None,
        max_workers: int = 1,
        **kwargs,
    ):
        self.output_folder = output_folder
        self.bounding_box = bounding_box
        self.operator = operator
        self.technology = technology
        self.zip_path = Path(zip_path) if zip_path else CACHE_FILE
        self.max_workers = max_workers

    def extract_antennas(self, config: dict | None = None) -> pd.DataFrame:
        """Extract antenna data from ACMA RRL ZIP.

        Downloads the ZIP if not cached, joins tables, filters to mobile
        cellular, applies bbox filter, and returns standardized DataFrame.
        """
        try:
            self._ensure_zip()
        except Exception as exc:
            logger.error("Failed to download ACMA RRL data: %s", exc)
            return pd.DataFrame()

        try:
            df = self._load_and_join()
        except Exception as exc:
            logger.error("Failed to parse ACMA RRL data: %s", exc)
            return pd.DataFrame()

        if df.empty:
            logger.warning("No mobile cellular antennas found in ACMA RRL")
            return pd.DataFrame()

        # Apply bbox filter
        if self.bounding_box:
            min_lon, max_lon, min_lat, max_lat = self.bounding_box
            df = df[
                (df["Latitude"] >= min_lat)
                & (df["Latitude"] <= max_lat)
                & (df["Longitude"] >= min_lon)
                & (df["Longitude"] <= max_lon)
            ]

        if self.operator:
            df = df[df["Operator"].str.contains(self.operator, case=False, na=False)]

        logger.info("Extracted %d antennas from ACMA RRL", len(df))

        try:
            from basestationLib.utils.create_output_df import create_output_df
            return create_output_df(df, config or {}, {})
        except Exception:
            return df

    def _ensure_zip(self) -> None:
        """Download the ACMA RRL ZIP if not cached."""
        if self.zip_path.exists():
            # Check age: re-download if older than 7 days
            import time
            age_hours = (time.time() - self.zip_path.stat().st_mtime) / 3600
            if age_hours < 168:  # 7 days
                logger.info("Using cached ACMA RRL data (%d hours old)", int(age_hours))
                return
            logger.info("ACMA cache is %d hours old, re-downloading", int(age_hours))

        self.zip_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Downloading ACMA RRL data from %s ...", DOWNLOAD_URL)
        resp = requests.get(DOWNLOAD_URL, timeout=300, stream=True)
        resp.raise_for_status()
        with open(self.zip_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.info("Downloaded ACMA RRL data to %s", self.zip_path)

    def _load_and_join(self) -> pd.DataFrame:
        """Load CSVs from ZIP and join into antenna records."""
        with zipfile.ZipFile(self.zip_path) as zf:
            names = zf.namelist()
            site_file = self._find_file(names, "site")
            antenna_file = self._find_file(names, "antenna")
            device_file = self._find_file(names, "device_detail")
            licence_file = self._find_file(names, "licence")

            if not all([site_file, antenna_file, device_file, licence_file]):
                logger.error("Missing required files in ACMA ZIP. Found: %s", names[:20])
                return pd.DataFrame()

            site = pd.read_csv(zf.open(site_file), delimiter="|", low_memory=False)
            antenna = pd.read_csv(zf.open(antenna_file), delimiter="|", low_memory=False)
            device = pd.read_csv(zf.open(device_file), delimiter="|", low_memory=False)
            licence = pd.read_csv(zf.open(licence_file), delimiter="|", low_memory=False)

        # Normalize column names to lowercase
        site.columns = site.columns.str.strip().str.lower()
        antenna.columns = antenna.columns.str.strip().str.lower()
        device.columns = device.columns.str.strip().str.lower()
        licence.columns = licence.columns.str.strip().str.lower()

        # Filter to active mobile licences
        if "licence_status_desc" in licence.columns:
            licence = licence[licence["licence_status_desc"].str.upper() == "CURRENT"]
        elif "licence_status" in licence.columns:
            licence = licence[licence["licence_status"].str.upper().isin(["CURRENT", "ACTIVE"])]

        # Join
        join_key = "licence_no" if "licence_no" in licence.columns else licence.columns[0]
        merged = licence
        if "site_id" in site.columns and "site_id" in licence.columns:
            merged = merged.merge(site, on="site_id", how="left", suffixes=("", "_site"))
        if join_key in antenna.columns:
            merged = merged.merge(antenna, on=join_key, how="left", suffixes=("", "_ant"))
        if join_key in device.columns:
            merged = merged.merge(device, on=join_key, how="left", suffixes=("", "_dev"))

        # Filter to cellular mobile frequencies
        freq_col = next((c for c in merged.columns if "frequency" in c and "band" not in c), None)
        if freq_col:
            merged[freq_col] = pd.to_numeric(merged[freq_col], errors="coerce")
            # Keep records in mobile bands (within 20% of known band centers)
            mobile_mask = pd.Series(False, index=merged.index)
            for band in MOBILE_BANDS_MHZ:
                mobile_mask |= (merged[freq_col] >= band * 0.8) & (merged[freq_col] <= band * 1.2)
            merged = merged[mobile_mask]

        # Map to standard columns
        rows = []
        lat_col = next((c for c in merged.columns if "lat" in c), None)
        lon_col = next((c for c in merged.columns if "lon" in c), None)
        if not lat_col or not lon_col:
            logger.error("Cannot find lat/lon columns in ACMA data")
            return pd.DataFrame()

        for _, row in merged.iterrows():
            lat = pd.to_numeric(row.get(lat_col), errors="coerce")
            lon = pd.to_numeric(row.get(lon_col), errors="coerce")
            if pd.isna(lat) or pd.isna(lon):
                continue

            # EIRP: ACMA stores in dBW, convert to dBm
            eirp_dbw = pd.to_numeric(row.get("eirp", row.get("eirp_dbw", np.nan)), errors="coerce")
            eirp_dbm = eirp_dbw + 30 if pd.notna(eirp_dbw) else np.nan

            freq = pd.to_numeric(row.get(freq_col, np.nan), errors="coerce")
            azimuth = pd.to_numeric(row.get("azimuth", row.get("bearing", np.nan)), errors="coerce")
            tilt = pd.to_numeric(row.get("antenna_tilt", row.get("tilt", np.nan)), errors="coerce")
            gain = pd.to_numeric(row.get("gain", row.get("antenna_gain", np.nan)), errors="coerce")
            height = pd.to_numeric(row.get("antenna_height", row.get("height", np.nan)), errors="coerce")

            licensee = str(row.get("licensee_name", row.get("client_name", "")))
            site_id = str(row.get("site_id", row.get(join_key, "")))

            rows.append({
                "SiteCode": f"AU_{site_id}",
                "AntennaLabel": f"AU_{site_id}_{int(azimuth) if pd.notna(azimuth) else 0}",
                "Operator": licensee,
                "Technology": self._freq_to_tech(freq),
                "Latitude": float(lat),
                "Longitude": float(lon),
                "CenterHeight": height if pd.notna(height) else None,
                "Power": eirp_dbm if pd.notna(eirp_dbm) else None,
                "Frequency": freq if pd.notna(freq) else None,
                "FrequencyBand": self._freq_to_band(freq) if pd.notna(freq) else None,
                "Electrical_Tilt": tilt if pd.notna(tilt) else None,
                "Mechanical_Tilt": None,
                "Azimuth": azimuth if pd.notna(azimuth) else None,
                "Gain": gain if pd.notna(gain) else None,
                "Horizontal_Beamwidth": None,
                "Vertical_Beamwidth": None,
            })

        return pd.DataFrame(rows)

    @staticmethod
    def _find_file(names: list[str], keyword: str) -> str | None:
        """Find a file in the ZIP matching a keyword."""
        for name in names:
            if keyword in name.lower() and name.lower().endswith(".csv"):
                return name
        return None

    @staticmethod
    def _freq_to_tech(freq_mhz: float) -> str:
        """Guess technology from frequency."""
        if pd.isna(freq_mhz):
            return ""
        if freq_mhz >= 24000:
            return "5G"
        if freq_mhz >= 3300:
            return "5G"
        if freq_mhz >= 2500:
            return "4G"
        if freq_mhz >= 1700:
            return "4G"
        if freq_mhz >= 800:
            return "4G"
        return "3G"

    @staticmethod
    def _freq_to_band(freq_mhz: float) -> str:
        """Map frequency to band name."""
        if pd.isna(freq_mhz):
            return ""
        bands = [
            (690, 760, "Band700MHz"),
            (820, 890, "Band850MHz"),
            (880, 960, "Band900MHz"),
            (1710, 1880, "Band1800MHz"),
            (1920, 2170, "Band2100MHz"),
            (2500, 2700, "Band2600MHz"),
            (3400, 3800, "Band3500MHz"),
            (24000, 30000, "Band26GHz"),
        ]
        for lo, hi, name in bands:
            if lo <= freq_mhz <= hi:
                return name
        return f"Band{int(freq_mhz)}MHz"
```

- [ ] **Step 5: Register in country_module_map.json**

Add `"australia": "basestationLib.Countries.Australia.basestations"` to the JSON.

- [ ] **Step 6: Add australia region to regions.yaml**

```yaml
  australia:
    sources:
      - type: basestationlib
        country: Australia
        bbox: [150.9, 151.4, -34.0, -33.7]
        priority: 1
    reference: data/basestations/raw/brussels_gov.parquet
```

- [ ] **Step 7: Run test, verify it passes**

```bash
python -m pytest tests/test_build.py::test_australia_adapter_importable -v
```

- [ ] **Step 8: Commit**

```bash
git add basestations/basestationLib/Countries/Australia/ basestations/basestationLib/core/country_module_map.json data/basestations/regions.yaml tests/test_build.py
git commit -m "Add Australia (ACMA RRL) adapter"
```

---

### Task 6: Fix source tag derivation and add new tags

**Files:**
- Modify: `src/aegis/basestation/build.py` (`_merge_region` function)
- Modify: `src/aegis/basestation/parquet_io.py:34-45`
- Modify: `data/basestations/regions.yaml`

Two fixes: (1) `_merge_region` derives source tags as `gov:{region_name}` (e.g. `gov:netherlands`) which won't match the `_SOURCE_CONFIDENCE` registry. Add an explicit `source_tag` field to each source in `regions.yaml` and use it in `_merge_region`. (2) Add confidence mappings for new source tags.

- [ ] **Step 1: Add `source_tag` field to all sources in regions.yaml**

Every source entry should have a `source_tag` field matching the registry:

```yaml
regions:
  brussels:
    sources:
      - type: basestationlib
        country: Belgium
        region: brussels
        priority: 1
        source_tag: gov:brussels
    reference: data/basestations/raw/brussels_gov.parquet

  flanders:
    sources:
      - type: basestationlib
        country: Belgium
        region: flanders
        priority: 1
        source_tag: gov:flanders
    reference: data/basestations/raw/brussels_gov.parquet

  france:
    sources:
      - type: basestationlib
        country: France
        bbox: [1.5, 3.0, 48.5, 49.2]
        priority: 1
        source_tag: gov:anfr
      - type: opencellid
        country_code: 208
        bbox: [1.5, 3.0, 48.5, 49.2]
        priority: 3
        source_tag: ocid
    reference: data/basestations/raw/brussels_gov.parquet

  denmark:
    sources:
      - type: mastedatabasen
        bbox: [12.4, 12.7, 55.6, 55.8]
        priority: 1
        source_tag: gov:mastedatabasen
      - type: opencellid
        country_code: 238
        bbox: [12.4, 12.7, 55.6, 55.8]
        priority: 3
        source_tag: ocid
    reference: data/basestations/raw/brussels_gov.parquet

  netherlands:
    sources:
      - type: basestationlib
        country: Netherlands
        bbox: [4.7, 5.1, 52.2, 52.5]
        priority: 1
        source_tag: gov:antenneregister
    reference: data/basestations/raw/brussels_gov.parquet

  austria:
    sources:
      - type: basestationlib
        country: Austria
        bbox: [16.2, 16.6, 48.1, 48.35]
        priority: 1
        source_tag: gov:rtr
    reference: data/basestations/raw/brussels_gov.parquet

  germany:
    sources:
      - type: basestationlib
        country: Germany
        bbox: [13.2, 13.6, 52.4, 52.6]
        priority: 1
        source_tag: gov:bnetza
    reference: data/basestations/raw/brussels_gov.parquet

  australia:
    sources:
      - type: basestationlib
        country: Australia
        bbox: [150.9, 151.4, -34.0, -33.7]
        priority: 1
        source_tag: gov:acma
    reference: data/basestations/raw/brussels_gov.parquet
```

- [ ] **Step 2: Fix `_merge_region` to use `source_tag` from config**

In `build.py`, change the source tag derivation in `_merge_region`:

```python
# Replace:
source_tag = f"gov:{source.get('region', region_name)}"
# With:
source_tag = source.get("source_tag", f"gov:{source.get('region', region_name)}")
```

Apply the same pattern for the `mastedatabasen` and `opencellid` cases:

```python
elif src_type == "mastedatabasen":
    raw_file = raw_dir / f"{region_name}_mastedatabasen.parquet"
    source_tag = source.get("source_tag", "gov:mastedatabasen")
elif src_type == "opencellid":
    raw_file = raw_dir / f"{region_name}_opencellid.parquet"
    source_tag = source.get("source_tag", "ocid")
```

- [ ] **Step 3: Add new source tags to `_SOURCE_CONFIDENCE` in parquet_io.py**

Add these two entries (the others are already present):

```python
"gov:rtr": CONFIDENCE_SCORES["gov_report"],
"gov:acma": CONFIDENCE_SCORES["gov_report"],
```

- [ ] **Step 4: Commit**

```bash
git add src/aegis/basestation/build.py src/aegis/basestation/parquet_io.py data/basestations/regions.yaml
git commit -m "Fix source tag derivation and add RTR/ACMA confidence mappings"
```

---

### Task 7: Run the build pipeline and fix bugs

**Files:**
- Modify: any files where bugs are found
- No test file: this is integration testing via the CLI

This is the most important task. Run the pipeline with real data and fix whatever breaks.

- [ ] **Step 1: Install basestationLib if needed**

```bash
pip install -e basestations/
```

- [ ] **Step 2: Extract Brussels first (gold standard)**

```bash
python -m aegis.basestation.build extract --region brussels --force
```

This should produce `data/basestations/raw/brussels_gov.parquet`. If it fails, debug the adapter and fix. Brussels is the reference dataset used by all other regions for estimation, so it must succeed first.

- [ ] **Step 3: Extract Flanders**

```bash
python -m aegis.basestation.build extract --region flanders --force
```

- [ ] **Step 4: Extract France**

```bash
python -m aegis.basestation.build extract --region france --force
```

- [ ] **Step 5: Extract Denmark**

```bash
python -m aegis.basestation.build extract --region denmark --force
```

- [ ] **Step 6: Extract Netherlands**

```bash
python -m aegis.basestation.build extract --region netherlands --force
```

- [ ] **Step 7: Extract Austria**

```bash
python -m aegis.basestation.build extract --region austria --force
```

- [ ] **Step 8: Extract Germany**

```bash
python -m aegis.basestation.build extract --region germany --force
```

- [ ] **Step 9: Extract Australia**

```bash
python -m aegis.basestation.build extract --region australia --force
```

Note: This downloads a ~200MB ZIP file. May take several minutes.

- [ ] **Step 10: Run merge and validate for all regions**

```bash
python -m aegis.basestation.build all
```

This will skip extraction (files exist), then merge, validate, and report. Fix any merge/validate bugs.

- [ ] **Step 11: Check the coverage report**

The report should show column fill percentages per region. Brussels should be ~100% on all columns. Denmark should be ~0% on Power/Azimuth/Tilt/Gain/Beamwidth (until estimation fills them). After merge with estimation, most fields should have some fill from `est:tech+band` or `est:ref`.

- [ ] **Step 12: Commit raw and merged data if reasonable size**

Check total size: `du -sh data/basestations/`. If under 50 MB, add to git. If larger, add to `.gitignore` and document.

```bash
git add data/basestations/raw/ data/basestations/merged/
git commit -m "Add extracted and merged base station data for 8 regions"
```

If data files are too large for git:

```bash
echo "data/basestations/raw/*.parquet" >> .gitignore
echo "data/basestations/merged/*.parquet" >> .gitignore
git add .gitignore
git commit -m "Exclude large Parquet data files from git"
```

---

### Task 8: MapRad research and documentation update

**Files:**
- Modify: `docs/internal/base-station-data-sources.md`

- [ ] **Step 1: Research MapRad.io**

Use WebSearch to answer:
1. What data sources does MapRad.io aggregate?
2. Is there a public API or only the web UI?
3. Is it free or commercial?
4. How does it compare to going direct to government sources?

- [ ] **Step 2: Update the research doc**

The file already has a brief MapRad section (around line 144). Expand it with the research findings. Keep it 2-3 paragraphs, factual, no marketing language. Answer the four questions above.

- [ ] **Step 3: Commit**

```bash
git add docs/internal/base-station-data-sources.md
git commit -m "Expand MapRad.io section in data sources research doc"
```

---

### Task 9: End-to-end viewer verification

**Files:**
- May need to modify: `src/aegis/viewer/routes/basestations.py` if bugs found

After data extraction, verify the full viewer pipeline works with Parquet data.

- [ ] **Step 1: Start the viewer**

```bash
python -m aegis.viewer &
```

- [ ] **Step 2: Test Parquet loading via API**

```bash
curl -s -X POST http://localhost:5000/api/basestations/load \
  -H "Content-Type: application/json" \
  -d '{"location": "Brussels, Belgium", "radius_m": 500}' | python -m json.tool | head -30
```

Verify:
- Response has `basestations` array
- Each entry has `confidence` (should be close to 1.0 for Brussels)
- Each entry has `provenance` dict with field-level sources
- `frequency_band` is populated

- [ ] **Step 3: Test other regions**

```bash
curl -s -X POST http://localhost:5000/api/basestations/load \
  -H "Content-Type: application/json" \
  -d '{"location": "Copenhagen, Denmark", "radius_m": 1000}' | python -m json.tool | head -30
```

Verify Denmark loads from Parquet with lower confidence scores (more estimation).

- [ ] **Step 4: Fix any issues found**

If loading fails or data is malformed, fix the relevant code (viewer route, parquet_io, merge).

- [ ] **Step 5: Commit any fixes**

Stage only the specific files that were modified, then commit:

```bash
git add src/aegis/viewer/routes/basestations.py  # and any other modified files
git commit -m "Fix viewer integration issues with Parquet loading"
```

---

### Task 10: Run lint and tests, final commit and push

**Files:**
- All modified files

- [ ] **Step 1: Run ruff**

```bash
python -m ruff check src/ tests/
python -m ruff format --check src/ tests/
```

Fix any issues.

- [ ] **Step 2: Run tests**

```bash
python -m pytest tests/ -m "not slow" -x
```

All tests should pass.

- [ ] **Step 3: Push to master**

```bash
git push origin master
```

- [ ] **Step 4: Tag if appropriate**

If the user confirms, tag a minor release:

```bash
git tag v0.12.0
git push origin master --tags
```
