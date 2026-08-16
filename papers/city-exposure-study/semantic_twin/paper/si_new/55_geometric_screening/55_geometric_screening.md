<!-- AUTO_BEGIN: assembled -->
\FloatBarrier
\section{Separate geometric fixed-grid diagnostic}
\label{sec:si-geometric-screening}

% claim: geometric_fixed_grid_diagnostic
A separate diagnostic describes ten urban locations with a deterministic point
design. At each location, the calculation builds a complete 6~m walkable-ground
lattice within 90~m and retains 64 observation points evenly across its
nearest-neighbor ordering. The visible roofline transmitter curve is built from
these same 64 points. Surface properties use geometry-based priors, and the
Duke phantom faces north at every point. The calculation uses the same
first-material transport model with 16 seeds, 200,000 primary rays per point
and seed, and 4,096 first-diffuse output cells. The fixed-grid design remains
separate from the pedestrian-route calculations and is not combined with the
five-route results.

Across the ten fixed-grid descriptions, the ratio of the largest to smallest
normalized whole-body-SAR quantile is 2.02 for $q_{10}$, 2.01 for $q_{50}$,
and 2.23 for $q_{90}$. The pooled component shares range from 75.2\% to
80.6\% for direct transport, 13.1\% to 19.6\% for order-1 specular transport,
and 4.1\% to 7.1\% for first-diffuse transport.

Changing the design from 16 to 64 points, evaluated with the first four seeds,
moved the site quantiles by at most 2.26~dB for $q_{10}$, 1.38~dB for
$q_{50}$, and 3.47~dB for $q_{90}$. By contrast, the change from eight to
16 seeds moved them by at most 0.0036, 0.0017, and 0.0020~dB. With the
64-point transmitter curve fixed, the change from 32 to 64 receiver points was
as large as 1.36, 0.219, and 0.636~dB. The calculation is therefore far more
sensitive to point selection than to the number of seeds.

Each quantile describes exactly 64 fixed observation points. Its reported
conditional Monte Carlo standard error is the sample standard deviation of the
16 within-seed 64-point quantiles divided by $\sqrt{16}$. This standard error
is not total uncertainty. It does not include uncertainty from the grid design,
body orientation, material
priors, or transmitter-curve design. The values therefore describe only the
declared fixed-grid calculation.

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
<!-- AUTO_END: assembled -->


## Aggregation notes (AI-owned)
