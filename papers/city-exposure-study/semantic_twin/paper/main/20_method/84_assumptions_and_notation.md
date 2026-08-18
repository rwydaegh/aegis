% PREV: \subsection{Exposure Calculation}
% PREV: \label{sec:exposure-calc}
% NEXT: The exact positions of future transmitters are unknown, but elevated rooflines
% NEXT: are plausible street-facing locations. The model therefore distributes the
% NEXT: expected transmitters uniformly per unit physical length of the roofline visible
% NEXT: from the route. Let $\rho_A$ be the expected active-site density and let
% NEXT: $A_{\mathrm{crop}}$ be the crop area. For a roofline segment with endpoints
% NEXT: $\mathbf{p}_i$ and $\mathbf{p}_{i+1}$, $\ell_i$ is its physical
% NEXT: three-dimensional length. The expected number of transmitters and the fraction
% NEXT: assigned to segment $i$ are
% NEXT: \begin{equation}
% NEXT: N_{\mathrm{site}}=\rho_A A_{\mathrm{crop}},
% NEXT: \qquad
% NEXT: p_i=\frac{\ell_i}{\sum_j \ell_j},
% NEXT: \qquad
% NEXT: \ell_i=\left\lVert\mathbf{p}_{i+1}-\mathbf{p}_i\right\rVert_2 \, .
% NEXT: \label{eq:source-measure}
% NEXT: \end{equation}
% NEXT: Thus, $N_{\mathrm{site}}$ sets the number of transmitters and $p_i$ assigns a
% NEXT: fraction of that number to segment $i$. Dividing by the total roofline length
% NEXT: ensures that splitting one segment into smaller numerical pieces does not add
% NEXT: transmitters. The baseline uses three-dimensional length rather than horizontal
% NEXT: projected length.
The calculation uses a fixed route, city mesh, material map, and roofline
transmitter model. Every route point uses 15~GHz and a crop with radius
$R_{\mathrm{crop}}=250$~m, which gives
$A_{\mathrm{crop}}=\pi R_{\mathrm{crop}}^2=196{,}349.54$~m$^2$. The receiver
position $\mathbf{x}$ is the ray origin and body reference point. The body model faces along the local direction of travel. Index $i$
denotes a roofline segment, $r_i(\mathbf{x})$ is its range to the receiver,
and $\mathbf{r}$ is a position on the body surface. These assumptions are fixed
across replicas and sites.

## reviews (paragraph)

_(empty, run /review to populate)_

## grinder notes

- Source: `docs/CURRENT_PRODUCTION_CONTRACT.md`, `docs/RESULTS_INVENTORY.md`, and `paper/spine.md`.
- Scope: Compact notation and fixed assumptions only. Scene construction belongs to Section II.
