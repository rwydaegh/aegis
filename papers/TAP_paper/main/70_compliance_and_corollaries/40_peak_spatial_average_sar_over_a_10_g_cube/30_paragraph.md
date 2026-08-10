% PREV: The following bound links the cube quantity to APD. For an axis-aligned
% PREV: $10$~g cube placed per IEC/IEEE~62704-1 on a planar
% PREV: three-layer body, the peak spatial-average SAR satisfies
% PREV: \begin{equation}\label{eq:apd-bound}
% PREV:   \mathrm{psSAR}_{10\mathrm{g}}
% PREV:   \;\le\; \frac{\sqrt{2}\,\APDAvg}{\rho_m\,L}\, ,
% PREV: \end{equation}
% PREV: where $L = (m/\rho_m)^{1/3} = 21.5$~mm and $\APDAvg$ is the local
% PREV: absorbed power density. At the ICNIRP basic restriction
% PREV: $\APDAvg \le 10$~W/m$^2$, this implies
% PREV: $\mathrm{psSAR}_{10\mathrm{g}} \le 0.66$~W/kg, a factor of three below
% PREV: the head and trunk basic restriction of $2$~W/kg and a factor of six
% PREV: below the limb restriction of $4$~W/kg.
The bound follows from energy conservation on the cube footprint,
with the $\sqrt{2}$ factor covering the worst-case tilt between cube
axes and body normal. Section~\ref{si:apd-bound} of the SI derives the bound,
gives the cube-intersection geometry under the IEC mass rule, and
confirms it on Thelonious to within a median ratio of $1.30$. The same
surface integral that gives $\APDAvg$ therefore controls
$\mathrm{psSAR}_{10\mathrm{g}}$.

## reviews (paragraph)



_PaperMaker9000 sweep — all clear across 4 lens(es)._

- **sentence-craft** — pass (14 rules cleared).
- **voice-tells** — pass (22 rules cleared).
- **lexical-spotcheck** — pass (54 rules cleared).
- **latex-micro** — pass (41 rules cleared).
- **incremental (2026-05-22)** — 1 flag(s):
    - `style.prose_structure.kiss_simple_verbs` (high): `The same surface integral that delivers $\APDAvg$ therefore controls` -> Replace 'delivers' with 'gives' (the integral yields APD); 'controls' stays as it carries the distinct bounding meaning.
