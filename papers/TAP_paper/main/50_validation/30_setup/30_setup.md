% PREV: Thelonious is a 6-year-old male phantom from the Virtual
# Setup

<!-- AUTO_BEGIN: assembled -->
% NEXT: Thelonious is a 6-year-old male phantom from the Virtual
\subsection{Configuration}\label{subsec:val-setup}

% PREV: \subsection{Configuration}\label{subsec:val-setup}
% NEXT: # Setup
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
<!-- AUTO_END: assembled -->





## section notes

_(AI-owned notes about this section as a whole)_
