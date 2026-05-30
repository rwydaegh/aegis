# Agent N — SI back sections (Strict visibility, Fabry-Pérot, Failure-mode, Compliance, Bibliography)

File: `JSAC2/paper/jsac2_v3_supp.tex`
Scope: section "Strict visibility variant for fingertip features" through end of file (sections SI-9 through SI-12 plus the SI bibliography).

## Summary

Aggressive sentence-level pass. Tightened cross-references, replaced semicolons with periods or commas (Robin's rule 2), restored notation consistency ($M_\mathrm{tri,*}$ throughout instead of drifting to $T$/$T_\mathrm{vis}$), corrected a quantitative claim that misstated headroom by three orders of magnitude, fixed Unicode é to LaTeX-escaped `\'{e}` and the Fabry hyphen to an en-dash to align with the main paper, and rebuilt the bibliography to IEEE house style with proper first-appearance ordering. Final compile is clean (only the harmless `Token not allowed in PDF string` warnings from math symbols in section titles, which are unavoidable with hyperref bookmarks).

## Edit list (found from the style docs)

1. **Wordy section reference** (Strict visibility lead): "Section~IV (UE-anchored Kirchhoff render) of the main paper" → "Section~IV of the main paper". Same fix for "Section~VII (Pose-differentiable rate and HITL control) of the main paper" → "Section~VII of the main paper". Robin §2/§B6 omit needless words; the parenthetical title duplicates what the reader gets by following the cross-reference.

2. **Semicolons → periods or commas** (Robin §2 "Never `;`"):
   - "FR2 mesh resolution; it under-counts" → period.
   - "back-face default; the strict variant" → period.
   - "centred at each surface vertex; the peak" → comma + "and".
   - "Larger FD step; more probe averages" (table cell) → comma.

3. **Notation drift fixed** (style guide §C10 one term, one meaning): the "Cost factor" paragraph was switching from $M_\mathrm{tri,total}/M_\mathrm{tri,vis}$ to $T = 20\,908$ / $T_\mathrm{vis} \approx 4\,000$. Replaced $T$ with $M_\mathrm{tri,total}$, $T_\mathrm{vis}$ with $M_\mathrm{tri,vis}$. Dropped "with roughly … $\approx$" double-hedge.

4. **Indicator-function notation in eq:V-strict** rewritten from `$\bigl[\,\text{...}\bigr]$` (ad-hoc bracketed prose, also overfull by 19.7~pt) to `$\mathbf{1}\bigl\{\text{no $t' \neq t$ blocks $\bm{c}_t \to \bm{r}_\mathrm{BS}^{(n)}$}\bigr\}$` (standard indicator). Resolves the overfull box and is clearer.

5. **Fabry-Pérot consistency with main paper** (latex_rules §10): `Fabry-Pérot` (hyphen + Unicode é) → `Fabry--P\'{e}rot` (en-dash + escaped accent). The main paper uses the latter form.

6. **Layered FP paragraph rewrite** for tighter prose: "are second-order in this spread" path; "introduces oscillations of $\pm 30\,\%$" → "$\pm 30\%$" (rule 72: no thin space before `%` in IEEE house style); "$\sim 10\,$GHz" → "${\sim}10\,$GHz" for tight binding; "$28$~GHz" inline → "$28\,$GHz" for unit-spacing consistency with the rest of the paragraph; replaced "is to replace" → "replaces" (active, fewer words); "(skin/fat/muscle)" → "(skin, fat, and muscle)" (slash list reads as informal).

7. **Failure-mode taxonomy lead** rewritten: "distinguishable from the iterate trace alone" was a dangling adjectival clause attached to "categories" → made it a finite clause "and the iterate trace alone distinguishes them". Tightened "the corresponding mitigation" (column header redundancy) to just "the mitigation".

8. **Closing paragraph of failure-mode taxonomy** restructured: the four-clause comma list ended with one clause structurally different from the first three ("the IMU-floor mode sets the operating envelope"). Split into two sentences: three independent mitigations as a parallel triplet, then the IMU-floor mode framed correctly as the operating envelope itself.

9. **Quantitative correction in compliance metrics** (wout_pet_peeves §11 numerical precision): the SI claimed whole-body SAR is "six orders of magnitude below the limit", but $0.08 / 1.2 \times 10^{-4} = 666 \approx 10^{2.8}$. Corrected to "more than two orders of magnitude below the limit". This is consistent with the main paper's "two orders of magnitude" language for the related peak-local APD claim. **Cross-section flag**: please verify the numerical value $\leq 1.2 \times 10^{-4}\,$W/kg against the simulation; if it is wrong rather than the wording, the fix needs to apply at the source.

10. **Compliance metrics rewordings**:
    - "ICNIRP 2020 general-public limit:" → "The ICNIRP 2020 general-public limit is" (avoid colon-headline style; subject-verb sentence is cleaner).
    - "averaged over $30\,$min over $10\,$g" → "averaged over $10\,$g of contiguous tissue and a $30\,$min time window" (the duplicated "over" was ambiguous about which axis the average was on).
    - "ICNIRP 2020 ${\geq}\,6\,$GHz general-public limit" → "The ICNIRP 2020 general-public limit above $6\,$GHz is …" (the `${\geq}\,$` rendering was awkward; "above $6\,$GHz" is the standard ICNIRP wording).
    - "$0.58\,\%$" → "$0.58\%$" (rule 72).
    - "actionable user-facing telemetry" → "the per-user dose that the regulatory framework specifies but does not measure directly" (style §A5/§C8: removed AI puffery; replaced with the substantive content the main paper already uses in Section~VIII).

## Bibliography actions

The SI cited four references inline (`BornWolf`, `Pavlakos2019VPoser`, `AMASS2019`, `Madgwick2011`). All four are still referenced after the prose pass; none was pruned.

Reformatted all four entries to IEEE house style:
- Full author lists (no bare "et~al." when the author count is small enough to spell out).
- Sentence-case paper titles, italic abbreviated venue names with proper IEEE abbreviations: `Proc.\ IEEE/CVF Int.\ Conf.\ Comput.\ Vis.\ (ICCV)`, `Proc.\ IEEE Int.\ Conf.\ Rehabil.\ Robot.\ (ICORR)`.
- City, country, abbreviated month, year, page range with en-dash (`pp.~5442--5451`, `pp.~10\,975--10\,985`, `pp.~1--7`).
- Non-breaking ties on initials (`F.~Lastname`), `7th~ed.`, `Univ.\ Press`.
- **Reordered** to first-appearance order in the body (rule 13): BornWolf [190] → Pavlakos2019VPoser [289] → AMASS2019 [300] → Madgwick2011 [404]. Previously the order was Pavlakos, AMASS, BornWolf, Madgwick.
- **Author correction**: VPoser previously credited to "G.~Pavlakos et al." with a generic "companion software release, MPI-IS, 2019" stub. The main paper attributes VPoser to N.~Ghorbani et al. (the GitHub release credits Ghorbani as primary), reserving the Pavlakos CVPR paper for SMPL-X under a different bibkey. I aligned the SI to match the main paper's attribution and added the standard MPI-IS software-release form with a `\url{}` to the public repository. Bibkey kept as `Pavlakos2019VPoser` to avoid breaking inline `\cite` calls outside my scope.

## Fix counts

- Sentence-level prose edits: 10 (ranging from one-word fixes to full-paragraph restructures).
- Semicolon removals: 4.
- Unicode-to-LaTeX accent fixes: 2 (section heading + body, Fabry--P\'{e}rot).
- Hyphen-to-en-dash fixes for compound name: 2 (same locations).
- Notation-consistency fixes: 1 ($T \to M_\mathrm{tri,*}$, two occurrences).
- Quantitative correction: 1 (orders-of-magnitude claim).
- IEEE-format bibliography entries: 4 (all entries rewritten and reordered).
- Overfull hbox eliminated: 1 (eq:V-strict, was 19.7~pt overfull).
- Overfull hbox eliminated in table: 1 (failure-mode table, was 51.7~pt overfull; column spec changed from `llll` to `l p{0.30\textwidth} p{0.27\textwidth} p{0.25\textwidth}`).

## Cross-section flags

- **Quantitative claim worth a sanity check**: I changed "six orders of magnitude" to "more than two orders of magnitude" because $0.08\,\text{W/kg} / 1.2 \times 10^{-4}\,\text{W/kg} = 666 \approx 10^{2.8}$. If the underlying number $1.2 \times 10^{-4}\,$W/kg is itself wrong (e.g. should be $1.2 \times 10^{-7}$ or similar), the fix should be on the number, not the words. Worth verifying against the simulation output.

- **Bibkey naming inconsistency**: the bibkey `Pavlakos2019VPoser` is now misleading because the entry is a Ghorbani et al. software release, not a Pavlakos paper. Out of scope to rename (would touch every `\cite{Pavlakos2019VPoser}` callsite in this file and would diverge from the main paper, which uses the same misleading key). Flagged for the next paper-wide pass.

- **Percent-spacing inconsistency across the file**: my scope now uses `0.58\%` and `\pm 30\%` (no thin space, per IEEE house style). Other parts of the SI mix `\,\%` and `\%`. Out of scope for me; flag for an editor sweep.

## Open issues

- The failure-mode table (`table*` environment) floats to its own page at the end of page 6 because of `[!t]` placement and the table-star + footnotesize configuration. Visually acceptable for a supplementary information document, but a perfectionist could move the table caption text above the rule and tighten further. Left as is.

- Three minor underfull hboxes inside the failure-mode table (badness 10000 once, 2300+ twice) are inherent to the new `p{}` column layout (short cells underfill the wrapped column width). Cosmetic only and not visible in the rendered PDF.

## Final compile status

`pdflatex jsac2_v3_supp.tex` (twice) produces a 6-page clean PDF. No `Citation undefined`, no `Reference undefined`, no `??` markers, no overfull boxes outside the unrelated lines 130--135 and 477--485 (out of scope). The hyperref-PDF-string warnings on math symbols in section titles are inherent and harmless.

PDF: `JSAC2/paper/jsac2_v3_supp.pdf` (598661 bytes, 6 pages).
