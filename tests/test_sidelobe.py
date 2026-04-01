def test_sidelobe_floor_applied():
    """Synthetic pattern with sidelobe floor has minimum gain = peak - suppression."""
    from aegis.basestation.pattern import synthetic_pattern_from_beamwidth

    pattern = synthetic_pattern_from_beamwidth(65.0, 10.0, 17.0, sidelobe_suppression_db=15.0)
    assert pattern.gain_dbi.min() >= 17.0 - 15.0 - 0.01  # 2.0 dBi floor


def test_sidelobe_floor_default():
    """Default sidelobe floor is 15 dB."""
    from aegis.basestation.pattern import synthetic_pattern_from_beamwidth

    pattern = synthetic_pattern_from_beamwidth(65.0, 10.0, 17.0)
    assert pattern.gain_dbi.min() >= 17.0 - 15.0 - 0.01


def test_no_sidelobe_floor():
    """Setting suppression to None disables the floor."""
    from aegis.basestation.pattern import synthetic_pattern_from_beamwidth

    pattern = synthetic_pattern_from_beamwidth(65.0, 10.0, 17.0, sidelobe_suppression_db=None)
    assert pattern.gain_dbi[90, 0] < 17.0 - 30.0  # back lobe, well below any floor
