"""Tests for the LSFModel large-scale fading model."""

from __future__ import annotations

import numpy as np


def _umi_los_params():
    """Minimal UMi LOS params for testing."""
    return {
        "DS_mu": -7.14,
        "DS_sigma": 0.38,
        "DS_omega": 1,
        "DS_gamma": -0.24,
        "KF_mu": 9,
        "KF_sigma": 5,
        "SF_sigma": 4,
        "AS_D_mu": 1.21,
        "AS_D_sigma": 0.41,
        "AS_D_omega": 1,
        "AS_D_gamma": -0.05,
        "AS_A_mu": 1.73,
        "AS_A_sigma": 0.28,
        "AS_A_omega": 1,
        "AS_A_gamma": -0.08,
        "AS_A_delta": 0.014,
        "ES_D_mu": 0.83,
        "ES_D_sigma": 0.35,
        "ES_A_mu": 0.73,
        "ES_A_sigma": 0.34,
        "ES_A_omega": 1,
        "ES_A_gamma": -0.1,
        "ES_A_delta": -0.04,
        "XPR_mu": 9,
        "XPR_sigma": 3,
        "DS_lambda": 7,
        "KF_lambda": 15,
        "SF_lambda": 10,
        "AS_D_lambda": 8,
        "AS_A_lambda": 8,
        "ES_D_lambda": 12,
        "ES_A_lambda": 12,
        "XPR_lambda": 15,
        "ds_kf": -0.7,
        "ds_sf": -0.4,
        "asD_ds": 0.5,
        "asA_ds": 0.8,
        "esA_ds": 0.2,
        "sf_kf": 0.5,
        "asD_kf": -0.2,
        "asA_kf": -0.3,
        "asD_sf": -0.5,
        "asA_sf": -0.4,
        "asD_asA": 0.4,
        "esD_asD": 0.5,
        "esA_asD": 0.3,
    }


class TestLSFModelBasic:
    def test_returns_dict_with_all_lsps(self):
        from aegis.channel.lsf import LSFModel

        model = LSFModel(_umi_los_params(), freq_ghz=3.5)
        pos = np.array([[0.0, 0.0, 1.5]])
        result = model.evaluate(pos)

        expected_keys = {"DS", "KF_dB", "SF_dB", "ASD_deg", "ASA_deg", "ESD_deg", "ESA_deg", "XPR_dB"}
        assert set(result.keys()) == expected_keys
        for key, val in result.items():
            assert val.shape == (1,), f"{key} should have shape (1,)"

    def test_output_shape_grid(self):
        from aegis.channel.lsf import LSFModel

        model = LSFModel(_umi_los_params(), freq_ghz=3.5)
        rng = np.random.default_rng(0)
        pos = rng.uniform(-100, 100, (25, 3))
        result = model.evaluate(pos)

        for key, val in result.items():
            assert val.shape == (25,), f"{key} should have shape (25,)"

    def test_deterministic(self):
        from aegis.channel.lsf import LSFModel

        params = _umi_los_params()
        pos = np.array([[10.0, 20.0, 1.5], [5.0, -3.0, 1.5]])

        model1 = LSFModel(params, freq_ghz=3.5, seed=42)
        model2 = LSFModel(params, freq_ghz=3.5, seed=42)

        r1 = model1.evaluate(pos)
        r2 = model2.evaluate(pos)

        for key in r1:
            np.testing.assert_array_equal(r1[key], r2[key], err_msg=f"{key} not deterministic")

    def test_ds_is_positive(self):
        from aegis.channel.lsf import LSFModel

        model = LSFModel(_umi_los_params(), freq_ghz=3.5)
        rng = np.random.default_rng(1)
        pos = rng.uniform(-200, 200, (100, 3))
        result = model.evaluate(pos)

        assert np.all(result["DS"] > 0), "DS must be positive (log-normal)"

    def test_angular_spreads_positive(self):
        from aegis.channel.lsf import LSFModel

        model = LSFModel(_umi_los_params(), freq_ghz=3.5)
        rng = np.random.default_rng(2)
        pos = rng.uniform(-200, 200, (100, 3))
        result = model.evaluate(pos)

        for key in ("ASD_deg", "ASA_deg", "ESD_deg", "ESA_deg"):
            assert np.all(result[key] > 0), f"{key} must be positive (log-normal)"

    def test_values_finite(self):
        from aegis.channel.lsf import LSFModel

        model = LSFModel(_umi_los_params(), freq_ghz=3.5)
        rng = np.random.default_rng(3)
        pos = rng.uniform(-500, 500, (200, 3))
        result = model.evaluate(pos)

        for key, val in result.items():
            assert np.all(np.isfinite(val)), f"{key} contains non-finite values"


class TestLSFModelSpatialCorrelation:
    def test_nearby_positions_have_similar_ds(self):
        from aegis.channel.lsf import LSFModel

        model = LSFModel(_umi_los_params(), freq_ghz=3.5)
        rng = np.random.default_rng(4)

        # 50 anchor positions
        anchors = rng.uniform(-100, 100, (50, 3))
        anchors[:, 2] = 1.5

        # Nearby: 1 m offset
        nearby = anchors + np.array([1.0, 0.0, 0.0])

        # Far: 200 m offset
        far = anchors + np.array([200.0, 0.0, 0.0])

        log_ds_anchor = np.log10(model.evaluate(anchors)["DS"])
        log_ds_near = np.log10(model.evaluate(nearby)["DS"])
        log_ds_far = np.log10(model.evaluate(far)["DS"])

        mean_diff_near = np.mean(np.abs(log_ds_anchor - log_ds_near))
        mean_diff_far = np.mean(np.abs(log_ds_anchor - log_ds_far))

        assert mean_diff_near < mean_diff_far, (
            f"Nearby diff ({mean_diff_near:.4f}) should be smaller than far diff ({mean_diff_far:.4f})"
        )

    def test_ds_kf_negatively_correlated(self):
        from aegis.channel.lsf import LSFModel

        model = LSFModel(_umi_los_params(), freq_ghz=3.5)
        rng = np.random.default_rng(5)
        pos = rng.uniform(-500, 500, (500, 3))
        pos[:, 2] = 1.5

        result = model.evaluate(pos)
        log_ds = np.log10(result["DS"])
        kf_db = result["KF_dB"]

        corr = np.corrcoef(log_ds, kf_db)[0, 1]
        assert corr < -0.2, f"DS-KF correlation should be < -0.2, got {corr:.3f}"


class TestLSFModelHeatmap:
    def test_generate_map_returns_grid(self):
        from aegis.channel.lsf import LSFModel

        model = LSFModel(_umi_los_params(), freq_ghz=3.5)
        grid = model.generate_map(bounds=(-50, 50, -50, 50), resolution=10, height=1.5, lsp_name="SF_dB")

        assert grid.shape == (10, 10), f"Expected (10, 10), got {grid.shape}"
        assert np.all(np.isfinite(grid)), "Grid contains non-finite values"

    def test_generate_map_has_spatial_variation(self):
        from aegis.channel.lsf import LSFModel

        model = LSFModel(_umi_los_params(), freq_ghz=3.5)
        grid = model.generate_map(bounds=(-100, 100, -100, 100), resolution=128, height=1.5, lsp_name="SF_dB")

        assert grid.shape == (128, 128)
        assert grid.std() > 0, "LSP map has no spatial variation (all identical values)"


class TestGenerateLSPHeatmapE2E:
    def test_viewer_heatmap_returns_varied_data(self):
        from aegis.viewer.compute import generate_lsp_heatmap

        result = generate_lsp_heatmap(
            preset_name="3GPP_38.901_UMi_LOS",
            freq_ghz=3.5,
            antenna_pos=(0.0, 0.0, 10.0),
            lsp_name="SF_dB",
            bounds=(-100, 100, -100, 100),
            resolution=128,
            seed=42,
        )

        assert result["resolution"] == 128
        data = np.array(result["data"])
        assert data.shape == (128, 128)
        assert data.std() > 0, "Heatmap has no spatial variation"
        assert result["vmin"] < result["vmax"], "vmin must be less than vmax for colormap"
