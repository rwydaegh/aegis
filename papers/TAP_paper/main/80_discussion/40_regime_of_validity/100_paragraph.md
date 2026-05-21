% PREV: For sources in the reactive near field ($d < \lambda/(2\pi)$, that is
The dielectric properties of biological tissue have been measured to
within approximately $20\%$ at mmWave~\cite{AlekseevZiskin2007}. This
input uncertainty produces $\pm 7\%$ on $T_0$ through the sublinear
propagation derived in \cref{subsec:corr-summary}, and it dominates
the error budget at every operating regime where the surface law
applies.

## reviews (paragraph)


_PaperMaker9000 sweep — 1 flag(s) across 4 lens(es)._

- **sentence-craft** — 1 flag(s), 13 cleared:
    - `style.positive_voice.no_passive_no_we` (high): "The dielectric properties of biological tissue have been measured to within approximately $20\%$ at mmWave" → Rewrite active: "Measurements place the dielectric properties of biological tissue within approximately $20\%$ at mmWave".
- **voice-tells** — pass (22 rules cleared).
    - _dismissed_ `style.anti_ai_language.anthropomorphism_standards_algorithms`: "dominates" describes the literal fact that the input-uncertainty term contributes the largest share of the error budget; it is standard technical usage, not intent ascribed to a standards body, field, or algorithm.
- **lexical-spotcheck** — pass (54 rules cleared).
    - _dismissed_ `style.positive_voice.passive_agent_unknown`: agent (the experimenters) is irrelevant to the reader and the measured-tolerance claim, so the passive is the correct choice here.
- **latex-micro** — pass (41 rules cleared).
    - _dismissed_ `latex.substitutions.approx_text_vs_math`: the prose hedge is the spelled-out word "approximately", not the \approx symbol; $20\%$ is a percentage value legitimately set in math mode, so the rule (which targets $\approx N\%$) does not apply.
    - _dismissed_ `latex.substitutions.cref_capitalized`: the reference is mid-sentence and renders lowercase "section" correctly; \Cref is only required at sentence start or where a capital prefix should render.
    - _dismissed_ `latex.math.subscript_labels_upright`: the subscript 0 is a numeric index, and digits render upright in math mode by default, so no \mathrm{} wrapping is needed.

