# LaTeX Quality Checklist for IEEE Papers

## Spacing and ties

1. Non-breaking tilde `~` before every `\cite{}`, `\ref{}`, `\eqref{}`, `\figurename`, `\tablename` reference, and section reference. "as shown in Fig.~\ref{...}", "see~\cite{...}", "Section~\ref{...}".
2. Non-breaking tilde between numbers and units: `5~\text{GHz}`, `28~\mathrm{GHz}`, never `5 GHz` with a regular space.
3. Non-breaking tilde inside names that shouldn't break: `Dr.~Smith`, `J.~Doe`, `et~al.`
4. `\,` (thin space) between number and unit in math mode if not using siunitx: `28\,\mathrm{GHz}`. Pick siunitx OR manual `\,` and stick with one across the paper.
5. Use `siunitx` (`\SI{28}{\giga\hertz}`, `\num{1.5e-3}`) for everything numerical if you commit to it — handles spacing, exponents, ranges, and uncertainty consistently.
6. `\dots` not `...`, and `\ldots` vs `\cdots` chosen by context (`a, b, \ldots, z` vs `a + b + \cdots + z`).
7. Inter-sentence spacing: `\@.` after capital-letter abbreviations ending sentences, or `\frenchspacing` globally if you don't want LaTeX's double space after periods.
8. `e.g.,` and `i.e.,` with the comma, and `\eg` / `\ie` macros if you want to enforce non-breaking spacing after them (`e.g.\ something` to prevent the inter-sentence space bug).
9. Each formula is punctuated within their sentences. There is always a small gap after last symbol (e.g. \,) before the punctuation.

## Dashes and quotes

9. Hyphen `-` for compound words (`ray-tracing`), en-dash `--` for ranges (`pp.~10--15`, `2020--2024`), em-dash `---` for parenthetical breaks. Never use a hyphen for a range.
10. Proper LaTeX quotes: `` `single' `` and ` ``double'' `, never straight quotes `"..."` or `'...'`.
11. Minus sign in math: `$-5$`, not a hyphen `-5` in text mode for a negative number.

## Citations (manual `\bibitem` style, no BibTeX)

12. Use `thebibliography` environment with explicit `\bibitem{key}` entries — full control, no `.bib` headaches.
13. **Order entries in the order they first appear in the text.** IEEE numeric style requires this. When you add a new citation mid-draft, renumber and reorder the bibitems manually (or use descriptive keys like `\bibitem{ref:joseph2024}` so reordering doesn't break refs).
14. Multiple citations merged: `\cite{a,b,c}` not `\cite{a}\cite{b}\cite{c}` — IEEE renders as `[1]–[3]` correctly only when merged.
15. Each `\bibitem` follows IEEE reference format strictly. Templates below — match punctuation, italics, and abbreviations exactly.

### IEEE bibitem templates

**Journal article:**
```latex
markdown# LaTeX Quality Checklist for IEEE Papers

## Spacing and ties

1. Non-breaking tilde `~` before every `\cite{}`, `\ref{}`, `\eqref{}`, `\figurename`, `\tablename` reference, and section reference. "as shown in Fig.~\ref{...}", "see~\cite{...}", "Section~\ref{...}".
2. Non-breaking tilde between numbers and units: `5~\text{GHz}`, `28~\mathrm{GHz}`, never `5 GHz` with a regular space.
3. Non-breaking tilde inside names that shouldn't break: `Dr.~Smith`, `J.~Doe`, `et~al.`
4. `\,` (thin space) between number and unit in math mode if not using siunitx: `28\,\mathrm{GHz}`. Pick siunitx OR manual `\,` and stick with one across the paper.
5. Use `siunitx` (`\SI{28}{\giga\hertz}`, `\num{1.5e-3}`) for everything numerical if you commit to it — handles spacing, exponents, ranges, and uncertainty consistently.
6. `\dots` not `...`, and `\ldots` vs `\cdots` chosen by context (`a, b, \ldots, z` vs `a + b + \cdots + z`).
7. Inter-sentence spacing: `\@.` after capital-letter abbreviations ending sentences, or `\frenchspacing` globally if you don't want LaTeX's double space after periods.
8. `e.g.,` and `i.e.,` with the comma, and `\eg` / `\ie` macros if you want to enforce non-breaking spacing after them (`e.g.\ something` to prevent the inter-sentence space bug).

## Dashes and quotes

9. Hyphen `-` for compound words (`ray-tracing`), en-dash `--` for ranges (`pp.~10--15`, `2020--2024`), em-dash `---` for parenthetical breaks. Never use a hyphen for a range.
10. Proper LaTeX quotes: `` `single' `` and ` ``double'' `, never straight quotes `"..."` or `'...'`.
11. Minus sign in math: `$-5$`, not a hyphen `-5` in text mode for a negative number.

## Citations (manual `\bibitem` style, no BibTeX)

12. Use `thebibliography` environment with explicit `\bibitem{key}` entries — full control, no `.bib` headaches.
13. **Order entries in the order they first appear in the text.** IEEE numeric style requires this. When you add a new citation mid-draft, renumber and reorder the bibitems manually (or use descriptive keys like `\bibitem{ref:joseph2024}` so reordering doesn't break refs).
14. Multiple citations merged: `\cite{a,b,c}` not `\cite{a}\cite{b}\cite{c}` — IEEE renders as `[1]–[3]` correctly only when merged.
15. Each `\bibitem` follows IEEE reference format strictly. Templates below — match punctuation, italics, and abbreviations exactly.

### IEEE bibitem templates

**Journal article:**
```latex
\bibitem{ref:key}
F.~Lastname, F.~Lastname, and F.~Lastname, ``Title of the paper in sentence case with only first word and proper nouns capitalized,'' \emph{Abbrev. Journal Name}, vol.~12, no.~3, pp.~45--67, Mar.~2024.
```

**Conference paper:**
```latex
\bibitem{ref:key}
F.~Lastname and F.~Lastname, ``Title of conference paper,'' in \emph{Proc. Abbrev. Conf. Name (ACRONYM)}, City, Country, Mon.~2024, pp.~123--128.
```

**Book:**
```latex
\bibitem{ref:key}
F.~Lastname, \emph{Title of the Book in Title Case}, 2nd~ed. City, Country: Publisher, 2024.
```

**Book chapter:**
```latex
\bibitem{ref:key}
F.~Lastname, ``Chapter title,'' in \emph{Title of the Book}, F.~Editor, Ed. City, Country: Publisher, 2024, ch.~3, pp.~45--67.
```

**Technical report / standard:**
```latex
\bibitem{ref:key}
\emph{Title of the Standard or Report}, Standard~IEEE~802.11-2020, 2020.
```

**arXiv preprint:**
```latex
\bibitem{ref:key}
F.~Lastname and F.~Lastname, ``Title of preprint,'' 2024, \emph{arXiv:2401.12345}.
```

**Online source:**
```latex
\bibitem{ref:key}
F.~Lastname. (2024). \emph{Title of the page}. [Online]. Available: \url{https://example.com}
```

**Thesis:**
```latex
\bibitem{ref:key}
F.~Lastname, ``Title of the thesis,'' Ph.D.~dissertation, Dept. of Elec. Eng., Univ. Name, City, Country, 2024.
```

### Citation formatting rules

16. **Authors:** Initials before surname, periods after each initial with non-breaking tilde to surname (`F.~Lastname`). Up to 6 authors listed; 7+ becomes "F.~Lastname \emph{et~al.}". Last author preceded by ", and" (Oxford comma).
17. **Title:** Sentence case (only first word and proper nouns capitalized) for papers, title case for books/journals.
18. **Journal/conference name:** Italicized via `\emph{}`, abbreviated per IEEE's standard abbreviation list (e.g., `IEEE Trans. Antennas Propag.`, not `IEEE Transactions on Antennas and Propagation`).
19. **Volume/issue/pages:** `vol.~12, no.~3, pp.~45--67` — note `pp.` for ranges, `p.` for single page, en-dash `--` between page numbers.
20. **Month:** Abbreviated three letters with period: `Jan.`, `Feb.`, `Mar.`, `Apr.`, `May`, `Jun.`, `Jul.`, `Aug.`, `Sep.`, `Oct.`, `Nov.`, `Dec.` (May and June/July often unabbreviated; pick one and stay consistent).
21. **Year:** Always present, follows month with non-breaking tilde: `Mar.~2024`.
22. **DOI:** Optional, on its own at the end: `doi:~10.1109/XXX.2024.YYY`.
23. **Punctuation between fields:** Commas separate fields, period ends the entry. Quotes around paper titles, italics around journal/book titles.
24. **"and" before last author:** `F.~A, F.~B, and F.~C` — comma before "and" (IEEE uses Oxford comma).

## Math

25. Variables italicized (`$x$`), functions/operators upright (`\sin`, `\cos`, `\log`, `\exp`, `\max`, `\min`, `\mathrm{SAR}`, `\mathrm{d}x` for differentials).
26. Vectors and matrices consistent: bold italic (`\boldsymbol{x}`) or bold upright (`\mathbf{x}`) — pick one convention and apply everywhere.
27. Subscripts that are labels, not variables, set upright: `$P_{\mathrm{tx}}$` not `$P_{tx}$`.
28. Multi-letter subscripts/superscripts always in `\mathrm{}` or `\text{}` to avoid them being parsed as products.
29. `\left( ... \right)` for delimiters that need to scale; manual `\bigl( ... \bigr)` if `\left\right` overshoots.
30. Equation punctuation: equations are part of sentences. End with `,` or `.` as grammar dictates, inside the equation environment.
31. `\eqref{}` (with parentheses) for equation refs, not `\ref{}`. IEEE style: "as in~\eqref{eq:foo}".
32. Number only equations referenced in text. Use `\nonumber` or `align*` for the rest.
33. `\cdot` for multiplication when needed for clarity, `\times` only for cross products or explicit multiplication ($2 \times 10^8$).
34. Differentials with thin space: `\int f(x)\,\mathrm{d}x`.
35. Long equations broken with `align`, `IEEEeqnarray`, or `split`, aligned at `=` or operators meaningfully.

## Floats and references

36. `Fig.` not `Figure` in IEEE running text (except at sentence start). `\figurename` set correctly via IEEEtran or manually.
37. `Table` always spelled out in IEEE; never `Tab.`
38. Float placement specifiers `[!t]` or `[!b]` consistently; avoid `[h]` and `[here]` — IEEE columns don't accommodate it well.
39. `\centering` inside floats, not `\begin{center}` (the latter adds extra vertical space).
40. Tables use `booktabs` (`\toprule`, `\midrule`, `\bottomrule`), no vertical rules, no double horizontal rules — IEEE style is clean horizontal-only.
41. Table captions *above* the table, figure captions *below* the figure (IEEE convention).
42. `\label{}` immediately after `\caption{}`, never before — otherwise the label points to the section.
43. Label prefixes consistent: `fig:`, `tab:`, `eq:`, `sec:`, `alg:`. Makes Find/Replace and grep sane.

## Structure and style

44. Section titles in title case for IEEE (`Related Work` not `Related work`).
45. No manual line breaks `\\` in body text or section titles to "fix" line breaking — let LaTeX do it, or use `\linebreak` / `\nolinebreak` sparingly with a reason.
46. No `\\` at the end of paragraphs — use a blank line.
47. Acronyms defined on first use: "specific absorption rate (SAR)", then "SAR" thereafter.
48. Acronym not redefined in the abstract *and* the intro — abstract is standalone, intro defines for the body. (IEEE convention varies; pick one.)
49. No widows/orphans if avoidable — single line of a paragraph at top/bottom of column. `\clubpenalty` and `\widowpenalty` to 10000, or manual `\looseness=-1` on offending paragraphs.
50. No overfull hboxes. Run with `\overfullrule=5pt` during drafting to make them visible, fix all before submission. Hyphenation hints (`\-`) or rephrasing.
51. No underfull hboxes ≥ 10pt either — usually a sign of a forced `\\` or weird spacing.

## IEEEtran-specific

52. Use `\IEEEauthorblockN`, `\IEEEauthorblockA` for author blocks, not custom `\author` hacks.
53. `\IEEEpeerreviewmaketitle` after `\maketitle` for conference templates.
54. Compile with `pdflatex` → `pdflatex` (no bibtex pass needed since you're using manual `\bibitem`). Verify no unresolved `??` references in the final PDF.
55. `\PassOptionsToPackage{hyphens}{url}` before loading `hyperref` if URLs are breaking weirdly.
56. `hyperref` loaded *last* (with rare exceptions like `cleveref` after it). `hidelinks` option for IEEE submissions to avoid colored boxes around refs.

## Final pass

57. Diff against the IEEE template — make sure no template-required boilerplate was deleted.
58. Embedded fonts check: `pdffonts output.pdf` should show all fonts as "yes" embedded.
59. Spell check ran on the source, not just the PDF (catches things in captions and labels).
60. Search the source for `TODO`, `XXX`, `FIXME`, `???`, `\todo{}` before submission.
61. Search for double spaces (`  `) and trailing whitespace.
62. Search for `Figure ` and `Table ` in body text — should mostly be `Fig.~\ref{...}` and `Table~\ref{...}`.
63. Compile with `draft` option once to spot overfull boxes via the black bars in the margin.
64. **Verify bibitem order matches first-appearance order in the final compiled PDF.** Easy to drift when adding citations late. Read the PDF, note each `[N]` as it appears, confirm sequential.
65. **Read the paper from a printed PDF, not the source.** Typesetting bugs invisible in the edi


## Also

On first new coinage of a term, always use italics.

## Common substitutions resolved in prior sessions

66. **`et al.` everywhere, never `co-workers`.** Replace globally on first draft.
67. **`approx.` in body text, `\approx` only in math mode.** "approx. 5%" in prose, not "$\approx 5\%$".
68. **No `\gls{}` inside `\IEEEkeywords`.** Just write the acronym. Keywords should also be short and generic — drop technical jargon.
69. **Acronym body capitalisation matches the acronym.** "Transverse Electric (TE)", "Reconfigurable Intelligent Surface (RIS)" — not "transverse electric (TE)".
70. **Units in `[ ]` brackets**, not `( )`, throughout the paper. Pick one and apply globally.
71. **American spelling** (`polarization`, `behavior`, `modeling`, `color`, `gray`, `meter`, `center`, `program`) for IEEE TAP/TWC/JSAC. The British forms (`polarisation`, `behaviour`, etc.) are a project habit but IEEE house style is American.
72. **No space before `%`** in IEEE house style: write `5.6%`, not `5.6\,\%`. This overrides the generic "thin space between number and unit" rule for the percent sign specifically.
73. **`\Cref{...}`** (capitalised, sentence-start safe) over `\cref{...}` when the reference begins or appears mid-sentence and would render as "Section~III". Use the combined form `\Cref{sec:a,sec:b}` rather than two separate `\Cref`s with "and" between them — `cleveref` will format "Sections~III and~V" correctly.
74. **Math/text unit spacing**: don't mix modes for units. Write `$0.08\,\mathrm{W/kg}$`, not `$0.08\,$W/kg`. Same pattern for `$\mathrm{GHz}$`, `$\mathrm{mm}$`, `$\mathrm{kg}$`, etc. inside tables.
75. **Bold convention for vectors and matrices stays consistent.** If you use `\mathbf` for matrices and `\bm` for hatted unit vectors, document that choice in a notation block and apply it globally. The split between `\mathbf{r}, \mathbf{E}, \mathbf{N}, \mathbf{V}` and `\hat{\bm{k}}, \hat{\bm{n}}` is defensible if it is consistent across the paper.

## Abstract precision

76. **Numbers in the abstract match the body to the third or fourth significant figure.** "shows a factor of 4 to 5 reduction" — not "shows a 4 to 5 reduction" (ambiguous units), and not "shows a factor of ~5 reduction" (loses precision). The abstract is not a place to round freely.
77. **State the regime where the number applies.** "Up to $10^{12}$ cells at $100\,\mathrm{GHz}$ on an adult phantom" beats "$10^{12}$ cells". An order-of-magnitude claim without its conditions reads as decoration.
78. **No author names in the abstract** unless the body has already introduced the named result. "Smith's identity" is fine in §III if §II derived or introduced the identity; in the abstract, the reader hasn't met Smith. Reframe to plain prose ("a published identity for...", "a recent result for...", or just describe the result).