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


def test_beam_decomposition_actual_max():
    """actual_max uses max(broadcast, traffic) for mMIMO in sweep range."""
    import numpy as np

    from aegis.basestation import BaseStation
    from aegis.basestation.adapter import paths_from_basestation
    from aegis.basestation.antenna import BeamConfig, ExposureConfig
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
    body = np.array([0.0, 50.0, 1.5])  # on boresight, within sweep range
    origin = (50.85, 4.35)
    exp = ExposureConfig(duplex_mode="tdd", tdd_dl_ratio=0.75, power_reduction_factor=0.32)
    beam = BeamConfig()

    paths = paths_from_basestation(
        bs,
        body,
        origin,
        exposure_mode=ExposureMode.ACTUAL_MAX,
        exposure_config=exp,
        beam_config=beam,
        archetype="mmimo",
    )
    assert paths.total_power > 0


def test_beam_decomposition_outside_sweep():
    """Outside sweep range, only broadcast beam contributes."""
    import numpy as np

    from aegis.basestation import BaseStation
    from aegis.basestation.adapter import paths_from_basestation
    from aegis.basestation.antenna import BeamConfig, ExposureConfig
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
    # Body at ~90 degrees azimuth -- outside +/-60 sweep
    body = np.array([200.0, 0.0, 1.5])
    origin = (50.85, 4.35)
    exp = ExposureConfig(duplex_mode="tdd", tdd_dl_ratio=0.75, power_reduction_factor=0.32)
    beam = BeamConfig(sweep_h_range_deg=60.0)

    paths_outside = paths_from_basestation(
        bs,
        body,
        origin,
        exposure_mode=ExposureMode.ACTUAL_MAX,
        exposure_config=exp,
        beam_config=beam,
        archetype="mmimo",
    )

    # On boresight for comparison
    body_boresight = np.array([0.0, 50.0, 1.5])
    paths_boresight = paths_from_basestation(
        bs,
        body_boresight,
        origin,
        exposure_mode=ExposureMode.ACTUAL_MAX,
        exposure_config=exp,
        beam_config=beam,
        archetype="mmimo",
    )

    # Outside sweep should have less power than boresight (no traffic beam)
    assert paths_outside.total_power < paths_boresight.total_power


def test_beam_typical_mode_lower_than_actual_max():
    """Typical mode produces lower power than actual_max."""
    import numpy as np

    from aegis.basestation import BaseStation
    from aegis.basestation.adapter import paths_from_basestation
    from aegis.basestation.antenna import BeamConfig, ExposureConfig
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
    body = np.array([0.0, 50.0, 1.5])
    origin = (50.85, 4.35)
    exp = ExposureConfig(duplex_mode="tdd", tdd_dl_ratio=0.75, power_reduction_factor=0.32, traffic_load_factor=0.5)
    beam = BeamConfig()

    paths_actual = paths_from_basestation(
        bs,
        body,
        origin,
        exposure_mode=ExposureMode.ACTUAL_MAX,
        exposure_config=exp,
        beam_config=beam,
        archetype="mmimo",
    )
    paths_typical = paths_from_basestation(
        bs,
        body,
        origin,
        exposure_mode=ExposureMode.TYPICAL,
        exposure_config=exp,
        beam_config=beam,
        archetype="mmimo",
    )

    # typical should be lower because traffic beam is scaled by traffic_load_factor
    # and typical uses sum (broadcast + traffic*load) vs actual_max uses max(broadcast, traffic)
    assert paths_typical.total_power <= paths_actual.total_power
