<!-- AUTO_BEGIN: assembled -->
\section{Replica convergence and lower tails}
\label{sec:si-convergence}

% claim: replica_convergence_48_to_64
\begin{table}[!t]
  \caption{Convergence from 48 to 64 replicas. Bootstrap width is the 95\% interval width for route $q_{10}$ whole-body SAR. Shadow change is the largest stepwise change among the six shadowed route points in Mexico City and Tokyo Hachiko.}
  \label{tab:si-convergence}
  \centering
  \begin{tabular}{lrrr}
    \toprule
    Site & \shortstack{$q_{10}$ change\\(dB)} & \shortstack{Bootstrap width\\(dB)} & \shortstack{Shadow change\\(dB)} \\
    \midrule
    Brussels & 0.000114 & 0.000592 & -- \\
    Ghent & 0.0000723 & 0.000221 & -- \\
    Krakow & 0.000130 & 0.00107 & -- \\
    London & 0.0000427 & 0.000671 & -- \\
    Madrid & 0.00000615 & 0.000374 & -- \\
    Mexico City & 0.00344 & 0.355 & 0.0125 \\
    Milan & 0.0000883 & 0.000236 & -- \\
    Prague & 0.0000203 & 0.000222 & -- \\
    Tokyo Hachiko & 0.00491 & 0.0528 & 0.0104 \\
    Toulouse & 0.0000110 & 0.000173 & -- \\
    \bottomrule
  \end{tabular}
\end{table}

The 64-replica extension uses seeds 7 through 70 and nested looks of 16, 24,
32, 48, and 64. Its first 16 replicas exactly match the verified campaign
arrays after timing fields are removed. Mexico City route points 0, 1, and 3
and Tokyo Hachiko route points 13, 14, and 15 remain the six shadowed points.
The first-diffuse estimate is their only nonzero modeled contribution.
From 48 to 64 replicas, their largest pointwise whole-body SAR changes are
0.0125 and 0.0104~dB. The route $q_{10}$ changes are 0.00344 and 0.00491~dB,
and their whole-replica bootstrap widths are 0.364 and 0.0538~dB.

The bootstrap resamples complete replicas jointly over all route points, so it
preserves spatial dependence within one replica. Its 2,000 draws use PCG64 with
the authenticated analysis seed 20260814. All ten identities, manifests,
component closures, and common inputs pass, and both lower tails meet the
stated 48-to-64 aggregate criteria. Mexico City nevertheless retains
rare-event first-diffuse behavior: its maximum positive replica contribution
is 5738 times its positive-replica median, compared with 2.38 for Tokyo
Hachiko. These intervals apply to each fixed route.
They do not include route-selection or city-sampling uncertainty.

\begin{figure*}[!t]
  \centering
  \includegraphics[width=\textwidth]{figures/convergence64/convergence64.pdf}
  \caption{Convergence through 64 replicas. Panel (a) shows
  route $q_{10}$ whole-body SAR changes from the verified 16-replica value. Panel
  (b) shows the largest stepwise change among the three shadowed route points in
  each of Mexico City and Tokyo Hachiko. The final 48-to-64 changes satisfy the
  stated aggregate lower-tail criteria. Mexico City retains rare-event
  first-diffuse behavior.}
  \label{fig:si-convergence}
\end{figure*}
<!-- AUTO_END: assembled -->





























## Aggregation notes (AI-owned)
