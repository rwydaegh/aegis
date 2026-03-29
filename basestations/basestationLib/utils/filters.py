import numpy as np
import pandas as pd
import re
from typing import Optional, Union, Sequence

def apply_filters(
    df: pd.DataFrame,
    operator=None,
    technology=None,
    bounding_box=None,
    frequency_range=[0, np.inf],
    frequency_band = None,
    date=None,
):
    """
    Apply all antenna filters in a fixed order.

    Args:
        df: DataFrame with at least columns
            ['Operator', 'Technology', 'Latitude', 'Longitude',
            'Frequency', 'Date'] (where applicable).
        operator: str or None. If given, keep only this operator.
        technology: str or None. If given, keep only this technology.
        bounding_box: (min_lon, max_lon, min_lat, max_lat) or None.
        frequency_range: [f_min, f_max] in MHz (inclusive).
        date: datetime or string or None.
        If given, keep rows with Date <= date.
    """
    
    df = filter_operator(df, operator)
    df = filter_technology(df, technology)
    df = filter_date(df, date)
    df = filter_bounding_box(df, bounding_box)
    df = filter_frequency_band(df, frequency_band)
    df = filter_frequency_range(df, frequency_range)
    
    return df

def filter_frequency_band(df: pd.DataFrame, frequency_band):
    if frequency_band is not None and "FrequencyBand" in df.columns: 
        df = df[df["FrequencyBand"] == frequency_band]
    return df 


def same_operator(op_value, op_query) -> bool:
    """
    True if ANY word token matches between op_value and op_query (case-insensitive).
    Handles NaN/non-string safely.
    """
    if pd.isna(op_value) or pd.isna(op_query):
        return False

    s1 = str(op_value).lower()
    s2 = str(op_query).lower()

    # Tokenize into words (safer than .split() for punctuation like "-", "/", ",")
    w1 = set(re.findall(r"[a-z0-9]+", s1))
    w2 = set(re.findall(r"[a-z0-9]+", s2))

    return len(w1 & w2) > 0


def filter_operator(
    df: pd.DataFrame,
    operator: Optional[Union[str, Sequence[str]]],
) -> pd.DataFrame:
    """
    Filter df where df['Operator'] shares at least one word token with the requested operator(s).
    operator can be a string or list/tuple/set of strings.
    """
    if operator is None or "Operator" not in df.columns:
        return df

    # Normalize operator terms once
    if isinstance(operator, (list, tuple, set)):
        terms = [op for op in operator if op is not None]
    else:
        terms = [operator]

    if not terms:
        return df

    def row_matches(val) -> bool:
        if pd.isna(val):
            return False
        return any(same_operator(val, term) for term in terms)

    mask = df["Operator"].apply(row_matches)
    return df[mask].reset_index(drop=True)

def filter_technology(df: pd.DataFrame, technology, *, case_sensitive=False) -> pd.DataFrame:
    if technology is None or "Technology" not in df.columns:
        return df

    terms = technology if isinstance(technology, (list, tuple, set)) else [technology]
    terms = [re.escape(str(t)) for t in terms if t is not None]
    if not terms:
        return df

    pattern = "|".join(terms)
    flags = 0 if case_sensitive else re.IGNORECASE
    mask = df["Technology"].astype(str).str.contains(pattern, flags=flags, na=False, regex=True)
    return df[mask]


def filter_bounding_box(df: pd.DataFrame, bounding_box):
    if bounding_box is not None and "Latitude" in df.columns and "Longitude" in df.columns:
        min_lon, max_lon, min_lat, max_lat = bounding_box
        df = df[
            (df["Longitude"] >= min_lon)
            & (df["Longitude"] <= max_lon)
            & (df["Latitude"] >= min_lat)
            & (df["Latitude"] <= max_lat)
        ]
    return df


def filter_frequency_range(df: pd.DataFrame, frequency_range):
    """
    Keep rows with Frequency in [f_min, f_max].

    frequency_range is expected as [f_min, f_max].
    If it is [0, np.inf] (default), no filtering is applied.
    """
    
    if frequency_range is None or frequency_range == [0, np.inf] or "Frequency" not in df.columns:
        return df

    # Unpack
    f_min, f_max = frequency_range

    # If it's the default full range, do nothing
    if (f_min == 0) and (np.isinf(f_max)):
        return df

    # Ensure numeric
    freq = pd.to_numeric(df["Frequency"], errors="coerce")
    df = df[(freq >= f_min) & (freq <= f_max)]
    return df


def filter_date(df: pd.DataFrame, date):
    """
    Filter rows based on Date column (string).

    Parameters
    ----------
    df : pd.DataFrame
    date : str | None
        'YYYY-MM-DD' string. Keeps rows with df["Date"] <= date.
        If None, no cutoff filter is applied.

    Behavior
    --------
    - Treats Date as ISO string (YYYY-MM-DD) for safe lexicographic comparison.
    - After optional cutoff, removes duplicates that only differ by Date by
      keeping the most recent row (max Date) per "same antenna".
    - "Same antenna" is defined as identical values across all columns except "Date".
      (If there are no other columns, it simply keeps the single most recent row.)

    Returns
    -------
    pd.DataFrame
    """
    if "Date" not in df.columns:
        return df

    df = df.copy()
    df["Date"] = df["Date"].astype(str)

    # Optional cutoff
    if date is not None:
        date = str(date)
        df = df[df["Date"] <= date]

    # If nothing left, return early
    if df.empty:
        return df

    # Keep most recent per "antenna identity" (all cols except Date)
    key_cols = [c for c in df.columns if c != "Date"]

    # If Date is the only column, just keep the max Date row
    if not key_cols:
        max_date = df["Date"].max()
        return df[df["Date"] == max_date].reset_index(drop=True)

    # Sort so "most recent" comes first within each group, then drop duplicates
    df = df.sort_values("Date", ascending=False, kind="mergesort")
    df = df.drop_duplicates(subset=key_cols, keep="first")

    return df.reset_index(drop=True)