# Report: COMPLIANCE

## Edits applied

- **Section titles: title case -> sentence case** (four headings):
  - `\section{Compliance and Corollaries}` -> `\section{Compliance and corollaries}`
  - `\subsection{Whole-Body SAR Threshold}` -> `\subsection{Whole-body SAR threshold}`
  - `\subsection{Multi-Source Matrix Form}` -> `\subsection{Multi-source matrix form}`
  - `\subsection{Peak Spatial-Average SAR Over a 10\,g Cube}` -> `\subsection{Peak spatial-average SAR over a 10\,g cube}`

- **Equation punctuation (rule 7)**: Added `\,` before comma inside all four display equations in this section:
  - `eq:Sinc-max-worst`: `\Aab},` -> `\Aab}\, ,`
  - `eq:mat-multi`: `\mathbf{s},` -> `\mathbf{s}\, ,`
  - `eq:cube`: `\bigr),` -> `\bigr)\, ,`
  - `eq:subsurface-criterion`: `> 1,` -> `> 1\, ,`

- **Grammar fix**: "below the body surface, with $g_1 = ...$ is the" was a syntactic error ("with X is Y"). Changed `with` -> `where`.

## Tougher questions for the author

- `eq:subsurface-criterion` is an inequality (`> 1`). The `\, ,` after the inequality looks correct per rule 7 but unusual. Worth a compiled-PDF check.
- The remark block (~line 1393) concatenates two logical sentences without a paragraph break. Minor flow issue; left as-is since it is inside a `remark` environment.

## DOIs / references that look suspicious

- `Cauchy1841`: 19th-century geometry paper; no DOI expected. Verify the bibitem text is accurate (title, journal, year).

## Anti-patterns found and fixed

- None present: no `\textit{lead-noun:}`, no em dashes, no "leverage", no British spelling, no flair words.

## Out-of-scope items spotted

- **GeLU first-use inconsistency** (line ~1282, outside range): "GELU function" appears in raw prose without `\gls{gelu}`, so the glossary entry is not marked as used there. At line 1437, `\gls{gelu}` then auto-expands as "Gaussian Error Linear Unit (GeLU)", causing a redundant spell-out for the reader. Fix: use `\gls{gelu}` at line 1282 so it abbreviates correctly at 1437. This is a boundary issue outside my range.
