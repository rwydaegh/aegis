
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from pyproj import Transformer

logger = logging.getLogger(__name__)

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


base_url = "https://www.senderkataster.at/"

current_folder = os.path.dirname(os.path.abspath(__file__))


def get_sites(session):
    """Fetch all base station sites from senderkataster.at API."""
    site_url = "https://www.senderkataster.at/backend/data/getconfig.php"
    response = session.get(site_url)
    response.raise_for_status()
    data = response.json()
    return data["data"]


def get_antennas(session, sites):
    """Fetch antenna details for all sites and return DataFrame.
    
    Note: is_sharing is kept for future implementation but not included in final output.
    """
    detail_url = "https://www.senderkataster.at/backend/data/getdetails.php"
    antennas = pd.DataFrame()
    transformer = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
    
    for site in _tqdm(sites, desc="Fetching antenna details"):
        params = {
            "layer": site["layer"],
            "sender_id": site["sender_id"]
        }
        if params["layer"] != 1:
            continue
        
        response = session.get(detail_url, params=params)
        response.raise_for_status()
        try:
            data = response.json()
        except Exception:
            logger.debug("Empty or invalid JSON for site %s, skipping", site.get("sender_id"))
            continue
        if not data:
            continue
        x = float(site["x"])
        y = float(site["y"])
        # convert to lat/lon
        lon, lat = transformer.transform(x, y)
        
        for antenna in data:
            technologies = antenna.get("system", "").split("/")  # API returns "/" as separator
            power = antenna.get("leistung", np.nan)
            antenna_structure = antenna.get("struktur", "")
            is_sharing = antenna.get("sharing", False)
            # TODO: Implement check with OpenCellID MNC to identify operators
            # Austria (country MCC: 232): A1: 01, Magenta(T-Mobile): 03, Three(Hutchison): 05, Tele.ring (T-Mobile): 07
            
            for tech in technologies:
                antenna_row = {
                    "SiteCode": f"SITE({site['sender_id']})",
                    "AntennaLabel": f"ANT({site['sender_id']}_{antenna_structure}_{tech})",
                    "Operator": None,  # Not available in this API
                    "Technology": tech,
                    "Latitude": lat,
                    "Longitude": lon,
                    "CenterHeight": np.nan,  # Not available in this API
                    "Power": power,
                    "Frequency": np.nan,  # Not available in this API yet
                    "FrequencyBand": np.nan,  # Not available in this API yet
                    "Electrical_Tilt": np.nan,  # Not available in this API
                    "Mechanical_Tilt": np.nan,  # Not available in this API
                    "Azimuth": np.nan,  # Not available in this API
                    "Gain": np.nan,  # Not available in this API
                    "Horizontal_Beamwidth": np.nan,  # Not available in this API
                    "Vertical_Beamwidth": np.nan,  # Not available in this API
                    "is_sharing": is_sharing  # Keep for future implementation
                }
                
                if antennas.empty:
                    antennas = pd.DataFrame([antenna_row])
                else:
                    antennas = pd.concat([antennas, pd.DataFrame([antenna_row])], ignore_index=True)
    
    return antennas


class BaseStations:
    """Austria base station extractor using senderkataster.at API."""

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
        output_folder: str = "output/austria/",
        max_workers: int = 1,
        file_identifier=None,
    ):
        """Initialize BaseStations extractor with parameters for filtering and output."""
        os.makedirs(output_folder, exist_ok=True)

        if frequency_range is None:
            frequency_range = [0, np.inf]
        if date is None:
            date = datetime.now(timezone.utc)

        self.operator = operator
        self.technology = technology
        self.bounding_box = bounding_box
        self.frequency_range = frequency_range
        self.frequency_band = frequency_band
        self.date = format_date_only(date)
        self.raw_antenna_cache_file = raw_antenna_cache_file or os.path.join(
            current_folder, "all.pkl"
        )
        self.pattern_file = pattern_file
        self.output_folder = output_folder
        self.max_workers = max(1, int(max_workers))

        self.antennas = pd.DataFrame()
        self.count = 0

        # Create unique file identifier if not provided
        if file_identifier is None:
            self.file_identifier = create_unique_file_identifier(self)
        else:
            self.file_identifier = file_identifier

    def extract_antennas(self, config=None):
        """Extract antennas from senderkataster.at API and return standardized output.
        
        Notes:
        - If all filter inputs are standard (None, default range, etc.), antennas
          are auto-saved to raw_antenna_cache_file for later reuse.
        - Uses parallel processing with self.max_workers.
        - Removes is_sharing column before returning final output.
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
            except Exception as e:
                print(f"Warning: failed to load cache {self.raw_antenna_cache_file}: {e}")

        # If no cache or cache load failed, extract
        if self.antennas is None or self.antennas.empty:
            session = create_session()
            session.headers.update({"Referer": "https://www.senderkataster.at/"})
            sites = get_sites(session)
            self.antennas = get_antennas(session, sites)
            session.close()

            if self.antennas.empty:
                print("Result is empty")
                return pd.DataFrame()

            self.count = len(self.antennas)

        # Save output CSV into output_folder/{file_identifier}_antennas.csv
        out_csv = (
            os.path.join(self.output_folder, f"{self.file_identifier}_antennas.csv")
            if self.output_folder
            else None
        )

        if out_csv:
            try:
                # Remove is_sharing column before creating output
                df = self.antennas.copy()
                if "is_sharing" in df.columns:
                    df = df.drop(columns=["is_sharing"])

                # Apply data estimation if enabled in config
                filter_args = {
                    "operator": self.operator,
                    "technology": self.technology,
                    "bounding_box": self.bounding_box,
                    "frequency_range": self.frequency_range,
                    "frequency_band": self.frequency_band,
                    "date": self.date,
                }
                self.antennas = create_output_df(df, config, filter_args=filter_args).copy()
                self.antennas.to_csv(out_csv, index=False)

                print(f"Saved output CSV to {out_csv}")
            except Exception as e:
                print(f"Warning: failed to save output CSV: {e}")

        # Save cache if requested and using standard parameters
        if save_cache and self.raw_antenna_cache_file:
            try:
                os.makedirs(os.path.dirname(self.raw_antenna_cache_file) or '.', exist_ok=True)
                pd.to_pickle(self.antennas, self.raw_antenna_cache_file)
                print(f"Saved raw antenna cache to {self.raw_antenna_cache_file}")
            except Exception as e:
                print(f"Warning: failed to save cache: {e}")

        return self.antennas

    def extract_patterns(self, *args, **kwargs):
        """Austria extractor does not support antenna pattern reconstruction.

        This method is provided for API compatibility and will return None.
        """
        print("Pattern extraction is not supported for Austria (no pattern data available).")
        return None


if __name__ == "__main__":
    BS = BaseStations()
    BS.extract_antennas()