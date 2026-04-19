# Metamorphic testing analysis (2026-04-18)

Wave 5, Agent L. Scope: identify metamorphic relations ("if input X transforms by T, output Y transforms by T'") that hold rigorously per the AEGIS monograph, and implement only the ones that survive mathematical validation. Cite every relation; do not invent.

Reference: `theory/monograph_v2.tex` (monograph v2, 5993 lines) and `theory/summary_paper.tex`.

## Method

1. Read the monograph end-to-end with the lens: "what transformations of input produce predictable transformations of output?"
2. For each candidate, write: relation, monograph reference, preconditions, known exceptions, whether the current engine can exercise it.
3. Mathematically validate each one.
4. Implement only those that survive validation, with tolerances reflecting numerical precision (no fudge-factor tolerances).

## Candidates considered (15)

### Implemented (6)

**A. Coherent quadratic scaling in precoder**
- Relation: for any complex alpha, `Sab(r; alpha*x) = |alpha|^2 * Sab(r; x)`.
- Monograph: Thm 4.1 (thm:coherent-law), Eq. 4.9. `Sab(r) = ||G_tilde(r) x||^2` is a pure quadratic form.
- Precondition: any x, alpha in C.
- Exception: none. This is algebraic from the norm-squared form.
- Tolerance: FP double precision, around 1e-12 relative.
- Status: IMPLEMENTED. test_metamorphic_coherent_scaling.

**B. Coherent global-phase invariance**
- Relation: for any real phi, `Sab(r; e^{i*phi}*x) = Sab(r; x)`.
- Monograph: same as A. Follows from `|e^{i*phi}*y|^2 = |y|^2`.
- Precondition: any x, phi real.
- Exception: none.
- Tolerance: FP double precision.
- Status: IMPLEMENTED. test_metamorphic_coherent_global_phase.

**C. Simultaneous rotation of (normals, k_hat) for incoherent levels**
- Relation: for any R in SO(3), rotating both the mesh normals and all k_hat vectors by R leaves per-triangle sab unchanged at Levels 2, 3, and 4 (with q=0).
- Monograph: Section 2.1 (sec:local-law), Eq. 2.5: `Sab = S_inc * Teff(mu) * ReLU(mu)`. The only geometric quantity appearing is `mu = n_hat . (-k_hat)`, which is invariant under simultaneous rotation of n_hat and k_hat.
- Precondition: q=0 (Level 4). For q != 0, Level 4 brings in the polarisation ellipse orientation alpha(r), which is not rotation-invariant without also rotating the global polarisation reference.
- Exception: Level 5/6 (curvature, diffraction) introduce additional terms I have not separately validated under rotation; skip.
- Tolerance: rotations composed from `scipy.spatial.transform.Rotation` are double-precision; atol around 1e-13 for sab values around unity.
- Status: IMPLEMENTED. test_metamorphic_simultaneous_rotation.

**D. Mesh scale invariance for incoherent per-triangle sab**
- Relation: for lambda > 0, scaling all vertices of the mesh by lambda leaves per-triangle `sab` unchanged for Levels 2, 3, 4 (q=0). Total absorbed power `P_abs` scales as lambda^2 (because triangle areas scale as lambda^2 and sab is unchanged).
- Monograph: Eq 2.5, 5.4. The spatial kernel depends on normals (unit vectors, invariant under scaling), k_hat, and path power. It does not reference centroids or areas in the sab computation. `P_abs = sum(sab * areas)`, so p_abs scales as lambda^2.
- Precondition: mesh is scaled about any fixed point; paths unchanged. Incoherent levels only.
- Exception: Coherent Levels 7 and 8 depend on `exp(-i*k_0*k.r)` at each centroid, which is NOT scale-invariant. Do not apply to coherent.
- Tolerance: FP double precision.
- Status: IMPLEMENTED. test_metamorphic_mesh_scaling.

**E. Incoherent path superposition (additivity)**
- Relation: for disjoint path sets A and B, `sab(A union B) = sab(A) + sab(B)` at Levels 2, 3, 4 (q=0).
- Monograph: Eq 5.4: `S_ab = T0 * ReLU(M) @ s`, linear in path-power vector s. For Level 3, 4, the kernel is `sum_i T_eff_i(mu_{j,i}) * ReLU(mu_{j,i}) * S_i`, a linear combination over paths.
- Precondition: Each path has its own (k_hat, power). Pure incoherent addition.
- Exception: Coherent levels have cross-terms between paths (by design). Do not apply.
- Tolerance: FP double precision.
- Status: IMPLEMENTED. test_metamorphic_incoherent_superposition.

**F. Peak sab at normal incidence is polarisation-universal**
- Relation: for a single plane wave carrying power density `S_inc`, any triangle whose normal exactly opposes k_hat (mu=1) absorbs `sab = S_inc * T0` regardless of polarisation (q in Level 4).
- Monograph: Section App. "Peak Sab is polarisation-universal" (around line 5378): "At theta=0, Delta T = 0, so Teff(0) = T0 for any polarisation and Sab(0) = S_inc * T0." Also sec:exact-bounds.
- Precondition: mu=1 exactly (head-on geometry).
- Exception: For mu strictly less than 1, polarisation matters.
- Tolerance: FP double precision.
- Status: IMPLEMENTED. test_metamorphic_peak_polarisation_universal.

### Rejected (9)

**Reciprocity (swap TX and RX)**: The framework is one-way (paths arrive at the body). The monograph does not state a reciprocity invariance at the dosimetry level; it would require a full EM reciprocity argument that the framework's abstractions do not expose cleanly. Dropped.

**Frequency extrema (DC, THz limits)**: The monograph is explicit that the framework is valid above 100 MHz (for total power via Tbar) and 6 GHz (for the local surface map). Below that, the framework breaks down. There is no clean continuous limiting relation of the form `output(f -> 0) = X`. Dropped.

**Distance scaling (1/r^2 in the near-field extension)**: Eq 5.20 (`Sab = P_t * G(k_hat) / (4 pi d^2) * T0 * ReLU(.)`) is a constitutive relation, not an invariance. It is what the kernel is expected to compute at level 2 with point-source input; we do not have a separate kernel-agnostic way to test it without circularity. Dropped.

**ECBF optimum ≥ any feasible precoder**: The monograph guarantees global optimality via S-procedure (sec:ecbf-solution). Testing would involve sampling random feasible precoders and checking the signal norm. The solver has a per-call numerical tolerance (Newton/bisection on Lagrange multipliers); strict inequality with tight atol is not achievable without fudge. A "ECBF signal is no worse than 1 - epsilon times any random feasible x" test exists in principle but would need epsilon tied to solver tolerance; too brittle. The existing `test_ecbf_satisfies_constraint` covers the constraint side; optimality is a harder ask and is best tested with golden cases, not metamorphic. Dropped.

**Convexity of the ECBF signal objective**: The signal objective `|h^T x|^2` is NOT convex in x (it is a rank-1 quadratic form, convex in `|.|^2` sense only along a ray). The roadmap suggested "convexity of coherent MIMO"; convexity applies to the feasible set (PSD constraints), not the signal objective, so the claim as stated is false. Dropped.

**Reverberation limit / diffuse field polarisation independence**: Monograph Eq 2.64 (sec:diffuse-limit) states `Sab(r) = S_total * T0 / 4 * eta(r)` in the isotropic limit. Verifying requires approximate isotropic illumination via Monte Carlo over many random directions; tolerance then scales as 1/sqrt(N). Not a clean algebraic metamorphic relation. Dropped (it is a validation target, not a metamorphic invariant).

**Level monotonicity (L0 >= L1 >= ... >= L_spatial_peak)**: Monograph does NOT claim a monotone fidelity ordering. Level 0 is a bound, Level 1 is exact for total power, Level 2 underestimates relative to Level 3 for some angles (pseudo-Brewster), and Level 3 vs Level 4 depends on sign of q. The existing `test_Tavg_exceeds_T0_near_pseudo_brewster` in test_physics_invariants.py explicitly documents that L3 can give HIGHER sab than L2. Level monotonicity does not hold. Rejected as unfounded.

**Scale invariance (generic)**: The phrasing in the roadmap is ambiguous. Specific scalings that hold: power linearity (tested), mesh geometric scaling for incoherent (candidate D). Scaling the body and sources together: not generally a clean invariant because the near-field regime boundary depends on d/lambda. Dropped as too vague.

**Cross-polarisation sum equals unpolarised**: The monograph does state that adding orthogonal polarisations with uncorrelated amplitudes (e.g., unpolarised = equal TE and TM power) gives `Teff = T_avg`. But there is no kernel API that lets you feed separate TE and TM paths; path psi is a single complex 3-vector. Not directly testable. Dropped.

## Summary

6 of 15 candidates survived validation and are implemented as pytest tests in `tests/test_metamorphic_*.py`. Each test cites the monograph section and uses tolerance that reflects FP arithmetic, not fudged wiggle room. The decorator `@metamorphic_relation` defined in `tests/_metamorphic.py` is a thin 30-line Hypothesis wrapper: no `GeMTest` dependency.

## Recommendation

Metamorphic testing is a **net-win for AEGIS, conditionally**. Net-win because:
- Candidates A, B, C, D, E, F catch whole classes of bugs (e.g., any future refactor that accidentally introduces coordinate-system dependence or drops a missing phase cancellation).
- They are cheap: no mesh fixtures beyond the conftest helpers.

Conditionally:
- Do NOT invest in relations that require Monte Carlo averaging or solver-tolerance arguments. Those are validation tests, not metamorphic.
- Resist the temptation to add "level monotonicity"; the monograph explicitly refutes it.
- If monograph v3 adds a concrete diffuse-limit or near-field analytical formula, revisit candidates that were dropped above.

## Usage

Adding a new relation requires (1) a monograph citation of the underlying invariant, (2) stating preconditions and exceptions, (3) a test whose tolerance matches FP arithmetic, not fudge. If the relation doesn't fit that mould, it is not metamorphic.
