# Wydaeghe paper style analysis

A comprehensive style audit of three papers in this directory:

- **`2026_npj_outdoor_RT-QuaDRiGa-FDTD_28GHz_CF-MaMIMO.tex`** (npj Wireless Comm., IEEEtran class) — primary focus
- **`2026_PMB_multifrequency_FDTD_environmental_auto-induced_450MHz-26GHz.tex`** (Phys. Med. Biol., iopjournal class) — primary focus
- **`2022_IEEEAccess_indoor_RT-FDTD_3.5-28GHz_DMaMIMO.tex`** (IEEE Access, ieeeaccess class) — older, used to triangulate authorial constants vs. journal-specific drift

Below "newer two" means the npj and PMB papers; "older" means the IEEE Access paper.

---

## 0a. Author's standing preferences (overrides — apply to upcoming drafts)

The author has reviewed this analysis and made the following corrections. These take precedence over any pattern observed in the example papers and apply to drafts going forward.

- **`\gls{}` is not used in the abstract.** Acronyms are spelled out in the abstract directly.
- **First appearance in a caption uses the manual short form** (`APD`, `IPD`, etc.) — *not* the spelled-out term. The defining first-use always happens in body prose. If `\gls{}` first-use auto-expansion would land inside a caption (because the body has not introduced the term yet), the caption short-form takes precedence and the body still spells it out at the first body mention. Captions read as labels, not definitions.
- **Italic paragraph leads (`\textit{Lead-noun:}` in Methods) are an anti-pattern.** They appeared in the npj 2026 paper as a journal-specific exception. The author does not like italics injected mid-prose this way. Use proper `\subsubsection{}` instead. (This invalidates §1#5, the last sentence of §5.1, §8.2, and any other mention of the pattern as positive.)
- **Vector conventions (§4.2) are soft.** Use `\boldsymbol{x}` / `\mathbf{H}` if free to choose, but do not treat as a hard rule.
- **`siunitx` is no longer favored.** Tilde-glued `28~GHz` style is preferred over `\SI{28}{\giga\hertz}`. Drop `siunitx` from new preambles unless a specific table benefits.
- **Avoid the verb "leverage".** It appears in older drafts but the author dislikes it. Use "use", "exploit", "rely on", "apply", "combine" instead.
- **Section organization (§8.3) is good, but the newest paper will likely diverge.** Don't assume the Configuration / Propagation / Hybridization / Exposure four-step is the canonical template for new work.
- **Multi-panel and image-inclusion conventions (§9.2, §9.3) likely won't apply to the newest paper.** Treat as historical observation, not as guidance.
- **PMB's structured abstract (Objective / Approach / Main results / Significance) was journal-forced.** It is not the author's preferred abstract shape. For non-IOP venues, prefer the traditional flowing single-paragraph abstract.
- **Use American English for IEEE venues.** "Modeling", "behavior", "acknowledgments" — not the British forms. (npj also leans American despite some drift in the example.)
- **`\doi{}` is liked.** Keep it. **But: do not guess DOIs.** If a DOI is missing, leave the field empty — never invent one. (Citation fact-check is needed because some references were generated with AI assistance; flag this for the author at draft-review time.)
- **Do not mimic typos.** "scalibility", "miutes", "Eventhough", "hybdrization", "numer", "Departement" are mistakes — fix them, don't preserve them as voice.

These overrides are integrated inline below as "**Override**:" callouts where they touch a specific pattern.

---

## 0. Conceptualizing style: the dimensions

Before listing patterns, the dimensions used in this audit, ordered from microscopic to macroscopic:

1. **Glyph / character level** — punctuation, dash usage, non-breaking spaces, quote glyphs, subscripts.
2. **Math typesetting** — equation termination, vector/matrix conventions, operator forms, `\mathrm` vs `\text` discipline.
3. **LaTeX surface** — package preamble, command-build habits, glossaries, image-include style.
4. **Word level** — verb register, hedging cadence, abbreviation discipline, emphasis with `\textit{}` / `\emph{}`.
5. **Sentence level** — topic-first construction, colon-then-list, definitional inversions.
6. **Paragraph level** — one-idea-per-paragraph rule, opening sentence shape, transitional connectives.
7. **Section / sub-organization** — sentence case, italic paragraph leads vs. true subsubsections, "Methods → Results" anatomy.
8. **Figure / table / caption** — caption shape, multi-panel grammar, lead-with-finding pattern.
9. **Citation surface** — numeric vs. author-year, "et al." styling, doi treatment.
10. **Document architecture** — abstract format, novelty enumeration, end-matter blocks (acknowledgements / data / conflicts).
11. **Authorial voice** — "this work" / "we" alternation, novelty disclaimers, hedging stance.
12. **Macro rhetoric** — how arguments are sequenced (gap → method → claim → numeric anchor).

---

## 1. Top patterns ranked by prominence

This is the ranked digest. Detailed sections expand each.

| Rank | Pattern | Prominence | Where most visible |
|------|---------|-----------|--------------------|
| 1 | **Sentence-case section and subsection titles** ("Configuration step", "Hot-spots", "Auto-induced exposure scenario") | Universal across all three | Every `\section{}` and `\subsection{}` |
| 2 | **Punctuation lives inside the display equation, set off by `\,`** (`\, .` or `\, ,` before `\end{equation}`) | Universal, hundreds of occurrences | Every numbered equation in newer papers |
| 3 | **Non-breaking tilde before units and short numerals** (`28~GHz`, `1.5~m`, `4~cm$^2$`, `\SI{}{\meter}`) | Universal, near-total compliance | Both numeric and unit slots |
| 4 | **Glossaries-driven acronym handling** (`\gls{5G}`, `\glspl{AP}`) — defined once, expanded automatically thereafter | All three; preamble shape near-identical | Top of preamble, throughout body |
| 5 | ~~`\textit{italic-term:}` paragraph leads acting as a third-level structure~~ — **anti-pattern, do not propagate.** Appeared in older drafts; the author dislikes italics injected into the middle of prose. Use real `\subsubsection{}` instead. | — | — |
| 6 | **First sentence of paragraph is the topic sentence; almost always either "Figure X shows…", "Table Y lists…", or a direct claim** | Universal | Results sections especially |
| 7 | **"First, … Second, … Third, … Finally, …" enumeration inside running prose** (rather than `enumerate`) | Universal | Method narration, justifications |
| 8 | **Numbered enumerate to declare novelty** in introduction, prefaced by "this work is novel in the following ways" or "Three gaps limit current understanding…(1)(2)(3)" | All three | End of intro |
| 9 | **"To the best (of the) knowledge of the authors"** as the canonical novelty disclaimer | All three, slight phrase drift between papers | Final intro paragraph |
| 10 | **Lead-with-finding figure captions** in PMB ("Children show 1.5–1.9× higher…", "Thelonious (6y) exceeds the ICNIRP basic restriction at 7 GHz (103%)") | PMB only — npj uses descriptive captions | PMB results figures |
| 11 | **Tight numeric anchoring**: every claim followed by a specific number with units (`12~dB`, `93\%`, `0.44 \lambda`) | Universal but most emphatic in newer papers | Results, abstract, conclusion |
| 12 | **`w.r.t.` / `e.g.,` / `i.e.,` / `vs.`** — the author uses the abbreviated forms with the trailing comma | Universal | Narrative prose |
| 13 | **Em dashes are ABSENT.** The author uses commas, parens, and colons. Hyphens with surrounding spaces never appear. (En dashes appear only in numeric ranges like `1.5--1.9`.) | Universal | Everywhere |
| 14 | **Vectors as `\boldsymbol{x}` / `\mathbf{H}`; subscripts with `\mathrm{}` for variable-naming context** (`S_\mathrm{ab}`, `S_\mathrm{inc}`) | Universal | All math | (Soft preference — take with a grain of salt. If free to choose, why not, but no need to enforce.) |
| 15 | **"Fig." abbreviation** in IEEE-class papers; **full "Figure"** in PMB IOP paper | Journal-driven | Figure cross-references |
| 16 | **Closing paragraph of intro lists novelty as enumerated bullets**, then methods opens with a flowchart figure or table | Newer two share this; older paper less explicit | Intro→Methods boundary |
| 17 | **Italic emphasis on freshly defined terms** (`\textit{exposure clusters}`, `\textit{multipath matrix}`, `\textit{auto-induced}`, `\emph{hotspot score}`) | Universal | First introduction of any local jargon |
| 18 | **Numeric ranges with `--` (en dash)**: `1.5--1.9`, `7--15~GHz`, `131--158\%` | Universal in newer papers; older paper more often uses `to` | Tables, numeric reporting |
| 19 | **Footnote-style citation context** is absent. Citations are inline `\cite{}` / `\citep{}`; no parenthetical "see also" or `cf.` | Universal | All citation slots |
| 20 | **Closing of Methods or Results subsections frequently contains a single sentence stating the implication** ("Therefore, the small-scale hot-spot increases the electric field by 12~dB…") | Newer two | End of subsections |

---

## 2. Microscopic: punctuation, dashes, glyphs

### 2.1 Em dashes — absent

The author **does not use em dashes**. Across all three papers there is no `---` and no spaced en-dash-as-em-dash construction. Where another writer would use em dashes for parenthetical asides, this author uses:

- A pair of commas: "Beamforming actively concentrates the emitted radiation optimally toward the UE, in contrast with fourth-generation BSs which do not target active users."
- Parentheses: "These networks span three frequency ranges: FR1 (450 MHz–6 GHz), FR2 (24–52.6 GHz for 5G mmWave), and the prospective FR3 (7–15 GHz for 6G)…"
- A colon: "Three gaps limit current understanding…: (1)…"

This is a strong tell — em dashes feel "off-brand" for this author.

### 2.2 En dashes — only for numeric ranges

`--` is reserved for ranges (`1.5--1.9~times`, `7--15~GHz`, `131--158\%`, `pp.~3115--30`). Page ranges in bibliography also use `--`. Not used as parenthetical separators.

### 2.3 Hyphenation conventions

- **Hyphenated noun-phrase modifiers**: `cell-free`, `line-of-sight`, `non-line-of-sight`, `large-scale`, `small-scale`, `quasi-deterministic`, `auto-induced`, `worst-case`, `mass-averaged`, `peak-spatial`, `non-user`, `body-worn`, `time-averaged`, `site-specific`, `whole-body`, `rule-based`, `wavelength-sized`, `vertically-polarized`, `frequency-dependent`.
- **`mmWave`/`mm-Wave`/`millimeter-wave`/`mmwave` drift**: the older paper writes `mm-Wave`; npj 2026 writes `mmWave` or, when in an acronym, `\gls{mmWave}`; PMB 2026 writes `millimeter-wave` and `mmWave` interchangeably. This is the one place the author is inconsistent across papers — though within a single paper they pick a form and largely stick to it.
- **Subscript names not hyphenated**: `psSAR_{10\mathrm{g}}`, `SAR_\mathrm{wb}`, `S_\mathrm{ab}` — the underscore content is the abbreviated noun.

### 2.4 Quotation marks

Always LaTeX double-tick: `` ``…'' ``. Never straight quotes, never directional Unicode. Even in informal asides ("`how much exposure do I \textit{realistically} experience when I walk down the street?'"), the typographic pair is preserved.

### 2.5 Non-breaking ties (`~`)

Pervasive and disciplined:
- Before units: `28~GHz`, `1.5~m`, `4~cm$^2$`, `1~W/m$^2$`
- Between author and number in cross-refs: `Fig.~\ref{...}`, `Section~\ref{...}`, `Eq.~\eqref{...}`, `Table~\ref{...}` (mostly, though `Fig. \ref{}` with space appears occasionally — slight inconsistency)
- Between author and "et al.": `Wydaeghe~\textit{et al.}`
- Between part and number in refs: `Band~31`, `Part~1`, `Grant~695495`
- Between numerical range tokens occasionally: `2~billion`

This is so consistent it's a fingerprint. If a sentence in the user's voice has a number followed by a unit and the gap is a regular space, it's almost certainly a draft mistake.

### 2.6 `siunitx` use

**Override**: the author no longer favors `siunitx`. Drop it from new preambles. Use tilde-glued plain text consistently (`28~GHz`, `1.5~m`, `4~cm$^2$`).

(Historical observation, kept for context: all three example papers loaded `\usepackage{siunitx}`. The older paper used it heavily — `\SI{50}{cm}`, `\SI{1.75}{\milli\meter}`, `\SI{}{W/m^2}`. The newer two were already drifting toward tilde-glued prose for most units, with `\SI{}` reserved for tables. The endpoint of that drift is: don't load `siunitx` at all.)

### 2.7 `\, ` thin space before equation-terminating punctuation

Effectively a signature. Inside display math: `\, .` and `\, ,`. See §4.

### 2.8 Comma after introductory adverbials

Heavy and consistent:
- "However,"
- "Therefore,"
- "Conversely,"
- "Moreover,"
- "Furthermore,"
- "In particular,"
- "First, … Second, … Finally, …"
- "Note that,"
- "Hence,"
- "Then,"
- "Thus,"

The connective is almost always followed by a comma, then a complete clause. "Hence" without a comma is rare.

### 2.9 Numeric formatting

- Decimals always with a leading zero or single digit: `0.25°`, `0.05`, `4.81~ps`.
- Percentages: `\%` (always escaped).
- Multipliers in prose: written as `2 to 3 times` (older) or `1.5--1.9~times` / `2$\times$ stronger` / `3.2-fold` (newer). The newer papers prefer the en-dash form and the explicit `$\times$` glyph.
- Order-of-magnitude: "an order of magnitude" appears verbatim.

### 2.10 Punctuation around `e.g.` / `i.e.`

Always with the trailing comma: `e.g.,` `i.e.,`. Never `eg.` or unbroken `e.g.X`.

### 2.11 Abbreviations of meta words

- "with respect to" almost always abbreviated as `w.r.t.` in body prose.
- "for example" → `e.g.`; "that is" → `i.e.`
- "vs.", "versus" both appear; the abbreviated form is more common.
- "approximately" written out, not `approx.` or `~`.

---

## 3. LaTeX surface conventions

### 3.1 Preamble shape

Both newer papers and the older paper share this skeleton:

```
\documentclass{<journal class>}
\usepackage{cite}                      % older + npj (numeric)
\usepackage[round,authoryear]{natbib}  % PMB only (author-year)
\usepackage{url}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{gensymb}
\usepackage{algorithmic}
\usepackage{graphicx}
\usepackage{siunitx}
\usepackage{textcomp}
\usepackage{lipsum}                    % left in even after drafting
\usepackage{subfloat}                  % older + npj
\usepackage{subcaption}                % all three
\usepackage{anyfontsize}
\usepackage{comment}
\usepackage{glossaries}                % all three (newer two with [acronym,nonumberlist])
\usepackage{booktabs}                  % newer two
\usepackage{orcidlink}                 % newer two
```

The author keeps `lipsum` and `comment` in the preamble even after draft text is removed — a habit, not a need.

### 3.2 Glossaries discipline

A canonical block of `\newacronym{...}{...}{...}` lines defines every abbreviation up front, and `\glspl{X}` handles plurals.

**Override / clarification on first-use**:
- **Abstract**: no `\gls`. Acronyms are spelled out in plain prose.
- **Body first appearance**: rely on `\gls`'s default first-use auto-expansion. The earlier guidance to "write it out normally first" was a fluke — drop it.
- **Caption first appearance**: use the manual short form (`APD`, `IPD`, etc.), *not* the spelled-out term. The defining first-use always happens in body prose. If the body has not yet introduced the term and a caption could land first, override to the short form in the caption and let the body still spell it out at its own first mention.

### 3.3 Image inclusion

- **`\input{Figures/<name>.pdf_tex}` and `\input{...eps_tex}`** dominate, indicating Inkscape-exported vector figures with embedded text. This is heavy throughout npj 2026 and the older paper, and present in PMB.
- **`\includegraphics[width=\columnwidth]{...}`** for raster/PDF figures, also in all three.
- The svg-include uses the boilerplate `\def\svgwidth{\columnwidth}` (or `\linewidth`, `3.3in`) immediately before the `\input`.

### 3.4 Custom commands

- `\newcommand{\refappendix}[1]{...}` and `\newcommand*{\doi}[1]{...}` (npj 2026) — small helper commands defined in preamble.
- `\newcommand{\headeretal}{et al.}` (older + iopjournal `\headeretal` redefinition) — standardize "et al." styling for headers.
- PMB defines `\conflict{}` because the iopjournal class lacks it, and overrides `\articletype` and `\fancyhead` in-preamble. The author is willing to override class-file behavior when a journal template doesn't fit.

### 3.5 Hyperref colour scheme

- npj: all blue (`colorlinks=true,linkcolor=blue,allcolors=blue`).
- PMB: blue citations and URLs, black internal links and acronyms (`linkcolor=black,citecolor=blue,urlcolor=blue`).

### 3.6 `lineno` package

npj 2026 includes `\usepackage[switch]{lineno}` (revisions / submissions). Older paper does not. PMB does not. Suggests npj draft is in the review/revision phase.

### 3.7 `\ justifying` / `\raggedbottom`

PMB explicitly overrides the iopjournal class default with `\usepackage{ragged2e}\justifying\raggedbottom`. The author wants justified body text and ragged bottom — a deliberate aesthetic choice.

---

## 4. Equation handling

### 4.1 Termination punctuation lives **inside** the equation environment

A near-universal pattern. Every numbered display equation ends with either `\, .` or `\, ,` followed by `\end{equation}` (or `\end{aligned}`). The thin space `\,` is always there. Examples:

```latex
\textbf{H} = \sum_{l} \textbf{M}_{l} \, .
\mathbf{w} = \frac{\mathbf{h}^*}{\|\mathbf{h}\|} \,,
m_{i,j,l,s}^\mathrm{precoded} = \hat{m}_{i,j,l,s} \cdot x_{j,s} \, .
H(\mathbf{r}_0) = \frac{1}{N_\mathrm{skin}} \sum_{k=1}^{N_\mathrm{skin}} \bigl|\mathbf{E}_\mathrm{combined}(\mathbf{r}_k)\bigr|^2 \,,
```

Whether it's `,` or `.` is determined by whether the sentence in the surrounding prose continues after the equation (`,`) or terminates (`.`). The thin space before either is invariant.

### 4.2 Vectors and matrices

**Override**: this convention is soft — not a hard rule. If you're free to choose, why not stick with the patterns below, but don't fight the journal style or co-authors over it.

- Vectors: `\boldsymbol{x}`, `\boldsymbol{y}`, `\boldsymbol{s}`, `\mathbf{w}`, `\mathbf{h}`, `\mathbf{r}`, `\mathbf{E}`, `\mathbf{H}` — both `\boldsymbol` and `\mathbf` appear, with `\boldsymbol` for explicitly multi-component channel vectors and `\mathbf` for fields and indices.
- Matrices: `\mathbf{M}`, `\mathbf{H}`, `\mathbf{W}`. Hat for intermediate values: `\widehat{\mathbf{M}}`, `\widehat{\boldsymbol{x}}`.
- Hadamard / element-wise: `\odot`, `\oslash` (defined inline).
- Conjugate transpose: `\mathbf{H}^H`. Transpose of plain matrix: `\mathsf{T}` (used in `|\mathbf{h}^\mathsf{T} \mathbf{w}|^2`).

### 4.3 Subscripts: `\mathrm{}` for noun-like subscripts

Convention is rigid: any subscript that names a thing (not an index) is wrapped in `\mathrm{}` — `S_\mathrm{ab}`, `S_\mathrm{inc}`, `psSAR_{10\mathrm{g}}`, `SAR_\mathrm{wb}`, `\delta_{90}`, `N_\mathrm{snapshot}^\mathrm{RT}`, `\mathbf{r}_\mathrm{ear}`. Index subscripts (`i`, `j`, `l`, `s`) are bare math-italic.

`\text{}` is used occasionally instead of `\mathrm{}` in older paper (`\text{Rx}`, `\text{tot}`) but the newer papers strongly prefer `\mathrm{}`.

### 4.4 Equation references

- npj: `\eqref{eq:precoding_definition}` and `\ref{eq:c_to_g}` are both used. Sometimes bare `\eqref{eq:...}`, sometimes preceded by `Eq.~`. Consistency within section, less across.
- PMB: `Eq.~\eqref{eq:hotspot_score}` is the dominant form.
- Equation labels are descriptive: `eq:c_to_g`, `eq:precoding_definition`, `eq:m_precoded`, `eq:hotspot_score`, `eq:mrt_polar`. They name the *equation's purpose*, not its number.

### 4.5 Display equation environments

- `equation` for a single line (with end-punctuation inside).
- `aligned` inside `equation` for multi-line systems where one number suffices: `\begin{equation}\begin{aligned}…\end{aligned}\end{equation}`.
- `dcases` for piecewise definitions (used once in npj 2026 for the per-AP precoder).
- `\[ ... \]` for unnumbered display in older paper (rare in newer).

### 4.6 Inline math hygiene

In running prose, the author rarely lets math go un-italicized. Even unit-like things are wrapped: `1~W/m$^2$` (the `^2` is in math mode). Greek letters in prose are always math: `$\lambda$`, `$\theta$`, `$\phi$`.

### 4.7 Operator words

`\arg`, `\sin`, `\cos`, `\exp`, `\sqrt` — standard. The author writes `\exp(jk\dots)` not `e^{jk\dots}` for engineering EM phasors. Imaginary unit is `j`, not `i`.

---

## 5. Sentence-level patterns

### 5.1 Topic-first sentences

Almost every paragraph in Results opens with a deictic claim:

- "Figure~\ref{fig:sar_divergence} shows the normalized SAR as a function of frequency."
- "Table~\ref{table:fr1_auto} compares auto-induced and environmental psSAR$_{10\mathrm{g}}$ and SAR$_\mathrm{wb}$ at both frequencies."
- "The hot-spot features a large-scale hot-spot around the receiver, a small-scale hot-spot as a result of the interference pattern, prominent sidelobes and spherical wavefronts."

### 5.2 Result-then-reason structure

The dominant micro-rhetorical move is **state the number, then explain why**:

> "Brain SAR decreases by 96\% from 450~MHz to 5.8~GHz as absorption shifts to the skin."
> "Eye SAR drops 77-fold from 7 to 26~GHz as penetration depth falls below eyelid thickness."
> "Skin SAR increases by a factor 3.2 between 450~MHz and 5800~MHz, as energy concentrates superficially."

Number is always concrete. Reason is always a single mechanism. Two-clause sentence.

### 5.3 Definitions by inversion

When introducing a new term, the author often inverts: "X, where Y is the … and Z is the …" or "We coin this \textit{X}, because …". Examples:

> "This is coined \textit{exposure-wise} averaging, because the concept of …"
> "We developed the \emph{hotspot score} that approximates APD without full extraction…"
> "We call these \textit{exposure clusters}."

The defined term is italicized (`\textit{}` or `\emph{}`); the definition follows.

### 5.4 Colon-then-list / colon-then-explanation

Heavy use of colons:
- "Three gaps limit current understanding of far-field RF–EMF exposure in the 5G/6G era: (1)…(2)…(3)…"
- "The ratio of the exposure metric divided by the relevant ICNIRP exposure limit is shown on the right vertical axis."
- "We introduce three properties to characterize the hot-spots:" (followed by `enumerate`)

### 5.5 "Therefore", "Hence", "Thus" — load-bearing connectives

Every two or three sentences carries one. The author rarely strings claims without an explicit logical connector. This makes the prose easy to follow but can read as didactic.

### 5.6 Sentence length

Mostly medium (15–28 words). Long sentences (40+ words) are rare and almost always broken with semicolons or em-dash equivalents (commas + parens). Very short declarative sentences (5–10 words) appear at high-impact moments:

> "All phantoms comply at 700~MHz."
> "Reference levels were derived from uniform plane-wave exposure and do not account for this scenario."
> "Adult phantoms remain below 52\% of the basic restriction at all frequencies."

This staccato is common in PMB Results.

### 5.7 Hedging

- Strong-claim verbs: "shows", "demonstrates", "establishes", "exceeds", "yields", "reaches", "compares".
- Hedging verbs: "may", "can", "could", "indicates", "suggests", "approximates".
- "approximately" / "roughly" / "on the order of" — hedges placed before numbers when the number is rounded.
- The author hedges the *interpretation* but not the *measurement*: "Compliance margins improve at higher frequencies" (claim) vs. "These results may be underestimated because material properties from the IT'IS database are isotropic" (hedge on cause).

### 5.8 Negation patterns

- "not always", "not necessarily", "do not account for", "does not increase the total absorbed power".
- The author rarely uses "never" or "always" without qualification — when an absolute appears, it's load-bearing.

---

## 6. Word choice / lexicon

### 6.1 Recurring verbs

A frequency-rank inventory of action verbs across the two newer papers (informal counting):

- **show / shows / shown** — the dominant verb of evidence.
- **compute / computes / computed / is computed** — for derivations.
- **assess / characterize / evaluate / quantify** — for measurement framing.
- **introduce / propose** — for novelty claims.
- **enable / enables** — for capability framing ("This enables…").
- **demonstrate** — used sparingly, only when very confident.
- **find / found / observe / observed** — for empirical claims.
- **indicate / suggest** — for inferred claims.
- **comprise / consist of** — for structure.
- **leverage** — used for combining methods.

### 6.2 Recurring adjectives

- "realistic" — appears in titles and ubiquitously in body. A signature word.
- "novel" — used at most once or twice per paper, anchored to specific contributions.
- "comprehensive" — used in intros and conclusions.
- "site-specific" / "deterministic" / "quasi-deterministic" / "stochastic" — paired oppositions used to position channel models.
- "worst-case" — used both as adjective and as noun ("worst-case scenario").
- "well-defined", "fine", "coarse", "spatially-consistent" — descriptive.

### 6.3 Recurring nouns / signatures

- "hot-spot" / "hotspot" — central concept across all three. Hyphenation drifts: older paper writes `hotspot`; npj writes `hot-spot` heavily; PMB writes `hotspot`.
- "exposure" / "exposure metric" / "exposure assessment" / "exposure quantity" / "exposure limit" / "exposure scenario" — a tight family of compound nouns.
- "pipeline" / "method" / "tool" / "framework" — used to refer to the computational stack.
- "the user" / "the UE" / "the pedestrian" / "a smartphone user" — character noun for the receiver.
- "compliance margin" — the centerpiece of PMB's numeric framing.

### 6.4 "Realistic" — a tell

Used in all three titles, abstracts, and conclusions. A single-word stance: the work distinguishes itself from worst-case theoretical bounds. When the author writes "realistic", expect a contrast with simplified or worst-case literature in the surrounding sentence.

### 6.5 "We" vs. "this work" vs. passive

- **"We"** (active, first-person plural): common in Methods and Results — "we performed", "we developed", "we computed", "we assume".
- **"This work"** / **"this paper"** / **"this study"**: used to refer to the document as a whole, especially in intro/conclusion claims of novelty.
- **"the authors"**: appears only in disclaimers ("To the best of the authors' knowledge").
- **Passive**: dominant in describing experimental setup ("The simulations were performed", "The fields are evaluated"). The author shifts register cleanly: passive for procedures, active for claims.

### 6.6 No first-person singular

"I" never appears (outside the layman quote in npj abstract).

### 6.6b Avoided verb: "leverage"

**Override**: the author dislikes "leverage" as a verb. It does appear in older drafts ("RT and QuaDRiGa simulations are leveraged efficiently…") but should be replaced with cleaner alternatives:

- "use", "exploit", "rely on", "apply", "combine", "draw on", "build on"

Watch for it specifically in Methods framing sentences, where AI-assisted drafting tends to insert it.

### 6.7 Discourse markers and connectives — vocabulary

- "However" — single most common.
- "Therefore" / "Hence" / "Thus" — interchangeable.
- "Moreover" / "Furthermore" / "In addition".
- "Conversely" / "On the other hand" — used for explicit contrast.
- "In particular" — used to specialize a general claim.
- "Note that" — used to flag a non-obvious caveat.
- "It should be noted that" — slightly more formal variant; rare.

### 6.8 Avoidance words / phrases

- No "very" / "really" / "extremely" without quantifier (the author writes "$f^4$" or "20~dB" instead).
- No "obviously", "clearly", "of course".
- No "in the literature, it has been shown" — the author cites specific papers.
- No "interestingly" / "surprisingly" / "remarkably" — neutral tone.

---

## 7. Paragraph structure

### 7.1 One idea per paragraph

The author is disciplined. A new claim almost always opens a new paragraph. Long paragraphs (>10 sentences) only appear in Methods when describing a chained procedure; even there, sub-procedures break out as italic-led paragraphs.

### 7.2 Paragraph opening shapes

Five recognizable shapes, in rough frequency order:

1. **Figure / table reference**: "Figure~\ref{fig:X} shows / lists / compares …". Most common in Results.
2. **Italic paragraph lead** (npj 2026 Methods): `\textit{Receiver path:}` then explanation.
3. **Direct claim**: "Children show 1.5–1.9× higher whole-body SAR than adults at all sub-6~GHz frequencies."
4. **Bridge / context**: "To model the exposure from these technologies, the propagation step needs to be interfaced with the exposure step…"
5. **Definition / framing**: "Auto-induced exposure occurs when a MaMIMO base station beamforms toward a user's device…"

### 7.3 Paragraph endings

- Often a single-sentence implication: "Therefore, the small-scale hot-spot increases the electric field by 12~dB on top of the large-scale beamforming gain."
- Occasionally a forward link: "The same single-direction approach was used for Thelonious at FR3 frequencies…"

### 7.4 Connective links between paragraphs

Most paragraph-to-paragraph transitions are *implicit* (topic continuity carries the link). When explicit, the connector is one of: "However,", "In addition,", "Conversely,", "Furthermore,", "Then,", or a number-step ("First,", "Second,").

---

## 8. Section / sub-organization

### 8.1 Sentence-case headings

Universal across all three papers:

- "Methods", "Results", "Conclusion"
- "Configuration step", "Propagation step", "Hybridization step", "Exposure step"
- "Hot-spots"
- "Case study in Helsinki, Finland"
- "Frequency selection and technology mapping"
- "Auto-induced exposure scenario"
- "Beamforming weights"
- "Hotspot score for efficient worst-case identification"
- "Numerical simulation framework"
- "Anatomical phantoms"
- "Children have higher whole-body SAR than adults"

Note: PMB sometimes uses **finding-as-heading** for `\subsubsection` (e.g., "Children have higher whole-body SAR than adults", "Penetration depth determines the frequency response", "ICNIRP limit exceeded at 7 GHz", "Peak APD decreases with frequency"). This is a signature of PMB only.

### 8.2 Italic paragraph leads as pseudo-subsubsections — **anti-pattern**

**Override**: do not use this pattern. The npj 2026 paper used `\textit{Processed and classified environments:} ...` style paragraph leads in its Methods section as a journal-driven exception. The author dislikes italics injected mid-prose and considers the pattern an anti-pattern for new drafts.

For new work, use real `\subsubsection{}` for any third-level structure. If the structure is too light to deserve a heading, just write a normal paragraph with a strong topic sentence — no inline italic label.

### 8.3 Section anatomy of a Wydaeghe paper

The author likes this overall shape, but **the newest draft will probably diverge** from the four-step Methods template below. Treat as guidance, not as a fixed scaffold. The Intro / Results / Conclusion shape is more durable than the specific Methods step names.

- **Introduction** — broad context (5G/6G demand, public concern, ICNIRP) → existing methods → gap → numbered novelty list. About 1.5–2 pages.
- **Methods** — broken into named steps (Configuration / Propagation / Hybridization / Exposure in npj; Frequency selection / Exposure metrics / Environmental scenario / Auto-induced scenario / Numerical framework in PMB). Almost always opens with a flowchart figure or a parameter table. The new draft may use an entirely different decomposition.
- **Results (and Discussion)** — typically two or three case studies or scenarios. Dense numeric. Each subsection = one finding.
- **Conclusion** — a recap that reuses the abstract numbers, then a "limitations" paragraph, then a "future work" paragraph.
- **Acknowledgements / Funding / Author Contributions / Data Availability / Conflicts** — formal end-matter. Format varies by journal class.

### 8.4 No "Introduction" / "Conclusion" subsections

The author keeps `\section{Introduction}` and `\section{Conclusion}` as flat — no children. The deep structure lives in Methods and Results.

---

## 9. Figure handling

### 9.1 Float placement

`[h]`, `[h!]`, `[t!]`, `[!t]` — the author over-specifies float placement. Most common: `[h!]` for inline figures, `[t!]` for top-of-page figures in two-column layouts. Almost never `[H]` (the `float` package). Consistent across papers.

### 9.2 Multi-panel figures

**Override**: this likely will not apply to the newest paper. Treat as historical observation only — not as a target convention.

(Historical: the older paper used `subfloat`; the newer two used `subcaption` with `\begin{subfigure}[b]{\columnwidth}`. Multi-panel cross-references appeared as `Fig.~\ref{fig:X}(a)`. The new draft may not need multi-panel figures at all, or may use a different mechanism.)

### 9.3 Figure inclusion forms

**Override**: this likely will not apply to the newest paper either. The Inkscape-`pdf_tex` workflow was a habit of earlier drafts, not a fixed convention. Use whatever vector pipeline fits the new paper — it does not have to be Inkscape-`pdf_tex`.

(Historical: previous papers mixed `\input{Figures/<name>.pdf_tex}` for Inkscape-with-LaTeX-text figures, `\includegraphics{...}` for matplotlib output, and `\input{...eps_tex}` for older Inkscape exports. `\graphicspath` was set once at preamble.)

### 9.4 Width specifications

- `\columnwidth` for column-width figures.
- `\textwidth` (in two-column layouts, with `figure*` environment) for full-width figures.
- Specific in-units like `3.5in`, `3.3in` in PMB — unusual choice, driven by the iopjournal class.

### 9.5 `\graphicspath`

Specified once at preamble. Subdirectory paths inside `\input{}` and `\includegraphics{}` are relative to that root.

---

## 10. Table handling

### 10.1 `booktabs` discipline (newer two)

`\toprule`, `\midrule`, `\bottomrule` — no vertical bars, minimal horizontal rules. Newer papers commit to `booktabs`. The 2022 IEEE Access paper still uses old-style `|c|c|c|` columns and `\hline` on every row — that's a pre-`booktabs` IEEE Access habit.

### 10.2 Caption above table

Always `\caption{...}` before `\begin{tabular}` (not below). Caption text is sentence-style with closing period.

### 10.3 Multi-column headers

`\multicolumn{N}{c}{...}`, often in groups (frequency bands, scenario columns) with `\cmidrule(lr){i-j}` to draw rule under the header span. PMB simulation parameter table uses `\cmidrule` extensively with column-coloured cells (`\rowcolor`, `\cellcolor`).

### 10.4 Row coloring / banding

PMB introduces `\rowcolor{lightgray}` for header/section rows in the omnibus simulation parameters table; the colour palette is defined in preamble (`fr1color`, `fr2color`, `fr3color`). This is unusual for the author and is journal-driven. The npj and older papers don't colour rows.

### 10.5 Footnotes inside tables

Footnotes are `^a`, `^b`, `^c` superscripts in the body, with explanations in a `\multicolumn{N}{@{}l}{\footnotesize $^a$...}` row below `\bottomrule`. Both newer papers use this.

### 10.6 Numerical formatting in tables

- Bold for headline numbers: `\textbf{93\%}` to highlight the tightest compliance margin.
- Footnote markers attached directly to numbers: `133\%$^b$`.
- Bracketed units in column headers: `[mW/kg]`, `(W/m$^2$)`.

---

## 11. Caption patterns

### 11.1 Caption shapes

Three recognizable forms. From most prominent in newer two:

**A. Lead-with-finding** (PMB results figures):
> "Thelonious (6y) exceeds the ICNIRP basic restriction at 7~GHz (103\%). Percentage of the basic restriction versus frequency for auto-induced exposure at 10~W/m$^2$ reference level. Shaded region above 100\% indicates non-compliance. At 15~GHz, all phantoms fall below 40\%."

A claim-sentence first, then the descriptive parts (axes, what's plotted), then secondary findings. This pattern *only* shows up in PMB; npj 2026 doesn't use it.

**B. Descriptive-only** (npj 2026 + older paper):
> "Reference (top) and basic (bottom) quantities as a function of distance along the path in Helsinki. Green or red patches indicate a LOS or NLOS state with the collocated antenna, respectively. The darker or lighter patches indicate an urban or suburban environment, respectively."

What's shown, what each colour means, no headline.

**C. Multi-panel umbrella** (all three):
> "Comparison of the $S_\mathrm{inc}$ with the propagation- and exposure-wise averaging using 2D slices. The former averages the fields in time first, the latter computes the exposure first and then averages these in time."

Sub-captions hold the panel-specific detail; the main caption gives the comparison theme.

### 11.2 Caption mechanics

- Always end with a period.
- Use sentence case.
- Cross-references inside captions (`as discussed in Section~\ref{...}`) are rare. Captions usually stand alone.
- Equation numbers are sometimes invoked in captions ("computed via Eq.~\eqref{...}") but mostly captions describe geometry or interpretation.

### 11.3 Caption length

- npj: medium-to-long captions (2–4 sentences). The author often packs interpretation into the caption.
- PMB: similar length but with the lead-with-finding shape.
- Older paper: shorter, more telegraphic.

### 11.4 Caption sub-references

When a caption refers to internal panels of its own figure, the form is `(a)`, `(b)` in plain text, matching `\caption[(a) ...]` in subfigures.

---

## 12. Citations and references

### 12.1 Citation styles

- **npj 2026**: numeric IEEE-style `\cite{key}`, with `\cite[Sec.~5]{key}` for in-text page refs (rare).
- **PMB 2026**: author-year via `natbib`, `\citep{author2024key}` and `\citet{author2024key}`. The setup line `\setcitestyle{aysep={},notesep={, },citesep={,}}` removes the comma between author and year (`\citep[]{}` shows `(Author 2024)` not `(Author, 2024)`).
- **2022 IEEE Access**: numeric `\cite{key}` with descriptive keys that *include spaces* (`\cite{Sergei RT-FDTD}`, `\cite{Bjornson book}`, `\cite{Marzetta first MaMIMO}`). The author's later papers replace these with namelastname+year+keyword keys (e.g., `wydaeghe2022realistic`, `bjornson2017massive`, `icnirp2020`). Big housekeeping shift.

### 12.2 "et al." styling

- Body: `\textit{et al.}` with the period.
- Header (markboth) / shortcite: `\headeretal` macro standardizes to `et al.` (no italic, no period in some headers).

### 12.3 doi handling

The author likes the `\doi{<doi>}` macro (linkifies the DOI via `\href{http://dx.doi.org/<doi>}{<doi>}`). Keep it for new IEEE-style bibliographies; bibliography entries end with `doi: \doi{...}`.

**Override — DOI fact-check warning**: do **not** guess DOIs. If a DOI is missing from a reference, leave the field empty. Some references in earlier drafts were generated with AI assistance, and AI-generated DOIs are frequently wrong. **At draft-review time, flag every reference for the author to fact-check** — the `\doi{}` link makes verification fast, but only if the DOI is real.

(Historical: the 2022 IEEE Access paper used plain `doi: 10.1109/...` text without the macro. PMB-style author-year bibliographies often omit DOIs entirely in favor of `(available at: \url{...})`.)

### 12.4 Bibliography body

- npj uses `\begin{thebibliography}{00}` with `\bibitem{key}` and rich formatting (`\textit{Journal}`, vol., no., pp., year, doi). Same in older paper.
- PMB uses `\begin{thebibliography}{99}` with `\bibitem[Author \emph{et al}(YYYY)]{key}` author-year format. Note `\emph` inside the optional argument — italic "et al" without period in the citation key; period in body.
- All three carefully alphabetize / order by appearance and are clean; journal abbreviation discipline ("IEEE Trans. Antennas Propag.", "Phys. Med. Biol.", "IEEE Access").

### 12.5 Reference text style

- "Available: \url{...}. [Accessed: <month> 2024]." for web references — present in all three.
- Software references styled like papers ("Remcom, 'Wireless InSite,' [Software]." / "ZMT Zurich MedTech AG 2024 Sim4Life: Computational Life Sciences Platform").
- Theses styled formally with department, university, location.

### 12.6 In-prose citation grammar

The author rarely names authors in body text. Citation is almost always parenthetical `\cite{}`/`\citep{}`. Exceptions in PMB intro are deliberate: "\citet{dimbylow2002fdtd} established baseline SAR values…", "\citet{uusitupa2010sar} extended this to 15 voxel models…". This is a PMB-specific move (natbib makes it natural); npj does not do this.

---

## 13. Macroscopic document architecture

### 13.1 Abstract format

Three different abstract styles, one per paper:

**Older paper (IEEE Access, 2022)** — single-paragraph traditional abstract, ~250 words. Opens with the realistic-exposure framing, ends with the headline number ("With equal power, distributed base stations contribute 2 to 3 times less to exposure than collocated base stations."). Uses italics for newly introduced jargon (`\textit{clusters}`).

**npj 2026** — single-paragraph traditional abstract, ~280 words. Opens with a layman quote in quotation marks (a rhetorical device unique to this paper: "the layman's question arises: ``how much exposure do I \textit{realistically} experience when I walk down the street?''"), immediately pivots to method, then ends with comparison numbers (20 dB, 12 dB) and a compliance reassurance (less than 1% of ICNIRP).

**PMB 2026** — **structured abstract** with bold-italic headers `\textit{Objective.}`, `\textit{Approach.}`, `\textit{Main results.}`, `\textit{Significance.}`. Each section is short paragraphs of single-claim sentences. The numeric anchors come in batches: "Children show 1.5–1.9~times higher whole-body SAR…", "A 6-year-old reaches 93\%…", "Brain SAR decreases by 96\%…", "Eye SAR drops 77-fold…".

**Override**: the structured shape was **forced by the IOP / Phys. Med. Biol. journal style**, not chosen. It is not the author's preferred abstract format. For non-IOP venues, default to the traditional flowing single-paragraph abstract (the npj or IEEE Access shape). Do not import the structured-abstract pattern into a draft unless the target journal mandates it.

### 13.2 Novelty enumeration

All three papers explicitly enumerate their novelty in the introduction:

- Older: "we present the first" + 2-item enumerate.
- npj 2026: "this work is novel in the following ways:" + 4-item enumerate.
- PMB 2026: "Three gaps limit current understanding…(1)…(2)…(3)…" inline, then the methods paragraph that addresses each.

The enumeration is always pinned to specific bands, technologies, or phantoms — never abstract.

### 13.3 End-matter

Required sections, in order:

**npj 2026** (npj wireless / IEEE-class):
- `\section{Acknowledgements}` (note the British spelling — see §15)
- `\section*{Data Availability}` (numbered or starred varies)
- `\section*{Author Contributions}` (CRediT-style sentence per author cluster)
- `\section*{Competing Interests}` ("The authors declare no competing interests.")

**PMB 2026** (iopjournal-class custom commands):
- `\funding{...}` — full grant agreement text including required EU disclaimer.
- `\roles{...}` — CRediT taxonomy by author (Conceptualization, Methodology, etc.)
- `\data{...}` — code / data / phantom availability with specific repo/license names.
- `\suppdata{...}` — Supplementary Information description.
- `\conflict{...}` — defined inline because the iopjournal class lacks the macro.

**Older paper** (IEEE Access):
- `\begin{IEEEbiography}` blocks with photo and mini-bio per author.
- No explicit data/conflicts sections (acknowledgements were part of `\tfootnote{}`).

### 13.4 Order-of-magnitude headlines

Every paper closes — both abstract and conclusion — by stating:
1. The headline number (e.g., 1% of ICNIRP, 93% of basic restriction, 20 dB difference).
2. The condition under which it holds (precoded LOS, FR3 7 GHz, child phantom).
3. The implication for the reader (network planner, regulator, public).

This three-step closing is a structural fingerprint.

### 13.5 Limitations and future work

In the conclusion, the author always:
1. States 2–3 limitations explicitly (often introduced as "Several extensions merit investigation" / "There are two key limitations of this study.").
2. Suggests concrete future directions, often pointing at specific tools or measurement modalities ("body-worn dosimeter", "MaMIMO testbed", "Posture variations").
3. Avoids overstating broader impact.

---

## 14. Authorial voice and rhetorical posture

### 14.1 The novelty disclaimer

A near-fixed phrase, with slight cross-paper drift:

- 2022 IEEE Access: "to the best knowledge of the authors"
- npj 2026: "To the best knowledge of the authors, this work is novel in the following ways:"
- PMB 2026: "To the best of the authors' knowledge, this is the first study to perform…"

Tells you which paper you're reading — but the move is always the same.

### 14.2 Stance: numeric-anchored, mildly cautious

- The author rarely makes a qualitative claim without a number.
- Hedging is reserved for inferred mechanisms, not measurements.
- The discussion sections take an explicit policy / engineering stance ("more power can be fed to a 6G CF-MaMIMO system…", "Reference levels were derived from uniform plane-wave exposure and do not account for this scenario.")

### 14.3 The "first" / "novel" cadence

When making first-claims, the author piles them into the intro (the enumerate or the sentence "we present the first") and then *does not* repeat them throughout the paper. Conclusion uses "characterized" / "demonstrated" / "show" instead of "first / novel" — the framing matures from prospective to retrospective.

### 14.4 Reader address

The reader is implicit. No "the reader will note", no "you can see". The author makes claims and shows figures.

---

## 15. Tells, tics, and minor inconsistencies

These are the small idiosyncrasies that survive across papers.

### 15.1 British / American spelling

**Override**: pick **American English** for IEEE venues (and as the default unless a target journal specifies British).

- Use "modeling", "modelled" → "modeled", "behavior", "acknowledgments" (US: no second "e"), "centimeter", "millimeter", "fiber".
- Search-and-fix British leak before submission: "behaviour", "modelling", "acknowledgements", "centimetre", "millimetre", "polarisation", "characterise", "optimise".
- The example papers drift between forms — that's a draft mistake, not a stylistic choice.

### 15.2 Hyphen drift on `mmWave` / `mm-Wave` / `millimeter-wave`

Already mentioned (§2.3). Pick one and stick with it within a paper, but the author's choice changes between papers.

### 15.3 `\, .` vs `\,.`

In npj 2026 and 2022 IEEE Access, the form is `\, .` (space after thin space, before period). In PMB, `\,.` (no space) is more common. Both render identically; the author isn't strict about source-level whitespace inside math.

### 15.4 `Fig.~\ref{}` vs `Fig. \ref{}`

The non-breaking tilde is the disciplined form. About 5–10% of references slip and use a regular space — always a draft mistake, never deliberate.

### 15.5 Typos — fix, don't preserve

**Override**: typos are mistakes, not voice. Find and fix every one. Do not import them into new drafts.



- "scalibility" (should be "scalability") — npj 2026.
- "miutes" (should be "minutes") — npj 2026.
- "Eventhough" (should be "Even though") — npj 2026.
- "henceforth" used naturally; "as we shall see" rare but appears.
- "excepted" appears once where "expected" was meant — npj 2026.
- "hybdrization" (typo for "hybridization") — npj 2026.
- "numer" for "number" — PMB.
- "Departement" (typo for "Department") — older paper affiliation line.
- The newer papers contain more typos than the older paper — likely because the older paper went through full IEEE copy-edit while the 2026 papers are pre-publication.

### 15.6 Trailing space after equations

Sometimes `\, .` followed by a blank line then prose, sometimes the prose continues immediately. Consistent within sections, less so across.

### 15.7 `\textit{}` vs. `\emph{}`

- `\textit{}` — dominant for emphasis and italic terms.
- `\emph{}` appears in PMB more than the others, typically for newly defined terms inside Methods (`\emph{hotspot score}`, `\emph{brain group}`, `\emph{eyes group}`). The two are not mixed within a single sub-context.

### 15.8 Acknowledgement ordering

ERC grant first, then Methusalem, then FWO — same order in npj as in older paper. This is the author's recurring funding stack and the order is preserved.

### 15.9 Author affiliation line

Older: "Departement of Information Technology" (typo).  
npj: "Department of Information Technology, Ghent University/IMEC, 9052 Ghent, Belgium."  
PMB: "Department of Information Technology, Ghent University - imec, WAVES Research Group, Technologiepark-Zwijnaarde 126, 9052 Ghent, Belgium" (more complete, includes group name and street).

The PMB form is the most complete; the npj form is the abbreviated default.

### 15.10 Date stamps in references

`[Accessed: Oct.~2024]` and `[Accessed Aug.~2022]` styles both appear. Month abbreviation is not standardized.

---

## 16. Differences between the three papers (evolution)

A short table of the most salient cross-paper deltas.

| Dimension | 2022 IEEE Access (older) | 2026 npj (newer 1) | 2026 PMB (newer 2) |
|-----------|--------------------------|--------------------|---------------------|
| Class file | `ieeeaccess` | `IEEEtran` | `iopjournal` |
| Citation style | numeric, descriptive keys with spaces | numeric, terse keys | author-year, name+year+keyword keys |
| Bibliography | `\begin{thebibliography}{00}` IEEE | IEEE w/ `\doi{}` macro | natbib-iop with `\emph{et al}` |
| Tables | old-school `|c|c|c|` + `\hline` | `booktabs` partial | `booktabs` + `\rowcolor` palette |
| Subsubsections | mix of `\subsubsection` and italic leads | predominantly italic leads | predominantly real `\subsubsection` |
| Subsubsection headings | descriptive nouns | descriptive nouns | finding-as-heading style |
| Abstract | traditional flow | traditional flow with layman quote | structured (Objective/Approach/Main results/Significance) |
| Captions | descriptive | descriptive | lead-with-finding |
| Author block | IEEE biographies w/ photos | ORCID + thanks footnotes | ORCID + affil block |
| Voice | mixed we/passive | mixed we/passive | crisper "we", more direct "this work" |
| Numeric formatting | `2 to 3 times` | `20~dB`, `12~dB`, `4\%` | `1.5--1.9~times`, `131--158\%` (en-dash form) |
| Hyphenation of mmWave | `mm-Wave` / `mm-waves` | `mmWave` / `\gls{mmWave}` | `millimeter-wave` / `mmWave` |
| End-matter | `IEEEbiography` | `Acknowledgements` + `Data Availability` + `Author Contributions` + `Competing Interests` | `\funding` / `\roles` / `\data` / `\suppdata` / `\conflict` |
| Length | shortest (~10 pages) | medium (~12 pages) | longest (~16 pages with omnibus parameter table) |
| Tone | engineering-first | engineering + light public-facing voice (the layman quote) | regulatory / public-health stance, dosimetry-first |

The trajectory:
- Tighter numeric anchoring over time.
- More explicit gap-method-claim sequencing in introductions.
- Less reliance on italic-paragraph leads, more on real subsubsection structure (PMB).
- Cleaner citation-key conventions (descriptive-with-spaces → namelastname+year+keyword).
- More aware of public-policy framing (the PMB conclusion explicitly addresses regulators and WRC-27).
- More "lead with the finding" caption style by 2026.

---

## 17. Pure tells: phrases that almost guarantee Wydaeghe authorship

If you see any of these in isolation, you can guess the author:

1. "**realistic** human exposure" / "realistic 5G EMF-levels" / "realistic exposure".
2. "**To the best (of the) knowledge of the authors**, …".
3. A display equation ending in `\, .` or `\, ,`.
4. "**Hot-spot**" with that specific hyphenation in a non-MIMO sentence.
5. Numbered "**this work is novel in the following ways**" inline at end of intro.
6. "**Realistic**" + "**worst-case**" co-occurring in the same paragraph (the author always frames their work against worst-case literature).
7. "**ICNIRP**" used as both a noun (the body) and modifier ("ICNIRP guidelines", "ICNIRP basic restriction", "ICNIRP reference level"). Always capitalised, always present.
8. "**Compliance margin**" used as a noun phrase rather than "headroom" or "safety factor".
9. The exact triplet **"reference quantities" + "basic restrictions" + "exposure metrics"** as the operating vocabulary.
10. "**Site-specific**" alongside "deterministic" / "stochastic" — the channel-modeling positioning.
11. A flowchart figure as the *first figure* in Methods.
12. Acronym ladder at the top of the preamble using `\newacronym{...}{...}{...}` for at least 30 entries.
13. `\input{Figures/<name>.pdf_tex}` (Inkscape vector with text).
14. Passive in Methods, "we" in Conclusion.
15. The phrase "**case study**" in a section heading.

---

## 18. Practical implications for editing

If editing or co-authoring with this voice in mind:

- Keep equation-end punctuation inside the equation, with a thin space.
- Use `~` before every unit and short numeric reference. Reflexively.
- Define every acronym via `\newacronym{}` once; never bare-spell after first use.
- Open Results paragraphs with "Figure X shows…" or a direct claim-with-number.
- For each claim, attach a number with units and a one-clause mechanism.
- Avoid em dashes; restructure with commas, parens, or colons.
- Keep section / subsection titles in sentence case.
- For PMB-style writing, use `\subsubsection{}` with finding-as-title; for npj-style, italic paragraph leads are acceptable.
- Use `booktabs` and put captions above tables.
- For figure captions, prefer the lead-with-finding shape if the journal allows, otherwise descriptive.
- Cite specific papers, not "the literature".
- Hedge mechanisms, not measurements.
- End the conclusion with a numeric headline, a condition, and an implication.

---

*Generated from a deep read of the three `.tex` sources in `papers/example_papers/`. Patterns are reported with examples and ranked by qualitative prominence rather than exhaustive count.*
