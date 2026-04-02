"""Canada adapter: ISED SMS (Spectrum Management System).

Data source: https://ised-isde.canada.ca/site/spectrum-management-system/en/download-sms-data
License: Open Government Licence - Canada
Updated weekly by ISED. Cache TTL: 7 days.

Primary path: download the SMS ZIP, join site_data.csv + transmitter_data.csv.
Fallback path: ArcGIS REST API for bbox queries when ZIP is not available.

Key columns used from the ZIP:
- site_data.csv:       SITE_ID, LATITUDE, LONGITUDE, ANTENNA_HEIGHT_M
- transmitter_data.csv: SITE_ID, AZIMUTH_OF_MAIN_LOBE, TX_POWER_DBW,
                         FREQUENCY_MHZ, LICENSE_TYPE_CODE, STATUS_CODE,
                         COMPANY_NAME, POWER_TYPE

Only active records with mobile cellular licence type codes are retained.
"""

from __future__ import annotations

import io
import logging
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
import requests

logger = logging.getLogger(__name__)

ZIP_URL = "https://ised-isde.canada.ca/ised/site/spectrum-management-system/files/sms_data.zip"
CACHE_PATH = Path.home() / ".cache" / "aegis" / "canada_ised.zip"
CACHE_TTL_DAYS = 7

# ArcGIS endpoint for bbox queries (fallback)
ARCGIS_URL = (
    "https://services1.arcgis.com/v6OKGagFNlXn4OTL/arcgis/rest/services"
    "/SMS_Public/FeatureServer/0/query"
)
ARCGIS_PAGE_SIZE = 2000

# Mobile cellular licence type codes to retain.
# CL=Cellular, PCS=Personal Communications, AWS=Advanced Wireless,
# 700=700 MHz band, 2500=2500 MHz band.
MOBILE_LICENCE_CODES = {"CL", "PCS", "AWS", "700", "2500", "MBS", "CELL", "IMT"}

# Operator MCC/MNC normalization. The SMS dataset uses subsidiary company names.
_OPERATOR_NORM: dict[str, str] = {
    "rogers": "Rogers",
    "fido": "Rogers",
    "chatr": "Rogers",
    "bell": "Bell",
    "virgin": "Bell",
    "solo": "Bell",
    "telus": "Telus",
    "koodo": "Telus",
    "public mobile": "Telus",
    "shaw": "Shaw",
    "freedom": "Freedom Mobile",
    "videotron": "Videotron",
    "sasktel": "SaskTel",
    "mts": "Bell",
    "eastlink": "Eastlink",
    "tbaytel": "TBayTel",
}


def _normalize_operator(name: str | None) -> str | None:
    """Map subsidiary/brand names to canonical operator names."""
    if not name:
        return name
    name_lc = name.lower()
    for keyword, canonical in _OPERATOR_NORM.items():
        if keyword in name_lc:
            return canonical
    return name


class BaseStations:
    """Extract antenna data from the ISED SMS dataset (Canada).

    Supports two extraction paths:
    - ZIP download (default): downloads and caches the full SMS dataset,
      filters by service type and bounding box, joins site + transmitter tables.
    - ArcGIS REST API (fallback): used when ``use_arcgis=True`` or when the
      ZIP is unavailable. Paginates by resultOffset for the given bbox.
    """

    def __init__(
        self,
        output_folder: str = "output/canada/",
        bounding_box: list[float] | None = None,
        operator: str | None = None,
        technology: str | None = None,
        zip_path: str | None = None,
        use_arcgis: bool = False,
        **kwargs,
    ):
        self.output_folder = output_folder
        # bbox: [min_lon, max_lon, min_lat, max_lat]
        self.bounding_box = bounding_box
        self.operator = operator
        self.technology = technology
        # Optional path to a pre-downloaded ZIP (skips download/cache logic)
        self.zip_path = Path(zip_path) if zip_path else None
        self.use_arcgis = use_arcgis

    def extract_antennas(self, config: dict | None = None) -> pd.DataFrame:
        """Extract antenna data from the ISED SMS dataset.

        Fields available: location, antenna height, azimuth, transmit power,
        frequency, operator name.
        Fields missing: electrical tilt, mechanical tilt, gain, beamwidth.
        """
        rows = self._extract_arcgis() if self.use_arcgis else self._extract_zip()

        if not rows:
            logger.warning("No antenna records extracted for Canada")
            return pd.DataFrame()

        df = pd.DataFrame(rows)

        if self.operator:
            df = df[df["Operator"].str.contains(self.operator, case=False, na=False)]
        if self.technology:
            df = df[df["Technology"].str.contains(self.technology, case=False, na=False)]

        from basestationLib.utils.create_output_df import create_output_df

        return create_output_df(df, config or {}, {})

    # ------------------------------------------------------------------
    # ZIP download path
    # ------------------------------------------------------------------

    def _extract_zip(self) -> list[dict]:
        """Download (or use cached) SMS ZIP, parse and return standardised rows."""
        try:
            zip_bytes = self._get_zip()
        except Exception as exc:
            logger.error("Failed to obtain ISED SMS ZIP: %s", exc)
            logger.info("Falling back to ArcGIS REST API")
            return self._extract_arcgis()

        try:
            return self._parse_zip(zip_bytes)
        except Exception as exc:
            logger.error("Failed to parse ISED SMS ZIP: %s", exc)
            return []

    def _get_zip(self) -> bytes:
        """Return ZIP bytes, using disk cache if fresh enough."""
        if self.zip_path and self.zip_path.exists():
            logger.info("Using provided ZIP path: %s", self.zip_path)
            return self.zip_path.read_bytes()

        if self._cache_is_fresh():
            logger.info("Using cached ISED SMS data from %s", CACHE_PATH)
            return CACHE_PATH.read_bytes()

        logger.info("Downloading ISED SMS data from %s", ZIP_URL)
        resp = requests.get(ZIP_URL, timeout=300, stream=True)
        resp.raise_for_status()

        chunks = []
        for chunk in resp.iter_content(chunk_size=1024 * 1024):
            if chunk:
                chunks.append(chunk)
        data = b"".join(chunks)

        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_bytes(data)
        logger.info("Cached ISED SMS data to %s (%d bytes)", CACHE_PATH, len(data))
        return data

    @staticmethod
    def _cache_is_fresh() -> bool:
        if not CACHE_PATH.exists():
            return False
        age = datetime.now(tz=UTC) - datetime.fromtimestamp(CACHE_PATH.stat().st_mtime, tz=UTC)
        return age < timedelta(days=CACHE_TTL_DAYS)

    def _parse_zip(self, zip_bytes: bytes) -> list[dict]:
        """Join SMS CSV tables and return standardised rows.

        The ZIP contains pipe-delimited files. Column names vary by dataset
        version, so we do case-insensitive matching.
        """
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            names_map = {n.lower(): n for n in zf.namelist()}

            def read_csv(keyword: str) -> pd.DataFrame:
                match = next(
                    (v for k, v in names_map.items() if keyword in k and k.endswith(".csv")),
                    None,
                )
                if match is None:
                    logger.warning("File containing '%s' not found in SMS ZIP", keyword)
                    return pd.DataFrame()
                logger.info("Reading %s from ZIP", match)
                with zf.open(match) as f:
                    return pd.read_csv(f, sep="|", dtype=str, low_memory=False)

            site_df = read_csv("site_data")
            tx_df = read_csv("transmitter_data")

        if site_df.empty or tx_df.empty:
            logger.warning(
                "Missing SMS tables (site_data=%s, transmitter_data=%s)",
                site_df.empty,
                tx_df.empty,
            )
            return []

        # Normalise column names to uppercase stripped strings
        site_df.columns = [c.strip().upper() for c in site_df.columns]
        tx_df.columns = [c.strip().upper() for c in tx_df.columns]

        logger.info("SMS raw: %d sites, %d transmitter records", len(site_df), len(tx_df))

        # Filter transmitters: active status only
        status_col = self._find_col(tx_df, "STATUS_CODE", "STATUS")
        if status_col:
            active_mask = tx_df[status_col].str.upper().isin({"ACTIVE", "1", "A"})
            tx_df = tx_df[active_mask]
            logger.info("After status filter: %d transmitter records", len(tx_df))

        # Filter to mobile cellular licence types
        lic_col = self._find_col(tx_df, "LICENSE_TYPE_CODE", "LICENCE_TYPE_CODE", "LIC_TYPE")
        if lic_col:
            mobile_mask = tx_df[lic_col].str.upper().isin(MOBILE_LICENCE_CODES)
            tx_df_mobile = tx_df[mobile_mask]
            if tx_df_mobile.empty:
                logger.warning(
                    "No records matched MOBILE_LICENCE_CODES %s; keeping all active records",
                    MOBILE_LICENCE_CODES,
                )
            else:
                tx_df = tx_df_mobile
                logger.info("After licence filter: %d transmitter records", len(tx_df))

        # Join site info onto transmitters
        site_id_col_tx = self._find_col(tx_df, "SITE_ID", "SITEID", "SITE")
        site_id_col_site = self._find_col(site_df, "SITE_ID", "SITEID", "SITE")

        if site_id_col_tx and site_id_col_site:
            # Resolve lat/lon column names from site_df
            lat_col = self._find_col(site_df, "LATITUDE", "LAT")
            lon_col = self._find_col(site_df, "LONGITUDE", "LON", "LNG", "LONG")
            height_col = self._find_col(site_df, "ANTENNA_HEIGHT_M", "HEIGHT_M", "ANT_HEIGHT", "HEIGHT")

            site_keep = [site_id_col_site]
            if lat_col:
                site_keep.append(lat_col)
            if lon_col:
                site_keep.append(lon_col)
            if height_col:
                site_keep.append(height_col)

            tx_df = tx_df.merge(
                site_df[site_keep].drop_duplicates(site_id_col_site),
                left_on=site_id_col_tx,
                right_on=site_id_col_site,
                how="left",
            )
        else:
            logger.warning("Could not join site data: site_id columns not found")
            lat_col = self._find_col(tx_df, "LATITUDE", "LAT")
            lon_col = self._find_col(tx_df, "LONGITUDE", "LON", "LNG", "LONG")
            height_col = self._find_col(tx_df, "ANTENNA_HEIGHT_M", "HEIGHT_M", "ANT_HEIGHT")

        # Resolve coordinate columns after merge
        lat_col = self._find_col(tx_df, "LATITUDE", "LAT")
        lon_col = self._find_col(tx_df, "LONGITUDE", "LON", "LNG", "LONG")

        if lat_col is None or lon_col is None:
            logger.error("Latitude/longitude columns not found in merged SMS data")
            return []

        tx_df[lat_col] = pd.to_numeric(tx_df[lat_col], errors="coerce")
        tx_df[lon_col] = pd.to_numeric(tx_df[lon_col], errors="coerce")
        tx_df = tx_df.dropna(subset=[lat_col, lon_col])

        # Bounding box filter (server-side not available for ZIP; done here)
        if self.bounding_box:
            min_lon, max_lon, min_lat, max_lat = self.bounding_box
            tx_df = tx_df[
                (tx_df[lon_col] >= min_lon)
                & (tx_df[lon_col] <= max_lon)
                & (tx_df[lat_col] >= min_lat)
                & (tx_df[lat_col] <= max_lat)
            ]
            logger.info("After bbox filter: %d transmitter records", len(tx_df))

        if tx_df.empty:
            return []

        logger.info("Building rows from %d SMS records", len(tx_df))
        return self._rows_from_df(tx_df, lat_col, lon_col, source="ZIP")

    def _rows_from_df(
        self, df: pd.DataFrame, lat_col: str, lon_col: str, source: str = "ZIP"
    ) -> list[dict]:
        """Convert a merged transmitter DataFrame to standardised row dicts."""
        # Resolve column names once
        height_col = self._find_col(df, "ANTENNA_HEIGHT_M", "HEIGHT_M", "ANT_HEIGHT", "HEIGHT")
        az_col = self._find_col(df, "AZIMUTH_OF_MAIN_LOBE", "AZIMUTH", "AZ")
        power_col = self._find_col(df, "TX_POWER_DBW", "POWER_DBW", "POWER")
        power_type_col = self._find_col(df, "POWER_TYPE")
        freq_col = self._find_col(df, "FREQUENCY_MHZ", "FREQ_MHZ", "FREQUENCY")
        company_col = self._find_col(df, "COMPANY_NAME", "LICENSEE", "OPERATOR", "CLIENT_NAME")
        site_id_col = self._find_col(df, "SITE_ID", "SITEID")

        rows = []
        for i, row in df.iterrows():
            lat = self._to_float_val(row.get(lat_col))
            lon = self._to_float_val(row.get(lon_col))
            if lat is None or lon is None:
                continue

            site_id = self._str_val(row.get(site_id_col)) if site_id_col else str(i)
            freq_mhz = self._to_float_val(row.get(freq_col)) if freq_col else None
            height = self._to_float_val(row.get(height_col)) if height_col else None
            azimuth = self._to_float_val(row.get(az_col)) if az_col else None

            # Power: convert dBW to dBm (+30), and ERP to EIRP (+2.15 dB) if needed
            power_dbm = None
            if power_col:
                power_dbw = self._to_float_val(row.get(power_col))
                if power_dbw is not None:
                    power_dbm = power_dbw + 30.0  # dBW -> dBm
                    # ERP (referenced to half-wave dipole) -> EIRP: add 2.15 dB
                    if power_type_col:
                        ptype = str(row.get(power_type_col) or "").strip().upper()
                        if ptype == "ERP":
                            power_dbm += 2.15

            operator_raw = self._str_val(row.get(company_col)) if company_col else None
            operator = _normalize_operator(operator_raw)

            freq_band = _freq_to_band(freq_mhz)
            tech = _guess_technology(freq_mhz)

            rows.append(
                {
                    "SiteCode": f"CA_{site_id}",
                    "AntennaLabel": f"CA_{site_id}_{tech}",
                    "Operator": operator,
                    "Technology": tech,
                    "Latitude": lat,
                    "Longitude": lon,
                    "CenterHeight": height,
                    "Power": power_dbm,
                    "Frequency": freq_mhz,
                    "FrequencyBand": freq_band,
                    "Electrical_Tilt": None,
                    "Mechanical_Tilt": None,
                    "Azimuth": azimuth,
                    "Gain": None,
                    "Horizontal_Beamwidth": None,
                    "Vertical_Beamwidth": None,
                }
            )
        return rows

    # ------------------------------------------------------------------
    # ArcGIS REST API path
    # ------------------------------------------------------------------

    def _extract_arcgis(self) -> list[dict]:
        """Fetch records from the ArcGIS FeatureServer using bbox + pagination."""
        if not self.bounding_box:
            logger.warning(
                "ArcGIS path requires a bounding_box. "
                "Provide bbox or use ZIP path for full-country extraction."
            )
            return []

        min_lon, max_lon, min_lat, max_lat = self.bounding_box
        geometry = (
            f'{{"xmin":{min_lon},"ymin":{min_lat},"xmax":{max_lon},"ymax":{max_lat},'
            f'"spatialReference":{{"wkid":4326}}}}'
        )

        session = requests.Session()
        session.headers.update({"Accept": "application/json"})

        all_features: list[dict] = []
        offset = 0
        while True:
            params = {
                "geometry": geometry,
                "geometryType": "esriGeometryEnvelope",
                "inSR": "4326",
                "outFields": "*",
                "where": "1=1",
                "resultOffset": offset,
                "resultRecordCount": ARCGIS_PAGE_SIZE,
                "f": "geojson",
            }
            try:
                resp = session.get(ARCGIS_URL, params=params, timeout=60)
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:
                logger.error("ArcGIS request failed at offset %d: %s", offset, exc)
                break

            features = data.get("features", [])
            if not features:
                break

            all_features.extend(features)
            logger.info(
                "ArcGIS offset %d: got %d features (total: %d)",
                offset,
                len(features),
                len(all_features),
            )

            if len(features) < ARCGIS_PAGE_SIZE:
                break
            offset += len(features)

        if not all_features:
            logger.warning("No features returned from ArcGIS endpoint")
            return []

        return self._parse_arcgis_features(all_features)

    def _parse_arcgis_features(self, features: list[dict]) -> list[dict]:
        """Convert GeoJSON features to standardised row dicts."""
        rows = []
        for feat in features:
            props = feat.get("properties") or {}
            geom = feat.get("geometry") or {}

            coords = geom.get("coordinates")
            if coords and len(coords) >= 2:
                lon, lat = float(coords[0]), float(coords[1])
            else:
                # Try flat properties for non-point geometries
                lat = self._to_float_val(props.get("LATITUDE") or props.get("LAT"))
                lon = self._to_float_val(props.get("LONGITUDE") or props.get("LON"))
                if lat is None or lon is None:
                    continue

            # Field names may differ between ArcGIS layer versions; try common names
            site_id = (
                self._str_val(props.get("SITE_ID"))
                or self._str_val(props.get("OBJECTID"))
                or "?"
            )
            freq_mhz = self._to_float_val(
                props.get("FREQUENCY_MHZ") or props.get("FREQ_MHZ") or props.get("FREQUENCY")
            )
            height = self._to_float_val(
                props.get("ANTENNA_HEIGHT_M") or props.get("HEIGHT_M") or props.get("HEIGHT")
            )
            azimuth = self._to_float_val(
                props.get("AZIMUTH_OF_MAIN_LOBE") or props.get("AZIMUTH")
            )

            power_dbw = self._to_float_val(
                props.get("TX_POWER_DBW") or props.get("POWER_DBW") or props.get("POWER")
            )
            power_dbm = None
            if power_dbw is not None:
                power_dbm = power_dbw + 30.0
                ptype = str(props.get("POWER_TYPE") or "").strip().upper()
                if ptype == "ERP":
                    power_dbm += 2.15

            operator_raw = (
                self._str_val(props.get("COMPANY_NAME"))
                or self._str_val(props.get("LICENSEE"))
            )
            operator = _normalize_operator(operator_raw)
            freq_band = _freq_to_band(freq_mhz)
            tech = _guess_technology(freq_mhz)

            rows.append(
                {
                    "SiteCode": f"CA_{site_id}",
                    "AntennaLabel": f"CA_{site_id}_{tech}",
                    "Operator": operator,
                    "Technology": tech,
                    "Latitude": lat,
                    "Longitude": lon,
                    "CenterHeight": height,
                    "Power": power_dbm,
                    "Frequency": freq_mhz,
                    "FrequencyBand": freq_band,
                    "Electrical_Tilt": None,
                    "Mechanical_Tilt": None,
                    "Azimuth": azimuth,
                    "Gain": None,
                    "Horizontal_Beamwidth": None,
                    "Vertical_Beamwidth": None,
                }
            )
        return rows

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_col(df: pd.DataFrame, *candidates: str) -> str | None:
        """Return the first matching column name (case-insensitive)."""
        cols_upper = {c.upper(): c for c in df.columns}
        for cand in candidates:
            if cand.upper() in cols_upper:
                return cols_upper[cand.upper()]
        return None

    @staticmethod
    def _to_float_val(val: object) -> float | None:
        if val is None:
            return None
        s = str(val).strip()
        if s in ("", "nan", "None", "N/A", "NA"):
            return None
        try:
            return float(s)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _str_val(val: object) -> str | None:
        if val is None:
            return None
        s = str(val).strip()
        return s if s and s not in ("nan", "None", "N/A") else None


# ------------------------------------------------------------------
# Module-level helpers (shared between ZIP and ArcGIS paths)
# ------------------------------------------------------------------


def _guess_technology(freq_mhz: float | None) -> str:
    """Heuristic technology label from centre frequency."""
    if freq_mhz is None:
        return "4G"
    if freq_mhz >= 3300:
        return "5G"
    if freq_mhz >= 2500:
        return "4G/5G"
    if freq_mhz >= 600:
        return "4G"
    if freq_mhz >= 400:
        return "3G"
    return "4G"


def _freq_to_band(freq_mhz: float | None) -> str | None:
    """Map centre frequency (MHz) to canonical band name."""
    if freq_mhz is None:
        return None
    bands = [
        (600, 630, "Band600MHz"),
        (698, 806, "Band700MHz"),
        (824, 894, "Band850MHz"),
        (880, 960, "Band900MHz"),
        (1710, 1880, "Band1800MHz"),
        (1850, 1990, "Band1900MHz"),
        (1920, 2170, "Band2100MHz"),
        (2300, 2400, "Band2300MHz"),
        (2496, 2690, "Band2600MHz"),
        (3300, 3800, "Band3500MHz"),
        (24250, 27500, "Band26GHz"),
    ]
    for lo, hi, name in bands:
        if lo <= freq_mhz <= hi:
            return name
    return f"Band{int(freq_mhz)}MHz"
