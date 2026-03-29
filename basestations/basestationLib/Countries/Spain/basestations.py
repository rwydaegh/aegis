import os
import re
import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from io import StringIO

from tqdm import tqdm




# The surrounding package is expected to provide these utilities.
try:
    from ...utils import * 
except Exception:  # pragma: no cover
    # set parent to import from basestationLib core utils
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    from basestationLib.utils import *

current_folder = os.path.dirname(os.path.abspath(__file__))




def get_simplified_operatorname(operator: str) -> str:
    operatornames = {"Vodafone": ["Vodafone"], "Orange": ["Orange"], "Movistar": ["Movistar", "Moviles"], "Digi": ["Digi"]}
    for name, aliases in operatornames.items():
        if name.lower() in operator.lower() or any(alias.lower() in operator.lower() for alias in aliases):
            return name
    return operator


# ----------------------------
# Spain: tiling helper
# ----------------------------

def create_subboxes_spain(bbox):
    """Split a Spain bbox into smaller subboxes.

    Spain's GeoJSON endpoint typically needs bbox + zoom.
    We use the user's provided sample bbox as the tile size.

    bbox format: [min_lon, max_lon, min_lat, max_lat]
    """
    # Provided sample bbox (used as tile size)
    sample_bbox = [-5.6239603443145,35.997021276854,-5.5843923969269,36.044786054992]
    tile_w = sample_bbox[2] - sample_bbox[0]
    tile_h = sample_bbox[3] - sample_bbox[1]
    min_lon, min_lat, max_lon, max_lat = bbox
    # if the bbox is smaller than tile size, just return it as is
    if (max_lon - min_lon) <= tile_w and (max_lat - min_lat) <= tile_h:
        return [[min_lon, min_lat, max_lon, max_lat]]
    
    cols = int(np.ceil((max_lon - min_lon) / tile_w))
    rows = int(np.ceil((max_lat - min_lat) / tile_h))

    subboxes = []
    for r in range(rows):
        for c in range(cols):
            box_min_lon = min_lon + c * tile_w
            box_max_lon = min(box_min_lon + tile_w, max_lon)
            box_min_lat = min_lat + r * tile_h
            box_max_lat = min(box_min_lat + tile_h, max_lat)
            subboxes.append([box_min_lon, box_min_lat, box_max_lon, box_max_lat])
    return subboxes


# ----------------------------
# Spain: parsing helpers
# ----------------------------

_SP_BANDS = {
    # Compact, practical bands (MHz), consistent naming with your other pipeline
    "Band700MHz": (758, 788),
    "Band800MHz": (791, 821),
    "Band900MHz": (925, 960),
    "Band1800MHz": (1805, 1880),
    "Band2100MHz": (2110, 2170),
    "Band2600MHz": (2575, 2675),
    "Band3600MHz": (3420, 3800),
    "Band26000MHz": (26100, 27500),

}


def infer_frequency_band(center_mhz: float) -> str:
    if center_mhz is None or not np.isfinite(center_mhz):
        return None
    for name, (lo, hi) in _SP_BANDS.items():
        if lo <= center_mhz <= hi:
            return name
    # Fallback: to be removed
    return None


def parse_band_string_to_center_mhz(band_str: str):
    """Parse strings like '935.10 - 949.90' to a center frequency in MHz."""
    if band_str is None:
        return None
    s = str(band_str)
    s = s.replace("\xa0", " ").strip()

    # Common formats:
    #  - "935.10 - 949.90"
    #  - "778.00 - 788.00"
    #  - sometimes "935,10 - 949,90" (comma decimal)
    s = s.replace(",", ".")

    nums = re.findall(r"\d+(?:\.\d+)?", s)
    if not nums:
        return None
    vals = [float(x) for x in nums]
    if len(vals) == 1:
        return float(vals[0])
    # take first two as range
    return float(vals[0] + vals[1]) / 2.0


def build_detail_url(base_url: str, detalle_field: str, emplazamiento: str):
    """Normalize the 'Detalle' field into an absolute URL."""
    if detalle_field:
        d = str(detalle_field)
        d = d.replace("\\/", "/")
        # Replace template token
        d = d.replace("@@<url-aplicacion>", base_url.rstrip("/"))
        if d.startswith("http"):
            return d
        if d.startswith("/"):
            return base_url.rstrip("/") + d
        # Sometimes it is just 'detalleEstacion.do?...'
        if "detalleEstacion.do" in d:
            return base_url.rstrip("/") + "/" + d.lstrip("/")

    # Fallback
    return f"{base_url.rstrip('/')}/detalleEstacion.do?emplazamiento={emplazamiento}"


def extract_tables(html: str):
    """Return all HTML tables as pandas DataFrames (best-effort)."""
    try:
        # only keep all html table labeled <table class="tablaDetalleEstacionNivelesMedidos"
        soup = BeautifulSoup(html, "lxml")
        tables = soup.find_all("table", class_="tablaDetalleEstacionNivelesMedidos")
        dfs = []
        for table in tables:
            html_table = str(table)
            df_list = pd.read_html(StringIO(html_table))
            
            if df_list:
                dfs.append(df_list[0])
        return dfs
        
    except Exception:
        return []


def parse_detail_page_spain(html: str):
    """Parse the station detail page.

    Returns:
      antennas_df: rows with columns [Operator, Frequency, FrequencyBand, Nantennas]
      meta: dict with extra station info (address, measured levels, etc.)
    """
    meta = {}

    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")

    # Quick meta extraction: station code and address (top "LOCALIZACIÓN" table)
    # We keep it best-effort because the HTML is quite table-heavy.
    text = soup.get_text(" ", strip=True)
    
    meta["raw_text_head"] = text[:5000]  # truncated, for debugging

    tables = extract_tables(html)
    antennas_df = pd.DataFrame(columns=["Frequency", "FrequencyBand", "AntennaLabel"]) 

    # Identify tables by column names
    for t in tables:
        # the first row may be header, ensure columns are strings
        # if columns are 0,1,2,... make first row as header and remove it from data
        if not all(isinstance(c, str) for c in t.columns):
            t.columns = [str(c) for c in t.iloc[0]]
            t = t.drop(t.index[0]).reset_index(drop=True)
        
        cols = [str(c).strip() for c in t.columns]

        # Technical characteristics table typically has these columns
        if any("Operador" in c for c in cols) and any("Banda" in c for c in cols) and any("Referencia" in c for c in cols):
            for _, row in t.iterrows():
                operator = str(row.get("Operador") or "").strip()
                operator = get_simplified_operatorname(operator)
                band_str = str(row.get("Banda Asignada (MHz)") or "").strip()
                all_bands = band_str.split(";")
                ref = str(row.get("Referencia") or "").strip()
                if not all_bands:
                    continue
                for band_str in all_bands:
                    freq_mhz = parse_band_string_to_center_mhz(band_str)
                    if freq_mhz is None:
                        continue
                    freq_band = infer_frequency_band(freq_mhz)
                    if freq_band is None:
                        continue
                    if antennas_df is None or antennas_df.empty:
                        antennas_df = pd.DataFrame(
                            {
                                "Operator": [operator],
                                "Frequency": [freq_mhz],
                                "FrequencyBand": [freq_band],
                                "AntennaLabel": [f"ANT({ref})"],
                            }
                        )
                    else:
                        antennas_df = pd.concat(
                            [
                                antennas_df,
                                pd.DataFrame(
                                    {
                                        "Operator": [operator],
                                        "Frequency": [freq_mhz],
                                        "FrequencyBand": [freq_band],
                                        "AntennaLabel": [f"ANT({ref})"],
                                    }
                                ),
                            ], 
                            ignore_index=True,
                        )
    return antennas_df


# ----------------------------
# Spain: API calls
# ----------------------------

def fetch_sites_in_bbox_spain(session: requests.Session, base_url: str, bbox, *, zoom: int = 6, timeout: int = 12):
    """Fetch stations from the VCTEL GeoJSON endpoint for one bbox.

    bbox format: [min_lon, max_lon, min_lat, max_lat]
    Endpoint expects bbox as 'minLon,minLat,maxLon,maxLat' (as observed in practice).
    """
    url = f"{base_url.rstrip('/')}/infoantenasGeoJSON.do"
    bbox_param = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"

    params = {
        "idCapa": "null",
        "bbox": bbox_param,
        "zoom": str(int(zoom)),
    }

    data = http_get_json(session, url, params=params, timeout=timeout)
    if not data:
        return []

    feats = data.get("features") or []
    out = []
    for f in feats:
        props = f.get("properties") or {}
        geom = f.get("geometry") or {}
        coords = geom.get("coordinates") or [None, None]
        lon, lat = (coords + [None, None])[:2]

        empl = str(props.get("Gis_ID") or f.get("id") or "").strip()
        if not empl:
            # Try from Detalle
            det = props.get("Detalle")
            if det:
                m = re.search(r"emplazamiento=([0-9A-Za-z]+)", str(det))
                if m:
                    empl = m.group(1)

        if not empl:
            continue

        detail_url = build_detail_url(base_url, props.get("Detalle"), empl)

        out.append(
            {
                "LocationID": empl,
                "Latitude": float(lat) if lat is not None else np.nan,
                "Longitude": float(lon) if lon is not None else np.nan,
                "Address": props.get("Dirección") or props.get("Direcci\u00f3n") or "",
                "SiteCodeRaw": props.get("C\u00f3digo") or props.get("Código") or props.get("Gis_Codigo") or "",
                "DetailURL": detail_url,
            }
        )

    return out


def get_antennas_in_multiple_bboxes_spain(
    bboxes,
    base_url: str,
    session=None,
    max_workers_bbox: int = 16,
    max_workers_details: int = 32,
    timeout: int = 12,
):
    """Optimized Spain extraction:

    1) Fetch all bboxes to collect unique sites.
    2) Fetch each unique detail page once.
    3) Parse technical characteristics table into one row per unique frequency.

    Returns:
      antennas_df (standard columns)
    """

    should_close_session = False
    if session is None:
        session = create_session(pool_maxsize=max(max_workers_bbox, max_workers_details) + 8)
        should_close_session = True

    # 1) Collect sites across all bboxes
    sites = {}  # LocationID -> site dict
    with ThreadPoolExecutor(max_workers=max_workers_bbox) as ex:
        futs = {ex.submit(fetch_sites_in_bbox_spain, session, base_url, bbox, zoom=6, timeout=timeout): bbox for bbox in bboxes}
        for fut in tqdm(as_completed(futs), total=len(futs), desc="Fetching bbox sites (ES)"):
            try:
                for s in fut.result() or []:
                    lid = s["LocationID"]
                    if lid not in sites:
                        sites[lid] = s
            except Exception as e:
                bbox = futs[fut]
                print(f"Error fetching Spain bbox {bbox}: {e}")

    if not sites:
        if should_close_session:
            session.close()
        return pd.DataFrame(), {}

    # 2) Fetch details
    frames = []
    
    with ThreadPoolExecutor(max_workers=max_workers_details) as ex:
        futs = {ex.submit(http_get_text, session, s["DetailURL"], timeout=timeout): lid for lid, s in sites.items()}
        for fut in tqdm(as_completed(futs), total=len(futs), desc="Fetching detail HTML (ES)"):
            lid = futs[fut]
            site = sites.get(lid, {})
            try:
                html = fut.result()
                if not html:
                    continue

                antennas_df = parse_detail_page_spain(html)

                if antennas_df is None or antennas_df.empty:
                    continue

                # Attach standardized columns expected by the pipeline
                antennas_df = antennas_df.copy()
                antennas_df["Latitude"] = site.get("Latitude", np.nan)
                antennas_df["Longitude"] = site.get("Longitude", np.nan)
                antennas_df["LocationID"] = lid

                site_code = lid
                antennas_df["SiteCode"] = f"SITE({site_code})"
                antennas_df["Technology"] = "UNKNOWN"
                antennas_df["Azimuth"] = "isotropic"

                # Numeric frequency
                antennas_df["Frequency"] = pd.to_numeric(antennas_df["Frequency"], errors="coerce")

                frames.append(antennas_df)

            except Exception as e:
                print(f"Error parsing Spain site {lid}: {e}")

    if should_close_session:
        session.close()

    if not frames:
        return pd.DataFrame()

    out = pd.concat(frames, ignore_index=True)

    # Ensure de-dup across sites on Operator x Frequency x LocationID
    # out = out.drop_duplicates(subset=["LocationID", "Operator", "Frequency"], keep="first")

    return out


# ----------------------------
# Spain: Class wrapper
# ----------------------------


class BaseStations:
    """Spain base station extractor (VCTEL Infoantenas)."""

    def __init__(
        self,
        operator=None,
        technology=None,
        bounding_box=[-9.31, 35.99, 3.33, 43.80],
        frequency_range=[0, np.inf],
        frequency_band=None,
        date=datetime.now(timezone.utc),
        raw_antenna_cache_file: str = os.path.join(current_folder, "all.pkl"),
        pattern_file: str = None,
        output_folder: str = "output/spain/",
        max_workers: int = 16,
        file_identifier=None,
        base_url: str = "https://geoportal.minetur.gob.es/VCTEL",
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
        self.site_metadata = {}

        self.base_url = base_url
        

        if not file_identifier:
            self.file_identifier = create_unique_file_identifier(self)
        else:
            self.file_identifier = file_identifier

    def extract_antennas(self, config=None):
        """Fetch antennas (or load from cache), apply filters via create_output_df, save CSV."""

        # Only cache the fully unfiltered crawl
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
                # A conservative default bbox for mainland Spain + islands can be set by the caller.
                # We leave it None by default to force explicit user choice in production.
                raise ValueError("bounding_box must be provided for Spain extraction")

            subboxes = create_subboxes_spain(self.bounding_box)
            print(f"Querying {len(subboxes)} tiles")

            pool_size = max(self.max_workers * 2, 32)
            session = create_session(pool_maxsize=pool_size)

            w_bbox = max(1, min(self.max_workers, 16))
            w_det = max(1, min(self.max_workers * 2, 32))

            df_raw = get_antennas_in_multiple_bboxes_spain(
                subboxes,
                base_url=self.base_url,
                session=session,
                max_workers_bbox=w_bbox,
                max_workers_details=w_det,
                timeout=12,
            )

            session.close()

            self.antennas = df_raw

        # Apply the standard filtering / formatting pipeline
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
    # Example: run a small bbox (the one you provided)
    bbox_example = [-5.6034947534558,36.012620758392,-5.6022582551,36.014113407708]
    config = {
        "computation": {
            "estimation": {
                "estimate_missing_data_based_on_existing": True
            }
        }
    }
    bs = BaseStations(bounding_box=bbox_example, max_workers=1)
    df = bs.extract_antennas(config=config)
    print(df.head())
