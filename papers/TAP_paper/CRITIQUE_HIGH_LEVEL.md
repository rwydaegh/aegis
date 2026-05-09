# High-level critique of `paper.tex`

Written 2026-05-08. I read the full LaTeX, every figure (page-by-page PNGs),
and skimmed the SI to see what got offloaded. This is not a copy-edit pass —
it's the things I would push back on if you brought the draft to a coffee
meeting before submission.

## Bottom line first

The paper is genuinely good. The core idea — that biological tissue lives
in Azzam's high-index regime so the angular Fresnel collapses, and that the
classical Cauchy projected-area identity extends to nonconvex absorbers via
the ambient-occlusion primitive — is the kind of thing reviewers remember.
Unifying Bamba / Flintoft / Zhang / Diao / Kodera into a single closed form
is, by itself, a strong scholarly contribution: those five empirical scalars
have been floating around the dosimetry literature uninterpreted, and you
nail them all at once. The Sim4Life "1.012 with no fitted parameters" number
is a clean kill shot.

What I'd push you on, before submitting, is **focus**. Right now the paper
is trying to do three things — surface law, whole-body identity, peak/cube
SAR — and the third one drags. Cut it (or shrink to a one-line corollary)
and the paper gets sharper, shorter, and easier to defend.

The list below is ordered by how much it would change the paper.

---

## 1. The cube-SAR / standing-wave / sub-surface-peak machinery is a
       different paper

Section VII.B (and the layered fat-resonance subsection it leans on, IV.C)
introduces a whole separate mechanical apparatus: Chew recursion, three-layer
transfer matrices, standing-wave SAR per layer, the sub-surface peak
criterion (Eq. 19), Fabry–Pérot enhancement factors of 2–4. The SI carries
~250 lines on it.

This material does not connect cleanly to the surface-Cauchy story. The
*thin-skin* cube SAR (Corollary 4, Eq. 18) is gorgeous — one line, follows
from energy conservation on an axis-aligned cube, exact in the αL≫1 limit.
Keep it. **Cut everything below 6 GHz on the cube quantity** to the SI.
- Below ~6 GHz the surface law itself "loses pointwise meaning" (your own
  line 1059), so promising a closed-form pointwise cube replacement there
  invites scrutiny you don't want.
- The whole-body identity stays valid via $T_{\rm lay}$, which is enough.
- The 3-GHz fat-dip story can stay in §IV.C as a one-paragraph "the same
  framework explains the dip qualitatively, full layered analysis in SI."

If you do this, the paper drops from 14 → ~11 pages and the contribution
list cleans up: surface law, whole-body identity, compliance corollary,
done.

## 2. The "headline result" is buried; lead with it

A reader currently has to wade through six sub-sections of Fresnel
derivation and pseudo-Brewster bookkeeping before they see a number that
shows the thing works. Section V's $\langle P_{\rm abs}\rangle/{\rm FDTD} =
1.012$ at 5.8 GHz, no fitted parameters, on a real anatomical phantom — that
is *the* result. Right now it's two sentences in §V.C.

Two ways to fix:
- **Open §II with the answer.** State the whole-body identity $\langle
  P_{\rm abs}\rangle = S_{\rm inc}\,\bar T(f)\,A_{\rm ab}/4$ on page 2, plus
  one sentence saying "this matches FDTD to 1% with no fitted parameters,"
  and then say "the rest of the paper derives it." This is the same
  rhetorical move as a math paper that states the main theorem in §1 before
  proving it.
- **Promote Fig. 8(e) (lit waterfall, common axis)** to a Page-1
  visual-abstract figure. That single panel collapses 168 volunteers + 5
  FDTD phantoms onto your closed-form curve. It is the most persuasive
  picture in the paper.

The flowchart (Fig. 1) is currently doing roadmap duty *and* visual-hook
duty. It's overloaded for a hook. Either simplify it (3 boxes, 3 arrows,
sub-6 GHz branch dropped) or let it do roadmap duty only and put a separate
results-front figure ahead of it.

## 3. The "three gaps" framing in the intro is the weakest part of the intro

Lines 215–227. Gap #1 ("empirical scalars are obtained from FDTD") isn't a
gap, it's just saying the prior work is empirical — that's a positioning
move, not a hole in the literature. Gap #3 ("3 GHz dip not embedded in body
integral") is narrow and feels engineered to justify §IV.C.

Replace with one bigger framing: the dosimetry literature has been measuring
*different cross-sections of the same closed-form object*. Bamba's $\eta(f)$,
Flintoft's $\langle Q^a\rangle/\gamma_s$, Zhang's $\xi$, Kodera's $T_{\rm
tr}$, Diao's $T$ — these are five different operationally-defined quantities
that, *under the closed form derived here*, all reduce to $\bar T(f)$ or
$\bar T \cdot A_{\rm ab}/A$. That's a cleaner and more ambitious framing
than "three gaps." It also previews Fig. 8 perfectly.

## 4. Demote contribution #2 (the "polarization cancellation theorem")

You list five contributions. #2 is "a polarization cancellation theorem
stating that the angular polarization correction vanishes under any of three
conditions: circular illumination, random ensemble, or multipath averaging."

It's not a theorem — it's three observations about how a TM-vs-TE difference
averages out in standard situations. Calling it a theorem inflates the
list and is the kind of thing a sharp reviewer will flag. Demote to a
remark in §II.D, or fold into contribution #1 ("the angular collapse holds
under standard regulatory averaging conditions including circular,
random-orientation linear, and multipath illumination").

The other four contributions are genuinely substantial and the list is
stronger with one strong demoted item than five mixed items.

## 5. The reference-level-shortfall finding (Remark 2) is undersold

Lines 1530–1548. You quietly note that the current ICNIRP reference level
of 10 W/m² exceeds your worst-case basic-restriction threshold by 61% on
an infant, 32% on a child, 1% on an adolescent. This is a regulatory finding
with policy implications, and it's hidden inside a `\begin{remark}` after
a population-scaling table.

Two paths:
- **Lean in.** Make this a separate §VII.B subsection titled "Reference
  level versus basic restriction across the human population." State the
  worst-case shortfall, state the directional-average mitigation that
  rescues it, and conclude with: "The closed form makes both the worst-case
  certificate and the directional-average evaluation explicit and cheap to
  evaluate." That is *the* compliance-relevance hook for ICNIRP / IEC /
  IEEE C95 reviewers.
- **Cut it entirely** if you don't want to make a regulatory claim in this
  paper and would rather isolate that finding in a follow-up. The current
  version is the worst of both worlds — a serious claim hedged in a remark.

## 6. Section reordering / pacing

Section II is closer to a chapter than a section. Six subsections, one of
which (II.F, the matrix multi-source form) is an *implementation* aside that
interrupts the derivation chain. Move II.F out into its own §III ("Discrete
mesh form and GPU primitives"), then have the derivation flow II → IV (now
the new §III is between law and Cauchy). This also gives you room to
consolidate the "ambient occlusion = the GPU primitive that runs at frame
rate" argument, which is currently distributed across §II.F and §IV.A and
underplayed.

The "this is video-game shading applied to RF dosimetry" line is one of
the paper's most quotable hooks. Right now it's mentioned but not
celebrated. A single subsection saying it loud — with a wall-clock number
("FDTD: weeks on a GPU cluster. Closed form: 38 ms on a laptop. ~10⁶×
speedup.") — would land hard. I don't see an explicit wall-clock anywhere.

## 7. The pseudo-Brewster story is missing a one-line "why this is
       interesting" hook for the optics audience

The Azzam connection (lines 604–611) is the paper's most surprising
intellectual move and it's stated almost apologetically: "This connection
between the Azzam criterion and biological dosimetry has not appeared in
the optics or bioelectromagnetics literature." Good — but you're selling
yourself short.

Azzam's high-index result is about *anti-reflection* surface design for
optical substrates. You're showing it's already happened, evolutionarily,
on every human body. Three-line digression in §III.A would be earned and
memorable.

## 8. Things that don't quite make sense or need to be tightened

- **The body polarization directivity $D_B \le 16\%$** (line 570) shows up
  out of nowhere as a known quantity. Where is it computed? Probably SI,
  but the main-text reader has no anchor. One sentence: "computed in the
  SI from a 128-direction sweep on Thelonious."
- **"Three conditions" wording** for circular / random ensemble / multipath
  reads like three independent things; really it's three averaging contexts
  any of which suffices. Reword: "under any of the standard regulatory
  averaging conditions — circular polarization, random-orientation linear,
  or multipath — the polarization correction vanishes in expectation."
- **Bamba's $\eta(f)$ vs your $\bar T(f)$** at the lower edge of his band
  (1.45 GHz). You correctly note this is body-Mie territory outside your
  validity window. But you state Bamba's $\eta$ is the same kind of object
  as $\bar T$ on line 998 ("coincides with $\bar T(f)$ to 3% at 5.8 GHz, and
  diverges toward the lower edge"). The reader needs to be told upfront
  that Bamba *defined* $\eta$ as a curve fit absorbing finite-size
  corrections — not as a Fresnel transmission. Right now this is implicit.
- **§V.C per-direction spread** (lines 1196–1199): "per-direction values
  are 1.06, 1.20, and 0.83." A 1.20 / 0.83 spread on three directions is
  large. You attribute it to FDTD discretization and per-direction
  polarization. This deserves more than one sentence — either show the
  spread in a figure (it must be in the data) or be more explicit about
  what the FDTD reference's per-direction noise floor is.
- **Validation Table V** lists "match" qualifiers like "within scatter,"
  "mechanism, qualitative." The Bamba 3 GHz row reports "−39.4%, −11.7%,
  +10.7%, +10.6%" residuals on Thelonious / Billie / Ella / Duke. A
  −39% residual on a phantom is not a small thing even if explained by
  body-Mie. Make sure the table doesn't read as "everything matches" when
  one row contains a 39% miss with a regime caveat.

## 9. Figure-level

- **Fig. 5 (Thelonious phantom maps with censored eyes/genitals)**:
  visually awkward. The black bars over a child phantom's face and groin
  are going to give some reviewers (and ICNIRP-affiliated readers) an
  uncomfortable moment. Either render the phantom posterior-only / clothed
  / chest-up, or use the adult Duke. The censoring is a tell that the
  default render isn't right for publication.
- **Fig. 8 (5-panel waterfall)**: panel (e) is the money panel. Either
  promote it to its own figure (front-of-paper, single column) and demote
  (a)–(d) to SI, or at least make (e) larger than the others within the
  composite.
- **Fig. 1 flowchart**: I would simplify. The dashed "+ Corrections" box
  curving over the top, the inputs box on the right, the sub-6 branch
  inside the formula box — three distinct overlay elements competing for
  attention. A minimalist 3-box, 3-arrow chain with one labeled side
  branch reads in 2 seconds; the current version takes 30.

## 10. Length and venue fit

14 IEEE-TAP-2col pages is fine but on the heavy side. With cube SAR layered
analysis pushed to SI (item 1) and Fig. 1 simplified, you should land
around 11. TAP reviewers tend to reward discipline. The story compresses
naturally to: introduce → derive → validate → comply, with everything else
in SI.

## 11. Title

"Closed-Form Absorbed-Power Dosimetry from 1 to 100 GHz" is descriptive but
flavorless. The abstract uses the words "Fresnel," "Cauchy,"
"pseudo-Brewster," "ambient occlusion" — any of which is more memorable.
A few alternatives:
- *A Cauchy Identity for Whole-Body RF Dosimetry from 1 to 100 GHz*
- *From Fresnel to Cauchy: Closed-Form Whole-Body Dosimetry without FDTD*
- *Replacing FDTD: A Surface-Optics Identity for Body Dosimetry, 1–100 GHz*

You don't have to be cute, but "closed-form" + frequency band is the most
commodified phrasing you could pick.

---

## What I'd actually do, in order

1. Cut layered-cube-SAR machinery from §VII; keep only Cor. 4 (one
   equation). Push standing-wave/Chew/sub-surface to SI. **(Biggest single
   improvement.)**
2. Lead §II with the answer. State the whole-body identity and the 1.012
   FDTD ratio in the first paragraph. Derive afterward.
3. Promote Fig. 8(e) to a stand-alone front-of-paper figure (or merge with
   Fig. 1 as a visual abstract).
4. Rewrite "three gaps" intro paragraph as "five empirical scalars, one
   closed-form object."
5. Demote contribution #2 (polarization cancellation "theorem") to a
   remark.
6. Either lean into or cut Remark 2 (reference-level shortfall on infants/
   children). Don't leave it as a hedged remark.
7. Rerender Fig. 5 without censor bars (different phantom / pose / crop).
8. Add a wall-clock number somewhere ("X seconds on a GPU vs Y hours of
   FDTD").
9. Rename Section II.F to its own section (mesh + GPU primitives) and
   make the "this is real-time graphics" point loudly in one place.
10. Tighten title.

Items 1, 2, 3, 6 will move the needle. The rest are polish.

---

## Honest assessment

Quality: top-quartile of TAP submissions. Probably top-decile if you cut
the cube SAR. The Cauchy generalization + Azzam connection + five-paper
unification is a triple play that very few dosimetry papers attempt, and
the validation evidence is unusually strong (no fitted parameters, real
anatomical phantom, 168 volunteers). It deserves to land in TAP and
probably will.

The risk is over-stuffing. You have at least two papers' worth of material
here and the second one (cube SAR + sub-surface peak + standing-wave
analysis) would itself be a respectable TAP letter. Putting them together
makes the main paper longer without making the central claim stronger.

When the cube-SAR / layered story comes out as a follow-up, this paper
becomes the canonical citation for closed-form whole-body RF dosimetry.
Don't dilute it.
