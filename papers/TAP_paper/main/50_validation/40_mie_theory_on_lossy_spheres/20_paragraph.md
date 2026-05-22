% PREV: For a lossy sphere of radius $a$ and complex refractive index
% PREV: $\ntilde$, the Mie series gives an exact solution for the absorption
% PREV: efficiency $Q_{\mathrm{abs}}$. The geometric law predicts
% PREV: $P_{\mathrm{abs}} = \IPD\,T_0\,\pi a^2$, so its error is
% PREV: $(T_0/Q_{\mathrm{abs}} - 1)$. We use skin properties from the
% PREV: IT'IS database~\cite{ITISv5,Gabriel1996} at each frequency. The total error splits into two
% PREV: contributions. The Fresnel approximation error is shape- and
% PREV: frequency-dependent but size-independent. On a sphere it is the
% PREV: sphere ratio $R = T_0/\langle\Tavg\rangle$, which crosses unity at
% PREV: approximately $39$~GHz (\cref{fig:R-of-f}). The diffraction error is
% PREV: size-dependent and scales as $x^{-2/3}$ in the optical regime, where
% PREV: $x = \pi d/\lambda$ is the size parameter. Diffraction bends waves
% PREV: into the geometric shadow, adding absorption that the surface law
% PREV: misses. We refer to the regime where $x$ is small enough that this
% PREV: diffracted contribution exceeds a few percent of total absorption as
% PREV: the \emph{body-Mie regime}. For body-scale targets it corresponds to
% PREV: frequencies below approximately $6$~GHz.
% NEXT: \begin{figure*}[!t]
% NEXT:   \centering
% NEXT:   \begin{subfigure}[t]{0.48\linewidth}
% NEXT:     \includegraphics[width=\linewidth]{mie_panel_size.pdf}
% NEXT:     \caption{Across size parameter at $28$~GHz.}
% NEXT:     \label{fig:mie:size}
% NEXT:   \end{subfigure}\hfill
% NEXT:   \begin{subfigure}[t]{0.48\linewidth}
% NEXT:     \includegraphics[width=\linewidth]{mie_panel_freq.pdf}
% NEXT:     \caption{Across frequency for four body-part diameters.}
% NEXT:     \label{fig:mie:freq}
% NEXT:   \end{subfigure}
% NEXT:   \caption{Mie validation against lossy spheres with frequency-dependent
% NEXT:   IT'IS skin properties~\cite{ITISv5,Gabriel1996}. (a)~Prediction error versus size parameter
% NEXT:   at $28$~GHz. Vertical dashed lines mark body-part sizes. The
% NEXT:   curve converges from below to the Fresnel limit
% NEXT:   $R_{\mathrm{sphere}}-1\approx -1.2\%$ as $x\to\infty$.
% NEXT:   (b)~Prediction error versus frequency for finger ($17$~mm), arm
% NEXT:   ($80$~mm), head ($180$~mm), and torso ($300$~mm) diameters. The
% NEXT:   wireless mmWave band is shaded green. The orange asymptote is
% NEXT:   $R_{\mathrm{sphere}}(f)-1$, the size-independent Fresnel limit.}
% NEXT:   \label{fig:mie}
% NEXT: \end{figure*}
\Cref{fig:mie} shows the Mie validation. \Cref{fig:mie}(a) shows
the error versus size parameter at $28$~GHz. It converges from
below towards the Fresnel limit $R_{\mathrm{sphere}} - 1 \approx
-1.2\%$ as $x \to \infty$. \Cref{fig:mie}(b) shows the error versus
frequency for four representative body-part diameters.

## reviews (paragraph)



_PaperMaker9000 sweep — all clear across 4 lens(es)._

- **sentence-craft** — pass (14 rules cleared).
- **voice-tells** — pass (22 rules cleared).
    - _dismissed_ `style.pet_peeves_wout.no_anthropomorphism`: The subject is the error curve, a mathematical quantity, not a standard, field, or algorithm; convergence of an error as x to infinity is the literal, correct technical verb, not anthropomorphic intent.
- **lexical-spotcheck** — pass (54 rules cleared).
- **latex-micro** — pass (41 rules cleared).
    - _dismissed_ `latex.structure_style.no_sentence_starting_with_acronym`: Sentence-initial reference uses \Cref (capital C), the cleveref form the cref_capitalized rule explicitly endorses; cleveref produces the capitalized abbreviation automatically, so this is the sanctioned cross-ref mechanism, not a hardcoded "Fig. 1".
    - _dismissed_ `latex.substitutions.approx_text_vs_math`: \approx and the -1.2\% sit inside a single $...$ math span (a relation between math quantities), not a bare prose approximation, so math-mode \approx is correct here.
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

