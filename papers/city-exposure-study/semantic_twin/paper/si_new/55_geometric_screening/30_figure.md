% PREV: Across the ten fixed-grid descriptions, the ratio of the largest to smallest
% PREV: normalized whole-body-SAR quantile is 2.02 for $q_{10}$, 2.01 for $q_{50}$,
% PREV: and 2.23 for $q_{90}$. The pooled component shares range from 75.2\% to
% PREV: 80.6\% for direct transport, 13.1\% to 19.6\% for order-1 specular transport,
% PREV: and 4.1\% to 7.1\% for first-diffuse transport.
% PREV:
% PREV: Changing the design from 16 to 64 points, evaluated with the first four seeds,
% PREV: moved the site quantiles by at most 2.26~dB for $q_{10}$, 1.38~dB for
% PREV: $q_{50}$, and 3.47~dB for $q_{90}$. By contrast, the change from eight to
% PREV: 16 seeds moved them by at most 0.0036, 0.0017, and 0.0020~dB. With the
% PREV: 64-point transmitter curve fixed, the change from 32 to 64 receiver points was
% PREV: as large as 1.36, 0.219, and 0.636~dB. The calculation is therefore far more
% PREV: sensitive to point selection than to the number of seeds.
% PREV:
% PREV: Each quantile describes exactly 64 fixed observation points. Its reported
% PREV: conditional Monte Carlo standard error is the sample standard deviation of the
% PREV: 16 within-seed 64-point quantiles divided by $\sqrt{16}$. This standard error
% PREV: is not total uncertainty. It does not include uncertainty from the grid design,
% PREV: body orientation, material
% PREV: priors, or transmitter-curve design. The values therefore describe only the
% PREV: declared fixed-grid calculation.
\begin{figure*}[!t]
  \centering
  \includegraphics[width=\textwidth]{figures/geometric_screening/geometric_screening.pdf}
  \caption{Separate geometric fixed-grid diagnostic at ten urban locations.
  Panel (a) shows $q_{10}$, $q_{50}$, and $q_{90}$ across the 64 fixed
  observation points. Red bars give the 16-seed conditional Monte Carlo
  standard error of $q_{50}$. Panel (b) shows the pooled additive component
  shares. These results are not combined with the five-route calculation.}
  \label{fig:si-geometric-screening}
\end{figure*}
