# Presentation Structure Concept

## Core idea

Combine **Option 1** (appendix + hyperlink buttons) with **Option 4** (section navigation headline).

The presentation has two distinct modes:
- **Talk mode** — the audience follows a coarse, linear narrative through three parts
- **Detail mode** — the presenter jumps on demand into an indexed appendix

---

## Headline navigation (Option 4)

Three clickable section tabs are always visible in the headline:

```
| Part I: mmWave Framework | Part II: Generalisations | Part III: Coherent MIMO |
```

Clicking a tab jumps immediately to the start of that part's summary slides.
This lets you navigate during Q&A without hunting slide-by-slide.

---

## Structure per part (Option 1)

Each of the three parts follows the same pattern:

```
[Summary slide 1]  ← coarse, 1 key idea
[Summary slide 2]
[Summary slide 3]
  ...as many as needed, no fixed count...
[Detail index slide]  ← the "gateway" to the appendix
```

### The detail index slide

This is the pivotal slide at the end of each part's summary block.
It is **not** a regular content slide — it is a navigation menu.

- Title: something like *"Part I — Details"* or *"Dive deeper"*
- Body: a list of named subsections/results, each as a `\beamergotobutton` hyperlink
- Clicking a link jumps directly to that topic's detail slides in the appendix
- The index makes the appendix **indexable at the granularity of individual results**

Example layout for Part I:

```
Part I: Details

  [Local absorption law]        [Pseudo-Brewster compensation]
  [Geometric framework]         [Whole-body SAR compliance]
  [Computational framework]     [Higher-order corrections]
  [Validation]                  [Applications]
```

---

## Appendix (the detail bank)

All detail slides live after `\appendix`.
They are excluded from the slide count and progress bar.

Each detail block:
- Has a clear title matching the label on the index slide
- Has a `\beamerreturnbutton{Back to Part I}` (or II / III) that returns to the detail index slide of the relevant part — not the start of the part, so you land back at the navigation menu

---

## Full slide order

```
Title slide

── PART I ──────────────────────────────────────────
  Summary slide(s)   (as many as needed)
  Detail index slide  [links → appendix]

── PART II ─────────────────────────────────────────
  Summary slide(s)
  Detail index slide  [links → appendix]

── PART III ────────────────────────────────────────
  Summary slide(s)
  Detail index slide  [links → appendix]

Conclusion

\appendix ──────────────────────────────────────────
  Part I detail slides   (one block per subsection)
  Part II detail slides
  Part III detail slides
```

---

## Source files

- Monograph: `monograph/monograph_v2.tex`
- Summary paper: `monograph/summary_paper.tex`

### Three parts from the monograph

| Headline tab | Monograph sections |
|---|---|
| Part I: mmWave Framework | Local absorption law · Pseudo-Brewster compensation · Geometric framework · Whole-body SAR compliance · Computational framework · Higher-order corrections · Validation · Applications |
| Part II: Generalisations | Polarisation-aware dosimetry · Extension above/below mmWave |
| Part III: Coherent MIMO | Setup · Field channel matrix · Fresnel transmission · Coherent absorption law · Exposure operator · MRT & body absorption · Coherent hotspot formation · Exposure-constrained beamforming · Multi-user MIMO |

---

## Key Beamer commands used

| Purpose | Command |
|---|---|
| Section headline tabs | `\section{}` + custom headline template |
| Jump to detail | `\hyperlink{label}{\beamergotobutton{...}}` |
| Return to index | `\hyperlink{label}{\beamerreturnbutton{Back}}` |
| Label a frame | `\begin{frame}[label=...]` |
| Exclude from count | `\appendix` |
