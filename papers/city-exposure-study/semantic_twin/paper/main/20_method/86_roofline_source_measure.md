% PREV: Following the central path in Fig.~\ref{fig:flowchart}, every route point uses
% PREV: 15~GHz and a circular scene crop with radius
% PREV: $R_{\mathrm{crop}}=250$~m and area
% PREV: $A_{\mathrm{crop}}=196{,}349.54$~m$^2$. The receiver position $\mathbf{x}$ is
% PREV: the ray origin and body reference point. The body faces the local direction of
% PREV: travel. Index $i$ denotes a roofline segment, $r_i(\mathbf{x})$ is its range to
% PREV: the receiver, and $\mathbf{r}$ is a point on the body surface.
% NEXT: An unobstructed reference separates source strength from scene geometry:
% NEXT: \begin{equation}
% NEXT: D_{\mathrm{ref}}(\mathbf{x})=
% NEXT: \sum_i\frac{p_i}{r_i(\mathbf{x})^2},
% NEXT: \qquad
% NEXT: S_{\mathrm{ref}}(\mathbf{x})=
% NEXT: \frac{A_{\mathrm{crop}}D_{\mathrm{ref}}(\mathbf{x})}{4\pi} \, .
% NEXT: \label{eq:reference-scale}
% NEXT: \end{equation}
% NEXT: We apply no visibility test to $D_{\mathrm{ref}}$. All reported values are
% NEXT: normalized per unit $\rho_A P_{\mathrm{EIRP}}$. Multiplication by
% NEXT: $\rho_A P_{\mathrm{EIRP}}$ gives physical units, but only for a deployment
% NEXT: that follows the same roofline transmitter model. The calculation omits
% NEXT: transmitters and interactions outside the crop.
The possible roofline transmitters in Fig.~\ref{fig:flowchart} represent a
future distributed massive MIMO (DMaMIMO) architecture only to
define possible access-point locations~\cite{wydaeghe2026,ngo2017}. Therefore,
the model uses visible rooflines as possible transmitter locations. The
calculation treats the possible sites as independent power sources and
distributes expected transmitters uniformly per
unit physical length of the roofline visible from the route. The active-site density $\rho_A$ gives an
expected count $N_{\mathrm{site}}=\rho_A A_{\mathrm{crop}}$. For a segment with
endpoints $\mathbf{p}_i$ and $\mathbf{p}_{i+1}$, its source fraction is
\begin{equation}
p_i=\frac{\ell_i}{\sum_j \ell_j},\qquad
\ell_i=\lVert\mathbf{p}_{i+1}-\mathbf{p}_i\rVert_2 .
\label{eq:source-measure}
\end{equation}
The denominator prevents a numerical split of one segment from adding source
power. The calculation uses three-dimensional length rather than horizontal
length.

## reviews (paragraph)

_(empty, run /review to populate)_

## grinder notes

- Source: `docs/CURRENT_PRODUCTION_CONTRACT.md` and `docs/SPINE.md`, M1.
- Guard: Physical three-dimensional edge length is the baseline. Plan-view length is not promoted.
