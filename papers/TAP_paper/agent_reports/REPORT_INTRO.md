# Report: INTRO

## Edits applied

- **`itemize` converted to `enumerate`** for the novelty list (lines ~206-223). Primary structural change requested.
- **Unit format normalized** throughout the intro: converted `$X\,$GHz` thin-space-in-math style to `X~GHz` tilde-glued style for all prose occurrences where the number is a plain literal. Conversions made:
  - `below $6\,$GHz` / `above $6\,$GHz` (paragraph 1)
  - `$10\,$g cube` (paragraph 1 and enumerate item 4)
  - `6~GHz that grows ... near 100~GHz` (cell-count sentence)
  - `from 7 to 11~GHz` (Flintoft range)
  - `above 6~GHz on $48$ subjects` (Zhang)
  - `from $10$ to 100~GHz` (Kodera range)
  - `at 28~GHz` (Diao)
  - `the 3~GHz dip` (three occurrences across paragraphs 2, 3, and summary)
  - `from 1 to 100~GHz` and `from 6 to 100~GHz` (summary paragraph)
  - `Below 6~GHz,` (was `Sub-$6\,$GHz`)
  - `the 10~g cube SAR` (flowchart description paragraph and caption)
  - `in the sub-5~GHz Fabry-Perot regime` (flowchart paragraph)
  - `4~cm$^2$ window` (flowchart caption)
  - `A sub-5~GHz branch` (flowchart caption)
  - `below 5~GHz` (roadmap paragraph)
  - `from 1 to 100~GHz` (enumerate item 5)
- **ICNIRP spelled out in Fig. 1 caption**: Changed "by ICNIRP" to "by the International Commission on Non-Ionizing Radiation Protection (ICNIRP)" per rule 8.
- **`Sub-$6\,$GHz behavior follows`** rewritten as `Below 6~GHz, behavior follows` for cleaner prose.

Left unchanged (intentionally):
- `$1.45$ to $5.8\,$GHz` in the Bamba sentence: decimal math range, conversion would break internal consistency of that expression.
- TikZ node label `Sub-5\,GHz` inside `\node{...}`: tight figure label, not running prose.

## Tougher questions for the author

- **"Below 6~GHz, behavior follows from the layered correction."** The rewrite is grammatically clean but the original "Sub-$6\,$GHz behavior" was a compound adjective modifying a noun. If preferred, alternative: "Behavior below 6~GHz follows from the layered correction."
- **ICNIRP in the flowchart caption**: Spelling it out adds length. If the journal copy-editor shortens the caption, the parenthetical "(International Commission on Non-Ionizing Radiation Protection)" could be dropped there since the first body-text introduction already covers it.

## DOIs / references that look suspicious

- **`\bibitem{Bamba2014}`**: Key implies 2014 but the entry says "Feb. 2013" (`Bioelectromagnetics`, vol.~34, no.~2). Likely an early-view vs. print-issue discrepancy common in that journal. Verify if disambiguation matters.
- No DOIs are present on any intro-cited references; the author's consistent style omits them. Nothing AI-fabricated to flag.

## Anti-patterns found and fixed

- `\begin{itemize}` for a numbered novelty list: converted to `\begin{enumerate}`.
- `Sub-$6\,$GHz` starting a sentence as a compound adjective: replaced with `Below 6~GHz,`.
- ICNIRP unspelled in flowchart caption: fixed.

## Patterns introduced

- Numbered novelty list with `enumerate`.
- Consistent `X~GHz` form in intro prose.
- ICNIRP spelled out on first caption appearance.

## Out-of-scope items spotted

- `$5.8\,$GHz` (Bamba range) and `$7$ to $11\,$GHz` were partially converted; `5.8~GHz` was left as-is. Other agents handling later sections will see the same `$X\,$GHz` math-thin-space pattern throughout the body.
- No `equation` environments in the intro; equation-punctuation rule does not apply here.
- The flowchart caption is long with the ICNIRP expansion. If the overall caption budget is tight, the author may want to consider a shorter form.
