% PREV: \section{Paired material-evidence control}
% PREV: \label{sec:si-material-control}
% NEXT: \begin{table}[!t]
% NEXT:   \caption{Atlas-to-geometric change in route quantiles of normalized
% NEXT:   whole-body SAR. Positive values mean that the atlas result is larger.}
% NEXT:   \label{tab:si-material-control}
% NEXT:   \centering
% NEXT:   \begin{tabular}{lrrr}
% NEXT:     \toprule
% NEXT:     Site & q10 (dB) & q50 (dB) & q90 (dB) \\
% NEXT:     \midrule
% NEXT:     Madrid & 0.233 & 0.249 & 0.269 \\
% NEXT:     Mexico City & 24.84 & -0.158 & 0.104 \\
% NEXT:     \bottomrule
% NEXT:   \end{tabular}
% NEXT: \end{table}
The control replaces the panorama-derived atlas layer with the geometric
fallback in Madrid and Mexico City. Each pair keeps the support mesh, route,
source curve, source weights, body, frequency, transport topology, ray count,
output cells, and 16 seeds fixed. A strict compatibility check permits changes
only in the material mode, the material arrays and hashes, the run
configuration, and the presence of the atlas files. Both paired manifests pass
all 42 file hashes. The comparison therefore measures sensitivity to the atlas
evidence layer under the current model. It does not isolate reflectance because
the atlas also changes roughness, specular share, and the nonblocking state of
woody vegetation. It does not measure semantic or material accuracy.

## AI notes

- Defines the estimand and its boundary before giving numbers.
