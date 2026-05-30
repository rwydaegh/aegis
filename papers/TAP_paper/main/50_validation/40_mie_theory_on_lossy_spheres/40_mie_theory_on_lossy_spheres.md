% PREV: \begin{figure*}[!t]
% NEXT: For body-relevant sizes (head, torso) over 6--100~GHz, the error ranges
# Mie theory on lossy spheres

<!-- AUTO_BEGIN: assembled -->
\subsection{Mie theory on lossy spheres}\label{subsec:val-mie}

For a lossy sphere of radius $a$ and complex refractive index
$\ntilde$, the Mie series gives an exact solution for the absorption
efficiency $Q_{\mathrm{abs}}$. The geometric law predicts
$P_{\mathrm{abs}} = \IPD\,T_0\,\pi a^2$, so its error is
$(T_0/Q_{\mathrm{abs}} - 1)$. We use skin properties from the
IT'IS database~\cite{ITISv5,Gabriel1996} at each frequency. The total error splits into two
contributions. The Fresnel approximation error is shape- and
frequency-dependent but size-independent. On a sphere it is the
sphere ratio $R = T_0/\langle\Tavg\rangle$, which crosses unity at
approximately $39$~GHz (\cref{fig:R-of-f}). The diffraction error is
size-dependent and scales as $x^{-2/3}$ in the optical regime, where
$x = \pi d/\lambda$ is the size parameter. Diffraction bends waves
into the geometric shadow, adding absorption that the surface law
misses. We refer to the regime where $x$ is small enough that this
diffracted contribution exceeds a few percent of total absorption as
the \emph{body-Mie regime}. For body-scale targets it corresponds to
frequencies below approximately $6$~GHz.

\Cref{fig:mie} shows the Mie validation. \Cref{fig:mie}(a) shows
the error versus size parameter at $28$~GHz. It converges from
below towards the Fresnel limit $R_{\mathrm{sphere}} - 1 \approx
-1.2\%$ as $x \to \infty$. \Cref{fig:mie}(b) shows the error versus
frequency for four representative body-part diameters.

\begin{figure*}[!t]
  \centering
  \begin{subfigure}[t]{0.48\linewidth}
    \includegraphics[width=\linewidth]{mie_panel_size.pdf}
    \caption{Across size parameter at $28$~GHz.}
    \label{fig:mie:size}
  \end{subfigure}\hfill
  \begin{subfigure}[t]{0.48\linewidth}
    \includegraphics[width=\linewidth]{mie_panel_freq.pdf}
    \caption{Across frequency for four body-part diameters.}
    \label{fig:mie:freq}
  \end{subfigure}
  \caption{Mie validation against lossy spheres with frequency-dependent
  IT'IS skin properties~\cite{ITISv5,Gabriel1996}. (a)~Prediction error versus size parameter
  at $28$~GHz. Vertical dashed lines mark body-part sizes. The
  curve converges from below to the Fresnel limit
  $R_{\mathrm{sphere}}-1\approx -1.2\%$ as $x\to\infty$.
  (b)~Prediction error versus frequency for finger ($17$~mm), arm
  ($80$~mm), head ($180$~mm), and torso ($300$~mm) diameters. The
  wireless mmWave band is shaded green. The orange asymptote is
  $R_{\mathrm{sphere}}(f)-1$, the size-independent Fresnel limit.}
  \label{fig:mie}
\end{figure*}

For body-relevant sizes (head, torso) over 6--100~GHz, the error ranges
from $0.4\%$ on a torso at $100$~GHz to $14\%$ on a head at
$28$~GHz, set mostly by diffraction into the geometric shadow at
the low end of the band. At $28$~GHz the law underestimates
absorption.
For fingers below 6~GHz, errors exceed $30\%$. On
body-scale objects in the claimed regime, the residual stays within
the dielectric uncertainty on $T_0$ (\cref{fig:err-budget}).
Per-frequency residuals across four body-part diameters ($17$, $80$,
$180$, $300$~mm) are in Table~\ref{tab:mie-residual} of the SI.
<!-- AUTO_END: assembled -->






## section notes

_(AI-owned notes about this section as a whole)_
