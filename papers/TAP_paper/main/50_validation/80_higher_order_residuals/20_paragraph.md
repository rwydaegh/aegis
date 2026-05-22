% PREV: The correction box in the flowchart collects the effects left out by
% PREV: the geometric law. We treat them in turn: curvature, diffraction at
% PREV: the shadow boundary, and inter-body reflections. The kernel labels in
% PREV: \cref{fig:val-fdtd} (``Fresnel only,'' ``+ polarization,'' ``+
% PREV: curvature \& diffraction,'' ``Full kernel,'' ``+ occlusion'') switch
% PREV: each correction on against the same FDTD reference.
% NEXT: \begin{table}[!t]
% NEXT: \centering
% NEXT: \caption{Curvature correction at $28$~GHz ($k \approx 587$~m$^{-1}$).
% NEXT: The correction is below the Fresnel approximation error for most
% NEXT: body regions and concentrates at small features.}
% NEXT: \label{tab:curv-mag}
% NEXT: \begin{tabular}{lccc}
% NEXT: \toprule
% NEXT: Region & $R$\,[mm] & $1/(kR)$ & Correction \\
% NEXT: \midrule
% NEXT: Torso, head & $> 100$ & $< 0.2\%$ & negligible \\
% NEXT: Arm         & approx.\ $40$ & $0.4\%$ & approx.\ $0.4\%$ \\
% NEXT: Finger      & approx.\ $8$  & $2.1\%$ & approx.\ $2\%$ \\
% NEXT: Ear edge    & approx.\ $2$  & $8.5\%$ & approx.\ $8\%$ \\
% NEXT: \bottomrule
% NEXT: \end{tabular}
% NEXT: \end{table}
First, consider the influence of curvature. The first-order Physical
Optics correction multiplies the geometric law by
$1 + \mu/(kR_1) + \mu/(kR_2)$ for a surface with twice the local mean
curvature $H = 1/R_1 + 1/R_2$, where $k = 2\pi/\lambda$ is the
free-space wavenumber. Since
$\pospart{\mu}\cdot\mu = \pospart{\mu}^2$, the per-triangle update
separates additively,
\begin{equation}\label{eq:curv-update}
  \APD^{(j)} = T_0 \sum_i S_i\!\left[
  \pospart{\mu_{ji}} + \frac{H_j}{k}\,\pospart{\mu_{ji}}^2 \right]
  V_{ji}\, ,
\end{equation}
adding a quadratic gate on top of the linear one. The magnitude is
set by $1/(kR)$. \Cref{tab:curv-mag} lists the correction at
$28$~GHz on representative body parts. The correction grows as the
wavelength approaches the local body-part size. At sub-$6$~GHz
frequencies, the smallest features have $kR \lesssim 5$ where the
correction is no longer small. At $28$~GHz, only the ear edges and
fingertips carry a correction above the Fresnel error floor.

## reviews (paragraph)



_PaperMaker9000 sweep — 2 flag(s) across 4 lens(es)._

- **sentence-craft** — 2 flag(s), 12 cleared:
    - `style.positive_voice.no_passive_no_we` (high): `First, we examine the influence of curvature.` -> Drop the pronoun: "First, consider the influence of curvature." or "Curvature comes first."
    - `style.positive_voice.subject_verb_early` (medium): `For a surface with twice the local mean curvature $H = 1/R_1 + 1/R_2$, the first-order Physical Optics correction multiplies the geometric law by` -> Front-load subject-verb: "The first-order Physical Optics correction multiplies the geometric law ... for a surface with twice the local mean curvature $H$."
- **voice-tells** — pass (22 rules cleared).
- **lexical-spotcheck** — pass (54 rules cleared).
    - _dismissed_ `style.anti_ai_language.first_second_third_overuse`: A single ordinal opener, not a repeated First/Second/Third cadence; one use is explicitly acceptable.
- **latex-micro** — pass (41 rules cleared).
    - _dismissed_ `latex.substitutions.units_math_mode_consistent`: Number-in-math, unit-in-text with a tie matches the prevailing in-paper convention ($6$~GHz, $5.8$~GHz, $7$--$11$~GHz, $10$~ms) used throughout this validation chapter; changing it would break local consistency, not improve it.
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

