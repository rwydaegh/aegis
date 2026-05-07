# Report: CORRECTIONS (lines 1224-1348)

Section: `\section{Higher-order corrections}` and its four subsections (Curvature, Diffraction at the shadow boundary, Inter-body reflections, Error budget).

## Edits applied

- **Section title sentence case**: `Higher-Order Corrections` → `Higher-order corrections`
- **Subsection titles sentence case** (3 fixes):
  - `Diffraction at the Shadow Boundary` → `Diffraction at the shadow boundary`
  - `Inter-Body Reflections` → `Inter-body reflections`
  - `Error Budget` → `Error budget`
  - (`Curvature` was already correct single-word.)
- **Inter-body reflections paragraph split**: broke the monolithic paragraph at the topic-shift ("Two effects keep the body-averaged correction small.") into two paragraphs. The first sets up the model; the second analyses the two effects numerically.
- **First/Second connectives added**: "First, the bound $f \le 1 - \eta$ self-compensates..." and "Second, specular reflection at mmWave..." for parallel structure. Replaces a weak "The bound...Specular reflection..." sequence.
- **Line wrap fixes**: reformatted awkward overlong line in the diffraction paragraph and a similar issue in the inter-body reflections paragraph.

## Anti-patterns found and fixed

- Title case in section/subsection headings (4 instances): all corrected to sentence case per IEEE TAP convention.
- No `\textit{lead-noun:}` paragraph leaders were present in this section.

## Tougher questions for the author

- **Table `tab:curv-mag` column header**: `$R$\,[mm]` uses `\,[mm]` (thin space + bracket notation). IEEE TAP typically prefers parentheses: `$R$ (mm)`. Minor but worth consistency check against other tables.
- **Error budget: figure not table**: this subsection has a figure (`fig:err-budget`), not a table. The figure caption is descriptive, ends with a period, and is in sentence case. No issue, but the author may want to consider whether a supplementary tabular summary (Fresnel 5.6%, diffraction up to 14%, inter-body <2%, dielectric ±7%) would strengthen the error budget for reviewers.
- **`\pospart{}` macro**: used in `eq:curv-update`. Verify it is defined in the preamble and renders as $[\cdot]_+$ as intended.

## DOIs / references that look suspicious

- None within this range. `\cite{Hendrycks2016}` (GELU paper) and `\cite{AlekseevZiskin2007}` (IT'IS Cole-Cole) look like real references.

## Out-of-scope items spotted

- `\section{Compliance and Corollaries}` at line 1348 (just below boundary): "Corollaries" should likely be lowercased — `Compliance and corollaries`. Another agent should handle.
- `$28\,$GHz` thin-space-inside-math pattern is used consistently throughout the entire paper, not just this section. Converting only this section would create inconsistency; left as-is. Recommend a global pass.
