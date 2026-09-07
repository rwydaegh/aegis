# Dries meeting, 25 August 2026

This directory contains the technical discussion deck for the meeting with Dries Vande Ginste.

The deck reflects the 24 August decision with Filip: the present patent and IOF scope remain dosimetry. The meeting is therefore framed as a bounded technical stress test, not as a request to approve a general-purpose EM solver or a broad EDA patent.

## Files

- `main.tex`: 12-slide main deck and 6 technical appendices.
- `main.pdf`: compiled presentation.
- `preamble.tex`: local Beamer design, derived from Robin's established AEGIS presentation language.
- `math_commands.tex`: local notation.
- `speaker_notes.md`: speaking script, likely objections and short responses.
- `figures/`: copied PDF assets from the current Chapter 5 source tree so the deck is portable.
- `_render/slide-01.png` through `_render/slide-18.png`: rendered slides used for visual inspection.
- `_render/contact_1.png` through `_render/contact_3.png`: six-slide review sheets.

## Build

Run from this directory:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

Render every slide for review:

```bash
pdftoppm -png -r 150 main.pdf _render/slide
```

## Intended flow

Slides 1 and 2 reset the mandate before any technical discussion. Slides 3 to 7 define the reduced operator and its coherent form. Slides 8 to 10 show the evidence boundary and the near-body failure question. Slides 11 and 12 convert critique into a benchmark and four precise decisions. The appendices hold equations, asymptotics, validation detail and the adjacent-application filter.

Most slides use step-by-step overlays. The questions slide reveals items one by one. The projected incidence factor and self-occlusion are kept separate throughout.
