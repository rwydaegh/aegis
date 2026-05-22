% PREV: \begin{figure}[!t]
% PREV:   \centering
% PREV:   \begin{tikzpicture}[
% PREV:     every node/.style={font=\footnotesize},
% PREV:     box/.style={draw=black, line width=0.5pt, rectangle,
% PREV:                 inner sep=2pt, minimum height=9mm, minimum width=33mm,
% PREV:                 fill=white, align=center, font=\footnotesize},
% PREV:     sub6/.style={draw=black, line width=0.5pt, rectangle,
% PREV:                 inner sep=2pt, minimum height=8mm, minimum width=28mm,
% PREV:                 fill=black!4, align=center, font=\footnotesize},
% PREV:     outbox/.style={draw=black, line width=0.5pt, rectangle,
% PREV:                 inner sep=2pt, minimum height=9mm, minimum width=30mm,
% PREV:                 align=center, font=\footnotesize},
% PREV:     smallout/.style={draw=black, line width=0.4pt, rectangle,
% PREV:                 inner sep=1.5pt, minimum height=5mm, minimum width=24mm,
% PREV:                 align=center, font=\scriptsize},
% PREV:     inputs/.style={draw=black, line width=0.4pt, rectangle, dashed,
% PREV:                 inner sep=4pt, text width=25mm, align=left,
% PREV:                 font=\footnotesize, fill=white},
% PREV:     corrbox/.style={draw=black, line width=0.4pt, rectangle, dashed,
% PREV:                 inner sep=2.5pt, text width=29mm, align=center,
% PREV:                 font=\scriptsize\itshape, fill=white},
% PREV:     arrow/.style={->, line width=0.45pt, >=Latex},
% PREV:     smallarrow/.style={->, line width=0.4pt, >=Latex,
% PREV:                 rounded corners=0.6pt},
% PREV:     tag/.style={font=\scriptsize\itshape, align=center,
% PREV:                 fill=white, inner sep=0.6pt}
% PREV:   ]
% PREV:     % Spine
% PREV:     \node[box] (exact) at (1.5, 0)     {Exact law\\$\APD\!=\!\IPD\,T_{\mathrm{eff}}\,\pospart{\mu}\,\Vis$};
% PREV:     \node[box] (avg)   at (1.5, -1.30) {Unpolarized\\$\APD\!=\!\IPD\,\Tavg\,\pospart{\mu}\,\Vis$};
% PREV:     \node[box] (geom)  at (1.5, -2.65) {Geometric\\$\APD\!=\!\IPD\,T_0\,\pospart{\mu}\,\Vis$};
% PREV:     \node[box] (whole) at (1.5, -5.85) {Whole-body\\$\langle P_{\mathrm{abs}}\rangle\!=\!\IPD\,\Tbar\,\Aab/4$};
% PREV: 
% PREV:     % Sub-6 GHz inside Formula
% PREV:     \node[sub6] (layered) at (2.25, -4.30) {Sub-6\,GHz\\$T_0\!\to\!\Tlay(f)$};
% PREV: 
% PREV:     % Outputs
% PREV:     \node[outbox, fill=outA] (outLocal) at (6.5, -2.65) {Local $\APDAvg$};
% PREV:     \node[smallout, fill=outA!60] (outLocalPeak) at (6.75, -3.42) {Peak $\APDAvg$};
% PREV:     \node[outbox, fill=outC] (outCube) at (6.5, -4.30) {$\mathrm{SAR}_{10\mathrm{g}}$};
% PREV:     \node[smallout, fill=outC!60] (outCubePeak) at (6.75, -5.07) {$\mathrm{psSAR}_{10\mathrm{g}}$};
% PREV:     \node[outbox, fill=outB] (outWB) at (6.5, -5.85) {$\mathrm{SAR}_{\mathrm{wb}}$};
% PREV: 
% PREV:     % Spine arrows top three
% PREV:     \draw[arrow] (exact) -- node[tag,right=2pt] {Three conditions} (avg);
% PREV:     \draw[arrow] (avg)   -- node[tag,right=2pt] {Pseudo-Brewster}   (geom);
% PREV: 
% PREV:     % Geom -> Whole at 1/4 width
% PREV:     \coordinate (geom_q1) at ($(geom.south west)!0.25!(geom.south east)$);
% PREV:     \coordinate (whole_q1) at ($(whole.north west)!0.25!(whole.north east)$);
% PREV:     \draw[arrow] (geom_q1) -- node[tag,pos=0.18] {Cauchy + occl.} (whole_q1);
% PREV: 
% PREV:     % Geom -> Sub-6 GHz, drawn straight vertically above the Sub-6 GHz box
% PREV:     \draw[arrow] (geom.south -| layered.north) -- (layered.north);
% PREV: 
% PREV:     % Horizontal east-west arrows
% PREV:     \draw[arrow] (geom.east)    -- (outLocal.west);
% PREV:     \draw[arrow] (layered.east) -- (outCube.west);
% PREV:     \draw[arrow] (whole.east)   -- (outWB.west);
% PREV: 
% PREV:     % Elbow refinement arrows
% PREV:     \draw[smallarrow] ($(outLocal.south west) + (1.5mm,0)$) |- (outLocalPeak.west);
% PREV:     \draw[smallarrow] ($(outCube.south west)  + (1.5mm,0)$) |- (outCubePeak.west);
% PREV: 
% PREV:     % Formula and Outputs dashed groups
% PREV:     \begin{pgfonlayer}{background}
% PREV:       \node[draw=black, line width=0.4pt, dashed,
% PREV:             fit=(exact)(whole)(layered),
% PREV:             inner sep=4pt,
% PREV:             name=formulabox,
% PREV:             label={[font=\scriptsize\itshape, anchor=center, fill=white, inner sep=1pt]north:Formula}] {};
% PREV:       \node[draw=black, line width=0.4pt, dashed,
% PREV:             fit=(outLocal)(outLocalPeak)(outCube)(outCubePeak)(outWB),
% PREV:             inner sep=4pt,
% PREV:             label={[font=\scriptsize\itshape, anchor=center, fill=white, inner sep=1pt]north:Regulatory outputs}] {};
% PREV:     \end{pgfonlayer}
% PREV: 
% PREV:     % Inputs box
% PREV:     \node[inputs, label={[font=\scriptsize\itshape, anchor=center, fill=white, inner sep=1pt]north:Inputs}] (inp) at (6.5, -0.85) {%
% PREV:       Tissue $\varepsilon$, $\mu$\\
% PREV:       Normals $\nhat$\\
% PREV:       Direction $\khat$\\
% PREV:       Visibility $\Vis$\\
% PREV:       Power $\IPD$};
% PREV: 
% PREV:     % Inputs -> Formula
% PREV:     \draw[arrow] (inp.west) -- (formulabox.east |- inp);
% PREV: 
% PREV:     % Corrections box and curved arrow
% PREV:     \node[corrbox] (corr) at (6.5, 0.85)
% PREV:       {+ Corrections for curvature,\\diffraction, inter-body};
% PREV:     \draw[arrow] (formulabox.north east) to[bend left=20] (corr.west);
% PREV:   \end{tikzpicture}
% PREV:   \caption{Flowchart of our approach. The formula has five inputs. Three
% PREV:   reductions take the exact law to a whole-body identity. Each arrow
% PREV:   is one reduction, justified in
% PREV:   \cref{subsec:exact-law,sec:pB,subsec:cauchy-thm}. A sub-6~GHz
% PREV:   branch replaces $T_0$ with a layered transmission $\Tlay(f)$
% PREV:   (\cref{subsec:fp}). Higher-order corrections are bounded errors on
% PREV:   the chain (\cref{subsec:corr-residuals}). The chain has three regulatory
% PREV:   outputs: surface-averaged absorbed power density $\APDAvg$,
% PREV:   peak-spatial SAR in a $10$~g cube $\mathrm{psSAR}_{10\mathrm{g}}$,
% PREV:   and whole-body SAR $\mathrm{SAR}_{\mathrm{wb}}$. Smaller boxes are the peak-spatial versions
% PREV:   used by ICNIRP (\cref{sec:compliance}).}
% PREV:   \label{fig:flowchart}
% PREV: \end{figure}
\begin{figure}[!t]
  \centering
  \includegraphics[width=\columnwidth]{fig_geometry.pdf}
  \caption{Configuration of the dosimetry problem. A plane wave with
  intensity $\IPD$ and direction $\hat{\bm{k}}$ illuminates the
  Thelonious phantom. The local APD at a visible
  surface point is $\APD = \IPD\,T(\theta)\cos\theta$, with $\theta$
  the angle between $-\hat{\bm{k}}$ and the outward normal
  $\hat{\bm{n}}$ on the triangulated body surface, and $T$ the
  Fresnel transmission.}
  \label{fig:configuration}
\end{figure}

## reviews (figure)



_PaperMaker9000 sweep — all clear across 1 lens(es)._

- **figure** — pass (43 rules cleared).
    - _dismissed_ `figures.visual_quality.minimalistic_academic_style`: These are privacy redactions on a child anthropomorphic phantom, a legitimate non-decorative element, not chartjunk/decoration the rule targets; removing them would not improve the figure.

## grinder notes
- **label**: fig:configuration
- **caption_preview**: Configuration of the dosimetry problem. A plane wave with intensity $\IPD$ and direction $\hat{\bm{k
