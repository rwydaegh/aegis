% PREV: With this configuration fixed, Table~\ref{tab:routes} summarizes the study
% PREV: route in each of the ten cities. Each
% PREV: route follows a connected street corridor covered by aligned 360-degree street
% PREV: images. Fixed observation points include positions between image locations, so
% PREV: the number of images and points can differ. The 163 points are fixed case-study
% PREV: observations that describe the selected routes. A different route would change
% PREV: both position and body orientation.
% NEXT: \subsection{AI-assisted digital twin}
% NEXT: \label{sec:digital-twin}
% NEXT:
% NEXT: Two image models are applied in sequence. First, Mask2Former assigns a Vistas object
% NEXT: class such as building, road, or vegetation to every pixel~\cite{mask2former,vistas}.
% NEXT: Next, SAM~3 Agent performs the agentic AI step by assigning material and vegetation
% NEXT: labels inside compatible object regions~\cite{sam3}. Its prompt-guided concepts
% NEXT: extend the fixed object classes with material evidence. The camera position and
% NEXT: viewing direction locate these labels on visible triangles in the city geometry. When several images cover one
% NEXT: triangle, their accepted labels are combined. A triangle changes material only
% NEXT: when its object and material labels are compatible and meet the selection
% NEXT: criteria. All other triangles keep their geometry-based material. The
% NEXT: supplementary material gives the prompts, alignment tests, rejected labels, and
% NEXT: assignment rules.
\begin{table}[!t]
  \caption{Study route in each city, with observation-point counts, route spans, and ray calculation times}
  \label{tab:routes}
  \centering
  \begin{tabular}{lrrr}
    \toprule
    City & Points & Span (m) & Time (s) \\
    \midrule
    Brussels & 14 & 87.00 & 32.16 \\
    Ghent & 10 & 49.04 & 6.59 \\
    Krakow & 16 & 116.10 & 31.76 \\
    London & 22 & 121.10 & 73.77 \\
    Madrid & 14 & 73.47 & 8.06 \\
    Mexico City & 11 & 60.79 & 5.95 \\
    Milan & 23 & 128.43 & 69.02 \\
    Prague & 22 & 119.39 & 39.00 \\
    Tokyo Hachiko & 16 & 87.38 & 10.02 \\
    Toulouse & 15 & 82.47 & 37.87 \\
    \midrule
    Total & 163 & 925.17 & 314.20 \\
    \bottomrule
  \end{tabular}
\end{table}
