% PREV: % claim: ten_route_production_extension
% PREV: The route-based extension applies the production contract to five additional
% PREV: prepared scenes and combines them with the original five routes in one
% PREV: authenticated report. The ten selected routes contain 163 observation points.
% PREV: Every route uses image-derived surface properties, a Duke phantom facing along
% PREV: the walk, 64 independent seeds from 7 through 70, 200,000 primary rays per
% PREV: point and seed, and 4,096 first-diffuse output cells. Direct, exact order-1
% PREV: specular, and first-diffuse transport use the same first-material model as the
% PREV: five detailed routes. The extension changes the site and route coverage. It
% PREV: does not turn the selected routes into a population sample or a city ranking.
% NEXT: \begin{figure*}[!t]
% NEXT:   \centering
% NEXT:   \includegraphics[width=0.92\textwidth]{figures/ten_route_extension/ten_route_extension.pdf}
% NEXT:   \caption{Production-contract results for ten selected routes. Panel (a) shows
% NEXT:   the route $q_{10}$--$q_{90}$ interval and an open marker at $q_{50}$ for
% NEXT:   normalized whole-body SAR. Panel (b) shows the route-summed additive absorbed-power
% NEXT:   shares. All routes use 64 replicas and image-derived surface properties. The
% NEXT:   selected routes do not represent city populations.}
% NEXT:   \label{fig:si-ten-route-extension}
% NEXT: \end{figure*}
The route-median normalized whole-body SAR ranges from
$0.009016\,\mathrm{m^2/kg}$ in Milan to $0.1291\,\mathrm{m^2/kg}$ in
Mexico City per unit $\rho_A P_\mathrm{EIRP}$, a factor of 14.3.
Fig.~\ref{fig:si-ten-route-extension} shows the full route ranges. The low
$q_{10}$ values in Mexico City and Tokyo Hachiko come from the shadowed points
described in Section~\ref{sec:si-convergence}, rather than a shift in the central
route values.

Direct transport accounts for 69.8\% to 89.5\% of route-summed absorbed power.
The order-1 specular share ranges from 9.1\% to 29.9\%, and the first-diffuse
share ranges from 0.301\% to 5.02\%. Between 48 and 64 replicas, the largest
absolute route-quantile changes across the ten routes are 0.00491~dB for
$q_{10}$, 0.000157~dB for $q_{50}$, and 0.0000762~dB for $q_{90}$.
The ten-route extension contains 10,432 point-replica body fields and
2.0864~billion primary rays.
