import os
import pandas as pd
import numpy as np

from datetime import datetime, timezone
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from ...utils import create_unique_file_identifier, format_date_only, create_output_df
import requests

current_folder = os.path.dirname(os.path.abspath(__file__))

# URL for Swiss MAST data (BAKOM)
MAST_DATA_URL = (
    "https://data.geo.admin.ch/ch.bakom.standorte-mobilfunkanlagen/standorte-mobilfunkanlagen/standorte-mobilfunkanlagen_2056.json"
)

# Lazy-loaded global cache; fetched once when needed
MAST_DATA = None


def ensure_mast_data_loaded(session):
    """
    Ensure that MAST_DATA is loaded once.

    This can be called before starting any parallel loops so that
    the HTTP request never happens inside worker threads.
    """
    print(f"Extracting MAST data from {MAST_DATA_URL} for Swisscom antennatypes.")
    global MAST_DATA
    if MAST_DATA is None:
        MAST_DATA = session.get(MAST_DATA_URL).json()


def create_session(timeout=10, retries=3):
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


def find_antennatype_in_json(data, station_name):
    """Return the first feature whose 'station' property matches station_name."""
    global MAST_DATA

    # If no data passed (None), make sure global MAST_DATA is loaded.
    if data is None:
        ensure_mast_data_loaded()
        data = MAST_DATA

    for feature in data["features"]:
        props = feature.get("properties", {})
        if props.get("station") == station_name:
            typ = props.get("typ_en")
            typelabel = typ.split(" ")[0]
            pow = props.get("power_en")
            if "very low" in pow:
                return typelabel, 6
            elif "low" in pow:
                return typelabel, 500
            # NOTE: keep original logic (even though the condition is odd)
            # to preserve behaviour/output.
            elif "high" or "medium" in pow:  # medium is < 5000, high >5000, but no other info is given
                return "Outdoor (High Power)", 5000
            else:
                raise ValueError(f"Power label {pow} not recognized in json data")

    return "Unknown type", np.nan


def get_info_antennatype(numberstring, operator, sitecode):
    if not isinstance(numberstring, str):
        raise TypeError("Antenna type number must be a string")

    # Try converting to int
    if not numberstring:
        # Swisscom: use MAST_DATA via JSON lookup.
        # We ensure it is loaded before any parallel loop in extract_antennas.
        return find_antennatype_in_json(MAST_DATA, f"{operator} {sitecode}")
    else:
        try:
            numberint = int(float(numberstring))
        except Exception:
            print(f"Failed to convert {numberstring} ({type(numberstring)}) to int for antennatype allocation")
            return "Unknown type", np.nan

    # Mapping of antenna types
    if numberint == 1:
        # Femtozelle – small indoor cell
        return "Femtocell", 6
    elif numberint == 2:
        # Innen – indoor antenna
        return "Indoor", 6
    elif numberint == 3:
        # Aussen – outdoor macro/micro
        return "Outdoor", 6
    elif numberint == 4:
        # Tunnel antenna / leaky feeder
        return "Tunnel", 500
    elif numberint == 5:
        # High-power outdoor
        return "Outdoor (High Power)", 5000
    else:
        return "Unknown type", np.nan


def _process_antennadata(antennadata, operator, technology):
    """Process a single antenna data point. Returns a dict for efficient bulk concatenation."""
    longitude = antennadata[0]
    latitude = antennadata[1]
    station = antennadata[2]
    sitecode = station.split(" ")[0]
    typelabel, power = get_info_antennatype(antennadata[3], operator, sitecode)

    if typelabel == "Femtocell" or typelabel == "Indoor" or typelabel == "Tunnel" or typelabel == "Unknown type":
        return None
    power_dbm = 10 * np.log10(power) + 30
    frequency = antennadata[4]
    adaptive = antennadata[5]
    centerheight = antennadata[6]
    pci = antennadata[7]
    azimuth = antennadata[8]
    date = antennadata[9]

    return {
        "Latitude": latitude,
        "Longitude": longitude,
        "AntennaLabel": f"ANT({station.replace(sitecode, '').strip(' _-.')})",
        "Operator": operator,
        "SiteCode": f"SITE({sitecode})",
        "Technology": technology,
        "Power": power_dbm,
        "Date": date,
        "Azimuth": azimuth,
        "AntennaType": typelabel,
        "CenterHeight": centerheight,
        "Frequency": frequency,
        "adaptive": adaptive,
    }


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
        output_folder: str = "output/switzerland/",
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
        if int(self.date.split("-")[0]) < 2023:
            print("$$$$$$$$$ WARNING $$$$$$$$$$")
            print(f"You have selected date: {self.date}")
            print("2G antennas were removed in 2023. The old 2G antenna (from before 2023) data will not be included in the output")

        self.raw_antenna_cache_file = raw_antenna_cache_file
        self.pattern_file = pattern_file
        self.output_folder = output_folder
        self.max_workers = max_workers
        self.antennas = pd.DataFrame()
        self.count = 0
        self.make_op_tech_pairs()

        # Create unique file identifier if not provided
        if file_identifier is None:
            self.file_identifier = create_unique_file_identifier(self)
        else:
            self.file_identifier = file_identifier

    def make_op_tech_pairs(self):
        all_operators = ["Swisscom", "Salt", "Sunrise"]
        all_technologies = ["3G", "4G", "5G"]
        # Case 1: Neither operator nor technology specified → all combinations
        if self.operator is None and self.technology is None:
            self.op_tech_pairs = [
                (op, tech) for op in all_operators for tech in all_technologies
            ]

        # Case 2: Only operator specified → all technologies for this operator
        elif self.operator is not None and self.technology is None:
            if self.operator not in all_operators:
                raise ValueError(f"Unknown operator: {self.operator}")
            self.op_tech_pairs = [(self.operator, tech) for tech in all_technologies]

        # Case 3: Only technology specified → all operators for this technology
        elif self.operator is None and self.technology is not None:
            if self.technology not in all_technologies:
                raise ValueError(f"Unknown technology: {self.technology}")
            self.op_tech_pairs = [(op, self.technology) for op in all_operators]

        # Case 4: Both operator and technology specified → single pair
        else:
            if self.operator not in all_operators:
                raise ValueError(f"Unknown operator: {self.operator}")
            if self.technology not in all_technologies:
                raise ValueError(f"Unknown technology: {self.technology}")
            self.op_tech_pairs = [(self.operator, self.technology)]



    def _process_operator_technology(self, op_tech_pair, session):
        """Process a single Swiss operator/technology pair and return antenna rows."""
        rows = []
        operator, technology = op_tech_pair
        filename = f"{operator}_{technology}.min1.json"
        url = f"https://carteantennesuisse.ch/serve_geojson_min.php?file={filename}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": "https://carteantennesuisse.ch/de/interaktive-karte-antennen-schweiz/",
            "Accept": "application/json,text/html,application/xhtml+xml",
        }

        try:
            r = session.get(url, headers=headers, timeout=10)
            while r.status_code == 400: # MAKE ROBUST FOR FUTURE FILE VERSIONS
                index = 2
                filename = f"{operator}_{technology}.min{index}.json"
                url = f"https://carteantennesuisse.ch/serve_geojson_min.php?file={filename}"
                r = session.get(url, headers=headers, timeout=10)
                index += 1 
                
            if r.status_code != 200:
                print(f"ERROR for url {url}: {r.status_code}")
                return pd.DataFrame()

            data = r.json()
            # Process antenna data in parallel
            if self.max_workers > 1:
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    futures = {
                        executor.submit(
                            _process_antennadata, antennadata, operator, technology
                        ): antennadata
                        for antennadata in data
                    }
                    for future in tqdm(
                        as_completed(futures),
                        total=len(futures),
                        desc=f"{operator}_{technology}",
                        leave=False,
                    ):
                        row_dict = future.result()
                        if row_dict is not None:
                            rows.append(row_dict)
                     
            else:
                # Sequential processing
                for antennadata in tqdm(data, total=len(data), desc=f"{operator}_{technology}", leave=False):
                    row_dict = _process_antennadata(antennadata, operator, technology)
                    if row_dict is not None:
                        rows.append(row_dict)
            # Create DataFrame once from all rows
            if rows:
                return pd.DataFrame(rows)
            else:
                return pd.DataFrame()

        except Exception as e:
            raise RuntimeError(f"Error processing {operator}_{technology}: {e}")

    def extract_antennas(self, config=None):
        """Extract antennas from Swiss JSON data, apply filters, and save CSV.

        Notes:
        - If all filter inputs are standard (None, default range, etc.), antennas
          are auto-saved to raw_antenna_cache_file for later reuse.
        - Uses parallel processing with self.max_workers.
        - Uses connection pooling for efficient HTTP requests.
        """
        print("####### WARNING ########")
        print(
            "Swiss antennatypes are labeled by Femtocell, Indoor, Outdoor or Outdoor (High Power). "
            "Only Outdoor and Outdoor (High Power) antennas are added."
        )
        print("########################")


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

        # If no cache or cache load failed, extract
        if self.antennas is None or self.antennas.empty:
            # Create shared session for connection pooling
            session = create_session()
            # Ensure MAST_DATA is loaded BEFORE any parallel loops start.
            # This guarantees the HTTP request is done once, in the main thread.
            if self.operator is None or self.operator == "Swisscom":
                ensure_mast_data_loaded(session)
                
            df = pd.DataFrame()
            if self.max_workers > 1:
                print(
                    f"Extracting antennas for different operator/technology pairs in parallel ({self.max_workers} workers)"
                )
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    futures = {
                        executor.submit(
                            self._process_operator_technology, pair, session
                        ): pair
                        for pair in self.op_tech_pairs
                    }
                    for future in tqdm(
                        as_completed(futures),
                        total=len(futures),
                        desc="operator/technology pairs",
                    ):
                        rows_results = future.result()
                        df = pd.concat([df, rows_results], ignore_index=True)
            else:
                print(
                    "Extracting antennas for different operator/technology pairs sequentially"
                )
                for pair in tqdm(
                    self.op_tech_pairs, desc="operator/technology pairs"
                ):
                    rows_results = self._process_operator_technology(pair, session)
                    df = pd.concat([df, rows_results], ignore_index=True)

            session.close()

            if not df.empty:
                self.antennas = df
            else:
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
        """Switzerland extractor does not support antenna pattern reconstruction.

        This method is provided for API compatibility and will return None.
        """
        print("Pattern extraction is not supported for Switzerland (no SPARQL pattern data).")
        return None


if __name__ == "__main__":
    BS = BaseStations()
    BS.extract_antennas()
