# Anatomy of a Wydaeghe introduction

A focused zoom on the Introduction section across the same three example papers used in `wydaeghe_style_analysis.md`:

- **`2026_npj_outdoor_RT-QuaDRiGa-FDTD_28GHz_CF-MaMIMO.tex`** (npj Wireless Comm., IEEEtran)
- **`2026_PMB_multifrequency_FDTD_environmental_auto-induced_450MHz-26GHz.tex`** (Phys. Med. Biol., iopjournal)
- **`2022_IEEEAccess_indoor_RT-FDTD_3.5-28GHz_DMaMIMO.tex`** (IEEE Access, ieeeaccess)

This document complements the broad style audit. The broad audit ranks tells across the whole document; this one dissects how the introduction is built, at three resolutions: macro (the arc of beats), meso (paragraph-by-paragraph moves), and micro (sentence, word, glyph). Override callouts from the broad audit apply here too and are flagged as **Override:** where they touch a specific pattern.

---

## 0. The introduction at a glance

The three intros differ a lot on the surface (one paragraph vs. five, IEEE class vs. IOP, numeric vs. author-year), but they all tell the same story in the same order. The constants are:

- A drop-cap first letter (`\IEEEPARstart` or `\PARstart`).
- The same six beats in the same sequence (technology → exposure framing → state of the art → gaps → this work → enumerated novelty).
- A closing numbered enumerate of contributions, guarded by "To the best (of the) knowledge of the authors".
- Every "first" or "novel" claim is pinned to a specific frequency, technology, or phantom.
- Italic emphasis (`\textit{}` / `\emph{}`) on every freshly named concept.
- Numeric anchors in the introduction itself, not just Methods or Results.

The variable is **how much each beat is broken out**. The 2022 paper crams the first three beats into one long paragraph; npj 2026 gives each beat its own paragraph; PMB 2026 goes further and gives the gap beat an inline `(1)(2)(3)` enumerate plus a stakeholder paragraph at the end.

The trajectory is from "one long flowing intro" to "modular, paragraph-per-beat intro". The newest draft will likely sit closer to the PMB end of that spectrum.

---

## 1. Macro: the six-beat arc

Every Wydaeghe introduction marches through these beats in order. Skipping one is rare; reordering one is even rarer.

| # | Beat | What it does | Anchor phrase types |
|---|------|--------------|---------------------|
| 1 | **Technology setup** | Names the cellular generation, MaMIMO, the frequency bands | "5G and 6G generation", "FR1 / FR2 / FR3", "MaMIMO", "DMaMIMO", "CF-MaMIMO" |
| 2 | **Exposure / regulator framing** | Pivots from technology to health, names ICNIRP, frames "realistic vs. worst-case" | "concerned", "ICNIRP", "worst-case", "realistic" |
| 3 | **State of the art** | Cites prior work, often by author surname in PMB; names methods (RT/FDTD, QuaDRiGa, plane-wave studies) | "Previous \dots~studies", "\citet{dimbylow2002fdtd} established \dots", "Hybrid \gls{RT}/\gls{FDTD} \dots" |
| 4 | **Gaps** | States what's missing, often as inline `(1)(2)(3)` or as "however"-clauses | "However, the method is not suitable for \dots", "Three gaps limit current understanding \dots" |
| 5 | **This work** | One paragraph that says what we did, scoped concretely | "Therefore, this work \dots", "This study addresses these gaps with \dots" |
| 6 | **Novelty enumerate** | Numbered list of contributions, sometimes inline, sometimes as `enumerate`; guarded by the disclaimer | "To the best (of the) knowledge of the authors, this work is novel in the following ways:" |

A good test of whether a draft introduction is "in voice": you should be able to label every paragraph with one of these beats. If two paragraphs do the same beat, merge them. If a beat is missing, the intro is incomplete.

### 1.1 Per-paper trace of the arc

**2022 IEEE Access** (compact, 2 paragraphs + enumerate):

| Para | Beat(s) | Rough length |
|------|---------|--------------|
| 1 | 1 (Technology setup) | ~25 sentences, single dense paragraph |
| 2 | 2 + 3 + 4 + 5 + 6 (Exposure framing → SoTA → gap → this work → "we present the first") | ~12 sentences, ends mid-flow |
| `enumerate` | 6 (2-item novelty list) | 2 items |

**2026 npj** (modular, 5 paragraphs + enumerate):

| Para | Beat | Anchor first sentence |
|------|------|-----------------------|
| 1 | 1 (Technology) | "The \gls{5G} and \gls{6G} generation of cellular networks address the ever-increasing demands \dots" |
| 2 | 2 (Exposure framing + thesis) | "A portion of the population is concerned that these new technologies could lead to adverse health effects \dots" |
| 3 | 5a (Method framing) | "To model the exposure from these technologies, the \textit{propagation step} \dots needs to be interfaced with the \textit{exposure step} \dots" |
| 4 | 3a (Geographic coverage SoTA) | "Google recently introduced an API for their photorealistic meshes \dots" |
| 5 | 3b + 4 (Hybrid RT/FDTD SoTA + gap) | "Hybrid \gls{RT}/\gls{FDTD} is an example of an integrated method \dots" |
| `enumerate` | 6 (4-item novelty list) | "To the best knowledge of the authors, this work is novel in the following ways:" |

**2026 PMB** (most modular, 5 paragraphs + inline gap enumerate + closing stakeholder paragraph):

| Para | Beat | Anchor first sentence |
|------|------|-----------------------|
| 1 | 1 (Technology + auto-induced/environmental + child motivation) | "With the deployment of 5G wireless technology, the number of base stations and antennas per base station has increased significantly compared to 4G \dots" |
| 2 | 3 (SoTA, named-author paragraph) | "Computational dosimetry quantifies \gls{SAR} and \gls{APD} induced in human tissues \dots" |
| 3 | 3 + 4 (Limits of prior work) | "These studies focused on sub-6~GHz frequencies and isotropic (environmental) exposure \dots" |
| 4 | 4 (Inline gap enumerate) | "Three gaps limit current understanding of far-field \gls{RF}--\gls{EMF} exposure in the 5G/6G era: (1) \dots (2) \dots (3) \dots" |
| 5 | 5 + 6 (This work + novelty disclaimer inline) | "This study addresses these gaps with \gls{FDTD} simulations covering 15 frequencies \dots To the best of the authors' knowledge, this is the first study to perform \dots" |
| 6 | Stakeholder framing | "The results inform regulators by identifying frequency--phantom combinations where compliance margins narrow \dots For public health researchers, including the GOLIAT consortium \dots" |

The PMB version is the most "modular": one beat per paragraph, an inline `(1)(2)(3)` for the gap enumerate, and an explicit stakeholder paragraph after the novelty disclaimer. The 2022 paper smears beats 2 through 6 into a single flowing paragraph; the npj paper sits in the middle.

### 1.2 Length budget

- 2022 IEEE Access: about 35 lines of `.tex`, mostly one giant paragraph plus a 2-item enumerate. Reads as a single breath.
- npj 2026: about 20 lines, but split across 5 paragraphs and a 4-item enumerate. Roughly 1.5 typeset pages.
- PMB 2026: about 40 lines, 5 body paragraphs plus a stakeholder paragraph; immediately precedes the omnibus simulation parameters table that spans both columns. Roughly 1.5 to 2 typeset pages.

All three are short by paper-introduction standards (1.5 to 2 pages, not 3+). The author is disciplined about not letting the intro bloat.

---

## 2. Meso: paragraph-level moves

The introduction is built from a small inventory of paragraph-shaped moves. Each move has a recognizable shape: a topic-first sentence, an internal arc, and a tell at the end.

### 2.1 The "technology-context" paragraph (beat 1)

**Job**: park the reader inside the cellular generation, list the frequency bands, name the enabling technologies (MaMIMO, DMaMIMO, CF-MaMIMO, mmWave).

**Shape**:
1. Open with a noun phrase about demand or deployment, anchored to a number (5G/6G, "2~billion subscribers", "more than 100 countries").
2. Cite a "general 5G" reference within the first two sentences.
3. List the three frequency ranges (FR1, FR2, FR3) with their bandwidths, parenthesized: `FR1 (450~MHz--6~GHz), FR2 (24--52.6~GHz), FR3 (7--15~GHz)`.
4. Define `\gls{MaMIMO}` and `\gls{DMaMIMO}` (and possibly `\gls{CF-MaMIMO}`) with their distinguishing property.
5. End with a forward-link sentence justifying why DMaMIMO and mmWave are studied together, or why auto-induced and environmental exposure both matter.

**Tell**: every example uses the cadence "ever-increasing demand" / "demand \dots is continuously increasing" / "deployment \dots increased significantly". The opening verb is always intransitive ("address", "increase", "feature", "deploy"). The author never opens with "Recently" or "In recent years".

### 2.2 The "exposure-framing" paragraph (beat 2)

**Job**: pivot from RF engineering to public health and regulatory framing.

**Shape**:
1. Pivot sentence: "A portion of the population is concerned \dots" / "The assessment of human exposure \dots is of great importance \dots" / "Children's developing tissues may respond differently \dots".
2. Cite ICNIRP within the first two sentences. Always use the abbreviation, never "International Commission on Non-Ionizing Radiation Protection" by itself.
3. Introduce the "realistic vs. worst-case" framing in italics: "\textit{worst-case}" or "\textit{realistic}".
4. Mention that the 2020 ICNIRP guidelines introduced absorbed power density above 6~GHz.
5. Optionally end with a forward-link sentence stating the thesis: "Therefore, this work comprehensively studies hot-spots \dots".

**Tell**: this paragraph always carries the word "realistic" at least once, often italicized. The author distances themselves from worst-case literature here, not in Methods or Results. Worst-case is treated as a foil, not an opponent.

### 2.3 The "state-of-the-art" paragraph(s) (beat 3)

This beat is sometimes one paragraph, sometimes two or three. Each SoTA paragraph covers a different strand: hybrid simulation methods, prior dosimetry studies, photogrammetry, channel modeling, etc.

**Shape (per paragraph)**:
1. Topic-first sentence naming the strand: "Hybrid \gls{RT}/\gls{FDTD} is an example of an integrated method \dots" / "Computational dosimetry quantifies \dots".
2. One or two sentences citing concrete prior work, with the actual contribution in two or three words: "The method was used to study hot-spots at 3.5~GHz \cite{hotspots\_art}." / "\citet{uusitupa2010sar} extended this to 15 voxel models \dots".
3. A "however" sentence that names the limitation in measurement-grade terms (a number, a frequency, a phantom set).
4. Optional closing sentence linking to the next strand or the gap.

**npj-specific move**: each SoTA paragraph ends with a "Hence, there is a need to \dots" closer that builds toward the novelty enumerate.

**PMB-specific move**: SoTA paragraph cites authors by surname via `\citet{}` (natbib makes this natural). The author rarely names authors in body text in npj or IEEE Access; PMB is the exception. The shape is "\citet{X} did Y." sentence after sentence, three or four in a row, building a chronology.

### 2.4 The "gap" paragraph or sentence cluster (beat 4)

**Two surface forms**:

**A. Inline `(1)(2)(3)` enumerate** (PMB):
```
Three gaps limit current understanding of far-field \gls{RF}--\gls{EMF} exposure in the 5G/6G era:
(1)~No single study spans the full spectral range \dots
(2)~Child exposure remains under-characterized at higher frequencies \dots
(3)~Auto-induced exposure \dots has not been systematically evaluated \dots
```
Each gap is one full sentence, anchored to a specific scope (frequency band, phantom group, scenario type).

**B. Embedded "however" clauses** (npj, older paper): the gap is mentioned in passing inside the SoTA paragraph, then expanded into a "Hence, there is a need to rethink \dots" sentence. Less structured but works when the gap is one-dimensional.

**Tell**: a gap statement always names the missing axis concretely. "No study has evaluated \gls{APD} in realistic whole-body phantoms across the 6G upper mid-band (7--15~GHz) \dots" not "Few studies have addressed \dots".

### 2.5 The "this work" paragraph (beat 5)

**Job**: state what we did, scoped to numbers.

**Shape**:
1. "This study addresses these gaps with \dots" / "Therefore, this work comprehensively studies \dots" / "The objective of this study is to \dots".
2. Scope sentence with the headline counts: "15 frequencies (450~MHz--26~GHz), four \gls{ViP} phantoms (two adults, two children), and two exposure scenarios".
3. Standards or metrics: "We compute psSAR$_{10\mathrm{g}}$, whole-body \gls{SAR}, and organ-specific \gls{SAR} following the IEC/IEEE~62704-1 standard \dots".
4. The disclaimer-and-first claim: "To the best of the authors' knowledge, this is the first study to \dots".

**Tell**: this paragraph is where the "first" / "novel" framing crystallizes, even when there's also an `enumerate` for it. The phrase "To the best (of the) knowledge of the authors" always appears here or in the immediately following enumerate intro. The disclaimer is non-optional.

### 2.6 The "novelty enumerate" (beat 6)

**Two surface forms**:

**A. `enumerate` environment after the disclaimer** (npj, older):
```
To the best knowledge of the authors, this work is novel in the following ways:
\begin{enumerate}
    \item The first end-to-end method for exposure assessment at \glspl{mmWave} \dots
    \item Premier application of high-accuracy high-coverage photogrammetry \dots
    \item Comparison of collocated and cell-free \gls{MaMIMO} in both user and non-user scenarios at 28~GHz.
    \item Characterization of realistic hot-spots at 28~GHz in realistic 3D environments \dots
\end{enumerate}
```

**B. Inline "first to" sentence** (PMB):
```
To the best of the authors' knowledge, this is the first study to perform whole-body dosimetry at 26~GHz in child phantoms and to characterize child \gls{APD} across the 7--15~GHz band.
```

The 2022 paper does both: a 2-item enumerate plus a free-standing "We also provide the first comparison \dots" sentence after the enumerate.

**Item shape (form A)**: each enumerate item is a noun phrase, not a full sentence. It starts with "The first \dots" or a noun ("Comparison of \dots", "Characterization of \dots"). It ends with the scope-pinning detail (a frequency, a technology, a metric).

**Override**: the npj item 1 contains "are leveraged efficiently" — this is the exact verb the author dislikes. For new drafts, use "are combined" / "are coupled" / "are exploited" instead. Watch for "leverage" specifically inside the enumerate, where AI-assisted drafting tends to insert it.

### 2.7 The "stakeholder framing" paragraph (PMB only, beat 7)

PMB closes its introduction with a paragraph addressing readers by role:

```
The results inform regulators by identifying frequency--phantom combinations where compliance margins narrow (e.g., 7~GHz auto-induced exposure in child phantoms).
For public health researchers, including the GOLIAT consortium \citep{goliat2023}, the organ-specific \gls{SAR} data \dots
```

This paragraph is a PMB-specific move driven by the journal's regulatory-policy audience. npj and IEEE Access don't have it. Whether to import it into a new draft depends entirely on the venue. For a methods-heavy IEEE journal: skip. For a public-health journal or a paper aimed at WRC-27 / regulators: keep.

---

## 3. Micro: sentence, word, glyph

### 3.1 The drop-cap opener

Every introduction opens with a drop-cap macro:
- npj 2026: `\IEEEPARstart{T}{he}` (IEEEtran).
- PMB 2026: no drop-cap, opens with normal "With the deployment \dots" (iopjournal class doesn't use one).
- 2022 IEEE Access: `\PARstart{T}{he}` (older IEEE Access class).

**Practical**: use `\IEEEPARstart{}{}` or the equivalent if the class supports it. Otherwise just open with the topic sentence.

### 3.2 Acronym density and `\gls` discipline

The introduction is the densest acronym territory in the paper. First-use auto-expansion via `\gls{}` does the typing for you. Counts in the npj introduction alone: `\gls{5G}`, `\gls{6G}`, `\gls{MaMIMO}`, `\gls{DMaMIMO}`, `\gls{CF-MaMIMO}`, `\gls{BS}`, `\gls{UE}`, `\gls{AP}`, `\gls{RS}`, `\gls{ICNIRP}`, `\gls{EMF}`, `\gls{LOS}`, `\gls{NLOS}`, `\gls{MRT}`, `\gls{SNR}`, `\gls{RT}`, `\gls{FDTD}`, `\gls{QuaDRiGa}`, `\gls{LSF}`, `\gls{LoD}`, `\gls{SOTA}`, `\gls{S\_inc}`, `\gls{S\_ab}` — 23 acronyms in the first paragraph alone.

**Override**: in the abstract no `\gls`. In the body intro, rely on `\gls`'s default first-use auto-expansion. In captions, use the manual short form, never the spelled-out.

### 3.3 Italic-defined terms

Every freshly named concept is italicized at first body use:
- `\textit{beamforming}`, `\textit{Distributed MaMIMO}`, `\textit{cell-free}`, `\textit{unfavorable propagation conditions}`, `\textit{pilot contamination}`, `\textit{mm-Wave}`, `\textit{What is next?}` (older paper).
- `\textit{worst-case}`, `\textit{realistic}`, `\textit{propagation step}`, `\textit{exposure step}` (npj).
- `\emph{auto-induced}`, `\emph{environmental}`, `\emph{brain group}`, `\emph{eyes group}` (PMB; PMB prefers `\emph{}` over `\textit{}` here).

The italic is a typographic claim that the term will be used as-is later. If you italicize a term and don't use it in Methods or Results, drop the italics and just say it plainly.

### 3.4 Numeric anchoring inside the introduction

Every example introduction packs numbers into the very first paragraph, not just into Results:

- npj: "order of magnitude increases", "26-28~GHz", "6~GHz", "93\%", "28~GHz", "12~dB", "20~dB".
- PMB: "2~billion subscribers", "100 countries", "2030", "450~MHz--6~GHz", "24--52.6~GHz", "7--15~GHz", "10~MHz to 3~GHz", "10~MHz to 5.6~GHz", "45\%", "100~GHz", "26~GHz", "550 simulations", "15 frequencies", "12 directions".
- 2022: "5G", "6G", "FR1", "FR2", "3.5 GHz", "28 GHz".

**Practical**: there should be at least one number with units in the first three sentences, and the gap statement should name a specific frequency or scope.

### 3.5 Inline gap enumerate

The PMB-style inline `(1)(2)(3)` is set with non-breaking ties:

```
(1)~No single study spans the full spectral range from sub-GHz cellular bands through the 6G upper mid-band and into millimeter wave (26~GHz) \dots
(2)~Child exposure remains under-characterized at higher frequencies \dots
(3)~Auto-induced exposure \dots has not been systematically evaluated against \gls{ICNIRP} 2020 basic restrictions \dots
```

The tilde after each number is non-optional. Each item is one sentence. Items end with a period; the introductory sentence ends with a colon.

### 3.6 Citation patterns specific to the introduction

The introduction has the highest citation density of any section:

- **npj / IEEE Access (numeric)**: clusters of `\cite{a, b}` and `\cite{a}~\cite{b}` (the second form is mostly older paper habit; new drafts should prefer `\cite{a, b}`). Examples: `\cite{worry5G}~\cite{worry5G2}` (older form) vs. `\cite{Ngo2015, Ngo2017}` (newer form).
- **PMB (author-year)**: `\citet{author2024key}` to name authors as subjects of sentences ("\citet{dimbylow2002fdtd} established \dots"); `\citep{key}` for parenthetical attribution at sentence end.

**Practical**: in numeric venues, name authors only when essential. In author-year venues, the SoTA paragraph naturally names a chronology of authors.

### 3.7 The novelty-disclaimer phrase

The phrase has slight cross-paper drift:
- 2022 IEEE Access: "to the best knowledge of the authors" (no "of the").
- npj 2026: "To the best knowledge of the authors, this work is novel in the following ways:".
- PMB 2026: "To the best of the authors' knowledge, this is the first study to \dots".

The PMB form ("To the best of the authors' knowledge") is the most idiomatic American English. Use that for new drafts unless the venue prefers the npj form.

### 3.8 Closing sentence shape

The intro ends in one of three shapes:

- **`enumerate` close**: the enumerate is the last thing before `\section{Methods}`. No trailing sentence. (npj, 2022 paper sort of: it has a single trailing claim "We also provide the first comparison \dots")
- **Inline "first to" sentence + scope sentence + (optional) stakeholder paragraph**: PMB form.
- **Forward-pointing thesis sentence**: "Therefore, this work comprehensively studies hot-spots in realistic environments at 28~GHz." (npj uses this at the end of paragraph 2, before the methods-framing paragraphs.)

The final sentence of the introduction never starts a new topic. It either lists the last contribution, or names the stakeholder, or anchors the scope number ("550 simulations enable comparisons \dots").

### 3.9 Punctuation tells specific to the introduction

- Em dashes are still absent. No `---` in any of the three intros.
- En dashes appear only in numeric ranges: `1.5--1.9`, `7--15~GHz`, `450~MHz--26~GHz`.
- `e.g.,` and `i.e.,` always with the trailing comma.
- The paragraph break inside one display block uses `\\` followed by a blank line in the older paper (line 48 ends with `\\\n` before the blank). New drafts should use a real `\par` or just two blank lines.

---

## 4. Recurring opening sentences

The first sentence of a Wydaeghe introduction is highly stereotyped. From the three example papers:

- "The \gls{5G} and \gls{6G} generation of cellular networks address the ever-increasing demands in internet connectivity \cite{general5G}." (npj)
- "The demand for more performant wireless networks is continuously increasing." (2022)
- "With the deployment of 5G wireless technology, the number of base stations and antennas per base station has increased significantly compared to 4G \citep{gsma2024wrc}." (PMB)

**Pattern**:
1. Subject is a noun phrase about cellular technology or demand.
2. Verb is intransitive and present tense ("address", "increase", "is increasing", "has increased").
3. Cited within the first sentence or two.
4. No temporal hedge ("Recently", "In recent years", "Over the past decade").
5. No first-person ("We", "Our work").
6. No question. (The npj abstract uses a quoted layman question, but the introduction never opens with one.)

If a draft introduction opens with "Recently, \dots" or "In recent years, \dots", that's not voice — that's a leak from a generic AI-assisted opener. Replace with a noun-phrase about demand or deployment.

---

## 5. Recurring closing moves

The last 10 lines of a Wydaeghe introduction always carry the same payload:

1. The phrase "To the best (of the) knowledge of the authors".
2. A claim of "first" or "novel", pinned to a specific scope.
3. Either an `enumerate` of contributions, or an inline "first to" sentence, or both.
4. (PMB only) a stakeholder paragraph addressing regulators or public-health audiences.

If a draft ends with "Section~2 describes the methods. Section~3 presents the results. Section~4 concludes." — that's not voice either. The author never writes a roadmap paragraph at the end of the intro. Sections speak for themselves; the table of contents is the sectioning, not a sentence.

---

## 6. Tells: phrases that almost guarantee a Wydaeghe introduction

If any of these appear in an introduction, you can guess the author:

1. "**this work is novel in the following ways:**" followed by an `enumerate`.
2. "**To the best (of the) knowledge of the authors, \dots**".
3. "**realistic**" used in opposition to "**worst-case**" within the same paragraph.
4. "**Three gaps limit current understanding \dots: (1) \dots (2) \dots (3) \dots**" inline.
5. "**The first end-to-end method**" / "**the first study to perform**" / "**we present the first**".
6. A drop-cap opener (`\IEEEPARstart` / `\PARstart`) followed by an `\gls{}`-laden first paragraph.
7. **ICNIRP** appearing in paragraph 2, never paragraph 1.
8. **FR1 / FR2 / FR3** listed with parenthesized frequency bands.
9. Italic on `\textit{worst-case}` or `\emph{auto-induced}` at first appearance.
10. The introduction ends within ~1.5 to 2 typeset pages, never 3+.

---

## 7. Anti-patterns to avoid in new introductions

These appeared in the example papers but are flagged as **don't import**:

- **"Leverage" in the novelty enumerate.** The npj item 1 has "leveraged efficiently" — replace with "combined", "exploited", "coupled".
- **Italic paragraph leads inside the introduction.** The npj Methods uses `\textit{Lead-noun:}`-style leads as pseudo-subsubsections; the introduction never does, and new drafts shouldn't either.
- **"Recently" / "In recent years" / "Over the past decade" as the first word.** Not in voice.
- **A roadmap sentence at the end ("This paper is organized as follows \dots").** None of the three examples does this. Don't add one.
- **A numbered novelty enumerate without scope pins.** "We propose a new method" is not enough. Each item must end with a specific frequency, technology, phantom, or metric.
- **Guessing DOIs in `\cite{}` keys when AI-assisted drafting filled them in.** Verify every DOI before submission.
- **British spelling.** "modelling", "behaviour", "characterise". Use American English: "modeling", "behavior", "characterize".

---

## 8. A scaffold for new introductions

For a new paper in this voice, here's a fillable skeleton (sentence-case headings, no em dashes, no roadmap):

```latex
\section{Introduction}
\label{sec:introduction}
\IEEEPARstart{T}{he} <noun-phrase about cellular generation> address <demand>~\cite{<general-ref>}.
<Sentence with frequency-band taxonomy: FR1, FR2, FR3 with parenthesized ranges>~\cite{<bands-ref>}.
<Sentence naming the enabling technology (MaMIMO / DMaMIMO / CF-MaMIMO) with definitional clause>.
<Forward-link sentence justifying why this combination matters>.

<Pivot to public health: "A portion of the population is concerned \dots" or "The assessment of human exposure \dots is of great importance \dots">~\cite{<concern-ref>}.
<ICNIRP framing sentence with 2020 update mention>~\cite{ICNIRP}.
<"realistic vs. worst-case" framing, with at least one italic term>.
<Optional: forward-link thesis sentence "Therefore, this work \dots">.

<SoTA paragraph 1: name a strand, cite 2--3 prior works, name the limit>.
<SoTA paragraph 2 (optional): name a second strand>.

<Gap statement: either inline "Three gaps limit \dots: (1) \dots (2) \dots (3) \dots" or "However, \dots" cluster>.

This study addresses these gaps with <method>, covering <N frequencies (range)>, <M phantoms>, and <K scenarios>.
We compute <metrics> following <standards>~\cite{<standards-ref>}.
To the best of the authors' knowledge, this is the first study to <claim, pinned to scope>.

% Optional novelty enumerate (use this OR the inline form above, not both unnecessarily):
% \begin{enumerate}
%     \item <noun-phrase contribution, scope-pinned>.
%     \item <noun-phrase contribution, scope-pinned>.
%     \item <noun-phrase contribution, scope-pinned>.
% \end{enumerate}

% Optional stakeholder paragraph (only for public-health / regulatory venues):
% The results inform regulators by <specific finding>.
% For <stakeholder group, e.g. GOLIAT consortium>, the <data subset> supports <use case>.
```

Fill in 200 to 600 words per paragraph. Keep the whole introduction under 2 typeset pages. The `enumerate` is the last block before `\section{Methods}` if you use it; otherwise the `To the best of the authors' knowledge \dots` sentence (or the stakeholder paragraph) is.

---

*Generated from a close read of the three Introduction sections in `papers/example_papers/`. Patterns are reported with examples; overrides from `wydaeghe_style_analysis.md` apply transitively.*
