% PREV: Fig.~\ref{fig:flowchart} connects the scene-building and exposure stages. The
% PREV: image and geometry branches first form the human-centric digital twin.
% PREV: Pedestrian locations, body orientations, and possible roofline transmitters
% PREV: complete its route-specific inputs. The final stages compute directional radio
% PREV: arrivals and apply them to the body.
% NEXT: \subsection{Exposure calculation}
% NEXT: \label{sec:exposure-calc}
\begin{figure*}[!htb]
  \centering
  \includegraphics[width=\textwidth]{figures/flowchart/flowchart.pdf}
  \caption{Flowchart from multimodal city data to whole-body specific absorption rate (SAR). Mask2Former assigns object labels, and SAM~3 Agent assigns material labels. These labels, 3-D city geometry, pedestrian locations and body orientations, and possible roofline transmitters form a human-centric digital twin. The propagation and body calculations then give whole-body SAR.}
  \label{fig:flowchart}
\end{figure*}
