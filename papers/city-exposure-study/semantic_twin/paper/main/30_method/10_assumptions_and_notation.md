% PREV: \section{Route-Conditioned Exposure Method}
% PREV: \label{sec:method}
% NEXT: The source model separates physical source scale from numerical placement. Let $\rho_A$ be the expected active-site density and let $A_{\mathrm{crop}}$ be the crop area. For a roofline element with endpoints $\mathbf{p}_i$ and $\mathbf{p}_{i+1}$, $\ell_i$ is its physical three-dimensional arc length. The expected site count and the conditional source weights are
% NEXT: \begin{equation}
% NEXT: N_{\mathrm{site}}=\rho_A A_{\mathrm{crop}},
% NEXT: \qquad
% NEXT: p_i=\frac{\ell_i}{\sum_j \ell_j},
% NEXT: \qquad
% NEXT: \ell_i=\left\lVert\mathbf{p}_{i+1}-\mathbf{p}_i\right\rVert_2 .
% NEXT: \label{eq:source-measure}
% NEXT: \end{equation}
% NEXT: Thus, $N_{\mathrm{site}}$ sets the physical scale, whereas $p_i$ distributes that scale over the observed route-aligned roofline. The number of numerical elements is not a source count. Horizontal projected length is an explicit sensitivity option and is not used in the baseline.
The calculation is conditioned on a fixed route, support mesh, material surface, and roofline source curve. Every standpoint uses 15~GHz and a crop with radius $R_{\mathrm{crop}}=250$~m, which gives $A_{\mathrm{crop}}=\pi R_{\mathrm{crop}}^2=196{,}349.54$~m$^2$. The receiver position $\mathbf{x}$ is also the reciprocal ray origin and body reference point. The body yaw follows the local route tangent. Index $i$ denotes a numerical roofline element, $r_i(\mathbf{x})$ is its range to the receiver, and $\mathbf{r}$ denotes a body surface element. These assumptions remain fixed across replicas and sites.

## reviews (paragraph)

_(empty, run /review to populate)_

## grinder notes

- Source: `docs/CURRENT_PRODUCTION_CONTRACT.md`, `docs/RESULTS_INVENTORY.md`, and `paper/spine.md`.
- Scope: Compact notation and fixed assumptions only. Scene construction belongs to Section II.
