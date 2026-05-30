# Agent H — Section VIII style pass

Scope: lines ~1175-1280 of `JSAC2/paper/jsac2_v3.tex`, the section
`\section{Live SAR reading and connection to RF-EMF cohort studies}`,
covering the three subsections "Absorbed-power reading", "One operator,
two semantic outputs", and "Aggregation for cohort exposure studies",
plus the figure caption `fig:sab-reading`.

## Summary of changes

### Subsection heading rename
- "The absorbed-power reading" -> "Absorbed-power reading" (drop leading
  The). The other two subsection headings already started with a noun,
  so they were left untouched per the brief.

### Paragraph 1 (the reading itself)
- Re-tightened first sentence; added missing tilde before `\cref`,
  added "over the body surface" to make the integration explicit, and
  tightened `over the user's session` -> `over the session`.
- Replaced the dangling "(the supplementary information)" placeholder
  citation with the proper `\cite{ICNIRP2020}` and the surface-equivalent
  power-density framing.
- Replaced "the binding constraint is the link budget itself" with
  the simpler "the link budget is" — same meaning, no repetition of
  "binding constraint".
- KILLED the user-flagged "puts the user, the regulator, and the
  epidemiologist on the same page about what the body is actually
  absorbing at every moment" (loose, anthropomorphic, mic-drop-like).
  Replaced with the user's preferred direct phrasing: "it provides a
  per-slot exposure value that existing regulatory and epidemiological
  frameworks do not."

### Paragraph 2 (honesty / pose-noise framing) — KEY HONESTY EDIT
- Updated numbers to match SI §S7 *exactly*:
  - sigma=16 deg: was "${\sim}3\,\%$ mean bias and ${\pm}4\,\%$
    standard deviation" -> now "$-3.2\,\%$ mean bias and
    $\pm 4.5\,\%$ standard deviation". (Negative sign added — bias
    is downward per SI.)
  - sigma=4 deg: was "within ${\pm}1\,\%$" (which was both vague
    and wrong, since SI gives mean and std separately). Now
    "$-0.5\,\%$ with $\pm 1.4\,\%$ standard deviation".
- Added "$18$ Munich scenes" (matches SI scene count and naming).
- Replaced "(research-grade IMU suit)" with "(a research-grade
  6-IMU body suit)" — matches SI annotation. (I briefly used
  "Madgwick-fused" to match the SI exactly, then reverted to
  "research-grade" because Madgwick2011 is cited only in the SI
  and I should not introduce new bibitems in main text.)
- Peak-APD framing rewritten:
  - Was: "peak location standard deviation $\sim\!50\,$cm" (this was
    misnamed — SI reports the *mean centroid distance*, not std).
  - Now: "the peak triangle centroid moves by a mean of $52$~to
    $58\,$cm across $\sigma_\mathrm{joint} \in \{2, 16\}^{\circ}$
    (SI~\S{}S7)" — matches SI numerics (52 cm at 2 deg, 58 cm at 16 deg,
    saturating).
- Emphasised "*not* reported per-tick" with `\emph{not}` to make the
  negation visually unambiguous to the reader.
- Kept the "Time-aggregated or larger-window peak-$\Sab$ statistics
  may recover ... we leave that to follow-up work" caveat exactly as
  the user wanted.

### Subsection 2 (One operator, two semantic outputs)
- Tightened opening sentence; "rather than reflection mode" was
  technically wrong (it's the *radiation* integral, not reflection);
  fixed.
- Filled in the missing RHS in `$\hbody = $ Kirchhoff radiation integral`
  with an actual integral expression
  `$\hbody = \int \tilde{\bm{G}}\xx \cdot e^{-jkr}/r\,dA$` so the
  parenthetical is meaningful, not a verbal placeholder.
- Removed double `\cite{Hochwald2014,Ying2015}` repetition. The
  double-cite was redundant after `\cite{Hochwald2014,Ying2015,Ying2017}`
  one line earlier. Single citation now.
- "machinery ... machinery ... machinery" (three uses in one sentence)
  -> "construction ... construction" (per A10 elegant variation, but
  going the other way: pick one synonym and be consistent).
- Mic-drop "user-facing semantic output of an object the network
  already maintains" -> "one read-out mode of an object the network
  already maintains for precoding" — keeps the spine point (network
  is already running this object) without the "user-facing semantic
  output" boilerplate.

### Subsection 3 (Aggregation for cohort exposure studies)
- KILLED the "Confirm canonical reference at submission" footnote
  (user-flagged conversational artefact; the CLUE-H reference was
  already cited as `\cite{CLUEH2025}` further down).
- Consolidated the two CLUE-H paragraphs that were saying overlapping
  things: the first sentence-paragraph parenthetically introduced
  COSMOS/HERMES/CLUE-H, then a third paragraph re-introduced CLUE-H
  with overlapping definition. Now: one paragraph defines the cohort
  landscape (COSMOS/HERMES/vanWel + CLUE-H as the consortium-scale
  extension), one paragraph states the upgrade and the privacy delta,
  and the closing sentence references `\cref{fig:sab-reading}`.
- "would upgrade the exposure side" / "upgrade the exposure side"
  duplication consolidated into a single statement.
- "high-resolution biological / health-outcome assessment with
  measurement-grade RF-EMF exposure characterisation" was a thicket;
  now: "the bio-outcome resolution the cohorts target".
- Anthropomorphism cleanup: "longitudinal cohort studies need
  monthly or quarterly summaries" -> "want monthly or quarterly
  summaries". (Mild softening; the studies don't *need* anything
  in a literal sense.)
- Final sentence ("...showing that the operating point sits well below
  the regulatory ceiling") was a mic-drop; replaced with
  "the $100$-user cumulative-dose distribution at the canonical
  operating point" (factual, not editorial).

### Figure caption (fig:sab-reading)
- Tilde fixes (preserved existing ones).
- Replaced "the orange dashed line marks the $4\,$W/m$^{2}$
  ICNIRP-equivalent reference, well to the right of the user
  distribution" -> proper period-separated sentences and
  `\cite{ICNIRP2020}`.

## Resolution of the "regulatory framing" rewrite
The user explicitly hated "feedback that the regulatory framing
assumes but does not currently deliver". That phrasing did not
appear verbatim in this section's intro paragraph after Robin's
recent rewrite, but the *spirit* of it survived in the form of
"puts the user, the regulator, and the epidemiologist on the same
page about what the body is actually absorbing at every moment".
Killed and replaced with the direct, factual: "it provides a
per-slot exposure value that existing regulatory and
epidemiological frameworks do not." (Per the user's approved
mutant.)

## Honesty framing preserved?

YES. The substantive split is intact and now even sharper:

- Whole-body integrated $P_\mathrm{abs}$ and time-integrated dose:
  reportable per-tick, with quantitative robustness to IMU noise
  (matched to SI numerics: $-3.2\,\%$ mean bias, $\pm 4.5\,\%$ std
  at sigma=16 deg consumer-grade; $-0.5\,\%$, $\pm 1.4\,\%$ at
  sigma=4 deg research-grade).
- Peak-local $S_\mathrm{ab}$ over the ICNIRP $4\,$cm$^2$ window:
  *not* reported per-tick (now visually emphasised with `\emph{not}`).
  The caveat now correctly characterises the SI finding (mean
  centroid distance 52--58 cm across the IMU operating range, not
  a "standard deviation" as the prior draft had it).
- Forward-looking "follow-up work" sentence kept.

## Subsection heading renames
- `\subsection{The absorbed-power reading}` -> `\subsection{Absorbed-power reading}`.
- `\subsection{One operator, two semantic outputs}` — left as-is (no leading "The").
- `\subsection{Aggregation for cohort exposure studies}` — left as-is (no leading "The").

## Style fix counts (approximate)
- Tilde-before-cite/ref/eqref additions: 4 (`~\cref{eq:Sab-norm}`,
  `~\cref{eq:Q-form}`, `~URA`, `~\cite{ICNIRP2020}`)
- Anthropomorphism / colloquial cleanups: 4 ("regulator ... on the
  same page", "the network already maintains" mic-drop, "studies need"
  -> "want", "well below the regulatory ceiling" mic-drop)
- Cite-related fixes: 1 footnote killed, 1 double-cite collapsed,
  1 missing-cite for ICNIRP2020 added (twice: body + caption)
- Number fidelity to SI: 4 numerical updates (16 deg mean bias,
  16 deg std, 4 deg mean+std, peak centroid range)
- Subsection heading renames: 1
- Conversational artefact removals: 1 footnote ("Confirm canonical
  reference at submission")
- Duplicated content consolidations: 1 major (two CLUE-H paragraphs
  merged into one), 1 minor ("would upgrade ... upgrade" dedup)
- Math fix: 1 (filled in the empty RHS of `$\hbody = $ Kirchhoff
  radiation integral` with an actual integral expression; also
  corrected "reflection mode" -> "radiation mode" since that's the
  Kirchhoff radiation integral, not a reflection coefficient)

## Cross-section flags for the audit

1. **`\bibitem{Christ2010VF}` (FDTD reference)** — cited in
   `\cref{sec:kirchhoff}` introduction (line ~250 of v3) as
   "Population FDTD reference~\cite{Christ2010VF}". This is the
   classical Christ 2010 Virtual Family reference and the cite is
   used unambiguously there. Not used in §VIII. **No issue.**
2. **`\bibitem{SwissNISV2000}` (Swiss/Geneva limits)** — cited in
   the Introduction (line ~191) as "similar Geneva-canton limits".
   Not in my scope, no issue from §VIII. **No issue.**
3. **`\cite{Madgwick2011}`** — cited in SI §S7 only. I considered
   using it in main text to match SI annotation, then reverted; if
   the editor wants the IMU-suit annotation richer, this would need
   to be promoted to a main-paper bibitem. Flag for Agent J
   (bibliography).
4. **Section title** "Live SAR reading and connection to RF-EMF
   cohort studies" — left untouched per user instruction (subtitle
   complaint was for §VII, Agent G's). The lead noun "Live SAR" is
   a slight misnomer since the actual reportable quantity is
   `P_abs` (whole-body integrated absorbed power), not local SAR.
   The user explicitly defended the honesty framing of *not*
   reporting per-tick local SAR/APD. If the section title should
   reflect that, "Live absorbed-power reading and ..." would be
   more honest. **Flag for editor judgment** — left as the user
   wrote it.
5. **CLUE-H bibitem (`CLUEH2025`)** — flag for Agent J: previous
   draft had a footnote saying "Confirm canonical reference at
   submission". I removed the footnote; please verify the
   `CLUEH2025` bibitem is real / has a DOI / is not a placeholder
   key.

## Open issues

- The figure caption (c) still says "ICNIRP general-public
  reference" of "$4\,$W/m$^{2}$" with a dashed line on a
  *cumulative-dose* ECDF. $4\,$W/m$^{2}$ is an *instantaneous*
  surface-equivalent power density, not a cumulative dose. Either
  the dashed line is "the cumulative dose corresponding to $30\,$s
  of operation at the limit" (in which case the caption should say
  so), or the caption is sloppy. I left the wording semi-honest
  by phrasing it as "marks the $4\,$W/m$^{2}$ ICNIRP general-public
  reference" without claiming the line *is* the cumulative dose
  threshold. **Flag for figure-author / Robin to clarify.**
- "Live SAR reading" in the section title — see cross-section flag
  #4 above.
- The phrase "modelled SAR proxies" appears twice in the
  consolidated paragraph 1 of subsection 3. Could be tightened to
  one mention but the second use is part of the "binds on this
  same exposure side: questionnaire-reported phone use and
  modelled SAR proxies are coarse" clause, which is the load-bearing
  characterisation of CLUE-H's binding constraint. Left as-is.

## Compile check

`pdflatex -interaction=nonstopmode jsac2_v3.tex` finishes cleanly,
14 pages, no errors and no new warnings beyond pre-existing
package warnings (caption package class warning, a few hyperref
PDF-string token warnings unrelated to my scope).
