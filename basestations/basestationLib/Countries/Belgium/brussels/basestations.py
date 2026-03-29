import os
import math
import pandas as pd
from bs4 import BeautifulSoup
from concurrent.futures import ProcessPoolExecutor, as_completed
import requests
import numpy as np
from matplotlib import pyplot as plt
import json
from scipy.io import savemat, loadmat
import datetime
from datetime import timezone,datetime
from .patterns import AntennaPattern   # your class
from tqdm import tqdm
from ....utils.create_unique_file_identifier import create_unique_file_identifier
from ....utils import create_output_df
from ....utils.pattern_utils import sanitize_label

API_URL = "https://geodata.environnement.brussels/api/geodata/postgis/risk/r_gsm_anten_outdoor_v"

current_folder = os.path.dirname(os.path.abspath(__file__))
parent_folder = os.path.abspath(os.path.join(current_folder, os.pardir))

with open(f"{parent_folder}/DL_frequency_bands.json") as f:
    DL_frequency_bands = json.load(f)

# Reuse HTTP connections (each process will get its own session)
_session = requests.Session()


def same_operator(operator1, operator2):
    """Check if one of the words in the string are the same (case insensitive)."""
    operator1 = operator1.lower()
    operator2 = operator2.lower()
    for word1 in operator1.split():
        for word2 in operator2.split():
            if word1 == word2:
                return True
    return False


# ---------- API helpers ----------

def extract_unique_hrefs(api_url: str) -> list[str]:
    data = _session.get(api_url, timeout=30).json()
    hrefs = []
    for feat in data.get("features", []):
        html_code = feat.get("properties", {}).get("html_fr", "")
        a = BeautifulSoup(html_code, "html.parser").select_one("a[href]")
        if a:
            hrefs.append(a["href"])
    seen, uniq = set(), []
    for h in hrefs:
        if h not in seen:
            seen.add(h)
            uniq.append(h)
    return uniq


def process_single_href(href: str):
    """
    Process one href and return:
      - antennas_df: pd.DataFrame with same columns/dtypes as original
      - patterns_dict: {label: {'gain_db_2d', 'azimuths_deg', 'elevations_deg'}}
    """
    BASE = "https://antennes3d.environnement.brussels"
    SITE_ID = href.split("?id=")[-1].split("&")[0]

    rows = []
    all_patterns = {}

    # --- fetch metadata ---
    meta_url = f"{BASE}/meta?id={SITE_ID}"
    resp = None
    try:
        resp = _session.get(meta_url, timeout=30)
        data = resp.json()

        isoldpermit = data.get("isOldPermit", None)
        if isoldpermit is None:
            print(f"Warning: isOldPermit missing for SITE_ID {SITE_ID}")
        if isoldpermit:
            # skip old permits
            return pd.DataFrame(), {}

        permit_id = data.get("id_global_outdoor")
        if not permit_id:
            permit_id = data.get("id_global_horiz")
        if not permit_id:
            permit_id = SITE_ID

        date = data.get("date_exportation", "")  # format "2014-10-15T12:44:01.969Z"
        date = date.split("T")[0]  # keep only date part
    except Exception as e:
        status = resp.status_code if resp is not None else "N/A"
        print(
            f"Error fetching metadata for SITE_ID {SITE_ID} with href {href} "
            f"and meta_url {meta_url} (status {status}): {e}"
        )
        return pd.DataFrame(), {}

    # --- fetch antenna data ---
    api_url = f"{BASE}/permitantennas?id={permit_id}"
    resp = None
    try:
        resp = _session.get(api_url, timeout=30)
        data = resp.json()

        for panel_key, all_info in data.items():
            coords = all_info.get("geometry", {}).get("coordinates", [])
            if len(coords) < 3:
                continue
            lat, lon, alt = coords[1], coords[0], coords[2]

            properties = all_info.get("properties", {})
            transmitters = properties.get("transmitters", [])

            for tx in transmitters:
                panel_id = tx.get("panneau_id", "")
                sitecode = tx.get("antbts", "")
                name = tx.get("antname", "")

                azimuth = tx.get("antazi", np.nan)
                power = tx.get("anteff", np.nan)
                gain = tx.get("antgain", np.nan)
                electical_tilt = tx.get("antelect", np.nan)
                mechanical_tilt = tx.get("antmect", np.nan)
                Centerheight = tx.get("anthma", np.nan)
                operator = tx.get("operateur", "")
                technology = tx.get("system", "")

                # Same logic as original for frequencyband string
                frequencyband = technology.split(" ")[-1]
                frequencyband = f"Band{frequencyband}MHz"
                # Find operator frequency
                frequency = np.nan
                for prov in DL_frequency_bands.keys():
                    if same_operator(prov, operator):
                        try:
                            frequency = float(
                                DL_frequency_bands.get(prov)
                                .get(frequencyband.replace("Band",""))
                                .get("centerfrequency_MHz")
                            )
                        except Exception:
                            frequency = np.nan
                        break

                duplex = tx.get("duplex", "")
                panel_config = tx.get("xxtxxt", "")
                horizontal_pattern = tx.get("diagram_hori", [])
                vertical_pattern = tx.get("diagram_verti", [])
                
                if frequencyband == "Band3500MHz":
                    frequencyband = "Band3600MHz"
                # Collect row instead of concatenating DataFrames
                rows.append(
                    {
                        "sitecode": f"SITE({sitecode})",
                        "date": date,
                        "name": f"ANT({name.replace(sitecode, '').strip(' ._-')})",
                        "lat": lat,
                        "lon": lon,
                        "alt": alt,
                        "center_height": Centerheight,
                        "azimuth": azimuth,
                        "power": power,
                        "gain": gain,
                        "electical_tilt": electical_tilt,
                        "mechanical_tilt": mechanical_tilt,
                        "operator": operator,
                        "technology": technology,
                        "frequencyband": frequencyband,
                        "frequency": frequency,
                        "duplex": duplex,
                        "panel_config": panel_config,
                        "filenumber": permit_id,
                    }
                )
                
                # Pattern generation
                pattern_instance = AntennaPattern(
                    horizontal_pattern, vertical_pattern, float(gain)
                )
                gain_matrix, elevation_angles, azimuth_angles = pattern_instance.get_3dpattern(
                    return_angles=True
                )
                # pattern_instance.plot_2dpattern(orientation="Horizontal")
                # pattern_instance.plot_2dpattern(orientation="Vertical")
                # pattern_instance.plot_3dpattern()
                # pattern_instance._3d_pattern_heatmap()
                # plt.show()
                label = f"SITE({sitecode})_ANT({name.replace(sitecode, '').strip(' ._-')})"
            
                # Sanitize pattern key for .mat file compatibility (remove parentheses)
                sanitized_label = sanitize_label(label)
                all_patterns[sanitized_label] = np.array(gain_matrix, dtype=np.float16)
                # except Exception as e:
                #     # Do not break the whole run if one pattern fails
                #     print(f"Error computing pattern for {rows['sitecode']}_{rows['name']}: {e}")

    except Exception as e:
        status = resp.status_code if resp is not None else "N/A"
        print(
            f"Error fetching data for SITE_ID {SITE_ID} with href {href} "
            f"and api_url {api_url} (status {status}): {e}"
        )
        return pd.DataFrame(rows), all_patterns

    antennas_df = pd.DataFrame(rows)
    return antennas_df, all_patterns

class BaseStations:
    def __init__(
        self,
        operator=None,
        technology=None,
        bounding_box=None,
        frequency_range=[0, np.inf],
        frequency_band= None,
        date=datetime.now(timezone.utc),
        raw_antenna_cache_file: str = os.path.join(current_folder,"all.pkl") ,
        pattern_file: str = os.path.join(current_folder, "patterns.mat"),
        output_folder: str = "output/belgium/brussels/",
        max_workers: int = 1,
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
        self.antennas = pd.DataFrame()
        self.patterns = {}
        self.max_workers = max(1, int(max_workers))  # enforce at least 1
        if file_identifier is None:
            self.file_identifier = create_unique_file_identifier(self)
        else:
            self.file_identifier = file_identifier
        if not os.path.exists(self.raw_antenna_cache_file) or not os.path.exists(self.pattern_file):
            self.run()

    def run(self):
        print(f"Using {self.max_workers} worker(s)")

        hrefs = extract_unique_hrefs(API_URL)
        if not hrefs:
            print("No links found in API.")
            return

        df_list = []
        all_patterns = {}

        if self.max_workers == 1:
            # Sequential (tqdm over hrefs)
            for h in tqdm(hrefs, desc="Processing hrefs (sequential)"):
                df, patterns = process_single_href(h)
                if not df.empty:
                    df_list.append(df)
                all_patterns.update(patterns)
        else:
            # Parallel with ProcessPoolExecutor
            with ProcessPoolExecutor(max_workers=self.max_workers) as exe:
                futures = {exe.submit(process_single_href, h): h for h in hrefs}
                for fut in tqdm(
                    as_completed(futures),
                    total=len(futures),
                    desc=f"Processing hrefs (parallel, {self.max_workers} workers)",
                ):
                    href = futures[fut]
                    try:
                        df, patterns = fut.result()
                    except Exception as e:
                        print(f"Error processing {href}: {e}")
                        continue
                    if not df.empty:
                        df_list.append(df)
                    all_patterns.update(patterns)

        if df_list:
            all_antennas = pd.concat(df_list, ignore_index=True)
        else:
            all_antennas = pd.DataFrame()

        self.antennas = all_antennas
        self.patterns = all_patterns
        os.makedirs(os.path.dirname(self.raw_antenna_cache_file), exist_ok=True)
        pd.to_pickle(self.antennas, self.raw_antenna_cache_file)
        os.makedirs(os.path.dirname(self.pattern_file), exist_ok=True)
        savemat(self.pattern_file, self.patterns, do_compression=True)
        return

    def filter_operator(self):
        if self.operator is None or self.antennas["operator"].empty:
            return
        indices = self.antennas["operator"].apply(lambda x: same_operator(x, self.operator))
        self.antennas = self.antennas[indices]
        return

    def filter_technology(self):
        if self.technology is None or self.antennas["technology"].empty:
            return
        self.antennas = self.antennas[self.antennas["technology"] == self.technology]
        return

    def filter_bounding_box(self):
        if self.bounding_box is None or self.antennas["lat"].empty or self.antennas["lon"].empty:
            return
        min_lon, max_lon, min_lat, max_lat = self.bounding_box
        self.antennas = self.antennas[
            (self.antennas["lon"] >= min_lon)
            & (self.antennas["lon"] <= max_lon)
            & (self.antennas["lat"] >= min_lat)
            & (self.antennas["lat"] <= max_lat)
        ]
        return

    def filter_frequency_range(self):
        # filter the technology column based on frequency range
        if self.frequency_range is None or self.antennas["frequency"].empty:
            return
        freq_min, freq_max = self.frequency_range
        technology_freqs = self.antennas["frequency"] * 10**6  # convert to Hz from MHz
        indices_to_keep = [i for i, freq in enumerate(technology_freqs) if freq_min <= freq <= freq_max]
        self.antennas = self.antennas.iloc[indices_to_keep]
        return

    def filter_date(self):
        if self.date is None or self.antennas["date"].empty:
            return
        ref_date = pd.to_datetime(self.date, utc=True)
        dates = pd.to_datetime(self.antennas["date"], utc=True, errors="coerce")
        self.antennas = self.antennas[dates <= ref_date]
        return

    def filter_patterns(self):
        # based on the names and sitecodes in self.antennas, filter self.patterns
        filtered_patterns = {}
        for _, row in self.antennas.iterrows():
            try:
                sitecode = row['sitecode']
                name = row['name']
            except KeyError:
                sitecode = row['SiteCode']
                name = row['AntennaLabel']
            # Handle combined AntennaLabels (e.g., "ANT(a)/ANT(b)")
            antenna_parts = str(name).split('/')
            first_part = antenna_parts[0].strip()
            label = f"{sitecode}_{name}"
            sanitized = sanitize_label(label)
            first_label = f"{sitecode}_{first_part}"
            first_sanitized = sanitize_label(first_label)

            if sanitized in self.patterns: 
                filtered_patterns[sanitized] = self.patterns[sanitized]
            elif first_sanitized in self.patterns:
                filtered_patterns[sanitized] = self.patterns[first_sanitized]
            else: 
                print(f"{sanitized} not found in patterns")

        self.patterns = filtered_patterns
        if len(self.antennas) != len(self.patterns):
            print(
                f"Warning: Mismatch in counts - antennas: {len(self.antennas)}, "
                f"patterns: {len(self.patterns)}"
            )
        return

    def calculate_beamwidths(self):
        """
        Iterate over self.antennas and, for each antenna, compute horizontal and
        vertical 3 dB beamwidths based on the corresponding entry in self.patterns.

        Assumes:
        - self.antennas has columns "sitecode" and "name" or "SiteCode" and "AntennaLabel"
        - self.patterns keys are sanitized "{sitecode}_{name}"
        - pattern is a 2D numpy array of shape (181, 360) for elevations -90..90 and azimuths -180..179
        """

        # Pre-fill with NaN in case some antennas have no pattern
        if "Horizontal_Beamwidth" in self.antennas.columns and "Vertical_Beamwidth" in self.antennas.columns:
            return 
        if not getattr(self, "patterns", None):
            try: 
                self.extract_patterns()
            except:
                return
        if "Horizontal_Beamwidth" not in self.antennas.columns:
            self.antennas["Horizontal_Beamwidth"] = np.nan
        if "Vertical_Beamwidth" not in self.antennas.columns:
            self.antennas["Vertical_Beamwidth"] = np.nan
        

        for row in self.antennas.itertuples(index=True):
            idx = row.Index
            try:
                sitecode = getattr(row, "sitecode", None)
                name = getattr(row, "name", None)
            except AttributeError:
                sitecode = getattr(row, "SiteCode", None)
                name = getattr(row, "AntennaLabel", None)
            if sitecode is None or name is None:
                continue

            label = f"{sitecode}_{name}"
            sanitized_label = sanitize_label(label)
            gain_matrix = self.patterns.get(sanitized_label, None)
            if gain_matrix is None:
                continue

            # Assume standard angles: elevations -90 to 90 (181 values), azimuths -180 to 179 (360 values)
            elevations = np.arange(-90, 91, dtype=np.int16)
            azimuths = np.arange(-180, 180, dtype=np.int16)

            if gain_matrix.shape != (elevations.size, azimuths.size):
                print(
                    f"[WARN] Shape mismatch for pattern {label}: "
                    f"gain={gain_matrix.shape}, expected {(elevations.size, azimuths.size)}"
                )
                continue

            # Horizontal 3 dB beamwidth
            el0_idx = np.argmin(np.abs(elevations))
            horiz_slice = gain_matrix[el0_idx, :]
            max_gain_horiz = np.max(horiz_slice)
            half_power_horiz = max_gain_horiz - 3.0
            indices_horiz = np.where(horiz_slice >= half_power_horiz)[0]
            if indices_horiz.size > 1:
                beamwidth_horiz = azimuths[indices_horiz[-1]] - azimuths[indices_horiz[0]]
            else:
                beamwidth_horiz = np.nan

            # Vertical 3 dB beamwidth
            az0_idx = np.argmin(np.abs(azimuths))
            vert_slice = gain_matrix[:, az0_idx]
            max_gain_vert = np.max(vert_slice)
            half_power_vert = max_gain_vert - 3.0
            indices_vert = np.where(vert_slice >= half_power_vert)[0]
            if indices_vert.size > 1:
                beamwidth_vert = elevations[indices_vert[-1]] - elevations[indices_vert[0]]
            else:
                beamwidth_vert = np.nan

            self.antennas.at[idx, "Horizontal_Beamwidth"] = beamwidth_horiz
            self.antennas.at[idx, "Vertical_Beamwidth"] = beamwidth_vert

        return

    def extract_antennas(self, filename=None, config=None):
        # Check if we should use/save the cache (only for standard parameters)

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

            except Exception as e:
                raise RuntimeError(
                    f"Warning: failed to load cache {self.raw_antenna_cache_file}: {e}"
                )

        
        # apply all filters and rename and remove columns
        self.calculate_beamwidths()
        df = self.antennas.rename(
            columns={
                "sitecode": "SiteCode",
                "name": "AntennaLabel",
                "lat": "Latitude",
                "lon": "Longitude",
                "center_height": "CenterHeight",
                "frequency": "Frequency",
                "frequencyband": "FrequencyBand",
                "operator": "Operator",
                "filenumber": "FileNumber",
                "power": "Power",
                "technology": "Technology",
                "azimuth": "Azimuth",
                "gain": "Gain",
                "electical_tilt": "Electrical_Tilt",
                "mechanical_tilt": "Mechanical_Tilt",
            }
        )
        if not filename: 
            output_csv = os.path.join(self.output_folder, f"{self.file_identifier}_antennas.csv")
        else: 
            if ".csv" not in filename:
                raise ValueError("filename must be .csv")
            output_csv = filename
        
        filter_args = {"operator": self.operator, "technology": self.technology, "bounding_box": self.bounding_box, "frequency_range": self.frequency_range, "frequency_band": self.frequency_band, "date": self.date}
        self.antennas = create_output_df(df, config, filter_args=filter_args)
        
        self.antennas.to_csv(output_csv , index=False)
        
        # Save cache if requested and using standard parameters
        if save_cache and self.raw_antenna_cache_file:
            try:
                os.makedirs(os.path.dirname(self.raw_antenna_cache_file), exist_ok=True)
                pd.to_pickle(self.antennas, self.raw_antenna_cache_file)
                print(f"Saved raw antenna cache to {self.raw_antenna_cache_file}")
            except Exception as e:
                raise RuntimeError(f"Warning: failed to save cache: {e}")
        if save_cache and self.pattern_file:
            try:
                os.makedirs(os.path.dirname(self.pattern_file), exist_ok=True)
                savemat(self.pattern_file, self.patterns, do_compression=True)
                print(f"Saved raw pattern cache to {self.pattern_file}")
            except Exception as e:
                raise RuntimeError(f"Warning: failed to save cache: {e}")
        return self.antennas


    def extract_patterns(self, filename=None):
        if not self.patterns:
            patterns_dict = loadmat(self.pattern_file, squeeze_me=True)
            header_keys = ["__globals__", "__header__", "__version__"]
            self.patterns = {k: v for k, v in patterns_dict.items() if k not in header_keys}

        self.filter_patterns()
        # save to .mat
        if not filename:
            output_mat = os.path.join(self.output_folder, f"{self.file_identifier}_patterns.mat")
        else: 
            if ".mat" not in filename: 
                raise ValueError("filename must be .mat")
            output_mat = filename
        savemat(output_mat, self.patterns, do_compression=True)
        return self.patterns


if __name__ == "__main__":
    from multiprocessing import freeze_support

    freeze_support()
    raw_antenna_cache_file = "Countries/Belgium/brussels/all.pkl"
    pattern_file = "Countries/Belgium/brussels/patterns.mat"
    output_folder = "output/Belgium/brussels/"
    filter_args = {
        "operator": None,
        "technology": None,
        "bounding_box": None,
        "frequency_range": [0, np.inf],
        "date": None,
    }

    # change max_workers here to enable parallel processing
    BSs = BaseStations(
        raw_antenna_cache_file=raw_antenna_cache_file,
        pattern_file=pattern_file,
        output_folder = output_folder,
        max_workers=6,
        **filter_args,
    )
    df = BSs.extract_antennas()
    print(len(df))
