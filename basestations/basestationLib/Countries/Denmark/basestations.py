"""Denmark adapter: Mastedatabasen (mastedatabasen.dk)."""

from __future__ import annotations

import logging

import pandas as pd
import requests

logger = logging.getLogger(__name__)

API_BASE = "https://dk-api.mastdatabase.co.uk"
PAGE_SIZE = 5000


class BaseStations:
    """Extract antenna data from the Danish Mastedatabasen."""

    def __init__(
        self,
        output_folder: str = "output/denmark/",
        bounding_box: list[float] | None = None,
        operator: str | None = None,
        technology: str | None = None,
        max_workers: int = 4,
        **kwargs,
    ):
        self.output_folder = output_folder
        self.bounding_box = bounding_box
        self.operator = operator
        self.technology = technology
        self.max_workers = max_workers

    def extract_antennas(self, config: dict | None = None) -> pd.DataFrame:
        """Extract antenna data from Mastedatabasen API.

        Fields available: location, operator, technology, frequency band.
        Fields missing: power, height, azimuth, tilt, gain, beamwidth.
        """
        try:
            sites = self._fetch_sites()
        except Exception as exc:
            logger.error("Failed to fetch from Mastedatabasen: %s", exc)
            logger.info("The dk-api.mastdatabase.co.uk API may be temporarily unavailable")
            return pd.DataFrame()

        if not sites:
            logger.warning("No sites returned from Mastedatabasen")
            return pd.DataFrame()

        rows = self._parse_sites(sites)
        df = pd.DataFrame(rows)

        # Apply filters
        if self.operator:
            df = df[df["Operator"].str.contains(self.operator, case=False, na=False)]
        if self.technology:
            df = df[df["Technology"].str.contains(self.technology, case=False, na=False)]

        from basestationLib.utils.create_output_df import create_output_df

        return create_output_df(df, config or {}, {})

    def _fetch_sites(self) -> list[dict]:
        """Fetch all sites from the API, paginated."""
        all_sites = []
        page = 1
        session = requests.Session()
        session.headers.update({"Accept": "application/vnd.api+json"})

        while True:
            params: dict = {"page[number]": page, "page[size]": PAGE_SIZE}
            if self.bounding_box:
                # bbox: [min_lon, max_lon, min_lat, max_lat]
                # API expects: lat1,lon1,lat2,lon2 (SW corner, NE corner)
                min_lon, max_lon, min_lat, max_lat = self.bounding_box
                params["filter[bounds]"] = f"{min_lat},{min_lon},{max_lat},{max_lon}"

            resp = session.get(f"{API_BASE}/sites", params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            sites = data.get("data", [])
            if not sites:
                break

            all_sites.extend(sites)
            logger.info("Fetched page %d: %d sites (total: %d)", page, len(sites), len(all_sites))

            # Check if there are more pages
            links = data.get("links", {})
            if not links.get("next"):
                break
            page += 1

        return all_sites

    def _parse_sites(self, sites: list[dict]) -> list[dict]:
        """Convert API response to standardized rows."""
        rows = []
        for site in sites:
            attrs = site.get("attributes", {})
            lat = attrs.get("latitude") or attrs.get("lat")
            lon = attrs.get("longitude") or attrs.get("lon") or attrs.get("lng")
            if lat is None or lon is None:
                continue

            operator = attrs.get("operator", attrs.get("owner", ""))
            technology = self._map_technology(attrs.get("technology", attrs.get("service_type", "")))
            freq_band = attrs.get("frequency_band", attrs.get("frequencyBand", ""))

            rows.append(
                {
                    "SiteCode": f"DK_{site.get('id', '')}",
                    "AntennaLabel": f"DK_{site.get('id', '')}_{technology}",
                    "Operator": operator,
                    "Technology": technology,
                    "Latitude": float(lat),
                    "Longitude": float(lon),
                    "CenterHeight": None,  # not available
                    "Power": None,  # not available
                    "Frequency": self._band_to_freq(freq_band),
                    "FrequencyBand": freq_band,
                    "Electrical_Tilt": None,
                    "Mechanical_Tilt": None,
                    "Azimuth": None,
                    "Gain": None,
                    "Horizontal_Beamwidth": None,
                    "Vertical_Beamwidth": None,
                }
            )
        return rows

    @staticmethod
    def _map_technology(tech: str) -> str:
        """Normalize technology strings to standard format."""
        tech_upper = str(tech).upper()
        if "NR" in tech_upper or "5G" in tech_upper:
            return "5G"
        if "LTE" in tech_upper or "4G" in tech_upper:
            return "4G"
        if "UMTS" in tech_upper or "3G" in tech_upper:
            return "3G"
        if "GSM" in tech_upper or "2G" in tech_upper:
            return "2G"
        return tech

    @staticmethod
    def _band_to_freq(band: str) -> float | None:
        """Rough center frequency from band name."""
        band_map = {
            "700": 740.0,
            "800": 830.0,
            "900": 942.5,
            "1800": 1842.5,
            "2100": 2140.0,
            "2600": 2630.0,
            "3500": 3500.0,
            "3600": 3600.0,
        }
        for key, freq in band_map.items():
            if key in str(band):
                return freq
        return None
