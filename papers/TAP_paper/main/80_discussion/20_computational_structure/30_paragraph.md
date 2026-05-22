% PREV: First, the network is differentiable in every input. Replacing the
% PREV: hard $[\cdot]_+$ gate with the smooth \gls{GELU}
% PREV: activation~\eqref{eq:gelu} preserves the chain rule. Gradients of
% PREV: regulatory quantities propagate to antenna positions, antenna
% PREV: orientations, beam codebooks, and reconfigurable-intelligent-surface
% PREV: phases through standard backpropagation. End-to-end exposure
% PREV: assessment in current practice carries a per-scenario FDTD
% PREV: evaluation on the user phantom as the back-end
% PREV: step~\cite{Wydaeghe2022access,Wydaeghe2026npj}. With the closed form
% PREV: replacing that step, exposure-constrained network design becomes a
% PREV: continuous optimization problem.
% NEXT: Third, the whole-body identity~\eqref{eq:cauchy-exact} factorizes the
% NEXT: body dependence into a single scalar $\Aab = \bar\eta\,A$. For a
% NEXT: given phantom and posture, $\bar\eta$ is computed once, in tens of
% NEXT: milliseconds, and cached. Population studies that previously
% NEXT: required one FDTD solve per body and per direction reduce to one
% NEXT: Fresnel quadrature shared across the population and one occlusion
% NEXT: pass per body.
Second, the per-triangle absorbed-power map for $M \approx 10^4$
triangles and $N \approx 10^2$ paths is one matrix-vector multiply on
a modern GPU, evaluated in under $10$~ms. The cost is independent of
frequency. Against an FDTD reference whose cost scales as $f^4$, the
speed advantage grows by roughly $10^4$ from $6$ to $60$~GHz, exactly
the band where the Fresnel approximation is sharpest and the closed
form holds pointwise within $3\%$ of FDTD (\cref{tab:bands}). The
cosine gate is rectified shading. The visibility matrix $\mathbf{V}$
is ambient occlusion, one of the most optimized computations in
real-time rendering~\cite{AkenineMoller2018}.

## reviews (paragraph)



_PaperMaker9000 sweep — all clear across 4 lens(es)._

- **sentence-craft** — pass (14 rules cleared).
- **voice-tells** — pass (22 rules cleared).
    - _dismissed_ `style.anti_ai_language.mic_drop_stinger_sentences`: Short sentence, but it states a new identification (cosine gate = rectified shading), not a restatement of the preceding longer sentence, so it is not a stinger.
- **lexical-spotcheck** — pass (54 rules cleared).
    - _dismissed_ `style.anti_ai_language.first_second_third_overuse`: Only one ordinal appears in this leaf; the rule allows a single use for genuinely enumerated distinct contributions, and the cadence spans separate paragraphs, not one.
    - _dismissed_ `style.misused_words.which_that`: Uses restrictive 'whose' correctly with no comma; no which/that misuse present.
- **latex-micro** — pass (41 rules cleared).
    - _dismissed_ `latex.substitutions.cref_capitalized`: Reference sits inside a trailing parenthetical, not at sentence start or as a mid-sentence reference word, so lowercase \cref rendering '(table 5)' is the standard cleveref form here.
    - _dismissed_ `latex.math.thin_space_units`: Number is in math mode, unit follows in text after a non-breaking tilde; this number-in-math plus tilde-unit pattern is internally consistent and not a missing-separator violation.
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

