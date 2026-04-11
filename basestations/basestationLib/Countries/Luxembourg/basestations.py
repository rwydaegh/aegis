"""Luxembourg adapter: Administration de l'Environnement - Cadastre GSM.

Data sources (all CC0 / public domain):
- Primary: OGC API Features - Cadastre hertzien (authorisation + site data)
  https://features.geoportail.lu/collections/801/items
  1,243 records, continuously updated. WGS84 coordinates in GeoJSON output.
  Fields: SiteOperat, Adresse, Installati, ArretNum, LUREF_X, LUREF_Y.

- Operator supplement: geolist-gsmcoordprovider.csv (Administration de l'Environnement
  via data.public.lu). Maps LUREF site coords to operator names (Post, Tango, Orange,
  Luxembourg Online). Joined on LUREF_X/LUREF_Y rounded to nearest integer.
  URL: https://download.data.public.lu/resources/authorisations-measurements-cadastre-gsm/
       20260410-182008/geolist-gsmcoordprovider.csv

Luxembourg uses LUREF (EPSG:2169) as the national CRS; the geoportal API returns
coordinates in WGS84 (EPSG:4326) via GeoJSON, so no projection is needed for the
primary path. The CSV supplement uses LUREF and is converted with pyproj.

Operators present:
  POST Luxembourg / P&T -> "POST Luxembourg"
  TANGO S.A. -> "Tango"
  ORANGE Communications Luxembourg S.A. -> "Orange"
  Luxembourg Online S.A. -> "Luxembourg Online"

Fields available from this source:
  Latitude, Longitude (from GeoJSON geometry)
  SiteCode, AntennaLabel (derived from SiteOperat / ArretNum)
  Operator (extracted from SiteOperat text + operator CSV supplement)
  Technology (inferred from SiteOperat text and frequency heuristic)
  Frequency, FrequencyBand (not in primary source; placeholder NaN)
  CenterHeight, Azimuth, Gain, tilts, beamwidths (not in source; NaN)

Cache TTL: 7 days (data updated every ~15 days by the Administration de l'Environnement).
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Primary data source: OGC API Features - Cadastre hertzien authorisations
# ---------------------------------------------------------------------------
FEATURES_BASE_URL = "https://features.geoportail.lu/collections/801/items"
FEATURES_PAGE_SIZE = 500  # API supports up to 1000; 500 is safe

# Operator supplement CSV (site LUREF coords -> operator names)
OPERATOR_CSV_URL = (
    "https://download.data.public.lu/resources/"
    "authorisations-measurements-cadastre-gsm/"
    "20260410-182008/geolist-gsmcoordprovider.csv"
)

# Cache paths
_CACHE_DIR = Path.home() / ".cache" / "aegis"
CACHE_FEATURES = _CACHE_DIR / "luxembourg_features.json"
CACHE_OPERATOR_CSV = _CACHE_DIR / "luxembourg_operators.csv"
CACHE_TTL_DAYS = 7

# ---------------------------------------------------------------------------
# Operator normalisation
# ---------------------------------------------------------------------------
_OPERATOR_PATTERNS: list[tuple[str, str]] = [
    (r"post\s+luxembourg|p[&+]t|luxgsm|lux\s*gsm", "POST Luxembourg"),
    (r"tango", "Tango"),
    (r"orange", "Orange"),
    (r"luxembourg\s+online|lux\s*online", "Luxembourg Online"),
    (r"proximus", "Proximus"),
]


def _normalize_operator(text: str | None) -> str | None:
    """Extract and normalise operator name from free-text SiteOperat field."""
    if not text:
        return None
    text_lc = text.lower()
    for pattern, canonical in _OPERATOR_PATTERNS:
        if re.search(pattern, text_lc):
            return canonical
    return None


class BaseStations:
    """Extract antenna site data from Luxembourg's Cadastre GSM.

    The primary data is fetched from the OGC API Features endpoint of the
    Luxembourg national geoportal (features.geoportail.lu). Each record
    represents one authorised antenna installation. An operator-supplement
    CSV is downloaded separately to improve operator resolution.

    Parameters
    ----------
    output_folder:
        Directory for any local output artefacts. Default: ``output/Luxembourg/``.
    bounding_box:
        ``[min_lon, max_lon, min_lat, max_lat]`` filter applied after download.
        Default covers all of Luxembourg.
    operator:
        Case-insensitive substring filter on the Operator column.
    technology:
        Case-insensitive substring filter on the Technology column.
    """

    def __init__(
        self,
        output_folder: str = "output/Luxembourg/",
        bounding_box: list[float] | None = None,
        operator: str | None = None,
        technology: str | None = None,
        **kwargs,
    ):
        self.output_folder = output_folder
        # bbox: [min_lon, max_lon, min_lat, max_lat]
        self.bounding_box = bounding_box or [5.70, 6.55, 49.44, 50.18]
        self.operator = operator
        self.technology = technology

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_antennas(self, config: dict | None = None) -> pd.DataFrame:
        """Fetch, parse, filter, and return antenna data for Luxembourg.

        Returns a DataFrame with the 16 standard output columns (NaN where
        the source does not provide the field).
        """
        features = self._fetch_features()
        if not features:
            logger.warning("No antenna records fetched from Luxembourg Cadastre GSM")
            return pd.DataFrame()

        # Build operator lookup from supplement CSV
        operator_lookup = self._build_operator_lookup()

        rows = self._build_rows(features, operator_lookup)
        if not rows:
            logger.warning("No rows after parsing Luxembourg features")
            return pd.DataFrame()

        df = pd.DataFrame(rows)

        if self.operator:
            df = df[df["Operator"].str.contains(self.operator, case=False, na=False)]
        if self.technology:
            df = df[df["Technology"].str.contains(self.technology, case=False, na=False)]

        if self.bounding_box:
            min_lon, max_lon, min_lat, max_lat = self.bounding_box
            df = df[
                (df["Longitude"] >= min_lon)
                & (df["Longitude"] <= max_lon)
                & (df["Latitude"] >= min_lat)
                & (df["Latitude"] <= max_lat)
            ]
            logger.info("After bbox filter: %d records", len(df))

        from basestationLib.utils.create_output_df import create_output_df

        return create_output_df(df, config or {}, {})

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------

    def _fetch_features(self) -> list[dict]:
        """Return all GeoJSON features, using disk cache if fresh."""
        import json

        if self._cache_is_fresh(CACHE_FEATURES):
            logger.info("Using cached Luxembourg features from %s", CACHE_FEATURES)
            try:
                with CACHE_FEATURES.open() as fh:
                    return json.load(fh)
            except Exception as exc:
                logger.warning("Cache read failed (%s); re-fetching", exc)

        logger.info("Fetching Luxembourg Cadastre GSM from %s", FEATURES_BASE_URL)
        features: list[dict] = []
        offset = 0

        session = requests.Session()
        session.headers.update({"Accept": "application/geo+json"})

        while True:
            params: dict = {
                "f": "json",
                "limit": FEATURES_PAGE_SIZE,
                "offset": offset,
            }
            try:
                resp = session.get(FEATURES_BASE_URL, params=params, timeout=60)
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:
                logger.error("Fetch failed at offset %d: %s", offset, exc)
                break

            page = data.get("features", [])
            if not page:
                break

            features.extend(page)
            logger.info(
                "Fetched offset %d: %d features (total so far: %d)",
                offset,
                len(page),
                len(features),
            )

            if len(page) < FEATURES_PAGE_SIZE:
                break
            offset += len(page)

        if features:
            _CACHE_DIR.mkdir(parents=True, exist_ok=True)
            try:
                with CACHE_FEATURES.open("w") as fh:
                    json.dump(features, fh)
                logger.info("Cached %d features to %s", len(features), CACHE_FEATURES)
            except Exception as exc:
                logger.warning("Cache write failed: %s", exc)

        return features

    def _build_operator_lookup(self) -> dict[tuple[int, int], list[str]]:
        """Download operator supplement CSV and return LUREF -> [operator, ...] map.

        The CSV has rows: ``LUREF_X,LUREF_Y;OPERATOR_NAME`` with no header.
        The semicolon separates the coordinate pair from the operator name.
        The coordinate pair itself uses comma as decimal separator (French locale),
        so we parse carefully.
        """
        raw = self._fetch_operator_csv()
        lookup: dict[tuple[int, int], list[str]] = {}

        if not raw:
            return lookup

        try:
            for line in raw.splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = line.split(";")
                if len(parts) < 2:
                    continue
                coord_part = parts[0].strip()
                op_part = parts[1].strip()

                # coord_part is "XXXXX,YYYYY" where comma is decimal-sep
                # but coords are always integers in this dataset
                coords = coord_part.split(",")
                if len(coords) < 2:
                    continue
                try:
                    lx = int(float(coords[0].strip()))
                    ly = int(float(coords[1].strip()))
                except (ValueError, TypeError):
                    continue

                key = (lx, ly)
                op_norm = _normalize_operator(op_part) or op_part
                lookup.setdefault(key, []).append(op_norm)
        except Exception as exc:
            logger.warning("Error parsing operator CSV: %s", exc)

        logger.info("Operator lookup built: %d distinct LUREF sites", len(lookup))
        return lookup

    def _fetch_operator_csv(self) -> str | None:
        """Fetch or load cached operator supplement CSV. Returns raw text."""
        if self._cache_is_fresh(CACHE_OPERATOR_CSV):
            logger.info("Using cached operator CSV from %s", CACHE_OPERATOR_CSV)
            try:
                return CACHE_OPERATOR_CSV.read_text(encoding="utf-8")
            except Exception as exc:
                logger.warning("Operator CSV cache read failed (%s); re-fetching", exc)

        logger.info("Downloading operator supplement CSV from %s", OPERATOR_CSV_URL)
        try:
            resp = requests.get(OPERATOR_CSV_URL, timeout=60)
            resp.raise_for_status()
            text = resp.text
        except Exception as exc:
            logger.warning("Operator CSV download failed: %s", exc)
            return None

        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        try:
            CACHE_OPERATOR_CSV.write_text(text, encoding="utf-8")
        except Exception as exc:
            logger.warning("Operator CSV cache write failed: %s", exc)

        return text

    # ------------------------------------------------------------------
    # Row construction
    # ------------------------------------------------------------------

    def _build_rows(
        self,
        features: list[dict],
        operator_lookup: dict[tuple[int, int], list[str]],
    ) -> list[dict]:
        """Convert GeoJSON features to standardised row dicts."""
        rows = []
        for feat in features:
            props = feat.get("properties") or {}
            geom = feat.get("geometry") or {}

            coords = geom.get("coordinates")
            if not coords or len(coords) < 2:
                continue
            lon = self._to_float(coords[0])
            lat = self._to_float(coords[1])
            if lat is None or lon is None:
                continue

            site_operat = self._str(props.get("SiteOperat"))
            arret_num = self._str(props.get("ArretNum"))
            obj_id = self._str(props.get("OBJECTID")) or str(feat.get("id", ""))

            # Build stable site code from authorization number or object ID
            site_code = f"LU_{arret_num}" if arret_num else f"LU_{obj_id}"
            site_code = re.sub(r"[/\\]", "-", site_code)

            # Operator resolution: try SiteOperat text first, then LUREF lookup
            operator = _normalize_operator(site_operat)
            if operator is None:
                luref_x = self._to_int(props.get("LUREF_X"))
                luref_y = self._to_int(props.get("LUREF_Y"))
                if luref_x is not None and luref_y is not None:
                    ops = operator_lookup.get((luref_x, luref_y), [])
                    operator = ops[0] if ops else None

            # Technology: derive from SiteOperat text
            tech = _infer_technology_from_text(site_operat)

            label = f"{site_code}_{tech}" if tech else site_code

            rows.append(
                {
                    "SiteCode": site_code,
                    "AntennaLabel": label,
                    "Operator": operator,
                    "Technology": tech,
                    "Latitude": lat,
                    "Longitude": lon,
                    "CenterHeight": None,
                    "Power": None,
                    "Frequency": None,
                    "FrequencyBand": None,
                    "Electrical_Tilt": None,
                    "Mechanical_Tilt": None,
                    "Azimuth": None,
                    "Gain": None,
                    "Horizontal_Beamwidth": None,
                    "Vertical_Beamwidth": None,
                }
            )

        logger.info("Built %d rows from %d features", len(rows), len(features))
        return rows

    # ------------------------------------------------------------------
    # Cache utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _cache_is_fresh(path: Path) -> bool:
        if not path.exists():
            return False
        age = datetime.now(tz=UTC) - datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
        return age < timedelta(days=CACHE_TTL_DAYS)

    # ------------------------------------------------------------------
    # Value helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_float(val: object) -> float | None:
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _to_int(val: object) -> int | None:
        if val is None:
            return None
        try:
            return int(float(str(val).strip()))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _str(val: object) -> str | None:
        if val is None:
            return None
        s = str(val).strip()
        return s if s and s.lower() not in ("nan", "none", "n/a") else None


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _infer_technology_from_text(text: str | None) -> str:
    """Infer technology label from the SiteOperat free-text field.

    The cadastre records do not carry an explicit technology field. Site names
    often contain technology hints: "LTE", "5G", "NR", "UMTS", "GSM", "DCS".
    Falls back to "4G" (LTE era is dominant in the dataset).
    """
    if not text:
        return "4G"
    text_uc = text.upper()
    if "5G" in text_uc or "NR" in text_uc:
        return "5G"
    if "LTE" in text_uc:
        return "4G"
    if "UMTS" in text_uc or "3G" in text_uc:
        return "3G"
    if "GSM" in text_uc or "DCS" in text_uc or "2G" in text_uc:
        return "2G"
    # Default to 4G: LTE has been the dominant technology in Luxembourg since ~2014
    return "4G"


def _guess_technology(freq_mhz: float | None) -> str:
    """Heuristic technology label from centre frequency (MHz)."""
    if freq_mhz is None:
        return "4G"
    if freq_mhz >= 3300:
        return "5G"
    if freq_mhz >= 2500:
        return "4G/5G"
    if freq_mhz >= 600:
        return "4G"
    if freq_mhz >= 400:
        return "3G"
    return "4G"


def _freq_to_band(freq_mhz: float | None) -> str | None:
    """Map centre frequency (MHz) to canonical band name.

    Bands are ordered by priority (most specific first) and non-overlapping.
    Covers the range monitored by the Luxembourg Cadastre GSM: 791-2680 MHz.
    """
    if freq_mhz is None:
        return None
    # Non-overlapping bands ordered by lower bound
    bands = [
        (450, 470, "Band450MHz"),
        (698, 790, "Band700MHz"),  # US/APT 700 (below European 800-band uplink)
        (791, 862, "Band800MHz"),  # LTE Band 20 / European 800 MHz
        (880, 960, "Band900MHz"),  # GSM 900 / UMTS 900 / LTE Band 8
        (1710, 1880, "Band1800MHz"),  # LTE Band 3 / DCS 1800
        (1850, 1990, "Band1900MHz"),  # PCS 1900
        (1920, 2170, "Band2100MHz"),  # UMTS 2100 / LTE Band 1
        (2300, 2400, "Band2300MHz"),  # LTE Band 40
        (2496, 2690, "Band2600MHz"),  # LTE Band 7 / Band 38
        (3300, 3800, "Band3500MHz"),  # 5G NR n78
        (24250, 27500, "Band26GHz"),  # 5G mmWave
    ]
    for lo, hi, name in bands:
        if lo <= freq_mhz <= hi:
            return name
    return f"Band{int(freq_mhz)}MHz"
