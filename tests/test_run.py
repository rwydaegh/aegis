"""Smoke tests for the CLI batch runner."""

import json
import subprocess
import sys

import numpy as np
import pytest
import yaml


@pytest.mark.slow
def test_run_with_yaml_config(tmp_path):
    """Run aegis.run with a YAML config, check output files exist."""
    config = {
        "tissue": {"name": "Skin", "frequency_hz": 28e9},
        "body": {"name": "thelonious"},
        "antenna": {"positions": [[5.0, 0.0, 1.0]], "power_dbm": 30.0},
        "raytracer": {"backend": "synthetic"},
        "dosimetry": {"level": 2},
        "output_dir": str(tmp_path / "out"),
    }
    config_path = tmp_path / "config.yaml"
    with config_path.open("w") as f:
        yaml.dump(config, f)

    result = subprocess.run(
        [sys.executable, "-m", "aegis.run", "--config", str(config_path)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"

    # Find the output directory (timestamped)
    out_dir = tmp_path / "out"
    assert out_dir.exists()
    run_dirs = list(out_dir.iterdir())
    assert len(run_dirs) == 1

    run_dir = run_dirs[0]
    assert (run_dir / "config.yaml").exists()
    assert (run_dir / "result.npz").exists()
    assert (run_dir / "summary.json").exists()

    # Verify summary.json has expected keys
    with (run_dir / "summary.json").open() as f:
        summary = json.load(f)
    assert "peak_sab" in summary
    assert "p_abs" in summary
    assert "compliant" in summary
    assert "level" in summary

    # Verify result.npz has sab array
    data = np.load(run_dir / "result.npz")
    assert "sab" in data
    assert data["sab"].ndim == 1


def test_synthetic_paths_generation():
    """Test that synthetic paths are generated correctly from antenna positions."""
    from aegis.run import _synthetic_paths

    tx_pos = np.array([[10.0, 0.0, 0.0]])
    power_w = 1.0
    paths = _synthetic_paths(tx_pos, power_w)
    assert paths.n_paths == 1
    # k_hat should point from TX toward origin
    np.testing.assert_allclose(paths.k_hat[0], [-1.0, 0.0, 0.0], atol=1e-10)
    # Power density at 10m from 1W isotropic: P/(4*pi*d^2)
    expected_power = 1.0 / (4 * np.pi * 100)
    np.testing.assert_allclose(paths.power[0], expected_power, rtol=1e-10)


def test_synthetic_paths_zero_distance():
    """TX at origin produces no paths (distance < 1e-10 threshold)."""
    from aegis.run import _synthetic_paths

    tx_pos = np.array([[0.0, 0.0, 0.0]])
    power_w = 1.0
    paths = _synthetic_paths(tx_pos, power_w)
    assert paths.n_paths == 0


def test_synthetic_paths_multiple_elements():
    """Multiple TX positions each produce one path."""
    from aegis.run import _synthetic_paths

    tx_pos = np.array([[10.0, 0.0, 0.0], [0.0, 5.0, 0.0], [0.0, 0.0, 2.0]])
    power_w = 1.0
    paths = _synthetic_paths(tx_pos, power_w)
    assert paths.n_paths == 3

    # Each k_hat should point toward origin from the TX position
    np.testing.assert_allclose(paths.k_hat[0], [-1.0, 0.0, 0.0], atol=1e-10)
    np.testing.assert_allclose(paths.k_hat[1], [0.0, -1.0, 0.0], atol=1e-10)
    np.testing.assert_allclose(paths.k_hat[2], [0.0, 0.0, -1.0], atol=1e-10)

    # Power densities scale as 1/(4*pi*d^2)
    np.testing.assert_allclose(paths.power[0], 1.0 / (4 * np.pi * 100), rtol=1e-10)
    np.testing.assert_allclose(paths.power[1], 1.0 / (4 * np.pi * 25), rtol=1e-10)
    np.testing.assert_allclose(paths.power[2], 1.0 / (4 * np.pi * 4), rtol=1e-10)
