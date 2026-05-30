# Paper JSAC handoff report

Compiled: `paper_jsac.pdf`, 11 pages, IEEEtran journal twocolumn,
no undefined refs, single 1.5 pt overfull (cosmetic).

## Top 3 structural choices

1. **Pivoted away from a compliance-aware-precoding paper to a
   regime-characterisation paper.** The plaza data is a null on the
   instantaneous metric (Brussels RL slack by ~10^4, all five precoders
   collapse, pose-information gain is zero). Rather than re-run with
   tighter scenarios to manufacture a Pareto, the paper now lives off
   what was actually measured. The hero figure shows the collapse, the
   chronic-dose ECDF is the practical value, and the conditional
   Cauchy bound is presented honestly (loose by 21-27 dB and breached
   by random/ECBF precoders). Robin's spine doc had this fallback;
   I committed to it.

2. **Single-author voice in sister-paper genre, no cross-paper refs.**
   Plain-noun-phrase title ("Body digital twin in the multi-user
   millimetre-wave precoder loop"), descriptive section names,
   weighted-MMSE drive vector restated rather than imported from
   paper C. Two appendices (Fresnel operator, multi-body ECBF dual
   problem, conditional Cauchy proof) keep the body within page budget
   and self-contained.

3. **Demoted the Cauchy bound to an honest conditional theorem.**
   The cauchy_tightness experiment showed Theorem 2 of paper_v2 was
   not a universal upper bound: top eigenvector misalignment with the
   BS steering vector leaves 21-27 dB slack on the LOS direction, and
   49-70% of random/ECBF precoders breach the unconditional form.
   I moved the theorem to Appendix C as a conditional statement over
   a chosen direction set, and devoted a §V subsection to measuring
   the slack. This is the biggest narrative correction.

## Top 3 figure choices

1. **Hero is wide (figure\*) and shows the null directly.** Two
   panels: (a) ECDF of P_abs/L_RL with the violation zone at x=1 and
   the data clustered at x ≈ 10^-3, (b) sum-rate per precoder showing
   the collapse. ZF singular under K=25 in UMa-LOS is annotated.
2. **Cauchy tightness lives where it lands the punch (§V-H).** The
   honest framing places the bound's failure mode next to the rank
   evidence, not buried in an appendix.
3. **Tiered chronic-dose ECDF carries the practical value.** Three
   curves, one per tier, log-x energy axis. Tier B (cooperating) at
   2.5× lower than tier A (served). This is what the paper actually
   sells.

## Intentionally rough

- **Single seed, 20 s window, Shannon proxy.** Stated as a discussion
  limitation, not patched in time. Multi-seed averaging would smooth
  the bystander tail; full Sionna NR PHY would shift absolute sum-rate
  numbers but not the collapse.
- **Cauchy bound proof in Appendix C.** Appeals to angular-spectrum
  decomposition without re-deriving the projected-area identity. The
  identity is classical (Cauchy 1841) and worth taking as given here.
- **Brussels averaging window** is cited as 6 min per current
  practice; the 2024 ordinance reference is a placeholder citation
  pending exact ordinance number.

## Figures stolen verbatim from `JSAC/code/experiments/`

`rank_cdf.pdf`, `tightness.pdf`, `residual_vs_snr.pdf`,
`detection_vs_range.pdf`, `hero_pareto.pdf`, `chronic_dose.pdf`,
`pose_info_gain.pdf`. All resolve via `\graphicspath{}` in the
preamble. No edits required to the figure scripts.

## Compile sequence

```bash
cd papers/drafts
pdflatex -interaction=nonstopmode paper_jsac.tex
bibtex paper_jsac
pdflatex -interaction=nonstopmode paper_jsac.tex
pdflatex -interaction=nonstopmode paper_jsac.tex
```
