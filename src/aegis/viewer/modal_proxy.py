"""Modal proxy for GPU-accelerated ray tracing.

Lazy-initializes Modal client on first RT request.
Falls back to None (caller handles fallback) if Modal is unavailable.
"""

from __future__ import annotations

import gzip
import logging
import os
import time as _time

import numpy as np

from aegis.defaults import DEFAULT_FREQ_HZ, DEFAULT_POWER_DBM

logger = logging.getLogger(__name__)

_MODAL_AVAILABLE = False
_initialized = False
_differt_cls = None
_sionna_cls = None

# Payload size threshold for gzip compression (bytes)
_GZIP_THRESHOLD = 5 * 1024 * 1024  # 5 MB

_SCALEDOWN_WINDOW = 120  # seconds, must match Modal @app.cls config

_last_rt_success: float = 0.0  # monotonic timestamp of last successful .remote() call


def _mark_success() -> None:
    """Record a successful RT call (updates warmth window)."""
    global _last_rt_success
    _last_rt_success = _time.monotonic()


def gpu_status() -> dict:
    """Return GPU warmth status based on last successful RT call timing."""
    if not (_initialized and _MODAL_AVAILABLE):
        if _is_enabled():
            return {"warm": False, "enabled": True, "seconds_remaining": 0}
        return {"warm": False, "enabled": False, "seconds_remaining": 0}
    elapsed = _time.monotonic() - _last_rt_success
    warm = _last_rt_success > 0 and elapsed < _SCALEDOWN_WINDOW
    remaining = max(0, int(_SCALEDOWN_WINDOW - elapsed)) if warm else 0
    return {"warm": warm, "enabled": True, "seconds_remaining": remaining}


def _is_enabled() -> bool:
    """Check if Modal RT is enabled via environment variables."""
    token = os.environ.get("MODAL_TOKEN_ID")
    enabled = os.environ.get("USE_MODAL_RT", "false").lower()
    return bool(token) and enabled in ("true", "1", "yes")


def _init_modal() -> bool:
    """Lazy-initialize Modal client. Called once on first RT request."""
    global _MODAL_AVAILABLE, _initialized, _differt_cls, _sionna_cls

    if _initialized:
        return _MODAL_AVAILABLE

    _initialized = True

    if not _is_enabled():
        logger.info("Modal RT disabled (USE_MODAL_RT not set or no token)")
        return False

    try:
        import modal

        _differt_cls = modal.Cls.from_name("aegis-rt", "DiffeRTTracer")
        _sionna_cls = modal.Cls.from_name("aegis-rt", "SionnaTracer")
        _MODAL_AVAILABLE = True
        logger.info("Modal RT initialized (DiffeRTTracer + SionnaTracer)")
        return True
    except Exception as e:
        logger.warning("Modal RT init failed: %s", e)
        return False


def _compress_scene_data(scene_data: dict) -> dict:
    """Gzip-compress large scene data for network transfer."""
    import pickle

    verts = np.asarray(scene_data["vertices"], dtype=np.float64)
    tris = np.asarray(scene_data["triangles"], dtype=np.int32)
    raw_size = verts.nbytes + tris.nbytes

    if raw_size > _GZIP_THRESHOLD:
        buf = pickle.dumps(
            {
                "vertices": verts,
                "triangles": tris,
                "materials": scene_data["materials"],
            }
        )
        compressed = gzip.compress(buf)
        logger.info(
            "Compressed scene data: %.1f MB -> %.1f MB",
            raw_size / 1e6,
            len(compressed) / 1e6,
        )
        return {"_compressed": True, "_data": compressed}
    return scene_data


def trace_differt(
    scene_xml: str,
    tx_pos: list[float],
    rx_pos: list[float],
    max_order: int = 1,
    freq_hz: float = DEFAULT_FREQ_HZ,
    tx_power_dbm: float = DEFAULT_POWER_DBM,
    reflection_loss_per_order: float = 0.5,
    method: str = "exhaustive",
    num_rays: int = 1_000_000,
    chunk_size: int | None = None,
    scene_files: dict[str, bytes] | None = None,
) -> dict | None:
    """Call Modal DiffeRTTracer. Returns result dict or None if unavailable."""
    if not _init_modal():
        return None

    try:
        tracer = _differt_cls()
        result = tracer.trace.remote(
            scene_xml=scene_xml,
            scene_files=scene_files or {},
            tx_pos=tx_pos,
            rx_pos=rx_pos,
            max_order=max_order,
            freq_hz=freq_hz,
            tx_power_dbm=tx_power_dbm,
            reflection_loss_per_order=reflection_loss_per_order,
            method=method,
            num_rays=num_rays,
            chunk_size=chunk_size,
        )
        _mark_success()
        return result
    except Exception as e:
        logger.error("Modal DiffeRT trace failed: %s", e)
        return None


def trace_sionna_bundled(
    scene_name: str,
    tx_pos: list[float],
    rx_pos: list[float],
    max_bounces: int = 5,
    freq_hz: float = DEFAULT_FREQ_HZ,
    tx_power_dbm: float = DEFAULT_POWER_DBM,
    rt_config: dict | None = None,
) -> dict | None:
    """Call Modal SionnaTracer for bundled scenes. Returns dict or None."""
    if not _init_modal():
        return None

    try:
        tracer = _sionna_cls()
        result = tracer.trace_bundled.remote(
            scene_name=scene_name,
            tx_pos=tx_pos,
            rx_pos=rx_pos,
            max_bounces=max_bounces,
            freq_hz=freq_hz,
            tx_power_dbm=tx_power_dbm,
            rt_config=rt_config,
        )
        _mark_success()
        return result
    except Exception as e:
        logger.error("Modal Sionna bundled trace failed: %s", e)
        return None


def trace_sionna_voxel(
    scene_key: str,
    scene_data: dict | None,
    tx_pos: list[float],
    rx_pos: list[float],
    max_bounces: int = 5,
    freq_hz: float = DEFAULT_FREQ_HZ,
    tx_power_dbm: float = DEFAULT_POWER_DBM,
    rt_config: dict | None = None,
) -> dict | None:
    """Call Modal SionnaTracer for voxel geometry. Returns dict or None."""
    if not _init_modal():
        return None

    # Compress large scene data
    if scene_data is not None:
        scene_data = _compress_scene_data(scene_data)

    try:
        tracer = _sionna_cls()
        result = tracer.trace_voxel.remote(
            scene_key=scene_key,
            scene_data=scene_data,
            tx_pos=tx_pos,
            rx_pos=rx_pos,
            max_bounces=max_bounces,
            freq_hz=freq_hz,
            tx_power_dbm=tx_power_dbm,
            rt_config=rt_config,
        )
        _mark_success()
        return result
    except Exception as e:
        logger.error("Modal Sionna voxel trace failed: %s", e)
        return None
