"""Merge multiple base station sources with spatial dedup and provenance tagging."""

from __future__ import annotations

import logging
import math

import pandas as pd

from aegis.basestation.parquet_io import _PROVENANCE_COLUMNS

logger = logging.getLogger(__name__)

_OPERATOR_ALIASES: dict[str, str] = {
    "be:proximus": "proximus",
    "be:orange": "orange",
    "be:telenet": "telenet",
    "proximus group": "proximus",
    "orange belgium": "orange",
}


def normalize_operator(name: str | None) -> str:
    if name is None or (isinstance(name, float) and math.isnan(name)):
        return "unknown"
    s = str(name).strip().lower()
    if not s:
        return "unknown"
    return _OPERATOR_ALIASES.get(s, s)


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371_000.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def spatial_dedup(df: pd.DataFrame, distance_m: float = 50) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df["_norm_op"] = df["Operator"].apply(normalize_operator)
    merged_rows = []
    used = set()
    for i, row_i in df.iterrows():
        if i in used:
            continue
        cluster = [row_i]
        used.add(i)
        for j, row_j in df.iterrows():
            if j in used or j <= i:
                continue
            if row_i["_norm_op"] != row_j["_norm_op"]:
                continue
            fb_i = row_i.get("FrequencyBand", "")
            fb_j = row_j.get("FrequencyBand", "")
            if pd.notna(fb_i) and pd.notna(fb_j) and fb_i != fb_j:
                continue
            dist = _haversine_m(
                row_i["Latitude"],
                row_i["Longitude"],
                row_j["Latitude"],
                row_j["Longitude"],
            )
            if dist <= distance_m:
                cluster.append(row_j)
                used.add(j)
        if len(cluster) == 1:
            merged_rows.append(cluster[0])
        else:
            merged = cluster[0].copy()
            for other in cluster[1:]:
                for col in merged.index:
                    if col == "_norm_op":
                        continue
                    if pd.isna(merged[col]) and pd.notna(other[col]):
                        merged[col] = other[col]
            merged_rows.append(merged)
    result = pd.DataFrame(merged_rows).reset_index(drop=True)
    result.drop(columns=["_norm_op"], inplace=True, errors="ignore")
    return result


def merge_sources(
    sources: list[tuple[pd.DataFrame, str, int]],
    distance_m: float = 50,
) -> pd.DataFrame:
    sources = sorted(sources, key=lambda x: x[2])
    tagged_dfs = []
    for df, source_tag, _priority in sources:
        df = df.copy()
        for col in _PROVENANCE_COLUMNS:
            src_col = f"{col}_source"
            if src_col not in df.columns:
                if col in df.columns:
                    df[src_col] = df[col].apply(lambda v, st=source_tag: "missing" if pd.isna(v) else st)
                else:
                    df[src_col] = "missing"
        if "Pattern_source" not in df.columns:
            df["Pattern_source"] = ""
        tagged_dfs.append(df)
    combined = pd.concat(tagged_dfs, ignore_index=True)
    return spatial_dedup(combined, distance_m=distance_m)


def estimate_with_provenance(
    df: pd.DataFrame,
    reference_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    NUMERIC_COLS = [
        "Power",
        "Electrical_Tilt",
        "Mechanical_Tilt",
        "Gain",
        "Horizontal_Beamwidth",
        "Vertical_Beamwidth",
    ]
    df = df.copy()
    present_cols = [c for c in NUMERIC_COLS if c in df.columns]
    for col in present_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    has_fb = "FrequencyBand" in df.columns and df["FrequencyBand"].notna().any()

    # --- Phase 1: fill from own (Technology, FrequencyBand) group medians ---
    if has_fb and present_cols:
        # Rows that can participate in groupby (both keys non-null)
        valid_keys = df["Technology"].notna() & df["FrequencyBand"].notna()
        group_medians = (
            df.loc[valid_keys]
            .groupby(
                ["Technology", "FrequencyBand"],
            )[present_cols]
            .transform("median")
        )

        for col in present_cols:
            was_nan = df[col].isna()
            # Only fill where the row had valid keys AND the median is non-NaN
            filled = group_medians[col]
            fill_mask = was_nan & valid_keys & filled.notna()
            if not fill_mask.any():
                continue
            df.loc[fill_mask, col] = filled[fill_mask]
            src_col = f"{col}_source"
            if src_col in df.columns:
                df.loc[fill_mask, src_col] = "est:tech+band"

    # --- Phase 2: fill remaining NaNs from reference_df medians ---
    if reference_df is not None:
        reference_df = reference_df.copy()
        ref_present = [c for c in NUMERIC_COLS if c in reference_df.columns]
        for col in ref_present:
            reference_df[col] = pd.to_numeric(reference_df[col], errors="coerce")

        ref_has_fb = "FrequencyBand" in reference_df.columns and reference_df["FrequencyBand"].notna().any()
        if ref_has_fb:
            ref_medians = reference_df.groupby(["Technology", "FrequencyBand"])[ref_present].median()
            # Build a lookup by mapping (Technology, FrequencyBand) -> median values
            valid_keys = df["Technology"].notna() & df["FrequencyBand"].notna()
            # Create a MultiIndex from the df rows to align with ref_medians
            df_keys = pd.MultiIndex.from_arrays(
                [df.loc[valid_keys, "Technology"], df.loc[valid_keys, "FrequencyBand"]],
            )
            # Reindex reference medians to match df rows (NaN where no match)
            ref_aligned = ref_medians.reindex(df_keys)
            ref_aligned.index = df.loc[valid_keys].index

            for col in present_cols:
                if col not in ref_present:
                    continue
                was_nan = df[col].isna()
                if not was_nan.any():
                    continue
                ref_vals = ref_aligned[col]
                fill_mask = was_nan & valid_keys & ref_vals.notna()
                if not fill_mask.any():
                    continue
                df.loc[fill_mask, col] = ref_vals[fill_mask]
                src_col = f"{col}_source"
                if src_col in df.columns:
                    df.loc[fill_mask, src_col] = "est:ref"

    return df
