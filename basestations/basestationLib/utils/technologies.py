import re
import pandas as pd
import numpy as np

def convert_technologies_in_df(df):
    """Normalize the `Technology` column in-place using `convert_technology`.

    - If the `Technology` column is missing the DataFrame is returned unchanged.
    - Handles composite values such as "GSM/UMTS" or "LTE,NR" by splitting
      on common separators and mapping each token. The mapped tokens are
      rejoined with a forward slash (`/`) in the original order.
    """
    if "Technology" not in df.columns:
        print("Technology not in DataFrame")
        return df

    def _map_tech(value):
        # Preserve NaN and non-scalar values
        if pd.isna(value):
            return value
        # If already a list-like, try to map each element
        if isinstance(value, (list, tuple)):
            tokens = [str(v).strip() for v in value if v is not None]
        else:
            tokens = [t.strip() for t in re.split(r"[,/;|\\+\\s]+", str(value)) if t.strip()]

        mapped = []
        for t in tokens:
            try:
                mapped_value = convert_technology(t)
            except Exception:
                # If convert_technology cannot handle it, keep original token
                mapped_value = t
            if mapped_value not in mapped:
                mapped.append(mapped_value)

        # Return single token or joined tokens
        if not mapped:
            return value
        return "/".join(mapped) if len(mapped) > 1 else mapped[0]

    df = df.copy()
    df["Technology"] = df["Technology"].apply(_map_tech)
    return df


def convert_technology(technologystring):
    if not isinstance(technologystring, str):
        raise TypeError("technology must be a string")
    if technologystring.lower() in ["n/a", "unknown", "", "na", "none"]:
        return technologystring
    s = technologystring.lower()
    if "gsm" in s:
        return "2G"
    elif "umts" in s or "wcdma" in s:
        return "3G"
    elif "lte" in s or "e-utra" in s:
        return "4G"
    elif "nr" in s or s.startswith("5g"):
        return "5G"
    else:
        # If it's already a generation like '2G' keep it, otherwise return original
        if re.match(r"^[2-5]g$", s):
            return technologystring.upper()
        print(f"Technology {technologystring} not recognized, keeping original")
        return technologystring


def add_frequency_band(df, freq_col='Frequency', out_col='FrequencyBand'):
    """Add a `FrequencyBand` column to `df` based on numeric frequency values.

    The function attempts to coerce the `freq_col` values to numeric MHz and
    matches them against a small table of common 3GPP/LTE/NR bands. If no
    exact band is found, it falls back to broad frequency groups.

    - Accepts frequencies expressed as numbers (MHz or Hz) or strings
        like '800', '800 MHz', '1.8 GHz'.
    - Adds `out_col` to the returned DataFrame (a copy) and does not modify
        the input in-place.
    """
    if out_col in df.columns and df[out_col].notna().all():
        return df
    if freq_col not in df.columns:
        df = df.copy()
        df[out_col] = pd.NA
        return df

    def _parse_freq_to_mhz(val):
        if pd.isna(val):
            return None
        # If already numeric
        try:
            v = float(val)
            # Heuristic: values > 1e4 are in Hz, values > 1000 likely Hz
            if v > 1e4:
                return v / 1e6
            # Typical MHz values are below a few tens of thousands
            return v
        except Exception:
            s = str(val).lower().strip()
            # Replace commas, MHz, khz, ghz
            s = s.replace(',', '.')
            if 'ghz' in s:
                try:
                    return float(s.replace('ghz', '').strip()) * 1000.0
                except Exception:
                    return None
            if 'mhz' in s:
                try:
                    return float(s.replace('mhz', '').strip())
                except Exception:
                    return None
            if 'hz' in s:
                try:
                    return float(s.replace('hz', '').strip()) / 1e6
                except Exception:
                    return None
            # Remove non-numeric chars
            cleaned = re.sub(r'[^0-9\.]', '', s)
            try:
                return float(cleaned) if cleaned else None
            except Exception:
                return None

    # Small table of common bands (approximate downlink ranges in MHz)
    # This is intentionally a compact list of frequently used bands.
    bands = {
        # --- Sub-6 GHz (LTE + NR) ---
        'Band700MHz':   [758, 803],     # APT700 DL (Band 28)
        'Band800MHz':   [791, 821],
        'Band900MHz':   [925, 960],
        'Band1500MHz':  [1452, 1492],
        'Band1800MHz':  [1805, 1880],
        'Band2100MHz':  [2110, 2170],   # Band 1 DL
        'Band2600MHz':  [2570, 2690],   # Band 7 DL
        'Band3600MHz':  [3400, 3800],   # NR n78 (3.4–3.8 GHz)

        # --- mmWave NR (FR2) ---
        'Band26000MHz': [24250, 27500], # n258 26 GHz
        'Band28000MHz': [26500, 29500], # n257 28 GHz
        'Band39000MHz': [37000, 40000], # n260 39 GHz
    }
    def _map_band(mhz):
        # Handle missing or unparsable values
        if mhz is None or pd.isna(mhz):
            return pd.NA

        # 1) Try to match one of the explicitly defined bands
        for band_name, (f_lo, f_hi) in bands.items():
            if f_lo <= mhz <= f_hi:
                return band_name

        # 2) Fall back to broader frequency groups
        # Adjust these buckets as you like for your use case
        if mhz < 700:
            return 'Unknown (<700MHz)'
        elif 700 <= mhz < 1000:
            return 'Unknown (700–1000MHz)'
        elif 1000 <= mhz < 2000:
            return 'Unknown (1–2GHz)'
        elif 2000 <= mhz < 3000:
            return 'Unknown (2–3GHz)'
        elif 3000 <= mhz < 6000:
            return 'Unknown (3–6GHz)'
        else:
            return 'Unknown (>6GHz)'

    df = df.copy()
    mhz_series = df[freq_col].apply(_parse_freq_to_mhz)
    df[out_col] = mhz_series.apply(_map_band)
    return df

# def combine_technologies_per_band(df: pd.DataFrame) -> pd.DataFrame:
#     """
#     Combine rows that correspond to the same physical antenna / sector.

#     - Same site if all `same_site_check_columns` are identical.
#     - Technologies in the group are merged to a single string, e.g. "4G/5G".
#     - Frequencies in the group are averaged and rounded to 1 decimal place.
#     - Other columns are taken from the first row in the group.
#     """
#     same_site_check_columns = [
#         "SiteCode",
#         "Operator",
#         "Latitude",
#         "Longitude",
#         "CenterHeight",
#         "Azimuth",
#         "FrequencyBand"
#     ]

#     def _combine_group(g: pd.DataFrame) -> pd.Series:
#         # Start from first row so we keep all other fields (Power, tilts, gain, etc.)
#         base = g.iloc[0].copy()
#         # Combine technologies: unique, sorted, joined with '/'
#         if "Technology" in g.columns:
#             techs = (
#                 g["Technology"]
#                 .dropna()
#                 .astype(str)
#                 .unique()
#             )
#             base["Technology"] = "/".join(sorted(techs)) if len(techs) > 0 else np.nan

#         # Average frequency, 1 decimal
#         if "Frequency" in g.columns:
#             freqs = g["Frequency"].dropna().astype(float)
#             base["Frequency"] = round(freqs.mean(), 1) if len(freqs) > 0 else np.nan

#         # Keep first non-NaN FrequencyBand (they should all be the same band)
#         if "FrequencyBand" in g.columns:
#             fb = g["FrequencyBand"].dropna().astype(str)
#             base["FrequencyBand"] = fb.iloc[0] if len(fb) > 0 else np.nan
#         if "AntennaLabel" in g.columns:
#             # append the labels after one another if they are different. If they are the same keep it once
#             labels = (
#                 g["AntennaLabel"]
#                 .dropna()
#                 .astype(str)
#                 .unique()
#             )
#             base["AntennaLabel"] = "/".join(sorted(labels)) if len(labels) > 0 else np.nan
#         return base
#     # Group by physical-site-defining columns and combine
#     combined = (
#         df.groupby(same_site_check_columns, dropna=False, group_keys=False)
#           .apply(_combine_group)
#           .reset_index(drop=True)
#     )
#     return combined

def combine_technologies_per_band(df: pd.DataFrame) -> pd.DataFrame:
    """
    Faster version of combine_technologies_per_band:
    - Avoids groupby.apply with a Python function
    - Uses vectorized groupby.agg + joins
    """

    same_site_check_columns = [
        "SiteCode",
        "Operator",
        "Latitude",
        "Longitude",
        "CenterHeight",
        "Azimuth",
        "FrequencyBand"
    ]

    # 1) Take the first row of each group as the "base" for all other columns
    #    (this is highly optimized in pandas)
    base = (
        df.sort_values(same_site_check_columns)
          .drop_duplicates(subset=same_site_check_columns, keep="first")
          .set_index(same_site_check_columns)
    )

    # 2) Aggregate Technology (unique, sorted, joined with "/")
    if "Technology" in df.columns:
        tech_agg = (
            df.dropna(subset=["Technology"])
              .assign(Technology=lambda x: x["Technology"].astype(str))
              .groupby(same_site_check_columns, dropna=False)["Technology"]
              .agg(lambda s: "/".join(sorted(pd.unique(s))))
        )
    else:
        tech_agg = None

    # 3) Aggregate Frequency (mean, 1 decimal)
    if "Frequency" in df.columns:
        freq_agg = (
            df.dropna(subset=["Frequency"])
              .assign(Frequency=lambda x: x["Frequency"].astype(float))
              .groupby(same_site_check_columns, dropna=False)["Frequency"]
              .mean()
              .round(1)
        )
    else:
        freq_agg = None

    # 4) Aggregate AntennaLabel (unique, sorted, joined with "/")
    if "AntennaLabel" in df.columns:
        label_agg = (
            df.dropna(subset=["AntennaLabel"])
              .assign(AntennaLabel=lambda x: x["AntennaLabel"].astype(str))
              .groupby(same_site_check_columns, dropna=False)["AntennaLabel"]
              .agg(lambda s: "/".join(sorted(pd.unique(s))))
        )
    else:
        label_agg = None

    # 5) Join the aggregated columns back onto the base
    if tech_agg is not None:
        base["Technology"] = tech_agg
    if freq_agg is not None:
        base["Frequency"] = freq_agg
    if label_agg is not None:
        base["AntennaLabel"] = label_agg

    # 6) Reset index to return a flat DataFrame
    combined = base.reset_index()

    return combined