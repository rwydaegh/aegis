"""Core data structures: BaseStation and AntennaPattern."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aegis.basestation.provenance import FieldSource

import numpy as np


@dataclass(frozen=True)
class AntennaPattern:
    """Antenna radiation pattern from a 181x360 gain matrix.

    Rows: elevation index 0..180 maps to -90..+90 degrees.
    Columns: azimuth index 0..359 maps to -180..+179 degrees.
    Values are gain in dBi. NaN means zero radiation.
    """

    gain_dbi: np.ndarray  # (181, 360) float
    max_gain_dbi: float

    def __post_init__(self) -> None:
        if self.gain_dbi.shape != (181, 360):
            raise ValueError(f"gain_dbi must be (181, 360), got {self.gain_dbi.shape}")

    @property
    def gain_linear(self) -> np.ndarray:
        """(181, 360) linear gain, NaN replaced with 0."""
        g = np.copy(self.gain_dbi).astype(np.float64)
        g[np.isnan(g)] = -200.0  # floor
        return 10.0 ** (g / 10.0)

    def evaluate(self, elevation_deg: np.ndarray, azimuth_deg: np.ndarray) -> np.ndarray:
        """Interpolate linear gain at arbitrary (elevation, azimuth) angles.

        Parameters
        ----------
        elevation_deg : (N,) in [-90, 90], -90=nadir, 0=horizontal, 90=zenith
        azimuth_deg : (N,) in [-180, 180], antenna-local

        Returns
        -------
        gain_linear : (N,) linear power gain
        """
        from scipy.ndimage import map_coordinates

        elev = np.asarray(elevation_deg, dtype=np.float64)
        azim = np.asarray(azimuth_deg, dtype=np.float64)

        # Map to grid indices
        # Elevation: -90 -> index 0, +90 -> index 180
        row = elev + 90.0  # [0, 180]
        # Azimuth: -180 -> index 0, +179 -> index 359
        col = (azim + 180.0) % 360.0  # [0, 360)

        # Interpolate on linear-scale gain (avoids dB artifacts at nulls)
        g_lin = self.gain_linear
        coords = np.array([np.clip(row, 0, 180), col])
        # mode='nearest' for elevation (physical boundary), 'wrap' for azimuth
        result = map_coordinates(g_lin, coords, order=1, mode="nearest")
        return np.maximum(result, 0.0)


@dataclass(frozen=True)
class ExposureConfig:
    """Exposure reduction parameters for realistic modeling."""

    duplex_mode: str = "fdd"
    tdd_dl_ratio: float = 1.0
    power_reduction_factor: float = 1.0
    traffic_load_factor: float = 0.5


@dataclass(frozen=True)
class BeamConfig:
    """mMIMO broadcast/traffic beam separation for realistic exposure."""

    broadcast_gain_dbi: float = 18.0
    broadcast_hbw_deg: float = 65.0
    broadcast_vbw_deg: float = 10.0
    traffic_gain_dbi: float = 25.0
    traffic_hbw_deg: float = 12.0
    traffic_vbw_deg: float = 8.0
    sweep_h_range_deg: float = 60.0
    sweep_v_range_deg: float = 15.0


@dataclass(frozen=True)
class BaseStation:
    """A single physical antenna panel from a cell tower database."""

    site_code: str
    antenna_label: str
    operator: str
    technology: str

    # Location (WGS84)
    latitude: float
    longitude: float
    height_m: float  # above ground

    # RF
    eirp_dbm: float  # EIRP, not TX power
    gain_dbi: float  # peak antenna gain
    freq_mhz: float

    # Orientation
    azimuth_deg: float  # compass bearing (0=N, 90=E)
    electrical_tilt_deg: float  # downtilt, positive = below horizon
    mechanical_tilt_deg: float

    # Beamwidths
    horizontal_beamwidth_deg: float
    vertical_beamwidth_deg: float

    # Pattern (optional)
    pattern: AntennaPattern | None = None

    # Provenance
    frequency_band: str = ""
    provenance: tuple[tuple[str, FieldSource], ...] = ()
    pattern_source: str = ""

    @property
    def provenance_dict(self) -> dict[str, FieldSource]:
        """Dict access to provenance tuple."""
        return dict(self.provenance)

    @property
    def total_tilt_deg(self) -> float:
        return self.electrical_tilt_deg + self.mechanical_tilt_deg

    @property
    def freq_hz(self) -> float:
        return self.freq_mhz * 1e6
