"""Tests for SimulationConfig dataclass hierarchy."""

import pytest

from aegis.config import (
    AntennaConfig,
    BodyConfig,
    DosimetryConfig,
    RayTracerConfig,
    SimulationConfig,
    TissueConfig,
)


def _make_config(**overrides):
    """Build a SimulationConfig with sensible defaults, overridable per sub-config."""
    defaults = dict(
        tissue=TissueConfig(),
        body=BodyConfig(),
        antenna=AntennaConfig(positions=[[5.0, 0.0, 1.0]]),
        raytracer=RayTracerConfig(),
        dosimetry=DosimetryConfig(),
    )
    defaults.update(overrides)
    return SimulationConfig(**defaults)


class TestValidation:
    def test_valid_config(self):
        cfg = _make_config()
        assert cfg.dosimetry.level == 2
        assert cfg.tissue.frequency_hz == 28e9

    def test_invalid_level_too_high(self):
        with pytest.raises(ValueError, match="level"):
            _make_config(dosimetry=DosimetryConfig(level=9))

    def test_invalid_level_negative(self):
        with pytest.raises(ValueError, match="level"):
            _make_config(dosimetry=DosimetryConfig(level=-1))

    def test_invalid_backend(self):
        with pytest.raises(ValueError, match="backend"):
            _make_config(raytracer=RayTracerConfig(backend="invalid"))

    def test_invalid_frequency(self):
        with pytest.raises(ValueError, match="frequency"):
            TissueConfig(frequency_hz=-1.0)


class TestYamlRoundTrip:
    def test_round_trip(self, tmp_path):
        original = _make_config()
        yaml_path = tmp_path / "config.yaml"
        original.to_yaml(yaml_path)
        loaded = SimulationConfig.from_yaml(yaml_path)
        assert loaded == original

    def test_round_trip_non_defaults(self, tmp_path):
        original = _make_config(
            tissue=TissueConfig(name="Muscle", frequency_hz=60e9),
            body=BodyConfig(name="duke", mass_kg=73.0),
            dosimetry=DosimetryConfig(level=6, spatial_averaging=True),
            raytracer=RayTracerConfig(backend="sionna", max_bounces=5, scene_path="/tmp/scene.xml"),
        )
        yaml_path = tmp_path / "config.yaml"
        original.to_yaml(yaml_path)
        loaded = SimulationConfig.from_yaml(yaml_path)
        assert loaded == original

    def test_yaml_is_readable(self, tmp_path):
        """The saved YAML should be human-readable, not a binary dump."""
        cfg = _make_config()
        yaml_path = tmp_path / "config.yaml"
        cfg.to_yaml(yaml_path)
        text = yaml_path.read_text()
        assert "tissue:" in text
        assert "frequency_hz:" in text
        assert "level: 2" in text
