# Report: PREAMBLE_ABSTRACT (wave 2)

## Edits applied

- **Abstract: four numeric ranges converted to en-dash form**
  - `1 to 100~GHz band` → `1--100~GHz band` (line ~116)
  - `$0^\circ$ to $75^\circ$` → `$0^\circ$--$75^\circ$` (line ~123)
  - `from 1 to 100~GHz` → `from 1--100~GHz` (line ~131)
  - `from 6 to 100~GHz` → `from 6--100~GHz` (line ~132)

- **Preamble: removed `\newacronym{relu}` and `\newacronym{gelu}`** — both acronyms appeared exactly once each in the body (verified via grep). Single-use acronyms do not belong in the glossaries table; both spelled out inline.

- **Preamble: removed `\usepackage{glossaries}` and `\makeglossaries`** — after removing the two `\newacronym` entries there are zero `\gls{}`, `\glspl{}`, or `\newacronym` calls remaining anywhere in the file (confirmed with grep). Entire package was dead weight. Both lines replaced with a single explanatory comment.

- **Body lines 1435–1437 (out of range, but required for compilation safety)**: replaced `\gls{relu}` with `Rectified Linear Unit (ReLU)` and `\gls{gelu}` with `Gaussian Error Linear Unit (GeLU)`. This edit was necessary to prevent a compilation error after removing the `\newacronym` definitions. No other changes in those lines.

## Tougher questions for the author

- **Title range form**: The manuscript title on line 92 reads `from 1 to 100\,GHz`. Left as-is — IEEE paper titles use prose form and the title is the official name of the work.
- **"from 1--100~GHz" phrasing**: After the edit, abstract reads "from 1--100~GHz". The en-dash without "to" is slightly awkward after "from". More idiomatic alternatives: "across 1--100~GHz" or "over 1--100~GHz". Left as edited per briefing's explicit instruction; author should decide.

## DOIs / references that look suspicious

None — lines 1–150 do not include the bibliography.

## Anti-patterns found and fixed

- Four `X to Y~GHz` prose ranges in the abstract using word "to" instead of en-dash `--`.
- Two single-use `\newacronym` entries (relu, gelu) driving an otherwise-empty `glossaries` package. Entire glossaries infrastructure removed cleanly.

## Patterns introduced

None needed. Abstract and preamble were structurally correct from wave-1; this wave handled long-tail glyph and dead-code cleanup only.

## Out-of-scope items spotted

- **Lines 218, 239–240** (introduction body, outside range): two more `from 1 to 100~GHz` and `from 6 to 100~GHz` constructions using `to` instead of `--`. Flagged for INTRO agent.
- **Line 92 (title)**: uses thin space `\,` before `GHz` rather than the non-breaking tie `~` used throughout the body. IEEE title formatting is distinct from body style.
- **All macros verified as used**: `\khat`, `\nhat`, `\rr`, `\EE`, `\Sinc`, `\Sab`, `\Aab`, `\Aperp`, `\Teff`, `\Tavg`, `\Tbar`, `\Tlay`, `\ntilde`, `\diff`, `\pospart`, `\Vis`, `\SabAvg`, `\RE`, `\censorphantom` — all have at least one call site. No dead macros.
- **Subscript discipline verified**: `\Sinc` → `S_{\mathrm{inc}}`, `\Sab` → `S_{\mathrm{ab}}`, `\SabAvg` → `\langle S_{\mathrm{ab}}\rangle_{4\,\mathrm{cm}^2}` — all noun-like subscripts correctly use `\mathrm{}`.
