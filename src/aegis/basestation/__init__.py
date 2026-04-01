"""Base station integration: load cell tower data into AEGIS dosimetry."""

from aegis.basestation.antenna import AntennaPattern, BaseStation, BeamConfig, ExposureConfig
from aegis.basestation.coords import wgs84_to_enu
from aegis.basestation.orientation import antenna_rotation_matrix
from aegis.basestation.power import (
    ExposureMode,
    effective_eirp_dbm,
    eirp_to_tx_power_dbm,
    eirp_to_tx_power_w,
)

__all__ = [
    "AntennaPattern",
    "BaseStation",
    "BeamConfig",
    "ExposureConfig",
    "ExposureMode",
    "antenna_rotation_matrix",
    "effective_eirp_dbm",
    "eirp_to_tx_power_dbm",
    "eirp_to_tx_power_w",
    "wgs84_to_enu",
]
