% PREV: Equation~\eqref{eq:geom-law} extends to a triangle mesh under
% PREV: multiple incident waves. Discretize the body into $M$ triangles. Row $j$ of
% PREV: $\mathbf{N} \in \mathbb{R}^{M\times 3}$ holds the outward unit
% PREV: normal $\nhat_j$. Let $N$ plane waves arrive with unit directions
% PREV: $\khat_1, \ldots, \khat_N$ and power densities $S_1, \ldots, S_N$.
% PREV: Stack the directions column-wise into
% PREV: $\mathbf{K} \in \mathbb{R}^{3\times N}$, with column $i$ equal to
% PREV: $-\khat_i$. Stack the powers into
% PREV: $\mathbf{s} = [S_1,\ldots,S_N]^\top \in \mathbb{R}^N$. Let
% PREV: $\mathbf{V} \in \{0,1\}^{M\times N}$ be the visibility matrix, with
% PREV: $V_{ji} = 1$ when direction $\khat_i$ reaches triangle $j$, and
% PREV: $V_{ji} = 0$ otherwise. Collect the per-triangle APD values into
% PREV: $\bm{\mathrm{APD}} \in \mathbb{R}^{M}$.
% NEXT: Each step is differentiable. The operator $\pospart{\cdot}$ is the
% NEXT: rectified linear unit (ReLU). Replacing it with the smooth
% NEXT: \gls{GELU} activation~\cite{Hendrycks2016} leaves the structure
% NEXT: intact and replaces the hard cutoff with a soft rolloff
% NEXT: (\cref{eq:gelu}). Gradients of regulatory quantities with respect to
% NEXT: antenna positions, antenna orientations, and RIS phases propagate
% NEXT: through any differentiable ray tracer~\cite{SionnaRT}. The arithmetic
% NEXT: primitive is the per-pixel shading operation that consumer GPUs run
% NEXT: at sub-millisecond rates, with the cosine gate as rectified shading
% NEXT: and $\mathbf{V}$ as ambient occlusion. For $M \approx 10^4$ and
% NEXT: $N \approx 10^2$, the spatial map is one matrix-vector multiply on
% NEXT: the GPU.
The geometric law on the mesh then reads
\begin{equation}\label{eq:mat-multi}
  \bm{\mathrm{APD}} = T_0\,\bigl(\pospart{\mathbf{N}\,\mathbf{K}}
  \odot \mathbf{V}\bigr)\,\mathbf{s}\, .
\end{equation}
The cosine matrix $\mathbf{N}\,\mathbf{K} \in \mathbb{R}^{M\times N}$
has entry $(j,i)$ equal to $\nhat_j\cdot(-\khat_i)$. The operator
$\pospart{\cdot} \equiv \max(\cdot,0)$ acts componentwise, and clamps
back-facing entries to zero. The Hadamard product $\odot$ with
$\mathbf{V}$ gates self-shadowed entries. The product with
$\mathbf{s}$ sums the contributions of the $N$ incident waves.

## reviews (paragraph)



_PaperMaker9000 sweep — all clear across 4 lens(es)._

- **sentence-craft** — pass (14 rules cleared).
- **voice-tells** — pass (22 rules cleared).
- **lexical-spotcheck** — pass (54 rules cleared).
- **latex-micro** — pass (41 rules cleared).
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

