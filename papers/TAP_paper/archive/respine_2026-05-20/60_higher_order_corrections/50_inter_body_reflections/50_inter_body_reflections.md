% PREV: Two effects keep the body-averaged correction small.
# Inter-body reflections

<!-- AUTO_BEGIN: assembled -->
% NEXT: At a surface point the fraction $T_0$ is absorbed and the remaining
\subsection{Inter-body reflections}\label{subsec:corr-interbody}

% PREV: \subsection{Inter-body reflections}\label{subsec:corr-interbody}
% NEXT: Two effects keep the body-averaged correction small.
At a surface point the fraction $T_0$ is absorbed and the remaining
$1 - T_0 \approx 0.46$ is reflected. On a nonconvex body, part of
this reflected power re-illuminates another point and contributes
to absorption that the first-bounce law omits. The radiosity series
gives a multiplier $C(\rr) = 1/(1 - \bar{R}\,f(\rr))$ at each point,
where $\bar{R} = 1 - \Tbar \approx 0.46$ is the flux-weighted
reflectance and $f(\rr) \le 1 - \eta(\rr)$ is the recapture fraction
bounded by the local nonvisible hemisphere area.

% PREV: At a surface point the fraction $T_0$ is absorbed and the remaining
% NEXT: # Inter-body reflections
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



## section notes

_(AI-owned notes about this section as a whole)_
