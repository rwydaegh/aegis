# Metamorphic testing in AEGIS

Metamorphic testing is a technique for scientific code where ground truth is hard to compute directly, but transformations of the input produce predictable transformations of the output. The shape is always "if input X transforms by T, output Y transforms by T'".

In AEGIS, the ground truth is often a full-wave electromagnetic simulation (FDTD) that costs millions of CPU hours. Metamorphic tests let us catch whole classes of bugs without that. A bug that introduces an accidental frame dependence, drops a cancellation, or breaks a quadratic form will fail a metamorphic relation test long before any end-to-end validation.

## Files

- `tests/_metamorphic.py` - 30-line helper with `rotation_matrix_from_axis_angle`, an `assert_invariant` wrapper, and an optional `@metamorphic` decorator. No external dependency (no GeMTest).
- `tests/test_metamorphic_<name>.py` - one file per relation. Each module's docstring cites the monograph theorem or equation it tests.
- `docs/internal/metamorphic_analysis_2026-04-18.md` - rejection notes for candidates that did NOT survive validation. Read this before adding a new relation: many "plausible" invariants do not hold.

## The six implemented relations

| File | Relation | Monograph |
|------|----------|-----------|
| `test_metamorphic_coherent_scaling.py` | `Sab(alpha*x) = |alpha|^2 Sab(x)` | Thm 4.1, Eq. 4.9 |
| `test_metamorphic_coherent_global_phase.py` | `Sab(e^{i*phi}*x) = Sab(x)` | Thm 4.1, Eq. 4.9 |
| `test_metamorphic_simultaneous_rotation.py` | sab invariant under R in SO(3) applied to (normals, k_hat) | Eq. 2.5, sec:local-law |
| `test_metamorphic_mesh_scaling.py` | sab invariant under uniform mesh scaling lambda > 0 | Eq. 2.5, sec:matrix |
| `test_metamorphic_incoherent_superposition.py` | `sab(A u B) = sab(A) + sab(B)` | Eq. 5.4 |
| `test_metamorphic_peak_polarisation_universal.py` | sab(mu=1) = S_inc * T0 for any q | App. "Peak Sab is polarisation-universal" |

## Adding a new relation

1. **Find it in the monograph.** Read `theory/monograph_v2.tex` with the lens "what transformations produce predictable outputs?". A relation you cannot cite is a guess, not a metamorphic invariant.
2. **State preconditions.** Under which fidelity levels does it hold? What assumptions (q=0? convex body? normal incidence?) are required?
3. **State exceptions.** Levels or regimes where the relation fails. (Examples: translation invariance fails for coherent levels. Mesh scaling fails for curvature levels because H scales as 1/lambda.)
4. **Write the test.** One file, `tests/test_metamorphic_<name>.py`. Include parametric cases and a Hypothesis sweep. Tolerance must match FP double precision (rtol around 1e-11, atol around 1e-14), NOT a loose wiggle room. If you need 1e-2 tolerance, your relation is approximate; it is not metamorphic.
5. **Link to the analysis doc.** If the relation was previously rejected, say why it is being revisited.

## Debugging a violation

When a metamorphic test fails, the cause is one of three things:

- **Code bug.** Most common. The kernel has an accidental dependence that the relation catches. Example: a rotation-invariance test failing would likely indicate a hidden reference to global axes inside the Fresnel operator. Fix the code, not the test.
- **Monograph bug.** Rare, but it has happened. The equation in the monograph might quietly assume a precondition that the test does not impose. Track down the assumption, tighten the test preconditions to match, and add a comment in the test citing the missing precondition. Do NOT loosen the tolerance.
- **Numerical tolerance issue.** FP accumulation in a large sum can legitimately approach 1e-12. Use `rtol=1e-11` or `atol=1e-13` and document why in the test.

If none of the above explains the failure, file a GitHub issue with a minimal Hypothesis counterexample (the failing `@given` case) and tag the maintainer. Do NOT silently rewrite physics to make a test pass.

## When metamorphic tests add value vs waste cycles

**Add value when:**
- The relation is an exact algebraic identity (scaling, rotation, linearity over disjoint inputs, quadratic form).
- The input transformation is cheap (permute paths, rotate by a matrix, multiply by a scalar).
- The tolerance is dominated by FP round-off, not by Monte Carlo variance or solver tolerance.

**Waste cycles when:**
- The relation holds only "in the limit" (large N, small epsilon). That is a convergence test, not metamorphic.
- The tolerance has to be inflated to hide solver noise. That is a golden-value test in disguise.
- Both legs of the relation use the same kernel path, so the test degenerates into a tautology. Check: does the transformation force a different code path in the kernel? If yes, good. If not, it might still have value as a regression guard, but be honest about it.

## Do NOT

- Invent a relation. Every test must cite the monograph.
- Use GeMTest or any other framework. 30 lines of Hypothesis is plenty.
- Weaken a tolerance to make a test pass. Fix the code.
- Add level-monotonicity (L0 >= L1 >= ... ). The monograph refutes it (pseudo-Brewster enhancement means L3 can exceed L2).
