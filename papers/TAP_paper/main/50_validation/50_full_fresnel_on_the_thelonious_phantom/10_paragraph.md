% PREV: \subsection{Full Fresnel on the Thelonious phantom}\label{subsec:val-fresnel}
% NEXT: \begin{table}[!t]
% NEXT: \centering
% NEXT: \caption{Geometric law versus full Fresnel integration on the
% NEXT: Thelonious phantom (skin at $28$~GHz, plane wave from above).}
% NEXT: \label{tab:phantom}
% NEXT: \begin{tabular}{lccc}
% NEXT: \toprule
% NEXT: Metric & Simplified & Full Fresnel & Error \\
% NEXT: \midrule
% NEXT: Mean $\APD$ (illum.)     & $0.185$~W/m$^2$ & $0.186$~W/m$^2$ & $0.5\%$ \\
% NEXT: Peak $\APD$              & $0.539$~W/m$^2$ & $0.539$~W/m$^2$ & $0.0\%$ \\
% NEXT: \bottomrule
% NEXT: \end{tabular}
% NEXT: \end{table}
The Mie test bounds the Fresnel error on a smooth shape. This
section validates the theory on a realistic human body. We compare the simplified
prediction $\APD^{\mathrm{simp}} = \IPD\,T_0 \pospart{\mu}$ against
the full polarization-aware Fresnel integration $\APD^{\mathrm{full}}
= \IPD\,\Teff(\theta, \mathrm{pol}) \pospart{\mu}$ on the Thelonious
mesh ($23\,826$ triangles, $0.787\,\mathrm{m}^2$ surface area). The
incident plane wave comes from above, with skin properties at
$28$~GHz.

## reviews (paragraph)


_PaperMaker9000 sweep — 1 flag(s) across 4 lens(es)._

- **sentence-craft** — 1 flag(s), 13 cleared:
    - `style.positive_voice.no_passive_no_we` (high): "We compare the simplified prediction" → Rewrite third-person: "This section compares the simplified prediction ..."
- **voice-tells** — pass (22 rules cleared).
    - _dismissed_ `style.anti_ai_language.throat_clearing_openings`: Not an empty meta opener: it pivots from the preceding sentence's smooth-shape Mie result to the realistic-body validation, the contrast the whole subsection rests on. The rule explicitly allows a connective transition that buys connection to the preceding sentence; deleting it would drop the smooth-shape-to-body bridge.
- **lexical-spotcheck** — pass (54 rules cleared).
    - _dismissed_ `style.prose_structure.throat_clearing`: A single connective transition, not stacked metadiscourse: it bridges the smooth-shape Mie result to the realistic-body validation. The rule permits a throat-clearing opener that buys connection to the preceding sentence.
- **latex-micro** — pass (41 rules cleared).
    - _dismissed_ `latex.substitutions.units_math_mode_consistent`: Number closed in math, unit set in text mode with a non-breaking tilde. This is the paper-wide simple-unit convention (28~GHz, 1~W/m$^2$ throughout); the rule's negative is a unit drifting out of math after a \, (e.g. $0.08\,$ W/kg), which does not occur here. The exponented-unit quantity $0.787\,\mathrm{m}^2$ correctly uses \,\mathrm{} matching the paper's mm$^{-1}$/cm$^2$ practice.
    - _dismissed_ `latex.spacing_ties.siunitx_consistency`: The paper adopts no siunitx in the body; all units use manual \,\mathrm{} (exponented) or text-mode ~unit (simple). The rule only bites once siunitx is adopted, so manual formatting here is consistent with the document's chosen convention.

