"""Project-wide default values.

Single source of truth for all defaults that appear in function
signatures, dataclass fields, and config dicts. This module has no
imports and must remain a leaf dependency to avoid circular imports.
"""

DEFAULT_FREQ_HZ: float = 28e9
DEFAULT_POWER_DBM: float = 60.0
DEFAULT_P_ABS_MAX: float = 0.1         # absorbed power limit [W]
DEFAULT_NOISE_POWER: float = 0.01      # MMSE noise power
DEFAULT_FIDELITY_LEVEL: int = 2
DEFAULT_MAX_BOUNCES: int = 3
DEFAULT_SEED: int = 42

NUMERICAL_FLOOR: float = 1e-30         # safe-division guard

CONCRETE_EPS_R: float = 5.31           # material fallback
CONCRETE_SIGMA: float = 0.0326
