# Direction 5: Estimating Q from channel feedback

## The gap

The ECBF precoder (monograph Part III Sec. 8.2) is:

```
x* = √P (λQ + νI)^{-1} h* / ‖(λQ + νI)^{-1} h*‖
```

Both `h` (UE channel vector, `ℂ^M`) and `Q` (exposure operator, `ℂ^{M×M}`) are required at the BS. `h` is estimated via standard uplink pilot sounding. `Q` is not.

`Q` depends on the full path-level information: for each path `n`, the polarisation-amplitude vector `ψ_n ∈ ℂ³` and direction of arrival `k̂_n`, plus the body surface normal and tissue parameters. The UE channel `h` is a scalar projection of this same information (monograph Eq. 4.5–4.6):

```
h_j = Σ_{n: j(n)=j}  C_R(k̂_n)^H ψ_n  ·  exp(-ik₀ k̂_n · r_UE)
```

The antenna pattern `C_R^H` collapses the 3D vector `ψ_n` to a scalar, discarding polarisation and direction structure that `Q` depends on (monograph Sec. 4.3, structural comparison table after Eq. 4.14). So `Q` cannot be recovered from `h` alone by algebraic inversion.

## What would need to be true for recovery

Three possible routes exist, each with open questions.

**Route A — ray tracing.** If the BS knows the scene geometry, site-specific ray tracing (DiffeRT) provides `{ψ_n, k̂_n}` directly, from which `Q` is computed analytically. This is the AEGIS pipeline. The question is: how sensitive is `Q` to scene geometry errors (moved furniture, people)? Does a stale `Q` from a prior ray-trace cause compliance violations, or just suboptimal precoding?

**Route B — body-mounted pilots.** If the UE transmits pilots on multiple antennas with known polarisation, the BS can reconstruct a coarser version of the multipath structure. Combined with a body model (position + orientation from the UE's IMU), an approximate `Q` could be assembled. This requires more than standard channel sounding.

**Route C — direct Q measurement.** `Q` is an `M×M` Hermitian PSD matrix. Its leading eigenvalue `λ_max(Q)` bounds absorbed power for any precoder: `P_abs ≤ λ_max(Q) · P` (monograph Sec. 5, below Def. 5.1, and Remark on phantom calibration in Sec. 9.3). Measuring `Q` via a calibrated body phantom (as Hochwald et al. do for their SAR matrix `S_V`) avoids the need to know the paths. The open question is update rate: `Q` changes as the user moves, so phantom-based calibration is a one-time measurement, not a live estimate.

## What is not known

1. Under route A: what is the tolerable staleness of `Q`? If body orientation changes by angle `θ`, how much does `λ_max(Q)` shift? Is the error in `P_abs` bounded by something proportional to `θ`?

2. Is there an `h`-observable lower bound on `ρ = h^T Q h* / (‖h‖² λ_max(Q))` — i.e., can the BS decide "ECBF is not needed here" from the channel alone, without knowing `Q`? This would require showing that certain channel configurations imply small ρ unconditionally.

3. How does `Q` update rate compare to the channel coherence time `T_c`? If `Q` changes on the body-rotation timescale (seconds), and `h` changes on the coherence timescale (milliseconds), a decoupled estimation architecture might work: estimate `h` per slot, estimate `Q` per body-rotation interval.

## References in own work

- `Q` definition and analytic derivation: monograph Part III Def. 5.1
- UE channel `h` and structural distinction from `Q`: monograph Sec. 4.3
- Exposure-signal alignment `ρ`: monograph Def. 6.1
- ECBF precoder: monograph Sec. 8.2 Eq. (8.3)
- Phantom calibration remark: monograph Sec. 9.3 (last remark)
- Hochwald SAR matrix: cited in monograph Sec. 5 discussion after Def. 5.1

## Status

Unaddressed. No analysis exists of Q estimation error or its effect on precoder performance. Route A (ray tracing) is already implemented in AEGIS; the staleness question is the most tractable starting point.
