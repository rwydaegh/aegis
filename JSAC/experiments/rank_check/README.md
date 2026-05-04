# Empirical rank of Q on Thelonious, plaza geometry at 26 GHz

## Takeaway

The paper's "3-10 dominant eigenmodes per body" claim in JSAC §II.7 and
Remark 4.5 **holds, at the low end of the stated range**. Across 20 bodies
spread over a 20-80 m range ring at ±60° azimuth and 26 GHz with an 8×8
half-wavelength UPA, the ε-effective rank of `Q^(u)` at ε = 10^-2 is
**median 3-4, never above 4** for both path models tested. At ε = 10^-3
the dominant rank is still **median 3, max 4**. The rank-few framing
stands; §IV does not need to be restructured.

The two models give consistent answers on the dominant end but differ
below that:

- **Plaza specular** (LOS + ground + 2 facades): hard cliff after k = 4 to
  the double-precision numerical floor (~10^-15). This is the theoretical
  rank ceiling — B bounces produce B BS-side steering vectors in C^64, so
  rank(Q) ≤ B by construction. It confirms the claim but cannot falsify
  it.
- **3GPP 38.901 UMa LOS stochastic** (12 clusters × 5 subpaths = 56
  physical subpaths per body): the spectrum decays smoothly, not
  cliff-like. λ_1 carries >95 % of the Frobenius energy (K-factor from
  the preset is large in LOS). The fall-off is geometry-limited by the
  array aperture: the 8×8 panel has ~14° of angular resolution per axis,
  so the ~50 subpaths collapse into just 3-5 distinguishable BS-side
  directions plus a long sub-dominant tail that reaches the numerical
  floor around k ≈ 30, well above the eps_double ≈ 2×10^-16 cutoff.

The "rank-few" label is therefore an array-resolution observation, not a
physical-multipath claim: even 60 subpaths only excite 3-10 modes that
the 8×8 array can actually resolve.

**Caveat.** Both models assume a LOS-dominant regime. The UMa preset has
a large K-factor; a NLOS preset or a denser scatterer field inside ±60°
could push the rank toward the upper end of the 3-10 range predicted in
the paper. Remark 4.5 already acknowledges this: it says the coherent
operator handles the higher-rank case without forking the solver. The
plaza spec in the prompt fits the LOS-dominant regime, so this
experiment confirms the concrete claim made for that scenario.

## Scenario

- Phantom: **Thelonious** STL (23826 triangles, ~0.79 m² surface area).
  Placed with feet on the ground at each sample position.
- BS: 8×8 UPA, half-wavelength spacing (d ≈ 5.77 mm at 26 GHz), 8 m
  mounting height, 10° down-tilt, broadside toward +x.
- Tissue: skin at 26 GHz (IT'IS Cole-Cole: ε_r ≈ 17.71, σ ≈ 24.4 S/m).
- 20 bodies sampled uniformly in a 20-80 m range ring, azimuth ±60°
  (areal-uniform via sqrt-radius sampling), feet on ground z = 0.
- Two independent path models are evaluated on every body:
  - **A. Plaza specular** — LOS + ground bounce + 2 facade specular
    reflections (image-method at z = 0 and y = ±20 m). 4 paths per body.
  - **B. 3GPP 38.901 UMa-LOS stochastic** — 12 clusters × 5 subpaths drawn
    by `aegis.channel.generator.generate_channel`. 56 physical arrival
    directions per body (LOS path + 11 * 5 subpaths; cluster 0's "LOS
    subpath" pattern yields 56 not 60).

Both models use the same centre-of-array → per-element expansion
(`expand_paths_to_array`) and the same factored body-channel builder
(`compute_body_channel_factored`) so that the element geometry and
Fresnel treatment are identical.

## Results

Spectrum of `Q^(u)` normalised by its top eigenvalue; median is the
blue line, grey traces are the 20 per-body curves, shaded band is the
10-90 percentile range:

![rank_cdf](rank_cdf.png)

### epsilon-effective rank

`epsilon-effective rank = #{k : lambda_k / lambda_1 >= epsilon}`

| model                | ε      | p10 | median | p90 | min | max |
| -------------------- | ------ | --- | ------ | --- | --- | --- |
| specular (4 paths)   | 1e-01  | 2   | 3      | 3   | 2   | 3   |
| specular (4 paths)   | 1e-02  | 3   | 4      | 4   | 3   | 4   |
| specular (4 paths)   | 1e-03  | 4   | 4      | 4   | 4   | 4   |
| stochastic (56 paths)| 1e-01  | 1   | 1      | 1   | 1   | 1   |
| stochastic (56 paths)| 1e-02  | 2   | 3      | 3   | 2   | 3   |
| stochastic (56 paths)| 1e-03  | 3   | 3      | 4   | 3   | 4   |

The stochastic tail continues below ε = 10^-3 with geometrically
decaying ratios, reaching the double-precision numerical floor
(~10^-15 × lambda_1) around k ≈ 30, so modes 5-30 carry exponentially
diminishing but non-zero energy. Whether any of that tail matters
depends on the exposure budget granularity; at the 1 % and 0.1 %
thresholds commonly used for compliance, rank 3-4 covers it.

## How to reproduce

```bash
# From repo root, with aegis installed in the active environment.
python3 JSAC/experiments/rank_check/run_rank_check.py
```

The script dispatches 20 bodies across a `ProcessPoolExecutor`
(`RANK_CHECK_WORKERS` env var, default 4). Runtime ~3 min on 4 cores
for both models combined. Memory per worker is ≤ 1 GB because the
factored body-channel builder avoids the large (M_tri × N_total)
transients that the vectorised builder would need.

## Files

- `run_rank_check.py` — experiment driver
- `spectra.npz` — raw eigenvalue matrices for both models and body positions
- `rank_cdf.{pdf,png}` — two-panel figure above
- `rank_table.md` — table of ε-effective ranks
