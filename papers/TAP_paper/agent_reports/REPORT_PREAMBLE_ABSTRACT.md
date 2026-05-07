# Report: PREAMBLE_ABSTRACT

## Edits applied

- **Abstract unit formatting (8 conversions)**: Replaced math-mode thin-space units (`$1$ to $100\,$GHz`, `$28\,$GHz`, `$6\,$GHz`, `$5.8\,$GHz`, `$6$ to $100\,$GHz`) with tilde-glued plain-text form (`1 to 100~GHz`, `28~GHz`, etc.), per the briefing's preferred style for literal numeric values.
- **Abstract percent signs (2 conversions)**: Removed unnecessary math-mode wrapping from `$5.6\%$` and `$0.35\%$` — replaced with plain-text `5.6\%` and `0.35\%` for prose context.
- **Abstract plain integers (2 conversions)**: `$168$ volunteers` and `$5$ FDTD phantoms` converted to `168 volunteers` and `5 FDTD phantoms`. Small counts in prose do not need math mode.
- **Source line-break hygiene (2 fixes)**: Reflowed two awkward mid-clause breaks in the abstract source:
  - `a pseudo-Brewster compensation\nthat puts` joined into one source line.
  - `Validation\nruns against Mie theory` joined as `Validation runs against Mie`.

## Tougher questions for the author

- **Hyperref colors** (`linkcolor=blue,citecolor=blue,urlcolor=blue`): All blue is sane for a preprint/review copy but IEEE TAP production will strip color links. If submitting in final form, consider `colorlinks=false` or all-black. Left as-is.
- **`$1.012$` in abstract**: This is a dimensionless ratio (Sim4Life FDTD result). Kept in math mode as a precise numeric result, not a prose count. Seems intentional — verify.

## DOIs / references that look suspicious

None — this range does not include the bibliography.

## Anti-patterns found and fixed

- Math-mode wrapping of plain prose numbers and units (`$1$`, `$100\,$GHz`, `$5.6\%$`, etc.) — all converted to tilde-glued or plain text.
- Two awkward source-level line breaks splitting clauses mid-phrase — reflowed.

## Patterns introduced

None needed in this range.

## Out-of-scope items spotted

- **Lines 1435–1437** (`\gls{relu}` and `\gls{gelu}`): Both acronyms appear only once each in the body via `\gls{}`. Briefing rule 8: spell out single-use acronyms, skip `\gls{}`. The `\newacronym` definitions on lines 36–37 are in my range but removing them without fixing the body calls would break compilation. Left in place — flagging for coordinated cleanup.
- **`\markboth` running head** (lines 106–109): `\MakeLowercase{\textit{et~al.}}` is standard IEEE style, no action needed.
- **`\SabAvg` macro** (line 70): `\langle S_{\mathrm{ab}}\rangle_{4\,\mathrm{cm}^2}` uses thin-space `\,` inside math mode — correct and intentional, leave alone.
