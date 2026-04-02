"""3GPP TR 38.901 stochastic channel model for dosimetry."""

from aegis.channel.correlation import build_correlation_matrix
from aegis.channel.generator import generate_channel
from aegis.channel.lsf import LSFModel
from aegis.channel.presets import list_presets, load_preset, parse_conf
from aegis.channel.sos import SumOfSinusoids

__all__ = [
    "LSFModel",
    "SumOfSinusoids",
    "build_correlation_matrix",
    "generate_channel",
    "list_presets",
    "load_preset",
    "parse_conf",
]
