"""Adapter: load basestationLib data into AEGIS BaseStation objects."""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from aegis.basestation.antenna import AntennaPattern, BaseStation, BeamConfig, ExposureConfig
from aegis.basestation.coords import wgs84_to_enu
from aegis.basestation.orientation import departure_to_antenna_local
from aegis.basestation.pattern import synthetic_pattern_from_beamwidth
from aegis.basestation.power import ExposureMode, effective_eirp_dbm, eirp_to_tx_power_w
from aegis.basestation.utils import _sanitize_label
from aegis.paths import PropagationPaths

logger = logging.getLogger(__name__)


def load_basestations_from_df(
    df: pd.DataFrame,
    patterns: dict | None = None,
) -> list[BaseStation]:
    """Convert a basestationLib DataFrame to a list of BaseStation objects.

    Parameters
    ----------
    df : standardized 16-column DataFrame from basestationLib
    patterns : dict mapping sanitized label -> (181, 360) gain array in dBi

    Returns
    -------
    list of BaseStation
    """
    patterns = patterns or {}
    n = len(df)
    if n == 0:
        return []

    # Pre-extract columns as arrays (avoids per-row Series construction)
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
    gains_arr = _col_float("Gain", 0.0)
    freqs = _col_float("Frequency", 2100.0)
    azimuths = _col_float("Azimuth", 0.0)
    e_tilts = _col_float("Electrical_Tilt", 0.0)
    m_tilts = _col_float("Mechanical_Tilt", 0.0)
    hbws = _col_float("Horizontal_Beamwidth", 65.0)
    vbws = _col_float("Vertical_Beamwidth", 10.0)
    freq_bands = _col("FrequencyBand")

    result: list[BaseStation] = [None] * n  # type: ignore[list-item]
    n_patterned = 0

    for i in range(n):
        site = str(sites[i])
        label = str(labels[i])
        key = _sanitize_label(f"{site}_{label}")

        pattern = None
        if key in patterns:
            matrix = np.array(patterns[key], dtype=np.float32)
            if matrix.shape == (181, 360):
                pattern = AntennaPattern(
                    gain_dbi=matrix,
                    max_gain_dbi=float(np.nanmax(matrix)),
                )

        fb = str(freq_bands[i])
        if fb == "nan":
            fb = ""

        gain = float(gains_arr[i])
        if pattern is None:
            hbw = float(hbws[i])
            vbw = float(vbws[i])
            if hbw > 0 and vbw > 0 and gain > 0:
                pattern = synthetic_pattern_from_beamwidth(hbw, vbw, gain)

        if pattern is not None:
            n_patterned += 1

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
        )

    logger.info("Loaded %d base stations (%d with patterns)", len(result), n_patterned)
    return result


def load_basestations_from_csv(
    csv_path: str,
    bbox: list[float] | None = None,
    operator: str | None = None,
    technology: str | None = None,
) -> list[BaseStation]:
    """Load base stations from a pre-extracted CSV file.

    This avoids the basestationLib runtime dependency and OOM issues
    from fetching all data from the API.
    """
    df = pd.read_csv(csv_path)

    # Apply filters
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

    logger.info("Loaded %d antennas from CSV (after filters)", len(df))

    # Auto-discover patterns
    from pathlib import Path

    patterns = {}
    csv_dir = Path(csv_path).parent
    region_name = Path(csv_path).stem
    for patterns_dir in [csv_dir / "patterns", csv_dir.parent / "patterns"]:
        mat_path = patterns_dir / f"{region_name}.mat"
        if mat_path.exists():
            import scipy.io

            mat = scipy.io.loadmat(str(mat_path))
            patterns = {k: v for k, v in mat.items() if not k.startswith("_")}
            logger.info("Auto-discovered %d patterns from %s", len(patterns), mat_path)
            break

    return load_basestations_from_df(df, patterns)


def load_basestations_from_parquet(
    path: str,
    bbox: list[float] | None = None,
    operator: str | None = None,
    technology: str | None = None,
    frequency_band: str | None = None,
) -> list[BaseStation]:
    """Load base stations from a merged Parquet file with provenance."""
    from pathlib import Path

    from aegis.basestation.parquet_io import read_merged_parquet

    # Auto-discover patterns
    patterns: dict = {}
    parquet_dir = Path(path).parent
    region_name = Path(path).stem
    for patterns_dir in [parquet_dir / "patterns", parquet_dir.parent / "patterns"]:
        mat_path = patterns_dir / f"{region_name}.mat"
        if mat_path.exists():
            import scipy.io

            mat = scipy.io.loadmat(str(mat_path))
            patterns = {k: v for k, v in mat.items() if not k.startswith("_")}
            logger.info("Auto-discovered %d patterns from %s", len(patterns), mat_path)
            break

    return read_merged_parquet(
        path,
        bbox=bbox,
        operator=operator,
        technology=technology,
        frequency_band=frequency_band,
        patterns=patterns,
    )


def load_basestations(
    country: str = "Belgium",
    region: str = "brussels",
    bbox: list[float] | None = None,
    operator: str | None = None,
    technology: str | None = None,
    max_workers: int = 4,
) -> list[BaseStation]:
    """Load base stations from basestationLib (requires basestationLib installed).

    Parameters
    ----------
    country : country name
    region : region/city (required for Belgium)
    bbox : [min_lon, max_lon, min_lat, max_lat]
    operator : filter by operator name
    technology : filter by technology (e.g. "5G")
    max_workers : parallel download threads

    Returns
    -------
    list of BaseStation
    """
    try:
        from basestationLib import get_basestation_instance
    except ImportError as exc:
        raise ImportError(
            "basestationLib is required for base station loading. "
            "Install from: https://github.ugent.be/WiCa/basestations"
        ) from exc

    kwargs: dict = {"region_city": region} if region else {}
    BSClass = get_basestation_instance(country, **kwargs)

    init_kwargs: dict = {
        "output_folder": f"/tmp/aegis_basestations/{country.lower()}/",
        "max_workers": max_workers,
    }
    if bbox:
        init_kwargs["bounding_box"] = bbox
    if operator:
        init_kwargs["operator"] = operator
    if technology:
        init_kwargs["technology"] = technology

    instance = BSClass(**init_kwargs)

    config = {
        "computation": {
            "max_workers": max_workers,
            "estimations": {"estimate_missing_data_based_on_existing": True},
        }
    }
    df = instance.extract_antennas(config=config)

    if df is None or len(df) == 0:
        logger.warning("No antennas found for %s/%s", country, region)
        return []

    # Load patterns if available
    patterns = {}
    try:
        import importlib
        from pathlib import Path

        import scipy.io

        # Try standard cache location
        mod = importlib.import_module(f"basestationLib.Countries.{country}.{region}.basestations")

        mod_dir = Path(mod.__file__).parent
        for candidate in ["patterns.mat", "all_patterns.mat"]:
            p = mod_dir / candidate
            if p.exists():
                logger.info("Loading patterns from %s", p)
                mat = scipy.io.loadmat(str(p))
                patterns = {k: v for k, v in mat.items() if not k.startswith("_")}
                logger.info("Loaded %d antenna patterns", len(patterns))
                break
    except Exception as exc:
        logger.debug("Could not load patterns: %s", exc)

    return load_basestations_from_df(df, patterns)


# ---------------------------------------------------------------------------
# Dosimetry helpers
# ---------------------------------------------------------------------------


def paths_from_basestation(
    bs: BaseStation,
    body_center: np.ndarray,
    scene_origin: tuple[float, float],
    ground_height: float = 0.0,
    exposure_mode: ExposureMode | None = None,
    exposure_config: ExposureConfig | None = None,
    beam_config: BeamConfig | None = None,
    archetype: str | None = None,
) -> PropagationPaths:
    """Create a LOS path from a base station to the body center.

    Applies antenna pattern gain modulation and EIRP correction.

    Parameters
    ----------
    bs : BaseStation
    body_center : (3,) body center in ENU scene coordinates
    scene_origin : (lat0, lon0) degrees
    ground_height : ground elevation at the antenna location

    Returns
    -------
    PropagationPaths with a single LOS path, power-modulated by pattern
    """
    # Antenna position in scene coords
    ant_pos = wgs84_to_enu(
        bs.latitude,
        bs.longitude,
        0.0,
        scene_origin[0],
        scene_origin[1],
    )
    ant_pos[2] = ground_height + bs.height_m

    # Direction from antenna to body
    direction = body_center - ant_pos
    dist = float(np.linalg.norm(direction))
    if dist < 0.1:
        # Body is at (or very near) the antenna. Use boresight as fallback direction
        # and clamp distance to avoid division by zero.
        az_r = np.deg2rad(bs.azimuth_deg)
        tilt_r = np.deg2rad(bs.total_tilt_deg)
        direction = np.array(
            [
                np.sin(az_r) * np.cos(tilt_r),
                np.cos(az_r) * np.cos(tilt_r),
                -np.sin(tilt_r),
            ]
        )
        dist = 0.1
    k_hat = direction / np.linalg.norm(direction)  # arrival direction at body

    # --- mMIMO beam decomposition path ---
    if (
        archetype == "mmimo"
        and exposure_mode in (ExposureMode.ACTUAL_MAX, ExposureMode.TYPICAL)
        and exposure_config is not None
        and beam_config is not None
    ):
        return _mmimo_beam_decomposition(bs, k_hat, dist, exposure_mode, exposure_config, beam_config)

    # --- Standard (non-mMIMO) path ---
    # TX power from EIRP (apply exposure reduction if configured)
    if exposure_mode is not None and exposure_config is not None:
        eff_eirp = effective_eirp_dbm(bs, exposure_config, exposure_mode)
    else:
        eff_eirp = bs.eirp_dbm
    tx_power_w = eirp_to_tx_power_w(eff_eirp, bs.gain_dbi)

    # Isotropic power density at distance d
    s_iso = tx_power_w / (4.0 * np.pi * dist**2)

    # Pattern gain in departure direction
    departure_dir = k_hat  # from antenna toward body (outgoing from antenna)

    if bs.pattern is not None:
        elev, azim = departure_to_antenna_local(
            departure_dir[np.newaxis, :],
            bs.azimuth_deg,
            bs.total_tilt_deg,
        )
        g_linear = bs.pattern.evaluate(elev, azim)[0]
    else:
        # No pattern: use peak gain (isotropic assumption with EIRP already includes it)
        g_linear = 10.0 ** (bs.gain_dbi / 10.0)

    s_modulated = s_iso * g_linear

    return PropagationPaths.from_powers(
        k_hat=k_hat[np.newaxis, :],
        power=np.array([max(s_modulated, 0.0)]),
    )


def _mmimo_beam_decomposition(
    bs: BaseStation,
    k_hat: np.ndarray,
    dist: float,
    exposure_mode: ExposureMode,
    exposure_config: ExposureConfig,
    beam_config: BeamConfig,
) -> PropagationPaths:
    """Compute mMIMO exposure as broadcast + traffic beam combination.

    For ACTUAL_MAX: power = max(broadcast, traffic)
    For TYPICAL: power = broadcast + traffic * traffic_load_factor
    """
    # TX power from EIRP (strip peak antenna gain)
    tx_power_w = eirp_to_tx_power_w(bs.eirp_dbm, bs.gain_dbi)

    # Isotropic power density from TX power at distance d
    s_iso = tx_power_w / (4.0 * np.pi * dist**2)

    # Antenna-local angles for the body direction
    elev_local, azim_local = departure_to_antenna_local(
        k_hat[np.newaxis, :],
        bs.azimuth_deg,
        bs.total_tilt_deg,
    )
    elev_deg = float(elev_local[0])
    azim_deg = float(azim_local[0])

    tdd_dl = exposure_config.tdd_dl_ratio
    prf = exposure_config.power_reduction_factor

    # --- Broadcast beam ---
    bc_pattern = synthetic_pattern_from_beamwidth(
        beam_config.broadcast_hbw_deg,
        beam_config.broadcast_vbw_deg,
        beam_config.broadcast_gain_dbi,
        sidelobe_suppression_db=15.0,
    )
    bc_gain = float(bc_pattern.evaluate(elev_local, azim_local)[0])
    # Broadcast is always-on during DL, no PRF reduction
    s_broadcast = s_iso * bc_gain * tdd_dl

    # --- Traffic beam ---
    in_sweep = abs(azim_deg) < beam_config.sweep_h_range_deg and abs(elev_deg) < beam_config.sweep_v_range_deg
    if in_sweep:
        tr_pattern = synthetic_pattern_from_beamwidth(
            beam_config.traffic_hbw_deg,
            beam_config.traffic_vbw_deg,
            beam_config.traffic_gain_dbi,
            sidelobe_suppression_db=15.0,
        )
        tr_gain = float(tr_pattern.evaluate(elev_local, azim_local)[0])
        s_traffic = s_iso * tr_gain * tdd_dl * prf
        if exposure_mode == ExposureMode.TYPICAL:
            s_traffic *= exposure_config.traffic_load_factor
    else:
        s_traffic = 0.0

    # --- Combine: ACTUAL_MAX takes envelope, TYPICAL sums ---
    power = max(s_broadcast, s_traffic) if exposure_mode == ExposureMode.ACTUAL_MAX else s_broadcast + s_traffic

    return PropagationPaths.from_powers(
        k_hat=k_hat[np.newaxis, :],
        power=np.array([max(power, 0.0)]),
    )


def paths_from_basestations(
    basestations: list[BaseStation],
    body_center: np.ndarray,
    scene_origin: tuple[float, float],
    max_distance_m: float = 2000.0,
    exposure_mode: ExposureMode | None = None,
    exposure_configs: list[ExposureConfig] | None = None,
) -> PropagationPaths:
    """Create LOS paths from multiple base stations to the body.

    Filters by distance, concatenates all paths.
    """
    all_paths = []
    for i, bs in enumerate(basestations):
        ant_pos = wgs84_to_enu(
            bs.latitude,
            bs.longitude,
            0.0,
            scene_origin[0],
            scene_origin[1],
        )
        ant_pos[2] = bs.height_m
        dist = float(np.linalg.norm(body_center - ant_pos))
        if dist > max_distance_m:
            continue
        exp_cfg = exposure_configs[i] if exposure_configs else None
        paths = paths_from_basestation(
            bs,
            body_center,
            scene_origin,
            exposure_mode=exposure_mode,
            exposure_config=exp_cfg,
        )
        all_paths.append(paths)

    if not all_paths:
        return PropagationPaths.from_powers(
            k_hat=np.array([[0.0, 0.0, -1.0]]),
            power=np.array([0.0]),
        )

    return PropagationPaths.concatenate(all_paths, reindex_elements=True)
