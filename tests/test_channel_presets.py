from pathlib import Path

import pytest

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "channel_presets"


def test_parse_freespace():
    from aegis.channel.presets import parse_conf

    params = parse_conf(DATA_DIR / "Freespace.conf")
    assert params["NumClusters"] == 1
    assert params["SF_sigma"] == 0
    assert params["KF_mu"] == 0
    assert params["PL_model"] == "logdist"
    assert params["PL_A"] == 20
    assert params["PL_B"] == pytest.approx(32.45)
    assert params["PL_C"] == 20


def test_parse_umi_los():
    from aegis.channel.presets import parse_conf

    params = parse_conf(DATA_DIR / "3GPP_38.901_UMi_LOS.conf")
    assert params["KF_mu"] == 9
    assert params["KF_sigma"] == 5
    assert params["AS_A_mu"] == pytest.approx(1.73)
    assert params["AS_A_omega"] == 1
    assert params["AS_A_gamma"] == pytest.approx(-0.08)
    assert params["AS_A_delta"] == pytest.approx(0.014)
    assert params["NumClusters"] == 12
    assert params["NumSubPaths"] == 20
    assert params["PerClusterAS_A"] == 17
    assert params["r_DS"] == 3


def test_parse_all_91_configs():
    from aegis.channel.presets import parse_conf

    conf_files = sorted(DATA_DIR.glob("*.conf"))
    assert len(conf_files) >= 91, f"Expected 91+ .conf files, found {len(conf_files)}"
    for conf in conf_files:
        params = parse_conf(conf)
        assert "NumClusters" in params, f"{conf.name}: missing NumClusters"
        assert params["NumClusters"] >= 1


def test_freq_scaling():
    import math

    from aegis.channel.presets import scale_param

    result = scale_param(mu=1.73, omega=1, gamma=-0.08, freq_ghz=28)
    expected = 1.73 + (-0.08) * math.log10(1 + 28)
    assert result == pytest.approx(expected, abs=0.001)


def test_load_preset():
    from aegis.channel.presets import load_preset

    preset = load_preset("3GPP_38.901_UMi_LOS", DATA_DIR)
    assert preset["name"] == "3GPP_38.901_UMi_LOS"
    assert "KF_mu" in preset["params"]


def test_list_presets():
    from aegis.channel.presets import list_presets

    names = list_presets(DATA_DIR)
    assert "Freespace" in names
    assert "3GPP_38.901_UMi_LOS" in names
    assert len(names) >= 91


def test_parse_decorrelation_distances():
    from aegis.channel.presets import parse_conf

    params = parse_conf(DATA_DIR / "3GPP_38.901_UMi_LOS.conf")
    lambda_keys = [
        "DS_lambda",
        "KF_lambda",
        "SF_lambda",
        "AS_D_lambda",
        "AS_A_lambda",
        "ES_D_lambda",
        "ES_A_lambda",
        "XPR_lambda",
    ]
    for key in lambda_keys:
        assert key in params, f"Missing key: {key}"
        assert isinstance(params[key], float), f"{key} should be float"
        assert params[key] > 0, f"{key} should be positive"


def test_parse_cross_correlations():
    from aegis.channel.presets import parse_conf

    params = parse_conf(DATA_DIR / "3GPP_38.901_UMi_LOS.conf")
    assert params["ds_kf"] == pytest.approx(-0.7)
    assert params["sf_kf"] == pytest.approx(0.5)
    assert params["asD_ds"] == pytest.approx(0.5)
    assert params["asA_ds"] == pytest.approx(0.8)


def test_parse_subpath_method():
    from aegis.channel.presets import parse_conf

    params = parse_conf(DATA_DIR / "3GPP_38.901_UMi_LOS.conf")
    assert params["SubpathMethod"] == "legacy"


def test_parse_esd_distance_params():
    from aegis.channel.presets import parse_conf

    params = parse_conf(DATA_DIR / "3GPP_38.901_UMi_LOS.conf")
    assert "ES_D_mu_min" in params
    assert "ES_D_mu_A" in params
