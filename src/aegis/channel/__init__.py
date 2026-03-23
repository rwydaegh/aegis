"""3GPP TR 38.901 stochastic channel model for dosimetry."""

from aegis.channel.generator import generate_channel
from aegis.channel.presets import list_presets, load_preset, parse_conf

__all__ = ["generate_channel", "list_presets", "load_preset", "parse_conf"]
