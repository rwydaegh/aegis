"""Configuration for the headless population-exposure study.

One run is one config file. The dataclasses mirror the design spec's config
block. Cadences under ``temporal`` default to ``None`` until the cost-discovery
spike sets them.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import get_type_hints

import yaml


@dataclass(frozen=True)
class CitiesConfig:
    count: int = 1
    radius_m: float = 200.0
    # Optional explicit city list for multi-city runs. Each entry is a dict with
    # "name", "lat", "lon". Empty falls back to the single hardcoded core (Ghent).
    specs: list = field(default_factory=list)


@dataclass(frozen=True)
class MobilityConfig:
    n_agents: int = 50
    window_s: float = 60.0
    walk_speed_mps: float = 1.4
    user_fraction: float = 0.5


@dataclass(frozen=True)
class SectoringConfig:
    sectors: int = 3
    az_coverage_deg: float = 120.0
    max_range_m: float = 150.0


@dataclass(frozen=True)
class EquipmentConfig:
    name: str = "mmwave_mamimo_28ghz"
    array: tuple[int, int] = (8, 8)
    tx_power_dbm: float = 30.0
    height_class: str = "rooftop"
    freq_hz: float = 28.0e9


@dataclass(frozen=True)
class DeploymentConfig:
    process: str = "ginibre"
    density_source: str = "dataset"
    densification: float = 1.0
    realizations_K: int = 1
    sectoring: SectoringConfig = field(default_factory=SectoringConfig)
    equipment: EquipmentConfig = field(default_factory=EquipmentConfig)
    precoder: str = "mrt"


@dataclass(frozen=True)
class ChannelConfig:
    stochastic: str = "coherent_38901"
    los_blend: str = "p_los"
    seed: int = 42
    # Deterministic-arm ray-trace shoot-and-bounce sample count. 30M is the
    # converged plateau (per the samples convergence study); 3M is ~0.5% off and
    # ~10x cheaper, a fair knob to trade for breadth (more cities) on CPU.
    samples_per_src: int = 30_000_000
    diffraction: bool = True
    # Cap the center-path set to the strongest K (by power) before the Gram. The
    # Gram cost grows with path count; a diffraction-rich trace (tens of paths)
    # otherwise dominates. None keeps all paths.
    max_center_paths: int | None = None


@dataclass(frozen=True)
class DosimetryConfig:
    level: int = 7
    # Compute the per-triangle 4 cm^2-peak S_ab map (the expensive ~100 s/call
    # spatial map). Off -> the headline CDF is the cheap scalar x^H Q x absorbed
    # power, which the spec names the per-person headline. Keep off for breadth
    # (many cities); turn on for the ICNIRP-peak-density figure.
    peak_sab: bool = True


@dataclass(frozen=True)
class TemporalConfig:
    dt_s: float | None = None
    pose_period: int | None = None
    recompute_period: int | None = None


@dataclass(frozen=True)
class StudyConfig:
    cities: CitiesConfig = field(default_factory=CitiesConfig)
    mobility: MobilityConfig = field(default_factory=MobilityConfig)
    deployment: DeploymentConfig = field(default_factory=DeploymentConfig)
    channel: ChannelConfig = field(default_factory=ChannelConfig)
    dosimetry: DosimetryConfig = field(default_factory=DosimetryConfig)
    temporal: TemporalConfig = field(default_factory=TemporalConfig)

    @classmethod
    def from_yaml(cls, path: str | Path) -> StudyConfig:
        raw = yaml.safe_load(Path(path).read_text()) or {}
        return _build(cls, raw)


def _build(cls, raw: dict):
    """Recursively construct a (possibly nested) dataclass from a plain dict."""
    if not is_dataclass(cls):
        return raw
    # ``from __future__ import annotations`` stringizes f.type, so resolve the
    # real classes via get_type_hints before checking is_dataclass.
    hints = get_type_hints(cls)
    kwargs = {}
    for f in fields(cls):
        if f.name not in raw:
            continue
        val = raw[f.name]
        ftype = hints[f.name]
        if is_dataclass(ftype):
            kwargs[f.name] = _build(ftype, val)
        elif f.name == "array" and isinstance(val, list):
            kwargs[f.name] = tuple(val)
        else:
            kwargs[f.name] = val
    return cls(**kwargs)
