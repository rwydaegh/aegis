% PREV: \section{Method: local absorption law}\label{sec:law}
% NEXT: \begin{figure}[!t]
% NEXT:   \centering
% NEXT:   \begin{tikzpicture}[
% NEXT:     every node/.style={font=\footnotesize},
% NEXT:     box/.style={draw=black, line width=0.5pt, rectangle,
% NEXT:                 inner sep=2pt, minimum height=9mm, minimum width=33mm,
% NEXT:                 fill=white, align=center, font=\footnotesize},
% NEXT:     sub6/.style={draw=black, line width=0.5pt, rectangle,
% NEXT:                 inner sep=2pt, minimum height=8mm, minimum width=28mm,
% NEXT:                 fill=black!4, align=center, font=\footnotesize},
% NEXT:     outbox/.style={draw=black, line width=0.5pt, rectangle,
% NEXT:                 inner sep=2pt, minimum height=9mm, minimum width=30mm,
% NEXT:                 align=center, font=\footnotesize},
% NEXT:     smallout/.style={draw=black, line width=0.4pt, rectangle,
% NEXT:                 inner sep=1.5pt, minimum height=5mm, minimum width=24mm,
% NEXT:                 align=center, font=\scriptsize},
% NEXT:     inputs/.style={draw=black, line width=0.4pt, rectangle, dashed,
% NEXT:                 inner sep=4pt, text width=25mm, align=left,
% NEXT:                 font=\footnotesize, fill=white},
% NEXT:     corrbox/.style={draw=black, line width=0.4pt, rectangle, dashed,
% NEXT:                 inner sep=2.5pt, text width=29mm, align=center,
% NEXT:                 font=\scriptsize\itshape, fill=white},
% NEXT:     arrow/.style={->, line width=0.45pt, >=Latex},
% NEXT:     smallarrow/.style={->, line width=0.4pt, >=Latex,
% NEXT:                 rounded corners=0.6pt},
% NEXT:     tag/.style={font=\scriptsize\itshape, align=center,
% NEXT:                 fill=white, inner sep=0.6pt}
% NEXT:   ]
% NEXT:     % Spine
% NEXT:     \node[box] (exact) at (1.5, 0)     {Exact law\\$\APD\!=\!\IPD\,T_{\mathrm{eff}}\,\pospart{\mu}\,\Vis$};
% NEXT:     \node[box] (avg)   at (1.5, -1.30) {Unpolarized\\$\APD\!=\!\IPD\,\Tavg\,\pospart{\mu}\,\Vis$};
% NEXT:     \node[box] (geom)  at (1.5, -2.65) {Geometric\\$\APD\!=\!\IPD\,T_0\,\pospart{\mu}\,\Vis$};
% NEXT:     \node[box] (whole) at (1.5, -5.85) {Whole-body\\$\langle P_{\mathrm{abs}}\rangle\!=\!\IPD\,\Tbar\,\Aab/4$};
% NEXT: 
% NEXT:     % Sub-6 GHz inside Formula
% NEXT:     \node[sub6] (layered) at (2.25, -4.30) {Sub-6\,GHz\\$T_0\!\to\!\Tlay(f)$};
% NEXT: 
% NEXT:     % Outputs
% NEXT:     \node[outbox, fill=outA] (outLocal) at (6.5, -2.65) {Local $\APDAvg$};
% NEXT:     \node[smallout, fill=outA!60] (outLocalPeak) at (6.75, -3.42) {Peak $\APDAvg$};
% NEXT:     \node[outbox, fill=outC] (outCube) at (6.5, -4.30) {$\mathrm{SAR}_{10\mathrm{g}}$};
% NEXT:     \node[smallout, fill=outC!60] (outCubePeak) at (6.75, -5.07) {$\mathrm{psSAR}_{10\mathrm{g}}$};
% NEXT:     \node[outbox, fill=outB] (outWB) at (6.5, -5.85) {$\mathrm{SAR}_{\mathrm{wb}}$};
% NEXT: 
% NEXT:     % Spine arrows top three
% NEXT:     \draw[arrow] (exact) -- node[tag,right=2pt] {Three conditions} (avg);
% NEXT:     \draw[arrow] (avg)   -- node[tag,right=2pt] {Pseudo-Brewster}   (geom);
% NEXT: 
% NEXT:     % Geom -> Whole at 1/4 width
% NEXT:     \coordinate (geom_q1) at ($(geom.south west)!0.25!(geom.south east)$);
% NEXT:     \coordinate (whole_q1) at ($(whole.north west)!0.25!(whole.north east)$);
% NEXT:     \draw[arrow] (geom_q1) -- node[tag,pos=0.18] {Cauchy + occl.} (whole_q1);
% NEXT: 
% NEXT:     % Geom -> Sub-6 GHz, drawn straight vertically above the Sub-6 GHz box
% NEXT:     \draw[arrow] (geom.south -| layered.north) -- (layered.north);
% NEXT: 
% NEXT:     % Horizontal east-west arrows
% NEXT:     \draw[arrow] (geom.east)    -- (outLocal.west);
% NEXT:     \draw[arrow] (layered.east) -- (outCube.west);
% NEXT:     \draw[arrow] (whole.east)   -- (outWB.west);
% NEXT: 
% NEXT:     % Elbow refinement arrows
% NEXT:     \draw[smallarrow] ($(outLocal.south west) + (1.5mm,0)$) |- (outLocalPeak.west);
% NEXT:     \draw[smallarrow] ($(outCube.south west)  + (1.5mm,0)$) |- (outCubePeak.west);
% NEXT: 
% NEXT:     % Formula and Outputs dashed groups
% NEXT:     \begin{pgfonlayer}{background}
% NEXT:       \node[draw=black, line width=0.4pt, dashed,
% NEXT:             fit=(exact)(whole)(layered),
% NEXT:             inner sep=4pt,
% NEXT:             name=formulabox,
% NEXT:             label={[font=\scriptsize\itshape, anchor=center, fill=white, inner sep=1pt]north:Formula}] {};
% NEXT:       \node[draw=black, line width=0.4pt, dashed,
% NEXT:             fit=(outLocal)(outLocalPeak)(outCube)(outCubePeak)(outWB),
% NEXT:             inner sep=4pt,
% NEXT:             label={[font=\scriptsize\itshape, anchor=center, fill=white, inner sep=1pt]north:Regulatory outputs}] {};
% NEXT:     \end{pgfonlayer}
% NEXT: 
% NEXT:     % Inputs box
% NEXT:     \node[inputs, label={[font=\scriptsize\itshape, anchor=center, fill=white, inner sep=1pt]north:Inputs}] (inp) at (6.5, -0.85) {%
% NEXT:       Tissue $\varepsilon$, $\mu$\\
% NEXT:       Normals $\nhat$\\
% NEXT:       Direction $\khat$\\
% NEXT:       Visibility $\Vis$\\
% NEXT:       Power $\IPD$};
% NEXT: 
% NEXT:     % Inputs -> Formula
% NEXT:     \draw[arrow] (inp.west) -- (formulabox.east |- inp);
% NEXT: 
% NEXT:     % Corrections box and curved arrow
% NEXT:     \node[corrbox] (corr) at (6.5, 0.85)
% NEXT:       {+ Corrections for curvature,\\diffraction, inter-body};
% NEXT:     \draw[arrow] (formulabox.north east) to[bend left=20] (corr.west);
% NEXT:   \end{tikzpicture}
% NEXT:   \caption{Flowchart of our approach. The formula has five inputs. Three
% NEXT:   reductions take the exact law to a whole-body identity. Each arrow
% NEXT:   is one reduction, justified in
% NEXT:   \cref{subsec:exact-law,sec:pB,subsec:cauchy-thm}. A sub-6~GHz
% NEXT:   branch replaces $T_0$ with a layered transmission $\Tlay(f)$
% NEXT:   (\cref{subsec:fp}). Higher-order corrections are bounded errors on
% NEXT:   the chain (\cref{subsec:corr-residuals}). The chain has three regulatory
% NEXT:   outputs: surface-averaged absorbed power density $\APDAvg$,
% NEXT:   peak-spatial SAR in a $10$~g cube $\mathrm{psSAR}_{10\mathrm{g}}$,
% NEXT:   and whole-body SAR $\mathrm{SAR}_{\mathrm{wb}}$. Smaller boxes are the peak-spatial versions
% NEXT:   used by ICNIRP (\cref{sec:compliance}).}
% NEXT:   \label{fig:flowchart}
% NEXT: \end{figure}
Flowchart \ref{fig:flowchart} shows the exact local law, the
reductions to whole-body absorbed power, the higher-order
corrections, and the regulatory outputs. This section derives the top
box: the local law at one visible surface point.

## reviews (paragraph)



_PaperMaker9000 sweep — 1 flag(s) across 4 lens(es)._

- **sentence-craft** — pass (14 rules cleared).
- **voice-tells** — 1 flag(s), 21 cleared:
    - `style.pet_peeves_wout.tilde_spacing` (high): `Flowchart \ref{fig:flowchart} shows` -> Use a non-breaking tie before the reference: Flowchart~\ref{fig:flowchart}.
- **lexical-spotcheck** — pass (54 rules cleared).
- **latex-micro** — pass (41 rules cleared).
    - _dismissed_ `latex.spacing_ties.tilde_before_refs`: The missing non-breaking tie before \ref is a real defect, but no canonical rule with this id exists in the latex-micro lens (the 41 rules cover tilde_number_unit and tilde_names only); the issue is flagged canonically under style.pet_peeves_wout.tilde_spacing in the voice-tells lens.
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

