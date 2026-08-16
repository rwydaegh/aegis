% PREV: Across the ten fixed-grid descriptions, the ratio of the largest to smallest
% PREV: normalized whole-body-SAR quantile is 2.09 for $q_{10}$, 2.10 for $q_{50}$,
% PREV: and 2.60 for $q_{90}$. The pooled component shares range from 74.2\% to
% PREV: 83.4\% for direct transport, 10.5\% to 20.0\% for order-1 specular transport,
% PREV: and 4.1\% to 7.4\% for first-diffuse transport.
% PREV:
% PREV: Each quantile describes exactly 16 fixed observation points. Its reported
% PREV: conditional Monte Carlo standard error is the sample standard deviation of the
% PREV: four within-seed 16-point quantiles divided by $\sqrt{4}$. Four seeds do not
% PREV: establish convergence, and this standard error is not total uncertainty. It
% PREV: does not include uncertainty from the grid design, body orientation, material
% PREV: priors, or transmitter-curve design. The values therefore describe only the
% PREV: declared fixed-grid calculation.
\begin{figure*}[!t]
  \centering
  \includegraphics[width=\textwidth]{figures/geometric_screening/geometric_screening.pdf}
  \caption{Separate geometric fixed-grid diagnostic at ten urban locations.
  Panel (a) shows $q_{10}$, $q_{50}$, and $q_{90}$ across the 16 fixed
  observation points. Red bars give the four-seed conditional Monte Carlo
  standard error of $q_{50}$. Panel (b) shows the pooled additive component
  shares. These results are not combined with the five-route calculation.}
  \label{fig:si-geometric-screening}
\end{figure*}
