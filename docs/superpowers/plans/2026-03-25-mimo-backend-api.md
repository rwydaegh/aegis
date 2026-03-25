# MIMO backend API routes (phase 2b) implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three MIMO API endpoints (`/api/mimo/compute`, `/api/mimo/result/<user_id>`, `/api/mimo/summary`) with session-scoped caching and MIMO config defaults, enabling the frontend to orchestrate multi-user dosimetry.

**Architecture:** A new route module `src/aegis/viewer/routes/mimo.py` follows the existing `register(app, cache, cache_lock)` pattern. It uses the phase 1 `MIMOScene`/`UserState`/`AntennaArray` data model to build scenes from request JSON, orchestrates per-user compute through the existing `DosimetryEngine`, and caches results keyed by user ID. A `compute_mimo_scene()` helper in `src/aegis/mimo/compute.py` encapsulates the orchestration loop (load bodies, generate/expand paths, build G_tilde/Q/h, compute MRT precoder, compute per-user sab). Phase 2a precoders (ZF, MMSE) are not yet available, so MRT is the only precoder for now. The route module stubs the precoder dispatch to MRT and will wire in others when 2a merges.

**Tech Stack:** Python 3.12, Flask, NumPy, existing aegis engine/tissue/paths/coherent/mimo packages.

**Spec:** `docs/design/multi-user-mimo-decisions.md` sections F1-F4, G+.

---

## File structure

| File | Action | Responsibility |
|------|--------|----------------|
| `src/aegis/mimo/compute.py` | Create | `compute_mimo_scene()` orchestrator: per-user path generation, G_tilde/Q/h, MRT precoder, per-user sab. Pure Python, no Flask dependency. |
| `src/aegis/mimo/__init__.py` | Modify | Export `compute_mimo_scene` |
| `src/aegis/viewer/routes/mimo.py` | Create | Three endpoints: POST compute, GET result, GET summary. Follows existing route module pattern. |
| `src/aegis/viewer/config.py` | Modify | Add `"mimo"` section to DEFAULTS |
| `src/aegis/viewer/server.py` | Modify (L397-403) | Import and register MIMO route module |
| `tests/test_mimo_compute.py` | Create | Unit tests for `compute_mimo_scene()` |
| `tests/viewer/test_mimo_api.py` | Create | Flask test client integration tests for all three endpoints |

---

### Task 1: MIMO config defaults

**Files:**
- Modify: `src/aegis/viewer/config.py` (insert after `"dosimetry"` section, ~L223)
- Test: `tests/viewer/test_mimo_api.py` (created in task 5, but config tested here inline)

- [ ] **Step 1: Write the failing test**

Create `tests/viewer/test_mimo_config.py`:

```python
"""Tests for MIMO config defaults."""

from aegis.viewer.config import DEFAULTS


def test_mimo_defaults_present():
    """DEFAULTS has a 'mimo' key with required subkeys."""
    mimo = DEFAULTS["mimo"]
    assert isinstance(mimo["enabled"], bool)
    assert mimo["enabled"] is False
    assert isinstance(mimo["array"], dict)
    assert mimo["array"]["type"] == "upa"
    assert mimo["array"]["n_h"] == 4
    assert mimo["array"]["n_v"] == 4
    assert isinstance(mimo["users"], list)
    assert mimo["precoder"] == "mrt"
    assert isinstance(mimo["max_users"], int)


def test_mimo_array_defaults():
    """Array config has element spacing in wavelength fractions and geometry."""
    arr = DEFAULTS["mimo"]["array"]
    assert arr["d_h_wavelengths"] == 0.5
    assert arr["d_v_wavelengths"] == 0.5
    assert len(arr["position"]) == 3
    assert len(arr["broadside"]) == 3


def test_mimo_default_user():
    """Default user list has one entry with required fields."""
    users = DEFAULTS["mimo"]["users"]
    assert len(users) == 1
    user = users[0]
    assert "id" in user
    assert "phantom" in user
    assert "position" in user
    assert "device_offset" in user
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/viewer/test_mimo_config.py -v`
Expected: FAIL with `KeyError: 'mimo'`

- [ ] **Step 3: Add MIMO section to DEFAULTS**

In `src/aegis/viewer/config.py`, insert after the `"dosimetry"` section (after line ~223, before `"colormap"`):

```python
    "mimo": {
        "enabled": False,
        "array": {
            "type": "upa",
            "n_h": 4,
            "n_v": 4,
            "d_h_wavelengths": 0.5,
            "d_v_wavelengths": 0.5,
            "position": [5.0, 0.0, 3.0],
            "broadside": [-1.0, 0.0, 0.0],
        },
        "users": [
            {
                "id": "user_0",
                "phantom": "thelonious",
                "position": [0.0, 0.0, 0.0],
                "orientation": 0.0,
                "device_offset": [0.25, 0.0, 1.4],
            },
        ],
        "precoder": "mrt",
        "exposure_budget_mw": 100,
        "max_users": 8,
    },
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/viewer/test_mimo_config.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add src/aegis/viewer/config.py tests/viewer/test_mimo_config.py
git commit -m "Add MIMO config defaults to viewer config"
```

---

### Task 2: Compute orchestrator (`compute_mimo_scene`)

This is the core compute function that the route will call. It lives in `src/aegis/mimo/compute.py` so it can be tested without Flask.

**Files:**
- Create: `src/aegis/mimo/compute.py`
- Modify: `src/aegis/mimo/__init__.py`
- Test: `tests/test_mimo_compute.py`

**Context the implementing agent needs:**
- `DosimetryEngine` is in `src/aegis/engine.py`. Call: `engine = DosimetryEngine(tissue)`, then `result = engine.compute(body, paths, level=level)`.
- `compute_body_channel` is in `src/aegis/coherent/body_channel.py`. It returns `G_tilde` of shape `(M_tri, 3, M_ant)`.
- `compute_exposure_operator` is in `src/aegis/coherent/exposure.py`. It returns `Q` of shape `(M_ant, M_ant)`.
- `expand_paths_to_array` is in `src/aegis/mimo/array_paths.py`.
- `compute_channel_vector` is in `src/aegis/mimo/channel.py`.
- `PropagationPaths.from_powers()` creates incoherent paths from k_hat + power arrays.
- For coherent compute, we need `PropagationPaths` with complex `psi` (not just power). The existing `compute_dosimetry` in `viewer/compute.py` synthesizes paths; our orchestrator does the same but expanded to per-element.
- MRT precoder for user k: `w_k = h_k* / ||h_k|| * sqrt(P/K)` where `P = total_power`, `K = n_users`.
- Per-user sab with multi-user precoder W: `sab_u[m] = sum_k |G_tilde_u[m] @ w_k|^2 = ||G_tilde_u[m] @ W||_F^2` (Frobenius norm squared per triangle).

- [ ] **Step 1: Write failing tests**

Create `tests/test_mimo_compute.py`:

```python
"""Tests for the MIMO compute orchestrator."""

from __future__ import annotations

import numpy as np
import pytest

from aegis.mimo import AntennaArray, MIMOScene, UserConfig, UserState


@pytest.fixture
def simple_array():
    """Single-element array at [5, 0, 3]."""
    return AntennaArray(
        element_positions=np.array([[5.0, 0.0, 3.0]]),
        reference_position=np.array([5.0, 0.0, 3.0]),
    )


@pytest.fixture
def two_element_array():
    """2-element array for basic MIMO tests."""
    return AntennaArray.upa(
        n_h=2, n_v=1,
        d_h=0.5 * 0.0107,  # lambda/2 at 28 GHz
        d_v=0.0107,
        center=np.array([5.0, 0.0, 3.0]),
        broadside=np.array([-1.0, 0.0, 0.0]),
    )


@pytest.fixture
def user_config_a():
    return UserConfig(
        user_id="user_a",
        phantom_name="thelonious",
        position=np.array([0.0, 0.0, 0.0]),
        device_position=np.array([0.25, 0.0, 1.4]),
        device_orientation=np.array([0.0, 0.0, 1.0]),
    )


@pytest.fixture
def user_config_b():
    return UserConfig(
        user_id="user_b",
        phantom_name="thelonious",
        position=np.array([0.0, 2.0, 0.0]),
        device_position=np.array([0.25, 2.0, 1.4]),
        device_orientation=np.array([0.0, 0.0, 1.0]),
    )


class TestMRTPrecoder:
    """Test MRT precoder computation."""

    def test_mrt_shape(self, two_element_array):
        from aegis.mimo.compute import compute_mrt_precoder

        H = np.array([
            [1 + 0j, 0.5 + 0.5j],
            [0.5 - 0.5j, 1 + 0j],
        ])  # (K=2, M=2)
        W = compute_mrt_precoder(H, total_power=1.0)
        assert W.shape == (2, 2)  # (M_ant, K)

    def test_mrt_conjugate_direction(self):
        from aegis.mimo.compute import compute_mrt_precoder

        h = np.array([[1 + 1j, 0 + 0j]])  # K=1, M=2
        W = compute_mrt_precoder(h, total_power=1.0)
        # MRT direction should be conjugate of h, normalized
        expected_dir = np.conj(h[0]) / np.linalg.norm(h[0])
        actual_dir = W[:, 0] / np.linalg.norm(W[:, 0])
        np.testing.assert_allclose(actual_dir, expected_dir, atol=1e-10)

    def test_mrt_equal_power_per_user(self):
        from aegis.mimo.compute import compute_mrt_precoder

        H = np.array([
            [1 + 0j, 0 + 0j],
            [0 + 0j, 1 + 0j],
        ])
        P = 2.0
        W = compute_mrt_precoder(H, total_power=P)
        # Each column should have power P/K = 1.0
        for k in range(2):
            np.testing.assert_allclose(
                np.linalg.norm(W[:, k]) ** 2, P / 2, atol=1e-10,
            )

    def test_mrt_total_power(self):
        from aegis.mimo.compute import compute_mrt_precoder

        rng = np.random.default_rng(42)
        H = rng.standard_normal((3, 8)) + 1j * rng.standard_normal((3, 8))
        P = 5.0
        W = compute_mrt_precoder(H, total_power=P)
        np.testing.assert_allclose(
            np.linalg.norm(W, "fro") ** 2, P, atol=1e-10,
        )


class TestComputeUserSab:
    """Test per-user sab computation from G_tilde and W."""

    def test_sab_shape(self):
        from aegis.mimo.compute import compute_user_sab

        M_tri, M_ant, K = 100, 4, 2
        rng = np.random.default_rng(0)
        G_tilde = rng.standard_normal((M_tri, 3, M_ant)) + 1j * rng.standard_normal((M_tri, 3, M_ant))
        W = rng.standard_normal((M_ant, K)) + 1j * rng.standard_normal((M_ant, K))
        sab = compute_user_sab(G_tilde, W)
        assert sab.shape == (M_tri,)

    def test_sab_nonnegative(self):
        from aegis.mimo.compute import compute_user_sab

        rng = np.random.default_rng(1)
        G_tilde = rng.standard_normal((50, 3, 4)) + 1j * rng.standard_normal((50, 3, 4))
        W = rng.standard_normal((4, 2)) + 1j * rng.standard_normal((4, 2))
        sab = compute_user_sab(G_tilde, W)
        assert np.all(sab >= 0)

    def test_sab_single_user_matches_single_column(self):
        """With K=1, sab = |G_tilde @ w|^2 summed over polarization."""
        from aegis.mimo.compute import compute_user_sab

        rng = np.random.default_rng(2)
        M_tri, M_ant = 30, 4
        G_tilde = rng.standard_normal((M_tri, 3, M_ant)) + 1j * rng.standard_normal((M_tri, 3, M_ant))
        w = rng.standard_normal((M_ant, 1)) + 1j * rng.standard_normal((M_ant, 1))

        sab = compute_user_sab(G_tilde, w)
        # Manual: for each triangle, ||G_tilde[m] @ w||^2
        expected = np.array([
            np.linalg.norm(G_tilde[m] @ w[:, 0]) ** 2 for m in range(M_tri)
        ])
        np.testing.assert_allclose(sab, expected, atol=1e-10)


class TestComputeExposureQuadratic:
    """Test w^H Q w computation for exposure checking."""

    def test_exposure_from_Q(self):
        from aegis.mimo.compute import compute_total_exposure

        M_ant, K = 4, 2
        rng = np.random.default_rng(3)
        # Make a valid PSD Q
        A = rng.standard_normal((M_ant, M_ant)) + 1j * rng.standard_normal((M_ant, M_ant))
        Q = A.conj().T @ A
        W = rng.standard_normal((M_ant, K)) + 1j * rng.standard_normal((M_ant, K))

        p_abs = compute_total_exposure(Q, W)
        # Manual: sum_k w_k^H Q w_k = trace(W^H Q W)
        expected = np.real(np.trace(W.conj().T @ Q @ W))
        np.testing.assert_allclose(p_abs, expected, atol=1e-10)
        assert p_abs >= 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_mimo_compute.py -v`
Expected: FAIL with `ModuleNotFoundError` or `ImportError`

- [ ] **Step 3: Implement `compute_mimo_scene` module**

Create `src/aegis/mimo/compute.py`:

```python
"""MIMO scene computation orchestrator.

Coordinates the multi-user dosimetry pipeline:
1. Per-user path generation and array expansion
2. Per-user G_tilde, Q, and h computation
3. Precoder computation (MRT for now)
4. Per-user sab from the multi-user precoder
"""

from __future__ import annotations

import logging
import time

import numpy as np

from aegis.mimo.array import AntennaArray
from aegis.mimo.array_paths import expand_paths_to_array
from aegis.mimo.channel import compute_channel_vector
from aegis.mimo.scene import MIMOScene
from aegis.mimo.user import UserState

logger = logging.getLogger(__name__)


def compute_mrt_precoder(H: np.ndarray, total_power: float) -> np.ndarray:
    """MRT (matched filter) precoder: w_k = h_k* / ||h_k|| * sqrt(P/K).

    Parameters
    ----------
    H : (K, M_ant) complex channel matrix, row k is h_k.
    total_power : total transmit power budget P [W].

    Returns
    -------
    W : (M_ant, K) precoding matrix, column k is w_k.
    """
    K = H.shape[0]
    W = H.conj().T  # (M_ant, K)
    # Normalize each column to equal power P/K
    per_user_power = total_power / K
    for k in range(K):
        norm = np.linalg.norm(W[:, k])
        if norm > 0:
            W[:, k] *= np.sqrt(per_user_power) / norm
    return W


def compute_user_sab(
    G_tilde: np.ndarray, W: np.ndarray,
) -> np.ndarray:
    """Per-triangle absorbed power density for one user under multi-user precoding.

    sab_u[m] = ||G_tilde_u[m] @ W||_F^2 = sum_k |G_tilde_u[m] @ w_k|^2

    Parameters
    ----------
    G_tilde : (M_tri, 3, M_ant) complex body channel for this user.
    W : (M_ant, K) precoding matrix (all users' columns).

    Returns
    -------
    sab : (M_tri,) real, non-negative absorbed power density per triangle.
    """
    # G_tilde @ W -> (M_tri, 3, K), then Frobenius norm squared per triangle
    GW = np.einsum("mij,jk->mik", G_tilde, W)  # (M_tri, 3, K)
    sab = np.sum(np.abs(GW) ** 2, axis=(1, 2))  # (M_tri,)
    return np.real(sab)


def compute_total_exposure(
    Q: np.ndarray, W: np.ndarray,
) -> float:
    """Total absorbed power on one body from all precoding vectors.

    P_abs = sum_k w_k^H Q w_k = trace(W^H Q W).

    Parameters
    ----------
    Q : (M_ant, M_ant) Hermitian PSD exposure operator.
    W : (M_ant, K) precoding matrix.

    Returns
    -------
    p_abs : real scalar, total absorbed power [W].
    """
    return float(np.real(np.trace(W.conj().T @ Q @ W)))


def compute_mimo_scene(
    scene: MIMOScene,
    bodies: dict[str, object],
    level: int = 7,
    generate_paths_fn=None,
) -> dict:
    """Run the full MIMO dosimetry pipeline for all users in the scene.

    Parameters
    ----------
    scene : MIMOScene with array, users (UserConfig populated), freq_hz, total_power, tissue.
    bodies : dict mapping phantom_name -> BodyMesh (preloaded).
    level : fidelity level (7 or 8 for coherent MIMO).
    generate_paths_fn : callable(body, array_center, freq_hz) -> PropagationPaths.
        Generates center-of-array paths for one user's body. If None, uses
        a simple LOS path from the array center to the body center.

    Returns
    -------
    dict with keys:
        "user_ids": list of user IDs in compute order
        "timings": dict of timing breakdowns
        "precoder_type": str
    Side effects: populates each UserState with body, paths, h, G_tilde, Q, result fields.
    """
    from aegis.coherent.body_channel import compute_body_channel
    from aegis.coherent.exposure import compute_exposure_operator
    from aegis.engine import DosimetryEngine
    from aegis.paths import PropagationPaths

    timings = {}
    t0 = time.perf_counter()

    array = scene.array
    freq_hz = scene.freq_hz
    tissue = scene.tissue

    if tissue is None:
        from aegis.tissue.dielectric import TissueModel
        tissue = TissueModel.skin(freq_hz)
        scene.tissue = tissue

    engine = DosimetryEngine(tissue)

    # --- Phase 1: Per-user body loading and path generation ---
    t_paths_start = time.perf_counter()
    for user in scene.users:
        cfg = user.config
        body = bodies.get(cfg.phantom_name)
        if body is None:
            raise ValueError(f"Phantom '{cfg.phantom_name}' not found in preloaded bodies")
        user.body = body.translated(cfg.position)

        if generate_paths_fn is not None:
            center_paths = generate_paths_fn(user.body, array.reference_position, freq_hz)
        else:
            center_paths = _default_los_paths(user.body, array.reference_position, freq_hz)

        user.center_paths = center_paths
        user.paths = expand_paths_to_array(center_paths, array, freq_hz)

    timings["paths_ms"] = (time.perf_counter() - t_paths_start) * 1e3

    # --- Phase 2: Per-user G_tilde, Q, h ---
    t_channel_start = time.perf_counter()
    for user in scene.users:
        cfg = user.config
        user.G_tilde = compute_body_channel(user.body, user.paths, tissue, freq_hz)
        user.Q = compute_exposure_operator(user.G_tilde, user.body.areas)
        user.h = compute_channel_vector(
            user.center_paths, array,
            cfg.device_position, cfg.device_orientation, freq_hz,
        )

    timings["channel_ms"] = (time.perf_counter() - t_channel_start) * 1e3

    # --- Phase 3: Precoder ---
    t_precoder_start = time.perf_counter()
    H = scene.all_h()  # (K, M_ant)
    W = compute_mrt_precoder(H, scene.total_power)
    precoder_type = "mrt"

    timings["precoder_ms"] = (time.perf_counter() - t_precoder_start) * 1e3

    # --- Phase 4: Per-user sab ---
    t_sab_start = time.perf_counter()
    for user in scene.users:
        sab = compute_user_sab(user.G_tilde, W)
        # Store raw sab on user state for binary serving
        user._sab_raw = sab
        # Also run through engine for compliance (spatial averaging, etc.)
        user.result = engine.compute(user.body, user.paths, level=level)

    timings["sab_ms"] = (time.perf_counter() - t_sab_start) * 1e3
    timings["total_ms"] = (time.perf_counter() - t0) * 1e3

    return {
        "user_ids": scene.user_ids,
        "timings": timings,
        "precoder_type": precoder_type,
    }


def _default_los_paths(body, array_center, freq_hz):
    """Generate a single LOS path from array center to body center."""
    from aegis.constants import C_0
    from aegis.paths import PropagationPaths

    direction = body.centroid - array_center
    distance = np.linalg.norm(direction)
    if distance < 1e-6:
        direction = np.array([1.0, 0.0, 0.0])
        distance = 1.0
    k_hat = direction / distance

    k0 = 2 * np.pi * freq_hz / C_0
    # Free-space path loss: power density at distance d from isotropic radiator
    # S = P / (4*pi*d^2). We set |psi|^2 to encode this, with unit Tx power.
    amplitude = 1.0 / (4 * np.pi * distance**2) ** 0.5
    psi = np.array([[amplitude, 0.0, 0.0]], dtype=complex)  # (1, 3)

    return PropagationPaths(
        k_hat=k_hat.reshape(1, 3),
        psi=psi,
        element_index=np.array([0]),
        delay=np.array([distance / C_0]),
        is_los=np.array([True]),
    )
```

- [ ] **Step 4: Add `_sab_raw` field to UserState**

In `src/aegis/mimo/user.py`, add to the `UserState` dataclass fields (after `result`):

```python
    _sab_raw: np.ndarray | None = None  # multi-user sab from G_tilde @ W
```

This avoids dynamic attribute assignment on the dataclass.

- [ ] **Step 5: Export from `__init__.py`**

Add to `src/aegis/mimo/__init__.py`:

```python
from aegis.mimo.compute import (
    compute_mimo_scene,
    compute_mrt_precoder,
    compute_total_exposure,
    compute_user_sab,
)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/test_mimo_compute.py -v`
Expected: All PASS (the `TestMRTPrecoder`, `TestComputeUserSab`, and `TestComputeExposureQuadratic` classes)

- [ ] **Step 7: Commit**

```bash
git add src/aegis/mimo/compute.py src/aegis/mimo/__init__.py src/aegis/mimo/user.py tests/test_mimo_compute.py
git commit -m "Add MIMO compute orchestrator with MRT precoder"
```

---

### Task 3: MIMO route module (POST /api/mimo/compute)

**Files:**
- Create: `src/aegis/viewer/routes/mimo.py`
- Modify: `src/aegis/viewer/server.py` (L397-403)
- Test: `tests/viewer/test_mimo_api.py`

**Context the implementing agent needs:**
- Follow the exact pattern from `routes/compute.py`: a `register(app, cache, cache_lock)` function that defines route handlers as closures.
- `cache["bodies"]` is a dict mapping phantom_name -> `{"body": BodyMesh, "binary": bytes, "meta": dict}`. This is set up by `server.py` on startup (the infra branch preloads all 4 phantoms).
- `cache["config"]` is the full viewer config dict.
- The `cache_lock` is a `threading.Lock()`. Acquire it when reading/writing cache.
- Binary response format: `Response(bytes, mimetype="application/octet-stream")` with `X-Stats` JSON header.
- Request JSON for `/api/mimo/compute` follows the design doc section F1 and G+.

- [ ] **Step 1: Write failing integration test**

Create `tests/viewer/test_mimo_api.py`:

```python
"""Integration tests for MIMO API routes."""

from __future__ import annotations

import json
import threading

import numpy as np
import pytest

from aegis.viewer.config import DEFAULTS


def _make_test_body():
    """Create a minimal BodyMesh for testing."""
    from aegis.geometry.mesh import BodyMesh

    # Minimal 2-triangle mesh (a thin quad)
    vertices = np.array([
        [0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0],
    ], dtype=np.float64)
    faces = np.array([[0, 1, 2], [1, 3, 2]])
    return BodyMesh(vertices=vertices, faces=faces, name="thelonious")


@pytest.fixture
def mimo_app():
    """Create a Flask test app with MIMO routes registered."""
    from flask import Flask

    app = Flask(__name__)
    app.config["TESTING"] = True

    body = _make_test_body()
    cache = {
        "config": DEFAULTS,
        "bodies": {
            "thelonious": {"body": body, "binary": b"", "meta": {}},
        },
        "default_body": "thelonious",
    }
    cache_lock = threading.Lock()

    from aegis.viewer.routes import mimo

    mimo.register(app, cache, cache_lock)
    return app, cache


@pytest.fixture
def client(mimo_app):
    app, _ = mimo_app
    return app.test_client()


class TestMIMOCompute:
    """POST /api/mimo/compute"""

    def test_basic_compute(self, client):
        resp = client.post(
            "/api/mimo/compute",
            json={
                "array": {
                    "type": "upa",
                    "n_h": 2,
                    "n_v": 1,
                    "position": [5.0, 0.0, 3.0],
                    "broadside": [-1.0, 0.0, 0.0],
                },
                "users": [
                    {
                        "id": "u1",
                        "phantom": "thelonious",
                        "position": [0.0, 0.0, 0.0],
                        "device_position": [0.25, 0.0, 1.4],
                        "device_orientation": [0.0, 0.0, 1.0],
                    },
                ],
                "freq_hz": 28e9,
                "power_dbm": 60,
                "precoder_type": "mrt",
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "user_ids" in data
        assert "u1" in data["user_ids"]
        assert "timings" in data
        assert "precoder_type" in data

    def test_missing_array(self, client):
        resp = client.post(
            "/api/mimo/compute",
            json={"users": [{"id": "u1", "phantom": "thelonious", "position": [0, 0, 0]}]},
        )
        assert resp.status_code == 400

    def test_empty_users(self, client):
        resp = client.post(
            "/api/mimo/compute",
            json={
                "array": {"type": "upa", "n_h": 2, "n_v": 1, "position": [5, 0, 3], "broadside": [-1, 0, 0]},
                "users": [],
            },
        )
        assert resp.status_code == 400

    def test_unknown_phantom(self, client):
        resp = client.post(
            "/api/mimo/compute",
            json={
                "array": {"type": "upa", "n_h": 2, "n_v": 1, "position": [5, 0, 3], "broadside": [-1, 0, 0]},
                "users": [{"id": "u1", "phantom": "nonexistent", "position": [0, 0, 0]}],
                "freq_hz": 28e9,
            },
        )
        assert resp.status_code == 404


class TestMIMOResult:
    """GET /api/mimo/result/<user_id>"""

    def test_result_before_compute(self, client):
        resp = client.get("/api/mimo/result/u1")
        assert resp.status_code == 404

    def test_result_after_compute(self, client):
        # Compute first
        client.post(
            "/api/mimo/compute",
            json={
                "array": {"type": "upa", "n_h": 2, "n_v": 1, "position": [5, 0, 3], "broadside": [-1, 0, 0]},
                "users": [{"id": "u1", "phantom": "thelonious", "position": [0, 0, 0],
                           "device_position": [0.25, 0, 1.4], "device_orientation": [0, 0, 1]}],
                "freq_hz": 28e9,
                "power_dbm": 60,
            },
        )
        resp = client.get("/api/mimo/result/u1")
        assert resp.status_code == 200
        assert resp.content_type == "application/octet-stream"
        # Binary should be float32 sab array
        data = np.frombuffer(resp.data, dtype=np.float32)
        assert len(data) > 0
        assert np.all(np.isfinite(data))

    def test_result_unknown_user(self, client):
        # Compute first
        client.post(
            "/api/mimo/compute",
            json={
                "array": {"type": "upa", "n_h": 2, "n_v": 1, "position": [5, 0, 3], "broadside": [-1, 0, 0]},
                "users": [{"id": "u1", "phantom": "thelonious", "position": [0, 0, 0],
                           "device_position": [0.25, 0, 1.4], "device_orientation": [0, 0, 1]}],
                "freq_hz": 28e9,
            },
        )
        resp = client.get("/api/mimo/result/nonexistent")
        assert resp.status_code == 404


class TestMIMOSummary:
    """GET /api/mimo/summary"""

    def test_summary_before_compute(self, client):
        resp = client.get("/api/mimo/summary")
        assert resp.status_code == 404

    def test_summary_after_compute(self, client):
        client.post(
            "/api/mimo/compute",
            json={
                "array": {"type": "upa", "n_h": 2, "n_v": 1, "position": [5, 0, 3], "broadside": [-1, 0, 0]},
                "users": [{"id": "u1", "phantom": "thelonious", "position": [0, 0, 0],
                           "device_position": [0.25, 0, 1.4], "device_orientation": [0, 0, 1]}],
                "freq_hz": 28e9,
                "power_dbm": 60,
            },
        )
        resp = client.get("/api/mimo/summary")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "users" in data
        assert len(data["users"]) == 1
        user_summary = data["users"][0]
        assert "id" in user_summary
        assert "p_abs_mw" in user_summary
        assert "compliant" in user_summary
        assert "precoder" in data
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/viewer/test_mimo_api.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'aegis.viewer.routes.mimo'`

- [ ] **Step 3: Implement the route module**

Create `src/aegis/viewer/routes/mimo.py`:

```python
"""MIMO multi-user dosimetry routes."""

from __future__ import annotations

import json
import logging
import time

import numpy as np
from flask import Flask, Response, jsonify, request

logger = logging.getLogger(__name__)

_OCTET_STREAM = "application/octet-stream"


def register(app: Flask, cache: dict, cache_lock) -> None:
    """Attach MIMO routes to *app*."""

    def _parse_array_config(params: dict) -> dict | None:
        """Extract and validate array config from request."""
        arr = params.get("array")
        if arr is None:
            return None
        if not isinstance(arr, dict):
            return None
        return arr

    def _build_scene(params: dict):
        """Build a MIMOScene from request JSON.

        Returns (scene, error_response). If error_response is not None,
        return it directly.
        """
        from aegis.mimo import AntennaArray, MIMOScene, UserConfig, UserState
        from aegis.tissue.dielectric import TissueModel

        cfg = cache["config"]
        mimo_cfg = cfg.get("mimo", {})

        # --- Array ---
        arr_params = _parse_array_config(params)
        if arr_params is None:
            return None, (jsonify({"error": "Missing or invalid 'array' in request"}), 400)

        freq_hz = float(params.get("freq_hz", cfg["dosimetry"].get("freq_hz", 28e9)))
        c0 = 299_792_458.0
        wavelength = c0 / freq_hz

        n_h = int(arr_params.get("n_h", 4))
        n_v = int(arr_params.get("n_v", 4))
        d_h_wl = float(arr_params.get("d_h_wavelengths", 0.5))
        d_v_wl = float(arr_params.get("d_v_wavelengths", 0.5))
        d_h = d_h_wl * wavelength
        d_v = d_v_wl * wavelength
        position = np.array(arr_params.get("position", [5.0, 0.0, 3.0]), dtype=np.float64)
        broadside = np.array(arr_params.get("broadside", [-1.0, 0.0, 0.0]), dtype=np.float64)

        array = AntennaArray.upa(n_h, n_v, d_h, d_v, center=position, broadside=broadside)

        # --- Users ---
        user_list = params.get("users", [])
        if not user_list:
            return None, (jsonify({"error": "At least one user is required"}), 400)

        max_users = int(mimo_cfg.get("max_users", 8))
        if len(user_list) > max_users:
            return None, (jsonify({"error": f"Maximum {max_users} users allowed"}), 400)

        bodies = cache.get("bodies", {})
        users = []
        for u in user_list:
            phantom = u.get("phantom", "thelonious")
            if phantom not in bodies:
                return None, (jsonify({"error": f"Phantom '{phantom}' not found"}), 404)

            pos = np.array(u.get("position", [0, 0, 0]), dtype=np.float64)
            orientation = float(u.get("orientation", 0.0))
            dev_pos = np.array(
                u.get("device_position", u.get("device_offset", [0.25, 0, 1.4])),
                dtype=np.float64,
            )
            dev_orient = np.array(
                u.get("device_orientation", [0.0, 0.0, 1.0]),
                dtype=np.float64,
            )

            config = UserConfig(
                user_id=u.get("id", f"user_{len(users)}"),
                phantom_name=phantom,
                position=pos,
                orientation=orientation,
                device_position=dev_pos,
                device_orientation=dev_orient,
            )
            users.append(UserState(config=config))

        # --- Power ---
        power_dbm = float(params.get("power_dbm", cfg["dosimetry"]["default_power_dbm"]))
        total_power = 10 ** ((power_dbm - 30) / 10)  # dBm to W

        tissue = TissueModel.skin(freq_hz)

        scene = MIMOScene(
            array=array,
            users=users,
            freq_hz=freq_hz,
            total_power=total_power,
            tissue=tissue,
        )
        return scene, None

    @app.route("/api/mimo/compute", methods=["POST"])
    def api_mimo_compute():
        """Compute multi-user MIMO dosimetry for all users atomically."""
        from aegis.mimo.compute import compute_mimo_scene

        params = request.get_json(silent=True)
        if params is None:
            if request.data:
                return jsonify({"error": "Invalid JSON body"}), 400
            params = {}
        elif not isinstance(params, dict):
            return jsonify({"error": "JSON body must be an object"}), 400

        scene, err = _build_scene(params)
        if err is not None:
            return err

        with cache_lock:
            bodies_raw = cache.get("bodies", {})
        bodies = {name: entry["body"] for name, entry in bodies_raw.items()}

        try:
            result = compute_mimo_scene(scene, bodies, level=7)
        except Exception as exc:
            logger.exception("MIMO compute failed")
            return jsonify({"error": str(exc)}), 500

        # Cache scene and per-user binary results
        mimo_binary = {}
        mimo_stats = {}
        for user in scene.users:
            uid = user.config.user_id
            sab = getattr(user, "_sab_raw", None)
            if sab is not None:
                mimo_binary[uid] = sab.astype(np.float32).tobytes()
            if user.result is not None:
                mimo_stats[uid] = _user_stats(user, scene)

        with cache_lock:
            cache["mimo_scene"] = scene
            cache["mimo_results_binary"] = mimo_binary
            cache["mimo_results_stats"] = mimo_stats
            cache["mimo_summary"] = result

        return jsonify(result)

    @app.route("/api/mimo/result/<user_id>")
    def api_mimo_result(user_id: str):
        """Serve cached binary sab for one user."""
        with cache_lock:
            binary_cache = cache.get("mimo_results_binary", {})
            data = binary_cache.get(user_id)

        if data is None:
            return jsonify({"error": f"No result for user '{user_id}'"}), 404

        with cache_lock:
            stats = cache.get("mimo_results_stats", {}).get(user_id, {})

        resp = Response(data, mimetype=_OCTET_STREAM)
        resp.headers["X-Stats"] = json.dumps(stats)
        resp.headers["Access-Control-Expose-Headers"] = "X-Stats"
        return resp

    @app.route("/api/mimo/summary")
    def api_mimo_summary():
        """Per-user compliance summary and precoder info."""
        with cache_lock:
            scene = cache.get("mimo_scene")
            summary = cache.get("mimo_summary")

        if scene is None or summary is None:
            return jsonify({"error": "No MIMO computation results available"}), 404

        users_summary = []
        for user in scene.users:
            uid = user.config.user_id
            entry = {
                "id": uid,
                "phantom": user.config.phantom_name,
                "position": user.config.position.tolist(),
            }
            if user.result is not None:
                entry["p_abs_mw"] = float(user.result.p_abs * 1e3)
                entry["peak_sab"] = float(user.result.peak_sab)
                entry["compliant"] = bool(
                    user.result.p_abs * 1e3
                    < cache["config"].get("mimo", {}).get("exposure_budget_mw", 100)
                )
            else:
                entry["p_abs_mw"] = None
                entry["peak_sab"] = None
                entry["compliant"] = None
            users_summary.append(entry)

        return jsonify({
            "users": users_summary,
            "precoder": summary.get("precoder_type", "mrt"),
            "timings": summary.get("timings", {}),
        })


def _user_stats(user, scene) -> dict:
    """Build per-user stats dict for X-Stats header."""
    r = user.result
    stats = {
        "user_id": user.config.user_id,
        "phantom": user.config.phantom_name,
        "p_abs": float(r.p_abs),
        "p_abs_mw": float(r.p_abs * 1e3),
        "peak_sab": float(r.peak_sab),
    }
    if r.sab_averaged is not None:
        stats["peak_sab_averaged"] = float(np.max(r.sab_averaged))
    return stats
```

- [ ] **Step 4: Register MIMO routes in server.py**

In `src/aegis/viewer/server.py`, modify the route registration block (lines 397-403):

Change:
```python
    from aegis.viewer.routes import analysis, compute, data, location
```
To:
```python
    from aegis.viewer.routes import analysis, compute, data, location, mimo
```

And add before `return app`:
```python
    mimo.register(app, _cache, _cache_lock)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/viewer/test_mimo_api.py -v -x`
Expected: All PASS.

**Important:** The integration tests use a minimal 2-triangle BodyMesh that may lack methods like `centroid` or `translated()` that `compute_mimo_scene` needs. If tests fail for this reason, mock `compute_mimo_scene` in the test fixture using `unittest.mock.patch`. The mock should:
1. Populate each `UserState` with `_sab_raw = np.ones(2, dtype=np.float32)` (2 triangles)
2. Set a minimal `user.result` with `p_abs`, `peak_sab`, `sab`, `sab_averaged` fields
3. Return `{"user_ids": [...], "timings": {}, "precoder_type": "mrt"}`

This keeps the API tests focused on the route logic, not the physics pipeline.

- [ ] **Step 6: Commit**

```bash
git add src/aegis/viewer/routes/mimo.py src/aegis/viewer/server.py tests/viewer/test_mimo_api.py
git commit -m "Add MIMO API routes: compute, result, summary"
```

---

### Task 4: Lint, full test suite, and push

- [ ] **Step 1: Run ruff lint**

```bash
python -m ruff check src/aegis/mimo/compute.py src/aegis/viewer/routes/mimo.py src/aegis/viewer/config.py tests/viewer/test_mimo_config.py tests/test_mimo_compute.py tests/viewer/test_mimo_api.py
```

Fix any issues.

- [ ] **Step 2: Run ruff format**

```bash
python -m ruff format src/aegis/mimo/compute.py src/aegis/viewer/routes/mimo.py src/aegis/viewer/config.py tests/viewer/test_mimo_config.py tests/test_mimo_compute.py tests/viewer/test_mimo_api.py
```

- [ ] **Step 3: Run existing test suite to check for regressions**

```bash
python -m pytest tests/ -m "not slow" -x --timeout=120
```

Expected: All existing tests still pass. New tests pass.

- [ ] **Step 4: Fix any failures**

If any existing tests break, fix the issue. Common pitfalls:
- Import errors from modified `__init__.py`
- Config changes affecting other tests that read DEFAULTS

- [ ] **Step 5: Commit fixes if any**

```bash
git add -u
git commit -m "Fix lint and test issues from MIMO backend API"
```

- [ ] **Step 6: Push**

```bash
git push origin wt/multi-user-2b
```

---

## Notes for the implementing agent

1. **Phase 2a is not merged yet.** The `compute_mimo_scene` orchestrator uses MRT only. When phase 2a lands (with `src/aegis/mimo/precoders.py`), add a `precoder_type` parameter to `compute_mimo_scene` and dispatch to the appropriate precoder function. The route already accepts `precoder_type` in the request JSON.

2. **The `changed` field** in the compute request (from the design doc's invalidation matrix) is deferred. The initial implementation recomputes everything on each request. Incremental recomputation will be added in phase 4 when the session cache is more mature.

3. **`BodyMesh.translated()`** may or may not exist. If it does not, apply the position offset manually: `body.centroids + position`, `body.vertices + position`. Check the BodyMesh API before implementing.

4. **Coordinate systems.** Python uses Z-up. The route receives positions in Z-up coordinates (the frontend converts Y-up to Z-up before sending). Do not swap coordinates in the route.

5. **The `_sab_raw` field** on UserState stores the multi-user sab (computed from G_tilde @ W) separately from the engine's single-user result. Task 2 adds it as a declared dataclass field. In phase 4, this will be cleaned up when the engine learns about multi-user sab directly.
