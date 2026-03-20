"""Tests for TissueModel dataclass."""

from pathlib import Path

import pytest

from aegis.tissue import FAT_28GHZ, MUSCLE_28GHZ, SKIN_28GHZ, SKIN_60GHZ, TissueModel


class TestPredefinedTissues:
    """Predefined tissue instances match expected values."""

    def test_skin_28ghz_T0(self):
        # Hardcoded params (eps_r=17, sigma=25) give T0~0.539, not 0.536
        # The 0.536 value uses IT'IS Cole-Cole params (eps_r=16.55, sigma=25.8)
        assert pytest.approx(0.539, abs=0.002) == SKIN_28GHZ.T0

    def test_skin_60ghz_T0(self):
        assert pytest.approx(0.622, abs=0.002) == SKIN_60GHZ.T0

    def test_fat_28ghz_T0(self):
        """Fat has higher transmission (lower |n|)."""
        # Hardcoded fat params (eps_r=4, sigma=2) give T0~0.876
        assert pytest.approx(0.876, abs=0.005) == FAT_28GHZ.T0

    def test_muscle_28ghz_T0(self):
        """Muscle has lower transmission (higher |n|)."""
        assert pytest.approx(0.48, abs=0.02) == MUSCLE_28GHZ.T0

    def test_T0_ordering(self):
        """Fat > Skin > Muscle (lower |n| means higher transmission)."""
        assert FAT_28GHZ.T0 > SKIN_28GHZ.T0 > MUSCLE_28GHZ.T0


class TestTissueModel:
    """TissueModel construction and properties."""

    def test_from_params(self):
        t = TissueModel.from_params("Test", 17.0, 25.0, 28e9)
        assert t.name == "Test"
        assert t.eps_r == 17.0
        assert t.sigma == 25.0
        assert t.freq_hz == 28e9

    def test_from_params_matches_direct(self):
        t1 = TissueModel("Skin 28 GHz", 17.0, 25.0, 28e9)
        t2 = TissueModel.from_params("Skin 28 GHz", 17.0, 25.0, 28e9)
        assert t1.T0 == t2.T0
        assert t1.n_complex == t2.n_complex

    def test_n_complex_positive_real(self):
        assert SKIN_28GHZ.n_complex.real > 0

    def test_T0_in_unit_interval(self):
        for tissue in [SKIN_28GHZ, SKIN_60GHZ, FAT_28GHZ, MUSCLE_28GHZ]:
            assert 0 < tissue.T0 < 1

    def test_frozen(self):
        with pytest.raises(AttributeError):
            SKIN_28GHZ.eps_r = 99.0


class TestSkinColeColeVsPreset:
    @pytest.mark.slow
    def test_skin_28ghz_database_near_literature_preset(self, data_dir: Path):
        db_path = data_dir / "itis_v5.db"
        if not db_path.exists():
            pytest.skip("itis_v5.db not found")
        from_db = TissueModel.from_database("Skin", 28e9, db_path=db_path)
        # Literature preset vs IT'IS Cole-Cole fit: allow moderate deviation.
        rel_eps = abs(from_db.eps_r - SKIN_28GHZ.eps_r) / max(SKIN_28GHZ.eps_r, 1e-12)
        rel_sig = abs(from_db.sigma - SKIN_28GHZ.sigma) / max(SKIN_28GHZ.sigma, 1e-12)
        assert rel_eps <= 0.20
        assert rel_sig <= 0.20
