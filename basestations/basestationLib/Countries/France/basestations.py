import os
import pandas as pd
import numpy as np

from datetime import datetime, timezone
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from ...utils import create_unique_file_identifier, format_date_only, create_output_df, same_operator
import requests

current_folder = os.path.dirname(os.path.abspath(__file__))

def create_session(timeout=10, retries=5):
    """Create a requests session with connection pooling and automatic retries."""
    session = requests.Session()
    retry_strategy = Retry(
        total=retries,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        backoff_factor=1,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session
def _select_center_dl_freq_mhz(bandes):
    """
    Given a list of 'bandes' from Cartoradio, determine the downlink (DL)
    center frequency in MHz, handling:
      - 1 band  (TDD, e.g. 5G 3.5 GHz)
      - 2 bands (UL + DL)
      - 4 or 5 bands (fragmented DL spectrum)
      - any arbitrary number of bands

    Returns
    -------
    center_freq_mhz : float
        Representative DL center frequency in MHz for ray-tracing.
    """

    if not bandes:
        raise ValueError("No 'bandes' provided for emitter.")

    # --- Internal helper: center freq in MHz ---
    def get_center_freq_mhz(unit_freq, start_freq, end_freq):
        if unit_freq == "M":
            return 0.5 * (start_freq + end_freq)
        elif unit_freq == "G":
            return 0.5 * ((start_freq * 1000.0) + (end_freq * 1000.0))
        elif unit_freq == "K": 
            return 0.5 * ((start_freq / 1000.0) + (end_freq / 1000.0))
        else:
            raise ValueError(f"Unrecognized frequency unit '{unit_freq}'")

    # --- Convert each band into center frequency (MHz) ---
    band_infos = []
    for band in bandes:
        if not band: 
            continue
        unit = band["unite"]
        start = band["debut"]
        end   = band["fin"]
        center_mhz = get_center_freq_mhz(unit, start, end)
        band_infos.append({
            "band": band,
            "center_mhz": center_mhz
        })
    if not band_infos:
        return np.inf

    # --- DL = highest frequencies (FDD) ---
    max_center = max(bi["center_mhz"] for bi in band_infos)
    # Allow several DL blocks within tolerance
    DL_TOL_MHZ = 30.0
    dl_blocks = [
        bi for bi in band_infos
        if (max_center - bi["center_mhz"]) <= DL_TOL_MHZ
    ]
    # Should never be empty
    if not dl_blocks:
        raise ValueError(f"Could not identify DL band(s). bandes={bandes}")

    # --- Case A: only one DL band ---
    if len(dl_blocks) == 1:
        return dl_blocks[0]["center_mhz"]

    # --- Case B: multiple DL blocks → compute combined effective DL center ---
    def to_mhz(unit, val):
        if unit == "G": 
            return 1000*val
        elif unit == "K":
            return val/1000
        elif unit == "M":
            return val
        else: 
            raise ValueError(f"Unrecognized frequency unit '{unit}'")

    dl_starts = [to_mhz(bi["band"]["unite"], bi["band"]["debut"]) for bi in dl_blocks]
    dl_ends   = [to_mhz(bi["band"]["unite"], bi["band"]["fin"])   for bi in dl_blocks]

    min_dl_start = min(dl_starts)
    max_dl_end   = max(dl_ends)

    # Combined DL center frequency
    center_freq_mhz = 0.5 * (min_dl_start + max_dl_end)

    return center_freq_mhz

def fill_in_missing_values(df):
    # ---------- Fix CenterHeight ----------
    try:
        valid_heights = df.loc[df["CenterHeight"] != np.inf, "CenterHeight"]
    except:
        print(df)
        raise ValueError("ERROR")
    if len(valid_heights) > 0:
        avg_height = valid_heights.mean()
    else:
        avg_height = np.nan  # fallback default if everything is inf

    df.loc[df["CenterHeight"] == np.inf, "CenterHeight"] = avg_height

    # ---------- Fix Frequency ----------
    for i, row in df.iterrows():
        if row["Frequency"] == np.inf:
            tech = row["Technology"]
            op = row["Operator"]

            mask = (df["Technology"] == tech) & (df["Operator"] == op) & (df.index != i)
            valid_freqs = df.loc[mask & (df["Frequency"] != np.inf), "Frequency"]

            if len(valid_freqs) > 0:
                freq = valid_freqs.mean()
            else:
                freq = np.nan  # fallback

            df.loc[i, "Frequency"] = freq

    return df

def _process_feature(feature,session): 
    df = pd.DataFrame()
    feature_id = feature.get("id")
    longitude, latitude = feature.get("geometry").get("coordinates")
    # build query parameters correctly
    techs = technologystring.split(",")
    params = {
        "categorie": "TEL",
        "technologies[]": techs,   # IMPORTANT
    }
    # Check nature of site
    site_url = f"https://www.cartoradio.fr/api/v1/sites/{feature_id}"
    resp = session.get(site_url, params = params)
    if resp.status_code != 200:
        print(f"Could not get data for url {resp.url}: \n {resp.status_code}")
    site_info = resp.json().get("data").get("description")
    nature = site_info.get("nature")
    site_height = site_info.get("hauteur")
    if "intérieur" in nature.lower() or "tunnel" in nature.lower() or "sous-terrain" in nature.lower():
        return df
    # if "pyl" not in nature.lower() and "timent" not in nature.lower() and 'immeuble' not in nature.lower():
    #     print(nature)

    url = f"https://www.cartoradio.fr/api/v1/sites/{feature_id}/antennes"
    resp = session.get(url, params= params)
    if resp.status_code != 200:
        print(f"Could not get data for url {resp.url}: \n {resp.status_code}")
    data = resp.json().get("data")
    
    for antenna in data:
        operator = antenna.get("station").get("exploitant")
        installations = antenna.get("installations")
        for all_panels in installations:
            height = all_panels.get("hauteur", np.inf)
            if height <= 0: 
                # print(f"\nHeight {height} <= 0: for site {feature_id}: \n {site_info}")
                continue
            for panel in all_panels.get("antennes"):
                id = panel.get("id")
                azimuth = panel.get("orientation", "isotropic")
                for emitter in panel.get("emetteurs"):
                    tech = emitter.get("systeme")
                    
                    freq_band = f"Band{tech.split()[-2]}MHz"
                    freq_band = "Band3600MHz" if freq_band == "Band3500MHz" else freq_band # rename for consistency with other countries
                    date = emitter.get("date_service", "")
                    if not date: 
                        date = antenna.get("station").get("service", "") # try for station date
                    
                    center_freq_mhz = _select_center_dl_freq_mhz(emitter.get("bandes")) 
                    df_to_add = pd.DataFrame({
                        "Latitude": [latitude], 
                        "Longitude": [longitude],
                        "AntennaLabel": [f"ANT({id})"],
                        "Operator": [operator],
                        "SiteCode": [f"SITE({feature_id})"],
                        "Technology": [tech],
                        # "Power": NOT AVAILABLE
                        "Date": [date],
                        "Azimuth": [azimuth],
                        "CenterHeight": [height],
                        "Frequency": [center_freq_mhz],
                        "FrequencyBand": [freq_band]
                    })
                    # if df_to_add.isna().values.any():
                    #     print(df_to_add)
                    #     print(antenna)
                    #     print(resp.url)
                    if not df_to_add.empty:
                        df = pd.concat([df, df_to_add], ignore_index = True)
    if not df.empty:
        df = fill_in_missing_values(df)
        if any(df["Azimuth"].isna()) or any(df["Azimuth"] == "isotropic") and len(df) > 1:
            # remove the rows with NaN azimuth if there are other rows with valid azimuth
            df = df.dropna(subset=["Azimuth"])
        elif any(df["Azimuth"].isna()) or any(df["Azimuth"] == "isotropic") and len(df) == 1:
            # if only one row and azimuth is NaN, set to "isotropic"
            df["Azimuth"] = df["Azimuth"].fillna("isotropic")
        
    # else: 
    #     print(f"{url} resulted in empty df for site {site_url}")
    return df

class BaseStations:
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
        output_folder: str = "output/france/",
        max_workers: int = 1,
        file_identifier=None,
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

        # Create unique file identifier if not provided
        if file_identifier is None:
            self.file_identifier = create_unique_file_identifier(self)
        else:
            self.file_identifier = file_identifier
    
    def set_global_vars(self, session):
        operator_url = "https://www.cartoradio.fr/api/v1/operateursbyterritoire/FXX"
        operators = session.get(operator_url).json().get("operateurs")
        global operatornumberstring
        global technologystring
        operatornumberstring = ""
        technologystring = ""
        for op in operators: 
            if self.operator is None or same_operator(self.operator, op.get("nom")):
                operatornumberstring = ",".join([operatornumberstring, str(op.get("id"))])
                
        technologystring = ""
        for tech in ["2G", "3G", "4G", "5G"]:
            if self.technology is None or tech == self.technology:
                technologystring = ",".join([technologystring, tech])
    
    def get_sites(self, session):
        bboxstring = f"{self.bounding_box[0]},{self.bounding_box[2]},{self.bounding_box[1]},{self.bounding_box[3]}" if self.bounding_box is not None else "-5.142222, 41.333740, 9.560000, 51.089062" # bbox format: min_lon, max_lon, min_lat, max_lat, 
                #url format: is min_lon, min_lat, max_lon, max_lat
                # if bbox not provided use bbox for entire France 
        
        params = {"enservice":"true", "operateurautre": "true", "operateurs": operatornumberstring, "technologies": technologystring, "categories": "TEL", "format": "geojson", "bbox": bboxstring}
        
        url = rf"https://www.cartoradio.fr/api/v1/sites" 
        resp = session.get(url, params = params )
        if resp.status_code != 200:
            print(f"Error getting sites from url {url} with {params}: \n {resp.status_code}")
        data = resp.json()
        return data
        
    def get_antennas(self, sites, session):
        features = sites.get("features")
        df = pd.DataFrame()
        if self.max_workers >1:
            print(f"Extracting antennas (parallel) using {self.max_workers} workers")
            print("WARNING: CartoRadio is often overloaded when using too many workers. If Retry gives an error, try reducing the number of workers")
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(
                        _process_feature, feature, session
                    ): feature
                    for feature in features
                }
                for future in tqdm(
                    as_completed(futures),
                    total=len(futures),
                    desc=f"Basestation sites",
                    leave=False,
                ):
                    df_results = future.result()
                    if not df_results.empty and df_results is not None:
                        df = pd.concat([df, df_results], ignore_index=True)
        else:
            # Sequential processing
            for feat in tqdm(features, total=len(features), desc=f"Basestation sites", leave=False):
                antennadata = _process_feature(feature=feat, session = session)
                if not antennadata.empty:
                    df = pd.concat([df, antennadata], ignore_index=True)
        self.antennas = df
        return
    def extract_antennas(self, config=None):
        """Extract antennas from Swiss JSON data, apply filters, and save CSV.

        Notes:
        - If all filter inputs are standard (None, default range, etc.), antennas
          are auto-saved to raw_antenna_cache_file for later reuse.
        - Uses parallel processing with self.max_workers.
        - Uses connection pooling for efficient HTTP requests.
        """
        # Check if we should use/save the cache (only for standard parameters)
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

        # Try loading cached combined raw data
        if self.raw_antenna_cache_file and os.path.exists(self.raw_antenna_cache_file):
            try:
                self.antennas = pd.read_pickle(self.raw_antenna_cache_file)
                
                print(f"Loaded cached antenna data from {self.raw_antenna_cache_file}")
                
                self.count = len(self.antennas)
                # for i, row in self.antennas.iterrows():
                #     tech = row["Technology"]
                #     freq_band = f"Band{tech.split()[-2]}MHz"
                #     freq_band = "Band3600MHz" if freq_band == "Band3500MHz" else freq_band # rename for consistency with other countries
                #     self.antennas.loc[i, "FrequencyBand"] = freq_band
                # self.antennas.to_csv("Test.csv")
            except Exception as e:
                raise RuntimeError(
                    f"Warning: failed to load cache {self.raw_antenna_cache_file}: {e}"
                )

        # If no cache or cache load failed, extract
        if self.antennas is None or self.antennas.empty:
            # Create shared session for connection pooling
            session = create_session()
            self.set_global_vars(session = session)
            sites = self.get_sites(session=session)
            self.get_antennas(sites = sites, session =session)

            session.close()

            if self.antennas.empty:
                print("Result is empty")
                return pd.DataFrame()
            

        # Save output CSV into output_folder/{file_identifier}_antennas.csv
        out_csv = (
            os.path.join(self.output_folder, f"{self.file_identifier}_antennas.csv")
            if self.output_folder
            else None
        )
        if out_csv:
            try:
                # Apply data estimation if enabled in config
                filter_args = {"operator": self.operator, "technology": self.technology, "bounding_box": self.bounding_box, "frequency_range": self.frequency_range, "frequency_band": self.frequency_band, "date": self.date}
                df = self.antennas.copy()
                self.antennas = create_output_df(df, config, filter_args = filter_args).copy()
                self.antennas.to_csv(out_csv, index=False)

                print(f"Saved output CSV to {out_csv}")
            except Exception as e:
                raise RuntimeError(f"Warning: failed to save output CSV: {e}")
        # Save cache if requested and using standard parameters
        if save_cache and self.raw_antenna_cache_file:
            try:
                os.makedirs(os.path.dirname(self.raw_antenna_cache_file), exist_ok=True)
                pd.to_pickle(self.antennas, self.raw_antenna_cache_file)
                print(f"Saved raw antenna cache to {self.raw_antenna_cache_file}")
            except Exception as e:
                raise RuntimeError(f"Warning: failed to save cache: {e}")
        return self.antennas

    def extract_patterns(self, *args, **kwargs):
        """France extractor does not support antenna pattern reconstruction.

        This method is provided for API compatibility and will return None.
        """
        print("Pattern extraction is not supported for France (no SPARQL pattern data).")
        return None


if __name__ == "__main__":
    BS = BaseStations()
    BS.extract_antennas()
