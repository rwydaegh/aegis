% PREV: \section{Replica convergence and lower tails}
% PREV: \label{sec:si-convergence}
% NEXT: The 64-replica extension uses seeds 7 through 70 and nested looks of 16, 24,
% NEXT: 32, 48, and 64. Its first 16 replicas are exactly equal to the sealed campaign
% NEXT: arrays after timing fields are removed. Mexico City standpoints 0, 1, and 3
% NEXT: and Tokyo Hachiko standpoints 13, 14, and 15 remain the explicit shadowed
% NEXT: stratum. The first-diffuse estimate is their only nonzero modeled contribution.
% NEXT: From 48 to 64 replicas, their largest pointwise whole-body SAR changes are
% NEXT: 0.0125 and 0.0104~dB. The route $q_{10}$ changes are 0.00344 and 0.00491~dB,
% NEXT: and their whole-replica bootstrap widths are 0.364 and 0.0538~dB.
% NEXT:
% NEXT: The bootstrap resamples complete replicas jointly over all standpoints, so it
% NEXT: preserves spatial dependence within one replica. Its 2,000 draws use PCG64 with
% NEXT: the authenticated analysis seed 20260814. All five identities, manifests,
% NEXT: component closures, and common inputs pass, and both lower tails meet the
% NEXT: declared 48-to-64 aggregate criteria. Mexico City nevertheless retains
% NEXT: rare-event first-diffuse behavior: its maximum positive replica contribution
% NEXT: is 5738 times its positive-replica median, compared with 2.38 for Tokyo
% NEXT: Hachiko. These intervals remain conditional on each fixed registered route.
% NEXT: They do not include route-selection or city-sampling uncertainty.
% claim: replica_convergence_48_to_64
\begin{table}[!t]
  \caption{Current-contract convergence from 48 to 64 replicas. Bootstrap width is the 95\% interval width for route $q_{10}$ whole-body SAR. Shadow change is the largest stepwise change among the six declared shadowed standpoints.}
  \label{tab:si-convergence}
  \centering
  \begin{tabular}{lrrr}
    \toprule
    Site & \shortstack{$q_{10}$ change\\(dB)} & \shortstack{Bootstrap width\\(dB)} & \shortstack{Shadow change\\(dB)} \\
    \midrule
    Korenmarkt & 0.0000723 & 0.000222 & -- \\
    Prague & 0.0000203 & 0.000218 & -- \\
    Madrid & 0.00000615 & 0.000378 & -- \\
    Mexico City & 0.00344 & 0.364 & 0.0125 \\
    Tokyo Hachiko & 0.00491 & 0.0538 & 0.0104 \\
    \bottomrule
  \end{tabular}
\end{table}

## AI notes

- Exact diagnostics from the authenticated 64-replica extension.
