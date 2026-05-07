# Front matter conventions for IEEE TAP and similar flagship journals

Notes captured from a survey of three Wydaeghe-group example papers
(`papers/example_papers/main.tex`, `main_iopjournal.tex`, `oldest_paper.tex`)
and the IEEE Editorial Style Manual. These are conventions to match,
not absolute laws.

## Index Terms (keywords)

- Six to nine entries is the typical TAP range. Anything past ten reads
  as fishing for indexers.
- Alphabetical, sentence-case lead, lowercase rest unless the term is a
  proper noun or established acronym (IT'IS, ICNIRP, Brewster, Cauchy,
  Fresnel, Mie).
- Acronyms can be expanded inline on first use: `specific absorption rate
  (SAR)`. The IEEE rule on first-use expansion holds in the keyword list
  too if the acronym is not in the IEEE Approved Indexing Keyword List.
- Pick keywords from the IEEE Approved Indexing Keyword List where you
  can. The system literally hands you a picklist at submission.

## Byline

- TAP / IEEEtran convention: `Robin~Wydaeghe,~\IEEEmembership{Member,~IEEE},
  ...` with non-breaking ties so the name does not split across a line.
- Membership grades that count for the byline: Student Member, Graduate
  Student Member, Member, Senior Member, Fellow, plus the Life-* variants.
  Affiliate Member does not appear in the byline.
- ORCID iDs go in a `\thanks{}` block (not in the byline itself in
  IEEEtran). The `orcidlink` package provides icons; bare ORCID strings
  also acceptable.
- Use `~` ties: `R.~Wydaeghe` to keep initials with surname.

## First-footnote `\thanks` blocks

Multiple `\thanks{}` after `\author{}`, in this order:

1. **Manuscript dates and funding.** "Manuscript received ...; revised
   ...; accepted .... This work was supported in part by [grant]. *(Corresponding
   author: Robin Wydaeghe.)*"
2. **Affiliations.** "The authors are with [department], [university] --
   [partner], [city, country] (e-mail: a@x.y; b@x.y; ...)." Department first,
   university second, postcode/country last. Lowercase emails. Semicolons
   between author emails.
3. **ORCID block** if not embedded in author macros.
4. **Supplementary-material note.** "This article has supplementary
   downloadable material (long-form derivations) provided by the authors,
   available at https://doi.org/...".

## Affiliations

Department, then university (with `-- imec` partner notation for our
group), then street address (`Technologiepark-Zwijnaarde 126`), then
postcode and city (`9052 Ghent`), then country (`Belgium`). Lowercase
emails (`robin.wydaeghe@ugent.be`). Semicolons separate multiple emails
in IEEE style.

## Funding

Funding statement lives in the first `\thanks` block on page 1. If
multiple sponsors apply, "supported in part by ... and in part by ...".
Acknowledgment section (singular, US spelling) repeats names of helpers
who are not authors and is placed *before* the bibliography.

## Section heading case

Across IEEE Access, IEEE TAP, and most Trans. journals: title case
(`Local Absorption Law` not `Local absorption law`). Articles, short
prepositions, and coordinating conjunctions stay lowercase unless first
or last word. Our existing AEGIS drafts use sentence case (project
preference); if matching this project, keep sentence case. If matching
strict TAP house style, switch to title case.

## Author biographies

`\begin{IEEEbiography}[{\includegraphics[...]{authors/aN.png}}]{Name}`
with a clipped 1in by 1.25in author photo. One paragraph, third person
past tense, 100--160 words. Beats:

- degrees with year and institution
- employment trajectory
- current affiliation and role
- "His research interests include ..."
- IEEE membership grade and notable awards or editorial roles

Use `\begin{IEEEbiographynophoto}{Name}` if a photo is not yet ready.

## Reference style

`\bibliographystyle{IEEEtran}` with a `.bib` file. Journal abbreviations
follow the IEEE list (`IEEE Trans. Antennas Propag.`,
`Phys. Med. Biol.`, etc.). Use `\textit{et al.}` after first author when
citation has more than three authors. Pack citations as `\cite{a, b, c}`
so `IEEEtran` collapses them as `[1]--[3]`.

## Math conventions

- `\mathrm{}` for multi-letter subscripts that are labels: `$P_\mathrm{abs}$`,
  `$T_\mathrm{eff}$`. Never `$P_{abs}$`.
- `\bm` for bold-italic vectors (`$\bm{k}$`). Project-wide consistency
  matters more than which command.
- `\,` thin space between number and unit: `$28\,\mathrm{GHz}$`. Or
  commit globally to `siunitx`.
- `\eqref{}` for equation references; `\Cref{}` (cleveref) for sections
  and figures.

## Body of the paper

- Abstract in 150--250 words, single paragraph, no display equations,
  no numbered citations, no footnotes.
- Equations in the introduction are uncommon in TAP; describe the
  identities in prose and let the reader find them in the body.
- Drop-cap on the first letter of the introduction
  (`\IEEEPARstart{W}{ireless}`).
- Markboth (running head) repeats the journal name and a shortened
  paper title.

## Things to flag for the corresponding author

When submitting, confirm or supply:

- IEEE membership grade per author.
- ORCID iDs (Robin's group has prior records: Wydaeghe
  0000-0002-1374-0118, Vermeeren 0000-0002-5309-3808, Tanghe
  0000-0003-0020-6466, Joseph 0000-0002-8807-0673; Martens not on file).
- Author photos at 1in by 1.25in.
- Up-to-date biographies for all co-authors.
- Funding agencies with grant numbers.
- Whether to disclose AI-assisted writing in the first footnote.
- Supplementary-material DOI (Dataverse, IEEE DataPort, or similar).
