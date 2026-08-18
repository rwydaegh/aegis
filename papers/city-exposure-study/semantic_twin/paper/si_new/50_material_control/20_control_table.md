% PREV: The control replaces the image-derived material map with geometry-based
% PREV: materials in Madrid and Mexico City. Each pair keeps the city mesh, route,
% PREV: source curve, source weights, body, frequency, transport steps, ray count,
% PREV: output cells, and 16 seeds fixed. A strict compatibility check permits changes
% PREV: only in the material mode, the material arrays and hashes, the run
% PREV: configuration, and the presence of the material-map files. Both paired manifests pass
% PREV: all 42 file hashes. The comparison therefore measures sensitivity to the
% PREV: image-derived material map under the current model. It does not isolate reflectance because
% PREV: the map also changes roughness, specular share, and the nonblocking state of
% PREV: woody vegetation. It does not measure semantic or material accuracy.
% NEXT: The direct component is identical within each pair. In Madrid, the image-derived map raises
% NEXT: the route-median all-specular whole-body SAR by 1.89 dB and lowers the
% NEXT: first-diffuse component by 12.43 dB. Their combined effect changes the total
% NEXT: route median by 0.249 dB. Mexico City's 24.84 dB q10 change is set by three
% NEXT: shadowed route points where both alternatives are near zero and first-diffuse
% NEXT: transport is the only nonzero modeled contribution. The Mexico City median and q90
% NEXT: changes are $-0.158$ and 0.104 dB. The two sites show that component changes can
% NEXT: be much larger than the change in total normalized whole-body SAR. The result
% NEXT: supports a material-map sensitivity statement for these routes only.
\begin{table}[!t]
  \caption{Image-to-geometry change in route quantiles of normalized
  whole-body SAR. Positive values mean that the image-derived result is larger.}
  \label{tab:si-material-control}
  \centering
  \begin{tabular}{lrrr}
    \toprule
    Site & q10 (dB) & q50 (dB) & q90 (dB) \\
    \midrule
    Madrid & 0.233 & 0.249 & 0.269 \\
    Mexico City & 24.84 & -0.158 & 0.104 \\
    \bottomrule
  \end{tabular}
\end{table}

## AI notes

- Current paired control only. No old evidence-ladder values.
