% PREV: \begin{figure*}[!t]
% PREV:   \centering
% PREV:   \includegraphics[width=\textwidth]{figures/flowchart/flowchart.pdf}
% PREV:   \caption{Flowchart of the computation and input checks. Aligned 360-degree street images and the city mesh give the material map. The fixed route and visible roofline give observation and transmitter positions. Transport retains direct, first-order specular, and first-diffuse terms. A hash-verified file list pins every input to the five-site result.}
% PREV:   \label{fig:flowchart}
% PREV: \end{figure*}
% NEXT: The calculation uses a fixed route, city mesh, material map, and roofline
% NEXT: transmitter model. Every route point uses 15~GHz and a crop with radius
% NEXT: $R_{\mathrm{crop}}=250$~m, which gives
% NEXT: $A_{\mathrm{crop}}=\pi R_{\mathrm{crop}}^2=196{,}349.54$~m$^2$. The receiver
% NEXT: position $\mathbf{x}$ is the ray origin and body reference point. The body model faces along the local direction of travel. Index $i$
% NEXT: denotes a roofline segment, $r_i(\mathbf{x})$ is its range to the receiver,
% NEXT: and $\mathbf{r}$ is a position on the body surface. These assumptions are fixed
% NEXT: across replicas and sites.
\subsection{Exposure Calculation}
\label{sec:exposure-calc}
