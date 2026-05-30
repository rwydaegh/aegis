# JSAC paper + code audit

19 issues in the LaTeX, 17 in the experimental code (some overlap). Several are blockers.

The most consequential single issue is **C1: solver formula mismatch** — the paper describes a WMMSE-ECBF derivation, but the production code runs a strictly simpler MMSE-with-exposure solver. Step-by-step explanation in the dedicated section at the bottom of this file.

---

## Theory issues (paper_jsac.tex)

| # | Severity | Where | Issue |
|---|----------|-------|-------|
| T1 | nit | line 868 | `\cref{tab:slack}` is a dangling reference; no such table exists. |
| T2 | serious | lines 838, 895, 920, 1216 | `\cref{sec:multibody-ecbf}` is a dangling reference (×4). The `app:ecbf` appendix that should be the target does not contain the `max_outer=8`, GPU-vmap, or low-rank Cholesky details these refs claim are there. |
| T3 | blocker | lines 339–348 | "tr(Q^(u)) equals the expected absorbed power under isotropic random precoding" is missing a `1/M` factor. With `E[xx^H] = (P_tx/M) I`, the correct identity is `E[x^H Q x] = (P_tx/M) tr(Q)`. Off by a factor of M=64. |
| T4 | blocker | lines 663–698 | Binding-distance arithmetic: paper says `P_tx = 30 dBm = 1 W` and `r* = √(P_tx/(π S_lim K))`, giving 0.75 m at K=1. Table claims 13.4 m. Table values reproduce only at `P_tx ≈ 316 W` (peak EIRP under directional MRT). Body text framing ("isotropic") contradicts the table. |
| T5 | blocker | lines 1334–1350 (App. C, proof of Theorem 1) | The Cauchy-bound proof does not establish the stated inequality. Pointwise `D ≤ D_max` and the projected-area integral identity are two different bounding strategies that don't compose to give the `T_0 A_ab/4 D_max sup\|a^H x\|²` form. The factor `T_0` never appears in the proof's opening identity. |
| T6 | serious | lines 1335–1338 (App. C) | The angular-spectrum decomposition `x^H Q x = ∫_{S²} D(k̂) \|α_BS^H x\|² dΩ` is asserted by name; reduction from the surface integral in eq:Q-def to a sphere integral requires unstated convexity, an explicit definition of `α_BS(k̂)`, and absorption of the `\|μ_n\|` projection factor. |
| T7 | serious | lines 133, 230, 740–741 | "Three orders of magnitude" / "four orders" / max value `1.7×10⁻³` are inconsistent. `1.7×10⁻³` = 2.77 orders, not four. |
| T8 | blocker | lines 133–134, 784–786, 791–792 | Chronic-dose ratios disagree: abstract = (B 0.40, C 0.92, 20 s window); body 5-min trace = (B 0.67, C 0.72); ablation 20 s static = (B ≈ 0.33). Three numbers, three windows, no consistent triple. |
| T9 | blocker | lines 123, 707–710, 1213–1214 | Operator-rank claim conflict: abstract "3 to 4 at 99%"; body "3/1 specular/UMa at 90%, 4/3 at 99%"; conclusion "exactly 3 to numerical precision, Frobenius residual 5×10⁻¹³ at r=3". Last claim is much stronger than the body data supports. |
| T10 | serious | lines 481–491 | Soft-budget DoF reasoning conflates `Σ rank(Q^(u)) ≤ 4(K+B) = 200` (sum of body ranks) with array dimension. `Q_tot` is M×M so rank ≤ M = 64 regardless of body count. The "200 effective directions well above 64" framing reverses the actual bound. |
| T11 | serious | lines 651–654 | Exposure-budget formula `L^(u) ≈ T_0 S_lim A_ab η̄` lacks the `/4` from the Cauchy direction-averaged identity. With η̄ = 0.5 the numerical answer is 2× the standard Cauchy value. Either redefine η̄ to absorb `/4` or restore the factor. |
| T12 | serious | line 288 vs 1276–1292 | Channel-conjugation convention inconsistent. Line 288 has `y(x) = h^T x` (no conjugate). Wirtinger differentiation of the WMMSE MSE then gives a drive `g_k = u_k v_k h_k^*` (with conjugate). Paper writes `g_k = u_k v_k h_k`. Either change line 288 to `y(x) = h^H x` or carry conjugates through the Lagrangian. |
| T13 | nit | lines 415–419 | `H_intf` runs over all `k'` including `k'=k`. This is correct (the self term comes from the `(1-...)²` MSE expansion), but presenting it as "inter-user interference Gram" is misleading — it's the WMMSE Hessian. One-line clarification needed. |
| T14 | serious | lines 305–307, App. A | "≤ 4% cross-term error at 26 GHz on skin" + "≤ 5% combined for any precoder" are asserted, not derived. With ñ = 4.47 - 1.85i at 26 GHz, `1/\|ñ\|² = 4.27%`, slightly above the stated 4%. The 5% combined bound for arbitrary precoders has no derivation. |
| T15 | serious | lines 622–623 | Pose-driven cadence table: 100 ms cadence + 50 bodies × 7.5 ms/body = 375 ms sequential. The 100 ms cadence and the 7.5 ms-per-body cost cannot both hold without a batched-GPU note. |
| T16 | nit | lines 291, 300, 514, 1260 | `α_n` overloaded: line 291 = per-path antenna projection scalar, line 300 onward = depth-decay imaginary part. Superscript `^(d)` distinguishes them but the convention is fragile. |
| T17 | nit | eq:psitil | Implicit normalisation of `ψ_n` not stated. For `Sab` to come out in W/m² while `\|x\|² ≤ P_tx` (W), `ψ_n` must carry units √(Z_0)/m ≈ V/(m·√W). Paper does not pin this. |
| T18 | nit | line 437 | "10 to 30 outer iterations vs 800 to 1,600 Gauss-Seidel sweeps" asserted with no figure, citation, or method. See C2 — there is no Gauss-Seidel baseline in the repo. |
| T19 | nit | line 838 vs §IV.D headline | M=256 ZF gives 18.7% violation; §IV.D headline is "all five precoders collapse to one operating point with no body-slot crossing the cap". The slack/binding regime distinction needs to be marked through the section so this isn't read as a contradiction. |

---

## Code issues (JSAC/code/experiments + src/aegis/coherent)

| # | Severity | Where | Issue |
|---|----------|-------|-------|
| C1 | blocker | `src/aegis/coherent/multibody_ecbf.py:188-194,532` and `multibody_ecbf_jax.py:189-194` | **Solver formula mismatch.** Code computes regularised MMSE with exposure caps. Paper claims WMMSE-ECBF. Detailed step-by-step below. |
| C2 | blocker | App. B vs codebase | Newton vs Gauss-Seidel benchmark is fictitious. No GS implementation in the repo, no logged comparison run produces "800 to 1,600 sweeps". |
| C3 | blocker | `rank_check/spectra.npz` vs paper line 1213 | "Frobenius residual 5×10⁻¹³ at r=3" is fabricated. Actual median residuals from the npz: 1.6×10⁻² (specular) / 9.6×10⁻⁴ (stochastic). Off by 10+ orders of magnitude. Data is in `complex64`, so float32 ulp ~10⁻⁷ precludes the claim by data type alone. |
| C4 | serious | `plaza_run/budgets.py` (T_0 = 0.4); §V text (implicit T_0 ≈ 0.466); `cauchy_tightness/summary.json` (T_0 = 0.530) | Three different T_0 values for skin@26 GHz across the codebase, three different `L_RL` values fall out (163 mW, 190 mW, ~225 mW). Pick one. |
| C5 | serious | rank_check vs paper §IV.B | Two different rank definitions used. Code: `#{k : λ_k/λ_1 ≥ ε}` (ratio). Paper: `min r : Σ_{k>r} λ_k ≤ ε·tr(Q)` (trace fraction). On the same data, ε=0.1 specular gives median 3 (code) vs 2 (paper definition). |
| C6 | serious | `plaza_run/paths.py:46` vs `rank_check/run_rank_check.py:177` vs paper §IV | UMa-LOS path counts disagree: rank_check uses 12×5 = 60 paths per body; plaza_run uses 4×2 = **8** paths per body for production figures. Paper says "60 subpaths per cluster". The hero figure was run on 8 paths. |
| C7 | serious | `slot_loop.py:445,475` and `figures/RESULTS.md:142,154` | `max_outer = 8` in production. Binding regime hits a min-absorption fallback on **83.6 %** of slots (proposed) and 26.3 % (oracle). Not disclosed in paper text. App. B's "machine-precision residual in 10 to 30 iterations" is incompatible with `max_outer = 8`. |
| C8 | serious | `JSAC/code/prompts/08_plaza_run_assembly_report.md:135` vs paper "31 ms median solve" | The 31 ms number is from an intermediate 600-slot run that was superseded. Slack 5-min `viz5min` plaza_run logs precoder p50 = **24.5 ms**; binding 5-min `v6_aware` = 388 ms. |
| C9 | serious | `RESULTS.md:115-118` vs abstract chronic-dose | Abstract uses superseded 600-slot static-position run (B 0.40, C 0.92). Production 5-min realistic-walk dataset has B 0.67, C 0.72. Documented supersession but not propagated to the abstract. |
| C10 | nit | `cauchy_tightness/run_tightness.py:104` | Path-budget override comment claims "match rank_check (12×5 = 60 paths)" — matches rank_check, not plaza_run. The Cauchy-tightness experiment runs the rank-test ensemble, not the plaza_run ensemble. |
| C11 | nit | `profile_q.npz` data type | Stored as `complex64`. Any sub-1e-7 precision claim about this data is precluded by float32 ulp. |
| C12 | nit | `figures/RESULTS.md:97-98` | Stale ZF spatial-mean numbers (median 0.50, p95 1.25) from the legacy run still present in `RESULTS.md`. Paper §IV.E uses the v6_aware numbers (0.064/0.201/0.400/3.375), which is correct, but a re-reader of `RESULTS.md` would be misled. |

Verified consistent (no issue):
- Cauchy tightness numbers (§IV.G/App. C): `summary.json` matches paper exactly (-21.4 / -27.1 dB LOS slack, 49–70% violation, +2.86 / +6.34 dB medians).
- 7.5 ms per-body Q refresh: matches `gpu_benchmark/timings_decim10.json`.
- CSI calibration: real 200-trial sweep, paper §IV.F numbers match `residual_table.md`.

---

# C1 explained step by step: the solver-formula mismatch

This is the single most consequential finding. The paper's central algorithmic contribution describes a derivation that the production code does not implement.

## Step 1: what the paper claims

App. B (`paper_jsac.tex:1255`–1297) sets up a **WMMSE surrogate** for sum-rate maximisation, following Christensen 2008 / Shi 2011:

```
R_sum  ≈  R̃({w_k})  =  Σ_k [log u_k - u_k · e_k(w_k) + const]
```

with per-user MSE

```
e_k(w_k)  =  |1 - v_k* h_k^T w_k|²  +  |v_k|² σ²_n  +  |v_k|² Σ_{k'≠k} |h_k^T w_{k'}|²
```

and three blocks of variables: precoders `{w_k}`, MMSE rate weights `{u_k}` (one scalar per stream), MMSE receive filters `{v_k}` (also scalars per stream).

The WMMSE algorithm is an outer block-coordinate descent:

| Block | Update |
|-------|--------|
| `v_k` | MMSE receive filter at fixed `{w_k}`: `v_k = h_k^T w_k / (Σ_{k'} \|h_k^T w_{k'}\|² + σ²_n)` |
| `u_k` | Rate weight at fixed `{w_k, v_k}`: `u_k = 1 / e_k` |
| `w_k` | KKT stationarity at fixed `{u_k, v_k}` plus Lagrange duals |

The KKT stationarity for `w_k` (the equation we just fixed in the paper) is

```
(Q_tot(λ) + H_intf + νI) w_k  =  u_k v_k h_k
```

with the **WMMSE Hessian**

```
H_intf  =  Σ_{k'} u_{k'} |v_{k'}|² h_{k'} h_{k'}^H.
```

Crucially, `u_{k'}` and `|v_{k'}|²` are stream-specific weights computed from the current iterate. They are **not constant**, and they are **not 1**.

## Step 2: what the code computes

`src/aegis/coherent/multibody_ecbf.py:188-194` (the CPU canonical solver, which the JAX version mirrors):

```python
M_lam = lambda_diag @ Q_stack  # Σ_u λ_u Q^(u)
if noise_power is not None and noise_power > 0:
    M_lam = M_lam + H.conj().T @ H + noise_power * np.eye(M)
else:
    M_lam = M_lam + np.eye(M)
W = np.linalg.solve(M_lam, H.conj().T)  # column k is w_k
```

In equation form, with noise present,

```
w_k  =  (H^H H + νI + Q_tot(λ))^{-1}  h_k^*
```

Two structural differences from the WMMSE form:

1. **No `(u_k, v_k)` block** — the precoder is computed once, not iterated against rate weights and MMSE filters. There is no inner WMMSE loop in the codebase.
2. **`H^H H` instead of `H_intf`** — the matrix `H^H H = Σ_{k'} h_{k'} h_{k'}^H` is `H_intf` only if every `u_{k'} |v_{k'}|² = 1`, i.e. the unweighted MMSE limit.

This is a **regularised MMSE precoder with exposure caps**, which is a multi-user / multi-body extension of Ying-2015 (single-user) and Joham 2002 / Peel-Hochwald 2005 (multi-user MMSE without exposure). It is **not** the WMMSE-ECBF the paper derives.

## Step 3: where the difference shows up numerically

Sum-rate gap. WMMSE rate-weighting is what closes the gap to the sum-rate optimum in interference-limited regimes. The empirical WMMSE-vs-MMSE gap in mmWave multi-user is typically 10–30 % in spectral efficiency at moderate SNR with `K ≥ 4`. The paper reports plaza-scale rates from the simpler MMSE form but attributes them to the WMMSE-ECBF derivation. A reviewer who re-implements the paper's stated math gets different numbers.

Convergence machinery. App. B describes an outer Newton ascent on the dual `(λ, ν)` driven by the WMMSE inner loop's residuals. The code's outer loop in `slot_loop.py` is a Newton ascent on `(λ, ν)` driven by the MMSE solve. Without the WMMSE inner loop, the "10 to 30 outer iterations to machine precision" framing is at the wrong abstraction level — those iteration counts pertain to a procedure (WMMSE block-coordinate) that isn't being run. (Compare with C7: production caps `max_outer = 8` and falls back on 83.6 % of binding-regime slots; the gap between paper and code on this is wide.)

Theoretical claims. Prop. 1 (rank-one ZF limit) holds for both formulations — `(H^H H + νI)^{-1} h_k^*` reduces to regularised ZF directly, and `(H_intf + νI)^{-1} g_k` does likewise. So the proposition itself is salvageable under either reading. But the citation chain (Christensen 2008 → Shi 2011) supports only the WMMSE reading.

## Step 4: consequences

1. **Reviewer-side:** any JSAC reviewer who implements the paper's derivation will get systematically lower SE numbers than the paper claims, by the WMMSE-vs-MMSE gap. The paper's empirical evaluation is reproducible only against the actual code, not against the paper's stated math.
2. **Theoretical contribution:** the paper currently positions its closed-form result as a generalisation of the *WMMSE-driven* SAR-precoder line (Hochwald, Ying). Properly described, the result is a generalisation of the *MMSE-driven* line — still a real contribution (Ying-2015 with multi-body exposure under MMSE), but smaller scope than the paper claims.
3. **Convergence claims void.** App. B's iteration counts and dual-ascent description don't apply to the simpler MMSE solver; the corresponding correct claims are about Newton ascent on the dual variables only.
4. **Existing prose now points two ways.** My earlier `\Hintf` "fix" to §III.A and App. B made the LaTeX self-consistent under the WMMSE reading. But that reading does not match the code. So either (a) roll back the `\Hintf` fix and rewrite §III.A / App. B as the MMSE-with-exposure derivation matching the code, or (b) implement the WMMSE inner loop in code, re-time everything, and update the empirical numbers.

## Step 5: the two reconciliation paths

**Path A — match paper to code (1–2 hours of LaTeX work).**

- Roll back `\Hintf` in §III.A and the abstract / intro / conclusion summaries.
- Rewrite App. B's Lagrangian: drop the WMMSE auxiliary block, replace `R̃` with the MMSE objective `Σ_k E[|s_k - v_k* h_k^T x_total|²]`, derive the same form `(H^H H + νI + Q_tot) w_k = h_k^*` from MMSE stationarity. Cite Joham 2002 + Ying 2015 + Peel-Hochwald 2005 as the precedent line, drop Christensen 2008 / Shi 2011.
- Update §III.A's framing from "WMMSE surrogate of sum-rate" to "regularised MMSE precoder with per-body exposure caps".
- Adjust `g_k` notation: it's just `h_k^*`, not `u_k v_k h_k`.
- Reposition contribution: "we generalise the multi-user regularised MMSE precoder (Joham/Peel-Hochwald) to a heterogeneous body population under per-body absorbed-power caps". This is the honest framing of what the experiments validate.

**Path B — match code to paper (1–2 days of code work + reruns).**

- Implement the WMMSE outer loop in `multibody_ecbf.py`: nested updates for `(u_k, v_k)`, then the existing dual ascent on `(λ, ν)` for the inner `w_k` solve.
- Validate against a known WMMSE benchmark.
- Re-run all `plaza_run` experiments. Re-time. Update §III.A timing numbers (which will likely increase by the WMMSE outer factor — typically 5–15 outer iterations).
- Re-generate hero / chronic / spatial figures.
- Confirm the empirical claims (rank, violation rates, dose ratios) are stable under the new solver.

**My recommendation: Path A.** Faster, honest, the existing experimental story stays intact. The claimed contribution shrinks slightly (from "WMMSE-ECBF" to "MMSE-ECBF") but the value of the per-body-cap formulation, the operator-rank result, and the plaza-scale evaluation are all unaffected. Path B is the right move only if the WMMSE-vs-MMSE rate gap matters for a downstream claim that the paper actually makes — and the current paper does not explicitly compare WMMSE vs MMSE rates anywhere, so it doesn't.

---

# Round 2 audit (2026-05-09): paper vs code drift across iterations

## Why this round was run

Robin reported that `paper_jsac.tex` was written across multiple sessions — at one point loose, then tightened by switching to a stricter Brussels limit (the strictest historical) and a max-realistic base-station output (40+ dBm), with an antenna-size change he half-remembered ("8×8 to more"). He suspected the .tex still carries fossils from prior iterations and asked for a full audit against the actual code and results in `JSAC/code/prompts` and `JSAC/code/experiments`.

## Ground truth anchored against

- `JSAC/code/experiments/plaza_run/figures/RESULTS.md` (canonical, 2026-05-05, post pol-fix and 5-min steady-state regen)
- `JSAC/code/experiments/plaza_run/configs/{brussels_2024_slack,brussels_2007_strict,binding_43dbm_6vpm,mmwave_aggressive_2007}.json`
- `JSAC/code/experiments/plaza_run/{run.py,scenario.py,budgets.py,phy.py}`
- `JSAC/code/prompts/{08_plaza_run_assembly_report.md,09_paper_figures_report.md,03_DONE.md}`

**Memory-vs-reality check on Robin's recollection:** the canonical configs settled at 8×8 + 43 dBm + 6 V/m (post-2014 Brussels / Italy attention level), `binding_43dbm_6vpm.json`. The 16×16 variant (`mmwave_aggressive_2007.json`, 43 dBm + 3 V/m) and the 30 dBm + 3 V/m variant (`brussels_2007_strict.json`) exist in the configs directory but are **not** what produced the final figures. The "switched 8×8 to more" recollection is a memory artefact; the panel never moved past 8×8 in the canonical run.

## New / sharper findings (not already covered above)

Numbering continues from the existing T-/C- series. Items marked `(reinforces Tn/Cn)` corroborate an existing entry from a different angle; `(new)` are not in the round-1 audit.

| # | Severity | Where | Issue |
|---|----------|-------|-------|
| R1 | blocker | `paper_jsac.tex:656-657` | (new) §VII.A intro: *"window is $20\,$s of wall-clock-equivalent simulation, $600$ slots at $33\,$ms slot spacing"*. Canonical run is **9000 slots = 5 min**. All current figures derive from the 5-min trace. |
| R2 | serious | `paper_jsac.tex:735` | (new) §VII.B body still reads "20 s window" while the same section's caption (line 757-758) correctly cites *"450,000 body-slots (50 bodies × 9000 slots, 5 min)"*. Self-contradictory. |
| R3 | serious | `paper_jsac.tex:1168-1170` | (new) Discussion: *"the 20 s window is a single seed and a fraction of the 5 min walk-cycle the chronic-dose argument calls for"*. The 5 min run is exactly what was done; this is no longer a real limitation. |
| R4 | serious | `paper_jsac.tex:744-748` vs `757-767` | (new) §VII.B body says *"Mean sum-rate likewise collapses across precoders, with one exception: ZF in UMa-LOS"* — but the same-section caption (and RESULTS.md headline) shows ZF dominates **plaza-specular at 44 Gbps**, 4× MRT. Body needs the rate-side ZF separation acknowledged. |
| R5 | serious | `paper_jsac.tex:638-639` | (new) §VII.A geometry: *"facade at $8\,$m height with $10^\circ$ downtilt"*. `scenario.py` uses `BS_Z_M = 12.0`, `BS_DOWNTILT_DEG = 5.0`; v6_aware NPZ confirms `bs_position = [0, -40, 12]` and broadside vector matches 5° downtilt. The 8 m / 10° numbers are the **rank_check** experiment's geometry; §VII.A is conflating the two scenarios. |
| R6 | serious | `paper_jsac.tex:643-645` | (new) Skin tissue stated as *"$\varepsilon_r = 16.55$, $\sigma = 25.8$ S/m, $\tilde n = 4.47 - 1.85i$ from IT'IS v5.0"*. `aegis.tissue.TissueModel.from_database("Skin", 26e9)` returns **$\varepsilon_r = 17.71$, $\sigma = 24.41$ S/m, $\tilde n = 4.59 - 1.84i$**. Looks like an older IT'IS revision baked into the prose. |
| R7 | serious | `paper_jsac.tex:951-952` | (new) ISAC link budget: *"$P_d = 0.99$ contour reaches 137 m"*. `tier_c_decision/decision.md` says *"the most stringent CPI choice only crosses $P_d = 0.9$ around 137 m"*. Should be 0.9, not 0.99. |
| R8 | serious | `paper_jsac.tex:651-654` | (new, refines T11) Per-body L_RL stated as *"$\approx 0.19\,$W per body for an adult of $A_{\mathrm{ab}} \approx 1.45$ m² at $\bar\eta = 0.5$"*. With $T_0=0.4$, $S_{\mathrm{lim}} = 14.57^2/376.73 = 0.564$ W/m², stated $A_{\mathrm{ab}}$ and $\bar\eta$: arithmetic gives **0.16 W = 163 mW**, not 0.19 W. Verified against `body_budgets_w` in slack viz5min NPZ (≈0.163 W). The 0.19 W figure implies $A_{\mathrm{ab}} \approx 1.7$ m² (older value). Independent of C4's `T_0` ambiguity — even at the paper's own stated `T_0 = 0.4`, the answer is 0.16 W. |
| R9 | serious | `paper_jsac.tex:649, 723-724` | (new, refines C6) Phrasing *"60 subpaths per cluster"* is wrong: each cluster has 5 subpaths, and 12 clusters × 5 subpaths = **~60 subpaths total** (`rank_check/README.md`). |
| R10 | blocker | abstract, §VII.C/D vs RESULTS.md | (new framing of an existing tension) **Two co-existing binding regimes in the repo.** Paper §VII.C-D matches `v6` NPZ (43 dBm + 6 V/m + L_RL = 27.7 mW): ZF viol 0.10%, ECBF infeas 83.6%, ablate infeas 55.1%, ECBF SR 2546 Mbps, oracle SR 11787 Mbps. RESULTS.md headline tables and Robin's "established facts" cite `bind5min` (×0.1 multiplier + L_RL = 16.3 mW): ZF viol 16.7%, ECBF infeas 96.6%, ablate infeas 88.0%, ECBF SR 882 Mbps, oracle SR 1705 Mbps. **The figure scripts default to v6 unless `AEGIS_BIND_KEY=specular_bind` is exported.** Either RESULTS.md needs to be regenerated from v6 (paper stays as written), or §VII.C-D needs to be rewritten to bind5min numbers. This is the load-bearing decision blocking other edits. |
| R11 | nit | `paper_jsac.tex:1087-1090` | (new) Italian attention-level claim *"$6\,$V/m on $24\,$h median outside dense urban centres and $15\,$V/m within them under the 2024 decree"* reads inverted vs `run.py:80-82` CLI help (*"6 = post-2014 Brussels / Italy attention (large urban); 3 = pre-2014 / small urban"*). DL 199/2024 partition needs domain check. |
| R12 | nit | `paper_jsac.tex:838` vs `paper_jsac.tex:613` | (new) §VII.C cites RTX 4090 wall-clock (1.1 s at M=256) while `tab:cadence` caption cites RTX 3090. Both real (brief 08 ran on 4090, gpu_benchmark on 3090) but the two hardware references want a one-sentence reconciliation. |
| R13 | nit | `paper_jsac.tex:920` plus ~8 other sites | (new) Style violations vs `CLAUDE.md` ("no em dashes, no semicolons"): em dashes on line 920, ~8 semicolons in body text. |
| R14 | — | abstract chronic-dose ratios | (reinforces T8) Specifically: line 134 says "20 s walk-cycle window" — replace "20 s" with "5 min" alongside the (B 0.40 / C 0.92) → (B 0.72 / C 0.67) update T8 already calls out. |
| R15 | — | "31 ms median solve" repeated 6× | (reinforces C8) Line numbers: 126, 229, 605, 621, 1174, 1305. The fix is regime-split: ~24 ms slack / ~116 ms binding per `tab:cadence` in RESULTS.md. |
| R16 | — | §III "10-30 outer iters" vs §VII.D "max_outer = 8" | (reinforces C7/T18) §III claim describes the unconstrained algorithm; §VII.D / Discussion claim describes the production cap. §III needs one sentence acknowledging the 8-cap is a production wall-clock bound, not the algorithmic convergence rate. |

## Things that look right (round 2 spot-check)

§II coherent absorption + cross-term bounds, §IV scene/path-dictionary + tier-C section, §VII.D ISAC link-budget headline numbers (14.3 dB single-pulse, 42.1 dB integrated, 12.69° HPBW, 11.07 m crossrange, 4.15 m² cell, 0.375 m range res, 400 MHz BW — all match `decision.md` except the Pd value flagged in R7), §VII.E CSI calibration plot description (uncorroborated against `csi_calibration/` in this round but not contradicted), §VII.F Cauchy-bound tightness numbers, §IX regulatory framing, §XI structure. Nothing in §I-§II changed since round 1.

## Recommended order of attack (combined with round 1)

1. **Decide v6 vs bind5min (R10).** Half the binding-regime numerical edits hang on this. Either regenerate RESULTS.md tables from v6, or override `AEGIS_BIND_KEY=specular_bind`, regenerate figures from bind5min, and rewrite §VII.C-D numerics.
2. **One coordinated 20-s → 5-min sweep (R1, R2, R3, R14).** Six sites: abstract chronic-dose ratios + window length, §VII.A intro, §VII.B body, Discussion limitations.
3. **Replace "31 ms" globally with regime-split 24 / 116 ms (R15).** Six sites.
4. **Fix the dangling cleveref labels (T1, T2).**
5. **Mechanical numeric corrections (R5, R6, R7, R8, R9, plus T7).** All small, all reviewer-visible.
6. **Reconcile §III iteration claim with §VII.D 8-cap (R16).** One added sentence in §III.
7. **Solver-formula mismatch (C1).** Path A or Path B per the round-1 recommendation. Independent of everything above.
8. **Style pass (R13).** Em dashes, semicolons.
