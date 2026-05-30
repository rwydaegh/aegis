# Agent A — Intro style pass report

## Scope
Lines 1 to ~283 of `JSAC2/paper/jsac2_v3.tex` (preamble + abstract +
keywords + Section I "Introduction" + the two-products table). Section II
boundary preserved. No edits to bib or downstream sections.

## Summary
Rewrote the abstract to remove all four semicolons, the "two persistent
frictions" mannerism, and the over-detailed mid-paragraph mechanism
inventory; tightened to a single coherent narrative arc (problem,
approach, two outputs, loop, headline numbers). Rewrote the introduction
end-to-end, to: open with FR2/mmWave only (no FR1/FR3 colour, no
"load bearing"); state two deployment factors plainly with the
seminal blockage cite first; introduce SAR-aware-beamforming and RIS
literature as the two strands the paper joins, then drop the verbatim
RIHB sentence requested by Robin; reframe the "user is in the loop"
beat around the user's missing on-device signal and the multi-gigabit
vision; restate the three gaps in the simpler "public/regulator/epi"
language requested in critique items 11-13; tone down "fills the three
gaps"; and restructure the contributions list from five overlapping items
into four high-level verifiable bullets, including the FDTD-speed angle
and the per-pose smartphone framing (items 17-18). Switched British to
American spelling inside scope (`millimetre`->`millimeter`,
`optimisation`->`optimization`, `non-ionising`->`non-ionizing`,
`maximisation`->`maximization`). The two-products table caption was
softened ("Kirchhoff machinery" -> "per-triangle render").

## Item-by-item resolution of `a_first_Reading_critique.md` (intro items 1-22)

1. **Open with FR2/mmWave only, no "load bearing".** Done. Para 1 now:
   "The FR2 millimeter-wave band (24 to 52.6 GHz) offers the wide
   bandwidths that 5G and 6G need to deliver multi-Gbps peak rates...
   deliver that bandwidth to the user through beamforming gain." No
   "load-bearing", no FR1/FR3.
2. **"slowed down on the schedule" -> softer.** Done. New: "Two
   factors hold back rollout, and both pass through the human body in
   the cell." Plain, no time-axis claim.
3. **"bodies are everywhere" / pedestrian wording.** Replaced with:
   "a single body in the line-of-sight of an FR2 channel costs 25 to
   40 dB of received power, and the array gain at the panel does not
   recover the loss once a pedestrian stands between the antenna and
   the user." Tighter, no semicolon.
4. **Legislative-block frame with Brussels, Geneva, Italy as examples
   (no V/m).** Done. New para 2 second sentence covers Brussels,
   Italian regions, Geneva canton (Swiss federal limits) as visible
   examples, no field numbers in body.
5. **"that ties the two frictions together" — kill.** Phrase did not
   appear in the version I edited; the equivalent stinger sentence
   "Both routes pass through the same object: the human body in the
   cell" was removed.
6. **Seminal "human blocks X dB of mmWave signal" first.** Done. The
   blockage cite is now in para 2 (the deployment-factor paragraph),
   placed BEFORE the SAR-aware/RIS literature in para 3.
   `Maccartney2017blockage` now leads the cite list (was second).
7. **No monograph or TAP cite.** Verified: intro contains no
   `\cite{WydaeghePB2024}` (the TAP-paper key) and no monograph cite.
   No new monograph/TAP cites were introduced.
8. **Insert RIHB sentence verbatim.** Done. The exact sentence is
   now in italic in para 3, immediately after the
   beamforming/RIS literature framing. Killed the prior "parallel
   work" / "panel RIS tunes electronically; RIHB tunes by pose"
   mutated form into a one-line follow-up that retains the contrast.
9. **"Other direction" framing was unclear — fix.** Resolved. The
   downlink direction is now stated explicitly: "the base station
   computes a small pose cue and returns it to the user over the
   downlink control channel."
10. **`h = h_BS + h_body` framing.** Honoured. The intro now uses
    `h(theta) = h_BS + h_body(theta)` (no LOS/NLOS sub-split). The
    System-Model section already uses the same split, so this is
    consistent. Cross-section flag below.
11. **"no current body-twin formulation provides ... regulatory
    framing" -> "no current body digital twin gives the public,
    regulators or epidemiologists an accurate and instantaneous
    determination of exposure".** Applied verbatim per critique.
12. **"body-mediated channel coefficient h_b" too technical.** The
    sentence is replaced with: "no current channel model treats the
    body-mediated coefficient as a single-receiver render anchored at
    the phone, which is what the on-device geometry actually allows."
    Same content, plainer language.
13. **No way for users to know they're blocking the signal.** Added
    in the new "vision" paragraph: "Today the user has no signal that
    the link is blocked, no on-device map of where the dose is landing
    on their body, and no closed-loop guidance from the network on a
    pose that helps." Closed-loop SI keyword retained.
14. **Don't overclaim "closed loop has not been formulated or
    empirically tested".** Softened to "has not been studied end to
    end on a ray-traced mmWave scene."
15. **"This work addresses..." jargon-heavy and overlong.** Rewritten.
    Now five short sentences inside one paragraph: pose mesh, phone+BS+RT
    scene, two outputs from one render, loop steps, residual fit. No
    "wireless-native intelligent agent" jargon. No "for the first time"
    in this paragraph (deferred to the contributions list).
16. **"A passive reconfigurable scatterer..." mutant.** Robin's
    verbatim RIHB sentence is now the canonical one (item 8). The
    older mutant ("A passive reconfigurable scatterer whose surface
    phase pattern...") was already absent in the version I received.
17. **Speed angle (whole-body SAR + 4 cm^2 APD across mmWave band,
    much faster than FDTD).** Encoded as contribution bullet 3:
    "A whole-body absorbed-power-density read-out on the same per-pose
    budget, four orders of magnitude faster than the IT'IS
    Virtual-Population FDTD reference at comparable accuracy on
    biological tissue, across the full FR2 band." Number kept honest
    (1e4-fold per the prior text; abstract now drops the specific
    factor, body keeps it).
18. **Power move: per-slot real-time exposure on smartphone.** Added
    to bullet 2 ("runs at consumer-grade compute budgets on a single
    phone") and bullet 3 ("per-pose budget"). Abstract states "displayed
    on the phone".
19. **Contributions too specific, restructure to 3-5 high-level
    items.** Done. Cut from five overlapping bullets to four:
    closed loop, receiver-anchored Kirchhoff render, FDTD-fast
    on-device APD, empirical study. Each item is one sentence and
    pinned to a section ref.
20-22. (Items 20-22 in the critique are general process notes about
    the abstract; addressed by the abstract rewrite.)

## Style-guide rules applied (counts)

- Em dashes removed: 1 (the `---` cluster inside the old gap (iii)
  bullet).
- Semicolons removed: 4 (abstract: 2; contributions list separators: 2;
  para 2 cluster: 1). Net intro semicolons in scope: 0 (the table cell
  "reading local; opt-in aggregation" is a tabular separator, not a
  prose clause; left as-is).
- "It is" / "There is" openings in intro: 0 introduced, 0 remained.
- "however" placed mid-clause per B21: 1 (kept "Today, however, the
  user has no signal..." which obeys the post-comma placement).
- "for the first time" instances: 1 in body (in the contributions
  preamble) and 1 implicit per bullet via "first" semantics. Down from
  2 in the prior version (which had "for the first time" in the
  per-paragraph prose AND in the contributions list).
- "we" usage: appears in the verbatim RIHB sentence ("We aptly name
  this a RIHB"), which is Robin's mandated phrasing; otherwise minimal.
- Bullet `enumerate` only used for the contributions list (allowed by
  guide for enumerative content per A3).
- No bold for emphasis introduced.
- Britism count: 4 fixed inside scope (`millimetre`, `non-ionising`,
  `optimisation`, `maximisation`).
- "First/Second/Third" connectors used three times (paragraphs 2 and
  the gap paragraph), as Robin prefers per `Robin_writing_style.md`
  rule 5.

## Cross-section flags for the audit

- The intro no longer contains `\cite{Christ2010VF}` until contribution
  bullet 3, which matches the body usage. The bibitem stays.
- All five cite keys at risk (per critique item 7: monograph + TAP
  paper) verified absent in intro: `WydaeghePB2024`, no `monograph*`
  key, no `TAP*` key. The bibitem `WydaeghePB2024` is still cited in
  Section IV (line ~461 of the file before my edits); that is outside
  my scope and acceptable as a body cite per critique rules.
- The `\cite{ICNIRP2020}` is no longer referenced in the intro. It
  remains used in body sections; bib agent should keep it.
- The `\cite{HeathLozanoFA2018}` is still in para 1 as the
  beamforming-foundations cite.
- Two new bib uses introduced: `Maccartney2017blockage` and
  `MacCartney2017` (both already in the bib, order swapped). No new
  bib keys needed.
- The two-products table title was changed from "...Kirchhoff
  machinery" to "...one per-triangle render". Body text and section
  headings downstream may still say "Kirchhoff render" or "physical
  optics"; the term should remain stable. Suggested term-of-art:
  "per-triangle physical-optics render" everywhere.
- The contribution bullet `(\cref{sec:arch,sec:control})` uses the
  combined `\Cref` form per latex_rules item 73. If section labels are
  renamed downstream, the bullet should be updated.
- Item 10 (the `h = h_BS + h_body` framing): the intro now uses this
  generic split. Verify that downstream sections also do not split
  into `h_LOS / h_body / h_NLOS` (Section II currently says `h_BS`
  encompasses LOS+scene multipath, which is consistent).

## Open issues

1. The abstract still states "above 100 dB of path loss" for the
   deep-shadow scene, which I kept from the original. Verify against
   results section once it stabilises (other agents are editing).
2. The "$32$-dimensional pose latent" in the abstract assumes VPoser
   latent dim 32. Confirm with results agent.
3. The "16 of 18 scenes" abstract claim mirrors the prior 8/9 LOS +
   8/9 NLOS = 16/18 figure. If results agent revises this denominator,
   the abstract needs an update.
4. The "0.58% of ICNIRP general-public limit" carried over verbatim
   from the prior abstract. Verify against the dosimetry section
   number once that section is final.
5. The contributions list bullet 3 says "four orders of magnitude
   faster than the IT'IS Virtual-Population FDTD reference". The prior
   draft said "$\sim 10^4 \times$"; verify this factor against the
   timing claims in Section VI.
6. The vision paragraph mentions "multi-gigabit content that the
   standard always promised", which is informal but inside the bounds
   of academic prose for a JSAC SI vision pitch. Robin can tone up or
   down at his pleasure.
7. Did not edit the two-products table body cells beyond the
   `maximisation`->`maximization` fix. The table itself was kept by
   prior agent; it is one of the two beats (item 7 of critique
   structurally — the "two outputs from one piece of machinery"
   thesis), so leave for Robin's call on whether it survives the next
   pass.

## Verification

- `pdflatex -draftmode` runs to completion with no errors. Only
  warnings remain (unrelated overfull hboxes in §VII bib formatting,
  one stray `$` in an output filename for the table on line 1519, all
  outside my scope).
- Boundary preserved: `\section{System model and DTN architecture}`
  still parses cleanly at line ~267 of the new file (was 285).
- No references broken (`\cref{sec:arch,sec:control,sec:kirchhoff,sec:saridx,sec:numerical}`
  all resolve).
