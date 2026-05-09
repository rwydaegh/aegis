# Report: SUPPLEMENTARY (wave 2)

Note: original Write was blocked by the harness; this report reconstructed from the agent's inline summary.

## Edits applied

**Eq. S18 (Du Bois, line 627)**: bare `\,` → `\, ,`. Sentence continues ("in m² with mass m in kg…"), so a comma is required. Wave-1 flagged this; the surrounding prose makes the grammatical case clear.

**Numeric ranges — `" to "` → `--`** (five instances in body prose):
- `0.3 to 100~GHz` → `0.3--100~GHz` (§S2.3, frequency window)
- `$d_2 \approx 5$ to 20~mm` → `$d_2 \approx 5$--20~mm` (§S3.2 three-layer model)
- `0.3 to 10~GHz` → `0.3--10~GHz` (§S3.2 figure-reference sentence)
- `$2$ to $4$ for typical anatomy` → `$2$--$4$ for typical anatomy` (§S3.5)
- `$5\%$ to $14\%$` → `5--14\%` (§S4 Mie residual paragraph)
- Left unchanged: title "1 to 100~GHz" (established title form matching main paper), bibliography "up to 3~GHz"/"up to 30~GHz" (prepositions, not ranges), all prose "to" prepositions.

**`\text{}` → `\mathrm{}`** in underbrace subscripts (Mie error decomposition equation):
- `_{\text{Fresnel}}` → `_{\mathrm{Fresnel}}`
- `_{\text{diffraction}}` → `_{\mathrm{diffraction}}`
- These are noun-like labels; `\mathrm{}` is the author's convention for noun subscripts.

**`approx.\` → `approximately`** in flowing body prose (four instances):
- `at approx.\ 175~MHz` → `at approximately 175~MHz` (§S3.5 parenthetical)
- `cartilage thickness approx.\ 2~mm` → `cartilage thickness approximately 2~mm`
- `forearm diameter approx.\ 60~mm` → `forearm diameter approximately 60~mm`
- `at approx.\ 39~GHz` → `at approximately 39~GHz` (Mie section)
- Left unchanged: `\paragraph{Whole-body resonance, below approx.\ 300~MHz.}` — tight technical heading, abbreviation appropriate.

## DOIs to add (author must fact-check before inserting)

Nine references, none have DOIs. The following have findable DOIs:
- **Diao2024** — IEEE TEMC vol. 66, no. 5, 2024: likely DOI `10.1109/TEMC.2024.3370219`
- **Azzam2015** — J. Mod. Opt. vol. 62, no. 10, 2015: likely DOI `10.1080/09500340.2015.1005186`
- **Gabriel1996** — Phys. Med. Biol. vol. 41, no. 11, 1996: likely DOI `10.1088/0031-9155/41/11/003`
- **Dimbylow2002** — Phys. Med. Biol. vol. 47, no. 16, 2002: likely DOI `10.1088/0031-9155/47/16/302`
- **DuBois1916** — Arch. Intern. Med. vol. 17, no. 6, 1916: likely DOI `10.1001/archinte.1916.00080130010002`
- **Hirata2007corr** — conference paper; check IEEE Xplore
- `Chew1995`, `Durney1986` — books, no DOI expected
- `ITISv5` — web resource with URL, no DOI needed

**Do not insert DOIs without author verification.**

## Anti-patterns fixed

- `" to "` as numeric range (5 body-prose instances) → `--`
- `\text{...}` for noun-like underbrace subscripts → `\mathrm{...}`
- `approx.\` in flowing prose (4 instances) → `approximately`
- Bare `\,` at equation end whose sentence continues (Du Bois) → `\, ,`

## Out-of-scope items confirmed clean (no edits needed)

- `\paragraph{}` headings: valid fourth-level structure, not the `\textit{lead-noun:}` anti-pattern.
- Abstract: `Section~\ref{}` form throughout — IEEE-friendly, consistent.
- No em dashes, no British spelling, no "leverage"/"clearly"/"obviously"/"very", no `siunitx`, no `\gls{}` in abstract.
- All captions: period-terminated, sentence case, descriptive (not lead-with-finding) — correct for IEEE TAP.
- All tables: booktabs format, captions above, no vertical rules.
- `hotspot` (no hyphen) consistent throughout the SI.
