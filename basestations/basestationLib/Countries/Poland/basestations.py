import contextlib
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime

import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from tqdm import tqdm
from urllib3.util.retry import Retry

from ...utils import create_output_df, create_unique_file_identifier

current_folder = os.path.dirname(os.path.abspath(__file__))


def create_session(retries=3, pool_maxsize=64):
    session = requests.Session()
    retry_strategy = Retry(
        total=retries,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        backoff_factor=1,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=pool_maxsize,
        pool_maxsize=pool_maxsize,
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.verify = False  # BTSearch SSL cert missing intermediate CA
    return session


def fetch_bbox_objects(session, bbox, timeout=10):
    """Fetch location IDs and coords from one bbox tile.

    bbox = [min_lon, max_lon, min_lat, max_lat]
    API expects bounds = min_lat,min_lon,max_lat,max_lon
    """
    api_url = f"https://beta.btsearch.pl/map/locations/?bounds={bbox[2]},{bbox[0]},{bbox[3]},{bbox[1]}"
    try:
        r = session.get(api_url, timeout=timeout)
        if r.status_code != 200:
            return []
        data = r.json()
    except Exception:
        return []
    out = []
    for d in data.get("objects", []):
        loc_id = d.get("id")
        if loc_id is not None:
            out.append((int(loc_id), float(d.get("latitude", 0)), float(d.get("longitude", 0))))
    return out


def parse_location_info(info_html, lat, lon, location_id):
    """Parse operator + technology entries from location JSON info HTML.

    Returns list of dicts, one per (operator, technology, frequency) combo.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(info_html, "html.parser")
    items = soup.select(".location-item")
    rows = []

    for item in items:
        strong = item.find("strong")
        operator = strong.get_text(strip=True) if strong else "Unknown"

        abbr = item.find("abbr", attrs={"title": re.compile(r"Identyfikator", re.I)})
        internal_id = abbr.get_text(strip=True) if abbr else str(location_id)

        # Technologies are listed in a <small> tag that also contains a detail link
        tech_text = ""
        for s in item.find_all("small"):
            if s.find("a"):
                text = s.get_text(" ", strip=True)
                text = re.sub(r"Szczeg.*", "", text).strip()
                tech_text = text
                break

        # Parse e.g. "GSM900", "LTE1800", "5G3500", "UMTS2100"
        tech_entries = re.findall(r"([A-Z0-9]+?)(\d+)", tech_text)
        for tech_name, freq_str in tech_entries:
            frequency = int(freq_str)
            # Normalize 3500 -> 3600 (n78 band)
            freq_band = f"Band{frequency}MHz"
            if frequency == 3500:
                freq_band = "Band3600MHz"

            site_code = f"SITE({internal_id})"
            rows.append(
                {
                    "SiteCode": site_code,
                    "AntennaLabel": f"ANT({internal_id}_{tech_name}_{frequency})",
                    "Operator": operator,
                    "Technology": tech_name,
                    "Latitude": lat,
                    "Longitude": lon,
                    "CenterHeight": np.nan,
                    "Power": np.nan,
                    "Frequency": float(frequency),
                    "FrequencyBand": freq_band,
                    "Electrical_Tilt": np.nan,
                    "Mechanical_Tilt": np.nan,
                    "Azimuth": np.nan,
                    "Gain": np.nan,
                    "Horizontal_Beamwidth": np.nan,
                    "Vertical_Beamwidth": np.nan,
                }
            )

    return rows


def fetch_and_parse_location(session, location_id, lat, lon, timeout=10):
    """Fetch location JSON and parse antennas from it."""
    url = f"https://beta.btsearch.pl/map/locations/{location_id}/?"
    try:
        r = session.get(url, timeout=timeout)
        if r.status_code != 200:
            return []
        data = r.json()
    except Exception:
        return []
    info_html = data.get("info", "")
    if not info_html:
        return []
    return parse_location_info(info_html, lat, lon, location_id)


def extract_all_antennas(bboxes, session=None, max_workers_bbox=16, max_workers_locations=32, timeout=10):
    """Two-stage extraction: bbox tiles -> location JSONs -> parsed antennas."""
    own_session = session is None
    if own_session:
        session = create_session(pool_maxsize=max(max_workers_bbox, max_workers_locations) + 8)

    # Stage 1: collect unique location IDs from all bbox tiles
    location_map = {}  # location_id -> (lat, lon)
    with ThreadPoolExecutor(max_workers=max_workers_bbox) as ex:
        futs = {ex.submit(fetch_bbox_objects, session, bbox, timeout): bbox for bbox in bboxes}
        for fut in tqdm(as_completed(futs), total=len(futs), desc="Bbox tiles"):
            try:
                for loc_id, lat, lon in fut.result():
                    if loc_id not in location_map:
                        location_map[loc_id] = (lat, lon)
            except Exception:
                pass

    if not location_map:
        if own_session:
            session.close()
        return pd.DataFrame()

    print(f"Found {len(location_map)} unique locations, fetching details...")

    # Stage 2: fetch each location JSON and parse antennas
    all_rows = []
    with ThreadPoolExecutor(max_workers=max_workers_locations) as ex:
        futs = {
            ex.submit(fetch_and_parse_location, session, lid, lat, lon, timeout): lid
            for lid, (lat, lon) in location_map.items()
        }
        for fut in tqdm(as_completed(futs), total=len(futs), desc="Location details"):
            with contextlib.suppress(Exception):
                all_rows.extend(fut.result())

    if own_session:
        session.close()

    if not all_rows:
        return pd.DataFrame()

    return pd.DataFrame(all_rows).drop_duplicates()


def create_subboxes(bbox):
    sample_bbox = [18.247381, 18.398271, 52.72217, 52.811494]
    tile_w = sample_bbox[1] - sample_bbox[0]
    tile_h = sample_bbox[3] - sample_bbox[2]

    min_lon, max_lon, min_lat, max_lat = bbox

    cols = int(np.ceil((max_lon - min_lon) / tile_w))
    rows = int(np.ceil((max_lat - min_lat) / tile_h))

    subboxes = []
    for r in range(rows):
        for c in range(cols):
            x0 = min_lon + c * tile_w
            x1 = min(x0 + tile_w, max_lon)
            y0 = min_lat + r * tile_h
            y1 = min(y0 + tile_h, max_lat)
            subboxes.append([x0, x1, y0, y1])
    return subboxes


class BaseStations:
    """Poland base station extractor using BTSearch map API."""

    def __init__(
        self,
        operator=None,
        technology=None,
        bounding_box=None,
        frequency_range=None,
        frequency_band=None,
        date=None,
        raw_antenna_cache_file=None,
        pattern_file=None,
        output_folder="output/poland/",
        max_workers=16,
        file_identifier=None,
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
        self.raw_antenna_cache_file = raw_antenna_cache_file or os.path.join(current_folder, "all.pkl")
        self.pattern_file = pattern_file
        self.output_folder = output_folder
        self.max_workers = max(1, int(max_workers))
        self.antennas = pd.DataFrame()

        if not file_identifier:
            self.file_identifier = create_unique_file_identifier(self)
        else:
            self.file_identifier = file_identifier

    def extract_antennas(self, config=None):
        save_cache = (
            self.operator is None
            and self.technology is None
            and self.bounding_box is None
            and self.frequency_band is None
            and (self.frequency_range == [0, np.inf] or np.array_equal(self.frequency_range, [0, np.inf]))
        )

        # Try cache first
        if self.raw_antenna_cache_file and os.path.exists(self.raw_antenna_cache_file):
            try:
                self.antennas = pd.read_pickle(self.raw_antenna_cache_file)
                print(f"Loaded cached antenna data from {self.raw_antenna_cache_file}")
            except Exception as e:
                print(f"Warning: failed to load cache: {e}")

        if self.antennas is None or self.antennas.empty:
            bbox = self.bounding_box or [14.12298, 24.14578, 49.00205, 54.83578]
            subboxes = create_subboxes(bbox)
            print(f"Querying {len(subboxes)} tiles...")

            pool_size = max(self.max_workers * 2, 32)
            session = create_session(pool_maxsize=pool_size)

            self.antennas = extract_all_antennas(
                subboxes,
                session=session,
                max_workers_bbox=min(self.max_workers, 16),
                max_workers_locations=min(self.max_workers * 2, 32),
                timeout=10,
            )
            session.close()

        if self.antennas.empty:
            print("Result is empty")
            return pd.DataFrame()

        df = self.antennas.copy()
        filter_args = {
            "operator": self.operator,
            "technology": self.technology,
            "bounding_box": self.bounding_box,
            "frequency_range": self.frequency_range,
            "frequency_band": self.frequency_band,
            "date": self.date,
        }
        self.antennas = create_output_df(df, config, filter_args=filter_args).copy()

        # Save cache
        if save_cache and self.raw_antenna_cache_file:
            try:
                os.makedirs(os.path.dirname(self.raw_antenna_cache_file) or ".", exist_ok=True)
                pd.to_pickle(self.antennas, self.raw_antenna_cache_file)
                print(f"Saved raw antenna cache to {self.raw_antenna_cache_file}")
            except Exception as e:
                print(f"Warning: failed to save cache: {e}")

        out_csv = (
            os.path.join(self.output_folder, f"{self.file_identifier}_antennas.csv") if self.output_folder else None
        )
        if out_csv:
            try:
                os.makedirs(os.path.dirname(out_csv), exist_ok=True)
                self.antennas.to_csv(out_csv, index=False)
                print(f"Saved output CSV to {out_csv}")
            except Exception as e:
                print(f"Warning: failed to save output CSV: {e}")

        return self.antennas

    def extract_patterns(self, *args, **kwargs):
        print("Pattern extraction is not supported for Poland.")
        return None


if __name__ == "__main__":
    poland_bbox = [14.12298, 24.14578, 49.00205, 54.83578]
    subboxes = create_subboxes(poland_bbox)
    print(f"Created {len(subboxes)} subboxes")

    session = create_session(pool_maxsize=96)
    antennas = extract_all_antennas(
        subboxes,
        session=session,
        max_workers_bbox=16,
        max_workers_locations=32,
        timeout=10,
    )
    session.close()

    print(f"Extracted {len(antennas)} antennas")
    if not antennas.empty:
        print(f"Operators: {antennas['Operator'].value_counts().to_dict()}")
        print(f"Technologies: {antennas['Technology'].value_counts().to_dict()}")
