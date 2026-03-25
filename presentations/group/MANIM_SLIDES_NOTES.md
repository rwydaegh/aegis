# Manim-slides: what I learned

Notes from setting up manim-slides 5.5.4 (by Jerome Eertmans) for the AEGIS group presentation.

## Installation

Needs system-level deps before pip install:
```bash
sudo apt install pkg-config libcairo2-dev libpango1.0-dev ffmpeg texlive-latex-extra texlive-fonts-extra
pip install "manim-slides[manim]"
```

The `[manim]` extra bundles Manim Community Edition. For the Qt presenter GUI, add `[pyside6-full]`.

## Core concept

Two-step workflow:
1. **Author** slides in Python. Use `Slide` as base class instead of `Scene`. Call `self.next_slide()` where you want a click-to-advance pause.
2. **Render** with `manim-slides render`, then **present** with `manim-slides present` or **export** to HTML/PDF/PPTX.

## Key API

```python
from manim import *
from manim_slides import Slide

class MyTalk(Slide):
    def construct(self):
        # Everything from manim works
        text = Text("Hello")
        self.play(FadeIn(text))
        self.next_slide()  # <-- pause here

        # next_slide() options:
        self.next_slide(loop=True)   # loop until click
        self.next_slide(notes="Speaker notes in Markdown")
        self.next_slide(auto_next=True)  # auto-advance
```

### Canvas (persistent objects across slides)
```python
self.add_to_canvas(header=header_mobject)  # survives wipe/zoom
self.remove_from_canvas("header")
```

### Built-in transitions
```python
self.wipe(old, new, direction=LEFT)  # slide out/in
self.zoom(old, new)                  # zoom transition
```

## Rendering

```bash
# Low quality (fast, for testing)
manim-slides render --CE -- -ql slides.py GroupTalk

# High quality (1080p, for presenting)
manim-slides render --CE -- -qh slides.py GroupTalk

# Note: the `--CE --` is needed to pass args to manim
# Without it, -qh is eaten by manim-slides itself
```

Output goes to `slides/files/GroupTalk/` (numbered mp4 segments) and `slides/GroupTalk.json` (config).

## Gotcha: --format png breaks manim-slides

Do NOT use `--format png` with `manim-slides render`. It causes a `ValueError` in the slide merger because manim-slides expects video files, not frame images. Use the default video format.

## Viewing frames as PNG (for verification without a display)

Since we cannot watch mp4 files, export to PDF and then split:

```bash
manim-slides convert --to=pdf GroupTalk talk.pdf
pdftoppm talk.pdf preview/slide -png -r 200
```

This gives one PNG per slide (the last frame of each animation segment). For the first frame instead: add `-cframe_index=first`.

## Export formats

```bash
# Self-contained HTML (RevealJS, works offline)
manim-slides convert GroupTalk talk.html --one-file --offline

# PDF (static, one image per slide)
manim-slides convert --to=pdf GroupTalk talk.pdf

# PowerPoint
manim-slides convert --to=pptx GroupTalk talk.pptx
```

## White background

Manim defaults to a dark background. For academic presentations, set white:
```python
self.camera.background_color = WHITE
```

Then use dark text colors (BLACK, NAVY, etc.) for everything.

## LaTeX in manim

`MathTex` renders LaTeX natively. The full LaTeX distribution must be installed. Use the same notation as the monograph:

```python
eq = MathTex(r"S_{\mathrm{ab}}(\mathbf{r}) = S_{\mathrm{inc}} \cdot T_0 \cdot \mathrm{ReLU}[\hat{\mathbf{n}} \cdot (-\hat{\mathbf{k}})]")
```

## Slide count

Each `self.next_slide()` creates one "click point". A 14-slide presentation with animations between click points produced 33 slide segments (each animation between two next_slide() calls is a segment).

## File structure

```
presentations/group/
  slides.py          # main presentation source
  slides/             # rendered slide data (auto-generated)
  media/              # manim media cache (auto-generated)
  preview_hq/         # exported PNG frames
  talk.html           # standalone HTML presentation
  talk_hq.pdf         # static PDF backup
  PLAN.md             # slide-by-slide plan
```
