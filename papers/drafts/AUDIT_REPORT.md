# Audit report: paper_AB.tex compliance with all your instructions

Five Opus auditors ran in parallel, each owning one part of `user_messages.txt`. Each one re-read the style guides in `papers/how_to_write_good/`, distilled actionable instructions from your messages, and verified by grep / Read against the current `paper_AB.tex` and `paper_AB_SI.tex`. Compaction-summary duplicates were skipped.

In addition, Figure 1 was created from scratch as you requested (separate task, not an audit).

---

## TL;DR — what's NOT done that you asked for

The big offenders, ranked by how loudly you flagged them:

1. **`None ... None ... None ...` anaphora at lines 156-158** — you cited this as the canonical example of "you don't listen". All five auditors saw it. **Still in the paper.**
2. **`None requires an FDTD solve...` mic-drop at line 1289** — same family.
3. **British spellings still scattered through both files** (~10 hits in main, 8 in SI) — you said "American it is" but `realised`, `summarises`, `catalogue`, `idealisation`, `regularises`, `modelled`, `minimised`, `organised` survive.
4. **Figure 8 (kernels vs FDTD) whitespace bug** — you sent the highlighted-whitespace screenshot. Root cause: `subplots_adjust` + `bbox_inches="tight"` collide in `validation/scripts/plot_tier0.py`. Pure code bug, not a config knob.
5. **Mic-drop pattern survives** — `are not five quantities. They are one.` (line 1625), `Three implications follow.` (1619), `Two results follow.` (1444), `The three criteria stratify cleanly.` (1515), `Two regulatory metrics are evaluated.` (1014), abstract `This is a generalized Cauchy formula.` (100).
6. **Cadenced "X is one Y" stop-burst** — the 7 consecutive parallel "is" sentences at lines 197-215, plus the abstract version at 100-103, plus the conclusion mirror.
7. **Figure caption inconsistency**: caption at line 1068 says `4 FDTD phantoms`; abstract and body both say `5`.
8. **Broken sentence at line 913**: `\Cref{fig:mie}(a) the error versus size parameter at $28\,$GHz.` — verb missing.
9. **`\thanks{}` block** — funding text only in the back-matter `\section*{Acknowledgment}`, missing from the title-page footnote where IEEE house style places it. Manuscript-received placeholder line is also absent.
10. **ORCID is wrong** — line 72 says `0000-0002-1374-0118`; you provided `0000-0001-9948-9157`.
11. **Bios are commented out** — `\iffalse...\fi` at lines 1822-1907 (intentional from your "comment out" message), but the wrap also disables Robin's bio. If the paper is single-author Robin, his bio should be active.
12. **"Chain" framing survives** — you said the word "chain"/"chaining" was unnecessary throughout, but it's still at lines 197, 636, 659.
13. **Salesy fig-1 caption** — `One closed-form identity matches every direction-averaged whole-body absorption ratio...` is the same "one identity, five studies" mic-drop you killed in the figure suptitle but it migrated into the caption.
14. **Two prose semicolons in SI** at lines 314, 316 (inside an itemize). You said "always split semicolons in prose". Main paper is clean.

A handful of softer / borderline items (residual `Azzam's`, "community" framing in conclusion, `admit/admits` Latinate verbs, "framework" survivor at line 1062, "this paper bounds" self-reference at line 1241, `et\nal.` line break at line 154) are listed in the per-part sections below — they're judgment calls, not unambiguous violations.

**No physics, math, or numerical values are touched by any of the proposed fixes.**

---

## Part-by-part findings

### Part 1 — msgs 1-19 (project kickoff through early structural feedback)

**Range:** 2026-05-04 19:48 → 2026-05-05 07:35.
**Themes:** read the monograph, write 3 papers, IEEE two-column, drop "as in paper A", strip mic-drops, simple language, present tense, no AI mention, scienceplots figures.
**Audited:** 35 distinct instructions.
**Status:** mostly APPLIED. 10 NOT/PARTIALLY APPLIED.

Concrete unfixed items from this batch:
- Cadenced anaphora `None of these works... None extends... None explains...` (lines 156-159) — your headline complaint
- Tail mic-drop `None requires an FDTD solve...` (lines 1289-1290)
- `Kodera are not five quantities. They are one.` (lines 1623-1625)
- `Two results follow.` (line 1444), `Three implications follow.` (line 1619), `The three criteria stratify cleanly. \Cref{tab:bands} summarises.` (line 1515), `Two regulatory metrics are evaluated.` (line 1014), abstract `This is a generalized Cauchy formula.` (line 100)
- Cadenced "X is one Y / X is the Z" parallel-structure paragraph at lines 205-212
- Promotional "the framework" survivor at line 1062

### Part 2 — msgs 20-37 (KISS sweep, figure iteration, paper merge into AB)

**Range:** 2026-05-05 07:37 → 2026-05-05 13:08.
**Themes:** kill micdrops in fig captions ("one identity, five studies"), aggressive KISS (`unification`, `exposes the anthropometric scaling`), avoid `ReLU` to hedge reviewers (keep GELU), psSAR10g placement, quantitative title justification (1-100 GHz), merge papers A+B.
**Audited:** 19 instructions plus 4 standalone findings.
**Status:** mostly APPLIED. 15 specific fixes proposed.

Concrete unfixed items from this batch:
- Mic-drop survives at fig waterfall caption: `One closed-form identity matches every...` (line 1068, also wrong phantom count `$4$` vs body's `$5$`)
- `admit/admits` Latinate verbs at lines 1275, 1438 (replace with `give/gives`)
- `thus produces` wordy at line 1314
- `framework` survivor at line 1062
- Self-referential `This paper bounds...` at line 1241
- Self-referential `proven in this paper` in fig caption at line 1262
- `Two results follow.` at line 1444 (from F2 finding)
- SI mic-drop `Smaller body sizes carry lower thresholds.` at lines 668-670
- Line-broken `Diao et\nal.` typo at lines 154-155
- Missing quantitative band-edge rationale in abstract / intro for "1 to 100 GHz" title
- Missing explicit "above 6 GHz the basic restriction switches to APD" honesty at lines 1373-1378
- ReLU/GELU substitution APPLIED cleanly (no ReLU in body, GELU mention at line 1199 preserved)

### Part 3 — msgs 38-58 (style references, SI creation, ORCID/funding/bio)

**Range:** 2026-05-05 13:23 → 2026-05-05 14:09 (only 2 unique messages; the rest of part 3 is a /compact re-injection block).
**Themes:** read style guides explicitly before writing, monograph_v2.tex is the gold standard, iterate via tex→png loop, Robin's ORCID, funding from SHAPE+GOLIAT, manuscript dates open, bio from oldest_paper.tex, no AI mention.
**Audited:** 12 instructions plus 7 cross-cutting style issues.
**Status:** mostly APPLIED for hard format rules. ORCID and bio are NOT APPLIED.

Concrete unfixed items from this batch:
- ORCID is wrong: line 72 has `0000-0002-1374-0118`; you supplied `0000-0001-9948-9157`
- Robin's bio is wrapped in `\iffalse...\fi` and not rendered (lines 1822-1907)
- Co-author bios for Luc/Günter/Emmeric/Wout exist in the file but the `\author{}` byline at line 72 only lists Robin — inconsistent. Either drop the co-author bios or restore them to the byline
- `\Cref{fig:mie}(a) the error versus...` — broken sentence, missing verb (line 913)
- Caption phantom-count inconsistency: `$4$ FDTD phantoms` (line 1068) vs `$5$` everywhere else
- Cadenced "X is one Y" parallel structure (same finding as Part 1, item 9) at lines 197-215 in introduction; mirrored at 1607-1617 in conclusion
- Funding currently only in `\section*{Acknowledgment}`, not in the title-page `\thanks{}` (IEEE house style places it there, per `papers/example_papers/oldest_paper.tex`)

### Part 4 — msgs 59-77 (post-compaction front-matter instructions)

**Range:** 2026-05-05 14:11 (only one genuine new message; rest of part 4 is the /compact dupe block plus subagent task notifications).
**Themes:** front-matter instructions — Martens ORCID, SHAPE+GOLIAT funding placement, manuscript dates open, bios from oldest_paper.tex, IEEE membership grades, no AI.
**Audited:** 7 instructions.
**Status:** front matter is partial — the user-supplied ORCID and IEEE membership grades are not in the byline.

Concrete unfixed items from this batch:
- Add Martens' ORCID `0000-0001-9948-9157` to the byline (the auditor read this as Martens' ORCID; cross-check Part 3 where it's read as Robin's ORCID — **clarify which**)
- Move SHAPE/GOLIAT funding into a first-page `\thanks{}` (currently only in back-matter)
- Insert `Manuscript received [date]; revised [date]; accepted [date]; ...` placeholder line into a `\thanks{}`
- Un-comment Robin's biography (remove `\iffalse...\fi` at 1822/1907); decide whether co-authors stay or go based on authorship
- Add `\IEEEmembership{Member,~IEEE}` etc. to the byline if multi-author; absent from byline entirely
- "AI mention" check: clean — no AI disclosure or mention of LLMs/Claude/etc.

**Conflict to resolve:** Part 3 read `0000-0001-9948-9157` as **Robin's** ORCID; Part 4 read it as **Luc Martens'** ORCID. Need your call on which is correct before applying.

### Part 5 — msgs 78-106 (recent micro-edits)

**Range:** 2026-05-05 14:34 → 2026-05-06 11:57.
**Themes:** American spelling, no space before %, manual bibitems, funding to acknowledgements, no IEEEmembership in byline, ()_+ → []_+ unit notation, no `regulator wants` framing, precise ICNIRP basic restrictions, drop `Five communities`/`chains five known results`, drop `Azzam's`, fig 8 x-axis 0-6 GHz with no whitespace, ±20% dielectric uncertainty propagating sub-linearly to ±7% on T_0 (not "linearly"), split prose semicolons, weak-verb cleanup, comment out bios, fix fig 8 width.
**Audited:** 35 instructions.
**Status:** most micro-edits APPLIED. 6 not.

Concrete unfixed items from this batch:
- ~10 British spellings remain in main paper, ~8 in SI (`realised`, `summarises`, `catalogue`, `idealisation`, `regularises`, `modelled`, `minimised`, `organised`)
- 2 prose semicolons in SI itemize at lines 314, 316
- Fig 8 (kernels vs FDTD) still has visible whitespace — the `subplots_adjust` + `bbox_inches="tight"` collision in `validation/scripts/plot_tier0.py` was not actually fixed. **This is a code bug, not a layout knob.**
- "chain" framing survives at lines 197, 636, 659 even though you said the word was unnecessary
- "community" framing in conclusion (lines 1619-1628) — "Five communities" is gone but two "community" refs remain (regulatory + propagation/antenna). You only explicitly killed "Five communities", so this is borderline.
- Bare `Azzam's` possessives at lines 180, 1636 — borderline judgment call

Confirmed APPLIED in part 5: ()_+ → []_+, all units `[ ]` not `( )`, `pospart` macro present, no `\)_+` anywhere, no space before %, manual bibitems, funding in acknowledgement, no IEEEmembership in byline, ORCID inline (not in thanks), bios commented out via `\iffalse`, sub-linear uncertainty propagation language at line 1252 ("sub-linear because $T_0$ depends on $|\ntilde| = \sqrt{|\varepsilon_c|}$"), no `regulator wants` / `dosimetry literature has converged` / `chains five known results into one closed form`, capitalized acronym expansions (FDTD, SAR, APD, GPU, TM, TE, ICNIRP), simple keywords without gls.

---

## Figure 1 (separate task)

You asked for a brand new Figure 1: gray Thelonious phantom (transparent background, same camera as fig 4a) + a TikZ overlay with a horizontal "Plane wave" arrow, a dot on the left forearm, dashed tangent lines from the dot to a circle, and inside the circle a TikZ tessellation of slightly-irregular triangles with one central highlighted triangle bearing a normal vector.

**What I built:**

1. `papers/drafts/figures/fig1/render_gray_phantom.py` — adapts the existing painter's-algorithm rasteriser (`theory/scripts/visualize_eta_3d.py`) to output flat gray with an alpha channel. Camera: azimuth 210°, elevation 5° (same as fig 4a `sab_phantom_visible.pdf`). 800×1600 px before trimming the transparent margins; final 461×1581 px.
2. `papers/drafts/figures/fig1/fig1_geom.tex` — standalone TikZ document. Phantom raster, plane-wave arrow, dot at (0.91·width, 0.55·height) image-relative (left forearm), proper tangent-point geometry to the inset circle (precomputed: `T_a = (4.886, 1.740)`, `T_b = (5.944, 4.743)` for `cc = (6.10, 3.00)`, `R = 1.75`). Inside the clipped circle: 23-vertex hex-style grid with ±0.05 cm random-feeling perturbations, 26 triangles in 4 strips. Central highlighted triangle is `(v0-1, v0-2, v1-1)` filled blue with thicker outline; outward `\hat{n}` arrow at 72° from horizontal.

**Iteration log:**
- v1: tangent lines were eyeballed (`(-0.55*R, ±0.84*R)` from cc) — they didn't envelope the circle correctly; dot was too low
- v2: switched to `let..in` pgfmath tangent computation with `asin/acos` half-angles — formula was right in principle but the let-in coordinates rendered wrong (lines went into the upper-left of the circle instead of opposite sides)
- v3: hardcoded the precomputed tangent-point coordinates; repositioned circle to `(6.10, 3.00)` so the wedge from the dot opens cleanly across the circle's long axis. Final.

**Output files:**
- `papers/drafts/figures/fig_geometry.pdf` (vector, the file to include from paper_AB.tex)
- `papers/drafts/figures/thelonious_gray.png` (the raster the TikZ document references)
- `papers/drafts/figures/fig1/` (working dir with the .py, .tex, .log, .aux)

The figure is 1:1 ~ 9.7 × 9.0 cm. At `\columnwidth = 8.89 cm` it scales to ~89%, with text rendering ~8 pt — IEEE-acceptable.

**Not yet done:** integrating it into `paper_AB.tex` (e.g. replacing the current `\label{fig:config}` block at lines 234-289). I'm waiting for your call on whether this *replaces* the existing tikz config figure or *adds* a new one.

---

## Recommended next step

I have a consolidated checklist of ~25 concrete edits across both files. I propose to apply them sequentially (no parallel agents, no edit conflicts) in this order:

1. **Hard fixes (unambiguous):** anaphora, mic-drops, broken sentence at 913, phantom-count typo, semicolons in SI, British→American spellings
2. **Front matter:** ORCID (after you clarify Robin vs Martens), `\thanks{}` block with funding+manuscript-dates placeholder, decide on bios (single-author Robin only, or restore co-authors)
3. **Code fix:** the `plot_tier0.py` `subplots_adjust` + `bbox_inches="tight"` collision for fig 8
4. **Borderline (ask first):** `Azzam's` body usages, "community" framing in conclusion, "chain" framing
5. **Figure 1 integration** if you want it to replace `fig:config`

Confirm and I'll start.
