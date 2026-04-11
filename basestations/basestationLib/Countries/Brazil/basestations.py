"""Brazil adapter: ANATEL SMP licensed stations (Estações Rádio Base).

Data source: ANATEL (Agência Nacional de Telecomunicações) open data portal
- https://www.anatel.gov.br/dadosabertos/PDA/Estacoes_Licenciadas/Estacoes_Licenciadas_SMP.csv
- Dataset page: https://dados.gov.br/dataset/estacoes-licenciadas-a-operar-no-servico-movel-pessoal
- License: Brazilian Open Data (Dados Abertos), free to use with attribution
- Updated daily by ANATEL
- ~110K ERBs (Estações Rádio Base) licensed for SMP (Serviço Móvel Pessoal)

The CSV is semicolon-delimited (common in Brazilian/Portuguese government data).
Key columns in the SMP dataset:
- Prestadora                        : operator/provider name
- Número da Estação                 : station number (used as SiteCode)
- Latitude, Longitude               : decimal degrees (WGS84)
- Altitude                          : ground elevation (m, not antenna height)
- Frequência de Transmissão         : transmit frequency (MHz)
- Frequência de Recepção            : receive frequency (MHz)
- Potência                          : transmit power (Watts or as-published unit)
- Azimute                           : azimuth of main lobe (degrees)
- Tecnologia                        : technology label (GSM, WCDMA, LTE, NR, etc.)
- Altura                            : antenna height above ground (m) — present in SMP CSV
- UF                                : Brazilian state code
- Município                         : municipality name
- Data do Licenciamento             : licensing date

Brazilian mobile operators: Claro, Vivo (Telefônica/Telefonica), TIM, Oi,
Algar Telecom, Sercomtel, Sky, Nextel.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# Direct CSV download from ANATEL open data portal (updated daily).
# The file is typically 50-150 MB uncompressed.
SMP_CSV_URL = "https://www.anatel.gov.br/dadosabertos/PDA/Estacoes_Licenciadas/Estacoes_Licenciadas_SMP.csv"

# Local cache location and TTL
CACHE_PATH = Path.home() / ".cache" / "aegis" / "brazil_anatel_smp.csv"
CACHE_TTL_DAYS = 7

# Brazil bounding box: [min_lon, max_lon, min_lat, max_lat]
BRAZIL_BBOX = [-73.99, -28.85, -33.75, 5.27]

# Canonical operator name mapping (lowercase keyword -> canonical)
_OPERATOR_NORM: dict[str, str] = {
    "claro": "Claro",
    "tim": "TIM",
    "vivo": "Vivo",
    "telefonica": "Vivo",
    "telefônica": "Vivo",
    "oi": "Oi",
    "algar": "Algar",
    "sercomtel": "Sercomtel",
    "nextel": "Nextel",
    "sky": "Sky",
    "brt": "BRT",
}


def _normalize_operator(name: str | None) -> str | None:
    """Map ANATEL Prestadora strings to canonical operator names."""
    if not name:
        return name
    name_lc = name.lower()
    for keyword, canonical in _OPERATOR_NORM.items():
        if keyword in name_lc:
            return canonical
    return name.strip() or None


class BaseStations:
    """Extract antenna data from the ANATEL SMP licensed-station dataset (Brazil).

    Downloads and caches the national ERB CSV from ANATEL's open data portal.
    Filters by bounding box, operator, and technology as requested.

    Parameters
    ----------
    output_folder:
        Directory for any output artefacts (currently unused, reserved for
        compatibility with the basestationLib pipeline).
    bounding_box:
        ``[min_lon, max_lon, min_lat, max_lat]`` filter applied after download.
        Defaults to the full Brazil bounding box.
    operator:
        Case-insensitive substring filter on the Operator column.
    technology:
        Case-insensitive substring filter on the Technology column.
    csv_path:
        Path to a pre-downloaded CSV file. Skips download/cache logic entirely.
    """

    def __init__(
        self,
        output_folder: str = "output/Brazil/",
        bounding_box: list[float] | None = None,
        operator: str | None = None,
        technology: str | None = None,
        csv_path: str | None = None,
        **kwargs,
    ):
        self.output_folder = output_folder
        self.bounding_box = bounding_box or BRAZIL_BBOX
        self.operator = operator
        self.technology = technology
        self.csv_path = Path(csv_path) if csv_path else None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_antennas(self, config: dict | None = None) -> pd.DataFrame:
        """Extract antenna data from the ANATEL SMP dataset.

        Fields available: location (lat/lon), antenna height, azimuth,
        transmit power, frequency, operator, technology, municipality/state.
        Fields missing: electrical tilt, mechanical tilt, gain, beamwidth.
        """
        rows = self._extract()

        if not rows:
            logger.warning("No antenna records extracted for Brazil")
            return pd.DataFrame()

        df = pd.DataFrame(rows)

        if self.operator:
            df = df[df["Operator"].str.contains(self.operator, case=False, na=False)]
        if self.technology:
            df = df[df["Technology"].str.contains(self.technology, case=False, na=False)]

        if df.empty:
            logger.warning("DataFrame is empty after applying operator/technology filters")
            return df

        from basestationLib.utils.create_output_df import create_output_df

        return create_output_df(df, config or {}, {})

    # ------------------------------------------------------------------
    # Download and parse
    # ------------------------------------------------------------------

    def _extract(self) -> list[dict]:
        """Download (or use cached) ANATEL SMP CSV and return standardised rows."""
        try:
            df_raw = self._load_csv()
        except Exception as exc:
            logger.error("Failed to load ANATEL SMP CSV: %s", exc)
            return []

        try:
            return self._parse_df(df_raw)
        except Exception as exc:
            logger.error("Failed to parse ANATEL SMP data: %s", exc)
            return []

    def _load_csv(self) -> pd.DataFrame:
        """Return the raw SMP DataFrame, downloading and caching as needed."""
        # If a local path was supplied, use it directly.
        if self.csv_path and self.csv_path.exists():
            logger.info("Using provided CSV path: %s", self.csv_path)
            return self._read_csv_file(self.csv_path)

        # Use disk cache if it is fresh enough.
        if self._cache_is_fresh():
            logger.info("Using cached ANATEL SMP data from %s", CACHE_PATH)
            return self._read_csv_file(CACHE_PATH)

        # Download the file.
        logger.info("Downloading ANATEL SMP data from %s", SMP_CSV_URL)
        resp = requests.get(SMP_CSV_URL, timeout=300, stream=True)
        resp.raise_for_status()

        chunks: list[bytes] = []
        for chunk in resp.iter_content(chunk_size=1024 * 1024):
            if chunk:
                chunks.append(chunk)
        data = b"".join(chunks)

        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_bytes(data)
        logger.info("Cached ANATEL SMP data to %s (%d bytes)", CACHE_PATH, len(data))

        import io

        return pd.read_csv(
            io.BytesIO(data),
            sep=";",
            dtype=str,
            low_memory=False,
            encoding="latin-1",
        )

    @staticmethod
    def _read_csv_file(path: Path) -> pd.DataFrame:
        """Read the semicolon-delimited ANATEL CSV from disk."""
        return pd.read_csv(
            path,
            sep=";",
            dtype=str,
            low_memory=False,
            encoding="latin-1",
        )

    @staticmethod
    def _cache_is_fresh() -> bool:
        if not CACHE_PATH.exists():
            return False
        age = datetime.now(tz=UTC) - datetime.fromtimestamp(CACHE_PATH.stat().st_mtime, tz=UTC)
        return age < timedelta(days=CACHE_TTL_DAYS)

    def _parse_df(self, df: pd.DataFrame) -> list[dict]:
        """Convert the raw ANATEL CSV DataFrame into standardised row dicts."""
        # Normalise column names: strip whitespace, keep original case for mapping
        df.columns = [c.strip() for c in df.columns]

        logger.info("ANATEL SMP raw: %d records, columns: %s", len(df), list(df.columns))

        # Resolve key column names (case-insensitive)
        lat_col = _find_col(df, "Latitude", "LATITUDE", "LAT")
        lon_col = _find_col(df, "Longitude", "LONGITUDE", "LON")
        station_col = _find_col(df, "Número da Estação", "Numero da Estacao", "NumeroEstacao")
        operator_col = _find_col(df, "Prestadora", "Operadora", "PRESTADORA")
        freq_tx_col = _find_col(
            df,
            "Frequência de Transmissão",
            "Frequencia de Transmissao",
            "FrequenciaTransmissao",
            "Freq_Tx",
        )
        freq_rx_col = _find_col(
            df,
            "Frequência de Recepção",
            "Frequencia de Recepcao",
            "FrequenciaRecepcao",
            "Freq_Rx",
        )
        power_col = _find_col(df, "Potência", "Potencia", "POTENCIA", "Power")
        azimuth_col = _find_col(df, "Azimute", "AZIMUTE", "Azimuth")
        tech_col = _find_col(df, "Tecnologia", "TECNOLOGIA", "Technology")
        height_col = _find_col(df, "Altura", "ALTURA", "AlturaAntena", "Antenna_Height")
        uf_col = _find_col(df, "UF", "Estado", "State")
        muni_col = _find_col(df, "Município", "Municipio", "MUNICIPIO", "City")

        if lat_col is None or lon_col is None:
            logger.error(
                "Latitude/longitude columns not found in ANATEL SMP data. Available columns: %s",
                list(df.columns),
            )
            return []

        # Parse coordinates and drop rows with missing/invalid lat-lon
        df[lat_col] = pd.to_numeric(df[lat_col].str.replace(",", ".", regex=False), errors="coerce")
        df[lon_col] = pd.to_numeric(df[lon_col].str.replace(",", ".", regex=False), errors="coerce")
        df = df.dropna(subset=[lat_col, lon_col])

        # Bounding box filter
        if self.bounding_box:
            min_lon, max_lon, min_lat, max_lat = self.bounding_box
            df = df[
                (df[lon_col] >= min_lon)
                & (df[lon_col] <= max_lon)
                & (df[lat_col] >= min_lat)
                & (df[lat_col] <= max_lat)
            ]
            logger.info("After bbox filter: %d records", len(df))

        if df.empty:
            return []

        logger.info("Building rows from %d ANATEL SMP records", len(df))

        rows = []
        for i, row in df.iterrows():
            lat = _to_float(row.get(lat_col))
            lon = _to_float(row.get(lon_col))
            if lat is None or lon is None:
                continue

            station_num = _str(row.get(station_col)) if station_col else str(i)
            site_code = f"BR_{station_num}" if station_num else f"BR_{i}"

            operator_raw = _str(row.get(operator_col)) if operator_col else None
            operator = _normalize_operator(operator_raw)

            # Prefer the transmit frequency; fall back to receive frequency
            freq_mhz: float | None = None
            if freq_tx_col:
                freq_mhz = _to_float(row.get(freq_tx_col))
            if freq_mhz is None and freq_rx_col:
                freq_mhz = _to_float(row.get(freq_rx_col))

            # Technology: use dataset label if available, else infer from frequency
            tech_raw = _str(row.get(tech_col)) if tech_col else None
            technology = _normalise_technology(tech_raw) if tech_raw else _guess_technology(freq_mhz)

            # Power: ANATEL SMP CSV stores Potência in Watts (floating point)
            power_dbm: float | None = None
            if power_col:
                power_w = _to_float(row.get(power_col))
                if power_w is not None and power_w > 0:
                    import math

                    power_dbm = 10.0 * math.log10(power_w * 1000.0)  # W -> dBm

            height = _to_float(row.get(height_col)) if height_col else None
            azimuth = _to_float(row.get(azimuth_col)) if azimuth_col else None

            uf = _str(row.get(uf_col)) if uf_col else None
            muni = _str(row.get(muni_col)) if muni_col else None
            label_parts = [p for p in [site_code, technology, uf, muni] if p]
            antenna_label = "_".join(label_parts)

            freq_band = _freq_to_band(freq_mhz)

            rows.append(
                {
                    "SiteCode": site_code,
                    "AntennaLabel": antenna_label,
                    "Operator": operator,
                    "Technology": technology,
                    "Latitude": lat,
                    "Longitude": lon,
                    "CenterHeight": height,
                    "Power": power_dbm,
                    "Frequency": freq_mhz,
                    "FrequencyBand": freq_band,
                    "Electrical_Tilt": None,
                    "Mechanical_Tilt": None,
                    "Azimuth": azimuth,
                    "Gain": None,
                    "Horizontal_Beamwidth": None,
                    "Vertical_Beamwidth": None,
                }
            )

        return rows


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _find_col(df: pd.DataFrame, *candidates: str) -> str | None:
    """Return the first matching column name (case-insensitive, accent-tolerant)."""
    import unicodedata

    def _norm(s: str) -> str:
        return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower().strip()

    cols_norm = {_norm(c): c for c in df.columns}
    for cand in candidates:
        key = _norm(cand)
        if key in cols_norm:
            return cols_norm[key]
    return None


def _to_float(val: object) -> float | None:
    """Convert a value to float, handling None/NaN/empty gracefully."""
    if val is None:
        return None
    s = str(val).strip().replace(",", ".")
    if s in ("", "nan", "None", "N/A", "NA", "-", "*"):
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _str(val: object) -> str | None:
    """Convert a value to a stripped string, returning None for blank/null."""
    if val is None:
        return None
    s = str(val).strip()
    return s if s and s not in ("nan", "None", "N/A", "NA", "*") else None


def _normalise_technology(raw: str) -> str:
    """Map ANATEL technology labels to canonical names."""
    raw_up = raw.upper().strip()
    # ANATEL uses NR, LTE, WCDMA, GSM, CDMA labels
    if "NR" in raw_up or "5G" in raw_up:
        return "5G"
    if "LTE" in raw_up or "4G" in raw_up:
        return "4G"
    if "WCDMA" in raw_up or "UMTS" in raw_up or "3G" in raw_up or "HSPA" in raw_up:
        return "3G"
    if "GSM" in raw_up or "2G" in raw_up or "EDGE" in raw_up or "GPRS" in raw_up:
        return "2G"
    if "CDMA" in raw_up:
        return "3G"
    return raw  # preserve unknown labels


def _guess_technology(freq_mhz: float | None) -> str:
    """Heuristic technology label from centre frequency."""
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
    if freq_mhz >= 150:
        return "2G"
    return "4G"


def _freq_to_band(freq_mhz: float | None) -> str | None:
    """Map centre frequency (MHz) to canonical band name."""
    if freq_mhz is None:
        return None
    bands = [
        (450, 470, "Band450MHz"),
        (600, 630, "Band600MHz"),
        (698, 806, "Band700MHz"),
        (824, 894, "Band850MHz"),
        (880, 960, "Band900MHz"),
        (1710, 1880, "Band1800MHz"),
        (1850, 1990, "Band1900MHz"),
        (1920, 2170, "Band2100MHz"),
        (2300, 2400, "Band2300MHz"),
        (2496, 2690, "Band2600MHz"),
        (3300, 3800, "Band3500MHz"),
        (24250, 27500, "Band26GHz"),
    ]
    for lo, hi, name in bands:
        if lo <= freq_mhz <= hi:
            return name
    return f"Band{int(freq_mhz)}MHz"
