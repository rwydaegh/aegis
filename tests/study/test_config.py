from pathlib import Path

from aegis.study.config import StudyConfig


def test_loads_v1_yaml(tmp_path):
    yaml_text = (Path(__file__).parents[2] / "configs/study/ghent_core_v1.yaml").read_text()
    cfg_file = tmp_path / "c.yaml"
    cfg_file.write_text(yaml_text)

    cfg = StudyConfig.from_yaml(cfg_file)

    assert cfg.cities.count == 1
    assert cfg.cities.radius_m == 200.0
    assert cfg.mobility.n_agents == 50
    assert cfg.mobility.walk_speed_mps == 1.4
    assert cfg.deployment.sectoring.sectors == 3
    assert cfg.deployment.sectoring.az_coverage_deg == 120.0
    assert cfg.deployment.equipment.array == (8, 8)
    assert cfg.deployment.equipment.freq_hz == 28.0e9
    assert cfg.dosimetry.level == 7
    assert cfg.channel.seed == 42


def test_defaults_round_trip():
    cfg = StudyConfig()  # all defaults from the spec
    assert cfg.deployment.realizations_K == 1
    assert cfg.deployment.precoder == "mrt"
    assert cfg.temporal.dt_s is None  # TBD until the spike sets it
