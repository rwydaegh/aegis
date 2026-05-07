# TAP_paper

Submission package for *Closed-Form Absorbed-Power Dosimetry on the Human Body, 1 to 100 GHz* (IEEE Trans. Antennas Propag.).

## Layout

- `paper.tex` — main manuscript (15 pages, IEEEtran journal class)
- `paper_SI.tex` — supplementary information (10 pages, single-column 11pt)
- `figures/` — every PDF/PNG used by the two LaTeX files
- `authors/` — author photos for the IEEEbiography blocks
- `scripts/` — Python scripts that produced the figures (snapshot at submission time)

## Build

The bibliography lives inline as `thebibliography` with manual `\bibitem` entries; no `.bib` file is needed. Glossary entries (`relu`, `gelu`) expand inline through the `glossaries` package.

```bash
pdflatex paper.tex
pdflatex paper.tex   # second pass for cross-references
pdflatex paper_SI.tex
pdflatex paper_SI.tex
```

## Figure provenance

| Figure                                | Script                                |
| ------------------------------------- | ------------------------------------- |
| `fig_geometry.pdf` (Fig. 1)           | `fig1_geom.tex`, `render_gray_phantom.py` |
| `apd_angle_panel_{T,Sab}.pdf`         | `apd_direction_analysis.py`           |
| `R_of_f.pdf`, `R_of_f_angle_family.pdf` | `R_of_f_landscape.py`               |
| `mie_panel_{size,freq}.pdf`           | `mie_theory_corrected.py`             |
| `sab_phantom_visible.pdf`, `eta_phantom_{front,side}.pdf` | `render_phantom_figs.py`, `visualize_{eta,sab}_3d.py` |
| `apd_direction_panel_{pdf,box}.pdf`   | `apd_direction_analysis.py`           |
| `fig_kernels_vs_fdtd.pdf`             | `plot_tier0.py`                       |
| `lit_waterfall.pdf`                   | `lit_waterfall.py`                    |
| `error_budget_comprehensive.pdf`      | `error_budget_comprehensive.py`       |
| `si_tissue_universality.pdf`          | `si_tissue_universality.py`           |
| `si_tlay_fat_resonance.pdf`           | `si_tlay_fat_resonance.py`            |
| `si_standing_wave_sar.pdf`            | `standing_wave_sar.py`                |

The scripts share `_plot_style.py` (SciencePlots-based IEEE column styling).
