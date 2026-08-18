% PREV: The calculation uses a fixed route, city mesh, material map, and roofline
% PREV: transmitter model. Every route point uses 15~GHz and a crop with radius
% PREV: $R_{\mathrm{crop}}=250$~m, which gives
% PREV: $A_{\mathrm{crop}}=\pi R_{\mathrm{crop}}^2=196{,}349.54$~m$^2$. The receiver
% PREV: position $\mathbf{x}$ is the ray origin and body reference point. The body model faces along the local direction of travel. Index $i$
% PREV: denotes a roofline segment, $r_i(\mathbf{x})$ is its range to the receiver,
% PREV: and $\mathbf{r}$ is a position on the body surface. These assumptions are fixed
% PREV: across replicas and sites.
% NEXT: An unobstructed reference separates the source density from the scene geometry. The reference sums the inverse-square contribution of every roofline segment:
% NEXT: \begin{equation}
% NEXT: D_{\mathrm{ref}}(\mathbf{x})=
% NEXT: \sum_i\frac{p_i}{r_i(\mathbf{x})^2},
% NEXT: \qquad
% NEXT: S_{\mathrm{ref}}(\mathbf{x})=
% NEXT: \frac{A_{\mathrm{crop}}D_{\mathrm{ref}}(\mathbf{x})}{4\pi} \, .
% NEXT: \label{eq:reference-scale}
% NEXT: \end{equation}
% NEXT: No visibility test enters $D_{\mathrm{ref}}$. All reported quantities are
% NEXT: normalized per unit $\rho_A P_{\mathrm{EIRP}}$. Multiplication by
% NEXT: $\rho_A P_{\mathrm{EIRP}}$ recovers physical units, but only for a deployment
% NEXT: that follows the same roofline transmitter model. The calculation omits
% NEXT: transmitters and interactions outside the crop.
The exact positions of future transmitters are unknown, but elevated rooflines
are plausible street-facing locations. The model therefore distributes the
expected transmitters uniformly per unit physical length of the roofline visible
from the route. Let $\rho_A$ be the expected active-site density and let
$A_{\mathrm{crop}}$ be the crop area. For a roofline segment with endpoints
$\mathbf{p}_i$ and $\mathbf{p}_{i+1}$, $\ell_i$ is its physical
three-dimensional length. The expected number of transmitters and the fraction
assigned to segment $i$ are
\begin{equation}
N_{\mathrm{site}}=\rho_A A_{\mathrm{crop}},
\qquad
p_i=\frac{\ell_i}{\sum_j \ell_j},
\qquad
\ell_i=\left\lVert\mathbf{p}_{i+1}-\mathbf{p}_i\right\rVert_2 \, .
\label{eq:source-measure}
\end{equation}
Thus, $N_{\mathrm{site}}$ sets the number of transmitters and $p_i$ assigns a
fraction of that number to segment $i$. Dividing by the total roofline length
ensures that splitting one segment into smaller numerical pieces does not add
transmitters. The baseline uses three-dimensional length rather than horizontal
projected length.

## reviews (paragraph)

_(empty, run /review to populate)_

## grinder notes

- Source: `docs/CURRENT_PRODUCTION_CONTRACT.md` and `docs/SPINE.md`, M1.
- Guard: Physical three-dimensional edge length is the baseline. Plan-view length is not promoted.
