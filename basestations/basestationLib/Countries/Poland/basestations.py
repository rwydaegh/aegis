import os
import pickle
import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from io import StringIO
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from ...utils import create_unique_file_identifier, create_output_df
from bs4 import BeautifulSoup
import re
from datetime import datetime, timezone

current_folder = os.path.dirname(os.path.abspath(__file__))


# ----------------------------
# Session and HTTP helpers
# ----------------------------
def create_session(retries=3, pool_maxsize=64):
    """
    Requests session with retries and a larger connection pool.
    pool_maxsize should be >= total parallel GETs you expect.
    """
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
    return session


def http_get_json(session: requests.Session, url: str, timeout=10):
    r = session.get(url, timeout=timeout)
    if r.status_code != 200:
        return None
    try:
        return r.json()
    except Exception:
        return None


def http_get_text(session: requests.Session, url: str, timeout=10):
    r = session.get(url, timeout=timeout)
    if r.status_code != 200:
        return None
    return r.text


# ----------------------------
# HTML parsing helpers
# ----------------------------
def find_hrefs(htmlstring: str):
    soup = BeautifulSoup(htmlstring, "html.parser")
    return [a["href"] for a in soup.find_all("a", href=True) if a.get("href")]


def parse_site_ids(html: str):
    """
    Returns (operator_name, location_record_id_in_parentheses, operator_internal_site_label)
    Example:
      operator = "Plus"
      location_record_id = "26001"
      operator_internal_site_label = "BT31999"
    """
    # lxml is faster if installed, fallback to html.parser if not
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")

    header = soup.select_one("#location-info-container-extended .location-address")
    if not header:
        return None, None, None

    strong = header.find("strong")
    operator = strong.get_text(strip=True) if strong else None

    header_text = header.get_text(" ", strip=True)
    m = re.search(r"\((\d+)\)", header_text)
    location_record_id = m.group(1) if m else None

    abbr = header.find("abbr", attrs={"title": re.compile(r"Identyfikator wewnętrzny operatora", re.I)})
    operator_internal_id = abbr.get_text(strip=True) if abbr else None

    return operator, location_record_id, operator_internal_id


def read_location_info_tables(html: str):
    """
    Faster than generic read_html because it restricts to the tables you care about.
    """
    try:
        dfs = pd.read_html(StringIO(html), attrs={"class": "location-info"})
        return dfs
    except Exception:
        return None


def split_technology(table: pd.DataFrame):
    """
    btsearch tables often come in a MultiIndex column format where top level is technology (LTE, GSM, UMTS).
    Returns (technology, flattened_table).
    """
    if isinstance(table.columns, pd.MultiIndex):
        tech = str(table.columns.get_level_values(0)[0])
        t = table.copy()
        t.columns = t.columns.droplevel(0)
        return tech, t
    else:
        return "UNKNOWN", table.copy()


def normalize_table(
    table: pd.DataFrame,
    operator: str,
    sitelabel: str,
    latitude: float,
    longitude: float,
    location_id: int,
):
    """
    Produces a standardized dataframe for one technology table.
    """
    technology, t = split_technology(table)

    if "UKE" in str(technology):
        return None

    # Basic expected rename
    map_cols = {"Pasmo": "Frequency"}
    t = t.rename(columns=map_cols)

    if "Frequency" not in t.columns:
        return None

    t["Frequency"] = t["Frequency"].astype(str)
    # FrequencyBand can be inferred from Frequency if needed "Band{f}MHz"
    t["FrequencyBand"] = t["Frequency"].map(lambda f: f"Band{f}MHz")
    if 'Band3500MHz' in t['FrequencyBand'].values:
        t.loc[t['FrequencyBand'] == 'Band3500MHz', 'FrequencyBand'] = 'Band3600MHz'
    # Vectorized counts and labels
    t["Nantennas"] = t.groupby("Frequency")["Frequency"].transform("size")

    # Metadata
    t["Operator"] = operator
    t["Technology"] = technology
    t["Latitude"] = float(latitude)
    t["Longitude"] = float(longitude)
    t["LocationID"] = location_id

    # Prefer stable station label for site code if present
    site_code = sitelabel if sitelabel else str(location_id)
    t["SiteCode"] = f"SITE({site_code})"

    # One AntennaLabel per frequency for this site and tech
    t["AntennaLabel"] = t["Frequency"].map(lambda f: f"ANT({site_code}_{technology}_{f})")

    # Current pipeline uses isotropic azimuth
    t["Azimuth"] = "isotropic"

    # Drop fully identical rows (safe)
    t = t.drop_duplicates()
    # convert "Frequency" to numeric 
    t["Frequency"] = pd.to_numeric(t["Frequency"], errors='coerce')

    return t


# ----------------------------
# Core optimized crawler
# ----------------------------
def fetch_bbox_objects(session: requests.Session, bbox, timeout=10):
    """
    One bbox request to get objects.
    bbox = [min_lon, max_lon, min_lat, max_lat]
    API expects bounds = min_lat,min_lon,max_lat,max_lon (as in your code)
    """
    api_url = f"https://beta.btsearch.pl/map/locations/?bounds={bbox[2]},{bbox[0]},{bbox[3]},{bbox[1]}"
    data = http_get_json(session, api_url, timeout=timeout)
    if not data:
        return []
    objs = data.get("objects", [])
    out = []
    for d in objs:
        out.append(
            (
                int(d.get("id")) if d.get("id") is not None else None,
                d.get("latitude", np.nan),
                d.get("longitude", np.nan),
            )
        )
    return [x for x in out if x[0] is not None]


def fetch_location_page_info(session: requests.Session, location_id: int, timeout=10):
    url = f"https://beta.btsearch.pl/map/locations/{location_id}/?"
    return http_get_json(session, url, timeout=timeout)


def extract_detail_urls_from_location_json(location_json):
    """
    location_json has "info" which is HTML containing <a href="..."> links to detail pages.
    Returns list of absolute urls.
    """
    if not location_json or "info" not in location_json:
        return []
    info = location_json.get("info") or ""
    hrefs = find_hrefs(info)
    # Make absolute and keep only those that look like location detail endpoints
    urls = []
    for h in hrefs:
        if not h:
            continue
        if h.startswith("http"):
            urls.append(h)
        else:
            urls.append(f"https://beta.btsearch.pl{h}")
    return urls


def get_antennas_in_multiple_bboxes_optimized(
    bboxes,
    session=None,
    max_workers_bbox=16,
    max_workers_locations=32,
    max_workers_details=32,
    timeout=10,
):
    """
    Optimized approach:
      1) Fetch all bbox objects (ids, lat, lon) and deduplicate by location_id.
      2) Fetch each location json once and extract detail urls.
      3) Deduplicate detail urls and fetch each html once.
      4) Parse and normalize tables into one dataframe.
    This avoids nested thread pools and avoids repeated GETs across tiles.
    """
    should_close_session = False
    if session is None:
        session = create_session(pool_maxsize=max(max_workers_bbox, max_workers_locations, max_workers_details) + 8)
        should_close_session = True

    # 1) Collect location ids across all bboxes
    location_map = {}  # location_id -> (lat, lon)
    with ThreadPoolExecutor(max_workers=max_workers_bbox) as ex:
        futs = {ex.submit(fetch_bbox_objects, session, bbox, timeout): bbox for bbox in bboxes}
        for fut in tqdm(as_completed(futs), total=len(futs), desc="Fetching bbox objects"):
            try:
                objs = fut.result()
                for location_id, lat, lon in objs:
                    if location_id not in location_map:
                        location_map[location_id] = (lat, lon)
            except Exception as e:
                bbox = futs[fut]
                print(f"Error fetching bbox {bbox}: {e}")

    if not location_map:
        if should_close_session:
            session.close()
        return pd.DataFrame()

    location_ids = list(location_map.keys())

    # 2) Fetch location pages and build detail urls
    detail_url_to_location = {}  # detail_url -> location_id
    with ThreadPoolExecutor(max_workers=max_workers_locations) as ex:
        futs = {ex.submit(fetch_location_page_info, session, lid, timeout): lid for lid in location_ids}
        for fut in tqdm(as_completed(futs), total=len(futs), desc="Fetching location JSON"):
            lid = futs[fut]
            try:
                loc_json = fut.result()
                urls = extract_detail_urls_from_location_json(loc_json)
                for u in urls:
                    # Dedup detail page fetches globally
                    if u not in detail_url_to_location:
                        detail_url_to_location[u] = lid
            except Exception as e:
                print(f"Error fetching location {lid}: {e}")

    detail_urls = list(detail_url_to_location.keys())
    if not detail_urls:
        if should_close_session:
            session.close()
        return pd.DataFrame()

    # 3) Fetch detail pages and parse
    frames = []
    with ThreadPoolExecutor(max_workers=max_workers_details) as ex:
        futs = {ex.submit(http_get_text, session, url, timeout): url for url in detail_urls}
        for fut in tqdm(as_completed(futs), total=len(futs), desc="Fetching detail HTML"):
            url = futs[fut]
            lid = detail_url_to_location.get(url)
            lat, lon = location_map.get(lid, (np.nan, np.nan))
            try:
                html = fut.result()
                if not html:
                    continue

                operator, _loc_paren, sitelabel = parse_site_ids(html)
                dfs = read_location_info_tables(html)
                if not dfs:
                    continue

                # Normalize each table
                for table in dfs:
                    t = normalize_table(
                        table=table,
                        operator=operator,
                        sitelabel=sitelabel,
                        latitude=lat,
                        longitude=lon,
                        location_id=lid,
                    )
                    if t is not None and not t.empty:
                        frames.append(t)
            except Exception as e:
                print(f"Error parsing detail page {url} for location {lid}: {e}")

    if should_close_session:
        session.close()

    if not frames:
        return pd.DataFrame()

    all_antennas = pd.concat(frames, ignore_index=True).drop_duplicates()
    return all_antennas


# ----------------------------
# Subbox helper (keep your logic)
# ----------------------------
def create_subboxes(bbox):
    sample_bbox = [18.247381, 18.398271, 52.72217, 52.811494]  # target tile size
    tile_w = sample_bbox[1] - sample_bbox[0]
    tile_h = sample_bbox[3] - sample_bbox[2]

    min_lon, max_lon, min_lat, max_lat = bbox[0], bbox[1], bbox[2], bbox[3]

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


# ----------------------------
# Class wrapper
# ----------------------------
class BaseStations:
    """Poland base station extractor (optimized crawler wrapped in a class)."""

    def __init__(
        self,
        operator=None,
        technology=None,
        bounding_box=None,
        frequency_range=[0, np.inf],
        frequency_band=None,
        date=datetime.now(timezone.utc),
        raw_antenna_cache_file: str = os.path.join(current_folder, "all.pkl"),
        pattern_file: str = None,
        output_folder: str = "output/poland/",
        max_workers: int = 16,
        file_identifier=None,
    ):
        os.makedirs(output_folder, exist_ok=True)
        self.operator = operator
        self.technology = technology
        self.bounding_box = bounding_box
        self.frequency_range = frequency_range
        self.frequency_band = frequency_band
        self.date = date
        self.raw_antenna_cache_file = raw_antenna_cache_file
        self.pattern_file = pattern_file
        self.output_folder = output_folder
        self.max_workers = max(1, int(max_workers))
        self.antennas = pd.DataFrame()

        if not file_identifier:
            self.file_identifier = create_unique_file_identifier(self)
        else:
            self.file_identifier = file_identifier

    def extract_antennas(self, config=None):
        """
        Fetch antennas (or load from cache), apply filters via create_output_df, save CSV.
        """
        save_cache = (
            self.operator is None
            and self.technology is None
            and self.bounding_box is None
            and self.frequency_band is None
            and (self.frequency_range == [0, np.inf] or np.array_equal(self.frequency_range, [0, np.inf]))
        )

        # Load cache if exists
        if self.raw_antenna_cache_file and os.path.exists(self.raw_antenna_cache_file):
            try:
                self.antennas = pd.read_pickle(self.raw_antenna_cache_file)
                print(f"Loaded cached antenna data from {self.raw_antenna_cache_file}")
            except Exception as e:
                print(f"Warning: failed to load cache {self.raw_antenna_cache_file}: {e}")

        if self.antennas is None or self.antennas.empty:
            if not self.bounding_box:
                self.bounding_box = [14.12298, 24.14578, 49.00205, 54.83578]

            subboxes = create_subboxes(self.bounding_box)
            print(f"Querying {len(subboxes)} tiles...")

            # One shared session with pool sized for concurrency
            pool_size = max(self.max_workers * 2, 32)
            session = create_session(pool_maxsize=pool_size)

            # Use one concurrency layer, split workers across stages
            # You can tune these, but these defaults work well in practice
            w_bbox = max(1, min(self.max_workers, 16))
            w_loc = max(1, min(self.max_workers * 2, 32))
            w_det = max(1, min(self.max_workers * 2, 32))

            self.antennas = get_antennas_in_multiple_bboxes_optimized(
                subboxes,
                session=session,
                max_workers_bbox=w_bbox,
                max_workers_locations=w_loc,
                max_workers_details=w_det,
                timeout=10,
            )

            session.close()

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
                os.makedirs(os.path.dirname(self.raw_antenna_cache_file), exist_ok=True)
                pd.to_pickle(self.antennas, self.raw_antenna_cache_file)
                print(f"Saved raw antenna cache to {self.raw_antenna_cache_file}")
            except Exception as e:
                print(f"Warning: failed to save cache: {e}")

        # Save output CSV
        out_csv = os.path.join(self.output_folder, f"{self.file_identifier}_antennas.csv") if self.output_folder else None
        if out_csv:
            try:
                os.makedirs(os.path.dirname(out_csv), exist_ok=True)
                self.antennas.to_csv(out_csv, index=False)
                print(f"Saved output CSV to {out_csv}")
            except Exception as e:
                print(f"Warning: failed to save output CSV: {e}")

        return self.antennas


if __name__ == "__main__":
    poland_bbox = [14.12298, 24.14578, 49.00205, 54.83578]
    subboxes = create_subboxes(poland_bbox)
    print(f"Created {len(subboxes)} subboxes")

    session = create_session(pool_maxsize=96)
    antennas = get_antennas_in_multiple_bboxes_optimized(
        subboxes,
        session=session,
        max_workers_bbox=16,
        max_workers_locations=32,
        max_workers_details=32,
        timeout=10,
    )
    session.close()

    print(f"Extracted {len(antennas)} antennas")
    antennas.to_csv("Countries/Poland/antennas.csv", index=False)
