% PREV: \Cref{tab:phantom} reports the pointwise comparison.
# Full Fresnel on the Thelonious phantom

<!-- AUTO_BEGIN: assembled -->
% NEXT: The Mie test bounds the Fresnel error on a smooth shape.
\subsection{Full Fresnel on the Thelonious phantom}\label{subsec:val-fresnel}

% PREV: \subsection{Full Fresnel on the Thelonious phantom}\label{subsec:val-fresnel}
% NEXT: \begin{table}[!t]
The Mie test bounds the Fresnel error on a smooth shape. This
section validates the theory on a realistic human body. We compare the simplified
prediction $\APD^{\mathrm{simp}} = \IPD\,T_0 \pospart{\mu}$ against
the full polarization-aware Fresnel integration $\APD^{\mathrm{full}}
= \IPD\,\Teff(\theta, \mathrm{pol}) \pospart{\mu}$ on the Thelonious
mesh ($23\,826$ triangles, $0.787\,\mathrm{m}^2$ surface area). The
incident plane wave comes from above, with skin properties at
$28$~GHz.

% PREV: The Mie test bounds the Fresnel error on a smooth shape.
% NEXT: \Cref{tab:phantom} reports the pointwise comparison.
\begin{table}[!t]
\centering
\caption{Geometric law versus full Fresnel integration on the
Thelonious phantom (skin at $28$~GHz, plane wave from above).}
\label{tab:phantom}
\begin{tabular}{lccc}
\toprule
Metric & Simplified & Full Fresnel & Error \\
\midrule
Mean $\APD$ (illum.)     & $0.185$~W/m$^2$ & $0.186$~W/m$^2$ & $0.5\%$ \\
Peak $\APD$              & $0.539$~W/m$^2$ & $0.539$~W/m$^2$ & $0.0\%$ \\
\bottomrule
\end{tabular}
\end{table}

% PREV: \begin{table}[!t]
% NEXT: # Full Fresnel on the Thelonious phantom
\Cref{tab:phantom} reports the pointwise comparison. For the
$4\,907$ illuminated triangles with
$\theta < 75^\circ$, the local statistics are mean error $-2.6\%$,
root-mean-square $3.2\%$, and range $[-5.3\%, 0.0\%]$. The peak
$\APD$ is recovered exactly because the maximum is at normal incidence,
where $\Teff(0) = T_0$ regardless of polarization. The local error is
below $5.5\%$ everywhere with $\theta < 75^\circ$.
Section~\ref{si:apd-direction} of the SI extends the analysis to
$128$ illumination directions and three polarization states. The
per-direction distribution of total absorbed power clusters around
$T_0\,\Aperp$ within the directional spread set by self-shadowing.
<!-- AUTO_END: assembled -->





## section notes

_(AI-owned notes about this section as a whole)_
