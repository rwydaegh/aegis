# Report: END_MATTER_BIB

Assigned range: lines 1721 to end-of-file (Acknowledgment, `thebibliography`, `\IEEEbiography` blocks).

## Edits applied

- **Removed `\quad` separators in 6 book/proceedings bibliography entries.** All used `\quad` to separate edition/editors from publisher location, which is non-standard IEEE style. Replaced with normal whitespace in:
  - `Zhukov1998`: `Eds.\quad Vienna` → `Eds.\n  Vienna`
  - `AkenineMoller2018`: `4th~ed.\quad Boca Raton` → `4th~ed. Boca Raton`
  - `BornWolf1999`: `7th~ed.\quad Cambridge` → `7th~ed.\n  Cambridge`
  - `Chew1995`: `Media}.\quad New York` → `Media}.\n  New York`
  - `BohrenHuffman1983`: `Particles}.\quad New York` → `Particles}.\n  New York`
  - `Durney1986`: `4th~ed.\quad Brooks` → `4th~ed. Brooks`

## Tougher questions for the author

1. **`Bamba2014` year mismatch**: The cite key says `Bamba2014` but the entry dates the paper as `Feb. 2013` in *Bioelectromagnetics*, vol. 34, no. 2. If the paper appeared online in 2013 and in print in 2014, the entry date should be verified. The key cannot be renamed without breaking body `\cite{Bamba2014}` calls.

2. **Biographies inside `\iffalse`**: The five `\IEEEbiography` blocks are currently disabled. They read cleanly in American English and are well-formatted. If the paper adds author bios before submission, uncomment this block and add photo files (`robin.png`, `luc.png`, `gunter.png`, `emmeric.png`, `wout.png`).

## DOIs / references that look suspicious

**No DOIs are present anywhere in the bibliography.** Nothing to flag for invented DOIs. Recommend adding DOIs before final submission (IEEE TAP encourages them).

### Reference data worth manually verifying

- **`Bamba2014`** — cite key year (2014) contradicts entry year (Feb. 2013). Verify publication year.
- **`Landis2002`** — "ACM SIGGRAPH 2002 Course Notes, vol. 16, pp. 87--102." Unusual citation for a course note; verify volume/page numbers.
- **`Cauchy1841`** — historical article, difficult to verify. Low-risk.
- **`Zhukov1998`** — check author spelling "Iones" and page range pp. 45--55.

## Anti-patterns found and fixed

- `\quad` used as inter-field separator in 6 book/proceedings `\bibitem` entries. Non-standard; removed.

## Patterns introduced (if applicable)

None new. The Acknowledgment is correctly headed `\section*{Acknowledgment}` (singular, IEEE TAP convention). American English confirmed throughout. No `\gls{}` in bibliography. Journal titles use `\emph{}` consistently. No em dashes (`---`) in range.

## Out-of-scope items spotted

- `\,` inside page numbers for large IEEE Access pages (`pp.~77\,665--77\,674` in `Funahashi2018`) — acceptable typographic convention, left untouched.
- Both arXiv entries (`Hendrycks2016`, `SionnaRT`) use `\emph{arXiv:XXXXXXX}` format rather than IEEE's `[Online]. Available:` style. Left as-is for internal consistency; author may standardize before submission.
- `\vspace{6pt}` before `\iffalse` biography block is harmless filler while the block is disabled.
