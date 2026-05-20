% PREV: The correction box in the flowchart collects the effects left out by
% NEXT: \begin{table}[!t]
First, we examine the influence of curvature. For a surface with
twice the local mean curvature $H = 1/R_1 +
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

## reviews (paragraph)

_(empty — run /review to populate)_
