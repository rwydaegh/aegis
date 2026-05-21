% PREV: # Mie theory on lossy spheres
For body-relevant sizes (head, torso) over 6--100~GHz, the error ranges
from $0.4\%$ on a torso at $100$~GHz to $14\%$ on a head at
$28$~GHz, set mostly by diffraction into the geometric shadow at
the low end of the band. At $28$~GHz the law underestimates
absorption.
For fingers below 6~GHz, errors exceed $30\%$. On
body-scale objects in the claimed regime, the residual stays within
the dielectric uncertainty on $T_0$ (\cref{fig:err-budget}).
Per-frequency residuals across four body-part diameters ($17$, $80$,
$180$, $300$~mm) are in Table~\ref{tab:mie-residual} of the SI.

## reviews (paragraph)


_PaperMaker9000 sweep — all clear across 4 lens(es)._

- **sentence-craft** — pass (14 rules cleared).
- **voice-tells** — pass (22 rules cleared).
    - _dismissed_ `style.anti_ai_language.mic_drop_stinger_sentences`: This adds new directional information (sign of the error), not a restatement of the preceding sentence, and it is not paragraph-final; it precedes the fingers and residual-budget sentences.
    - _dismissed_ `style.pet_peeves_wout.tilde_spacing`: The cref is preceded by an open parenthesis, not a plain space; a tilde after '(' is non-idiomatic and would not improve the leaf. Every number and unit in the leaf already carries a tilde.
- **lexical-spotcheck** — pass (54 rules cleared).
    - _dismissed_ `style.anti_ai_language.false_ranges`: Both endpoints are points on a real numerical error scale (0.4% to 14%), so 'from X to Y' is the correct construction, not a false categorical range.
    - _dismissed_ `style.anti_ai_language.filler_adverbs_intensifiers`: 'mostly' quantifies the dominant contribution and is not one of the banned intensifiers (very/highly/notably/significantly); it carries factual meaning.
- **latex-micro** — pass (41 rules cleared).
    - _dismissed_ `latex.substitutions.cref_capitalized`: The cref sits inside parentheses as a bare pointer, not sentence-initial nor a grammatical 'Figure X shows' subject, so lowercase \cref renders correctly here.
    - _dismissed_ `latex.substitutions.units_math_mode_consistent`: The leaf consistently uses number-in-math then text-mode tilde+unit ($100$~GHz, $300$~mm); the number is fully closed before the unit, matching tilde_number_unit, and no mixing occurs within the leaf.

