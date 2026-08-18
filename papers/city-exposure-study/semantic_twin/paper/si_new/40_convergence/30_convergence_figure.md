% PREV: The 64-replica extension uses seeds 7 through 70 and nested looks of 16, 24,
% PREV: 32, 48, and 64. Its first 16 replicas exactly match the verified campaign
% PREV: arrays after timing fields are removed. Mexico City route points 0, 1, and 3
% PREV: and Tokyo Hachiko route points 13, 14, and 15 remain the six shadowed points.
% PREV: The first-diffuse estimate is their only nonzero modeled contribution.
% PREV: From 48 to 64 replicas, their largest pointwise whole-body SAR changes are
% PREV: 0.0125 and 0.0104~dB. The route $q_{10}$ changes are 0.00344 and 0.00491~dB,
% PREV: and their whole-replica bootstrap widths are 0.364 and 0.0538~dB.
% PREV:
% PREV: The bootstrap resamples complete replicas jointly over all route points, so it
% PREV: preserves spatial dependence within one replica. Its 2,000 draws use PCG64 with
% PREV: the authenticated analysis seed 20260814. All five identities, manifests,
% PREV: component closures, and common inputs pass, and both lower tails meet the
% PREV: stated 48-to-64 aggregate criteria. Mexico City nevertheless retains
% PREV: rare-event first-diffuse behavior: its maximum positive replica contribution
% PREV: is 5738 times its positive-replica median, compared with 2.38 for Tokyo
% PREV: Hachiko. These intervals apply to each fixed route.
% PREV: They do not include route-selection or city-sampling uncertainty.
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

## Reviews

_(empty)_
