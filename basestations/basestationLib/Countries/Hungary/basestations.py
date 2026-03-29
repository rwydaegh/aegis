import os
import re
import warnings
from datetime import datetime, timezone

import numpy as np
import pandas as pd

try:
    from ...utils import (
        create_output_df,
        create_session,
        create_unique_file_identifier,
        format_date_only,
        http_get_json,
    )
except Exception:  # pragma: no cover
    import sys

    sys.path.insert(
        0,
        os.path.dirname(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
        ),
    )
    from basestationLib.utils import (  # type: ignore
        create_output_df,
        create_session,
        create_unique_file_identifier,
        format_date_only,
        http_get_json,
    )


current_folder = os.path.dirname(os.path.abspath(__file__))

# OpenStreetMap/Hungary community export with OpenCellID-derived tags.
GEOJSON_URL = "http://cellavadasz.openstreetmap.hu/opencellid/sites/overpass.geojson"

_DISCLAIMER_INCOMPLETE_BAND_DATA = (
    "HUNGARY DATASET DISCLAIMER:\n 1) Open-sourced data: Mind accuracy \n 2) Source GeoJSON does not consistently include "
    "frequency/band/technology fields. For incomplete records, this extractor assigns all plausible "
    "bands for detected 2G/3G/4G/5G technologies as an assumption (if technology not available, all techs are added). \n 3) Operators are not always known: Filled in UNKOWN"
)

_LTE_BAND_TO_FREQ_MHZ = {
    "1": 2140.0,
    "3": 1842.5,
    "7": 2637.5,
    "8": 942.5,
    "20": 806.0,
    "28": 773.0,
}

_LTE_BAND_TO_NAME = {
    "1": "Band2100MHz",
    "3": "Band1800MHz",
    "7": "Band2600MHz",
    "8": "Band900MHz",
    "20": "Band800MHz",
    "28": "Band700MHz",
}

# Fallback possible bands per RAT when source does not provide explicit per-tech band.
_POSSIBLE_BANDS_BY_TECH = {
    "2G": [
        (942.5, "Band900MHz"),
        (1842.5, "Band1800MHz"),
    ],
    "3G": [
        (947.5, "Band900MHz"),
        (2140.0, "Band2100MHz"),
    ],
    "4G": [
        (773.0, "Band700MHz"),
        (806.0, "Band800MHz"),
        (942.5, "Band900MHz"),
        (1842.5, "Band1800MHz"),
        (2140.0, "Band2100MHz"),
        (2637.5, "Band2600MHz"),
    ],
    "5G": [
        (773.0, "Band700MHz"),
        (2140.0, "Band2100MHz"),
        (3600.0, "Band3600MHz"),
        (26500.0, "Band26000MHz"),
    ],
    "UNKNOWN": [
        (np.nan, "Unknown (2G/3G/4G/5G)"),
    ],
}


def _unique_keep_order(values):
    out = []
    seen = set()
    for v in values:
        if v is None:
            continue
        s = str(v).strip()
        if not s:
            continue
        if s not in seen:
            out.append(s)
            seen.add(s)
    return out


def _split_multi(value):
    if value is None:
        return []
    return _unique_keep_order(
        re.split(r"[;,|/]+", str(value).replace("\n", " "))
    )


def _parse_first_number(value):
    if value is None:
        return np.nan
    s = str(value).strip().replace(",", ".")
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    if not m:
        return np.nan
    try:
        return float(m.group(0))
    except Exception:
        return np.nan


def _parse_frequency_to_mhz(value):
    if value is None:
        return np.nan

    s = str(value).strip().lower().replace(",", ".")
    nums = re.findall(r"\d+(?:\.\d+)?", s)
    if not nums:
        return np.nan

    vals = [float(x) for x in nums]
    freq = vals[0] if len(vals) == 1 else (vals[0] + vals[1]) / 2.0

    if "ghz" in s:
        freq *= 1000.0
    elif "khz" in s:
        freq /= 1000.0
    elif "hz" in s and "mhz" not in s:
        freq /= 1_000_000.0
    return float(freq)


def _infer_band_from_mhz(freq_mhz):
    if freq_mhz is None or not np.isfinite(freq_mhz):
        return np.nan
    if 758 <= freq_mhz <= 803:
        return "Band700MHz"
    if 791 <= freq_mhz <= 821:
        return "Band800MHz"
    if 925 <= freq_mhz <= 960:
        return "Band900MHz"
    if 1805 <= freq_mhz <= 1880:
        return "Band1800MHz"
    if 2110 <= freq_mhz <= 2170:
        return "Band2100MHz"
    if 2570 <= freq_mhz <= 2690:
        return "Band2600MHz"
    if 3400 <= freq_mhz <= 3800:
        return "Band3600MHz"
    return np.nan


def _extract_lon_lat(feature):
    geom = feature.get("geometry") or {}
    gtype = geom.get("type")
    coords = geom.get("coordinates") or []

    lon = np.nan
    lat = np.nan

    if gtype == "Point" and isinstance(coords, list) and len(coords) >= 2:
        lon, lat = coords[0], coords[1]
    elif gtype == "LineString" and isinstance(coords, list) and coords:
        points = [p for p in coords if isinstance(p, (list, tuple)) and len(p) >= 2]
        if points:
            lon = float(np.mean([float(p[0]) for p in points]))
            lat = float(np.mean([float(p[1]) for p in points]))

    props = feature.get("properties") or {}
    if not np.isfinite(lon):
        lon = _parse_first_number(props.get("lon"))
    if not np.isfinite(lat):
        lat = _parse_first_number(props.get("lat"))

    return lon, lat


def _normalize_operator(operator):
    op = str(operator).strip()
    low = op.lower()
    if not op or op == "??":
        print(op)
        return "UNKNOWN"
    if "telekom" in low or "westel" in low:
        return "Telekom"
    if "yettel" in low or "telenor" in low:
        return "Yettel"
    if "vodafone" in low or low == "one" or " digi" in f" {low}":
        return "One"
    return op


def _operator_from_mnc(value):
    out = []
    for token in _split_multi(value):
        num = re.sub(r"[^0-9]", "", token)
        if num == "01":
            out.append("Yettel")
        elif num == "30":
            out.append("Telekom")
        elif num == "70":
            out.append("One")
    return _unique_keep_order(out)


def _extract_operators(tags):
    operators = []

    for key in ["operator", "communication:operator", "monitoring:operator"]:
        operators.extend(_split_multi(tags.get(key)))

    # infer from operator-specific reference keys when operator is missing
    if tags.get("ref:one") or tags.get("ref:vodafone") or tags.get("ref:digi"):
        operators.append("One")
    if tags.get("ref:yettel") or tags.get("ref:telenor"):
        operators.append("Yettel")
    if tags.get("ref:telekom"):
        operators.append("Telekom")

    if not operators and tags.get("MNC"):
        operators.extend(_operator_from_mnc(tags.get("MNC")))

    operators = [_normalize_operator(op) for op in operators]
    operators = _unique_keep_order(operators)
    return operators if operators else ["UNKNOWN"]


def _normalize_technology_token(token):
    t = str(token).strip().lower()
    if not t or t in {"yes", "no", "n/a", "na", "none"}:
        return None
    if "gsm" in t:
        return "2G"
    if "umts" in t or "wcdma" in t:
        return "3G"
    if "lte" in t or "e-utra" in t:
        return "4G"
    if t == "nr" or t.startswith("5g"):
        return "5G"
    return token


def _extract_technologies(tags):
    techs = []

    # Explicit technology tags (only dedicated keys, not ref:* keys)
    for key in ["communication:mobile_phone", "mobile_phone"]:
        val = tags.get(key)
        for tok in _split_multi(val):
            mapped = _normalize_technology_token(tok)
            if mapped:
                techs.append(mapped)

    # Infer from cell-id namespaces
    if tags.get("gsm:cellid"):
        techs.append("2G")
    if tags.get("umts:cellid"):
        techs.append("3G")
    if tags.get("lte:cellid"):
        techs.append("4G")
    if tags.get("nr:cellid"):
        techs.append("5G")

    techs = _unique_keep_order(techs)
    return techs


def _feature_is_mobile(tags):
    mobile_value = str(tags.get("communication:mobile_phone") or tags.get("mobile_phone") or "").strip().lower()
    mobile_is_explicit_no = mobile_value in {"no", "false", "0"}

    mobile_indicators = [
        (not mobile_is_explicit_no) and bool(mobile_value),
        tags.get("gsm:cellid"),
        tags.get("umts:cellid"),
        tags.get("lte:cellid"),
        tags.get("nr:cellid"),
    ]
    return any(v for v in mobile_indicators)


def _extract_site_code(tags, feature_id, operator):
    op = _normalize_operator(operator)
    if op == "One":
        preferred = ["ref:one", "ref:vodafone", "ref:digi"]
    elif op == "Yettel":
        preferred = ["ref:yettel", "ref:telenor"]
    elif op == "Telekom":
        preferred = ["ref:telekom"]
    else:
        preferred = []

    generic = ["ref", "ref:one", "ref:yettel", "ref:telekom", "ref:vodafone", "ref:telenor", "ref:digi"]

    for k in preferred + generic:
        if tags.get(k):
            return str(_split_multi(tags.get(k))[0]).strip()

    return str(feature_id)


def _extract_frequency_records(tags, technology):
    records = []

    # For LTE we can reliably map lte:band to center DL frequencies.
    if technology == "4G" and tags.get("lte:band"):
        for b in _split_multi(tags.get("lte:band")):
            band_num = re.sub(r"[^0-9]", "", b)
            if not band_num:
                continue
            freq = _LTE_BAND_TO_FREQ_MHZ.get(band_num, np.nan)
            band_name = _LTE_BAND_TO_NAME.get(band_num, f"Band{band_num}MHz")
            records.append((freq, band_name))

    # Generic fallback frequency if present.
    if not records and tags.get("frequency"):
        freq = _parse_frequency_to_mhz(tags.get("frequency"))
        # Keep only plausible cellular ranges to avoid unrelated radio tags.
        if np.isfinite(freq) and 600.0 <= float(freq) <= 40_000.0:
            inferred = _infer_band_from_mhz(freq)
            records.append((freq, inferred if pd.notna(inferred) else "Unknown (2G/3G/4G/5G)"))

    # Requested behavior: if band cannot be extracted explicitly, emit all plausible
    # generation bands for the detected technology.
    if not records:
        records = list(_POSSIBLE_BANDS_BY_TECH.get(technology, _POSSIBLE_BANDS_BY_TECH["UNKNOWN"]))

    # Deduplicate by FrequencyBand while keeping order.
    out = []
    seen = set()
    for freq, band in records:
        band_key = str(band)
        if band_key in seen:
            continue
        seen.add(band_key)
        out.append((freq, band))
    return out


def _sanitize_label_token(value):
    s = str(value).strip()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^0-9A-Za-z_\-.]", "", s)
    return s[:80] if s else "UNK"


def _feature_to_rows(feature):
    props = feature.get("properties") or {}
    tags = props.get("tags") or {}

    if not _feature_is_mobile(tags):
        return []

    lon, lat = _extract_lon_lat(feature)
    if not (np.isfinite(lon) and np.isfinite(lat)):
        return []

    operators = _extract_operators(tags)
    technologies = _extract_technologies(tags)
    if not technologies:
        # assume all of them are there
        technologies = ["2G", "3G", "4G", "5G"]

    feature_id = props.get("id") or feature.get("id") or "unknown"
    center_height = _parse_first_number(tags.get("height"))
    if not np.isfinite(center_height):
        center_height = _parse_first_number(tags.get("est_height"))
    power = _parse_first_number(tags.get("power"))

    rows = []
    for operator in operators:
        site_code_raw = _extract_site_code(tags, feature_id, operator)
        site_code_raw = _sanitize_label_token(site_code_raw)

        for technology in technologies:
            for frequency, frequency_band in _extract_frequency_records(tags, technology):
                freq_tag = ""
                if frequency_band is not None and pd.notna(frequency_band):
                    freq_tag = f"_{_sanitize_label_token(frequency_band)}"

                rows.append(
                    {
                        "SiteCode": f"SITE({site_code_raw})",
                        "AntennaLabel": (
                            f"ANT({site_code_raw}_{_sanitize_label_token(operator)}"
                            f"_{_sanitize_label_token(technology)}{freq_tag})"
                        ),
                        "Operator": operator,
                        "Technology": technology,
                        "Latitude": float(lat),
                        "Longitude": float(lon),
                        "CenterHeight": center_height,
                        "Power": power,
                        "Frequency": frequency,
                        "FrequencyBand": frequency_band,
                        "Azimuth": "isotropic",
                    }
                )

    return rows


def _extract_hungary_raw_antennas(geojson_url: str):
    session = create_session(pool_maxsize=32)
    data = http_get_json(session, geojson_url, timeout=(8, 60))
    session.close()

    features = (data or {}).get("features") or []
    rows = []
    for feature in features:
        rows.extend(_feature_to_rows(feature))

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


class BaseStations:
    """Hungary base station extractor using the OSM/OpenCellID community GeoJSON."""

    def __init__(
        self,
        operator=None,
        technology=None,
        bounding_box=None,
        frequency_range=[0, np.inf],
        frequency_band=None,
        date=datetime.now(timezone.utc),
        raw_antenna_cache_file: str = os.path.join(current_folder, "all.pkl"),
        pattern_file: str = None,
        output_folder: str = "output/hungary/",
        max_workers: int = 1,
        file_identifier=None,
        geojson_url: str = GEOJSON_URL,
    ):
        os.makedirs(output_folder, exist_ok=True)

        self.operator = operator
        self.technology = technology
        self.bounding_box = bounding_box
        self.frequency_range = frequency_range
        self.frequency_band = frequency_band
        self.date = format_date_only(date)
        self.raw_antenna_cache_file = raw_antenna_cache_file
        self.pattern_file = pattern_file
        self.output_folder = output_folder
        self.max_workers = max(1, int(max_workers))
        self.geojson_url = geojson_url

        self.antennas = pd.DataFrame()

        if file_identifier is None:
            self.file_identifier = create_unique_file_identifier(self)
        else:
            self.file_identifier = file_identifier

    def extract_antennas(self, config=None):
        """Fetch Hungary antennas, standardize with create_output_df, and save CSV."""
        print(70*"-")
        warnings.warn(_DISCLAIMER_INCOMPLETE_BAND_DATA, UserWarning, stacklevel=2)
        print(70*"-")
        save_cache = (
            self.operator is None
            and self.technology is None
            and self.bounding_box is None
            and self.frequency_band is None
            and (
                self.frequency_range == [0, np.inf]
                or np.array_equal(self.frequency_range, [0, np.inf])
            )
        )

        if self.raw_antenna_cache_file and os.path.exists(self.raw_antenna_cache_file):
            try:
                self.antennas = pd.read_pickle(self.raw_antenna_cache_file)
                print(f"Loaded cached antenna data from {self.raw_antenna_cache_file}")
            except Exception as e:
                print(f"Warning: failed to load cache {self.raw_antenna_cache_file}: {e}")

        if self.antennas is None or self.antennas.empty:
            self.antennas = _extract_hungary_raw_antennas(self.geojson_url)
            if self.antennas.empty:
                print("No Hungarian mobile base station rows extracted from source GeoJSON")

        df = self.antennas.copy()
        filter_args = {
            "operator": self.operator,
            "technology": self.technology,
            "bounding_box": self.bounding_box,
            "frequency_range": self.frequency_range,
            "frequency_band": self.frequency_band,
            "date": self.date,
        }
        self.antennas = create_output_df(df, config, filter_args=filter_args).copy()

        if save_cache and self.raw_antenna_cache_file:
            try:
                os.makedirs(os.path.dirname(self.raw_antenna_cache_file) or ".", exist_ok=True)
                pd.to_pickle(self.antennas, self.raw_antenna_cache_file)
                print(f"Saved raw antenna cache to {self.raw_antenna_cache_file}")
            except Exception as e:
                print(f"Warning: failed to save cache: {e}")

        out_csv = (
            os.path.join(self.output_folder, f"{self.file_identifier}_antennas.csv")
            if self.output_folder
            else None
        )
        if out_csv:
            try:
                os.makedirs(os.path.dirname(out_csv), exist_ok=True)
                self.antennas.to_csv(out_csv, index=False)
                print(f"Saved output CSV to {out_csv}")
            except Exception as e:
                print(f"Warning: failed to save output CSV: {e}")

        return self.antennas


if __name__ == "__main__":
    bs = BaseStations(max_workers=1)
    out = bs.extract_antennas(config=None)
    print(out.head())
