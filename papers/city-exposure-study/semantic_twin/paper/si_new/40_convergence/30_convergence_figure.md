% PREV: The route medians are stable at 16 replicas under the retained estimator.
% PREV: Mexico City standpoints 0, 1, and 3 and Tokyo Hachiko standpoints 13, 14, and 15
% PREV: have zero direct and zero order-1 all-specular transport. The first-diffuse
% PREV: estimate is their only nonzero modeled contribution. These six points form the long
% PREV: lower tails and have greater relative uncertainty than the central route
% PREV: results. The finite-replica bootstrap resamples complete replicas jointly over
% PREV: all standpoints, so it preserves spatial dependence within one replica. Its
% PREV: 2,000 draws use NumPy PCG64 with a seed derived from the sealed calculation
% PREV: manifest. Reported route quantiles use NumPy's linear interpolation rule.
% PREV: Pointwise linear standard errors are the sample standard deviation divided by
% PREV: the square root of the replica count. Their decibel values use the delta-method
% PREV: factor $10/[\ln(10)\,\bar{x}]$.
% PREV: The intervals are conditional on the fixed registered route. They do not include
% PREV: route-selection or city-sampling uncertainty. The study therefore claims
% PREV: stability of the central fixed-route statistics and does not claim convergence
% PREV: of every lower-tail standpoint.
\begin{figure*}[!t]
  \centering
  \includegraphics[width=\textwidth]{figures/convergence/convergence.pdf}
  \caption{Replica convergence for the five fixed routes. Panel (a) shows changes in
  the route median between nested replica looks. Panel (b) shows that the lower-tail
  changes in Mexico City and Tokyo Hachiko remain larger than the route-median
  changes. The calculation therefore supports central route statistics but not full
  pointwise lower-tail convergence.}
  \label{fig:si-convergence}
\end{figure*}

## Reviews

_(empty)_
