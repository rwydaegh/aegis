#!/usr/bin/env python3
"""
Download all OpenCellID cells in a bounding box and save to CSV.

Input bbox is: [min_lon, max_lon, min_lat, max_lat]
OpenCellID expects: BBOX=latmin,lonmin,latmax,lonmax
"""

import argparse
import csv
import math
import sys
import os
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import timezone, datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

import requests

from ..utils import create_unique_file_identifier, create_output_df


BASE_URL = "https://opencellid.org"
MAX_LIMIT = 50  # per API docs, max allowed for getInArea
MAX_BBOX_AREA_SQM = 4_000_000  # 4,000,000 m² limit from API


# ─────────────────────────────────────────────────────────────
# API key / BBOX utilities
# ─────────────────────────────────────────────────────────────

def read_api_key(path) -> str:
    """
    Read the API key from a text file.
    The file should contain the key as plain text (optionally with a trailing newline).
    """
    if not isinstance(path, Path):
        path = Path(path)
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        print(f"ERROR: API key file not found: {path}", file=sys.stderr)
        sys.exit(1)


def bbox_to_param(bbox):
    """
    Convert bbox = [min_lon, max_lon, min_lat, max_lat]
    to OpenCellID BBOX format: latmin,lonmin,latmax,lonmax
    """
    min_lon, max_lon, min_lat, max_lat = bbox
    latmin = min_lat
    lonmin = min_lon
    latmax = max_lat
    lonmax = max_lon
    return f"{latmin},{lonmin},{latmax},{lonmax}"


def bbox_area_sqm(bbox) -> float:
    """
    Approximate area of bbox in square meters.

    bbox = [min_lon, max_lon, min_lat, max_lat]
    We approximate:
      - 1 deg latitude ≈ 111,320 m (fairly constant)
      - 1 deg longitude ≈ 111,320 * cos(latitude) m (depends on latitude)
    """
    min_lon, max_lon, min_lat, max_lat = bbox

    # Center latitude for lon scaling
    center_lat = 0.5 * (min_lat + max_lat)

    # Degrees
    d_lat = max_lat - min_lat
    d_lon = max_lon - min_lon

    # Meters per degree
    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * math.cos(math.radians(center_lat))

    height_m = abs(d_lat) * m_per_deg_lat
    width_m = abs(d_lon) * m_per_deg_lon

    return height_m * width_m


def split_bbox_if_needed(bbox, max_area_sqm=MAX_BBOX_AREA_SQM):
    """
    If bbox area <= max_area_sqm, return [bbox].
    Otherwise, split into smaller tiles (grid) so each tile is below the limit.

    Returns a list of bboxes: [[min_lon, max_lon, min_lat, max_lat], ...]
    """
    area = bbox_area_sqm(bbox)
    if area <= max_area_sqm:
        return [bbox]

    min_lon, max_lon, min_lat, max_lat = bbox

    # Approximate tile size (square) in meters
    tile_edge_m = math.sqrt(max_area_sqm)

    # Compute total width and height in meters
    center_lat = 0.5 * (min_lat + max_lat)
    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * math.cos(math.radians(center_lat))

    total_height_m = abs(max_lat - min_lat) * m_per_deg_lat
    total_width_m = abs(max_lon - min_lon) * m_per_deg_lon

    # Number of tiles in each direction (ceil)
    n_lat = max(1, math.ceil(total_height_m / tile_edge_m))
    n_lon = max(1, math.ceil(total_width_m / tile_edge_m))

    # Step in degrees
    step_lat = (max_lat - min_lat) / n_lat
    step_lon = (max_lon - min_lon) / n_lon

    sub_bboxes = []
    for i in range(n_lon):
        sub_min_lon = min_lon + i * step_lon
        sub_max_lon = min_lon + (i + 1) * step_lon
        for j in range(n_lat):
            sub_min_lat = min_lat + j * step_lat
            sub_max_lat = min_lat + (j + 1) * step_lat
            sub = [sub_min_lon, sub_max_lon, sub_min_lat, sub_max_lat]

            # Just in case: re-check area and skip if zero
            if bbox_area_sqm(sub) <= 0:
                continue

            sub_bboxes.append(sub)

    return sub_bboxes


# ─────────────────────────────────────────────────────────────
# OpenCellID API calls
# ─────────────────────────────────────────────────────────────

def get_cell_count(api_key: str, bbox_param: str) -> int:
    """
    Use /cell/getInAreaSize to get the number of cells in the specified area.
    """
    url = f"{BASE_URL}/cell/getInAreaSize"
    params = {
        "key": api_key,
        "BBOX": bbox_param,
        "format": "json",
    }
    resp = requests.get(url, params=params, timeout=30)
    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        print(f"ERROR: getInAreaSize failed: {e}\nResponse: {resp.text}", file=sys.stderr)
        sys.exit(1)

    data = resp.json()
    if "error" in data:
        print(f"ERROR: getInAreaSize failed: {data['error']}", file=sys.stderr)
        sys.exit(1)

    return int(data.get("count", 0))


def fetch_cells_one_bbox(api_key: str,
                         bbox,
                         csv_writer,
                         header_written: bool) -> bool:
    """
    Fetch all cells in *one* bbox and append them to csv_writer.

    Returns:
      header_written (bool): updated header_written flag.
    """
    bbox_param = bbox_to_param(bbox)
    area = bbox_area_sqm(bbox)
    print(f"  BBOX {bbox_param} (area ≈ {area:,.0f} m²)")

    total = get_cell_count(api_key, bbox_param)
    print(f"    Found {total} cells in this sub-area.")

    if total == 0:
        return header_written

    url = f"{BASE_URL}/cell/getInArea"

    for offset in range(0, total, MAX_LIMIT):
        limit = min(MAX_LIMIT, total - offset)
        params = {
            "key": api_key,
            "BBOX": bbox_param,
            "format": "csv",
            "limit": str(limit),
            "offset": str(offset),
        }

        print(f"    Requesting cells {offset}–{offset + limit - 1} ...")
        resp = requests.get(url, params=params, timeout=60)

        # If we still hit "BBOX too big" for some reason, warn and skip this tile
        if resp.status_code == 400 and "BBOX too big" in resp.text:
            print("    WARNING: API says BBOX too big even after splitting. Skipping this sub-bbox.")
            continue

        try:
            resp.raise_for_status()
        except requests.HTTPError as e:
            print(f"ERROR: getInArea failed at offset {offset}: {e}\nResponse: {resp.text}", file=sys.stderr)
            break

        text = resp.text.strip()
        if not text:
            print(f"    Warning: empty response at offset {offset}", file=sys.stderr)
            continue

        lines = text.splitlines()
        if not lines:
            print(f"    Warning: no CSV lines at offset {offset}", file=sys.stderr)
            continue

        reader = csv.reader(lines)
        page_header = next(reader, None)

        if page_header is None:
            print(f"    Warning: missing header at offset {offset}", file=sys.stderr)
            continue

        if not header_written:
            csv_writer.writerow(page_header)
            header_written = True

        for row in reader:
            csv_writer.writerow(row)

    return header_written


def fetch_cells_multiple_bboxes_to_csv(api_key: str,
                                       bboxes,
                                       output_csv):
    """
    Fetch cells for all bboxes in `bboxes` and write them into a single CSV.
    """
    if not isinstance(output_csv, Path):
        output_csv = Path(output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Total sub-bboxes to query: {len(bboxes)}")

    header_written = False
    with output_csv.open("w", newline="", encoding="utf-8") as f_out:
        csv_writer = csv.writer(f_out)

        for idx, bbox in enumerate(bboxes, start=1):
            print(f"\nProcessing sub-bbox {idx}/{len(bboxes)} ...")
            header_written = fetch_cells_one_bbox(
                api_key=api_key,
                bbox=bbox,
                csv_writer=csv_writer,
                header_written=header_written,
            )

    print(f"\nDone. CSV saved to: {output_csv}")
    print("Note: cells near tile borders might appear twice. "
          "If needed, you can post-process the CSV to remove duplicates.")


# ─────────────────────────────────────────────────────────────
# BaseStations class - unified interface
# ─────────────────────────────────────────────────────────────

class BaseStations:
    """
    OpenCellID-based base station extractor.
    Uses the OpenCellID API to fetch cell tower data for a given bounding box.
    """
    
    def __init__(self,
                 operator=None,
                 technology=None,
                 bounding_box=None,
                 frequency_range=[0, np.inf],
                 frequency_band=None,
                 date=datetime.now(timezone.utc),
                 raw_antenna_cache_file=None,
                 pattern_file=None,
                 output_folder=None,
                 max_workers=1,
                 file_identifier=None,
                 api_key_path="opencellid_api_key.txt"):
        """
        Initialize BaseStations for OpenCellID data extraction.
        
        Args:
            operator: Filter by operator name (not supported by OpenCellID, stored for API compatibility)
            technology: Filter by technology type (not supported by OpenCellID, stored for API compatibility)
            bounding_box: [min_lon, max_lon, min_lat, max_lat] for data extraction
            frequency_range: [min_hz, max_hz] for filtering (not supported by OpenCellID)
            frequency_band: Alternative frequency filter (not supported by OpenCellID)
            date: Date filter (not supported by OpenCellID, stored for compatibility)
            raw_antenna_cache_file: Path to cache raw SPARQL results
            pattern_file: Pattern output file (not applicable for OpenCellID)
            output_folder: Directory to save output CSV
            max_workers: Number of parallel workers for bbox fetching
            file_identifier: Unique file identifier (auto-generated if None)
            api_key_path: Path to OpenCellID API key file (default: "opencellid_api_key.txt")
        """
        self.operator = operator
        self.technology = technology
        self.bounding_box = bounding_box
        self.frequency_range = frequency_range
        self.frequency_band = frequency_band
        self.date = date
        self.pattern_file = pattern_file
        self.max_workers = max_workers
        self.api_key_path = api_key_path
        
        # Set default output folder
        if output_folder is None:
            output_folder = os.path.join(os.path.dirname(__file__), "output")
        self.output_folder = output_folder
        
        
        # Create file identifier
        if file_identifier is None:
            file_identifier = create_unique_file_identifier(self)
            
        self.file_identifier = file_identifier
        
        # Initialize antennas DataFrame
        self.antennas = pd.DataFrame()
        
        # Read API key
        if os.path.exists(self.api_key_path):
            self.api_key = read_api_key(self.api_key_path)
        else:
            raise FileNotFoundError(f"WARNING: API key file not found at {self.api_key_path}")
    
    def extract_antennas(self, config=None):
        """
        Main extraction workflow:
        1. Check cache for raw data
        2. If not cached, fetch from OpenCellID API
        3. Apply filters
        4. Standardize output columns
        5. Save to CSV
        """
        if self.bounding_box is None:
            print("ERROR: bounding_box is required for extraction")
            return
        
        if self.api_key is None:
            print("ERROR: API key not available")
            return
        
        # Split bounding box if needed
        subboxes = split_bbox_if_needed(self.bounding_box, MAX_BBOX_AREA_SQM)
        
        # Fetch cells with parallel processing
        if self.max_workers > 1:
            print(f"(parallel with {self.max_workers} workers)")
            all_results = []
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {executor.submit(self._fetch_cells_from_bbox, bbox): bbox for bbox in subboxes}
                for future in tqdm(as_completed(futures), total=len(futures), desc="Fetching antennas"):
                    try:
                        result = future.result()
                        if result is not None and len(result) > 0:
                            all_results.append(result)
                    except Exception as e:
                        bbox = futures[future]
                        print(f"Error fetching bbox {bbox}: {e}")
            if all_results:
                self.antennas = pd.concat(all_results, ignore_index=True)
            else:
                self.antennas = pd.DataFrame()
        else:
            # Sequential processing
            print("(sequential)")
            self.antennas = self._fetch_cells_sequential(subboxes)
        
        # Remove duplicates
        if len(self.antennas) > 0:
            self.antennas = self.antennas.drop_duplicates()
        
        # Apply filters and save
        self._apply_filters()
        self._standardize_output_columns()
        filter_args = {"operator": self.operator, "technology": self.technology, "bounding_box": self.bounding_box, "frequency_range": self.frequency_range, "frequency_band": self.frequency_band, "date": self.date}
        self.antennas = create_output_df(config = config, filter_args = filter_args)
        out_csv = (
            os.path.join(self.output_folder, f"{self.file_identifier}_antennas.csv")
            if self.output_folder
            else None
        )
        if out_csv:
            self.antennas.to_csv(out_csv, index = False)
        
    def _fetch_cells_from_bbox(self, bbox):
        """
        Fetch cells for a single bbox and return as DataFrame.
        Used by ThreadPoolExecutor.
        """
        bbox_param = bbox_to_param(bbox)
        area = bbox_area_sqm(bbox)
        
        total = get_cell_count(self.api_key, bbox_param)
        
        if total == 0:
            return pd.DataFrame()
        
        rows = []
        url = f"{BASE_URL}/cell/getInArea"
        
        for offset in range(0, total, MAX_LIMIT):
            limit = min(MAX_LIMIT, total - offset)
            params = {
                "key": self.api_key,
                "BBOX": bbox_param,
                "format": "csv",
                "limit": str(limit),
                "offset": str(offset),
            }
            
            try:
                resp = requests.get(url, params=params, timeout=60)
                
                if resp.status_code == 400 and "BBOX too big" in resp.text:
                    continue
                
                resp.raise_for_status()
                
                text = resp.text.strip()
                if not text:
                    continue
                
                lines = text.splitlines()
                if not lines:
                    continue
                
                reader = csv.reader(lines)
                header = next(reader, None)
                
                if header is None:
                    continue
                
                for row in reader:
                    rows.append(dict(zip(header, row)))
            
            except Exception as e:
                print(f"ERROR fetching bbox {bbox}: {e}")
                continue
        
        if rows:
            return pd.DataFrame(rows)
        return pd.DataFrame()
    
    def _fetch_cells_sequential(self, subboxes):
        """
        Fetch cells sequentially for all subboxes.
        """
        all_results = []
        for bbox in tqdm(subboxes, desc="Fetching antennas"):
            result = self._fetch_cells_from_bbox(bbox)
            if result is not None and len(result) > 0:
                all_results.append(result)
        
        if all_results:
            return pd.concat(all_results, ignore_index=True)
        return pd.DataFrame()
    
    def _apply_filters(self):
        """
        Apply operator, technology, frequency filters to antennas.
        Note: OpenCellID API doesn't provide operator/technology info,
        so these filters have no effect on the raw data.
        """
        if len(self.antennas) == 0:
            return
        
        # OpenCellID raw data doesn't have operator/technology columns
        # These filters are stored for compatibility with other adapters
        pass
    
    def _standardize_output_columns(self):
        """
        Ensure all standardized columns are present.
        OpenCellID only provides: cell, lat, lon, etc.
        Fill missing antenna-specific columns with NaN.
        """
        if len(self.antennas) == 0:
            self.antennas = pd.DataFrame(columns=[
                "SiteCode", "AntennaLabel", "FileNumber", "Operator", "Technology",
                "Latitude", "Longitude", "CenterHeight", "Power",
                "Frequency", "FrequencyBand", "Electrical_Tilt", "Mechanical_Tilt", "Azimuth", "Gain",
                "Horizontal_Beamwidth", "Vertical_Beamwidth"
            ])
            return
        
        # Rename OpenCellID columns to standard format
        rename_map = {
            'lat': 'Latitude',
            'lon': 'Longitude',
            'cell': 'SiteCode',
        }
        self.antennas = self.antennas.rename(columns=rename_map)
        return self.antennas
    def extract_patterns(self):
        """
        Extract antenna patterns (not applicable for OpenCellID).
        No-op method for API compatibility.
        """
        print("INFO: Pattern extraction not supported for OpenCellID")


def main():
    """
    Legacy main() function - demonstrates OpenCellID data extraction.
    Uses the BaseStations class for the actual workflow.
    """
    bbox = [3.695, 3.766, 51.005, 51.091]
    output = "Countries/Belgium/flanders"
    
    # Use BaseStations class
    bs = BaseStations(
        bounding_box=bbox,
        output_folder=output,
        max_workers=1,
        api_key_path="opencellid_api_key.txt"
    )
    bs.extract_antennas()


if __name__ == "__main__":
    main()
