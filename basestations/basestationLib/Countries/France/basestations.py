"""France adapter: ANFR bulk download (data.anfr.fr).

Data source: ANFR Etalab open data export
- https://data.anfr.fr/api/datasets/anfr_data_export_etalab/
- License: Etalab Open License v2.0 (commercial use permitted)
- Updated monthly by ANFR

The bulk download contains all radioelectric installations in France as
semicolon-delimited TXT files inside a ZIP archive. This replaces the
previous approach of scraping the CartoRadio API one site at a time
(~130K HTTP requests, 17+ hours, frequent rate limiting).

Fallback: set use_cartoradio=True in extract_antennas() to use the old
per-site CartoRadio API path (not recommended).
"""

from __future__ import annotations

import io
import logging
import os
import re
import zipfile
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from tqdm import tqdm
from urllib3.util.retry import Retry

from ...utils import (
    create_output_df,
    create_unique_file_identifier,
    format_date_only,
    same_operator,
)

logger = logging.getLogger(__name__)

current_folder = os.path.dirname(os.path.abspath(__file__))

# ANFR bulk download URLs (Etalab open data, updated monthly)
ANFR_DATA_ZIP_URL = (
    "https://data.anfr.fr/api/datasets/anfr_data_export_etalab/"
    "attachments/export_etalab_data_zip/"
)
ANFR_REF_ZIP_URL = (
    "https://data.anfr.fr/api/datasets/anfr_data_export_etalab/"
    "attachments/export_etalab_ref_zip/"
)

# Mobile operator ADM_IDs in the ANFR dataset
MOBILE_OPERATOR_IDS = {
    6: "BOUYGUES TELECOM",
    23: "ORANGE",
    137: "SFR",
    240: "FREE MOBILE",
}

# Technology patterns to keep (mobile cellular only)
MOBILE_TECH_PATTERNS = re.compile(
    r"\b(LTE|UMTS|WCDMA|GSM|5G\s*NR|NR)\b", re.IGNORECASE
)

# Metropolitan France bounding box (lat/lon)
METRO_FRANCE_LAT = (41.0, 52.0)
METRO_FRANCE_LON = (-6.0, 10.0)


def create_session(timeout=10, retries=5):
    """Create a requests session with connection pooling and automatic retries."""
    session = requests.Session()
    retry_strategy = Retry(
        total=retries,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        backoff_factor=1,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def _select_center_dl_freq_mhz(bandes):
    """
    Given a list of 'bandes' from Cartoradio, determine the downlink (DL)
    center frequency in MHz, handling:
      - 1 band  (TDD, e.g. 5G 3.5 GHz)
      - 2 bands (UL + DL)
      - 4 or 5 bands (fragmented DL spectrum)
      - any arbitrary number of bands

    Returns
    -------
    center_freq_mhz : float
        Representative DL center frequency in MHz for ray-tracing.
    """

    if not bandes:
        raise ValueError("No 'bandes' provided for emitter.")

    # --- Internal helper: center freq in MHz ---
    def get_center_freq_mhz(unit_freq, start_freq, end_freq):
        if unit_freq == "M":
            return 0.5 * (start_freq + end_freq)
        elif unit_freq == "G":
            return 0.5 * ((start_freq * 1000.0) + (end_freq * 1000.0))
        elif unit_freq == "K":
            return 0.5 * ((start_freq / 1000.0) + (end_freq / 1000.0))
        else:
            raise ValueError(f"Unrecognized frequency unit '{unit_freq}'")

    # --- Convert each band into center frequency (MHz) ---
    band_infos = []
    for band in bandes:
        if not band:
            continue
        unit = band["unite"]
        start = band["debut"]
        end = band["fin"]
        center_mhz = get_center_freq_mhz(unit, start, end)
        band_infos.append({
            "band": band,
            "center_mhz": center_mhz,
        })
    if not band_infos:
        return np.inf

    # --- DL = highest frequencies (FDD) ---
    max_center = max(bi["center_mhz"] for bi in band_infos)
    # Allow several DL blocks within tolerance
    DL_TOL_MHZ = 30.0
    dl_blocks = [
        bi for bi in band_infos
        if (max_center - bi["center_mhz"]) <= DL_TOL_MHZ
    ]
    # Should never be empty
    if not dl_blocks:
        raise ValueError(f"Could not identify DL band(s). bandes={bandes}")

    # --- Case A: only one DL band ---
    if len(dl_blocks) == 1:
        return dl_blocks[0]["center_mhz"]

    # --- Case B: multiple DL blocks -> compute combined effective DL center ---
    def to_mhz(unit, val):
        if unit == "G":
            return 1000 * val
        elif unit == "K":
            return val / 1000
        elif unit == "M":
            return val
        else:
            raise ValueError(f"Unrecognized frequency unit '{unit}'")

    dl_starts = [to_mhz(bi["band"]["unite"], bi["band"]["debut"]) for bi in dl_blocks]
    dl_ends = [to_mhz(bi["band"]["unite"], bi["band"]["fin"]) for bi in dl_blocks]

    min_dl_start = min(dl_starts)
    max_dl_end = max(dl_ends)

    # Combined DL center frequency
    center_freq_mhz = 0.5 * (min_dl_start + max_dl_end)

    return center_freq_mhz


def fill_in_missing_values(df):
    # ---------- Fix CenterHeight ----------
    try:
        valid_heights = df.loc[df["CenterHeight"] != np.inf, "CenterHeight"]
    except Exception:
        print(df)
        raise ValueError("ERROR")
    if len(valid_heights) > 0:
        avg_height = valid_heights.mean()
    else:
        avg_height = np.nan  # fallback default if everything is inf

    df.loc[df["CenterHeight"] == np.inf, "CenterHeight"] = avg_height

    # ---------- Fix Frequency ----------
    for i, row in df.iterrows():
        if row["Frequency"] == np.inf:
            tech = row["Technology"]
            op = row["Operator"]

            mask = (df["Technology"] == tech) & (df["Operator"] == op) & (df.index != i)
            valid_freqs = df.loc[mask & (df["Frequency"] != np.inf), "Frequency"]

            if len(valid_freqs) > 0:
                freq = valid_freqs.mean()
            else:
                freq = np.nan  # fallback

            df.loc[i, "Frequency"] = freq

    return df


# ---------------------------------------------------------------------------
# ANFR bulk download helpers
# ---------------------------------------------------------------------------


def _download_zip(url: str, description: str = "Downloading") -> zipfile.ZipFile:
    """Download a ZIP file from *url* into memory and return a ZipFile handle."""
    logger.info("Downloading %s from %s", description, url)
    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()
    total = int(resp.headers.get("content-length", 0))
    buf = io.BytesIO()
    with tqdm(
        total=total, unit="B", unit_scale=True, desc=description, leave=False
    ) as pbar:
        for chunk in resp.iter_content(chunk_size=1 << 16):
            buf.write(chunk)
            pbar.update(len(chunk))
    buf.seek(0)
    return zipfile.ZipFile(buf)


def _read_anfr_txt(zf: zipfile.ZipFile, filename: str, usecols=None) -> pd.DataFrame:
    """Read a semicolon-delimited TXT file from an ANFR ZIP archive.

    The files use Latin-1 encoding and semicolons as delimiters.
    """
    # Find the matching member (may have a subdirectory prefix)
    matching = [n for n in zf.namelist() if n.endswith(filename)]
    if not matching:
        raise FileNotFoundError(
            f"{filename} not found in ZIP. Contents: {zf.namelist()}"
        )
    member = matching[0]
    logger.info("Reading %s (%s)", filename, member)
    with zf.open(member) as f:
        df = pd.read_csv(
            f,
            sep=";",
            encoding="latin-1",
            low_memory=False,
            usecols=usecols,
        )
    logger.info("  %s: %d rows, %d columns", filename, len(df), len(df.columns))
    return df


def _parse_technology(systeme: pd.Series) -> pd.Series:
    """Map EMR_LB_SYSTEME strings to generation labels (2G/3G/4G/5G).

    Examples: "LTE 700" -> "LTE 700" (convert_technologies_in_df handles
    the final 2G/3G/4G/5G mapping downstream). We keep the raw system
    string as the Technology column so that frequency extraction works.
    """
    return systeme


def _extract_freq_from_systeme(systeme: pd.Series) -> pd.Series:
    """Extract numeric frequency (MHz) from EMR_LB_SYSTEME strings.

    Takes the *last* number in the string, which is the frequency band.

    Examples:
        "LTE 700"    -> 700.0
        "NR 3500"    -> 3500.0
        "GSM 900"    -> 900.0
        "UMTS 2100"  -> 2100.0
        "5G NR 3500" -> 3500.0

    Returns NaN where no number is found.
    """

    def _last_number(s):
        if not isinstance(s, str):
            return np.nan
        matches = re.findall(r"\d+", s)
        if not matches:
            return np.nan
        return float(matches[-1])

    return systeme.apply(_last_number)


def _dms_to_decimal(
    deg: pd.Series,
    mn: pd.Series,
    sec: pd.Series,
    hemisphere: pd.Series,
    negative_hemispheres: tuple[str, ...] = ("S", "W"),
) -> pd.Series:
    """Vectorized DMS to decimal degrees conversion.

    Parameters
    ----------
    deg, mn, sec : pd.Series of numeric DMS components
    hemisphere : pd.Series of str, e.g. "N"/"S" or "E"/"W"
    negative_hemispheres : tuple of hemisphere codes that negate the result
    """
    dd = deg.astype(float) + mn.astype(float) / 60.0 + sec.astype(float) / 3600.0
    # Negate for S/W hemispheres
    neg_mask = hemisphere.isin(negative_hemispheres)
    dd = dd.where(~neg_mask, -dd)
    return dd


def _extract_bulk(bounding_box=None) -> pd.DataFrame:
    """Download and parse the ANFR Etalab bulk export.

    Returns a DataFrame with the standard 16-column schema.
    """
    # ------------------------------------------------------------------
    # 1. Download both ZIP archives
    # ------------------------------------------------------------------
    data_zip = _download_zip(ANFR_DATA_ZIP_URL, "ANFR data ZIP (~63 MB)")
    ref_zip = _download_zip(ANFR_REF_ZIP_URL, "ANFR ref ZIP (~5 KB)")

    # ------------------------------------------------------------------
    # 2. Read the relevant TXT files
    # ------------------------------------------------------------------
    # Supports (coordinates, height, address)
    sup_support = _read_anfr_txt(
        data_zip,
        "SUP_SUPPORT.txt",
        usecols=[
            "SUP_ID",
            "COR_NB_DG_LAT", "COR_NB_MN_LAT", "COR_NB_SC_LAT", "COR_CD_NS_LAT",
            "COR_NB_DG_LON", "COR_NB_MN_LON", "COR_NB_SC_LON", "COR_CD_EW_LON",
            "SUP_NM_HAUT",
        ],
    )

    # Stations (links support to operator, service date)
    sup_station = _read_anfr_txt(
        data_zip,
        "SUP_STATION.txt",
        usecols=["STA_NM_ANFR", "SUP_ID", "ADM_ID", "DTE_EN_SERVICE"],
    )

    # Emitters (technology system name)
    sup_emetteur = _read_anfr_txt(
        data_zip,
        "SUP_EMETTEUR.txt",
        usecols=["EMR_ID", "EMR_LB_SYSTEME", "STA_NM_ANFR", "AER_ID"],
    )

    # Antennas (azimuth, height offset)
    sup_antenne = _read_anfr_txt(
        data_zip,
        "SUP_ANTENNE.txt",
        usecols=["AER_ID", "AER_NB_AZIMUT", "AER_NB_ALT_BAS", "SUP_ID", "TAE_ID"],
    )

    # Operator reference table (read for validation, mapping uses
    # MOBILE_OPERATOR_IDS which is sufficient for the four mobile operators)
    _sup_exploitant = _read_anfr_txt(  # noqa: F841
        ref_zip,
        "SUP_EXPLOITANT.txt",
    )

    data_zip.close()
    ref_zip.close()

    # ------------------------------------------------------------------
    # 3. Filter to mobile operators only
    # ------------------------------------------------------------------
    mobile_adm_ids = set(MOBILE_OPERATOR_IDS.keys())
    sup_station = sup_station[sup_station["ADM_ID"].isin(mobile_adm_ids)].copy()
    logger.info("Stations after mobile operator filter: %d", len(sup_station))

    # ------------------------------------------------------------------
    # 4. Filter emitters to mobile technologies only
    # ------------------------------------------------------------------
    tech_mask = sup_emetteur["EMR_LB_SYSTEME"].str.contains(
        MOBILE_TECH_PATTERNS, na=False
    )
    sup_emetteur = sup_emetteur[tech_mask].copy()
    logger.info("Emitters after mobile tech filter: %d", len(sup_emetteur))

    # ------------------------------------------------------------------
    # 5. Join: stations -> emitters -> antennas -> supports
    # ------------------------------------------------------------------
    # Station + emitter (on STA_NM_ANFR)
    merged = sup_emetteur.merge(sup_station, on="STA_NM_ANFR", how="inner")
    logger.info("After station-emitter join: %d rows", len(merged))

    # + antenna (on AER_ID)
    merged = merged.merge(sup_antenne, on="AER_ID", how="left", suffixes=("", "_ant"))
    logger.info("After antenna join: %d rows", len(merged))

    # + support for coordinates (on SUP_ID from antenna table, fall back to station)
    # Use SUP_ID from the antenna table when available, otherwise from station
    merged["SUP_ID_resolved"] = merged["SUP_ID_ant"].fillna(merged["SUP_ID"])
    merged = merged.merge(
        sup_support,
        left_on="SUP_ID_resolved",
        right_on="SUP_ID",
        how="left",
        suffixes=("", "_sup"),
    )
    logger.info("After support join: %d rows", len(merged))

    # ------------------------------------------------------------------
    # 6. Convert DMS coordinates to decimal (vectorized)
    # ------------------------------------------------------------------
    merged["Latitude"] = _dms_to_decimal(
        merged["COR_NB_DG_LAT"],
        merged["COR_NB_MN_LAT"],
        merged["COR_NB_SC_LAT"],
        merged["COR_CD_NS_LAT"],
        negative_hemispheres=("S",),
    )
    merged["Longitude"] = _dms_to_decimal(
        merged["COR_NB_DG_LON"],
        merged["COR_NB_MN_LON"],
        merged["COR_NB_SC_LON"],
        merged["COR_CD_EW_LON"],
        negative_hemispheres=("W",),
    )

    # Drop rows with missing coordinates
    merged = merged.dropna(subset=["Latitude", "Longitude"])

    # ------------------------------------------------------------------
    # 7. Filter to metropolitan France
    # ------------------------------------------------------------------
    if bounding_box is not None:
        min_lon, max_lon, min_lat, max_lat = bounding_box
    else:
        min_lat, max_lat = METRO_FRANCE_LAT
        min_lon, max_lon = METRO_FRANCE_LON

    metro_mask = (
        (merged["Latitude"] >= min_lat)
        & (merged["Latitude"] <= max_lat)
        & (merged["Longitude"] >= min_lon)
        & (merged["Longitude"] <= max_lon)
    )
    merged = merged[metro_mask].copy()
    logger.info("After metropolitan France filter: %d rows", len(merged))

    # ------------------------------------------------------------------
    # 8. Map operator IDs to names
    # ------------------------------------------------------------------
    merged["Operator"] = merged["ADM_ID"].map(MOBILE_OPERATOR_IDS)

    # ------------------------------------------------------------------
    # 9. Extract frequency from EMR_LB_SYSTEME
    # ------------------------------------------------------------------
    merged["Frequency"] = _extract_freq_from_systeme(merged["EMR_LB_SYSTEME"])

    # ------------------------------------------------------------------
    # 10. Build output DataFrame with standard 16-column schema
    # ------------------------------------------------------------------
    # Antenna height: use AER_NB_ALT_BAS from antenna table, fall back to
    # support height SUP_NM_HAUT
    height = pd.to_numeric(merged["AER_NB_ALT_BAS"], errors="coerce")
    sup_height = pd.to_numeric(merged["SUP_NM_HAUT"], errors="coerce")
    height = height.where(height > 0, sup_height)

    # Service date
    date_col = merged["DTE_EN_SERVICE"].astype(str).str.strip()
    # ANFR dates are DD/MM/YYYY, convert to ISO YYYY-MM-DD
    date_parsed = pd.to_datetime(date_col, format="%d/%m/%Y", errors="coerce")
    date_iso = date_parsed.dt.strftime("%Y-%m-%d").fillna("")

    # Azimuth
    azimuth = pd.to_numeric(merged["AER_NB_AZIMUT"], errors="coerce")

    out = pd.DataFrame({
        "SiteCode": "FR_" + merged["SUP_ID_resolved"].astype(str),
        "AntennaLabel": "FR_" + merged["AER_ID"].astype(str),
        "Operator": merged["Operator"],
        "Technology": merged["EMR_LB_SYSTEME"],
        "Latitude": merged["Latitude"],
        "Longitude": merged["Longitude"],
        "CenterHeight": height,
        "Power": np.nan,
        "Frequency": merged["Frequency"],
        "FrequencyBand": np.nan,
        "Electrical_Tilt": np.nan,
        "Mechanical_Tilt": np.nan,
        "Azimuth": azimuth,
        "Gain": np.nan,
        "Horizontal_Beamwidth": np.nan,
        "Vertical_Beamwidth": np.nan,
        "Date": date_iso,
    })

    # Drop duplicates (same emitter can appear multiple times via bands)
    out = out.drop_duplicates(
        subset=["SiteCode", "AntennaLabel", "Technology", "Azimuth", "Frequency"],
    ).reset_index(drop=True)

    logger.info("Final bulk output: %d antenna records", len(out))
    return out


# ---------------------------------------------------------------------------
# Legacy CartoRadio API helpers (fallback path)
# ---------------------------------------------------------------------------

# Module-level globals used by the legacy CartoRadio path
operatornumberstring = ""
technologystring = ""


def _process_feature(feature, session):
    df = pd.DataFrame()
    feature_id = feature.get("id")
    longitude, latitude = feature.get("geometry").get("coordinates")
    # build query parameters correctly
    techs = technologystring.split(",")
    params = {
        "categorie": "TEL",
        "technologies[]": techs,
    }
    # Check nature of site
    site_url = f"https://www.cartoradio.fr/api/v1/sites/{feature_id}"
    resp = session.get(site_url, params=params)
    if resp.status_code != 200:
        print(f"Could not get data for url {resp.url}: \n {resp.status_code}")
    site_info = resp.json().get("data").get("description")
    nature = site_info.get("nature")
    site_height = site_info.get("hauteur")
    if (
        "intérieur" in nature.lower()
        or "tunnel" in nature.lower()
        or "sous-terrain" in nature.lower()
    ):
        return df

    url = f"https://www.cartoradio.fr/api/v1/sites/{feature_id}/antennes"
    resp = session.get(url, params=params)
    if resp.status_code != 200:
        print(f"Could not get data for url {resp.url}: \n {resp.status_code}")
    data = resp.json().get("data")

    for antenna in data:
        operator = antenna.get("station").get("exploitant")
        installations = antenna.get("installations")
        for all_panels in installations:
            height = all_panels.get("hauteur", np.inf)
            if height <= 0:
                continue
            for panel in all_panels.get("antennes"):
                id = panel.get("id")
                azimuth = panel.get("orientation", "isotropic")
                for emitter in panel.get("emetteurs"):
                    tech = emitter.get("systeme")

                    freq_band = f"Band{tech.split()[-2]}MHz"
                    freq_band = (
                        "Band3600MHz" if freq_band == "Band3500MHz" else freq_band
                    )
                    date = emitter.get("date_service", "")
                    if not date:
                        date = antenna.get("station").get("service", "")

                    center_freq_mhz = _select_center_dl_freq_mhz(
                        emitter.get("bandes")
                    )
                    df_to_add = pd.DataFrame({
                        "Latitude": [latitude],
                        "Longitude": [longitude],
                        "AntennaLabel": [f"ANT({id})"],
                        "Operator": [operator],
                        "SiteCode": [f"SITE({feature_id})"],
                        "Technology": [tech],
                        "Date": [date],
                        "Azimuth": [azimuth],
                        "CenterHeight": [height],
                        "Frequency": [center_freq_mhz],
                        "FrequencyBand": [freq_band],
                    })
                    if not df_to_add.empty:
                        df = pd.concat([df, df_to_add], ignore_index=True)
    if not df.empty:
        df = fill_in_missing_values(df)
        if (
            any(df["Azimuth"].isna()) or any(df["Azimuth"] == "isotropic")
        ) and len(df) > 1:
            df = df.dropna(subset=["Azimuth"])
        elif (
            any(df["Azimuth"].isna()) or any(df["Azimuth"] == "isotropic")
        ) and len(df) == 1:
            df["Azimuth"] = df["Azimuth"].fillna("isotropic")

    return df


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class BaseStations:
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
        output_folder: str = "output/france/",
        max_workers: int = 1,
        file_identifier=None,
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
        self.max_workers = max_workers
        self.antennas = pd.DataFrame()
        self.count = 0

        # Create unique file identifier if not provided
        if file_identifier is None:
            self.file_identifier = create_unique_file_identifier(self)
        else:
            self.file_identifier = file_identifier

    # ------------------------------------------------------------------
    # Legacy CartoRadio helpers (used only when use_cartoradio=True)
    # ------------------------------------------------------------------

    def set_global_vars(self, session):
        operator_url = (
            "https://www.cartoradio.fr/api/v1/operateursbyterritoire/FXX"
        )
        operators = session.get(operator_url).json().get("operateurs")
        global operatornumberstring
        global technologystring
        operatornumberstring = ""
        technologystring = ""
        for op in operators:
            if self.operator is None or same_operator(
                self.operator, op.get("nom")
            ):
                operatornumberstring = ",".join(
                    [operatornumberstring, str(op.get("id"))]
                )

        technologystring = ""
        for tech in ["2G", "3G", "4G", "5G"]:
            if self.technology is None or tech == self.technology:
                technologystring = ",".join([technologystring, tech])

    def get_sites(self, session):
        bboxstring = (
            f"{self.bounding_box[0]},{self.bounding_box[2]},"
            f"{self.bounding_box[1]},{self.bounding_box[3]}"
            if self.bounding_box is not None
            else "-5.142222, 41.333740, 9.560000, 51.089062"
        )

        params = {
            "enservice": "true",
            "operateurautre": "true",
            "operateurs": operatornumberstring,
            "technologies": technologystring,
            "categories": "TEL",
            "format": "geojson",
            "bbox": bboxstring,
        }

        url = r"https://www.cartoradio.fr/api/v1/sites"
        resp = session.get(url, params=params)
        if resp.status_code != 200:
            print(
                f"Error getting sites from url {url} with {params}: "
                f"\n {resp.status_code}"
            )
        data = resp.json()
        return data

    def get_antennas(self, sites, session):
        features = sites.get("features")
        df = pd.DataFrame()
        if self.max_workers > 1:
            print(
                f"Extracting antennas (parallel) using {self.max_workers} workers"
            )
            print(
                "WARNING: CartoRadio is often overloaded when using too many "
                "workers. If Retry gives an error, try reducing the number of "
                "workers"
            )
            from concurrent.futures import ThreadPoolExecutor, as_completed

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(
                        _process_feature, feature, session
                    ): feature
                    for feature in features
                }
                for future in tqdm(
                    as_completed(futures),
                    total=len(futures),
                    desc="Basestation sites",
                    leave=False,
                ):
                    df_results = future.result()
                    if not df_results.empty and df_results is not None:
                        df = pd.concat([df, df_results], ignore_index=True)
        else:
            for feat in tqdm(
                features,
                total=len(features),
                desc="Basestation sites",
                leave=False,
            ):
                antennadata = _process_feature(feature=feat, session=session)
                if not antennadata.empty:
                    df = pd.concat([df, antennadata], ignore_index=True)
        self.antennas = df

    # ------------------------------------------------------------------
    # Main extraction entry point
    # ------------------------------------------------------------------

    def extract_antennas(self, config=None, use_cartoradio=False):
        """Extract antenna data for France.

        Parameters
        ----------
        config : dict, optional
            Configuration dict passed to create_output_df for data estimation.
        use_cartoradio : bool, default False
            If True, use the legacy per-site CartoRadio API instead of the
            ANFR bulk download. Not recommended (slow, rate-limited).

        Returns
        -------
        pd.DataFrame
            Standard 16-column antenna DataFrame.
        """
        # Check if we should use/save the cache (only for standard parameters)
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

        # Try loading cached combined raw data
        if self.raw_antenna_cache_file and os.path.exists(
            self.raw_antenna_cache_file
        ):
            try:
                self.antennas = pd.read_pickle(self.raw_antenna_cache_file)
                print(
                    f"Loaded cached antenna data from "
                    f"{self.raw_antenna_cache_file}"
                )
                self.count = len(self.antennas)
            except Exception as e:
                raise RuntimeError(
                    f"Warning: failed to load cache "
                    f"{self.raw_antenna_cache_file}: {e}"
                )

        # If no cache or cache load failed, extract
        if self.antennas is None or self.antennas.empty:
            if use_cartoradio:
                # Legacy path: per-site CartoRadio API
                print("Using legacy CartoRadio API (slow, ~130K requests)")
                session = create_session()
                self.set_global_vars(session=session)
                sites = self.get_sites(session=session)
                self.get_antennas(sites=sites, session=session)
                session.close()
            else:
                # Primary path: ANFR bulk download
                print("Using ANFR bulk download (fast, single ZIP)")
                self.antennas = _extract_bulk(bounding_box=self.bounding_box)

            if self.antennas.empty:
                print("Result is empty")
                return pd.DataFrame()

        # Save output CSV into output_folder/{file_identifier}_antennas.csv
        out_csv = (
            os.path.join(
                self.output_folder, f"{self.file_identifier}_antennas.csv"
            )
            if self.output_folder
            else None
        )
        if out_csv:
            try:
                filter_args = {
                    "operator": self.operator,
                    "technology": self.technology,
                    "bounding_box": self.bounding_box,
                    "frequency_range": self.frequency_range,
                    "frequency_band": self.frequency_band,
                    "date": self.date,
                }
                df = self.antennas.copy()
                self.antennas = create_output_df(
                    df, config, filter_args=filter_args
                ).copy()
                self.antennas.to_csv(out_csv, index=False)
                print(f"Saved output CSV to {out_csv}")
            except Exception as e:
                raise RuntimeError(f"Warning: failed to save output CSV: {e}")

        # Save cache if requested and using standard parameters
        if save_cache and self.raw_antenna_cache_file:
            try:
                os.makedirs(
                    os.path.dirname(self.raw_antenna_cache_file), exist_ok=True
                )
                pd.to_pickle(self.antennas, self.raw_antenna_cache_file)
                print(
                    f"Saved raw antenna cache to {self.raw_antenna_cache_file}"
                )
            except Exception as e:
                raise RuntimeError(
                    f"Warning: failed to save cache: {e}"
                )
        return self.antennas

    def extract_patterns(self, *args, **kwargs):
        """France extractor does not support antenna pattern reconstruction.

        This method is provided for API compatibility and will return None.
        """
        print(
            "Pattern extraction is not supported for France "
            "(no SPARQL pattern data)."
        )
        return None


if __name__ == "__main__":
    BS = BaseStations()
    BS.extract_antennas()
