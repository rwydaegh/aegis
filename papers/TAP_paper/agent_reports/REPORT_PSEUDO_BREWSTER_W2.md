# Report: PSEUDO_BREWSTER (Wave 2)

Lines 505--736: `\section{Pseudo-Brewster compensation}` and all subsections.

Wave-2 applied a long-tail pass on top of Wave-1's changes. The section was already in good shape after Wave-1; this pass handles the remaining micro-issues.

## Edits applied

- **Numeric range `" to "` → `--`**: `$T_0 \approx 0.5$ to $0.6$` → `$T_0 \approx 0.5$--$0.6$` (Mechanism subsection, normal-incidence value range). `$70$ to $75^\circ$` → `$70$--$75^\circ$` (Quantitative behavior subsection, maximum deviation angle range).

- **Noun-like subscripts → `\mathrm{}`**: `\theta_B` → `\theta_{\mathrm{B}}` (Brewster angle) and `\theta_{pB}` → `\theta_{\mathrm{pB}}` (pseudo-Brewster angle) throughout the Mechanism subsection. These subscripts label named physical phenomena, not indices.

- **Definition-by-inversion: italicize freshly-defined terms**: "pseudo-Brewster angle" italicized on first formal definition (`\textit{pseudo-Brewster angle}`, line ~520). "geometric absorption law" italicized when the term is first introduced formally in body prose, replacing the weaker "the geometric form" (`\textit{geometric absorption law}`, line ~663).

- **Hedging discipline: uncited threshold claim softened**: "The criterion weakens for $|\ntilde| > 2.5$ but the near-constancy persists" → "Empirically, the near-constancy extends to $|\ntilde| > 2.5$, below the strict Azzam threshold." The original "weakens" was ambiguous (sounds like the compensation degrades, not that the index threshold for qualification is lower). The new phrasing signals this is an empirical observation, not a theorem.

- **Figure caption R_of_f: finding-in-caption → descriptive**: The old caption stated findings ("stays within ±4%...", "crosses one exactly at 40.4 GHz", "underestimates... overestimates"). IEEE TAP captions should describe what is plotted, not report results. The findings are already stated in the body paragraph. New caption describes the axes, what R=1/R<1/R>1 means, and what the dashed horizontal lines mark.

- **Unit format in phantom figure caption**: `$\Sinc = 1\,$W/m$^2$` (thin space inside math, then units in text) → `$\Sinc = 1$~W/m$^2$` (tilde-glued, preferred form per STYLE_ANALYSIS).

## Tougher questions for the author

- **"agreement is at the fourth significant figure" (line ~574)**: Table shows $\Tavg/T_0 = 1.002$ at $30^\circ$, which is $0.2\%$ deviation -- three-decimal-place agreement, not four significant figures of $T_0$ (that would be $< 0.01\%$). The phrase is ambiguous. Consider replacing with the actual deviation: "Below $30^\circ$ the deviation stays below $0.2\%$."

- **`Azzam~\cite{Azzam2015}` in-prose author name**: Per IEEE style, citations are usually parenthetical, not "AuthorName showed...". However, naming Azzam establishes an eponymous criterion and is used only once. This may be intentional. No change made.

- **Paragraph topic-first in Mechanism subsection**: The second paragraph starts "Azzam showed that for lossless dielectrics..." rather than leading with the biological tissue finding. The Mechanism subsection is theory (not Results), so deductive flow is defensible. If the author wants strict result-then-reason even here, the paragraph could open "Biological tissue at mmWave has $|\ntilde| \in [3, 6]$, placing it in Azzam's high-index regime~\cite{Azzam2015}..." No change made; flagging for author decision.

- **R_of_f figure caption dashed lines**: New caption says "The dashed horizontal lines mark the $\pm 4\%$ band" -- verify that the actual figure has such dashed lines. If not, adjust wording.

## DOIs / references that look suspicious

None new. Wave-1 flagged `Potter1970`, `Ohman1977`, `Azzam2015` -- still open.

## Anti-patterns found and fixed

- `"X to Y"` numeric range form (two instances) → en-dash form.
- Bare noun subscripts `\theta_B`, `\theta_{pB}` → `\mathrm{}`.
- Finding in IEEE TAP figure caption (R_of_f) → descriptive caption.
- Thin space inside math for unit (`$1\,$W/m$^2$`) → tilde-glued form.
- Uncited threshold claim `$|\ntilde| > 2.5$` hedged with "Empirically".

## Patterns introduced

- `\textit{}` on first formal definition of "pseudo-Brewster angle" (line ~520).
- `\textit{}` on first body-prose introduction of "geometric absorption law" (line ~663).

## Out-of-scope items spotted

- `T_s`, `T_p` throughout the entire paper use bare math-italic subscripts. Per STYLE_ANALYSIS, "s" and "p" are noun-like labels (s-polarization, p-polarization) and should be `T_{\mathrm{s}}`, `T_{\mathrm{p}}`. This is established before this range (line ~447). Changing only within this range would create inconsistency. The author should decide and apply globally.
- `$X\,$GHz` thin-space-in-math constructions continue from line ~826 onward (outside range).
- Line ~874: `$1.45$ to $5.8$~GHz` -- "to" range outside this range that should become `$1.45$--$5.8$~GHz`.
