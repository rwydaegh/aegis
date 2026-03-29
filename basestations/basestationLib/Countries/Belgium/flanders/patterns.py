import numpy as np
from .sparql import *


def calculate_electrical_tilt(v_losses_array: np.ndarray) -> float:
    """
    Calculates the electrical tilt (angle of minimum vertical loss).
    
    Args:
        v_losses_array: Array of vertical loss values (181 elements for -90 to +90 degrees)
    
    Returns:
        Electrical tilt in degrees, or None if calculation fails
    """
    if v_losses_array is None or len(v_losses_array) != 181:
        return None
    
    try:
        min_loss_idx = np.nanargmin(v_losses_array)
        electrical_tilt_deg = float(min_loss_idx - 90)
        if electrical_tilt_deg > 180:
            electrical_tilt_deg -= 360
        return electrical_tilt_deg
    except Exception as e:
        print(f"Error calculating electrical tilt: {e}")
        return None


def _safe_float_convert(value, default=None) -> float:
    """Safely converts a value to float, returning default if conversion fails."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def reconstruct_pattern_array(segments: list, plane: str = 'horizontal') -> np.ndarray:
    """
    Reconstructs a 1-degree resolution loss pattern array from SPARQL segments.
    Uses vectorized numpy operations for better performance.
    
    Args:
        segments: List of segment dicts with 'vanhoek', 'tothoek', 'winst' keys
        plane: Either 'horizontal' (360 elements) or 'vertical' (181 elements)
    
    Returns:
        NumPy array of loss values
    """
    if not segments:
        return None
    
    if plane == 'horizontal':
        pattern_array = np.full(360, np.nan, dtype=np.float32)
        angle_offset = -180
    elif plane == 'vertical':
        pattern_array = np.full(181, np.nan, dtype=np.float32)
        angle_offset = -90
    else:
        raise ValueError("Plane must be 'horizontal' or 'vertical'")
    
    # Pre-allocate arrays for vectorized operations
    valid_count = 0
    for seg in segments:
        try:
            vanhoek = _safe_float_convert(seg.get('vanhoek', {}).get('value'))
            tothoek = _safe_float_convert(seg.get('tothoek', {}).get('value'))
            winst = _safe_float_convert(seg.get('winst', {}).get('value'))
            
            if vanhoek is None or tothoek is None or winst is None:
                continue
            
            winst_abs = abs(winst)
            start_idx = int(round(vanhoek)) - angle_offset
            end_idx = int(round(tothoek)) - angle_offset
            
            if plane == 'horizontal' and end_idx < start_idx:
                # Wrap-around case for horizontal plane
                pattern_array[start_idx:] = winst_abs
                pattern_array[:end_idx] = winst_abs
            else:
                # Standard case
                start_idx = max(0, start_idx)
                end_idx = min(len(pattern_array), end_idx)
                if start_idx < end_idx:
                    pattern_array[start_idx:end_idx] = winst_abs
            
            valid_count += 1
        except (ValueError, TypeError):
            continue
    
    if valid_count == 0:
        print(f"Warning: No valid segments found for {plane} plane.")
    
    return pattern_array

class AntennaPatternExtractor:
    """Extracts antenna details and patterns from SPARQL endpoint with caching and optimization."""
    
    def __init__(self, sparql_url: str, timeout: int = 60):
        """
        Initialize the extractor.
        
        Args:
            sparql_url: SPARQL endpoint URL
            timeout: SPARQL query timeout in seconds (default 60, reduce for faster failure)
        """
        self.sparql_url = sparql_url
        self.timeout = timeout
        self._cache = {}  # Cache for extracted patterns to avoid re-fetching
        self._type_cache = {}  # Cache for antenna type details (widely shared across antennas)
    
    def extract_pattern(self, antenna_uri: str) -> tuple:
        """
        Extracts antenna details using pure Python SPARQL queries with caching.
        
        Args:
            antenna_uri: The URI of the antenna to extract
        
        Returns:
            Tuple: (antenna_uri, physical_height, physical_width, max_gain_dbi,
                    mechanical_tilt, electrical_tilt, gain_pattern_2d,
                    azimuths_deg, elevations_deg, vertical_beamwidth, horizontal_beamwidth)
        """
        # Check cache first
        if antenna_uri in self._cache:
            return self._cache[antenna_uri]
        
        result = self._extract_pattern_uncached(antenna_uri)
        self._cache[antenna_uri] = result
        return result
    
    def _extract_pattern_uncached(self, antenna_uri: str) -> tuple:
        """Internal method to extract pattern without caching."""
        antenna_type_uri = None
        mechanical_tilt = None
        max_gain_dbi = None
        physical_height = None
        physical_width = None
        electrical_tilt = None
        gain_pattern_2d = None
        vertical_beamwidth = None
        horizontal_beamwidth = None
        azimuths_deg = np.arange(-180, 180, 1)
        elevations_deg = np.arange(-90, 91, 1)
        
        try:
            # 1. Get Antenna Type URI and Mechanical Tilt
            query_details = get_query_antenna_full_details(antenna_uri)
            results_details = execute_sparql_query(self.sparql_url, query_details, timeout=self.timeout)
            
            if not results_details:
                return (antenna_uri, None, None, None, None, None, None, None, None, None, None)
            
            details = results_details[0]
            antenna_type_uri = details.get("type", {}).get("value")
            mechanical_tilt = _safe_float_convert(details.get("mechtilt", {}).get("value"), default=0.0)
            
            if not antenna_type_uri:
                return (antenna_uri, None, None, None, mechanical_tilt, None, None, None, None, None, None)
            
            # 2. Get Antenna Type Details (Gain, Height, Width, Beamwidths) - cached since types repeat
            if antenna_type_uri in self._type_cache:
                type_details = self._type_cache[antenna_type_uri]
            else:
                query_type_details = get_query_antenna_type_details(antenna_type_uri)
                results_type_details = execute_sparql_query(self.sparql_url, query_type_details, timeout=self.timeout)
                
                if results_type_details:
                    type_details = results_type_details[0]
                    self._type_cache[antenna_type_uri] = type_details  # Cache for future antennas
                else:
                    type_details = {}
            
            if type_details:
                max_gain_dbi = _safe_float_convert(type_details.get("winst", {}).get("value"))
                physical_height = _safe_float_convert(type_details.get("hoogte", {}).get("value"))
                physical_width = _safe_float_convert(type_details.get("breedte", {}).get("value"))
                vertical_beamwidth = _safe_float_convert(type_details.get("verticaleopeningshoek", {}).get("value"))
                horizontal_beamwidth = _safe_float_convert(type_details.get("horizontaleopeningshoek", {}).get("value"))
            
            # 3. Get Loss Patterns (Winstverlies) - also cached by type
            h_losses = None
            v_losses = None
            loss_cache_key = f"{antenna_type_uri}_losses"
            
            if loss_cache_key in self._type_cache:
                h_losses, v_losses = self._type_cache[loss_cache_key]
            else:
                query_loss = get_query_winstverlies(antenna_type_uri)
                results_loss = execute_sparql_query(self.sparql_url, query_loss, timeout=self.timeout)
                
                if results_loss:
                    h_segments = [seg for seg in results_loss if seg.get('vlak', {}).get('value', '').upper() == 'HORIZONTAAL']
                    v_segments = [seg for seg in results_loss if seg.get('vlak', {}).get('value', '').upper() == 'VERTICAAL']
                    
                    h_losses = reconstruct_pattern_array(h_segments, plane='horizontal')
                    v_losses = reconstruct_pattern_array(v_segments, plane='vertical')
                    self._type_cache[loss_cache_key] = (h_losses, v_losses)  # Cache patterns by type
            
            # 4. Calculate Electrical Tilt from Vertical Loss Pattern
            electrical_tilt = calculate_electrical_tilt(v_losses)
            
            # 5. Calculate 2D Gain Pattern using vectorized operations
            if h_losses is not None and v_losses is not None and max_gain_dbi is not None:
                try:
                    h_losses_bc = h_losses[np.newaxis, :].astype(np.float32)
                    v_losses_bc = v_losses[:, np.newaxis].astype(np.float32)
                    gain_pattern_2d = -h_losses_bc - v_losses_bc + max_gain_dbi
                except Exception as e_calc:
                    pass
        
        except Exception as e:
            pass
        
        return (antenna_uri, physical_height, physical_width, max_gain_dbi, mechanical_tilt, electrical_tilt,
                gain_pattern_2d, azimuths_deg, elevations_deg, vertical_beamwidth, horizontal_beamwidth)