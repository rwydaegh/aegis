% PREV: Figure~\ref{fig:flowchart} shows the computation and its audit boundary. A sealed manifest binds the registered evidence, material surface, transport mesh, route, source curve, body, sampler, and transport model before execution. The transport calculation keeps direct, first-order specular, and first-diffuse contributions separate until body coupling. Only matching files enter the five-site data set. The five manifests contain 210 verified entries. Across the resulting 1,168 directional body fields, the largest additive-closure residual is $1.735\times10^{-18}\,\mathrm{m}^{-2}$.
\begin{figure*}[!t]
  \centering
  \includegraphics[width=\textwidth]{figures/flowchart/flowchart.pdf}
  \caption{Computation and audit boundary. Registered panorama evidence and the support mesh give the fused material surface. The fixed route and its visible roofline give receiver positions and source support. Transport retains the exact direct term, the exact first-order specular term, and the first-diffuse term. Direction-aware body coupling then gives fixed-route exposure distributions. A sealed manifest binds the inputs before any result enters the five-site data set.}
  \label{fig:flowchart}
\end{figure*}
