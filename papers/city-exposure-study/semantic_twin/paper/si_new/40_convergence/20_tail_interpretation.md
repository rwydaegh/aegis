% PREV: \begin{table}[!t]
% PREV:   \caption{Finite-replica diagnostics at the retained 16-replica look.}
% PREV:   \label{tab:si-convergence}
% PREV:   \centering
% PREV:   \begin{tabular}{lrr}
% PREV:     \toprule
% PREV:     Site & \shortstack{Max. 12-to-16\\change (dB)} & \shortstack{p90 pointwise total-transfer\\s.e. (dB)} \\
% PREV:     \midrule
% PREV:     Korenmarkt & 0.0000819 & 0.000258 \\
% PREV:     Prague & 0.0001559 & 0.000244 \\
% PREV:     Madrid & 0.0004083 & 0.000344 \\
% PREV:     Mexico City & 0.043625 & 0.1461 \\
% PREV:     Tokyo Hachiko & 0.019732 & 0.0310 \\
% PREV:     \bottomrule
% PREV:   \end{tabular}
% PREV: \end{table}
% NEXT: \begin{figure*}[!t]
% NEXT:   \centering
% NEXT:   \includegraphics[width=\textwidth]{figures/convergence/convergence.pdf}
% NEXT:   \caption{Replica convergence for the five fixed routes. Panel (a) shows changes in
% NEXT:   the route median between nested replica looks. Panel (b) shows that the lower-tail
% NEXT:   changes in Mexico City and Tokyo Hachiko remain larger than the route-median
% NEXT:   changes. The calculation therefore supports central route statistics but not full
% NEXT:   pointwise lower-tail convergence.}
% NEXT:   \label{fig:si-convergence}
% NEXT: \end{figure*}
The route medians are stable at 16 replicas under the retained estimator.
Mexico City standpoints 0, 1, and 3 and Tokyo Hachiko standpoints 13, 14, and 15
have zero direct and zero order-1 all-specular transport. The first-diffuse
estimate is their only nonzero modeled contribution. These six points form the long
lower tails and have greater relative uncertainty than the central route
results. The finite-replica bootstrap resamples complete replicas jointly over
all standpoints, so it preserves spatial dependence within one replica. Its
2,000 draws use NumPy PCG64 with a seed derived from the sealed calculation
manifest. Reported route quantiles use NumPy's linear interpolation rule.
Pointwise linear standard errors are the sample standard deviation divided by
the square root of the replica count. Their decibel values use the delta-method
factor $10/[\ln(10)\,\bar{x}]$.
The intervals are conditional on the fixed registered route. They do not include
route-selection or city-sampling uncertainty. The study therefore claims
stability of the central fixed-route statistics and does not claim convergence
of every lower-tail standpoint.

## AI notes

- Keeps the lower-tail qualification next to the convergence table.
