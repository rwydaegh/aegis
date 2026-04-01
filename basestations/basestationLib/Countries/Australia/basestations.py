"""Australia adapter: ACMA Register of Radiocommunications Licences (RRL).

Data source: https://web.acma.gov.au/rrl-updates/spectra_rrl.zip
Updated daily by ACMA. Cache TTL: 7 days.

The ZIP contains pipe-delimited CSV files. We join:
- site.csv          -- lat/lon, site_id, site_name
- antenna.csv       -- antenna_id, site_id, height, azimuth, polarisation, tilt,
                       gain, h_beamwidth, v_beamwidth
- device_details.csv -- antenna_id, licence_no, eirp (dBW), frequency (MHz)
- licence.csv       -- licence_no, licensee, licence_type_name, status

Only active mobile cellular licences are retained.
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

DOWNLOAD_URL = "https://web.acma.gov.au/rrl-updates/spectra_rrl.zip"
CACHE_PATH = Path.home() / ".cache" / "aegis" / "acma_rrl.zip"
CACHE_TTL_DAYS = 7

# Licence type substrings that indicate mobile cellular base stations.
MOBILE_LICENCE_TYPES = (
    "MOBILE CARRIER",
    "MOBILE PHONE",
    "APPARATUS LICENCE",
    "PUBLIC MOBILE",
)


class BaseStations:
    """Extract antenna data from the Australian ACMA RRL dataset."""

    def __init__(
        self,
        output_folder: str = "output/australia/",
        bounding_box: list[float] | None = None,
        operator: str | None = None,
        technology: str | None = None,
        **kwargs,
    ):
        self.output_folder = output_folder
        # bbox: [min_lon, max_lon, min_lat, max_lat]
        self.bounding_box = bounding_box
        self.operator = operator
        self.technology = technology

    def extract_antennas(self, config: dict | None = None) -> pd.DataFrame:
        """Extract antenna data from the ACMA RRL dataset.

        Fields available: location, frequency, EIRP, azimuth, tilt, gain, height.
        Fields missing: beamwidth (Horizontal_Beamwidth, Vertical_Beamwidth).
        """
        try:
            zip_bytes = self._get_zip()
        except Exception as exc:
            logger.error("Failed to download ACMA RRL data: %s", exc)
            return pd.DataFrame()

        try:
            rows = self._parse_zip(zip_bytes)
        except Exception as exc:
            logger.error("Failed to parse ACMA RRL ZIP: %s", exc)
            return pd.DataFrame()

        if not rows:
            logger.warning("No rows extracted from ACMA RRL data")
            return pd.DataFrame()

        df = pd.DataFrame(rows)

        if self.operator:
            df = df[df["Operator"].str.contains(self.operator, case=False, na=False)]
        if self.technology:
            df = df[df["Technology"].str.contains(self.technology, case=False, na=False)]

        from basestationLib.utils.create_output_df import create_output_df

        return create_output_df(df, config or {}, {})

    # ------------------------------------------------------------------
    # Download / cache
    # ------------------------------------------------------------------

    def _get_zip(self) -> bytes:
        """Return ZIP bytes, using disk cache if fresh enough."""
        if self._cache_is_fresh():
            logger.info("Using cached ACMA RRL data from %s", CACHE_PATH)
            return CACHE_PATH.read_bytes()

        logger.info("Downloading ACMA RRL data from %s", DOWNLOAD_URL)
        resp = requests.get(DOWNLOAD_URL, timeout=300, stream=True)
        resp.raise_for_status()
        chunks = []
        for chunk in resp.iter_content(chunk_size=1024 * 1024):
            if chunk:
                chunks.append(chunk)
        data = b"".join(chunks)

        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_bytes(data)
        logger.info("Cached ACMA RRL data to %s (%d bytes)", CACHE_PATH, len(data))
        return data

    @staticmethod
    def _cache_is_fresh() -> bool:
        if not CACHE_PATH.exists():
            return False
        age = datetime.now(tz=UTC) - datetime.fromtimestamp(CACHE_PATH.stat().st_mtime, tz=UTC)
        return age < timedelta(days=CACHE_TTL_DAYS)

    # ------------------------------------------------------------------
    # Parse
    # ------------------------------------------------------------------

    def _parse_zip(self, zip_bytes: bytes) -> list[dict]:
        """Join RRL tables and return standardised rows.

        The ACMA RRL ZIP uses comma-delimited CSV files with UPPERCASE column names.
        Key tables: site.csv, device_details.csv, licence.csv, client.csv.
        Note: antenna.csv contains only antenna specs (gain, beamwidth) - height,
        azimuth, tilt, and frequency are in device_details.csv.
        """
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            names = {n.lower(): n for n in zf.namelist()}

            def read_csv(key: str) -> pd.DataFrame:
                match = next((v for k, v in names.items() if key in k and k.endswith(".csv")), None)
                if match is None:
                    logger.warning("File containing '%s' not found in ZIP", key)
                    return pd.DataFrame()
                with zf.open(match) as f:
                    return pd.read_csv(f, sep=",", dtype=str, low_memory=False)

            site_df = read_csv("site.csv")
            device_df = read_csv("device_details")
            licence_df = read_csv("licence.csv")
            client_df = read_csv("client.csv")

        if any(df.empty for df in [site_df, device_df, licence_df]):
            logger.warning("One or more required RRL tables are missing or empty")
            return []

        # Normalise column names to lowercase
        for df in [site_df, device_df, licence_df, client_df]:
            df.columns = [c.strip().lower() for c in df.columns]

        # Filter licence to active status (STATUS=1 means active in ACMA data)
        if "status" in licence_df.columns:
            active = licence_df[licence_df["status"].isin(["1", "ACTIVE"])]
            if not active.empty:
                licence_df = active

        # Filter to "Land Mobile" licence type (mobile base stations in Australia)
        if "licence_type_name" in licence_df.columns:
            mobile_pattern = "LAND MOBILE|MOBILE CARRIER|PUBLIC MOBILE"
            mobile = licence_df[
                licence_df["licence_type_name"].str.upper().str.contains(mobile_pattern, na=False)
            ]
            if not mobile.empty:
                licence_df = mobile
            else:
                logger.warning("No mobile licences found; using all active licences")

        # Join client info (licensee name) onto licence
        if not client_df.empty and "client_no" in licence_df.columns and "client_no" in client_df.columns:
            licensee_col = "licencee" if "licencee" in client_df.columns else "client_name"
            if licensee_col in client_df.columns:
                licence_df = licence_df.merge(
                    client_df[["client_no", licensee_col]],
                    on="client_no",
                    how="left",
                )
        else:
            licence_df["licencee"] = None

        # Join device_details -> licence
        if "licence_no" in device_df.columns and "licence_no" in licence_df.columns:
            keep_cols = ["licence_no", "licence_type_name"]
            if "licencee" in licence_df.columns:
                keep_cols.append("licencee")
            device_df = device_df.merge(
                licence_df[keep_cols].drop_duplicates("licence_no"),
                on="licence_no",
                how="inner",
            )

        if device_df.empty:
            logger.warning("No device records after joining with licence table")
            return []

        # Join device_details -> site (for lat/lon)
        if "site_id" in device_df.columns and "site_id" in site_df.columns:
            device_df = device_df.merge(
                site_df[["site_id", "latitude", "longitude"]],
                on="site_id",
                how="left",
            )

        # Resolve lat/lon
        lat_col = self._find_col(device_df, "latitude", "lat")
        lon_col = self._find_col(device_df, "longitude", "lon", "lng")
        if lat_col is None or lon_col is None:
            logger.warning("Latitude/longitude columns not found in merged RRL data")
            return []

        device_df[lat_col] = pd.to_numeric(device_df[lat_col], errors="coerce")
        device_df[lon_col] = pd.to_numeric(device_df[lon_col], errors="coerce")
        device_df = device_df.dropna(subset=[lat_col, lon_col])

        # Bounding box filter
        if self.bounding_box:
            min_lon, max_lon, min_lat, max_lat = self.bounding_box
            device_df = device_df[
                (device_df[lon_col] >= min_lon)
                & (device_df[lon_col] <= max_lon)
                & (device_df[lat_col] >= min_lat)
                & (device_df[lat_col] <= max_lat)
            ]

        if device_df.empty:
            logger.warning("No records in bounding box %s", self.bounding_box)
            return []

        logger.info("Parsing %d device records in bbox", len(device_df))

        rows = []
        for _, row in device_df.iterrows():
            freq_mhz = self._to_float(row, "frequency", "freq", "carrier_freq")
            # EIRP is stored in dBW in ACMA data; convert to dBm
            eirp_str = row.get("eirp") or row.get("transmitter_power")
            eirp_dbw = None
            if eirp_str and str(eirp_str).strip() not in ("", "nan", "None"):
                try:
                    eirp_dbw = float(eirp_str)
                    # Check unit: if EIRP_UNIT is 'W', convert watts to dBW first
                    unit = str(row.get("eirp_unit", "") or "").strip().upper()
                    if unit == "W":
                        import math
                        eirp_dbw = 10 * math.log10(max(eirp_dbw, 1e-9))
                    elif unit == "DBM":
                        eirp_dbw = eirp_dbw - 30.0  # convert to dBW for consistency
                except (ValueError, TypeError):
                    pass
            power_dbm = (eirp_dbw + 30.0) if eirp_dbw is not None else None

            height = self._to_float(row, "height")
            azimuth = self._to_float(row, "azimuth")
            tilt = self._to_float(row, "tilt")
            gain = self._to_float(row, "gain")

            site_id = self._str(row, "site_id")
            antenna_id = self._str(row, "antenna_id")
            operator = self._str(row, "licencee")
            tech = self._guess_technology(freq_mhz)
            freq_band = self._freq_to_band(freq_mhz)

            rows.append(
                {
                    "SiteCode": f"AU_{site_id}",
                    "AntennaLabel": f"AU_{antenna_id}_{tech}",
                    "Operator": operator,
                    "Technology": tech,
                    "Latitude": float(row[lat_col]),
                    "Longitude": float(row[lon_col]),
                    "CenterHeight": height,
                    "Power": power_dbm,
                    "Frequency": freq_mhz,
                    "FrequencyBand": freq_band,
                    "Electrical_Tilt": tilt,
                    "Mechanical_Tilt": None,
                    "Azimuth": azimuth,
                    "Gain": gain,
                    "Horizontal_Beamwidth": None,
                    "Vertical_Beamwidth": None,
                }
            )
        return rows

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_col(df: pd.DataFrame, *candidates: str) -> str | None:
        """Return the first matching column name (case-insensitive)."""
        cols_lower = {c.lower(): c for c in df.columns}
        for cand in candidates:
            if cand.lower() in cols_lower:
                return cols_lower[cand.lower()]
        return None

    @staticmethod
    def _to_float(row: pd.Series, *keys: str) -> float | None:
        for key in keys:
            val = row.get(key)
            if val is not None and str(val).strip() not in ("", "nan", "None"):
                try:
                    return float(val)
                except (ValueError, TypeError):
                    pass
        return None

    @staticmethod
    def _str(row: pd.Series, *keys: str) -> str | None:
        for key in keys:
            val = row.get(key)
            if val is not None and str(val).strip() not in ("", "nan", "None"):
                return str(val).strip()
        return None

    @staticmethod
    def _guess_technology(freq_mhz: float | None) -> str:
        """Heuristic technology label from centre frequency."""
        if freq_mhz is None:
            return "4G"
        if freq_mhz >= 24000:
            return "5G"
        if freq_mhz >= 3300:
            return "5G"
        if freq_mhz >= 2500:
            return "4G/5G"
        if freq_mhz >= 1700:
            return "4G"
        if freq_mhz >= 700:
            return "4G"
        return "4G"

    @staticmethod
    def _freq_to_band(freq_mhz: float | None) -> str | None:
        """Map centre frequency (MHz) to canonical band name."""
        if freq_mhz is None:
            return None
        bands = [
            (600, 620, "Band600MHz"),
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
