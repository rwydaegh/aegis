# Report: COMPLIANCE (wave 2)

Range: lines 1349-1547.

## Edits applied

- Numeric ranges converted from "to" to en-dash (3 instances):
  - fat d2 approx 5 to 20mm -> 5--20mm
  - Tlay reaching 1.6 to 1.8 -> 1.6--1.8
  - factors of 2 to 4 -> 2--4

## Tougher questions for the author

- Section-opening redundancy: "The closed forms reduce regulatory compliance to closed-form functions..." has "closed forms" and "closed-form" in the same clause. A light reword such as "The main results of this paper reduce regulatory compliance to explicit functions of three precomputed scalars..." would remove the echo without touching science. Left as-is; flagged for author.

- Missing connective at remark boundary (~line 1395): "Under realistic plane-wave or multipath exposure the directivity is substantially below this worst case..." follows the worst-case finding without an explicit contrast connective. Adding "However," or "Conversely," at the start would match the author's pattern. Left as-is to stay within style-polish scope.

- approx. vs. approximately: The paper consistently uses approx.\ throughout (~15 occurrences), including twice at line 1490 inside this range. The STYLE_ANALYSIS says "approximately" is preferred in body prose, but replacing only in-range instances would create inconsistency. A whole-document pass should decide.

## DOIs / references that look suspicious

None in this range beyond what wave-1 flagged for Cauchy1841.

## Anti-patterns found and fixed

- Three numeric "to" ranges replaced with en-dash (see edits applied).

## Patterns confirmed correct

- Quotation glyphs: no straight quotes present.
- Introductory adverbials: none present in this range; no comma-omission errors.
- Forbidden verbs/intensifiers: no "leverage", "obviously", "clearly", "very", "really" found.
- British English: none found.
- Italic discipline: no \textit{} or \emph{} present; no anti-pattern italic leads.
- \mathrm{} on noun subscripts: \mathrm{SAR}_{\mathrm{wb}}, P_{\mathrm{abs}}, A_{\mathrm{CH}}, \delta_{\mathrm{SAR}}, \mathbf{S}_{\mathrm{ab}}, \langle\mathrm{SAR}\rangle_{\mathrm{cube}} -- all correct.
- \Sinc^{\max}: \max is a standard upright math operator, effectively \mathrm{max}. Correct.
- Equation punctuation: \, , inside all four equations already applied by wave-1.
- Table captions (tab:anthro, tab:depth): sentence case, descriptive, end with a period.
- Subsection titles: sentence case confirmed on all three subsections (applied by wave-1).
- Hedging discipline: measurements are sharp numbers; interpretive claims appropriately hedged.
- Result-then-reason: the remark paragraph states numbers ($61\%$, $32\%$, $1\%$) then the implication. Thin-skin and sub-6 GHz paragraphs follow the same pattern.
- Topic-first paragraphs: each subsection body paragraph opens with the key claim or setup condition.
- Non-breaking ties: consistent throughout.

## ReLU / GeLU coordination note

Both terms are hand-spelled at their only body occurrence (lines 1435 and 1437): "Rectified Linear Unit (ReLU)" and "Gaussian Error Linear Unit (GeLU)". The glossaries package was removed (preamble comment at line 34 confirms). The wave-1 report references to \gls{relu} and \gls{gelu} described the pre-wave-1 state; the current file is already correct. No action needed from the CORRECTIONS wave-2 agent.

## Out-of-scope items spotted

- Source line break between "The Hadamard product with" and "$\mathbf{V}$ gates..." (~line 1440) is cosmetically awkward in source but renders correctly in PDF. Not a style error.
