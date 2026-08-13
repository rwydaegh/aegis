% PREV: The calculation is conditioned on a fixed route, support mesh, material surface, and roofline source curve. Every standpoint uses 15~GHz and a crop with radius $R_{\mathrm{crop}}=250$~m, which gives $A_{\mathrm{crop}}=\pi R_{\mathrm{crop}}^2=196{,}349.54$~m$^2$. The receiver position $\mathbf{x}$ is also the reciprocal ray origin and body reference point. The body yaw follows the local route tangent. Index $i$ denotes a numerical roofline element, $r_i(\mathbf{x})$ is its range to the receiver, and $\mathbf{r}$ denotes a body surface element. These assumptions remain fixed across replicas and sites.
% NEXT: An unobstructed reference keeps network scale separate from scene visibility. The reference includes the inverse-square geometry of the complete source curve:
% NEXT: \begin{equation}
% NEXT: D_{\mathrm{ref}}(\mathbf{x})=
% NEXT: \sum_i\frac{p_i}{r_i(\mathbf{x})^2},
% NEXT: \qquad
% NEXT: S_{\mathrm{ref}}(\mathbf{x})=
% NEXT: \frac{A_{\mathrm{crop}}D_{\mathrm{ref}}(\mathbf{x})}{4\pi} .
% NEXT: \label{eq:reference-scale}
% NEXT: \end{equation}
% NEXT: No visibility test enters $D_{\mathrm{ref}}$. The reported transfer and body endpoints are normalized per unit $\rho_A P_{\mathrm{EIRP}}$. Multiplication by $\rho_A P_{\mathrm{EIRP}}$ gives a physical scale only for a deployment that follows the same conditional roofline source measure. Sources and interactions outside the crop are absent.
The source model separates physical source scale from numerical placement. Let $\rho_A$ be the expected active-site density and let $A_{\mathrm{crop}}$ be the crop area. For a roofline element with endpoints $\mathbf{p}_i$ and $\mathbf{p}_{i+1}$, $\ell_i$ is its physical three-dimensional arc length. The expected site count and the conditional source weights are
\begin{equation}
N_{\mathrm{site}}=\rho_A A_{\mathrm{crop}},
\qquad
p_i=\frac{\ell_i}{\sum_j \ell_j},
\qquad
\ell_i=\left\lVert\mathbf{p}_{i+1}-\mathbf{p}_i\right\rVert_2 .
\label{eq:source-measure}
\end{equation}
Thus, $N_{\mathrm{site}}$ sets the physical scale, whereas $p_i$ distributes that scale over the observed route-aligned roofline. The number of numerical elements is not a source count. Horizontal projected length is an explicit sensitivity option and is not used in the baseline.

## reviews (paragraph)

_(empty, run /review to populate)_

## grinder notes

- Source: `docs/CURRENT_PRODUCTION_CONTRACT.md` and `docs/SPINE.md`, M1.
- Guard: Physical three-dimensional edge length is the baseline. Plan-view length is not promoted.
