% PREV: The correction grows as the wavelength approaches the local
% PREV: body-part size. At sub-$6$~GHz frequencies the smallest features
% PREV: have $kR \lesssim 5$ where the correction is no longer small. At
% PREV: $28$~GHz, only the ear edges and fingertips carry a correction
% PREV: above the Fresnel error floor.
% NEXT: Finally, we study the impact of inter-body reflections. At a surface
% NEXT: point the fraction $T_0$ is absorbed and the remaining
% NEXT: $1 - T_0 \approx 0.46$ is reflected. On a nonconvex body, part of
% NEXT: this reflected power re-illuminates another point and contributes
% NEXT: to absorption that the first-bounce law omits. The radiosity series
% NEXT: gives a multiplier $C(\rr) = 1/(1 - \bar{R}\,f(\rr))$ at each point,
% NEXT: where $\bar{R} = 1 - \Tbar \approx 0.46$ is the flux-weighted
% NEXT: reflectance and $f(\rr) \le 1 - \eta(\rr)$ is the recapture fraction
% NEXT: bounded by the local nonvisible hemisphere area.
Second, we quantify the effect of diffraction at the shadow boundary.
The sharp $[\cdot]_+$ cutoff at $\mu = 0$ is a geometric-optics
idealization. Diffraction smooths the shadow edge over a Fresnel-zone
width $\sqrt{\lambda R_j}$. The physical activation becomes
\begin{equation}\label{eq:gelu}
  \mu \mapsto \mu\;\tfrac{1}{2}\!\left[1 + \mathrm{erf}(\mu/\sigma_j)\right],
  \qquad \sigma_j = \sqrt{\lambda / (2\pi R_j)}\, .
\end{equation}
The \gls{ICNIRP} centimeter-scale spatial
averaging regularizes the boundary at a length scale larger
than $\sigma_j$ across the wireless band, so the diffraction
correction is significant only for high-resolution local maps or
for comparisons against point measurements. On the Thelonious phantom, the integrated whole-body effect is
$1.2\%$ at $28$~GHz, below $1\%$ above $30$~GHz, and several percent
below $6$~GHz, in line with the Mie analysis on body-scale spheres in
\cref{subsec:val-mie}. Numerical values across $1$--$100$~GHz on
the Thelonious phantom are in Table~\ref{tab:si-diffraction} of the SI.

## reviews (paragraph)



_PaperMaker9000 sweep — 2 flag(s) across 4 lens(es)._

- **sentence-craft** — 2 flag(s), 12 cleared:
    - `style.positive_voice.no_passive_no_we` (high): `Second, we quantify the effect of diffraction at the shadow boundary.` -> Drop the pronoun: "Second, diffraction at the shadow boundary smooths the sharp cutoff."
    - `style.positive_voice.subject_verb_early` (medium): `The integrated effect on whole-body absorbed power on the Thelonious phantom is $1.2\%$ at $28$~GHz` -> Move the qualifier forward so the verb lands early: "On the Thelonious phantom, the integrated whole-body effect is 1.2% at 28 GHz..."
- **voice-tells** — pass (22 rules cleared).
- **lexical-spotcheck** — pass (54 rules cleared).
- **latex-micro** — pass (41 rules cleared).
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

