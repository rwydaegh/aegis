"""Adapter: load basestationLib data into AEGIS BaseStation objects."""

from __future__ import annotations

import logging
import re

import numpy as np
import pandas as pd

from aegis.basestation.antenna import AntennaPattern, BaseStation, BeamConfig, ExposureConfig
from aegis.basestation.coords import wgs84_to_enu
from aegis.basestation.orientation import departure_to_antenna_local
from aegis.basestation.pattern import synthetic_pattern_from_beamwidth
from aegis.basestation.power import ExposureMode, effective_eirp_dbm, eirp_to_tx_power_w
from aegis.paths import PropagationPaths

logger = logging.getLogger(__name__)


def _sanitize_label(label: str) -> str:
    """Match basestationLib's label sanitization for pattern key lookup."""
    return re.sub(r"[() .&/\\-]", "_", label)


def _safe_float(val, default: float = 0.0) -> float:
    """Convert to float, returning default for NaN/None."""
    try:
        f = float(val)
        return default if np.isnan(f) else f
    except (TypeError, ValueError):
        return default


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
    result = []

    for _, row in df.iterrows():
        site = str(row.get("SiteCode", ""))
        label = str(row.get("AntennaLabel", ""))
        key = _sanitize_label(f"{site}_{label}")

        # Try to find pattern
        pattern = None
        if key in patterns:
            matrix = np.array(patterns[key], dtype=np.float32)
            if matrix.shape == (181, 360):
                pattern = AntennaPattern(
                    gain_dbi=matrix,
                    max_gain_dbi=float(np.nanmax(matrix)),
                )

        # If no measured pattern, synthesize from beamwidth
        gain = _safe_float(row.get("Gain"), 0.0)
        if pattern is None:
            hbw = _safe_float(row.get("Horizontal_Beamwidth"), 0.0)
            vbw = _safe_float(row.get("Vertical_Beamwidth"), 0.0)
            if hbw > 0 and vbw > 0 and gain > 0:
                pattern = synthetic_pattern_from_beamwidth(hbw, vbw, gain)

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
            )
        )

    n_patterned = sum(1 for b in result if b.pattern is not None)
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
    return load_basestations_from_df(df)


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
