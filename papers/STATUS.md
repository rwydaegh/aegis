# Status of the three-paper effort

**As of 2026-05-04, end of autonomous session.** This document
consolidates everything produced. Subsequent edits should update this
file in place.


## What's been produced

### Three full draft papers

All three are LaTeX sources that compile cleanly with the shared
bibliography. Run `pdflatex paper_X; bibtex paper_X; pdflatex; pdflatex`
to rebuild.

| Paper | Title | Target | Pages (single-col draft) | TeX | PDF |
|---|---|---|---|---|---|
| A | Pseudo-Brewster compensation collapses Fresnel dosimetry to geometry | TAP | 15 | `papers/drafts/paper_A.tex` | `papers/drafts/paper_A.pdf` |
| B | The absorption-cross-section identity | TAP | 11 | `papers/drafts/paper_B.tex` | `papers/drafts/paper_B.pdf` |
| C | A closed-form exposure operator for coherent millimetre-wave | TWC | 17 | `papers/drafts/paper_C.tex` | `papers/drafts/paper_C.pdf` |

Single-column drafts; converting to two-column IEEE will roughly halve
page counts. Total content is approximately 21 IEEE pages of substantive
material, including figures, tables, and theorem-proof structure.

All three drafts are content-complete: introduction, derivations,
validation/results, limitations, conclusion, bibliography wired up. They
are not yet submission-polished.


### Three medium-level plans

Concrete planning documents that were the precursors to the drafts. They
contain section-by-section structure, headline numerical claims, headline
figures, adversarial self-critique, and open decisions. Use these for
revising the drafts; they are richer than the drafts in places where
the drafts had to compress for brevity.

- `papers/drafts/paper_A_spine.md`
- `papers/drafts/paper_B_spine.md`
- `papers/drafts/paper_C_spine.md`


### One findings synthesis

`papers/findings_synthesis.md` consolidates the agent extractions from
the three reference PDFs (Flintoft 2014, Zhang 2017 thesis, Bamba 2014),
the FDTD validation evidence in `validation/`, and the AEGIS coherent
code inventory. It is the source of truth for the positioning claims
made in the drafts.


### Headline figures

#### Paper B figure 6 (the literature waterfall)

`papers/drafts/figures/lit_waterfall.{pdf,png}` — six panels
(Flintoft / Zhang / Bamba / Diao+Kodera / AEGIS-vs-FDTD / unification),
plus a summary version `lit_waterfall_summary.{pdf,png}` showing only
the unification panel. Reproducer at
`papers/drafts/figures/lit_waterfall.py`. README at
`papers/drafts/figures/lit_waterfall_README.md`.

The figure is the visual core of Paper B. It collapses 168 volunteers
across three independent measurement campaigns and two FDTD studies onto
a single closed-form prediction.

#### Paper C figures (canonical scenario at 28 GHz)

In `papers/drafts/figures/paperC/`:

- `ecbf_pareto.{pdf,png}` — ECBF Pareto curve for two UE positions.
  MRT, GEP optimum, ECBF family, random-precoder cloud, incoherent
  baseline.
- `hotspot_pair.{pdf,png}` — body-surface S_ab on Thelonious under MRT
  vs ECBF at 50% SNR target.
- `spectrum.{pdf,png}` — cumulative eigenvalue fraction of Q vs rank
  for four multipath densities.
- `paperC_results.npz` — raw simulation data (Q, h, eigenvalues, paths).
- `paperC_simulate.py` — runner script.

The fourth planned figure (`rho_landscape`) was not produced in the
session. Headline ρ values for the two UE positions are extracted and
quoted in §9.2; the full landscape sweep remains a follow-up.

The fifth planned figure (`approx_error_budget`) was not separately
produced; the combined approximation error is quoted as
≤3% (Frobenius) for the canonical scenario.


### Reference extractions

In `papers/extracted/`:
- `flintoft_summary.md` plus PNG crops of figures and tables
- `zhang_summary.md` plus PNG crops
- `gosselin_summary.md` (folder name is a misnomer; the paper is
  actually Bamba 2014, PMB 59:7435)

These extractions provided the headline numerical claims that the three
drafts cite.


### Shared bibliography

`papers/drafts/refs.bib` with 65 entries. Pulled from the monograph's
existing fact-checked bibliography
(`presentations/promotors/references.bib`, 56 entries) plus 9 additions
for citations needed by the three papers (Boyd-Vandenberghe, Chew,
Christensen, Shi, Tomita, three Wydaeghe self-references, AEGIS
software).


## Headline numerical claims by paper

### Paper A
- Pseudo-Brewster constancy on skin at 28 GHz: T_avg/T_0 within 5.6%
  over [0°, 75°].
- R = 1 sweet spot at 40 GHz; RMS error < 5% across 0.3-100 GHz.
- Phantom validation: total power error 0.35% on Thelonious at 28 GHz.
- FDTD validation: peak 4-cm² SAPD ratio 1.027 at 7 GHz.
- FDTD validation: direction-averaged Cauchy 1.012 at 5.8 GHz.

### Paper B
- Direction-averaged identity ⟨P_abs⟩ = S_inc T̄(f) A_ab / 4, exact
  above 100 MHz.
- Flintoft plateau (γ_s-corrected): 0.47-0.49 vs T_0 = 0.48, within 2%.
- Bamba plateau: η = 0.50-0.56 vs T̄ = 0.47-0.50, within 5-10%.
- Zhang plateau: ξ = 0.45-0.65 vs T̄·A_ab/A = 0.43-0.49, within scatter.
- Diao 28 GHz: T = 0.52 vs T_0 = 0.536, within 3%.
- AEGIS A_ab/A on Thelonious = 0.865, vs Flintoft's 0.75-0.85 estimate.
- Anthropometric S_inc^max varies by 2× from infant to large adult.

### Paper C
- Approximation 1 cross-term error ≤4%, Approximation 2 ≤0.5%, combined
  ≤5%.
- Combined ‖ΔQ‖_F / ‖Q‖_F ≤3% on canonical scenario.
- Effective rank of Q: 5/64 at 90% trace, 8-9/64 at 99%.
- ECBF reduces P_abs by factor 4-5 at 50% MRT signal power.
- λ_max(Q_a) = 3.6e-5, λ_max(Q_b) = 6.4e-4 (factor 17 between UE
  positions).
- ρ_a = 0.53, ρ_b = 0.66.


## What remains before submission

### Style polish (not yet done)
- Convert remaining body semicolons to periods (5-15 left per paper).
- Review for AI-writing tells per `papers/how_to_write_good/style_guide.md`.
- Verify sentence-case headings and no em dashes.
- Replace any remaining `\citep` mixed style with consistent natbib usage.
- Verify all theorem cross-references resolve.

### IEEE conversion
- Move from generic `article` class to IEEEtran with two-column layout.
- Author affiliation block, ORCID, copyright, etc.
- IEEE-style figure caption text.
- Page-budget triage if any paper exceeds the journal's 12 or 14 page
  limit.

### Numerical follow-ups
- **Paper B**: fetch Flintoft supplementary data at
  `stacks.iop.org/PMB/59/3297/mmedia` and replot figure 6 panel (a) with
  per-subject scatter. Add the layered-tissue T_lay(f) overlay on
  panels (a) and (b) for the 3 GHz dip.
- **Paper B**: the anthropometric compliance landscape (figure 5 in the
  spine) was deferred from the rendering task; it would strengthen §5.
- **Paper C**: render the rho landscape figure 5 by sweeping UE
  position over a horizontal grid; same scenario as the rest of §9.
- **Paper C**: render the approximation-error-budget figure as a separate
  panel in §9.6 with per-pair breakdown.

### External validation
- **Paper C**: a direct entry-by-entry comparison of analytical Q against
  an FDTD-calibrated S on a Hochwald-2014-style scenario at 28 GHz is
  open work.

### Author and author-affiliation
- All three papers list the user as sole author at Ghent University and
  imec; if Wout / Carolina / Joe / Luc are co-authors, update author
  blocks before submission.

### CV-grade decisions
- For Paper B, the children-vulnerability discussion in §5.2 is currently
  framed as a quantitative scaling without a regulatory-recommendation
  flag. The user previously indicated this is fine; reaffirm before
  submission.


## Recommended order of next moves

1. **Paper B is closest to camera-ready** — short, validated, with the
   waterfall figure. Polish first.
2. **Paper A is foundational** — needed before Papers B and C can
   reference it. Polish second.
3. **Paper C needs the rho landscape figure** — that's the one
   missing-from-§9 deliverable that the spine called for. Run an agent
   to generate it from the existing `paperC_results.npz`. After
   integration, polish.

Roughly 2-3 days of polish per paper, plus the IEEEtran conversion and
the optional follow-up figures.


## Files modified or created in this session

```
papers/
├── STATUS.md                     (this file)
├── brainstorm.md                 (initial 3-paper brainstorm)
├── findings_synthesis.md         (consolidated agent + validation findings)
├── extracted/
│   ├── flintoft_summary.md       + 10 PNG crops
│   ├── zhang_summary.md          + 14 PNG crops
│   └── gosselin_summary.md       + 6 PNG crops (folder is Bamba 2014)
└── drafts/
    ├── paper_A.tex / .pdf        (15 pages, 1509 KB)
    ├── paper_A_spine.md          (medium-level plan)
    ├── paper_B.tex / .pdf        (11 pages, 558 KB)
    ├── paper_B_spine.md
    ├── paper_C.tex / .pdf        (17 pages, 8873 KB)
    ├── paper_C_spine.md
    ├── refs.bib                  (65 entries)
    └── figures/
        ├── lit_waterfall.{pdf,png}        (Paper B headline)
        ├── lit_waterfall_summary.{pdf,png}
        ├── lit_waterfall_README.md
        ├── lit_waterfall.py
        ├── lit_waterfall_data.csv
        └── paperC/
            ├── ecbf_pareto.{pdf,png}
            ├── hotspot_pair.{pdf,png}
            ├── spectrum.{pdf,png}
            ├── paperC_results.npz
            └── paperC_simulate.py
```
