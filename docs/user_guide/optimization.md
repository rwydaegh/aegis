# Differentiable optimization

AEGIS kernels run on JAX. Every level except 1 and 8 supports `jax.grad`, so you can compute gradients of exposure metrics with respect to antenna parameters, path powers, or precoding vectors.

## The gradient boundary

`DosimetryEngine.compute()` converts JAX arrays to NumPy before returning a `DosimetryResult`. This breaks the gradient chain. Use `compute_sab()` instead when you need gradients:

```python
import jax
import jax.numpy as jnp
from aegis import DosimetryEngine, TissueModel

tissue = TissueModel.from_params("Skin", 17.0, 25.0, 28.0e9)
engine = DosimetryEngine(tissue)

def loss(power):
    sab = engine.compute_sab(body, paths, level=2)
    return jnp.max(sab)

grad = jax.grad(loss)(power)
```

`compute_sab()` returns the raw per-triangle $S_{\mathrm{ab}}$ array without conversion. It accepts the same parameters as `compute()`, plus `precoder_x` for passing a raw JAX array instead of a `Precoder` object.

## Which levels are differentiable

| Level | `jax.grad` w.r.t. power | `jax.grad` w.r.t. precoder $\mathbf{x}$ |
|-------|------------------------|-----------------------------------------|
| 0     | Yes                    | n/a                                     |
| 1     | No (scipy SH)          | n/a                                     |
| 2-6   | Yes                    | n/a                                     |
| 7     | n/a                    | Yes                                     |
| 8     | n/a                    | No (bisection solver)                   |

Level 1 uses `scipy.special` for spherical harmonics, which JAX cannot trace. Level 8's ECBF solver uses a Python bisection loop. The forward evaluation works fine for both, but `jax.grad` does not flow through them.

## Loss functions

The `aegis.optim` module provides common loss functions that work inside `jax.grad`:

```python
from aegis.optim import peak_exposure, total_absorbed_power, soft_peak_exposure

sab = engine.compute_sab(body, paths, level=3)

# Hard max (subgradient, works for gradient descent)
loss = peak_exposure(sab)

# Surface integral (fully smooth)
loss = total_absorbed_power(sab, body.areas)

# Smooth approximation to max via log-sum-exp
# Higher temperature = tighter bound but sharper gradients
loss = soft_peak_exposure(sab, temperature=100.0)
```

`peak_exposure` uses `jnp.max`, which has a well-defined subgradient in JAX. If you need a smooth loss for second-order optimizers, use `soft_peak_exposure`.

## Antenna placement

Gradients flow from exposure through path parameters to antenna position. The full chain is: antenna position, free-space path loss, direction of arrival, dosimetry kernel, loss.

```python
from aegis.kernels.level2_geometric import level2_geometric

normals = jnp.array([[0.0, 0.0, 1.0]])
T0 = tissue.T0

def exposure_at(antenna_pos):
    direction = jnp.array([0.0, 0.0, 0.0]) - antenna_pos
    d = jnp.linalg.norm(direction)
    k_hat = (direction / d)[None, :]
    power = jnp.array([1.0 / (4 * jnp.pi * d**2)])
    sab = level2_geometric(normals, k_hat, power, T0)
    return jnp.sum(sab)

grad = jax.grad(exposure_at)(jnp.array([0.0, 0.0, 2.0]))
```

This calls the kernel directly rather than going through the engine. For simple geometries (LOS, few paths), calling the kernel is the most direct approach. For full scenes with a differentiable ray tracer like DiffeRT, the same principle applies: DiffeRT outputs JAX arrays, and AEGIS kernels consume them.

## Beamforming optimization

For coherent levels, the optimization target is the precoding vector $\mathbf{x}$. The body-surface channel $\tilde{\mathbf{G}}$ is expensive to build but does not depend on $\mathbf{x}$, so you build it once and optimize in the inner loop:

```python
from aegis.coherent.body_channel import compute_body_channel
from aegis.optim import coherent_sab, total_absorbed_power

# Build G_tilde once (expensive)
G_tilde = compute_body_channel(
    body.normals, body.centroids, paths.k_hat, paths.psi,
    paths.element_index, tissue.n_complex, tissue.sigma,
    tissue.freq_hz, paths.n_elements,
)

# Optimize x (cheap per iteration)
def loss(x):
    sab = coherent_sab(G_tilde, x)
    return total_absorbed_power(sab, body.areas)

grad = jax.grad(loss)(x_init)
```

`coherent_sab(G_tilde, x)` computes $\|\tilde{\mathbf{G}} \mathbf{x}\|^2$ per triangle. It is the same computation as Level 7 but extracted for inner-loop use.

!!! note
    Level 8 (ECBF) finds the optimal $\mathbf{x}^*$ analytically via a QCQP solver. The solver uses Python bisection and is not differentiable. If you need gradients of the optimal precoder with respect to system parameters (antenna positions, channel), use Level 7 with your own optimizer instead.

## Spatial averaging stays outside the gradient

ICNIRP 4 cm$^2$ spatial averaging uses `scipy.spatial.cKDTree`, which is not JAX-traceable. This is intentional. Spatial averaging is a post-processing step for compliance reporting, not part of the optimization loss. Optimize raw $S_{\mathrm{ab}}$, then check compliance on the result.
