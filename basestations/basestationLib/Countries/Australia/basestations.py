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
        resp = requests.get(DOWNLOAD_URL, timeout=120, stream=True)
        resp.raise_for_status()
        data = resp.content

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
        """Join RRL tables and return standardised rows."""
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            names = {n.lower(): n for n in zf.namelist()}

            def read_csv(key: str) -> pd.DataFrame:
                match = next((v for k, v in names.items() if key in k), None)
                if match is None:
                    logger.warning("File containing '%s' not found in ZIP", key)
                    return pd.DataFrame()
                with zf.open(match) as f:
                    return pd.read_csv(f, sep="|", dtype=str, low_memory=False)

            site_df = read_csv("site")
            antenna_df = read_csv("antenna")
            device_df = read_csv("device_details")
            licence_df = read_csv("licence")

        if any(df.empty for df in [site_df, antenna_df, device_df, licence_df]):
            logger.warning("One or more required RRL tables are missing or empty")
            return []

        # Normalise column names to lowercase/stripped
        for df in [site_df, antenna_df, device_df, licence_df]:
            df.columns = [c.strip().lower() for c in df.columns]

        # Filter to active licences
        if "status" in licence_df.columns:
            licence_df = licence_df[licence_df["status"].str.upper().str.strip() == "ACTIVE"]

        # Join: device_details -> licence (to get licensee / type)
        licence_key = self._find_col(licence_df, "licence_no", "licenceno", "licence_number")
        device_lic_key = self._find_col(device_df, "licence_no", "licenceno", "licence_number")
        if licence_key and device_lic_key:
            device_df = device_df.merge(
                licence_df[[licence_key, "licensee", "licence_type_name"]],
                left_on=device_lic_key,
                right_on=licence_key,
                how="left",
            )

        # Filter to mobile cellular licences
        if "licence_type_name" in device_df.columns:
            mask = (
                device_df["licence_type_name"]
                .fillna("")
                .str.upper()
                .apply(lambda t: any(kw in t for kw in MOBILE_LICENCE_TYPES))
            )
            device_df = device_df[mask]
            if device_df.empty:
                logger.warning(
                    "No mobile carrier licences found after filtering; relaxing filter to all active licences"
                )
                # fall through with unfiltered device_df for bbox filter at least

        # Join: device_details -> antenna
        ant_key = self._find_col(antenna_df, "antenna_id")
        dev_ant_key = self._find_col(device_df, "antenna_id")
        if ant_key and dev_ant_key:
            merged = device_df.merge(
                antenna_df,
                left_on=dev_ant_key,
                right_on=ant_key,
                how="left",
                suffixes=("_dev", "_ant"),
            )
        else:
            merged = device_df

        # Join: -> site
        site_key = self._find_col(site_df, "site_id")
        merged_site_key = self._find_col(merged, "site_id")
        if site_key and merged_site_key:
            merged = merged.merge(
                site_df,
                left_on=merged_site_key,
                right_on=site_key,
                how="left",
                suffixes=("", "_site"),
            )

        # Resolve lat/lon columns
        lat_col = self._find_col(merged, "latitude", "lat")
        lon_col = self._find_col(merged, "longitude", "lon", "lng")
        if lat_col is None or lon_col is None:
            logger.warning("Latitude/longitude columns not found in merged RRL data")
            return []

        merged[lat_col] = pd.to_numeric(merged[lat_col], errors="coerce")
        merged[lon_col] = pd.to_numeric(merged[lon_col], errors="coerce")
        merged = merged.dropna(subset=[lat_col, lon_col])

        # Bounding box filter
        if self.bounding_box:
            min_lon, max_lon, min_lat, max_lat = self.bounding_box
            merged = merged[
                (merged[lon_col] >= min_lon)
                & (merged[lon_col] <= max_lon)
                & (merged[lat_col] >= min_lat)
                & (merged[lat_col] <= max_lat)
            ]

        if merged.empty:
            return []

        rows = []
        for _, row in merged.iterrows():
            freq_mhz = self._to_float(row, "frequency", "freq")
            eirp_dbw = self._to_float(row, "eirp", "tx_eirp", "power")
            power_dbm = (eirp_dbw + 30.0) if eirp_dbw is not None else None

            height = self._to_float(row, "height", "antenna_height", "height_amsl")
            azimuth = self._to_float(row, "azimuth", "azi")
            elec_tilt = self._to_float(row, "electrical_tilt", "elec_tilt", "etilt")
            mech_tilt = self._to_float(row, "mechanical_tilt", "mech_tilt", "mtilt")
            gain = self._to_float(row, "gain", "antenna_gain")

            site_id = self._str(row, "site_id")
            antenna_id = self._str(row, "antenna_id")
            operator = self._str(row, "licensee")
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
                    "Electrical_Tilt": elec_tilt,
                    "Mechanical_Tilt": mech_tilt,
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
