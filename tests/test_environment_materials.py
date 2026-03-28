import pytest

from aegis.environment import MATERIAL_EM_PROPERTIES, MaterialType
from aegis.environment.materials import classify_color, get_em_properties


class TestGetEmProperties:
    def test_default_concrete(self):
        eps_r, sigma = get_em_properties(MaterialType.CONCRETE)
        assert eps_r == pytest.approx(5.31)
        assert sigma == pytest.approx(0.0326)

    def test_override(self):
        eps_r, sigma = get_em_properties(
            MaterialType.CONCRETE,
            overrides={"concrete": {"eps_r": 6.0, "sigma": 0.05}},
        )
        assert eps_r == pytest.approx(6.0)
        assert sigma == pytest.approx(0.05)

    def test_unknown_defaults_to_concrete(self):
        eps_r, sigma = get_em_properties(MaterialType.UNKNOWN)
        concrete = MATERIAL_EM_PROPERTIES[MaterialType.CONCRETE]
        assert eps_r == pytest.approx(concrete["eps_r"])


class TestClassifyColor:
    def test_gray_is_concrete(self):
        assert classify_color(128, 128, 128) == MaterialType.CONCRETE

    def test_green_is_vegetation(self):
        assert classify_color(50, 150, 50) == MaterialType.VEGETATION

    def test_blue_is_water(self):
        assert classify_color(30, 30, 200) == MaterialType.WATER

    def test_dark_gray_is_asphalt(self):
        assert classify_color(60, 60, 60) == MaterialType.ASPHALT

    def test_brown_is_brick(self):
        assert classify_color(160, 82, 45) == MaterialType.BRICK
