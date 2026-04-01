import math

import pytest


def test_theoretical_mode_no_reduction():
    from aegis.basestation import BaseStation
    from aegis.basestation.antenna import ExposureConfig
    from aegis.basestation.power import ExposureMode, effective_eirp_dbm

    bs = BaseStation(
        site_code="T",
        antenna_label="A",
        operator="Op",
        technology="5G",
        latitude=0,
        longitude=0,
        height_m=10,
        eirp_dbm=50.0,
        gain_dbi=25.0,
        freq_mhz=3500,
        azimuth_deg=0,
        electrical_tilt_deg=0,
        mechanical_tilt_deg=0,
        horizontal_beamwidth_deg=65,
        vertical_beamwidth_deg=10,
    )
    exp = ExposureConfig(
        duplex_mode="tdd",
        tdd_dl_ratio=0.75,
        power_reduction_factor=0.32,
        traffic_load_factor=0.5,
    )
    result = effective_eirp_dbm(bs, exp, ExposureMode.THEORETICAL)
    assert result == pytest.approx(50.0)


def test_actual_max_applies_tdd_and_prf():
    from aegis.basestation import BaseStation
    from aegis.basestation.antenna import ExposureConfig
    from aegis.basestation.power import ExposureMode, effective_eirp_dbm

    bs = BaseStation(
        site_code="T",
        antenna_label="A",
        operator="Op",
        technology="5G",
        latitude=0,
        longitude=0,
        height_m=10,
        eirp_dbm=50.0,
        gain_dbi=25.0,
        freq_mhz=3500,
        azimuth_deg=0,
        electrical_tilt_deg=0,
        mechanical_tilt_deg=0,
        horizontal_beamwidth_deg=65,
        vertical_beamwidth_deg=10,
    )
    exp = ExposureConfig(
        duplex_mode="tdd",
        tdd_dl_ratio=0.75,
        power_reduction_factor=0.32,
        traffic_load_factor=0.5,
    )
    result = effective_eirp_dbm(bs, exp, ExposureMode.ACTUAL_MAX)
    # factor = 0.75 * 0.32 = 0.24, 10*log10(0.24) = -6.198
    expected = 50.0 + 10 * math.log10(0.75 * 0.32)
    assert result == pytest.approx(expected, abs=0.01)


def test_typical_applies_all_factors():
    from aegis.basestation import BaseStation
    from aegis.basestation.antenna import ExposureConfig
    from aegis.basestation.power import ExposureMode, effective_eirp_dbm

    bs = BaseStation(
        site_code="T",
        antenna_label="A",
        operator="Op",
        technology="5G",
        latitude=0,
        longitude=0,
        height_m=10,
        eirp_dbm=50.0,
        gain_dbi=25.0,
        freq_mhz=3500,
        azimuth_deg=0,
        electrical_tilt_deg=0,
        mechanical_tilt_deg=0,
        horizontal_beamwidth_deg=65,
        vertical_beamwidth_deg=10,
    )
    exp = ExposureConfig(
        duplex_mode="tdd",
        tdd_dl_ratio=0.75,
        power_reduction_factor=0.32,
        traffic_load_factor=0.5,
    )
    result = effective_eirp_dbm(bs, exp, ExposureMode.TYPICAL)
    # factor = 0.75 * 0.32 * 0.5 = 0.12
    expected = 50.0 + 10 * math.log10(0.75 * 0.32 * 0.5)
    assert result == pytest.approx(expected, abs=0.01)


def test_near_zero_traffic_load_clamped():
    """traffic_load_factor=0 should not produce -inf."""
    from aegis.basestation import BaseStation
    from aegis.basestation.antenna import ExposureConfig
    from aegis.basestation.power import ExposureMode, effective_eirp_dbm

    bs = BaseStation(
        site_code="T",
        antenna_label="A",
        operator="Op",
        technology="5G",
        latitude=0,
        longitude=0,
        height_m=10,
        eirp_dbm=50.0,
        gain_dbi=25.0,
        freq_mhz=3500,
        azimuth_deg=0,
        electrical_tilt_deg=0,
        mechanical_tilt_deg=0,
        horizontal_beamwidth_deg=65,
        vertical_beamwidth_deg=10,
    )
    exp = ExposureConfig(tdd_dl_ratio=0.75, power_reduction_factor=0.32, traffic_load_factor=0.0)
    result = effective_eirp_dbm(bs, exp, ExposureMode.TYPICAL)
    assert math.isfinite(result)
    assert result <= -50


def test_paths_from_basestation_actual_max_reduces_power():
    """actual_max mode produces lower power than theoretical."""
    import numpy as np

    from aegis.basestation import BaseStation
    from aegis.basestation.adapter import paths_from_basestation
    from aegis.basestation.antenna import ExposureConfig
    from aegis.basestation.power import ExposureMode

    bs = BaseStation(
        site_code="T",
        antenna_label="A",
        operator="Op",
        technology="5G",
        latitude=50.85,
        longitude=4.35,
        height_m=30,
        eirp_dbm=50.0,
        gain_dbi=25.0,
        freq_mhz=3500,
        azimuth_deg=0,
        electrical_tilt_deg=6,
        mechanical_tilt_deg=0,
        horizontal_beamwidth_deg=65,
        vertical_beamwidth_deg=10,
    )
    body = np.array([0.0, 100.0, 1.5])
    origin = (50.85, 4.35)
    exp = ExposureConfig(tdd_dl_ratio=0.75, power_reduction_factor=0.32, traffic_load_factor=0.5)

    paths_theo = paths_from_basestation(bs, body, origin)
    paths_actual = paths_from_basestation(bs, body, origin, exposure_mode=ExposureMode.ACTUAL_MAX, exposure_config=exp)

    assert paths_actual.total_power < paths_theo.total_power
    # Factor should be 0.75 * 0.32 = 0.24, so power ratio should be ~0.24
    ratio = paths_actual.total_power / paths_theo.total_power
    assert 0.2 < ratio < 0.3


def test_paths_from_basestation_backward_compatible():
    """Without exposure params, behavior is unchanged."""
    import numpy as np

    from aegis.basestation import BaseStation
    from aegis.basestation.adapter import paths_from_basestation

    bs = BaseStation(
        site_code="T",
        antenna_label="A",
        operator="Op",
        technology="5G",
        latitude=50.85,
        longitude=4.35,
        height_m=30,
        eirp_dbm=50.0,
        gain_dbi=25.0,
        freq_mhz=3500,
        azimuth_deg=0,
        electrical_tilt_deg=6,
        mechanical_tilt_deg=0,
        horizontal_beamwidth_deg=65,
        vertical_beamwidth_deg=10,
    )
    body = np.array([0.0, 100.0, 1.5])
    origin = (50.85, 4.35)

    paths1 = paths_from_basestation(bs, body, origin)
    paths2 = paths_from_basestation(bs, body, origin)
    assert abs(paths1.total_power - paths2.total_power) < 1e-12
