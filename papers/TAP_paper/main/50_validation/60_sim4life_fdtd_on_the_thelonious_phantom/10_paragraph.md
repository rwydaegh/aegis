% PREV: \subsection{Sim4Life FDTD on the Thelonious phantom}\label{subsec:val-fdtd}
% NEXT: The second metric is the direction-averaged Cauchy formula~\eqref{eq:cauchy-exact}
% NEXT: across $12$ directions and $2$ polarizations at $5.8$~GHz. The ratio
% NEXT: of law to FDTD on direction-averaged total absorbed power is
% NEXT: $1.012$, with $\Aab/A = 0.865$ and $\Tbar(f)$ from \cref{tab:Tbar}.
% NEXT: \Cref{fig:val-fdtd} extends the comparison
% NEXT: across $0.45$--$5.8$~GHz.
The Mie and Fresnel tests check approximations against analytic and
semi-analytic ground truths. Full Sim4Life FDTD on the same
Thelonious mesh, matched dielectric properties, and matched
plane-wave excitation completes the comparison. The comparison
evaluates two regulatory metrics. The first is the IEC/IEEE~63195 peak
$\APD$ averaged over a $4$~cm$^2$ patch. The direction-averaged ratio
of law to FDTD is $1.027$ at $7$~GHz over three lateral and frontal
incidence directions with $\theta$-polarization. A
$\pm 20\%$ uncertainty on the IT'IS dielectric properties~\cite{ITISv5,Gabriel1996} propagates
through the Fresnel coefficient at $7$~GHz to $\pm 7\%$ on
$T_0$. The direction-averaged ratio falls inside this band. The
per-direction values are $1.06$, $1.20$, and $0.83$. The spread
beyond $\pm 7\%$ is set by the reference, not the closed form: FDTD
voxel discretization and per-direction polarization detail give about
$\pm 15\%$ per direction at $7$~GHz, against the closed form's own
$\approx 5\%$ diffraction error (Table~\ref{tab:si-diffraction} of the
SI).

## reviews (paragraph)



_PaperMaker9000 sweep — 3 flag(s) across 4 lens(es)._

- **sentence-craft** — 3 flag(s), 11 cleared:
    - `style.positive_voice.no_passive_no_we` (high): `Two regulatory metrics are evaluated.` -> Active third-person: "The comparison evaluates two regulatory metrics."
    - `style.positive_voice.subject_verb_early` (medium): `At $7$~GHz on three lateral and frontal incidence directions with $\theta$-polarization, the direction-averaged ratio of law to FDTD is $1.027$.` -> Front the subject-verb: "The direction-averaged ratio of law to FDTD is $1.027$ at $7$~GHz over three lateral and frontal incidence directions with $\theta$-polarization."
    - `style.prose_structure.subject_verb_rest` (high): `At $7$~GHz on three lateral and frontal incidence directions with $\theta$-polarization, the direction-averaged ratio of law to FDTD is $1.027$.` -> Reorder to subject-verb-rest, moving the fronted condition clause to the end of the sentence.
- **voice-tells** — pass (22 rules cleared).
- **lexical-spotcheck** — pass (54 rules cleared).
- **latex-micro** — pass (41 rules cleared).
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

