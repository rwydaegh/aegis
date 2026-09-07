% PREV: Second, the per-triangle absorbed-power map for $M \approx 10^4$ triangles\footnote{Note
% PREV: that the number of triangles is arbitrary. As long as the geometric shadow is
% PREV: kept constant, $\mathrm{SAR}_{\mathrm{wb}}$ results will not change. A correct
% PREV: validation with FDTD requires similar geometric accuracy of the underlying
% PREV: mesh.}
% PREV: and $N \approx 10^2$ paths is one matrix-vector multiply on
% PREV: a modern GPU, evaluated in under $10$~ms. The cost is independent of
% PREV: frequency. Against an FDTD reference whose cost scales as $f^4$, the
% PREV: speed advantage grows by roughly $10^4$ from $6$ to $60$~GHz, exactly
% PREV: the band where the Fresnel approximation is sharpest and the closed
% PREV: form holds pointwise within $3\%$ of FDTD (\cref{tab:bands}). The
% PREV: cosine gate is rectified shading. The visibility matrix $\mathbf{V}$
% PREV: is ambient occlusion, one of the most optimized computations in
% PREV: real-time rendering~\cite{AkenineMoller2018}.
% NEXT: We highlight three potential applications. First, dosimetry can be
% NEXT: computed in real time, because each evaluation takes about $10$~ms,
% NEXT: well below the timescale on which the body pose and environment
% NEXT: change, given an accurate digital twin of both. Second, exposure
% NEXT: metrics can be optimized under design constraints, because the method
% NEXT: is differentiable end to end. Third, large-scale dosimetric assessment
% NEXT: across diverse populations is possible and useful at the city scale,
% NEXT: e.g., for epidemiological studies such as the GOLIAT
% NEXT: project~\cite{Goliat}.
Third, the whole-body identity~\eqref{eq:cauchy-exact} factorizes the
body dependence into a single scalar $\Aab = \bar\eta\,A$. For a
given phantom and posture, $\bar\eta$ is computed once, in tens of
milliseconds, and cached. Population studies that previously
required one FDTD solve per body and per direction reduce to one
Fresnel quadrature shared across the population and one occlusion
pass per body.

## reviews (paragraph)



_PaperMaker9000 sweep — all clear across 4 lens(es)._

- **sentence-craft** — pass (14 rules cleared).
    - _dismissed_ `style.positive_voice.no_passive_no_we`: Passive keeps $\bar\eta$ as the topical subject linking to the prior sentence's $\bar\eta\,A$; an active rewrite would have to invent an agent and break old-before-new flow, so the exception applies.
    - _dismissed_ `style.positive_voice.subject_verb_early`: Subject is at word 1; the relative clause delaying the verb carries the essential old-state contrast, and front-loading the verb would break the previously/reduce parallel that drives the sentence.
- **voice-tells** — pass (22 rules cleared).
- **lexical-spotcheck** — pass (54 rules cleared).
    - _dismissed_ `style.anti_ai_language.first_second_third_overuse`: A single ordinal opening this paragraph; the rule targets repeated First/Second/Third cadence within one paragraph, and the enumeration here is spread one item per sibling paragraph, not a listicle inside this leaf.
    - _dismissed_ `style.misused_words.which_that`: Restrictive clause defining which studies, so 'that' with no comma is correct.
- **latex-micro** — pass (41 rules cleared).
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

