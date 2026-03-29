"""Tests for base station archetype classification."""

from aegis.basestation.classify import classify_antenna, infer_element_grid


class TestClassifyAntenna:
    """Archetype assignment from antenna metadata."""

    def test_mmimo_high_gain_5g(self):
        result = classify_antenna(
            gain_dbi=24.8,
            technology="5G",
            freq_mhz=3750.0,
            h_bw=126,
            v_bw=34,
        )
        assert result == "mmimo"

    def test_mmimo_mixed_4g5g(self):
        result = classify_antenna(
            gain_dbi=22.0,
            technology="4G/5G",
            freq_mhz=3750.0,
            h_bw=100,
            v_bw=20,
        )
        assert result == "mmimo"

    def test_sector_typical_4g(self):
        result = classify_antenna(
            gain_dbi=16.8,
            technology="4G",
            freq_mhz=1800.0,
            h_bw=65,
            v_bw=10,
        )
        assert result == "sector"

    def test_sector_high_gain_non_5g(self):
        """High gain but not 5G should NOT be mmimo."""
        result = classify_antenna(
            gain_dbi=22.0,
            technology="4G",
            freq_mhz=2600.0,
            h_bw=65,
            v_bw=7,
        )
        assert result == "sector"

    def test_small_cell_low_gain(self):
        result = classify_antenna(
            gain_dbi=2.1,
            technology="2G",
            freq_mhz=800.0,
            h_bw=168,
            v_bw=100,
        )
        assert result == "small_cell"

    def test_null_technology_not_mmimo(self):
        """Unknown tech should never classify as mmimo."""
        result = classify_antenna(
            gain_dbi=24.0,
            technology=None,
            freq_mhz=3750.0,
            h_bw=126,
            v_bw=34,
        )
        assert result != "mmimo"

    def test_empty_technology_not_mmimo(self):
        result = classify_antenna(
            gain_dbi=24.0,
            technology="",
            freq_mhz=3750.0,
            h_bw=126,
            v_bw=34,
        )
        assert result != "mmimo"


class TestInferElementGrid:
    """Element count inference and grid snapping."""

    def test_mmimo_snaps_to_standard_grid(self):
        n_h, n_v = infer_element_grid(
            archetype="mmimo",
            gain_dbi=24.8,
            element_gain_dbi=5.0,
        )
        assert n_h * n_v in (64, 128)
        assert n_v >= n_h  # tall panels

    def test_sector_dual_column(self):
        n_h, n_v = infer_element_grid(
            archetype="sector",
            gain_dbi=16.0,
            element_gain_dbi=5.0,
        )
        assert n_h in (1, 2)
        assert n_v >= 2

    def test_small_cell_minimal(self):
        n_h, n_v = infer_element_grid(
            archetype="small_cell",
            gain_dbi=2.1,
            element_gain_dbi=5.0,
        )
        assert n_h == 1
        assert n_v == 1

    def test_small_cell_moderate_gain(self):
        n_h, n_v = infer_element_grid(
            archetype="small_cell",
            gain_dbi=8.0,
            element_gain_dbi=5.0,
        )
        assert n_h * n_v in (1, 4)

    def test_custom_element_gain(self):
        n_h_5, n_v_5 = infer_element_grid(
            archetype="mmimo",
            gain_dbi=24.8,
            element_gain_dbi=5.0,
        )
        n_h_7, n_v_7 = infer_element_grid(
            archetype="mmimo",
            gain_dbi=24.8,
            element_gain_dbi=7.0,
        )
        # Higher element gain means fewer inferred elements
        assert n_h_7 * n_v_7 <= n_h_5 * n_v_5
