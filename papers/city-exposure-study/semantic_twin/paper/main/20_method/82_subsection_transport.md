% PREV: \begin{figure*}[!htb]
% PREV:   \centering
% PREV:   \includegraphics[width=\textwidth]{figures/flowchart/flowchart.pdf}
% PREV:   \caption{Flowchart from multimodal city data to whole-body specific absorption rate (SAR). Mask2Former assigns object labels, and SAM~3 Agent assigns material labels. These labels, 3-D city geometry, pedestrian locations and body orientations, and possible roofline transmitters form a human-centric digital twin. The propagation and body calculations then give whole-body SAR.}
% PREV:   \label{fig:flowchart}
% PREV: \end{figure*}
% NEXT: Following the central path in Fig.~\ref{fig:flowchart}, every route point uses
% NEXT: 15~GHz and a circular scene crop with radius
% NEXT: $R_{\mathrm{crop}}=250$~m and area
% NEXT: $A_{\mathrm{crop}}=196{,}349.54$~m$^2$. The receiver position $\mathbf{x}$ is
% NEXT: the ray origin and body reference point. The body faces the local direction of
% NEXT: travel. Index $i$ denotes a roofline segment, $r_i(\mathbf{x})$ is its range to
% NEXT: the receiver, and $\mathbf{r}$ is a point on the body surface.
\subsection{Exposure calculation}
\label{sec:exposure-calc}
