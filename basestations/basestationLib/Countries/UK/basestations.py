"""UK adapter: Ofcom Wireless Telegraphy Register (WTR) fixed-link data.

The WTR CSV is published daily by Ofcom under the Open Government Licence v3.
It contains all wireless telegraphy licences including Fixed Links used as
microwave backhaul by mobile operators. These are co-located at cell sites,
making them a useful proxy for site locations.

Source: https://static.ofcom.org.uk/static/radiolicensing/html/register/WTR.csv
"""

from __future__ import annotations

import logging
import math
import os
from datetime import UTC, datetime

import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ...utils import create_output_df, create_unique_file_identifier

logger = logging.getLogger(__name__)

current_folder = os.path.dirname(os.path.abspath(__file__))

_WTR_URL = "https://static.ofcom.org.uk/static/radiolicensing/html/register/WTR.csv"

# Mobile operators that hold Fixed Link licences for backhaul
_MOBILE_OPERATOR_KEYWORDS = [
    "Telefonica",
    "Vodafone",
    "MOBILE BROADBAND NETWORK",
    "Airwave",
    "Cornerstone",
    "CTIL",
]

# Map raw Licencee Company names to short operator labels
_OPERATOR_MAP = {
    "Telefonica UK Limited": "O2",
    "Vodafone Limited": "Vodafone",
    "MOBILE BROADBAND NETWORK LIMITED": "EE/Three",
    "Airwave Solutions Limited": "Airwave",
    "Cornerstone Telecommunications Infrastructure Limited": "CTIL",
    "CTIL": "CTIL",
}


def _create_session(retries: int = 3) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=retries,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        backoff_factor=1,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def _map_operator(licencee: str) -> str:
    """Map a Licencee Company string to a short operator name."""
    if not licencee:
        return "Unknown"
    # Try exact match first
    if licencee in _OPERATOR_MAP:
        return _OPERATOR_MAP[licencee]
    # Try substring match
    licencee_upper = licencee.upper()
    for key, label in _OPERATOR_MAP.items():
        if key.upper() in licencee_upper:
            return label
    return licencee


def _is_mobile_operator(licencee: str) -> bool:
    """Check if a Licencee Company string belongs to a mobile operator."""
    if not licencee:
        return False
    licencee_upper = licencee.upper()
    return any(kw.upper() in licencee_upper for kw in _MOBILE_OPERATOR_KEYWORDS)


def _derive_frequency_band(freq_mhz: float) -> str:
    """Derive a frequency band label from frequency in MHz.

    Groups into standard microwave bands (e.g. Band10000MHz for 10 GHz).
    """
    if np.isnan(freq_mhz):
        return ""
    # Round to nearest GHz for standard microwave bands
    freq_ghz = freq_mhz / 1000.0
    if freq_ghz < 1:
        band_mhz = int(round(freq_mhz / 100) * 100)
        return f"Band{band_mhz}MHz"
    band_ghz = int(round(freq_ghz))
    return f"Band{band_ghz * 1000}MHz"


def _convert_erp_to_dbm(erp_value: float, erp_unit: str, erp_type: str) -> float:
    """Convert Antenna ERP to dBm.

    The WTR can report ERP in dBW or W. Convert everything to dBm.
    dBm = dBW + 30
    dBm = 10*log10(W) + 30

    The WTR CSV uses '-' as a placeholder for missing values.
    """
    if pd.isna(erp_value):
        return np.nan
    try:
        erp_float = float(erp_value)
    except (ValueError, TypeError):
        return np.nan
    unit = str(erp_unit).strip().upper() if pd.notna(erp_unit) else ""
    if unit == "DBW":
        return erp_float + 30.0
    if unit == "W":
        if erp_float <= 0:
            return np.nan
        return round(10 * math.log10(erp_float) + 30, 1)
    # Default: assume dBW if unit is missing or unrecognized
    return erp_float + 30.0


def _download_wtr(session: requests.Session) -> pd.DataFrame:
    """Download and parse the Ofcom WTR CSV."""
    logger.info("Downloading WTR CSV from %s ...", _WTR_URL)
    print(f"Downloading WTR CSV from {_WTR_URL} ...")

    resp = session.get(_WTR_URL, timeout=120)
    resp.raise_for_status()

    # The CSV uses ISO-8859-1 encoding (Latin-1)
    from io import StringIO

    text = resp.content.decode("latin-1")
    df = pd.read_csv(StringIO(text), low_memory=False)
    logger.info("Downloaded %d rows from WTR", len(df))
    print(f"Downloaded {len(df)} rows from WTR.")
    return df


def _filter_mobile_fixed_links(df: pd.DataFrame) -> pd.DataFrame:
    """Filter WTR to Fixed Links from mobile operators only."""
    # Filter by Product Description
    if "Product Description" not in df.columns:
        logger.warning("Column 'Product Description' not found in WTR data")
        return pd.DataFrame()

    mask_product = df["Product Description"].str.strip().str.lower() == "fixed links"

    # Filter by mobile operator
    if "Licencee Company" not in df.columns:
        logger.warning("Column 'Licencee Company' not found in WTR data")
        return pd.DataFrame()

    mask_operator = df["Licencee Company"].apply(lambda x: _is_mobile_operator(x) if pd.notna(x) else False)

    filtered = df[mask_product & mask_operator].copy()
    logger.info(
        "Filtered to %d Fixed Link rows from mobile operators (from %d total)",
        len(filtered),
        len(df),
    )
    return filtered


def _to_float(value) -> float:
    """Convert a value to float, returning NaN for missing/placeholder values.

    The Ofcom WTR CSV uses '-' as a placeholder for missing numeric fields.
    """
    if pd.isna(value):
        return np.nan
    try:
        return float(value)
    except (ValueError, TypeError):
        return np.nan


def _wtr_to_antenna_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Convert filtered WTR rows to the standard 16-column antenna DataFrame."""
    rows = []
    for _, row in df.iterrows():
        # SiteCode: use first part of Licence Number split by '/'
        licence_num = str(row.get("Licence Number", ""))
        site_id = licence_num.split("/")[0] if "/" in licence_num else licence_num

        # Frequency in MHz
        freq_hz = _to_float(row.get("Frequency (Hz)"))
        freq_mhz = freq_hz / 1e6 if not np.isnan(freq_hz) else np.nan

        # ERP to dBm
        erp_value = row.get("Antenna ERP")
        erp_unit = row.get("Antenna ERP Unit", "")
        erp_type = row.get("Antenna ERP Type", "")
        power_dbm = _convert_erp_to_dbm(erp_value, erp_unit, erp_type)

        # Elevation / tilt
        electrical_tilt = _to_float(row.get("Antenna Elevation"))

        rows.append(
            {
                "SiteCode": f"SITE({site_id})",
                "AntennaLabel": f"ANT({licence_num})",
                "Operator": _map_operator(row.get("Licencee Company", "")),
                "Technology": "FH",
                "Latitude": _to_float(row.get("Latitude(Deg)")),
                "Longitude": _to_float(row.get("Longitude(Deg)")),
                "CenterHeight": _to_float(row.get("Antenna Height")),
                "Power": power_dbm,
                "Frequency": freq_mhz,
                "FrequencyBand": _derive_frequency_band(freq_mhz) if not np.isnan(freq_mhz) else "",
                "Electrical_Tilt": electrical_tilt,
                "Mechanical_Tilt": np.nan,
                "Azimuth": _to_float(row.get("Antenna AZIMUTH")),
                "Gain": _to_float(row.get("Antenna Gain")),
                "Horizontal_Beamwidth": np.nan,
                "Vertical_Beamwidth": np.nan,
            }
        )

    return pd.DataFrame(rows)


def _deduplicate_sites(df: pd.DataFrame) -> pd.DataFrame:
    """Deduplicate by site location, rounding lat/lon to 5 decimal places.

    Keeps one representative row per unique (rounded_lat, rounded_lon) pair.
    For each site, keeps the row with the most complete data (fewest NaNs).
    """
    if df.empty:
        return df

    df = df.copy()
    df["_lat_round"] = df["Latitude"].round(5)
    df["_lon_round"] = df["Longitude"].round(5)

    # Count non-null values per row to pick the most complete record
    data_cols = [c for c in df.columns if not c.startswith("_")]
    df["_completeness"] = df[data_cols].notna().sum(axis=1)

    # Sort by completeness descending, then drop duplicates keeping first
    df = df.sort_values("_completeness", ascending=False)
    df = df.drop_duplicates(subset=["_lat_round", "_lon_round"], keep="first")

    # Clean up helper columns
    df = df.drop(columns=["_lat_round", "_lon_round", "_completeness"])
    return df.reset_index(drop=True)


class BaseStations:
    """Extract UK base station site data from the Ofcom WTR (Fixed Links)."""

    def __init__(
        self,
        operator: str | None = None,
        technology: str | None = None,
        bounding_box: list[float] | None = None,
        frequency_range: list[float] | None = None,
        frequency_band: str | None = None,
        date: datetime | None = None,
        raw_antenna_cache_file: str = os.path.join(current_folder, "all.pkl"),
        pattern_file: str | None = None,
        output_folder: str = "output/uk/",
        max_workers: int = 1,
        file_identifier: str | None = None,
    ):
        os.makedirs(output_folder, exist_ok=True)
        if frequency_range is None:
            frequency_range = [0, np.inf]
        if date is None:
            date = datetime.now(UTC)

        self.operator = operator
        self.technology = technology
        self.bounding_box = bounding_box
        self.frequency_range = frequency_range
        self.frequency_band = frequency_band
        self.date = date
        self.raw_antenna_cache_file = raw_antenna_cache_file
        self.pattern_file = pattern_file
        self.output_folder = output_folder
        self.max_workers = max_workers
        self.antennas = pd.DataFrame()
        self.count = 0

        if file_identifier is None:
            self.file_identifier = create_unique_file_identifier(self)
        else:
            self.file_identifier = file_identifier

    def extract_antennas(self, config: dict | None = None) -> pd.DataFrame:
        """Extract antenna sites from Ofcom WTR, apply filters, and save CSV."""
        save_cache = (
            self.operator is None
            and self.technology is None
            and self.bounding_box is None
            and self.frequency_band is None
            and (self.frequency_range == [0, np.inf] or np.array_equal(self.frequency_range, [0, np.inf]))
        )

        # Try loading cached raw data
        if self.raw_antenna_cache_file and os.path.exists(self.raw_antenna_cache_file):
            try:
                self.antennas = pd.read_pickle(self.raw_antenna_cache_file)
                logger.info("Loaded cached antenna data from %s", self.raw_antenna_cache_file)
                self.count = len(self.antennas)
                print(f"Loaded cached antenna data from {self.raw_antenna_cache_file}")
            except Exception as exc:
                logger.warning("Failed to load cache %s: %s", self.raw_antenna_cache_file, exc)
                self.antennas = pd.DataFrame()

        if self.antennas is None or self.antennas.empty:
            session = _create_session()
            try:
                raw_df = _download_wtr(session)
            finally:
                session.close()

            filtered = _filter_mobile_fixed_links(raw_df)
            if filtered.empty:
                logger.warning("No mobile Fixed Link records found in WTR")
                return pd.DataFrame()

            antenna_df = _wtr_to_antenna_rows(filtered)
            self.antennas = _deduplicate_sites(antenna_df)
            self.count = len(self.antennas)
            print(f"Extracted {self.count} unique sites from Ofcom WTR.")

        # Save raw cache if unfiltered
        if save_cache and self.raw_antenna_cache_file:
            try:
                os.makedirs(os.path.dirname(self.raw_antenna_cache_file) or ".", exist_ok=True)
                pd.to_pickle(self.antennas, self.raw_antenna_cache_file)
                logger.info("Saved raw antenna cache to %s", self.raw_antenna_cache_file)
            except Exception as exc:
                logger.warning("Failed to save cache: %s", exc)

        # Apply filters and produce standardized output
        filter_args = {
            "operator": self.operator,
            "technology": self.technology,
            "bounding_box": self.bounding_box,
            "frequency_range": self.frequency_range,
            "frequency_band": self.frequency_band,
            "date": self.date,
        }
        df_out = create_output_df(self.antennas.copy(), config, filter_args=filter_args)

        # Save CSV
        if self.output_folder:
            out_csv = os.path.join(self.output_folder, f"{self.file_identifier}_antennas.csv")
            try:
                os.makedirs(os.path.dirname(out_csv), exist_ok=True)
                df_out.to_csv(out_csv, index=False)
                print(f"Saved output CSV to {out_csv}")
            except Exception as exc:
                logger.warning("Failed to save output CSV: %s", exc)

        return df_out

    def extract_patterns(self, *args, **kwargs):
        """Pattern extraction is not supported for UK WTR data.

        The WTR does not include antenna radiation pattern information.
        """
        print("Pattern extraction is not supported for UK (no pattern data in WTR).")
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bs = BaseStations()
    df = bs.extract_antennas()
    if not df.empty:
        print(f"\nOperators: {df['Operator'].value_counts().to_dict()}")
        print(f"Total unique sites: {len(df)}")
