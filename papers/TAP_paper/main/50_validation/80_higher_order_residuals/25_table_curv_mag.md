% PREV: First, we examine the influence of curvature. For a surface with
% PREV: twice the local mean curvature $H = 1/R_1 +
% PREV: 1/R_2$, the first-order Physical Optics correction multiplies the
% PREV: geometric law by $1 + \mu/(kR_1) + \mu/(kR_2)$, where
% PREV: $k = 2\pi/\lambda$ is the free-space wavenumber. Since
% PREV: $\pospart{\mu}\cdot\mu = \pospart{\mu}^2$, the per-triangle update
% PREV: separates additively,
% PREV: \begin{equation}\label{eq:curv-update}
% PREV:   \APD^{(j)} = T_0 \sum_i S_i\!\left[
% PREV:   \pospart{\mu_{ji}} + \frac{H_j}{k}\,\pospart{\mu_{ji}}^2 \right]
% PREV:   V_{ji}\, ,
% PREV: \end{equation}
% PREV: adding a quadratic gate on top of the linear one. The magnitude is
% PREV: set by $1/(kR)$. \Cref{tab:curv-mag} lists the correction at
% PREV: $28$~GHz on representative body parts.
% NEXT: The correction grows as the wavelength approaches the local
% NEXT: body-part size. At sub-$6$~GHz frequencies the smallest features
% NEXT: have $kR \lesssim 5$ where the correction is no longer small. At
% NEXT: $28$~GHz, only the ear edges and fingertips carry a correction
% NEXT: above the Fresnel error floor.
\begin{table}[!t]
\centering
\caption{Curvature correction at $28$~GHz ($k \approx 587$~m$^{-1}$).
The correction is below the Fresnel approximation error for most
body regions and concentrates at small features.}
\label{tab:curv-mag}
\begin{tabular}{lccc}
\toprule
Region & $R$\,[mm] & $1/(kR)$ & Correction \\
\midrule
Torso, head & $> 100$ & $< 0.2\%$ & negligible \\
Arm         & approx.\ $40$ & $0.4\%$ & approx.\ $0.4\%$ \\
Finger      & approx.\ $8$  & $2.1\%$ & approx.\ $2\%$ \\
Ear edge    & approx.\ $2$  & $8.5\%$ & approx.\ $8\%$ \\
\bottomrule
\end{tabular}
\end{table}

## reviews (table)



_PaperMaker9000 sweep — all clear across 1 lens(es)._

- **table** — pass (10 rules cleared).

## grinder notes
- **label**: tab:curv-mag
- **caption_preview**: Curvature correction at $28$~GHz ($k \approx 587$~m$^{-1
