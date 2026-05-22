% PREV: \begin{figure*}[!t]
% PREV:   \centering
% PREV:   \includegraphics[width=\linewidth]{lit_waterfall_combined.pdf}
% PREV:   \caption{Closed-form prediction~\eqref{eq:cauchy-exact} compared
% PREV:   with direction-averaged whole-body absorption ratios from the
% PREV:   dosimetry literature. The thick black line uses the
% PREV:   population-averaged layered transmission, the thin black line is the
% PREV:   geometric-optics asymptote $\Tbar(f)\Aab/A$, and the dotted line is
% PREV:   the normal-incidence reference $T_0(f)\Aab/A$. The gray band shows
% PREV:   the layered-transmission envelope for subcutaneous-fat thicknesses
% PREV:   $d_{\mathrm{SF}}\in[2,30]$~mm. Error bars are standard errors of the
% PREV:   mean. The inset gives framework validity by frequency band.}
% PREV:   \label{fig:waterfall}
% PREV: \end{figure*}
% NEXT: \begin{table*}[!t]
% NEXT: \centering
% NEXT: \caption{Quantitative comparison of the closed-form prediction to the
% NEXT: empirical literature. The shaded sub-$3$~GHz regime, where the
% NEXT: layered tissue model in \cref{subsec:fp} replaces $\Tbar$, is
% NEXT: excluded.}
% NEXT: \label{tab:waterfall}
% NEXT: \begin{tabular}{lp{0.36\linewidth}p{0.26\linewidth}p{0.16\linewidth}}
% NEXT: \toprule
% NEXT: Reference & Empirical observation & Closed-form prediction & Match \\
% NEXT: \midrule
% NEXT: Flintoft~\cite{Flintoft2014}
% NEXT: & $\langle Q^a\rangle/\gamma_s = 0.47$--$0.49$ at $7$--$11$~GHz, $60$ volunteers
% NEXT: & $T_0(f) = 0.48$ at $9$~GHz, $\Tbar(f) = 0.50$
% NEXT: & $2\%$--$4\%$ \\
% NEXT: Bamba~\cite{Bamba2014}
% NEXT: & $\eta(f) = 0.48$--$0.56$ at $1.45$--$5.8$~GHz, four FDTD ellipsoids
% NEXT: & $\Tbar(f) = 0.47$--$0.50$
% NEXT: & $3\%$ at $5.8$~GHz; convergent with frequency \\
% NEXT: Zhang~\cite{Zhang2017thesis}
% NEXT: & $\xi = 0.45$--$0.65$ at $6$--$18$~GHz, $48$ subjects
% NEXT: & $\Tbar(f)\cdot\Aab/A = 0.43$--$0.49$
% NEXT: & within scatter \\
% NEXT: Kodera~\cite{Kodera2024}
% NEXT: & $T_{\mathrm{tr}}$ matches $\Aperp$ scaling at $10$--$100$~GHz, parametric FDTD
% NEXT: & $T_{\mathrm{tr}} \equiv T_0$
% NEXT: & $\le 5\%$ \\
% NEXT: Diao~\cite{Diao2024}
% NEXT: & $T = 0.52$ at $28$~GHz, anatomical FDTD
% NEXT: & $T_0 = 0.536$ at $28$~GHz
% NEXT: & $3\%$ \\
% NEXT: Flintoft~\cite{Flintoft2014}
% NEXT: & $-0.0061\,\mathrm{mm}^{-1}$ slope of $\langle Q^a\rangle$ vs $d_{\mathrm{SF}}$ at $3$~GHz
% NEXT: & Layered Fabry--P\'erot in fat
% NEXT: & mechanism, qualitative \\
% NEXT: \bottomrule
% NEXT: \end{tabular}
% NEXT: \end{table*}
\Cref{tab:waterfall} lists the numerical comparisons. Bamba
\textit{et~al.}~\cite{Bamba2014}'s $\eta$ in panel (c) is fit from full-body FDTD on
ellipsoidal phantoms in diffuse-field exposure. Their fit absorbs
creeping-wave and finite-curvature contributions that the
planar-tissue $\Tbar$ omits. At $5.8$~GHz, the upper edge of their calibration range, $\eta$
converges to $\Tbar$ in the geometric-optics regime predicted by a Mie
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
    - `style.positive_voice.subject_verb_early` (medium): `Its convergence to $\Tbar$ at $5.8$~GHz, the upper edge of their calibration range, is the convergence to the geometric-optics regime` -> Lift the verb forward, e.g. "At $5.8$~GHz, the upper edge of their calibration range, $\eta$ converges to $\Tbar$ ...", so the verb lands within the first 7-9 words.
    - `style.prose_structure.action_in_verb` (high): `Its convergence to $\Tbar$ at $5.8$~GHz ... is the convergence to the geometric-optics regime` -> Replace the copula-plus-nominalization (and doubled "convergence") with a verb: "$\eta$ converges to $\Tbar$ ... into the geometric-optics regime ...".
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
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

