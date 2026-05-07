# Swarm briefing — TAP paper style polish

This document is the canonical brief for every agent in the swarm. Read it once at the start of your run; refer back as needed.

> **MASTER SOURCE**: `/home/user/aegis/papers/example_papers/STYLE_ANALYSIS.md` is the full style reference. **You must apply every applicable rule and override from it, not only the ones distilled below.** The list below is a kickoff cheat-sheet, not an exhaustive specification. After your first pass on the obvious anti-patterns, do a second pass with the full md open, working through long-tail patterns (lexicon, quotation glyphs, hyphenation, definition-by-inversion, sentence-length variation, etc.) section by section.

## Target

- **File 1**: `/home/user/aegis/papers/TAP_paper/paper.tex` (~2000 lines, IEEEtran two-column journal)
- **File 2**: `/home/user/aegis/papers/TAP_paper/paper_SI.tex` (~740 lines, single-column 11pt)
- **Target journal**: IEEE Transactions on Antennas and Propagation (IEEE TAP).
- **Manuscript title**: "Closed-Form Absorbed-Power Dosimetry on the Human Body from 1 to 100 GHz"
- **Author**: Robin Wydaeghe (sole first author, end-of-PhD at UGent/IMEC)

## What this swarm is doing

A coordinated style and structure polish, applying the author's preferences from `papers/example_papers/STYLE_ANALYSIS.md`. This is **NOT** a content rewrite — the science stands. We are fixing surface and structural issues, removing anti-patterns, and introducing patterns that should be present but are not.

## Style rules (the canonical list)

### Hard rules (always apply)

1. **IEEE TAP conventions only.** This is not npj Wireless Comm, not Phys. Med. Biol., not IEEE Access. No IOP-style structured abstracts. No IOP custom commands like `\funding{}` / `\roles{}`. No author-year citations. No `\citep`. Use IEEEtran defaults: numeric `\cite{}`, `\section*{Acknowledgment}` (singular for IEEE TAP), `\IEEEbiography` blocks if author bios are wanted, etc.

2. **American English.** "modeling", "modeled", "behavior", "acknowledgment" (singular for IEEE), "color", "fiber", "centimeter", "millimeter", "polarization", "characterize", "optimize", "analyze", "neighbor". Search-and-replace any British leak: "modelling", "behaviour", "colour", "fibre", "polarisation", "characterise", etc.

3. **No em dashes.** The author does not use `---`. Replace with commas, parentheses, or colons. (En dash `--` for numeric ranges only: `1--100`, `pp.~12--34`.)

4. **No `\textit{lead-noun:}` paragraph leads in the middle of prose.** This is an anti-pattern. Use proper `\subsubsection{}` if structure is needed, or just write a normal paragraph with a strong topic sentence.

5. **Drop `siunitx` if present.** Use plain text with non-breaking ties: `28~GHz`, `1.5~m`, `4~cm$^2$`, `1~W/m$^2$`. Do not use `\SI{}{...}`.

6. **Non-breaking ties (`~`) before units and short cross-references.** `28~GHz`, `1.5~m`, `4~cm$^2$`, `Fig.~\ref{...}`, `Table~\ref{...}`, `Section~\ref{...}`, `Eq.~\eqref{...}`. Almost no exceptions. The TAP paper currently uses `$X\,$GHz` (thin-space inside math mode) — this is acceptable but the tilde-glued form is preferred. **You may convert the easy cases (e.g., where the number is purely a literal like `28`); leave more complex math-mode constructions alone if conversion is risky.**

7. **Equation-terminating punctuation lives INSIDE the equation, with a thin space.** End every numbered display equation with `\, .` or `\, ,` before `\end{equation}` (or `\end{aligned}`). Decide between `,` and `.` by whether the surrounding sentence continues or terminates. Hunt down equations with the punctuation outside (`\end{equation}.` or `\end{equation},`) and move it inside.

8. **Glossaries first-use is hand-managed.**
   - **Abstract: NEVER `\gls{}`.** Spell out every acronym in plain text in the abstract.
   - **First appearance in body: spell it out manually** as plain prose, then use `\gls{}` from the second mention onward.
   - **First appearance in a caption: spell it out manually.** Don't trust auto-expansion in floats.
   - If an acronym only appears in one place, spell it out and don't bother with `\gls{}`.

9. **Avoid the verb "leverage".** Replace with "use", "exploit", "rely on", "apply", "combine", "draw on", "build on" as appropriate.

10. **Sentence case for all section/subsection titles.** "Closed-form absorbed-power dosimetry" not "Closed-Form Absorbed-Power Dosimetry". (Note: titles in the manuscript title block and reference titles follow IEEE style — do NOT downcase those.) Inside the body, **always use sentence case** for `\section`/`\subsection`/`\subsubsection` headings. **Decisive rule, no exceptions:** downcase every section/subsection/subsubsection title in your range, even if other parts of the paper still have title-case (those will be downcased by the second-wave swarm). Capitalize only the first word and proper nouns (Cauchy, Fresnel, Mie, Sim4Life, Thelonious, ICNIRP, GHz, IEEE, etc.).

11. **Fix typos. Always.** Do not preserve typos as "voice". Run a typo pass on your assigned range.

12. **Do not invent DOIs.** If a reference has a DOI, keep it. If not, leave it blank. Do not fabricate. **Tag any reference whose DOI looks AI-generated (suspicious) in your report.** The author wants to fact-check the bibliography manually.

### Soft rules (apply with judgment)

- **Vector / matrix notation**: `\boldsymbol{x}` for explicit vectors, `\mathbf{H}` for matrices and fields, `\mathrm{}` for noun-like subscripts (`S_\mathrm{ab}`, `S_\mathrm{inc}`). Soft rule — don't fight existing custom macros (the paper has `\Sinc`, `\Sab`, etc. already). Verify the macros render to the right form; otherwise leave alone.

- **Topic-first paragraphs in Results-like sections**: paragraphs should open with "Figure X shows…" / "Table Y lists…" or a direct numeric claim. Restructure if a paragraph buries the lead.

- **Result-then-reason sentences**: state the number and units, then a one-clause mechanism. "Brain SAR decreases by 96\% from 450~MHz to 5.8~GHz as absorption shifts to the skin." Strong pattern in the author's voice.

- **Connectives**: "However,", "Therefore,", "Conversely,", "Hence,", "Thus,", "Moreover,", "Furthermore,", "First, … Second, … Finally, …" — use them.

- **Hedging**: hedge interpretations and mechanisms, not measurements. "may", "can", "approximately" go before reasons; numbers stay sharp.

- **Italic emphasis**: `\textit{}` for one-time emphasis or to introduce a new term that's about to be defined. Don't sprinkle italics for stylistic flair.

- **Avoid "obviously", "clearly", "of course", "interestingly", "remarkably"** — neutral tone.

## Pattern injection (introduce if missing)

If your range covers the introduction or end-matter, the author may want these in if absent:

- **Numbered novelty list at end of intro**: prefaced by "To the best of the authors' knowledge, the paper makes the following contributions for the first time." (TAP paper currently has this — verify it's an `enumerate`, not `itemize`.)
- **End-matter sections** (in the IEEE TAP order, after Conclusion):
  - `\section*{Acknowledgment}` (singular for IEEE TAP)
  - Optionally `\section*{Data Availability}` if appropriate
  - Optionally `\IEEEbiography` blocks if author bios fit
  - For IEEE TAP, **no** explicit "Author Contributions" or "Competing Interests" section is required; do not add unless present already.

## Scope cap

- **You can do a lot.** Rephrase paragraphs. Restructure sub-organization. Replace `itemize` with `enumerate`. Re-do figure captions. Move sentences to improve flow.
- **You cannot** write entire new Methods or Results sections from scratch. You cannot add new claims, new equations, new figures, new validations.
- **Anything obvious**: just do it. Make assumptions.
- **Truly hard / scientific judgment**: flag in your report. Don't guess if you'd be wrong.

## Coordination rules

- **Stay in your assigned line range.** Other agents are working on other ranges in parallel. Touching content outside your range risks merge conflicts.
- **Use unique surrounding context** in `Edit` `old_string` parameters. The Edit tool requires exact, unique matches.
- **If a hard issue spans your boundary**, mention it in your report and do not edit across the boundary.
- **Note**: line numbers shift as edits happen. Always use Edit's anchor-string matching, not absolute line numbers, when modifying. Use Read with line-range to peek but expect drift.

## Reporting

Each agent writes one report file at:
`/home/user/aegis/papers/TAP_paper/agent_reports/REPORT_<AREA>.md`

Where `<AREA>` is your assigned area name (e.g., `INTRO`, `LOCAL_LAW`, `VALIDATION`, etc.).

Report format:

```markdown
# Report: <area>

## Edits applied
- bullet list of significant changes

## Tougher questions for the author
- if any — keep this short. Only the genuinely hard ones.

## DOIs / references that look suspicious
- (if applicable) bullet list of `\bibitem{key}` entries with suspicious DOIs

## Anti-patterns found and fixed
- bullet list

## Patterns introduced (if applicable)
- bullet list

## Out-of-scope items spotted
- things outside your range you noticed but didn't touch
```

Keep reports terse. The author will read them all together.

## Long-tail checklist (extracted from STYLE_ANALYSIS.md — apply in addition to hard rules above)

These are NOT optional. Work through every one within your assigned range.

### Microscopic glyph / punctuation

- **Quotation marks**: always LaTeX double-tick `` `` ... '' ``. Never straight quotes. Never directional Unicode. Even informal asides keep this form.
- **Numeric ranges always use en-dash `--`**: `1--100~GHz`, `1.5--1.9$\times$`, `pp.~3115--30`. Replace any `1 to 100~GHz` constructions with the en-dash form unless the prose flow specifically benefits from "to".
- **Decimals always have a leading zero**: `0.25` not `.25`.
- **Multipliers**: prefer `2$\times$ stronger`, `3.2-fold`, `1.5--1.9~times` (en-dash range). Older "2 to 3 times" form is acceptable but the new style anchors numerics tighter.
- **Comma after intro adverbials**: "However,", "Therefore,", "Conversely,", "Moreover,", "Furthermore,", "In particular,", "First,", "Second,", "Finally,", "Note that,", "Hence,", "Then,", "Thus," — every one followed by a comma, then a complete clause.
- **`e.g.,`, `i.e.,`, `vs.`, `cf.`** — abbreviated form with trailing comma. No `e.g.` without the comma. No `eg.` typo.
- **`w.r.t.`** — author's preferred abbreviation for "with respect to" in body prose.
- **`approx.`** — generally written out as "approximately"; abbreviation only in tight technical contexts.
- **Percent sign always escaped**: `\%`, never raw `%`.
- **Non-breaking ties (`~`)** — repeat from above: before units, before numbers in cross-refs, between author and "et al.", between part and number in references.

### Hyphenation conventions

Apply within your range, fix any inconsistency:

- **Hyphenated compound modifiers**: `cell-free`, `line-of-sight`, `non-line-of-sight`, `large-scale`, `small-scale`, `quasi-deterministic`, `auto-induced`, `worst-case`, `mass-averaged`, `peak-spatial`, `non-user`, `body-worn`, `time-averaged`, `site-specific`, `whole-body`, `wavelength-sized`, `vertically-polarized`, `frequency-dependent`, `closed-form`, `flux-weighted`, `direction-averaged`, `area-weighted`, `polarization-aware`, `incident-power-density`, `surface-averaged`, `mass-averaged`.
- **Pick one mmWave form per paper and stick to it**: `mmWave` vs `mm-Wave` vs `millimeter-wave`. The TAP paper currently mixes — pick one (likely `mmWave` for IEEE TAP) and unify within your range, but do NOT cross your boundary.
- **Subscript names not hyphenated**: `psSAR_{10\mathrm{g}}`, `SAR_\mathrm{wb}`, `S_\mathrm{ab}`.

### Math typesetting (full discipline)

- **Equation termination**: `\, .` or `\, ,` BEFORE `\end{equation}` or `\end{aligned}`. Always.
- **Subscripts that name a thing** (not an index): wrap in `\mathrm{}`. So `S_\mathrm{ab}`, `S_\mathrm{inc}`, `psSAR_{10\mathrm{g}}`, `SAR_\mathrm{wb}`, `\delta_{90}`, `\mathbf{r}_\mathrm{ear}`, `N^\mathrm{rays}`. Index subscripts (`i`, `j`, `l`, `s`) stay bare math-italic.
- **Don't use `\text{}` for noun-subscripts**; the convention is `\mathrm{}`.
- **Equation labels are descriptive nouns**: `eq:cauchy`, `eq:precoder`, `eq:hotspot_score`, `eq:final_channel`. Rename if you spot pure-numeric labels in a way that doesn't break refs (don't break refs, just flag).
- **`\eqref{eq:...}`** is the preferred form for inline equation refs (with parens auto-added). `Eq.~\eqref{eq:...}` for sentence-leading.
- **Inline math hygiene**: Greek letters (`$\lambda$`, `$\theta$`, `$\phi$`), exponents (`^2`), and unit composites all live in math mode. The `^2` in `cm$^2$` is mathmode; the `cm` is text mode.
- **Operator words**: `\arg`, `\sin`, `\cos`, `\exp`, `\sqrt`. Imaginary unit is `j` (engineering convention), not `i`.
- **Phasor exponentials**: `\exp(jk\cdot)` rather than `e^{jk\cdot}` is the author's habit.
- **Multi-line systems**: `\begin{equation}\begin{aligned}\dots\end{aligned}\end{equation}` for one number across several lines.
- **Piecewise**: `\begin{dcases}\dots\end{dcases}`.

### Sentence-level

- **Topic-first sentences**: every paragraph in Results-style sections opens with a deictic claim — "Figure X shows…", "Table Y lists…", or a direct numeric claim. Restructure if the lead is buried.
- **Result-then-reason**: state the number and units, then a one-clause mechanism. "Brain SAR decreases by 96\% from 450~MHz to 5.8~GHz as absorption shifts to the skin."
- **Definitions by inversion**: when introducing a new term, the form is "X, where Y is the …" or "We coin this \textit{X}, because …". The defined term gets `\textit{}` (or `\emph{}`) on first appearance.
- **Colon-then-list / colon-then-explanation**: heavy use. After a setup clause, a colon, then a clean structure (enumerate, list, or single explanatory clause).
- **Connectives**: "Therefore", "Hence", "Thus", "However", "Moreover", "Furthermore", "Conversely", "In particular", "Note that" — load-bearing. Almost no two consecutive claim-sentences without an explicit logical link.
- **Sentence length**: medium dominant (15–28 words). Short staccato (5–10 words) at high-impact moments. Avoid 40+ word sentences without commas/parens to break them.
- **Hedging**: hedge mechanisms ("may indicate", "approximately", "on the order of"), not measurements. Numbers stay sharp.
- **Negation discipline**: avoid absolute "never"/"always" without qualification.

### Word level / lexicon

- **Verb register**: prefer "show / shows / shown", "compute", "characterize", "introduce / propose", "enable / enables", "find / found / observe / observed", "indicate / suggest", "comprise / consist of", "demonstrate" (sparingly).
- **AVOID the verb "leverage"** (already in hard rules — repeated for emphasis).
- **AVOID intensifiers without quantification**: "very", "really", "extremely". Replace with the actual number or the actual mechanism (`$f^4$ scaling`, `20~dB`).
- **AVOID "obviously", "clearly", "of course", "interestingly", "surprisingly", "remarkably"** — neutral tone is the author's posture.
- **Recurring adjective family**: "realistic", "site-specific", "deterministic", "quasi-deterministic", "stochastic", "comprehensive", "novel" (used sparingly — at most twice per paper, anchored to specific contributions). "Worst-case" both as adjective and as noun.
- **First-person discipline**:
  - **"we"** — active first-person plural, dominant in Methods, Results, claims.
  - **"this work" / "this paper" / "this study"** — for self-reference of the document, especially intro/conclusion novelty claims.
  - **"the authors"** — only in disclaimers ("To the best of the authors' knowledge").
  - **"I"** — never. (Possibly in a quoted layman aside, otherwise no.)
  - **Passive** — for procedures and setup ("simulations were performed", "fields are evaluated"). Active for claims.

### `\textit{}` vs `\emph{}` discipline

- **`\textit{}`** for one-time emphasis, foreign words ("\textit{et al.}"), and the *first* introduction of a new local jargon term that's then defined.
- **`\emph{}`** sparingly, in PMB-style usage; for the TAP paper, `\textit{}` is sufficient.
- **Do NOT mix the two within a single subsection** without reason.
- **NEVER use `\textit{Lead-noun:}` paragraph leads** — anti-pattern (already in hard rules).
- **Do not sprinkle italics for "stylistic flair"** — every italicized phrase should pay rent.

### Paragraph structure

- **One idea per paragraph**. Long paragraphs (>10 sentences) acceptable only in Methods chained-procedure descriptions; even there, sub-procedures should be true `\subsubsection{}` (not italic leads).
- **Opening shapes** (in rough frequency order): figure/table reference; direct claim; bridge/context; definition/framing.
- **Closing shape**: single-sentence implication is common ("Therefore, the small-scale hot-spot increases the electric field by 12~dB on top of the large-scale beamforming gain.").

### Section / subsection conventions

- **Sentence case** for subsection titles where free to choose. **BUT**: be consistent with what the rest of the paper already uses. The TAP paper currently uses title case for subsections — do not unilaterally flip; flag in your report if you think the whole paper should be redone, do not change inside your range.
- **No "Introduction" or "Conclusion" subsections** — keep these flat.
- **No `\textit{Lead-noun:}` pseudo-subsubsections** — convert to real `\subsubsection{}` or normal prose.

### Figures and captions

- **Float placement**: `[h]`, `[h!]`, `[t!]`, `[!t]`. Avoid `[H]`. The author over-specifies placement — match existing convention.
- **Caption shape (IEEE TAP)**: descriptive, not lead-with-finding. What's shown, what each colour/symbol means. End with period. Sentence case.
- **Multi-panel**: `subcaption` package's `subfigure` environment. Sub-captions are short noun phrases. Cross-refs as `Fig.~\ref{fig:X}(a)`.
- **Width**: `\columnwidth` for column figures, `\textwidth` (with `figure*`) for full-page. Avoid hardcoded inches if possible.

### Tables

- **booktabs**: `\toprule`, `\midrule`, `\bottomrule`. No `\hline`. No `|c|c|`.
- **Caption above table**, sentence-style with closing period.
- **Multi-column headers** with `\multicolumn` and `\cmidrule(lr){i-j}` for grouped headers.
- **Footnotes inside tables**: `^a`, `^b` superscripts, with `\multicolumn{N}{@{}l}{\footnotesize $^a$...}` row below `\bottomrule`.
- **Bold for headline numbers** (the tightest compliance margin, the worst-case row).
- **Bracketed units in column headers**: `[mW/kg]`, `(W/m$^2$)`.

### Citations and bibliography (IEEE TAP specific)

- **Numeric `\cite{key}`** only. No author-year, no `\citep`/`\citet`.
- **Bibliography entries** styled IEEE-style: `\textit{Journal Name}`, `vol.~XX`, `no.~Y`, `pp.~MM-NN`, `Month YYYY`, `doi: \doi{...}`.
- **`\doi{}`** macro is preferred — keep wherever DOIs are present. **Never invent or guess DOIs.** Flag suspicious ones in your report.
- **`\textit{et al.}`** in body-text in-prose mentions; `et al.` plain in headers (`\headeretal` macro).
- **Citation keys**: prefer `lastname2024keyword` style. Don't rename existing keys (would break refs); flag inconsistencies.
- **In-prose author naming is rare** in the TAP paper / IEEE style — citations stay parenthetical `\cite{}`. Don't introduce "Smith et al. showed that…" patterns; use `[N] showed that…` or `\cite{X} showed…` IEEE-style.

### Document architecture

- **Abstract**: traditional flowing single paragraph, ~250–300 words. Numeric anchors. Closes with the headline result.
- **Numbered novelty list at end of intro**: `\begin{enumerate}` (NOT `\begin{itemize}`), prefaced by "To the best of the authors' knowledge, the paper makes the following contributions for the first time."
- **End-matter (IEEE TAP order)**: `\section*{Acknowledgment}` (singular for IEEE TAP; not "Acknowledgements"), then `thebibliography`, then optional `\IEEEbiography` blocks.
- **Closing of Conclusion**: numeric headline + condition + implication, in three steps.
- **Limitations + future work** explicit, late in Conclusion.

### Voice / posture

- **Numeric anchoring**: every qualitative claim attached to a number with units.
- **Hedge interpretations, not measurements**.
- **Don't repeat "first" / "novel"** beyond intro; conclusion uses retrospective verbs ("characterized", "demonstrated", "show").
- **Reader is implicit** — no "the reader will note", no "you can see".

### Specific tells / signature checks

If your range covers any of these, ensure they're present:

- `\IEEEPARstart{X}{ext}` first letter at the very start of `\section{Introduction}`.
- The phrase "To the best of the authors' knowledge" before the novelty list.
- `\Cref{}` / `\cref{}` (cleveref) for cross-refs to environments; `Fig.~\ref{}` / `Section~\ref{}` for plain refs.
- A flowchart or summary figure as the first figure in Methods or near the end of Introduction.
- Acronym ladder at top of preamble.
- Acknowledgment block near end.

### Typo hot list (if any of these appear, fix without thinking)

- "scalibility" → "scalability"
- "miutes" → "minutes"
- "Eventhough" → "Even though"
- "hybdrization" → "hybridization"
- "numer" → "number"
- "Departement" → "Department"
- "excepted" where "expected" was meant — read context.
- Other plausible typos in your range.

### British → American replacement set

(For your range, search-and-replace where it doesn't break a quoted title.)

- modelling → modeling
- modelled → modeled
- behaviour → behavior
- colour → color
- centimetre → centimeter
- millimetre → millimeter
- fibre → fiber
- polarisation → polarization
- characterise → characterize
- optimise → optimize
- analyse → analyze
- neighbour → neighbor
- favour → favor
- acknowledgement → acknowledgment (and Acknowledgements → Acknowledgment for the IEEE TAP section title)
- judgement → judgment
- programme → program
- centre → center

---

## Files you can read for context

- `/home/user/aegis/papers/example_papers/STYLE_ANALYSIS.md` — **MASTER STYLE REFERENCE.** Read every applicable section, not just the briefing.
- `/home/user/aegis/papers/TAP_paper/paper.tex` — the manuscript.
- `/home/user/aegis/papers/TAP_paper/paper_SI.tex` — the supplement.
- `/home/user/aegis/papers/TAP_paper/README.md` — figure provenance.
- `/home/user/aegis/papers/example_papers/2026_npj_outdoor_RT-QuaDRiGa-FDTD_28GHz_CF-MaMIMO.tex`, `2026_PMB_multifrequency_FDTD_environmental_auto-induced_450MHz-26GHz.tex`, `2022_IEEEAccess_indoor_RT-FDTD_3.5-28GHz_DMaMIMO.tex` — example papers for cross-reference (especially the IEEE Access one for closest IEEE-style precedent).
