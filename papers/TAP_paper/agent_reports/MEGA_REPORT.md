# Mega report — TAP paper style polish (waves 1 + 2)

Built from a full read of all 22 individual reports under `agent_reports/`. Compact per-point digest; ranked by edit volume.

## Tally

| Edit class | Count | Where |
|---|---|---|
| Numeric ranges → en-dash (`X to Y` → `X--Y`) | ~70 | abstract, intro, pseudo-Brewster, whole-body, validation, corrections, compliance, discussion, SI |
| Section / subsection / subsubsection titles → sentence case | 33 | every section + 19 in SI |
| Equation-end punctuation `\, .` / `\, ,` inside the equation | 36 | local-law (6), pseudo-Brewster (2), whole-body (3), corrections (2), compliance (4), validation, SI (18) |
| Unit attachment `$X\,$UNIT` → `X~UNIT` | ~80 | abstract, intro, pseudo-Brewster, whole-body, validation, SI |
| `approx.\` in prose → "approximately" | 6 | whole-body (2), SI (4) — `\paragraph{}` heads kept |
| Cross-section / one-idea paragraph splits | 3 | corrections (1), validation (1), discussion (1 spacing) |
| Result-then-reason restructures | 6 | validation (1 Mie, 1 Fresnel post-table), discussion (5 boundary paragraphs) |
| `\textit{}` first-use on freshly defined terms | 3 | "pseudo-Brewster angle", "geometric absorption law", "exposure fraction" |
| `\mathrm{}` wraps on noun-like subscripts | 4 | `\theta_B`/`\theta_{pB}`, SI Mie underbrace `\text{Fresnel}`/`\text{diffraction}` |
| Bibliography fixes | 5 | `\quad` removals (×6), Zhukov page range, two arXiv normalizations, Hirata title-case |
| Glossaries package | removed | preamble + body refs hand-spelled |

## Per-range edits

### Preamble + abstract (lines 1–150)

**Wave 1.** 12 unit conversions in the abstract (`$1$ to $100\,$GHz` → `1 to 100~GHz`, `$28\,$GHz` → `28~GHz`, etc.); 2 percent-sign demotions (`$5.6\%$` → `5.6\%`, `$0.35\%$` → `0.35\%`); 2 plain-integer demotions (`$168$` → `168`, `$5$` → `5`); 2 mid-clause source line breaks reflowed.
Flag: hyperref all-blue colors (preprint OK; flip to false for IEEE TAP final). `$1.012$` kept in math mode as a precise dimensionless ratio.

**Wave 2.** 4 numeric ranges → en-dash (`1--100~GHz` body, `0°--75°`, `from 1--100~GHz`, `from 6--100~GHz`); **`\newacronym{relu}`/`\newacronym{gelu}` and `\usepackage{glossaries}`/`\makeglossaries` all removed** after grep verified zero remaining users; body refs at lines 1435–1437 hand-spelled to "Rectified Linear Unit (ReLU)" and "Gaussian Error Linear Unit (GeLU)" to keep file compiling. All 19 custom math macros verified used.
Open: title `from 1 to 100\,GHz` left as-is (IEEE title typography). "from 1--100~GHz" reads slightly awkward; alternatives "across" / "over".

### Introduction (152–~398)

**Wave 1.** `\begin{itemize}` → `\begin{enumerate}` for the novelty list; ~16 `$X\,$GHz` → `X~GHz` conversions through prose, captions, and flowchart; ICNIRP spelled out at first caption use; `Sub-$6\,$GHz behavior` → `Below 6~GHz, behavior`. Left `$1.45$ to $5.8\,$GHz` (decimal range) and the TikZ node label `Sub-5\,GHz` (tight figure label) intentionally.
Flag: Bamba2014 cite-key vs entry-year mismatch (key 2014, entry Feb 2013).

**Wave 2.** 6 ranges → en-dash (Bamba `0.50--0.56` across `1.45--5.8~GHz`; Flintoft `7--11~GHz`; Zhang `0.45--0.65`; Kodera `10--100~GHz`; summary `1--100~GHz` ×2; `6--100~GHz`); `divide by ..., to obtain a normalized cross-section` → `..., yielding a ...` (verb register); `However,` added at literature-survey → gap-statement pivot.
Open: `approx.\ $10^{8}$` and `approx.\ $10^{12}$` borderline (paragraph 1) — leave or expand.
Out-of-scope: line 1190 (validation table) and line 877 (whole-body) still had "to" ranges — caught by their range agents.

### Local absorption law (399–509)

**Wave 1.** Six numbered display equations all gained `\, .`/`\, ,` inside `\end{equation}` (eq:Sab-pol, rs-rp, T0, Teff, Teff-decomp, Sab-Tavg). eq:Sab-exact already correct (`}\,.`). No anti-patterns found. Subsection titles deliberately left in title case in wave 1 for paper-wide consistency.

**Wave 2.** Section title and 4 subsection titles → sentence case (caught up to the rest of the paper); `$28\,$GHz` ×7 → `28~GHz`; `$25.8\,$S/m` → `$25.8$~S/m`. All other long-tail checks passed; the three inline glosses ("unpolarized baseline", "polarization splitting", "local TM excess") are descriptive names for math symbols, not coined jargon — no `\textit{}` warranted.

### Pseudo-Brewster compensation (510–739)

**Wave 1.** Section + 4 subsection titles → sentence case; "towards" → "toward"; `$28\,$GHz` ×7, `$40.4\,$GHz` ×2, `$100\,$GHz` ×3 → tilde form; `$0.3$ to 100~GHz` → `$0.3$--100~GHz` (body + caption); eq:R-of-f added `\, ,` inside; eq:geom-law boxed-equation punctuation restructured to `}` / `\, .` / `\end{equation}`; passive "The application of the criterion..." → "This connection between the Azzam criterion..."; "Hence," connective added before the Geometric absorption law error-bound paragraph.
Open: `\boxed{}` punctuation convention; `$|\ntilde| > 2.5$` empirical extension lacks citation.

**Wave 2.** 2 more ranges → en-dash (`$T_0 \approx 0.5$--$0.6$`, `$70$--$75^\circ$`); `\theta_B` → `\theta_{\mathrm{B}}` and `\theta_{pB}` → `\theta_{\mathrm{pB}}` (Mechanism subsection); `\textit{pseudo-Brewster angle}` italicized at first formal definition; `\textit{geometric absorption law}` italicized when first introduced in body prose; the uncited `$|\ntilde| > 2.5$` claim hedged as "Empirically, the near-constancy extends to..."; figure caption R_of_f rewritten from finding-in-caption to descriptive (axes, R<1/R>1 meaning, dashed lines marking ±4%); `$\Sinc = 1\,$W/m$^2$` → `$\Sinc = 1$~W/m$^2$`.
Open: "fourth significant figure" wording overstates a 0.2% deviation. `T_s`, `T_p` polarization subscripts — paper-wide decision needed (parallel to Brewster fix). Mechanism paragraph 2 ("Azzam showed...") inverts result-then-reason; defensible as theory section.

### Whole-body absorbed power (740–943)

**Wave 1.** Section + 3 subsection titles → sentence case; eq:eta-def, eq:cauchy, eq:T-lay each gained `\, .`/`\, ,` inside; `, ~\cite[Table~6]{Flintoft2014}` → `,~\cite[...]{...}` (stray space).
Flag: `\label{def:eta}` inside `remark` env semantically odd (deferred to wave 2 to verify safety).

**Wave 2.** `\label{def:eta}` → `\label{rem:eta}` (grep confirmed zero `\cref{def:eta}`/`\ref{def:eta}` users); `\textit{exposure fraction}` italicized at first introduction in the remark; 9 ranges → en-dash (`0.75--0.85`, `0.3--100~GHz` ×2, `5\%--10\%` across `1.45--5.8~GHz`, `0.47--0.49` at `7--11~GHz`, `0.45--0.65`, `7--11~GHz`, `2--20~mm`); 2 `approx.\` → "approximately" on the opacity-condition line.
Open: `[0.75, 0.85]` interval-set notation coexists with `0.75--0.85` two lines earlier; both reference Flintoft band. Confirm.

### Validation (944–1223)

**Wave 1.** Subject-verb fix ("literature ... tests" → "test"); ~30 `$X\,$UNIT` → `$X$~UNIT` across body, subfig captions, main captions, table rows, discussion paragraphs (2/5/60/0.45–5.8/1/4/39/28/7/5.8/100/12/11/18/10–100/3/9 GHz; 48.12/47.95 mW; 0.185/0.186/0.539 W/m²; 105.9 mW; 10 W/m²; 4 cm²); `IEC/IEEE\,$63195` → `IEC/IEEE~63195`; 4 subsection titles → sentence case; Mie paragraph result-then-reason restructure ("Fingers at sub-mmWave frequencies are the worst case, with errors above 30%" → "For fingers at sub-mmWave frequencies, errors exceed 30%."); Combined dosimetry literature paragraph topic-first (`\Cref{fig:waterfall} compares…`); Fresnel post-table topic sentence (`\Cref{tab:phantom} reports total absorbed power, mean, and peak $\Sab$.`) with 0.35% pulled to second sentence; awkward "second\nis" line-break fixed → "second metric\nis".

**Wave 2.** 20+ ranges → en-dash (Setup `0.45--5.8~GHz`, `1--4~mm`; Mie `3--14\%`; FDTD `0.45--5.8~GHz` body+caption; literature `5\%--10\%`; waterfall caption 7 ranges; tab:waterfall 12 cells across Flintoft/Bamba/Zhang/Kodera rows; Kodera paragraph `Models I--IV` and `1--100~GHz`); `Kodera et~al.` × 2 → `Kodera \textit{et~al.}`; FDTD subsection paragraph split (IEC/IEEE 63195 vs Cauchy each in own paragraph); "is informative" → "is expected:" with colon-then-mechanism (Bamba paragraph); closing `}` repaired on waterfall caption after a Python batch sed dropped it.
Open: short FDTD closing paragraph nearly duplicates the figure caption — fold or expand. Flintoft `slope` row has no `\cite{}` — likely intentional (same paper as plateau row).

### Higher-order corrections (1224–1348)

**Wave 1.** Section + 3 subsection titles → sentence case (Curvature already single-word); inter-body reflections paragraph split at "Two effects keep the body-averaged correction small."; "First, … Second, …" connectives added in inter-body subsection (subject-verb-mechanism parallel structure replacing weak "The bound...Specular reflection..."); line-wrap fixes in diffraction and inter-body paragraphs.
Open: tab:curv-mag column header `$R$\,[mm]` uses `\,[mm]` notation; IEEE TAP slightly prefers `(mm)`. Error budget is a figure not a table — author may want a tabular summary for reviewers. `\pospart{}` macro renders correctly.
Out-of-scope: `\section{Compliance and Corollaries}` "Corollaries" needs downcasing (caught by COMPLIANCE).

**Wave 2.** eq:curv-update added `\,` before its trailing comma; eq:gelu added `\,` before its trailing comma; `which is the GELU function` → `which is the Gaussian Error Linear Unit (GELU) function` at first prose mention (line 1278).
Open: GELU vs GeLU casing (line 1278 uses GELU all-caps; old line 1437 used GeLU mixed-case — but PREAMBLE_ABSTRACT_W2 already replaced the line 1437 spell-out with `Gaussian Error Linear Unit (GeLU)`, so a casing decision is needed). Stale preamble comment about glossaries (now moot since the package was removed).

### Compliance and corollaries (1349–1547)

**Wave 1.** Section + 3 subsection titles → sentence case; eq:Sinc-max-worst, eq:mat-multi, eq:cube, eq:subsurface-criterion all gained `\,` before the trailing comma; "with $g_1=\dots$ is the" syntactic error → "where $g_1=\dots$ is the".
Flag: eq:subsurface-criterion is `> 1\, ,` — looks correct but unusual after an inequality; verify in the rendered PDF. Cauchy1841 19th-century reference, no DOI expected.
Out-of-scope (caught later): GeLU first-use raw "GELU function" at line 1282 needs hand-spell.

**Wave 2.** 3 ranges → en-dash (`5--20~mm`, `1.6--1.8`, factors of `2--4`). All other long-tail checks passed; ReLU/GeLU coordination confirmed (glossaries already removed).
Open: section-opening "closed forms ... closed-form" echo within one clause — minor reword. Missing `However,` at the remark contrast (`Under realistic plane-wave or multipath exposure ...`). `approx.\` ×2 in this range left untouched pending paper-wide decision.

### Discussion + conclusion (1548–1720)

**Wave 1.** 3 subsection titles → sentence case (Low-frequency boundary, High-frequency boundary, Other regime boundaries); Conclusion: 0.35% Fresnel match line added (was missing despite being a headline result in the abstract); future-directions sentence added (extending below 1 GHz via resonance correction; refining tissue dielectric data above 100 GHz to reduce ±20% input uncertainty); blank-line spacing fix between two paragraphs in "Other regime boundaries". Closing pattern verified: numeric headline + condition + implication intact.
Flag: exposure-fraction paragraph in "Other regime boundaries" feels out of place (computational note, not regime limit) — better fit in Error Budget or Compliance.

**Wave 2.** 15 ranges → en-dash (table caption + 5 cells; 7 body ranges across all three boundary subsections; Conclusion `0.3--100~GHz`); `hotspot/Hotspot` → `hot-spot/Hot-spot` ×3 (matches author's tell from STYLE_ANALYSIS); 5 boundary paragraphs restructured for result-then-reason (each now opens with the numeric breakdown boundary — opacity 700~MHz–1~GHz, Mie 3–5~GHz / 5%–14%, resonance 300~MHz, Azzam 200–250~GHz, roughness 1~THz — supporting tables and derivations follow).
Open: Conclusion's three-step closing — implication clause is in an earlier sentence rather than the final line. Minimal fix possible but risks padding. New compound adjective "papillary-ridge-scale" in roughness rewrite — author should confirm or shorten to "ridge-scale". Wave-2 confirms recommendation: relocate the exposure-fraction paragraph.

### End matter + bibliography (1721–end)

**Wave 1.** 6 spurious `\quad` separators removed from book/proceedings `\bibitem` entries (Zhukov1998, AkenineMoller2018, BornWolf1999, Chew1995, BohrenHuffman1983, Durney1986). `\section*{Acknowledgment}` confirmed singular (correct IEEE TAP). Five `\IEEEbiography` blocks inside `\iffalse` read cleanly in American English. No `\gls{}` in bibliography; journal titles consistently use `\emph{}`.
Flag: Bamba2014 key/year mismatch; arXiv refs `\emph{arXiv:...}` non-standard; Funahashi2018 page `pp.~77\,665--77\,674` thousands-separator acceptable.

**Wave 2.** Zhukov1998 `pp.~45--55` → `pp.~45--56` (verified via DBLP `conf/rt/ZhukovIK98`); Hendrycks2016 `\emph{arXiv:1606.08415}` → `[Online]. Available: \url{https://arxiv.org/abs/1606.08415}` (arXiv ID verified); SionnaRT same normalization (arXiv ID 2303.11103 verified, author list cross-checked); Hirata2021 title `Review of computational dosimetry studies` → `review` (sentence case after colon).

**Full key/year audit table (32 entries)**: only Bamba2014 mismatches. Samaras2019 verified correct (vol. 40 no. 2, not vol. 41 some other paper).

**Confirmed DOIs available** (do NOT insert without author verification): ICNIRP2020 `10.1097/HP.0000000000001210`; Bamba2013 `10.1002/bem.21749`; Samaras2019 `10.1002/bem.22170`; Flintoft2014 `10.1088/0031-9155/59/13/3297`; Hirata2021 `10.1088/1361-6560/abf1b7`; Ohman1977 `10.1109/TAP.1977.1141718`. SI ones: Diao2024 `10.1109/TEMC.2024.3370219`; Azzam2015 `10.1080/09500340.2015.1005186`; Gabriel1996 `10.1088/0031-9155/41/11/003`; Dimbylow2002 `10.1088/0031-9155/47/16/302`; DuBois1916 `10.1001/archinte.1916.00080130010002`. **All identified, none inserted.**

Open: FWO/ERC absent from Acknowledgment despite earlier Wydaeghe papers listing them; verify whether these support this paper. Tomita1999 unverifiable (J. Tokyo Med. Univ. unindexed). Durney1986 report number `USAFSAM-TR-85-73` non-standard placement.

### Supplementary information (`paper_SI.tex`, ~740 lines)

**Wave 1.** Title `1 to 100\,GHz` → `1 to 100~GHz`; abstract `$6\,$GHz` and `$10\,$g` demoted from math; **18 numbered display equations** across `equation`/`align`/`multline` envs all gained `\, .`/`\, ,` inside; 19 subsection titles → sentence case (Polarization-aware Fresnel law, Layered tissue model, Mie residual analysis, Anthropometric scaling, etc.); ~30 `$X\,$unit` → `X~unit`; 4 `v$5.0$` → `v5.0` (IT'IS version refs); table headers `Finger ($17\,$mm)` → `Finger (17~mm)`; bibliography `30\,GHz`/`3\,GHz` thin-spaces normalized.
Flag: Eq. S18 (Du Bois) ends with bare `\,` — sentence continues, should be `\, ,`.

**Wave 2.** Eq. S18 fixed; 5 ranges → en-dash (`0.3--100~GHz`, `5--20~mm`, `0.3--10~GHz`, `2--4`, `5--14\%`); `\text{Fresnel}`/`\text{diffraction}` → `\mathrm{Fresnel}`/`\mathrm{diffraction}` in Mie underbrace decomposition (noun-like labels); 4 `approx.\` → "approximately" in flowing prose (left unchanged inside the tight `\paragraph{Whole-body resonance, below approx.\ 300~MHz.}` heading).
DOIs identified for SI references (see above) — all flagged for author fact-check.

## Bibliography fact-check (consolidated)

**Tier A — needs author resolution:**
- `Bamba2014` cite key vs entry year. PubMed PMID 22926824 confirms Feb 2013 print + epub Aug 2012. Recommend global find/replace `Bamba2014` → `Bamba2013` in `paper.tex` and `paper_SI.tex` (~6 calls in main text, possibly more in SI).
- `Tomita1999` *J. Tokyo Med. Univ.* not indexed — author should verify directly.

**Tier B — DOIs identified, not inserted:**
- Main paper: ICNIRP2020, Bamba2013, Samaras2019, Flintoft2014, Hirata2021, Ohman1977.
- SI: Diao2024, Azzam2015, Gabriel1996, Dimbylow2002, DuBois1916.
- IEEE TAP encourages DOIs; add `\newcommand*{\doi}[1]{\href{https://doi.org/#1}{#1}}` to preamble if adopting.

**Tier C — verified clean:**
- All other 32 main paper cite keys; year suffixes match entry dates.

## Open paper-wide decisions (cross-cutting)

1. `approx.\` vs "approximately" — 15+ remaining mixed occurrences. Recommend "approximately" in flowing prose, `approx.` only in tight `\paragraph{}` heads.
2. `T_s`, `T_p` polarization subscripts → `\mathrm{}` paper-wide (parallel to the `\theta_\mathrm{B}` fix).
3. Title block `1 to 100\,GHz` vs body `1--100~GHz` — title left as-is per IEEE convention.
4. Table column headers `[mm]` vs `(mm)` — currently mixed (line 1250 `[mm]`, line 616 `[S/m]`, line 585 `(TE)`). IEEE TAP slightly prefers parens.
5. "from 1--100~GHz" reads slightly awkward after "from" — alternatives "across 1--100~GHz" or "over 1--100~GHz".
6. Exposure-fraction paragraph in "Other regime boundaries" → relocate to ambient-occlusion methods region or to a closing computational remark in compliance.
7. GELU vs GeLU casing — current state: line 1278 "GELU"; line ~1437 "GeLU"; pick one.
8. "agreement is at the fourth significant figure" overstates a 0.2% deviation (≈3 decimal places). Suggest "Below $30^\circ$ the deviation stays below $0.2\%$."
9. `papillary-ridge-scale` new compound adjective from wave-2 roughness rewrite — confirm or shorten to "ridge-scale".
10. Conclusion's three-step closing — implication is in an earlier sentence; minor.
11. FWO / ERC absence in Acknowledgment vs author's typical funding stack.
12. Section-opening "closed forms ... closed-form" echo in Compliance.
13. Missing `However,` at remark contrast in Compliance (line ~1395).
14. Short FDTD subsection closing paragraph nearly duplicates figure caption.
15. `[0.75, 0.85]` interval set vs `0.75--0.85` en-dash range — same Flintoft band, different syntax. Unify or confirm intentional.

## Anti-patterns confirmed absent

- Em dashes (`---`) — none.
- `\textit{Lead-noun:}` paragraph leads — none (anti-pattern correctly absent in TAP draft).
- "leverage" verb — none.
- British spellings (modelling, behaviour, colour, polarisation, characterise, etc.) — none.
- Straight quotes — none; all LaTeX `` `` ... '' ``.
- `siunitx` — never loaded.
- `\gls{}` in abstract — none (and the entire glossaries package is now gone from the preamble).
- "obviously" / "clearly" / "of course" / "interestingly" / "surprisingly" / "remarkably" / "very" / "really" / "extremely" — none.

## Compile / structural risk

- Glossaries package and macros fully removed → next pdflatex run should be cleaner; verify no stale `\gls`/`\glspl` survived.
- VALIDATION wave-2 caught a missing `}` from a Python batch sed and repaired in the same run.
- `\label{def:eta}` → `\label{rem:eta}` rename verified by grep before commit.
- All custom math macros (`\Sinc`, `\Sab`, `\Aab`, `\Aperp`, `\Teff`, `\Tavg`, `\Tbar`, `\Tlay`, `\ntilde`, `\diff`, `\pospart`, `\Vis`, `\SabAvg`, `\RE`, `\censorphantom`, `\khat`, `\nhat`, `\rr`, `\EE`) confirmed used.

## Reports inventory (`agent_reports/`)

22 reports: 11 wave-1 (`REPORT_<AREA>.md`) + 11 wave-2 (`REPORT_<AREA>_W2.md`). `_SWARM_BRIEFING.md` is the master spec the agents read. Two reports (WHOLE_BODY wave 1, SUPPLEMENTARY wave 2) had their original Write blocked by the agent harness — content reconstructed from inline summaries.
