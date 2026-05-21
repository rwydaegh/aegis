% PREV: \section{Validation and error analysis}\label{sec:val}
We validate the theory four ways: (i) Mie theory on lossy spheres,
(ii) full polarization-aware Fresnel calculations on the Thelonious
phantom, (iii) Sim4Life FDTD on the same phantom, and (iv) the
reverberation-chamber and FDTD literature across $168$ volunteers
and $5$ phantoms. The four checks isolate, respectively, the
Fresnel approximation, realistic anatomy, volumetric FDTD agreement,
and population-level scaling. We then add the higher-order corrections
for curvature, diffraction, and inter-body reflection, and close with a
single error budget that propagates the dielectric uncertainty.

## reviews (paragraph)


_PaperMaker9000 sweep — 2 flag(s) across 4 lens(es)._

- **sentence-craft** — 1 flag(s), 13 cleared:
    - `style.positive_voice.no_passive_no_we` (high): "We validate the theory four ways" → Recast as a noun-verb opener, e.g. "Four checks validate the theory:" and likewise "We then add" -> "Higher-order corrections then follow".
- **voice-tells** — 1 flag(s), 21 cleared:
    - `style.pet_peeves_wout.tilde_spacing` (high): "across $168$ volunteers and $5$ phantoms" → Use non-breaking ties before the numbers: "across~$168$ volunteers and~$5$ phantoms".
- **lexical-spotcheck** — pass (54 rules cleared).
    - _dismissed_ `BOOK_ELOS_style.misused_words.respectively`: Four checks map to four distinct targets; respectively carries the pairing and removing it would force the reader to guess the mapping. respectively_welcome explicitly sanctions this parallel construction.
    - _dismissed_ `style.anti_ai_language.rule_of_three`: Three items is the actual count of higher-order corrections, not a cadenced triplet; the companion list earlier has four items, so the prose is fact-driven, not template-driven.
- **latex-micro** — pass (41 rules cleared).
    - _dismissed_ `latex.spacing_ties.tilde_number_unit`: $168$ and $5$ are bare counts with no attached unit, so the number-unit tie rule does not apply; the universal pre-number tie is Wout's tilde_spacing, handled by the voice-tells lens.

