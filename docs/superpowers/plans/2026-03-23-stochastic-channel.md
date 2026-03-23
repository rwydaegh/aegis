# Stochastic channel model implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a 3GPP TR 38.901-based stochastic channel model that generates cluster-based multipath from standardized scenario presets, replacing the crude N-plane-wave synthetic path generator.

**Architecture:** New `src/aegis/channel/` module with .conf parser, cluster-based generator, and path loss models. Frontend gets a new "Stochastic" accordion panel with scenario dropdown and editable parameters. Mutual exclusion with RT via a `pathSource` enum in the scene store.

**Tech Stack:** Python 3.12 (NumPy), React/TypeScript (Zustand, Vite), Flask REST API

**Spec:** `docs/superpowers/specs/2026-03-23-stochastic-channel-design.md`

---

## Task 1: Preset parser

Parse QuaDRiGa `.conf` files into Python dicts with frequency-dependent parameter scaling.

**Files:**
- Create: `src/aegis/channel/__init__.py`
- Create: `src/aegis/channel/presets.py`
- Test: `tests/test_channel_presets.py`

- [ ] **Step 1: Write preset parser tests**

```python
# tests/test_channel_presets.py
import pytest
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "channel_presets"


def test_parse_freespace():
    from aegis.channel.presets import parse_conf

    params = parse_conf(DATA_DIR / "Freespace.conf")
    assert params["NumClusters"] == 1
    assert params["SF_sigma"] == 0
    assert params["KF_mu"] == 0
    assert params["PL_model"] == "logdist"
    assert params["PL_A"] == 20
    assert params["PL_B"] == 32.45
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
    from aegis.channel.presets import scale_param

    # AS_A_mu for UMi LOS: 1.73 + (-0.08) * log10(1 + 28) = 1.73 - 0.117 = 1.613
    import math
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `py -3.12 -m pytest tests/test_channel_presets.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'aegis.channel')

- [ ] **Step 3: Implement preset parser**

Create `src/aegis/channel/__init__.py`:
```python
"""3GPP TR 38.901 stochastic channel model for dosimetry."""
```

Create `src/aegis/channel/presets.py`:
```python
"""Parse QuaDRiGa .conf files and manage channel presets."""

from __future__ import annotations

import math
import re
from pathlib import Path

# Parameters we extract from .conf files. All others are silently ignored.
# Values are: (python_type, default_if_missing_or_None)
KNOWN_PARAMS: dict[str, type] = {
    # Large-scale distributions
    "DS_mu": float, "DS_sigma": float, "DS_omega": float,
    "DS_gamma": float, "DS_delta": float,
    "KF_mu": float, "KF_sigma": float,
    "SF_sigma": float,
    "AS_D_mu": float, "AS_D_sigma": float, "AS_D_omega": float,
    "AS_D_gamma": float, "AS_D_delta": float,
    "AS_A_mu": float, "AS_A_sigma": float, "AS_A_omega": float,
    "AS_A_gamma": float, "AS_A_delta": float,
    "ES_D_mu": float, "ES_D_sigma": float, "ES_D_omega": float,
    "ES_D_gamma": float, "ES_D_delta": float,
    "ES_A_mu": float, "ES_A_sigma": float, "ES_A_omega": float,
    "ES_A_gamma": float, "ES_A_delta": float,
    "XPR_mu": float, "XPR_sigma": float,
    # Model parameters
    "NumClusters": int, "NumSubPaths": int,
    "r_DS": float, "LNS_ksi": float,
    "PerClusterDS": float, "PerClusterAS_D": float,
    "PerClusterAS_A": float, "PerClusterES_D": float,
    "PerClusterES_A": float,
    # Decorrelation (stored but not used for dosimetry)
    "SC_lambda": float,
    # Path loss
    "PL_model": str,
    "PL_A": float, "PL_B": float, "PL_C": float,
    "PL_A1": float, "PL_A2": float, "PL_E": float, "PL_hE": float,
    "PL_D": float,
    "PL_An": float, "PL_Bn": float, "PL_Cn": float,
    "PL_E3n": float,
}

_LINE_RE = re.compile(r"^(\w+)\s*=\s*(.+?)(?:\s*%.*)?$")


def parse_conf(path: Path | str) -> dict:
    """Parse a QuaDRiGa .conf file into a flat dict of typed values."""
    path = Path(path)
    params: dict = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("%"):
            continue
        m = _LINE_RE.match(line)
        if not m:
            continue
        key, raw_val = m.group(1), m.group(2).strip()
        if key in KNOWN_PARAMS:
            typ = KNOWN_PARAMS[key]
            try:
                params[key] = typ(raw_val)
            except (ValueError, TypeError):
                pass
    return params


def scale_param(
    mu: float,
    omega: float = 1.0,
    gamma: float = 0.0,
    freq_ghz: float = 28.0,
) -> float:
    """Apply frequency-dependent scaling: mu + gamma * log10(omega + freq)."""
    return mu + gamma * math.log10(omega + freq_ghz)


def load_preset(name: str, preset_dir: Path | str) -> dict:
    """Load a named preset from the preset directory."""
    preset_dir = Path(preset_dir)
    path = preset_dir / f"{name}.conf"
    if not path.exists():
        raise FileNotFoundError(f"Preset not found: {path}")
    params = parse_conf(path)
    return {"name": name, "params": params}


def list_presets(preset_dir: Path | str) -> list[str]:
    """List available preset names (stem of .conf files)."""
    preset_dir = Path(preset_dir)
    return sorted(p.stem for p in preset_dir.glob("*.conf"))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `py -3.12 -m pytest tests/test_channel_presets.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Lint and commit**

```bash
py -3.12 -m ruff check src/aegis/channel/ tests/test_channel_presets.py
py -3.12 -m ruff format src/aegis/channel/ tests/test_channel_presets.py
git add src/aegis/channel/__init__.py src/aegis/channel/presets.py tests/test_channel_presets.py
git commit -m "Add QuaDRiGa .conf preset parser for stochastic channel model"
```

---

## Task 2: Path loss models

Implement logdist, dual_slope, and nlos path loss formulas from 3GPP TR 38.901.

**Files:**
- Create: `src/aegis/channel/path_loss.py`
- Test: `tests/test_channel_path_loss.py`

- [ ] **Step 1: Write path loss tests**

```python
# tests/test_channel_path_loss.py
import pytest
import math


def test_logdist_freespace():
    """Freespace: PL = 20*log10(d) + 32.45 + 20*log10(f)."""
    from aegis.channel.path_loss import compute_path_loss

    params = {"PL_model": "logdist", "PL_A": 20, "PL_B": 32.45, "PL_C": 20}
    # d=100m, f=28GHz: PL = 20*2 + 32.45 + 20*log10(28) = 40 + 32.45 + 28.94 = 101.39
    pl = compute_path_loss(params, distance_m=100, freq_ghz=28)
    expected = 20 * math.log10(100) + 32.45 + 20 * math.log10(28)
    assert pl == pytest.approx(expected, abs=0.01)


def test_dual_slope():
    """UMi LOS dual slope before breakpoint."""
    from aegis.channel.path_loss import compute_path_loss

    params = {
        "PL_model": "dual_slope",
        "PL_A1": 21, "PL_A2": 40, "PL_B": 32.4, "PL_C": 20,
        "PL_E": 13.34, "PL_hE": 1,
    }
    # Before breakpoint at d=50m, f=28GHz, hBS=10, hMS=1.5
    pl = compute_path_loss(params, distance_m=50, freq_ghz=28, h_bs=10, h_ms=1.5)
    d3d = math.sqrt(50**2 + (10 - 1.5)**2)
    expected = 21 * math.log10(d3d) + 32.4 + 20 * math.log10(28)
    assert pl == pytest.approx(expected, abs=0.5)


def test_unsupported_model_fallback():
    """Unsupported PL model falls back to free-space."""
    from aegis.channel.path_loss import compute_path_loss

    params = {"PL_model": "satellite"}
    pl = compute_path_loss(params, distance_m=100, freq_ghz=28)
    # FSPL = 20*log10(d) + 20*log10(f) + 32.45
    expected = 20 * math.log10(100) + 20 * math.log10(28) + 32.45
    assert pl == pytest.approx(expected, abs=0.1)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `py -3.12 -m pytest tests/test_channel_path_loss.py -v`

- [ ] **Step 3: Implement path loss models**

Create `src/aegis/channel/path_loss.py`:
```python
"""3GPP TR 38.901 path loss models."""

from __future__ import annotations

import logging
import math

log = logging.getLogger(__name__)


def compute_path_loss(
    params: dict,
    distance_m: float,
    freq_ghz: float,
    h_bs: float = 10.0,
    h_ms: float = 1.5,
) -> float:
    """Compute path loss in dB for the given model parameters.

    Supports: logdist, dual_slope, nlos. Unknown models fall back to FSPL.
    """
    model = params.get("PL_model", "logdist")
    d3d = max(distance_m, 1.0)

    if model == "logdist":
        return _logdist(params, d3d, freq_ghz)
    elif model == "dual_slope":
        return _dual_slope(params, d3d, freq_ghz, h_bs, h_ms)
    elif model == "nlos":
        return _nlos(params, d3d, freq_ghz, h_bs, h_ms)
    else:
        log.warning("Unsupported PL model %r, using free-space", model)
        return _fspl(d3d, freq_ghz)


def _fspl(d3d: float, freq_ghz: float) -> float:
    return 20 * math.log10(d3d) + 20 * math.log10(freq_ghz) + 32.45


def _logdist(params: dict, d3d: float, freq_ghz: float) -> float:
    A = params.get("PL_A", 20)
    B = params.get("PL_B", 32.45)
    C = params.get("PL_C", 20)
    return A * math.log10(d3d) + B + C * math.log10(freq_ghz)


def _dual_slope(
    params: dict, d3d: float, freq_ghz: float, h_bs: float, h_ms: float,
) -> float:
    A1 = params.get("PL_A1", 21)
    A2 = params.get("PL_A2", 40)
    B = params.get("PL_B", 32.4)
    C = params.get("PL_C", 20)
    E = params.get("PL_E", 13.34)
    hE = params.get("PL_hE", 1)
    D = params.get("PL_D", 0)

    d_bp = E * (h_bs - hE) * (h_ms - hE) * freq_ghz
    d_bp = max(d_bp, 1.0)

    pl1 = A1 * math.log10(d3d) + B + C * math.log10(freq_ghz) + D * d3d
    if d3d <= d_bp:
        return pl1
    pl1_bp = A1 * math.log10(d_bp) + B + C * math.log10(freq_ghz) + D * d_bp
    return pl1_bp + A2 * math.log10(d3d / d_bp)


def _nlos(
    params: dict, d3d: float, freq_ghz: float, h_bs: float, h_ms: float,
) -> float:
    # LOS component (dual slope)
    pl_los = _dual_slope(params, d3d, freq_ghz, h_bs, h_ms)
    # NLOS component
    An = params.get("PL_An", 39.08)
    Bn = params.get("PL_Bn", 14.44)
    Cn = params.get("PL_Cn", 20)
    E3n = params.get("PL_E3n", 0)
    pl_nlos = An * math.log10(d3d) + Bn + Cn * math.log10(freq_ghz) + E3n * h_ms
    return max(pl_los, pl_nlos)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `py -3.12 -m pytest tests/test_channel_path_loss.py -v`

- [ ] **Step 5: Lint and commit**

```bash
py -3.12 -m ruff check src/aegis/channel/path_loss.py tests/test_channel_path_loss.py
py -3.12 -m ruff format src/aegis/channel/path_loss.py tests/test_channel_path_loss.py
git add src/aegis/channel/path_loss.py tests/test_channel_path_loss.py
git commit -m "Add 3GPP path loss models (logdist, dual_slope, nlos)"
```

---

## Task 3: Channel generator

Core algorithm: cluster powers, angles, sub-paths, LOS rotation, PropagationPaths output.

**Files:**
- Create: `src/aegis/channel/generator.py`
- Test: `tests/test_channel_generator.py`

- [ ] **Step 1: Write generator tests**

```python
# tests/test_channel_generator.py
import numpy as np
import pytest
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "channel_presets"

# 3GPP sub-path offset table (Table 26, QuaDRiGa docs)
SUBPATH_OFFSETS = [
    0.0447, 0.0447, 0.1413, 0.1413, 0.2492, 0.2492, 0.3715, 0.3715,
    0.5129, 0.5129, 0.6797, 0.6797, 0.8844, 0.8844, 1.1481, 1.1481,
    1.5195, 1.5195, 2.1551, 2.1551,
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
    # Freespace has 1 cluster, should produce 1 path
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
        powers = _generate_cluster_powers(
            n_clusters=12, r_ds=3, ds=1e-7, kf_db=9, lns_ksi=3, rng=rng,
        )
        assert powers.sum() == pytest.approx(1.0, abs=1e-10)
        assert np.all(powers >= 0)


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
    k_linear = 10 ** (9 / 10)  # KF_mu = 9 dB
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
        preset["params"], freq_ghz=28,
        antenna_pos=ant, body_center=body, power_dbm=30, seed=42,
    )
    # First path (LOS) should point from antenna toward body
    expected_dir = (body - ant) / np.linalg.norm(body - ant)
    cos_angle = np.dot(paths.k_hat[0], expected_dir)
    assert cos_angle > 0.99, f"LOS direction off: cos={cos_angle}"


def test_khats_are_unit_vectors():
    from aegis.channel.generator import generate_channel
    from aegis.channel.presets import load_preset

    preset = load_preset("3GPP_38.901_Indoor_LOS", DATA_DIR)
    paths = generate_channel(
        preset["params"], freq_ghz=28,
        antenna_pos=np.array([5.0, 0.0, 2.0]),
        body_center=np.array([0.0, 0.0, 1.0]),
        power_dbm=30, seed=42,
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
        power_dbm=30, seed=123,
    )
    p1 = generate_channel(preset["params"], **kwargs)
    p2 = generate_channel(preset["params"], **kwargs)
    np.testing.assert_array_equal(p1.k_hat, p2.k_hat)
    np.testing.assert_array_equal(p1.power, p2.power)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `py -3.12 -m pytest tests/test_channel_generator.py -v`

- [ ] **Step 3: Implement channel generator**

Create `src/aegis/channel/generator.py`. This is the largest file (~300 lines). The implementation follows the spec algorithm steps 2-7 exactly. Key functions:

- `generate_channel(params, freq_ghz, antenna_pos, body_center, power_dbm, seed, overrides=None) -> PropagationPaths`
- `_draw_large_scale(params, freq_ghz, rng) -> dict` (K, SF, ASA, ESA, DS)
- `_generate_cluster_powers(n_clusters, r_ds, ds, kf_db, lns_ksi, rng) -> ndarray`
- `_generate_cluster_angles(n_clusters, powers, asa_deg, esa_deg, rng) -> (az, el)`
- `_rotate_to_los(az, el, los_az, los_el) -> (az, el)`
- `_expand_subpaths(az, el, powers, n_subpaths, c_asa, c_esa, is_los) -> (az, el, powers)`
- `_angles_to_khats(az, el) -> ndarray` (spherical to Cartesian, negate for propagation dir)

```python
"""3GPP TR 38.901 cluster-based channel generator (dosimetry spatial subset)."""

from __future__ import annotations

import math

import numpy as np

from aegis.channel.path_loss import compute_path_loss
from aegis.channel.presets import scale_param
from aegis.paths import PropagationPaths

# 3GPP sub-path offset angles (Table 26 in QuaDRiGa v2.8.1 docs)
# 10 pairs of +/- offsets for 20 sub-paths total
_SUBPATH_OFFSETS_DEG = np.array([
    -0.0447, 0.0447, -0.1413, 0.1413, -0.2492, 0.2492,
    -0.3715, 0.3715, -0.5129, 0.5129, -0.6797, 0.6797,
    -0.8844, 0.8844, -1.1481, 1.1481, -1.5195, 1.5195,
    -2.1551, 2.1551,
])


def generate_channel(
    params: dict,
    freq_ghz: float,
    antenna_pos: np.ndarray,
    body_center: np.ndarray,
    power_dbm: float,
    seed: int = 42,
    overrides: dict | None = None,
) -> PropagationPaths:
    """Generate stochastic multipath from a 3GPP/QuaDRiGa preset.

    Returns PropagationPaths suitable for incoherent dosimetry (levels 0-6).
    """
    rng = np.random.default_rng(seed)
    ov = overrides or {}

    # Merge overrides into params
    p = {**params, **ov}

    n_clusters = int(p.get("NumClusters", 12))
    n_subpaths = int(p.get("NumSubPaths", 20))

    # Step 1: large-scale parameters
    lsp = _draw_large_scale(p, freq_ghz, rng, ov)

    # Step 2: cluster delays and powers
    powers = _generate_cluster_powers(
        n_clusters, p.get("r_DS", 2.5), lsp["DS"],
        lsp["KF_dB"], p.get("LNS_ksi", 3), rng,
    )

    # Step 3: cluster arrival angles
    az, el = _generate_cluster_angles(
        n_clusters, powers, lsp["ASA_deg"], lsp["ESA_deg"], rng,
    )

    # Step 4: LOS rotation
    direction = body_center - antenna_pos
    dist = np.linalg.norm(direction)
    if dist < 1e-6:
        dist = 1.0
        direction = np.array([1.0, 0.0, 0.0])
    los_az = math.atan2(direction[1], direction[0])
    los_el = math.atan2(direction[2], math.sqrt(direction[0]**2 + direction[1]**2))
    az, el = _rotate_to_los(az, el, los_az, los_el)

    # Step 5: sub-paths
    is_los_scenario = lsp["KF_dB"] > -50  # NLOS presets have KF = -100
    az, el, powers = _expand_subpaths(
        az, el, powers, n_subpaths,
        p.get("PerClusterAS_A", 10), p.get("PerClusterES_A", 7),
        is_los_scenario,
    )

    # Step 6: convert to k_hat and power
    k_hats = _angles_to_khats(az, el)

    # Compute S_inc with path loss and shadow fading
    tx_w = 10 ** ((power_dbm - 30) / 10)
    pl_db = compute_path_loss(p, dist, freq_ghz)
    sf_db = lsp["SF_dB"]
    s_inc = tx_w / (4 * math.pi * dist**2) * 10 ** (sf_db / 10)

    path_powers = powers * s_inc

    return PropagationPaths.from_powers(k_hat=k_hats, power=path_powers)


def _draw_large_scale(
    params: dict, freq_ghz: float, rng: np.random.Generator, overrides: dict,
) -> dict:
    """Draw large-scale fading parameters with frequency scaling."""

    def _scaled_mu(prefix: str) -> float:
        return scale_param(
            mu=params.get(f"{prefix}_mu", 0),
            omega=params.get(f"{prefix}_omega", 1),
            gamma=params.get(f"{prefix}_gamma", 0),
            freq_ghz=freq_ghz,
        )

    def _scaled_sigma(prefix: str) -> float:
        sigma_0 = params.get(f"{prefix}_sigma", 0)
        delta = params.get(f"{prefix}_delta", 0)
        omega = params.get(f"{prefix}_omega", 1)
        return sigma_0 + delta * math.log10(omega + freq_ghz)

    def _draw(prefix: str, is_log10: bool = False, unit: str = "linear") -> float:
        mu = _scaled_mu(prefix)
        sigma = _scaled_sigma(prefix) if f"{prefix}_mu" not in overrides else 0
        val = mu + sigma * rng.standard_normal()
        if is_log10:
            return 10 ** val
        return val

    kf_mu = params.get("KF_mu", 0)
    kf_sigma = params.get("KF_sigma", 0) if "KF_mu" not in overrides else 0
    kf_db = kf_mu + kf_sigma * rng.standard_normal()

    sf_sigma = params.get("SF_sigma", 0)
    sf_db = sf_sigma * rng.standard_normal()

    asa_deg = _draw("AS_A", is_log10=True)
    esa_deg = _draw("ES_A", is_log10=True)
    ds = _draw("DS", is_log10=True)  # in seconds, for power generation

    return {
        "KF_dB": kf_db,
        "SF_dB": sf_db,
        "ASA_deg": max(asa_deg, 0.1),
        "ESA_deg": max(esa_deg, 0.1),
        "DS": max(ds, 1e-12),
    }


def _generate_cluster_powers(
    n_clusters: int,
    r_ds: float,
    ds: float,
    kf_db: float,
    lns_ksi: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Generate normalized cluster powers using exponential PDP + K-factor."""
    # Synthetic delays (eq 51)
    delays = -np.log(rng.uniform(1e-12, 1, size=n_clusters))
    delays[0] = 0  # LOS delay
    delays = np.sort(delays)

    # Scale delays to match DS
    if r_ds > 1:
        delays = delays * ds * r_ds / max(delays.max(), 1e-12)

    # Powers from exponential PDP (eq 57, delay term only)
    if r_ds > 1 and ds > 0:
        powers = np.exp(-delays * (r_ds - 1) / (r_ds * ds))
    else:
        powers = np.ones(n_clusters)

    # Per-cluster shadowing
    if lns_ksi > 0:
        shadow = 10 ** (-rng.normal(0, lns_ksi, size=n_clusters) / 10)
        powers *= shadow

    # Apply K-factor (eq 61)
    k_linear = 10 ** (kf_db / 10)
    if n_clusters > 1 and k_linear > 1e-10:
        nlos_sum = powers[1:].sum()
        if nlos_sum > 0:
            powers[0] = k_linear * nlos_sum
    elif k_linear <= 1e-10:
        # Pure NLOS: LOS cluster gets same treatment as others
        pass

    # Normalize (eq 62)
    total = powers.sum()
    if total > 0:
        powers /= total

    return powers


def _generate_cluster_angles(
    n_clusters: int,
    powers: np.ndarray,
    asa_deg: float,
    esa_deg: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate cluster arrival angles scaled to target ASA/ESA."""
    # Initial uniform angles (eq 54)
    az_init = rng.uniform(-math.pi / 2, math.pi / 2, size=n_clusters)
    el_init = rng.uniform(-math.pi / 2, math.pi / 2, size=n_clusters)
    az_init[0] = 0  # LOS
    el_init[0] = 0

    az = _scale_angles(az_init, powers, math.radians(asa_deg), max_scale=3.0)
    el = _scale_angles(el_init, powers, math.radians(esa_deg), max_scale=1.5)

    return az, el


def _scale_angles(
    angles: np.ndarray,
    powers: np.ndarray,
    target_as_rad: float,
    max_scale: float,
) -> np.ndarray:
    """Scale initial angles to match target angular spread (eqs 66-69)."""
    # Power-weighted mean offset (eq 66)
    delta = np.angle(np.sum(np.exp(1j * angles) * powers))
    # Shift (eq 67)
    shifted = np.angle(np.exp(1j * (angles - delta)))
    # Compute achieved AS (eq 68)
    p_total = powers.sum()
    if p_total < 1e-30:
        return angles
    mean_sq = np.sum(powers * shifted**2) / p_total
    mean_val = np.sum(powers * shifted) / p_total
    achieved_as = math.sqrt(max(mean_sq - mean_val**2, 1e-30))
    # Scale (eq 69)
    s = target_as_rad / max(achieved_as, 1e-10)
    s = min(s, max_scale)
    return np.angle(np.exp(1j * angles * s))


def _rotate_to_los(
    az: np.ndarray, el: np.ndarray, los_az: float, los_el: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Rotate cluster angles so LOS cluster points toward the body (eqs 70-78)."""
    # Convert to Cartesian
    cos_el = np.cos(el)
    x = cos_el * np.cos(az)
    y = cos_el * np.sin(az)
    z = np.sin(el)
    vecs = np.column_stack([x, y, z])

    # Build rotation matrix from LOS angles (eq 76)
    cp, sp = math.cos(los_az), math.sin(los_az)
    ct, st = math.cos(los_el), math.sin(los_el)
    R = np.array([
        [ct * cp, -sp, -st * cp],
        [ct * sp,  cp, -st * sp],
        [st,        0,  ct],
    ])

    rotated = (R @ vecs.T).T

    # Back to spherical (eqs 77-78)
    az_out = np.arctan2(rotated[:, 1], rotated[:, 0])
    el_out = np.arctan2(rotated[:, 2], np.sqrt(rotated[:, 0]**2 + rotated[:, 1]**2))

    return az_out, el_out


def _expand_subpaths(
    az: np.ndarray,
    el: np.ndarray,
    powers: np.ndarray,
    n_subpaths: int,
    c_asa: float,
    c_esa: float,
    is_los: bool,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Expand NLOS clusters into sub-paths using fixed offset table."""
    offsets_rad = np.radians(_SUBPATH_OFFSETS_DEG[:n_subpaths])

    all_az, all_el, all_pow = [], [], []

    for i in range(len(az)):
        if is_los and i == 0:
            # LOS: single specular path
            all_az.append(az[i])
            all_el.append(el[i])
            all_pow.append(powers[i])
        else:
            # NLOS cluster: expand into sub-paths
            sub_az = az[i] + c_asa * offsets_rad
            sub_el = el[i] + c_esa * offsets_rad
            sub_pow = np.full(n_subpaths, powers[i] / n_subpaths)
            all_az.extend(sub_az)
            all_el.extend(sub_el)
            all_pow.extend(sub_pow)

    return np.array(all_az), np.array(all_el), np.array(all_pow)


def _angles_to_khats(az: np.ndarray, el: np.ndarray) -> np.ndarray:
    """Convert spherical arrival angles to unit propagation direction vectors."""
    cos_el = np.cos(el)
    # Arrival direction -> negate for propagation direction (toward body)
    k_hat = np.column_stack([
        cos_el * np.cos(az),
        cos_el * np.sin(az),
        np.sin(el),
    ])
    # Negate: arrival direction is FROM scatterer, we want direction OF propagation
    # Actually the rotation already points cluster 0 toward the body,
    # so k_hat is already the propagation direction. No negation needed.
    norms = np.linalg.norm(k_hat, axis=1, keepdims=True)
    return k_hat / np.where(norms > 0, norms, 1.0)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `py -3.12 -m pytest tests/test_channel_generator.py -v`

- [ ] **Step 5: Lint and commit**

```bash
py -3.12 -m ruff check src/aegis/channel/generator.py tests/test_channel_generator.py
py -3.12 -m ruff format src/aegis/channel/generator.py tests/test_channel_generator.py
git add src/aegis/channel/generator.py tests/test_channel_generator.py
git commit -m "Add 3GPP cluster-based channel generator for dosimetry"
```

---

## Task 4: Public API and backend integration

Wire the channel module into the viewer compute pipeline.

**Files:**
- Modify: `src/aegis/channel/__init__.py`
- Modify: `src/aegis/viewer/config.py:204-208` (add stochastic config)
- Modify: `src/aegis/viewer/compute.py:137-183` (add stochastic branch)
- Modify: `src/aegis/viewer/routes/compute.py:140-220` (accept stochastic params, add preset endpoint)

- [ ] **Step 1: Update channel __init__.py with public API**

```python
"""3GPP TR 38.901 stochastic channel model for dosimetry."""

from aegis.channel.generator import generate_channel
from aegis.channel.presets import list_presets, load_preset, parse_conf

__all__ = ["generate_channel", "list_presets", "load_preset", "parse_conf"]
```

- [ ] **Step 2: Add stochastic config to viewer config.py**

In `src/aegis/viewer/config.py`, add to the `DEFAULTS["dosimetry"]` dict (after `synthetic_paths` block around line 208):

```python
        "stochastic": {
            "preset_dir": "data/channel_presets",
            "default_preset": "3GPP_38.901_UMi_LOS",
            "default_seed": 42,
            "featured_presets": [
                "Freespace",
                "3GPP_38.901_UMi_LOS",
                "3GPP_38.901_UMi_NLOS",
                "3GPP_38.901_UMa_LOS",
                "3GPP_38.901_UMa_NLOS",
                "3GPP_38.901_Indoor_LOS",
                "3GPP_38.901_Indoor_NLOS",
                "3GPP_38.901_InF_LOS",
                "3GPP_38.901_RMa_LOS",
                "3GPP_38.901_RMa_NLOS",
            ],
        },
```

- [ ] **Step 3: Add stochastic branch to compute.py**

In `src/aegis/viewer/compute.py`:

1. Add `stochastic: dict | None = None` parameter to the `compute_dosimetry` function signature (after `config`).
2. Add a branch before the existing `n_paths` code (around line 162):

```python
    # --- after tx_power_w and S_inc computation (line 160) ---

    if stochastic:
        from aegis.channel import generate_channel, load_preset
        preset_dir = Path(cfg.get("dosimetry", {}).get("stochastic", {}).get(
            "preset_dir", "data/channel_presets"))
        # Resolve relative to package root
        if not preset_dir.is_absolute():
            preset_dir = Path(__file__).resolve().parents[2] / preset_dir
        preset = load_preset(stochastic["preset"], preset_dir)
        paths = generate_channel(
            preset["params"],
            freq_ghz=stochastic.get("freq_ghz", 28),
            antenna_pos=antenna_pos,
            body_center=body_center,
            power_dbm=power_dbm,
            seed=stochastic.get("seed", 42),
            overrides=stochastic.get("overrides"),
        )
    elif n_paths == 1:
        # existing single plane wave code...
```

- [ ] **Step 4: Add stochastic validation and preset endpoint to routes/compute.py**

Add to the `/api/compute` route (after n_paths validation, around line 191), and update the `compute_dosimetry(...)` call at line 207 to pass `stochastic=stochastic`:

```python
        # Stochastic channel params (optional, overrides n_paths when present)
        stochastic = None
        if params.get("stochastic"):
            stoch_cfg = cfg["dosimetry"].get("stochastic", {})
            stochastic = {
                "preset": params.get("stochastic_preset", stoch_cfg.get("default_preset", "3GPP_38.901_UMi_LOS")),
                "seed": int(params.get("stochastic_seed", stoch_cfg.get("default_seed", 42))),
                "overrides": params.get("stochastic_overrides", {}),
                "freq_ghz": float(params.get("freq_ghz", 28)),
            }
```

Add new endpoint:

```python
@bp.route("/api/channel-presets", methods=["GET"])
def channel_presets():
    from aegis.channel import list_presets, load_preset
    stoch_cfg = cfg["dosimetry"].get("stochastic", {})
    preset_dir = Path(stoch_cfg.get("preset_dir", "data/channel_presets"))
    if not preset_dir.is_absolute():
        preset_dir = Path(__file__).resolve().parents[3] / preset_dir
    featured = stoch_cfg.get("featured_presets", [])
    all_names = list_presets(preset_dir)
    presets = []
    for name in all_names:
        try:
            p = load_preset(name, preset_dir)
            presets.append({
                "name": name,
                "featured": name in featured,
                "params": p["params"],
            })
        except Exception:
            continue
    return jsonify(presets)
```

- [ ] **Step 5: Test the integration manually**

Run: `py -3.12 -m pytest tests/ -m "not slow" -x`
Expected: All existing tests still pass, plus new channel tests

- [ ] **Step 6: Lint and commit**

```bash
py -3.12 -m ruff check src/aegis/channel/ src/aegis/viewer/
py -3.12 -m ruff format src/aegis/channel/ src/aegis/viewer/
git add src/aegis/channel/__init__.py src/aegis/viewer/config.py src/aegis/viewer/compute.py src/aegis/viewer/routes/compute.py
git commit -m "Wire stochastic channel into viewer compute pipeline"
```

---

## Task 5: Frontend store and API client changes

Add pathSource enum, stochastic state, and update API client.

**Files:**
- Modify: `aegis-web/src/stores/scene.ts:39,79,103` (pathSource enum)
- Modify: `aegis-web/src/stores/simulation.ts:17,59,80` (stochastic state)
- Modify: `aegis-web/src/api/client.ts:195-222` (stochastic params in payload)
- Modify: `aegis-web/src/hooks/useDosimetry.ts:22,58,67-74,107,120` (pathSource branching)

- [ ] **Step 1: Update scene store**

In `aegis-web/src/stores/scene.ts`, replace `rtEnabled: boolean` with `pathSource`:

```typescript
// Replace line 39: rtEnabled: boolean
pathSource: 'synthetic' | 'stochastic' | 'rt'

// Replace line 79: rtEnabled: false,
pathSource: 'synthetic',

// Replace line 103: setRtEnabled: (enabled) => set({ rtEnabled: enabled }),
setPathSource: (source: SceneStore['pathSource']) => set({ pathSource: source }),
```

Update the interface and action types accordingly.

- [ ] **Step 2: Update simulation store**

In `aegis-web/src/stores/simulation.ts`, add stochastic fields (keep nPaths):

```typescript
// Add after line 17 (nPaths):
stochasticPreset: string
stochasticOverrides: Record<string, number>
stochasticSeed: number

// Add defaults after line 59 (nPaths: 1):
stochasticPreset: '3GPP_38.901_UMi_LOS',
stochasticOverrides: {},
stochasticSeed: 42,

// Add setters:
setStochasticPreset: (v: string) => set({ stochasticPreset: v }),
setStochasticOverrides: (v: Record<string, number>) => set({ stochasticOverrides: v }),
setStochasticSeed: (v: number) => set({ stochasticSeed: v }),
```

- [ ] **Step 3: Update API client**

In `aegis-web/src/api/client.ts`, add stochastic fields to `ComputeParams` and `computePayload`:

```typescript
// Add to ComputeParams interface (after nPaths):
stochastic?: boolean
stochasticPreset?: string
stochasticOverrides?: Record<string, number>
stochasticSeed?: number
freqGhz?: number

// Add to computePayload function (after n_paths):
...(params.stochastic ? {
  stochastic: true,
  stochastic_preset: params.stochasticPreset,
  stochastic_overrides: params.stochasticOverrides,
  stochastic_seed: params.stochasticSeed,
  freq_ghz: params.freqGhz,
} : {}),
```

- [ ] **Step 4: Update RayTracingPanel.tsx (must be in same commit as store change)**

In `aegis-web/src/components/panels/RayTracingPanel.tsx`, replace `rtEnabled` references with `pathSource`:

```typescript
// Replace: const rtEnabled = useSceneStore(s => s.rtEnabled)
const pathSource = useSceneStore(s => s.pathSource)
const rtEnabled = pathSource === 'rt'

// Replace: onChange={e => useSceneStore.setState({ rtEnabled: e.target.checked })}
onChange={e => useSceneStore.getState().setPathSource(e.target.checked ? 'rt' : 'synthetic')}
```

- [ ] **Step 5: Update useDosimetry hook**

In `aegis-web/src/hooks/useDosimetry.ts`:

```typescript
// Replace rtEnabled read (line 22):
const pathSource = useSceneStore(s => s.pathSource)

// Add stochastic reads:
const stochasticPreset = useSimulationStore(s => s.stochasticPreset)
const stochasticOverrides = useSimulationStore(s => s.stochasticOverrides)
const stochasticSeed = useSimulationStore(s => s.stochasticSeed)
const freqGhz = useSimulationStore(s => s.freqGhz)

// Update params object to include stochastic fields:
const params = {
  ...existingParams,
  stochastic: pathSource === 'stochastic',
  stochasticPreset,
  stochasticOverrides,
  stochasticSeed,
  freqGhz,
}

// Update endpoint selection (lines 67-74):
if (pathSource === 'rt' && rtSource === 'voxel') { ... }
else if (pathSource === 'rt' && rtSource === 'differt' && loadedScenePath) { ... }
else if (pathSource === 'rt' && rtSource === 'sionna' && loadedScenePath) { ... }
else { computeCall = computeDosimetry(params, controller.signal) }

// IMPORTANT: update BOTH dependency arrays explicitly:
// useCallback deps (line 107):
}, [antennaPos, mode, fresnel, polarisation, curvature, diffraction, powerDbm, tissue, nPaths,
    bodyOffset, bodyRotationY, config, caps, pathSource, rtSource, rtMaxOrder, loadedScenePath,
    stochasticPreset, stochasticOverrides, stochasticSeed, freqGhz])

// useEffect deps (line 120):
}, [antennaPos, mode, fresnel, polarisation, curvature, diffraction, powerDbm, tissue, nPaths,
    bodyOffset, bodyRotationY, triggerCompute, config, stochasticPreset, stochasticOverrides,
    stochasticSeed, freqGhz, pathSource])
```

- [ ] **Step 6: Type check and commit**

```bash
cd aegis-web && npx tsc --noEmit  # type check
cd ..
git add aegis-web/src/stores/scene.ts aegis-web/src/stores/simulation.ts aegis-web/src/api/client.ts aegis-web/src/hooks/useDosimetry.ts aegis-web/src/components/panels/RayTracingPanel.tsx
git commit -m "Add pathSource enum and stochastic state to frontend stores"
```

---

## Task 6: Frontend panels

New StochasticPanel, update RayTracingPanel and ParametersPanel.

**Files:**
- Create: `aegis-web/src/components/panels/StochasticPanel.tsx`
- Modify: `aegis-web/src/components/panels/ParametersPanel.tsx:165-176` (hide old dropdown)
- Modify: `aegis-web/src/components/layout/Sidebar.tsx:12,69-76` (add accordion item)

Note: RayTracingPanel.tsx was already updated in Task 5 (same commit as store migration).

- [ ] **Step 1: Create StochasticPanel.tsx**

```tsx
// aegis-web/src/components/panels/StochasticPanel.tsx
import { useEffect, useState } from 'react'
import { useSceneStore } from '@/stores/scene'
import { useSimulationStore } from '@/stores/simulation'

interface PresetInfo {
  name: string
  featured: boolean
  params: Record<string, number | string>
}

export default function StochasticPanel() {
  const pathSource = useSceneStore(s => s.pathSource)
  const setPathSource = useSceneStore(s => s.setPathSource)
  const preset = useSimulationStore(s => s.stochasticPreset)
  const setPreset = useSimulationStore(s => s.setStochasticPreset)
  const overrides = useSimulationStore(s => s.stochasticOverrides)
  const setOverrides = useSimulationStore(s => s.setStochasticOverrides)
  const seed = useSimulationStore(s => s.stochasticSeed)
  const setSeed = useSimulationStore(s => s.setStochasticSeed)
  const freqGhz = useSimulationStore(s => s.freqGhz)

  const [presets, setPresets] = useState<PresetInfo[]>([])
  const [presetParams, setPresetParams] = useState<Record<string, number | string>>({})

  const enabled = pathSource === 'stochastic'

  useEffect(() => {
    fetch('/api/channel-presets')
      .then(r => r.json())
      .then((data: PresetInfo[]) => {
        setPresets(data.filter(p => p.featured))
        const current = data.find(p => p.name === preset)
        if (current) setPresetParams(current.params)
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    const p = presets.find(p => p.name === preset)
    if (p) setPresetParams(p.params)
  }, [preset, presets])

  const selectClass = "w-full bg-background border border-border rounded px-2 py-1.5 text-sm text-foreground"
  const inputClass = selectClass
  const labelClass = "text-xs text-muted-foreground block mt-2 mb-1"

  const getVal = (key: string, fallback: number = 0) =>
    overrides[key] ?? (presetParams[key] as number) ?? fallback

  const setOverride = (key: string, val: number) =>
    setOverrides({ ...overrides, [key]: val })

  return (
    <div>
      <label className="flex items-center gap-2 text-xs text-foreground">
        <input type="checkbox" checked={enabled}
          onChange={e => setPathSource(e.target.checked ? 'stochastic' : 'synthetic')} />
        Enable stochastic channel
      </label>

      {enabled && (
        <>
          <label className={labelClass}>Scenario</label>
          <select className={selectClass} value={preset}
            onChange={e => { setPreset(e.target.value); setOverrides({}) }}>
            {presets.map(p => (
              <option key={p.name} value={p.name}>
                {p.name.replace(/_/g, ' ').replace('3GPP ', '')}
              </option>
            ))}
          </select>

          <label className={labelClass}>K-factor (dB)</label>
          <input type="number" className={inputClass} step={1}
            value={getVal('KF_mu', 9)}
            onChange={e => setOverride('KF_mu', Number(e.target.value))} />

          <label className={labelClass}>Azimuth spread (deg)</label>
          <input type="number" className={inputClass} step={1} min={1} max={180}
            value={Math.round(10 ** getVal('AS_A_mu', 1.73))}
            onChange={e => {
              const deg = Number(e.target.value)
              if (deg > 0) setOverride('AS_A_mu', Math.log10(deg))
            }} />

          <label className={labelClass}>Elevation spread (deg)</label>
          <input type="number" className={inputClass} step={1} min={1} max={90}
            value={Math.round(10 ** getVal('ES_A_mu', 0.73))}
            onChange={e => {
              const deg = Number(e.target.value)
              if (deg > 0) setOverride('ES_A_mu', Math.log10(deg))
            }} />

          <label className={labelClass}>Clusters</label>
          <input type="number" className={inputClass} step={1} min={1} max={50}
            value={getVal('NumClusters', 12)}
            onChange={e => setOverride('NumClusters', Number(e.target.value))} />

          <label className={labelClass}>Sub-paths per cluster</label>
          <input type="number" className={inputClass} step={1} min={1} max={20}
            value={getVal('NumSubPaths', 20)}
            onChange={e => setOverride('NumSubPaths', Number(e.target.value))} />

          <label className={labelClass}>Seed</label>
          <input type="number" className={inputClass}
            value={seed} onChange={e => setSeed(Number(e.target.value))} />

          <button
            className="mt-2 text-xs text-primary hover:underline cursor-pointer"
            onClick={() => setOverrides({})}
          >
            Reset to preset defaults
          </button>
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Update ParametersPanel.tsx**

Hide the old "Stochastic propagation" dropdown when stochastic mode is active:

```tsx
// Add at top of component:
const pathSource = useSceneStore(s => s.pathSource)

// Wrap the stochastic propagation section (lines 165-176) in:
{pathSource !== 'stochastic' && (
  <>
    <label className={labelClass}>Stochastic propagation</label>
    <select ...>...</select>
  </>
)}
```

- [ ] **Step 3: Add StochasticPanel to Sidebar.tsx**

```tsx
// Add import (after line 12):
import StochasticPanel from '@/components/panels/StochasticPanel'

// Add accordion item after Ray Tracing (after line 76):
<AccordionItem value="stochastic" className="border-b border-border px-3">
  <AccordionTrigger className="text-sm font-medium py-3">Stochastic</AccordionTrigger>
  <AccordionContent>
    <div className="py-2">
      <StochasticPanel />
    </div>
  </AccordionContent>
</AccordionItem>
```

- [ ] **Step 4: Type check and commit**

```bash
cd aegis-web && npx tsc --noEmit
cd ..
git add aegis-web/src/components/panels/StochasticPanel.tsx aegis-web/src/components/panels/ParametersPanel.tsx aegis-web/src/components/layout/Sidebar.tsx
git commit -m "Add Stochastic panel with 3GPP scenario presets and editable params"
```

---

## Task 7: Config and documentation

Update default.json, viewer docs.

**Files:**
- Modify: `configs/default.json` (add stochastic block)
- Modify: `docs/user_guide/viewer.md:61` (update dosimetry panel description)

- [ ] **Step 1: Update default.json**

Add `stochastic` key inside the `dosimetry` object (after `synthetic_paths`):

```json
"stochastic": {
  "preset_dir": "data/channel_presets",
  "default_preset": "3GPP_38.901_UMi_LOS",
  "default_seed": 42,
  "featured_presets": [
    "Freespace",
    "3GPP_38.901_UMi_LOS",
    "3GPP_38.901_UMi_NLOS",
    "3GPP_38.901_UMa_LOS",
    "3GPP_38.901_UMa_NLOS",
    "3GPP_38.901_Indoor_LOS",
    "3GPP_38.901_Indoor_NLOS",
    "3GPP_38.901_InF_LOS",
    "3GPP_38.901_RMa_LOS",
    "3GPP_38.901_RMa_NLOS"
  ]
}
```

- [ ] **Step 2: Update viewer.md**

Replace the dosimetry panel paragraph with:

```markdown
**Dosimetry panel.** Choose fidelity level (0-6), tissue preset, transmit power, and frequency. Levels 4-6 add polarization, curvature, and diffraction corrections.

**Stochastic panel.** When ray tracing is off, controls how multipath is modeled. Select a 3GPP TR 38.901 scenario preset (UMi, UMa, Indoor, InF, RMa, in LOS or NLOS variants) and the channel model generates cluster-based multipath with proper K-factor splitting, angular spreads, and sub-path structure. You can override individual parameters (K-factor, azimuth/elevation spread, number of clusters) or reset to the preset defaults. This is mutually exclusive with ray tracing: enabling one disables the other.
```

- [ ] **Step 3: Run all fast tests**

Run: `py -3.12 -m pytest tests/ -m "not slow" -x`
Expected: All pass

- [ ] **Step 4: Lint, format, commit**

```bash
py -3.12 -m ruff check src/ tests/
py -3.12 -m ruff format src/ tests/
git add configs/default.json docs/user_guide/viewer.md
git commit -m "Add stochastic channel config and update viewer docs"
```

---

## Task 8: Final integration test and push

- [ ] **Step 1: Run full test suite**

Run: `py -3.12 -m pytest tests/ -m "not slow" -x -v`
Expected: All pass including new channel tests

- [ ] **Step 2: Run frontend build**

```bash
cd aegis-web && npm run build
```
Expected: Build succeeds with no errors

- [ ] **Step 3: Manual smoke test**

```bash
py -3.12 -m aegis.viewer --no-open
```

Open `http://localhost:5173`, place antenna, open Stochastic panel, enable, select "UMi LOS", verify heatmap updates. Toggle between Stochastic and Ray Tracing, verify mutual exclusion.

- [ ] **Step 4: Push**

```bash
git push origin master
```
