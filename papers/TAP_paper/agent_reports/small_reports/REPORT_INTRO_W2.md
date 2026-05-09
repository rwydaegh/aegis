# Report: INTRO wave-2

## Edits applied

### Numeric ranges — "to" → en-dash
All prose numeric ranges in the intro body converted to en-dash form:

- `$\eta(f) \approx 0.50$ to $0.56$ across $1.45$ to $5.8\,$GHz` → `$0.50$--$0.56$ across $1.45$--$5.8$~GHz` (Bamba sentence)
- `from 7 to 11~GHz` → `from 7--11~GHz` (Flintoft sentence)
- `$\xi$ of $0.45$ to $0.65$ above 6~GHz` → `$0.45$--$0.65$ above 6~GHz` (Zhang sentence)
- `from $10$ to 100~GHz` → `from 10--100~GHz` (Kodera sentence; also eliminated the mid-range line break)
- `from 1 to 100~GHz` → `from 1--100~GHz` (enumerate item 5 and summary paragraph, twice)
- `and from 6 to 100~GHz` → `and from 6--100~GHz` (summary paragraph)

Note: `from 1 to 100\,GHz` in the title (line 92) was intentionally left unchanged.

### Verb register
- `divide by ..., to obtain a normalized cross-section` → `divide by ..., yielding a normalized cross-section` (Flintoft sentence). Avoids the "to obtain" construction.

### Connectives
- Added `However,` before "these works fit empirical scalars" to mark the explicit logical pivot from literature survey to gap statement. This is the key connective in the intro — it bridges the survey to the critique.

## Tougher questions for the author

- **`approx.\`** appears twice in para 1 (`approx.\ $10^{8}$`, `approx.\ $10^{12}$`). Style guide says "approximately" should generally be written out, abbreviation allowed only in tight technical contexts. Borderline here — leave as-is or replace with "approximately $10^{8}$".

## DOIs / references that look suspicious

None in intro range. No DOIs are present on any intro-cited reference.

## Anti-patterns found and fixed

- Six "X to Y" numeric ranges in the intro body using prose "to" instead of en-dash `--`: all converted.
- `to obtain` after a participial: replaced with `yielding`.
- Missing `However,` before the gap-statement sentence: added.

## Patterns introduced

- En-dash numeric ranges throughout the intro body (consistent with abstract, which already had them).
- `However,` connective at the literature-critique pivot.
- `yielding` replacing `to obtain`.

## Out-of-scope items spotted

- Line 1190 (validation table): `$\eta(f) = 0.50$ to $0.56$ at $1.5$ to $5.8$~GHz` — still uses "to" form; outside intro range.
- Line 877: `within $5\%$ to $10\%$ across $1.45$ to` — outside intro range.
