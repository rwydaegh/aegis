# Fidelity refactor: modes + corrections

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the broken 0-8 level hierarchy with a mode + corrections architecture, fix the A_ab factor-of-4 bug, and add physics regression tests.

**Architecture:** Three computation modes (bound, aggregate, spatial) with composable correction flags (fresnel, polarisation, curvature, diffraction). Coherent mode (coherent, ecbf) stays as a separate track. Old level= integers map to mode+flags for backward compatibility. A unified spatial kernel replaces levels 2-6 (Level 2 = spatial with `fresnel=False`).

**Tech Stack:** NumPy core, JAX-compatible via `_array_backend.py` shim, pytest + Hypothesis for testing.

**Key references:**
- Theory: `theory/composability_analysis.md` (derivations and bug analysis)
- Monograph: `../monograph/monograph_v2.tex` (equations referenced by line number)
- Style: `.claude/rules/docs-style.md`

---

### Task 1: Fix A_ab factor-of-4 bug

The viewer and tests use `A_ab = total_area / 4` but the monograph defines
`A_ab = total_area` for convex bodies (eq. 2.23, line 2196). The `/4` is
already in the Level 1 formula. This causes Level 0/1 to underestimate
P_abs by 4x.

**Files:**
- Modify: `src/aegis/viewer/config.py:208`
- Modify: `src/aegis/viewer/compute.py:186-187`
- Modify: `tests/test_engine.py` (TestLevel0, TestLevel1 fixtures)
- Create: `tests/test_level_consistency.py`

- [ ] **Step 1: Write a test that exposes the bug**

In `tests/test_level_consistency.py`:

```python
"""Cross-level physics consistency tests."""

import numpy as np
import pytest

from aegis.engine import DosimetryEngine
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import SKIN_28GHZ
from tests.conftest import make_icosahedron


class TestAggregateSpatialConsistency:
    """Level 1 and Level 2 must give the same total absorbed power."""

    def test_p_abs_matches_with_correct_A_ab_and_D(self):
        """With correct A_ab and directivity, L1 P_abs == L2 P_abs."""
        body = make_icosahedron()
        k_hat = np.array([[1.0, 0.0, 0.0]])
        power = np.array([10.0])
        paths = PropagationPaths.from_powers(k_hat, power)
        engine = DosimetryEngine(SKIN_28GHZ)

        # Level 2: spatial ground truth
        r2 = engine.compute(body, paths, level=2)

        # Compute correct directivity from mesh
        mu_plus = np.maximum(body.normals @ np.array([-1.0, 0.0, 0.0]), 0.0)
        A_perp = float(np.sum(mu_plus * body.areas))
        mean_A_perp = body.total_area / 4.0  # Cauchy for convex
        D_val = A_perp / mean_A_perp

        # Level 1 with correct A_ab = total_area
        r1 = engine.compute(
            body, paths, level=1,
            A_ab=body.total_area,
            D_table=np.array([D_val]),
            D_dirs=np.array([[-1.0, 0.0, 0.0]]),
        )

        assert r1.p_abs == pytest.approx(r2.p_abs, rel=1e-6)

    def test_p_abs_multi_path(self):
        """Multi-path: L1 P_abs == L2 P_abs with per-path directivity."""
        body = make_icosahedron()
        rng = np.random.default_rng(42)
        N = 20
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        power = rng.uniform(0.5, 5.0, size=N)
        paths = PropagationPaths.from_powers(k_hat, power)
        engine = DosimetryEngine(SKIN_28GHZ)

        r2 = engine.compute(body, paths, level=2)

        # Compute per-direction directivity
        D_vals = np.zeros(N)
        mean_A_perp = body.total_area / 4.0
        for i in range(N):
            mu_plus = np.maximum(body.normals @ (-k_hat[i]), 0.0)
            D_vals[i] = float(np.sum(mu_plus * body.areas)) / mean_A_perp

        r1 = engine.compute(
            body, paths, level=1,
            A_ab=body.total_area,
            D_table=D_vals,
            D_dirs=-k_hat,
        )

        assert r1.p_abs == pytest.approx(r2.p_abs, rel=1e-6)
```

- [ ] **Step 2: Run test to confirm it fails with current A_ab**

Run: `py -3.12 -m pytest tests/test_level_consistency.py -x -v`
Expected: FAIL (L1 P_abs is 4x too small if old fixtures leak in)

- [ ] **Step 3: Fix the config default**

In `src/aegis/viewer/config.py`, change `convex_body_area_factor`:

```python
# Before:
"convex_body_area_factor": 0.25,
# After:
"convex_body_area_factor": 1.0,
```

- [ ] **Step 4: Fix the viewer compute comment**

In `src/aegis/viewer/compute.py` line 186, fix the comment:

```python
# Before:
# Cauchy formula: A_ab = A_total / 4 for convex bodies
extra_kwargs["A_ab"] = body.total_area * dos_cfg["convex_body_area_factor"]
# After:
# A_ab = total surface area for convex bodies (monograph eq. 2.23)
extra_kwargs["A_ab"] = body.total_area * dos_cfg["convex_body_area_factor"]
```

- [ ] **Step 5: Fix existing test fixtures that use A_ab = total_area/4**

In `tests/test_engine.py`, update TestLevel0 and any test that sets
`A_ab = ico_mesh.total_area / 4.0` to use `A_ab = ico_mesh.total_area`.
Update the expected values accordingly.

Search for all occurrences: `grep -n "A_ab.*total_area.*4" tests/`

- [ ] **Step 6: Run all fast tests**

Run: `py -3.12 -m pytest tests/ -m "not slow" -x -v`
Expected: all pass

- [ ] **Step 7: Lint and commit**

```bash
py -3.12 -m ruff check src/ tests/ && py -3.12 -m ruff format src/ tests/
git add src/aegis/viewer/config.py src/aegis/viewer/compute.py tests/test_level_consistency.py tests/test_engine.py
git commit -m "Fix A_ab factor-of-4 bug in Level 0/1

The monograph defines A_ab = total_area for convex bodies (eq. 2.23).
The /4 is already in the formula P_abs = T0 * (A_ab/4) * sum(S*D).
convex_body_area_factor was 0.25 (applying the factor twice), now 1.0.

Add cross-level consistency tests verifying L1 P_abs == L2 P_abs."
git push origin master
```

---

### Task 2: Create unified spatial kernel

Replace levels 3-6 with a single kernel that accepts correction flags.
Keep the old kernel files for now (they become thin wrappers).

**Files:**
- Create: `src/aegis/kernels/spatial.py`
- Modify: `src/aegis/kernels/_base.py` (add `physical_gelu` helper)
- Create: `tests/test_spatial_kernel.py`

- [ ] **Step 1: Write tests for the unified kernel**

In `tests/test_spatial_kernel.py`:

```python
"""Tests for the unified spatial kernel with composable corrections."""

import numpy as np
import pytest

from aegis.tissue.dielectric import SKIN_28GHZ
from tests.conftest import make_icosahedron, make_flat_mesh


@pytest.fixture
def setup():
    body = make_icosahedron()
    rng = np.random.default_rng(99)
    N = 10
    k_hat = rng.standard_normal((N, 3))
    k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
    power = rng.uniform(0.5, 3.0, size=N)
    n_tilde = SKIN_28GHZ.n_complex
    T0 = SKIN_28GHZ.T0
    freq_hz = SKIN_28GHZ.freq_hz
    curvature_H = np.full(body.n_triangles, 10.0)  # 10 m^-1
    return body, k_hat, power, n_tilde, T0, freq_hz, curvature_H


class TestUnifiedSpatialMatchesOldLevels:
    """Unified kernel with specific flags must match old per-level kernels."""

    def test_fresnel_off_matches_level2(self, setup):
        body, k_hat, power, n_tilde, T0, freq_hz, _ = setup
        from aegis.kernels.level2_geometric import level2_geometric
        from aegis.kernels.spatial import spatial_kernel

        expected = level2_geometric(body.normals, k_hat, power, T0)
        actual = spatial_kernel(
            body.normals, k_hat, power, n_tilde, T0, freq_hz,
            fresnel=False,
        )

        np.testing.assert_allclose(actual, expected, rtol=1e-12)

    def test_no_corrections_matches_level3(self, setup):
        body, k_hat, power, n_tilde, T0, freq_hz, _ = setup
        from aegis.kernels.level3_fresnel import level3_fresnel
        from aegis.kernels.spatial import spatial_kernel

        expected = level3_fresnel(body.normals, k_hat, power, n_tilde)
        actual = spatial_kernel(body.normals, k_hat, power, n_tilde, T0, freq_hz)

        np.testing.assert_allclose(actual, expected, rtol=1e-12)

    def test_polarisation_matches_level4(self, setup):
        body, k_hat, power, n_tilde, T0, freq_hz, _ = setup
        from aegis.kernels.level4_polarisation import level4_polarisation
        from aegis.kernels.spatial import spatial_kernel

        q = 0.5
        expected = level4_polarisation(body.normals, k_hat, power, n_tilde, q=q)
        actual = spatial_kernel(
            body.normals, k_hat, power, n_tilde, T0, freq_hz,
            polarisation=True, q=q,
        )

        np.testing.assert_allclose(actual, expected, rtol=1e-12)

    def test_curvature_matches_level5(self, setup):
        body, k_hat, power, n_tilde, T0, freq_hz, curvature_H = setup
        from aegis.kernels.level5_curvature import level5_curvature
        from aegis.kernels.spatial import spatial_kernel

        expected = level5_curvature(
            body.normals, k_hat, power, n_tilde, T0, curvature_H, freq_hz,
        )
        actual = spatial_kernel(
            body.normals, k_hat, power, n_tilde, T0, freq_hz,
            curvature=True, curvature_H=curvature_H,
        )

        np.testing.assert_allclose(actual, expected, rtol=1e-12)

    def test_curvature_diffraction_matches_level6(self, setup):
        body, k_hat, power, n_tilde, T0, freq_hz, curvature_H = setup
        from aegis.kernels.level6_diffraction import level6_diffraction
        from aegis.kernels.spatial import spatial_kernel

        expected = level6_diffraction(
            body.normals, k_hat, power, n_tilde, T0, curvature_H, freq_hz,
        )
        actual = spatial_kernel(
            body.normals, k_hat, power, n_tilde, T0, freq_hz,
            curvature=True, diffraction=True, curvature_H=curvature_H,
        )

        np.testing.assert_allclose(actual, expected, rtol=1e-12)

    def test_polarisation_curvature_new_combination(self, setup):
        """Pol + curvature: a combination the old system could not express."""
        body, k_hat, power, n_tilde, T0, freq_hz, curvature_H = setup
        from aegis.kernels.spatial import spatial_kernel

        sab = spatial_kernel(
            body.normals, k_hat, power, n_tilde, T0, freq_hz,
            polarisation=True, q=0.5,
            curvature=True, curvature_H=curvature_H,
        )
        assert sab.shape == (body.n_triangles,)
        assert np.all(np.isfinite(sab))

    def test_all_corrections_on(self, setup):
        """All three corrections: pol + curvature + diffraction."""
        body, k_hat, power, n_tilde, T0, freq_hz, curvature_H = setup
        from aegis.kernels.spatial import spatial_kernel

        sab = spatial_kernel(
            body.normals, k_hat, power, n_tilde, T0, freq_hz,
            polarisation=True, q=0.3,
            curvature=True, diffraction=True,
            curvature_H=curvature_H,
        )
        assert sab.shape == (body.n_triangles,)
        assert np.all(np.isfinite(sab))
        # With q=0 it should match level 6
        sab_q0 = spatial_kernel(
            body.normals, k_hat, power, n_tilde, T0, freq_hz,
            polarisation=True, q=0.0,
            curvature=True, diffraction=True,
            curvature_H=curvature_H,
        )
        from aegis.kernels.level6_diffraction import level6_diffraction
        expected = level6_diffraction(
            body.normals, k_hat, power, n_tilde, T0, curvature_H, freq_hz,
        )
        np.testing.assert_allclose(sab_q0, expected, rtol=1e-10)

    def test_polarisation_diffraction_no_curvature(self, setup):
        """Pol + diffraction without curvature additive term."""
        body, k_hat, power, n_tilde, T0, freq_hz, curvature_H = setup
        from aegis.kernels.spatial import spatial_kernel

        sab = spatial_kernel(
            body.normals, k_hat, power, n_tilde, T0, freq_hz,
            polarisation=True, q=0.5,
            diffraction=True,
            curvature_H=curvature_H,
        )
        assert sab.shape == (body.n_triangles,)
        assert np.all(np.isfinite(sab))
        # Without curvature term, should be T_eff * GELU @ power
        # Verify no curvature additive by comparing with curvature=True
        sab_with_curv = spatial_kernel(
            body.normals, k_hat, power, n_tilde, T0, freq_hz,
            polarisation=True, q=0.5,
            curvature=True, diffraction=True,
            curvature_H=curvature_H,
        )
        # Curvature adds power, so with_curv >= without (on average)
        assert float(np.sum(sab_with_curv * body.areas)) >= float(
            np.sum(sab * body.areas)
        ) - 1e-10

    def test_diffraction_requires_curvature_H(self, setup):
        body, k_hat, power, n_tilde, T0, freq_hz, _ = setup
        from aegis.kernels.spatial import spatial_kernel

        with pytest.raises(ValueError, match="curvature_H"):
            spatial_kernel(
                body.normals, k_hat, power, n_tilde, T0, freq_hz,
                diffraction=True,
            )

    def test_curvature_requires_curvature_H(self, setup):
        body, k_hat, power, n_tilde, T0, freq_hz, _ = setup
        from aegis.kernels.spatial import spatial_kernel

        with pytest.raises(ValueError, match="curvature_H"):
            spatial_kernel(
                body.normals, k_hat, power, n_tilde, T0, freq_hz,
                curvature=True,
            )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `py -3.12 -m pytest tests/test_spatial_kernel.py -x -v`
Expected: ImportError (spatial_kernel does not exist yet)

- [ ] **Step 3: Move physical_gelu to _base.py**

In `src/aegis/kernels/_base.py`, add at the bottom:

```python
from aegis._array_backend import erf


def physical_gelu(mu, sigma):
    """Physical GELU: mu * (1/2)[1 + erf(mu / sigma)].

    Replaces ReLU at the shadow boundary with a diffraction-smoothed
    transition (monograph eq. 2.44). Width sigma = sqrt(lambda*H/(4*pi)).
    """
    sigma_safe = xp.where(sigma > 0, sigma, 1e-30)
    z = mu / sigma_safe[:, None]
    return mu * 0.5 * (1.0 + erf(z))
```

- [ ] **Step 4: Implement the unified spatial kernel**

Create `src/aegis/kernels/spatial.py`:

```python
"""Unified spatial kernel with composable physics corrections.

Computes per-triangle S_ab from the general incoherent formula:

    S_ab = T(mu, q) * g(mu, sigma) @ power + T0 * (H/k) * g(mu, sigma)^2 @ power

where:
    T = T_avg + (q/2)*DeltaT  (with polarisation) or T_avg (without)
    g = GELU(mu, sigma)        (with diffraction)  or ReLU(mu) (without)
    curvature term present or absent

See theory/composability_analysis.md for derivation and limiting cases.
"""

from __future__ import annotations

from aegis._array_backend import jit, xp
from aegis.constants import C_0
from aegis.kernels._base import fresnel_weights, incidence_geometry, physical_gelu


@jit
def spatial_kernel(
    normals,
    k_hat,
    power,
    n_tilde,
    T0,
    freq_hz,
    *,
    fresnel: bool = True,
    polarisation: bool = False,
    q: float = 0.0,
    curvature: bool = False,
    diffraction: bool = False,
    curvature_H=None,
):
    """Compute per-triangle S_ab with composable physics corrections.

    Parameters
    ----------
    normals : (M, 3) unit outward normals
    k_hat : (N, 3) incident directions
    power : (N,) per-path power density [W/m^2]
    n_tilde : complex refractive index
    T0 : normal-incidence transmission coefficient
    freq_hz : frequency [Hz]
    fresnel : use angle-dependent T_avg(mu) instead of constant T0
    polarisation : enable polarisation correction (requires fresnel=True)
    q : TM excess parameter (scalar or (N,) array), used if polarisation=True
    curvature : enable curvature correction (requires curvature_H)
    diffraction : enable diffraction smoothing (requires curvature_H)
    curvature_H : (M,) twice mean curvature per triangle [1/m]

    Returns
    -------
    sab : (M,) absorbed power density per triangle [W/m^2]
    """
    if (curvature or diffraction) and curvature_H is None:
        raise ValueError("curvature_H is required when curvature=True or diffraction=True")

    mu, mu_plus = incidence_geometry(normals, k_hat)

    # Fresnel factor
    if fresnel:
        T_s, T_p, T_avg = fresnel_weights(mu, n_tilde)
        if polarisation:
            DeltaT = T_p - T_s
            T = T_avg + 0.5 * q * DeltaT
        else:
            T = T_avg
    else:
        T = T0  # constant, broadcasts over (M, N)

    # Activation: ReLU or GELU (with diffraction)
    if diffraction:
        wavelength = C_0 / freq_hz
        H_safe = xp.maximum(curvature_H, 0.0)
        sigma = xp.sqrt(xp.maximum(wavelength * H_safe / (4.0 * xp.pi), 0.0))
        g = physical_gelu(mu, sigma)
    else:
        g = mu_plus

    sab = (T * g) @ power

    # Curvature correction: additive perturbative term
    if curvature:
        k = 2.0 * xp.pi * freq_hz / C_0
        H_for_curv = xp.maximum(curvature_H, 0.0) if not diffraction else H_safe
        g_sq = g ** 2
        sab_curvature = T0 * ((H_for_curv / k)[:, None] * g_sq) @ power
        sab = sab + sab_curvature

    if curvature or diffraction:
        sab = xp.maximum(sab, 0.0)

    return sab
```

- [ ] **Step 5: Run tests**

Run: `py -3.12 -m pytest tests/test_spatial_kernel.py -x -v`
Expected: all pass

- [ ] **Step 6: Lint and commit**

```bash
py -3.12 -m ruff check src/ tests/ && py -3.12 -m ruff format src/ tests/
git add src/aegis/kernels/spatial.py src/aegis/kernels/_base.py tests/test_spatial_kernel.py
git commit -m "Add unified spatial kernel with composable corrections

Single kernel handles all incoherent spatial combinations:
polarisation, curvature, diffraction (any subset). Matches old
level 2-6 kernels exactly in their respective configurations.
fresnel=False matches Level 2 (constant T0).
Old kernel files kept as-is for backward compatibility."
git push origin master
```

Also update `level6_diffraction.py` to import `physical_gelu` from `_base`
instead of defining its own `_physical_gelu` (deduplication).

---

### Task 3: Refactor engine to mode-based API

Add a `mode=` parameter to `DosimetryEngine.compute()` alongside the
existing `level=` for backward compatibility. The level parameter maps
to mode + flags internally.

**Files:**
- Modify: `src/aegis/engine.py`
- Create: `tests/test_engine_modes.py`

- [ ] **Step 1: Write tests for the new mode API**

In `tests/test_engine_modes.py`:

```python
"""Tests for mode-based engine API."""

import numpy as np
import pytest

from aegis.engine import DosimetryEngine
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import SKIN_28GHZ
from tests.conftest import make_icosahedron


@pytest.fixture
def setup():
    body = make_icosahedron()
    rng = np.random.default_rng(77)
    N = 15
    k_hat = rng.standard_normal((N, 3))
    k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
    power = rng.uniform(0.5, 3.0, size=N)
    paths = PropagationPaths.from_powers(k_hat, power)
    engine = DosimetryEngine(SKIN_28GHZ)
    return engine, body, paths


class TestModeAPI:
    def test_spatial_default_matches_level3(self, setup):
        engine, body, paths = setup
        r_mode = engine.compute(body, paths, mode="spatial")
        r_level = engine.compute(body, paths, level=3)
        np.testing.assert_allclose(r_mode.sab, r_level.sab, rtol=1e-12)

    def test_spatial_with_polarisation_matches_level4(self, setup):
        engine, body, paths = setup
        r_mode = engine.compute(body, paths, mode="spatial", polarisation=True, q=0.5)
        r_level = engine.compute(body, paths, level=4, q=0.5)
        np.testing.assert_allclose(r_mode.sab, r_level.sab, rtol=1e-12)

    def test_spatial_new_combination(self, setup):
        """Pol + curvature: mode API enables what level API could not."""
        engine, body, paths = setup
        H = np.full(body.n_triangles, 5.0)
        r = engine.compute(
            body, paths, mode="spatial",
            polarisation=True, q=0.3,
            curvature=True, curvature_H=H,
        )
        assert r.sab.shape == (body.n_triangles,)
        assert r.p_abs > 0

    def test_backward_compat_level_still_works(self, setup):
        engine, body, paths = setup
        r = engine.compute(body, paths, level=2)
        assert r.fidelity_level == 2
        assert r.p_abs > 0

    def test_level_and_mode_exclusive(self, setup):
        engine, body, paths = setup
        with pytest.raises(ValueError, match="Cannot specify both"):
            engine.compute(body, paths, level=2, mode="spatial")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `py -3.12 -m pytest tests/test_engine_modes.py -x -v`
Expected: FAIL (mode parameter not accepted yet)

- [ ] **Step 3: Implement mode-based dispatch in engine.py**

In `src/aegis/engine.py`, modify the `compute()` method signature to
accept `mode=` and correction flags. Add a `_level_to_mode()` mapping
for backward compat. Route spatial modes through the unified kernel.

Key changes to `compute()`:
- Add parameters: `mode`, `fresnel`, `polarisation`, `diffraction`
- Add mapping: `level=2` maps to `mode="spatial", fresnel=False`;
  `level=3` maps to `mode="spatial"`; `level=4` maps to
  `mode="spatial", polarisation=True`, etc.
- For `mode="spatial"`, call `spatial_kernel()` with the appropriate flags
- Raise `ValueError` if both `level` and `mode` are given

Update `DosimetryResult` in `src/aegis/result.py`:
- Add `mode: str | None = None` field (default None for backward compat)
- Add `corrections: tuple[str, ...] = ()` field listing active corrections

Update `compute_sab()` to also accept `mode=` and correction flags,
since this method is the JAX-differentiable entry point.

- [ ] **Step 4: Run all tests**

Run: `py -3.12 -m pytest tests/ -m "not slow" -x -v`
Expected: all pass (both old level= and new mode= APIs work)

- [ ] **Step 5: Lint and commit**

```bash
py -3.12 -m ruff check src/ tests/ && py -3.12 -m ruff format src/ tests/
git add src/aegis/engine.py src/aegis/result.py tests/test_engine_modes.py
git commit -m "Add mode-based engine API with composable corrections

New mode= parameter: 'bound', 'aggregate', 'spatial', 'coherent', 'ecbf'.
Spatial mode accepts polarisation=, curvature=, diffraction= flags.
Old level= parameter still works via internal mapping.
DosimetryResult now stores mode and active corrections."
git push origin master
```

---

### Task 4: Add physics regression tests

End-to-end tests with realistic scenarios. These are regression tests:
they lock in known-good values from the current (corrected) implementation.

**Files:**
- Create: `tests/test_physics_regression.py`

- [ ] **Step 1: Write the regression test file**

```python
"""Physics regression tests: realistic scenarios with locked-in values.

These tests verify that the dosimetry pipeline produces consistent results
across code changes. Values were computed once and verified against the
monograph. If a test fails, the physics changed: investigate before updating.
"""

import numpy as np
import pytest

from aegis.engine import DosimetryEngine
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import SKIN_28GHZ
from tests.conftest import make_icosahedron


class TestSingleWaveFrontIllumination:
    """Single plane wave hitting a convex body from the front."""

    def test_level2_p_abs_icosahedron(self):
        body = make_icosahedron()
        k_hat = np.array([[1.0, 0.0, 0.0]])
        power = np.array([10.0])  # 10 W/m^2
        paths = PropagationPaths.from_powers(k_hat, power)
        engine = DosimetryEngine(SKIN_28GHZ)

        r = engine.compute(body, paths, level=2)

        # T0 * S * A_perp(+x): compute analytically
        mu_plus = np.maximum(body.normals @ np.array([-1.0, 0.0, 0.0]), 0.0)
        A_perp = float(np.sum(mu_plus * body.areas))
        expected = SKIN_28GHZ.T0 * 10.0 * A_perp
        assert r.p_abs == pytest.approx(expected, rel=1e-6)
        assert r.p_abs > 0
        # Bound: P_abs <= T0 * S * total_area
        assert r.p_abs <= SKIN_28GHZ.T0 * 10.0 * body.total_area * 1.001

    def test_level3_more_accurate_than_level2(self):
        """Level 3 (Fresnel) should differ from Level 2 (T0) by < 10%."""
        body = make_icosahedron()
        k_hat = np.array([[1.0, 0.0, 0.0]])
        power = np.array([10.0])
        paths = PropagationPaths.from_powers(k_hat, power)
        engine = DosimetryEngine(SKIN_28GHZ)

        r2 = engine.compute(body, paths, level=2)
        r3 = engine.compute(body, paths, level=3)

        rel_diff = abs(r3.p_abs - r2.p_abs) / r2.p_abs
        assert rel_diff < 0.10  # monograph: ~0.35% for complex bodies


class TestMultipathDiffuse:
    """Many paths from random directions (quasi-diffuse environment)."""

    def test_diffuse_50_paths(self):
        body = make_icosahedron()
        rng = np.random.default_rng(2026)
        N = 50
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        power = np.ones(N)  # 1 W/m^2 each
        paths = PropagationPaths.from_powers(k_hat, power)
        engine = DosimetryEngine(SKIN_28GHZ)

        r2 = engine.compute(body, paths, level=2)
        r3 = engine.compute(body, paths, level=3)

        # For diffuse: P_abs ~ T0 * S_total * A_total / 4
        expected = SKIN_28GHZ.T0 * N * body.total_area / 4.0
        assert r2.p_abs == pytest.approx(expected, rel=0.15)
        assert abs(r3.p_abs - r2.p_abs) / r2.p_abs < 0.10


class TestCorrectionComposability:
    """Combined corrections produce physically reasonable results."""

    def test_polarisation_bounded_by_TE_TM_extremes(self):
        body = make_icosahedron()
        k_hat = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
        power = np.array([5.0, 3.0])
        paths = PropagationPaths.from_powers(k_hat, power)
        engine = DosimetryEngine(SKIN_28GHZ)

        r_te = engine.compute(body, paths, level=4, q=-1.0)   # full TE
        r_avg = engine.compute(body, paths, level=4, q=0.0)    # unpolarised
        r_tm = engine.compute(body, paths, level=4, q=1.0)     # full TM

        # TM absorbs more than TE at oblique angles
        assert r_tm.p_abs >= r_avg.p_abs
        assert r_avg.p_abs >= r_te.p_abs

    def test_all_corrections_energy_conservation(self):
        body = make_icosahedron()
        rng = np.random.default_rng(42)
        N = 20
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        power = rng.uniform(1.0, 5.0, size=N)
        paths = PropagationPaths.from_powers(k_hat, power)
        engine = DosimetryEngine(SKIN_28GHZ)
        H = np.full(body.n_triangles, 10.0)

        from aegis.kernels.spatial import spatial_kernel
        sab = spatial_kernel(
            body.normals, k_hat, power,
            SKIN_28GHZ.n_complex, SKIN_28GHZ.T0, SKIN_28GHZ.freq_hz,
            polarisation=True, q=0.5,
            curvature=True, diffraction=True,
            curvature_H=H,
        )

        p_abs = float(np.sum(sab * body.areas))
        upper_bound = float(np.sum(power)) * body.total_area
        assert p_abs <= upper_bound
        assert p_abs > 0


class TestAggregateSpatialEquivalence:
    """Level 1 (aggregate) and Level 2 (spatial) give same P_abs."""

    def test_single_direction(self):
        body = make_icosahedron()
        k_hat = np.array([[0.0, 0.0, -1.0]])
        power = np.array([10.0])
        paths = PropagationPaths.from_powers(k_hat, power)
        engine = DosimetryEngine(SKIN_28GHZ)

        r2 = engine.compute(body, paths, level=2)

        # Compute A_perp and D for this direction
        mu_plus = np.maximum(body.normals @ np.array([0.0, 0.0, 1.0]), 0.0)
        A_perp = float(np.sum(mu_plus * body.areas))
        mean_A_perp = body.total_area / 4.0
        D = A_perp / mean_A_perp

        r1 = engine.compute(
            body, paths, level=1,
            A_ab=body.total_area,
            D_table=np.array([D]),
            D_dirs=np.array([[0.0, 0.0, 1.0]]),
        )

        assert r1.p_abs == pytest.approx(r2.p_abs, rel=1e-6)
```

- [ ] **Step 2: Run tests**

Run: `py -3.12 -m pytest tests/test_physics_regression.py -x -v`
Expected: all pass

- [ ] **Step 3: Commit**

```bash
git add tests/test_physics_regression.py
git commit -m "Add physics regression tests for cross-level consistency

Tests lock in: single-wave P_abs, diffuse-environment approximation,
polarisation bounds (TE <= avg <= TM), energy conservation with all
corrections, and aggregate-spatial P_abs equivalence."
git push origin master
```

---

### Task 5: Update documentation

Rewrite the fidelity levels page to reflect modes + corrections. Follow
`.claude/rules/docs-style.md` strictly.

**Files:**
- Modify: `docs/user_guide/fidelity_levels.md`
- Modify: `docs/user_guide/overview.md` (brief mention of new API)

- [ ] **Step 1: Rewrite fidelity_levels.md**

The new structure:

1. **Computation modes** (bound, aggregate, spatial, coherent, ecbf) with
   cost and output
2. **Physics corrections** (fresnel, polarisation, curvature, diffraction)
   with what each adds, when to use, required data
3. **Quick reference table** mapping old levels to new mode + flags
4. **Code examples** showing mode= API

Follow docs-style.md: sentence case headings, no em dashes, no semicolons,
no promotional language. Use `$` for inline math.

- [ ] **Step 2: Update overview.md**

Add a brief note about the mode= API in the "Computing dosimetry" section.
Keep the level= mention for backward compat but mark it as legacy.

- [ ] **Step 3: Preview docs locally**

Run: `py -3.12 -m mkdocs serve`
Check the fidelity page renders correctly with MathJax.

- [ ] **Step 4: Lint and commit**

```bash
py -3.12 -m ruff check src/ tests/
git add docs/user_guide/fidelity_levels.md docs/user_guide/overview.md
git commit -m "Rewrite fidelity docs: modes + composable corrections

Replace the linear 0-8 hierarchy with computation modes (bound,
aggregate, spatial, coherent, ecbf) plus independent physics
corrections (polarisation, curvature, diffraction). Add quick
reference table mapping old levels to new API."
git push origin master
```

---

### Task 6: Wire viewer to use mode API

Update the viewer compute pipeline to use the new mode-based engine API.
This also lets the viewer expose correction checkboxes in the future.

**Files:**
- Modify: `src/aegis/viewer/compute.py`

- [ ] **Step 1: Update viewer compute to use mode= for levels >= 2**

In `compute_dosimetry()`, when the level is 2-6, translate to the
appropriate mode + flags call. Levels 0-1 stay as-is (they use A_ab).
Levels 7-8 stay as-is (coherent track).

For levels 2-6:
- level 2: `mode="spatial", fresnel=False` (constant T0)
- level 3: `mode="spatial"` (with Fresnel, which is the default)
- level 4: `mode="spatial", polarisation=True`
- level 5: `mode="spatial", curvature=True`
- level 6: `mode="spatial", curvature=True, diffraction=True`

- [ ] **Step 2: Run fast tests**

Run: `py -3.12 -m pytest tests/ -m "not slow" -x`
Expected: all pass

- [ ] **Step 3: Commit**

```bash
git add src/aegis/viewer/compute.py
git commit -m "Wire viewer to mode-based engine API

Viewer compute translates level selection to mode + correction
flags internally. No user-facing changes yet."
git push origin master
```

---

### Task 7: Verify differentiability

Ensure the unified spatial kernel works under JAX JIT and grad.
This is a verification task, not new code (the `@jit` decorator and
`xp` backend should already handle it).

**Files:**
- Create: `tests/test_differentiable.py`

- [ ] **Step 1: Write a differentiability test**

```python
"""Verify the spatial kernel is differentiable via JAX (when available)."""

import numpy as np
import pytest

from aegis._array_backend import JAX_AVAILABLE
from aegis.tissue.dielectric import SKIN_28GHZ
from tests.conftest import make_icosahedron

pytestmark = pytest.mark.skipif(not JAX_AVAILABLE, reason="JAX not installed")


@pytest.fixture
def setup():
    body = make_icosahedron()
    k_hat = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    power = np.array([5.0, 3.0])
    return body, k_hat, power


def test_spatial_kernel_jit(setup):
    """spatial_kernel runs under jax.jit without error."""
    import jax
    import jax.numpy as jnp
    from aegis.kernels.spatial import spatial_kernel

    body, k_hat, power = setup

    @jax.jit
    def f(power_jax):
        return spatial_kernel(
            jnp.array(body.normals), jnp.array(k_hat), power_jax,
            SKIN_28GHZ.n_complex, SKIN_28GHZ.T0, SKIN_28GHZ.freq_hz,
        )

    sab = f(jnp.array(power))
    assert sab.shape == (body.n_triangles,)


def test_spatial_kernel_grad_wrt_power(setup):
    """Gradient of total P_abs w.r.t. path powers exists and is finite."""
    import jax
    import jax.numpy as jnp
    from aegis.kernels.spatial import spatial_kernel

    body, k_hat, power = setup
    normals_j = jnp.array(body.normals)
    k_hat_j = jnp.array(k_hat)
    areas_j = jnp.array(body.areas)

    def p_abs(power_jax):
        sab = spatial_kernel(
            normals_j, k_hat_j, power_jax,
            SKIN_28GHZ.n_complex, SKIN_28GHZ.T0, SKIN_28GHZ.freq_hz,
        )
        return jnp.sum(sab * areas_j)

    grad_fn = jax.grad(p_abs)
    g = grad_fn(jnp.array(power))
    assert g.shape == (2,)
    assert jnp.all(jnp.isfinite(g))
    assert jnp.all(g >= 0)  # more power in = more absorption


def test_spatial_kernel_grad_with_all_corrections(setup):
    """Gradient works with all corrections enabled (GELU is smooth)."""
    import jax
    import jax.numpy as jnp
    from aegis.kernels.spatial import spatial_kernel

    body, k_hat, power = setup
    normals_j = jnp.array(body.normals)
    k_hat_j = jnp.array(k_hat)
    areas_j = jnp.array(body.areas)
    H = jnp.full(body.n_triangles, 10.0)

    def p_abs(power_jax):
        sab = spatial_kernel(
            normals_j, k_hat_j, power_jax,
            SKIN_28GHZ.n_complex, SKIN_28GHZ.T0, SKIN_28GHZ.freq_hz,
            polarisation=True, q=0.3,
            curvature=True, diffraction=True,
            curvature_H=H,
        )
        return jnp.sum(sab * areas_j)

    grad_fn = jax.grad(p_abs)
    g = grad_fn(jnp.array(power))
    assert jnp.all(jnp.isfinite(g))
```

- [ ] **Step 2: Run (skip if no JAX)**

Run: `py -3.12 -m pytest tests/test_differentiable.py -x -v`
Expected: PASS if JAX installed, SKIP otherwise

- [ ] **Step 3: If JIT fails, fix the kernel**

The most common issue: Python `if` branches on boolean flags are not
JIT-compatible in JAX (they need to be traced as static). Fix by adding
`static_argnums` to the `@jit` decorator for the boolean flags, or use
`jax.lax.cond`. The `@jit` in `_array_backend.py` is a no-op for NumPy
so NumPy path is unaffected.

If the `@jit` on `spatial_kernel` needs static args:
```python
# At the top of spatial.py, instead of bare @jit:
from aegis._array_backend import jit as _jit

def _make_jit():
    from aegis._array_backend import JAX_AVAILABLE
    if JAX_AVAILABLE:
        import jax
        return jax.jit(spatial_kernel, static_argnames=[
            'polarisation', 'curvature', 'diffraction',
        ])
    return spatial_kernel
```

Or simply do not `@jit` the outer function and let `compute_sab` in the
engine handle JIT boundaries.

- [ ] **Step 4: Commit**

```bash
git add tests/test_differentiable.py
# If kernel changes were needed:
git add src/aegis/kernels/spatial.py
git commit -m "Add differentiability tests for spatial kernel

Verify JIT compilation and gradient computation through the unified
kernel, including with all corrections enabled (GELU is smooth).
Tests skip when JAX is not installed."
git push origin master
```

---

### Task 8: Final integration test and tag

Run the full test suite, push, and tag.

- [ ] **Step 1: Run full test suite**

Run: `py -3.12 -m pytest tests/ -m "not slow" -x -v`
Expected: all pass

- [ ] **Step 2: Run lint**

Run: `py -3.12 -m ruff check src/ tests/ && py -3.12 -m ruff format --check src/ tests/`

- [ ] **Step 3: Push and tag**

```bash
git push origin master
git tag v0.5.0
git push origin master --tags
gh release create v0.5.0 --generate-notes
```

Version bump rationale: new feature (mode API, unified kernel, new
correction combinations). The A_ab bug fix is a meaningful capability
change (Level 0/1 now give correct results).
