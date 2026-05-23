% PREV: \subsection{Discrete multi-source form}\label{subsec:matrix}
% NEXT: The geometric law on the mesh then reads
% NEXT: \begin{equation}\label{eq:mat-multi}
% NEXT:   \bm{\mathrm{APD}} = T_0\,\bigl(\pospart{\mathbf{N}\,\mathbf{K}}
% NEXT:   \odot \mathbf{V}\bigr)\,\mathbf{s}\, .
% NEXT: \end{equation}
% NEXT: The cosine matrix $\mathbf{N}\,\mathbf{K} \in \mathbb{R}^{M\times N}$
% NEXT: has entry $(j,i)$ equal to $\nhat_j\cdot(-\khat_i)$. The operator
% NEXT: $\pospart{\cdot} \equiv \max(\cdot,0)$ acts componentwise, and clamps
% NEXT: back-facing entries to zero. The Hadamard product $\odot$ with
% NEXT: $\mathbf{V}$ gates self-shadowed entries. The product with
% NEXT: $\mathbf{s}$ sums the contributions of the $N$ incident waves.
Equation~\eqref{eq:geom-law} extends to a triangle mesh under
multiple incident waves. Discretize the body into $M$ triangles. Row $j$ of
$\mathbf{N} \in \mathbb{R}^{M\times 3}$ holds the outward unit
normal $\nhat_j$. Let $N$ plane waves arrive with unit directions
$\khat_1, \ldots, \khat_N$ and incident power densities
$\IPD_1, \ldots, \IPD_N$.
Stack the directions column-wise into
$\mathbf{K} \in \mathbb{R}^{3\times N}$, with column $i$ equal to
$-\khat_i$. Stack the incident power densities into
$\bm{\mathrm{IPD}} = [\IPD_1,\ldots,\IPD_N]^\top \in \mathbb{R}^N$. Let
$\mathbf{V} \in \{0,1\}^{M\times N}$ be the visibility matrix, with
$V_{ji} = 1$ when direction $\khat_i$ reaches triangle $j$, and
$V_{ji} = 0$ otherwise. Collect the per-triangle APD values into
$\bm{\mathrm{APD}} \in \mathbb{R}^{M}$.

## reviews (paragraph)



_PaperMaker9000 sweep — 1 flag(s) across 4 lens(es)._

- **sentence-craft** — pass (14 rules cleared).
- **voice-tells** — pass (22 rules cleared).
- **lexical-spotcheck** — pass (54 rules cleared).
- **latex-micro** — 1 flag(s), 40 cleared:
    - `latex.math.vector_matrix_bold_consistent` (high): `\bm{\mathrm{APD}} \in \mathbb{R}^{M}` -> Set the APD vector with the same macro as the other vectors/matrices: \mathbf{\mathrm{APD}} to match \mathbf{N}, \mathbf{K}, \mathbf{s}, \mathbf{V}.
    - _dismissed_ `latex.substitutions.vector_bold_convention_documented`: APD is a vector in the same category as \mathbf{s}, so this is plain macro inconsistency captured by vector_matrix_bold_consistent, not an intentional documented category split.
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

