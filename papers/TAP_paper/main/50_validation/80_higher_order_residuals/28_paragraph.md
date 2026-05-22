% PREV: \begin{table}[!t]
% PREV: \centering
% PREV: \caption{Curvature correction at $28$~GHz ($k \approx 587$~m$^{-1}$).
% PREV: The correction is below the Fresnel approximation error for most
% PREV: body regions and concentrates at small features.}
% PREV: \label{tab:curv-mag}
% PREV: \begin{tabular}{lccc}
% PREV: \toprule
% PREV: Region & $R$\,[mm] & $1/(kR)$ & Correction \\
% PREV: \midrule
% PREV: Torso, head & $> 100$ & $< 0.2\%$ & negligible \\
% PREV: Arm         & approx.\ $40$ & $0.4\%$ & approx.\ $0.4\%$ \\
% PREV: Finger      & approx.\ $8$  & $2.1\%$ & approx.\ $2\%$ \\
% PREV: Ear edge    & approx.\ $2$  & $8.5\%$ & approx.\ $8\%$ \\
% PREV: \bottomrule
% PREV: \end{tabular}
% PREV: \end{table}
% NEXT: Second, we quantify the effect of diffraction at the shadow boundary.
% NEXT: The sharp $[\cdot]_+$ cutoff at $\mu = 0$ is a geometric-optics
% NEXT: idealization. Diffraction smooths the shadow edge over a Fresnel-zone
% NEXT: width $\sqrt{\lambda R_j}$. The physical activation becomes
% NEXT: \begin{equation}\label{eq:gelu}
% NEXT:   \mu \mapsto \mu\;\tfrac{1}{2}\!\left[1 + \mathrm{erf}(\mu/\sigma_j)\right],
% NEXT:   \qquad \sigma_j = \sqrt{\lambda / (2\pi R_j)}\, .
% NEXT: \end{equation}
% NEXT: The \gls{ICNIRP} centimeter-scale spatial
% NEXT: averaging regularizes the boundary at a length scale larger
% NEXT: than $\sigma_j$ across the wireless band, so the diffraction
% NEXT: correction is significant only for high-resolution local maps or
% NEXT: for comparisons against point measurements. The integrated effect on
% NEXT: whole-body absorbed power on the Thelonious phantom is $1.2\%$ at
% NEXT: $28$~GHz, below $1\%$ above $30$~GHz, and several percent below
% NEXT: $6$~GHz, in line with the Mie analysis on body-scale spheres in
% NEXT: \cref{subsec:val-mie}. Numerical values across $1$--$100$~GHz on
% NEXT: the Thelonious phantom are in Table~\ref{tab:si-diffraction} of the SI.
The correction grows as the wavelength approaches the local
body-part size. At sub-$6$~GHz frequencies, the smallest features
have $kR \lesssim 5$ where the correction is no longer small. At
$28$~GHz, only the ear edges and fingertips carry a correction
above the Fresnel error floor.

## reviews (paragraph)



_PaperMaker9000 sweep — 1 flag(s) across 4 lens(es)._

- **sentence-craft** — pass (14 rules cleared).
- **voice-tells** — pass (22 rules cleared).
- **lexical-spotcheck** — 1 flag(s), 53 cleared:
    - `BOOK_WILLIAMS_style.prose_structure.comma_after_long_intro` (unknown): `At sub-$6$~GHz frequencies the smallest features` -> Add a comma after the four-word intro phrase: "At sub-$6$~GHz frequencies, the smallest features..." (matching the comma already present in the parallel "At $28$~GHz," sentence).
    - _dismissed_ `style.positive_voice.positive_form`: "no longer small" precisely conveys a threshold crossing (was small, now is not); a single positive adjective would lose that before/after sense, so the negative form is the clearer choice here.
- **latex-micro** — pass (41 rules cleared).
    - _dismissed_ `latex.substitutions.units_math_mode_consistent`: Number is fully closed in math, then a non-breaking tilde, then the unit in text -- the endorsed "$N$~unit" form (cf. tilde_number_unit positives "100~mW", "5~\text{GHz}"); there is no \, straddling the math/text boundary, so this is not the mixed-mode failure the rule targets. Whether the paper should commit globally to siunitx is a paper-wide call, out of scope for a single leaf.
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

