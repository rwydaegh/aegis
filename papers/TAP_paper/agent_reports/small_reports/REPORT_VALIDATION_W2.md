# Report: VALIDATION wave-2

Lines 944–1223 of `paper.tex` (`\section{Validation}` and all four subsections).

## Edits applied

### Numeric ranges — `$X$ to $Y$` → `$X$--$Y$` (en-dash)

All tight numeric comparisons in this section now use the en-dash form. Converted:

**Setup subsection (body text)**
- `$0.45$ to $5.8$~GHz` → `$0.45$--$5.8$~GHz`
- `$1$ to $4$~mm` → `$1$--$4$~mm`

**Mie subsection (body text)**
- `$3$ to $14\%$` → `$3$--$14\%$`

**FDTD subsection (body text + caption)**
- `$0.45$ to $5.8$~GHz` → `$0.45$--$5.8$~GHz` (body and caption)

**Combined dosimetry literature (body text)**
- `$5\%$ to $10\%$` → `$5\%$--$10\%$` (Bamba offset sentence)

**Waterfall figure caption (all ranges)**
- `$1$ to $100$~GHz` → `$1$--$100$~GHz`
- `$1$ to $12$~GHz` → `$1$--$12$~GHz`
- `$5$ to $11$~GHz` → `$5$--$11$~GHz`
- `$2\%$ to $4\%$` → `$2\%$--$4\%$`
- `$1$ to $18$~GHz` → `$1$--$18$~GHz`
- `$1.45$ to $5.8$~GHz` → `$1.45$--$5.8$~GHz`
- `$10$ to $100$~GHz` → `$10$--$100$~GHz`

**Tab. waterfall (all table rows)**
- Flintoft row: `$0.47$ to $0.49$`, `$7$ to $11$~GHz`, `$2\%$ to $4\%$` → en-dash forms
- Bamba row: `$0.50$ to $0.56$`, `$1.5$ to $5.8$~GHz`, `$0.47$ to $0.50$`, `$5\%$ to $10\%$` → en-dash forms
- Zhang row: `$0.45$ to $0.65$`, `$6$ to $18$~GHz`, `$0.43$ to $0.49$` → en-dash forms
- Kodera row: `$10$ to $100$~GHz` → en-dash form

**Kodera paragraph**
- `Models I to IV` → `Models I--IV`
- `$1$ to $100$~GHz` → `$1$--$100$~GHz`

### et al. formatting

`Kodera et~al.` (two occurrences in the Kodera discussion paragraph) → `Kodera \textit{et~al.}` per author style (STYLE_ANALYSIS.md §12.2).

### Paragraph structure — one idea per paragraph

The FDTD subsection had both the IEC/IEEE 63195 peak-Sab metric and the Cauchy metric in one paragraph. Split at "The second metric is..." to give each metric its own paragraph. Strengthens topic-first discipline for the second paragraph.

### Predicate strengthening

"The Bamba offset of $5\%$--$10\%$ in panel (c) is informative." → "...is expected:" (colon introduces the mechanism). "Informative" is a non-predicate; "expected" connects the result to the omitted physics that follows immediately.

### Closing brace repair

The waterfall figure caption lost its closing `}` during the Python batch replace. Restored: `...recovers the dip.}` before `\label{fig:waterfall}`.

## Tougher questions for the author

- **Bamba2014 key vs year (confirmed from wave-1)**: `\bibitem{Bamba2014}` entry reads "Feb. 2013". The caption labels the dataset "Bamba 2014" and the cite key implies 2014. Likely an online-first / print split. Resolve: update the bibentry year to 2014 (and verify page numbers to the print issue), or rename the key to `Bamba2013`. All six `\cite{Bamba2014}` calls must be updated consistently if the key changes.

- **Flintoft second appearance in Tab. II without cite**: the last row ("slope of mean Qa vs dSF") cites Flintoft with no `\cite{Flintoft2014}`. Looks intentional (same paper as the plateau row), but confirm no separate citation is needed.

- **Short closing paragraph in FDTD subsection**: "The closed-form Cauchy prediction approaches unity at the upper end of the band. Below 5 GHz..." nearly repeats the figure caption. Consider folding it into the caption or expanding it. Not touched — author decision.

## DOIs / references that look suspicious

- `\bibitem{Bamba2014}`: year mismatch (key says 2014, entry says Feb. 2013). Flagged in wave-1. No DOI; not fabricated.
- `\bibitem{Zhang2017thesis}`: Ph.D. thesis; no DOI (expected). Fine.
- `\bibitem{Kodera2024}`, `\bibitem{Diao2024}`, `\bibitem{Flintoft2014}`: no DOIs, not fabricated.
- `\bibitem{BohrenHuffman1983}`, `\bibitem{SionnaRT}`, `\bibitem{ITISv5}`: standard references, no issues.

## Anti-patterns found and fixed

- Numeric "X to Y" ranges (over 20 instances across body text, captions, and table rows) — all converted to en-dash.
- Two-idea paragraph in FDTD subsection — split.
- `Kodera et~al.` without `\textit{}` — fixed (two occurrences).
- Vague predicate "is informative" — replaced with "is expected:" plus colon-mechanism.
- Missing closing `}` on waterfall caption — repaired.

## Patterns introduced

- Consistent en-dash numeric ranges across all four subsections, captions, and table rows.
- `\textit{et~al.}` in in-prose author mentions.
- Colon-then-explanation after a numeric result sentence (Bamba paragraph).
- Paragraph break between the two FDTD regulatory metrics (one idea per paragraph).

## Out-of-scope items spotted

- Line 168: `Bamba et~al.~\cite{Bamba2014}` also lacks `\textit{}` on "et al." — outside range, not touched.
- The `$X\,$GHz` thin-space-inside-math pattern (wave-1 resolved most instances) is absent from this range — no residual instances found.
