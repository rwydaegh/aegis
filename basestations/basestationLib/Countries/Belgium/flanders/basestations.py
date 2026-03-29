import numpy as np
import os
import pandas as pd
from datetime import datetime, timezone
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from scipy.io import savemat
from .sparql import *
from .patterns import AntennaPatternExtractor
from ....utils import create_unique_file_identifier, format_date_only, create_output_df, apply_filters
from ....utils.pattern_utils import sanitize_label


# Assuming import_sparql_service_from_plugin and AntennaPatternExtractor are available in the environment
# or will be imported from a local module. For now, we assume they are globally accessible or handled elsewhere.

# Define mega constant if not already defined
mega = 1_000_000 # 10^6
current_folder = os.path.dirname(os.path.abspath(__file__))
parent_folder = os.path.abspath(os.path.join(current_folder, os.pardir))
class BaseStations:
    """
    Base station data extraction and processing from SPARQL endpoints.

    This class handles the complete workflow of extracting base station data
    from SPARQL endpoints, including filtering by operator/technology/frequency,
    fetching antenna patterns and physical dimensions, and caching results.
    """
    def __init__(
        self,
        operator=None,
        technology=None,
        bounding_box=None,
        frequency_range=None,
        frequency_band=None,
        date=None,
        raw_antenna_cache_file: str = None,
        pattern_file: str = None,
        pattern_cache_file: str = None,
        output_folder: str = "output/belgium/flanders/",
        max_workers: int = 1,
        file_identifier=None,
    ):
        """Initialize BaseStations extractor with parameters for filtering and output."""
        os.makedirs(output_folder, exist_ok=True)
        
        # Set defaults
        if frequency_range is None:
            frequency_range = [0, np.inf]
        if date is None:
            date = datetime.now(timezone.utc)
        if raw_antenna_cache_file is None:
            raw_antenna_cache_file = os.path.join(current_folder, "all.pkl")
        if pattern_file is None:
            pattern_file = os.path.join(current_folder, "patterns.mat")
        
        # Store parameters
        self.operator = operator
        self.technology = technology
        self.bounding_box = bounding_box
        self.frequency_range = frequency_range
        self.frequency_band = frequency_band
        self.date = format_date_only(date)
        self.raw_antenna_cache_file = raw_antenna_cache_file
        self.pattern_file = pattern_file
        self.output_folder = output_folder
        self.max_workers = max(1, int(max_workers))
        
        # Initialize data containers
        self.antennas = pd.DataFrame()
        self.patterns = {}
        self.count = 0
        
        # Set output identifier and SPARQL endpoint
        self.file_identifier = file_identifier or create_unique_file_identifier(self)
        self.sparql_url = "https://data.zendantennes.omgeving.vlaanderen.be/sparql"
        
        # Set pattern cache file (caching when using default parameters)
        if pattern_cache_file is None and self._should_save_cache():
            self.pattern_cache_file = os.path.join(current_folder, "all_patterns.mat")
        else:
            self.pattern_cache_file = pattern_cache_file

    # === HELPER METHODS FOR EXTRACTION ===
    
    def _load_cache(self) -> pd.DataFrame:
        """Load combined raw antenna data from cache if available."""
        if not self.raw_antenna_cache_file or not os.path.exists(self.raw_antenna_cache_file):
            return None
        
        try:
            print(f"Attempting to load combined raw antenna data from cache: {self.raw_antenna_cache_file}")
            combined_df = pd.read_pickle(self.raw_antenna_cache_file)
            if isinstance(combined_df, pd.DataFrame):
                print("Successfully loaded combined raw antenna data from cache.")
                return combined_df
            else:
                print("Warning: Cached data is not a DataFrame. Re-querying.")
                return None
        except Exception as e:
            print(f"Warning: Failed to load cache file. Error: {e}. Re-querying SPARQL.")
            return None
    
    def _load_pattern_cache(self) -> dict:
        """Load cached antenna patterns from .mat file if available."""
        if not self.pattern_cache_file or not os.path.exists(self.pattern_cache_file):
            return None
        
        try:
            print(f"Attempting to load antenna patterns from cache: {self.pattern_cache_file}")
            mat_data = savemat.__class__.__bases__[0]  # Hack to import savemat's module
            from scipy.io import loadmat
            mat_contents = loadmat(self.pattern_cache_file)
            
            patterns = {}
            for key, value in mat_contents.items():
                if not key.startswith('__'):
                    patterns[key] = value
            
            if patterns:
                print(f"Successfully loaded {len(patterns)} patterns from cache.")
                return patterns
            else:
                print("Warning: Pattern cache file is empty.")
                return None
        except Exception as e:
            print(f"Warning: Failed to load pattern cache. Error: {e}. Re-extracting patterns.")
            return None
    
    def _save_pattern_cache(self):
        """Save antenna patterns to .mat cache file."""
        if not self.pattern_cache_file or not self.patterns:
            return
        
        try:
            os.makedirs(os.path.dirname(self.pattern_cache_file) or '.', exist_ok=True)
            savemat(self.pattern_cache_file, self.patterns, do_compression=True)
            print(f"Saved {len(self.patterns)} patterns to cache: {self.pattern_cache_file}")
        except Exception as e:
            print(f"Warning: Failed to save pattern cache. Error: {e}")
    
    def _should_save_cache(self) -> bool:
        """Determine if cache should be saved based on filter parameters."""
        return (
            self.operator is None
            and self.technology is None
            and self.bounding_box is None
            and self.frequency_band is None
            and (
                self.frequency_range == [0, np.inf]
                or np.array_equal(self.frequency_range, [0, np.inf])
            )
        )
    
    def _query_sparql_batches(self, s) -> tuple:
        """Query SPARQL endpoint in batches and combine results."""
        offset = 0
        limit = 10000
        raw_antennas_list, raw_infos_list = [], []
        
        pbar_sparql = tqdm(desc="Querying SPARQL batches", unit=" batch")
        while True:
            try:
                antennas_batch = s.get_antenna_locations_extended(limit=limit, offset=offset)
                infos_batch = s.get_antenna_extended(limit=limit, offset=offset)
            except Exception as e:
                pbar_sparql.close()
                print(f"Error during SPARQL query (offset {offset}): {e}")
                break
            
            if not antennas_batch:
                break
            
            raw_antennas_list.extend(antennas_batch)
            raw_infos_list.extend(infos_batch[:len(antennas_batch)])
            offset += limit
            pbar_sparql.update(1)
        
        pbar_sparql.close()
        return raw_antennas_list, raw_infos_list
    
    def _combine_raw_dataframes(self, raw_antennas_list: list, raw_infos_list: list) -> pd.DataFrame:
        """Combine raw antenna locations and info into single DataFrame."""
        print("Combining raw antenna location and info data...")
        raw_antennas_df = pd.DataFrame([a.__dict__ for a in raw_antennas_list])
        raw_infos_df = pd.DataFrame([i.__dict__ for i in raw_infos_list])
        
        combined_df = raw_antennas_df.copy()
        for col in raw_infos_df.columns:
            if col not in combined_df.columns or combined_df[col].isnull().all():
                if col in raw_infos_df.columns:
                    combined_df[col] = raw_infos_df[col]
        
        return combined_df
    
    @staticmethod
    def _extract_coords_from_wkt(wkt_str: str) -> tuple:
        """Extract (lon, lat) from WKT POINT string. Returns (None, None) on parse error."""
        if not isinstance(wkt_str, str) or not wkt_str.startswith('POINT'):
            return None, None
        try:
            parts = wkt_str.replace('POINT(', '').replace(')', '').strip().split()
            if len(parts) >= 2:
                return float(parts[0]), float(parts[1])
        except (ValueError, IndexError):
            pass
        return None, None
    
    def _apply_coordinate_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract latitude and longitude from WKT geometry column."""
        if "wkt" in df.columns:
            coords = df["wkt"].apply(self._extract_coords_from_wkt)
            df["Longitude"] = coords.apply(lambda x: x[0] if x else None)
            df["Latitude"] = coords.apply(lambda x: x[1] if x else None)
        return df
    
    def _apply_date_filter(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter antennas by approval date. Keeps records with approvaldate <= self.date."""
        if 'approvaldate' not in df.columns or self.date is None:
            return df
        df['approvaldate'] = pd.to_datetime(df['approvaldate'], format='ISO8601', errors='coerce', utc=True)
        cutoff_date = pd.to_datetime(self.date, format='ISO8601', errors='coerce', utc=True)
        return df[df['approvaldate'] <= cutoff_date].reset_index(drop=True)
    
    def _apply_site_grouping(self, df: pd.DataFrame) -> pd.DataFrame:
        """Group antennas by site and keep only most recent approval date."""
        if 'site' not in df.columns or 'wkt' not in df.columns:
            print("Warning: Cannot perform duplicate removal as 'site' or 'wkt' column is missing.")
            return df
        
        def get_site_label(site_dict):
            return f"SITE({site_dict['label']})" if isinstance(site_dict, dict) and 'label' in site_dict else None
        
        df["SiteCode"] = df["site"].apply(get_site_label)
        latest_dates = df.groupby('SiteCode')['approvaldate'].transform('max')
        original_count = len(df)
        df = df[df['approvaldate'] == latest_dates]
        new_count = len(df)
        print(f"Filtered antennas by site. Removed {original_count - new_count} older entries.")
        return df
    
    def _fetch_patterns_and_dimensions(self, df: pd.DataFrame) -> tuple:
        """Fetch antenna patterns and physical dimensions in parallel."""
        if df.empty or 'id' not in df.columns:
            print("Skipping dimension/pattern fetching as data is empty or lacks 'id' column.")
            return {}, []
        
        print("Fetching physical antenna dimensions and patterns...")
        extractor = AntennaPatternExtractor(self.sparql_url)
        unique_antenna_uris = df['id'].dropna().unique()
        print(f"Found {len(unique_antenna_uris)} unique antenna URIs.")
        
        temp_pattern_results = {}
        dimensions_data = []
        
        if self.max_workers > 1:
            print(f"(parallel with {self.max_workers} workers)")
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {executor.submit(extractor.extract_pattern, uri): uri for uri in unique_antenna_uris}
                for future in tqdm(as_completed(futures), total=len(futures), desc="Extracting patterns", unit=" antenna"):
                    uri = futures[future]
                    try:
                        _, p_height, p_width, max_gain, mech_tilt, el_tilt, gain2d, az_deg, el_deg, vert_bw, hor_bw = future.result()
                        temp_pattern_results[uri] = (gain2d, az_deg, el_deg)
                        if p_height is not None and p_width is not None and max_gain is not None and el_tilt is not None:
                            dimensions_data.append({
                                'id': uri, 'physical_height': p_height, 'physical_width': p_width,
                                'max_gain': max_gain, 'mechanical_tilt': mech_tilt, 'electrical_tilt': el_tilt,
                                'vertical_beamwidth': vert_bw, 'horizontal_beamwidth': hor_bw
                            })
                    except Exception as exc:
                        print(f'Antenna URI {uri} generated an exception: {exc}')
                        temp_pattern_results[uri] = (None, None, None)
        else:
            print("(sequential)")
            for uri in unique_antenna_uris:
                try:
                    _, p_height, p_width, max_gain, mech_tilt, el_tilt, gain2d, az_deg, el_deg, vert_bw, hor_bw = extractor.extract_pattern(uri)
                    temp_pattern_results[uri] = (gain2d, az_deg, el_deg)
                    if p_height is not None and p_width is not None and max_gain is not None and el_tilt is not None:
                        dimensions_data.append({
                            'id': uri, 'physical_height': p_height, 'physical_width': p_width,
                            'max_gain': max_gain, 'mechanical_tilt': mech_tilt, 'electrical_tilt': el_tilt,
                            'vertical_beamwidth': vert_bw, 'horizontal_beamwidth': hor_bw
                        })
                except Exception as exc:
                    print(f'Antenna URI {uri} generated an exception: {exc}')
                    temp_pattern_results[uri] = (None, None, None)
        
        print(f"Successfully processed {len(temp_pattern_results)} URIs.")
        return temp_pattern_results, dimensions_data
    
    def _merge_dimensions(self, df: pd.DataFrame, dimensions_data: list) -> pd.DataFrame:
        """Merge dimension data into antenna DataFrame."""
        if dimensions_data:
            dimensions_df = pd.DataFrame(dimensions_data)
            df = pd.merge(df, dimensions_df, on='id', how='left')
        else:
            for col in ['physical_height', 'physical_width', 'max_gain', 'mechanical_tilt',
                       'electrical_tilt', 'vertical_beamwidth', 'horizontal_beamwidth']:
                df[col] = np.nan
        return df
    
    def _populate_patterns_cache(self, temp_pattern_results: dict):
        """Populate self.patterns from temporary results."""
        self.patterns = {}
        if self.antennas.empty or 'id' not in self.antennas.columns or 'label' not in self.antennas.columns:
            print("Skipping pattern cache population (no antennas or missing columns).")
            return
        
        processed_labels = set()
        for _, row in self.antennas.iterrows():
            uri = row['id']
            label = row['label']
            
            if pd.isna(uri) or pd.isna(label):
                continue
            
            pattern_data = temp_pattern_results.get(uri)
            if pattern_data and len(pattern_data) == 3 and isinstance(pattern_data[0], np.ndarray):
                antenna_label = f"ANT({str(label).replace(' ', '_').strip(' ._-')})"
                pattern_key = sanitize_label(f"{row['SiteCode']}_{antenna_label}")
                
                if pattern_key not in processed_labels:
                    self.patterns[pattern_key] = pattern_data[0]
                    processed_labels.add(pattern_key)
        
        print(f"Stored {len(self.patterns)} patterns in cache.")
    
    def _prepare_output_dataframe(self, providers_dict: dict, technologies_dict: dict) -> pd.DataFrame:
        """Prepare final output DataFrame with correct column names and formats."""
        df = self.antennas.copy()
        
        # Extract coords if not already done
        if "Latitude" not in df.columns and "wkt" in df.columns:
            df = self._apply_coordinate_filters(df)
        
        # Populate columns from nested dicts
        def safe_get_dict_value(item, keys, default=None):
            """Safely extract nested dict value."""
            if not isinstance(item, dict):
                return default
            for key in keys:
                item = item.get(key, {})
                if not isinstance(item, dict):
                    return item if item else default
            return default
        
        # SiteCode and AntennaLabel
        if "SiteCode" not in df.columns and "site" in df.columns:
            df["SiteCode"] = df["site"].apply(lambda x: safe_get_dict_value(x, ["label"]))
        
        if "AntennaLabel" not in df.columns and "label" in df.columns:
            df["AntennaLabel"] = "ANT(" + df["label"].astype(str).str.replace(" ", "_").str.strip(" .-_") + ")"
        
        # FileNumber from dossier
        if "FileNumber" not in df.columns and "dossier" in df.columns:
            df["FileNumber"] = df["dossier"].apply(lambda x: safe_get_dict_value(x, ["label"]))
        
        # Operator
        if "Operator" not in df.columns:
            if self.operator:
                df["Operator"] = self.operator
            elif "operator" in df.columns:
                df["Operator"] = df["operator"].apply(lambda x: safe_get_dict_value(x, ["label"]))
        
        # Technology
        if "Technology" not in df.columns and "technology" in df.columns:
            df["Technology"] = df["technology"].apply(lambda x: technologies_dict.get(x))
        
        # Rename columns to final output format
        rename_map = {
            'height': 'CenterHeight', 'physical_height': 'Height', 'physical_width': 'Width',
            'max_gain': 'Gain', 'electrical_tilt': 'Electrical_Tilt', 'mechanical_tilt': 'Mechanical_Tilt',
            'power': 'Power', 'frequency': 'Frequency', 'azimuth': 'Azimuth',
            'vertical_beamwidth': 'Vertical_Beamwidth', 'horizontal_beamwidth': 'Horizontal_Beamwidth'
        }
        actual_renames = {k: v for k, v in rename_map.items() if k in df.columns}
        df.rename(columns=actual_renames, inplace=True)
        
        return df

    # === MAIN PROCESSING METHOD ===
    def extract_antennas(self, filename=None, config=None):
        """
        Extracts antenna data, filters it, fetches physical dimensions and patterns,
        and saves the combined data to output_csv. Patterns are stored in self.patterns.
        """
        save_cache = self._should_save_cache()
        SparqlService = import_sparql_service_from_plugin()
        
        # === STEP 1: CACHE CHECK ===
        combined_df = self._load_cache()
        
        # === STEP 2: SPARQL QUERY (if cache miss) ===
        if combined_df is None:
            print("Querying SPARQL for raw antenna data...")
            s = SparqlService(self.sparql_url)
            raw_antennas_list, raw_infos_list = self._query_sparql_batches(s)
            
            print(f"Total raw antennas fetched: {len(raw_antennas_list)}")
            if not raw_antennas_list:
                print("Warning: No raw antennas were fetched from SPARQL.")
                self.antennas = pd.DataFrame()
                self.patterns = {}
                return
            
            combined_df = self._combine_raw_dataframes(raw_antennas_list, raw_infos_list)
        
        if combined_df is None or combined_df.empty:
            print("No antenna data available. Exiting.")
            self.antennas = pd.DataFrame()
            self.patterns = {}
            return
        
        # === STEP 3: APPLY LOCAL FILTERING ===
        s_filter = SparqlService(self.sparql_url)
        providers_dict = {p.id: p.label for p in s_filter.get_operators()}
        technologies_dict = {t.id: t.label for t in s_filter.get_technologies()}
        
        # Apply basic transformations
        filtered_df = combined_df.copy()
        filtered_df = self._apply_date_filter(filtered_df)
        filtered_df = self._apply_site_grouping(filtered_df)
        # apply other filters now also to reduce number of antennas for pattern fetching
        # first apply coordinate extraction if needed
        filtered_df = self._apply_coordinate_filters(filtered_df)
        filtered_df = apply_filters(
            filtered_df, operator=self.operator, technology=self.technology,
            bounding_box=self.bounding_box, frequency_range=self.frequency_range,
            frequency_band=self.frequency_band) 
        
        # Populate operator labels from dict
        if "operator" in filtered_df.columns:
            def populate_operator_label(op_dict):
                if isinstance(op_dict, dict) and 'id' in op_dict:
                    op_dict['label'] = providers_dict.get(op_dict['id'])
                return op_dict
            filtered_df['operator'] = filtered_df['operator'].apply(populate_operator_label)
        
        # === STEP 4: FETCH PHYSICAL DIMENSIONS & PATTERNS ===
        if save_cache and self.pattern_cache_file and os.path.exists(self.pattern_cache_file):
            print("Attempting to load patterns from cache...")
            cached_patterns = self._load_pattern_cache()
            if cached_patterns:
                self.patterns = cached_patterns
                temp_pattern_results = {}
                dimensions_data = []
            else:
                temp_pattern_results, dimensions_data = self._fetch_patterns_and_dimensions(filtered_df)
        else:
            temp_pattern_results, dimensions_data = self._fetch_patterns_and_dimensions(filtered_df)
        
        filtered_df = self._merge_dimensions(filtered_df, dimensions_data)
        
        # === STEP 5: STORE FINAL DATA & POPULATE PATTERNS ===
        self.antennas = filtered_df.reset_index(drop=True)
        self.count = len(self.antennas)
        print(f"Total antennas after filtering: {self.count}")
        
        if not self.patterns:  # Only populate if not loaded from cache
            self._populate_patterns_cache(temp_pattern_results)
        
        # === STEP 6: PREPARE OUTPUT & APPLY FINAL FILTERS ===
        if not self.antennas.empty:
            print(f"Preparing {self.count} antennas for output...")
            
            # Prepare dataframe with proper columns
            self.antennas = self._prepare_output_dataframe(providers_dict, technologies_dict)
            
            # Apply create_output_df which handles final filtering, deduplication, etc.
            filter_args = {
                "operator": self.operator, "technology": self.technology,
                "bounding_box": self.bounding_box, "frequency_range": self.frequency_range,
                "frequency_band": self.frequency_band, "date": self.date
            }
            self.antennas = create_output_df(self.antennas, config, filter_args=filter_args)
            
            # Save output
            out_csv = os.path.join(self.output_folder, f"{self.file_identifier}_antennas.csv") if self.output_folder else None
            if out_csv:
                try:
                    self.antennas.to_csv(out_csv, index=False)
                    self.filter_patterns()
                    print(f"Saved output CSV to {out_csv}")
                except Exception as e:
                    raise RuntimeError(f"Failed to save output CSV: {e}")
                
                # Save pattern cache if using standard parameters
                if save_cache and self.pattern_cache_file:
                    self._save_pattern_cache()
                
                # Save antenna cache if using standard parameters
                if save_cache and self.raw_antenna_cache_file:
                    try:
                        os.makedirs(os.path.dirname(self.raw_antenna_cache_file), exist_ok=True)
                        pd.to_pickle(self.antennas, self.raw_antenna_cache_file)
                        print(f"Saved cache to {self.raw_antenna_cache_file}")
                    except Exception as e:
                        print(f"Warning: failed to save cache: {e}")
                
                return self.antennas
        else:
            print("No antennas remaining after filtering.")


    def filter_patterns(self):
        # based on the names and sitecodes in self.antennas, filter self.patterns
        filtered_patterns = {}
        for _, row in self.antennas.iterrows():
            sitecode = row['SiteCode']
            name = row['AntennaLabel']
            # Handle combined AntennaLabels (e.g., "ANT(a)/ANT(b)")
            antenna_parts = str(name).split('/')
            first_part = antenna_parts[0].strip()
            label = f"{sitecode}_{name}"
            sanitized = sanitize_label(label)
            first_label = f"{sitecode}_{first_part}"
            first_sanitized = sanitize_label(first_label)
            if first_sanitized in self.patterns:
                filtered_patterns[sanitized] = self.patterns[first_sanitized]
        self.patterns = filtered_patterns
        if len(self.antennas) != len(self.patterns):
            print(
                f"Warning: Mismatch in counts - antennas: {len(self.antennas)}, "
                f"patterns: {len(self.patterns)}"
            )
        return


    # === PATTERN EXPORT METHOD ===
    def extract_patterns(self, filename=None):  # max_workers unused but kept for signature consistency
        """Saves the antenna patterns (fetched during extract_antennas) to a .mat file."""
        if self.patterns is None:
            print("Warning: Patterns not extracted yet. Run extract_antennas() first.")
            return None

        if not self.patterns:
            print("No patterns were successfully extracted or stored. Cannot save .mat file.")
            return None
        # save to .mat
        if not filename:
            mat_file_path = os.path.join(self.output_folder, f"{self.file_identifier}_patterns.mat")
        else: 
            if ".mat" not in filename: 
                raise ValueError("filename must be .mat")
            mat_file_path = filename   
        try:
            # Need to save the dictionary structure correctly
            # savemat expects a dictionary where keys are variable names and values are arrays/data
            # Our self.patterns is {label: {pattern_data_dict}}
            # We need to save self.patterns directly, or restructure it if savemat has issues with nested dicts.
            # Let's try saving directly first.
            savemat(mat_file_path, self.patterns, do_compression=True)
            print(f"Saved {len(self.patterns)} patterns from cache to {mat_file_path}")
            return mat_file_path
        except TypeError as e:
            print(f"Error saving patterns to {mat_file_path}: {e}")
            print("This might be due to the nested dictionary structure. Attempting restructure...")
            # Attempt restructuring: Create a flat dictionary suitable for savemat
            mat_dict = {}
            for label, pattern_dict in self.patterns.items():
                # Since label is already sanitized, use it directly
                valid_label = label
                for key, value in pattern_dict.items():
                    mat_dict[f"{valid_label}_{key}"] = value
            try:
                savemat(mat_file_path, mat_dict, do_compression=True)
                print(f"Saved {len(self.patterns)} patterns (restructured) to {mat_file_path}")
                return mat_file_path
            except Exception as e2:
                print(f"Error saving restructured patterns to {mat_file_path}: {e2}")
                return None
        except Exception as e:
            print(f"General error saving patterns to {mat_file_path}: {e}")
            return None

        
if __name__ == "__main__":
    Bounding_Box =  [3.695, 3.766, 51.005, 51.091]
    # antenne_cache = r"C:\Users\mattleem\Downloads/raw_antenna_data.pkl"
    folder = os.path.dirname(os.path.realpath(__file__))
    
    antenne_cache = os.path.join(folder , "raw_antenna_data.pkl" )
    patterns_file = os.path.join(folder , "patterns.mat" )

    output_folder = "output/Belgium/flanders"
    filter_args = {
        "operator": None,
        "technology": None,
        "bounding_box": None,
        "frequency_range": [0, np.inf],
        "date": None,
    }

    BS_class = BaseStations(
                 output_folder= output_folder, 
                 raw_antenna_cache_file=antenne_cache, 
                 pattern_file= patterns_file,
                 max_workers=8, 
                 **filter_args
                 )
    BS_class.extract_antennas()
    
    # save in this folder (where code is located)
    # BS_class.extract_patterns(save_dir= folder)