% PREV: \subsection{Configuration}
\Cref{fig:configuration} shows the considered configuration. A
plane wave with intensity $\IPD$ and direction $\khat$ illuminates
the body, and we evaluate $\APD(\rr)$ at each visible surface point.

A harmonic plane wave illuminates a body, with time-averaged Poynting
vector $\mathbf{S}_{\mathrm{inc}} = \IPD\,\khat$ (units W/m$^2$). Three
working assumptions hold throughout. First, the
surface $\Sigma$ is locally flat on the wavelength scale. Second, the
skin depth at every frequency of interest is much smaller than any
body dimension, so all power transmitted through the surface is
absorbed within a thin surface layer. Third, coherent reflections
from internal tissue interfaces and from other body parts are
neglected at this stage and re-enter as bounded corrections in
\cref{sec:cauchy,subsec:corr-residuals}. At a surface point $\rr$ with
outward unit normal $\nhat(\rr)$, the incidence cosine is
$\mu(\rr) \equiv \nhat(\rr)\cdot(-\khat) = \cos\theta_i(\rr)$. A
front-facing point has $\mu > 0$. A point facing away from the
source has $\mu \le 0$.

## reviews (paragraph)



_PaperMaker9000 sweep — 2 flag(s) across 4 lens(es)._

- **sentence-craft** — 1 flag(s), 13 cleared:
    - `style.positive_voice.subject_verb_early` (medium): `A harmonic plane wave with time-averaged Poynting vector $\mathbf{S}_{\mathrm{inc}} = \IPD\,\khat$ (units W/m$^2$) illuminates a body.` -> Front the verb, trail the qualifier: "A harmonic plane wave illuminates a body, with time-averaged Poynting vector $\mathbf{S}_{\mathrm{inc}} = \IPD\,\khat$ (units W/m$^2$)."
    - _dismissed_ `style.positive_voice.no_passive_no_we`: The only natural active rewrite needs an agent (the absorption law) not yet introduced at this setup point, so the active form is genuinely awkward and the exception applies; the passives "is absorbed"/"are neglected" are agentless physics statements, also exempt.
- **voice-tells** — 1 flag(s), 22 cleared:
    - `style.pet_peeves_wout.no_semicolons` (high): `front-facing point has $\mu > 0$; a point facing away from the` -> Replace the semicolon with a period: "...has $\mu > 0$. A point facing away from the source has $\mu \le 0$."
- **lexical-spotcheck** — pass (54 rules cleared).
- **latex-micro** — pass (41 rules cleared).
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

