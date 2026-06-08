"""Dosimetry computation for the interactive viewer."""

from __future__ import annotations

import functools
import math
import os
import time
import warnings
from pathlib import Path

import numpy as np
import yaml

from aegis.basestation.classify import _lookup_tdd
from aegis.constants import C_0, EPS_0
from aegis.defaults import DEFAULT_FREQ_HZ, DEFAULT_POWER_DBM
from aegis.engine import DosimetryEngine
from aegis.geometry import curvature as _curvature_module
from aegis.geometry.mesh import BodyMesh
from aegis.paths import PropagationPaths
from aegis.tissue.cole_cole import debye_permittivity
from aegis.tissue.dielectric import TissueModel
from aegis.viewer.config import DEFAULTS


@functools.lru_cache(maxsize=1)
def _load_phantom_masses() -> dict[str, float]:
    """Load phantom masses from data/phantoms.yaml (cached)."""
    data_dir = Path(os.environ.get("AEGIS_DATA_DIR", str(Path(__file__).resolve().parents[3] / "data")))
    path = Path(data_dir) / "phantoms.yaml"
    if not path.exists():
        return {
            "thelonious": 17.4,
            "duke": 72.4,
            "eartha": 56.0,
            "ella": 58.7,
            "adult_male": 73.0,
            "adult_female": 60.0,
            "boy_6y": 19.0,
            "girl_8y": 30.0,
        }
    with open(path) as f:
        data = yaml.safe_load(f)
    return {name: info["mass_kg"] for name, info in data.items()}


# Curvature is cached inside ``aegis.geometry.curvature`` (the real owner). These
# names are re-exported aliases of that module's cache and lock so the viewer and
# its tests share the single live cache rather than a dead viewer-local copy.
_curvature_cache = _curvature_module._cache
_curvature_cache_lock = _curvature_module._cache_lock


def _compute_face_curvature(body: BodyMesh) -> np.ndarray:
    """Per-face twice-mean-curvature, in 1/m.

    Thin wrapper over ``geometry.curvature.face_curvature`` (a local quadric fit
    over the centroid k-NN, caching internally on the rigid-invariant geometry
    hash). It supersedes the old |delta_normal| / distance proxy with the same
    twice-mean-curvature quantity used by the Fock gate.
    """
    from aegis.geometry.curvature import face_curvature

    return face_curvature(body)


# ---------------------------------------------------------------------------
# Skin model registry
# ---------------------------------------------------------------------------

SKIN_MODELS = [
    {"id": "itis", "label": "Homogeneous - IT’IS database (v5)"},
    {"id": "christ2021", "label": "Homogeneous - Gabriel × 1.2 (Christ 2021)"},
    {"id": "christ2025", "label": "Homogeneous - Christ 2025 Dermis"},
    {"id": "nict", "label": "Homogeneous - NICT Measurements"},
]

_nict_data: dict | None = None


def _load_nict_data() -> dict:
    """Load and cache NICT skin measurement CSV."""
    global _nict_data
    if _nict_data is not None:
        return _nict_data

    import csv

    # Search for CSV: AEGIS_DATA_DIR env var, then CWD/data, then relative to source
    import os
    import re
    from pathlib import Path

    candidates = []
    env_dir = os.environ.get("AEGIS_DATA_DIR")
    if env_dir:
        candidates.append(Path(env_dir) / "measurements-Skin.csv")
    candidates.append(Path("data") / "measurements-Skin.csv")
    candidates.append(Path(__file__).parent.parent.parent.parent / "data" / "measurements-Skin.csv")
    csv_path = next((p for p in candidates if p.exists()), candidates[-1])
    freq_hz_list, eps_r_list, sigma_list = [], [], []

    with open(csv_path) as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for row in reader:
            if len(row) >= 4 and row[0].strip():
                try:

                    def parse(s, _re=re):
                        return float(_re.sub(r"\.E", "E", s.strip()))

                    freq_hz_list.append(parse(row[0]))
                    eps_r_list.append(parse(row[1]))
                    sigma_list.append(parse(row[3]))
                except ValueError:
                    continue

    _nict_data = {
        "log_freq": np.log10(np.array(freq_hz_list)),
        "log_eps_r": np.log10(np.array(eps_r_list)),
        "log_sigma": np.log10(np.array(sigma_list)),
    }
    return _nict_data


def resolve_skin_model(name: str, freq_hz: float) -> TissueModel:
    """Compute skin TissueModel from a named data source at a given frequency."""
    if name == "itis":
        return TissueModel.from_database("Skin", freq_hz)

    if name == "christ2021":
        base = TissueModel.from_database("Skin", freq_hz)
        return TissueModel(
            name="Skin (Gabriel × 1.2)",
            eps_r=base.eps_r * 1.2,
            sigma=base.sigma * 1.2,
            freq_hz=freq_hz,
        )

    if name == "christ2025":
        eps = debye_permittivity(
            freq_hz,
            eps_inf=7.88,
            eps_static=47.0,
            sigma=5.19,
            tau_s=8.35e-12,
        )
        omega = 2 * np.pi * freq_hz
        return TissueModel(
            name="Skin (Christ 2025 Dermis)",
            eps_r=float(eps.real),
            sigma=float(-eps.imag * omega * EPS_0),
            freq_hz=freq_hz,
        )

    if name == "nict":
        data = _load_nict_data()
        log_f = np.log10(freq_hz)
        log_f_clamped = np.clip(log_f, data["log_freq"][0], data["log_freq"][-1])
        eps_r = 10 ** float(np.interp(log_f_clamped, data["log_freq"], data["log_eps_r"]))
        sigma = 10 ** float(np.interp(log_f_clamped, data["log_freq"], data["log_sigma"]))
        return TissueModel(
            name="Skin (NICT)",
            eps_r=eps_r,
            sigma=sigma,
            freq_hz=freq_hz,
        )

    raise ValueError(f"Unknown skin model: {name!r}")


def _resolve_channel_preset_dir(config: dict | None = None, preset_dir: str | Path | None = None) -> Path:
    """Resolve channel preset directories against AEGIS data roots."""
    if preset_dir is None:
        cfg = config or DEFAULTS
        preset_dir = cfg.get("dosimetry", {}).get("stochastic", {}).get("preset_dir", "channel_presets")

    preset_path = Path(preset_dir)
    if preset_path.is_absolute():
        return preset_path

    data_root = Path(os.environ.get("AEGIS_DATA_DIR", str(Path(__file__).resolve().parents[3] / "data")))
    return data_root / preset_path


def _rotation_matrix_z(angle: float) -> np.ndarray:
    """Build a rotation matrix around the Z axis (yaw in Z-up coords)."""
    c, s = np.cos(angle), np.sin(angle)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def _transform_body_for_viewer(
    body: BodyMesh,
    body_offset: np.ndarray,
    body_rotation_y: float,
) -> BodyMesh:
    """Apply viewer yaw (Z-up) and translation; keeps vertices, centroids, normals consistent.

    Previously, only normals and centroids were rotated while vertices stayed fixed, which
    breaks triangle geometry and mis-places coherent phases. Offset must move the mesh,
    not only the aim point used for k_hat.
    """
    off = np.asarray(body_offset, dtype=np.float64).reshape(3)
    rigid = abs(body_rotation_y) > 1e-9 or np.any(np.abs(off) > 1e-12)
    if not rigid:
        return body

    if abs(body_rotation_y) > 1e-9:
        R = _rotation_matrix_z(body_rotation_y)
        vertices = body.vertices @ R.T
        normals = body.normals @ R.T
        centroids = body.centroids @ R.T
    else:
        vertices = body.vertices
        normals = body.normals
        centroids = body.centroids

    vertices = vertices + off.reshape(1, 1, 3)
    centroids = centroids + off

    return BodyMesh(
        vertices=vertices,
        normals=normals,
        centroids=centroids,
        areas=body.areas,
        name=body.name,
    )


_SPEED_OF_LIGHT = 299_792_458.0  # m/s


def array_factor_gain(
    k_hat: np.ndarray,
    n_h: int,
    n_v: int,
    d_h: float,
    d_v: float,
    broadside: np.ndarray,
    element_pattern: str,
    freq_hz: float,
) -> float:
    """Compute |AF(k_hat)|^2 * G_element(k_hat) for a Uniform Planar Array.

    For a 1x1 array the array factor is 1.0, so the result is just the
    element gain.

    Parameters
    ----------
    k_hat : (3,) unit direction from antenna toward body.
    n_h, n_v : horizontal and vertical element counts.
    d_h, d_v : element spacings in wavelengths.
    broadside : (3,) unit vector for array normal (main beam direction).
    element_pattern : "isotropic", "patch", or "short_dipole".
    freq_hz : carrier frequency [Hz].

    Returns
    -------
    float : |AF|^2 * G_element >= 0.
    """
    k_hat = np.asarray(k_hat, dtype=np.float64)
    broadside = np.asarray(broadside, dtype=np.float64)
    broadside = broadside / np.linalg.norm(broadside)

    # --- Element gain ---
    if element_pattern == "isotropic":
        g_elem = 1.0
    elif element_pattern == "patch":
        cos_theta = float(k_hat @ broadside)
        g_elem = max(cos_theta, 0.0) ** 1.5
    elif element_pattern == "short_dipole":
        # Dipole axis: perpendicular to broadside, using least-aligned canonical axis
        abs_b = np.abs(broadside)
        ref = np.zeros(3)
        ref[int(np.argmin(abs_b))] = 1.0
        dipole_axis = np.cross(broadside, ref)
        dipole_axis /= np.linalg.norm(dipole_axis)
        # alpha = angle between k_hat and dipole axis
        cos_alpha = float(k_hat @ dipole_axis)
        sin2_alpha = max(1.0 - cos_alpha**2, 0.0)
        g_elem = 1.5 * sin2_alpha
    else:
        raise ValueError(f"Unknown element_pattern: {element_pattern!r}")

    # --- Array factor ---
    if n_h == 1 and n_v == 1:
        return float(g_elem)

    wavelength = C_0 / freq_hz
    d_h_m = d_h * wavelength
    d_v_m = d_v * wavelength
    k0 = 2.0 * np.pi / wavelength

    # Build broadside-perpendicular axes (same as AntennaArray.upa)
    abs_b = np.abs(broadside)
    ref = np.zeros(3)
    ref[int(np.argmin(abs_b))] = 1.0
    e_h = np.cross(broadside, ref)
    e_h /= np.linalg.norm(e_h)
    e_v = np.cross(broadside, e_h)

    # Element offsets relative to array center
    h_idx = np.arange(n_h) - (n_h - 1) / 2.0
    v_idx = np.arange(n_v) - (n_v - 1) / 2.0
    hh, vv = np.meshgrid(h_idx, v_idx)  # (n_v, n_h)
    offsets = (hh.ravel()[:, None] * d_h_m * e_h) + (vv.ravel()[:, None] * d_v_m * e_v)  # (M, 3)

    phases = k0 * (offsets @ k_hat)  # (M,)
    af = np.sum(np.exp(1j * phases))
    af2 = float(np.abs(af) ** 2)

    return af2 * g_elem


def _build_cluster_viz(viz_out: dict) -> dict:
    """Compute FBS/LBS positions for clusters and sub-paths.

    Returns a dict with:
      clusters: list of {fbs, lbs, power, is_los} at cluster level
      subpaths: list of {fbs, lbs, power, is_los, cluster} at sub-path level
    """
    n = viz_out["n_clusters"]
    is_los = viz_out["is_los"]
    antenna = np.array(viz_out["antenna_pos"])
    body_c = np.array(viz_out["body_center"])
    dist = np.linalg.norm(body_c - antenna)
    n_sub = viz_out.get("n_subpaths", 20)
    sub_az_all = viz_out.get("sub_az", [])
    sub_el_all = viz_out.get("sub_el", [])
    sub_pow_all = viz_out.get("sub_power", [])

    clusters = []
    subpaths = []

    for i in range(n):
        power = viz_out["cluster_power"][i]

        if is_los and i == 0:
            clusters.append({"fbs": None, "lbs": None, "power": power, "is_los": True})
            if sub_pow_all:
                subpaths.append({"fbs": None, "lbs": None, "power": sub_pow_all[0], "is_los": True, "cluster": 0})
            continue

        # Departure direction from antenna (same for cluster and its sub-paths)
        dep_az = viz_out["cluster_dep_az"][i]
        dep_el = viz_out["cluster_dep_el"][i]
        cos_dep_el = math.cos(dep_el)
        dep_dir = np.array([cos_dep_el * math.cos(dep_az), cos_dep_el * math.sin(dep_az), math.sin(dep_el)])

        delay_s = viz_out["cluster_delay"][i]
        d_excess = min(delay_s * _SPEED_OF_LIGHT, dist * 2.0)
        r_fbs = min(max(d_excess * 0.5, dist * 0.15), dist * 0.8)
        r_lbs = min(max(d_excess * 0.5, dist * 0.15), dist * 0.8)

        fbs = (antenna + dep_dir * r_fbs).tolist()

        # Cluster-level LBS from center arrival angle
        arr_az = viz_out["cluster_az"][i]
        arr_el = viz_out["cluster_el"][i]
        cos_el = math.cos(arr_el)
        arr_dir = np.array([cos_el * math.cos(arr_az), cos_el * math.sin(arr_az), math.sin(arr_el)])
        lbs = (body_c - arr_dir * r_lbs).tolist()

        clusters.append({"fbs": fbs, "lbs": lbs, "power": power, "is_los": False})

        # Sub-path level: each has its own arrival angle -> own LBS
        nlos_idx = i - 1 if is_los else i
        base = (1 if is_los else 0) + nlos_idx * n_sub
        for j in range(n_sub):
            idx = base + j
            if idx >= len(sub_az_all):
                break
            s_az = sub_az_all[idx]
            s_el = sub_el_all[idx]
            cos_s_el = math.cos(s_el)
            s_dir = np.array([cos_s_el * math.cos(s_az), cos_s_el * math.sin(s_az), math.sin(s_el)])
            s_lbs = (body_c - s_dir * r_lbs).tolist()
            subpaths.append({"fbs": fbs, "lbs": s_lbs, "power": sub_pow_all[idx], "is_los": False, "cluster": i})

    return {"clusters": clusters, "subpaths": subpaths}


def apply_exposure_reduction(
    power_dbm: float,
    freq_hz: float,
    n_elements: int,
    exposure_mode: str,
) -> float:
    """Apply exposure mode reduction to transmit power.

    Infers TDD from frequency (assumes 5G NR), applies power reduction
    factor for mMIMO arrays (>= 16 elements), and traffic load for
    typical mode.
    """
    if exposure_mode == "theoretical":
        return power_dbm

    freq_mhz = freq_hz / 1e6
    factor = 1.0

    # TDD duty cycle (assume 5G NR for band lookup)
    is_tdd, dl_ratio = _lookup_tdd("5G", freq_mhz)
    if is_tdd:
        factor *= dl_ratio

    # Power reduction factor: 0.32 for mMIMO panels (>= 16 elements)
    prf = 0.32 if n_elements >= 16 else 1.0
    factor *= prf

    # Traffic load (typical mode only)
    if exposure_mode == "typical":
        factor *= 0.5

    factor = max(factor, 1e-10)
    return power_dbm + 10 * math.log10(factor)


def _compute_incidence_geometry(
    antenna_pos: np.ndarray,
    body_center: np.ndarray,
    power_dbm: float,
) -> tuple[np.ndarray, float, float, float]:
    """Compute direction, distance, incident power density, and clamped distance.

    Returns ``(k_hat, dist, S_inc, d_clamped)``.
    """
    from aegis.viewer.raytracer import _DEFAULT_FSPL_DISTANCE_CLAMP_M

    direction = body_center - antenna_pos
    dist = float(np.linalg.norm(direction))
    k_hat = np.array([0.0, 0.0, -1.0]) if dist < 1e-6 else direction / dist

    tx_power_w = 10 ** ((power_dbm - 30) / 10)
    d_clamped = max(dist, _DEFAULT_FSPL_DISTANCE_CLAMP_M)
    S_inc = tx_power_w / (4 * np.pi * d_clamped**2)
    return k_hat, dist, S_inc, d_clamped


def _generate_stochastic_paths(
    stochastic: dict,
    antenna_pos: np.ndarray,
    body_center: np.ndarray,
    power_dbm: float,
    cfg: dict,
    polarised: bool = False,
) -> tuple[PropagationPaths, dict | None]:
    """Build paths from a stochastic channel preset; returns ``(paths, cluster_viz)``.

    When ``polarised`` is True the channel assigns a physical XPR-split
    polarisation per path so polarisation-aware dosimetry uses it.
    """
    from aegis.channel import generate_channel, load_preset

    preset_dir = _resolve_channel_preset_dir(cfg)
    preset = load_preset(stochastic["preset"], preset_dir)
    viz_out: dict = {}
    paths = generate_channel(
        preset["params"],
        freq_ghz=stochastic.get("freq_ghz", 28),
        antenna_pos=antenna_pos,
        body_center=body_center,
        power_dbm=power_dbm,
        seed=stochastic.get("seed", 42),
        overrides=stochastic.get("overrides"),
        viz_out=viz_out,
        xpr_db=float(stochastic.get("xpr_db", 8.0)) if polarised else None,
    )
    cluster_viz = _build_cluster_viz(viz_out)
    return paths, cluster_viz


def _default_incident_polarisation(k_hat: np.ndarray) -> np.ndarray:
    """A physical default incident polarisation for analytic single-source paths.

    Vertical (z) projected onto the plane transverse to ``k_hat``, falling back
    to horizontal when ``k_hat`` is (anti)parallel to z. Base-station antennas
    are predominantly vertically polarised. Replaces the unphysical uniform
    ``q=1`` knob, so the polarisation toggle yields the true polarised answer.
    """
    k = np.asarray(k_hat, dtype=np.float64)
    k = k / np.linalg.norm(k)
    z = np.array([0.0, 0.0, 1.0])
    pol = z - (z @ k) * k
    if np.linalg.norm(pol) < 1e-6:
        x = np.array([1.0, 0.0, 0.0])
        pol = x - (x @ k) * k
    return pol / np.linalg.norm(pol)


def _build_single_antenna_paths(
    ant: dict,
    body_center: np.ndarray,
    tissue: TissueModel | None,
    exposure_mode: str,
    fallback_power_dbm: float,
) -> tuple[PropagationPaths, float]:
    """Build a single-path PropagationPaths for one antenna entry.

    Returns ``(paths, S_eff)`` where ``S_eff`` is the array-gain-scaled incident
    power density at the body center.
    """
    from aegis.viewer.raytracer import _DEFAULT_FSPL_DISTANCE_CLAMP_M

    _freq_hz = tissue.freq_hz if tissue else DEFAULT_FREQ_HZ
    ant_pos = np.asarray(ant["position"], dtype=np.float64)
    ant_power_dbm = float(ant.get("power_dbm", fallback_power_dbm))
    acfg = ant.get("array_config", {})
    if exposure_mode and exposure_mode != "theoretical":
        ant_power_dbm = apply_exposure_reduction(
            ant_power_dbm,
            _freq_hz,
            int(acfg.get("n_h", 1)) * int(acfg.get("n_v", 1)),
            exposure_mode,
        )
    ant_tx_w = 10 ** ((ant_power_dbm - 30) / 10)

    a_dir = body_center - ant_pos
    a_dist = np.linalg.norm(a_dir)
    a_k_hat = np.array([0.0, 0.0, -1.0]) if a_dist < 1e-6 else a_dir / a_dist
    a_d_clamped = max(a_dist, _DEFAULT_FSPL_DISTANCE_CLAMP_M)
    a_S_inc = ant_tx_w / (4 * np.pi * a_d_clamped**2)

    a_gain = array_factor_gain(
        k_hat=a_k_hat,
        n_h=int(acfg.get("n_h", 1)),
        n_v=int(acfg.get("n_v", 1)),
        d_h=float(acfg.get("d_h_wavelengths", 0.5)),
        d_v=float(acfg.get("d_v_wavelengths", 0.5)),
        broadside=np.asarray(acfg.get("broadside", [0, 0, -1]), dtype=np.float64),
        element_pattern=acfg.get("element_pattern", "short_dipole"),
        freq_hz=_freq_hz,
    )

    a_S_eff = a_S_inc * a_gain
    paths = PropagationPaths.from_powers(
        k_hat=a_k_hat[np.newaxis, :],
        power=np.array([a_S_eff]),
        polarisation=_default_incident_polarisation(a_k_hat),
    )
    return paths, a_S_eff


def _generate_multi_antenna_paths(
    antennas: list[dict],
    body_center: np.ndarray,
    tissue: TissueModel | None,
    exposure_mode: str,
    power_dbm: float,
    k_hat: np.ndarray,
) -> tuple[PropagationPaths, float]:
    """Build merged PropagationPaths from a list of antennas.

    For an empty list returns a zero-power single path along ``k_hat`` and
    ``S_inc = 0``.
    """
    if len(antennas) == 0:
        paths = PropagationPaths.from_powers(k_hat=k_hat[np.newaxis, :], power=np.array([0.0]))
        return paths, 0.0

    per_antenna_paths = []
    total_S_inc = 0.0
    for ant in antennas:
        ant_paths, ant_S_eff = _build_single_antenna_paths(ant, body_center, tissue, exposure_mode, power_dbm)
        per_antenna_paths.append(ant_paths)
        total_S_inc += ant_S_eff
    paths = PropagationPaths.concatenate(per_antenna_paths, reindex_elements=True)
    return paths, total_S_inc


def _generate_single_plane_wave_paths(
    k_hat: np.ndarray,
    S_inc: float,
    d_clamped: float,
    power_dbm: float,
    tissue: TissueModel | None,
    exposure_mode: str,
) -> tuple[PropagationPaths, float]:
    """Build a single-plane-wave PropagationPaths; returns ``(paths, S_inc_effective)``."""
    _freq_hz = tissue.freq_hz if tissue else DEFAULT_FREQ_HZ
    if exposure_mode and exposure_mode != "theoretical":
        _reduced_power_dbm = apply_exposure_reduction(power_dbm, _freq_hz, 1, exposure_mode)
        _tx_power_w = 10 ** ((_reduced_power_dbm - 30) / 10)
        S_inc = _tx_power_w / (4 * np.pi * d_clamped**2)
    paths = PropagationPaths.from_powers(
        k_hat=k_hat[np.newaxis, :],
        power=np.array([S_inc]),
        polarisation=_default_incident_polarisation(k_hat),
    )
    return paths, S_inc


def _run_engine_mode(
    engine: DosimetryEngine,
    body: BodyMesh,
    paths: PropagationPaths,
    body_mass: float | None,
    mode: str,
    corrections: dict | None,
    dos_cfg: dict,
    total_area: float,
) -> tuple:
    """Run engine using the new mode-based API (``bound`` / ``aggregate`` / ``spatial``)."""
    corr = corrections or {}
    if mode == "bound":
        A_ab = total_area * dos_cfg["convex_body_area_factor"]
        D_max = dos_cfg["level0_D_max"]
        return engine.compute_with_timings(body, paths, mode="bound", A_ab=A_ab, D_max=D_max, body_mass=body_mass)
    if mode == "aggregate":
        A_ab = total_area * dos_cfg["convex_body_area_factor"]
        return engine.compute_with_timings(body, paths, mode="aggregate", A_ab=A_ab, body_mass=body_mass)

    # spatial mode with correction flags
    mode_kwargs: dict = {"mode": "spatial", "fresnel": corr.get("fresnel", True)}
    if corr.get("polarisation"):
        mode_kwargs["polarisation"] = True
        # Real polarisation flows through paths.psi (set by the path builders);
        # no scalar q knob.
    if corr.get("curvature"):
        mode_kwargs["curvature"] = True
        mode_kwargs["curvature_H"] = _compute_face_curvature(body)
    # Shadow-edge gate: an explicit diffraction_model wins over the legacy bool.
    diffraction_model = corr.get("diffraction_model")
    if diffraction_model is not None:
        mode_kwargs["diffraction_model"] = diffraction_model
        if diffraction_model != "none" and "curvature_H" not in mode_kwargs:
            mode_kwargs["curvature_H"] = _compute_face_curvature(body)
    elif corr.get("diffraction"):
        mode_kwargs["diffraction"] = True
        if "curvature_H" not in mode_kwargs:
            mode_kwargs["curvature_H"] = _compute_face_curvature(body)
    inter_body = corr.get("inter_body")
    if inter_body is not None:
        mode_kwargs["inter_body"] = inter_body
    return engine.compute_with_timings(body, paths, body_mass=body_mass, **mode_kwargs)


def _run_engine_legacy_level(
    engine: DosimetryEngine,
    body: BodyMesh,
    paths: PropagationPaths,
    body_mass: float | None,
    level: int | None,
    dos_cfg: dict,
    total_area: float,
) -> tuple:
    """Run engine using the legacy level-based API (levels 0-8)."""
    if level is None:
        level = 2
    extra_kwargs: dict = {}
    if level <= 1:
        extra_kwargs["A_ab"] = total_area * dos_cfg["convex_body_area_factor"]
        if level == 0:
            extra_kwargs["D_max"] = dos_cfg["level0_D_max"]
        return engine.compute_with_timings(body, paths, level=level, body_mass=body_mass, **extra_kwargs)
    if level <= 6:
        mode_kwargs: dict = {"mode": "spatial"}
        if level == 2:
            mode_kwargs["fresnel"] = False
        if level >= 4:
            mode_kwargs["polarisation"] = True
        if level >= 5:
            mode_kwargs["curvature"] = True
            mode_kwargs["curvature_H"] = _compute_face_curvature(body)
        if level == 6:
            mode_kwargs["diffraction"] = True
        return engine.compute_with_timings(body, paths, body_mass=body_mass, **mode_kwargs)
    return engine.compute_with_timings(body, paths, level=level, body_mass=body_mass, **extra_kwargs)


def _run_engine_compute(
    engine: DosimetryEngine,
    body: BodyMesh,
    paths: PropagationPaths,
    body_mass: float | None,
    mode: str | None,
    level: int | None,
    corrections: dict | None,
    dos_cfg: dict,
    total_area: float,
) -> tuple:
    """Dispatch to ``engine.compute_with_timings`` for mode-based or legacy-level APIs.

    Returns ``(result, engine_timings)``.
    """
    if mode is not None:
        return _run_engine_mode(engine, body, paths, body_mass, mode, corrections, dos_cfg, total_area)
    return _run_engine_legacy_level(engine, body, paths, body_mass, level, dos_cfg, total_area)


_ECBF_WARNING_MARKERS = ("ECBF", "absorption", "infeasible")


def collect_ecbf_warnings(captured: list[warnings.WarningMessage]) -> list[str]:
    """Filter captured warnings for ECBF/absorption-constraint messages."""
    out: list[str] = []
    for w in captured:
        msg = str(w.message)
        if any(marker in msg for marker in _ECBF_WARNING_MARKERS):
            out.append(msg)
    return out


def _build_compute_extras(
    S_inc: float,
    dist: float,
    paths: PropagationPaths,
    antennas: list[dict] | None,
    timings: dict,
    cluster_viz: dict | None,
    corrections: dict | None,
    mode: str | None,
) -> tuple[dict, list | None]:
    """Build the ``extra`` dict and ``corr_list`` returned from ``compute_dosimetry``."""
    extra = {
        "S_inc": float(S_inc),
        "distance_m": float(dist),
        "n_paths": paths.n_paths,
        "n_antennas": len(antennas) if antennas is not None else 1,
        "timings": timings,
    }
    if cluster_viz is not None:
        extra["cluster_viz"] = cluster_viz

    corr_list = None
    if mode is not None:
        # Lazy import: _responses imports this module at top level, so a
        # module-level import here would be circular.
        from aegis.viewer.routes.compute._responses import _diffraction_active

        corr = corrections or {}
        corr_list = [k for k in ("fresnel", "polarisation", "curvature") if corr.get(k)]
        if _diffraction_active(corr):
            corr_list.append("diffraction")
    return extra, corr_list


def compute_dosimetry(
    body: BodyMesh,
    antenna_pos: np.ndarray,
    body_offset: np.ndarray | None = None,
    body_rotation_y: float = 0.0,
    level: int | None = 2,
    mode: str | None = None,
    corrections: dict | None = None,
    tissue: TissueModel | None = None,
    power_dbm: float = DEFAULT_POWER_DBM,
    config: dict | None = None,
    stochastic: dict | None = None,
    antennas: list[dict] | None = None,
    exposure_mode: str = "theoretical",
) -> tuple:
    """Run dosimetry from a single antenna position toward the body.

    Parameters
    ----------
    body : the body mesh
    antenna_pos : (3,) antenna position in scene coordinates [meters]
    body_offset : (3,) translation applied to all triangle vertices [meters]
    body_rotation_y : yaw angle [radians], Three.js Y-rotation mapped to Z-rotation in Z-up
    level : fidelity level 0-8 (legacy API, used when mode is None)
    mode : computation mode (bound, aggregate, spatial)
    corrections : dict of correction flags (fresnel, polarisation, curvature, diffraction)
    tissue : tissue model (defaults to skin at 28 GHz)
    power_dbm : transmit power [dBm]
    config : viewer config dict
    antennas : list of antenna dicts, each with keys ``position``, ``power_dbm`` (optional),
        and ``array_config`` (optional). When provided, one PropagationPaths is built per
        antenna and they are merged via ``PropagationPaths.concatenate``.

    Returns
    -------
    Tuple of ``(result, transformed_body, tissue, level, mode, corrections, extra)``.
    """
    timings: dict[str, float] = {}
    t_total = time.perf_counter()

    cfg = config or DEFAULTS
    dos_cfg = cfg["dosimetry"]

    if tissue is None:
        tissue = resolve_skin_model("itis", DEFAULT_FREQ_HZ)

    antenna_pos = np.asarray(antenna_pos, dtype=np.float64)
    body_offset = np.asarray(body_offset, dtype=np.float64) if body_offset is not None else np.zeros(3)

    t0 = time.perf_counter()
    rotated_body = _transform_body_for_viewer(body, body_offset, body_rotation_y)
    body_center = rotated_body.centroids.mean(axis=0)
    timings["body_transform_ms"] = (time.perf_counter() - t0) * 1e3

    k_hat, dist, S_inc, d_clamped = _compute_incidence_geometry(antenna_pos, body_center, power_dbm)

    # Polarisation-aware dosimetry needs a real incident polarisation. For the
    # stochastic arm that means assigning an XPR-split field per path.
    want_polarisation = bool(
        (corrections or {}).get("polarisation") if mode is not None else (level is not None and level >= 4)
    )

    cluster_viz = None
    if stochastic:
        paths, cluster_viz = _generate_stochastic_paths(
            stochastic, antenna_pos, body_center, power_dbm, cfg, polarised=want_polarisation
        )
    elif antennas is not None:
        paths, S_inc = _generate_multi_antenna_paths(antennas, body_center, tissue, exposure_mode, power_dbm, k_hat)
    else:
        paths, S_inc = _generate_single_plane_wave_paths(k_hat, S_inc, d_clamped, power_dbm, tissue, exposure_mode)

    # Resolve body mass for SAR computation
    body_mass = _load_phantom_masses().get(body.name) if body.name else None

    engine = DosimetryEngine(tissue)
    t0 = time.perf_counter()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result, engine_timings = _run_engine_compute(
            engine, rotated_body, paths, body_mass, mode, level, corrections, dos_cfg, body.total_area
        )
    ecbf_warnings = collect_ecbf_warnings(caught)
    timings["engine_compute_ms"] = (time.perf_counter() - t0) * 1e3
    timings["total_ms"] = (time.perf_counter() - t_total) * 1e3

    # Pull fine-grained timings from the call-local dict returned by compute_with_timings
    for key in ("kernel_ms", "avg_build_G_4cm2_ms", "avg_matvec_4cm2_ms", "avg_build_G_1cm2_ms"):
        if key in engine_timings:
            timings[key] = engine_timings[key]

    extra, corr_list = _build_compute_extras(S_inc, dist, paths, antennas, timings, cluster_viz, corrections, mode)
    if ecbf_warnings:
        extra["ecbf_warnings"] = ecbf_warnings

    return result, rotated_body, tissue, level, mode, corr_list, extra


def generate_lsp_heatmap(
    preset_name: str,
    freq_ghz: float,
    antenna_pos: tuple[float, float, float],
    lsp_name: str = "SF_dB",
    bounds: tuple[float, float, float, float] = (-100, 100, -100, 100),
    resolution: int = 128,
    seed: int = 42,
    preset_dir: str | None = None,
) -> dict:
    """Generate an LSP heatmap for the frontend."""
    from aegis.channel.lsf import LSFModel
    from aegis.channel.presets import load_preset

    preset = load_preset(preset_name, _resolve_channel_preset_dir(DEFAULTS, preset_dir))
    model = LSFModel(preset["params"], freq_ghz, seed=seed)
    grid = model.generate_map(
        bounds=bounds,
        resolution=resolution,
        height=1.5,
        lsp_name=lsp_name,
    )

    return {
        "data": grid.tolist(),
        "bounds": list(bounds),
        "lsp_name": lsp_name,
        "vmin": float(grid.min()),
        "vmax": float(grid.max()),
        "resolution": resolution,
    }
