% PREV: The Mie test bounds the Fresnel error on a smooth shape. This
% PREV: section validates the theory on a realistic human body. We compare the simplified
% PREV: prediction $\APD^{\mathrm{simp}} = \IPD\,T_0 \pospart{\mu}$ against
% PREV: the full polarization-aware Fresnel integration $\APD^{\mathrm{full}}
% PREV: = \IPD\,\Teff(\theta, \mathrm{pol}) \pospart{\mu}$ on the Thelonious
% PREV: mesh ($23\,826$ triangles, $0.787\,\mathrm{m}^2$ surface area). The
% PREV: incident plane wave comes from above, with skin properties at
% PREV: $28$~GHz.
% NEXT: \Cref{tab:phantom} reports the pointwise comparison. For the
% NEXT: $4\,907$ illuminated triangles with
% NEXT: $\theta < 75^\circ$, the local statistics are mean error $-2.6\%$,
% NEXT: root-mean-square $3.2\%$, and range $[-5.3\%, 0.0\%]$. The peak
% NEXT: $\APD$ is recovered exactly because the maximum is at normal incidence,
% NEXT: where $\Teff(0) = T_0$ regardless of polarization. The local error is
% NEXT: below $5.5\%$ everywhere with $\theta < 75^\circ$.
% NEXT: Section~\ref{si:apd-direction} of the SI extends the analysis to
% NEXT: $128$ illumination directions and three polarization states. The
% NEXT: per-direction distribution of total absorbed power clusters around
% NEXT: $T_0\,\Aperp$ within the directional spread set by self-shadowing.
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

## reviews (table)



_PaperMaker9000 sweep — all clear across 1 lens(es)._

- **table** — pass (10 rules cleared).

## grinder notes
- **label**: tab:phantom
- **caption_preview**: Geometric law versus full Fresnel integration on the Thelonious phantom (skin at $28$~GHz, plane wav
