"""Verify defaults.py constants match the values previously hardcoded."""

from aegis.defaults import (
    CONCRETE_EPS_R,
    CONCRETE_SIGMA,
    DEFAULT_FIDELITY_LEVEL,
    DEFAULT_FREQ_HZ,
    DEFAULT_MAX_BOUNCES,
    DEFAULT_NOISE_POWER,
    DEFAULT_P_ABS_MAX,
    DEFAULT_POWER_DBM,
    DEFAULT_SEED,
    NUMERICAL_FLOOR,
)


def test_default_values():
    assert DEFAULT_FREQ_HZ == 28e9
    assert DEFAULT_POWER_DBM == 60.0
    assert DEFAULT_P_ABS_MAX == 0.1
    assert DEFAULT_NOISE_POWER == 0.01
    assert DEFAULT_FIDELITY_LEVEL == 2
    assert DEFAULT_MAX_BOUNCES == 3
    assert DEFAULT_SEED == 42
    assert NUMERICAL_FLOOR == 1e-30
    assert CONCRETE_EPS_R == 5.31
    assert CONCRETE_SIGMA == 0.0326
