# Multi-antenna support implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Support multiple independent transmitter antennas in the AEGIS viewer with combined incoherent dosimetry, fixing the pattern-browser visualization-only bug along the way.

**Architecture:** New `useAntennaStore` Zustand store owns antenna CRUD. Backend `compute_dosimetry()` loops over an `antennas` array, computes per-antenna array factor gain and power density, merges paths via `PropagationPaths.concatenate()`, then runs a single `engine.compute()`. Existing `antennaPos`/`powerDbm` on the simulation store become derived getters delegating to the selected antenna, preserving backward compat for 15+ consumer files.

**Tech Stack:** Python (NumPy), TypeScript/React (Zustand, React Three Fiber), Flask REST API.

**Spec:** `docs/superpowers/specs/2026-04-10-multi-antenna-design.md`

---

## File structure

### New files

| File | Purpose |
|------|---------|
| `aegis-web/src/stores/antenna.ts` | AntennaStore: Map of AntennaConfig, selectedId, CRUD actions |
| `aegis-web/src/components/panels/AntennasPanel.tsx` | Antenna list + per-antenna config panel for sidebar |
| `tests/test_array_factor.py` | Unit tests for `array_factor_gain()` |

### Modified files

| File | Change |
|------|--------|
| `src/aegis/viewer/compute.py` | Add `array_factor_gain()`. Refactor `compute_dosimetry()` to accept `antennas` list, loop over them, merge paths. |
| `src/aegis/viewer/routes/compute.py` | Parse `antennas` array in `/api/compute`. Backward compat wrapper for legacy `antenna_pos`. |
| `aegis-web/src/stores/simulation.ts` | `antennaPos` and `powerDbm` become derived getters delegating to antenna store. |
| `aegis-web/src/api/types.ts` | Add `AntennaElementPattern` type (extends `ElementPattern` with `'short_dipole'`). |
| `aegis-web/src/api/client.ts` | Update `ComputeParams` with `antennas` array. Update `computePayload`. |
| `aegis-web/src/hooks/useDosimetry.ts` | Build `antennas` array from antenna store, send to API. |
| `aegis-web/src/hooks/useClickToPlace.ts` | Ctrl+click adds antenna, click moves selected. |
| `aegis-web/src/components/scene/Antenna.tsx` | Accept props for position/config/selected state. |
| `aegis-web/src/components/scene/SceneRoot.tsx` | Map over antenna store, render multiple `<Antenna>` instances. |
| `aegis-web/src/components/panels/ParametersPanel.tsx` | Remove antenna chip and power control. |
| `aegis-web/src/components/layout/Sidebar.tsx` | Add Antennas accordion section. |
| `tests/test_viewer_compute.py` | Add multi-antenna integration tests. |
| `tests/viewer/test_compute_routes.py` | Add route tests for `antennas` param and backward compat. |

---

### Task 1: Backend `array_factor_gain()` utility

**Files:**
- Create: `tests/test_array_factor.py`
- Modify: `src/aegis/viewer/compute.py:1-23` (add import), `src/aegis/viewer/compute.py:348` (add function before `compute_dosimetry`)

This task adds the `array_factor_gain()` function that computes `|AF(k_hat)|^2 * G_element(k_hat)` for a UPA. For a 1x1 array it returns just the element gain. The existing `AntennaArray` class in `src/aegis/mimo/array.py` has `element_gain()` (line 110) and `steering_vector()` (line 134) but those are tied to the MIMO coherent pipeline. We need a standalone power-gain function for the incoherent multi-antenna pipeline.

- [ ] **Step 1: Write failing tests for `array_factor_gain`**

Create `tests/test_array_factor.py`:

```python
"""Tests for array_factor_gain utility."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("flask", reason="Flask not installed (viewer extra)")

from aegis.viewer.compute import array_factor_gain  # noqa: E402


class TestArrayFactorGain:
    """Unit tests for array_factor_gain()."""

    def test_isotropic_1x1_returns_one(self):
        """1x1 isotropic array: gain = 1.0 for any direction."""
        k = np.array([0.0, 0.0, -1.0])
        g = array_factor_gain(
            k_hat=k,
            n_h=1, n_v=1,
            d_h=0.5, d_v=0.5,
            broadside=np.array([0.0, 0.0, -1.0]),
            element_pattern="isotropic",
            freq_hz=28e9,
        )
        assert g == pytest.approx(1.0)

    def test_isotropic_1x1_off_axis_still_one(self):
        """Isotropic element has no angular dependence."""
        k = np.array([1.0, 0.0, 0.0])
        g = array_factor_gain(
            k_hat=k,
            n_h=1, n_v=1,
            d_h=0.5, d_v=0.5,
            broadside=np.array([0.0, 0.0, -1.0]),
            element_pattern="isotropic",
            freq_hz=28e9,
        )
        assert g == pytest.approx(1.0)

    def test_short_dipole_1x1_broadside(self):
        """1x1 short_dipole: G = 1.5 * sin^2(theta).

        For a vertical dipole (broadside=[0,0,-1]) and k_hat=[0,0,-1],
        theta=90 deg (perpendicular to dipole axis which is vertical),
        so sin^2(theta)=1, G=1.5.
        
        But broadside defines the main beam direction, not the dipole axis.
        The dipole axis is perpendicular to broadside. For broadside=[0,0,-1],
        we need to think about what theta means. The element gain for
        short_dipole is 1.5*sin^2(theta) where theta is angle from dipole axis.
        The dipole axis is derived perpendicular to broadside.
        """
        # k_hat along broadside direction: max gain for patch, specific for dipole
        k = np.array([0.0, 0.0, -1.0])
        g = array_factor_gain(
            k_hat=k,
            n_h=1, n_v=1,
            d_h=0.5, d_v=0.5,
            broadside=np.array([0.0, 0.0, -1.0]),
            element_pattern="short_dipole",
            freq_hz=28e9,
        )
        # Short dipole gain: 1.5 * sin^2(theta) where theta is from dipole axis
        # Dipole axis is perpendicular to broadside. k along broadside means
        # theta=90 from dipole axis, so sin^2=1, G=1.5
        assert g == pytest.approx(1.5)

    def test_short_dipole_1x1_along_axis(self):
        """Along dipole axis, gain = 0."""
        # Dipole axis is perpendicular to broadside [0,0,-1].
        # One perpendicular direction is [0,1,0].
        g = array_factor_gain(
            k_hat=np.array([0.0, 1.0, 0.0]),
            n_h=1, n_v=1,
            d_h=0.5, d_v=0.5,
            broadside=np.array([0.0, 0.0, -1.0]),
            element_pattern="short_dipole",
            freq_hz=28e9,
        )
        assert g == pytest.approx(0.0, abs=1e-10)

    def test_patch_1x1_broadside(self):
        """Patch at broadside: cos^q(0) = 1.0."""
        g = array_factor_gain(
            k_hat=np.array([0.0, 0.0, -1.0]),
            n_h=1, n_v=1,
            d_h=0.5, d_v=0.5,
            broadside=np.array([0.0, 0.0, -1.0]),
            element_pattern="patch",
            freq_hz=28e9,
        )
        assert g == pytest.approx(1.0)

    def test_patch_1x1_backside_zero(self):
        """Patch behind the array: cos(theta) < 0, gain = 0."""
        g = array_factor_gain(
            k_hat=np.array([0.0, 0.0, 1.0]),
            n_h=1, n_v=1,
            d_h=0.5, d_v=0.5,
            broadside=np.array([0.0, 0.0, -1.0]),
            element_pattern="patch",
            freq_hz=28e9,
        )
        assert g == pytest.approx(0.0)

    def test_4x4_broadside_gain_equals_N_squared_times_element(self):
        """4x4 UPA at broadside: AF peak = N^2, total = N^2 * G_element.

        At broadside, all elements are in phase. |AF|^2 = (N_h * N_v)^2 = 256.
        With patch element at broadside, G_element = 1.0.
        Total gain = 256.
        """
        g = array_factor_gain(
            k_hat=np.array([0.0, 0.0, -1.0]),
            n_h=4, n_v=4,
            d_h=0.5, d_v=0.5,
            broadside=np.array([0.0, 0.0, -1.0]),
            element_pattern="patch",
            freq_hz=28e9,
        )
        assert g == pytest.approx(256.0, rel=1e-6)

    def test_2x2_isotropic_broadside(self):
        """2x2 isotropic at broadside: |AF|^2 = 16, G_element = 1."""
        g = array_factor_gain(
            k_hat=np.array([0.0, 0.0, -1.0]),
            n_h=2, n_v=2,
            d_h=0.5, d_v=0.5,
            broadside=np.array([0.0, 0.0, -1.0]),
            element_pattern="isotropic",
            freq_hz=28e9,
        )
        assert g == pytest.approx(16.0, rel=1e-6)

    def test_gain_is_always_nonnegative(self):
        """Array factor gain must be >= 0 for random directions."""
        rng = np.random.default_rng(42)
        for _ in range(50):
            k = rng.standard_normal(3)
            k /= np.linalg.norm(k)
            g = array_factor_gain(
                k_hat=k,
                n_h=4, n_v=2,
                d_h=0.5, d_v=0.5,
                broadside=np.array([1.0, 0.0, 0.0]),
                element_pattern="short_dipole",
                freq_hz=28e9,
            )
            assert g >= 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_array_factor.py -v`
Expected: FAIL with `ImportError: cannot import name 'array_factor_gain'`

- [ ] **Step 3: Implement `array_factor_gain()` in `compute.py`**

Add this function before `compute_dosimetry()` (insert at line ~348 of `src/aegis/viewer/compute.py`):

```python
C_0 = 299_792_458.0  # speed of light [m/s]


def array_factor_gain(
    k_hat: np.ndarray,
    n_h: int,
    n_v: int,
    d_h: float,
    d_v: float,
    broadside: np.ndarray,
    element_pattern: str,
    freq_hz: float,
) -> float:
    """Compute |AF|^2 * G_element for a UPA in direction k_hat.

    Parameters
    ----------
    k_hat : (3,) unit direction from antenna toward body.
    n_h, n_v : horizontal and vertical element counts.
    d_h, d_v : element spacings in wavelengths.
    broadside : (3,) unit vector for array normal.
    element_pattern : "isotropic", "patch", or "short_dipole".
    freq_hz : carrier frequency [Hz].

    Returns
    -------
    Power gain (scalar). For 1x1 returns element gain only.
    """
    broadside = np.asarray(broadside, dtype=np.float64)
    broadside = broadside / max(np.linalg.norm(broadside), 1e-12)
    k_hat = np.asarray(k_hat, dtype=np.float64)

    # Element power gain
    if element_pattern == "isotropic":
        g_element = 1.0
    elif element_pattern == "patch":
        cos_theta = float(np.dot(k_hat, broadside))
        g_element = max(cos_theta, 0.0) ** 1.5
    else:  # short_dipole
        # Dipole axis is perpendicular to broadside. Pick a consistent axis.
        abs_b = np.abs(broadside)
        ref = np.zeros(3)
        ref[np.argmin(abs_b)] = 1.0
        dipole_axis = np.cross(broadside, ref)
        dipole_axis /= max(np.linalg.norm(dipole_axis), 1e-12)
        cos_alpha = float(np.dot(k_hat, dipole_axis))
        sin2_alpha = 1.0 - cos_alpha * cos_alpha
        g_element = 1.5 * max(sin2_alpha, 0.0)

    # 1x1 array: no array factor
    if n_h == 1 and n_v == 1:
        return g_element

    # Build element offsets relative to center (in wavelengths)
    lam = C_0 / freq_hz
    k0 = 2.0 * np.pi / lam

    # Two axes perpendicular to broadside
    abs_b = np.abs(broadside)
    ref = np.zeros(3)
    ref[np.argmin(abs_b)] = 1.0
    e_h = np.cross(broadside, ref)
    e_h /= np.linalg.norm(e_h)
    e_v = np.cross(broadside, e_h)

    h_idx = np.arange(n_h) - (n_h - 1) / 2.0
    v_idx = np.arange(n_v) - (n_v - 1) / 2.0
    hh, vv = np.meshgrid(h_idx, v_idx)

    # Physical offsets [m]
    offsets = hh.ravel()[:, None] * (d_h * lam) * e_h + vv.ravel()[:, None] * (d_v * lam) * e_v

    # Array factor: AF = sum_m exp(j * k0 * offset_m . k_hat)
    phases = k0 * (offsets @ k_hat)
    af_complex = np.sum(np.exp(1j * phases))
    af_sq = float(np.abs(af_complex) ** 2)

    return af_sq * g_element
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_array_factor.py -v`
Expected: All tests PASS

- [ ] **Step 5: Lint check**

Run: `python -m ruff check src/aegis/viewer/compute.py tests/test_array_factor.py`
Fix any issues.

- [ ] **Step 6: Commit**

```bash
git add tests/test_array_factor.py src/aegis/viewer/compute.py
git commit -m "Add array_factor_gain() utility for multi-antenna compute"
```

---

### Task 2: Backend multi-antenna `compute_dosimetry()`

**Files:**
- Modify: `src/aegis/viewer/compute.py:350-528` (`compute_dosimetry` function)
- Modify: `tests/test_viewer_compute.py` (add integration tests)

Refactor `compute_dosimetry()` to accept an optional `antennas` list. When provided, it loops over antennas, computes per-antenna `k_hat`, `S_inc`, and `array_factor_gain`, builds per-antenna `PropagationPaths`, then merges via `PropagationPaths.concatenate()`. The existing `antenna_pos` + `power_dbm` single-antenna path is preserved as the default.

- [ ] **Step 1: Write failing integration tests**

Append to `tests/test_viewer_compute.py`:

```python
def test_compute_dosimetry_multi_antenna_higher_power():
    """Two co-located antennas produce higher total power than one."""
    body = make_flat_mesh(8)
    pos = np.array([0.0, 0.0, 2.0])

    with patch(
        "aegis.viewer.compute.DosimetryEngine.compute_with_timings",
    ) as mock_compute:
        mock_compute.return_value = (_fake_result(body.n_triangles), {})

        # Single antenna
        compute_dosimetry(body, antenna_pos=pos)
        single_call = mock_compute.call_args
        single_paths = single_call.args[1]  # paths argument
        single_power = float(single_paths.power.sum())

        mock_compute.reset_mock()

        # Two antennas via antennas param
        antennas = [
            {"position": [0.0, 0.0, 2.0], "power_dbm": 60.0,
             "array_config": {"n_h": 1, "n_v": 1, "d_h_wavelengths": 0.5,
                              "d_v_wavelengths": 0.5, "broadside": [0.0, 0.0, -1.0],
                              "element_pattern": "short_dipole"}},
            {"position": [0.0, 0.0, 2.0], "power_dbm": 60.0,
             "array_config": {"n_h": 1, "n_v": 1, "d_h_wavelengths": 0.5,
                              "d_v_wavelengths": 0.5, "broadside": [0.0, 0.0, -1.0],
                              "element_pattern": "short_dipole"}},
        ]
        compute_dosimetry(body, antenna_pos=pos, antennas=antennas)
        multi_call = mock_compute.call_args
        multi_paths = multi_call.args[1]
        multi_power = float(multi_paths.power.sum())

        assert multi_power > single_power
        assert multi_paths.n_paths == 2


def test_compute_dosimetry_empty_antennas_returns_zero():
    """Empty antennas list produces zero-power paths."""
    body = make_flat_mesh(8)
    pos = np.array([0.0, 0.0, 2.0])

    with patch(
        "aegis.viewer.compute.DosimetryEngine.compute_with_timings",
    ) as mock_compute:
        mock_compute.return_value = (_fake_result(body.n_triangles), {})
        compute_dosimetry(body, antenna_pos=pos, antennas=[])
        paths = mock_compute.call_args.args[1]
        assert paths.n_paths == 1
        assert float(paths.power.sum()) == pytest.approx(0.0)


def test_compute_dosimetry_antennas_with_array_gain():
    """4x4 patch array at broadside has 256x gain over isotropic."""
    body = make_flat_mesh(8)
    pos = np.array([0.0, 0.0, 2.0])

    with patch(
        "aegis.viewer.compute.DosimetryEngine.compute_with_timings",
    ) as mock_compute:
        mock_compute.return_value = (_fake_result(body.n_triangles), {})

        # 1x1 isotropic
        antennas_1x1 = [
            {"position": [0.0, 0.0, 2.0], "power_dbm": 60.0,
             "array_config": {"n_h": 1, "n_v": 1, "d_h_wavelengths": 0.5,
                              "d_v_wavelengths": 0.5, "broadside": [0.0, 0.0, -1.0],
                              "element_pattern": "isotropic"}},
        ]
        compute_dosimetry(body, antenna_pos=pos, antennas=antennas_1x1)
        power_1x1 = float(mock_compute.call_args.args[1].power.sum())

        mock_compute.reset_mock()

        # 4x4 isotropic at broadside: gain = 256
        antennas_4x4 = [
            {"position": [0.0, 0.0, 2.0], "power_dbm": 60.0,
             "array_config": {"n_h": 4, "n_v": 4, "d_h_wavelengths": 0.5,
                              "d_v_wavelengths": 0.5, "broadside": [0.0, 0.0, -1.0],
                              "element_pattern": "isotropic"}},
        ]
        compute_dosimetry(body, antenna_pos=pos, antennas=antennas_4x4)
        power_4x4 = float(mock_compute.call_args.args[1].power.sum())

        assert power_4x4 / power_1x1 == pytest.approx(256.0, rel=0.01)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_viewer_compute.py::test_compute_dosimetry_multi_antenna_higher_power -v`
Expected: FAIL (no `antennas` parameter)

- [ ] **Step 3: Implement multi-antenna loop in `compute_dosimetry()`**

Modify the function signature at line 350 to add the `antennas` parameter:

```python
def compute_dosimetry(
    body: BodyMesh,
    antenna_pos: np.ndarray,
    body_offset: np.ndarray | None = None,
    body_rotation_y: float = 0.0,
    level: int | None = 2,
    mode: str | None = None,
    corrections: dict | None = None,
    tissue: TissueModel | None = None,
    power_dbm: float = DEFAULT_POWER_DBM,
    config: dict | None = None,
    stochastic: dict | None = None,
    antennas: list[dict] | None = None,
) -> tuple:
```

Then replace the S_inc computation and path creation block (lines 399-436) with the multi-antenna loop. The key change: after computing `rotated_body` and `body_center` (which stays the same), replace everything from `# Direction from antenna to body` through the `PropagationPaths.from_powers(...)` call with:

```python
    # Direction from antenna to body (used for single-antenna fallback and stochastic)
    direction = body_center - antenna_pos
    dist = np.linalg.norm(direction)
    if dist < 1e-6:
        dist = 1.0
    k_hat = direction / dist

    # Power at body surface (free-space path loss, clamp distance for near-field)
    tx_power_w = 10 ** ((power_dbm - 30) / 10)
    from aegis.viewer.raytracer import _DEFAULT_FSPL_DISTANCE_CLAMP_M

    d_clamped = max(dist, _DEFAULT_FSPL_DISTANCE_CLAMP_M)
    S_inc = tx_power_w / (4 * np.pi * d_clamped**2)

    cluster_viz = None
    if stochastic:
        from aegis.channel import generate_channel, load_preset

        preset_dir = _resolve_channel_preset_dir(cfg)
        preset = load_preset(stochastic["preset"], preset_dir)
        viz_out: dict = {}
        paths = generate_channel(
            preset["params"],
            freq_ghz=stochastic.get("freq_ghz", 28),
            antenna_pos=antenna_pos,
            body_center=body_center,
            power_dbm=power_dbm,
            seed=stochastic.get("seed", 42),
            overrides=stochastic.get("overrides"),
            viz_out=viz_out,
        )
        cluster_viz = _build_cluster_viz(viz_out)
    elif antennas is not None:
        # Multi-antenna mode: loop over antennas, compute per-antenna paths, merge
        # Note: stochastic takes precedence (elif). When stochastic mode is enabled,
        # only the selected antenna (legacy antenna_pos) is used. This is by design
        # per the spec ("per-antenna stochastic channels are future work").
        if len(antennas) == 0:
            # No antennas: zero-power single path
            paths = PropagationPaths.from_powers(
                k_hat=k_hat[np.newaxis, :],
                power=np.array([0.0]),
            )
            S_inc = 0.0
        else:
            per_antenna_paths = []
            total_S_inc = 0.0
            for ant in antennas:
                ant_pos = np.asarray(ant["position"], dtype=np.float64)
                ant_power_dbm = float(ant.get("power_dbm", power_dbm))
                ant_tx_w = 10 ** ((ant_power_dbm - 30) / 10)
                acfg = ant.get("array_config", {})

                a_dir = body_center - ant_pos
                a_dist = np.linalg.norm(a_dir)
                if a_dist < 1e-6:
                    a_dist = 1.0
                a_k_hat = a_dir / a_dist
                a_d_clamped = max(a_dist, _DEFAULT_FSPL_DISTANCE_CLAMP_M)
                a_S_inc = ant_tx_w / (4 * np.pi * a_d_clamped**2)

                # Array factor gain
                a_gain = array_factor_gain(
                    k_hat=a_k_hat,
                    n_h=int(acfg.get("n_h", 1)),
                    n_v=int(acfg.get("n_v", 1)),
                    d_h=float(acfg.get("d_h_wavelengths", 0.5)),
                    d_v=float(acfg.get("d_v_wavelengths", 0.5)),
                    broadside=np.asarray(acfg.get("broadside", [0, 0, -1]), dtype=np.float64),
                    element_pattern=acfg.get("element_pattern", "short_dipole"),
                    freq_hz=tissue.freq_hz if tissue else DEFAULT_FREQ_HZ,
                )

                a_S_eff = a_S_inc * a_gain
                total_S_inc += a_S_eff
                per_antenna_paths.append(
                    PropagationPaths.from_powers(
                        k_hat=a_k_hat[np.newaxis, :],
                        power=np.array([a_S_eff]),
                    )
                )

            paths = PropagationPaths.concatenate(per_antenna_paths, reindex_elements=True)
            S_inc = total_S_inc
    else:
        # Single plane wave (legacy single-antenna path)
        paths = PropagationPaths.from_powers(
            k_hat=k_hat[np.newaxis, :],
            power=np.array([S_inc]),
        )
```

Also update the `extra` dict (line 515-518) to include `n_paths` and handle the multi-antenna distance:

```python
    extra = {
        "S_inc": float(S_inc),
        "distance_m": float(dist),  # distance from legacy antenna_pos (first/selected antenna)
        "n_paths": paths.n_paths,
        "n_antennas": len(antennas) if antennas else 1,
        "timings": timings,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_viewer_compute.py tests/test_array_factor.py -v`
Expected: All PASS

- [ ] **Step 5: Lint check**

Run: `python -m ruff check src/aegis/viewer/compute.py tests/test_viewer_compute.py`

- [ ] **Step 6: Commit**

```bash
git add src/aegis/viewer/compute.py tests/test_viewer_compute.py
git commit -m "Add multi-antenna loop to compute_dosimetry with array factor gain"
```

---

### Task 3: Backend route: parse `antennas` array

**Files:**
- Modify: `src/aegis/viewer/routes/compute.py:523-668` (`api_compute` handler)
- Modify: `tests/viewer/test_compute_routes.py` (add route tests)

The `/api/compute` route gains `antennas` array parsing. Backward compat: if the old `antenna_pos` format is sent (no `antennas` key), the route wraps it into a single-antenna array internally.

- [ ] **Step 1: Write failing route tests**

Append to `tests/viewer/test_compute_routes.py` (find the existing test class or add at module level):

```python
def test_compute_with_antennas_array(viewer_app):
    """POST /api/compute with antennas array."""
    with patch("aegis.viewer.compute.compute_dosimetry", side_effect=_mock_compute_dosimetry):
        client = viewer_app.test_client()
        resp = client.post("/api/compute", json={
            "antennas": [
                {"position": [5, 0, 1], "power_dbm": 60,
                 "array_config": {"n_h": 1, "n_v": 1, "d_h_wavelengths": 0.5,
                                  "d_v_wavelengths": 0.5, "broadside": [0, 0, -1],
                                  "element_pattern": "short_dipole"}},
                {"position": [-5, 0, 1], "power_dbm": 50,
                 "array_config": {"n_h": 2, "n_v": 2, "d_h_wavelengths": 0.5,
                                  "d_v_wavelengths": 0.5, "broadside": [0, 0, -1],
                                  "element_pattern": "patch"}},
            ],
            "mode": "spatial",
        })
    assert resp.status_code == 200


def test_compute_legacy_antenna_pos_still_works(viewer_app):
    """POST /api/compute with old antenna_pos (no antennas key) still works."""
    with patch("aegis.viewer.compute.compute_dosimetry", side_effect=_mock_compute_dosimetry):
        client = viewer_app.test_client()
        resp = client.post("/api/compute", json={
            "antenna_pos": [5, 0, 1],
            "power_dbm": 60,
            "mode": "bound",
        })
    assert resp.status_code == 200
```

Note: the mock target is `aegis.viewer.compute.compute_dosimetry` (the module where it's defined), not `aegis.viewer.routes.compute.compute_dosimetry`. The route handler uses a lazy import (`from aegis.viewer.compute import compute_dosimetry`) inside the function body, but patching at the source module is correct because the import re-fetches each call. Match the pattern used by existing tests in this file (check `_mock_compute_dosimetry` usage). Also use `viewer_app.test_client()` to get a Flask test client, matching the existing test patterns.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/viewer/test_compute_routes.py::test_compute_with_antennas_array -v`
Expected: FAIL (test function may not exist yet or param not parsed)

- [ ] **Step 3: Implement `antennas` parsing in the route handler**

In `src/aegis/viewer/routes/compute.py`, after the `antenna_pos` parsing (line 638) and before the `compute_dosimetry` call (line 656), add:

```python
        # Parse multi-antenna array (new API)
        antennas = None
        raw_antennas = params.get("antennas")
        if raw_antennas is not None:
            if not isinstance(raw_antennas, list):
                return jsonify({"error": "antennas must be a list"}), 400
            antennas = []
            for i, raw_ant in enumerate(raw_antennas):
                if not isinstance(raw_ant, dict):
                    return jsonify({"error": f"antennas[{i}] must be an object"}), 400
                ant_pos, err = _parse_vec3(raw_ant, "position", [5, 0, 1])
                if err:
                    return err
                ant_power = float(raw_ant.get("power_dbm", power_dbm))
                acfg = raw_ant.get("array_config", {})
                antennas.append({
                    "position": ant_pos.tolist(),
                    "power_dbm": ant_power,
                    "array_config": acfg,
                })
```

Then pass `antennas=antennas` to the `compute_dosimetry` call (line 668):

```python
            result, res_body, res_tissue, res_level, res_mode, res_corr, extra = compute_dosimetry(
                body,
                antenna_pos=antenna_pos,
                body_offset=body_offset,
                body_rotation_y=body_rotation_y,
                level=level,
                mode=mode,
                corrections=corrections,
                tissue=tissue,
                power_dbm=power_dbm,
                config=cfg,
                stochastic=stochastic,
                antennas=antennas,
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/viewer/test_compute_routes.py -v -k "antennas or legacy"`
Expected: PASS

- [ ] **Step 5: Lint and commit**

```bash
python -m ruff check src/aegis/viewer/routes/compute.py tests/viewer/test_compute_routes.py
git add src/aegis/viewer/routes/compute.py tests/viewer/test_compute_routes.py
git commit -m "Accept antennas array in /api/compute with backward compat"
```

---

### Task 4: Frontend antenna store

**Files:**
- Create: `aegis-web/src/stores/antenna.ts`
- Modify: `aegis-web/src/api/types.ts:337` (add `'short_dipole'` to `ElementPattern`)

This is the new Zustand store that owns all antenna state. Pattern follows the MIMO store (`aegis-web/src/stores/mimo.ts`) which uses a Map for multi-entity management.

- [ ] **Step 1: Add `'short_dipole'` to `ElementPattern` type**

In `aegis-web/src/api/types.ts` line 337, change:
```typescript
export type ElementPattern = 'isotropic' | 'patch'
```
to:
```typescript
export type ElementPattern = 'isotropic' | 'patch' | 'short_dipole'
```

- [ ] **Step 2: Create `aegis-web/src/stores/antenna.ts`**

```typescript
import { create } from 'zustand'
import type { ScenePos } from '@/api/coordinates'
import type { ElementPattern } from '@/api/types'

export interface AntennaArrayConfig {
  n_h: number
  n_v: number
  d_h_wavelengths: number
  d_v_wavelengths: number
  broadside: [number, number, number]
  element_pattern: ElementPattern
}

export interface AntennaConfig {
  id: string
  name: string
  position: ScenePos
  powerDbm: number
  arrayConfig: AntennaArrayConfig
  enabled: boolean
}

interface AntennaStore {
  antennas: Map<string, AntennaConfig>
  selectedId: string | null
  _nextNumber: number

  addAntenna: (position: ScenePos) => string
  removeAntenna: (id: string) => void
  updateAntenna: (id: string, partial: Partial<AntennaConfig>) => void
  selectAntenna: (id: string | null) => void
  moveAntenna: (id: string, position: ScenePos) => void
  setEnabled: (id: string, on: boolean) => void

  // Derived helpers
  selectedAntenna: () => AntennaConfig | null
  enabledAntennas: () => AntennaConfig[]
}

function defaultArrayConfig(): AntennaArrayConfig {
  return {
    n_h: 1,
    n_v: 1,
    d_h_wavelengths: 0.5,
    d_v_wavelengths: 0.5,
    broadside: [0, 0, -1],
    element_pattern: 'short_dipole',
  }
}

export const useAntennaStore = create<AntennaStore>((set, get) => ({
  antennas: new Map(),
  selectedId: null,
  _nextNumber: 1,

  addAntenna: (position) => {
    const state = get()
    const num = state._nextNumber
    const id = `ant_${num}`
    const antenna: AntennaConfig = {
      id,
      name: `Antenna ${num}`,
      position,
      powerDbm: 60,
      arrayConfig: defaultArrayConfig(),
      enabled: true,
    }
    const next = new Map(state.antennas)
    next.set(id, antenna)
    set({ antennas: next, selectedId: id, _nextNumber: num + 1 })
    return id
  },

  removeAntenna: (id) => {
    const state = get()
    const next = new Map(state.antennas)
    next.delete(id)
    // Select next available antenna if we removed the selected one
    let selectedId = state.selectedId
    if (selectedId === id) {
      const remaining = [...next.keys()]
      selectedId = remaining.length > 0 ? remaining[remaining.length - 1] : null
    }
    set({ antennas: next, selectedId })
  },

  updateAntenna: (id, partial) => {
    const state = get()
    const existing = state.antennas.get(id)
    if (!existing) return
    const next = new Map(state.antennas)
    next.set(id, { ...existing, ...partial })
    set({ antennas: next })
  },

  selectAntenna: (id) => set({ selectedId: id }),

  moveAntenna: (id, position) => {
    const state = get()
    const existing = state.antennas.get(id)
    if (!existing) return
    const next = new Map(state.antennas)
    next.set(id, { ...existing, position })
    set({ antennas: next })
  },

  setEnabled: (id, on) => {
    const state = get()
    const existing = state.antennas.get(id)
    if (!existing) return
    const next = new Map(state.antennas)
    next.set(id, { ...existing, enabled: on })
    set({ antennas: next })
  },

  selectedAntenna: () => {
    const state = get()
    if (!state.selectedId) return null
    return state.antennas.get(state.selectedId) ?? null
  },

  enabledAntennas: () => {
    return [...get().antennas.values()].filter(a => a.enabled)
  },
}))
```

- [ ] **Step 3: Verify TypeScript compiles**

Run: `cd aegis-web && npx tsc --noEmit --pretty 2>&1 | head -30`
Expected: No errors related to `antenna.ts`

- [ ] **Step 4: Commit**

```bash
git add aegis-web/src/stores/antenna.ts aegis-web/src/api/types.ts
git commit -m "Add AntennaStore for multi-antenna state management"
```

---

### Task 5: Simulation store derived getters

**Files:**
- Modify: `aegis-web/src/stores/simulation.ts:115-154` (store creation)

Make `antennaPos` and `powerDbm` delegate to the antenna store's selected antenna. This preserves backward compat for 15+ consumer files (DistanceLine, ClusterPaths, useKeyboard, shareLink, AntennaHint, WelcomeOverlay, useOptimization, OptimizePanel, sentry, etc.).

The key insight: Zustand's `create()` uses a simple `set`/`get` pattern. We can't use ES6 getters inside the object literal passed to `create()`. Instead, we intercept `setAntennaPos` and `setPowerDbm` to write through to the antenna store, and subscribe to the antenna store to sync back.

- [ ] **Step 1: Add antenna store import and sync logic**

At the top of `aegis-web/src/stores/simulation.ts`, add:

```typescript
import { useAntennaStore } from '@/stores/antenna'
```

- [ ] **Step 2: Modify `setAntennaPos` to write through to antenna store**

Change `setAntennaPos` (line 154) from:
```typescript
setAntennaPos: (pos) => set({ antennaPos: pos }),
```
to:
```typescript
setAntennaPos: (pos) => {
  set({ antennaPos: pos })
  // Sync to antenna store: if setting a position and no antenna exists, create one
  const antStore = useAntennaStore.getState()
  if (pos && antStore.antennas.size === 0) {
    antStore.addAntenna(pos)
  } else if (pos && antStore.selectedId) {
    antStore.moveAntenna(antStore.selectedId, pos)
  } else if (!pos) {
    // Clearing: deselect but keep antennas (callers like keyboard delete
    // may clear antennaPos; removing all would be too aggressive)
    antStore.selectAntenna(null)
  }
},
```

- [ ] **Step 3: Modify `setPowerDbm` to write through**

Change `setPowerDbm` (line 196) from:
```typescript
setPowerDbm: (power) => set({ powerDbm: power }),
```
to:
```typescript
setPowerDbm: (power) => {
  set({ powerDbm: power })
  const antStore = useAntennaStore.getState()
  if (antStore.selectedId) {
    antStore.updateAntenna(antStore.selectedId, { powerDbm: power })
  }
},
```

- [ ] **Step 4: Add antenna store subscription to sync selected antenna back**

After the `create()` call (after line 272), add a subscription that syncs the selected antenna's position and power back to the simulation store:

```typescript
// Bootstrap antenna store from existing antennaPos (config, share link, scenario)
const initialPos = useSimulationStore.getState().antennaPos
if (initialPos && useAntennaStore.getState().antennas.size === 0) {
  useAntennaStore.getState().addAntenna(initialPos)
}

// Sync antenna store -> simulation store (selected antenna's pos/power)
useAntennaStore.subscribe((state) => {
  const selected = state.selectedId ? state.antennas.get(state.selectedId) : null
  const sim = useSimulationStore.getState()
  if (selected) {
    if (sim.antennaPos?.[0] !== selected.position[0] ||
        sim.antennaPos?.[1] !== selected.position[1] ||
        sim.antennaPos?.[2] !== selected.position[2]) {
      useSimulationStore.setState({ antennaPos: selected.position })
    }
    if (sim.powerDbm !== selected.powerDbm) {
      useSimulationStore.setState({ powerDbm: selected.powerDbm })
    }
  } else if (state.antennas.size === 0 && sim.antennaPos !== null) {
    useSimulationStore.setState({ antennaPos: null })
  }
})
```

- [ ] **Step 5: Verify TypeScript compiles**

Run: `cd aegis-web && npx tsc --noEmit --pretty 2>&1 | head -30`
Expected: No errors

- [ ] **Step 6: Commit**

```bash
git add aegis-web/src/stores/simulation.ts
git commit -m "Wire simulation store antennaPos/powerDbm to antenna store"
```

---

### Task 6: API client `antennas` array

**Files:**
- Modify: `aegis-web/src/api/client.ts:320-364` (ComputeParams and computePayload)

Update the API client to send an `antennas` array instead of a single `antenna_pos` when multiple antennas exist.

- [ ] **Step 1: Add `AntennaParam` type and update `ComputeParams`**

In `aegis-web/src/api/client.ts`, add before `ComputeParams` (line ~318):

```typescript
export interface AntennaParam {
  position: ScenePos
  power_dbm: number
  array_config: {
    n_h: number
    n_v: number
    d_h_wavelengths: number
    d_v_wavelengths: number
    broadside: [number, number, number]
    element_pattern: string
  }
}
```

Add to `ComputeParams` interface (after line 338):
```typescript
  antennas?: AntennaParam[]
```

- [ ] **Step 2: Update `computePayload` to include antennas**

Modify `computePayload` (line 341) to conditionally send `antennas` instead of `antenna_pos`:

```typescript
function computePayload(params: ComputeParams) {
  const base: Record<string, unknown> = {
    body_offset: toServer(params.bodyOffset),
    body_rotation_y: params.bodyRotationY,
    mode: params.mode,
    fresnel: params.fresnel,
    polarisation: params.polarisation,
    curvature: params.curvature,
    diffraction: params.diffraction,
    skin_model: params.skinModel,
    freq_hz: params.freqGhz * 1e9,
    quantities: params.quantities,
    exposure_scenario: params.exposureScenario,
    ...(params.bodyName ? { body_name: params.bodyName } : {}),
    ...(params.stochastic ? {
      stochastic: true,
      stochastic_preset: params.stochasticPreset,
      stochastic_overrides: params.stochasticOverrides,
      stochastic_seed: params.stochasticSeed,
    } : {}),
  }

  if (params.antennas && params.antennas.length > 0) {
    base.antennas = params.antennas.map(a => ({
      position: toServer(a.position),
      power_dbm: a.power_dbm,
      array_config: a.array_config,
    }))
    // Also send antenna_pos for backward compat (first antenna)
    base.antenna_pos = toServer(params.antennaPos)
    base.power_dbm = params.powerDbm
  } else {
    base.antenna_pos = toServer(params.antennaPos)
    base.power_dbm = params.powerDbm
  }

  return base
}
```

- [ ] **Step 3: Verify TypeScript compiles**

Run: `cd aegis-web && npx tsc --noEmit --pretty 2>&1 | head -30`

- [ ] **Step 4: Commit**

```bash
git add aegis-web/src/api/client.ts
git commit -m "Add antennas array to compute API client"
```

---

### Task 7: `useDosimetry` builds antennas array

**Files:**
- Modify: `aegis-web/src/hooks/useDosimetry.ts:1-94`

The dosimetry hook reads all enabled antennas from the antenna store, builds the `antennas` API parameter, and sends it with the compute request.

- [ ] **Step 1: Import antenna store and read enabled antennas**

Add import at top of `useDosimetry.ts`:

```typescript
import { useAntennaStore } from '@/stores/antenna'
```

Inside `useDosimetry()`, add a subscription to the antenna store. After the `sim` destructure (line 29), add:

```typescript
  const antennaStoreState = useAntennaStore(useShallow(s => ({
    antennas: s.antennas,
    selectedId: s.selectedId,
  })))
```

- [ ] **Step 2: Build antennas array in `triggerCompute`**

Inside `triggerCompute` (after the antenna tip computation at line 73), build the antennas array:

```typescript
    // Build multi-antenna array from antenna store
    const antStore = useAntennaStore.getState()
    const enabledAntennas = [...antStore.antennas.values()].filter(a => a.enabled)
    const antennasParam = enabledAntennas.length > 0 ? enabledAntennas.map(a => ({
      position: [a.position[0], a.position[1] + poleH, a.position[2]] as [number, number, number],
      power_dbm: a.powerDbm,
      array_config: {
        n_h: a.arrayConfig.n_h,
        n_v: a.arrayConfig.n_v,
        d_h_wavelengths: a.arrayConfig.d_h_wavelengths,
        d_v_wavelengths: a.arrayConfig.d_v_wavelengths,
        broadside: a.arrayConfig.broadside,
        element_pattern: a.arrayConfig.element_pattern,
      },
    })) : undefined
```

Then add `antennas: antennasParam` to the `params` object (line 75-94):

```typescript
    const params = {
      antennaPos: antennaTip,
      // ...existing fields...
      antennas: antennasParam,
    }
```

- [ ] **Step 3: Add `antennaStoreState` to effect dependencies**

Update the `useEffect` dependency array (line 215) to include `antennaStoreState`:

```typescript
  }, [sim, scene, exposureScenario, antennaStoreState, triggerCompute])
```

And the `triggerCompute` useCallback deps (line 202):

```typescript
  }, [sim, scene, exposureScenario, antennaStoreState])
```

- [ ] **Step 4: Verify TypeScript compiles**

Run: `cd aegis-web && npx tsc --noEmit --pretty 2>&1 | head -30`

- [ ] **Step 5: Commit**

```bash
git add aegis-web/src/hooks/useDosimetry.ts
git commit -m "Build multi-antenna array in useDosimetry hook"
```

---

### Task 8: Click-to-place: ctrl+click adds, click moves

**Files:**
- Modify: `aegis-web/src/hooks/useClickToPlace.ts:18-47`

Change the non-MIMO click handler: regular click moves the selected antenna, ctrl+click adds a new antenna at the click point.

- [ ] **Step 1: Update useClickToPlace**

Replace the single-antenna branch (lines 42-44) with multi-antenna logic:

```typescript
import { useAntennaStore } from '@/stores/antenna'
```

Then in the `onPointerUp` handler, replace lines 42-44:

```typescript
      } else {
        // Multi-antenna mode
        const antStore = useAntennaStore.getState()
        if (e.nativeEvent.ctrlKey || e.nativeEvent.metaKey) {
          // Ctrl+click: add new antenna at click point
          antStore.addAntenna([point.x, point.y, point.z])
        } else if (antStore.selectedId) {
          // Click: move selected antenna
          antStore.moveAntenna(antStore.selectedId, [point.x, point.y, point.z])
        } else {
          // No antenna exists yet: create one
          antStore.addAntenna([point.x, point.y, point.z])
        }
      }
```

Also remove the direct `useSimulationStore.getState().setAntennaPos(...)` call. The antenna store subscription in simulation.ts handles syncing `antennaPos` back.

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd aegis-web && npx tsc --noEmit --pretty 2>&1 | head -30`

- [ ] **Step 3: Commit**

```bash
git add aegis-web/src/hooks/useClickToPlace.ts
git commit -m "Ctrl+click adds antenna, click moves selected"
```

---

### Task 9: Antenna component accepts props, supports multi-render

**Files:**
- Modify: `aegis-web/src/components/scene/Antenna.tsx:65-201`

Convert `Antenna` from reading the simulation store directly to accepting props for position, config, and selected state. This allows `SceneRoot` to render multiple instances.

- [ ] **Step 1: Add props interface and refactor component**

Change the component to accept props:

```typescript
interface AntennaProps {
  position: [number, number, number]
  selected?: boolean
}

export default function Antenna({ position, selected = true }: AntennaProps) {
  const config = useSceneStore(s => s.viewerConfig)
  const wireframe = useUIStore(s => s.wireframe)
  const cameraMode = useUIStore(s => s.cameraMode)
  const appliedPattern = useSimulationStore(s => s.appliedPattern)
  const appliedPatternMeta = useSimulationStore(s => s.appliedPatternMeta)
```

Remove the `pos` read from simulation store (line 66: `const pos = useSimulationStore(s => s.antennaPos)`).

Replace `if (!pos || !config) return null` (line 135) with `if (!config) return null`.

Replace `<group position={pos}>` (line 151) with `<group position={position}>`.

Add a visual highlight for the selected antenna. In the pole material (line 155), make the color brighter when selected:

```typescript
<meshStandardMaterial color={selected ? (ant.color ?? '#ff3333') : (ant.pole_color ?? '#888888')} />
```

Add opacity dimming for non-selected antennas on the hub sphere and pattern mesh:

```typescript
opacity={(rp.opacity ?? 0.94) * (selected ? 1.0 : 0.5)}
```

Keep `scalarRadiationGain` and `interpolatePatternGain` helper functions unchanged (they are module-level, not component-level).

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd aegis-web && npx tsc --noEmit --pretty 2>&1 | head -30`

- [ ] **Step 3: Commit**

```bash
git add aegis-web/src/components/scene/Antenna.tsx
git commit -m "Refactor Antenna to accept position/selected props"
```

---

### Task 10: SceneRoot renders multiple antennas

**Files:**
- Modify: `aegis-web/src/components/scene/SceneRoot.tsx:382-390`

Replace the single `<Antenna />` with a loop over the antenna store.

- [ ] **Step 1: Import antenna store**

Add at top of `SceneRoot.tsx`:

```typescript
import { useAntennaStore } from '@/stores/antenna'
```

- [ ] **Step 2: Read antenna store state inside the scene component**

Inside the `Scene` component (or wherever `<Antenna />` is rendered), add:

```typescript
const antennaEntries = useAntennaStore(s => [...s.antennas.values()])
const selectedAntennaId = useAntennaStore(s => s.selectedId)
```

- [ ] **Step 3: Replace single `<Antenna />` with multi-antenna render**

Change lines 384-389 from:

```tsx
<>
  {bodyMeshVisible && (phantomType === 'gltf' ? <AnimatedBody /> : <BodyMesh />)}
  <Antenna />
  <DistanceLine />
</>
```

to:

```tsx
<>
  {bodyMeshVisible && (phantomType === 'gltf' ? <AnimatedBody /> : <BodyMesh />)}
  {antennaEntries.map(ant => (
    <Antenna
      key={ant.id}
      position={ant.position}
      selected={ant.id === selectedAntennaId}
    />
  ))}
  <DistanceLine />
</>
```

- [ ] **Step 4: Verify TypeScript compiles**

Run: `cd aegis-web && npx tsc --noEmit --pretty 2>&1 | head -30`

- [ ] **Step 5: Commit**

```bash
git add aegis-web/src/components/scene/SceneRoot.tsx
git commit -m "Render multiple antennas from antenna store in SceneRoot"
```

---

### Task 11: AntennasPanel sidebar component

**Files:**
- Create: `aegis-web/src/components/panels/AntennasPanel.tsx`

New sidebar panel with antenna list (compact rows), add button, and per-antenna config controls (reusing the same UI patterns from `AntennaPanel.tsx`). The config section reuses array size, element spacing, element pattern, position, and power controls.

- [ ] **Step 1: Create `AntennasPanel.tsx`**

```typescript
import { useAntennaStore, type AntennaConfig, type AntennaArrayConfig } from '@/stores/antenna'
import { useSimulationStore } from '@/stores/simulation'
import { useMIMOStore } from '@/stores/mimo'
import type { ElementPattern } from '@/api/types'
import Tex from '@/components/ui/Tex'

const PATTERN_OPTIONS: { value: ElementPattern; label: string }[] = [
  { value: 'short_dipole', label: 'Dipole' },
  { value: 'patch', label: 'Patch' },
  { value: 'isotropic', label: 'Iso' },
]

export default function AntennasPanel() {
  const mimoEnabled = useMIMOStore(s => s.enabled)
  const antennas = useAntennaStore(s => [...s.antennas.values()])
  const selectedId = useAntennaStore(s => s.selectedId)
  const addAntenna = useAntennaStore(s => s.addAntenna)
  const removeAntenna = useAntennaStore(s => s.removeAntenna)
  const selectAntenna = useAntennaStore(s => s.selectAntenna)
  const updateAntenna = useAntennaStore(s => s.updateAntenna)
  const setEnabled = useAntennaStore(s => s.setEnabled)
  const freqGhz = useSimulationStore(s => s.freqGhz)

  if (mimoEnabled) {
    return (
      <p className="text-xs text-muted-foreground">
        MIMO mode active. Antenna config is managed in the MIMO and Antenna tabs.
      </p>
    )
  }

  const selected = antennas.find(a => a.id === selectedId) ?? null
  const lambda_m = 3e8 / (freqGhz * 1e9)

  const inputClass = "w-full bg-muted/50 border border-border rounded px-1.5 py-1 text-[11px] text-foreground font-mono"
  const labelClass = "text-[10px] text-muted-foreground block mb-0.5"

  const updateConfig = (partial: Partial<AntennaArrayConfig>) => {
    if (!selected) return
    updateAntenna(selected.id, {
      arrayConfig: { ...selected.arrayConfig, ...partial },
    })
  }

  return (
    <div className="space-y-3">
      {/* Antenna list */}
      <div className="space-y-1">
        {antennas.map(ant => (
          <div
            key={ant.id}
            className={`flex items-center gap-1.5 px-1.5 py-1 rounded text-xs cursor-pointer transition-colors ${
              ant.id === selectedId
                ? 'bg-primary/15 border border-primary/40'
                : 'bg-muted/50 border border-transparent hover:bg-muted'
            }`}
            onClick={() => selectAntenna(ant.id)}
          >
            <input
              type="checkbox"
              className="h-3 w-3 rounded accent-primary"
              checked={ant.enabled}
              onChange={(e) => { e.stopPropagation(); setEnabled(ant.id, e.target.checked) }}
              onClick={(e) => e.stopPropagation()}
            />
            <span className="flex-1 truncate text-foreground">{ant.name}</span>
            {ant.arrayConfig.n_h * ant.arrayConfig.n_v > 1 && (
              <span className="text-[9px] text-muted-foreground px-1 py-0.5 bg-muted rounded">
                {ant.arrayConfig.n_h}x{ant.arrayConfig.n_v}
              </span>
            )}
            <span className="text-[9px] text-muted-foreground">
              ({ant.position[0].toFixed(1)}, {ant.position[1].toFixed(1)}, {ant.position[2].toFixed(1)})
            </span>
            <button
              className="ml-1 shrink-0 w-4 h-4 flex items-center justify-center rounded text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
              title="Remove"
              onClick={(e) => { e.stopPropagation(); removeAntenna(ant.id) }}
            >
              <svg width="10" height="10" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
                <path d="M3 3l6 6M9 3l-6 6" />
              </svg>
            </button>
          </div>
        ))}
      </div>

      {/* Add button */}
      <button
        className="w-full text-xs py-1.5 rounded border border-dashed border-border text-muted-foreground hover:text-foreground hover:border-foreground/30 transition-colors cursor-pointer"
        onClick={() => addAntenna([5, 0, 0])}
      >
        + Add antenna
      </button>

      {/* Selected antenna config */}
      {selected && (
        <div className="space-y-3 pt-2 border-t border-border">
          <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
            {selected.name}
          </p>

          {/* Power */}
          <div>
            <label className={labelClass}><Tex math={'P_\\text{TX}'} /></label>
            <div className="flex gap-2 items-center">
              <div className="flex-1">
                <input
                  type="number"
                  className={inputClass}
                  value={selected.powerDbm}
                  onChange={(e) => updateAntenna(selected.id, { powerDbm: Number(e.target.value) })}
                  step={1} min={0} max={100}
                />
                <span className="text-[9px] text-muted-foreground mt-0.5 block">dBm</span>
              </div>
              <span className="text-muted-foreground text-[10px] pb-3">=</span>
              <div className="flex-1">
                <input
                  type="number"
                  className={inputClass}
                  value={Number((10 ** ((selected.powerDbm - 30) / 10)).toPrecision(4))}
                  onChange={(e) => {
                    const w = Number(e.target.value)
                    if (w > 0) updateAntenna(selected.id, { powerDbm: Math.round((10 * Math.log10(w) + 30) * 100) / 100 })
                  }}
                  step={0.1} min={0}
                />
                <span className="text-[9px] text-muted-foreground mt-0.5 block">W</span>
              </div>
            </div>
          </div>

          {/* Array size */}
          <div>
            <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-1">Array size</p>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className={labelClass}>N_h</label>
                <input type="number" className={inputClass} value={selected.arrayConfig.n_h}
                  min={1} max={16} step={1}
                  onChange={e => { const v = parseInt(e.target.value); if (!isNaN(v) && v >= 1 && v <= 16) updateConfig({ n_h: v }) }}
                />
              </div>
              <div>
                <label className={labelClass}>N_v</label>
                <input type="number" className={inputClass} value={selected.arrayConfig.n_v}
                  min={1} max={16} step={1}
                  onChange={e => { const v = parseInt(e.target.value); if (!isNaN(v) && v >= 1 && v <= 16) updateConfig({ n_v: v }) }}
                />
              </div>
            </div>
            <p className="text-[9px] text-muted-foreground/60 mt-0.5">
              {selected.arrayConfig.n_h * selected.arrayConfig.n_v} elements
            </p>
          </div>

          {/* Spacing */}
          <div>
            <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-1">Spacing</p>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className={labelClass}>d_h (λ)</label>
                <input type="number" className={inputClass} value={selected.arrayConfig.d_h_wavelengths}
                  min={0.1} max={2.0} step={0.1}
                  onChange={e => { const v = parseFloat(e.target.value); if (!isNaN(v) && v > 0) updateConfig({ d_h_wavelengths: v }) }}
                />
              </div>
              <div>
                <label className={labelClass}>d_v (λ)</label>
                <input type="number" className={inputClass} value={selected.arrayConfig.d_v_wavelengths}
                  min={0.1} max={2.0} step={0.1}
                  onChange={e => { const v = parseFloat(e.target.value); if (!isNaN(v) && v > 0) updateConfig({ d_v_wavelengths: v }) }}
                />
              </div>
            </div>
            <p className="text-[9px] text-muted-foreground/60 mt-0.5">
              {(selected.arrayConfig.d_h_wavelengths * lambda_m * 1000).toFixed(1)} x{' '}
              {(selected.arrayConfig.d_v_wavelengths * lambda_m * 1000).toFixed(1)} mm
            </p>
          </div>

          {/* Element pattern */}
          <div>
            <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-1">Element</p>
            <div className="flex gap-1">
              {PATTERN_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  onClick={() => updateConfig({ element_pattern: opt.value })}
                  className={`flex-1 text-[10px] py-1 px-1 rounded border transition-colors cursor-pointer ${
                    selected.arrayConfig.element_pattern === opt.value
                      ? 'bg-primary/15 text-primary border-primary/40'
                      : 'bg-muted/50 text-muted-foreground border-border hover:bg-muted'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Position */}
          <div>
            <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-1">Position</p>
            <div className="flex gap-1">
              {(['X', 'Y', 'Z'] as const).map((axis, i) => (
                <label key={axis} className="flex items-center gap-0.5 flex-1">
                  <span className="text-[9px] text-muted-foreground">{axis}</span>
                  <input type="number" step={0.5} value={selected.position[i]}
                    onChange={e => {
                      const v = parseFloat(e.target.value)
                      if (isNaN(v)) return
                      const pos: [number, number, number] = [...selected.position]
                      pos[i] = i === 1 ? Math.max(0, v) : v
                      updateAntenna(selected.id, { position: pos })
                    }}
                    className="w-full bg-muted/50 border border-border rounded px-1 py-0.5 text-[10px] text-foreground font-mono"
                  />
                </label>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd aegis-web && npx tsc --noEmit --pretty 2>&1 | head -30`

- [ ] **Step 3: Commit**

```bash
git add aegis-web/src/components/panels/AntennasPanel.tsx
git commit -m "Add AntennasPanel with antenna list and per-antenna config"
```

---

### Task 12: Wire up sidebar and clean ParametersPanel

**Files:**
- Modify: `aegis-web/src/components/layout/Sidebar.tsx:21,59-69`
- Modify: `aegis-web/src/components/panels/ParametersPanel.tsx:47-48,60-61,87-111,157-186`

Add the Antennas accordion section to the sidebar. Remove the antenna chip and power control from ParametersPanel (those now live in AntennasPanel).

- [ ] **Step 1: Add Antennas section to Sidebar**

In `Sidebar.tsx`, add import:
```typescript
import AntennasPanel from '@/components/panels/AntennasPanel'
```

Add a new `AccordionItem` right after the Parameters section (after line 69):

```tsx
<AccordionItem value="antennas" className="border-b border-border px-3">
  <AccordionTrigger className="text-sm font-medium py-3">Antennas</AccordionTrigger>
  <AccordionContent>
    <div className="py-2">
      <PanelErrorBoundary name="Antennas">
        <AntennasPanel />
      </PanelErrorBoundary>
    </div>
  </AccordionContent>
</AccordionItem>
```

- [ ] **Step 2: Remove antenna chip from ParametersPanel**

In `ParametersPanel.tsx`:

1. Remove the `antennaPos`, `setAntennaPos`, `clearResults` reads (lines 47-49). Keep other reads.
2. Remove the antenna chip block (lines 87-111, the `{antennaPos && (` block).
3. Remove the power input block (lines 157-186, from `<label className={labelClass}><Tex math={'P_\\text{TX}'} />` through the closing `</div>` of the dBm/W inputs).
4. Remove the `useMIMOStore` import if it's only used for the antenna chip clear (check if used elsewhere in the component). The MIMO store is used at line 98-103 for clearing MIMO state on antenna remove. Since the antenna chip is removed, that code goes too. Keep the import if other code uses it.

- [ ] **Step 3: Verify TypeScript compiles**

Run: `cd aegis-web && npx tsc --noEmit --pretty 2>&1 | head -30`

- [ ] **Step 4: Commit**

```bash
git add aegis-web/src/components/layout/Sidebar.tsx aegis-web/src/components/panels/ParametersPanel.tsx
git commit -m "Add Antennas sidebar section, remove antenna chip from Parameters"
```

---

### Task 13: Integration test and smoke check

**Files:**
- No new files. Run existing test suite + manual browser check.

- [ ] **Step 1: Run backend tests**

```bash
python -m ruff check src/ tests/
python -m ruff format --check src/ tests/
python -m pytest tests/ -m "not slow" -x -v
```
Expected: All pass, no lint errors.

- [ ] **Step 2: Build frontend**

```bash
cd aegis-web && npm run build
```
Expected: Build succeeds with no TypeScript errors.

- [ ] **Step 3: Start dev server and test in browser**

Start: `cd aegis-web && npm run dev` (in background)
Start backend: `python -m aegis.viewer` (in background)

Test checklist:
- Click scene to place first antenna (creates it in antenna store)
- Verify antenna renders with pole and pattern
- Ctrl+click to add second antenna
- Verify both antennas render, second is selected (highlighted pole)
- Click first antenna's row in Antennas panel to select it
- Verify dosimetry computes and heatmap updates
- Delete one antenna via X button
- Verify remaining antenna stays selected
- Change power in AntennasPanel, verify recompute

- [ ] **Step 4: Final commit and push**

```bash
git add -A
git status  # review
git commit -m "Multi-antenna integration: final wiring and cleanup"
```

Push the feature branch and create PR:

```bash
git push -u origin feature/multi-antenna
gh pr create --title "Add multi-antenna support with array factor gain" \
  --body "## Summary
- Multiple independent antennas with per-antenna power and array config
- Backend computes array factor gain and merges paths via PropagationPaths.concatenate()
- New Antennas sidebar panel with antenna list and per-antenna config
- Ctrl+click to add, click to move selected
- Backward compatible: existing single-antenna workflow unchanged

Spec: docs/superpowers/specs/2026-04-10-multi-antenna-design.md" \
  --base master
gh pr merge --squash --delete-branch
git checkout master && git pull origin master
```
