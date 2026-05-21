% PREV: \subsection{Mechanism}\label{subsec:pB-mech}
% NEXT: Azzam~\cite{Azzam2015} showed that for lossless dielectric substrates
The Brewster angle of a lossless dielectric is $\theta_{\mathrm{B}} =
\arctan(n_2/n_1)$, at which the TM reflection coefficient
vanishes~\cite{BornWolf1999}. For a lossy dielectric the reflection
minimum is finite but small. The angle at which $|r_p|^2$ is
minimized is the \textit{pseudo-Brewster angle} and satisfies
$\theta_{\mathrm{pB}} \approx \arctan|\ntilde|$ to within $1^\circ$ for
$|\ntilde| > 3$~\cite{Potter1970,Ohman1977}. At this angle, $T_p$
peaks near $0.95$, while $T_s$ has fallen below $0.20$. Their
average $\Tavg(\theta_{\mathrm{pB}}) \approx 0.5$ is close to the
normal-incidence value $T_0 \approx 0.5$--$0.6$ for biological
tissue at mmWave.

## reviews (paragraph)


_PaperMaker9000 sweep — 2 flag(s) across 4 lens(es)._

- **sentence-craft** — 1 flag(s), 13 cleared:
    - `style.positive_voice.no_passive_no_we` (high): "The angle at which $|r_p|^2$ is minimized is the \textit{pseudo-Brewster angle}" → Use the active relative clause: "The angle that minimizes $|r_p|^2$ is the pseudo-Brewster angle" (drops the passive and one copula).
- **voice-tells** — pass (22 rules cleared).
- **lexical-spotcheck** — 1 flag(s), 53 cleared:
    - `BOOK_ELOS_style.misused_words.while_as_although` (low): "$T_p$ peaks near $0.95$, while $T_s$ has fallen below $0.20$." → Replace contrastive "while" with "whereas": "$T_p$ peaks near $0.95$, whereas $T_s$ has fallen below $0.20$."
- **latex-micro** — pass (41 rules cleared).
    - _dismissed_ `latex.math.subscript_labels_upright`: p/s are conventional optics polarization-state labels written italic and used consistently here and paper-wide (matching $r_p$); forcing \mathrm would break the established notation.
    - _dismissed_ `latex.structure_style.acronym_first_use`: TM is registered via \newacronym{TM}{TM}{Transverse Magnetic} and expanded by the glossaries package paper-wide; first-use handling is not a per-leaf concern, and TE/TM are standard optics labels.
    - _dismissed_ `latex.substitutions.approx_text_vs_math`: \approx sits inside genuine inline math relations (and $\Tavg(\theta_{\mathrm{pB}}) \approx 0.5$), not a prose approximation, so the math symbol is correct.

