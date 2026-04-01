"""Thin CloudRF API client for antenna patterns and coverage."""

import logging

import numpy as np
import requests

from aegis.basestation.antenna import AntennaPattern
from aegis.basestation.msi import msi_to_antenna_pattern

logger = logging.getLogger(__name__)


class CloudRFClient:
    BASE_URL = "https://api.cloudrf.com"

    def __init__(self, api_key: str):
        self._session = requests.Session()
        self._session.headers["key"] = api_key

    def search_antennas(
        self,
        manufacturer: str = "",
        model: str = "",
        freq_lower: float = 0,
        freq_upper: float = 100000,
        gain_lower: float = -10,
        gain_upper: float = 50,
        page: int = 1,
    ) -> list[dict]:
        """Search CloudRF antenna database. Returns list of antenna dicts."""
        body: dict = {"page": page}
        if manufacturer:
            body["manufacturer"] = manufacturer
        if model:
            body["model"] = model
        if freq_lower > 0:
            body["frequency_lower"] = freq_lower
        if freq_upper < 100000:
            body["frequency_upper"] = freq_upper
        resp = self._session.post(f"{self.BASE_URL}/API/antennas", json=body)
        resp.raise_for_status()
        data = resp.json()
        return data.get("rows", data) if isinstance(data, dict) else data

    def fetch_antenna(self, antenna_id: int) -> dict:
        """Get full antenna detail including pattern_data."""
        resp = self._session.post(f"{self.BASE_URL}/API/antenna/{antenna_id}")
        resp.raise_for_status()
        return resp.json()

    def antenna_to_pattern(self, antenna_data: dict) -> AntennaPattern:
        """Convert CloudRF antenna response to AntennaPattern(181, 360).

        CloudRF pattern_data has 'horizontal' and 'vertical' keys, each
        containing [angles_array, gains_array]. Gains are in dBd relative to peak.
        The antenna's peak gain is in dBd too. Convert to dBi by adding 2.15.
        """
        pd = antenna_data["pattern_data"]
        h_gains = np.array(pd["horizontal"][1], dtype=np.float64)  # relative dBd
        v_gains = np.array(pd["vertical"][1], dtype=np.float64)

        # These are gains relative to peak (0 = peak, negative = below peak).
        # Convert to attenuation (0 = peak, positive = below peak) for msi_to_antenna_pattern.
        h_atten = -h_gains
        v_atten = -v_gains

        # Peak gain: CloudRF may provide gain_dbd or gain_dbi.
        if "gain_dbd" in antenna_data and antenna_data["gain_dbd"] is not None:
            gain_dbi = float(antenna_data["gain_dbd"]) + 2.15
        elif "gain_dbi" in antenna_data and antenna_data["gain_dbi"] is not None:
            gain_dbi = float(antenna_data["gain_dbi"])
        else:
            gain_dbi = float(antenna_data.get("gain") or 0) + 2.15

        return msi_to_antenna_pattern(h_atten, v_atten, gain_dbi)

    def list_manufacturers(self) -> list[dict]:
        """List all antenna manufacturers in the CloudRF database."""
        resp = self._session.post(f"{self.BASE_URL}/API/antenna/manufacturers")
        resp.raise_for_status()
        return resp.json()

    def area(
        self,
        lat: float,
        lon: float,
        alt: float,
        freq_mhz: float,
        power_w: float,
        gain_dbi: float,
        azimuth: float = 0,
        tilt: float = 0,
        hbw: float = 65,
        vbw: float = 10,
        radius_km: float = 2,
        res_m: int = 10,
        propagation_model: int = 1,
    ) -> bytes:
        """Compute coverage heatmap. Returns GeoTIFF bytes."""
        body = {
            "engine": 2,
            "coordinates": 1,
            "transmitter": {
                "lat": lat,
                "lon": lon,
                "alt": alt,
                "frq": freq_mhz,
                "txw": power_w,
                "bwi": 10,
            },
            "receiver": {"lat": 0, "lon": 0, "alt": 1, "rxg": 1, "rxs": -100},
            "antenna": {
                "txg": gain_dbi,
                "txl": 0,
                "ant": 0,
                "azi": azimuth,
                "tlt": tilt,
                "hbw": hbw,
                "vbw": vbw,
                "fbr": 12,
                "pol": "v",
            },
            "model": {"pm": propagation_model, "pe": 2, "ked": 1, "rel": 50},
            "environment": {"elevation": 1, "landcover": 1, "buildings": 1, "obstacles": 0},
            "output": {
                "units": "m",
                "col": "RAINBOW.dBm",
                "out": 2,
                "nf": -104,
                "res": res_m,
                "rad": radius_km,
            },
        }
        resp = self._session.post(f"{self.BASE_URL}/area", json=body)
        resp.raise_for_status()
        data = resp.json()
        tiff_url = data.get("tiff_4326") or data.get("tiff")
        if not tiff_url:
            raise ValueError(f"No TIFF URL in CloudRF response: {list(data.keys())}")
        tiff_resp = self._session.get(tiff_url)
        tiff_resp.raise_for_status()
        return tiff_resp.content

    def path(
        self,
        tx_lat: float,
        tx_lon: float,
        tx_alt: float,
        rx_lat: float,
        rx_lon: float,
        rx_alt: float,
        freq_mhz: float,
        power_w: float,
        gain_dbi: float,
    ) -> dict:
        """Point-to-point link budget."""
        body = {
            "engine": 2,
            "coordinates": 1,
            "transmitter": {
                "lat": tx_lat,
                "lon": tx_lon,
                "alt": tx_alt,
                "frq": freq_mhz,
                "txw": power_w,
                "bwi": 10,
            },
            "receiver": {"lat": rx_lat, "lon": rx_lon, "alt": rx_alt, "rxg": 1, "rxs": -100},
            "antenna": {
                "txg": gain_dbi,
                "txl": 0,
                "ant": 1,
                "azi": 0,
                "tlt": 0,
                "hbw": 360,
                "vbw": 90,
                "fbr": 0,
                "pol": "v",
            },
            "model": {"pm": 1, "pe": 2, "ked": 1, "rel": 50},
            "environment": {"elevation": 1, "landcover": 1, "buildings": 0, "obstacles": 0},
            "output": {
                "units": "m",
                "col": "RAINBOW.dBm",
                "out": 2,
                "nf": -104,
                "res": 30,
                "rad": 5,
            },
        }
        resp = self._session.post(f"{self.BASE_URL}/path", json=body)
        resp.raise_for_status()
        return resp.json()
