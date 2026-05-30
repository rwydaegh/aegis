# TT / patent meeting: what this presentation should be

CONFIDENTIAL. Internal. For the 20 May 2026 meeting at UGent TechTransfer. Ref P2026/040.

Written after reading the signed IDF, the TAP far-field paper, the coherent TWC paper and the near-field on-device paper, the two presentation decks and their animations, the feature inventory, and the strategy notes. Slides will be built in LaTeX/Beamer, reusing the existing beamer projects.

---

## Adversarial review: read this first

This section red-teams the plan and answers the two open questions. The detailed plan follows.

### Your two questions

Demo or screenshots. Lead with embedded media, keep the live demo optional. Build the narrative on screenshots and one short screen recording (place antenna, heatmap updates, run the optimizer, ICNIRP overlay flags a region). That guarantees the story lands regardless of the room's network or projector. Offer a two-minute live interaction at the very end as an "it is running right now" capstone, pre-loaded and logged in on a second tab, with the recording as fallback. For a patent meeting a brief live touch is worth it because it is reduction-to-practice you can point at, but never make it load-bearing. One catch: the Thelonious phantom is a child model, and the TAP paper censors it (black bars over eyes and genitals). Use an adult phantom (duke or ella) for anything shown live or in screenshots.

Animations. Worth it, used surgically, all from existing assets, no new builds.

- Opener: `PhantomScene` (`presentations/group/phantom_scene.py`). Zooms from the whole body to a single surface triangle, then shows the field decaying over the skin depth delta. Paired with the existing "FDTD intractable, 10^12 cells, weeks of GPU" line (`slides.py:113`), this is the problem stated viscerally. It is the best animation for this room because it answers the question Filip cares about most ("what is the problem") and it is the one animation that is completely claim-safe, so it cannot look slick to a skeptical IP adviser. Needs a render to mp4 (only a pptx exists). Uses the child phantom mesh, grey and zoomed to the arm, so probably fine, but swap to an adult STL if trivial.
- Framework B: `CoherentPhasors`. Random phases align, absorption concentrates, motivating Q and ECBF (claims 2/2a). Phase alignment is dynamic, a static figure cannot show it.
- Differentiability beat (claims 3/3a, the EPO technical effect): do not build an animation. Record the real deployed optimizer running, hotspot drops and compliance flips green. That doubles as reduction to practice and is more convincing than a stylized clip.
- Optional Framework A explainer: `GeometryOfAbsorption` (central claim 1: lit glows, shadow dark, the wave rotates and the shadow follows). Include if the static censored phantom figure does not already land it.
- Skip pseudo-Brewster as a hero, it is the claim you are deliberately de-emphasizing. Keep its static figure, hold the animation in the appendix for a "why does it collapse to one number" question.

### Four things the plan got wrong or underweighted

1. Get the near-field maturity exactly right, because it is easy to overclaim. The deployed, validated deliverable is the far-field framework plus the AEGIS GUI. The near-field is real science but only research-grade: it is derived in the papers, and there is a small prototype script (the near-field on-device render, demonstrated on ray-traced scenes), but it is not a product, not a GUI, and not FDTD-validated. The simpler geometric near-field primitives (point-source law 1a, view-factor 1b, Gamma_lm 16a) are derived-only, not even coded. So the honest line is: near-field is derived, prototyped, and feasible to build, not shipped. That is not a weakness for the meeting, it is the pitch, because the near-field device product is exactly what IOF money would fund. (An earlier subagent digest overstated the near-field on-device work as a submitted, validated engine and tied it to uplink ECBF. Both wrong. It is an unsubmitted prototype about downlink pose-aware links plus a live exposure reading, not uplink.)

2. This is three inventive clusters plus a platform, not two frameworks. Alessandro asked for geometric/non-coherent versus coherent MIMO, and you should give him exactly that split. But the work is really: (A) the far-field geometric framework (TAP paper, 5 authors, near submission), (B) the coherent exposure operator Q and ECBF (the TWC paper, not yet submitted), and (C) the on-device near-field body digital twin that produces a live APD reading plus a pose-differentiable channel (near-field on-device paper, complete draft). Cluster C is the commercially hottest piece and it may be under-claimed by the current IDF, whose claims center on the dosimetry method, Q, and the systems. Flag to Alessandro: is this one filing or several, and does the on-device twin need its own claims. That is a bigger strategic question than the slide deck.

3. The disclosure surface is wider than one defense date. Three unpublished papers describe the invention and are in flight (TAP near submission, near-field on-device paper complete draft, TWC paper drafting). Three already-published papers (npj 2026, IEEE Access 2022 and 2025) describe the older hybrid RT/FDTD method, not the invention, so they are prior art by the inventors but do not disclose the invention. Confirm one thing out loud: the internal WAVES PhD Forum talk on 26/03/2026 was internal-only with no outside non-NDA attendees. If outsiders were present, that is a disclosure and Alessandro needs to know today. The priority-before-publication rule now has to be coordinated across three papers, not one.

4. Do not headline pseudo-Brewster as the patentable core. The TAP paper itself, honestly, says it recovers the empirical scalars of Kodera, Bamba, Flintoft, and Zhang as special cases, and that Azzam proved the optical-substrate constancy. An examiner can read that as "you derived what others measured." The defensible patent core is the integrated system, the closed-form exposure operator Q without FDTD calibration, the on-device near-field twin, and end-to-end differentiability. Present pseudo-Brewster as the enabling physics, not as the claim that carries the patent. Your own honest_analysis.md reaches the same conclusion.

### Format and scope decisions

LaTeX/Beamer, reusing the promotors and group beamer projects. Tighten the main line to about 12 to 14 slides so the back half of the 90 minutes is discussion. Open technical-first, not pitch-first: slide 1 names the technical purpose Alessandro set, and the one commercial-context slide is short and framed as "why protection matters," so the IP adviser does not feel the meeting was hijacked into a sales pitch.

---

## Who is in the room

- Alessandro Biondi, IP adviser. Called the meeting, owns the patent decision. Wants the precise technical decomposition: inventive core, novelty, enablement, reduction to practice.
- Filip Louagie, named IOF/valorisation responsible on this file. BD Manager (INDATA) and Director Valorisation at imec, ex-Alcatel. Owns the summer IOF call (you put it near one in two). Busy, has not read the monograph, thinks in markets, wants to be in the loop.
- Wout Joseph, promotor and 1% co-inventor, standards-committee seat. Your voucher in the room.
- Likely also Ann Vangeem (paralegal) and possibly Luc Martens, Emmeric Tanghe.

Two decision-makers, two questions. Alessandro decides the patent now, Filip decides the money later, and the patent you settle today is the backbone of Filip's IOF case.

## What the meeting is really for

Two linked gates. Unblock the priority filing before the August defense (hard EPO absolute-novelty deadline). And form the first impression that seeds the summer IOF. The deck serves both because the facts that make this patentable are the facts that make it valuable.

## The IOF lens: what Anniek's deck teaches (Filip, and the summer pitch)

Anniek Eerdekens' IOF deck (equine colic injectable chip, same WAVES group, narrated, in `IOF-AnniekEerdekens-...pptx`) is the template Filip judges against this summer. It is a valorization pitch end to end: of 17 slides, about 14 are problem-in-money, market, competition, business model, roadmap, and budget, and roughly 3 are technology. Ours is the opposite. The gap is packaging, not substance. Our position is stronger than hers (deployed product, real validation, a patentable method versus her trade-secret IP, deeper theory), but it is dressed as science and IP rather than as a fundable bet.

What she does that the IOF rewards and our materials do not yet:

- Problem in money, stakes, and emotion, quantified, first (incidence, fatality, cost per case, global burden). Ours states a researcher's problem (FDTD is slow). Recast as the buyer's: OEMs face a mandatory per-product regulatory gate and an FDTD loop costing weeks and money per design cycle.
- An explicit ROI slide (hers: "even one avoided surgery saves 12,700 euro"). We have speed multipliers, not euros saved per customer.
- A competitive matrix on buyer axes (accuracy, comfort, price, practicality) ending with her solution winning. Ours compares against academic prior art, not the products buyers pay for (Sim4Life, CST, IXUS, DASY).
- Validation framed as TRL-staged de-risking with hard numbers. We have stronger numbers, framed for patent reduction-to-practice, not TRL.
- A segmented TAM table with adoption assumptions, a business model with break-even, and external market validation.
- A staged valorization roadmap with a market-entry probability lift (hers: ~10-20% to ~40-60%) showing exactly what the IOF de-risks, plus WPs, a Gantt, a broken-down budget, and a go/no-go milestone with criteria.
- Honest "next critical risk-reduction steps" that ARE the funding ask. Our near-field-not-productized gap is exactly this.
- Accessible visuals (stock photos, icons, matrices), and a narrated delivery.

What to do with it:

- The May meeting stays Biondi's: the technical decomposition, claims, enablement, and status he asked for, undiluted. But make the two or three Filip-facing beats Anniek-flavored: the problem in money, the market, and a trajectory slide stating in IOF terms what the summer money de-risks (near-field productization plus FDTD validation) and how it lifts the TRL and success probability.
- The summer IOF deck is a separate, mostly-commercial deliverable on Anniek's skeleton. Most raw material already exists in `honest_analysis.md` (incumbents, TAM, the device wedge, the ZMT path). Assemble: problem-in-money, competitive matrix versus Sim4Life/IXUS/DASY, segmented TAM, SaaS model with break-even, the TRL/probability-lift roadmap, and WP/budget/go-no-go.

## The spine: one narrative, two payloads, three clusters

The same speed plus closed-form plus differentiability is the patent's technical effect and the commercial wedge. The frameworks map onto markets: far-field to networks and academia, near-field to device OEMs, coherent across both. The IDF flowchart (`IDF/flowchart.png`) already draws this and even splits "software platform invention" from "theoretic framework invention," which is two protectable layers. Present Alessandro's clean A/B split, but be ready to name cluster C (the on-device near-field twin) as the commercial spearhead.

## Alessandro's four-beat template

For each framework he asked for: essential steps, how performed, how implemented, development status. Those are independent claims, enablement, and reduction to practice. Build every Framework A and B slide on that spine.

---

## The deck: three layers, tightened

Aim 25 to 30 minutes of talking. Main line about 12 to 14 slides. Everything else lives in the navigable appendix for the discussion.

### Layer 1: orientation (about 4 slides, for everyone)

1. Title. CONFIDENTIAL. Named as a technical briefing for the IP discussion.
2. The problem, viscerally. The `PhantomScene` animation (zoom from whole body to a surface triangle to the skin depth) plus the line "to resolve that, FDTD needs 10^12 cells and weeks of GPU." Answers "what is the problem" in one motion, for Filip and Alessandro both. This is the opener.
3. The one invention, and that it is real. APD(r) = IPD * T_0 * ReLU[n . (-k)] in one line, then the payoff: milliseconds not weeks, differentiable, a deployed product, the market is mmWave device pre-compliance. This is the problem's answer plus the commercial context in one slide, framed as why protection matters, not a pitch.
4. Two frameworks, two markets. The IDF flowchart, relabelled with claim families and customer groups.

### Layer 2: technical depth (Alessandro's zone)

Framework A, geometric / non-coherent (4 slides):
- A1 essential steps, from the IDF essential-elements list, with an essential / variable / implemented strip.
- A2 pseudo-Brewster collapses material to T_0. Use the TAP figure `apd_angle_panel_T.pdf` (and the APD panel), not the old `fresnel_curves.png`. Present as enabling physics, honest about Azzam and the empirical-scalar recovery.
- A3 it is all geometry: APD map, view-factor, Cauchy. Use the censored TAP phantom figures `sab_phantom_visible.pdf` and `eta_phantom_front.pdf`. This is the most persuasive image you have.
- A4 validation and status. Use `fig_kernels_vs_fdtd.pdf`, the Mie panels, and the `lit_waterfall` figure. State plainly: validated far-field against Mie, full-Fresnel phantom (1.2% on total power), Sim4Life FDTD at 5.8 GHz, and 168 volunteers across 5 phantoms.

Framework B, coherent MIMO (3 slides):
- B1 incoherent to coherent, the signal-versus-exposure branch split. Use `presentations/promotors/figures/channel_block_panel_a.png` (the signal-versus-exposure branch split) or the TWC paper setup.
- B2 the exposure operator Q, closed form, no FDTD calibration, Q = J^T M J. The payoff figure is `coherent-exposure-operator/figures/ecbf_pareto.pdf` (4 to 5x absorbed-power reduction at half the MRT signal) and `hotspot_pair.pdf` (MRT versus ECBF body maps).
- B3 the near-field device direction (cluster C). A near-field prototype render (mp4 or screenshot Robin supplies). Present it honestly as a research prototype that demonstrates near-field exposure on a body, the feasibility proof for a device pre-compliance product, not a shipped tool. This is the commercial spearhead and the IOF build target, and possibly its own claim cluster.

### Layer 3: the close (both payloads land)

- C1 claim map. Technical block to IDF claim, independent versus dependent. Draft below.
- C2 development status. The corrected deployed / derived / validated table. Draft below.
- C3 disclosure and timeline. No public disclosure, one internal-only talk, three papers in flight, defense the hard wall.
- C4 valorisation trajectory. Patent now, IOF this summer, spin-off, ZMT and standards. End by asking Filip for his read.

Behind all of it: keep the promotors appendix detail bank, navigable with goto buttons, plus the TWC paper figures, for depth on demand.

---

## Reuse map (best available figures)

Prefer paper figures over the older presentation PNGs. The paper figures are newer, cleaner, and (for the phantom) censored.

| Slide | Best figure | Source | Note |
|---|---|---|---|
| Problem opener | `PhantomScene` (zoom + skin depth) + the 10^12-cells line | `presentations/group/phantom_scene.py`, `slides.py:113` | render to mp4; the visceral "what is the problem" |
| Two frameworks, two markets | `flowchart.png` | `spinoff/patent/IDF/` | already drawn, relabel |
| The method in one figure | `fig:flowchart` tikz | `papers/TAP_paper/paper.tex` | exact-to-whole-body reduction chain |
| Configuration | `fig_geometry.pdf` | TAP `figures/` | clean problem setup |
| A2 pseudo-Brewster | `apd_angle_panel_T.pdf` + `apd_angle_panel_APD.pdf` | TAP `figures/` | supersedes `fresnel_curves.png` |
| A2 frequency validity | `R_of_f.pdf` | TAP `figures/` | crossover 40.4 GHz, conservative below |
| A3 APD + occlusion | `sab_phantom_visible.pdf`, `eta_phantom_front.pdf`, `eta_phantom_side.pdf` | TAP `figures/` | CENSORED, use these not `sab_3d_front.png` |
| A4 vs FDTD | `fig_kernels_vs_fdtd.pdf`, `mie_panel_size/freq.pdf`, `mie_R_sphere.pdf` | TAP `figures/` | latest validation |
| A4 literature match | `lit_waterfall.pdf` / `lit_waterfall_summary.pdf` | TAP `figures/` | 168 volunteers, 5 phantoms, supersedes the old lit table |
| B1 branch diagram | `channel_block_panel_a.png` | `presentations/promotors/figures/` | signal vs exposure branch |
| B2 ECBF payoff | `ecbf_pareto.pdf`, `hotspot_pair.pdf`, `spectrum.pdf` | `papers/coherent-exposure-operator/figures/` | hero results (note: TWC paper pre-submission, some figs not yet in text, present as demonstration) |
| B3 near-field direction | near-field render (Robin supplies) | local asset | prototype, RT-scene demo, not a product |
| Error budget | `error_budget_comprehensive.pdf` | TAP `figures/` | honest accounting |
| Live tool + differentiability | page-8 screenshot + screen recording of the optimizer running (hotspot drops, compliance flips green) | IDF + viewer (adult phantom) | reduction to practice + claims 3/3a, the technical-effect beat |
| Motion | coherent-hotspot mp4 (B); optional geometry-of-absorption mp4 (A); pseudo-Brewster mp4 to appendix | `presentations/group/animations/` | embed as video |

Keep Part II (polarisation, Stokes, sub-6 GHz) in the appendix, not the main line.

---

## The new slides (draft content)

### C1 claim map

```
Framework A (geometric / non-coherent)        Cluster
  Core spatial law ............... Claim 1     A (TAP, deployed+validated)
  Near-field point-source law .... Claim 1a    A (derived only)
  View-factor whole-body ......... Claim 1b    A (derived only)
  Gamma_lm body-response ......... Claim 16a   A (derived only)
  Differentiable optimization .... Claim 3, 3a A (deployed)
  Fast pre-screen for FDTD ....... Claim 17    A
  Embodiments (T0/Tavg/Tbar, AO,
    Stokes, GELU) ................ Claims 6-11 A (dependent)

Framework B (coherent MIMO)
  Exposure operator Q + ECBF ..... Claim 2     B (TWC paper, derived+demo)
  Near-field uplink/device ECBF .. Claim 2a    B (TWC paper extension, derived only)

System / platform
  Base-station compliance system . Claim 4     deployed
  Device pre-compliance system ... Claim 4b    deployed
  On-device body twin (downlink
    pose + live exposure) ........ (new?)      C (near-field prototype, may need its own claims)
```

Tell him: the system claims (4, 4b) are strongest because they bundle novelty with implementation, the near-field/device claims are most valuable because they sit where OEMs pay, pseudo-Brewster is the contestable one, and the on-device twin may be under-claimed today.

### C2 development status (corrected)

```
                                       Derived   Code                  Validated
Far-field geometric (levels 0-6) ..... yes       deployed product      Mie + Fresnel phantom
                                                  (GUI, 2469 tests)     + Sim4Life FDTD @5.8GHz
                                                                        + 168 volunteers/5 phantoms
Coherent Q + ECBF (levels 7-8) ....... yes       in engine             analytic bounds + 28GHz demo;
                                                  (paper unfinished)    coherent FDTD open
Near-field on-device render .......... yes       prototype script      demo on RT scenes only;
                                                  (not a product)       not FDTD; paper unsubmitted
Geometric near-field primitives
  (1a / 1b / 16a) .................... yes       not coded             no
```

The far-field framework is the deliverable: deployed product, GUI, 2469 tests, FDTD-validated at 5.8 GHz. The coherent operator is derived and implemented in the engine, paper unfinished and numbers preliminary, direct coherent FDTD still open. The near-field is research-grade: derived, with a prototype script demonstrated on ray-traced scenes, not a product and not FDTD-validated. The geometric near-field primitives are derived only. Say exactly this. The near-field productization gap is the IOF target, not a thing to hide.

### C3 disclosure and timeline

```
Public disclosure so far:   NONE (one internal-only WAVES talk 26/03/2026; server password-only)
In flight, unpublished:     TAP (near submission), near-field on-device (draft), TWC paper (drafting)
Already published (OLD method, prior art by inventors, not the invention):
                            npj Wireless Tech 2026, IEEE Access 2022, IEEE Access 2025
PhD defense (public):       ~Aug 2026   <- hard EPO deadline
Rule: priority filing must precede the defense and any Early Access / preprint / print,
      coordinated across all three unpublished papers. Confidential peer review is not disclosure.
```

Urgency order: TAP (near submission) is the main disclosure driver. The near-field on-device paper and the TWC paper are unsubmitted drafts with more runway. The defense is the hard wall regardless, and the patent does not wait on any of the three.

### C4 valorisation trajectory

```
  now ........ priority filing (this meeting)   <- before the Aug defense
  summer ..... IOF proposal: POC funding for near-field device validation vs FDTD
  2026/27 .... spin-off (istart), matched validation vs Sim4Life, first OEM / ZMT / lab talks
  parallel ... standards: IEC/IEEE 63195-2 2026 edition, via Wout's committee seat
  The patent decided today is the IP backbone of the summer IOF proposal.
```

End by asking Filip for his read on the valorisation framing.

---

## Talk-track corrections to carry in

- Near-field is derived and prototyped (a research script demonstrated on RT scenes), not a product and not FDTD-validated. Do not overclaim it. Frame the device product as feasible future work and the IOF build target. The near-field on-device work is downlink pose-aware links plus a live exposure reading, not uplink.
- Framework B rests on proved theorems plus the deployed engine (levels 7-8, Q, and ECBF are coded), not on the TWC paper, which is still in progress. The claims are filable from the derivations and the implementation. The paper status only affects the disclosure clock. Treat the coherent numbers (the 4 to 5x reduction, effective rank) as preliminary and illustrative until the experiments are locked, and do not put an unverified headline number on a slide Alessandro might quote to the attorney.
- The on-device body digital twin may be its own invention. Raise it.
- Pseudo-Brewster is enabling physics, not the headline claim.
- Filip is the valorisation owner on this file, so the commercial layer is legitimate meeting content.
- Use the censored phantom figures and an adult phantom for any live view.

## What I read, and did not

Read: signed IDF (18 pages) and IDF source, the TAP far-field paper (structure, abstract, intro, derivation, figures), the coherent TWC paper and the near-field on-device paper (via a thorough digest of structure, figures, status, claim mapping), features.md, both presentation decks and their plans, the patent-decision and honest-analysis strategy notes, and the figures referenced above. Did not read in full: the monograph itself (covered by the two papers), the TAP validation and discussion sections line by line (have the section map and the abstract claims), and the older published papers (they describe the prior method). Point me at any of these if a detail matters.

## One line

Build an invention briefing in Beamer: a short orientation both decision-makers absorb, a four-beat decomposition of the two frameworks Alessandro asked for using the latest paper figures, an honest status table that now credits the implemented near-field work, and a close that proposes the filing scope and ties it to Filip's IOF. Lead with screenshots and one clip, keep the live demo optional, use three surgical animations including a new differentiability one, and be ready for the one-versus-many-filings and novelty questions.
