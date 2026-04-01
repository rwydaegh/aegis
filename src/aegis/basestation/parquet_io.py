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
from aegis.basestation.utils import _safe_float, _sanitize_label

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
    result = []
    for _, row in df.iterrows():
        site = str(row.get("SiteCode", ""))
        label = str(row.get("AntennaLabel", ""))
        pattern = None
        pattern_source = ""
        key = _sanitize_label(f"{site}_{label}")
        if key in patterns:
            matrix = np.array(patterns[key], dtype=np.float32)
            if matrix.shape == (181, 360):
                pattern = AntennaPattern(gain_dbi=matrix, max_gain_dbi=float(np.nanmax(matrix)))
                pattern_source = str(row.get("Pattern_source", "gov"))
        gain = _safe_float(row.get("Gain"), 0.0)
        if pattern is None:
            hbw = _safe_float(row.get("Horizontal_Beamwidth"), 0.0)
            vbw = _safe_float(row.get("Vertical_Beamwidth"), 0.0)
            if hbw > 0 and vbw > 0 and gain > 0:
                pattern = synthetic_pattern_from_beamwidth(hbw, vbw, gain)
                pattern_source = "synthetic:gaussian"
        if not pattern_source and "Pattern_source" in df.columns:
            pattern_source = str(row.get("Pattern_source", ""))
        prov: tuple[tuple[str, FieldSource], ...] = ()
        if with_provenance:
            prov_list = []
            for col in _PROVENANCE_COLUMNS:
                src_col = f"{col}_source"
                field_name = COLUMN_TO_FIELD.get(col, col)
                if src_col in df.columns:
                    src_val = str(row.get(src_col, "missing"))
                    conf = _confidence_for_source(src_val)
                    prov_list.append((field_name, FieldSource(origin=src_val, confidence=conf)))
            prov = tuple(prov_list)
        fb = str(row.get("FrequencyBand", ""))
        if fb == "nan" or pd.isna(row.get("FrequencyBand")):
            fb = ""
        result.append(
            BaseStation(
                site_code=site,
                antenna_label=label,
                operator=str(row.get("Operator", "")),
                technology=str(row.get("Technology", "")),
                latitude=float(row["Latitude"]),
                longitude=float(row["Longitude"]),
                height_m=_safe_float(row.get("CenterHeight"), 10.0),
                eirp_dbm=_safe_float(row.get("Power"), 30.0),
                gain_dbi=gain,
                freq_mhz=_safe_float(row.get("Frequency"), 2100.0),
                azimuth_deg=_safe_float(row.get("Azimuth"), 0.0),
                electrical_tilt_deg=_safe_float(row.get("Electrical_Tilt"), 0.0),
                mechanical_tilt_deg=_safe_float(row.get("Mechanical_Tilt"), 0.0),
                horizontal_beamwidth_deg=_safe_float(row.get("Horizontal_Beamwidth"), 65.0),
                vertical_beamwidth_deg=_safe_float(row.get("Vertical_Beamwidth"), 10.0),
                pattern=pattern,
                frequency_band=fb,
                provenance=prov,
                pattern_source=pattern_source,
            )
        )
    logger.info("Converted %d rows to BaseStation objects", len(result))
    return result
