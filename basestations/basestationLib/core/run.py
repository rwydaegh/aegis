"""
Core run module for basestation extraction.

This module provides the `run` function that:
1. Reads a YAML config file
2. Instantiates the appropriate BaseStations class based on country/region
3. Passes parameters from the YAML config to the BaseStations constructor
4. Executes extract_antennas() and extract_patterns()
"""

import os
import sys
from datetime import datetime, timezone
import numpy as np

from . import get_basestation_instance


def run(config_file_path):
    """
    Main execution function that orchestrates basestation extraction.
    
    Args:
        config_file_path: Path to YAML configuration file
    
    Expected YAML structure:
        locationinfo:
            country: "<country_name>"  # Required
            region/city: "<region_or_city>"  # Optional, for Belgium
            bbox: [min_lon, max_lon, min_lat, max_lat]  # Optional
        
        antennafilters:  # Optional
            operator: "<operator_name>"
            technology: "<technology>"
            frequency_range: [min_hz, max_hz]
            frequencyband: "<band>"
            date: "<YYYY-MM-DD>"
        
        output:  # Optional
            folder: "<output_folder>"
            identifier: "<custom_identifier>"
        
        computation:
            max_workers: <int>  # Number of parallel workers
        
        opencellid:  # Optional (for OpenCellID fallback)
            api_key_path: "<path_to_api_key>"
    """
    import yaml
    
    # Load YAML config
    if not os.path.exists(config_file_path):
        raise FileNotFoundError(f"Config file not found: {config_file_path}")
    
    with open(config_file_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    if config is None:
        raise ValueError("Config file is empty or invalid YAML")
    
    # Extract location info
    locationinfo = config.get("locationinfo", {})
    country = locationinfo.get("country")
    
    if not country:
        raise ValueError("'locationinfo.country' is required in config")
    
    region_city = locationinfo.get("region/city") or locationinfo.get("region") or locationinfo.get("city")
    bbox = locationinfo.get("bbox")
    
    # Extract antenna filters (optional)
    antenna_filters = config.get("antennafilters", {})
    if antenna_filters:
        operator = antenna_filters.get("operator")
        technology = antenna_filters.get("technology")
        frequency_range = antenna_filters.get("frequency_range", [0, np.inf])
        frequency_band = antenna_filters.get("frequencyband") or antenna_filters.get("frequency_band")
        date_str = antenna_filters.get("date")
        
        # Parse date if provided
        if date_str:
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except ValueError:
                print(f"WARNING: Could not parse date '{date_str}', using current date")
                date = datetime.now(timezone.utc)
        else:
            date = datetime.now(timezone.utc)
    else: 
        operator = None
        technology = None
        frequency_range = [0, np.inf]
        frequency_band = None
        date = None
    # Extract output settings (optional)
    output_config = config.get("output", {})
    if output_config:
        output_folder = output_config.get("folder")
        file_identifier = output_config.get("identifier")
    else: 
        output_folder = None
        file_identifier = None
    # Extract computation settings
    computation_config = config.get("computation", {})
    if computation_config:
        max_workers = computation_config.get("max_workers", 1)
    else: 
        max_workers = None
    # Extract OpenCellID settings (for fallback or when using OpenCellID)
    opencellid_config = config.get("opencellid", {})
    if opencellid_config:
        api_key_path = opencellid_config.get("api_key_path", "opencellid_api_key.txt")
    else:
        api_key_path = None
    # Instantiate BaseStations with region_city if provided
    if region_city:
        bs_instance = get_basestation_instance(country, region_city=region_city)
    else:
        bs_instance = get_basestation_instance(country)
    
    # Check if it's a class (has __init__) or a module
    if hasattr(bs_instance, '__init__') and not isinstance(bs_instance, type):
        # It's an instance - this shouldn't happen with current get_basestation_instance
        constructor_kwargs = {}
        if operator is not None:
            constructor_kwargs['operator'] = operator
        if technology is not None:
            constructor_kwargs['technology'] = technology
        if bbox is not None:
            constructor_kwargs['bounding_box'] = bbox
        if frequency_range is not None:
            constructor_kwargs['frequency_range'] = frequency_range
        if frequency_band is not None:
            constructor_kwargs['frequency_band'] = frequency_band
        if date is not None:
            constructor_kwargs['date'] = date
        if output_folder is not None:
            constructor_kwargs['output_folder'] = output_folder
        if max_workers is not None:
            constructor_kwargs['max_workers'] = max_workers
        if file_identifier is not None:
            constructor_kwargs['file_identifier'] = file_identifier
        bs_instance = bs_instance(**constructor_kwargs)
    elif isinstance(bs_instance, type):
        # It's a class - instantiate it with config parameters
        constructor_kwargs = {}
        if operator is not None:
            constructor_kwargs['operator'] = operator
        if technology is not None:
            constructor_kwargs['technology'] = technology
        if bbox is not None:
            constructor_kwargs['bounding_box'] = bbox
        if frequency_range is not None:
            constructor_kwargs['frequency_range'] = frequency_range
        if frequency_band is not None:
            constructor_kwargs['frequency_band'] = frequency_band
        if date is not None:
            constructor_kwargs['date'] = date
        if output_folder is not None:
            constructor_kwargs['output_folder'] = output_folder
        if max_workers is not None:
            constructor_kwargs['max_workers'] = max_workers
        if file_identifier is not None:
            constructor_kwargs['file_identifier'] = file_identifier
        
        # Add api_key_path for OpenCellID
        if hasattr(bs_instance, '__init__'):
            import inspect
            sig = inspect.signature(bs_instance.__init__)
            if 'api_key_path' in sig.parameters:
                constructor_kwargs['api_key_path'] = api_key_path
        
        bs_instance = bs_instance(**constructor_kwargs)
    else:
        # It's a module - try to instantiate BaseStations class from it
        if hasattr(bs_instance, 'BaseStations'):
            BaseStations = bs_instance.BaseStations
            constructor_kwargs = {}
            if operator is not None:
                constructor_kwargs['operator'] = operator
            if technology is not None:
                constructor_kwargs['technology'] = technology
            if bbox is not None:
                constructor_kwargs['bounding_box'] = bbox
            if frequency_range is not None:
                constructor_kwargs['frequency_range'] = frequency_range
            if frequency_band is not None:
                constructor_kwargs['frequency_band'] = frequency_band
            if date is not None:
                constructor_kwargs['date'] = date
            if output_folder is not None:
                constructor_kwargs['output_folder'] = output_folder
            if max_workers is not None:
                constructor_kwargs['MAX_WORKERS'] = max_workers
            if file_identifier is not None:
                constructor_kwargs['file_identifier'] = file_identifier
            
            # Add api_key_path for OpenCellID
            import inspect
            sig = inspect.signature(BaseStations.__init__)
            if 'api_key_path' in sig.parameters:
                constructor_kwargs['api_key_path'] = api_key_path
            
            bs_instance = BaseStations(**constructor_kwargs)
        else:
            raise ValueError(f"Module {country} has no BaseStations class")
    
    # Execute extraction workflow
    print(f"Extracting antennas for {country}" + (f" ({region_city})" if region_city else ""))
    bs_instance.extract_antennas(config=config)
    
    # Try to extract patterns if the method exists
    if hasattr(bs_instance, 'extract_patterns'):
        try:
            bs_instance.extract_patterns()
        except Exception as e:
            print(f"Note: Pattern extraction skipped or failed: {e}")
    
    print("###### Workflow done ######")
