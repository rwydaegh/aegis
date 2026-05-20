% PREV: Flowchart \ref{fig:flowchart} shows the exact local law, the
% NEXT: \begin{figure}[!t]
\begin{figure}[!t]
  \centering
  \begin{tikzpicture}[
    every node/.style={font=\footnotesize},
    box/.style={draw=black, line width=0.5pt, rectangle,
                inner sep=2pt, minimum height=9mm, minimum width=33mm,
                fill=white, align=center, font=\footnotesize},
    sub6/.style={draw=black, line width=0.5pt, rectangle,
                inner sep=2pt, minimum height=8mm, minimum width=28mm,
                fill=black!4, align=center, font=\footnotesize},
    outbox/.style={draw=black, line width=0.5pt, rectangle,
                inner sep=2pt, minimum height=9mm, minimum width=30mm,
                align=center, font=\footnotesize},
    smallout/.style={draw=black, line width=0.4pt, rectangle,
                inner sep=1.5pt, minimum height=5mm, minimum width=24mm,
                align=center, font=\scriptsize},
    inputs/.style={draw=black, line width=0.4pt, rectangle, dashed,
                inner sep=4pt, text width=25mm, align=left,
                font=\footnotesize, fill=white},
    corrbox/.style={draw=black, line width=0.4pt, rectangle, dashed,
                inner sep=2.5pt, text width=29mm, align=center,
                font=\scriptsize\itshape, fill=white},
    arrow/.style={->, line width=0.45pt, >=Latex},
    smallarrow/.style={->, line width=0.4pt, >=Latex,
                rounded corners=0.6pt},
    tag/.style={font=\scriptsize\itshape, align=center,
                fill=white, inner sep=0.6pt}
  ]
    % Spine
    \node[box] (exact) at (1.5, 0)     {Exact law\\$\APD\!=\!\IPD\,T_{\mathrm{eff}}\,\pospart{\mu}\,\Vis$};
    \node[box] (avg)   at (1.5, -1.30) {Unpolarized\\$\APD\!=\!\IPD\,\Tavg\,\pospart{\mu}\,\Vis$};
    \node[box] (geom)  at (1.5, -2.65) {Geometric\\$\APD\!=\!\IPD\,T_0\,\pospart{\mu}\,\Vis$};
    \node[box] (whole) at (1.5, -5.85) {Whole-body\\$\langle P_{\mathrm{abs}}\rangle\!=\!\IPD\,\Tbar\,\Aab/4$};

    % Sub-6 GHz inside Formula
    \node[sub6] (layered) at (2.25, -4.30) {Sub-6\,GHz\\$T_0\!\to\!\Tlay(f)$};

    % Outputs
    \node[outbox, fill=outA] (outLocal) at (6.5, -2.65) {Local $\APDAvg$};
    \node[smallout, fill=outA!60] (outLocalPeak) at (6.75, -3.42) {Peak $\APDAvg$};
    \node[outbox, fill=outC] (outCube) at (6.5, -4.30) {$\mathrm{SAR}_{10\mathrm{g}}$};
    \node[smallout, fill=outC!60] (outCubePeak) at (6.75, -5.07) {$\mathrm{psSAR}_{10\mathrm{g}}$};
    \node[outbox, fill=outB] (outWB) at (6.5, -5.85) {$\mathrm{SAR}_{\mathrm{wb}}$};

    % Spine arrows top three
    \draw[arrow] (exact) -- node[tag,right=2pt] {Three conditions} (avg);
    \draw[arrow] (avg)   -- node[tag,right=2pt] {Pseudo-Brewster}   (geom);

    % Geom -> Whole at 1/4 width
    \coordinate (geom_q1) at ($(geom.south west)!0.25!(geom.south east)$);
    \coordinate (whole_q1) at ($(whole.north west)!0.25!(whole.north east)$);
    \draw[arrow] (geom_q1) -- node[tag,pos=0.18] {Cauchy + occl.} (whole_q1);

    % Geom -> Sub-6 GHz, drawn straight vertically above the Sub-6 GHz box
    \draw[arrow] (geom.south -| layered.north) -- (layered.north);

    % Horizontal east-west arrows
    \draw[arrow] (geom.east)    -- (outLocal.west);
    \draw[arrow] (layered.east) -- (outCube.west);
    \draw[arrow] (whole.east)   -- (outWB.west);

    % Elbow refinement arrows
    \draw[smallarrow] ($(outLocal.south west) + (1.5mm,0)$) |- (outLocalPeak.west);
    \draw[smallarrow] ($(outCube.south west)  + (1.5mm,0)$) |- (outCubePeak.west);

    % Formula and Outputs dashed groups
    \begin{pgfonlayer}{background}
      \node[draw=black, line width=0.4pt, dashed,
            fit=(exact)(whole)(layered),
            inner sep=4pt,
            name=formulabox,
            label={[font=\scriptsize\itshape, anchor=center, fill=white, inner sep=1pt]north:Formula}] {};
      \node[draw=black, line width=0.4pt, dashed,
            fit=(outLocal)(outLocalPeak)(outCube)(outCubePeak)(outWB),
            inner sep=4pt,
            label={[font=\scriptsize\itshape, anchor=center, fill=white, inner sep=1pt]north:Regulatory outputs}] {};
    \end{pgfonlayer}

    % Inputs box
    \node[inputs, label={[font=\scriptsize\itshape, anchor=center, fill=white, inner sep=1pt]north:Inputs}] (inp) at (6.5, -0.85) {%
      Tissue $\varepsilon$, $\mu$\\
      Normals $\nhat$\\
      Direction $\khat$\\
      Visibility $\Vis$\\
      Power $\IPD$};

    % Inputs -> Formula
    \draw[arrow] (inp.west) -- (formulabox.east |- inp);

    % Corrections box and curved arrow
    \node[corrbox] (corr) at (6.5, 0.85)
      {+ Corrections for curvature,\\diffraction, inter-body};
    \draw[arrow] (formulabox.north east) to[bend left=20] (corr.west);
  \end{tikzpicture}
  \caption{Flowchart of our approach. The formula has five inputs. Three
  reductions take the exact law to a whole-body identity. Each arrow
  is one reduction, justified in
  \cref{subsec:exact-law,sec:pB,subsec:cauchy-thm}. A sub-6~GHz
  branch replaces $T_0$ with a layered transmission $\Tlay(f)$
  (\cref{subsec:fp}). Higher-order corrections are bounded errors on
  the chain (\cref{subsec:corr-residuals}). The chain has three regulatory
  outputs: surface-averaged absorbed power density $\APDAvg$,
  peak-spatial SAR in a $10$~g cube $\mathrm{psSAR}_{10\mathrm{g}}$,
  and whole-body SAR $\mathrm{SAR}_{\mathrm{wb}}$. Smaller boxes are the peak-spatial versions
  used by ICNIRP (\cref{sec:compliance}).}
  \label{fig:flowchart}
\end{figure}

## reviews (figure)

_(empty — run /review to populate)_

## grinder notes
- **label**: fig:flowchart
- **caption_preview**: Flowchart of our approach. The formula has five inputs.
