"""Denmark adapter: Mastedatabasen (mastedatabasen.dk)."""

from __future__ import annotations

import logging

import pandas as pd
import requests

logger = logging.getLogger(__name__)

API_BASE = "https://dk-api.mastdatabase.co.uk"
PAGE_SIZE = 5000

# Lookup tables (pre-fetched from /operators and /technologies)
_OPERATORS: dict[str, str] = {}
_TECHNOLOGIES: dict[str, str] = {}


def _fetch_lookups(session: requests.Session) -> None:
    """Pre-fetch operator and technology name maps."""
    global _OPERATORS, _TECHNOLOGIES
    if _OPERATORS and _TECHNOLOGIES:
        return
    for endpoint, target in [("/operators", "_OPERATORS"), ("/technologies", "_TECHNOLOGIES")]:
        resp = session.get(f"{API_BASE}{endpoint}", timeout=30)
        resp.raise_for_status()
        mapping = {}
        for item in resp.json().get("data", []):
            name_key = "operatorName" if "operator" in endpoint else "technologyName"
            mapping[item["id"]] = item.get("attributes", {}).get(name_key, "")
        if target == "_OPERATORS":
            _OPERATORS = mapping
        else:
            _TECHNOLOGIES = mapping
    logger.info("Loaded %d operators, %d technologies", len(_OPERATORS), len(_TECHNOLOGIES))


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
        """Fetch all sites from the API using offset pagination."""
        all_sites = []
        session = requests.Session()
        session.headers.update({"Accept": "application/vnd.api+json"})

        _fetch_lookups(session)

        offset = 0
        while True:
            params: dict = {"page[offset]": offset, "page[limit]": PAGE_SIZE}
            resp = session.get(f"{API_BASE}/sites", params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            sites = data.get("data", [])
            if not sites:
                break

            all_sites.extend(sites)
            offset += len(sites)
            logger.info("Fetched offset %d: %d sites (total: %d)", offset, len(sites), len(all_sites))

            # Check if there are more pages
            links = data.get("links", {})
            if not links.get("next"):
                break

        # Apply bbox filter client-side (API does not filter server-side)
        if self.bounding_box:
            min_lon, max_lon, min_lat, max_lat = self.bounding_box
            filtered = []
            for site in all_sites:
                attrs = site.get("attributes", {})
                lat = attrs.get("lat")
                lon = attrs.get("lon")
                if lat is not None and lon is not None:
                    if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
                        filtered.append(site)
            logger.info("Bbox filter: %d -> %d sites", len(all_sites), len(filtered))
            all_sites = filtered

        return all_sites

    def _parse_sites(self, sites: list[dict]) -> list[dict]:
        """Convert API response to standardized rows."""
        rows = []
        for site in sites:
            attrs = site.get("attributes", {})
            lat = attrs.get("lat")
            lon = attrs.get("lon")
            if lat is None or lon is None:
                continue

            # Resolve operator and technology from relationships
            rels = site.get("relationships", {})
            op_data = (rels.get("Operator") or {}).get("data") or {}
            tech_data = (rels.get("Technology") or {}).get("data") or {}
            operator = _OPERATORS.get(op_data.get("id", ""), "")
            raw_tech = _TECHNOLOGIES.get(tech_data.get("id", ""), "")
            technology = self._map_technology(raw_tech)

            freq_data = (rels.get("FrequencyBand") or {}).get("data")
            freq_band = ""
            if freq_data and isinstance(freq_data, dict):
                freq_band = freq_data.get("id", "")

            rows.append(
                {
                    "SiteCode": f"DK_{site.get('id', '')}",
                    "AntennaLabel": f"DK_{site.get('id', '')}_{technology}",
                    "Operator": operator,
                    "Technology": technology,
                    "Latitude": float(lat),
                    "Longitude": float(lon),
                    "CenterHeight": None,
                    "Power": None,
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
        if "NR" == tech_upper or "5G" in tech_upper:
            return "5G"
        if "LTE" in tech_upper or "4G" in tech_upper:
            return "4G"
        if "UMTS" in tech_upper or "3G" in tech_upper:
            return "3G"
        if "GSM-R" in tech_upper:
            return "GSM-R"
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
