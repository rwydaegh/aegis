% PREV: \section{Replica convergence and lower tails}
% PREV: \label{sec:si-convergence}
% NEXT: The route medians are stable at 16 replicas under the retained estimator.
% NEXT: Mexico City standpoints 0, 1, and 3 and Tokyo Hachiko standpoints 13, 14, and 15
% NEXT: have zero direct and zero order-1 all-specular transport. The first-diffuse
% NEXT: estimate is their only nonzero modeled contribution. These six points form the long
% NEXT: lower tails and have greater relative uncertainty than the central route
% NEXT: results. The finite-replica bootstrap resamples complete replicas jointly over
% NEXT: all standpoints, so it preserves spatial dependence within one replica. Its
% NEXT: 2,000 draws use NumPy PCG64 with a seed derived from the sealed calculation
% NEXT: manifest. Reported route quantiles use NumPy's linear interpolation rule.
% NEXT: Pointwise linear standard errors are the sample standard deviation divided by
% NEXT: the square root of the replica count. Their decibel values use the delta-method
% NEXT: factor $10/[\ln(10)\,\bar{x}]$.
% NEXT: The intervals are conditional on the fixed registered route. They do not include
% NEXT: route-selection or city-sampling uncertainty. The study therefore claims
% NEXT: stability of the central fixed-route statistics and does not claim convergence
% NEXT: of every lower-tail standpoint.
\begin{table}[!t]
  \caption{Finite-replica diagnostics at the retained 16-replica look.}
  \label{tab:si-convergence}
  \centering
  \begin{tabular}{lrr}
    \toprule
    Site & \shortstack{Max. 12-to-16\\change (dB)} & \shortstack{p90 pointwise total-transfer\\s.e. (dB)} \\
    \midrule
    Korenmarkt & 0.0000819 & 0.000258 \\
    Prague & 0.0001559 & 0.000244 \\
    Madrid & 0.0004083 & 0.000344 \\
    Mexico City & 0.043625 & 0.1461 \\
    Tokyo Hachiko & 0.019732 & 0.0310 \\
    \bottomrule
  \end{tabular}
\end{table}

## AI notes

- Exact diagnostics from the authenticated aggregate.
