% PREV: Equation~\eqref{eq:geom-law} extends to a triangle mesh under
% NEXT: Each step is differentiable.
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

