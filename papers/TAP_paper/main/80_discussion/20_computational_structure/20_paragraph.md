% PREV: The matrix form~\eqref{eq:mat-multi} is a single-hidden-layer
% PREV: rectified-linear `network' whose weights are the path directions and
% PREV: powers from a ray tracer~\cite{SionnaRT}. Three properties follow.
% NEXT: Second, the per-triangle absorbed-power map for $M \approx 10^4$ triangles\footnote{Note
% NEXT: that the number of triangles is arbitrary. As long as the geometric shadow is
% NEXT: kept constant, $\mathrm{SAR}_{\mathrm{wb}}$ results will not change. A correct
% NEXT: validation with FDTD requires similar geometric accuracy of the underlying
% NEXT: mesh.}
% NEXT: and $N \approx 10^2$ paths is one matrix-vector multiply on
% NEXT: a modern GPU, evaluated in under $10$~ms. The cost is independent of
% NEXT: frequency. Against an FDTD reference whose cost scales as $f^4$, the
% NEXT: speed advantage grows by roughly $10^4$ from $6$ to $60$~GHz, exactly
% NEXT: the band where the Fresnel approximation is sharpest and the closed
% NEXT: form holds pointwise within $3\%$ of FDTD (\cref{tab:bands}). The
% NEXT: cosine gate is rectified shading. The visibility matrix $\mathbf{V}$
% NEXT: is ambient occlusion, one of the most optimized computations in
% NEXT: real-time rendering~\cite{AkenineMoller2018}.
First, the network is differentiable in every input. The smooth
\gls{GELU} activation~\eqref{eq:gelu} replaces the hard $[\cdot]_+$
gate, preserving the chain rule. Gradients of
regulatory quantities propagate to antenna positions, antenna
orientations, beam codebooks, and reconfigurable-intelligent-surface
phases through standard backpropagation.
End-to-end exposure assessment in current practice requires a
per-scenario FDTD evaluation on the user phantom as the back-end
step~\cite{Wydaeghe2022access,Wydaeghe2026npj}. With the closed form
replacing that step, exposure-constrained network design becomes a
continuous optimization problem, because of a speed increase and the
availability of gradients on each differentiable computation.

## reviews (paragraph)



_PaperMaker9000 sweep — 1 flag(s) across 4 lens(es)._

- **sentence-craft** — 1 flag(s), 13 cleared:
    - `style.positive_voice.subject_verb_early` (medium): `Replacing the hard $[\cdot]_+$ gate with the smooth \gls{GELU} activation~\eqref{eq:gelu} preserves the chain rule.` -> Front the subject: "The smooth \gls{GELU} activation~\eqref{eq:gelu} replaces the hard $[\cdot]_+$ gate, preserving the chain rule."
- **voice-tells** — pass (22 rules cleared).
    - _dismissed_ `style.anti_ai_language.grand_narrative_framing`: "chain rule" is the standard calculus term, not the banned structural metaphor of "chaining" results together.
    - _dismissed_ `style.pet_peeves_wout.standalone_no_companion_cites`: Both keys are published works with real DOIs (IEEE Access 2022, npj Wireless Technol. 2026) cited as prior FDTD practice, not unpublished sister papers.
- **lexical-spotcheck** — pass (54 rules cleared).
    - _dismissed_ `style.anti_ai_language.first_second_third_overuse`: "First" appears once in this leaf and opens a genuine multi-sentence enumeration continued as Second/Third in separate paragraphs, not a padded triplet within one paragraph.
    - _dismissed_ `style.prose_structure.no_cross_ref_unpublished`: Both cited works are published with real DOIs, so the paper still stands alone.
- **latex-micro** — pass (41 rules cleared).
    - _dismissed_ `latex.structure_style.acronym_first_use`: GELU is introduced via the \gls{} glossary macro, which handles spelled-out first-use expansion automatically.
    - _dismissed_ `latex.math.subscript_labels_upright`: The + subscript is the standard positive-part operator notation, not an italic label subscript needing \mathrm{}.
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).
