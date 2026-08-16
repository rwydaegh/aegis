<!-- AUTO_BEGIN: assembled -->
\FloatBarrier
\section{Separate geometric fixed-grid diagnostic}
\label{sec:si-geometric-screening}

% claim: geometric_fixed_grid_diagnostic
A separate diagnostic describes ten urban locations with a deterministic point
design. At each location, the calculation builds a complete 6~m walkable-ground
lattice within 90~m and retains 16 observation points evenly across its
nearest-neighbor ordering. The visible roofline transmitter curve is built from
these same 16 points. Surface properties use geometry-based priors, and the
Duke phantom faces north at every point. The calculation uses the same
first-material transport model with four seeds, 200,000 primary rays per point
and seed, and 4,096 first-diffuse output cells. The fixed-grid design remains
separate from the pedestrian-route calculations and is not combined with the
five-route results.

Across the ten fixed-grid descriptions, the ratio of the largest to smallest
normalized whole-body-SAR quantile is 2.09 for $q_{10}$, 2.10 for $q_{50}$,
and 2.60 for $q_{90}$. The pooled component shares range from 74.2\% to
83.4\% for direct transport, 10.5\% to 20.0\% for order-1 specular transport,
and 4.1\% to 7.4\% for first-diffuse transport.

Each quantile describes exactly 16 fixed observation points. Its reported
conditional Monte Carlo standard error is the sample standard deviation of the
four within-seed 16-point quantiles divided by $\sqrt{4}$. Four seeds do not
establish convergence, and this standard error is not total uncertainty. It
does not include uncertainty from the grid design, body orientation, material
priors, or transmitter-curve design. The values therefore describe only the
declared fixed-grid calculation.

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
<!-- AUTO_END: assembled -->

## Aggregation notes (AI-owned)
