% PREV: Fig.~\ref{fig:flowchart} shows the computation and its input checks. A
% PREV: hash-verified manifest lists every input file: aligned images, material map,
% PREV: city mesh, route, roofline, body model, and transport settings. Only files whose
% PREV: hashes match the manifest enter the five-site data set. The transport
% PREV: calculation keeps direct, specular, and diffuse contributions separate until
% PREV: the field is applied to the body. The five manifests contain 210 verified entries. Across the
% PREV: resulting 1,168 directional body fields, the largest residual when the three
% PREV: components are summed back to the stored total is
% PREV: $1.735\times10^{-18}\,\mathrm{m}^{-2}$.
% NEXT: \subsection{Exposure Calculation}
% NEXT: \label{sec:exposure-calc}
\begin{figure*}[!t]
  \centering
  \includegraphics[width=\textwidth]{figures/flowchart/flowchart.pdf}
  \caption{Flowchart of the computation and input checks. Aligned 360-degree street images and the city mesh give the material map. The fixed route and visible roofline give observation and transmitter positions. Transport retains direct, first-order specular, and first-diffuse terms. A hash-verified file list pins every input to the ten-site result.}
  \label{fig:flowchart}
\end{figure*}
