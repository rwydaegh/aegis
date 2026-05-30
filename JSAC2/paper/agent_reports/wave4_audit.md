# Wave 4: Audit and cross-cutting fixes

Final v3 state after 14 style-pass agents (10 main + 4 SI) and a coordinator audit.

## Compile

- `jsac2_v3.pdf`: 14 pages, 3.0 MB. Zero undefined references, zero never-used bibitems.
- `jsac2_v3_supp.pdf`: 6 pages, 585 KB. Zero undefined refs.

## Cross-cutting fixes applied in Wave 4

1. **TAP self-cite removed.** Dropped `\cite{WydaeghePB2024}` at body line 463 (§III.B pseudo-Brewster collapse) and pruned the `\bibitem{WydaeghePB2024}`. The prose now claims the naming directly without citation. Bibitem count: 34 → 33.
2. **AMASS expanded on first use.** §VI.B: "the AMASS motion-capture corpus" → "the Archive of Motion Capture as Surface Shapes (AMASS) corpus".
3. **`\cref{prop:approx1}` rendering.** Changed `\crefname{proposition}{Proposition}{Propositions}` → `{Approximation}{Approximations}` so refs read "Approximation 1" rather than "Proposition 1" (per Agent C's flag and main-paper title convention).
4. **`dA` → `\mathrm{d}A`** in two locations (main line 1236, SI line 429) for differential-symbol consistency.
5. **SI percent spacing** harmonised to IEEE house style: 13 occurrences of `\,\%` → `\%`.
6. **British/American spelling** harmonised to British (project habit, Agent A had introduced 9 American forms in the abstract/intro). Bibitem titles preserving "millimeter" / "Beamformer optimization" left as the original published titles.
7. **Prose semicolons.** Per Robin's "never `;`" rule: 15 prose semicolons in the main body and 4 in the SI converted to period + capitalised next word. Remaining `;` are in math (`\;`), proposition optional-argument titles (`[Title; Approximation~1]`), enumerator parentheticals, table cells, and verbatim cited titles (TS38214 standard name).
8. **NLOS-prose semicolon** at §VII setup line 966 fixed (broke a long sentence into two).

## Regression check (v2 critique items still intact)

- **RIHB sentence** in intro: present at line 190 verbatim from the critique.
- **Manually-picked 18 RXs** framing in §VII.B Setup: present at line 963 with explicit "manually selected" + 9 LOS / 9 NLOS + bbox (-69 to 136 m × -27 to 159 m).
- **Honest peak-APD framing** in §X live-SAR + SI §S7 reference: present at lines 1213-1226 (whole-body P_abs reportable; peak-local NOT reportable per-tick).
- **Zero monograph / TAP cites in intro**: verified.
- **Fig 3 Kirchhoff schematic**: untouched.

## Open issues for Robin to decide (math substance, not style)

1. **`β_n` overloaded.** Used as per-path complex amplitude (§IV.A line 492, line 653) AND as per-path in-tissue phase rate (§III.D lines 525-535; appendix lines 1449-1507). Renaming one needs paper-wide coordination. Suggested: rename the per-path amplitude to something like `c_n` or `α_n^{\mathrm{path}}` (collides less since `α_n` is already attenuation rate). Defer to Robin.
2. **`Pavlakos2019VPoser` bibkey** is misleading — the entry is now Ghorbani et al. (the correct VPoser authors per Agent N's fix). Renaming the bibkey requires sweeping the body cites; left as-is.
3. **Section title "Live SAR reading…"** — the section reports whole-body integrated `P_abs`, not local SAR. Agent H flagged but left untouched per scope. Robin to decide if rename is wanted.
4. **CLUEH2025 cite** is a real Horizon Europe project URL; not a placeholder.
5. **`fig2_svd_spectrum.pdf`** stale filename inside SI (Agent M flag) — figure source path needs verification.
6. **Some bibitems still use `et~al.`** where author count may be ≤6 (Agent J flag). Cosmetic; not blocking.
7. **The DTN flowchart figure** (Fig 1) needs a visual iteration: white label boxes covering arrows, `K_99` mode label opaque, `J` not visibly tied to RT box. Agent B flagged. Out of text-agent scope.

## What Robin specifically asked to verify

- **Did agents do a real broad style sweep beyond the prompt's listed items?** Sampled the abstract+intro v2→v3 diff (lines 117-260): yes. Beyond the 22 items I listed, Agent A also (a) replaced "Two persistent frictions" → "Two factors hold back" (drier), (b) killed "central new primitive" stinger, (c) restructured the contribution paragraph from i/ii/iii bullet emphasis to flowing prose, (d) tightened the cohort-side framing, (e) cleaned multiple `optimisation` / `polarisation` to British where they had drifted to American (then I re-harmonised paper-wide).
- **Did agents misinterpret the first-reading critique and regress correct work?** Spot-checked the RIHB sentence, manually-picked RX framing, peak-APD honest caveat, and intro cite list. All intact.

## Aggregate change stats

- Lines changed v2→v3 main: 1838 changed (1687 → 1743 lines, +56 net).
- Bibitems: 34 → 33 (one TAP self-cite pruned).
- Subsection headings de-`The`-prefixed: 8 (across §III, §IV, §V, §VI, §VIII, appendix C).
- Em-dashes in body: 0 remaining.
- Prose semicolons: removed 19 (15 main + 4 SI).
- Mic-drop stinger sentences killed: ~6 (across agents D, F, G, H, I, M).
- Anthropomorphisms fixed: ~10 (across agents B, C, F, G, H).
- SI table values + honesty framing preserved: confirmed.
