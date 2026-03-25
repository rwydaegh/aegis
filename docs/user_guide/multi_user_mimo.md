# Multi-user MIMO

AEGIS evaluates absorbed power density for multiple users served simultaneously by a phased antenna array. Each user has their own body mesh, position, and exposure map. The engine computes per-user exposure operators $\mathbf{Q}_u$, builds a multi-user precoder $\mathbf{W} = [\mathbf{w}_1, \dots, \mathbf{w}_K]$, and reports per-user compliance.

This page covers the Python API and the interactive viewer workflow. For single-user coherent dosimetry (one body, one precoder), see [coherent MIMO](coherent.md).

## Core idea

In single-user MIMO, one precoding vector $\mathbf{x}$ shapes the beam toward one user. In multi-user MIMO, each user $k$ gets their own precoding vector $\mathbf{w}_k$, and every body in the scene absorbs power from all $K$ beams. The absorbed power density on body $u$ is:

$$S_{\mathrm{ab}}^{(u)}(\mathbf{r}) = \sum_{k=1}^{K} \|\tilde{\mathbf{G}}_u(\mathbf{r}) \, \mathbf{w}_k\|^2 = \|\tilde{\mathbf{G}}_u(\mathbf{r}) \, \mathbf{W}\|_F^2$$

The cross-stream terms vanish because data symbols are uncorrelated across users. Total absorbed power on body $u$ is $P_{\mathrm{abs}}^{(u)} = \sum_k \mathbf{w}_k^H \mathbf{Q}_u \, \mathbf{w}_k = \mathrm{tr}(\mathbf{W}^H \mathbf{Q}_u \mathbf{W})$.

The exposure constraint is per-body, not per-stream:

$$\sum_{k=1}^{K} \mathbf{w}_k^H \mathbf{Q}_u \, \mathbf{w}_k \le P_{\mathrm{abs}}^{\mathrm{max}} \quad \text{for all } u$$

This means precoding for user 3 can violate the exposure limit on user 1's body, even if user 1's own stream is benign.

## Antenna array

The `AntennaArray` dataclass holds element positions in world coordinates. It carries geometry only, no frequency or power.

```python
from aegis.mimo import AntennaArray

# 4x4 uniform planar array, half-wavelength spacing at 28 GHz
lam = 3e8 / 28e9  # 10.7 mm
array = AntennaArray.upa(
    n_h=4, n_v=4,
    d_h=0.5 * lam, d_v=0.5 * lam,
    center=np.array([5.0, 0.0, 3.0]),
    broadside=np.array([-1.0, 0.0, 0.0]),
)
print(array.n_elements)  # 16
```

The `upa()` constructor builds element positions on a grid perpendicular to the broadside direction. Element spacing is in meters, not wavelength fractions, so the geometry is independent of frequency.

Steering vectors map a propagation direction to per-element phase shifts:

```python
k_hat = np.array([-0.8, 0.0, -0.6])  # arrival direction at body
a = array.steering_vector(k_hat, freq_hz=28e9)  # (16,) complex
```

## Users

Each user in the scene is described by a `UserConfig` (static inputs) and tracked by a `UserState` (computed quantities).

```python
from aegis.mimo import UserConfig

user_a = UserConfig(
    user_id="alice",
    phantom_name="thelonious",
    position=np.array([0.0, 0.0, 0.0]),
    orientation=0.0,
    device_position=np.array([0.25, 0.0, 1.4]),
    device_orientation=np.array([0.0, 0.0, 1.0]),  # vertical dipole
)

user_b = UserConfig(
    user_id="bob",
    phantom_name="duke",
    position=np.array([0.0, 2.0, 0.0]),
    orientation=0.0,
    device_position=np.array([0.25, 2.0, 1.4]),
    device_orientation=np.array([0.0, 0.0, 1.0]),
)
```

The `device_position` and `device_orientation` define a half-wave dipole at the smartphone location. The communication channel $\mathbf{h}_k$ is computed from the multipath environment observed at this point.

## Building the scene

A `MIMOScene` groups the array, users, and shared parameters.

```python
from aegis.mimo import MIMOScene

scene = MIMOScene(
    array=array,
    users=[user_a_state, user_b_state],
    freq_hz=28e9,
    total_power=1.0,  # W
    tissue=tissue,
)
```

The scene does not generate paths or compute results on construction. That happens in the compute step.

## Path expansion

Propagation paths are generated once from the array center to each user's body, then expanded to per-element paths by applying transmit steering phases. This is the standard far-field phased array model.

```python
from aegis.mimo import expand_paths_to_array

# center_paths: PropagationPaths from array center to user's body
expanded = expand_paths_to_array(center_paths, array, freq_hz=28e9)
```

For $N$ multipath directions and $M$ antenna elements, the expanded paths object has $N \times M$ entries. Each path carries $\psi_{nj} = \psi_n \cdot \exp(+i k_0 \, \hat{k}_n \cdot \mathbf{p}_j)$, where $\mathbf{p}_j$ is the element offset from the array center. The existing coherent pipeline in `body_channel.py` handles the rest, applying $\exp(-i k_0 \, \hat{k}_n \cdot \mathbf{r}_m)$ per surface point. The two phases combine into the correct plane-wave phase from element $j$ to surface point $\mathbf{r}_m$.

All three channel models work: analytical (LOS), ray tracing (DiffeRT/Sionna), and stochastic (3GPP). The stochastic channel is disabled for multi-user scenarios with $K \ge 2$ because independent per-link generation produces spatially inconsistent large-scale parameters. Ray tracing is the recommended path source for multi-user.

## Precoders

Four multi-user precoders are available. All produce a $(M_{\mathrm{ant}} \times K)$ precoding matrix $\mathbf{W}$.

```python
from aegis.mimo.precoders import mrt, zf, mmse, zf_exposure

H = np.stack([user_a_state.h, user_b_state.h])  # (K, M_ant)

W_mrt  = mrt(H, P=1.0)                          # per-user MRT, equal power
W_zf   = zf(H, P=1.0)                           # zero-forcing
W_mmse = mmse(H, P=1.0, alpha=0.1)              # regularized ZF
W_safe = zf_exposure(H, Q_list, P=1.0,          # ZF directions, exposure-scaled
                     P_abs_max=0.05)
```

MRT maximizes per-user SNR but ignores inter-user interference. ZF nulls interference ($\mathbf{H} \mathbf{W} = \mathbf{I}$ up to scaling) at the cost of higher total transmit power per user. MMSE trades some interference suppression for better noise performance. ZF + exposure scaling starts from ZF directions and scales each column down until the per-body absorption constraint is met.

ZF and MMSE require $M_{\mathrm{ant}} \ge K$. If there are more users than antenna elements, these precoders are infeasible and AEGIS falls back to MRT.

## Running the computation

The `compute_mimo_scene` orchestrator runs the full pipeline: path generation, channel estimation, precoder computation, and per-user dosimetry.

```python
from aegis.mimo.compute import compute_mimo_scene

results = compute_mimo_scene(
    scene=scene,
    engine=engine,
    precoder_type="zf",
)

for user_id, result in results.items():
    print(f"{user_id}: P_abs = {result.p_abs:.4f} W, "
          f"peak Sab = {result.peak_sab:.2f} W/m²")
```

Each user's result is a standard `DosimetryResult` with $S_{\mathrm{ab}}(\mathbf{r})$, $P_{\mathrm{abs}}$, $\mathbf{Q}$, eigenvalues, and $\rho$. The per-user $S_{\mathrm{ab}}$ includes contributions from all $K$ beams, not just the user's own stream.

## Compliance

Compliance checking works per-body. Each body must independently satisfy the ICNIRP limits, accounting for power absorbed from all beams.

```python
for user_id, result in results.items():
    compliance = result.evaluate_compliance()
    print(f"{user_id}: {'pass' if compliance.overall_pass else 'FAIL'}")
```

The per-body constraint is:

$$P_{\mathrm{abs}}^{(u)} = \mathrm{tr}(\mathbf{W}^H \mathbf{Q}_u \mathbf{W}) \le P_{\mathrm{abs}}^{\mathrm{max}}$$

This captures cross-user exposure. A bystander (a body in the scene that is not a served user) can be added to the scene and checked for compliance without receiving a data stream.

## Interactive viewer

The viewer supports multi-user MIMO as a mode toggle. When MIMO is enabled, the single-user controls are replaced by a multi-user interface.

### Enabling MIMO

Set `mimo.enabled` in the viewer config or toggle it in the UI:

```json
{
  "mimo": {
    "enabled": true,
    "array": {
      "type": "upa",
      "n_h": 4,
      "n_v": 4,
      "d_h_wavelengths": 0.5,
      "d_v_wavelengths": 0.5,
      "position": [5.0, 0.0, 3.0],
      "broadside": [-1.0, 0.0, 0.0]
    },
    "precoder": "zf",
    "exposure_budget_mw": 100
  }
}
```

### Adding and positioning users

Click "Add User" and select a phantom (thelonious, duke, eartha, ella). Each user is placed at a default offset from the array and auto-named "User 1", "User 2", etc. Up to 8 users are supported.

WASD keys move the controlled user (highlighted in the 3D scene). Number keys 1-9 switch which user WASD controls. Tab cycles through users. Clicking a body in the scene focuses that user, showing their detailed heatmap and compliance data.

### Heatmap display

Two display modes:

- **Focus mode** shows the full heatmap on the focused user. Other bodies display their last computed heatmap at reduced opacity.
- **All mode** shows heatmaps on every body simultaneously, with a shared color scale (the global maximum across all users sets the legend range).

### Compute behavior

Moving a user shows an incoherent preview (level 2, about 100 ms) during the drag. On release, the full coherent pipeline runs for all users (1-3 seconds depending on user count). Switching the precoder type is fast (about 200 ms) because the exposure operators $\mathbf{Q}_u$ are cached and only the precoder and heatmaps need updating.

Compliance badges in the user list panel update after each computation: green for compliant, yellow within 10% of the limit, red for exceeding.

### Limitations

- The stochastic channel model is disabled for multi-user ($K \ge 2$). Use ray tracing or analytical paths.
- Maximum 8 concurrent users (configurable via `mimo.max_users`).
- ZF and MMSE require at least as many antenna elements as users. When $M_{\mathrm{ant}} < K$, only MRT is available.

## Choosing a precoder

| Precoder | Inter-user interference | Exposure awareness | When to use |
|----------|------------------------|-------------------|-------------|
| MRT | ignored | none | Baseline, quick comparison |
| ZF | nulled | none | Interference-free reference |
| MMSE | suppressed | none | Noisy channels, ill-conditioned H |
| ZF + exposure scaling | nulled | per-body scaling | Exposure-aware without full optimization |

For research on exposure-constrained beamforming, the single-user ECBF solver (level 8) can be extended to multi-constraint problems. See [coherent MIMO](coherent.md) for the single-user formulation.
