final_columns = [
    "SiteCode",
    "AntennaLabel",
    "Operator",
    "Technology",
    "Latitude",
    "Longitude",
    "CenterHeight",
    "Power",
    "Frequency",
    "FrequencyBand",
    "Electrical_Tilt",
    "Mechanical_Tilt",
    "Azimuth",
    "Gain",
    "Horizontal_Beamwidth",
    "Vertical_Beamwidth",
]
from .estimate_missing_data import *
from .technologies import *
from .filters import apply_filters
import numpy as np
def create_output_df(df, config = None, filter_args = {}):
    # Add missing columns with NA values
    for col in final_columns:
        if col not in df.columns:
            df[col] = np.nan
        elif col == "Azimuth":
            # ensure dtype is int
            df["Azimuth"] = pd.to_numeric(df[col], errors="coerce").round().astype("Int64")
    # Reorder to match final_columns (keep only columns that should be in output)
    df = df[
        [col for col in final_columns if col in df.columns]
        ]
    df = df[final_columns]
    init_len = len(df)
    new_len = init_len
    print(f"{init_len} raw antennas")
    df = convert_technologies_in_df(df)
    df = add_frequency_band(df, freq_col = "Frequency", out_col = "FrequencyBand")
    if filter_args:
        df = apply_filters(df, **filter_args)
        new_len = len(df)
        print(f"{init_len - new_len} antennas removed based on antenna-filter arguments")
    df = combine_technologies_per_band(df)
    df = estimate_from_config(df, config = config) if config else df
    final_len = len(df)
    print(f"Removed {new_len - final_len} duplicates, resulting in {final_len} physical antenna panels")
    return df[final_columns]
