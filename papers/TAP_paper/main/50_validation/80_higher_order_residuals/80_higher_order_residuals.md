% PREV: Two effects keep the body-averaged correction small.
<!-- AUTO_BEGIN: assembled -->
% NEXT: The correction box in the flowchart collects the effects left out by
\subsection{Higher-order corrections}\label{subsec:corr-residuals}

% PREV: \subsection{Higher-order corrections}\label{subsec:corr-residuals}
% NEXT: First, we examine the influence of curvature.
The correction box in the flowchart collects the effects left out by
the geometric law. We treat them in turn: curvature, diffraction at
the shadow boundary, and inter-body reflections. The kernel labels in
\cref{fig:val-fdtd} (``Fresnel only,'' ``+ polarization,'' ``+
curvature \& diffraction,'' ``Full kernel,'' ``+ occlusion'') switch
each correction on against the same FDTD reference.

% PREV: The correction box in the flowchart collects the effects left out by
% NEXT: \begin{table}[!t]
First, we examine the influence of curvature. For a surface with
twice the local mean curvature $H = 1/R_1 +
1/R_2$, the first-order Physical Optics correction multiplies the
geometric law by $1 + \mu/(kR_1) + \mu/(kR_2)$, where
$k = 2\pi/\lambda$ is the free-space wavenumber. Since
$\pospart{\mu}\cdot\mu = \pospart{\mu}^2$, the per-triangle update
separates additively,
\begin{equation}\label{eq:curv-update}
  \APD^{(j)} = T_0 \sum_i S_i\!\left[
  \pospart{\mu_{ji}} + \frac{H_j}{k}\,\pospart{\mu_{ji}}^2 \right]
  V_{ji}\, ,
\end{equation}
adding a quadratic gate on top of the linear one. The magnitude is
set by $1/(kR)$. \Cref{tab:curv-mag} lists the correction at
$28$~GHz on representative body parts.

% PREV: First, we examine the influence of curvature.
% NEXT: The correction grows as the wavelength approaches the local
\begin{table}[!t]
\centering
\caption{Curvature correction at $28$~GHz ($k \approx 587$~m$^{-1}$).
The correction is below the Fresnel approximation error for most
body regions and concentrates at small features.}
\label{tab:curv-mag}
\begin{tabular}{lccc}
\toprule
Region & $R$\,[mm] & $1/(kR)$ & Correction \\
\midrule
Torso, head & $> 100$ & $< 0.2\%$ & negligible \\
Arm         & approx.\ $40$ & $0.4\%$ & approx.\ $0.4\%$ \\
Finger      & approx.\ $8$  & $2.1\%$ & approx.\ $2\%$ \\
Ear edge    & approx.\ $2$  & $8.5\%$ & approx.\ $8\%$ \\
\bottomrule
\end{tabular}
\end{table}

% PREV: \begin{table}[!t]
% NEXT: Second, we quantify the effect of diffraction at the shadow boundary.
The correction grows as the wavelength approaches the local
body-part size. At sub-$6$~GHz frequencies the smallest features
have $kR \lesssim 5$ where the correction is no longer small. At
$28$~GHz, only the ear edges and fingertips carry a correction
above the Fresnel error floor.

% PREV: The correction grows as the wavelength approaches the local
% NEXT: Finally, we study the impact of inter-body reflections.
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
for comparisons against point measurements. The integrated effect on
whole-body absorbed power on the Thelonious phantom is $1.2\%$ at
$28$~GHz, below $1\%$ above $30$~GHz, and several percent below
$6$~GHz, in line with the Mie analysis on body-scale spheres in
\cref{subsec:val-mie}. Numerical values across $1$--$100$~GHz on
the Thelonious phantom are in Table~\ref{tab:si-diffraction} of the SI.

% PREV: Second, we quantify the effect of diffraction at the shadow boundary.
% NEXT: Two effects keep the body-averaged correction small.
Finally, we study the impact of inter-body reflections. At a surface
point the fraction $T_0$ is absorbed and the remaining
$1 - T_0 \approx 0.46$ is reflected. On a nonconvex body, part of
this reflected power re-illuminates another point and contributes
to absorption that the first-bounce law omits. The radiosity series
gives a multiplier $C(\rr) = 1/(1 - \bar{R}\,f(\rr))$ at each point,
where $\bar{R} = 1 - \Tbar \approx 0.46$ is the flux-weighted
reflectance and $f(\rr) \le 1 - \eta(\rr)$ is the recapture fraction
bounded by the local nonvisible hemisphere area.

% PREV: Finally, we study the impact of inter-body reflections.
% NEXT: <!-- AUTO_BEGIN: assembled -->
Two effects keep the body-averaged correction small. First, the bound
$f \le 1 - \eta$ self-compensates: deep concavities ($\eta$ low) have
a high recapture fraction ($f$ high), so the product $\eta\cdot C$
varies much less than $\eta$ alone. Second, specular reflection at
mmWave (skin meets the Rayleigh roughness criterion) reduces $f$ by
roughly a factor of three relative to the diffuse bound. On the
Thelonious phantom at $28$~GHz, the area-weighted recapture fraction is
$f_{\mathrm{global}} \approx 0.09$ under the diffuse bound, giving
$C \approx 1.04$. The specular estimate brings this to
$C \approx 1.01$. The body-averaged correction stays below $2\%$,
smaller than the propagated dielectric uncertainty derived in
\cref{subsec:corr-summary}. The convex-hull energy bound
$\langle P_{\mathrm{abs}}\rangle \le \IPD\,A_{\mathrm{CH}}/4$
brackets the true absorbed power within
$A_{\mathrm{CH}}/A \approx 1.20$ on Thelonious.
<!-- AUTO_END: assembled -->


## Aggregation notes (AI-owned)

