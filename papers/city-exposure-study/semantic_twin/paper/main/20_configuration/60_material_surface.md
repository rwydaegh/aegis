% PREV: \begin{table}[!t]
% PREV:   \caption{Five fixed routes and prepared-scene numerical campaign times}
% PREV:   \label{tab:routes}
% PREV:   \centering
% PREV:   \begin{tabular}{lrrr}
% PREV:     \hline
% PREV:     Site & Standpoints & Route span (m) & Wall time (s) \\
% PREV:     \hline
% PREV:     Korenmarkt & 10 & 49.04 & 29.79 \\
% PREV:     Prague & 22 & 119.39 & 69.02 \\
% PREV:     Madrid & 14 & 73.47 & 40.70 \\
% PREV:     Mexico City & 11 & 60.79 & 30.92 \\
% PREV:     Tokyo Hachiko & 16 & 87.38 & 50.11 \\
% PREV:     \hline
% PREV:     Total & 73 & 390.07 & 220.54 \\
% PREV:     \hline
% PREV:   \end{tabular}
% PREV: \end{table}
% NEXT: Figure~\ref{fig:flowchart} shows the computation and its audit boundary. A sealed manifest binds the registered evidence, material surface, transport mesh, route, source curve, body, sampler, and transport model before execution. The transport calculation keeps direct, first-order specular, and first-diffuse contributions separate until body coupling. Only matching files enter the five-site data set. The five manifests contain 210 verified entries. Across the resulting 1,168 directional body fields, the largest additive-closure residual is $1.735\times10^{-18}\,\mathrm{m}^{-2}$.
The two image models have separate roles. A dense Mask2Former model uses the Vistas street-scene taxonomy to assign one object class to every image pixel~\cite{mask2former,vistas}. This pass distinguishes, for example, buildings, road surfaces, people, vehicles, and vegetation. A promptable SAM 3 pass then tests radio-frequency material and vegetation concepts within object regions that can support them~\cite{sam3}. Thus, the dense pass supplies the object partition, while the promptable pass resolves compatible parts of that partition along the material axis. Registered camera locations and orientations project both forms of evidence onto the visible support surface. The projected observations are fused in a surface atlas and remain linked to the original support mesh. Image evidence changes a structural surface only when its object and material evidence is compatible and decisive. Evidence that is absent or does not pass these conditions leaves the declared geometry-based fallback unchanged. The prompt catalogue, registration gates, refusal categories, and fusion rules are given in the supplementary material.
