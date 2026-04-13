"""Parquet read/write for base station data with provenance columns."""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from aegis.basestation.antenna import AntennaPattern, BaseStation
from aegis.basestation.pattern import synthetic_pattern_from_beamwidth
from aegis.basestation.provenance import (
    COLUMN_TO_FIELD,
    CONFIDENCE_SCORES,
    FieldSource,
)
from aegis.basestation.utils import _sanitize_label

logger = logging.getLogger(__name__)

_PROVENANCE_COLUMNS = [
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

_SOURCE_CONFIDENCE: dict[str, float] = {
    "gov:brussels": CONFIDENCE_SCORES["gov_direct"],
    "gov:flanders": CONFIDENCE_SCORES["gov_direct"],
    "gov:anfr": CONFIDENCE_SCORES["gov_direct"],
    "gov:antenneregister": CONFIDENCE_SCORES["gov_direct"],
    "gov:mastedatabasen": CONFIDENCE_SCORES["gov_report"],
    "gov:bnetza": CONFIDENCE_SCORES["gov_report"],
    "gov:rtr": CONFIDENCE_SCORES["gov_report"],
    "gov:acma": CONFIDENCE_SCORES["gov_report"],
    "ocid": CONFIDENCE_SCORES["crowdsourced"],
    "est:tech+band": CONFIDENCE_SCORES["est_same_dataset"],
    "est:ref": CONFIDENCE_SCORES["est_reference"],
    "missing": CONFIDENCE_SCORES["missing"],
}


def _confidence_for_source(source: str) -> float:
    if source in _SOURCE_CONFIDENCE:
        return _SOURCE_CONFIDENCE[source]
    if source.startswith("gov:"):
        return CONFIDENCE_SCORES["gov_report"]
    if source.startswith("est:"):
        return CONFIDENCE_SCORES["est_reference"]
    return 0.5


def write_raw_parquet(df: pd.DataFrame, path: str) -> None:
    df.to_parquet(path, index=False, engine="pyarrow")
    logger.info("Wrote %d rows to %s", len(df), path)


def write_merged_parquet(df: pd.DataFrame, path: str, source_tag: str = "unknown") -> None:
    out = df.copy()
    for col in _PROVENANCE_COLUMNS:
        src_col = f"{col}_source"
        if src_col not in out.columns:
            if col in out.columns:
                out[src_col] = out[col].apply(lambda v, st=source_tag: "missing" if pd.isna(v) else st)
            else:
                out[src_col] = "missing"
    if "Pattern_source" not in out.columns:
        out["Pattern_source"] = ""
    out.to_parquet(path, index=False, engine="pyarrow")
    logger.info("Wrote %d rows (merged) to %s", len(out), path)


def read_merged_parquet(
    path: str,
    bbox: list[float] | None = None,
    operator: str | None = None,
    technology: str | None = None,
    frequency_band: str | None = None,
    patterns: dict | None = None,
) -> list[BaseStation]:
    df = pd.read_parquet(path, engine="pyarrow")
    if bbox and len(bbox) == 4:
        min_lon, max_lon, min_lat, max_lat = bbox
        df = df[
            (df["Longitude"] >= min_lon)
            & (df["Longitude"] <= max_lon)
            & (df["Latitude"] >= min_lat)
            & (df["Latitude"] <= max_lat)
        ]
    if operator:
        df = df[df["Operator"].str.contains(operator, case=False, na=False)]
    if technology:
        df = df[df["Technology"].str.contains(technology, case=False, na=False)]
    if frequency_band:
        df = df[df["FrequencyBand"] == frequency_band]
    has_provenance = any(f"{c}_source" in df.columns for c in _PROVENANCE_COLUMNS)
    return dataframe_to_basestations(df, patterns=patterns, with_provenance=has_provenance)


def dataframe_to_basestations(
    df: pd.DataFrame,
    patterns: dict | None = None,
    with_provenance: bool = False,
) -> list[BaseStation]:
    patterns = patterns or {}
    n = len(df)
    if n == 0:
        return []

    # Pre-extract columns as arrays for fast iteration (avoids iterrows overhead)
    def _col(name: str, default: str = "") -> np.ndarray:
        if name in df.columns:
            return df[name].fillna(default).to_numpy()
        return np.full(n, default)

    def _col_float(name: str, default: float) -> np.ndarray:
        if name in df.columns:
            return pd.to_numeric(df[name], errors="coerce").fillna(default).to_numpy(dtype=np.float64)
        return np.full(n, default, dtype=np.float64)

    sites = _col("SiteCode")
    labels = _col("AntennaLabel")
    operators = _col("Operator")
    technologies = _col("Technology")
    latitudes = df["Latitude"].to_numpy(dtype=np.float64)
    longitudes = df["Longitude"].to_numpy(dtype=np.float64)
    heights = _col_float("CenterHeight", 10.0)
    powers = _col_float("Power", 30.0)
    gains = _col_float("Gain", 0.0)
    freqs = _col_float("Frequency", 2100.0)
    azimuths = _col_float("Azimuth", 0.0)
    e_tilts = _col_float("Electrical_Tilt", 0.0)
    m_tilts = _col_float("Mechanical_Tilt", 0.0)
    hbws = _col_float("Horizontal_Beamwidth", 65.0)
    vbws = _col_float("Vertical_Beamwidth", 10.0)
    freq_bands = _col("FrequencyBand")
    pattern_sources_col = _col("Pattern_source") if "Pattern_source" in df.columns else None

    # Pre-extract provenance source columns
    prov_src_cols: list[tuple[str, str, np.ndarray]] | None = None
    if with_provenance:
        prov_src_cols = []
        for col in _PROVENANCE_COLUMNS:
            src_col = f"{col}_source"
            field_name = COLUMN_TO_FIELD.get(col, col)
            if src_col in df.columns:
                prov_src_cols.append((field_name, src_col, df[src_col].fillna("missing").to_numpy()))

    result: list[BaseStation] = [None] * n  # type: ignore[list-item]
    for i in range(n):
        site = str(sites[i])
        label = str(labels[i])
        key = _sanitize_label(f"{site}_{label}")

        pattern = None
        pattern_source = ""
        if key in patterns:
            matrix = np.array(patterns[key], dtype=np.float32)
            if matrix.shape == (181, 360):
                pattern = AntennaPattern(gain_dbi=matrix, max_gain_dbi=float(np.nanmax(matrix)))
                pattern_source = str(pattern_sources_col[i]) if pattern_sources_col is not None else "gov"

        gain = float(gains[i])
        if pattern is None:
            hbw = float(hbws[i])
            vbw = float(vbws[i])
            if hbw > 0 and vbw > 0 and gain > 0:
                pattern = synthetic_pattern_from_beamwidth(hbw, vbw, gain)
                pattern_source = "synthetic:gaussian"

        if not pattern_source and pattern_sources_col is not None:
            pattern_source = str(pattern_sources_col[i])

        prov: tuple[tuple[str, FieldSource], ...] = ()
        if prov_src_cols is not None:
            prov = tuple(
                (field_name, FieldSource(origin=str(src_arr[i]), confidence=_confidence_for_source(str(src_arr[i]))))
                for field_name, _, src_arr in prov_src_cols
            )

        fb = str(freq_bands[i])
        if fb == "nan":
            fb = ""

        result[i] = BaseStation(
            site_code=site,
            antenna_label=label,
            operator=str(operators[i]),
            technology=str(technologies[i]),
            latitude=float(latitudes[i]),
            longitude=float(longitudes[i]),
            height_m=float(heights[i]),
            eirp_dbm=float(powers[i]),
            gain_dbi=gain,
            freq_mhz=float(freqs[i]),
            azimuth_deg=float(azimuths[i]),
            electrical_tilt_deg=float(e_tilts[i]),
            mechanical_tilt_deg=float(m_tilts[i]),
            horizontal_beamwidth_deg=float(hbws[i]),
            vertical_beamwidth_deg=float(vbws[i]),
            pattern=pattern,
            frequency_band=fb,
            provenance=prov,
            pattern_source=pattern_source,
        )
    logger.info("Converted %d rows to BaseStation objects", len(result))
    return result
