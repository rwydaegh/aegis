<!-- AUTO_BEGIN: assembled -->
\FloatBarrier
\section{Ten-route production detail}
\label{sec:si-ten-route-detail}

% claim: ten_route_production_detail
The ten selected routes contain 163 observation points. Every route uses
image-derived surface properties, a Duke phantom facing along the walk, 64
independent seeds from 7 through 70, 200,000 primary rays per point and seed,
and 4,096 first-diffuse output cells. Direct, exact order-1 specular, and
first-diffuse transport use the first-material model described in the main text.
The selected routes are fixed case studies, not a population sample or a city
ranking.

The route-median normalized whole-body SAR ranges from
$0.009016\,\mathrm{m^2/kg}$ in Milan to $0.1291\,\mathrm{m^2/kg}$ in
Mexico City per unit $\rho_A P_\mathrm{EIRP}$, a factor of 14.3.
Fig.~\ref{fig:si-ten-route-detail} shows the full route ranges. The low
$q_{10}$ values in Mexico City and Tokyo Hachiko come from the shadowed points
described in Section~\ref{sec:si-convergence}, rather than a shift in the central
route values.

Direct transport accounts for 69.8\% to 89.5\% of route-summed absorbed power.
The order-1 specular share ranges from 9.1\% to 29.9\%, and the first-diffuse
share ranges from 0.301\% to 5.02\%. Between 48 and 64 replicas, the largest
absolute route-quantile changes across the ten routes are 0.00491~dB for
$q_{10}$, 0.000157~dB for $q_{50}$, and 0.0000762~dB for $q_{90}$.
The ten routes contain 10,432 point-replica body fields and
2.0864~billion primary rays.

\begin{figure*}[!t]
  \centering
  \includegraphics[width=0.92\textwidth]{figures/ten_route_extension/ten_route_extension.pdf}
  \caption{Per-route exposure and component detail. Panel (a) shows
  the route $q_{10}$--$q_{90}$ interval and an open marker at $q_{50}$ for
  normalized whole-body SAR. Panel (b) shows the route-summed additive absorbed-power
  shares. All routes use 64 replicas and image-derived surface properties. The
  selected routes do not represent city populations.}
  \label{fig:si-ten-route-detail}
\end{figure*}
<!-- AUTO_END: assembled -->


## Aggregation notes (AI-owned)

Content above is the assembled version. The section provides per-route detail
complementing the main text summary. Label changed from si-ten-route-extension
to si-ten-route-detail to match the rewrite.
