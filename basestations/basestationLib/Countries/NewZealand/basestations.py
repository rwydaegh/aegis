"""New Zealand adapter: RSM RRF (Radio Spectrum Management - Radiocommunications Register of Frequencies)."""

from __future__ import annotations

import logging
import math
import os

import pandas as pd
import requests

logger = logging.getLogger(__name__)

API_BASE = "https://api.business.govt.nz/services/v1/rsm/search/licences"
PAGE_SIZE = 100

# Cellular frequency bands of interest (MHz centre frequencies)
_MOBILE_FREQ_BANDS = {
    "700": 746.0,
    "850": 850.0,
    "900": 942.5,
    "1800": 1842.5,
    "2100": 2140.0,
    "2600": 2630.0,
    "3500": 3550.0,
}

# Main NZ mobile operators
_NZ_OPERATORS = {"spark", "one nz", "vodafone nz", "2degrees", "2degrees mobile"}


def _haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in metres between two WGS84 points."""
    r = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _bbox_to_circles(
    min_lon: float, max_lon: float, min_lat: float, max_lat: float, tile_radius_m: float = 20_000.0
) -> list[tuple[float, float, float]]:
    """Tile a bounding box into overlapping circles of the given radius.

    Returns a list of (lat, lon, radius_m) tuples that fully cover the bbox.
    Overlap factor is sqrt(2) to guarantee no gaps at tile corners.
    """
    # Degrees per metre (approximate, using centre latitude)
    centre_lat = (min_lat + max_lat) / 2
    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * math.cos(math.radians(centre_lat))

    # Step size: tile_radius / sqrt(2) ensures full coverage with overlap
    step_lat = tile_radius_m / math.sqrt(2) / m_per_deg_lat
    step_lon = tile_radius_m / math.sqrt(2) / m_per_deg_lon

    circles = []
    lat = min_lat + step_lat / 2
    while lat <= max_lat + step_lat / 2:
        lon = min_lon + step_lon / 2
        while lon <= max_lon + step_lon / 2:
            circles.append((min(lat, max_lat), min(lon, max_lon), tile_radius_m))
            lon += step_lon
        lat += step_lat

    return circles


def _fetch_page(
    lat: float,
    lon: float,
    radius_m: float,
    page: int,
    api_key: str,
    session: requests.Session,
) -> dict:
    """Fetch a single page of licence records from the RSM RRF API."""
    resp = session.get(
        API_BASE,
        params={
            "lat": lat,
            "lon": lon,
            "radius": int(radius_m),
            "licenceType": "MOBILE",
            "status": "CURRENT",
            "page": page,
            "pageSize": PAGE_SIZE,
        },
        headers={"apikey": api_key},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _derive_frequency_band(freq_mhz: float | None) -> str:
    """Map a centre frequency (MHz) to the nearest named band."""
    if freq_mhz is None:
        return ""
    thresholds = [
        (400, ""),
        (750, "700"),
        (875, "850"),
        (1000, "900"),
        (2000, "1800"),
        (2400, "2100"),
        (3000, "2600"),
        (4000, "3500"),
    ]
    for upper, band in thresholds:
        if freq_mhz < upper:
            return band
    return "3500"


def _map_technology(freq_mhz: float | None) -> str:
    """Infer likely technology from frequency (best-effort heuristic)."""
    if freq_mhz is None:
        return ""
    if freq_mhz >= 3000:
        return "5G"
    if freq_mhz >= 2500:
        return "4G"
    if freq_mhz >= 1700:
        return "4G"
    if freq_mhz >= 800:
        return "4G"
    if freq_mhz >= 400:
        return "3G"
    return ""


class BaseStations:
    """Extract antenna data from the NZ RSM Radiocommunications Register of Frequencies."""

    def __init__(
        self,
        bounding_box: list[float] | None = None,
        output_folder: str = "output/newzealand/",
        operator: str | None = None,
        technology: str | None = None,
        api_key: str | None = None,
        tile_radius_m: float = 20_000.0,
        **kwargs,
    ):
        self.bounding_box = bounding_box
        self.output_folder = output_folder
        self.operator = operator
        self.technology = technology
        self.api_key = api_key or os.environ.get("NZ_RSM_API_KEY") or os.environ.get("RSM_API_KEY", "")
        self.tile_radius_m = tile_radius_m

    def extract_antennas(self, config: dict | None = None) -> pd.DataFrame:
        """Extract antenna data from the RSM RRF API.

        Fields available: location, height, azimuth, power (EIRP dBW),
        frequency, gain, electrical tilt.
        Fields missing: Horizontal_Beamwidth, Vertical_Beamwidth, Mechanical_Tilt.
        """
        if not self.api_key:
            logger.error(
                "No RSM API key provided. Set NZ_RSM_API_KEY env var or pass api_key= to constructor."
            )
            return pd.DataFrame()

        try:
            records = self._fetch_all_records()
        except Exception as exc:
            logger.error("Failed to fetch from RSM RRF API: %s", exc)
            return pd.DataFrame()

        if not records:
            logger.warning("No records returned from RSM RRF API")
            return pd.DataFrame()

        rows = self._parse_records(records)
        df = pd.DataFrame(rows)

        if df.empty:
            return df

        # Apply optional filters
        if self.operator:
            df = df[df["Operator"].str.contains(self.operator, case=False, na=False)]
        if self.technology:
            df = df[df["Technology"].str.contains(self.technology, case=False, na=False)]

        from basestationLib.utils.create_output_df import create_output_df

        return create_output_df(df, config or {}, {})

    def _fetch_all_records(self) -> list[dict]:
        """Tile the bbox into circles, fetch all pages, and deduplicate by licence number."""
        if self.bounding_box:
            min_lon, max_lon, min_lat, max_lat = self.bounding_box
        else:
            # Full New Zealand bounding box
            min_lon, max_lon, min_lat, max_lat = 166.0, 178.5, -47.5, -34.0

        circles = _bbox_to_circles(min_lon, max_lon, min_lat, max_lat, self.tile_radius_m)
        logger.info(
            "Tiled bbox into %d circles (radius=%.0f m)", len(circles), self.tile_radius_m
        )

        session = requests.Session()
        seen_ids: set[str] = set()
        all_records: list[dict] = []

        for idx, (lat, lon, radius_m) in enumerate(circles, 1):
            logger.info("Fetching circle %d/%d at (%.4f, %.4f)", idx, len(circles), lat, lon)
            page = 1
            while True:
                data = _fetch_page(lat, lon, radius_m, page, self.api_key, session)
                items = data.get("results") or data.get("data") or []
                if not items:
                    break

                new_count = 0
                for item in items:
                    licence_id = str(item.get("licenceId") or item.get("id") or "")
                    if licence_id and licence_id not in seen_ids:
                        seen_ids.add(licence_id)
                        all_records.append(item)
                        new_count += 1

                total = data.get("totalResults") or data.get("total") or 0
                logger.info(
                    "  Page %d: %d items (%d new), total=%s", page, len(items), new_count, total
                )

                # Stop if we have fetched all results for this circle
                if len(items) < PAGE_SIZE:
                    break
                if total and page * PAGE_SIZE >= int(total):
                    break
                page += 1

        logger.info("Total deduplicated records: %d", len(all_records))
        return all_records

    def _parse_records(self, records: list[dict]) -> list[dict]:
        """Convert raw RSM RRF licence records to standardized rows."""
        rows = []
        for rec in records:
            # Field names vary slightly across API versions; try both camelCase and snake_case
            licence_id = str(rec.get("licenceId") or rec.get("licence_id") or rec.get("id") or "")
            lat = self._coerce_float(rec.get("latitude") or rec.get("lat"))
            lon = self._coerce_float(rec.get("longitude") or rec.get("lon"))

            if lat is None or lon is None:
                continue

            height = self._coerce_float(
                rec.get("antennaHeight")
                or rec.get("antenna_height")
                or rec.get("height")
            )
            azimuth = self._coerce_float(
                rec.get("azimuth") or rec.get("bearingDegrees") or rec.get("bearing")
            )
            # Power: EIRP in dBW per licence record
            power = self._coerce_float(
                rec.get("eirp")
                or rec.get("eirpDbw")
                or rec.get("power")
                or rec.get("maxEirp")
            )
            freq_mhz = self._coerce_float(
                rec.get("frequency") or rec.get("frequencyMhz") or rec.get("freq")
            )
            gain = self._coerce_float(
                rec.get("antennaGain") or rec.get("antenna_gain") or rec.get("gain")
            )
            elec_tilt = self._coerce_float(
                rec.get("electricalTilt")
                or rec.get("electrical_tilt")
                or rec.get("tilt")
                or rec.get("antennaTilt")
            )
            operator = str(rec.get("licencee") or rec.get("operator") or rec.get("clientName") or "")
            callsign = str(rec.get("callsign") or rec.get("callSign") or "")

            freq_band = _derive_frequency_band(freq_mhz)
            technology = _map_technology(freq_mhz)

            label = f"NZ_{licence_id}"
            if callsign:
                label = f"NZ_{callsign}"

            rows.append(
                {
                    "SiteCode": f"NZ_{licence_id}",
                    "AntennaLabel": label,
                    "Operator": operator,
                    "Technology": technology,
                    "Latitude": lat,
                    "Longitude": lon,
                    "CenterHeight": height,
                    "Power": power,
                    "Frequency": freq_mhz,
                    "FrequencyBand": freq_band,
                    "Electrical_Tilt": elec_tilt,
                    "Mechanical_Tilt": None,
                    "Azimuth": azimuth,
                    "Gain": gain,
                    "Horizontal_Beamwidth": None,
                    "Vertical_Beamwidth": None,
                }
            )
        return rows

    @staticmethod
    def _coerce_float(value) -> float | None:
        """Return float or None for missing/non-numeric values."""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
