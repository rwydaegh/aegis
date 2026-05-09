# Report: Higher-order corrections (wave-2)

**Range**: lines ~1216 to ~1348 (`\section{Higher-order corrections}` through `\subsection{Error budget}` figure).

---

## Edits applied

- **`eq:curv-update` terminal punctuation** (line 1240): Added `\,` before the closing comma — changed `V_{ji},` to `V_{ji}\, ,`. The sentence after the equation continues ("adding a quadratic gate…"), so a comma is correct; it just needed the thin space per the author's equation-termination convention.

- **`eq:gelu` terminal punctuation** (line 1276): Added `\,` before the closing comma — changed `\sqrt{\lambda / (2\pi R_j)},` to `\sqrt{\lambda / (2\pi R_j)}\, ,`. Same rationale (sentence continues with "which is…").

- **GELU first-use spelling** (line 1278): Changed `which is the GELU function` to `which is the Gaussian Error Linear Unit (GELU) function`. This is the first prose appearance of the acronym in the paper; the earlier `\label{eq:gelu}` is not prose. The spell-out now correctly precedes all later shorthand uses.

---

## Tougher questions for the author

- **Table column header `$R$\,[mm]`** (line 1250): Uses thin-space + square bracket form. The paper is inconsistent: line 616 uses `$\sigma$ [S/m]` (space + bracket) and line 585 uses `$T_s$ (TE)` (parentheses). IEEE TAP house style slightly prefers parentheses for units in column headers, but changing only this table while leaving others would create a new inconsistency. Recommend a uniform pass across all table headers in the paper — out of scope for this agent.

- **GELU capitalization**: line 1278 now uses "GELU" (all caps, matching the `\label{eq:gelu}` and the Hendrycks 2016 citation which uses "GELUs"). Line ~1437 (outside range) uses "GeLU" (mixed case). The author should decide on one form. All-caps GELU is the more common IEEE/ML convention.

---

## Anti-patterns found and fixed

- Missing `\,` (thin space) before equation-terminating punctuation in two display equations (`eq:curv-update` and `eq:gelu`). Fixed.
- Raw `GELU` abbreviation used on first prose appearance without spelling out. Fixed.

---

## Patterns introduced

- GELU spelled out as "Gaussian Error Linear Unit (GELU)" at first prose mention, consistent with the author's first-mention-by-hand rule (STYLE_ANALYSIS §3.2).

---

## Out-of-scope items spotted

- **Line ~1437** (Compliance section): `Gaussian Error Linear Unit (GeLU)` spells out GeLU a second time — now redundant since it was already spelled out at line 1278 (this fix). That section's agent should reduce it to just "GeLU" or "GELU" (whichever form the author chooses).

- **Preamble comment** (lines 34-35): Reads "relu and gelu were the only acronyms defined, each appearing once; both are now spelled out inline in the body." After the line 1278 fix, GELU appears at both 1278 and ~1437. The comment is stale and should be updated (outside this range).

- **Table `$R$\,[mm]` header** (line 1250): Flagged above. Not changed to avoid introducing a new partial inconsistency.

- **"First, … Second, …" structure** (lines 1295-1300): Parallelism is clean — both branches are grammatically parallel subject-verb clauses with mechanisms following results. No action needed.

- **No forbidden intensifiers** ("very", "clearly", "obviously", "leverage", "remarkably") found in this range.

- **No straight quotation marks** in range. The `\`\`Fresnel only,'' ...'' labels use correct LaTeX glyphs.

- **No British spellings** in range.

- **All hyphenated compounds** (`body-part`, `whole-body`, `body-averaged`, `Inter-body`, `first-bounce`, `flux-weighted`, `convex-hull`) are correct per the style guide.

- **Noun-like subscripts** in this section (e.g., `f_{\mathrm{global}}`) are already in `\mathrm{}`. The macros `\Sab`, `\Sinc`, `\Tbar` expand to the correct forms.

- **Result-then-reason structure** is well observed throughout the Error budget subsection — error magnitudes lead each sentence, mechanisms follow.

- **Topic-first paragraphs**: Error budget opens with `\Cref{fig:err-budget} shows…` (figure-reference lead). Other subsections open with definitional/framing sentences appropriate to their context. Structure is sound.
