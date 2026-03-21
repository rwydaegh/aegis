# Phase 1: Reproducible research backbone - Implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add dataclass simulation configs, a CLI batch runner, and Sionna RT integration so dosimetry runs are reproducible and large-scene ray tracing is available.

**Architecture:** Three independent modules: `config.py` (frozen dataclass hierarchy with YAML serialization), `run.py` (CLI entry point that orchestrates load-trace-compute-save), `integration/sionna.py` (converts Sionna RT channel coefficients to PropagationPaths using a dual-pol isotropic RX probe and the scale factor `sqrt(8*pi*Z_0*P_T)/lambda`).

**Tech Stack:** Python 3.12, NumPy, PyYAML, sionna-rt (optional), pytest, existing AEGIS engine/tissue/geometry modules.

**Spec:** `docs/superpowers/specs/2026-03-21-phase1-reproducible-backbone-design.md`

---

## File structure

| File | Responsibility |
|------|----------------|
| `src/aegis/config.py` (create) | SimulationConfig dataclass hierarchy, YAML serialization, validation |
| `src/aegis/run.py` (create) | CLI batch runner: argparse, config resolution, orchestration, result saving |
| `src/aegis/integration/sionna.py` (create) | Sionna RT to PropagationPaths conversion (physics, unit scaling) |
| `src/aegis/integration/__init__.py` (modify) | Add sionna exports |
| `src/aegis/paths.py` (modify) | Fix psi docstring from `V/m / sqrt(W)` to `V/m` |
| `pyproject.toml` (modify) | Add pyyaml dep, sionna optional dep, aegis-run script |
| `tests/test_config.py` (create) | Config validation, round-trip, CLI override tests |
| `tests/test_run.py` (create) | CLI smoke tests |
| `tests/test_sionna.py` (create) | Sionna unit conversion and integration tests |

---

## Task 1: Fix psi docstring in paths.py

**Files:**
- Modify: `src/aegis/paths.py:25`

- [ ] **Step 1: Fix the docstring**

Change line 25 from:
```python
    psi : (N, 3) complex polarisation-amplitude vectors (V/m / sqrt(W))
```
to:
```python
    psi : (N, 3) complex polarisation-amplitude vectors (V/m)
```

The code stores absolute E-field with TX power included. The `power` property `|psi|^2 / (2*Z_0)` returns W/m^2 directly, confirming V/m units.

- [ ] **Step 2: Run existing tests to confirm nothing breaks**

Run: `py -3.12 -m pytest tests/ -m "not slow" -x`
Expected: all pass (docstring-only change)

- [ ] **Step 3: Commit**

```bash
git add src/aegis/paths.py
git commit -m "Fix psi docstring: units are V/m, not V/m/sqrt(W)

The code stores absolute E-field with TX power included. The monograph's
per-sqrt(W) convention is for theoretical development only."
```

---

## Task 2: Add PyYAML dependency and Sionna optional group

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add pyyaml to core dependencies**

In `pyproject.toml`, change:
```toml
dependencies = [
    "numpy>=1.24",
    "scipy>=1.10,<2",
]
```
to:
```toml
dependencies = [
    "numpy>=1.24",
    "scipy>=1.10,<2",
    "pyyaml>=6.0",
]
```

- [ ] **Step 2: Add sionna optional dependency group and aegis-run script**

After the `rt` group, add:
```toml
sionna = ["sionna-rt>=1.0,<2.0"]
```

Update the `all` group to include sionna:
```toml
all = ["aegis[gpu,viz,rt,sionna,docs,dev,cloud]"]
```

Add the `aegis-run` console script:
```toml
[project.scripts]
aegis = "aegis.__main__:main"
aegis-run = "aegis.run:main"
```

- [ ] **Step 3: Reinstall**

Run: `pip install -e ".[dev]"`
Expected: installs pyyaml, no errors

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "Add pyyaml dependency, sionna optional group, aegis-run script"
```

---

## Task 3: SimulationConfig dataclasses with validation

**Files:**
- Create: `src/aegis/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing tests for config validation**

Create `tests/test_config.py`:
```python
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

    def test_frozen(self):
        cfg = _make_config()
        with pytest.raises(AttributeError):
            cfg.dosimetry = DosimetryConfig(level=3)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3.12 -m pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'aegis.config'`

- [ ] **Step 3: Implement config.py**

Create `src/aegis/config.py`:
```python
"""Simulation configuration: frozen dataclasses with YAML serialization.

Defines a complete, reproducible simulation run. Separate from the viewer
config system (viewer/config.py). Each run saves its resolved config as
YAML alongside results.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class TissueConfig:
    """Tissue properties for the simulation."""

    name: str = "Skin"  # IT'IS database uses capitalized names
    frequency_hz: float = 28e9

    def __post_init__(self) -> None:
        if self.frequency_hz <= 0:
            raise ValueError(f"frequency_hz must be positive, got {self.frequency_hz}")


@dataclass(frozen=True)
class BodyConfig:
    """Body phantom selection."""

    name: str = "thelonious"
    mass_kg: float | None = None


@dataclass(frozen=True)
class AntennaConfig:
    """Transmit antenna configuration."""

    positions: list[list[float]] = field(default_factory=lambda: [[5.0, 0.0, 1.0]])
    power_dbm: float = 30.0
    polarisation: str = "vertical"
    pattern: str = "isotropic"


@dataclass(frozen=True)
class RayTracerConfig:
    """Ray tracer backend selection."""

    backend: str = "differt"
    max_bounces: int = 3
    scene_path: str | None = None

    def __post_init__(self) -> None:
        if self.backend not in ("differt", "sionna", "synthetic"):
            raise ValueError(f"backend must be 'differt', 'sionna', or 'synthetic', got '{self.backend}'")


@dataclass(frozen=True)
class DosimetryConfig:
    """Dosimetry computation parameters."""

    level: int = 2
    spatial_averaging: bool = False

    def __post_init__(self) -> None:
        if not 0 <= self.level <= 8:
            raise ValueError(f"level must be 0-8, got {self.level}")


@dataclass(frozen=True)
class SimulationConfig:
    """Complete simulation run configuration.

    Fully describes a reproducible simulation: tissue, body, antenna,
    ray tracer, and dosimetry parameters.
    """

    tissue: TissueConfig = field(default_factory=TissueConfig)
    body: BodyConfig = field(default_factory=BodyConfig)
    antenna: AntennaConfig = field(default_factory=AntennaConfig)
    raytracer: RayTracerConfig = field(default_factory=RayTracerConfig)
    dosimetry: DosimetryConfig = field(default_factory=DosimetryConfig)
    output_dir: str = "outputs"

    def to_yaml(self, path: str | Path) -> None:
        """Save config as YAML."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w") as f:
            yaml.dump(dataclasses.asdict(self), f, default_flow_style=False, sort_keys=False)

    @classmethod
    def from_yaml(cls, path: str | Path) -> SimulationConfig:
        """Load config from YAML."""
        with Path(path).open() as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)


@classmethod
    def from_dict(cls, data: dict) -> SimulationConfig:
        """Reconstruct a SimulationConfig from a nested dict (e.g. YAML output)."""
        known = {f.name for f in dataclasses.fields(cls)}
        unknown = set(data) - known
        if unknown:
            raise ValueError(f"Unknown config keys: {unknown}")
        kwargs = {}
        for key, val in data.items():
            if key in _CONFIG_CLASSES and isinstance(val, dict):
                kwargs[key] = _CONFIG_CLASSES[key](**val)
            else:
                kwargs[key] = val
        return cls(**kwargs)


_CONFIG_CLASSES: dict[str, type] = {
    "tissue": TissueConfig,
    "body": BodyConfig,
    "antenna": AntennaConfig,
    "raytracer": RayTracerConfig,
    "dosimetry": DosimetryConfig,
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `py -3.12 -m pytest tests/test_config.py -v`
Expected: all 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/aegis/config.py tests/test_config.py
git commit -m "Add SimulationConfig dataclass hierarchy with validation"
```

---

## Task 4: Config YAML round-trip

**Files:**
- Modify: `tests/test_config.py`

- [ ] **Step 1: Write failing round-trip test**

Add to `tests/test_config.py`:
```python
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
```

- [ ] **Step 2: Run tests**

Run: `py -3.12 -m pytest tests/test_config.py -v`
Expected: all 9 tests PASS (validation tests + round-trip tests)

- [ ] **Step 3: Commit**

```bash
git add tests/test_config.py
git commit -m "Add YAML round-trip tests for SimulationConfig"
```

---

## Task 5: CLI batch runner

**Files:**
- Create: `src/aegis/run.py`
- Create: `tests/test_run.py`

- [ ] **Step 1: Write failing smoke test**

Create `tests/test_run.py`:
```python
"""Smoke tests for the CLI batch runner."""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import yaml


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3.12 -m pytest tests/test_run.py -v`
Expected: FAIL (aegis.run module doesn't exist yet, or "synthetic" backend not recognized)

- [ ] **Step 3: Update RayTracerConfig validation to allow "synthetic"**

In `src/aegis/config.py`, update the backend validation:
```python
    def __post_init__(self) -> None:
        if self.backend not in ("differt", "sionna", "synthetic"):
            raise ValueError(f"backend must be 'differt', 'sionna', or 'synthetic', got '{self.backend}'")
```

The "synthetic" backend generates random paths without needing a ray tracer. This is needed for testing and for quick dosimetry estimates.

- [ ] **Step 4: Implement run.py**

Create `src/aegis/run.py`:
```python
"""CLI batch runner for reproducible dosimetry simulations.

Usage:
    py -3.12 -m aegis.run --config config.yaml
    py -3.12 -m aegis.run --body duke --level 3 --frequency 28e9
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from aegis.config import DosimetryConfig, RayTracerConfig, SimulationConfig, TissueConfig
from aegis.constants import Z_0
from aegis.engine import DosimetryEngine
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import TissueModel


def _find_data_dir() -> Path:
    """Find the data/ directory, respecting AEGIS_DATA_DIR env var."""
    import os

    env = os.environ.get("AEGIS_DATA_DIR")
    if env:
        return Path(env)
    return Path(__file__).parent.parent.parent / "data"


def _load_body(cfg: SimulationConfig):
    """Load body mesh from config."""
    from aegis.geometry.mesh import BodyMesh

    data_dir = _find_data_dir()
    stl_path = data_dir / f"{cfg.body.name}.stl"
    if not stl_path.exists():
        raise FileNotFoundError(f"Body mesh not found: {stl_path}")
    return BodyMesh.load(stl_path)


def _load_tissue(cfg: SimulationConfig) -> TissueModel:
    """Load tissue model from config."""
    return TissueModel.from_database(cfg.tissue.name, cfg.tissue.frequency_hz)


def _generate_paths(cfg: SimulationConfig) -> PropagationPaths:
    """Generate propagation paths based on configured backend."""
    tx_pos = np.array(cfg.antenna.positions, dtype=np.float64)
    power_w = 10 ** ((cfg.antenna.power_dbm - 30) / 10)

    if cfg.raytracer.backend == "synthetic":
        return _synthetic_paths(tx_pos, power_w)
    elif cfg.raytracer.backend == "differt":
        from aegis.integration.differt import paths_from_differt_scene

        if cfg.raytracer.scene_path is None:
            raise ValueError("scene_path required for differt backend")
        return paths_from_differt_scene(
            scene_path=cfg.raytracer.scene_path,
            tx_positions=tx_pos,
            rx_position=np.zeros(3),
            freq_hz=cfg.tissue.frequency_hz,
            max_bounces=cfg.raytracer.max_bounces,
            tx_power_dbm=cfg.antenna.power_dbm,
            initial_polarisation=cfg.antenna.polarisation,
        )
    elif cfg.raytracer.backend == "sionna":
        from aegis.integration.sionna import paths_from_sionna_scene

        if cfg.raytracer.scene_path is None:
            raise ValueError("scene_path required for sionna backend")
        import sionna.rt

        scene = sionna.rt.load_scene(cfg.raytracer.scene_path)
        return paths_from_sionna_scene(
            scene=scene,
            tx_positions=tx_pos,
            rx_position=np.zeros(3),
            freq_hz=cfg.tissue.frequency_hz,
            max_bounces=cfg.raytracer.max_bounces,
            tx_power_dbm=cfg.antenna.power_dbm,
            tx_pattern=cfg.antenna.pattern,
        )
    else:
        raise ValueError(f"Unknown backend: {cfg.raytracer.backend}")


def _synthetic_paths(tx_pos: np.ndarray, power_w: float) -> PropagationPaths:
    """Generate synthetic paths for testing (no ray tracer needed)."""
    n_elements = tx_pos.shape[0]
    k_hats = []
    powers = []
    for i in range(n_elements):
        direction = -tx_pos[i]
        dist = np.linalg.norm(direction)
        if dist < 1e-10:
            continue
        k_hat = direction / dist
        s_inc = power_w / (4 * np.pi * dist**2)
        k_hats.append(k_hat)
        powers.append(s_inc)

    if not k_hats:
        return PropagationPaths.from_powers(k_hat=np.zeros((0, 3)), power=np.zeros(0))
    return PropagationPaths.from_powers(
        k_hat=np.array(k_hats),
        power=np.array(powers),
    )


def _save_results(cfg: SimulationConfig, result, elapsed: float) -> Path:
    """Save config, result arrays, and summary JSON to output directory."""
    from aegis.compliance import ICNIRP_2020

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = Path(cfg.output_dir) / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)

    cfg.to_yaml(run_dir / "config.yaml")

    np.savez(
        run_dir / "result.npz",
        sab=result.sab,
        p_abs=np.array(result.p_abs),
    )

    peak_sab = float(np.max(result.sab)) if len(result.sab) > 0 else 0.0
    summary = {
        "peak_sab": peak_sab,
        "p_abs": float(result.p_abs),
        "compliant": peak_sab < ICNIRP_2020.sab_peak,
        "compliant_note": "conservative (no spatial averaging)",
        "level": cfg.dosimetry.level,
        "n_triangles": len(result.sab),
        "elapsed_s": round(elapsed, 3),
    }
    with (run_dir / "summary.json").open("w") as f:
        json.dump(summary, f, indent=2)

    return run_dir


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="aegis-run", description="AEGIS batch dosimetry runner")
    p.add_argument("--config", type=str, help="Path to YAML config file")
    p.add_argument("--body", type=str, help="Body phantom name (e.g. thelonious, duke)")
    p.add_argument("--frequency", type=float, help="Frequency in Hz (e.g. 28e9)")
    p.add_argument("--level", type=int, help="Fidelity level 0-8")
    p.add_argument("--power-dbm", type=float, help="TX power in dBm")
    p.add_argument("--antenna-pos", type=str, help="TX position as 'x,y,z'")
    p.add_argument("--backend", type=str, help="Ray tracer backend: differt, sionna, synthetic")
    p.add_argument("--max-bounces", type=int, help="Max ray bounces")
    p.add_argument("--scene-path", type=str, help="Scene file path")
    p.add_argument("--output-dir", type=str, help="Output directory")
    return p


def _apply_overrides(cfg_dict: dict, args: argparse.Namespace) -> dict:
    """Apply CLI overrides to config dict."""
    if args.body is not None:
        cfg_dict.setdefault("body", {})["name"] = args.body
    if args.frequency is not None:
        cfg_dict.setdefault("tissue", {})["frequency_hz"] = args.frequency
    if args.level is not None:
        cfg_dict.setdefault("dosimetry", {})["level"] = args.level
    if args.power_dbm is not None:
        cfg_dict.setdefault("antenna", {})["power_dbm"] = args.power_dbm
    if args.antenna_pos is not None:
        pos = [float(x) for x in args.antenna_pos.split(",")]
        cfg_dict.setdefault("antenna", {})["positions"] = [pos]
    if args.backend is not None:
        cfg_dict.setdefault("raytracer", {})["backend"] = args.backend
    if args.max_bounces is not None:
        cfg_dict.setdefault("raytracer", {})["max_bounces"] = args.max_bounces
    if args.scene_path is not None:
        cfg_dict.setdefault("raytracer", {})["scene_path"] = args.scene_path
    if args.output_dir is not None:
        cfg_dict["output_dir"] = args.output_dir
    return cfg_dict


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Load base config from YAML or empty dict
    if args.config:
        import yaml

        with open(args.config) as f:
            cfg_dict = yaml.safe_load(f) or {}
    else:
        cfg_dict = {}

    cfg_dict = _apply_overrides(cfg_dict, args)

    cfg = SimulationConfig.from_dict(cfg_dict) if cfg_dict else SimulationConfig()

    print(f"AEGIS batch run: level={cfg.dosimetry.level}, backend={cfg.raytracer.backend}")

    body = _load_body(cfg)
    tissue = _load_tissue(cfg)
    paths = _generate_paths(cfg)
    engine = DosimetryEngine(tissue)

    t0 = time.monotonic()
    result = engine.compute(body, paths, level=cfg.dosimetry.level)
    elapsed = time.monotonic() - t0

    run_dir = _save_results(cfg, result, elapsed)
    peak = float(np.max(result.sab)) if len(result.sab) > 0 else 0.0
    print(f"Done in {elapsed:.2f}s. Peak Sab={peak:.4f} W/m^2. Results: {run_dir}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run smoke test**

Run: `py -3.12 -m pytest tests/test_run.py::test_run_with_yaml_config -v`
Expected: PASS (uses "synthetic" backend, needs body mesh data)

Note: this test requires body mesh data. Mark it `@pytest.mark.slow` in the test file. Add `@pytest.mark.slow` decorator above `def test_run_with_yaml_config`.

- [ ] **Step 6: Add a unit test that doesn't need mesh data**

Add to `tests/test_run.py`:
```python
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
```

- [ ] **Step 7: Run all tests**

Run: `py -3.12 -m pytest tests/test_config.py tests/test_run.py -v`
Expected: all PASS

- [ ] **Step 8: Lint and commit**

```bash
py -3.12 -m ruff check src/aegis/config.py src/aegis/run.py tests/test_config.py tests/test_run.py
py -3.12 -m ruff format src/aegis/config.py src/aegis/run.py tests/test_config.py tests/test_run.py
git add src/aegis/config.py src/aegis/run.py tests/test_config.py tests/test_run.py
git commit -m "Add CLI batch runner with synthetic backend

python -m aegis.run --config config.yaml runs a complete dosimetry
pipeline and saves config.yaml, result.npz, summary.json to outputs/."
```

---

## Task 6: Sionna RT integration - unit conversion core

**Files:**
- Create: `src/aegis/integration/sionna.py`
- Create: `tests/test_sionna.py`

This is the physics-critical task. The conversion formula is `psi = sqrt(8*pi*Z_0*P_T)/lambda * (a_theta * e_theta + a_phi * e_phi)`.

- [ ] **Step 1: Write the physics canary test (no Sionna dependency)**

Create `tests/test_sionna.py`:
```python
"""Tests for Sionna RT integration.

The unit conversion test does NOT require sionna-rt to be installed.
It tests the pure-math conversion from Sionna's channel coefficients to
AEGIS psi vectors.
"""

import numpy as np
import pytest

from aegis.constants import C_0, Z_0


class TestUnitConversion:
    """Test the Sionna a -> AEGIS psi conversion formula.

    Reference: spec section 1c, numerical verification table.
    LOS, isotropic TX, P_T=1W, d=10m, f=28GHz, lambda=0.01071m.
    """

    def test_los_power_density(self):
        """Verify converted psi gives correct free-space power density."""
        from aegis.integration.sionna import _convert_a_to_psi, _spherical_basis

        freq_hz = 28e9
        lambda_ = C_0 / freq_hz
        d = 10.0
        P_T = 1.0

        # Sionna LOS coefficient for isotropic TX: a = lambda/(4*pi*d)
        # Arriving from +x direction: theta_r = pi/2, phi_r = pi (pointing -x)
        a_magnitude = lambda_ / (4 * np.pi * d)

        # Vertically polarized: all energy in theta component
        a_theta = np.array([a_magnitude + 0j])
        a_phi = np.array([0.0 + 0j])
        theta_r = np.array([np.pi / 2])
        phi_r = np.array([np.pi])

        psi = _convert_a_to_psi(a_theta, a_phi, theta_r, phi_r, freq_hz, P_T)

        # |psi|^2 / (2*Z_0) should equal S_inc = P_T / (4*pi*d^2)
        power = np.sum(np.abs(psi) ** 2, axis=1) / (2 * Z_0)
        expected = P_T / (4 * np.pi * d**2)
        np.testing.assert_allclose(power, expected, rtol=1e-10)

    def test_los_psi_magnitude_matches_differt(self):
        """Cross-check: psi magnitude should match DiffeRT's formula."""
        from aegis.integration.sionna import _convert_a_to_psi

        freq_hz = 28e9
        lambda_ = C_0 / freq_hz
        d = 10.0
        P_T = 1.0

        a_theta = np.array([lambda_ / (4 * np.pi * d) + 0j])
        a_phi = np.array([0.0 + 0j])
        theta_r = np.array([np.pi / 2])
        phi_r = np.array([0.0])

        psi = _convert_a_to_psi(a_theta, a_phi, theta_r, phi_r, freq_hz, P_T)

        # DiffeRT formula: amplitude = sqrt(2*Z_0*P_T/(4*pi)) / d
        expected_magnitude = np.sqrt(2 * Z_0 * P_T / (4 * np.pi)) / d
        actual_magnitude = np.linalg.norm(psi[0])
        np.testing.assert_allclose(actual_magnitude, expected_magnitude, rtol=1e-10)

    def test_psi_perpendicular_to_k_hat(self):
        """psi must be perpendicular to the direction of arrival."""
        from aegis.integration.sionna import _convert_a_to_psi, _spherical_basis

        freq_hz = 28e9
        a_theta = np.array([0.001 + 0.002j])
        a_phi = np.array([0.003 - 0.001j])
        theta_r = np.array([1.2])
        phi_r = np.array([0.7])

        psi = _convert_a_to_psi(a_theta, a_phi, theta_r, phi_r, freq_hz, 1.0)

        # k_hat from spherical angles
        k_hat = np.array([
            np.sin(theta_r[0]) * np.cos(phi_r[0]),
            np.sin(theta_r[0]) * np.sin(phi_r[0]),
            np.cos(theta_r[0]),
        ])
        dot = np.abs(np.dot(psi[0].real, k_hat)) + np.abs(np.dot(psi[0].imag, k_hat))
        assert dot < 1e-12

    def test_spherical_basis_orthonormality(self):
        """e_theta and e_phi should be orthonormal and perpendicular to r_hat."""
        from aegis.integration.sionna import _spherical_basis

        theta = np.array([0.5, 1.0, 2.5])
        phi = np.array([0.3, 1.5, 4.0])
        e_theta, e_phi = _spherical_basis(theta, phi)

        for i in range(3):
            # Unit length
            np.testing.assert_allclose(np.linalg.norm(e_theta[i]), 1.0, atol=1e-14)
            np.testing.assert_allclose(np.linalg.norm(e_phi[i]), 1.0, atol=1e-14)
            # Orthogonal to each other
            np.testing.assert_allclose(np.dot(e_theta[i], e_phi[i]), 0.0, atol=1e-14)
            # Orthogonal to r_hat
            r_hat = np.array([
                np.sin(theta[i]) * np.cos(phi[i]),
                np.sin(theta[i]) * np.sin(phi[i]),
                np.cos(theta[i]),
            ])
            np.testing.assert_allclose(np.dot(e_theta[i], r_hat), 0.0, atol=1e-14)
            np.testing.assert_allclose(np.dot(e_phi[i], r_hat), 0.0, atol=1e-14)

    def test_higher_power_scales_psi(self):
        """Doubling TX power should multiply |psi| by sqrt(2)."""
        from aegis.integration.sionna import _convert_a_to_psi

        freq_hz = 28e9
        lambda_ = C_0 / freq_hz
        a_theta = np.array([lambda_ / (4 * np.pi * 10) + 0j])
        a_phi = np.array([0.0 + 0j])
        theta_r = np.array([np.pi / 2])
        phi_r = np.array([0.0])

        psi_1w = _convert_a_to_psi(a_theta, a_phi, theta_r, phi_r, freq_hz, 1.0)
        psi_2w = _convert_a_to_psi(a_theta, a_phi, theta_r, phi_r, freq_hz, 2.0)

        ratio = np.linalg.norm(psi_2w) / np.linalg.norm(psi_1w)
        np.testing.assert_allclose(ratio, np.sqrt(2), rtol=1e-10)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `py -3.12 -m pytest tests/test_sionna.py -v`
Expected: FAIL with `ImportError: cannot import name '_convert_a_to_psi' from 'aegis.integration.sionna'`

- [ ] **Step 3: Implement the conversion core in sionna.py**

Create `src/aegis/integration/sionna.py`:
```python
"""Sionna RT ray tracer integration.

Converts Sionna RT channel coefficients to AEGIS PropagationPaths.
Uses a dual-polarized isotropic RX probe to capture the full E-field
polarisation state, then scales to absolute V/m using:

    psi = sqrt(8*pi*Z_0*P_T) / lambda * (a_theta * e_theta + a_phi * e_phi)

Requires: pip install aegis[sionna]  (installs sionna-rt>=1.0)
"""

from __future__ import annotations

import warnings

import numpy as np

from aegis.constants import C_0, Z_0
from aegis.paths import PropagationPaths


def _check_sionna() -> None:
    """Raise ImportError with helpful message if sionna-rt is not installed."""
    try:
        import sionna.rt  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "Sionna RT is required for this integration. Install with: pip install aegis[sionna]"
        ) from exc


def _spherical_basis(theta: np.ndarray, phi: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Spherical basis vectors e_theta, e_phi at given angles.

    Parameters
    ----------
    theta : (N,) zenith angles in radians
    phi : (N,) azimuth angles in radians

    Returns
    -------
    e_theta : (N, 3) theta basis vectors
    e_phi : (N, 3) phi basis vectors
    """
    ct, st = np.cos(theta), np.sin(theta)
    cp, sp = np.cos(phi), np.sin(phi)
    e_theta = np.column_stack([ct * cp, ct * sp, -st])
    e_phi = np.column_stack([-sp, cp, np.zeros_like(theta)])
    return e_theta, e_phi


def _convert_a_to_psi(
    a_theta: np.ndarray,
    a_phi: np.ndarray,
    theta_r: np.ndarray,
    phi_r: np.ndarray,
    freq_hz: float,
    tx_power_w: float,
) -> np.ndarray:
    """Convert Sionna channel coefficients to AEGIS psi vectors.

    Parameters
    ----------
    a_theta : (N,) complex theta-component of Sionna's channel coefficient
    a_phi : (N,) complex phi-component
    theta_r : (N,) zenith angle of arrival in radians
    phi_r : (N,) azimuth angle of arrival in radians
    freq_hz : carrier frequency in Hz
    tx_power_w : total TX power in watts

    Returns
    -------
    psi : (N, 3) complex polarisation-amplitude vectors in V/m
    """
    lambda_ = C_0 / freq_hz
    scale = np.sqrt(8 * np.pi * Z_0 * tx_power_w) / lambda_

    e_theta, e_phi = _spherical_basis(theta_r, phi_r)

    psi = scale * (a_theta[:, np.newaxis] * e_theta + a_phi[:, np.newaxis] * e_phi)
    return psi.astype(complex)


def paths_from_sionna_scene(
    scene,
    tx_positions: np.ndarray,
    rx_position: np.ndarray,
    freq_hz: float,
    max_bounces: int = 5,
    tx_power_dbm: float = 30.0,
    tx_pattern: str = "isotropic",
) -> PropagationPaths:
    """Run Sionna RT and convert results to PropagationPaths.

    Parameters
    ----------
    scene : sionna.rt Scene object (loaded externally)
    tx_positions : (M_ant, 3) transmitter element positions
    rx_position : (3,) body centroid position
    freq_hz : carrier frequency in Hz
    max_bounces : maximum number of ray interactions
    tx_power_dbm : transmit power in dBm
    tx_pattern : TX antenna pattern name

    Returns
    -------
    PropagationPaths with k_hat, psi, element_index, delay, is_los
    """
    _check_sionna()
    from sionna.rt import PlanarArray, PathSolver

    tx_positions = np.asarray(tx_positions, dtype=np.float64)
    rx_position = np.asarray(rx_position, dtype=np.float64)
    if tx_positions.ndim == 1:
        tx_positions = tx_positions[np.newaxis, :]

    tx_power_w = 10 ** ((tx_power_dbm - 30) / 10)
    n_elements = tx_positions.shape[0]

    # Configure dual-polarized isotropic RX to capture theta/phi field components
    scene.rx_array = PlanarArray(
        num_rows=1, num_cols=1,
        pattern="iso",
        polarization="cross",
    )

    # Configure TX array
    scene.tx_array = PlanarArray(
        num_rows=1, num_cols=n_elements,
        pattern=tx_pattern,
        polarization="V",
    )

    # Set TX and RX positions
    scene.add_transmitter("tx", position=tx_positions[0].tolist())
    scene.add_receiver("rx", position=rx_position.tolist())

    # Compute paths
    solver = PathSolver()
    paths = solver(
        scene=scene,
        max_depth=max_bounces,
        los=True,
        specular_reflection=True,
        diffuse_reflection=False,
        refraction=True,
    )

    # Extract data as numpy
    a_raw, tau_raw = paths.cir(out_type="numpy")
    # a_raw shape: (1, 2, 1, n_elements, n_paths)  [rx, rx_pol, tx, tx_ant, paths]
    # tau_raw shape: (1, 2, 1, n_elements, n_paths)

    theta_r_raw = np.array(paths.theta_r)  # (1, 2, 1, n_elements, n_paths)
    phi_r_raw = np.array(paths.phi_r)
    valid = np.array(paths.valid)  # (1, 2, 1, n_elements, n_paths)

    all_k_hat = []
    all_psi = []
    all_element_index = []
    all_delay = []
    all_is_los = []

    for elem in range(n_elements):
        # Extract per-element data. Use pol=0 (theta) and pol=1 (phi).
        a_theta = a_raw[0, 0, 0, elem, :]  # (n_paths,) complex
        a_phi = a_raw[0, 1, 0, elem, :]
        theta_r = theta_r_raw[0, 0, 0, elem, :]
        phi_r = phi_r_raw[0, 0, 0, elem, :]
        tau = tau_raw[0, 0, 0, elem, :]
        mask = valid[0, 0, 0, elem, :]

        # Filter valid paths
        idx = np.where(mask)[0]
        if len(idx) == 0:
            continue

        a_theta = a_theta[idx]
        a_phi = a_phi[idx]
        theta_r = theta_r[idx]
        phi_r = phi_r[idx]
        tau = tau[idx]

        # Convert to AEGIS psi
        psi = _convert_a_to_psi(a_theta, a_phi, theta_r, phi_r, freq_hz, tx_power_w)

        # k_hat from arrival angles (direction of propagation, toward the body)
        # Sionna's (theta_r, phi_r) gives the direction FROM the body TO the source.
        # AEGIS k_hat is the propagation direction (toward the body), so negate.
        k_hat = -np.column_stack([
            np.sin(theta_r) * np.cos(phi_r),
            np.sin(theta_r) * np.sin(phi_r),
            np.cos(theta_r),
        ])

        # Detect LOS paths (first path in each element is typically LOS)
        is_los = np.zeros(len(idx), dtype=bool)
        if len(idx) > 0:
            is_los[0] = True  # Conservative: mark shortest-delay path as LOS

        all_k_hat.append(k_hat)
        all_psi.append(psi)
        all_element_index.append(np.full(len(idx), elem, dtype=np.intp))
        all_delay.append(tau)
        all_is_los.append(is_los)

    if not all_k_hat:
        return PropagationPaths.from_powers(k_hat=np.zeros((0, 3)), power=np.zeros(0))

    return PropagationPaths(
        k_hat=np.vstack(all_k_hat),
        psi=np.vstack(all_psi),
        element_index=np.concatenate(all_element_index),
        delay=np.concatenate(all_delay),
        is_los=np.concatenate(all_is_los),
    )
```

- [ ] **Step 4: Run unit conversion tests**

Run: `py -3.12 -m pytest tests/test_sionna.py -v`
Expected: all 5 tests PASS (these only test the math, not Sionna itself)

- [ ] **Step 5: Lint and commit**

```bash
py -3.12 -m ruff check src/aegis/integration/sionna.py tests/test_sionna.py
py -3.12 -m ruff format src/aegis/integration/sionna.py tests/test_sionna.py
git add src/aegis/integration/sionna.py tests/test_sionna.py
git commit -m "Add Sionna RT integration with unit conversion

Converts Sionna channel coefficients to AEGIS psi vectors using
psi = sqrt(8*pi*Z_0*P_T)/lambda * (a_theta*e_theta + a_phi*e_phi).
Verified against DiffeRT and free-space path loss to float64 precision."
```

---

## Task 7: Update integration __init__.py

**Files:**
- Modify: `src/aegis/integration/__init__.py`

- [ ] **Step 1: Add conditional sionna imports**

Update `src/aegis/integration/__init__.py`. Import unconditionally (matching the DiffeRT pattern). Sionna is only imported lazily inside `paths_from_sionna_scene()` via `_check_sionna()`, so this import always succeeds:
```python
"""Ray tracer integration: load propagation paths from external tools."""

from aegis.integration.differt import paths_from_differt, paths_from_differt_scene
from aegis.integration.sionna import paths_from_sionna_scene

__all__ = [
    "paths_from_differt",
    "paths_from_differt_scene",
    "paths_from_sionna_scene",
]
```

- [ ] **Step 2: Run all tests**

Run: `py -3.12 -m pytest tests/ -m "not slow" -x`
Expected: all pass

- [ ] **Step 3: Commit**

```bash
git add src/aegis/integration/__init__.py
git commit -m "Export paths_from_sionna_scene from integration package"
```

---

## Task 8: Full test suite validation and push

**Files:** None new

- [ ] **Step 1: Run full fast test suite**

Run: `py -3.12 -m pytest tests/ -m "not slow" -x`
Expected: all pass (existing 133+ tests plus new tests)

- [ ] **Step 2: Run linter**

Run: `py -3.12 -m ruff check src/ tests/`
Expected: no errors

- [ ] **Step 3: Run formatter check**

Run: `py -3.12 -m ruff format --check src/ tests/`
Expected: all files already formatted

- [ ] **Step 4: Push**

```bash
git push origin master
```

---

## Execution order

Tasks 1-2 are prerequisites (docstring fix, dependencies). Tasks 3-4 build the config system. Task 5 builds the CLI runner. Task 6 builds the Sionna integration. Task 7 wires it together. Task 8 validates everything.

Tasks 3-4 and 6 are independent of each other and could be parallelized.

```
Task 1 (psi docstring) ──┐
Task 2 (dependencies)  ──┼── Task 3-4 (config) ──┐
                          │                       ├── Task 5 (CLI runner) ── Task 7 ── Task 8
                          └── Task 6 (sionna)  ───┘
```
