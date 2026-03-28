"""3GPP TR 38.901 cluster-based channel generator (dosimetry spatial subset)."""

from __future__ import annotations

import math

import numpy as np

from aegis.channel.path_loss import compute_path_loss
from aegis.channel.presets import scale_param
from aegis.defaults import DEFAULT_SEED, NUMERICAL_FLOOR
from aegis.paths import PropagationPaths

# 3GPP sub-path offset angles (Table 26 in QuaDRiGa v2.8.1 docs)
_SUBPATH_OFFSETS_DEG = np.array(
    [
        -0.0447,
        0.0447,
        -0.1413,
        0.1413,
        -0.2492,
        0.2492,
        -0.3715,
        0.3715,
        -0.5129,
        0.5129,
        -0.6797,
        0.6797,
        -0.8844,
        0.8844,
        -1.1481,
        1.1481,
        -1.5195,
        1.5195,
        -2.1551,
        2.1551,
    ]
)


def generate_channel(
    params: dict,
    freq_ghz: float,
    antenna_pos: np.ndarray,
    body_center: np.ndarray,
    power_dbm: float,
    seed: int = DEFAULT_SEED,
    overrides: dict | None = None,
) -> PropagationPaths:
    """Generate stochastic multipath from a 3GPP/QuaDRiGa preset.

    Returns PropagationPaths suitable for incoherent dosimetry (levels 0-6).
    """
    rng = np.random.default_rng(seed)
    ov = overrides or {}

    p = {**params, **ov}

    n_clusters = int(p.get("NumClusters", 12))
    n_subpaths = int(p.get("NumSubPaths", 20))

    # Step 1: large-scale parameters
    lsp = _draw_large_scale(p, freq_ghz, rng, ov)

    # Step 2: cluster delays and powers
    powers = _generate_cluster_powers(
        n_clusters,
        p.get("r_DS", 2.5),
        lsp["DS"],
        lsp["KF_dB"],
        p.get("LNS_ksi", 3),
        rng,
    )

    # Step 3: cluster arrival angles
    az, el = _generate_cluster_angles(
        n_clusters,
        powers,
        lsp["ASA_deg"],
        lsp["ESA_deg"],
        rng,
    )

    # Step 4: LOS rotation
    direction = body_center - antenna_pos
    dist = np.linalg.norm(direction)
    if dist < 1e-6:
        dist = 1.0
        direction = np.array([1.0, 0.0, 0.0])
    los_az = math.atan2(direction[1], direction[0])
    los_el = math.atan2(direction[2], math.sqrt(direction[0] ** 2 + direction[1] ** 2))
    az, el = _rotate_to_los(az, el, los_az, los_el)

    # Step 5: sub-paths
    is_los_scenario = lsp["KF_dB"] > -50  # NLOS presets have KF = -100
    az, el, powers = _expand_subpaths(
        az,
        el,
        powers,
        n_subpaths,
        p.get("PerClusterAS_A", 10),
        p.get("PerClusterES_A", 7),
        is_los_scenario,
    )

    # Step 6: convert to k_hat and power
    k_hats = _angles_to_khats(az, el)

    # Compute S_inc: free-space spreading + shadow fading, path loss via model
    tx_w = 10 ** ((power_dbm - 30) / 10)
    pl_db = compute_path_loss(p, dist, freq_ghz)
    sf_db = lsp["SF_dB"]
    s_inc = tx_w * 10 ** ((sf_db - pl_db) / 10)

    path_powers = powers * s_inc

    return PropagationPaths.from_powers(k_hat=k_hats, power=path_powers)


def _draw_large_scale(
    params: dict,
    freq_ghz: float,
    rng: np.random.Generator,
    overrides: dict,
) -> dict:
    """Draw large-scale fading parameters with frequency scaling."""

    def _scaled_mu(prefix: str) -> float:
        return scale_param(
            mu=params.get(f"{prefix}_mu", 0),
            omega=params.get(f"{prefix}_omega", 1),
            gamma=params.get(f"{prefix}_gamma", 0),
            freq_ghz=freq_ghz,
        )

    def _scaled_sigma(prefix: str) -> float:
        sigma_0 = params.get(f"{prefix}_sigma", 0)
        delta = params.get(f"{prefix}_delta", 0)
        omega = params.get(f"{prefix}_omega", 1)
        return sigma_0 + delta * math.log10(omega + freq_ghz)

    def _draw(prefix: str, is_log10: bool = False) -> float:
        mu = _scaled_mu(prefix)
        sigma = _scaled_sigma(prefix) if f"{prefix}_mu" not in overrides else 0
        val = mu + sigma * rng.standard_normal()
        if is_log10:
            return 10**val
        return val

    kf_mu = params.get("KF_mu", 0)
    kf_sigma = params.get("KF_sigma", 0) if "KF_mu" not in overrides else 0
    kf_db = kf_mu + kf_sigma * rng.standard_normal()

    sf_sigma = params.get("SF_sigma", 0)
    sf_db = sf_sigma * rng.standard_normal()

    asa_deg = _draw("AS_A", is_log10=True)
    esa_deg = _draw("ES_A", is_log10=True)
    ds = _draw("DS", is_log10=True)

    return {
        "KF_dB": kf_db,
        "SF_dB": sf_db,
        "ASA_deg": max(asa_deg, 0.1),
        "ESA_deg": max(esa_deg, 0.1),
        "DS": max(ds, 1e-12),
    }


def _generate_cluster_powers(
    n_clusters: int,
    r_ds: float,
    ds: float,
    kf_db: float,
    lns_ksi: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Generate normalized cluster powers using exponential PDP + K-factor."""
    delays = -np.log(rng.uniform(1e-12, 1, size=n_clusters))
    delays[0] = 0
    delays = np.sort(delays)

    if r_ds > 1:
        delays = delays * ds * r_ds / max(delays.max(), 1e-12)

    powers = np.exp(-delays * (r_ds - 1) / (r_ds * ds)) if r_ds > 1 and ds > 0 else np.ones(n_clusters)

    if lns_ksi > 0:
        shadow = 10 ** (-rng.normal(0, lns_ksi, size=n_clusters) / 10)
        powers *= shadow

    k_linear = 10 ** (kf_db / 10)
    if n_clusters > 1 and k_linear > 1e-10:
        nlos_sum = powers[1:].sum()
        if nlos_sum > 0:
            powers[0] = k_linear * nlos_sum
    elif k_linear <= 1e-10:
        pass

    total = powers.sum()
    if total > 0:
        powers /= total

    return powers


def _generate_cluster_angles(
    n_clusters: int,
    powers: np.ndarray,
    asa_deg: float,
    esa_deg: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate cluster arrival angles scaled to target ASA/ESA."""
    az_init = rng.uniform(-math.pi / 2, math.pi / 2, size=n_clusters)
    el_init = rng.uniform(-math.pi / 2, math.pi / 2, size=n_clusters)
    az_init[0] = 0
    el_init[0] = 0

    az = _scale_angles(az_init, powers, math.radians(asa_deg), max_scale=3.0)
    el = _scale_angles(el_init, powers, math.radians(esa_deg), max_scale=1.5)

    return az, el


def _scale_angles(
    angles: np.ndarray,
    powers: np.ndarray,
    target_as_rad: float,
    max_scale: float,
) -> np.ndarray:
    """Scale initial angles to match target angular spread (eqs 66-69)."""
    delta = np.angle(np.sum(np.exp(1j * angles) * powers))
    shifted = np.angle(np.exp(1j * (angles - delta)))
    p_total = powers.sum()
    if p_total < NUMERICAL_FLOOR:
        return angles
    mean_sq = np.sum(powers * shifted**2) / p_total
    mean_val = np.sum(powers * shifted) / p_total
    achieved_as = math.sqrt(max(mean_sq - mean_val**2, NUMERICAL_FLOOR))
    s = target_as_rad / max(achieved_as, 1e-10)
    s = min(s, max_scale)
    return np.angle(np.exp(1j * angles * s))


def _rotate_to_los(
    az: np.ndarray,
    el: np.ndarray,
    los_az: float,
    los_el: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Rotate cluster angles so LOS cluster points toward the body (eqs 70-78)."""
    cos_el = np.cos(el)
    x = cos_el * np.cos(az)
    y = cos_el * np.sin(az)
    z = np.sin(el)
    vecs = np.column_stack([x, y, z])

    cp, sp = math.cos(los_az), math.sin(los_az)
    ct, st = math.cos(los_el), math.sin(los_el)
    R = np.array(
        [
            [ct * cp, -sp, -st * cp],
            [ct * sp, cp, -st * sp],
            [st, 0, ct],
        ]
    )

    rotated = (R @ vecs.T).T

    az_out = np.arctan2(rotated[:, 1], rotated[:, 0])
    el_out = np.arctan2(rotated[:, 2], np.sqrt(rotated[:, 0] ** 2 + rotated[:, 1] ** 2))

    return az_out, el_out


def _expand_subpaths(
    az: np.ndarray,
    el: np.ndarray,
    powers: np.ndarray,
    n_subpaths: int,
    c_asa: float,
    c_esa: float,
    is_los: bool,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Expand NLOS clusters into sub-paths using fixed offset table."""
    offsets_rad = np.radians(_SUBPATH_OFFSETS_DEG[:n_subpaths])

    all_az, all_el, all_pow = [], [], []

    for i in range(len(az)):
        if is_los and i == 0:
            all_az.append(az[i])
            all_el.append(el[i])
            all_pow.append(powers[i])
        else:
            sub_az = az[i] + c_asa * offsets_rad
            sub_el = el[i] + c_esa * offsets_rad
            sub_pow = np.full(n_subpaths, powers[i] / n_subpaths)
            all_az.extend(sub_az)
            all_el.extend(sub_el)
            all_pow.extend(sub_pow)

    return np.array(all_az), np.array(all_el), np.array(all_pow)


def _angles_to_khats(az: np.ndarray, el: np.ndarray) -> np.ndarray:
    """Convert spherical arrival angles to unit propagation direction vectors."""
    cos_el = np.cos(el)
    k_hat = np.column_stack(
        [
            cos_el * np.cos(az),
            cos_el * np.sin(az),
            np.sin(el),
        ]
    )
    norms = np.linalg.norm(k_hat, axis=1, keepdims=True)
    return k_hat / np.where(norms > 0, norms, 1.0)
