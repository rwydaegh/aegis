# Report: END_MATTER_BIB — Wave 2

Assigned range: lines 1721 to end of file (Acknowledgment, `thebibliography`, `\IEEEbiography` blocks).

---

## Suspicious references — consolidated list

This is the key deliverable. Every reference with a confirmed or plausible problem is listed here.

### 1. `Bamba2014` — confirmed key/year mismatch (HIGHEST PRIORITY)

- **Cite key**: `Bamba2014`
- **Entry date**: Feb. 2013 (`Bioelectromagnetics`, vol.~34, no.~2, pp.~122--132)
- **PubMed confirmation**: PMID 22926824. Published February 2013; epub August 24, 2012. DOI: 10.1002/bem.21749.
- **Verdict**: The paper was never published in 2014. The key suffix `2014` is wrong. The entry data itself is correct (Feb. 2013). The cite key cannot be renamed without breaking all `\cite{Bamba2014}` calls in the body.
- **Action for author**: Decide whether to tolerate the mismatch or do a global find/replace `Bamba2014` -> `Bamba2013` in `paper.tex` and `paper_SI.tex`. No body edit was made here.

### 2. `Zhukov1998` — page range error (confirmed by DBLP BibTeX)

- **Old entry**: `pp.~45--55`
- **DBLP canonical BibTeX**: pages = {45-56} (confirmed via DBLP record `conf/rt/ZhukovIK98`, ISBN 3-211-83213-0, DOI 10.1007/978-3-7091-6453-2_5)
- **Verdict**: Off-by-one on the end page. Wave-1 flagged "Iones" as a possible transliteration issue — DBLP confirms `Iones, Andrei` is the correct transliteration.
- **Fix applied in this wave**: Changed `pp.~45--55` to `pp.~45--56`.

### 3. `Hendrycks2016` — non-standard arXiv format (fixed)

- **Old**: `Jun. 2016, \emph{arXiv:1606.08415}.`
- **Problem**: `\emph{arXiv:...}` is non-standard for IEEE. Wave-1 flagged both arXiv entries as needing normalization.
- **Fix applied**: Converted to IEEE `[Online]. Available:` form.
- **arXiv ID verified**: 1606.08415 is correct (Hendrycks and Gimpel, "Gaussian Error Linear Units").

### 4. `SionnaRT` — non-standard arXiv format (fixed)

- **Old**: `Mar. 2023, \emph{arXiv:2303.11103}.`
- **Fix applied**: Converted to IEEE `[Online]. Available:` form.
- **arXiv ID verified**: 2303.11103 is correct. Author list (Hoydis, Ait Aoudia, Cammerer, Nimier-David, Binder, Marcus, Keller) verified against arXiv — matches entry exactly.

### 5. `Hirata2021` — title-case error (fixed)

- **Old**: `energy above 6\,GHz: Review of computational dosimetry studies,''`
- **Problem**: "Review" is capitalized after a colon in a sentence-case title. In IEEE style, article titles are in sentence case; words after a colon are not capitalized unless they are proper nouns.
- **Fix applied**: `Review` -> `review`.

### 6. `Samaras2019` — verified correct

- **Entry**: vol.~40, no.~2, pp.~136--139, Feb. 2019
- **PubMed verification** (fetched directly): vol. 40, issue 2, pp. 136--139, Feb. 2019, DOI 10.1002/bem.22170. Correct.
- Earlier web searches erroneously returned vol. 41, pp. 348--359 (that is a different Christ et al. 2020 paper). No change needed.

### 7. No DOIs anywhere in the bibliography

Wave-1 already flagged this. None of the 32 entries carries a DOI. IEEE TAP encourages DOIs. Author should add them before submission. Several confirmed DOIs for reference: ICNIRP2020 = 10.1097/HP.0000000000001210; Bamba (2013) = 10.1002/bem.21749; Samaras2019 = 10.1002/bem.22170; Flintoft2014 = 10.1088/0031-9155/59/13/3297; Hirata2021 = 10.1088/1361-6560/abf1b7; Ohman1977 = 10.1109/TAP.1977.1141718. These must be fact-checked before inserting. No DOIs were invented here.

---

## Edits applied

1. **`Zhukov1998` page range corrected**: `pp.~45--55` -> `pp.~45--56` (confirmed by DBLP BibTeX).
2. **`Hendrycks2016` arXiv format normalized**: `Jun. 2016, \emph{arXiv:1606.08415}.` -> `Jun. 2016. [Online]. Available: \url{https://arxiv.org/abs/1606.08415}`
3. **`SionnaRT` arXiv format normalized**: `Mar. 2023, \emph{arXiv:2303.11103}.` -> `Mar. 2023. [Online]. Available: \url{https://arxiv.org/abs/2303.11103}`
4. **`Hirata2021` title sentence case fixed**: `Review of computational dosimetry studies` -> `review of computational dosimetry studies`

---

## Full key/year audit — all 32 bibitem keys

| Key | Key suffix | Entry year | Status |
|-----|------------|------------|--------|
| `ICNIRP2020` | 2020 | May 2020 | OK |
| `Kodera2024` | 2024 | Jan. 2024 | OK |
| `Diao2024` | 2024 | Oct. 2024 | OK |
| `Bamba2014` | **2014** | **Feb. 2013** | **MISMATCH** |
| `Flintoft2014` | 2014 | Jul. 2014 | OK |
| `Zhang2017thesis` | 2017 | 2017 | OK |
| `ZhangRobinson2020` | 2020 | Apr. 2020 | OK |
| `Azzam2015` | 2015 | Jun. 2015 | OK |
| `Cauchy1841` | 1841 | 1841 | OK |
| `Zhukov1998` | 1998 | 1998 | OK |
| `Landis2002` | 2002 | Jul. 2002 | OK |
| `AkenineMoller2018` | 2018 | 2018 | OK |
| `ITISv5` | v5 (version key) | 2024 | OK |
| `Gabriel1996` | 1996 | Nov. 1996 | OK |
| `BornWolf1999` | 1999 | 1999 | OK |
| `Potter1970` | 1970 | Jul. 1970 | OK |
| `Ohman1977` | 1977 | Nov. 1977 | OK |
| `Funahashi2018` | 2018 | 2018 | OK |
| `AlekseevZiskin2007` | 2007 | Jul. 2007 | OK |
| `Tomita1999` | 1999 | 1999 | OK |
| `Chew1995` | 1995 | 1995 | OK |
| `BohrenHuffman1983` | 1983 | 1983 | OK |
| `Hendrycks2016` | 2016 | Jun. 2016 | OK |
| `DuBois1916` | 1916 | Jun. 1916 | OK |
| `Hirata2007corr` | 2007 | Jul. 2007 | OK |
| `Dimbylow2002` | 2002 | Aug. 2002 | OK |
| `SionnaRT` | (no year suffix) | Mar. 2023 | OK |
| `62704-1` | (standard no.) | 2017 | OK |
| `C953` | (standard no.) | 2021 | OK |
| `Hirata2021` | 2021 | Apr. 2021 | OK |
| `Samaras2019` | 2019 | Feb. 2019 | OK |
| `Durney1986` | 1986 | 1986 | OK |

One confirmed mismatch: `Bamba2014`.

---

## IEEE format compliance audit

### Month abbreviations
All bibliography entries use three-letter abbreviated months with trailing period: Jan., Feb., Apr., May (no period), Jun., Jul., Aug., Oct., Nov. No full-month forms appear in any bibitem. Consistent throughout.

### Page ranges
All `pp.~` entries use `--` (en-dash). No hyphens used for ranges. After Zhukov fix: `45--56`. All others confirmed correct.

### Quotation marks in titles
All article titles use ```` ``...'' ```` (LaTeX double-tick). No straight quotes found in bibitem entries.

### vol./no./pp. structure
Journal entries carry `vol.~XX, no.~Y, pp.~MM--NN, Mon. YYYY` consistently. Exceptions:
- `Funahashi2018` (IEEE Access): no issue number — correct, IEEE Access does not use issue numbers.
- `Cauchy1841`: no issue number (19th-century journal) — acceptable.
- `Hirata2021`: `Art. no. 08TR01` instead of page range — correct for this article type.

### Title sentence case in entry titles
Article titles in IEEE bibliographies are rendered in sentence case by the bibliography processor. Only `Hirata2021` had an internal capitalization error (`Review` after colon) — fixed.

---

## Acknowledgment audit

- Heading: `\section*{Acknowledgment}` — singular, correct for IEEE TAP.
- American English confirmed. No "Acknowledgements".
- Funders: Methusalem/SHAPE and EU Horizon Europe/GOLIAT (grant No.~101057262). The mixed-case in `5G~expOsure, causaL effects, and rIsk perception through citizen engAgemenT` is intentional — the capitals spell the acronym GOLIAT. Correct as written.
- FWO and ERC are absent from this acknowledgment. Per STYLE_ANALYSIS.md §15.8, earlier papers list ERC first, then Methusalem, then FWO. Author should confirm whether FWO/ERC support this specific paper. Not modified.

---

## IEEEbiography blocks audit

Five blocks inside `\iffalse ... \fi` (disabled). All five read cleanly:
- American English throughout.
- No em dashes, no typos detected.
- `\IEEEbiography` format correct (photo include, name, membership tag).
- Degree abbreviations use `B.Sc.\`, `M.Sc.\`, `Ph.D.\` with backslash-space — correct.
- IEEE membership designations `(Member, IEEE)`, `(Senior Member, IEEE)` correct.
- Photo files referenced: `robin.png`, `luc.png`, `gunter.png`, `emmeric.png`, `wout.png` — must exist when uncommented.

---

## Tougher questions for the author

1. **`Bamba2014` key rename**: PubMed confirms this is a 2013 paper (PMID 22926824). Recommend global find/replace `Bamba2014` -> `Bamba2013` in `paper.tex` (and `paper_SI.tex` if cited there). Safe to do in a single sed pass.

2. **DOIs**: Add before submission. `\newcommand*{\doi}[1]{\href{https://doi.org/#1}{#1}}` should be added to the preamble if DOIs are added. Never invent — verify each one.

3. **FWO/ERC in Acknowledgment**: Verify whether either funder applies to this paper.

4. **`Tomita1999`**: `J. Tokyo Med. Univ.` is not indexed in major databases; the entry could not be independently verified. Low risk (body-surface-area classical reference), but flagged.

5. **`Durney1986` report number**: `USAFSAM-TR-85-73` appended after publisher is non-standard. Consider moving to a parenthetical: `1986 (Tech. Rep. USAFSAM-TR-85-73)`. Low priority.

---

## Anti-patterns found and fixed

- `\emph{arXiv:XXXXXXX}` non-standard IEEE arXiv format in `Hendrycks2016` and `SionnaRT` — normalized to `[Online]. Available: \url{...}`.
- Off-by-one page range in `Zhukov1998` — corrected.
- Title-case error in `Hirata2021` article title — corrected.

## Out-of-scope items spotted

- `\providecommand{\url}[1]{#1}` at top of `thebibliography` is a no-op when `hyperref` is loaded. Harmless; left untouched.
- `pp.~77\,665--77\,674` (Funahashi2018) — `\,` is a thousands separator for IEEE Access large page numbers. Acceptable convention; left untouched.
