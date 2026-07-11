# Military / high-power RF for AEGIS: the synthesis

Orchestrator's consolidation of an eleven-agent study, 2026-07-09. The agent reports are in
`agent_reports/`. This is the mother-agent's own read, not a staple of theirs. It disagrees with a
few of them where the evidence made me.

Read `AGENT_BRIEF.md` for the shared ground truth and `agent_reports/00_orchestrator_thermal_note.md`
for the thermal calc I ran myself. Every load-bearing number below traces to a report and a source.

---

## The verdict, in one paragraph

Do not build the company on military RF safety. The physics fit is real but the business is not:
three independent tier-1 kills each remove a load-bearing leg (the operational pain is misattributed
to the wrong hazard, the flagship fielded system is already personnel-safety-certified by the
incumbent method, and a cleared US competitor is three years and ~$1.5M ahead on the exact product
funded by the exact customer). The crown-jewel "certifiable exposure envelope" is not novel IP: it is
the MRI Virtual Observation Point, published 2011, patented by Siemens in 2009, published again for
mmWave arrays by Xu 2018 in AEGIS's own domain, and shipped commercially by ZMT (AEGIS's own first
customer) as the "Q-Matrix toolbox." And the headline "steerable hotspot the standard cannot see"
shrinks, once you run the heat equation, from a 57x scandal to a ~2.6x effect at 28 GHz that Hirata
and Kuster largely already published. **What genuinely survives is a good standards paper, a redrawn
patent, and at most one grant-funded work package.** The company should still be built on the
civilian mmWave pre-compliance wedge Robin's own IOF analysis already identified.

---

## What died, and why (the kills, ranked by how load-bearing)

**1. The operational-tempo pitch rests on a misattributed hazard.** The claim that ships blank radar
during flight ops because of *personnel* exposure, and that shrinking the HERP zone gives back air
defense, is a Gemini paraphrase with no citation, and doctrine points the other way. Flight-quarters
radar restrictions are driven by EMCON (emissions control / not being detected), avionics
interference, and HERO (ordnance on deck). The SPY arrays sit high on the superstructure, far from
deck crew, so deck crew are not even the HERP population for them. If the blanking is not
personnel-driven, Play B has no pain to sell. This is the cheapest kill to settle and the most
decisive: one credentialed naval answer settles it. (Report 07, kill 1.)

**2. The certification gap is already closed by the dumb method.** Epirus Leonidas, the flagship
fielded non-lethal HPM system, already holds HERP + HERF + HERO certification, performed by National
Technical Systems (a physical-measurement EMC house) with no body model and no envelope. Epirus owns
its own "software-controlled safe zones." There is no slot for a third-party body-dosimetry
certificate. The single best AEGIS-shaped pull that report 03 identified is already filled. (Report
07, kill 2; my own verification of Epirus HERP/HERF via Epirus marketing.)

**3. A funded US competitor is years ahead, in a supply chain Robin cannot enter.** AFRL's Bioeffects
Division funded RATE-EM (Stellar Science): a fast ML surrogate for EM bioeffects, explicitly built to
"account for uncertainty." Phase I FA8650-23-P-6472 ($249,957, verified sbir.gov/awards/206951),
Phase II reported ~$1.25M to ~2027. This confirms the pain and willingness-to-pay AND means the buyer
is served and closed. US defense supply-chain entry (ITAR, CAGE, CMMC Level 2 with mandatory
third-party assessment from Nov 2026) is structurally impossible for a two-person foreign entity
except by licensing to a cleared US firm that takes most of the value. (Report 07, kill 3; my own
verification of RATE-EM.)

**4. The body-aware envelope ties the incumbent zone, it does not beat it.** This is the one
calculation nobody had run, and it is the whole business case. At X-band, worst-case-over-all-beams
absorbed power density gives a keep-out radius of 361 m versus the incumbent 369 m: a 2% wash. The
reason is exact and fatal: ICNIRP's reference level already discounts incident power by the skin
coupling factor (T0 = 0.489 ~ the limit ratio 100/185 = 0.54), so the supremum over all beams selects
the best-coupled patch and the body-orientation information that is AEGIS's differentiator gives zero
relief on the worst case. Yaw 0/90/180 are identical. (Report 02, with reproducible code in
`agent_reports/envelope_calc/`.)

**5. The headline physics finding is ~2.6x, not 57x, and mostly already published.** Two independent
thermal calculations (mine, report 00; the deep Pennes solve, report 10) agree: concentrating power
into a diffraction-limited hotspot raises peak skin *temperature* by ~2-2.6x at 28 GHz, not the 57x
electromagnetic peak-to-mean, because peak dT scales as 1/radius (lateral conduction), not 1/area.
The 4 cm2 and 6-minute windows are the thermal averaging scales of skin, chosen on purpose. Worse for
novelty: Hashimoto & Hirata (2017) already prescribed a beam-area compensation factor for small
non-uniform beams from an array, and Neufeld & Kuster (2018) already showed 4 cm2 is not conservative
for focused sources and 6 min is too long for pulsed mmWave. Robin is second, and Hirata is his warm
contact and a likely reviewer. (Reports 00, 10.)

**6. Modeling the body sometimes makes the zone bigger.** Curvature and stratification raise absorbed
density 16-30% near-field; a standing wave against a conducting deck can reach 4x at an antinode. A
tool whose honest output is sometimes "your keep-out zone must grow" cannot make the single-figure
sales pitch. (Report 07, kill 6; report 02, Q3.)

**7. Adjacent kills.** Dismounted-soldier / body-worn RF is dead twice over: all sub-6 GHz (wrong
physics) and single-antenna (no beam, no Q), and the Italian Army already published the Sim4Life FDTD
version in 2025 (report 04). Every HPM flagship (Leonidas L-band, THOR S-band) is sub-6 GHz where the
surface speed does not apply, and the only in-band anti-personnel system is the 95 GHz ADS, owned by
US JNLWD and inaccessible (report 05). MRI pTx, fusion ICRH, accelerators, mmWave scanners, and space
solar power all graded KILL as markets on physics, buyer, or timing (report 09).

---

## What actually survives (in descending order of value)

**A. One good standards paper, co-authored with Hirata.** The genuinely open, fundable object is
narrow and real: the compliance-methodology gap for a *steerable, dynamically reconfigurable* array.
A parked or slowly-repointed coherent beam defeats *both* the static beam-area compensation factor
(Hashimoto) *and* the statistical time-averaged-PRF argument (Thors, Colombi) that the current
mmWave-compliance literature relies on, because those assume either a fixed pattern or a fast scan.
An agile array is neither. And the deep thermal solve found a second live result that corrects my own
note: the gap does NOT self-close above 30 GHz. At 60-95 GHz a *compliant* hotspot can reach the 5 C
injury threshold, because the 1 cm2 averaging backstop cannot resolve a sub-millimetre spot. That is
a citable hole in the standard's own thermal reasoning, in-band for AEGIS's surface method, and it is
exactly Wout's world. Pitch it to Hirata as a co-authored extension of his 2017 framework, framed in
*temperature* not APD-area-ratio, or it dies in review. First check (Wout, one email): is the
agile-array worst case already a work item in the non-public IEC 62232 / IEEE ICES TC95 drafts. That
email decides whether this is a paper or a footnote.

**B. A redrawn patent, filed around the engine not the envelope.** The envelope ("closed-form
exposure operator," worst-case bound) is triply anticipated and must be demoted from anything reading
as independent novelty. What survives as defensible IP is the differentiable, measurement-free,
Fresnel-surface *field-channel* construction G_t in a ray-traced environment: geometry, where MRI and
Xu both start from a solved or measured field. Convert "entries from Fresnel," "without a volumetric
solve," "without measurement," and "differentiable" into hard claim limitations. This is an
obviousness fight, not a clean anticipation defense, and it rests entirely on claims 1-8 holding
against the real non-patent prior art (Kodera, Bamba, Diao, Li). Alessandro must add Eichfelder 2011,
US8,547,097, US8,653,818, US11,940,477, Xu 2018, and ZMT Sim4Life to the IDF prior-art section before
any public disclosure. The one thing that could someday make "certifiable" honest is an unbuilt,
validated, *one-sided* margin on the PO error (AEGIS's lambda_max is currently the exact supremum of
an approximate, two-sided model, so it can under-estimate the true worst case). Its novelty would
live in the conservativeness proof, not the eigenvalue. (Report 01, the sharpest in the study.)

**C. At most one grant-funded work package, not a business.** If a European prime genuinely needs a
body-aware topside component under EDF or EDA and cannot get it from CST-plus-Duke fast enough, AEGIS
could be that component as research revenue. The correct vehicle is VLAIO (dropped its weapons
exclusion April 2025) or EDF via UGent as beneficiary (a new company cannot apply, and IOF policy
will not fund purely-military work). The live disruptive-tech call is EDF-2026-LS-DIS-NT (deadline
29 Sep 2026); Gemini's -STEP call codes were confirmed hallucinated. Nothing is signable before the
3 Aug IOF deadline except possibly a soft academic letter from RMA Brussels. (Report 06.)

---

## The thing Robin is not seeing (and the whole study kept circling)

The military pivot is a smart person's way of avoiding the boring win. Robin's *own* IOF analysis
calls mmWave device pre-compliance against IEC 63195-2 "the biggest wedge, and the one the internal
docs underweight." That wedge has everything defense lacks: a legal mandate, a reachable buyer with
budget, no classified inputs, no clearance, no name collision, and a regulator (FCC/IEC) that already
accepts computed absorbed power density. Every military report in this study ended by pointing back
at it. The reason to keep any military thread alive at all is not the market. It is that the *same*
physics claim and the *same* de-risking experiment serve both.

## The single highest-value action, and it is an experiment not an email

Turn the physics claim into a photograph. Robin's headline finding exists only as JAX output. The
one asset that would make the paper, the redrawn patent, the IOF proposal, and any future standards
or defense conversation real is a thermal image of a coherent 28 GHz beam painting a hotspot on a
phantom, next to the flat map the 4 cm2 metric predicts. It has never been done: the dosimetry
community images single horns, the massive-MIMO community points beams at receivers not phantoms with
an IR camera, and nobody co-runs the two. The hardware is one hour from Ghent (KU Leuven WaveCoRE
28 GHz array, Pollin / Schreurs). Two honesties from my thermal calc: the array must focus in the
near field (first question for Pollin), and at safe power the real spot is a ~2.6x thermal bump, so
drive the *phantom* past human limits to make it visible, never a human. Wout sends the email,
professor to professor, same country, no funding or clearance gate. That experiment de-risks the
civilian beachhead and the standards paper simultaneously, and it is the cheapest ambitious thing in
the entire study.

Do that. Let defense follow the photograph, if it ever does, rather than lead.

---

## Corrections this study made to its own inputs (so they are not re-inherited)

- The "military tier is 5x the civilian tier" claim is wrong; military-controlled == ICNIRP
  occupational, numerically identical (brief section 2).
- AESOP is the Afloat Electromagnetic Spectrum Operations Program, not "Automated Electromagnetic
  System Onboard Ships," and is being replaced by RTSO; neither models a body (report 03).
- The linear cumulative-exposure sum is *correct* for incoherent multi-emitter thermal bounding;
  Gemini's "it ignores coherence" critique is itself wrong (report 03).
- The "450 MW / 20 ns" figure is a vircator spec, not the GaN solid-state Leonidas (report 05).
- The averaging-window gap does NOT self-close above 30 GHz; it re-opens to an injury-threshold
  hazard at 60-95 GHz (report 10 corrects orchestrator note 00).
- Gemini's EDF call codes (-STEP suffix) are hallucinated (report 06).
