"""Exposure Lab dosimetry: near-field phone OR far-field plane-wave on a posed body.

The result is shaped exactly like the main ``/api/compute`` route so the frontend
binary reader and X-Stats parser are reused unchanged. Heavy imports (torch via
``ParametricBody``, the nearfield kernel) are lazy inside the function so non-lab
requests never pay the RAM.
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np


def _posed_body(params: dict[str, Any]):
    """Load the SMPL-X parametric body and pose it from preset or raw pose vector.

    Uses the shared cached generator so this dose-side pose reuses the body the
    /api/parametric-body call already built for the same (gender, betas, pose).
    """
    from aegis.geometry.parametric import generate_posed

    from ._presets import POSE_PRESETS

    gender = params.get("gender", "neutral")

    raw_betas = params.get("betas")
    betas = np.asarray(raw_betas, dtype=np.float64) if raw_betas else np.zeros(10)

    preset = params.get("preset")
    if preset is not None:
        if preset not in POSE_PRESETS:
            raise ValueError(f"unknown preset {preset!r}")
        pose = np.asarray(POSE_PRESETS[preset], dtype=np.float64)
    elif params.get("pose") is not None:
        pose = np.asarray(params["pose"], dtype=np.float64)
    else:
        pose = None

    return generate_posed("smplx", gender, betas, pose=pose)


def _near_field(body, tissue, freq_hz: float, src: dict, physics: dict, power_w: float):
    """Near-field phone-source dose. Returns a DosimetryResult shaped like /api/compute."""
    from aegis.geometry.averaging import apply_spatial_averaging
    from aegis.nearfield import phone
    from aegis.result import DosimetryResult

    from ._patterns import get_pattern

    freq_mhz = freq_hz / 1e6
    pat = get_pattern(src["pattern_id"], freq_mhz)
    position = np.asarray(src["position"], dtype=np.float64)
    source = phone.PhoneSource.from_euler(
        position=position,
        pattern=pat,
        yaw=float(src.get("yaw", 0.0)),
        pitch=float(src.get("pitch", 0.0)),
        roll=float(src.get("roll", 0.0)),
        radiated_power_w=power_w,
    )
    sab = phone.compute_sab(
        body.centroids,
        body.normals,
        source,
        t0=tissue.T0,
        n_tilde=tissue.n_complex,
        fresnel=physics.get("fresnel", True),
        body=body,
        diffraction_model=physics.get("diffraction_model", "fock"),
        self_shadow=physics.get("self_shadow", True),
        source_pos=position,
    )
    sab = np.asarray(sab)
    p_abs = float(np.sum(sab * body.areas))
    sab_avg = apply_spatial_averaging(sab, body.centroids, body.areas, 4e-4)
    return DosimetryResult(
        sab=sab,
        sab_averaged=sab_avg,
        p_abs=p_abs,
        fidelity_level=2,
        mode="spatial",
        freq_hz=freq_hz,
        corrections=("near_field",),
    )


def _far_field(body, tissue, freq_hz: float, src: dict, physics: dict, power_w: float):
    """Far-field plane-wave dose via the standard spatial engine."""
    from aegis.engine import DosimetryEngine
    from aegis.paths import PropagationPaths

    theta = float(src["theta_inc"])
    phi = float(src["phi_inc"])
    st, ct = np.sin(theta), np.cos(theta)
    sp, cp = np.sin(phi), np.cos(phi)
    k_hat = np.array([st * cp, st * sp, ct])
    e_theta = np.array([ct * cp, ct * sp, -st])
    e_phi = np.array([-sp, cp, 0.0])
    pol = float(src.get("pol_angle", 0.0))
    e_field = np.cos(pol) * e_theta + np.sin(pol) * e_phi

    paths = PropagationPaths.from_powers(
        k_hat=k_hat[None, :],
        power=np.array([power_w]),
        polarisation=e_field[None, :],
    )
    engine = DosimetryEngine(tissue)
    return engine.compute(
        body,
        paths,
        mode="spatial",
        freq_hz=freq_hz,
        fresnel=physics.get("fresnel", True),
        polarisation=True,
        self_shadow=physics.get("self_shadow", False),
        diffraction_model=physics.get("diffraction_model", "fock"),
    )


def compute_lab(params: dict[str, Any]) -> tuple[Any, Any, Any, dict[str, Any]]:
    """Run Exposure Lab dose on a posed phantom.

    Returns ``(body, tissue, result, extra)`` where ``result`` is a
    ``DosimetryResult`` shaped exactly like the main ``/api/compute`` route.
    """
    from aegis.viewer.compute import resolve_skin_model

    freq_hz = float(params["freq_mhz"]) * 1e6
    power_w = float(params.get("power_w", 1.0))
    physics = params.get("physics", {})
    src = params["source"]

    timings: dict[str, float] = {}
    t_total = time.perf_counter()

    t0 = time.perf_counter()
    body = _posed_body(params)
    timings["pose_body_ms"] = (time.perf_counter() - t0) * 1e3

    t0 = time.perf_counter()
    tissue = resolve_skin_model("itis", freq_hz)
    timings["tissue_ms"] = (time.perf_counter() - t0) * 1e3

    kind = src.get("kind", "near")
    t0 = time.perf_counter()
    if kind == "near":
        result = _near_field(body, tissue, freq_hz, src, physics, power_w)
    elif kind == "far":
        result = _far_field(body, tissue, freq_hz, src, physics, power_w)
    else:
        raise ValueError(f"unknown source kind {kind!r}")
    timings["dose_ms"] = (time.perf_counter() - t0) * 1e3
    timings["total_ms"] = (time.perf_counter() - t_total) * 1e3

    return body, tissue, result, {"timings": timings}
