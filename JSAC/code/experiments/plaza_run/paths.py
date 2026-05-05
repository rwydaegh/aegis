"""Path generation for plaza_run.

Two production modes plus an optional Sionna RT mode:

- ``plaza_specular``  Deterministic LOS + ground bounce + 2 facade specular
  bounces by image method. Same construction the rank_check experiment used.
  Cheap, defensible, and matches the §V "scene as path dictionary" framing
  for a stylised plaza with the south facade housing the BS.
- ``uma_los``         3GPP TR 38.901 UMa-LOS stochastic preset via
  ``aegis.channel.generator.generate_channel``. The brief's required sanity
  comparator; mirrors rank_check's dual-model strategy.
- ``sionna_dict``     Sionna RT through Modal L4 with results memoised on
  a coarse plaza grid. Brief 08 keeps this as the "plan honors §V" path,
  but the production run defaults to ``plaza_specular`` because each
  Sionna trace is ~50-200 ms even on L4 and the dictionary build is on
  the wall-clock critical path. Falls back to ``plaza_specular`` when
  Modal credentials or the bundled scene are unavailable.

All three return ``PropagationPaths`` in the same canonical centre-of-array
form. Brief 08 uses ``expand_paths_to_array`` downstream to turn them into
per-element steering for the 8x8 panel.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from aegis.channel.generator import generate_channel
from aegis.channel.presets import load_preset
from aegis.constants import C_0, Z_0
from aegis.paths import PropagationPaths

logger = logging.getLogger(__name__)

PRESET_NAME = "3GPP_38.901_UMa_LOS"
PRESET_DIR = Path("data/channel_presets")
# 4 clusters x 2 subpaths = 8 paths/body. Keeps N_c small enough that
# ``compute_static_path_gram`` fits in memory and avoids a 30-60 s JIT
# recompile vs. plaza_specular's N_c = 4. Reducing further makes
# ``uma_los`` indistinguishable from a sparse-LOS toy.
STOCHASTIC_CLUSTERS = 4
STOCHASTIC_SUBPATHS = 2

# Plaza-specular reflector geometry (matches rank_check facades + ground).
GROUND_NORMAL = np.array([0.0, 0.0, 1.0])
GROUND_POINT = np.zeros(3)
FACADE_PLUS_NORMAL = np.array([0.0, -1.0, 0.0])  # north facade at y=+FACADE_Y
FACADE_MINUS_NORMAL = np.array([0.0, +1.0, 0.0])  # south facade at y=-FACADE_Y
FACADE_Y_M = 35.0  # plaza facade ring half-extent
REFL_GROUND = 0.55
REFL_FACADE = 0.35
DICT_GRID_SPACING_M = 4.0  # coarse-grid spacing for Sionna dictionary lookups


@dataclass(frozen=True)
class PathSpec:
    """One body's path-generation request."""

    bs_position: np.ndarray  # (3,) BS phase center
    body_target: np.ndarray  # (3,) body centroid in world frame
    freq_hz: float
    tx_power_w: float
    body_index: int
    slot_index: int  # used as a stochastic seed offset for ``uma_los``


def _reflect_point(p: np.ndarray, plane_point: np.ndarray, plane_normal: np.ndarray) -> np.ndarray:
    d = float(np.dot(p - plane_point, plane_normal))
    return p - 2.0 * d * plane_normal


def _perpendicular_pol(k_hat: np.ndarray) -> np.ndarray:
    z = np.array([0.0, 0.0, 1.0])
    ref = z if abs(k_hat[2]) < 0.95 else np.array([1.0, 0.0, 0.0])
    e = np.cross(k_hat, ref)
    return e / np.linalg.norm(e)


def plaza_specular_paths(spec: PathSpec) -> PropagationPaths:
    """LOS + ground + 2 facade specular bounces, image method."""
    sources = [
        ("los", spec.bs_position, 1.0),
        ("ground", _reflect_point(spec.bs_position, GROUND_POINT, GROUND_NORMAL), REFL_GROUND),
        (
            "facade_plus",
            _reflect_point(spec.bs_position, np.array([0.0, +FACADE_Y_M, 0.0]), FACADE_PLUS_NORMAL),
            REFL_FACADE,
        ),
        (
            "facade_minus",
            _reflect_point(spec.bs_position, np.array([0.0, -FACADE_Y_M, 0.0]), FACADE_MINUS_NORMAL),
            REFL_FACADE,
        ),
    ]
    psi_1m = float(np.sqrt(2.0 * Z_0 * spec.tx_power_w / (4.0 * np.pi)))

    k_hats, psis, delays, is_los = [], [], [], []
    for name, source, refl in sources:
        d = spec.body_target - source
        dist = float(np.linalg.norm(d))
        k_hat = d / max(dist, 1e-6)
        amp = psi_1m * refl / max(dist, 1e-6)
        e_pol = _perpendicular_pol(k_hat)
        psi = (amp * e_pol).astype(complex)
        k_hats.append(k_hat)
        psis.append(psi)
        delays.append(dist / C_0)
        is_los.append(name == "los")

    return PropagationPaths(
        k_hat=np.stack(k_hats),
        psi=np.stack(psis),
        element_index=np.zeros(len(sources), dtype=np.intp),
        delay=np.array(delays),
        is_los=np.array(is_los, dtype=bool),
    )


_PRESET_CACHE: dict | None = None


def _get_preset() -> dict:
    global _PRESET_CACHE
    if _PRESET_CACHE is None:
        _PRESET_CACHE = load_preset(PRESET_NAME, PRESET_DIR)
    return _PRESET_CACHE


def uma_los_paths(spec: PathSpec, *, base_seed: int = 0) -> PropagationPaths:
    """3GPP UMa-LOS stochastic paths; deterministic per ``(body, slot)`` seed."""
    seed = base_seed + 1000 * spec.body_index + spec.slot_index
    return generate_channel(
        params=_get_preset(),
        freq_ghz=spec.freq_hz / 1e9,
        antenna_pos=spec.bs_position,
        body_center=spec.body_target,
        power_dbm=10.0 * np.log10(spec.tx_power_w * 1e3),
        seed=seed,
        overrides={
            "NumClusters": STOCHASTIC_CLUSTERS,
            "NumSubPaths": STOCHASTIC_SUBPATHS,
        },
    )


# ---------------------------------------------------------------------------
# Sionna dictionary (Modal L4 — best-effort, falls back to plaza_specular).
# ---------------------------------------------------------------------------


@dataclass
class SionnaDictionary:
    """Lazy Sionna RT dictionary keyed by quantised plaza position."""

    bs_position: np.ndarray
    freq_hz: float
    tx_power_w: float
    grid_spacing_m: float = DICT_GRID_SPACING_M
    _cache: dict[tuple[int, int, int], PropagationPaths] | None = None
    _modal_tracer: object | None = None
    _disabled: bool = False

    def _quantise(self, body_target: np.ndarray) -> tuple[int, int, int]:
        return tuple(int(round(v / self.grid_spacing_m)) for v in body_target)

    def _ensure_tracer(self) -> object | None:
        if self._modal_tracer is not None or self._disabled:
            return self._modal_tracer
        try:
            from aegis.modal_rt.sionna_tracer import SionnaTracer

            self._modal_tracer = SionnaTracer()
        except Exception as exc:  # pragma: no cover - environmental
            logger.warning("Sionna Modal tracer unavailable (%s); falling back to plaza_specular", exc)
            self._disabled = True
        return self._modal_tracer

    def get(self, spec: PathSpec) -> PropagationPaths:
        if self._cache is None:
            self._cache = {}
        key = self._quantise(spec.body_target)
        if key in self._cache:
            return self._cache[key]

        tracer = self._ensure_tracer()
        paths: PropagationPaths
        if tracer is None:
            paths = plaza_specular_paths(spec)
        else:
            try:
                # Bundled scene "etoile" is a dense urban canyon; closest
                # available Sionna-bundled stand-in. A real Brussels Mitsuba
                # XML would replace this in a follow-up.
                grid_pos = np.array(key, dtype=np.float64) * self.grid_spacing_m
                result = tracer.trace_bundled.remote(  # type: ignore[attr-defined]
                    scene_name="etoile",
                    tx_pos=spec.bs_position.tolist(),
                    rx_pos=grid_pos.tolist(),
                    max_bounces=3,
                    freq_hz=spec.freq_hz,
                    tx_power_dbm=10.0 * np.log10(spec.tx_power_w * 1e3),
                )
                paths = PropagationPaths.from_dict(result["paths"])
            except Exception as exc:  # pragma: no cover - environmental
                logger.warning("Sionna trace failed at %s (%s); falling back", key, exc)
                self._disabled = True
                paths = plaza_specular_paths(spec)
        self._cache[key] = paths
        return paths


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


def make_path_generator(
    mode: str,
    bs_position: np.ndarray,
    freq_hz: float,
    tx_power_w: float,
    *,
    base_seed: int = 0,
):
    """Return a callable ``spec -> PropagationPaths`` for the requested mode."""
    if mode == "plaza_specular" or mode == "dict":
        return lambda spec: plaza_specular_paths(spec)
    if mode == "uma_los" or mode == "uma":
        return lambda spec: uma_los_paths(spec, base_seed=base_seed)
    if mode == "sionna_dict":
        d = SionnaDictionary(
            bs_position=np.asarray(bs_position, dtype=np.float64),
            freq_hz=freq_hz,
            tx_power_w=tx_power_w,
        )
        return lambda spec: d.get(spec)
    raise ValueError(f"unknown path mode: {mode!r}")
