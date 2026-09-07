% PREV: \subsection{AI-assisted digital twin}
% PREV: \label{sec:digital-twin}
% PREV:
% PREV: Two image models are applied in sequence. First, Mask2Former assigns a Vistas object
% PREV: class such as building, road, or vegetation to every pixel~\cite{mask2former,vistas}.
% PREV: Next, SAM~3 Agent performs the agentic AI step by assigning material and vegetation
% PREV: labels inside compatible object regions~\cite{sam3}. Its prompt-guided concepts
% PREV: extend the fixed object classes with material evidence. The camera position and
% PREV: viewing direction locate these labels on visible triangles in the city geometry. When several images cover one
% PREV: triangle, their accepted labels are combined. A triangle changes material only
% PREV: when its object and material labels are compatible and meet the selection
% PREV: criteria. All other triangles keep their geometry-based material. The
% PREV: supplementary material gives the prompts, alignment tests, rejected labels, and
% PREV: assignment rules.
% NEXT: \begin{figure*}[!htb]
% NEXT:   \centering
% NEXT:   \includegraphics[width=\textwidth]{figures/flowchart/flowchart.pdf}
% NEXT:   \caption{Flowchart from multimodal city data to whole-body specific absorption rate (SAR). Mask2Former assigns object labels, and SAM~3 Agent assigns material labels. These labels, 3-D city geometry, pedestrian locations and body orientations, and possible roofline transmitters form a human-centric digital twin. The propagation and body calculations then give whole-body SAR.}
% NEXT:   \label{fig:flowchart}
% NEXT: \end{figure*}
Fig.~\ref{fig:flowchart} connects the scene-building and exposure stages. The
image and geometry branches first form the human-centric digital twin.
Pedestrian locations, body orientations, and possible roofline transmitters
complete its route-specific inputs. The final stages compute directional radio
arrivals and apply them to the body.
