% PREV: \subsection{Configuration}\label{subsec:val-setup}
Thelonious is a 6-year-old male phantom from the Virtual
Population~\cite{ITISv5}, shown in \cref{fig:phantom}. The surface is
a high-resolution triangle mesh with $23{,}826$ faces. Tissue
properties at every frequency follow the tissue-properties
database~\cite{ITISv5,Gabriel1996}. Mie
benchmarks use lossy spheres of skin permittivity at the listed
frequencies, evaluated with the standard recursive series of Bohren
and Huffman~\cite{BohrenHuffman1983}. Sim4Life FDTD runs use the
$0.45$--$5.8$~GHz band on the same Thelonious mesh embedded in a
free-space cube with a perfectly matched layer of $10$ cells, voxel
edge of $1$~mm in the body and graded $1$--$4$~mm outside, and
$12$ plane-wave directions per frequency at two orthogonal
polarizations. Path-level data come from a differentiable
ray-tracer~\cite{SionnaRT} with no roughness model. All scripts and
input geometries that produced the figures in this section are in the
companion code release.

## reviews (paragraph)



_PaperMaker9000 sweep — 2 flag(s) across 4 lens(es)._

- **sentence-craft** — 1 flag(s), 13 cleared:
    - `style.positive_voice.subject_verb_early` (medium): `All scripts and input geometries that produced the figures in this section are in the companion code release.` -> The companion code release contains all scripts and input geometries that produced the figures in this section.
- **voice-tells** — 1 flag(s), 21 cleared:
    - `style.pet_peeves_wout.tilde_spacing` (high): `free-space cube with a perfectly matched layer of $10$ cells, voxel` -> Tie numbers to their referents: 'layer of~$10$ cells', and likewise 'with~$23{,}826$ faces', 'use the~$0.45$--$5.8$', 'edge of~$1$~mm', 'graded~$1$--$4$~mm', 'and~$12$ plane-wave directions' (Wout applies ~ before nearly every number).
- **lexical-spotcheck** — pass (54 rules cleared).
- **latex-micro** — pass (41 rules cleared).
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

