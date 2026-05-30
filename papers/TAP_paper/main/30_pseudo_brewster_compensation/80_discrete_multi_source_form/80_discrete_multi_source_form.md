% PREV: Each step is differentiable.
# Discrete multi-source form

<!-- AUTO_BEGIN: assembled -->
\subsection{Discrete multi-source form}\label{subsec:matrix}

Equation~\eqref{eq:geom-law} extends to a triangle mesh under
multiple incident waves. Discretize the body into $M$ triangles. Row $j$ of
$\mathbf{N} \in \mathbb{R}^{M\times 3}$ holds the outward unit
normal $\nhat_j$. Let $N$ plane waves arrive with unit directions
$\khat_1, \ldots, \khat_N$ and power densities $S_1, \ldots, S_N$.
Stack the directions column-wise into
$\mathbf{K} \in \mathbb{R}^{3\times N}$, with column $i$ equal to
$-\khat_i$. Stack the powers into
$\mathbf{s} = [S_1,\ldots,S_N]^\top \in \mathbb{R}^N$. Let
$\mathbf{V} \in \{0,1\}^{M\times N}$ be the visibility matrix, with
$V_{ji} = 1$ when direction $\khat_i$ reaches triangle $j$, and
$V_{ji} = 0$ otherwise. Collect the per-triangle APD values into
$\bm{\mathrm{APD}} \in \mathbb{R}^{M}$.

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

Each step is differentiable. The operator $\pospart{\cdot}$ is the
rectified linear unit (ReLU). Replacing it with the smooth
\gls{GELU} activation~\cite{Hendrycks2016} leaves the structure
intact and replaces the hard cutoff with a soft rolloff
(\cref{eq:gelu}). Gradients of regulatory quantities with respect to
antenna positions, antenna orientations, and RIS phases propagate
through any differentiable ray tracer~\cite{SionnaRT}. The arithmetic
primitive is the per-pixel shading operation that consumer GPUs run
at sub-millisecond rates, with the cosine gate as rectified shading
and $\mathbf{V}$ as ambient occlusion. For $M \approx 10^4$ and
$N \approx 10^2$, the spatial map is one matrix-vector multiply on
the GPU.
<!-- AUTO_END: assembled -->






## section notes

_(AI-owned notes about this section as a whole)_
