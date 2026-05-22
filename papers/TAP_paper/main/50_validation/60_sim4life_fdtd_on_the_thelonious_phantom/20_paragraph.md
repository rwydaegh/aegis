% PREV: The Mie and Fresnel tests check approximations against analytic and
% PREV: semi-analytic ground truths. Full Sim4Life FDTD on the same
% PREV: Thelonious mesh, matched dielectric properties, and matched
% PREV: plane-wave excitation completes the comparison. Two regulatory
% PREV: metrics are evaluated. The first is the IEC/IEEE~63195 peak $\APD$
% PREV: averaged over a $4$~cm$^2$ patch. At $7$~GHz on three
% PREV: lateral and frontal incidence directions with $\theta$-polarization,
% PREV: the direction-averaged ratio of law to FDTD is $1.027$. A
% PREV: $\pm 20\%$ uncertainty on the IT'IS dielectric properties~\cite{ITISv5,Gabriel1996} propagates
% PREV: through the Fresnel coefficient at $7$~GHz to $\pm 7\%$ on
% PREV: $T_0$. The direction-averaged ratio falls inside this band. The
% PREV: per-direction values are $1.06$, $1.20$, and $0.83$. The spread
% PREV: beyond $\pm 7\%$ comes from FDTD discretization and per-direction
% PREV: polarization detail in the reference, not the closed form.
% NEXT: \begin{figure}[!t]
% NEXT:   \centering
% NEXT:   \includegraphics[width=\columnwidth]{fig_kernels_vs_fdtd.pdf}
% NEXT:   \caption{Closed-form prediction versus Sim4Life FDTD on the
% NEXT:   Thelonious phantom. Twelve directions and two polarizations per
% NEXT:   frequency from $0.45$--$5.8$~GHz; error bars show the spread
% NEXT:   across directions. The kernel curves switch on the corrections of
% NEXT:   \cref{subsec:corr-residuals} in sequence: ``Fresnel only'' uses
% NEXT:   $T_s/T_p$ at the convex limit, ``+ polarization'' adds the
% NEXT:   polarization-aware $\Teff$, ``+ curvature \& diffraction'' adds
% NEXT:   the $1/(kR)$ refinement, ``Full kernel'' is the constant-$T_0$
% NEXT:   geometric law without occlusion, ``Full + occlusion'' multiplies
% NEXT:   by $\Vis(\rr,\khat)$. The Cauchy stars are the closed-form
% NEXT:   whole-body identity, giving $1.012$ at $5.8$~GHz. The layered
% NEXT:   $\Tlay$ of \cref{subsec:fp} recovers the
% NEXT:   sub-$6$~GHz dip qualitatively.}
% NEXT:   \label{fig:val-fdtd}
% NEXT: \end{figure}
The second metric is the direction-averaged Cauchy formula~\eqref{eq:cauchy-exact}
across $12$ directions and $2$ polarizations at $5.8$~GHz. The ratio
of law to FDTD on direction-averaged total absorbed power is
$1.012$, with $\Aab/A = 0.865$ and $\Tbar(f)$ from \cref{tab:Tbar}.
\Cref{fig:val-fdtd} extends the comparison
across $0.45$--$5.8$~GHz. The closed-form Cauchy prediction approaches
unity at the upper end of the band. Below $6$~GHz the surface law
underestimates because body-scale Mie and resonance effects do not
enter a surface-only law, in line with the Mie analysis on a sphere of
comparable size parameter.

## reviews (paragraph)



_PaperMaker9000 sweep — 1 flag(s) across 4 lens(es)._

- **sentence-craft** — 1 flag(s), 13 cleared:
    - `style.positive_voice.subject_verb_early` (medium): `The ratio of law to FDTD on direction-averaged total absorbed power is $1.012$` -> Front-load the verb: "Law matches FDTD on direction-averaged total absorbed power to within a ratio of $1.012$, with ..."
- **voice-tells** — pass (22 rules cleared).
- **lexical-spotcheck** — pass (54 rules cleared).
- **latex-micro** — pass (41 rules cleared).
    - _dismissed_ `latex.spacing_ties.inter_sentence_spacing`: Sentence ends on the capital abbreviation GHz, but the canonical fix is a global \frenchspacing in the preamble (one decision), not per-leaf \@. insertions; not a leaf-level defect.
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

