% PREV: \subsection{Computational structure}\label{subsec:disc-primitives}
% NEXT: First, the network is differentiable in every input. Replacing the
% NEXT: hard $[\cdot]_+$ gate with the smooth \gls{GELU}
% NEXT: activation~\eqref{eq:gelu} preserves the chain rule. Gradients of
% NEXT: regulatory quantities propagate to antenna positions, antenna
% NEXT: orientations, beam codebooks, and reconfigurable-intelligent-surface
% NEXT: phases through standard backpropagation. End-to-end exposure
% NEXT: assessment in current practice carries a per-scenario FDTD
% NEXT: evaluation on the user phantom as the back-end
% NEXT: step~\cite{Wydaeghe2022access,Wydaeghe2026npj}. With the closed form
% NEXT: replacing that step, exposure-constrained network design becomes a
% NEXT: continuous optimization problem.
The matrix form~\eqref{eq:mat-multi} is a single-hidden-layer
rectified-linear `network' whose weights are the path directions and
powers from a ray tracer~\cite{SionnaRT}. Three properties follow.

## reviews (paragraph)



_PaperMaker9000 sweep — all clear across 4 lens(es)._

- **sentence-craft** — pass (14 rules cleared).
- **voice-tells** — pass (22 rules cleared).
    - _dismissed_ `style.anti_ai_language.mic_drop_stinger_sentences`: Short closing sentence, but it forward-points to the enumeration that follows rather than restating the preceding sentence, so it is a legitimate setup cue, not an op-ed stinger.
    - _dismissed_ `style.pet_peeves_wout.hackneyed_nouns`: "form" and "properties" are precise mathematical referents here (the matrix form of the law, its mathematical properties), not empty filler nouns.
- **lexical-spotcheck** — pass (54 rules cleared).
    - _dismissed_ `style.prose_structure.staccato_sentences`: A short single-claim sentence is exactly what this rule prefers; it sets up the enumeration cleanly and reads well in IEEE prose.
    - _dismissed_ `style.anti_ai_language.rule_of_three`: Not a cadenced adjective triplet; "three" is the literal count of properties enumerated in the following leaves, so the number is factual, not decorative.
- **latex-micro** — pass (41 rules cleared).
    - _dismissed_ `latex.structure_style.first_coinage_italics`: The scare-quotes mark "network" as a deliberate informal analogy, not a defined term the paper reuses by that name; \emph here would falsely signal a reusable coinage, so quotes are the better choice.
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

