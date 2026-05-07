# Agent brief: IEEE journal-quality revision of the three papers

You are revising one of three companion papers (A, B, or C) drawn from the
AEGIS dosimetry monograph (`/home/user/aegis/monograph/monograph_v2.tex`).
The revision is comprehensive: structure, layout, language, figures.

The three papers, after revision, must be **standalone**: a reader of paper
B has not read A, and the paper must hold up. Some content overlap is
expected and acceptable; the cardinal sin is `\cref{}` or "see companion
Paper~A" type references. Each paper rederives or restates whatever it
needs.

## What the user said, in his words

The summary that follows is a faithful paraphrase of the user's directional
guidance. Treat this as the highest-priority requirement set.

1. **IEEE journal layout.** The current drafts are single-column `article`
   class. Convert to **IEEEtran two-column** (journal article style).
   Use 10pt. Page budget is the journal's normal limit; use appendices to
   absorb derivations if the body is tight.

2. **IEEE structure.** IEEE is "very keen" on the IMRaD-with-discussion
   pattern. Roughly: Introduction → Methods/Theory → Results/Validation →
   Discussion → Conclusion. Adapt as appropriate but keep the spine
   recognisable. **Do not subsection the Introduction.** The intro is a
   single flowing block.

3. **Section names.** "Subtitles should be deadsimple and clear (not
   'What this paper is' lol)." Replace clever or self-referential headings
   with plain noun-phrases. Examples of fine headings:
   "Computational models and methods", "Refined skin thickness",
   "Discussion". Examples of bad headings: "What this paper does",
   "Three branches of one carrier", "Mechanism" (too vague). Always check
   that no heading begins with "The".

4. **Standalone papers.** "We can't have 'as in paper A'. It's standalone.
   But overlap is okay." Find every "companion Paper~A/B/C", "as derived
   in Paper A", "see Paper B", and either rederive the result inline,
   restate it as a known fact with a citation to the monograph
   (`\cite{Wydaeghe2026Monograph}`) or to the AEGIS preprint, or remove
   the cross-reference. **Zero cross-paper references in the final draft.**

5. **Language: simpler, drier, present-tense, subject-verb-rest.** The
   user wrote: "you should review many sentences to make sure there is
   no unnecessary constructions and big(ish) words. I am sensitive to
   that." Style: "The experiment shows a higher X value." kind of
   sentence. Subject + verb + a small bit. Default short. Long sentences
   only for enumerations/lists. **"Respectively" is allowed freely.**

6. **No mic-drop sentences.** The user's exact phrase: "you have a lot
   of 'mic drop' moments. Like. You are describing something, clearly
   holding yourself in to not splurge, and then say a 3 word sentence
   like 'The physics does not'. No need." Find and remove these short
   stinger sentences that follow a buildup.

7. **No promotional language.** No "powerful", "remarkable", "elegant",
   "groundbreaking", "stunning", "we make several key contributions",
   "the framework's strength lies in...", etc. State the result; let the
   reader judge.

8. **Big paragraph blocks, justified text.** Mimic IEEE literature.
   Paragraphs of contiguous prose, not one-sentence-per-newline. Leave
   meaningful space between paragraphs. Use `\justify` (default in
   IEEEtran) and avoid `\\` line breaks in body text.

9. **Figures fit IEEE columns.** Single-column figures fit in 3.5 in
   (~89 mm). Full-page figures in `figure*` use 7.16 in. Find the figure
   scripts (e.g. `papers/drafts/figures/lit_waterfall.py`,
   `figures/paperC/paperC_simulate.py`) and adjust `figsize=` so the
   rendered PDF looks correct at the target width. Re-run the script.

10. **Compile-render-critique loop.** "Do a big write now, compile,
    convert to png, read the png files, critique visual issues, iterate
    until satisfied. Especially when latex is unusual." After each major
    revision pass: compile with `pdflatex` (twice for refs) and `bibtex`,
    convert each PDF page to PNG with `pdftoppm -r 150 -png`, read each
    page image, fix what looks broken (overflow boxes, broken floats,
    wrong figure widths, broken cross-references, equations spilling out
    of column), recompile.

11. **No emojis, no em dashes (—), no semicolons in body prose.** Replace
    semicolons with periods or restructure. Replace em dashes with comma,
    parens, colon, or rephrase.

## Style guides to read

Before you start writing, read these in full. They are short.

- `papers/how_to_write_good/style_guide.md` (the master guide; ~450 lines)
- `papers/how_to_write_good/style_analysis.md` (style example: the
  monograph; emulate this)
- `papers/how_to_write_good/ai_writing.md` (catalogue of AI tells to
  avoid; can skim)

The single most useful section is style_guide.md PART C ("Voice and Tone
Preferences for This Project"). The single most useful concrete model is
style_analysis.md, which describes the monograph's writing style.

## IEEE formatting reference

A sample IEEE TMTT paper is at `papers/key_literature/Kodera2024.pdf`,
with PNG renders in `papers/key_literature/kodera_pages/p-*.png`. Look at
its section headings, paragraph density, equation density, and figure
captions. The user explicitly wants the papers to look like that.

Kodera's section structure (page 2 onwards):
- I. Introduction
- II. Computational Models and Methods
  - A. Finite-Difference Time-Domain Method
  - B. Original Anatomical Human Models
  - C. Models with Refined Skin Thickness
- III. (results)
- IV. Discussion
- V. Conclusion
- Appendix
- References

Section headings are in title case but plain noun phrases (no "The...").

## IEEEtran preamble template

```latex
\documentclass[journal,twocolumn,10pt]{IEEEtran}

\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{microtype}
\usepackage{amsmath,amssymb,amsthm,mathtools}
\usepackage{bm}
\usepackage{graphicx}
\graphicspath{{../../theory/figures/}{../../validation/}{figures/}}
\usepackage{booktabs}
\usepackage{array}
\usepackage{caption}
\usepackage{subcaption}
\usepackage{cite}        % IEEEtran-friendly
\usepackage{xcolor}
\usepackage[colorlinks=true,linkcolor=blue,citecolor=blue,urlcolor=blue]{hyperref}
\usepackage[capitalize]{cleveref}

% Theorem environments
\theoremstyle{plain}
\newtheorem{theorem}{Theorem}
\newtheorem{proposition}[theorem]{Proposition}
\newtheorem{corollary}[theorem]{Corollary}
\theoremstyle{remark}
\newtheorem{remark}[theorem]{Remark}

\crefname{proposition}{Proposition}{Propositions}
\Crefname{proposition}{Proposition}{Propositions}
\crefname{corollary}{Corollary}{Corollaries}
\Crefname{corollary}{Corollary}{Corollaries}
\crefname{remark}{Remark}{Remarks}
\Crefname{remark}{Remark}{Remarks}

% Math macros (customise per paper as needed)
\newcommand{\khat}{\hat{\bm{k}}}
\newcommand{\nhat}{\hat{\bm{n}}}
\newcommand{\rr}{\mathbf{r}}
\newcommand{\Sinc}{S_{\mathrm{inc}}}
\newcommand{\Sab}{S_{\mathrm{ab}}}
\newcommand{\Tavg}{T_{\mathrm{avg}}}
\newcommand{\Tbar}{\bar{T}}
\newcommand{\ntilde}{\tilde{n}}
\newcommand{\diff}{\mathrm{d}}
\DeclareMathOperator{\ReLU}{ReLU}
\DeclareMathOperator{\RE}{Re}

\begin{document}

\title{<Plain title in sentence case>}
\author{Robin~Wydaeghe%
  \thanks{R. Wydaeghe is with Ghent University and imec, Ghent, Belgium
  (e-mail: robin.wydaeghe@ugent.be).}}

\markboth{IEEE Transactions on <Antennas and Propagation/Wireless Communications>,
  Vol.~XX, No.~X, Month~2026}%
{Wydaeghe: <Short title>}

\maketitle

\begin{abstract}
...
\end{abstract}

\begin{IEEEkeywords}
keyword 1, keyword 2, keyword 3
\end{IEEEkeywords}

\IEEEpeerreviewmaketitle

\section{Introduction}
\IEEEPARstart{T}{he} <intro starts here, no subsections>...

\section{Theory}
...

\section{Validation}
...

\section{Discussion}
...

\section{Conclusion}
...

\appendices
\section{Proof of ...}
...

\bibliographystyle{IEEEtran}
\bibliography{refs}

\end{document}
```

Bibliography: `refs.bib` is shared across all three papers. Use existing
entries when possible. If you need a new entry, append it; do not edit
existing entries.

## Compile and render commands

From `papers/drafts/`:

```bash
pdflatex -interaction=nonstopmode paper_X.tex
bibtex paper_X
pdflatex -interaction=nonstopmode paper_X.tex
pdflatex -interaction=nonstopmode paper_X.tex
mkdir -p tmp_render_X
pdftoppm -r 150 -png paper_X.pdf tmp_render_X/p
```

Then `Read` each `tmp_render_X/p-NN.png` to inspect. Watch for:
- overfull `\hbox` warnings in the log
- figures wider than the column
- equations broken at column edge
- bad page breaks (orphan headings)
- `??` for missing references
- broken `\cref` links

Iterate until clean.

## Output expectations

When you finish, the deliverables are:
- `paper_X.tex` IEEEtran two-column, compiles cleanly
- `paper_X.pdf` rendered, no overflow, no broken floats
- Updated figure scripts and rendered PDFs in `figures/...`
- A short report (under 300 words) describing: top three structural
  changes you made, top three language fixes, what visual issues you saw
  in the PNG renders and how you fixed them, and any remaining concerns.

Do NOT touch the other two papers. Do NOT edit other authors' bib
entries. Coordinate by appending only.

Good luck. Be aggressive with the language. The user's threshold for
mediocrity is low.
