% PREV: # Computational structure
% NEXT: Second, the per-triangle absorbed-power map for $M \approx 10^4$
First, the network is differentiable in every input. Replacing the
hard $[\cdot]_+$ gate with the smooth \gls{GELU}
activation~\eqref{eq:gelu} preserves the chain rule. Gradients of
regulatory quantities propagate to antenna positions, antenna
orientations, beam codebooks, and reconfigurable-intelligent-surface
phases through standard backpropagation. End-to-end exposure
assessment in current practice carries a per-scenario FDTD
evaluation on the user phantom as the back-end
step~\cite{Wydaeghe2022access,Wydaeghe2026npj}. With the closed form
replacing that step, exposure-constrained network design becomes a
continuous optimization problem.

## reviews (paragraph)


_PaperMaker9000 sweep — 1 flag(s) across 4 lens(es)._

- **sentence-craft** — 1 flag(s), 13 cleared:
    - `style.positive_voice.subject_verb_early` (medium): "Replacing the hard $[\cdot]_+$ gate with the smooth \gls{GELU} activation~\eqref{eq:gelu} preserves the chain rule." → Front the subject: "The smooth \gls{GELU} activation~\eqref{eq:gelu} replaces the hard $[\cdot]_+$ gate, preserving the chain rule."
- **voice-tells** — pass (22 rules cleared).
    - _dismissed_ `style.anti_ai_language.grand_narrative_framing`: "chain rule" is the standard calculus term, not the banned structural metaphor of "chaining" results together.
    - _dismissed_ `style.pet_peeves_wout.standalone_no_companion_cites`: Both keys are published works with real DOIs (IEEE Access 2022, npj Wireless Technol. 2026) cited as prior FDTD practice, not unpublished sister papers.
- **lexical-spotcheck** — pass (54 rules cleared).
    - _dismissed_ `style.anti_ai_language.first_second_third_overuse`: "First" appears once in this leaf and opens a genuine multi-sentence enumeration continued as Second/Third in separate paragraphs, not a padded triplet within one paragraph.
    - _dismissed_ `style.prose_structure.no_cross_ref_unpublished`: Both cited works are published with real DOIs, so the paper still stands alone.
- **latex-micro** — pass (41 rules cleared).
    - _dismissed_ `latex.structure_style.acronym_first_use`: GELU is introduced via the \gls{} glossary macro, which handles spelled-out first-use expansion automatically.
    - _dismissed_ `latex.math.subscript_labels_upright`: The + subscript is the standard positive-part operator notation, not an italic label subscript needing \mathrm{}.

