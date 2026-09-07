% PREV: \begin{table}[!t]
% PREV:   \caption{Study route in each city, with observation-point counts, route spans, and ray calculation times}
% PREV:   \label{tab:routes}
% PREV:   \centering
% PREV:   \begin{tabular}{lrrr}
% PREV:     \toprule
% PREV:     City & Points & Span (m) & Time (s) \\
% PREV:     \midrule
% PREV:     Brussels & 14 & 87.00 & 32.16 \\
% PREV:     Ghent & 10 & 49.04 & 6.59 \\
% PREV:     Krakow & 16 & 116.10 & 31.76 \\
% PREV:     London & 22 & 121.10 & 73.77 \\
% PREV:     Madrid & 14 & 73.47 & 8.06 \\
% PREV:     Mexico City & 11 & 60.79 & 5.95 \\
% PREV:     Milan & 23 & 128.43 & 69.02 \\
% PREV:     Prague & 22 & 119.39 & 39.00 \\
% PREV:     Tokyo Hachiko & 16 & 87.38 & 10.02 \\
% PREV:     Toulouse & 15 & 82.47 & 37.87 \\
% PREV:     \midrule
% PREV:     Total & 163 & 925.17 & 314.20 \\
% PREV:     \bottomrule
% PREV:   \end{tabular}
% PREV: \end{table}
% NEXT: Fig.~\ref{fig:flowchart} connects the scene-building and exposure stages. The
% NEXT: image and geometry branches first form the human-centric digital twin.
% NEXT: Pedestrian locations, body orientations, and possible roofline transmitters
% NEXT: complete its route-specific inputs. The final stages compute directional radio
% NEXT: arrivals and apply them to the body.
\subsection{AI-assisted digital twin}
\label{sec:digital-twin}

Two image models are applied in sequence. First, Mask2Former assigns a Vistas object
class such as building, road, or vegetation to every pixel~\cite{mask2former,vistas}.
Next, SAM~3 Agent performs the agentic AI step by assigning material and vegetation
labels inside compatible object regions~\cite{sam3}. Its prompt-guided concepts
extend the fixed object classes with material evidence. The camera position and
viewing direction locate these labels on visible triangles in the city geometry. When several images cover one
triangle, their accepted labels are combined. A triangle changes material only
when its object and material labels are compatible and meet the selection
criteria. All other triangles keep their geometry-based material. The
supplementary material gives the prompts, alignment tests, rejected labels, and
assignment rules.
