
"""
Data estimation utility for filling missing values in antenna datasets.

This module provides functions to estimate missing antenna parameters
based on statistical analysis of similar technologies from reference datasets.
"""

import os
import pandas as pd
import numpy as np

try:
    if os.environ.get("DISPLAY"):
        import tkinter as tk
        from tkinter import filedialog
        _HAS_TK = True
    else:
        _HAS_TK = False
except ImportError:
    _HAS_TK = False

NUMERIC_COLS = [
    "Power", "Electrical_Tilt", "Mechanical_Tilt",
    "Gain", "Horizontal_Beamwidth", "Vertical_Beamwidth"
]

# Tokens that should be treated as "missing"/unknown for categorical fields
_UNKNOWN_TOKENS = {
    None, "", "UNKNOWN", "Unknown", "unknown",
    "N/A", "n/a", "NA", "na", "null", "NULL", "None", "none",
    np.nan, pd.NA
}


def _is_missing_cat(x) -> bool:
    """True if x is None/NaN/NA/UNKNOWN-like."""
    if x is None:
        return True
    # pd.isna handles np.nan and pd.NA
    try:
        if pd.isna(x):
            return True
    except Exception:
        pass
    s = str(x).strip()
    if s in ("",):
        return True
    return s in {str(t).strip() for t in _UNKNOWN_TOKENS if t is not None and not (isinstance(t, float) and np.isnan(t))}


def _norm_cat(x):
    """Normalize categorical values: unknown-like -> pd.NA, else stripped string."""
    return pd.NA if _is_missing_cat(x) else str(x).strip()


def _cast_scalar_to_target(val, col, target_dtypes):
    """Cast a single scalar to the desired dtype for column `col`."""
    if pd.isna(val):
        # Respect nullable Int64
        return pd.NA if target_dtypes.get(col) == "Int64" else np.nan

    dtype = target_dtypes.get(col)
    if dtype is None:
        return val  # no special handling

    if dtype == "Int64":
        # nullable int: store as Python int, NaNs as pd.NA
        return int(round(val))
    elif dtype == "float64":
        return float(val)
    else:
        # fallback for any other target dtype you might add
        return dtype(val)


def is_tech_in_string(string, technology) -> bool:
    """Return True if any tech in `technology` appears in `string` (case-insensitive, '/'-separated)."""
    if string is None or technology is None:
        return False

    # Treat unknown-like as missing
    if _is_missing_cat(string) or _is_missing_cat(technology):
        return False

    # Normalize to lowercase, strip spaces, drop empties
    s_set = {s.strip().lower() for s in str(string).split("/") if s.strip()}
    t_set = {t.strip().lower() for t in str(technology).split("/") if t.strip()}

    if not s_set or not t_set:
        return False

    # True if any overlap
    return bool(s_set & t_set)


def estimate_missing_data(antennas_df, config):
    """
    Vectorized estimation + datatype enforcement.

    Priority for each numeric column:
        1) Use means from the *same df* for matching (Technology, FrequencyBand)
        2) If still missing: use means from reference data for (Technology, FrequencyBand)
        3) If still missing: use means from reference data for Technology only
        4) If still missing: use means from reference data for FrequencyBand only
        5) If still missing: leave NaN

    Summary prints how many values were filled at each stage.
    """

    computation = config.get("computation", {})
    estimations = computation.get("estimations", {})
    estimate_enabled = estimations.get("estimate_missing_data_based_on_existing", True)

    if not estimate_enabled:
        return antennas_df.copy()

    df = antennas_df.copy()

    # ---------------------------------------------------------
    # Normalize categorical columns (so UNKNOWN/NA behave like missing)
    # ---------------------------------------------------------
    if "Technology" in df.columns:
        df["Technology"] = df["Technology"].apply(_norm_cat)
    else:
        # without Technology we cannot estimate using your matching logic
        return df

    if "FrequencyBand" in df.columns:
        df["FrequencyBand"] = df["FrequencyBand"].apply(_norm_cat)

    has_fb = ("FrequencyBand" in df.columns) and df["FrequencyBand"].notna().any()

    # convert numerical_cols to numeric
    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Column → dtype mapping
    target_dtypes = {
        # Floats
        "Power": "float64",
        "Gain": "float64",

        # Int-like (use nullable Int64 to keep NaN support)
        "Electrical_Tilt": "Int64",
        "Mechanical_Tilt": "Int64",
        "Horizontal_Beamwidth": "Int64",
        "Vertical_Beamwidth": "Int64",
    }

    # =========================================================
    # Stage A: Estimation using DF itself
    #   A1) (Technology, FrequencyBand) when BOTH available
    #   A2) Technology-only when FrequencyBand missing/unknown
    #   A3) FrequencyBand-only when Technology missing/unknown
    # =========================================================

    # aggregated means from df
    df_mean_t = df.groupby(["Technology"])[NUMERIC_COLS].mean().reset_index()

    if has_fb:
        df_mean_tf = df.groupby(["Technology", "FrequencyBand"])[NUMERIC_COLS].mean().reset_index()
        df_mean_f = df.groupby(["FrequencyBand"])[NUMERIC_COLS].mean().reset_index()
    else:
        df_mean_tf = None
        df_mean_f = None

    # Counters
    tf_count_df = 0
    t_count_df = 0
    f_count_df = 0
    cols_filled_tf_df = []
    cols_filled_t_df = []
    cols_filled_f_df = []

    for col in NUMERIC_COLS:
        if col not in df.columns:
            continue

        # A1: (Technology, FrequencyBand)
        nan_mask = df[col].isna()
        if nan_mask.any() and has_fb and df_mean_tf is not None:
            # Only fill rows where both Technology and FrequencyBand are available
            elig = nan_mask & df["Technology"].notna() & df["FrequencyBand"].notna()

            if elig.any():
                for _, row in df_mean_tf.iterrows():
                    tech, fb, val = row["Technology"], row["FrequencyBand"], row[col]
                    if pd.isna(val) or pd.isna(tech) or pd.isna(fb):
                        continue
                    mask = elig & df["Technology"].apply(is_tech_in_string, technology=tech) & (df["FrequencyBand"] == fb)
                    filled = int(mask.sum())
                    if filled > 0:
                        df.loc[mask, col] = _cast_scalar_to_target(val, col, target_dtypes)
                        tf_count_df += filled
                        if col not in cols_filled_tf_df:
                            cols_filled_tf_df.append(col)

        # A2: Technology-only (FrequencyBand missing/unknown or not present)
        nan_mask = df[col].isna()
        if nan_mask.any():
            elig = nan_mask & df["Technology"].notna() & ((~has_fb) | df["FrequencyBand"].isna())
            if elig.any():
                for _, row in df_mean_t.iterrows():
                    tech, val = row["Technology"], row[col]
                    if pd.isna(val) or pd.isna(tech):
                        continue
                    mask = elig & df["Technology"].apply(is_tech_in_string, technology=tech)
                    filled = int(mask.sum())
                    if filled > 0:
                        df.loc[mask, col] = _cast_scalar_to_target(val, col, target_dtypes)
                        t_count_df += filled
                        if col not in cols_filled_t_df:
                            cols_filled_t_df.append(col)

        # A3: FrequencyBand-only (Technology missing/unknown)
        nan_mask = df[col].isna()
        if nan_mask.any() and has_fb and df_mean_f is not None:
            elig = nan_mask & df["Technology"].isna() & df["FrequencyBand"].notna()
            if elig.any():
                for _, row in df_mean_f.iterrows():
                    fb, val = row["FrequencyBand"], row[col]
                    if pd.isna(val) or pd.isna(fb):
                        continue
                    mask = elig & (df["FrequencyBand"] == fb)
                    filled = int(mask.sum())
                    if filled > 0:
                        df.loc[mask, col] = _cast_scalar_to_target(val, col, target_dtypes)
                        f_count_df += filled
                        if col not in cols_filled_f_df:
                            cols_filled_f_df.append(col)

    # Early exit if no missing values remain
    still_missing = any((col in df.columns and df[col].isna().any()) for col in NUMERIC_COLS)
    if not still_missing:
        print("Estimation summary:")
        if tf_count_df > 0:
            print(f"  - Technology + FrequencyBand (df): {tf_count_df} values estimated, spread over {cols_filled_tf_df} columns.")
        if t_count_df > 0:
            print(f"  - Technology only (df): {t_count_df} values estimated, spread over {cols_filled_t_df} columns.")
        if f_count_df > 0:
            print(f"  - FrequencyBand only (df): {f_count_df} values estimated, spread over {cols_filled_f_df} columns.")
        # datatype enforcement at the end keeps output consistent
        for col, dtype in target_dtypes.items():
            if col in df.columns:
                try:
                    if dtype == "Int64":
                        df[col] = pd.to_numeric(df[col], errors="coerce").round().astype(dtype)
                    else:
                        df[col] = df[col].astype(dtype)
                except Exception:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                    if dtype == "Int64":
                        df[col] = df[col].round().astype(dtype)
                    else:
                        df[col] = df[col].astype(dtype)
        return df

    # =========================================================
    # Stage B: Reference-based estimation
    #   B1) (Technology, FrequencyBand)
    #   B2) Technology-only
    #   B3) FrequencyBand-only
    # =========================================================

    print("Estimating missing values based on reference data...")

    # Read paths from config, default to empty list
    csv_paths = estimations.get("csv_paths", [])

    # Normalize to a list of strings
    if isinstance(csv_paths, str):
        csv_paths = [csv_paths]
    elif csv_paths is None:
        csv_paths = []
    else:
        csv_paths = list(csv_paths)

    # If no paths given in config, open file dialog (when display available)
    if not csv_paths and _HAS_TK:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        root.update()

        csv_paths = filedialog.askopenfilenames(
            title="Select reference CSV files",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            parent=root,
        )

        root.destroy()
        csv_paths = list(csv_paths)

    # If still nothing chosen, just return current df
    if not csv_paths:
        print("No CSV files selected, skipping reference estimation.")
        print("Estimation summary:")
        if tf_count_df > 0:
            print(f"  - Technology + FrequencyBand (df): {tf_count_df} values estimated, spread over {cols_filled_tf_df} columns.")
        if t_count_df > 0:
            print(f"  - Technology only (df): {t_count_df} values estimated, spread over {cols_filled_t_df} columns.")
        if f_count_df > 0:
            print(f"  - FrequencyBand only (df): {f_count_df} values estimated, spread over {cols_filled_f_df} columns.")
        # datatype enforcement
        for col, dtype in target_dtypes.items():
            if col in df.columns:
                try:
                    if dtype == "Int64":
                        df[col] = pd.to_numeric(df[col], errors="coerce").round().astype(dtype)
                    else:
                        df[col] = df[col].astype(dtype)
                except Exception:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                    if dtype == "Int64":
                        df[col] = df[col].round().astype(dtype)
                    else:
                        df[col] = df[col].astype(dtype)
        return df

    # Load reference data
    ref_list = []
    for p in csv_paths:
        try:
            ref_list.append(pd.read_csv(p))
        except Exception as e:
            print(f"WARNING: cannot load {p}: {e}")

    if not ref_list:
        print("WARNING: no reference data → return current.")
        print("Estimation summary:")
        if tf_count_df > 0:
            print(f"  - Technology + FrequencyBand (df): {tf_count_df} values estimated, spread over {cols_filled_tf_df} columns.")
        if t_count_df > 0:
            print(f"  - Technology only (df): {t_count_df} values estimated, spread over {cols_filled_t_df} columns.")
        if f_count_df > 0:
            print(f"  - FrequencyBand only (df): {f_count_df} values estimated, spread over {cols_filled_f_df} columns.")
        # datatype enforcement
        for col, dtype in target_dtypes.items():
            if col in df.columns:
                try:
                    if dtype == "Int64":
                        df[col] = pd.to_numeric(df[col], errors="coerce").round().astype(dtype)
                    else:
                        df[col] = df[col].astype(dtype)
                except Exception:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                    if dtype == "Int64":
                        df[col] = df[col].round().astype(dtype)
                    else:
                        df[col] = df[col].astype(dtype)
        return df

    ref = pd.concat(ref_list, ignore_index=True)

    # Normalize categorical columns in ref too
    if "Technology" in ref.columns:
        ref["Technology"] = ref["Technology"].apply(_norm_cat)
    else:
        # without Technology in reference, only FB-only fallback can work (if any)
        ref["Technology"] = pd.NA

    if "FrequencyBand" in ref.columns:
        ref["FrequencyBand"] = ref["FrequencyBand"].apply(_norm_cat)
    else:
        ref["FrequencyBand"] = pd.NA

    # convert numerical_cols to numeric in ref
    for col in NUMERIC_COLS:
        if col in ref.columns:
            ref[col] = pd.to_numeric(ref[col], errors="coerce")
        else:
            ref[col] = np.nan

    ref_has_fb = ref["FrequencyBand"].notna().any()

    # Aggregated means from REFERENCE data
    ref_mean_t = ref.groupby(["Technology"])[NUMERIC_COLS].mean().reset_index()

    if ref_has_fb:
        ref_mean_tf = ref.groupby(["Technology", "FrequencyBand"])[NUMERIC_COLS].mean().reset_index()
        ref_mean_f = ref.groupby(["FrequencyBand"])[NUMERIC_COLS].mean().reset_index()
    else:
        ref_mean_tf = None
        ref_mean_f = None

    # Counters for reference
    tf_count_ref = 0
    t_count_ref = 0
    f_count_ref = 0
    cols_filled_tf_ref = []
    cols_filled_t_ref = []
    cols_filled_f_ref = []

    for col in NUMERIC_COLS:
        if col not in df.columns:
            continue

        # B1: (Technology, FrequencyBand)
        nan_mask = df[col].isna()
        if nan_mask.any() and has_fb and ref_has_fb and ref_mean_tf is not None:
            elig = nan_mask & df["Technology"].notna() & df["FrequencyBand"].notna()
            if elig.any():
                for _, row in ref_mean_tf.iterrows():
                    tech, fb, val = row["Technology"], row["FrequencyBand"], row[col]
                    if pd.isna(val) or pd.isna(tech) or pd.isna(fb):
                        continue
                    mask = elig & df["Technology"].apply(is_tech_in_string, technology=tech) & (df["FrequencyBand"] == fb)
                    filled = int(mask.sum())
                    if filled > 0:
                        df.loc[mask, col] = _cast_scalar_to_target(val, col, target_dtypes)
                        tf_count_ref += filled
                        if col not in cols_filled_tf_ref:
                            cols_filled_tf_ref.append(col)

        # B2: Technology-only
        nan_mask = df[col].isna()
        if nan_mask.any():
            elig = nan_mask & df["Technology"].notna() & ((~has_fb) | df["FrequencyBand"].isna())
            if elig.any():
                for _, row in ref_mean_t.iterrows():
                    tech, val = row["Technology"], row[col]
                    if pd.isna(val) or pd.isna(tech):
                        continue
                    mask = elig & df["Technology"].apply(is_tech_in_string, technology=tech)
                    filled = int(mask.sum())
                    if filled > 0:
                        df.loc[mask, col] = _cast_scalar_to_target(val, col, target_dtypes)
                        t_count_ref += filled
                        if col not in cols_filled_t_ref:
                            cols_filled_t_ref.append(col)

        # B3: FrequencyBand-only
        nan_mask = df[col].isna()
        if nan_mask.any() and has_fb and ref_has_fb and ref_mean_f is not None:
            elig = nan_mask & df["Technology"].isna() & df["FrequencyBand"].notna()
            if elig.any():
                for _, row in ref_mean_f.iterrows():
                    fb, val = row["FrequencyBand"], row[col]
                    if pd.isna(val) or pd.isna(fb):
                        continue
                    mask = elig & (df["FrequencyBand"] == fb)
                    filled = int(mask.sum())
                    if filled > 0:
                        df.loc[mask, col] = _cast_scalar_to_target(val, col, target_dtypes)
                        f_count_ref += filled
                        if col not in cols_filled_f_ref:
                            cols_filled_f_ref.append(col)

    # =========================================================
    # DATATYPE ENFORCEMENT
    # =========================================================
    for col, dtype in target_dtypes.items():
        if col in df.columns:
            try:
                if dtype == "Int64":
                    df[col] = pd.to_numeric(df[col], errors="coerce").round().astype(dtype)
                else:
                    df[col] = df[col].astype(dtype)
            except Exception:
                df[col] = pd.to_numeric(df[col], errors="coerce")
                if dtype == "Int64":
                    df[col] = df[col].round().astype(dtype)
                else:
                    df[col] = df[col].astype(dtype)

    # =========================================================
    # SUMMARY MESSAGE
    # =========================================================
    total_filled = tf_count_df + t_count_df + f_count_df + tf_count_ref + t_count_ref + f_count_ref
    if total_filled == 0:
        print("Estimation summary: no missing numeric values to estimate.")
        return df

    print("Estimation summary:")
    if tf_count_df > 0:
        print(f"  - Technology + FrequencyBand (df): {tf_count_df} values estimated, spread over {cols_filled_tf_df} columns.")
    if t_count_df > 0:
        print(f"  - Technology only (df): {t_count_df} values estimated, spread over {cols_filled_t_df} columns.")
    if f_count_df > 0:
        print(f"  - FrequencyBand only (df): {f_count_df} values estimated, spread over {cols_filled_f_df} columns.")
    if tf_count_ref > 0:
        print(f"  - Technology + FrequencyBand (ref): {tf_count_ref} values estimated, spread over {cols_filled_tf_ref} columns.")
    if t_count_ref > 0:
        print(f"  - Technology only (ref): {t_count_ref} values estimated, spread over {cols_filled_t_ref} columns.")
    if f_count_ref > 0:
        print(f"  - FrequencyBand only (ref): {f_count_ref} values estimated, spread over {cols_filled_f_ref} columns.")

    return df


def estimate_from_config(antennas_df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    Estimate missing data using settings from config dictionary.

    Args:
        antennas_df: DataFrame with antenna data
        config: Configuration dictionary with 'computation' section

    Returns:
        DataFrame with estimated values (or unchanged if estimation disabled)
    """
    return estimate_missing_data(antennas_df, config)

