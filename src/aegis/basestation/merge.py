"""Merge multiple base station sources with spatial dedup and provenance tagging."""

from __future__ import annotations

import logging
import math

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from aegis.basestation.parquet_io import _PROVENANCE_COLUMNS

logger = logging.getLogger(__name__)

_OPERATOR_ALIASES: dict[str, str] = {
    "be:proximus": "proximus",
    "be:orange": "orange",
    "be:telenet": "telenet",
    "proximus group": "proximus",
    "orange belgium": "orange",
}

_R_EARTH = 6_371_000.0


def normalize_operator(name: str | None) -> str:
    if name is None or pd.isna(name):
        return "unknown"
    s = str(name).strip().lower()
    if not s:
        return "unknown"
    return _OPERATOR_ALIASES.get(s, s)


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return _R_EARTH * 2 * math.asin(math.sqrt(a))


def _project_to_metres(lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
    """Equirectangular projection of lat/lon arrays to (N, 2) metres."""
    lat_rad = np.radians(lats)
    lon_rad = np.radians(lons)
    cos_lat = np.cos(lat_rad)
    x = lon_rad * cos_lat * _R_EARTH
    y = lat_rad * _R_EARTH
    return np.column_stack([x, y])


def _bfs_cluster_labels(
    neighbor_lists: list[list[int]],
    norm_ops: np.ndarray,
    freq_bands: np.ndarray | None,
) -> np.ndarray:
    """Assign cluster labels via BFS over neighbor lists, sharing operator+freq."""
    n = len(neighbor_lists)
    labels = np.full(n, -1, dtype=np.intp)
    cluster_id = 0
    has_fb = freq_bands is not None

    for seed in range(n):
        if labels[seed] >= 0:
            continue
        labels[seed] = cluster_id
        queue = [seed]
        head = 0
        while head < len(queue):
            cur = queue[head]
            head += 1
            for j in neighbor_lists[cur]:
                if labels[j] >= 0 or norm_ops[j] != norm_ops[seed]:
                    continue
                if has_fb:
                    fb_seed = freq_bands[seed]
                    fb_j = freq_bands[j]
                    if pd.notna(fb_seed) and pd.notna(fb_j) and fb_seed != fb_j:
                        continue
                labels[j] = cluster_id
                queue.append(j)
        cluster_id += 1
    return labels


def _merge_cluster_rows(group: pd.DataFrame) -> pd.Series:
    """Merge a cluster: keep first row, fill NaNs from subsequent rows."""
    if len(group) == 1:
        return group.iloc[0]
    merged = group.iloc[0].copy()
    for idx in range(1, len(group)):
        other = group.iloc[idx]
        for col in merged.index:
            if col in ("_norm_op", "_cluster"):
                continue
            if pd.isna(merged[col]) and pd.notna(other[col]):
                merged[col] = other[col]
    return merged


def spatial_dedup(df: pd.DataFrame, distance_m: float = 50) -> pd.DataFrame:
    """Spatially deduplicate antennas of the same operator within *distance_m*.

    Uses a cKDTree in projected (x, y) coordinates for O(n log n) neighbor
    lookups instead of the previous O(n^2) pairwise scan.
    """
    if df.empty:
        return df
    df = df.copy()
    df["_norm_op"] = df["Operator"].apply(normalize_operator)

    coords = _project_to_metres(
        df["Latitude"].to_numpy(dtype=np.float64),
        df["Longitude"].to_numpy(dtype=np.float64),
    )
    tree = cKDTree(coords)
    neighbor_lists = tree.query_ball_tree(tree, r=distance_m)

    freq_bands = df["FrequencyBand"].to_numpy() if "FrequencyBand" in df.columns else None
    labels = _bfs_cluster_labels(neighbor_lists, df["_norm_op"].to_numpy(), freq_bands)

    df["_cluster"] = labels
    merged_rows = [_merge_cluster_rows(g) for _, g in df.groupby("_cluster", sort=False)]

    result = pd.DataFrame(merged_rows).reset_index(drop=True)
    result.drop(columns=["_norm_op", "_cluster"], inplace=True, errors="ignore")
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
