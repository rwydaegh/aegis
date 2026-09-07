% PREV: The Brewster angle of a lossless dielectric is $\theta_{\mathrm{B}} =
% PREV: \arctan(n_2/n_1)$, at which the TM reflection coefficient
% PREV: vanishes~\cite{BornWolf1999}. For a lossy dielectric the reflection
% PREV: minimum is finite but small. The angle that minimizes $|r_p|^2$ is
% PREV: the \textit{pseudo-Brewster angle} and satisfies
% PREV: $\theta_{\mathrm{pB}} \approx \arctan|\ntilde|$ to within $1^\circ$ for
% PREV: $|\ntilde| > 3$~\cite{Potter1970,Ohman1977}. At this angle, $T_p$
% PREV: peaks near $0.95$, whereas $T_s$ has fallen below $0.20$. Their
% PREV: average $\Tavg(\theta_{\mathrm{pB}}) \approx 0.5$ is close to the
% PREV: normal-incidence value $T_0 \approx 0.5$--$0.6$ for biological
% PREV: tissue at mmWave.
Azzam~\cite{Azzam2015} showed that for lossless dielectric substrates
with refractive index $|\ntilde| > 2 + \sqrt{3} \approx 3.73$, the
unpolarized reflectance varies by less than $1\%$ over $[0^\circ,
60^\circ]$. Empirically, the near-constancy extends to $|\ntilde| > 2.5$,
below the strict Azzam threshold. The SI evaluates this extension on
the IT'IS tissue-properties database~\cite{ITISv5,Gabriel1996}. Biological tissue in the wireless mmWave
band has $|\ntilde| \in [3, 6]$, putting it in the high-index
regime. This connection between the Azzam criterion and biological dosimetry
has not appeared in the antenna propagation or bioelectromagnetics literature;
prior work has evaluated the angular and polarization
dependence of body transmission above $6$~GHz
numerically~\cite{Samaras2019} without the high-index reduction.

## reviews (paragraph)



_PaperMaker9000 sweep — all clear across 4 lens(es)._

- **sentence-craft** — pass (14 rules cleared).
- **voice-tells** — pass (22 rules cleared).
- **lexical-spotcheck** — pass (54 rules cleared).
- **latex-micro** — pass (41 rules cleared).
    - _dismissed_ `latex.substitutions.units_math_mode_consistent`: The number sits in math mode and GHz is a text-mode tied unit, matching the paper's established convention (28~GHz, 100~GHz, sub-6~GHz, and other $6$~GHz / $100$~GHz instances in main.md); this is a clean tied unit, not a stranded thin-space drift, so no defect.
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).
