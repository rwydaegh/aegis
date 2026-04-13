"""Netherlands base station extractor using the official Antenneregister WFS.

This class is designed to match the same BaseStations-style interface you use for
Poland/Spain, while pulling data from:
  https://antenneregister.nl/mapserver/wfs/

Data model notes
- The WFS layer "Antennes" returns site points in EPSG:28992 and includes ANT_IDS
  which reference antenna group ids in the layer "Antennes_Groepen".
- We fetch sites (optionally tiled over a bbox), then fetch antenna groups in batches
  using WFS ResourceId filters.

Output columns
We keep a superset of common fields so create_output_df(...) can standardize/filter:
  AntennaLabel, SiteCode, LocationID,
  Operator, Technology,
  Latitude, Longitude,
  Directional, CenterHeight, Azimuth,
  Frequency, FrequencyBand,
  Power, Date,
  Nantennas

Technology filtering
- The WFS "SAT_CODE" values are mapped to {2G,3G,4G,5G} using a heuristic mapper.
- If you pass technology=None, all {2G,3G,4G,5G} are included.
- If you pass technology=['5G'] only those are included.

Parallelism
- parallel=True enables parallel tile fetching and parallel antenna-group batch fetching.

"""

from __future__ import annotations

import os
import sys
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd
import requests
import json
from pyproj import Transformer

# Optional progress bar
try:
    import tqdm  # type: ignore

    def _tqdm(it, **kwargs):
        return tqdm.tqdm(it, **kwargs)

except Exception:  # pragma: no cover

    def _tqdm(it, **kwargs):
        return it


# -----------------------------------------------------------------------------
# Project utilities (keep same import pattern as your other files)
# -----------------------------------------------------------------------------

try:
    from ...utils import *  # type: ignore
except Exception:  # pragma: no cover
    # Fallback: try to import from a known local package name
    # (adjusted in your project; this keeps this file runnable standalone)
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    from basestationLib.utils import *  # type: ignore



# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

WFS_BASE_URL = "https://antenneregister.nl/mapserver/wfs/"

# WFS layer names
LAYER_SITES = "Antennes"
LAYER_GROUPS = "Antennes_Groepen"

# -----------------------------------------------------------------------------
# Geometry helpers
# -----------------------------------------------------------------------------


def _normalize_bbox(bbox: Sequence[float]) -> Tuple[float, float, float, float]:
    """Accept either ordering and return (min_lon, min_lat, max_lon, max_lat)."""
    if bbox is None: 
        bbox = [3.358333, 50.750417, 7.227778, 53.465556]
    if len(bbox) != 4:
        raise ValueError("bounding_box must be a list of 4 numbers")
    b = [float(x) for x in bbox]

    # Heuristic for EU bboxes: if b[1] > b[2], it is (min_lon, min_lat, max_lon, max_lat)
    # else it's likely (min_lon, max_lon, min_lat, max_lat)
    if b[1] > b[2]:
        min_lon, min_lat, max_lon, max_lat = b
    else:
        min_lon, max_lon, min_lat, max_lat = b

    if max_lon < min_lon:
        min_lon, max_lon = max_lon, min_lon
    if max_lat < min_lat:
        min_lat, max_lat = max_lat, min_lat

    return min_lon, min_lat, max_lon, max_lat

# -----------------------------------------------------------------------------
# Domain helpers
# -----------------------------------------------------------------------------


def convert_frequency_to_mhz(freq_str: str) -> Union[float, pd._libs.missing.NAType]:
    """Convert frequency strings to MHz.

    Examples seen in WFS:
      "3600 MHz" or "3.6 GHz" or "1805-1880 MHz".

    Returns pd.NA if empty.
    """
    if freq_str is None:
        return pd.NA

    s = str(freq_str).strip()
    if not s:
        return pd.NA

    factor = 1.0
    if "GHz" in s:
        factor = 1000.0
        s = s.replace("GHz", "").strip()
    elif "MHz" in s:
        factor = 1.0
        s = s.replace("MHz", "").strip()
    elif "kHz" in s:
        factor = 0.001
        s = s.replace("kHz", "").strip()
    elif "Hz" in s:
        factor = 1e-6
        s = s.replace("Hz", "").strip()

    # Sometimes commas are used as decimal separators
    s = s.replace(",", ".")

    def _to_float(x: str) -> Optional[float]:
        x = x.strip()
        if not x:
            return None
        try:
            return float(x)
        except Exception:
            return None

    if "-" in s:
        parts = [p for p in s.split("-") if p.strip()]
        vals = [v for v in (_to_float(p) for p in parts) if v is not None]
        if not vals:
            return pd.NA
        return float(sum(vals) / len(vals) * factor)

    v = _to_float(s)
    if v is None:
        return pd.NA
    return float(v * factor)

def provider_frequencies(session: requests.Session, timeout: int = 25) -> Dict[str, List[float]]:
    """
    Fetch provider downlink mid frequencies from Antennekaart API (in MHz),
    cached to provider_frequencies.json next to this file.

    Returns
    -------
    Dict[str, List[float]]
        Mapping: provider_name -> list of center frequencies (MHz).
    """
    json_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "provider_frequencies.json")

    # ----------------------------
    # 1) Load cache if present
    # ----------------------------
    if os.path.exists(json_file):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                cached = json.load(f)

            # Normalize to Dict[str, List[float]]
            out: Dict[str, List[float]] = {}
            if isinstance(cached, dict):
                for k, v in cached.items():
                    if isinstance(v, list):
                        out[str(k)] = [
                            float(x) for x in v
                            if x is not None and not (isinstance(x, float) and np.isnan(x))
                        ]
            return out
        except Exception:
            # If cache is corrupted, fall back to fetching
            pass

    # ----------------------------
    # 2) Fetch from API
    # ----------------------------
    url = "https://antennekaart.nl/api/v1/carriers/"
    out: Dict[str, List[float]] = {}
    for tech in ["2g", "3g", "4g", "5g"]:
        params = {  
            "technology": tech
        }
        data = http_get_json(session, params = params, url =url, timeout=timeout)
        if not data:
            return out
        
        for res in data.get("results", []) or []:
            provider_obj = res.get("provider") or {}
            provider = provider_obj.get("name") if isinstance(provider_obj, dict) else None
            if not provider:
                continue

            freq_hz = res.get("freq_dl_mid", np.nan)
            try:
                freq_hz = float(freq_hz)
            except Exception:
                continue

            if not np.isfinite(freq_hz) or freq_hz <= 0:
                continue

            center_mhz = freq_hz / 1_000_000.0
            
            if provider == "Tele 2":
                provider = "Odido"
            if provider not in out:
                out[provider] = [center_mhz]
            else:
                out[provider].append(center_mhz)
            

    # Optional: sort and unique (keeps things tidy)
    for prov in list(out.keys()):
        vals = sorted(set(out[prov]))
        out[prov] = vals

    # ----------------------------
    # 3) Write cache (best effort)
    # ----------------------------
    try:
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    return out

def link_provider_to_freq_in_df(df: pd.DataFrame, provider_freqs: Dict[str, List[float]], tol_mhz = 1) -> pd.DataFrame:
    if df is None or df.empty:
        return df

    df["Operator"] = pd.NA

    f = pd.to_numeric(df["Frequency"], errors="coerce").to_numpy(dtype=float)

    for provider, freqs in provider_freqs.items():
        for freq in freqs:
            freq = float(freq)
            mask = np.isfinite(f) & (np.abs(f - freq) <= tol_mhz)
            df.loc[mask, "Operator"] = provider

    return df

# -----------------------------------------------------------------------------
# WFS calls
# -----------------------------------------------------------------------------


def _wfs_base_params(typename: str) -> Dict[str, str]:
    return {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typename": typename,
        "outputFormat": "application/json",
    }


def _bbox_4326_to_28992(bbox4326: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    """Convert (min_lon, min_lat, max_lon, max_lat) to EPSG:28992 bbox (minx,miny,maxx,maxy)."""
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:28992", always_xy=True)
    min_lon, min_lat, max_lon, max_lat = bbox4326

    x0, y0 = transformer.transform(min_lon, min_lat)
    x1, y1 = transformer.transform(max_lon, max_lat)

    minx, maxx = (x0, x1) if x0 <= x1 else (x1, x0)
    miny, maxy = (y0, y1) if y0 <= y1 else (y1, y0)
    return float(minx), float(miny), float(maxx), float(maxy)


def _tile_bbox_4326(bbox: Tuple[float, float, float, float], step: float = 0.5) -> List[Tuple[float, float, float, float]]:
    """Split a (min_lon, min_lat, max_lon, max_lat) bbox into sub-tiles."""
    min_lon, min_lat, max_lon, max_lat = bbox
    tiles = []
    lat = min_lat
    while lat < max_lat:
        lon = min_lon
        lat_end = min(lat + step, max_lat)
        while lon < max_lon:
            lon_end = min(lon + step, max_lon)
            tiles.append((lon, lat, lon_end, lat_end))
            lon = lon_end
        lat = lat_end
    return tiles


def _fetch_sites_single(session: requests.Session, bbox_4326: Tuple[float, float, float, float], timeout: int = 25) -> List[Dict]:
    """Fetch site features for a single bbox tile."""
    params = _wfs_base_params(LAYER_SITES)
    bbox_28992 = _bbox_4326_to_28992(bbox_4326)
    params["bbox"] = ",".join(map(str, bbox_28992))
    data = http_get_json(session, WFS_BASE_URL, params=params, timeout=timeout)
    if not data:
        return []
    return data.get("features") or []


def fetch_sites(session: requests.Session, *, bbox_4326= None, timeout: int = 25) -> List[Dict]:
    """Fetch site features from layer Antennes, tiling the bbox to avoid WFS 2000-result cap."""
    if bbox_4326 is None:
        params = _wfs_base_params(LAYER_SITES)
        data = http_get_json(session, WFS_BASE_URL, params=params, timeout=timeout)
        if not data:
            return []
        return data.get("features") or []

    tiles = _tile_bbox_4326(bbox_4326, step=0.5)
    print(f"Fetching sites across {len(tiles)} tiles")
    seen_ids = set()
    all_features = []
    for i, tile in enumerate(tiles):
        feats = _fetch_sites_single(session, tile, timeout=timeout)
        for f in feats:
            fid = f.get("id")
            if fid not in seen_ids:
                seen_ids.add(fid)
                all_features.append(f)
        if (i + 1) % 10 == 0 or (i + 1) == len(tiles):
            print(f"  Tile {i+1}/{len(tiles)}: {len(all_features)} unique sites so far")
    return all_features

def create_df_from_antenna_features(features: List[Dict]) -> pd.DataFrame:
    rows = []
    for feature in features:
        props = feature.get("properties") or {}
        # Clean up frequency field
        freq = props.get("FREQUENTIE", None)
        freq_mhz = convert_frequency_to_mhz(str(freq)) if freq is not None else pd.NA
        ant_freq = freq_mhz
        ant_id = props.get("ID")
        ant_tech = props.get("SAT_CODE")
        TECH_TOKENS = ("LTE", "5G", "UMTS", "GSM", "NR", "WCDMA", "EDGE", "4G", "3G", "2G", "5G NR")

        ant_tech_str = "" if ant_tech is None else str(ant_tech)

        if not any(tok in ant_tech_str for tok in TECH_TOKENS):
            continue

        ant_directional = True if props.get("DIR_NONDIR") == "D" else False
        ant_height = props.get("HOOGTE", np.nan)
        ant_azimuth = props.get("HOOFDSTRAALRICHTING", "isotropic")
        if ant_azimuth == "0-359":
            ant_azimuth = "isotropic"
        ant_power = props.get("ZENDVERMOGEN", np.nan)
        ant_date = props.get("DATUM_WIJZIGING") or props.get("DATUM_INGEBRUIKNAME") or props.get("DATUM_PLAATSING")
        rows.append({
            "AntennaLabel": f"ANT({ant_id})",
            "Technology": ant_tech,
            "Frequency": ant_freq,
            "Directional": ant_directional,
            "CenterHeight": ant_height,
            "Azimuth": ant_azimuth,
            "Power": ant_power,
            "Date": ant_date,
        })
    return pd.DataFrame(rows) if rows else pd.DataFrame()
        
def get_antennas_for_site(session: requests.Session, site: Dict, timeout: int = 25) -> List[Dict]:
    
    """Fetch antenna group features for a given site ID."""
    params = _wfs_base_params(LAYER_GROUPS)

    ant_ids = site.get("properties").get("ANT_IDS")
    ant_ids = ant_ids.split(",") if ant_ids else []
    if not ant_ids:
        return pd.DataFrame()
    x, y = site.get("geometry").get("coordinates", [np.nan, np.nan])
    transformer = Transformer.from_crs("EPSG:28992", "EPSG:4326",  always_xy=True)
    longitude, latitude = transformer.transform(x, y)
    
    filter_xml = "<Filter>" + "".join(f'<ResourceId id="{gid.strip()}"/>' for gid in ant_ids) + "</Filter>"
    params["filter"] = filter_xml
    data = http_get_json(session, WFS_BASE_URL, params=params, timeout=timeout)
    if not data:
        return []
    df = create_df_from_antenna_features(data.get("features") or [])
    if not df.empty:    
        df["SiteCode"] = f"SITE({site.get('properties').get('ID')})"
        df["Longitude"] = float(longitude)
        df["Latitude"] = float(latitude)
    return df
    
# Main class
# -----------------------------------------------------------------------------


class BaseStations:
    def __init__(
        self,
        operator=None,
        technology=None,
        bounding_box=None,
        frequency_range=[0, np.inf],
        frequency_band=None,
        date=datetime.now(timezone.utc),
        raw_antenna_cache_file: str = None,
        pattern_file: str = None,
        output_folder: str = "output/netherlands/",
        max_workers: int = 16,
        file_identifier=None,
        parallel: bool = True,
        tile_width_deg: float = 0.5,
        tile_height_deg: float = 0.5,
        batch_size: int = 200,
        timeout: int = 25,
        proxy_servers: list = None,
    ):
        os.makedirs(output_folder, exist_ok=True)

        self.operator = operator
        self.technology = technology
        self.bounding_box = bounding_box
        self.frequency_range = frequency_range
        self.frequency_band = frequency_band
        self.date = date

        self.raw_antenna_cache_file = raw_antenna_cache_file or os.path.join(os.path.dirname(os.path.abspath(__file__)), "all.pkl")
        self.pattern_file = pattern_file
        self.output_folder = output_folder
        self.max_workers = max(1, int(max_workers))

        self.parallel = bool(parallel)
        self.tile_width_deg = float(tile_width_deg)
        self.tile_height_deg = float(tile_height_deg)
        self.batch_size = max(1, int(batch_size))
        self.timeout = int(timeout)

        self.antennas: pd.DataFrame = pd.DataFrame()
        if file_identifier is None:
            self.file_identifier = create_unique_file_identifier(self)
        else:
            self.file_identifier = file_identifier

        # Transformers used many times
        self._to4326 = Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_antennas(self, config=None) -> pd.DataFrame:
        """Extract antenna data and return standardized output df."""
        
        save_cache = (
            self.operator is None
            and self.technology is None
            and self.bounding_box is None
            and self.frequency_band is None
            and (self.frequency_range == [0, np.inf] or np.array_equal(self.frequency_range, [0, np.inf]))
        )

        # Load cache if present
        if self.raw_antenna_cache_file and os.path.exists(self.raw_antenna_cache_file):
            try:
                self.antennas = pd.read_pickle(self.raw_antenna_cache_file)
                print(f"Loaded cached antenna data from {self.raw_antenna_cache_file}")
            except Exception:
                self.antennas = pd.DataFrame()

        if self.antennas is None or self.antennas.empty:
            bbox = _normalize_bbox(self.bounding_box)
            

            session = create_session(pool_maxsize=max(32, self.max_workers * 4))

            # 1) Fetch sites for all tiles

            site_features = fetch_sites(session, bbox_4326=bbox, timeout=self.timeout)
            frames = []
            if self.parallel and self.max_workers > 1:
                with ThreadPoolExecutor(max_workers=min(self.max_workers, 32)) as ex:
                    futs = [ex.submit(get_antennas_for_site, session, site, timeout=self.timeout)
                            for site in site_features]

                    for fut in _tqdm(as_completed(futs), total=len(futs), desc="Iterating over BS sites"):
                        try:
                            df_part = fut.result()
                        except Exception:
                            continue

                        # Skip empty or all-NA frames (prevents the warning)
                        if df_part is None or df_part.empty or df_part.dropna(how="all").empty:
                            continue

                        frames.append(df_part)

            else:
                for site in _tqdm(site_features, total=len(site_features), desc="Iterating over BS sites"):
                    try:
                        df_part = get_antennas_for_site(session, site, timeout=self.timeout)
                    except Exception:
                        continue

                    if df_part is None or df_part.empty or df_part.dropna(how="all").empty:
                        continue

                    frames.append(df_part)

            # One concat at the end (no warning + much faster)
            if frames:
                self.antennas = pd.concat(frames, ignore_index=True)
            else:
                self.antennas = pd.DataFrame()  # or predefine columns if you want
                
            df = self.antennas
            
            # Link provider names
            session = create_session(pool_maxsize=max(32, self.max_workers * 4))
            provider_freqs = provider_frequencies(session, timeout=self.timeout)
                
            df = link_provider_to_freq_in_df(df, provider_freqs)
            
            session.close()
            self.antennas = df

            if save_cache and self.raw_antenna_cache_file:
                try:
                    self.antennas.to_pickle(self.raw_antenna_cache_file)
                    print(f"Saved raw antenna cache to {self.raw_antenna_cache_file}")
                except Exception:
                    pass
        
        return self._finalize_output(config)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _finalize_output(self, config=None) -> pd.DataFrame:
        df_out = create_output_df(
            self.antennas.copy() if self.antennas is not None else pd.DataFrame(),
            config,
            filter_args={
                "operator": self.operator,
                "technology": self.technology,
                "frequency_range": self.frequency_range,
                "frequency_band": self.frequency_band,
            },
        )
        self.antennas = df_out
        out_csv = os.path.join(self.output_folder, f"{self.file_identifier}_antennas.csv")
        try:
            df_out.to_csv(out_csv, index=False)
            print(f"Saved filtered output to {out_csv}")
        except Exception:
            pass

        return df_out

if __name__ == "__main__":
    # Example usage
    extractor = BaseStations(
        operator=None,
        technology=["4G", "5G"],
        bounding_box= [4.88, 52.35, 4.95, 52.38],  # Approximate bbox for the Amsterdam area
        output_folder="output/netherlands/",
        parallel=True,
        max_workers=1,
    )
    df_antennas = extractor.extract_antennas()
    print(df_antennas.head())
