% PREV: \begin{figure*}[!t]
% NEXT: \begin{table*}[!t]
\Cref{tab:waterfall} lists the numerical comparisons. Bamba
\textit{et~al.}~\cite{Bamba2014}'s $\eta$ in panel (c) is fit from full-body FDTD on
ellipsoidal phantoms in diffuse-field exposure. Their fit absorbs
creeping-wave and finite-curvature contributions that the
planar-tissue $\Tbar$ omits. Its convergence to $\Tbar$ at
$5.8$~GHz, the upper edge of their calibration range, is the
convergence to the geometric-optics regime predicted by a Mie
analysis of body-scale spheres~\cite{BohrenHuffman1983}. The
$1.45$--$3$~GHz portion of their fit lies outside the
geometric-optics validity window of the present framework
(\cref{tab:bands}). The systematic divergence in panel (c) below
$3$~GHz is the body-Mie regime, not a model failure. Bamba
\textit{et~al.}'s anatomical-phantom validation at $3$~GHz returns
residuals of $-39.4\%$, $-11.7\%$, $+10.7\%$, and $+10.6\%$ on the
Thelonious, Billie, Ella, and Duke phantoms~\cite[Table~7]{Bamba2014}.
The largest divergence is on the smallest phantom. The same
mechanism appears in panel (d) on the Diao \textit{et~al.}~\cite{Diao2024}
TARO sweep (frontal plane wave, vertical polarization, projected area
$0.54$~m$^2$), where $T_{\mathrm{eff}}$ rises from $0.43$ at $10$~GHz
to $0.88$ at $1$~GHz.

## reviews (paragraph)


_PaperMaker9000 sweep — 2 flag(s) across 4 lens(es)._

- **sentence-craft** — 2 flag(s), 12 cleared:
    - `style.positive_voice.subject_verb_early` (medium): "Its convergence to $\Tbar$ at $5.8$~GHz, the upper edge of their calibration range, is the convergence to the geometric-optics regime" → Lift the verb forward, e.g. "At $5.8$~GHz, the upper edge of their calibration range, $\eta$ converges to $\Tbar$ ...", so the verb lands within the first 7-9 words.
    - `style.prose_structure.action_in_verb` (high): "Its convergence to $\Tbar$ at $5.8$~GHz ... is the convergence to the geometric-optics regime" → Replace the copula-plus-nominalization (and doubled "convergence") with a verb: "$\eta$ converges to $\Tbar$ ... into the geometric-optics regime ...".
    - _dismissed_ `style.positive_voice.no_passive_no_we`: The passive keeps $\eta$ (the panel-(c) quantity) as the topic subject, preserving old-before-new flow; the active "Bamba et al. fit" would shift focus to the authors.
- **voice-tells** — pass (22 rules cleared).
    - _dismissed_ `style.anti_ai_language.mic_drop_stinger_sentences`: Under five words but it states a new factual correlation (divergence scales with phantom size), not a restatement of the preceding residual list, so it is a content sentence, not a punchline stinger.
    - _dismissed_ `style.pet_peeves_wout.first_time_framing`: This is a mid-paper validation paragraph, not the end of the introduction; first-time framing is mandated only at the contribution list and would be out of place here.
- **lexical-spotcheck** — pass (54 rules cleared).
    - _dismissed_ `style.anti_ai_language.false_ranges`: Both endpoints are real numerical values on a continuous transmission-coefficient scale across a frequency sweep, so 'from X to Y' is the literal correct usage, not a false pseudo-range.
    - _dismissed_ `style.prose_structure.no_interjectional_subsentences`: This is a terminal parenthetical qualifying 'TARO sweep', not a mid-clause aside splitting a subject from its verb, so it is permitted.
    - _dismissed_ `style.prose_structure.no_contractions`: The 's is a possessive genitive on 'et al.' and on 'Bamba', not a contraction of 'is'/'has'; no expansion applies.
- **latex-micro** — pass (41 rules cleared).
    - _dismissed_ `latex.substitutions.cref_capitalized`: Lowercase \cref is correct here: the reference is a bare parenthetical pointer mid-sentence, the standard cleveref convention for which is the lowercase 'table' form; the sentence-initial reference correctly uses \Cref.
    - _dismissed_ `latex.structure_style.acronym_first_use`: This is a mid-paper validation leaf; FDTD and TARO are defined on first use in earlier sections, so this is not their first appearance in the body and no inline definition is needed here.
    - _dismissed_ `latex.spacing_ties.thin_space_math_units`: The number-tilde-unit pattern ($5.8$~GHz, $0.54$~m$^2$) is the document's consistent house style for quantities, not a stray text/math mix; it is applied uniformly throughout the leaf.

