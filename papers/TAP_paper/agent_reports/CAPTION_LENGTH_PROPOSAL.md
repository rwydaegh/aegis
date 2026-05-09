# Caption-length proposal

Goal: smart variation, not uniform ≤4 lines. Captions weigh more when
the figure is a punchline carrying numerical claims; less when the
figure is iconic. Captions should not duplicate body text adjacent to
them.

Counts below are typeset lines in the current `paper.pdf` (post the
edits already applied: Fig 7 removal, Fig 8/Fig 2 trims, Fig 10
prose tightening).

---

## Per-figure recommendation

| # | Figure | Current | Verdict | Rationale |
|---|--------|---------|---------|-----------|
| 1 | Flowchart | ~7 lines | **Keep** | Complex pictorial chain. Caption is the only place the reader gets an arrow-by-arrow legend. Pruning hurts comprehension. |
| 2 | Configuration / phantom + sphere of normals | 3 lines (already trimmed) | **Keep** | Iconic diagram, prose handles the law statement. |
| 3 | Pseudo-Brewster T_s / T_p / T_avg + APD/IPD | ~8 lines | **Trim to ~5** | The body text in §III-B already describes the 5.6% bound. Caption can collapse to: panel labels + the dotted-reference identification. Concrete rewrite below. |
| 4 | R(f) sphere ratio | ~6 lines | **Keep** | Single-panel but loaded with regulatory framing (R<1 conservative, R>1 not). Worth the lines. |
| 5 | Phantom triptych (APD + η front + η side) | ~9 lines | **Trim to ~6** | Caption restates η definition that §IV-A already gives. Replace per-panel narration with terse panel labels + one sentence on the role of (a) vs (b,c). Concrete rewrite below. |
| 6 | Mie validation (size + frequency) | ~7 lines | **Keep** | The caption is the only place the body-part dashed lines and the orange asymptote are decoded; they do not appear in the body text. |
| 8 | val_fdtd kernels vs Sim4Life | 6 lines (already trimmed) | **Keep** | The five-curve legend needs the in-caption decoding. |
| 9 | lit_waterfall (5 panels) | ~12 lines | **Trim to ~9** | The five-panel decoding has to live in the caption; this is the punchline figure. Cut: the sub-clause in (a) about γ_s = 0.865 (already in body), the per-marker enumeration in (c) (Table V carries it), and the Bamba × marker list. Concrete rewrite below. |
| 10 | Error budget bars | 5 lines (already trimmed) | **Keep** | Now mirrors Table VIII; short is right. |

Net change: ~10 lines saved, distributed across three captions where
the body text was duplicating the caption. No caption forced below a
"4-line floor" that would amputate the figure's job.

---

## Concrete rewrites

### Fig 3 caption (was ~8 lines, target ~5)

> Pseudo-Brewster compensation for skin at 28 GHz (ñ = 4.49 − 1.79i,
> T₀ = 0.539). (a) Fresnel power-absorption coefficients T_s (TE),
> T_p (TM), and T_avg = ½(T_s + T_p) versus incidence angle θ. T_avg
> stays within 5.6% of T₀ up to 75°. (b) Normalized absorbed power
> APD/IPD = T(θ) cosθ for the same three states. The dotted reference
> is the simplified T₀ cosθ prediction; the gap to T_avg cosθ is the
> Fresnel approximation error.

Changes: dropped the redundant "TE and TM curves diverge but T_avg
stays within 5.6%" — already stated. Dropped the "(b) for the same
three states" repetition.

### Fig 5 caption (was ~9 lines, target ~6)

> APD and η maps on the Thelonious phantom (skin at 28 GHz, IPD = 1
> W/m², area-weighted mean η̄ = 0.865). (a) APD(r) under frontal
> illumination k̂ = +ŷ: front-facing triangles absorb at the cosine
> rate T₀ IPD cosθ; self-shadowed elements drop to zero through
> V(r,k̂). (b,c) Direction-isotropic exposure fraction η(r) ∈ [0,1]
> from (10), front and side views. Panel (a) is the integrand of the
> Cauchy formula along one direction; panels (b,c) integrate over the
> full sphere.

Changes: dropped the body-region enumeration ("medial thighs, inside
of the wrists, ..."), dropped the recap of where reductions occur
(also in body), and tightened the closing "integrand of the Cauchy
formula" sentence.

### Fig 9 caption (was ~12 lines, target ~9)

> Closed-form prediction (12) compared against direction-averaged
> whole-body absorption ratios reported in the dosimetry literature
> across 168 volunteers and 5 FDTD phantoms from 1–100 GHz.
> (a) Flintoft 2014, 60 volunteers, 1–12 GHz: γ_s-corrected points
> (filled triangles) collapse the 5–11 GHz plateau onto T̄(f) within
> 2%–4%. (b) Zhang 2017, 48 subjects, 1–18 GHz: plateau values
> ξ = 4 C₁(f) match T̄ A_ab/A; the Fig. 4.11 envelope (digitized,
> 1–6 GHz) covers the body-Mie regime. (c) Bamba 2014, four FDTD
> ellipsoid phantoms, 1.45–5.8 GHz: regression points with ≤ 6%
> per-phantom scatter and a 3-GHz anatomical-phantom validation
> point. (d) Kodera 2024 T_tr (homogeneous-skin 1-D, 1–100 GHz) plus
> Diao 2024 T_eff on TARO (1–30 GHz, plane-wave) and the 5G
> patch-array back-fit at 28 GHz. (e) Common axis: every dataset
> converted to T̄·A_ab/A on a single curve. The body-Mie /
> fat-resonance regime below 6 GHz is shaded gray on every panel,
> where Section IV-C's layered transmission recovers the dip.

Changes: dropped per-marker enumerations that are now in Table V;
the panel-(c) sentence dropped the four numerical residuals
(`-39.4%, -11.7%, +10.7%, +10.6%`) which appear in the body text and
do not need to be in the caption.

---

## What to apply

If you agree, I will apply the three rewrites above. The other six
captions stay as-is.
