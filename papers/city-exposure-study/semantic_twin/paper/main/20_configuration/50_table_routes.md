% PREV: Table~\ref{tab:routes} lists the five selected routes. The standpoint counts and spans come from the sealed route records used for the five-site data set. Each route follows a connected corridor supported by registered panoramas, and the calculation samples fixed positions along that corridor. A panorama center constrains the route but is not, in general, an exposure standpoint. Therefore, panorama and standpoint counts need not agree. The 73 standpoints are fixed observations, not a random sample of pedestrians or places. Route distributions in this study are conditional on these five paths. The local route tangent also fixes body yaw, so a change in route definition would change both receiver position and orientation.
% NEXT: The two image models have separate roles. A dense Mask2Former model uses the Vistas street-scene taxonomy to assign one object class to every image pixel~\cite{mask2former,vistas}. This pass distinguishes, for example, buildings, road surfaces, people, vehicles, and vegetation. A promptable SAM 3 pass then tests radio-frequency material and vegetation concepts within object regions that can support them~\cite{sam3}. Thus, the dense pass supplies the object partition, while the promptable pass resolves compatible parts of that partition along the material axis. Registered camera locations and orientations project both forms of evidence onto the visible support surface. The projected observations are fused in a surface atlas and remain linked to the original support mesh. Image evidence changes a structural surface only when its object and material evidence is compatible and decisive. Evidence that is absent or does not pass these conditions leaves the declared geometry-based fallback unchanged. The prompt catalogue, registration gates, refusal categories, and fusion rules are given in the supplementary material.
\begin{table}[!t]
  \caption{Five fixed routes and prepared-scene numerical campaign times}
  \label{tab:routes}
  \centering
  \begin{tabular}{lrrr}
    \hline
    Site & Standpoints & Route span (m) & Wall time (s) \\
    \hline
    Korenmarkt & 10 & 49.04 & 29.79 \\
    Prague & 22 & 119.39 & 69.02 \\
    Madrid & 14 & 73.47 & 40.70 \\
    Mexico City & 11 & 60.79 & 30.92 \\
    Tokyo Hachiko & 16 & 87.38 & 50.11 \\
    \hline
    Total & 73 & 390.07 & 220.54 \\
    \hline
  \end{tabular}
\end{table}
