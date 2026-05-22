% PREV: The second metric is the direction-averaged Cauchy formula~\eqref{eq:cauchy-exact}
% PREV: across $12$ directions and $2$ polarizations at $5.8$~GHz. The ratio
% PREV: of law to FDTD on direction-averaged total absorbed power is
% PREV: $1.012$, with $\Aab/A = 0.865$ and $\Tbar(f)$ from \cref{tab:Tbar}.
% PREV: \Cref{fig:val-fdtd} extends the comparison
% PREV: across $0.45$--$5.8$~GHz.
% NEXT: The closed-form Cauchy prediction approaches unity at the upper end
% NEXT: of the band. Below $6$~GHz the surface law underestimates because
% NEXT: body-scale Mie and resonance effects do not enter a surface-only law,
% NEXT: in line with the Mie analysis on a sphere of comparable size
% NEXT: parameter.
\begin{figure}[!t]
  \centering
  \includegraphics[width=\columnwidth]{fig_kernels_vs_fdtd.pdf}
  \caption{Closed-form prediction versus Sim4Life FDTD on the
  Thelonious phantom. Twelve directions and two polarizations per
  frequency from $0.45$--$5.8$~GHz; error bars show the spread
  across directions. The kernel curves switch on the corrections of
  \cref{subsec:corr-residuals} in sequence: ``Fresnel only'' uses
  $T_s/T_p$ at the convex limit, ``+ polarization'' adds the
  polarization-aware $\Teff$, ``+ curvature \& diffraction'' adds
  the $1/(kR)$ refinement, ``Full kernel'' is the constant-$T_0$
  geometric law without occlusion, ``Full + occlusion'' multiplies
  by $\Vis(\rr,\khat)$. The Cauchy stars are the closed-form
  whole-body identity, giving $1.012$ at $5.8$~GHz. The layered
  $\Tlay$ of \cref{subsec:fp} recovers the
  sub-$6$~GHz dip qualitatively.}
  \label{fig:val-fdtd}
\end{figure}

## reviews (figure)



_PaperMaker9000 sweep — 1 flag(s) across 1 lens(es)._

- **figure** — 1 flag(s), 42 cleared:
    - `figures.conventions.axis_units` (high): `$P_{\mathrm{abs}}^{\mathrm{law}} / P_{\mathrm{abs}}^{\mathrm{FDTD}}$` -> Append a dimensionless unit marker to the y-axis label, e.g. add ' (1)' to match the parenthesised dimensionless convention used elsewhere in the paper (lit_waterfall y-axes).
    - _dismissed_ `BOOK_WSRA_figures.conventions.stand_alone`: Caption phrases (``Fresnel only'', ``Full kernel'') are obvious expansions of the legend abbreviations (Fresnel, Full); the mapping is unambiguous and forcing exact-match strings would only lengthen the legend without aiding clarity.
    - _dismissed_ `BOOK_WSRA_figures.conventions.storytelling_title`: The opening clause frames the comparison and the finding is delivered in the same caption ('giving $1.012$ at $5.8$~GHz', 'recovers the sub-$6$~GHz dip'); leading with a single numeric headline would over-simplify a five-curve diagnostic figure.
    - _dismissed_ `figures.wout_specifics.no_brand_names_in_figures`: Legend entries (Fresnel, + polar., + curv./diffr., Full, Full + occl., Cauchy formula) are descriptive scientific identifiers, not codebase names like the L3_Pabs/Lall_Pabs columns in the source script.

## grinder notes
- **label**: fig:val-fdtd
- **caption_preview**: Closed-form prediction versus Sim4Life FDTD on the Thelonious phantom. Twelve directions and two pol
