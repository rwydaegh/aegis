# Handover brief: writing the JSAC paper

You are writing the JSAC paper for Robin Wydaeghe, sole author at Ghent
University + imec. Three sister papers (A, B, C) are already drafted and
share the same conventions; this brief distils what Robin actually wants,
extracted from his direct feedback in `papers/user_inputs.md`. Read that
file in full before you start.

## What he expects

- Publication quality, not a draft. He says: "It's not just a draft."
- He'll give you a long autonomous floor. "You can have the floor for a
  long time. Impress me. You are opus. You are in control. You have
  freedom. Get guided by a great paper not just copying or summarizing
  a monograph."
- Pivot when zooming in if the framing isn't working.
- Iterate. Multiple compile-render-critique cycles, not one-shot.
- Use sub-agents for parallelisable sub-tasks but brief them thoroughly
  with file paths, excerpts, and explicit acceptance criteria.

## Files to read before writing

| File | Purpose |
|---|---|
| `papers/how_to_write_good/style_guide.md` | Master language rules. Part C ("Voice and Tone Preferences") is the spec. |
| `papers/how_to_write_good/style_analysis.md` | The monograph's voice. Emulate it. |
| `papers/how_to_write_good/ai_writing.md` | AI-tells catalogue. Read once, sweep against. |
| `papers/key_literature/Kodera2024.pdf` | IEEE format reference (TMTT but applies). |
| `theory/monograph_v2.tex` | Theorem/proposition style, equation conventions, prose voice. |
| `papers/drafts/paper_A.tex`, `paper_B.tex`, `paper_C.tex` | Sister papers; same conventions, same author block. |
| `papers/drafts/refs.bib` | Shared bibliography. Append only, do not edit existing entries. |
| `papers/user_inputs.md` | Robin's verbatim feedback on the sister papers. The most useful single source. |

## LaTeX preamble and structure

- `\documentclass[journal,twocolumn,10pt]{IEEEtran}`. Use the same
  preamble template as `paper_A.tex` (cite, hyperref, cleveref,
  amsmath/amssymb/amsthm, bm, booktabs, subcaption).
- `\graphicspath{{../../theory/figures/}{../../validation/}{figures/}}` (and
  `{figures/jsac/}` if you have your own).
- Title in plain prose, no `\textbf{}`, no manual line breaks.
- Author block: Robin Wydaeghe, sole author, UGent + imec.
- `\markboth{IEEE Journal on Selected Areas in Communications, Vol.~XX,
  No.~X, Month~2026}{Wydaeghe: <short title>}`.
- Use `\IEEEPARstart{X}{xxx}` to open the introduction.

## Section structure

- Descriptive section titles, NOT strict IMRAD. "Methods" and "Results"
  forced into IEEE papers is *not* what Robin wants. Look at sister
  Paper C for the genre: "System model", "Coherent absorption law",
  "Path-space factorisation", "Numerical demonstration", "Discussion",
  "Conclusion". Plain noun phrases.
- No section title starts with "The".
- Drop clever framings ("Three branches of one carrier" — that kind of
  thing got removed from C).
- Do NOT subsection the Introduction. One flowing block.
- Discussion and Conclusion are separate sections, not combined.
- Use appendices for long derivations to keep the body within journal
  page budget.

## Standalone

- Zero "as in companion Paper~A/B/C". Zero "see Paper~A". Zero
  cross-paper labels. The paper must hold up on its own.
- Overlap with sister papers is fine. Cross-references are not.
- If you need a result from a sister paper, restate it briefly and cite
  any actual published version. Do NOT cite a "Wydaeghe2026" arXiv
  preprint that does not exist. Robin pushed back on that explicitly.
- "and co-workers" -> "et al.~". Robin asked for this verbatim.

## Voice and language

- Subject-verb-rest sentences. Present tense for stable results.
  Past tense for what was done in this study.
- Short sentences default. Long ones only for enumerations or lists.
- "Respectively" allowed freely; no cognitive load penalty.
- No semicolons in body prose (preamble `\Crefname{}` is OK).
- No em dashes (`---` or `—`). No emojis. No bold for emphasis.
- Justified text via the IEEEtran default. Don't break paragraphs every
  sentence. Mimic IEEE literature density: contiguous prose blocks with
  meaningful paragraph breaks.

## Words to hunt and replace (Robin is sensitive to these)

| Class | Examples to remove or replace |
|---|---|
| Inflated verbs | utilise, demonstrate, leverage, enable, facilitate, embody, encompass, capture (non-literal), unify, expose, reveal, elucidate, illuminate, deliver, attain, commence, terminate. |
| Promotional adjectives | powerful, elegant, remarkable, striking, compelling, robust (non-statistical), sophisticated, comprehensive (filler), groundbreaking, novel, innovative. |
| Filler intensifiers | very, highly, extremely, particularly, especially, remarkably, notably, crucially, importantly. |
| Throat-clearing | "It is worth noting", "It should be emphasised", "In essence", "It can be shown that", chained "Furthermore / Moreover / Additionally". |
| Editorialising tail clauses | "...ensuring broader adoption", "...highlighting its importance", "...underscoring the significance". |
| AI tells | "Not only ... but also", "from X to Y" with no real range, rule-of-three triplets, generic "it shows the importance of". |

## Mic-drop sentences (the worst offender)

A short stinger (<= 6 words) that follows a long sentence (>= 12 words)
and reads like a punchline. Robin's example: after a long buildup, a
3-word sentence "The physics does not." is exactly the pattern he hates.
Fold all such sentences into the surrounding prose. Examples we already
removed:
- "This collapses dosimetry to geometry." (Paper A)
- "We substitute our analytical Q." (Paper C)
- ":  one identity, five independent studies" (lit_waterfall suptitle)

Apply the same surgery to your draft.

## Tone

- Do not be alarmist about regulatory or biological consequences. Stay
  factual. "This happens every day in dosimetry" is Robin's own line.
- Be critical of your own claims. State limitations honestly. State
  conservative-vs-non-conservative direction of every error.
- Wide-then-narrow introduction: open with the broader trend (5G/6G
  deployment, ICNIRP 2020 shift, sensing-communication convergence),
  narrow through the prior-art tradition with named work, narrow further
  to the specific gap, then state the contribution. Don't open with
  equations.
- Position honestly against prior work. If a sister method has the same
  idea in different notation (e.g. Flintoft's gamma_s = ambient
  occlusion), say so and frame your contribution as extension or
  closed-form, not as novelty.

## Don't quote unreliable internal numbers

- The "backflip variability" number from internal AEGIS validation has a
  suspected bug. Robin said: "the backflip probably has an error cuz I
  think the variability is suspiciously low. so dont quote that."
- The 7 GHz Sim4Life total-power factor-of-2 anomaly is a Sim4Life setup
  artefact. Carve it out in one sentence; do not headline.

## Figure pipeline

- Use the project SciencePlots helper:
  ```python
  import sys
  sys.path.insert(0, "theory/scripts")
  from _plot_style import apply_monograph_style, fig_size_ieee
  apply_monograph_style(mode="pdf")
  fig, ax = plt.subplots(figsize=fig_size_ieee(columns=1, aspect=0.75))
  ```
  `mode="pdf"` enables LaTeX rendering with Latin Modern, matching the
  paper body. `fig_size_ieee(columns=1)` returns 3.5 in (single col),
  `columns=2` returns 7.16 in (full text width for `figure*`).
- Save PDF (vector with LaTeX text) AND PNG (for critique). PDF goes in
  the paper; PNG is for visual review.
- Typography: paper body 10 pt -> axis labels/ticks 8 pt, panel titles
  8.5 pt, legends 6-7 pt. Robin explicitly accepts <10 pt legends when
  density forces it.
- Self-contained labels: no internal AEGIS jargon ("L2/L3/L4/L_all/×O")
  in figures unless the paper defines it. Replace with physical names:
  "Fresnel only", "+ polarisation", "+ curvature & diffraction", "Full
  kernel", "+ occlusion".
- Phantom-with-colour visualisations land much harder than line plots in
  the bioEM genre. If your data supports one, add one. Re-render via
  AEGIS scripts (e.g. `visualize_sab_3d.py`,
  `visualize_eta_3d.py`, `compute_exposure_fraction_eta.py`) at clean
  publication styling, not the internal-grade defaults.
- Iterate relentlessly on layout: no legend overlapping data, no wasted
  whitespace in any quadrant, no mangled tick labels.

## Compile-render-critique loop (mandatory)

After every substantive revision pass:

```bash
cd papers/drafts
pdflatex -interaction=nonstopmode paper_jsac.tex
bibtex paper_jsac
pdflatex -interaction=nonstopmode paper_jsac.tex
pdflatex -interaction=nonstopmode paper_jsac.tex
rm -rf tmp_jsac && mkdir -p tmp_jsac
pdftoppm -r 150 -png paper_jsac.pdf tmp_jsac/p
```

Then `Read` every `tmp_jsac/p-NN.png`. Look for:
- column overflow on long matrix or aligned equations
- figures spilling beyond their column
- legend boxes covering data
- broken `??` references
- bad page breaks (orphan headings, half-empty pages from float pressure)
- font inconsistencies (e.g. text in non-Latin-Modern)
- equations broken across columns

Fix what you see, recompile, repeat. At least 3 cycles. Stop only when
you can read every page and see no sloppiness.

## Acceptance bar before declaring done

- pdflatex exit 0.
- No `??` in PDF.
- No Overfull `\hbox` greater than ~10 pt.
- All `\cref{...}` resolved.
- Page count within journal target (JSAC is typically 8-14 pages).
- Visual scan of every page PNG passes a "no reader will say this looks
  sloppy" test.
- A grep for the inflated-words list above returns mostly false
  positives (a few left is fine if the technical context demands it).

## Final checklist before handing off

1. Run `python -m ruff check theory/scripts validation/scripts` if you
   touched any plot scripts (Robin runs ruff in pre-commit).
2. Confirm the figure scripts you used actually produce reproducible
   output if Robin runs them again.
3. Write a short report (<400 words) with: top 3 structural choices, top
   3 figure design choices, anything you intentionally left rough.

Do not push to git, do not tag a release, do not commit. Robin commits
when he is happy.
