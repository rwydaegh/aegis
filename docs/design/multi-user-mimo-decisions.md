# Multi-user MIMO extension: design decisions

Status: DRAFT v3
Date: 2026-03-25

This document is the single source of truth for the multi-user MIMO feature.
It covers execution strategy, all architectural decisions, user lifecycle,
and the full invalidation model.

---

## Execution plan (read this first)

### How this gets built

This feature touches 20+ new files across backend (`src/aegis/mimo/`),
viewer (`src/aegis/viewer/routes/`), and frontend (`aegis-web/src/`). One
Claude Code session cannot do it all. The plan uses multiple sessions and
git worktrees for parallelism.

### Dependency on the infrastructure branch

The `wt/infra` worktree is implementing production deployment, multi-user
isolation, and a stateless server. It has already landed changes we depend on:

1. **Preloaded body meshes.** All 4 phantoms loaded on startup into a
   read-only dict. `/api/body?name=X` returns any phantom. The mutation
   endpoint `/api/body/switch` is removed. This solves multi-body loading.

2. **Stateless compute.** `body_name` is a request parameter. Compliance
   returned in the response. Timings returned from `engine.compute()`.

3. **Thread safety.** Locks on caches, session-keyed pipeline.

4. **Frontend refactors.** `useDosimetry` sends `body_name`, `fetchBody(name)`
   exists, stores refactored, shareable URLs encode state.

Phase 1 and 2a (pure Python in `src/aegis/mimo/`) have zero overlap with
infra and can start immediately. Phases 2b and 3 (viewer routes and frontend)
must build on infra's stateless server and refactored frontend. They wait
for infra to merge to master.

### Phase structure

**Phase 1: Core data model + paths + channels** (one session, this worktree)

```
src/aegis/mimo/__init__.py
src/aegis/mimo/array.py         -- AntennaArray, upa(), steering vectors
src/aegis/mimo/user.py          -- UserConfig, UserState
src/aegis/mimo/scene.py         -- MIMOScene, invalidation logic
src/aegis/mimo/array_paths.py   -- expand_paths_to_array
src/aegis/mimo/channel.py       -- communication channel h_k, dipole UE
tests/test_mimo_array.py
tests/test_mimo_paths.py
tests/test_mimo_channel.py
```

Merge to feature branch. Everything else depends on this.

**Phase 2a: Precoders + orchestration** (one session, worktree A)

```
src/aegis/mimo/precoders.py     -- MRT, ZF, MMSE, ZF+exposure-scaling
src/aegis/mimo/compute.py       -- compute_mimo_scene orchestrator
tests/golden/test_multiuser.py  -- golden tests for 2-user ZF
tests/test_mimo_precoders.py    -- property tests for invariants
```

**Phase 2b: Backend API routes** (parallel session, worktree B)
Depends on infra merging to master first.

```
src/aegis/viewer/routes/mimo.py   -- /api/mimo/compute, /api/mimo/result/{id}, /api/mimo/summary
src/aegis/viewer/config.py        -- mimo config section
src/aegis/viewer/routes/__init__.py
```

Phase 2a and 2b can run in parallel: 2a touches `src/aegis/mimo/`, 2b
touches `src/aegis/viewer/`. Zero file overlap.

**Phase 3a: Frontend MIMO store + 3D rendering** (one session, worktree C)
Depends on infra merging to master first.

```
aegis-web/src/stores/mimo.ts
aegis-web/src/api/mimo.ts
aegis-web/src/hooks/useActiveSimulation.ts  -- adaptor hook
aegis-web/src/components/scene/BodyMeshInstance.tsx
aegis-web/src/components/scene/AntennaArray.tsx
aegis-web/src/components/scene/SceneRoot.tsx
```

**Phase 3b: Frontend UI panels + user management** (parallel or sequential)

```
aegis-web/src/components/hud/MIMOPanel.tsx   -- user list, add/remove
aegis-web/src/components/hud/UserBadges.tsx  -- compliance badges
aegis-web/src/hooks/useMIMODosimetry.ts      -- compute trigger
aegis-web/src/hooks/useMIMOKeyboard.ts       -- WASD, Tab, number keys
```

**Phase 4: Integration testing + polish** (one session, on merged branch)

```
tests/viewer/test_mimo_api.py    -- Flask endpoint integration tests
tests/e2e/test_mimo_viewer.py    -- Playwright E2E
Bug fixes, UX polish, edge cases from lifecycle spec (section G+)
```

### Parallelism map

```
                        infra merges to master
                               |
Phase 1 (core)  ──────────────┤
       |                       |
       +──> Phase 2a (precoders)  ──────┐
       |                                |
       |                                ├──> Phase 4 (integration)
       |                                |        |
       └────────────────── infra ──> Phase 2b ──┘        PR to master
                              |                            |
                              └──> Phase 3a (scene) ──────┘
                                        |
                                   Phase 3b (UI) ─────────┘
```

The critical path is: Phase 1 -> (infra merge) -> Phase 2b + Phase 3a.
Phases 2a runs in parallel with everything after Phase 1. Phase 3b can
overlap with 3a since they touch different component directories.

### Session strategy

- Each phase is one Claude Code superpowers session with its own
  implementation plan written at session start (not all upfront).
- Phases 2a and 2b run in parallel worktrees.
- Within each session, subagents handle independent file groups.
- Phase 4 is explicitly an integration + bug-fix pass. This is where the
  parallel streams converge and get tested together.

### What can go wrong

- **Merge conflicts between worktrees.** Mitigated by non-overlapping file
  sets (mimo/ vs viewer/ vs aegis-web/).
- **API contract mismatch between backend and frontend.** Mitigated by the
  API shape defined in section F1 and the compute orchestration protocol
  in section G+.
- **Infra branch takes longer than expected.** Phase 1 and 2a are unblocked
  regardless. Only 2b and 3 wait.
- **Integration bugs at Phase 4.** Expected. That is why Phase 4 exists.

### Reconciling infra's statelessness with MIMO's cached state

The infra branch makes the server stateless per-request. MIMO needs state
between requests (cached G_tilde, Q per user, precoder matrix).

**Decision: session-scoped cache.** Use the session cookie from infra's auth
system to key a per-session cache. Each browser tab gets its own MIMOScene.
TTL 30 minutes. Maximum 4 concurrent sessions. This is the minimal stateful
layer on top of infra's otherwise stateless design.

### Existing code that stays unchanged

The engine, kernels, coherent pipeline, paths, and all existing tests are
untouched by design. The multi-user orchestration lives entirely in the new
`src/aegis/mimo/` package and calls the existing engine in a loop.

---

## Design decisions

What follows are the technical decisions organized by subsystem.

## A. Data model and abstractions

### A1. Primary antenna abstraction

**Problem.** The current codebase has no antenna model at all. The viewer
places a point in space and synthesizes paths from it. Multi-user MIMO
requires an array of M elements at known positions with a shared phase
reference. What is the right abstraction?

**Options.**

| # | Option | Pros | Cons |
|---|--------|------|------|
| 1 | `AntennaArray` dataclass | Minimal, composable. Contains element positions, element pattern, reference point. No base station concept to outgrow. | Needs a separate "Scenario" to add Tx power, frequency, etc. |
| 2 | `BaseStation` wrapping an `AntennaArray` | Groups frequency, power budget, array geometry in one object. Closer to 3GPP language. | Heavier. If we ever want distributed MIMO (multiple panels), the single-BaseStation assumption leaks. |
| 3 | No new type; add `element_positions` parameter to compute calls | Zero-cost to start. | Scattered parameters, no validation, no reuse. Collapses under multi-user. |

**Recommendation: Option 1 -- `AntennaArray` dataclass.**

```python
@dataclass(frozen=True)
class AntennaArray:
    element_positions: np.ndarray   # (M, 3) in world coords [m]
    element_pattern: str = "isotropic"  # or "patch", extensible later
    reference_position: np.ndarray  # (3,) phase center

    @classmethod
    def upa(cls, n_h, n_v, d_h, d_v, center, orientation) -> AntennaArray: ...

    @property
    def n_elements(self) -> int: ...
```

Keep it frozen, geometry-only, no frequency or power. Those belong to the
scenario or the engine call. This mirrors how `BodyMesh` is pure geometry and
`TissueModel` carries the EM properties separately.

Add `BaseStation` later (v2) if needed.

---

### A2. What is a "User"?

**Problem.** A "user" in multi-user MIMO is a body at a position, holding a
device, with a communication channel h_k and an exposure operator Q_u. The
current code has no such concept: it is one body, one antenna, one result.

**Options.**

| # | Option | Pros | Cons |
|---|--------|------|------|
| 1 | `User` dataclass grouping everything | Single source of truth. Easy to iterate. | Mutable state (results change each compute). |
| 2 | Input side only: `UserConfig` for static data, results stored externally | Clean separation of config vs results. | Two objects to manage per user. |
| 3 | No new type; use dicts in the viewer | Fast to prototype. | Type safety gone, refactoring nightmare. |

**Recommendation: Option 1 -- `User` dataclass** but split into frozen input
and mutable result container.

```python
@dataclass(frozen=True)
class UserConfig:
    """Static per-user setup."""
    user_id: str
    phantom_name: str           # "thelonious", "duke", ...
    position: np.ndarray        # (3,) world coords [m]
    orientation: float          # rotation about z-axis [rad]
    device_position: np.ndarray # (3,) smartphone location [m], world coords
    device_orientation: np.ndarray  # (3,) dipole axis, unit vector

@dataclass
class UserState:
    """Mutable per-user computation results."""
    config: UserConfig
    body: BodyMesh | None = None
    paths: PropagationPaths | None = None
    h: np.ndarray | None = None       # (M_ant,) communication channel
    G_tilde: np.ndarray | None = None  # (M_tri, 3, M_ant) body channel
    Q: np.ndarray | None = None        # (M_ant, M_ant) exposure operator
    result: DosimetryResult | None = None
```

The `UserConfig` is what the frontend sends. The `UserState` is what the
backend builds and caches. This mirrors the existing pattern where `BodyMesh`
(loaded once) is separate from `DosimetryResult` (recomputed each time).

---

### A3. Scene abstraction

**Problem.** The viewer currently has a flat cache dict with one body, one
antenna position, one config. Multi-user needs a structured scene containing
the array plus K users.

**Options.**

| # | Option | Pros | Cons |
|---|--------|------|------|
| 1 | `MIMOScene` dataclass | Clean container, serializable, testable in isolation. | One more type to maintain. |
| 2 | Expand the viewer cache dict with `users: list[UserState]` | Minimal change to Flask routing. | Scene logic leaks into route handlers. |
| 3 | Keep everything flat, one user at a time, loop in the endpoint | Fastest to ship. | Defeats the purpose of multi-user. |

**Recommendation: Option 1 -- `MIMOScene`.**

```python
@dataclass
class MIMOScene:
    array: AntennaArray
    users: list[UserState]
    freq_hz: float
    total_power: float            # total Tx power budget P [W]
    tissue: TissueModel

    def get_user(self, user_id: str) -> UserState: ...
    def all_Q(self) -> list[np.ndarray]: ...
```

Lives in a new `src/aegis/mimo/` package. The viewer stores one `MIMOScene`
in its cache. This keeps the core engine untouched (it still takes one body +
one paths) while the scene orchestrates the multi-user loop.

---

### A4. Smartphone / UE abstraction

**Problem.** The communication channel h_k is measured at the smartphone
position. The smartphone also has a radiation pattern (dipole). Do we need a
dedicated type?

**Options.**

| # | Option | Pros | Cons |
|---|--------|------|------|
| 1 | Fields on `UserConfig` (position, orientation, pattern type) | Simple, no extra type. Sufficient for v1 where every UE is a dipole. | Harder to extend to multi-antenna UEs. |
| 2 | `UserEquipment` dataclass with position, orientation, pattern | Extensible to MIMO UEs. | Over-engineering for v1 where UE = single dipole. |

**Recommendation: Option 1 -- fields on `UserConfig`.** The device is just
a position + dipole axis for the MVP. If we ever model multi-antenna UEs,
factor out a `UserEquipment` then.

---

### A5. PropagationPaths in multi-user context

**Problem.** Currently one `PropagationPaths` object goes into the engine.
In multi-user, each user's body receives paths from the same antenna array.
The paths are different per user (different geometry, different distances).

**Options.**

| # | Option | Pros | Cons |
|---|--------|------|------|
| 1 | One `PropagationPaths` per user, generated independently | Clean separation. Each user's paths carry their own `element_index`. Works with the existing engine unchanged. | Repeated path generation. |
| 2 | One global `PropagationPaths` with a `user_index` field | Single generation pass. | Engine must filter by user. Breaks the existing API. Major refactor. |
| 3 | One per user, with shared `element_index` space (all referencing the same array) | Natural extension. `element_index` already maps to antenna elements; just ensure all users use the same array dimension. | Must be careful that `n_elements` is consistent across users. |

**Recommendation: Option 3 -- one `PropagationPaths` per user, shared element
index space.** No changes to `PropagationPaths` itself. Each user gets their
own instance where `element_index` values range over `[0, M_ant)` for the
same antenna array. The engine sees one body + one paths per call, unchanged.
The `MIMOScene` orchestrates calling the engine K times.

---

## B. Antenna array model

### B1. Uniform Planar Array geometry

**Problem.** Need to go from `(N_h, N_v, d_h, d_v, center, orientation)` to
element positions in world coordinates.

**Recommendation:** Add a `upa()` classmethod on `AntennaArray`.

```python
@classmethod
def upa(cls, n_h: int, n_v: int, d_h: float, d_v: float,
        center: np.ndarray, broadside: np.ndarray) -> AntennaArray:
    """Uniform Planar Array.

    d_h, d_v in meters (typically 0.5 * lambda).
    broadside: (3,) unit vector for array normal (main beam direction).
    """
```

Internally: build a local grid `[-n_h/2..n_h/2] * d_h` in two axes
perpendicular to `broadside`, then rotate/translate to world coords.

This is straightforward geometry. No decision needed beyond confirming that
`d_h` and `d_v` are in meters, not wavelength fractions. The caller converts
`0.5 * lambda` to meters. This avoids coupling the geometry to frequency.

---

### B2. Element radiation pattern

**Problem.** Real antenna elements have gain patterns. Isotropic elements are
simpler but physically wrong (gain < 1 at grazing angles).

**Options.**

| # | Option | Pros | Cons |
|---|--------|------|------|
| 1 | Isotropic elements only (v1) | Simple. The viewer already has a `radiation_pattern` config for visualization, but the physics path ignores it. Isotropic is the standard assumption in the monograph. | Overestimates exposure at grazing angles. |
| 2 | Cosine/patch pattern from the start | More realistic. `cos(theta)^n` is one line of code. | Must define "theta" relative to element broadside, which requires tracking per-element orientation. |
| 3 | Arbitrary per-element pattern (callable) | Maximum flexibility. | Premature generality. |

**Recommendation: Option 1 (isotropic) for MVP, with a flag for Option 2.**
The monograph uses isotropic elements. Adding `cos(theta)^n` is a one-line
weight on each path's power, so it can be added as a boolean flag later
without changing any data structures. The important thing is that the array
geometry and phase model are correct.

---

### B3. Per-element path generation

**Problem.** In a UPA, all elements see roughly the same scattering
environment (same walls, same reflectors), but with different phases due to
their spatial offset. Two approaches:

**Options.**

| # | Option | Pros | Cons |
|---|--------|------|------|
| 1 | **Shared directions, per-element phase shifts** (far-field assumption). Generate N multipath directions from the array center. For element j at position p_j, apply transmit steering phase `exp(+i*k0 * k_hat_n . p_j)` to the shared psi (positive sign because k_hat_n is the arrival direction at the body, and the element offset creates a shorter/longer path). | Standard array signal processing assumption. O(N) path generation, O(N*M) phase application. | Breaks down if elements are separated by many wavelengths (not typical for 5G UPA at 28 GHz). |
| 2 | **Independent paths per element** via full ray tracing from each element. | Exact for large arrays or near-field. | O(N*M) ray tracing cost. Overkill at 28 GHz where d = 5mm. |
| 3 | **Cluster-level sharing** (3GPP hybrid). Share cluster-level angles, apply per-element steering. | Standard 3GPP 38.901 approach. | More complex to implement. |

**Recommendation: Option 1 -- shared directions, per-element phase shifts.**
This is the textbook phased array model and exactly what the monograph
assumes. For a UPA at 28 GHz with d = lambda/2 = 5.35 mm, the far-field
assumption holds for any user beyond ~0.5 m (Fraunhofer distance for a
16-element array is D^2/(2*lambda) = ~4 cm). The implementation:

1. Generate N paths from the array center (using existing synthetic/stochastic/RT generators).
2. For each element j, create paths with `psi_nj = psi_n * exp(+i*k0 * k_hat_n . p_j)`.
   (Positive sign: k_hat_n is the arrival direction at the body. Element j at
   offset p_j from the array center has a shorter path by k_hat_n . p_j,
   giving a phase advance. The monograph's body_channel.py applies
   `exp(-i*k0 * k_hat_n . r_m)`, so the total becomes
   `exp(-i*k0 * k_hat_n . (r_m - p_j))`, the correct plane-wave phase from
   element j to surface point r_m.)
3. Set `element_index` to j for all N paths of element j.
4. Concatenate into one `PropagationPaths` with N*M total paths.

This reuses the existing path generators unchanged.

---

### B4. Steering vectors

**Problem.** The transmit steering vector `a(k_hat) = [exp(+i*k0 * k_hat . p_1), ..., exp(+i*k0 * k_hat . p_M)]` maps an arrival direction k_hat to per-element phase advances. Where does this live?

**Recommendation:** Method on `AntennaArray`:

```python
def steering_vector(self, k_hat: np.ndarray, freq_hz: float) -> np.ndarray:
    """(M,) complex steering vector for direction k_hat."""
    k0 = 2 * np.pi * freq_hz / C_0
    return np.exp(+1j * k0 * (self.element_positions @ k_hat))
```

And the bulk version for N directions:

```python
def steering_matrix(self, k_hat: np.ndarray, freq_hz: float) -> np.ndarray:
    """(N, M) complex steering matrix."""
```

This is the only frequency-dependent operation on the array object, and
frequency is passed as an argument, not stored.

---

## C. Channel model

### C1. Communication channel h_k

**Problem.** The precoder needs `h_k`, the (M_ant,) complex channel from the
array to user k's smartphone. This is a scalar channel per antenna element
(assuming single-antenna UE). How do we compute it?

**Options.**

| # | Option | Pros | Cons |
|---|--------|------|------|
| 1 | **Sum of steering vectors weighted by path gains.** `h_k = sum_n alpha_n * a(k_hat_n)` where `alpha_n` is the complex path gain at the UE. | Standard channel model. Reuses the same multipath environment. Matches 3GPP 38.901 structure. | Requires the path gain `alpha_n` at the UE, not at the body surface. |
| 2 | **LOS-only free-space channel.** `h_k = sqrt(P_rx) * a(k_hat_LOS)` | Simplest possible. Good enough for initial testing. | Ignores multipath. |
| 3 | **Full ray-traced channel** from array to smartphone position. | Most accurate. | Requires ray tracing to a point target. |

**Recommendation: Option 1 (full multipath channel), with Option 2 as a
degenerate special case when paths are LOS-only.**

The per-element channel is:

```
h_j = sum_{n: j(n)=j} C_R(k_hat_n)^H @ psi_n * exp(-i*k0 * k_hat_n . r_UE)
```

where `C_R(k_hat_n)` is the (3,) effective length vector of the UE antenna
for arrival direction `k_hat_n`. For a short dipole oriented along unit vector
`d_hat`, the effective length is `C_R(k_hat) = l_eff * (I - k_hat k_hat^T) @ d_hat`,
which projects the dipole axis onto the plane perpendicular to k_hat. The
receive power is proportional to `|C_R^H psi_n|^2`.

For a realistic dipole antenna (not the textbook sin(theta) approximation),
the radiation pattern includes the full electromagnetic response: finite
dipole length (half-wave), ground plane effects from the phone chassis,
and polarization mismatch. For v1, use the half-wave dipole effective length:

```
C_R(k_hat) = (l / (2*pi)) * (cos(k0*l*cos(theta)/2) - cos(k0*l/2)) / sin(theta) * theta_hat
```

where `theta` is the angle between k_hat and the dipole axis, `theta_hat` is
the unit vector in the theta direction (perpendicular to both k_hat and the
dipole axis), and `l` is the dipole physical length (lambda/2 for a
half-wave dipole). This captures the full radiation pattern including nulls
at the poles, polarization selectivity, and the cos/sin pattern that differs
from the simple sin(theta) approximation.

**UE orientation:** `UserConfig.device_orientation` gives the dipole axis
`d_hat` in world coordinates. Default: vertical (along body axis).

The key insight is that h_k and the body-illumination paths can share the
same multipath directions -- they just differ in where the response is
evaluated (smartphone point vs body surface).

---

### C2. Paths from array to user body (for Q_u)

**Problem.** The body channel `G_tilde` needs paths arriving at the body
surface. These come from the array but potentially via multipath.

**Recommendation:** Same mechanism as today. The existing path generators
(synthetic, stochastic, ray-traced) produce paths arriving at a body from a
source position. For multi-user, call the path generator once per user with
that user's body position and the array center as the source. Then expand to
per-element paths using the steering vector approach from B3.

New function in `src/aegis/mimo/array_paths.py`:

```python
def expand_paths_to_array(
    center_paths: PropagationPaths,
    array: AntennaArray,
    freq_hz: float,
) -> PropagationPaths:
    """Expand center-of-array paths to per-element paths with phase steering."""
```

---

### C3. Channel model support

**Problem.** The viewer currently supports three path sources: analytical
(LOS from a single direction), stochastic (3GPP channel model), and
ray-traced (DiffeRT/Sionna). All three must work with multi-user MIMO from
the start. Ray tracing is the headline feature of AEGIS.

**Decision: all three channel models are supported.**

The abstraction already exists: all channel models produce `PropagationPaths`.
The multi-user extension calls the path generator once per user, then expands
to per-element paths via `expand_paths_to_array()`. The channel model is
orthogonal to the multi-user machinery.

Implementation difficulty by channel model:

1. **Analytical (LOS):** Trivial. One path per user, direction from array
   center to body center. Already works.

2. **Ray tracing (DiffeRT/Sionna):** The environment is shared across users,
   so the ray tracer runs once per user-body but the scatterers are
   physically consistent. This is mostly a for-loop over the existing RT
   integration. Paths from different users share the same scene geometry.

3. **Stochastic (3GPP/QuaDRiGa):** Disabled for multi-user in v1. The reason:
   large-scale parameters (shadow fading, delay spread) must be spatially
   consistent across users sharing the same scatterers. Per-link generation
   with independent LSPs gives physically inconsistent channels (one user
   could see a cluster that the adjacent user cannot, which is impossible
   when they are 2m apart). Proper 3GPP 38.901 multi-link generation
   requires correlated LSP maps (TR 38.901 Sec 7.5), which is a significant
   implementation effort. Stochastic remains fully supported in single-user
   mode. The multi-user UI should gray out the stochastic option and show a
   tooltip: "Stochastic channels require correlated LSP maps for multi-user
   consistency. Use ray tracing or analytical for multi-user scenarios."

**No channel model abstraction layer needed.** `PropagationPaths` is already
the abstraction. Each channel model produces it. The multi-user code does not
care how paths were generated.

---

### C4. Phase model

**Problem.** Coherent levels 7-8 need the absolute phase `exp(-i*k0 * k_hat . r)` at each surface point. For multi-element arrays, the element position
offsets must be encoded in this phase.

**Recommendation:** Already handled by B3. When we expand center paths to
per-element paths, the per-element phase advance `exp(+i*k0 * k_hat_n . p_j)`
is baked into `psi_nj`. The existing `compute_body_channel()` in
`src/aegis/coherent/body_channel.py` already computes
`exp(-i*k0 * k_hat_n . r_m)` per surface point. These combine correctly:

```
psi_nj * exp(-i*k0*k_hat_n . r_m) = psi_n * exp(+i*k0*k_hat_n . p_j) * exp(-i*k0*k_hat_n . r_m)
                                   = psi_n * exp(-i*k0*k_hat_n . (r_m - p_j))
```

This is the correct plane-wave phase from element j at position p_j to
surface point r_m via propagation direction k_hat_n.

**Note on departure vs arrival directions:** The above uses `k_hat_n`
(arrival direction at the body). Strictly, the array factor uses the
departure direction `k_hat_{T,n}`. For far-field scatterers (distance >>
array aperture), the departure direction to a given scatterer is
approximately the same for all elements, so `k_hat_{T,n}` can be replaced by
the center-of-array departure direction. For LOS paths, `k_hat_T = -k_hat_n`
and the steering factor reduces to `exp(+i*k0*k_hat_n . p_j)` as written. For
reflected paths via far scatterers, the approximation error is
O(d_array / d_scatterer).

No changes to existing coherent code needed. The phase model comes for free
from correct path construction.

---

## D. Multi-user precoding

### D1. Which precoders to implement

**Problem.** Single-user AEGIS has MRT and ECBF. Multi-user needs precoders
that serve K users simultaneously. MRT is the baseline for single-user and
must extend to multi-user (per-user MRT, i.e. matched filtering per stream).

**Precoders, in implementation order:**

| # | Precoder | Formula | Role |
|---|----------|---------|------|
| 1 | **MRT (per-user)** | `w_k = sqrt(P/K) * h_k* / \|\|h_k\|\|` | Baseline. Maximizes per-user SNR, ignores inter-user interference and exposure. Already exists for single-user. |
| 2 | **Zero-Forcing (ZF)** | `W = H^H (H H^H)^{-1}`, column-normalize | Nulls inter-user interference. Closed-form. |
| 3 | **Regularized ZF (MMSE)** | `W = H^H (H H^H + alpha I)^{-1}` | Better conditioned than ZF, trades interference suppression for noise. |
| 4 | **ZF + exposure scaling** | ZF directions, scale each `w_k` to satisfy `w_k^H Q_u w_k <= P_abs_max` | Exposure-aware without a full optimizer. Good stepping stone. |
| 5 | **Multi-constraint ECBF** | QCQP with K*U exposure constraints. SCA or WMMSE. | The research contribution. |

**Decision: implement 1-4 in the initial build, defer 5.**

MRT is trivial (already exists, just call it per-user). ZF and MMSE are one
function each. ZF + exposure scaling is a natural bridge. Multi-constraint
ECBF is the research solver and needs careful validation against a CVXPY
reference. It comes in a follow-up pass.

---

### D2. Multi-constraint ECBF solver structure

**Problem.** The current ECBF solves a QCQP with one power constraint and one
exposure constraint via bisection on a single Lagrange multiplier. Multi-user
has K*U exposure constraints (K users, U bodies, each precoding vector w_k
must satisfy exposure limits on all U bodies).

**Options.**

| # | Option | Pros | Cons |
|---|--------|------|------|
| 1 | **Per-column SCA (successive convex approximation).** Fix all w except w_k, solve a single-constraint QCQP for w_k (reuse existing `solve_ecbf` with modified Q). Iterate. | Reuses existing solver. Provably convergent. | Slow convergence. |
| 2 | **WMMSE-style alternating optimization.** Well-studied in the MIMO literature. | Good performance. Well-understood theory. | More complex to implement. New solver from scratch. |
| 3 | **CVXPY/SciPy SOCP formulation.** Cast the QCQP as an SOCP and use a general-purpose solver. | Correct by construction. Easy to verify. | CVXPY dependency. Slower than custom solver for large M_ant. |
| 4 | **Projected gradient descent.** Gradient step on sum-rate, project onto constraint set. | Simple. JAX-friendly. | Slow, no convergence guarantee for non-convex. |

**Recommendation: Option 3 for correctness verification, Option 1 for
production.**

Start with CVXPY as a reference solver (already a common optional dependency
in wireless research). Use it to validate the custom solver. Then implement
the per-column SCA (Option 1), which reuses `solve_ecbf` almost unchanged:

```python
def solve_multi_ecbf(
    H: np.ndarray,             # (K, M_ant) stacked channel vectors
    Q_list: list[np.ndarray],  # U exposure operators, each (M_ant, M_ant)
    P_abs_max: float,          # per-user exposure budget
    P: float,                  # total Tx power
    max_iter: int = 50,
) -> np.ndarray:               # (M_ant, K) precoding matrix W
```

The per-column SCA inner loop: for user k, the effective exposure constraint
is `w_k^H Q_eff w_k <= P_abs_max - sum_{j!=k} w_j^H Q_u w_j`. This is a
tightened single-constraint ECBF.

---

### D3. Per-user vs per-body exposure constraints

**Problem.** User u's body is exposed by radiation from ALL precoding vectors
w_1, ..., w_K (not just w_u). The total absorbed power on body u is
`P_abs^(u) = sum_k w_k^H Q_u w_k` (incoherent across data streams because
data symbols are independent).

**Recommendation:** Per-body constraints. The constraint is on the total
absorbed power on each body, summed over all data streams:

```
sum_{k=1}^{K}  w_k^H Q_u w_k  <=  P_abs_max    for all u in {1,...,U}
```

In multi-user MIMO, U = K (each user is also an exposed body). But the
framework should support U != K for generality (a bystander who is not a
served user but still absorbs power).

This is a modeling decision, not an implementation question. The code
naturally handles it: Q_u is computed from any body in the scene, regardless
of whether that body is a "user" or a "bystander."

---

### D4. Power allocation across users

**Problem.** With K users, how is the total power P split?

**Decision: sum power constraint `sum_k ||w_k||^2 <= P`.**

Three normalization options, all supported:

1. **Per-column normalization:** `||w_k||^2 = P/K` for all k. Default for
   MRT. Each user gets equal transmit power. Simple, deterministic.

2. **Frobenius normalization:** `||W||_F^2 = sum_k ||w_k||^2 = P`. Default
   for ZF and MMSE. Total power is P but individual columns may have
   unequal power (ZF naturally allocates more power to weaker channels).

3. **Per-column power control:** Each `||w_k||^2` set independently to
   satisfy per-user exposure or rate targets. This is the full optimization
   case (ECBF, waterfilling). Deferred to v2.

For v1, MRT uses option 1, ZF and MMSE use option 2. The ZF normalization
step: `W_zf = H^H (H H^H)^{-1}`, then `W_zf *= sqrt(P) / ||W_zf||_F`.

---

## E. Kernel and engine changes

### E1. Engine multi-body awareness

**Problem.** `DosimetryEngine.compute()` takes one `BodyMesh` + one
`PropagationPaths`. Should it become multi-body aware?

**Options.**

| # | Option | Pros | Cons |
|---|--------|------|------|
| 1 | **Keep engine single-body, loop externally.** The `MIMOScene` calls `engine.compute()` K times. | Zero changes to tested engine code. Clean separation. | Repeated overhead (tissue init, averaging matrix). |
| 2 | **Add a `compute_multi()` method** that accepts a list of (body, paths) pairs. | Batch opportunities (shared tissue, shared averaging build). | More complex engine API. Must handle heterogeneous bodies. |

**Recommendation: Option 1 -- keep the engine unchanged.**

The engine is the most tested module (golden tests, property tests, Mie
canary). Modifying it introduces risk for minimal gain. The overhead of
repeated tissue init is negligible (one TissueModel per frequency, shared).
The averaging matrix is cached by body hash and reused.

The orchestration logic goes into `src/aegis/mimo/scene.py`:

```python
def compute_scene(scene: MIMOScene, engine: DosimetryEngine, level: int):
    for user in scene.users:
        user.result = engine.compute(user.body, user.paths, level=level)
```

---

### E2. Different tissue models per phantom

**Problem.** A child phantom might need different tissue properties than an
adult. The current engine takes one `TissueModel`.

**Recommendation:** This is already solved. Each `engine.compute()` call uses
one TissueModel. If the child needs different tissue, create a second
`DosimetryEngine(child_tissue)`. The scene orchestrator can map phantom type
to tissue model. For the MVP, use the same tissue for all users (skin
properties are not strongly age-dependent at 28 GHz).

---

### E3. Batching Q computation across users

**Problem.** Computing Q requires `G_tilde` which is O(M_tri * 3 * M_ant)
per user. With 4 users, we build 4 independent G_tilde matrices. Is there
a batching opportunity?

**Recommendation:** No batching needed. Each user has different body geometry
(different normals, centroids, areas) and different paths (different
positions). There is no shared computation to factor out. The only shared
input is `n_tilde` and `sigma`, which are scalars. Build Q independently per
user.

The compute cost is honest: 4 users = 4x the G_tilde and Q computation.
This is unavoidable physics.

---

### E4. Which kernel levels for multi-user

**Problem.** Multi-user precoding is inherently coherent (levels 7-8). But
quick previews at level 2 (geometric ReLU, incoherent) are valuable for
interactive positioning.

**Recommendation:** Support two modes:

1. **Preview mode (incoherent, levels 2-6):** Use the existing single-user
   pipeline per user, with isotropic radiation from the array center. This
   gives a quick heatmap showing which body regions face the antenna. No
   precoding, no Q.

2. **Full mode (coherent, levels 7-8):** Build G_tilde and Q per user.
   Compute precoder W = [w_1, ..., w_K]. Per-user heatmap is
   `Sab_u(r) = sum_{k=1}^{K} ||G_tilde_u(r) @ w_k||^2` (sum over ALL K
   precoders, not just stream u). This is the monograph's eq:Sab-MU-expect:
   uncorrelated data symbols cause cross-stream terms to vanish pointwise.
   Implementation: `sab_u = sum_k ||G_tilde_u @ w_k||^2` via a single
   Frobenius norm: `sab_u(r) = ||G_tilde_u(r) @ W||_F^2`.

The viewer can switch between these. Preview mode is fast (sub-second for
level 2). Full mode is the real result.

---

## F. Viewer backend changes

### F1. API shape

**Problem.** Currently `/api/compute` accepts one antenna_pos and one
body_offset, returns one binary sab array. Multi-user needs results for
multiple bodies.

**Options.**

| # | Option | Pros | Cons |
|---|--------|------|------|
| 1 | **New `/api/mimo/compute` batch endpoint.** Accepts scene config (array + users), returns per-user results in one response. | Single round-trip. Atomic. | Larger payload. Cannot update one user independently. |
| 2 | **Per-user `/api/compute?user_id=X` endpoint.** Extends existing endpoint with user selection. | Incremental, backward-compatible. | K round-trips for K users. Race conditions if scene changes between calls. |
| 3 | **Hybrid: batch compute, per-user fetch.** `/api/mimo/compute` triggers computation for all users. `/api/mimo/result/{user_id}` fetches individual results. | Compute once, fetch as needed. Supports lazy frontend. | Two endpoints. Cache management. |

**Recommendation: Option 3 -- hybrid.**

The compute is the expensive part and must be atomic (all users with the same
precoder). The fetch is cheap (serve cached binary). This also supports the
"focused user" UX: compute all, but only transfer the focused user's heatmap
initially, fetch others on demand.

```
POST /api/mimo/compute
  Body: { array: {...}, users: [...], freq_hz, power_dbm, ... }
  Returns: { user_ids: [...], compute_time_ms, precoder_type, ... }

GET /api/mimo/result/{user_id}
  Returns: binary sab (same format as current /api/compute)
  Headers: X-Stats (same format as current, but per-user)

GET /api/mimo/summary
  Returns: { users: [{id, p_abs, compliant, ...}], precoder: {...} }
```

The existing `/api/compute` continues to work for single-user mode.

---

### F2. Cache structure

**Problem.** Currently `cache["body"]` is a single BodyMesh. Need to store
multiple bodies.

**Recommendation:** Add `cache["mimo_scene"]` containing the `MIMOScene`
object. Each `UserState` within it holds its own `BodyMesh`, `G_tilde`, `Q`,
and `DosimetryResult`. The old `cache["body"]` stays for backward
compatibility (single-user mode).

```python
cache = {
    # Existing (single-user)
    "body": BodyMesh,
    "body_binary": bytes,
    "body_meta": dict,
    "config": dict,
    # New (multi-user)
    "mimo_scene": MIMOScene | None,
    "mimo_results_binary": {user_id: bytes},
    "mimo_results_stats": {user_id: dict},
}
```

---

### F3. Config structure for multi-user scenarios

**Problem.** Config needs to express array geometry and multiple users.

**Recommendation:** Extend the `scenarios` section in config.py DEFAULTS:

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
    "precoder": "zf",
    "exposure_budget_mw": 100,
}
```

When `mimo.enabled` is True, the viewer uses the multi-user pipeline.
When False, it uses the existing single-user pipeline. This ensures
backward compatibility.

---

### F4. Compute flow

**Problem.** Computing dosimetry for 4 users at level 7 with a 16-element
array is ~4x slower than single user. Should we compute all at once or
on-demand?

**Recommendation:** Compute all users atomically (the precoder depends on all
Q_u), but serve results lazily. The flow:

1. Frontend sends `POST /api/mimo/compute` with full scene config.
2. Backend loads/caches all body meshes, generates paths for all users.
3. Backend builds G_tilde and Q for each user.
4. Backend computes precoder W using all {Q_u} and {h_k}.
5. Backend computes `sab` for each user and caches results.
6. Backend returns summary (compute time, per-user compliance yes/no).
7. Frontend fetches detailed results for the focused user via
   `GET /api/mimo/result/{user_id}`.

Steps 2-5 must be atomic because the precoder depends on all users. But the
binary transfer in step 7 is per-user and on-demand.

---

## G. Frontend changes

### G1. Store architecture

**Problem.** The simulation store has scalar fields: one `sabArray`, one
`antennaPos`, one `bodyOffset`. Multi-user needs per-user versions.

**Decision: separate MIMO store + adaptor hook.**

A new `useMIMOStore` holds all multi-user state. To avoid feature-flag
spaghetti (every component branching on `mimoEnabled`), a single
`useActiveSimulation()` adaptor hook dispatches to the right backing store.
Components consume this hook and never know whether they are in single-user
or MIMO mode.

```typescript
// useActiveSimulation.ts
function useActiveSimulation() {
  const mimoEnabled = useMIMOStore(s => s.enabled)
  const focusedUser = useMIMOStore(s => s.focusedUser())

  if (mimoEnabled && focusedUser) {
    return {
      sabArray: focusedUser.sabArray,
      stats: focusedUser.stats,
      bodyGeometry: focusedUser.bodyGeometry,
      bodyOffset: focusedUser.position,
      bodyRotationY: focusedUser.orientation,
      // ...
    }
  }
  // Fall back to single-user store
  return useSimulationStore(s => ({
    sabArray: s.sabArray,
    stats: s.stats,
    // ...
  }))
}
```

The MIMO store:

```typescript
interface MIMOStore {
  enabled: boolean
  users: Map<string, UserMIMOState>
  focusedUserId: string | null
  controlledUserId: string | null   // which user WASD controls
  precoderType: 'mrt' | 'zf' | 'mmse' | 'zf_exposure'
  arrayConfig: ArrayConfig | null
  summaryStats: MIMOSummary | null
  showAllHeatmaps: boolean          // toggle: all heatmaps vs focus-only

  // Actions
  addUser: (phantom: string, position: ScenePos) => void
  removeUser: (id: string) => void
  setFocusedUser: (id: string) => void
  setControlledUser: (id: string) => void
  moveUser: (id: string, position: ScenePos) => void
  setUserResult: (id: string, sab: Float32Array, stats: DosimetryStats) => void
  setPrecoderType: (type: string) => void
  setShowAllHeatmaps: (on: boolean) => void
}

interface UserMIMOState {
  userId: string
  displayName: string              // "User 1", "User 2", ...
  phantomName: string              // "thelonious", "duke", "eartha", "ella"
  position: ScenePos
  orientation: number
  deviceOrientation: [number, number, number]  // dipole axis in world coords
  bodyGeometry: BufferGeometry | null
  sabArray: Float32Array | null
  stats: DosimetryStats | null
  compliant: boolean | null
}
```

User naming: auto-generated as "User 1", "User 2", etc. The display name
can be overridden but defaults are fine. The userId is a stable UUID.

Zustand re-render strategy: use selectors that pick individual user fields.
`useMIMOStore(s => s.users.get(userId)?.sabArray)` only re-renders when that
specific user's sab changes. The Map structure with shallow equality checks
prevents cascade re-renders.

---

### G2. Rendering multiple bodies

**Problem.** `BodyMesh.tsx` renders one mesh. Need to render K meshes with
independent heatmaps at different positions.

**Decision:** Factor `BodyMesh.tsx` into a reusable `BodyMeshInstance` that
takes explicit props (geometry, sabArray, position, etc.) instead of reading
from the store. The existing `BodyMesh` becomes a thin wrapper that pulls
from the simulation store and delegates to `BodyMeshInstance`.

```tsx
// SceneRoot.tsx
{mimoEnabled ? (
  <>
    {users.map(user => (
      <BodyMeshInstance
        key={user.userId}
        geometry={user.bodyGeometry}
        sabArray={showAllHeatmaps ? user.sabArray : (
          user.userId === focusedUserId ? user.sabArray : null
        )}
        position={user.position}
        rotation={user.orientation}
        opacity={user.userId === focusedUserId ? 1.0 : 0.7}
        onClick={() => setFocusedUser(user.userId)}
      />
    ))}
    <AntennaArray config={arrayConfig} />
  </>
) : (
  <>
    <BodyMesh />
    <Antenna />
  </>
)}
```

**Heatmap display modes** (toggle via `showAllHeatmaps`):
- **Focus mode:** Focused user has full heatmap. Other users show their last
  computed heatmap (cached) or a neutral material if never computed. Not gray,
  just the cached result at reduced opacity.
- **All mode:** All users show heatmaps simultaneously with a shared colormap
  scale (global max across all users determines the legend).

When bodies share the same phantom mesh (e.g., two thelonious), the
geometry is fetched once and cloned. The color attribute (heatmap) is
per-instance. The infra branch already supports `GET /api/body?name=X`
for fetching individual meshes.

---

### G3. User management UI

**Problem.** Users need to add, remove, select, and name phantom users.
This is a primary UI element that drives most of the MIMO experience.

**Decision:** A prominent "Users" panel in the sidebar with:

1. **"Add User" button** at the top. Opens a dropdown to select phantom type
   (thelonious, duke, eartha, ella). New user is placed at a default offset
   from the array, auto-named "User N+1".

2. **User list** showing each user with:
   - Display name (editable inline)
   - Phantom type (changeable via dropdown)
   - Compliance badge (green/yellow/red circle)
   - Peak Sab value
   - "Focus" button (eye icon) to make this user the focused user
   - "Control" button (gamepad icon) to make WASD control this user
   - "Remove" button (x icon)

3. **Active user indicator:** The controlled user has a visible highlight
   in the 3D scene (subtle outline or ground marker) so the user knows
   which phantom WASD will move.

4. **Keyboard controls:** WASD moves the controlled user (not the camera).
   Camera orbits around the controlled user. Number keys 1-9 switch the
   controlled user. Tab cycles through users.

The user list is always visible in MIMO mode. It replaces the phantom
selector dropdown in the sidebar (which currently picks a single phantom).

---

### G4. Antenna array visualization

**Problem.** Currently the antenna is a red sphere + cone + pole. An array
of 16 elements needs a different visual.

**Decision:** Replace the single antenna visual with an array grid:

- Small sphere per element, arranged in the UPA pattern (InstancedMesh).
- Shared pole/base structure.
- Broadside direction shown as a cone or arrow.
- Optional: color elements by precoding weight magnitude for the focused
  user's stream.

The array is draggable (existing antenna drag behavior). Moving the array
triggers a full recompute (same as moving a user).

---

### G5. Per-user compliance display

**Problem.** The compliance panel shows one set of results. Multi-user needs
per-user compliance.

**Decision:** Two levels:

1. **Summary badges** in the user list panel: colored circle per user
   (green = compliant, yellow = within 10% of limit, red = exceeds limit).
   Shows peak Sab and margin. Visible at all times.

2. **Detail panel** for the focused user: the existing compliance panel,
   populated with the focused user's data (Sab map, spatial average, peak,
   ICNIRP limit comparison).

3. **Global summary** in the toolbar: "3/4 users compliant" or a single
   worst-case indicator.

---

### G6. Interactive positioning and recompute strategy

**Problem.** Moving one user changes Q_u for that user. But the precoder
depends on ALL Q_u matrices. So moving one user requires recomputing the
precoder and all per-user Sab arrays. This can take seconds.

**Decision: preview mode during drag, full compute on release.**

1. **During drag (mousedown + mousemove):** Show an incoherent preview
   (level 2) for the moved user only. This takes ~100ms and gives
   instant visual feedback (which body regions face the antenna).
   Other users' heatmaps stay cached from the last full compute.

2. **On drag end (mouseup):** Trigger full coherent compute for all users.
   Show a progress indicator ("Computing MIMO...") while Q matrices and
   precoders are rebuilt.

3. **Precoder switching:** When the user changes precoder type (MRT -> ZF),
   Q matrices do not need recomputation (Q depends on geometry and paths,
   not the precoder). Only the precoder and per-user Sab need updating.
   This should be near-instant for small arrays (~10ms for 16 elements).

4. **Adding a user:** Triggers body mesh fetch, path generation, Q
   computation for the new user, precoder recomputation for all users, and
   Sab recomputation for all users.

5. **Debounce:** Full compute is debounced at 500ms after the last change.
   Multiple rapid changes (drag multiple users in sequence) coalesce into
   one compute.

---

## G+. User lifecycle and invalidation

This section specifies every user lifecycle operation and its cascading
consequences through the entire stack. The precoder W depends on ALL users
simultaneously, so ANY change to ANY user invalidates W and therefore ALL
users' heatmaps. This coupling is the fundamental challenge.

### Dependency graph of cached quantities

```
body mesh (geometry, position-independent)
    |
    v
paths_u (PropagationPaths, depends on: body position, body orientation, array position, array geometry, frequency, channel model)
    |
    +--> G_tilde_u (body channel, depends on: paths_u, body mesh_u, tissue, frequency)
    |       |
    |       +--> Q_u (exposure operator, depends on: G_tilde_u, body areas_u)
    |
    +--> h_u (comm channel, depends on: paths_u, device position_u, device orientation_u)

Q_1..Q_K + h_1..h_K + precoder type + power
    |
    v
W = precoder(H, {Q_u}, P)   -- DEPENDS ON ALL USERS
    |
    v
sab_u(r) = ||G_tilde_u(r) @ W||_F^2   -- DEPENDS ON ALL COLUMNS OF W
```

### Invalidation matrix

Each row is an operation. "x" = must recompute, "." = reusable, "(s)" = scale only.
Subscript u = affected user, v = other users.

```
                    | paths_u | G_tilde_u | Q_u | h_u | paths_v | G_tilde_v | Q_v | h_v | W  | sab_all |
--------------------|---------|-----------|-----|-----|---------|-----------|-----|-----|----|---------|
Add user            |  NEW    |  NEW      | NEW | NEW |    .    |     .     |  .  |  .  | x  |   x     |
Remove user         |  DEL    |  DEL      | DEL | DEL |    .    |     .     |  .  |  .  | x  |   x     |
Change phantom      |   x     |   x       |  x  |  x  |    .    |     .     |  .  |  .  | x  |   x     |
Move user           |   x     |   x       |  x  |  x  |    .    |     .     |  .  |  .  | x  |   x     |
Rotate user         |   x     |   x       |  x  |  x  |    .    |     .     |  .  |  .  | x  |   x     |
Move smartphone     |   .     |   .       |  .  |  x  |    .    |     .     |  .  |  .  | x  |   x     |
Rotate smartphone   |   .     |   .       |  .  |  x  |    .    |     .     |  .  |  .  | x  |   x     |
Move array          |   x     |   x       |  x  |  x  |    x    |     x     |  x  |  x  | x  |   x     |
Change array geo    |   x     |   x       |  x  |  x  |    x    |     x     |  x  |  x  | x  |   x     |
Change frequency    |   x     |   x       |  x  |  x  |    x    |     x     |  x  |  x  | x  |   x     |
Change precoder     |   .     |   .       |  .  |  .  |    .    |     .     |  .  |  .  | x  |   x     |
Change power        |   .     |   .       |  .  |  .  |    .    |     .     |  .  |  .  |(s) |  (s)    |
Switch channel      |   x     |   x       |  x  |  x  |    x    |     x     |  x  |  x  | x  |   x     |
Focus/control user  |   .     |   .       |  .  |  .  |    .    |     .     |  .  |  .  |  . |   .     |
```

Key insight: operations that only touch h (move/rotate smartphone) or only W
(change precoder) are cheap (~100-200ms). Operations that touch G_tilde/Q are
expensive (~1-3s for 4 users). Power changes are free (frontend scaling).

### Operation details

**Add user.** UI: "Add User" button, select phantom from dropdown. New user
placed at default offset (2m from array broadside, lateral offset K*1m).
Auto-named "User N+1". UUID generated on frontend. If first user, set as
both focused and controlled. Compute: fetch body mesh, generate paths, build
G_tilde/Q/h for new user only. Recompute W and sab for ALL users. Reuse
all existing users' cached Q/h.

**Remove user.** UI: "X" button on user row. UUID-based, no renumbering of
display names (avoids confusion). If removed user was focused/controlled,
transfer to next user. Compute: garbage collect removed user's state,
recompute W and sab for remaining users using cached Q/h.

**Change phantom type.** UI: phantom dropdown on user row. Full invalidation
for that user (new mesh, new paths, new G_tilde/Q/h). Other users untouched.
Recompute W and sab for all.

**Move user (drag/WASD).** Two phases:
- During drag: update position in store, move Three.js mesh. Optional
  incoherent level-2 preview for moved user (~100ms). Other users frozen.
- On release: full coherent compute. Invalidates paths/G_tilde/Q/h for moved
  user. Other users' cached state reused. Recompute W and sab for all.

**Rotate user.** Same invalidation as move (normals change, Fresnel changes).
Same two-phase preview/commit.

**Move/rotate smartphone.** Cheap: only h changes for that user. Q and
G_tilde unaffected (body surface properties independent of smartphone).
Recompute W and sab. Should feel instant (~200ms).

**Move array.** Full pipeline restart for ALL users. Everything depends on
array position. Preview mode during drag (level 2 for focused user only).

**Change array geometry (N_h, N_v, d).** Same as move array but also changes
M_ant dimension. G_tilde shape changes, Q shape changes, h shape changes.
Edge case: if M_ant drops below K, ZF/MMSE are infeasible. Fall back to MRT
with a warning.

**Change frequency.** Full pipeline restart. Tissue model changes, wavelength
changes, element spacing changes (if specified in wavelength fractions).

**Change precoder type.** Cheap: only W and sab. All Q/h cached. Should feel
instant (~200ms for 4 users with 16 elements).

**Change power.** Free: frontend scales cached sab arrays by P_new/P_ref.
No backend call. Compliance recheck only.

**Switch channel model.** Full pipeline restart. Stochastic disabled for
multi-user K>=2 (grayed out in UI with tooltip).

**Focus/control user.** Pure frontend state. No compute, no fetch (unless
focused user's sab hasn't been transferred yet in lazy-fetch mode).

### Compute orchestration protocol

The `POST /api/mimo/compute` request includes a `changed` field:

```json
{
  "array": {...},
  "users": [...],
  "freq_hz": 28e9,
  "power_dbm": 60,
  "precoder_type": "zf",
  "changed": {
    "type": "user_moved",
    "user_id": "uuid-1"
  }
}
```

The backend uses `changed.type` to determine minimal recomputation per the
invalidation matrix above. The session-scoped cache holds per-user Q/h/G_tilde
between requests. A generation counter prevents stale results from being
applied (if the user makes a change while compute is in flight, the old
response is discarded).

### Edge cases

**K=0 (no users).** MIMO enabled, no users added. Scene shows only the
antenna array. "Add User" button prominent. No compute possible.

**K=1.** Degenerates to single-user coherent. ZF with K=1 = MRT (the
pseudoinverse of a 1xM row is the normalized conjugate). Sab formula with
K=1 reduces to existing level-7 computation. The implementing agent must add
a test asserting numerical equivalence between the multi-user pipeline at
K=1 and the existing single-user level-7 pipeline.

**K=K_max.** "Add User" button disabled. K_max is a config parameter
(default 8). At M_ant=16 and K=8: ~720 MB backend memory, ~4s compute.

**Duplicate phantoms.** Two users with same phantom share the base geometry
(fetched once). Heatmap colors are per-instance. Backend reuses the loaded
BodyMesh by reference.

**M_ant < K.** ZF/MMSE infeasible. Auto-fall-back to MRT. Disable ZF/MMSE
in precoder dropdown. Show warning.

**ZF near-singular H.** Two users at similar directions from the array cause
rank-deficient H H^H. MMSE regularization handles this. ZF may produce
extreme power allocation. The ZF+exposure-scaling precoder is more robust.

### User IDs and naming

UUIDs (via `crypto.randomUUID()`), not sequential integers. Prevents
cache key reuse after remove+add. Display names auto-generated as
"User 1", "User 2", etc., editable inline. Display names are NOT renumbered
when a user is removed (User 1, User 3 after removing User 2). User ordering
in the list is insertion order. Ordering does not affect results (ZF is
permutation-equivariant).

### Performance budget

| Operation | Target latency | Bottleneck |
|-----------|---------------|------------|
| Add user (fetch + compute) | < 3s | G_tilde + Q for new user |
| Move user (preview) | < 100ms | Level-2 incoherent |
| Move user (full compute) | < 3s | G_tilde + Q for moved user |
| Move smartphone | < 200ms | h + W + sab only |
| Change precoder | < 200ms | W + sab only |
| Change power | < 10ms | Frontend scaling |
| Focus/control user | < 1ms | Frontend state only |
| Full scene recompute | < 5s | All users, all quantities |

---

## H. Testing strategy

### H1. Golden tests for multi-user

**Recommendation:** Add golden tests for:

1. **Two-user ZF:** Known array geometry, known body positions, known
   channels. Verify precoder W against a hand-computed reference.
2. **Exposure operator additivity:** `sum_k w_k^H Q_u w_k` from the code
   matches `trace(W^H Q_u W)` from theory.
3. **Two-user ECBF:** Verify that all exposure constraints are satisfied.

Place in `tests/golden/test_multiuser.py`.

---

### H2. Property tests (invariants)

**Recommendation:** Key invariants for Hypothesis:

1. `P_abs_total = sum_u sum_k w_k^H Q_u w_k >= 0` (non-negative).
2. `sum_u P_abs^(u) <= P * lambda_max(sum_u Q_u)` (upper bound).
3. For ZF precoder: `H @ W = I` up to a scaling factor (zero inter-user
   interference).
4. For exposure-constrained precoders: `sum_k w_k^H Q_u w_k <= P_abs_max`
   for all u (constraints satisfied).
5. `S_ab(r) >= 0` for all triangles, all users (physics).

---

### H3. Frontend testing

**Recommendation:** Playwright snapshot tests:

1. Load a 2-user scene, verify two bodies render at correct positions.
2. Click each body, verify compliance panel updates.
3. Switch precoder type, verify heatmaps update.

These extend the existing screenshot-based testing approach.

---

## I. Performance concerns

### I1. Memory: multiple G_tilde matrices

**Problem.** `G_tilde` is (M_tri, 3, M_ant) complex128. For thelonious
(~100k triangles) and a 16-element array:

```
100,000 * 3 * 16 * 16 bytes = 76.8 MB per user
4 users = 307 MB
```

With a 64-element array (8x8): 4.8 GB for 4 users. That is too much.

**Recommendation:** Three mitigations:

1. **Downsampled body for G_tilde.** The viewer already uses full-res meshes
   for visualization but could use a decimated mesh (10k triangles) for
   G_tilde. The spatial averaging step (4 cm^2) already blurs fine detail.
   10k triangles with 64 elements = 30 MB per user.

2. **Build Q without storing G_tilde.** Q is M_ant x M_ant, which is tiny
   (64x64 = 32 KB). Build it in a streaming fashion:
   `Q += G_tilde[m]^H @ G_tilde[m] * area[m]` triangle by triangle, then
   discard G_tilde rows. Only store Q.

3. **Only store G_tilde for the focused user** (needed for sab computation).
   Others store only Q.

Option 2 is the most impactful. Refactor `compute_exposure_operator` to
accept a generator or process in chunks.

---

### I2. Compute cost

**Problem.** Q computation is O(M_tri * M_ant^2) per user. 4 users with
100k triangles and 16 elements: ~1s. With 64 elements: ~16s.

**Recommendation:** Acceptable for the viewer (compute is triggered on
demand, not per frame). For larger arrays, the decimated mesh (I1) brings
this down proportionally. JAX backend can parallelize the einsum.

---

### I3. Frontend rendering

**Problem.** 4 detailed meshes (100k triangles each) with per-vertex colors.

**Recommendation:** Three.js handles this. 400k triangles total is well
within GPU budgets. Use `InstancedMesh` only for the antenna array elements.
Each body mesh is a separate `<mesh>` with its own geometry and color
attribute (they have different topologies so instancing does not apply).

Optimization if needed: render non-focused bodies with a simpler material
(flat color, no heatmap) and only apply heatmap colors to the focused body.

---

### I4. Lazy vs eager computation

**Recommendation:** Eager Q computation for all users (needed for the
precoder), lazy sab computation per user (only compute for the focused
user initially, compute others on demand).

The bottleneck is not per-user sab (that is a single `G_tilde @ w_k`
matvec), but the Q computation. Since Q is needed for all users to compute
the precoder, there is no way to be lazy about it.

---

## J. Phasing and MVP

### J1. Minimum viable multi-user demo

**The initial build includes:**

1. `AntennaArray` dataclass with `upa()` constructor, steering vectors
   (`exp(+i*k0*k_hat.p_j)` transmit convention).
2. `UserConfig` and `UserState` dataclasses.
3. `MIMOScene` with array + users.
4. `expand_paths_to_array()` -- shared directions, per-element phase steering.
5. Communication channel `h_k` with half-wave dipole UE pattern (full EM
   response, not the sin(theta) approximation).
6. Analytical and ray-traced channel models for multi-user. Stochastic
   disabled for multi-user (flagged in UI with tooltip).
7. Precoders: MRT, ZF, MMSE, ZF+exposure-scaling. ZF normalized to
   sum power constraint.
8. Per-user `G_tilde`, `Q`, and multi-stream `sab` via existing engine
   (called in a loop). `Sab_u(r) = sum_k ||G_tilde_u(r) @ w_k||^2`.
9. Backend: `/api/mimo/compute`, `/api/mimo/result/{user_id}`,
   `/api/mimo/summary`. Session-scoped cache for Q matrices.
10. Frontend: MIMO store with adaptor hook, multi-body rendering, "Add User"
    button, user list panel, WASD control of selected user, per-user
    compliance badges, antenna array visualization, toggle between
    focused/all heatmap display, preview-during-drag with full compute
    on release.
11. Golden test: 2-user ZF with known geometry.
12. Property tests: multi-user invariants (sum P_abs <= total power,
    Sab >= 0, Q Hermitian PSD, ZF inter-user interference near zero).

End-to-end demo: multiple phantoms at different positions (different body
types), a UPA base station, MRT/ZF/MMSE precoding, interactive positioning
with WASD, per-user heatmaps with compliance checking, shared colormap.

---

### J2. What can be deferred

Items safe to defer to v2:

- Multi-constraint ECBF solver (research contribution, needs careful validation).
- Realistic BS element patterns (cos^n instead of isotropic).
- 3GPP multi-link LSP correlation for stochastic channels (blocks stochastic
  multi-user entirely, clearly flagged in UI).
- Per-user tissue model differences (child vs adult EM properties).
- Max-min SINR fairness power allocation.
- Bystander support (U != K, bodies without a served smartphone).
- CVXPY reference solver for ECBF validation.
- Memory optimization (streaming Q computation for large arrays).
- Per-stream Sab decomposition (show which data stream contributes most to
  each user's exposure, useful for debugging precoder behavior).

---

## Summary of all decisions

| ID | Decision | Recommendation | Needs input? |
|----|----------|---------------|--------------|
| A1 | Primary antenna abstraction | `AntennaArray` dataclass (geometry only) | No |
| A2 | User representation | `UserConfig` (frozen) + `UserState` (mutable) | No |
| A3 | Scene abstraction | `MIMOScene` dataclass | No |
| A4 | Smartphone abstraction | Fields on `UserConfig`, no separate type | No |
| A5 | PropagationPaths in multi-user | One per user, shared element index space | No |
| B1 | UPA geometry | `upa()` classmethod, distances in meters | No |
| B2 | Element pattern | Isotropic for MVP | No |
| B3 | Per-element path generation | Shared directions + per-element phase | No |
| B4 | Steering vectors | Method on `AntennaArray` | No |
| C1 | Communication channel h_k | Full multipath with half-wave dipole UE pattern | No |
| C2 | Paths to body | Existing generators + `expand_paths_to_array` | No |
| C3 | Channel model support | All three (analytical, stochastic, RT) from the start | No |
| C4 | Phase model | Comes free from correct path construction | No |
| D1 | Precoder order | MRT -> ZF -> MMSE -> ZF+scaling -> multi-ECBF | No |
| D2 | Multi-ECBF solver | CVXPY reference + per-column SCA | No |
| D3 | Exposure constraints | Per-body, summed over all streams | No |
| D4 | Power allocation | Sum power constraint, equal default | No |
| E1 | Engine changes | None (loop externally) | No |
| E2 | Per-phantom tissue | Same TissueModel for MVP | No |
| E3 | Batch Q | No batching (independent geometry) | No |
| E4 | Kernel levels | Preview (2-6) + Full (7-8) | No |
| F1 | API shape | Hybrid: batch compute + per-user fetch | No |
| F2 | Cache structure | `cache["mimo_scene"]` + per-user binaries | No |
| F3 | Config structure | `mimo` section with array + users | No |
| F4 | Compute flow | Atomic compute, lazy fetch | No |
| G1 | Store architecture | Separate MIMO Zustand store | No |
| G2 | Multi-body rendering | Reusable BodyMeshInstance, all heatmaps toggle | No |
| G3 | User management | Add/remove users, WASD control, keyboard switching | No |
| G4 | Array visualization | InstancedMesh grid of small spheres | No |
| G5 | Per-user compliance | Summary badges + focused detail panel | No |
| H1 | Golden tests | 2-user ZF with hand-computed reference | No |
| H2 | Property tests | 5 invariants (non-neg, bound, ZF null, constraints, physics) | No |
| H3 | Frontend tests | Playwright snapshots for 2-user scene | No |
| I1 | Memory | Streaming Q build, decimated mesh option | No |
| I2 | Compute cost | Acceptable, decimated mesh for large arrays | No |
| I3 | Frontend rendering | Standard Three.js, simplify non-focused bodies | No |
| I4 | Lazy vs eager | Eager Q (needed for precoder), lazy sab | No |
| J1 | MVP scope | Array + users + ZF + viewer, 10 items | No |
| J2 | Deferred items | ECBF, RT paths, tissue differences, fairness | No |
| -- | Execution strategy | Phased with parallel worktrees, ~6 sessions (see top of doc) | No |

---

## Files that will be created or modified

**New files (Phase 1-3):**
- `src/aegis/mimo/__init__.py`
- `src/aegis/mimo/array.py`
- `src/aegis/mimo/user.py`
- `src/aegis/mimo/scene.py`
- `src/aegis/mimo/array_paths.py`
- `src/aegis/mimo/channel.py`
- `src/aegis/mimo/precoders.py`
- `src/aegis/mimo/compute.py`
- `src/aegis/viewer/routes/mimo.py`
- `aegis-web/src/stores/mimo.ts`
- `aegis-web/src/components/scene/BodyMeshInstance.tsx`
- `aegis-web/src/components/scene/AntennaArray.tsx`
- `aegis-web/src/components/hud/MIMOPanel.tsx`
- `tests/test_mimo_array.py`
- `tests/test_mimo_paths.py`
- `tests/golden/test_multiuser.py`

**Modified files:**
- `src/aegis/viewer/config.py` -- add `mimo` DEFAULTS section
- `src/aegis/viewer/routes/__init__.py` -- register MIMO routes
- `aegis-web/src/components/scene/SceneRoot.tsx` -- conditional multi-body rendering
- `aegis-web/src/components/scene/Antenna.tsx` -- optional array mode
- `aegis-web/src/components/hud/` -- compliance badges, user panel

**Unchanged files (by design):**
- `src/aegis/engine.py`
- `src/aegis/paths.py`
- `src/aegis/precoder.py` (existing single-user Precoder stays)
- `src/aegis/result.py`
- `src/aegis/coherent/` (all files)
- `src/aegis/kernels/` (all files)
- `src/aegis/tissue/` (all files)
- `src/aegis/geometry/mesh.py`
- All existing tests
