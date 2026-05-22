% NEXT: The mechanism is a Fabry--P\'erot resonance in the subcutaneous fat
% NEXT: layer. Below $6$~GHz the SAR penetration depth in fat exceeds
% NEXT: $70$~mm, against fat thicknesses of $2$--$20$~mm in the Flintoft
% NEXT: cohort~\cite[Table~1]{Flintoft2014}. The wave passes through the fat
% NEXT: layer with little attenuation and reflects from the fat-muscle
% NEXT: interface. Constructive interference enhances absorption, and destructive
% NEXT: interference suppresses it. A three-layer transfer-matrix model with
% NEXT: skin, fat, and a semi-infinite muscle half-space gives the layered
% NEXT: transmission
% NEXT: \begin{equation}\label{eq:T-lay}
% NEXT:   \Tlay(f, d_{\mathrm{SF}})
% NEXT:   = 1 - \bigl|\widetilde{\Gamma}_1(f, d_{\mathrm{SF}})\bigr|^2\, ,
% NEXT: \end{equation}
% NEXT: where $\widetilde{\Gamma}_1$ is the generalized Fresnel reflection
% NEXT: coefficient at the air-skin interface, computed recursively from the
% NEXT: fat-muscle interface upward~\cite{Chew1995,BornWolf1999}.
% NEXT: Section~\ref{si:layered} of the SI gives the full Chew recursion,
% NEXT: the standing-wave SAR per layer, and the layer-by-layer cube
% NEXT: integral. Fig.~\ref{fig:si-tlay-fr} of the SI shows $\Tlay(f)$ for
% NEXT: the canonical $2$~mm skin / $10$~mm fat / muscle stack. Replacing
% NEXT: $\Tbar$ with $\Tlay$ in~\eqref{eq:cauchy-exact} gives a
% NEXT: frequency-dependent direction-averaged absorbed power that includes
% NEXT: the fat-layer resonance. For a fat thickness of $10$~mm the model
% NEXT: predicts a $40\%$ enhancement above the homogeneous prediction at
% NEXT: $0.9$~GHz (quarter-wave matching) and a $27\%$ reduction at
% NEXT: $3.5$~GHz (destructive interference).
Above $6$~GHz, \eqref{eq:cauchy-exact} matches the plateau values
reported by Bamba, Flintoft, and Zhang. Below $6$~GHz, Flintoft and
Zhang observe a structured dip near $3$~GHz that the homogeneous
half-space model does not reproduce~\cite{Flintoft2014,Zhang2017thesis}. The
dip is anatomical. Flintoft's negative
correlation of $\langle Q^a\rangle$ with mean subcutaneous fat
thickness $d_{\mathrm{SF}}$ is steepest at $3$~GHz
($-0.0061\,\mathrm{mm}^{-1}$, $R^2 = 0.40$,~\cite[Table~6]{Flintoft2014}),
with the slope falling to $-0.0030\,\mathrm{mm}^{-1}$ at $7$--$11$~GHz.

## reviews (paragraph)



_PaperMaker9000 sweep — 1 flag(s) across 4 lens(es)._

- **sentence-craft** — 1 flag(s), 13 cleared:
    - `style.positive_voice.subject_verb_early` (medium): `Flintoft's negative correlation of $\langle Q^a\rangle$ with mean subcutaneous fat thickness $d_{\mathrm{SF}}$ is steepest at $3$~GHz` -> Front the subject-verb: "$\langle Q^a\rangle$ correlates negatively with mean subcutaneous fat thickness $d_{\mathrm{SF}}$, most steeply at $3$~GHz (...)" so the verb lands within the first 7-9 words.
- **voice-tells** — pass (22 rules cleared).
    - _dismissed_ `style.anti_ai_language.mic_drop_stinger_sentences`: This three-word sentence makes a new causal claim (the cause is anatomy) rather than restating the preceding sentence, and it functions as the topic sentence the following correlation evidence supports; it is not a stinger restatement.
- **lexical-spotcheck** — pass (54 rules cleared).
- **latex-micro** — pass (41 rules cleared).
    - _dismissed_ `latex.spacing_ties.tilde_number_unit`: The lint_hint quote 's fat Above $6$~GHz' is a spurious concatenation across the leaf boundary; the actual text already reads $6$~GHz with a non-breaking tilde before the unit, and the cited tilde_before_refs id is not even a rule in this lens. No missing tie exists.
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

