# Direction 4: ICNIRP spatial compliance — worst-case 4 cm² hotspot

## The gap

The exposure operator `Q` (monograph Part III, Def. 5.1) integrates `G̃(r)^H G̃(r)` over the entire body surface `Σ`, yielding total absorbed power as a quadratic form `P_abs = x^H Q x`. This is a body-global quantity.

ICNIRP 2020 (6–300 GHz) does not restrict total absorbed power. It restricts **absorbed power density spatially averaged over any 4 cm² patch**:

```
APD_avg(r₀) = (1/A) ∫_{patch A centered at r₀} S_ab(r) dA  ≤  20 W/m²
```

for all `r₀ ∈ Σ` simultaneously (public exposure; A = 4 cm²).

## The local exposure operator

Define the **local exposure operator** for patch center `r₀` and area `A`:

```
Q_local(r₀, A) = (1/A) ∫_{|r - r₀| < √(A/π)} G̃(r)^H G̃(r) dA  ∈ ℂ^{M×M}
```

Then `APD_avg(r₀) = x^H Q_local(r₀, A) x`.

ICNIRP compliance requires:

```
max_{r₀ ∈ Σ}  x^H Q_local(r₀, A) x  ≤  20 W/m²  ∀ x with ‖x‖² ≤ P
```

The **worst-case patch** — the location that produces the tightest constraint on the precoder — is the one that maximises `λ_max(Q_local(r₀, A))` over `r₀`. This is where a coherent hotspot could form (monograph Sec. 7 on hotspot formation).

## What is not known

1. How much tighter is the worst-case local constraint than the whole-body `Q`? Formally: what is the ratio `λ_max(Q_local(r₀*, A)) / (λ_max(Q) / |Σ| A)` in realistic scenarios?

2. Does the worst-case patch coincide with the coherent hotspot under MRT, or is it located elsewhere (because the Fresnel filter reshapes which paths dominate after spatial averaging)?

3. The ECBF formulation (monograph Sec. 8) uses `Q` as a single constraint matrix. For ICNIRP compliance, it should be replaced by an infinite family of constraints indexed by `r₀`. Is a finite covering sufficient? What is the minimal set of patch centers needed such that satisfying those constraints implies compliance everywhere?

4. How does patch size `A` interact with the coherence length `δ_coh` (monograph Sec. 7.2)? If `A > δ_coh²`, spatial averaging reduces the effective constraint; if `A < δ_coh²`, the hotspot fits inside the patch and the full peak is seen.

## References in own work

- Exposure operator `Q`: monograph Part III Def. 5.1
- Coherent hotspot formation and coherence length: monograph Sec. 7.1–7.2
- Fresnel filtering effects on hotspot shape: monograph Sec. 7.3
- ECBF formulation using `Q`: monograph Sec. 8
- ICNIRP 2020: Health Phys. 118(5), pp. 483–524

## Status

Unaddressed. No simulation, no derivation. To make progress, implement `Q_local(r₀, A)` in AEGIS (sliding spatial window over the mesh) and compute `λ_max(Q_local)` as a function of `r₀` for a reference scenario.
