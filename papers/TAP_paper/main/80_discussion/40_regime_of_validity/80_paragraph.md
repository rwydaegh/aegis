% PREV: The pseudo-Brewster compensation softens above $200$--$250$~GHz,
% PREV: where the Azzam high-index criterion $|\ntilde| > 2.5$ weakens and
% PREV: worst-case angular variation grows from $5.6\%$ at $28$~GHz to
% PREV: approximately $10\%$ at $250$~GHz and $15\%$ at $300$~GHz, comparable
% PREV: to the dielectric uncertainty on $T_0$ (\cref{fig:err-budget}). Skin
% PREV: refractive-index modulus from the IT'IS database~\cite{ITISv5,Gabriel1996} is $4.84$ at $28$~GHz,
% PREV: $3.68$ at $60$~GHz, and $3.01$ at $100$~GHz, and extrapolation puts
% PREV: $|\ntilde|$ near $2.5$ around $200$--$250$~GHz, approximately $2.2$
% PREV: at $300$~GHz, and $1.8$--$2$ at $1$~THz.
% NEXT: For sources in the reactive near field ($d < \lambda/(2\pi)$, that is
% NEXT: $1.7$~mm at $28$~GHz), evanescent waves and antenna-body impedance
% NEXT: coupling require full-wave simulation. Outside this regime, the law
% NEXT: applies pointwise with spatially varying inputs.
Skin roughness sets an upper limit near $1$~THz, where the Rayleigh
criterion $h\cos\theta/\lambda < 1/8$ is violated on
papillary-ridge-scale features and diffuse scattering becomes the
dominant correction. Skin features are stratified into
stratum-corneum microtexture at $10$--$100\,\mu$m, papillary ridges
at $0.4$--$0.5$~mm spacing, and gross body curvature at centimeters.
Wavelength is $3$~mm at $100$~GHz, $1$~mm at $300$~GHz, $0.3$~mm at
$1$~THz. The Rayleigh criterion is met at $100$~GHz on ridge-scale
features and is marginal at $300$~GHz.

## reviews (paragraph)



_PaperMaker9000 sweep — 1 flag(s) across 4 lens(es)._

- **sentence-craft** — 1 flag(s), 13 cleared:
    - `style.positive_voice.no_passive_no_we` (high): `Skin features are stratified into` -> Use the active verb: "Skin features stratify into ..." (keeps the subject fronted, no awkwardness).
- **voice-tells** — pass (22 rules cleared).
- **lexical-spotcheck** — pass (54 rules cleared).
- **latex-micro** — pass (41 rules cleared).
    - _dismissed_ `latex.substitutions.units_math_mode_consistent`: The number-then-tie-then-text-unit pattern ($num$~mm/GHz/THz, with \,\mu inside math only for the prefix symbol) is the paper-wide convention and matches the PREV/NEXT neighbours; it is internally consistent, so forcing all units into \mathrm{} would be a global change, not a leaf-level fix.
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

