"""Simulation configuration: frozen dataclasses with YAML serialization.

Defines a complete, reproducible simulation run. Separate from the viewer
config system (viewer/config.py). Each run saves its resolved config as
YAML alongside results.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from aegis.defaults import (
    DEFAULT_FIDELITY_LEVEL,
    DEFAULT_FREQ_HZ,
    DEFAULT_MAX_BOUNCES,
    DEFAULT_NOISE_POWER,
    DEFAULT_P_ABS_MAX,
    DEFAULT_POWER_DBM,
    DEFAULT_SEED,
)


@dataclass(frozen=True)
class TissueConfig:
    """Tissue properties for the simulation."""

    name: str = "Skin"  # IT'IS database uses capitalized names
    frequency_hz: float = DEFAULT_FREQ_HZ

    def __post_init__(self) -> None:
        if self.frequency_hz <= 0:
            raise ValueError(f"frequency_hz must be positive, got {self.frequency_hz}")


@dataclass(frozen=True)
class BodyConfig:
    """Body phantom selection."""

    name: str = "thelonious"
    mass_kg: float | None = None


@dataclass(frozen=True)
class AntennaConfig:
    """Transmit antenna configuration."""

    positions: list[list[float]] = field(default_factory=lambda: [[5.0, 0.0, 1.0]])
    power_dbm: float = DEFAULT_POWER_DBM
    polarisation: str = "vertical"
    pattern: str = "isotropic"


@dataclass(frozen=True)
class RayTracerConfig:
    """Ray tracer backend selection."""

    backend: str = "differt"
    max_bounces: int = DEFAULT_MAX_BOUNCES
    scene_path: str | None = None

    def __post_init__(self) -> None:
        if self.backend not in ("differt", "sionna", "synthetic"):
            raise ValueError(f"backend must be 'differt', 'sionna', or 'synthetic', got '{self.backend}'")


@dataclass(frozen=True)
class DosimetryConfig:
    """Dosimetry computation parameters."""

    level: int = DEFAULT_FIDELITY_LEVEL
    spatial_averaging: bool = False
    n_paths: int = 1
    max_order: int = 0
    p_abs_max: float = DEFAULT_P_ABS_MAX

    def __post_init__(self) -> None:
        if not 0 <= self.level <= 8:
            raise ValueError(f"level must be 0-8, got {self.level}")


@dataclass(frozen=True)
class ChannelConfig:
    """Stochastic channel model parameters."""

    preset: str = "3GPP_38.901_UMi_LOS"
    seed: int = DEFAULT_SEED
    overrides: dict = field(default_factory=dict)


@dataclass(frozen=True)
class MIMOConfig:
    """MIMO array and precoder parameters."""

    precoder: str = "mrt"
    noise_power: float = DEFAULT_NOISE_POWER
    n_rows: int = 4
    n_cols: int = 4


@dataclass(frozen=True)
class SimulationConfig:
    """Complete simulation run configuration.

    Fully describes a reproducible simulation: tissue, body, antenna,
    ray tracer, and dosimetry parameters.
    """

    tissue: TissueConfig = field(default_factory=TissueConfig)
    body: BodyConfig = field(default_factory=BodyConfig)
    antenna: AntennaConfig = field(default_factory=AntennaConfig)
    raytracer: RayTracerConfig = field(default_factory=RayTracerConfig)
    dosimetry: DosimetryConfig = field(default_factory=DosimetryConfig)
    channel: ChannelConfig = field(default_factory=ChannelConfig)
    mimo: MIMOConfig = field(default_factory=MIMOConfig)
    output_dir: str = "outputs"

    def to_yaml(self, path: str | Path) -> None:
        """Save config as YAML."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w") as f:
            yaml.dump(dataclasses.asdict(self), f, default_flow_style=False, sort_keys=False)

    @classmethod
    def from_yaml(cls, path: str | Path) -> SimulationConfig:
        """Load config from YAML."""
        with Path(path).open() as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict) -> SimulationConfig:
        """Reconstruct a SimulationConfig from a nested dict (e.g. YAML output)."""
        known = {f.name for f in dataclasses.fields(cls)}
        unknown = set(data) - known
        if unknown:
            raise ValueError(f"Unknown config keys: {unknown}")
        kwargs = {}
        for key, val in data.items():
            if key in _CONFIG_CLASSES and isinstance(val, dict):
                kwargs[key] = _CONFIG_CLASSES[key](**val)
            else:
                kwargs[key] = val
        return cls(**kwargs)


_CONFIG_CLASSES: dict[str, type] = {
    "tissue": TissueConfig,
    "body": BodyConfig,
    "antenna": AntennaConfig,
    "raytracer": RayTracerConfig,
    "dosimetry": DosimetryConfig,
    "channel": ChannelConfig,
    "mimo": MIMOConfig,
}
