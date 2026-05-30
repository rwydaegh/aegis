% NEXT: Equation~\eqref{eq:geom-law} extends to a triangle mesh under
% NEXT: multiple incident waves. Discretize the body into $M$ triangles. Row $j$ of
% NEXT: $\mathbf{N} \in \mathbb{R}^{M\times 3}$ holds the outward unit
% NEXT: normal $\nhat_j$. Let $N$ plane waves arrive with unit directions
% NEXT: $\khat_1, \ldots, \khat_N$ and power densities $S_1, \ldots, S_N$.
% NEXT: Stack the directions column-wise into
% NEXT: $\mathbf{K} \in \mathbb{R}^{3\times N}$, with column $i$ equal to
% NEXT: $-\khat_i$. Stack the powers into
% NEXT: $\mathbf{s} = [S_1,\ldots,S_N]^\top \in \mathbb{R}^N$. Let
% NEXT: $\mathbf{V} \in \{0,1\}^{M\times N}$ be the visibility matrix, with
% NEXT: $V_{ji} = 1$ when direction $\khat_i$ reaches triangle $j$, and
% NEXT: $V_{ji} = 0$ otherwise. Collect the per-triangle APD values into
% NEXT: $\bm{\mathrm{APD}} \in \mathbb{R}^{M}$.
\subsection{Discrete multi-source form}\label{subsec:matrix}

## reviews (subsection_header)

_(empty — run /review to populate)_
