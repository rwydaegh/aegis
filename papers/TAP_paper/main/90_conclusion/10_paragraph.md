% PREV: \section{Conclusion}\label{sec:conc}
% NEXT: The cost decouples from frequency. The $f^4$ FDTD scaling collapses
% NEXT: to one matrix-vector multiply with positive-part gating,
% NEXT: differentiable in antenna position, orientation, beam codebooks, and
% NEXT: reconfigurable-intelligent-surface phases. A simulation campaign
% NEXT: that takes weeks of FDTD reduces to a tissue-property lookup and an
% NEXT: ambient-occlusion pass on the body mesh.
A closed-form method is proposed for the absorbed power density on
biological tissue from $1$ to $100$~GHz. The whole-body absorbed
power factors into a flux-weighted Fresnel transmission $\Tbar(f)$
times a body shape factor $\Aab/A$.

## reviews (paragraph)



_PaperMaker9000 sweep — 1 flag(s) across 4 lens(es)._

- **sentence-craft** — 1 flag(s), 13 cleared:
    - `style.positive_voice.no_passive_no_we` (high): `A closed-form method is proposed for the absorbed power density on biological tissue from $1$ to $100$~GHz.` -> Rewrite active: 'A closed-form method gives the absorbed power density on biological tissue from 1 to 100 GHz.'
- **voice-tells** — pass (22 rules cleared).
    - _dismissed_ `style.pet_peeves_wout.hackneyed_nouns`: "factor" here names the dimensionless quantity $\Aab/A$ (a defined technical term), not empty filler; replacing it would lose the referent.
- **lexical-spotcheck** — pass (54 rules cleared).
    - _dismissed_ `BOOK_ELOS_style.misused_words.factor_hackneyed`: "factor" is the literal name of the multiplicative quantity $\Aab/A$, not the "X is a factor in Y" filler construction the rule targets.
    - _dismissed_ `style.anti_ai_language.false_ranges`: 1 GHz and 100 GHz are real endpoints of a numerical frequency scale, the licensed use of "from X to Y".
- **latex-micro** — pass (41 rules cleared).
    - _dismissed_ `latex.math.thin_space_units`: Unit uses the paper-wide text-mode tilde convention ($num$~GHz, 581 occurrences); this rule wants \,\mathrm{} inside math, but the paper has consistently committed to the tilde form, so flagging is merely different, not better.
    - _dismissed_ `latex.spacing_ties.tilde_number_unit`: The tilde is present ($100$~GHz); no plain space between number and unit, so the rule is satisfied.
    - _dismissed_ `latex.substitutions.units_math_mode_consistent`: GHz is consistently set in text mode after a tilde across the whole paper; this is the document's adopted convention, not a stray mode drift.
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

