<!-- AUTO_BEGIN: assembled -->
\section{Configuration and Scene Evidence}
\label{sec:configuration}

The study configuration is shown in Fig.~\ref{fig:configuration}. Registered street panoramas supply surface evidence to a photogrammetric support mesh cropped to a 250\,m radius. They do not create or alter its geometry. The original mesh remains the transport surface, while the image evidence supplies the surface classes queried on that mesh. A route-visible roofline defines the source support. Fixed positions along a pedestrian route define the receiver locations. At each position, the anatomical body has a horizontal orientation set by the local route tangent.

\begin{figure*}[!t]
  \centering
  \includegraphics[width=\textwidth]{figures/configuration/configuration.pdf}
  \caption{Study configuration at Prague Old Town Square. The registered panorama in (a) is aligned with the traced support in (b). Panel (c) shows the surface classes supplied to transport: atlas interfaces, nonblocking woody vegetation, and the geometric fallback. In (d), orange marks roofline source support, filled squares mark registered panorama endpoints, and the arrow gives one route-tangent yaw. The calculation uses a 250\,m-radius support mesh, 502 roofline source elements, and 22 fixed standpoints. Panel (e) shows the anatomical body in neutral gray.}
  \label{fig:configuration}
\end{figure*}

Table~\ref{tab:routes} lists the five selected routes. The standpoint counts and spans come from the sealed route records used for the five-site data set. Each route follows a connected corridor supported by registered panoramas, and the calculation samples fixed positions along that corridor. A panorama center constrains the route but is not, in general, an exposure standpoint. Therefore, panorama and standpoint counts need not agree. The 73 standpoints are fixed observations, not a random sample of pedestrians or places. Route distributions in this study are conditional on these five paths. The local route tangent also fixes body yaw, so a change in route definition would change both receiver position and orientation.

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

The two image models have separate roles. A dense Mask2Former model uses the Vistas street-scene taxonomy to assign one object class to every image pixel~\cite{mask2former,vistas}. This pass distinguishes, for example, buildings, road surfaces, people, vehicles, and vegetation. A promptable SAM 3 pass then tests radio-frequency material and vegetation concepts within object regions that can support them~\cite{sam3}. Thus, the dense pass supplies the object partition, while the promptable pass resolves compatible parts of that partition along the material axis. Registered camera locations and orientations project both forms of evidence onto the visible support surface. The projected observations are fused in a surface atlas and remain linked to the original support mesh. Image evidence changes a structural surface only when its object and material evidence is compatible and decisive. Evidence that is absent or does not pass these conditions leaves the declared geometry-based fallback unchanged. The prompt catalogue, registration gates, refusal categories, and fusion rules are given in the supplementary material.

Figure~\ref{fig:flowchart} shows the computation and its audit boundary. A sealed manifest binds the registered evidence, material surface, transport mesh, route, source curve, body, sampler, and transport model before execution. The transport calculation keeps direct, first-order specular, and first-diffuse contributions separate until body coupling. Only matching files enter the five-site data set. The five manifests contain 210 verified entries. Across the resulting 1,168 directional body fields, the largest additive-closure residual is $1.735\times10^{-18}\,\mathrm{m}^{-2}$.

\begin{figure*}[!t]
  \centering
  \includegraphics[width=\textwidth]{figures/flowchart/flowchart.pdf}
  \caption{Computation and audit boundary. Registered panorama evidence and the support mesh give the fused material surface. The fixed route and its visible roofline give receiver positions and source support. Transport retains the exact direct term, the exact first-order specular term, and the first-diffuse term. Direction-aware body coupling then gives fixed-route exposure distributions. A sealed manifest binds the inputs before any result enters the five-site data set.}
  \label{fig:flowchart}
\end{figure*}
<!-- AUTO_END: assembled -->





## Aggregation notes (AI-owned)
