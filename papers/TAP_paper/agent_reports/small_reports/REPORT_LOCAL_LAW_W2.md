# Report: LOCAL_LAW (wave 2)

## Edits applied

- `\section{Local Absorption Law}` → `\section{Local absorption law}` (primary mission: sentence case)
- `\subsection{Power Flux Through the Surface}` → `\subsection{Power flux through the surface}`
- `\subsection{Fresnel Coefficients}` → `\subsection{Fresnel coefficients}`
- `\subsection{Polarization-Aware Exact Law}` → `\subsection{Polarization-aware exact law}`
- `\subsection{Setup}` — unchanged (single word)
- `$28\,$GHz` → `28~GHz` (thin-space-in-math unit attachment converted to preferred tilde-glued form outside math mode)
- `$25.8\,$S/m` → `$25.8$~S/m` (same conversion; value stays in math mode, unit glued outside with tilde)

## Tougher questions for the author

None. All changes are mechanical.

## Anti-patterns found and fixed

- Four title-case subsection headings corrected to sentence case (LOCAL_LAW was the last range still in title case after wave 1).
- Two `$X\,$unit` constructions converted to tilde-glued plain-text units.

## Long-tail checklist pass

- **Quotation glyphs**: no straight quotes in this range.
- **Numeric ranges**: no "X to Y" constructions; all numeric mentions are single values. No `--` conversions needed.
- **Equation termination**: all seven equations in range already carry `\, .` or `\, ,` before `\end{equation}`. The boxed equation uses `}\,.` which is correct.
- **Noun-like subscripts in `\mathrm{}`**: `\mathbf{S}_{\mathrm{inc}}` and `\diff P_{\mathrm{in}}` already correct. Index subscripts (`i`, `s`, `p`) bare math-italic.
- **Topic-first paragraphs**: all subsection-opening paragraphs lead with the subject matter.
- **Italics for freshly defined terms**: the three inline glosses ("unpolarized baseline", "polarization splitting", "local TM excess") are descriptive names for math symbols (`\Tavg`, `\Delta T`, `q`), not coined jargon. No `\textit{}` warranted.
- **Connectives**: "therefore", "so" — adequate throughout.
- **Verb register**: "shows", "gives", "enter as" — all appropriate.
- **No "leverage", "obviously", "clearly", "interestingly"** detected.
- **American English**: no British spellings.
- **Typos**: none.

## Out-of-scope items spotted

None. Next section (`\section{Pseudo-Brewster compensation}` at line ~508) outside this range and not touched.
