% PREV: \subsection{Exposure calculation}
% PREV: \label{sec:exposure-calc}
% NEXT: The possible roofline transmitters in Fig.~\ref{fig:flowchart} represent a
% NEXT: future distributed massive MIMO (DMaMIMO) architecture only to
% NEXT: define possible access-point locations~\cite{wydaeghe2026,ngo2017}. Therefore,
% NEXT: the model uses visible rooflines as possible transmitter locations. The
% NEXT: calculation treats the possible sites as independent power sources and
% NEXT: distributes expected transmitters uniformly per
% NEXT: unit physical length of the roofline visible from the route. The active-site density $\rho_A$ gives an
% NEXT: expected count $N_{\mathrm{site}}=\rho_A A_{\mathrm{crop}}$. For a segment with
% NEXT: endpoints $\mathbf{p}_i$ and $\mathbf{p}_{i+1}$, its source fraction is
% NEXT: \begin{equation}
% NEXT: p_i=\frac{\ell_i}{\sum_j \ell_j},\qquad
% NEXT: \ell_i=\lVert\mathbf{p}_{i+1}-\mathbf{p}_i\rVert_2 .
% NEXT: \label{eq:source-measure}
% NEXT: \end{equation}
% NEXT: The denominator prevents a numerical split of one segment from adding source
% NEXT: power. The calculation uses three-dimensional length rather than horizontal
% NEXT: length.
Following the central path in Fig.~\ref{fig:flowchart}, every route point uses
15~GHz and a circular scene crop with radius
$R_{\mathrm{crop}}=250$~m and area
$A_{\mathrm{crop}}=196{,}349.54$~m$^2$. The receiver position $\mathbf{x}$ is
the ray origin and body reference point. The body faces the local direction of
travel. Index $i$ denotes a roofline segment, $r_i(\mathbf{x})$ is its range to
the receiver, and $\mathbf{r}$ is a point on the body surface.

## reviews (paragraph)

_(empty, run /review to populate)_

## grinder notes

- Source: `docs/CURRENT_PRODUCTION_CONTRACT.md`, `docs/RESULTS_INVENTORY.md`, and `paper/spine.md`.
- Scope: Compact notation and fixed assumptions only. Scene construction belongs to Section II.
