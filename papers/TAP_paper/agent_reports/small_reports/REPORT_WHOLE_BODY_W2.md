# Report: WHOLE_BODY (wave 2)

Range: lines ~736--934 (`\section{Whole-body absorbed power}` through end of `\subsection{Layered transmission below 5\,GHz}`).

## Edits applied

- **`\label{def:eta}` renamed to `\label{rem:eta}`** inside the `remark[Exposure fraction]` environment. Confirmed safe: `grep` found zero occurrences of `\cref{def:eta}` or `\ref{def:eta}` anywhere in `paper.tex` or `paper_SI.tex`. The label was only defined, never cross-referenced.

- **`\textit{exposure fraction}`** added on first use inside the remark (line 756). The term was introduced without italics; per style, the first introduction of a local jargon term gets `\textit{}`.

- **Numeric ranges: "to" -> en-dash `--`** (all within scope):
  - `$0.75$ to $0.85$` -> `$0.75$--$0.85$` (Flintoft estimate band)
  - `$0.3$ to $100\,$GHz` -> `$0.3$--$100\,$GHz` (two occurrences: Cauchy-T0 accuracy sentence and table-caption sentence)
  - `$5\%$ to $10\%$ across $1.45$ to $5.8\,$GHz` -> `$5\%$--$10\%$ across $1.45$--$5.8\,$GHz` (Bamba range, was split across lines)
  - `$0.47$ to $0.49$ at $7$ to $11\,$GHz` -> `$0.47$--$0.49$ at $7$--$11\,$GHz` (Flintoft plateau)
  - `$0.45$ to $0.65$` -> `$0.45$--$0.65$` (Zhang plateau)
  - `$7$ to $11\,$GHz` -> `$7$--$11\,$GHz` (fat-slope context, Layered section)
  - `$2$ to $20\,$mm` -> `$2$--$20\,$mm` (fat thickness range)

- **`approx.\ ` twice on the opacity-condition line** -> `approximately` (written out; style prefers "approximately" in prose).

- **Reflowed over-long lines**: After collapsing Flintoft and Zhang plateau sentences, lines were broken at sensible column positions.

## Tougher questions for the author

- **`[0.75, 0.85]` bracket notation** at line 776: interval-set notation coexists with en-dash range `$0.75$--$0.85$` two lines earlier. Both refer to the Flintoft band but in different syntactic roles. No change made -- confirm if intentional or if one form should be unified.

- **`\cref{thm:exact}` scope hedge**: "For any body opaque at the wavelength" is the key assumption. This is correctly stated. The Generalized Cauchy is hedged under "isotropic, unpolarized plane-wave illumination" and "$T_0$" approximation -- both constraints explicit. Scope is properly hedged; no changes to theorem statements made.

## DOIs / references that look suspicious

None. References in this range: `Cauchy1841`, `Zhukov1998`, `Landis2002`, `AkenineMoller2018`, `Flintoft2014`, `Tomita1999`, `Bamba2014`, `Zhang2017thesis`, `Chew1995`, `BornWolf1999`. Classical and well-known; no AI-generated DOI risk detected.

## Anti-patterns found and fixed

- `\label{def:eta}` inside `remark` environment (semantically misleading: `def:` prefix implies `definition` env). Renamed to `rem:eta`.
- Numeric ranges using prose "to" in tight mathematical context -- all converted to `--`.
- `approx.\ ` in prose -- replaced with "approximately".
- Missing `\textit{}` on first introduction of "exposure fraction".

## Patterns introduced

- `\textit{exposure fraction}` on first use (definition-by-inversion pattern per style spec).

## Out-of-scope items spotted

- Figure caption for `fig:phantom` (lines ~710--725) references `\eqref{eq:eta-def}`: correct. Caption ends with period, uses sentence case: correct.
- Table caption (lines 852--854): ends with period, sentence case, placed above `tabular`: all correct.
- No `leverage`, `obviously`, `clearly`, `very`, `really` found in scope.
- No em dashes in scope.
- No British spellings in scope.
- All quotation marks already use LaTeX double-tick form.
- `Fabry--P\'erot` already has en-dash: correct.
- `whole-body`, `self-shadowing`, `ambient occlusion` (no hyphen), `direction-averaged`, `flux-weighted` all hyphenated correctly.
