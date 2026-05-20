% PREV: \begin{table}[!t]
% NEXT: The correction grows as the wavelength approaches the local
# Curvature

<!-- AUTO_BEGIN: assembled -->
% NEXT: For a surface with twice the local mean curvature $H = 1/R_1 +
\subsection{Curvature}\label{subsec:corr-curv}

% PREV: \subsection{Curvature}\label{subsec:corr-curv}
% NEXT: \begin{table}[!t]
For a surface with twice the local mean curvature $H = 1/R_1 +
1/R_2$, the first-order Physical Optics correction multiplies the
geometric law by $1 + \mu/(kR_1) + \mu/(kR_2)$, where
$k = 2\pi/\lambda$ is the free-space wavenumber. Since
$\pospart{\mu}\cdot\mu = \pospart{\mu}^2$, the per-triangle update
separates additively,
\begin{equation}\label{eq:curv-update}
  \APD^{(j)} = T_0 \sum_i S_i\!\left[
  \pospart{\mu_{ji}} + \frac{H_j}{k}\,\pospart{\mu_{ji}}^2 \right]
  V_{ji}\, ,
\end{equation}
adding a quadratic gate on top of the linear one. The magnitude is
set by $1/(kR)$. \Cref{tab:curv-mag} lists the correction at
$28$~GHz on representative body parts.

% PREV: For a surface with twice the local mean curvature $H = 1/R_1 +
% NEXT: # Curvature
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

% PREV: # Curvature
The correction grows as the wavelength approaches the local
body-part size. At sub-$6$~GHz frequencies the smallest features
have $kR \lesssim 5$ where the correction is no longer small. At
$28$~GHz, only the ear edges and fingertips carry a correction
above the Fresnel error floor.
<!-- AUTO_END: assembled -->



## section notes

_(AI-owned notes about this section as a whole)_
