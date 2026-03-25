# Group presentation plan (15 min + 5 min Q&A)

## Narrative arc

"Tissue physics conspires to make dosimetry pure geometry, and that geometry is fast enough to do in real time."

## Slide plan

| # | Title | Time | Type | Purpose |
|---|-------|------|------|---------|
| 0 | Title | 15s | LaTeX | Frame the topic |
| 1 | The problem | 45s | LaTeX | FDTD intractability |
| 2 | Key equation (first pass) | 30s | LaTeX | Plant the equation |
| 3 | Pseudo-Brewster (HERO 1) | 90s | Manim | Central physics insight |
| 4 | Geometric absorption law | 30s | LaTeX | Land the simplification |
| 5 | Dosimetry is geometry (HERO 2) | 90s | Manim | Shadow = absorption |
| 6 | ReLU network | 45s | LaTeX | Computation + differentiability |
| 7 | Validation | 45s | LaTeX | Credibility (one slide, two numbers) |
| 8 | Demo title + LIVE DEMO | 130s | Live | Proof it works, real time |
| 9 | Incoherent to coherent | 45s | LaTeX | Bridge to Part III |
| 10 | Coherent hotspot (HERO 3) | 75s | Manim | N^2 risk, exposure operator Q |
| 11 | Exposure-constrained BF | 60s | LaTeX | Payoff: closed-form precoder |
| 12 | Summary | 45s | LaTeX | Three beats: physics, speed, application |
| 13 | Thank you | 10s | LaTeX | Q&A card |

Total: ~12:35 content + ~2:25 buffer = 15:00

## Hero animations

1. **Pseudo-Brewster** (slide 3): T_s and T_p curves animate, average stays flat, collapses to T_0
2. **Dosimetry is geometry** (slide 5): 3D body illumination, ReLU gate, shadow area, Cauchy
3. **Coherent hotspot** (slide 10): Phasor alignment, N^2 scaling, exposure operator

## Style

- Cold dry academic. Let facts speak.
- No buzzwords, no em dashes, no semicolons.
- Dark background for manim, light for LaTeX-style slides.
- Same math notation as monograph.
