% PREV: \subsection{Higher-order corrections}\label{subsec:corr-residuals}
% NEXT: First, we examine the influence of curvature. For a surface with
% NEXT: twice the local mean curvature $H = 1/R_1 +
% NEXT: 1/R_2$, the first-order Physical Optics correction multiplies the
% NEXT: geometric law by $1 + \mu/(kR_1) + \mu/(kR_2)$, where
% NEXT: $k = 2\pi/\lambda$ is the free-space wavenumber. Since
% NEXT: $\pospart{\mu}\cdot\mu = \pospart{\mu}^2$, the per-triangle update
% NEXT: separates additively,
% NEXT: \begin{equation}\label{eq:curv-update}
% NEXT:   \APD^{(j)} = T_0 \sum_i S_i\!\left[
% NEXT:   \pospart{\mu_{ji}} + \frac{H_j}{k}\,\pospart{\mu_{ji}}^2 \right]
% NEXT:   V_{ji}\, ,
% NEXT: \end{equation}
% NEXT: adding a quadratic gate on top of the linear one. The magnitude is
% NEXT: set by $1/(kR)$. \Cref{tab:curv-mag} lists the correction at
% NEXT: $28$~GHz on representative body parts.
The correction box in the flowchart collects the effects left out by
the geometric law. We treat them in turn: curvature, diffraction at
the shadow boundary, and inter-body reflections. The kernel labels in
\cref{fig:val-fdtd} (``Fresnel only,'' ``+ polarization,'' ``+
curvature \& diffraction,'' ``Full kernel,'' ``+ occlusion'') switch
each correction on against the same FDTD reference.

## reviews (paragraph)



_PaperMaker9000 sweep — 2 flag(s) across 4 lens(es)._

- **sentence-craft** — 1 flag(s), 13 cleared:
    - `style.positive_voice.no_passive_no_we` (high): `We treat them in turn: curvature, diffraction at the shadow boundary, and inter-body reflections.` -> Recast subject-first without we: "Three corrections follow in turn: curvature, diffraction at the shadow boundary, and inter-body reflections."
- **voice-tells** — 1 flag(s), 21 cleared:
    - `style.pet_peeves_wout.tilde_spacing` (high): `The kernel labels in \cref{fig:val-fdtd}` -> Use a non-breaking tie before the cross-reference: "labels in~\cref{fig:val-fdtd}".
- **lexical-spotcheck** — pass (54 rules cleared).
- **latex-micro** — pass (41 rules cleared).
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

