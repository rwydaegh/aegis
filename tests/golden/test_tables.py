"""Golden tests: monograph table reproduction using IT'IS database.

These tests require the IT'IS v5.0 database (itis_v5.db) in the data directory.
They validate the full Cole-Cole pipeline against published monograph values.
"""

import pytest

from aegis.tissue.dielectric import TissueModel

pytestmark = pytest.mark.slow


# Monograph Table 4: T_0 values for skin at various frequencies (IT'IS v5.0 Cole-Cole)
# Source: monograph_v2.tex, tab:Tbar
TABLE_T0_SKIN = [
    # (freq_ghz, expected_T0)
    (6, 0.481),
    (10, 0.489),
    (28, 0.536),
    (40, 0.570),
    (60, 0.622),
    (100, 0.701),
]


class TestMonographTableT0:
    """Monograph Table 4: T_0 from IT'IS database skin properties."""

    @pytest.mark.parametrize(("freq_ghz", "expected_T0"), TABLE_T0_SKIN)
    def test_T0_skin(self, freq_ghz, expected_T0):
        tissue = TissueModel.from_database("Skin", freq_ghz * 1e9)
        assert pytest.approx(expected_T0, abs=0.003) == tissue.T0

    def test_T0_increases_with_frequency(self):
        """T_0 for skin increases monotonically from 6 to 100 GHz."""
        T0_values = []
        for freq_ghz, _ in TABLE_T0_SKIN:
            tissue = TissueModel.from_database("Skin", freq_ghz * 1e9)
            T0_values.append(tissue.T0)

        for i in range(len(T0_values) - 1):
            assert T0_values[i] < T0_values[i + 1]


# Monograph Table 5: Dielectric properties of skin (IT'IS v5.0)
# Source: monograph_v2.tex, tab:skin-data
TABLE_SKIN_PROPERTIES = [
    # (freq_ghz, expected_eps_r, expected_abs_n)
    (6, 34.95, 6.07),
    (28, 16.55, 4.84),
    (60, 7.98, 3.68),
    (100, 5.60, 3.01),
]


class TestMonographTableSkinProperties:
    """Monograph Table 5: skin dielectric properties from Cole-Cole model."""

    @pytest.mark.parametrize(("freq_ghz", "exp_eps_r", "exp_abs_n"), TABLE_SKIN_PROPERTIES)
    def test_skin_properties(self, freq_ghz, exp_eps_r, exp_abs_n):
        tissue = TissueModel.from_database("Skin", freq_ghz * 1e9)
        assert tissue.eps_r == pytest.approx(exp_eps_r, rel=0.02)
        assert abs(tissue.n_complex) == pytest.approx(exp_abs_n, abs=0.05)
