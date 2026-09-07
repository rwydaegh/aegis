% PREV: The geometric law on the mesh then reads
% PREV: \begin{equation}\label{eq:mat-multi}
% PREV:   \bm{\mathrm{APD}} = T_0\,\bigl(\pospart{\mathbf{N}\,\mathbf{K}}
% PREV:   \odot \mathbf{V}\bigr)\,\bm{\mathrm{IPD}}\, .
% PREV: \end{equation}
% PREV: The cosine matrix $\mathbf{N}\,\mathbf{K} \in \mathbb{R}^{M\times N}$
% PREV: has entry $(j,i)$ equal to $\nhat_j\cdot(-\khat_i)$. The operator
% PREV: $\pospart{\cdot} \equiv \max(\cdot,0)$ acts componentwise, and clamps
% PREV: back-facing entries to zero. The Hadamard product $\odot$ with
% PREV: $\mathbf{V}$ gates self-shadowed entries. The product with
% PREV: $\bm{\mathrm{IPD}}$ sums the contributions of the $N$ incident waves.
Each step is differentiable almost everywhere. The operator $\pospart{\cdot}$ is the
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

## reviews (paragraph)



_PaperMaker9000 sweep — 1 flag(s) across 4 lens(es)._

- **sentence-craft** — 1 flag(s), 13 cleared:
    - `style.positive_voice.subject_verb_early` (medium): `Gradients of regulatory quantities with respect to antenna positions, antenna orientations, and RIS phases propagate through any differentiable ray tracer~\cite{SionnaRT}.` -> Move the qualification list after the verb: "Gradients of regulatory quantities propagate through any differentiable ray tracer, taken with respect to antenna positions, antenna orientations, and RIS phases."
- **voice-tells** — pass (22 rules cleared).
- **lexical-spotcheck** — pass (54 rules cleared).
- **latex-micro** — pass (41 rules cleared).
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).
