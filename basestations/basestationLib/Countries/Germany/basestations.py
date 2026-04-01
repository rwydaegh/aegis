"""Germany adapter: BNetzA EMF database (bundesnetzagentur.de)."""

from __future__ import annotations

import base64
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# BNetzA EMF portal endpoints
EMF_BASE = "https://www.bundesnetzagentur.de"
EMF_INIT_URL = f"{EMF_BASE}/DE/Vportal/TK/Funktechnik/EMF/start.html"
EMF_JS_URL = f"{EMF_BASE}/emf-karte/js.asmx/jscontent?set=gsb2021"
EMF_POSITIONS_URL = f"{EMF_BASE}/emf-karte/Standortservice.asmx/GetStandorteFreigabe"
EMF_DETAIL_URL = f"{EMF_BASE}/emf-karte/hf.aspx"

CRYPTO_PW_RE = re.compile(r'var c=CryptoJS\.enc\.Utf8\.parse\("(.*?)"\);')

INIT_HEADERS = {
    "Accept": "*/*",
    "Host": "www.bundesnetzagentur.de",
    "Origin": EMF_BASE,
    "Accept-Language": "de;q=0.8",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36"
    ),
    "Referer": EMF_INIT_URL,
}

API_HEADERS = {
    "Origin": EMF_BASE,
    "Accept-Language": "de;q=0.8",
    "dataType": "json",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36"
    ),
    "Content-type": "application/json; charset=UTF-8 application/json",
    "Accept": "application/json",
    "Referer": EMF_INIT_URL,
}

# Tile size for bbox splitting (degrees)
TILE_SIZE = 0.1


def _unpad(s: bytes) -> bytes:
    return s[0 : -s[-1]]


def _decrypt(password: str, data: str) -> list | dict:
    """AES-CBC decrypt BNetzA response using PBKDF2-derived key."""
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    backend = default_backend()
    iv = bytes.fromhex("a5a8d2e9c1721ae0e84ad660c472b1f3")
    pw = password.encode("utf-8")
    salt = b"cryptography123example"
    kdf = PBKDF2HMAC(algorithm=hashes.SHA1(), length=16, salt=salt, iterations=1000, backend=backend)
    key = kdf.derive(pw)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=backend)
    data_bytes = base64.b64decode(data)
    decryptor = cipher.decryptor()
    decrypted = decryptor.update(data_bytes) + decryptor.finalize()
    return json.loads(_unpad(decrypted).decode("utf-8"))


def _to_float(s: str | None) -> float | None:
    if s is None:
        return None
    s = str(s).strip().replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


class BaseStations:
    """Extract antenna data from the German BNetzA EMF database."""

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
        """Extract antenna data from BNetzA EMF database.

        Fields available: location, height, operator, azimuth.
        Fields missing: power, technology, frequency, tilt, gain, beamwidth.
        """
        try:
            session, password = self._init_session()
        except Exception as exc:
            logger.error("Failed to initialize BNetzA session: %s", exc)
            return pd.DataFrame()

        if self.bounding_box is None:
            logger.warning("No bounding_box provided; returning empty DataFrame")
            return pd.DataFrame()

        tiles = list(self._tile_bbox(self.bounding_box))
        logger.info("Fetching %d tiles from BNetzA EMF database", len(tiles))

        # Collect positions from all tiles
        positions = []
        for tile in tiles:
            tile_positions = self._fetch_positions(session, password, tile)
            positions.extend(tile_positions)

        # Deduplicate by fID
        seen = set()
        unique_positions = []
        for pos in positions:
            fid = pos.get("fID")
            if fid not in seen:
                seen.add(fid)
                unique_positions.append(pos)

        logger.info("Fetching details for %d unique sites", len(unique_positions))

        # Fetch details concurrently (max 2 workers to be polite)
        rows = []
        with ThreadPoolExecutor(max_workers=min(self.max_workers, 2)) as executor:
            future_to_pos = {
                executor.submit(self._fetch_site_detail, session, pos): pos
                for pos in unique_positions
            }
            for future in as_completed(future_to_pos):
                pos = future_to_pos[future]
                try:
                    site_rows = future.result()
                    rows.extend(site_rows)
                except Exception as exc:
                    logger.warning("Failed to fetch detail for fID %s: %s", pos.get("fID"), exc)

        if not rows:
            logger.warning("No antenna data returned from BNetzA")
            return pd.DataFrame()

        df = pd.DataFrame(rows)

        if self.operator:
            df = df[df["Operator"].str.contains(self.operator, case=False, na=False)]
        if self.technology:
            df = df[df["Technology"].str.contains(self.technology, case=False, na=False)]

        from basestationLib.utils.create_output_df import create_output_df

        return create_output_df(df, config or {}, {})

    def _init_session(self) -> tuple[requests.Session, str]:
        """Initialize a BNetzA session and extract the crypto password."""
        session = requests.Session()
        session.get(EMF_INIT_URL, headers=INIT_HEADERS, timeout=30)
        r = session.get(EMF_JS_URL, headers=INIT_HEADERS, timeout=30)
        r.raise_for_status()
        match = CRYPTO_PW_RE.search(r.text)
        if not match:
            raise RuntimeError("Could not extract crypto password from BNetzA JS")
        password = match.group(1)
        return session, password

    def _fetch_positions(
        self, session: requests.Session, password: str, tile: tuple[float, float, float, float]
    ) -> list[dict]:
        """Fetch site positions for a single tile bbox."""
        west, south, east, north = tile
        data = {"Box": {"nord": north, "ost": east, "sued": south, "west": west}}
        try:
            resp = session.post(
                EMF_POSITIONS_URL,
                headers=API_HEADERS,
                data=json.dumps(data),
                timeout=30,
            )
            resp.raise_for_status()
            if "text/html" in resp.headers.get("Content-Type", ""):
                logger.debug("Tile %s returned HTML (likely empty/error)", tile)
                return []
            result = resp.json().get("d", [])
            if isinstance(result, dict) and result.get("SecMode"):
                result = _decrypt(password, result["Result"])
            if not isinstance(result, list):
                return []
            logger.debug("Tile %s: %d positions", tile, len(result))
            return result
        except Exception as exc:
            logger.warning("Failed to fetch tile %s: %s", tile, exc)
            return []

    def _fetch_site_detail(self, session: requests.Session, pos: dict) -> list[dict]:
        """Fetch HTML detail page for a site and parse antenna rows."""
        from lxml import html as lxml_html

        fid = pos.get("fID")
        lat = pos.get("Lat")
        lon = pos.get("Lng")
        site_code = pos.get("Titel", str(fid))

        r = session.get(EMF_DETAIL_URL, params={"fid": fid}, headers=API_HEADERS, timeout=30)
        r.raise_for_status()
        root = lxml_html.fromstring(r.text)

        # Extract operators from logo img alt tags
        provider_imgs = root.findall('.//div[@id="div_mobilfunkanbieter"]/img')
        providers = [img.get("alt", "") for img in provider_imgs if img.get("alt")]
        operator_str = ", ".join(providers) if providers else None

        # Extract standortbescheinigung number (site code from BNetzA)
        bnr_divs = root.findall('.//div[@id="standortbnr"]')
        if bnr_divs:
            spans = bnr_divs[0].findall("span")
            if len(spans) >= 2:
                site_code = spans[1].text_content().strip() or site_code

        # Extract antenna rows from the sendeantennen table
        rows = []
        tables = root.findall('.//div[@id="div_sendeantennen"]/table')
        if tables:
            for row in tables[0].findall("tr")[1:]:
                cells = row.findall("td")
                if len(cells) < 3:
                    continue
                atype = cells[0].text_content().strip()
                height = _to_float(cells[1].text_content())
                direction_text = cells[2].text_content().strip()
                direction = None if direction_text == "ND" else _to_float(direction_text)

                rows.append(
                    {
                        "SiteCode": f"DE_{site_code}",
                        "AntennaLabel": f"DE_{site_code}_{atype}_{direction}",
                        "Operator": operator_str,
                        "Technology": None,
                        "Latitude": float(lat) if lat is not None else None,
                        "Longitude": float(lon) if lon is not None else None,
                        "CenterHeight": height,
                        "Power": None,
                        "Frequency": None,
                        "FrequencyBand": None,
                        "Electrical_Tilt": None,
                        "Mechanical_Tilt": None,
                        "Azimuth": direction,
                        "Gain": None,
                        "Horizontal_Beamwidth": None,
                        "Vertical_Beamwidth": None,
                    }
                )

        # If no antenna table, emit a single row for the site
        if not rows:
            rows.append(
                {
                    "SiteCode": f"DE_{site_code}",
                    "AntennaLabel": f"DE_{site_code}",
                    "Operator": operator_str,
                    "Technology": None,
                    "Latitude": float(lat) if lat is not None else None,
                    "Longitude": float(lon) if lon is not None else None,
                    "CenterHeight": None,
                    "Power": None,
                    "Frequency": None,
                    "FrequencyBand": None,
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
    def _tile_bbox(bbox: list[float]) -> list[tuple[float, float, float, float]]:
        """Split bbox into 0.1 x 0.1 degree tiles.

        bbox format: [min_lon, max_lon, min_lat, max_lat]
        Returns tiles as (west, south, east, north).
        """
        min_lon, max_lon, min_lat, max_lat = bbox
        tiles = []
        lat = min_lat
        while lat < max_lat:
            north = min(lat + TILE_SIZE, max_lat)
            lon = min_lon
            while lon < max_lon:
                east = min(lon + TILE_SIZE, max_lon)
                tiles.append((lon, lat, east, north))
                lon = round(lon + TILE_SIZE, 6)
            lat = round(lat + TILE_SIZE, 6)
        return tiles
