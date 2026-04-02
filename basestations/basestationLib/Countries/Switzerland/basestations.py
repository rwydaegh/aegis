"""Switzerland adapter: BAKOM mobile antenna register via api3.geo.admin.ch."""

from __future__ import annotations

import logging
import math
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ...utils import create_unique_file_identifier, create_output_df, format_date_only

logger = logging.getLogger(__name__)

current_folder = os.path.dirname(os.path.abspath(__file__))

# Swisstopo identify endpoint for mobile antenna layer
_API_URL = "https://api3.geo.admin.ch/rest/services/all/MapServer/identify"
_LAYER = "all:ch.bakom.standorte-mobilfunkanlagen"

# Tile step in degrees (~2 km) to stay under 200-result cap per tile
_TILE_DEG = 0.02

# Power class -> Watts, then converted to dBm
_POWER_CLASS_W = {
    "very low": 6.0,       # up to 6 W  -> 37.8 dBm
    "low": 500.0,          # up to 500 W -> 57 dBm
    "medium": 5000.0,      # up to 5000 W -> 67 dBm
    "high": 5000.0,        # over 5000 W -> use 5000 W as estimate -> 67 dBm
}

# Known Swiss MNO names (first word of station field)
_KNOWN_OPERATORS = {"Swisscom", "Sunrise", "Salt", "SBB"}

# Technology priority for picking highest when multiple are listed
_TECH_PRIORITY = {"5G": 3, "4G": 2, "3G": 1, "2G": 0}


def _create_session(timeout: int = 15, retries: int = 3) -> requests.Session:
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


def _tile_bbox(bbox: list[float]) -> list[tuple[float, float, float, float]]:
    """Split a [min_lon, max_lon, min_lat, max_lat] bbox into 0.02-degree tiles."""
    min_lon, max_lon, min_lat, max_lat = bbox
    tiles = []
    lat = min_lat
    while lat < max_lat:
        lon = min_lon
        lat_end = min(lat + _TILE_DEG, max_lat)
        while lon < max_lon:
            lon_end = min(lon + _TILE_DEG, max_lon)
            tiles.append((lon, lat, lon_end, lat_end))
            lon = lon_end
        lat = lat_end
    return tiles


def _fetch_tile(session: requests.Session, tile: tuple[float, float, float, float]) -> list[dict]:
    """Fetch results for a single tile from the identify endpoint."""
    min_lon, min_lat, max_lon, max_lat = tile
    geometry = f"{min_lon},{min_lat},{max_lon},{max_lat}"
    params = {
        "geometry": geometry,
        "geometryType": "esriGeometryEnvelope",
        "mapExtent": geometry,
        "imageDisplay": "1000,1000,96",
        "tolerance": "0",
        "layers": _LAYER,
        "returnGeometry": "true",
        "sr": "4326",
        "limit": "200",
    }
    resp = session.get(_API_URL, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json().get("results", [])


def _parse_power(power_en: str) -> float:
    """Convert power_en string to dBm. Returns NaN if unrecognized."""
    if not power_en:
        return np.nan
    low = power_en.lower()
    for key, watts in _POWER_CLASS_W.items():
        if key in low:
            return round(10 * math.log10(watts) + 30, 1)
    return np.nan


def _parse_operator(station: str) -> str:
    """Extract operator from the first word of the station field."""
    if not station:
        return "Unknown"
    first = station.split()[0] if station.split() else ""
    return first if first in _KNOWN_OPERATORS else first or "Unknown"


def _parse_technology(techno_en: str) -> str:
    """Pick the highest-generation technology listed in techno_en."""
    if not techno_en:
        return ""
    # e.g. "Technology 3G,4G,5G" or "Technology 4G"
    text = techno_en.upper()
    best = ""
    best_priority = -1
    for tech, priority in _TECH_PRIORITY.items():
        if tech in text and priority > best_priority:
            best = tech
            best_priority = priority
    return best or techno_en


def _result_to_row(result: dict) -> dict | None:
    """Convert a single API result feature to a standardized row dict."""
    attrs = result.get("attributes", {})
    geom = result.get("geometry", {})

    points = geom.get("points")
    if points:
        lon, lat = points[0][0], points[0][1]
    else:
        lon = geom.get("x")
        lat = geom.get("y")

    if lon is None or lat is None:
        return None

    station = attrs.get("station", "")
    operator = _parse_operator(station)
    technology = _parse_technology(attrs.get("techno_en", ""))
    power_dbm = _parse_power(attrs.get("power_en", ""))

    # Derive site code and antenna label from station string
    parts = station.split()
    site_code = parts[1] if len(parts) > 1 else station
    antenna_label = f"ANT({' '.join(parts[2:]) if len(parts) > 2 else site_code})"

    return {
        "SiteCode": f"SITE({site_code})",
        "AntennaLabel": antenna_label,
        "Operator": operator,
        "Technology": technology,
        "Latitude": float(lat),
        "Longitude": float(lon),
        "CenterHeight": None,
        "Power": power_dbm,
        "Frequency": None,
        "FrequencyBand": None,
        "Electrical_Tilt": None,
        "Mechanical_Tilt": None,
        "Azimuth": None,
        "Gain": None,
        "Horizontal_Beamwidth": None,
        "Vertical_Beamwidth": None,
    }


class BaseStations:
    """Extract Swiss mobile antenna data from the BAKOM register via api3.geo.admin.ch."""

    def __init__(
        self,
        operator: str | None = None,
        technology: str | None = None,
        bounding_box: list[float] | None = None,
        frequency_range: list[float] = [0, np.inf],
        frequency_band: str | None = None,
        date: datetime = datetime.now(timezone.utc),
        raw_antenna_cache_file: str = os.path.join(current_folder, "all.pkl"),
        pattern_file: str | None = None,
        output_folder: str = "output/switzerland/",
        max_workers: int = 1,
        file_identifier: str | None = None,
    ):
        os.makedirs(output_folder, exist_ok=True)
        self.operator = operator
        self.technology = technology
        self.bounding_box = bounding_box
        self.frequency_range = frequency_range
        self.frequency_band = frequency_band
        self.date = format_date_only(date)
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

    def _default_bbox(self) -> list[float]:
        """Return a bounding box covering Switzerland when none is provided."""
        # [min_lon, max_lon, min_lat, max_lat]
        return [5.96, 10.49, 45.82, 47.81]

    def _fetch_all_results(self) -> list[dict]:
        """Tile the bbox and fetch all results, deduplicating by featureId."""
        bbox = self.bounding_box if self.bounding_box else self._default_bbox()
        tiles = _tile_bbox(bbox)
        logger.info("Querying %d tiles over bbox %s", len(tiles), bbox)

        session = _create_session()
        seen_ids: set[str | int] = set()
        all_results: list[dict] = []

        for i, tile in enumerate(tiles):
            try:
                results = _fetch_tile(session, tile)
            except Exception as exc:
                logger.warning("Tile %d/%d failed: %s", i + 1, len(tiles), exc)
                continue

            for r in results:
                fid = r.get("featureId")
                if fid is None or fid not in seen_ids:
                    if fid is not None:
                        seen_ids.add(fid)
                    all_results.append(r)

            if (i + 1) % 50 == 0 or (i + 1) == len(tiles):
                logger.info(
                    "Progress: %d/%d tiles, %d unique features",
                    i + 1, len(tiles), len(all_results),
                )

        session.close()
        return all_results

    def extract_antennas(self, config: dict | None = None) -> pd.DataFrame:
        """Extract antennas from BAKOM via api3.geo.admin.ch, apply filters, and save CSV."""
        save_cache = (
            self.operator is None
            and self.technology is None
            and self.bounding_box is None
            and self.frequency_band is None
            and (
                self.frequency_range == [0, np.inf]
                or np.array_equal(self.frequency_range, [0, np.inf])
            )
        )

        # Try loading cached raw data
        if self.raw_antenna_cache_file and os.path.exists(self.raw_antenna_cache_file):
            try:
                self.antennas = pd.read_pickle(self.raw_antenna_cache_file)
                logger.info("Loaded cached antenna data from %s", self.raw_antenna_cache_file)
                self.count = len(self.antennas)
            except Exception as exc:
                logger.warning("Failed to load cache %s: %s", self.raw_antenna_cache_file, exc)
                self.antennas = pd.DataFrame()

        if self.antennas is None or self.antennas.empty:
            print(f"Fetching Swiss antenna data from {_API_URL} ...")
            results = self._fetch_all_results()

            rows = []
            for r in results:
                row = _result_to_row(r)
                if row is not None:
                    rows.append(row)

            if not rows:
                logger.warning("No antenna records returned")
                return pd.DataFrame()

            self.antennas = pd.DataFrame(rows)
            self.count = len(self.antennas)
            print(f"Fetched {self.count} antenna records from BAKOM.")

        # Optionally save the raw cache
        if save_cache and self.raw_antenna_cache_file:
            try:
                os.makedirs(os.path.dirname(self.raw_antenna_cache_file), exist_ok=True)
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
                df_out.to_csv(out_csv, index=False)
                print(f"Saved output CSV to {out_csv}")
            except Exception as exc:
                logger.warning("Failed to save output CSV: %s", exc)

        return df_out

    def extract_patterns(self, *args, **kwargs):
        """Switzerland extractor does not support antenna pattern reconstruction.

        This method is provided for API compatibility and will return None.
        """
        print("Pattern extraction is not supported for Switzerland (no pattern data available).")
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    BS = BaseStations()
    BS.extract_antennas()
