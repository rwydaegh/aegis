"""Base station integration: load cell tower data into AEGIS dosimetry."""

from aegis.basestation.antenna import AntennaPattern, BaseStation
from aegis.basestation.coords import wgs84_to_enu
from aegis.basestation.exposure import ExposureMode, power_reduction_factor
from aegis.basestation.msi import PatternIndex, parse_msi
from aegis.basestation.orientation import antenna_rotation_matrix
from aegis.basestation.power import eirp_to_tx_power_dbm, eirp_to_tx_power_w

__all__ = [
    "AntennaPattern",
    "BaseStation",
    "ExposureMode",
    "PatternIndex",
    "antenna_rotation_matrix",
    "eirp_to_tx_power_dbm",
    "eirp_to_tx_power_w",
    "parse_msi",
    "power_reduction_factor",
    "wgs84_to_enu",
]
