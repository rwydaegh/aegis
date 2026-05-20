% PREV: The bound follows from energy conservation on the cube footprint,
# Peak spatial-average SAR over a 10~g cube

<!-- AUTO_BEGIN: assembled -->
% NEXT: Below $6$~GHz the ICNIRP basic restriction is the peak spatial-average
\subsection{Peak spatial-average SAR over a 10~g cube}\label{subsec:compl-cube}

% PREV: \subsection{Peak spatial-average SAR over a 10~g cube}\label{subsec:compl-cube}
% NEXT: The following bound links the cube quantity to APD.
Below $6$~GHz the ICNIRP basic restriction is the peak spatial-average
SAR over a $10$~g cube~\cite{ICNIRP2020,62704-1}. An
energy-conservation argument on the cube footprint bounds this
restriction by the absorbed power density, so no explicit cube search
is needed.

% PREV: Below $6$~GHz the ICNIRP basic restriction is the peak spatial-average
% NEXT: The bound follows from energy conservation on the cube footprint,
The following bound links the cube quantity to APD.
\begin{theorem}\label{thm:apd-bound}
For an axis-aligned $10$~g cube placed per IEC/IEEE~62704-1 on a planar
three-layer body, the peak spatial-average SAR satisfies
\begin{equation}\label{eq:apd-bound}
  \mathrm{psSAR}_{10\mathrm{g}}
  \;\le\; \frac{\sqrt{2}\,\APDAvg}{\rho_m\,L}\, ,
\end{equation}
where $L = (m/\rho_m)^{1/3} = 21.5$~mm and $\APDAvg$ is the local
absorbed power density. At the ICNIRP basic restriction
$\APDAvg \le 10$~W/m$^2$, this implies
$\mathrm{psSAR}_{10\mathrm{g}} \le 0.66$~W/kg, a factor of three below
the head and trunk basic restriction of $2$~W/kg and a factor of six
below the limb restriction of $4$~W/kg.
\end{theorem}

% PREV: The following bound links the cube quantity to APD.
% NEXT: # Peak spatial-average SAR over a 10~g cube
The bound follows from energy conservation on the cube footprint,
with the $\sqrt{2}$ factor covering the worst-case tilt between cube
axes and body normal. Section~\ref{si:apd-bound} of the SI derives the bound,
gives the cube-intersection geometry under the IEC mass rule, and
confirms it on Thelonious to within a median ratio of $1.30$. The same
surface integral that delivers $\APDAvg$ therefore controls
$\mathrm{psSAR}_{10\mathrm{g}}$.
<!-- AUTO_END: assembled -->





## section notes

_(AI-owned notes about this section as a whole)_
