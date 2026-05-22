% PREV: Second, we quantify the effect of diffraction at the shadow boundary.
% PREV: The sharp $[\cdot]_+$ cutoff at $\mu = 0$ is a geometric-optics
% PREV: idealization. Diffraction smooths the shadow edge over a Fresnel-zone
% PREV: width $\sqrt{\lambda R_j}$. The physical activation becomes
% PREV: \begin{equation}\label{eq:gelu}
% PREV:   \mu \mapsto \mu\;\tfrac{1}{2}\!\left[1 + \mathrm{erf}(\mu/\sigma_j)\right],
% PREV:   \qquad \sigma_j = \sqrt{\lambda / (2\pi R_j)}\, .
% PREV: \end{equation}
% PREV: The \gls{ICNIRP} centimeter-scale spatial
% PREV: averaging regularizes the boundary at a length scale larger
% PREV: than $\sigma_j$ across the wireless band, so the diffraction
% PREV: correction is significant only for high-resolution local maps or
% PREV: for comparisons against point measurements. The integrated effect on
% PREV: whole-body absorbed power on the Thelonious phantom is $1.2\%$ at
% PREV: $28$~GHz, below $1\%$ above $30$~GHz, and several percent below
% PREV: $6$~GHz, in line with the Mie analysis on body-scale spheres in
% PREV: \cref{subsec:val-mie}. Numerical values across $1$--$100$~GHz on
% PREV: the Thelonious phantom are in Table~\ref{tab:si-diffraction} of the SI.
% NEXT: Two effects keep the body-averaged correction small. First, the bound
% NEXT: $f \le 1 - \eta$ self-compensates: deep concavities ($\eta$ low) have
% NEXT: a high recapture fraction ($f$ high), so the product $\eta\cdot C$
% NEXT: varies much less than $\eta$ alone. Second, specular reflection at
% NEXT: mmWave (skin meets the Rayleigh roughness criterion) reduces $f$ by
% NEXT: roughly a factor of three relative to the diffuse bound. On the
% NEXT: Thelonious phantom at $28$~GHz, the area-weighted recapture fraction is
% NEXT: $f_{\mathrm{global}} \approx 0.09$ under the diffuse bound, giving
% NEXT: $C \approx 1.04$. The specular estimate brings this to
% NEXT: $C \approx 1.01$. The body-averaged correction stays below $2\%$,
% NEXT: smaller than the propagated dielectric uncertainty derived in
% NEXT: \cref{subsec:corr-summary}. The convex-hull energy bound
% NEXT: $\langle P_{\mathrm{abs}}\rangle \le \IPD\,A_{\mathrm{CH}}/4$
% NEXT: brackets the true absorbed power within
% NEXT: $A_{\mathrm{CH}}/A \approx 1.20$ on Thelonious.
Finally, we study the impact of inter-body reflections. At a surface
point the fraction $T_0$ is absorbed and the remaining
$1 - T_0 \approx 0.46$ is reflected. On a nonconvex body, part of
this reflected power re-illuminates another point and contributes
to absorption that the first-bounce law omits. The radiosity series
gives a multiplier $C(\rr) = 1/(1 - \bar{R}\,f(\rr))$ at each point,
where $\bar{R} = 1 - \Tbar \approx 0.46$ is the flux-weighted
reflectance and $f(\rr) \le 1 - \eta(\rr)$ is the recapture fraction
bounded by the local nonvisible hemisphere area. Two effects keep the
body-averaged correction small. First, the bound $f \le 1 - \eta$
self-compensates: deep concavities ($\eta$ low) have a high recapture
fraction ($f$ high), so the product $\eta\cdot C$ varies much less
than $\eta$ alone. Second, specular reflection at mmWave (skin meets
the Rayleigh roughness criterion) reduces $f$ by roughly a factor of
three relative to the diffuse bound. On the Thelonious phantom at
$28$~GHz, the area-weighted recapture fraction is
$f_{\mathrm{global}} \approx 0.09$ under the diffuse bound, giving
$C \approx 1.04$. The specular estimate gives $C \approx 1.01$. The
body-averaged correction stays below $2\%$, smaller than the
propagated dielectric uncertainty derived in
\cref{subsec:corr-summary}. The convex-hull energy bound
$\langle P_{\mathrm{abs}}\rangle \le \IPD\,A_{\mathrm{CH}}/4$ brackets
the true absorbed power within $A_{\mathrm{CH}}/A \approx 1.20$ on
Thelonious.

## reviews (paragraph)



_PaperMaker9000 sweep — all clear across 4 lens(es)._

- **sentence-craft** — pass (14 rules cleared).
    - _dismissed_ `style.positive_voice.no_passive_no_we`: This 'we' is a deliberate enumeration parallel with the prev leaf ('we quantify the effect of diffraction'); rewriting only this leaf would break the First/Second/Finally series and make it different, not better. Remaining passives ('is absorbed', 'is reflected') are natural state descriptions of the physical process.
- **voice-tells** — pass (22 rules cleared).
- **lexical-spotcheck** — pass (54 rules cleared).
- **latex-micro** — pass (41 rules cleared).
    - _dismissed_ `latex.substitutions.approx_text_vs_math`: \approx sits inside a complete relational math expression, not as a bare prose approximation like $\approx N\%$; legitimate math-mode use.
    - _dismissed_ `latex.dashes_quotes.minus_sign_math`: The minus is inside math mode, so it renders as a proper math minus, not a text-mode hyphen.
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

