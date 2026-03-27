# Configuration centralization and export implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate all hardcoded default values from the codebase, expand SimulationConfig for reproducibility, add viewer config export, and compress share URLs.

**Architecture:** Create a single `defaults.py` module as the source of truth for all numeric defaults. Replace ~60 scattered literals across 28 backend files. Add a `/api/export-config` endpoint and frontend button. Swap share URL encoding from plain base64 to deflate+base64url via pako.

**Tech Stack:** Python (dataclasses, PyYAML), TypeScript/React (Zustand, pako), Flask

**Spec:** `docs/superpowers/specs/2026-03-27-config-centralization-design.md`

---

### Task 1: Create defaults.py and test it

**Files:**
- Create: `src/aegis/defaults.py`
- Create: `tests/test_defaults.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_defaults.py
"""Verify defaults.py constants match the values previously hardcoded."""
from aegis.defaults import (
    CONCRETE_EPS_R,
    CONCRETE_SIGMA,
    DEFAULT_FIDELITY_LEVEL,
    DEFAULT_FREQ_HZ,
    DEFAULT_MAX_BOUNCES,
    DEFAULT_NOISE_POWER,
    DEFAULT_P_ABS_MAX,
    DEFAULT_POWER_DBM,
    DEFAULT_SEED,
    NUMERICAL_FLOOR,
)


def test_default_values():
    assert DEFAULT_FREQ_HZ == 28e9
    assert DEFAULT_POWER_DBM == 60.0
    assert DEFAULT_P_ABS_MAX == 0.1
    assert DEFAULT_NOISE_POWER == 0.01
    assert DEFAULT_FIDELITY_LEVEL == 2
    assert DEFAULT_MAX_BOUNCES == 3
    assert DEFAULT_SEED == 42
    assert NUMERICAL_FLOOR == 1e-30
    assert CONCRETE_EPS_R == 5.31
    assert CONCRETE_SIGMA == 0.0326
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_defaults.py -v`
Expected: FAIL with ModuleNotFoundError (defaults.py does not exist yet)

- [ ] **Step 3: Create defaults.py**

```python
# src/aegis/defaults.py
"""Project-wide default values.

Single source of truth for all defaults that appear in function
signatures, dataclass fields, and config dicts. This module has no
imports and must remain a leaf dependency to avoid circular imports.
"""

DEFAULT_FREQ_HZ: float = 28e9
DEFAULT_POWER_DBM: float = 60.0
DEFAULT_P_ABS_MAX: float = 0.1         # absorbed power limit [W]
DEFAULT_NOISE_POWER: float = 0.01      # MMSE noise power
DEFAULT_FIDELITY_LEVEL: int = 2
DEFAULT_MAX_BOUNCES: int = 3
DEFAULT_SEED: int = 42

NUMERICAL_FLOOR: float = 1e-30         # safe-division guard

CONCRETE_EPS_R: float = 5.31           # material fallback
CONCRETE_SIGMA: float = 0.0326
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_defaults.py -v`
Expected: PASS

- [ ] **Step 5: Lint**

Run: `python -m ruff check src/aegis/defaults.py tests/test_defaults.py && python -m ruff format --check src/aegis/defaults.py tests/test_defaults.py`

- [ ] **Step 6: Commit**

```bash
git add src/aegis/defaults.py tests/test_defaults.py
git commit -m "Add defaults.py as single source of truth for project defaults"
```

---

### Task 2: Replace hardcoded values in core engine files

**Files:**
- Modify: `src/aegis/engine.py` (lines 233, 375, 528, 643)
- Modify: `src/aegis/kernels/level8_ecbf.py` (line 35)
- Modify: `src/aegis/kernels/_base.py` (line 57)
- Modify: `src/aegis/coherent/ecbf.py` (lines 92, 140, 169)
- Modify: `src/aegis/coherent/exposure_operator.py` (lines 110, 117)
- Modify: `src/aegis/coherent/body_channel.py` (line 110)
- Modify: `src/aegis/precoder.py` (line 51)
- Modify: `src/aegis/result.py` (line 310)
- Modify: `src/aegis/geometry/occlusion.py` (line 47)

- [ ] **Step 1: Run baseline tests**

Run: `python -m pytest tests/ -m "not slow" -x -q 2>&1 | tail -5`
Record the pass count.

- [ ] **Step 2: Update engine.py**

Add import at top:
```python
from aegis.defaults import DEFAULT_P_ABS_MAX
```
Replace all four `P_abs_max: float = 0.1` and `P_abs_max=0.1` with `P_abs_max: float = DEFAULT_P_ABS_MAX` and `P_abs_max=DEFAULT_P_ABS_MAX` at lines 233, 375, 528, 643.

- [ ] **Step 3: Update kernels/level8_ecbf.py**

Add import at top:
```python
from aegis.defaults import DEFAULT_P_ABS_MAX
```
Line 35: replace `P_abs_max=0.1` with `P_abs_max=DEFAULT_P_ABS_MAX`.

- [ ] **Step 4: Update kernels/_base.py**

Add import at top:
```python
from aegis.defaults import NUMERICAL_FLOOR
```
Line 57: replace `1e-30` with `NUMERICAL_FLOOR` in `sigma_safe = xp.where(sigma > 0, sigma, 1e-30)`.

- [ ] **Step 5: Update coherent/ecbf.py**

Add import at top:
```python
from aegis.defaults import NUMERICAL_FLOOR
```
Replace `1e-30` at lines 92, 140, 169 with `NUMERICAL_FLOOR`.

- [ ] **Step 6: Update coherent/exposure_operator.py**

Add import at top:
```python
from aegis.defaults import NUMERICAL_FLOOR
```
Replace `1e-30` at lines 110, 117 with `NUMERICAL_FLOOR`.

- [ ] **Step 7: Update coherent/body_channel.py**

Add import at top:
```python
from aegis.defaults import NUMERICAL_FLOOR
```
Line 110: replace `1e-30` with `NUMERICAL_FLOOR`.

- [ ] **Step 8: Update precoder.py**

Add import at top:
```python
from aegis.defaults import NUMERICAL_FLOOR
```
Line 51: replace `1e-30` with `NUMERICAL_FLOOR`.

- [ ] **Step 9: Update result.py**

Add import at top:
```python
from aegis.defaults import NUMERICAL_FLOOR
```
Line 310: replace `1e-30` with `NUMERICAL_FLOOR`.

- [ ] **Step 10: Update geometry/occlusion.py**

Add import at top:
```python
from aegis.defaults import NUMERICAL_FLOOR
```
Line 47: replace `1e-30` with `NUMERICAL_FLOOR` in `eps: float = 1e-30`.

- [ ] **Step 11: Lint and test**

Run: `python -m ruff check src/aegis/engine.py src/aegis/kernels/ src/aegis/coherent/ src/aegis/precoder.py src/aegis/result.py src/aegis/geometry/occlusion.py && python -m ruff format --check src/aegis/engine.py src/aegis/kernels/ src/aegis/coherent/ src/aegis/precoder.py src/aegis/result.py src/aegis/geometry/occlusion.py`

Run: `python -m pytest tests/ -m "not slow" -x -q 2>&1 | tail -5`
Expected: Same pass count as baseline.

- [ ] **Step 12: Commit**

```bash
git add src/aegis/engine.py src/aegis/kernels/level8_ecbf.py src/aegis/kernels/_base.py src/aegis/coherent/ecbf.py src/aegis/coherent/exposure_operator.py src/aegis/coherent/body_channel.py src/aegis/precoder.py src/aegis/result.py src/aegis/geometry/occlusion.py
git commit -m "Replace hardcoded defaults in core engine with imports from defaults.py"
```

---

### Task 3: Replace hardcoded values in MIMO files

**Files:**
- Modify: `src/aegis/mimo/compute.py` (lines 229, 230, 442)
- Modify: `src/aegis/mimo/precoders.py` (lines 27, 57, 62, 72, 98, 109, 120)
- Modify: `src/aegis/mimo/scene.py` (line 36)

- [ ] **Step 1: Update mimo/compute.py**

Add import at top:
```python
from aegis.defaults import DEFAULT_NOISE_POWER, DEFAULT_P_ABS_MAX
```
Line 229: replace `noise_power: float = 0.01` with `noise_power: float = DEFAULT_NOISE_POWER`.
Line 230: replace `P_abs_max: float = 0.1` with `P_abs_max: float = DEFAULT_P_ABS_MAX`.
Line 442: replace `P_abs_max=0.1` with `P_abs_max=DEFAULT_P_ABS_MAX`.

- [ ] **Step 2: Update mimo/precoders.py**

Add import at top:
```python
from aegis.defaults import DEFAULT_NOISE_POWER, NUMERICAL_FLOOR
```
Replace all `1e-30` occurrences (lines 27, 57, 72, 98, 109) with `NUMERICAL_FLOOR`.
Line 62: replace `noise_power: float = 0.01` with `noise_power: float = DEFAULT_NOISE_POWER`.
Line 120: replace `noise_power: float = 0.01` with `noise_power: float = DEFAULT_NOISE_POWER`.

- [ ] **Step 3: Update mimo/scene.py**

Add import at top:
```python
from aegis.defaults import DEFAULT_FREQ_HZ
```
Line 36: replace `freq_hz: float = 28e9` with `freq_hz: float = DEFAULT_FREQ_HZ`.

- [ ] **Step 4: Lint and test**

Run: `python -m ruff check src/aegis/mimo/ && python -m ruff format --check src/aegis/mimo/`
Run: `python -m pytest tests/ -m "not slow" -x -q 2>&1 | tail -5`
Expected: Same pass count.

- [ ] **Step 5: Commit**

```bash
git add src/aegis/mimo/
git commit -m "Replace hardcoded defaults in MIMO module with imports from defaults.py"
```

---

### Task 4: Replace hardcoded values in integration and channel files

**Files:**
- Modify: `src/aegis/integration/differt.py` (lines 238, 475, 556, 562, 576)
- Modify: `src/aegis/integration/sionna.py` (lines 144, 157)
- Modify: `src/aegis/modal_rt/differt_tracer.py` (lines 33, 34)
- Modify: `src/aegis/modal_rt/sionna_tracer.py` (lines 33, 34, 108, 109)
- Modify: `src/aegis/channel/generator.py` (lines 46, 235, 239)
- Modify: `src/aegis/channel/presets.py` (line 92)

- [ ] **Step 1: Update integration/differt.py**

Add import at top:
```python
from aegis.defaults import CONCRETE_EPS_R, CONCRETE_SIGMA, DEFAULT_POWER_DBM
```
Lines 238, 475: replace `tx_power_dbm: float = 60.0` with `tx_power_dbm: float = DEFAULT_POWER_DBM`.
Lines 556, 562, 576: replace `5.31` with `CONCRETE_EPS_R` and `0.0326` with `CONCRETE_SIGMA`.

- [ ] **Step 2: Update integration/sionna.py**

Add import at top:
```python
from aegis.defaults import DEFAULT_POWER_DBM, DEFAULT_SEED
```
Line 144: replace `tx_power_dbm: float = 60.0` with `tx_power_dbm: float = DEFAULT_POWER_DBM`.
Line 157: replace `seed: int = 42` with `seed: int = DEFAULT_SEED`.

- [ ] **Step 3: Update modal_rt/differt_tracer.py**

Add import at top:
```python
from aegis.defaults import DEFAULT_FREQ_HZ, DEFAULT_POWER_DBM
```
Line 33: replace `freq_hz: float = 28e9` with `freq_hz: float = DEFAULT_FREQ_HZ`.
Line 34: replace `tx_power_dbm: float = 60.0` with `tx_power_dbm: float = DEFAULT_POWER_DBM`.

- [ ] **Step 4: Update modal_rt/sionna_tracer.py**

Add import at top:
```python
from aegis.defaults import DEFAULT_FREQ_HZ, DEFAULT_POWER_DBM
```
Lines 33, 108: replace `freq_hz: float = 28e9` with `freq_hz: float = DEFAULT_FREQ_HZ`.
Lines 34, 109: replace `tx_power_dbm: float = 60.0` with `tx_power_dbm: float = DEFAULT_POWER_DBM`.

- [ ] **Step 5: Update channel/generator.py**

Add import at top:
```python
from aegis.defaults import DEFAULT_SEED, NUMERICAL_FLOOR
```
Line 46: replace `seed: int = 42` with `seed: int = DEFAULT_SEED`.
Lines 235, 239: replace `1e-30` with `NUMERICAL_FLOOR`.

- [ ] **Step 6: Update channel/presets.py**

Add import at top:
```python
from aegis.defaults import DEFAULT_FREQ_HZ
```
Line 92: replace `freq_ghz: float = 28.0` with `freq_ghz: float = DEFAULT_FREQ_HZ / 1e9`.

- [ ] **Step 7: Lint and test**

Run: `python -m ruff check src/aegis/integration/ src/aegis/modal_rt/ src/aegis/channel/ && python -m ruff format --check src/aegis/integration/ src/aegis/modal_rt/ src/aegis/channel/`
Run: `python -m pytest tests/ -m "not slow" -x -q 2>&1 | tail -5`
Expected: Same pass count.

- [ ] **Step 8: Commit**

```bash
git add src/aegis/integration/ src/aegis/modal_rt/ src/aegis/channel/
git commit -m "Replace hardcoded defaults in integration and channel modules"
```

---

### Task 5: Replace hardcoded values in viewer backend and remaining files

**Files:**
- Modify: `src/aegis/config.py` (lines 22, 42)
- Modify: `src/aegis/compliance/__init__.py` (line 194)
- Modify: `src/aegis/viz/dashboard.py` (lines 80, 113, 162)
- Modify: `src/aegis/viewer/compute.py` (lines 235, 268)
- Modify: `src/aegis/viewer/raytracer.py` (lines 145, 146)
- Modify: `src/aegis/viewer/modal_proxy.py` (lines 90-91, 125-126, 155-156)
- Modify: `src/aegis/viewer/routes/compute.py` (lines 61, 419, 622, 780, 922)
- Modify: `src/aegis/viewer/routes/mimo.py` (line 32)

- [ ] **Step 1: Update config.py**

Add import at top:
```python
from aegis.defaults import DEFAULT_FREQ_HZ, DEFAULT_POWER_DBM
```
Line 22: replace `frequency_hz: float = 28e9` with `frequency_hz: float = DEFAULT_FREQ_HZ`.
Line 42: replace `power_dbm: float = 60.0` with `power_dbm: float = DEFAULT_POWER_DBM`.

- [ ] **Step 2: Update compliance/__init__.py**

Add import at top:
```python
from aegis.defaults import DEFAULT_FREQ_HZ
```
Line 194: replace `freq_hz: float = 28.0e9` with `freq_hz: float = DEFAULT_FREQ_HZ`.

- [ ] **Step 3: Update viz/dashboard.py**

Add import at top:
```python
from aegis.defaults import DEFAULT_FREQ_HZ, NUMERICAL_FLOOR
```
Lines 80, 113: replace `28.0e9` with `DEFAULT_FREQ_HZ`.
Line 162: replace `1e-30` with `NUMERICAL_FLOOR`.

- [ ] **Step 4: Update viewer/config.py DEFAULTS literals**

The DEFAULTS dict in `viewer/config.py` also contains hardcoded values. These cannot be replaced with Python imports directly since they are inside a dict literal, but you can define them using the imported constants:

At the top of `viewer/config.py`, add:
```python
from aegis.defaults import DEFAULT_FIDELITY_LEVEL, DEFAULT_FREQ_HZ, DEFAULT_POWER_DBM
```

Line 173: replace `"default_power_dbm": 60` with `"default_power_dbm": DEFAULT_POWER_DBM`.
Line 176: replace `"freq_hz": 28.0e9` with `"freq_hz": DEFAULT_FREQ_HZ`.
Line 172: replace `"default_level": 2` with `"default_level": DEFAULT_FIDELITY_LEVEL`.

- [ ] **Step 5: Update viewer/compute.py**

Add import at top:
```python
from aegis.defaults import DEFAULT_FREQ_HZ, DEFAULT_POWER_DBM
```
Line 235: replace `power_dbm: float = 60.0` with `power_dbm: float = DEFAULT_POWER_DBM`.
Line 268: replace `28e9` with `DEFAULT_FREQ_HZ` in the `resolve_skin_model` call.

- [ ] **Step 5: Update viewer/raytracer.py**

Add import at top:
```python
from aegis.defaults import DEFAULT_FREQ_HZ, DEFAULT_POWER_DBM
```
Line 145: replace `freq_hz: float = 28e9` with `freq_hz: float = DEFAULT_FREQ_HZ`.
Line 146: replace `tx_power_dbm: float = 60.0` with `tx_power_dbm: float = DEFAULT_POWER_DBM`.

- [ ] **Step 6: Update viewer/modal_proxy.py**

Add import at top:
```python
from aegis.defaults import DEFAULT_FREQ_HZ, DEFAULT_POWER_DBM
```
Lines 90, 125, 155: replace `freq_hz: float = 28e9` with `freq_hz: float = DEFAULT_FREQ_HZ`.
Lines 91, 126, 156: replace `tx_power_dbm: float = 60.0` with `tx_power_dbm: float = DEFAULT_POWER_DBM`.

- [ ] **Step 7: Update viewer/routes/compute.py**

Add import at top:
```python
from aegis.defaults import DEFAULT_FREQ_HZ, DEFAULT_POWER_DBM
```
Line 61: replace `default_freq: float = 28e9` with `default_freq: float = DEFAULT_FREQ_HZ`.
Line 419: replace `28e9` with `DEFAULT_FREQ_HZ`.
Lines 622, 780, 922: replace `60.0` with `DEFAULT_POWER_DBM`.

- [ ] **Step 8: Update viewer/routes/mimo.py**

Add import at top:
```python
from aegis.defaults import DEFAULT_FREQ_HZ
```
Line 32: replace `28e9` with `DEFAULT_FREQ_HZ`.

- [ ] **Step 9: Lint and test**

Run: `python -m ruff check src/aegis/config.py src/aegis/compliance/ src/aegis/viz/ src/aegis/viewer/ && python -m ruff format --check src/aegis/config.py src/aegis/compliance/ src/aegis/viz/ src/aegis/viewer/`
Run: `python -m pytest tests/ -m "not slow" -x -q 2>&1 | tail -5`
Expected: Same pass count.

- [ ] **Step 10: Commit**

```bash
git add src/aegis/config.py src/aegis/compliance/__init__.py src/aegis/viz/dashboard.py src/aegis/viewer/compute.py src/aegis/viewer/raytracer.py src/aegis/viewer/modal_proxy.py src/aegis/viewer/routes/compute.py src/aegis/viewer/routes/mimo.py
git commit -m "Replace hardcoded defaults in viewer, compliance, and viz modules"
```

---

### Task 6: Create phantoms.yaml and update viewer/compute.py

**Files:**
- Create: `data/phantoms.yaml`
- Modify: `src/aegis/viewer/compute.py` (lines 19-24)

- [ ] **Step 1: Create data/phantoms.yaml**

```yaml
thelonious:
  mass_kg: 17.4
duke:
  mass_kg: 72.4
eartha:
  mass_kg: 56.0
ella:
  mass_kg: 58.7
```

- [ ] **Step 2: Update viewer/compute.py**

Replace the hardcoded `PHANTOM_MASS_KG` dict (lines 19-24) with a loader:

```python
import functools
from pathlib import Path
import yaml

@functools.lru_cache(maxsize=1)
def _load_phantom_masses() -> dict[str, float]:
    """Load phantom masses from data/phantoms.yaml (cached)."""
    data_dir = Path(os.environ.get("AEGIS_DATA_DIR", Path(__file__).resolve().parents[3] / "data"))
    path = data_dir / "phantoms.yaml"
    if not path.exists():
        # Fallback for environments without the data file
        return {"thelonious": 17.4, "duke": 72.4, "eartha": 56.0, "ella": 58.7}
    with open(path) as f:
        data = yaml.safe_load(f)
    return {name: info["mass_kg"] for name, info in data.items()}
```

Update all references from `PHANTOM_MASS_KG[name]` to `_load_phantom_masses()[name]` or `_load_phantom_masses().get(name)`.

- [ ] **Step 3: Lint and test**

Run: `python -m ruff check src/aegis/viewer/compute.py && python -m ruff format --check src/aegis/viewer/compute.py`
Run: `python -m pytest tests/ -m "not slow" -x -q 2>&1 | tail -5`

- [ ] **Step 4: Commit**

```bash
git add data/phantoms.yaml src/aegis/viewer/compute.py
git commit -m "Move phantom masses to data/phantoms.yaml"
```

---

### Task 7: Fix config drift in viewer/config.py

**Files:**
- Modify: `src/aegis/viewer/config.py` (lines 88, 195, 196, 222)

- [ ] **Step 1: Write verification test**

```python
# tests/test_config_drift.py
"""Verify DEFAULTS and default.json produce identical merged config."""
import json
from pathlib import Path
from aegis.viewer.config import load_config, DEFAULTS
import copy


def test_defaults_match_merged():
    """load_config(None) should equal load_config('configs/default.json')."""
    bare = load_config(None)
    merged = load_config(Path("configs/default.json"))
    assert bare == merged, f"Drift detected: {_find_diffs(bare, merged)}"


def _find_diffs(a, b, path=""):
    diffs = []
    for key in set(list(a.keys()) + list(b.keys())):
        p = f"{path}.{key}" if path else key
        if key not in a:
            diffs.append(f"{p}: missing from DEFAULTS")
        elif key not in b:
            diffs.append(f"{p}: missing from JSON")
        elif isinstance(a[key], dict) and isinstance(b[key], dict):
            diffs.extend(_find_diffs(a[key], b[key], p))
        elif a[key] != b[key]:
            diffs.append(f"{p}: DEFAULTS={a[key]!r} vs merged={b[key]!r}")
    return diffs
```

- [ ] **Step 2: Run test to see current drift**

Run: `python -m pytest tests/test_config_drift.py -v`
Expected: FAIL listing the 4 known drifts + 2 missing keys.

- [ ] **Step 3: Fix DEFAULTS**

In `src/aegis/viewer/config.py`:
- Line 88: change `"size_scale": 0.99` to `"size_scale": 0.95`
- Line 195: change `"min": -30` to `"min": 0`
- Line 196: change `"max": 80` to `"max": 60`
- Line 222: change `"convex_body_area_factor": 1.0` to `"convex_body_area_factor": 0.25`
- Add `"compliance_threshold": 10.0` to the dosimetry section
- Add `"max_order_options"` array (3 entries matching default.json lines 255-268) to dosimetry section

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_config_drift.py -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `python -m pytest tests/ -m "not slow" -x -q 2>&1 | tail -5`
Expected: Same pass count.

- [ ] **Step 6: Commit**

```bash
git add src/aegis/viewer/config.py tests/test_config_drift.py
git commit -m "Fix config drift between viewer DEFAULTS and default.json"
```

---

### Task 8: Expand SimulationConfig

**Files:**
- Modify: `src/aegis/config.py`
- Modify: `tests/test_config.py` (or create if missing)

- [ ] **Step 1: Check for existing config tests**

Run: `find tests/ -name '*config*' -o -name '*simulation*' | head -10`

- [ ] **Step 2: Write tests for new dataclasses**

```python
# tests/test_config.py (append or create)
from aegis.config import (
    ChannelConfig, DosimetryConfig, MIMOConfig, SimulationConfig,
)
from aegis.defaults import DEFAULT_P_ABS_MAX, DEFAULT_SEED, DEFAULT_NOISE_POWER
import tempfile
from pathlib import Path


def test_channel_config_defaults():
    c = ChannelConfig()
    assert c.preset == "3GPP_38.901_UMi_LOS"
    assert c.seed == DEFAULT_SEED
    assert c.overrides == {}


def test_mimo_config_defaults():
    m = MIMOConfig()
    assert m.precoder == "mrt"
    assert m.noise_power == DEFAULT_NOISE_POWER
    assert m.n_rows == 4


def test_dosimetry_config_expanded():
    d = DosimetryConfig()
    assert d.n_paths == 1
    assert d.max_order == 0
    assert d.p_abs_max == DEFAULT_P_ABS_MAX


def test_simulation_config_backwards_compat():
    """Old YAML without channel/mimo sections still loads."""
    old_yaml = {
        "tissue": {"name": "Skin", "frequency_hz": 28e9},
        "body": {"name": "thelonious"},
        "antenna": {"positions": [[5, 0, 1]], "power_dbm": 60},
        "raytracer": {"backend": "differt", "max_bounces": 3},
        "dosimetry": {"level": 2, "spatial_averaging": False},
        "output_dir": "outputs",
    }
    cfg = SimulationConfig.from_dict(old_yaml)
    assert cfg.channel.preset == "3GPP_38.901_UMi_LOS"
    assert cfg.mimo.precoder == "mrt"


def test_simulation_config_roundtrip():
    cfg = SimulationConfig()
    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
        cfg.to_yaml(f.name)
        loaded = SimulationConfig.from_yaml(f.name)
    assert cfg == loaded
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL (ChannelConfig and MIMOConfig don't exist yet)

- [ ] **Step 4: Implement the changes in config.py**

Add imports at top:
```python
from aegis.defaults import (
    DEFAULT_FREQ_HZ, DEFAULT_MAX_BOUNCES, DEFAULT_NOISE_POWER,
    DEFAULT_P_ABS_MAX, DEFAULT_POWER_DBM, DEFAULT_SEED,
    DEFAULT_FIDELITY_LEVEL,
)
```

Update existing dataclasses to use imported defaults. Add new dataclasses:

```python
@dataclass(frozen=True)
class ChannelConfig:
    """Stochastic channel model parameters."""
    preset: str = "3GPP_38.901_UMi_LOS"
    seed: int = DEFAULT_SEED
    overrides: dict = field(default_factory=dict)


@dataclass(frozen=True)
class MIMOConfig:
    """MIMO array and precoder parameters."""
    precoder: str = "mrt"
    noise_power: float = DEFAULT_NOISE_POWER
    n_rows: int = 4
    n_cols: int = 4
```

Expand DosimetryConfig:
```python
@dataclass(frozen=True)
class DosimetryConfig:
    level: int = DEFAULT_FIDELITY_LEVEL
    spatial_averaging: bool = False
    n_paths: int = 1
    max_order: int = 0
    p_abs_max: float = DEFAULT_P_ABS_MAX
```

Update SimulationConfig to include new fields with default factories:
```python
channel: ChannelConfig = field(default_factory=ChannelConfig)
mimo: MIMOConfig = field(default_factory=MIMOConfig)
```

Update `_CONFIG_CLASSES`:
```python
_CONFIG_CLASSES: dict[str, type] = {
    "tissue": TissueConfig,
    "body": BodyConfig,
    "antenna": AntennaConfig,
    "raytracer": RayTracerConfig,
    "dosimetry": DosimetryConfig,
    "channel": ChannelConfig,
    "mimo": MIMOConfig,
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 6: Full test suite**

Run: `python -m pytest tests/ -m "not slow" -x -q 2>&1 | tail -5`
Expected: Same pass count.

- [ ] **Step 7: Lint and commit**

```bash
python -m ruff check src/aegis/config.py tests/test_config.py && python -m ruff format --check src/aegis/config.py tests/test_config.py
git add src/aegis/config.py tests/test_config.py
git commit -m "Expand SimulationConfig with ChannelConfig, MIMOConfig, and DosimetryConfig fields"
```

---

### Task 9: Add round-trip DEFAULTS keys to viewer config

**Depends on:** Task 7 (both modify `viewer/config.py` DEFAULTS)

**Files:**
- Modify: `src/aegis/viewer/config.py` (DEFAULTS dict)
- Modify: `aegis-web/src/hooks/useConfig.ts`

- [ ] **Step 1: Add new keys to DEFAULTS dict in viewer/config.py**

Add these keys in the appropriate sections of the DEFAULTS dict:

In the `"antenna"` section:
```python
"default_position": None,
```

In the `"dosimetry"` section:
```python
"skin_model": "itis",
"dynamic_range_db": 30,
```

In the `"body"` section:
```python
"default_offset": [0, 0, 0],
"default_rotation_y": 0,
"wireframe": False,
```

In the `"raytracer"` section:
```python
"default_source": "differt",
```

- [ ] **Step 2: Update useConfig.ts to read new keys**

In `aegis-web/src/hooks/useConfig.ts`, after the existing config reads, add. Note: you may need to obtain `const scene = useSceneStore.getState()` and `const ui = useUIStore.getState()` if they are not already available in scope:

```typescript
// Read new round-trip config keys
const antennaPos = cfg.antenna?.default_position ?? null
if (antennaPos) sim.setAntennaPos(antennaPos)

const skinModel = cfg.dosimetry?.skin_model
if (skinModel) sim.setSkinModel(skinModel)

const dynamicRangeDb = cfg.dosimetry?.dynamic_range_db
if (dynamicRangeDb !== undefined) ui.setDynamicRangeDb(dynamicRangeDb)

const bodyOffset = cfg.body?.default_offset
if (bodyOffset) sim.setBodyOffset(bodyOffset)

const bodyRotationY = cfg.body?.default_rotation_y
if (bodyRotationY !== undefined) sim.setBodyRotationY(bodyRotationY)

const wireframe = cfg.body?.wireframe
if (wireframe !== undefined && wireframe !== ui.wireframe) ui.toggleWireframe()

const rtSource = cfg.raytracer?.default_source
if (rtSource) scene.setRtSource(rtSource)

const maxOrder = cfg.dosimetry?.max_order
if (maxOrder !== undefined) scene.setRtMaxOrder(maxOrder)
```

- [ ] **Step 3: Verify config drift test still passes**

Run: `python -m pytest tests/test_config_drift.py -v`
Expected: PASS (new keys exist in DEFAULTS but not in default.json, so load_config(None) has them and merged also has them since they're not overridden)

Wait: this will FAIL because `load_config(None)` now has extra keys that `load_config("configs/default.json")` also has (from DEFAULTS). But both will have the same values since default.json doesn't override them. Actually it should PASS because deep-merge preserves DEFAULTS keys that JSON doesn't override.

- [ ] **Step 4: Build frontend**

Run: `cd aegis-web && npm run build`
Expected: Build succeeds with no TS errors.

- [ ] **Step 5: Commit**

```bash
git add src/aegis/viewer/config.py aegis-web/src/hooks/useConfig.ts
git commit -m "Add round-trip config keys for viewer export"
```

---

### Task 10: Add export-config backend endpoint

**Files:**
- Modify: `src/aegis/viewer/routes/data.py`

- [ ] **Step 1: Read current data.py to find imports and cache_lock usage**

Read `src/aegis/viewer/routes/data.py` to understand the existing pattern for `cache`, `cache_lock`, and imports. Note: `data.py` uses a `register(app, cache, cache_lock)` closure pattern. All route functions must be defined INSIDE the `register()` function body, not at module level.

- [ ] **Step 2: Add the endpoint inside the register() function**

Add to `src/aegis/viewer/routes/data.py` inside the `register()` function, after the existing `api_viewer_config` endpoint. Make sure `copy` is imported at the module level:

```python
@app.route("/api/export-config", methods=["POST"])
def api_export_config():
    """Return the full viewer config with interactive state overlaid."""
    with cache_lock:
        base = copy.deepcopy(cache["config"])
    interactive = request.get_json(silent=True) or {}

    # Map interactive state (camelCase) to config paths
    if "freqGhz" in interactive:
        base["dosimetry"]["freq_hz"] = interactive["freqGhz"] * 1e9
    if "powerDbm" in interactive:
        base["dosimetry"]["default_power_dbm"] = interactive["powerDbm"]
    if "nPaths" in interactive:
        base["dosimetry"]["default_n_paths"] = interactive["nPaths"]
    if "bodyName" in interactive:
        base["body"]["default_name"] = interactive["bodyName"]
    if "antennaPos" in interactive and interactive["antennaPos"]:
        base["antenna"]["default_position"] = interactive["antennaPos"]
    if "skinModel" in interactive:
        base["dosimetry"]["skin_model"] = interactive["skinModel"]
    if "bodyOffset" in interactive:
        base["body"]["default_offset"] = interactive["bodyOffset"]
    if "bodyRotationY" in interactive:
        base["body"]["default_rotation_y"] = interactive["bodyRotationY"]
    if "wireframe" in interactive:
        base["body"]["wireframe"] = interactive["wireframe"]

    # Fidelity level from mode + toggles
    if "mode" in interactive:
        mode = interactive["mode"]
        if mode == "bound":
            base["dosimetry"]["default_level"] = 0
        elif mode == "aggregate":
            base["dosimetry"]["default_level"] = 1
        else:
            level = 2
            if interactive.get("fresnel"):
                level = 3
            if interactive.get("polarisation"):
                level = 4
            if interactive.get("curvature"):
                level = 5
            if interactive.get("diffraction"):
                level = 6
            base["dosimetry"]["default_level"] = level

    # RT config
    if "rtSource" in interactive:
        base["raytracer"]["default_source"] = interactive["rtSource"]
    if "rtMaxOrder" in interactive:
        base["dosimetry"]["default_max_order"] = interactive["rtMaxOrder"]
    if "rtConfig" in interactive:
        base["raytracer"].update(interactive["rtConfig"])

    # Stochastic channel
    if "stochasticPreset" in interactive:
        base["dosimetry"]["stochastic"]["default_preset"] = interactive["stochasticPreset"]
    if "stochasticSeed" in interactive:
        base["dosimetry"]["stochastic"]["default_seed"] = interactive["stochasticSeed"]

    # Display
    if "exposureScenario" in interactive:
        base["dosimetry"]["exposure_scenario"] = interactive["exposureScenario"]
    if "legendScale" in interactive:
        base["dosimetry"]["display_mode"] = interactive["legendScale"]
    if "dynamicRangeDb" in interactive:
        base["dosimetry"]["dynamic_range_db"] = interactive["dynamicRangeDb"]

    return jsonify(base)
```

Make sure `copy` is imported at the top of the file.

- [ ] **Step 3: Lint**

Run: `python -m ruff check src/aegis/viewer/routes/data.py && python -m ruff format --check src/aegis/viewer/routes/data.py`

- [ ] **Step 4: Commit**

```bash
git add src/aegis/viewer/routes/data.py
git commit -m "Add POST /api/export-config endpoint for viewer config export"
```

---

### Task 11: Add Export Configuration button to frontend

**Files:**
- Modify: `aegis-web/src/api/client.ts`
- Modify: `aegis-web/src/components/panels/ExportPanel.tsx`
- Modify: `aegis-web/src/lib/shareLink.ts` (export collectState)

- [ ] **Step 1: Export collectState from shareLink.ts**

The `collectState()` function in `shareLink.ts` is currently module-private. Add `export` to its declaration:

```typescript
export function collectState(): Record<string, unknown> {
```

- [ ] **Step 2: Add exportConfig to client.ts**

Add to `aegis-web/src/api/client.ts`:

Use the existing `postJson` helper in client.ts:

```typescript
export function exportConfig(state: Record<string, unknown>): Promise<Record<string, unknown>> {
  return postJson<Record<string, unknown>>('/api/export-config', state)
}
```

- [ ] **Step 3: Add Export Configuration button to ExportPanel.tsx**

Add import at top:
```typescript
import { collectState } from '../../lib/shareLink'
import { exportConfig } from '../../api/client'
```

Add a new handler and button alongside the existing export buttons. The handler:

```typescript
async function handleExportConfig() {
  try {
    const state = collectState()
    const config = await exportConfig(state)
    const json = JSON.stringify(config, null, 2)
    const blob = new Blob([json], { type: 'application/json' })
    downloadBlob(blob, `aegis-config-${new Date().toISOString().slice(0, 10)}.json`)
  } catch (err) {
    console.error('Config export failed:', err)
  }
}
```

Add a button in the export panel UI, using the same styling pattern as existing buttons:
```tsx
<button onClick={handleExportConfig}>
  Export configuration
</button>
```

- [ ] **Step 4: Build frontend**

Run: `cd aegis-web && npm run build`
Expected: Build succeeds.

- [ ] **Step 5: Commit**

```bash
git add aegis-web/src/lib/shareLink.ts aegis-web/src/api/client.ts aegis-web/src/components/panels/ExportPanel.tsx
git commit -m "Add Export Configuration button to viewer"
```

---

### Task 12: Add pako and compress share URLs

**Files:**
- Modify: `aegis-web/package.json`
- Modify: `aegis-web/src/lib/shareLink.ts`

- [ ] **Step 1: Install pako**

Run: `cd aegis-web && npm install pako && npm install -D @types/pako`

- [ ] **Step 2: Update shareLink.ts encoding**

Replace the `serializeShareableState` function and add helpers:

```typescript
import pako from 'pako'

function toBase64Url(bytes: Uint8Array): string {
  let binary = ''
  for (const b of bytes) binary += String.fromCharCode(b)
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

function fromBase64Url(str: string): Uint8Array {
  const padded = str.replace(/-/g, '+').replace(/_/g, '/') +
    '='.repeat((4 - str.length % 4) % 4)
  const binary = atob(padded)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
  return bytes
}

export function serializeShareableState(): string {
  const current = collectState()
  const diff = diffState(current)
  const json = JSON.stringify(diff)
  const compressed = pako.deflateRaw(new TextEncoder().encode(json))
  return toBase64Url(compressed)
}
```

- [ ] **Step 3: Update deserializeShareLink with backwards compat**

Replace the `deserializeShareLink` function:

```typescript
export function deserializeShareLink(encoded: string): Partial<ShareState> {
  try {
    let json: string
    try {
      // New format: deflated + base64url
      const bytes = fromBase64Url(encoded)
      json = new TextDecoder().decode(pako.inflateRaw(bytes))
    } catch {
      // Backwards compat: old plain base64 format
      json = atob(encoded)
    }
    const parsed = JSON.parse(json) as Record<string, unknown>
    const result: Record<string, unknown> = {}
    for (const key of Object.keys(SHARE_DEFAULTS)) {
      if (key in parsed) result[key] = parsed[key]
    }
    return result as Partial<ShareState>
  } catch {
    console.warn('Failed to parse share link')
    return {}
  }
}
```

- [ ] **Step 4: Build frontend**

Run: `cd aegis-web && npm run build`
Expected: Build succeeds.

- [ ] **Step 5: Commit**

```bash
git add aegis-web/package.json aegis-web/package-lock.json aegis-web/src/lib/shareLink.ts
git commit -m "Compress share URLs with deflate + base64url via pako"
```

---

### Task 13: Expand share state vocabulary

**Depends on:** Task 12 (both modify `shareLink.ts`)

**Files:**
- Modify: `aegis-web/src/lib/shareDefaults.ts`
- Modify: `aegis-web/src/lib/shareLink.ts`
- Modify: `aegis-web/src/stores/scene.ts`

- [ ] **Step 1: Add display state to scene store**

In `aegis-web/src/stores/scene.ts`, add properties and setters:

```typescript
// In the store state type:
colormapName: string
sunIntensity: number
ambientIntensity: number
cameraFov: number

// In the store defaults:
colormapName: 'inferno',
sunIntensity: 1.2,
ambientIntensity: 0.6,
cameraFov: 55,

// Setters:
setColormapName: (name: string) => set({ colormapName: name }),
setSunIntensity: (v: number) => set({ sunIntensity: v }),
setAmbientIntensity: (v: number) => set({ ambientIntensity: v }),
setCameraFov: (v: number) => set({ cameraFov: v }),
```

These values should be initialized from viewerConfig in useConfig.ts. Note: `useConfig.ts` accesses scene store via `useSceneStore.getState()` - make sure to obtain it if not already available:
```typescript
const scene = useSceneStore.getState()
scene.setColormapName(cfg.colormap?.name ?? 'inferno')
scene.setSunIntensity(cfg.lighting?.sun?.intensity ?? 1.2)
scene.setAmbientIntensity(cfg.lighting?.ambient?.intensity ?? 0.6)
scene.setCameraFov(cfg.camera?.fov ?? 55)
```

- [ ] **Step 2: Add new fields to SHARE_DEFAULTS**

In `aegis-web/src/lib/shareDefaults.ts`:

```typescript
// Add after existing fields:
colormapName: 'inferno' as string,
sunIntensity: 1.2,
ambientIntensity: 0.6,
cameraFov: 55,
```

- [ ] **Step 3: Add collection and application in shareLink.ts**

In `collectState()`, add:
```typescript
// display state from scene store
colormapName: scene.colormapName,
sunIntensity: scene.sunIntensity,
ambientIntensity: scene.ambientIntensity,
cameraFov: scene.cameraFov,
```

In `applyShareState()`, add:
```typescript
if (state.colormapName !== undefined) scene.setColormapName(state.colormapName)
if (state.sunIntensity !== undefined) scene.setSunIntensity(state.sunIntensity)
if (state.ambientIntensity !== undefined) scene.setAmbientIntensity(state.ambientIntensity)
if (state.cameraFov !== undefined) scene.setCameraFov(state.cameraFov)
```

- [ ] **Step 4: Build frontend**

Run: `cd aegis-web && npm run build`
Expected: Build succeeds.

- [ ] **Step 5: Commit**

```bash
git add aegis-web/src/stores/scene.ts aegis-web/src/lib/shareDefaults.ts aegis-web/src/lib/shareLink.ts aegis-web/src/hooks/useConfig.ts
git commit -m "Expand share state with colormap, lighting, and camera fields"
```

---

### Task 14: Copy built frontend to Flask static and final verification

**Files:**
- No new files

- [ ] **Step 1: Build and copy frontend**

Run: `cd aegis-web && npm run build:copy`
Expected: Build completes and files are copied to `src/aegis/viewer/static/`.

- [ ] **Step 2: Run full backend test suite**

Run: `python -m pytest tests/ -m "not slow" -x -q`
Expected: All tests pass, same count as baseline from Task 2 Step 1 plus the new tests.

- [ ] **Step 3: Lint entire project**

Run: `python -m ruff check src/ tests/ && python -m ruff format --check src/ tests/`
Expected: Clean.

- [ ] **Step 4: Verify no remaining hardcoded 28e9 in function defaults**

Run: `grep -rn "= 28e9\|= 28.0e9\|= 28\.0," src/aegis/ --include="*.py" | grep -v defaults.py | grep -v __pycache__ | grep -v "SKIN_28GHZ\|MUSCLE_28GHZ\|tissue.*28"`

Expected: No hits in function signatures or default parameters. Hits in comments, string literals, or predefined tissue constants (SKIN_28GHZ) are acceptable.

- [ ] **Step 5: Verify no remaining hardcoded P_abs_max=0.1**

Run: `grep -rn "P_abs_max.*= 0.1\|P_abs_max=0.1" src/aegis/ --include="*.py" | grep -v defaults.py | grep -v __pycache__`
Expected: No hits.

- [ ] **Step 6: Push and create PR**

```bash
git push -u origin feature/config-centralization
gh pr create --title "Centralize config defaults and add viewer export" --body "## Summary
- Create defaults.py as single source of truth for all project defaults
- Replace ~60 hardcoded literals across 28 backend files
- Fix config drift between viewer DEFAULTS and default.json
- Move phantom masses to data/phantoms.yaml
- Expand SimulationConfig with ChannelConfig, MIMOConfig fields
- Add POST /api/export-config endpoint and Export Configuration button
- Compress share URLs with deflate + base64url (pako)
- Expand share state vocabulary with display settings

## Test plan
- [ ] All existing tests pass (no behavior change)
- [ ] Config drift test verifies DEFAULTS == merged default.json
- [ ] SimulationConfig roundtrip test (YAML save/load)
- [ ] Export config from viewer, relaunch with exported JSON, verify same state
- [ ] Share URL: generate link, open in new tab, verify state matches
- [ ] Share URL: test old-format link still decodes (backwards compat)
- [ ] Grep for remaining hardcoded defaults (28e9, 0.1, 1e-30, 60.0) in function sigs
" --base master
```
