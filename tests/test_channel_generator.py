from pathlib import Path

import numpy as np
import pytest

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "channel_presets"

SUBPATH_OFFSETS = [
    0.0447,
    0.0447,
    0.1413,
    0.1413,
    0.2492,
    0.2492,
    0.3715,
    0.3715,
    0.5129,
    0.5129,
    0.6797,
    0.6797,
    0.8844,
    0.8844,
    1.1481,
    1.1481,
    1.5195,
    1.5195,
    2.1551,
    2.1551,
]


def test_generate_freespace_single_path():
    from aegis.channel.generator import generate_channel
    from aegis.channel.presets import load_preset

    preset = load_preset("Freespace", DATA_DIR)
    paths = generate_channel(
        preset["params"],
        freq_ghz=28,
        antenna_pos=np.array([5.0, 0.0, 2.0]),
        body_center=np.array([0.0, 0.0, 1.0]),
        power_dbm=30,
        seed=42,
    )
    assert paths.n_paths == 1
    assert paths.power.sum() > 0


def test_generate_umi_los_path_count():
    from aegis.channel.generator import generate_channel
    from aegis.channel.presets import load_preset

    preset = load_preset("3GPP_38.901_UMi_LOS", DATA_DIR)
    paths = generate_channel(
        preset["params"],
        freq_ghz=28,
        antenna_pos=np.array([5.0, 0.0, 2.0]),
        body_center=np.array([0.0, 0.0, 1.0]),
        power_dbm=30,
        seed=42,
    )
    # UMi LOS: 12 clusters, 1 LOS + 11 NLOS * 20 sub-paths = 221
    assert paths.n_paths == 1 + 11 * 20


def test_generate_nlos_all_clusters_have_subpaths():
    from aegis.channel.generator import generate_channel
    from aegis.channel.presets import load_preset

    preset = load_preset("3GPP_38.901_UMa_NLOS", DATA_DIR)
    paths = generate_channel(
        preset["params"],
        freq_ghz=28,
        antenna_pos=np.array([5.0, 0.0, 2.0]),
        body_center=np.array([0.0, 0.0, 1.0]),
        power_dbm=30,
        seed=42,
    )
    # UMa NLOS: KF_mu = -100 dB, all 21 clusters are NLOS: 21 * 20 = 420
    assert paths.n_paths == 21 * 20


def test_cluster_powers_normalize_to_one():
    """Cluster power fractions must sum to 1 before S_inc scaling."""
    from aegis.channel.generator import _generate_cluster_powers

    rng = np.random.default_rng(42)
    for _ in range(50):
        powers, delays = _generate_cluster_powers(
            n_clusters=12,
            r_ds=3,
            ds=1e-7,
            kf_db=9,
            lns_ksi=3,
            rng=rng,
        )
        assert powers.sum() == pytest.approx(1.0, abs=1e-10)
        assert np.all(powers >= 0)
        assert delays.shape == powers.shape
        assert delays[0] == 0.0


def test_power_positive_and_finite():
    from aegis.channel.generator import generate_channel
    from aegis.channel.presets import load_preset

    preset = load_preset("3GPP_38.901_UMi_LOS", DATA_DIR)
    paths = generate_channel(
        preset["params"],
        freq_ghz=28,
        antenna_pos=np.array([10.0, 0.0, 2.0]),
        body_center=np.array([0.0, 0.0, 1.0]),
        power_dbm=30,
        seed=42,
    )
    total_power = paths.power.sum()
    assert total_power > 0
    assert np.isfinite(total_power)
    assert np.all(paths.power >= 0)


def test_k_factor_statistical():
    """Over many seeds, mean LOS/NLOS power ratio should match K-factor."""
    from aegis.channel.generator import generate_channel
    from aegis.channel.presets import load_preset

    preset = load_preset("3GPP_38.901_UMi_LOS", DATA_DIR)
    ratios = []
    for seed in range(200):
        paths = generate_channel(
            preset["params"],
            freq_ghz=28,
            antenna_pos=np.array([10.0, 0.0, 2.0]),
            body_center=np.array([0.0, 0.0, 1.0]),
            power_dbm=30,
            seed=seed,
        )
        los_power = paths.power[0]
        nlos_power = paths.power[1:].sum()
        if nlos_power > 0:
            ratios.append(los_power / nlos_power)
    mean_ratio = np.mean(ratios)
    # Within 3 dB of expected (stochastic, so generous tolerance)
    assert abs(10 * np.log10(mean_ratio) - 9) < 3


def test_los_direction():
    from aegis.channel.generator import generate_channel
    from aegis.channel.presets import load_preset

    preset = load_preset("3GPP_38.901_UMi_LOS", DATA_DIR)
    ant = np.array([10.0, 0.0, 2.0])
    body = np.array([0.0, 0.0, 1.0])
    paths = generate_channel(
        preset["params"],
        freq_ghz=28,
        antenna_pos=ant,
        body_center=body,
        power_dbm=30,
        seed=42,
    )
    expected_dir = (body - ant) / np.linalg.norm(body - ant)
    cos_angle = np.dot(paths.k_hat[0], expected_dir)
    assert cos_angle > 0.99, f"LOS direction off: cos={cos_angle}"


def test_khats_are_unit_vectors():
    from aegis.channel.generator import generate_channel
    from aegis.channel.presets import load_preset

    preset = load_preset("3GPP_38.901_Indoor_LOS", DATA_DIR)
    paths = generate_channel(
        preset["params"],
        freq_ghz=28,
        antenna_pos=np.array([5.0, 0.0, 2.0]),
        body_center=np.array([0.0, 0.0, 1.0]),
        power_dbm=30,
        seed=42,
    )
    norms = np.linalg.norm(paths.k_hat, axis=1)
    np.testing.assert_allclose(norms, 1.0, atol=1e-10)


def test_reproducible_with_seed():
    from aegis.channel.generator import generate_channel
    from aegis.channel.presets import load_preset

    preset = load_preset("3GPP_38.901_UMi_LOS", DATA_DIR)
    kwargs = dict(
        freq_ghz=28,
        antenna_pos=np.array([5.0, 0.0, 2.0]),
        body_center=np.array([0.0, 0.0, 1.0]),
        power_dbm=30,
        seed=123,
    )
    p1 = generate_channel(preset["params"], **kwargs)
    p2 = generate_channel(preset["params"], **kwargs)
    np.testing.assert_array_equal(p1.k_hat, p2.k_hat)
    np.testing.assert_array_equal(p1.power, p2.power)


def test_spatial_consistency_nearby_positions():
    """Nearby body positions should produce similar channel powers."""
    from aegis.channel import generate_channel, load_preset

    preset = load_preset("3GPP_38.901_UMi_LOS", DATA_DIR)
    params = preset["params"]
    antenna = np.array([0.0, 0.0, 10.0])
    body_a = np.array([50.0, 0.0, 1.5])
    body_b = np.array([51.0, 0.0, 1.5])
    paths_a = generate_channel(params, 28.0, antenna, body_a, 40.0, seed=42)
    paths_b = generate_channel(params, 28.0, antenna, body_b, 40.0, seed=42)
    power_a = np.sum(paths_a.power)
    power_b = np.sum(paths_b.power)
    ratio_db = 10 * np.log10(power_a / power_b)
    assert abs(ratio_db) < 3.0, f"Power difference {ratio_db} dB too large for 1m move"


def test_sc_disabled_when_sc_lambda_zero():
    """Presets without SC_lambda should use i.i.d. path."""
    from aegis.channel import generate_channel, load_preset

    preset = load_preset("Freespace", DATA_DIR)
    params = preset["params"]
    antenna = np.array([0.0, 0.0, 10.0])
    body = np.array([50.0, 0.0, 1.5])
    paths = generate_channel(params, 28.0, antenna, body, 40.0, seed=42)
    assert len(paths.k_hat) >= 1


def test_sc_path_count_unchanged():
    """SC mode should produce same number of paths as non-SC."""
    from aegis.channel import generate_channel, load_preset

    preset = load_preset("3GPP_38.901_UMi_LOS", DATA_DIR)
    params = preset["params"]
    antenna = np.array([0.0, 0.0, 10.0])
    body = np.array([50.0, 0.0, 1.5])
    paths = generate_channel(params, 28.0, antenna, body, 40.0, seed=42)
    assert len(paths.k_hat) == 221  # 1 LOS + 11*20 NLOS


@pytest.mark.parametrize(
    ("override", "expected"),
    [
        ({"NumClusters": 0}, "NumClusters must be >= 1"),
        ({"NumSubPaths": 0}, "NumSubPaths must be >= 1"),
    ],
)
def test_rejects_zero_cluster_or_subpath_override(override, expected):
    """Zero clusters/sub-paths raises ValueError instead of IndexError on empty array."""
    from aegis.channel import generate_channel, load_preset

    preset = load_preset("3GPP_38.901_UMi_LOS", DATA_DIR)
    with pytest.raises(ValueError, match=expected):
        generate_channel(
            preset["params"],
            freq_ghz=28.0,
            antenna_pos=np.array([0.0, 0.0, 10.0]),
            body_center=np.array([50.0, 0.0, 1.5]),
            power_dbm=40.0,
            seed=42,
            overrides=override,
        )


def test_generate_coherent_channel_structure():
    import numpy as np

    from aegis.channel.generator import generate_channel, generate_coherent_channel
    from aegis.channel.presets import load_preset
    from aegis.constants import Z_0

    preset = load_preset("3GPP_38.901_UMi_LOS", DATA_DIR)
    kw = dict(
        freq_ghz=28,
        antenna_pos=np.array([20.0, 0.0, 10.0]),
        body_center=np.array([0.0, 0.0, 1.1]),
        power_dbm=30,
        seed=7,
    )
    incoh = generate_channel(preset["params"], **kw)
    coh = generate_coherent_channel(preset["params"], xpr_db=8.0, **kw)

    n = coh.k_hat.shape[0]
    assert n == incoh.n_paths
    assert n > 0
    # coherent: complex field, one per path, in 3D
    assert coh.psi.shape == (n, 3)
    assert np.iscomplexobj(coh.psi)
    assert np.any(np.abs(coh.psi.imag) > 0)
    # center-of-array contract: all element_index zero
    assert np.all(np.asarray(coh.element_index) == 0)
    # field is transverse to the propagation direction
    dot = np.einsum("ni,ni->n", coh.psi, coh.k_hat.astype(complex))
    assert np.all(np.abs(dot) < 1e-9 * (np.linalg.norm(coh.psi, axis=1) + 1e-30))
    # energy consistency: sum |psi|^2 == 2 Z0 * sum incident power density
    np.testing.assert_allclose(np.sum(np.abs(coh.psi) ** 2), 2.0 * Z_0 * incoh.power.sum(), rtol=1e-6)
