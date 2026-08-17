% PREV: Fig.~\ref{fig:flowchart} shows the computation and the files checked before it
% PREV: runs. A hash-verified manifest lists the aligned images, material map, city
% PREV: mesh, route, roofline, body, sampler, and transport settings. Only files that
% PREV: match this list enter the five-site data set. The transport calculation keeps
% PREV: direct, first-order specular, and first-diffuse contributions separate until
% PREV: body coupling. The five manifests contain 210 verified entries. Across the
% PREV: resulting 1,168 directional body fields, the largest additive-closure residual
% PREV: is $1.735\times10^{-18}\,\mathrm{m}^{-2}$.
\begin{figure*}[!t]
  \centering
  \includegraphics[width=\textwidth]{figures/flowchart/flowchart.pdf}
  \caption{Flowchart of the computation and input checks. Aligned 360-degree street images and the city mesh give the material map. The fixed route and visible roofline give observation and transmitter positions. Transport retains direct, first-order specular, and first-diffuse terms. A hash-verified file list pins every input to the five-site result.}
  \label{fig:flowchart}
\end{figure*}
