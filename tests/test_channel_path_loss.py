import math

import pytest


def test_logdist_freespace():
    """Freespace: PL = 20*log10(d) + 32.45 + 20*log10(f)."""
    from aegis.channel.path_loss import compute_path_loss

    params = {"PL_model": "logdist", "PL_A": 20, "PL_B": 32.45, "PL_C": 20}
    pl = compute_path_loss(params, distance_m=100, freq_ghz=28)
    expected = 20 * math.log10(100) + 32.45 + 20 * math.log10(28)
    assert pl == pytest.approx(expected, abs=0.01)


def test_dual_slope():
    """UMi LOS dual slope before breakpoint."""
    from aegis.channel.path_loss import compute_path_loss

    params = {
        "PL_model": "dual_slope",
        "PL_A1": 21,
        "PL_A2": 40,
        "PL_B": 32.4,
        "PL_C": 20,
        "PL_E": 13.34,
        "PL_hE": 1,
    }
    pl = compute_path_loss(params, distance_m=50, freq_ghz=28, h_bs=10, h_ms=1.5)
    d3d = math.sqrt(50**2 + (10 - 1.5) ** 2)
    expected = 21 * math.log10(d3d) + 32.4 + 20 * math.log10(28)
    assert pl == pytest.approx(expected, abs=0.5)


def test_unsupported_model_fallback():
    """Unsupported PL model falls back to free-space."""
    from aegis.channel.path_loss import compute_path_loss

    params = {"PL_model": "satellite"}
    pl = compute_path_loss(params, distance_m=100, freq_ghz=28)
    expected = 20 * math.log10(100) + 20 * math.log10(28) + 32.45
    assert pl == pytest.approx(expected, abs=0.1)


def test_constant_model():
    """Constant PL model returns PL_A regardless of distance or frequency."""
    from aegis.channel.path_loss import compute_path_loss

    params = {"PL_model": "constant", "PL_A": 95}
    assert compute_path_loss(params, distance_m=10, freq_ghz=2) == pytest.approx(95.0)
    assert compute_path_loss(params, distance_m=1000, freq_ghz=28) == pytest.approx(95.0)


def test_constant_model_null_preset():
    """Null preset (PL_A=1000) attenuates the channel to effectively zero."""
    from aegis.channel.path_loss import compute_path_loss

    params = {"PL_model": "constant", "PL_A": 1000}
    pl = compute_path_loss(params, distance_m=4, freq_ghz=28)
    assert pl == pytest.approx(1000.0)


def test_constant_model_default_a():
    """Constant PL model with no PL_A defaults to 0 dB (no attenuation)."""
    from aegis.channel.path_loss import compute_path_loss

    params = {"PL_model": "constant"}
    assert compute_path_loss(params, distance_m=100, freq_ghz=28) == pytest.approx(0.0)
